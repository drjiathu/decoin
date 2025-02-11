import asyncio
import aiohttp
from concurrent import futures
import datetime
from functools import wraps
from pathlib import Path
import time
from urllib.parse import unquote
from zoneinfo import ZoneInfo

import pandas as pd
import requests


def _wait_and_exec(wait=0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            time.sleep(wait)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def download_one(url, filepath):
    # 流式下载大文件
    with requests.get(url, stream=True, timeout=10) as r:
        r.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:  # 过滤保持连接的空白块
                    f.write(chunk)
    return filepath


def download_many(
    urls: list[str],
    save_path: Path = Path("./data"),
    speed_limit=0.1,
    max_workers=5,
) -> int:
    with futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        todo: list[futures.Future] = []
        for url in urls:
            filename = unquote(url.split("/")[-1])
            future = executor.submit(download_one, url, save_path.joinpath(filename))
            todo.append(future)
            print(f"Scheduled for {url}: {future}")
    num = 0
    for _ in futures.as_completed(todo):
        num += 1

    return num


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
            target = _wait_and_exec(self.rate_limit * i)(download_one)
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


#     def stop(self):
#         """停止下载服务"""
#         self.executor.shutdown(wait=True)
#         print("jobs done")


def main1():
    # 示例使用
    # downloader = OKXDownloader(max_workers=10, rate_limit=0.1)

    # 添加示例下载任务（替换为实际OKX数据URL）
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
    # download_many(urls=tasks, save_path=Path("./data/swaprate"), speed_limit=0.1)
    downloader = OKXDownloader(Path("./data/testdata"))
    downloader.add_urls(urls)
    # 开始下载
    downloader.start()


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


# # 主函数
# async def main():
#     # API 基础 URL
#     base_url = "https://www.okx.com/cdn/okex/traderecords/swaprate/monthly/date.strftime('%Y%m')/allswaprate-"
#     filename = "swaprate-{date.strftime('%Y-%m-%d')}.zip"
#     url = base_url + filename
#     filepath = savepath.joinpath(filename)
#     end_date = datetime.datetime.now(tz=ZoneInfo("UTC")).date() - datetime.timedelta(
#         days=1
#     )
#     start_date = datetime.date(2021, 10, 1)
#     dates = pd.date_range(start=start_date, end=end_date)
#     url_list = [url.format(date=d) for d in dates]

#     # 创建信号量，限制并发数为 20
#     semaphore = asyncio.Semaphore(20)

#     # 创建 aiohttp 会话
#     async with aiohttp.ClientSession() as session:
#         # 创建任务列表
#         tasks = [
#             limited_fetch(session, url, semaphore=semaphore, speed_limit=0.1)
#             for url in url_list
#         ]

#         # 并发执行任务并等待所有任务完成
#         results = await asyncio.gather(*tasks)

#         # 处理结果
#         for result in results:
#             print(result)


# 运行主函数
if __name__ == "__main__":
    # asyncio.run(main())
    main1()
