import aiofiles
from concurrent import futures
import datetime
from enum import Enum
from http import HTTPStatus
from pathlib import Path
import time
from typing import Iterator
from urllib.parse import unquote
from zoneinfo import ZoneInfo

import ccxt
import httpx
import pandas as pd


from app.api.okx import OKXDownloader
from app.utils import stream_download

DownloadStatus = Enum("DownloadStatus", "OK NOT_FOUND ERROR")


def get_ccxt_history(symbol, timeframe="1m", since=None, limit=1000):
    exchange = ccxt.okx(
        {
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},  # 永续合约类型：swap/spot
        }
    )
    since = exchange.parse8601(since)

    all_ohlcv = []
    while True:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
        if not ohlcv:
            break
        since = ohlcv[-1][0] + 1
        all_ohlcv.extend(ohlcv)
        print(
            f"Fetched {len(ohlcv)} candles up to {pd.to_datetime(ohlcv[-1][0], unit='ms')}"
        )
        time.sleep(exchange.rateLimit / 1000)  # 严格遵守速率限制

    df = pd.DataFrame(
        all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def download_many(
    urls: list[str],
    save_path: Path = Path("./data"),
    max_workers=5,
) -> int:
    with futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        todo: list[futures.Future] = []
        for url in urls:
            filename = unquote(url.split("/")[-1])
            future = executor.submit(stream_download, url, save_path.joinpath(filename))
            todo.append(future)
            print(f"Scheduled for {url}: {future}")
    num = 0
    for _ in futures.as_completed(todo):
        num += 1

    return num


def main1():
    base = "https://www.okx.com/cdn/okex/traderecords/swaprate/monthly/"
    end_date = datetime.datetime.now(tz=ZoneInfo("UTC")).date() - datetime.timedelta(
        days=1
    )
    start_date = datetime.date(2021, 10, 1)
    dates = pd.date_range(start=start_date, end=end_date)
    urls = [
        base + f"{d.strftime('%Y%m')}/allswaprate-swaprate-{d.strftime('%Y-%m-%d')}.zip"
        for d in dates
    ]
    downloader = OKXDownloader(Path("./data/testdata"))
    downloader.add_urls(urls)
    downloader.start()


async def download_file(client: httpx.AsyncClient, url: str, filepath: Path) -> int:
    total_size: int = 0
    async with client.stream("GET", url=url) as resp:
        # resp = await client.get(url=url)
        resp.raise_for_status()
        # 打开本地文件进行写入
        async with aiofiles.open(filepath, "wb") as f:
            # 逐块读取并写入文件
            async for chunk in resp.aiter_bytes(chunk_size=8192):
                if chunk:  # 过滤保持连接的空白块
                    await f.write(chunk)
                    total_size += len(chunk)
    return total_size


async def get_resp(client: httpx.AsyncClient, url: str) -> Iterator[bytes]:
    async with client.stream("GET", url=url) as resp:
        resp.raise_for_status()
        return resp.iter_bytes(chunk_size=8192)


async def save_file(resp_it: Iterator[bytes], filepath: Path) -> int:
    file_size = 0
    async with aiofiles.open(filepath, "wb") as f:
        async for chunk in resp_it:
            if chunk:
                await f.write(chunk)
                file_size += len(chunk)
    return file_size


async def download_one(
    client: httpx.AsyncClient,
    date: datetime.date,
    base_url: str,
    filepath: Path,
    # semaphore: asyncio.Semaphore,
    verbose: bool,
) -> DownloadStatus:
    try:
        # async with semaphore:
        url = (
            base_url
            + f"{date.strftime('%Y%m')}/allswap-trades-{date.strftime('%Y-%m-%d')}.zip"
        )
        content_iter = await get_resp(client, url)
    except httpx.HTTPStatusError as exc:
        res = exc.response
        if res.status_code == HTTPStatus.NOT_FOUND:
            status = DownloadStatus.NOT_FOUND
            msg = f"not found: {res.url}"
        else:
            status = DownloadStatus.ERROR
            raise
    else:
        # await asyncio.to_thread(save_file, content_iter, filepath)
        await save_file(content_iter, filepath)
        status = DownloadStatus.OK
        msg = "DOWNLOADED"
    if verbose and msg:
        print(filepath, msg)
    return status


# async def fetch_historical_data(session, instId, start, end):
#     url = "https://www.okx.com/api/v5/market/candles"
#     params = {
#         "instId": instId,
#         "bar": "1m",
#         "before": int(start.timestamp() * 1000),
#         "after": int(end.timestamp() * 1000),
#         "limit": 100,
#     }
#     async with session.get(url, params=params) as response:
#         data = await response.json()
#         return data.get("data", [])


# # 模拟的 API 请求函数
# async def download(session, url, params):
#     async with session.get(url, params=params) as response:
#         try:
#             response = requests.get(url, stream=True)
#             response.raise_for_status()  # 检查 HTTP 状态码
#             with open(save_path, "wb") as f:
#                 for chunk in response.iter_content(chunk_size=8192):
#                     f.write(chunk)
#             print(f"文件已下载到: {save_path}")
#         except requests.exceptions.RequestException as e:
#             print(f"下载失败: {e}")


# async def main():
#     instId = "BTC-USDT-SWAP"
#     start_date = datetime(2020, 1, 1)
#     end_date = datetime(2023, 12, 31)
#     date_chunks = [start_date + timedelta(days=i * 30) for i in range(48)]  # 按月分片

#     async with aiohttp.ClientSession() as session:
#         tasks = []
#         for i in range(len(date_chunks) - 1):
#             task = fetch_historical_data(
#                 session, instId, date_chunks[i], date_chunks[i + 1]
#             )
#             tasks.append(task)

#         results = await asyncio.gather(*tasks)
#         all_data = [item for sublist in results for item in sublist]


# # 执行异步采集
# asyncio.run(main())


# # 任务函数，控制请求速率
# async def limited_fetch(session, url, params, semaphore, speed_limit):
#     async with semaphore:  # 限制并发数
#         await asyncio.sleep(speed_limit)  # 控制请求间隔
#         return await fetch(session, url, params)


# 主函数
async def main():
    # API 基础 URL
    date = datetime.date(2025, 2, 10)
    # aggtrades_url = f"https://www.okx.com/cdn/okex/traderecords/aggtrades/monthly/{date.strftime('%Y%m')}/allfuture-aggtrades-{date.strftime('%Y-%m-%d')}.zip"
    # swaprate_url = "https://www.okx.com/cdn/okex/traderecords/swaprate/monthly/"
    trades_url = "https://www.okx.com/cdn/okex/traderecords/trades/monthly/"
    filepath = Path("./data/test.zip")
    async with httpx.AsyncClient() as client:
        # file_size = await download_file(client, url, Path("./data/test.zip"))
        await download_one(client, date, trades_url, filepath, verbose=True)
    # filename = "allswaprate-swaprate-" + date.isoformat() + ".zip"

    # filepath = savepath.joinpath(filename)
    # end_date = datetime.datetime.now(tz=ZoneInfo("UTC")).date() - datetime.timedelta(
    #     days=1
    # )
    # start_date = datetime.date(2021, 10, 1)
    # dates = pd.date_range(start=start_date, end=end_date)
    # url_list = [url.format(date=d) for d in dates]

    # # 创建信号量，限制并发数为 20
    # semaphore = asyncio.Semaphore(20)

    # # 创建 aiohttp 会话
    # async with aiohttp.ClientSession() as session:
    #     # 创建任务列表
    #     tasks = [
    #         limited_fetch(session, url, semaphore=semaphore, speed_limit=0.1)
    #         for url in url_list
    #     ]

    #     # 并发执行任务并等待所有任务完成
    #     results = await asyncio.gather(*tasks)

    #     # 处理结果
    #     for result in results:
    #         print(result)


# 运行主函数
if __name__ == "__main__":
    # asyncio.run(main())
    # main1()
    x = test()
