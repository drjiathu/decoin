from concurrent import futures
import datetime
from pathlib import Path
import time
from urllib.parse import unquote

import pandas as pd
import requests
from tqdm import tqdm

from app.utils import retry, stream_download, wait_then_exec


def get_option_underlyings():
    url = "https://www.okx.com/api/v5/public/underlying"
    params = {"instType": "OPTION"}

    # response = get_with_proxy_rotation(url, params=params)
    response = requests.get(url, params=params)
    data = response.json()
    return data["data"][0]


def get_option_instruments(uly: str):
    url = "https://www.okx.com/api/v5/public/instruments"
    params = {"instType": "OPTION", "uly": uly}  # 必填参数

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data["code"] != "0":
            print(f"API错误: {data['msg']}")
            return []

        return data["data"]

    except Exception as e:
        print(f"请求失败: {e}")
        return []


def get_all_options():
    underlyings = get_option_underlyings()
    all_options = []

    for uly in underlyings:
        print(f"正在获取 {uly} 的期权数据...")
        options = get_option_instruments(uly)
        all_options.extend(options)
        time.sleep(0.1)  # 控制速率

    return all_options


def get_instruments(
    inst_type,
    uly: str = None,
    inst_family: str = None,
    inst_id: str = None,
) -> pd.DataFrame:
    """
    获取OKX指定类型的产品信息
    :param
        inst_type:
            1. SPOT(现货)
            2. MARGIN(币币杠杆)
            3. SWAP(永续)
            4. FUTURES(交割)
            5. OPTION(期权), 必填 `uly`
    :return: DataFrame格式的产品信息
    """
    url = "https://www.okx.com/api/v5/public/instruments"
    params = {
        "instType": inst_type,
        "uly": uly,
        "instFamily": inst_family,
        "instId": inst_id,
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # 检查HTTP错误
        data = response.json()

        if data["code"] != "0":  # OKX API返回码0表示成功
            raise Exception(f"API Error: {data['msg']}")

        # 提取数据并转为DataFrame
        df = pd.DataFrame(data["data"])
        # 过滤需要的列, 详细字段内容可参考官方 API 文档
        # https://my.okx.com/docs-v5/zh/#public-data-rest-api
        columns = [
            "instId",  # 产品id，如 BTC-USDT
            "instType",  # 产品类型
            "uly",  # 标的指数，如 BTC-USD，仅适用于杠杆/交割/永续/期权
            "instFamily",  # 交易品种，如 BTC-USD，仅适用于杠杆/交割/永续/期权
            "baseCcy",  # 交易货币币种，如 BTC-USDT 中的 BTC ，仅适用于币币/币币杠杆
            "quoteCcy",  # 计价货币币种，如 BTC-USDT 中的USDT ，仅适用于币币/币币杠杆
            "settleCcy",  # 盈亏结算和保证金币种，如 BTC 仅适用于交割/永续/期权
            "ctVal",  # 合约面值，仅适用于交割/永续/期权
            "ctMult",  # 合约乘数，仅适用于交割/永续/期权
            "ctValCcy",  # 合约面值计价币种，仅适用于交割/永续/期权
            "optType",  # 期权类型，C或P 仅适用于期权
            "stk",  # 行权价格，仅适用于期权
            "listTime",  # 上线时间, Unix时间戳的毫秒数格式，如 "1597026383085"
            "auctionEndTime",  # 集合竞价结束时间，Unix时间戳的毫秒数格式，如 "1597026383085", 仅适用于通过集合竞价方式上线的币币，其余情况返回""
            "expTime",  # String	产品下线时间, 适用于币币/杠杆/交割/永续/期权，对于 交割/期权，为交割/行权日期；亦可以为产品下线时间，有变动就会推送。
            "lever",  # 该instId支持的最大杠杆倍数，不适用于币币、期权
            "tickSz",  # 下单价格精度，如 0.0001。对于期权来说，是梯度中的最小下单价格精度，如果想要获取期权价格梯度，请使用"获取期权价格梯度"接口
            "lotSz",  # 下单数量精度。合约的数量单位是张，现货的数量单位是交易货币
            "minSz",  # 最小下单数量。合约的数量单位是张，现货的数量单位是交易货币
            "ctType",  # 合约类型
            "state",  # 产品状态
            "ruleType",  # 交易规则类型
            "maxLmtSz",  # 限价单的单笔最大委托数量
            "maxMktSz",  # 市价单的单笔最大委托数量
            "maxLmtAmt",  # 限价单的单笔最大美元价值
            "maxMktAmt",  # 市价单的单笔最大美元价值
            "maxTwapSz",  # 时间加权单的单笔最大委托数量
            "maxIcebergSz",  # 冰山委托的单笔最大委托数量
            "maxTriggerSz",  # 计划委托委托的单笔最大委托数量
            "maxStopSz",  # 止盈止损市价委托的单笔最大委托数量
        ]
        return df[columns] if not df.empty else df

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None


@retry(max_retries=3)
def get_all_markets(inst_type: str = None) -> pd.DataFrame:
    all_types = ["SPOT", "MARGIN", "SWAP", "FUTURES", "OPTION"]
    inst_types = [inst_type] if inst_type else all_types
    data = []
    for inst_type in inst_types:
        if inst_type == "OPTION":
            underlyings = get_option_underlyings()
            for uly in underlyings:
                data.append(get_instruments(inst_type, uly))
        else:
            data.append(get_instruments(inst_type))
    df = pd.concat(data, axis=0, ignore_index=True)
    return df


def fetch_historical_candles(
    inst_id: str,
    bar="1m",
    start_ms: int = None,
    end_ms: int = None,
):
    """从 API 获取最近几年的历史k线数据(1s k线支持查询最近3个月的数据)

    Parameters
    ----------
    inst_id : str

    bar : str, optional
        K线图维度, by default "1m" 分钟线
    start_ms : int, optional
        起始ms时间戳, REST API 设定为不包含起始时间点, by default None
    end_ms : int, optional
        截止ms时间戳, REST API 设定为不包含截止时间点, by default None

    Returns
    -------
    _type_
        _description_
    """
    url = "https://www.okx.com/api/v5/market/history-candles"
    period = 2 / 20  # 限速 20次/2s
    all_data = []
    current_end = end_ms
    while True:
        params = {"instId": inst_id, "bar": bar, "after": current_end, "limit": "100"}
        if start_ms:
            params["before"] = start_ms
        try:
            response = requests.get(url, params=params)
            data = response.json()

            # 错误处理
            if data["code"] != "0":
                print(f"API错误: {data['msg']}")
                break
            # 无数据处理
            if not data["data"]:
                break

            candles = data["data"]
            all_data.extend(candles)
            # 获取最早一条数据的时间戳
            earliest_ms = int(candles[-1][0])
            if start_ms and earliest_ms <= start_ms:
                break

            current_end = earliest_ms - 1  # 避免重复
            time.sleep(period)  # 控制请求频率

        except Exception as e:
            print(f"Error fetching data: {e}")
            break
    # 转换为DataFrame
    df = pd.DataFrame(
        all_data,
        columns=[
            "ts",
            "open",
            "high",
            "low",
            "close",
            "vol",
            "volCcy",
            "volCcyQuote",
            "confirm",
        ],
    )
    df["ts"] = pd.to_datetime(df["ts"].astype(int), utc=True, unit="ms")
    df[["open", "high", "low", "close", "vol"]] = df[
        ["open", "high", "low", "close", "vol"]
    ].apply(pd.to_numeric)
    return df.sort_values("ts").reset_index(drop=True)


@retry(max_retries=3)
def fetch_funding_rate(inst_id: str) -> dict:
    """获取永续合约资金费率数据

    Parameters
    ----------
    inst_id : str
    """
    url = "https://www.okx.com/api/v5/public/funding-rate"
    params = {"instId": inst_id}
    try:
        response = requests.get(url, params=params)
        data = response.json()

        # 错误处理
        if data["code"] != "0":
            print(f"API错误: {data['msg']}")
        if not data["data"]:
            raise ValueError(f"API获取{inst_id}资金费率为空")
    except Exception as e:
        print(f"请求失败: {e}")
    rate = data["data"][0]

    return rate


def fetch_all_funding_rate() -> pd.DataFrame:
    swaps = get_all_markets(inst_type="SWAP")
    funding_rates = []
    pbar = tqdm(swaps["instId"])
    for inst_id in pbar:
        pbar.set_description(desc=f"fetching {inst_id}")
        funding_rates.append(fetch_funding_rate(inst_id))
        # time.sleep(2 / 20)  # 限速：20次/2s
    df = pd.DataFrame(funding_rates)
    if not df.empty:
        for ts_col in ["fundingTime", "nextFundingTime", "ts"]:
            df[ts_col] = pd.to_datetime(df[ts_col].astype(int), utc=True, unit="ms")
        for rate_col in [
            "fundingRate",
            "nextFundingRate",
            "minFundingRate",
            "maxFundingRate",
            "settFundingRate",
            "premium",
        ]:
            df[rate_col] = pd.to_numeric(df[rate_col], errors="coerce")
        df = df.sort_values("instId").reset_index(drop=True)

    return df


def download_historical_funding_rates(date: datetime.date | pd.Timestamp):
    savepath = Path("./data/swaprate")
    savepath.mkdir(parents=True, exist_ok=True)
    wraprate_monthly_url = "https://www.okx.com/cdn/okex/traderecords/swaprate/monthly/"
    filename = "swaprate-" + date.strftime("%Y-%m-%d") + ".zip"
    url = wraprate_monthly_url + date.strftime("%Y%m") + "/allswaprate-" + filename
    filepath = savepath.joinpath(filename)
    stream_download(url, filepath)


class OKXDownloader:
    def __init__(self, savepath: Path = Path(".data"), max_workers=5, rate_limit=0):
        """
        :param max_workers: 最大并发工作线程数
        :param rate_limit: 请求间隔（秒）
        """
        self.savepath: Path = savepath
        self.rate_limit = rate_limit
        self.executor = futures.ThreadPoolExecutor(max_workers=max_workers)
        self._urls: list[str] = None
        self._futures: list[futures.Future] = []

    def _submit_tasks(self):
        """带速率控制的下载任务"""
        for i, url in enumerate(self._urls):
            filename = unquote(url.split("/")[-1])
            filepath = self.savepath.joinpath(filename)
            target = wait_then_exec(self.rate_limit * i)(stream_download)
            future = self.executor.submit(target, url, filepath)
            self._futures.append(future)

    def add_urls(self, urls: str | list[str]):
        """添加下载任务"""
        if isinstance(urls, str):
            urls = [urls]
        self._urls = urls

    def _monitor(self):
        num = 0
        for f in futures.as_completed(self._futures):
            filepath = f.result()
            print(f"{filepath} downloading complete")
            num += 1
        print(f"{num} files downloaded")

    def start(self):
        """启动下载任务"""
        self.savepath.mkdir(parents=True, exist_ok=True)
        self._submit_tasks()
        self._monitor()
