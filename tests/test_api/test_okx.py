import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from app.api.okx import fetch_historical_candles, get_okx_option_underlyings


class TestOKXApi:
    # @staticmethod
    def test_get_okx_option_underlyings(self):
        expected = ["BTC-USD", "ETH-USD"]
        result = get_okx_option_underlyings()
        assert result == expected

    @pytest.mark.parametrize(
        "inst_id",
        "bar",
        "start_ts",
        "end_ts",
        [
            (
                "BTC-USDT-SWAP",
                "1H",
                pd.Timestamp(year=2025, month=1, day=1),
                pd.Timestamp(year=2025, month=2, day=8),
            )
        ],
    )
    def test_fetch_historical_candles(inst_id, bar, start_ts, end_ts):
        if start_ts:
            start_ms = start_ts.value / 1_000_000
        if end_ts:
            end_ms = end_ts.value / 1_000_000
        df = fetch_historical_candles(inst_id, bar, start_ms - 1, end_ms + 1)
        assert (df["ts"].iat[0] == start_ms) & (df["ts"].iat[-1] == end_ms)
