from concurrent import futures
import datetime
from pathlib import Path
from urllib.parse import unquote
from zoneinfo import ZoneInfo

import pandas as pd


from app.api.okx import (
    OKXDownloader,
    download_historical_funding_rates,
    download_all_historical_funding_rates,
)
from app.utils import stream_download

START_DATE = datetime.date(2021, 10, 1)


def download_many(
    urls: list[str], save_path: Path = Path("./data"), max_workers=5
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


def main():
    base = "https://www.okx.com/cdn/okex/traderecords/swaprate/monthly/"
    end_date = datetime.datetime.now(tz=ZoneInfo("UTC")).date() - datetime.timedelta(
        days=1
    )
    dates = pd.date_range(start=START_DATE, end=end_date)
    urls = [
        base + f"{d.strftime('%Y%m')}/allswaprate-swaprate-{d.strftime('%Y-%m-%d')}.zip"
        for d in dates
    ]
    downloader = OKXDownloader(Path("./data/testdata"))
    downloader.add_urls(urls)
    downloader.start()


def update_swaprates():
    swaprate_datapath = Path("./data/OKX") / "swaprate"
    files = sorted(swaprate_datapath.glob("*.zip"), reverse=True)
    date = datetime.date(*map(int, files[0].stem.split("-")[-3:])) + datetime.timedelta(
        days=1
    )
    today = datetime.datetime.now(tz=ZoneInfo("UTC")).date()
    while date < today:
        download_historical_funding_rates(date)
        date += datetime.timedelta(days=1)


def download_okx_swaprate():
    download_all_historical_funding_rates(True, 10)


# 运行主函数
if __name__ == "__main__":
    # main()
    download_okx_swaprate()
    # update_swaprates()
