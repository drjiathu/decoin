import asyncio
from collections import Counter
from enum import Enum
from http import HTTPStatus
from pathlib import Path
import tqdm
from typing import AsyncIterator
from urllib.parse import unquote

import aiofiles
import httpx


DownloadStatus = Enum("DownloadStatus", "OK NOT_FOUND ERROR")


async def download_file(
    client: httpx.AsyncClient,
    url: str,
    filepath: Path,
    semaphore: asyncio.Semaphore,
    verbose: bool,
) -> int:
    total_size: int = 0
    try:
        async with semaphore:
            async with client.stream("GET", url=url) as resp:
                resp.raise_for_status()
                # 打开本地文件进行写入
                async with aiofiles.open(filepath, "wb") as f:
                    # 逐块读取并写入文件
                    async for chunk in resp.aiter_bytes(chunk_size=8192):
                        if chunk:  # 过滤保持连接的空白块
                            await f.write(chunk)
                            total_size += len(chunk)
    except httpx.HTTPStatusError as exc:
        res = exc.response
        if res.status_code == HTTPStatus.NOT_FOUND:
            status = DownloadStatus.NOT_FOUND
            msg = f"not found: {res.url}"
        else:
            status = DownloadStatus.ERROR
            raise
    except Exception as exc:
        status = DownloadStatus.ERROR
        msg = f"[{type(exc).__name__}]: {exc.args[0]}"
    else:
        status = DownloadStatus.OK
        msg = f"DOWNLOADED {total_size}"
    if verbose and msg:
        print(filepath, msg)
    return status


async def fetch_file(client: httpx.AsyncClient, url: str) -> AsyncIterator:
    async with client.stream("GET", url=url) as resp:
        resp.raise_for_status()
        async for chunk in resp.aiter_bytes(8192):
            yield chunk


async def write_file(file_path: Path, chunk_generator: AsyncIterator) -> int:
    file_size = 0
    async with aiofiles.open(file_path, "wb") as f:
        async for chunk in chunk_generator:
            if chunk:
                await f.write(chunk)
                file_size += len(chunk)
    return file_size


async def download_one(
    client: httpx.AsyncClient,
    url: str,
    file_path: Path,
    semaphore: asyncio.Semaphore,
) -> DownloadStatus:
    try:
        async with semaphore:
            chunk_gen = fetch_file(client, url)
    except httpx.HTTPStatusError as exc:
        res = exc.response
        if res.status_code == HTTPStatus.NOT_FOUND:
            status = DownloadStatus.NOT_FOUND
            msg = f"not found: {res.url}"
        else:
            status = DownloadStatus.ERROR
            msg = exc.args[0]
            raise
    else:
        # await asyncio.to_thread(write_file, file_path, chunk_gen)
        await write_file(file_path, chunk_gen)
        status = DownloadStatus.OK
        msg = "DOWNLOADED"
    # if verbose and msg:
    #     print(file_path, msg)
    return file_path, status, msg


async def supervisor(
    urls: list[str],
    save_path: Path,
    verbose: bool,
    concur_req: int,
) -> Counter[DownloadStatus]:
    counter: Counter[DownloadStatus] = Counter()
    semaphore = asyncio.Semaphore(concur_req)
    async with httpx.AsyncClient() as client:
        to_do = []
        for url in sorted(urls):
            filename = unquote(url).split("/")[-1]
            file_path: Path = save_path / filename
            to_do.append(download_file(client, url, file_path, semaphore))
        to_do_iter = asyncio.as_completed(to_do)
        if not verbose:
            to_do_iter = tqdm.tqdm(to_do_iter, total=len(urls))
        error: httpx.HTTPError | None = None
        for coro in to_do_iter:
            try:
                file_path, status, msg = await coro
                if verbose and msg:
                    print(f"{file_path} {status}: {msg}")
            except httpx.HTTPStatusError as exc:
                error_msg = "HTTP error {resp.status_code} - {resp.reason_phrase}"
                error_msg = error_msg.format(resp=exc.response)
                error = exc
            except httpx.RequestError as exc:
                error_msg = f"{exc} {type(exc)}".strip()
                error = exc
            except KeyboardInterrupt:
                break

            if error:
                status = DownloadStatus.ERROR
                if verbose:
                    url = str(error.request.url)
                    cc = Path(url).stem
                    print(f"{cc} error: {error_msg}")
            counter[status] += 1

    return counter
