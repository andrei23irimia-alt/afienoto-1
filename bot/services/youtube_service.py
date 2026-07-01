from __future__ import annotations

import asyncio
import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

import yt_dlp

from bot.config import settings

YOUTUBE_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([\w-]+)"
)
PLAYLIST_URL_RE = re.compile(r"youtube\.com/playlist\?[^ ]*\blist=")

ProgressCallback = Callable[[int], Awaitable[None]]


def _ffmpeg_location() -> str | None:
    if shutil.which("ffmpeg"):
        return None  # let yt-dlp find it on PATH
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def ffmpeg_path() -> str:
    return _ffmpeg_location() or "ffmpeg"


@dataclass
class YoutubeTrack:
    file_path: Path
    video_id: str
    title: str
    artist: str
    duration: int
    thumbnail_url: str | None


def is_youtube_url(text: str) -> bool:
    return bool(YOUTUBE_URL_RE.search(text))


def is_youtube_playlist_url(text: str) -> bool:
    return bool(PLAYLIST_URL_RE.search(text))


def extract_video_id(url: str) -> str | None:
    match = YOUTUBE_URL_RE.search(url)
    return match.group(1) if match else None


def _make_progress_hook(loop: asyncio.AbstractEventLoop, on_progress: ProgressCallback | None):
    last_bucket = {"value": -1}

    def hook(d: dict) -> None:
        if on_progress is None:
            return
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes")
            if not total or not downloaded:
                return
            pct = int(downloaded / total * 100)
            bucket = (pct // 20) * 20
            if bucket > last_bucket["value"]:
                last_bucket["value"] = bucket
                asyncio.run_coroutine_threadsafe(on_progress(bucket), loop)
        elif status == "finished" and last_bucket["value"] < 100:
            last_bucket["value"] = 100
            asyncio.run_coroutine_threadsafe(on_progress(100), loop)

    return hook


def _ydl_opts(
    out_template: str,
    quality: str = "192",
    loop: asyncio.AbstractEventLoop | None = None,
    on_progress: ProgressCallback | None = None,
) -> dict:
    opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 3,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality,
            }
        ],
    }
    ffmpeg_location = _ffmpeg_location()
    if ffmpeg_location:
        opts["ffmpeg_location"] = ffmpeg_location
    if loop is not None:
        opts["progress_hooks"] = [_make_progress_hook(loop, on_progress)]
    return opts


def _extract(
    query_or_url: str,
    quality: str,
    loop: asyncio.AbstractEventLoop | None,
    on_progress: ProgressCallback | None,
) -> dict:
    out_template = str(Path(settings.download_dir) / f"{uuid.uuid4().hex}.%(ext)s")
    opts = _ydl_opts(out_template, quality, loop, on_progress)
    with yt_dlp.YoutubeDL(opts) as ydl:
        search = query_or_url if is_youtube_url(query_or_url) else f"ytsearch1:{query_or_url}"
        info = ydl.extract_info(search, download=True)
        if "entries" in info:
            info = info["entries"][0]
        final_path = Path(ydl.prepare_filename(info)).with_suffix(".mp3")
        return {"info": info, "path": final_path}


async def download(
    query_or_url: str, quality: str = "192", on_progress: ProgressCallback | None = None
) -> YoutubeTrack:
    loop = asyncio.get_running_loop() if on_progress else None
    result = await asyncio.to_thread(_extract, query_or_url, quality, loop, on_progress)
    info = result["info"]
    return YoutubeTrack(
        file_path=result["path"],
        video_id=info.get("id") or "",
        title=info.get("title") or "Unknown title",
        artist=info.get("uploader") or info.get("channel") or "Unknown artist",
        duration=int(info.get("duration") or 0),
        thumbnail_url=info.get("thumbnail"),
    )


def _search(query: str, limit: int) -> list[dict]:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
        return info.get("entries") or []


async def search_candidates(query: str, limit: int = 5) -> list[dict]:
    return await asyncio.to_thread(_search, query, limit)


async def download_video_id(
    video_id: str, quality: str = "192", on_progress: ProgressCallback | None = None
) -> YoutubeTrack:
    return await download(f"https://www.youtube.com/watch?v={video_id}", quality, on_progress)


def _list_playlist(url: str, limit: int) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
        "playlistend": limit,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        entries = [e for e in (info.get("entries") or []) if e and e.get("id")]
        return {"title": info.get("title") or "Playlist", "entries": entries[:limit]}


async def list_playlist(url: str, limit: int) -> dict:
    return await asyncio.to_thread(_list_playlist, url, limit)
