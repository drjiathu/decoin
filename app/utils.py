from datetime import datetime
from functools import wraps
import hashlib
from pathlib import Path
import random
import time

import pytz
import requests
from tqdm import tqdm


def retry(max_retries=3, delay=1, backoff=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"重试 {retries + 1}/{max_retries}: {e}")
                    time.sleep(current_delay + random.uniform(0, 0.1))
                    current_delay *= backoff
                    retries += 1
            return None

        return wrapper

    return decorator


def wait_then_exec(wait=0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            time.sleep(wait)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def unix_timestamp_to_datetime(timestamp: int, unit: str = "ms", tz=None) -> datetime:

    if tz is None:
        tz = pytz.timezone("UTC")
    elif isinstance(tz, str):
        tz = pytz.timezone(tz)
    else:
        raise ValueError("Invalid timezone")

    if unit == "ms":
        divider = 1_000
    elif unit == "us":
        divider = 1_000_000
    else:
        raise ValueError("Invalid unit")

    return datetime.fromtimestamp(timestamp / divider, tz=tz)


def stream_download(url: str, filepath: Path | str) -> Path:
    filepath = Path(filepath)
    # 流式下载大文件
    with requests.get(url, stream=True, timeout=10) as r:
        r.raise_for_status()
        if filepath.exists():
            print(f"文件已存在: {filepath}")
            return filepath
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:  # 过滤保持连接的空白块
                    f.write(chunk)
    return filepath


def file_checksum(
    filepath: str | Path, checksum_url: str, hash_algorithm: str = "sha256"
) -> tuple[bool, str]:
    try:
        response = requests.get(checksum_url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to get checksum {checksum_url}: {e}")
        raise e

    expected_checksum = response.text.split()[0]
    hash_obj = hashlib.new(hash_algorithm)
    with open(filepath, "rb") as f:
        # 分块读取以处理大文件
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    actual_checksum = hash_obj.hexdigest()

    # 比较哈希值
    if actual_checksum == expected_checksum:
        return True, f"checksum successful: {filepath}"
    else:
        return (
            False,
            f"checksum failed: {filepath}\n"
            f"expected: {expected_checksum}\n"
            f"actual: {actual_checksum}",
        )


def download_file_with_progress(url, save_path):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # 获取文件总大小（字节）
        total_size = int(response.headers.get("content-length", 0))

        with open(save_path, "wb") as f, tqdm(
            desc=save_path,
            total=total_size,
            unit="iB",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                size = f.write(chunk)
                bar.update(size)
        print(f"\n文件已下载到: {save_path}")
    except requests.exceptions.RequestException as e:
        print(f"下载失败: {e}")
