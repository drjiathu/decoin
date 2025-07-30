import asyncio
from collections import Counter
from enum import Enum
from http import HTTPStatus
from pathlib import Path
from typing import AsyncIterator
from urllib.parse import unquote

import aiofiles
import httpx
import tqdm

from .utils import retry


DownloadStatus = Enum("DownloadStatus", "OK NOT_FOUND ERROR")


@retry(3)
async def fetch_file(client: httpx.AsyncClient, url: str) -> AsyncIterator:
    async with client.stream("GET", url=url) as resp:
        resp.raise_for_status()
        async for chunk in resp.aiter_bytes(8192):
            yield chunk


async def write_file(file_path: Path, generator: AsyncIterator) -> int:
    file_size = 0
    async with aiofiles.open(file_path, "wb") as f:
        async for chunk in generator:
            if chunk:
                await f.write(chunk)
                file_size += len(chunk)
    return file_size


async def download_one(
    client: httpx.AsyncClient,
    url: str,
    file_path: Path,
    semaphore: asyncio.Semaphore,
) -> Path | None:
    try:
        async with semaphore:
            chunk_gen = fetch_file(client, url)
            await write_file(file_path, chunk_gen)
            return file_path
    except Exception:
        if file_path.exists():
            file_path.unlink()
        raise


async def supervisor(
    urls: list[str],
    save_path: Path,
    verbose: bool,
    concur_req: int,
) -> Counter[DownloadStatus]:
    counter: Counter[DownloadStatus] = Counter()
    semaphore = asyncio.Semaphore(concur_req)
    async with httpx.AsyncClient() as client:
        to_do = {}
        for url in sorted(urls):
            filename = unquote(url).split("/")[-1]
            file_path: Path = save_path / filename
            to_do[download_one(client, url, file_path, semaphore)] = url
        to_do_iter = asyncio.as_completed(to_do)
        if not verbose:
            to_do_iter = tqdm.tqdm(to_do_iter, total=len(urls))
        # error: httpx.HTTPError | None = None
        error: Exception | None = None
        error_msg: str | None = None
        for coro in to_do_iter:
            try:
                file_path = await coro
                status, msg = DownloadStatus.OK, "DOWNLOADED"
                if verbose:
                    print(f"{file_path} {status}: {msg}")
            except httpx.HTTPStatusError as exc:
                resp = exc.response
                if resp.status_code == HTTPStatus.NOT_FOUND:
                    status = DownloadStatus.NOT_FOUND
                    msg = f"{resp.url} NOT FOUND"
                else:
                    status = DownloadStatus.ERROR
                    error_msg = f"HTTP error {resp.status_code} - {resp.reason_phrase}"
                error = exc
            except httpx.RequestError as exc:
                status = DownloadStatus.ERROR
                error_msg = f"{exc} {type(exc)}".strip()
                error = exc
            except KeyboardInterrupt:
                break
            except Exception as exc:
                status = DownloadStatus.ERROR
                error_msg = f"Unexpected error - {exc}"
                error = exc

            if error and verbose:
                url = to_do[coro]
                print(f"{url} error: {error_msg}")
            counter[status] += 1

    return counter


def download_many(
    urls: list[str],
    save_path: Path,
    verbose: bool,
    concur_req: int,
) -> Counter[DownloadStatus]:
    coro = supervisor(urls, save_path, verbose, concur_req)
    counts = asyncio.run(coro)

    return counts
