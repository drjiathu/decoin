import datetime
from pathlib import Path
# from zoneinfo import ZoneInfo

# from requests.exceptions import HTTPError

from app.constants import BINANCE_DATA_BASE_URL, OKX_DATA_BASE_URL
from app.utils import stream_download, file_checksum
from config import RAWDATAPATH


def dowload_historical_file(url: str, target_path: Path, checksum=False) -> int:
    target_path.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    target_file = target_path / f"{filename}"
    stream_download(url, target_file)
    if checksum:
        checksum_url = url + ".CHECKSUM"
        check_res, msg = file_checksum(target_file, checksum_url)
        if not check_res:
            raise ValueError(msg)
        
    return target_file.stat().st_size

def download_binance_historical_daily_trades(symbol: str, kind: str, date: datetime.date, checksum=True) -> int:
    filename = f"{symbol}-trades-{date.isoformat()}.zip"
    url = f"{BINANCE_DATA_BASE_URL}/{kind}/daily/trades/{symbol}/{filename}"
    target_path = RAWDATAPATH / "binance" / f"{kind}" / "trades"

    return dowload_historical_file(url, target_path, checksum)


def download_binance_historical_daily_klines(symbol: str, kind: str, freq: str, date: datetime.date, checksum=True) -> int:
    filename = f"{symbol}-{freq}-{date.isoformat()}.zip"
    url = f"{BINANCE_DATA_BASE_URL}/{kind}/daily/klines/{symbol}/{freq}/{filename}"
    target_path = RAWDATAPATH / "binance" / f"{kind}" / "klines"
    
    return dowload_historical_file(url, target_path, checksum)


def download_okx_historical_daily_trades(symbol: str, date: datetime.date) -> int:
    filename = f"{symbol}-trades-{date.isoformat()}.zip"
    url = f"{OKX_DATA_BASE_URL}/traderecords/trades/daily/{date.strftime('%Y%m%d')}/{filename}"
    target_path = RAWDATAPATH / "okx" / "trades"

    # No checksum for OKX
    return dowload_historical_file(url, target_path)


def download_okx_historical_klines(bar="1m"):
    pass
#     markets = get_all_markets()
#     for _, row in markets.iterrows():
#         if row["instType"] == "SWAP":
#             inst_id = row["instId"]
#             df = fetch_historical_candles(inst_id, bar=bar)
#             filepath = f"./data/{inst_id}.parquet"
#             df.to_parquet(filepath)
#             print(f"get 1s candle of {inst_id}, store to {filepath}")


# def get_okx_historical_funding_rate():
#     datapath = DATAPATH.joinpath("funding_rate")
#     datapath.mkdir(parents=True, exist_ok=True)
#     swaps = get_all_markets(inst_type="SWAP")
#     pbar = tqdm(swaps["instId"])
#     for inst_id in pbar:
#         fr_df = fetch_historical_funding_rate(inst_id)
#         fr_df.to_parquet(datapath.joinpath(inst_id + ".parquet"))
