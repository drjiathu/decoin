import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.async_utils import download_many


def main():
    # API 基础 URL
    start = datetime.date(2021, 10, 1)
    end = datetime.datetime.now(tz=ZoneInfo("UTC")).date()
    dates = [start + datetime.timedelta(days=i) for i in range((end - start).days)]
    base_url = "https://www.okx.com/cdn/okex/traderecords/swaprate/monthly/"
    urls = [
        base_url + f"{d.strftime('%Y%m')}/allswaprate-swaprate-{d.isoformat()}.zip"
        for d in dates
    ]
    save_path = Path("./data/test")
    counts = download_many(urls, save_path, True, 10)
    print(counts)


# 运行主函数
if __name__ == "__main__":
    main()
