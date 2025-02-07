import requests
import time

import pandas as pd

# from app.utils import get_with_proxy_rotation


def get_okx_option_underlyings():
    url = "https://www.okx.com/api/v5/public/underlying"
    params = {"instType": "OPTION"}

    # response = get_with_proxy_rotation(url, params=params)
    response = requests.get(url, params=params)
    data = response.json()
    return data["data"][0]


def get_okx_option_instruments(uly: str):
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
    underlyings = get_okx_option_underlyings()
    all_options = []

    for uly in underlyings:
        print(f"正在获取 {uly} 的期权数据...")
        options = get_okx_option_instruments(uly)
        all_options.extend(options)
        time.sleep(0.1)  # 控制速率

    return all_options


def get_okx_instruments(
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


def get_all_okx_markets() -> pd.DataFrame:
    inst_types = ["SPOT", "MARGIN", "SWAP", "FUTURES", "OPTION"]
    data = []
    for inst_type in inst_types:
        if inst_type == "OPTION":
            underlyings = get_okx_option_underlyings()
            for uly in underlyings:
                data.append(get_okx_instruments(inst_type, uly))
        else:
            data.append(get_okx_instruments(inst_type))
    df = pd.concat(data, axis=0)
    return df
