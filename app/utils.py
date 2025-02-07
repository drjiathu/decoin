from datetime import datetime


def unix_timestamp_ms_to_datetime(timestamp_ms: int) -> datetime:
    return datetime.fromtimestamp(timestamp_ms / 1_000)
