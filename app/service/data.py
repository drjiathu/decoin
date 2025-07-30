import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from tqdm import tqdm

from app.api.okx import (
    download_historical_funding_rates,
    get_all_markets,
    fetch_historical_candles,
    fetch_historical_funding_rate,
)
from config import OKX_DATAPATH


DATAPATH = Path("./data")


def get_okx_historical_candles(bar="1m"):
    markets = get_all_markets()
    for _, row in markets.iterrows():
        if row["instType"] == "SWAP":
            inst_id = row["instId"]
            df = fetch_historical_candles(inst_id, bar=bar)
            filepath = f"./data/{inst_id}.parquet"
            df.to_parquet(filepath)
            print(f"get 1s candle of {inst_id}, store to {filepath}")


def get_okx_historical_funding_rate():
    datapath = DATAPATH.joinpath("funding_rate")
    datapath.mkdir(parents=True, exist_ok=True)
    swaps = get_all_markets(inst_type="SWAP")
    pbar = tqdm(swaps["instId"])
    for inst_id in pbar:
        fr_df = fetch_historical_funding_rate(inst_id)
        fr_df.to_parquet(datapath.joinpath(inst_id + ".parquet"))
