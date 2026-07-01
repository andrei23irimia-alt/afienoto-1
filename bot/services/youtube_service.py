from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

import shutil

import yt_dlp

from bot.config import settings

YOUTUBE_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([\w-]+)"
)


def _ffmpeg_location() -> str | None:
    if shutil.which("ffmpeg"):
        return None  # let yt-dlp find it on PATH
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


@dataclass
class YoutubeTrack:
    file_path: Path
    title: str
    artist: str
    duration: int
    thumbnail_url: str | None


def is_youtube_url(text: str) -> bool:
    return bool(YOUTUBE_URL_RE.search(text))


def _ydl_opts(out_template: str) -> dict:
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
                "preferredquality": "192",
            }
        ],
    }
    ffmpeg_location = _ffmpeg_location()
    if ffmpeg_location:
        opts["ffmpeg_location"] = ffmpeg_location
    return opts


def _extract(query_or_url: str) -> dict:
    out_template = str(Path(settings.download_dir) / f"{uuid.uuid4().hex}.%(ext)s")
    opts = _ydl_opts(out_template)
    with yt_dlp.YoutubeDL(opts) as ydl:
        search = query_or_url if is_youtube_url(query_or_url) else f"ytsearch1:{query_or_url}"
        info = ydl.extract_info(search, download=True)
        if "entries" in info:
            info = info["entries"][0]
        final_path = Path(ydl.prepare_filename(info)).with_suffix(".mp3")
        return {"info": info, "path": final_path}


async def download(query_or_url: str) -> YoutubeTrack:
    result = await asyncio.to_thread(_extract, query_or_url)
    info = result["info"]
    return YoutubeTrack(
        file_path=result["path"],
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


async def download_video_id(video_id: str) -> YoutubeTrack:
    return await download(f"https://www.youtube.com/watch?v={video_id}")
