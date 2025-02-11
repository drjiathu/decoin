from datetime import datetime
from functools import wraps
import random
import time

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


def unix_timestamp_ms_to_datetime(timestamp_ms: int) -> datetime:
    return datetime.fromtimestamp(timestamp_ms / 1_000)


def stream_download(url, filepath):
    # 流式下载大文件
    with requests.get(url, stream=True, timeout=10) as r:
        r.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:  # 过滤保持连接的空白块
                    f.write(chunk)
    return filepath


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
