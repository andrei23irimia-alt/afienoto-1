from __future__ import annotations

import logging
from pathlib import Path
from typing import Awaitable

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.config import settings
from bot.services import tagging, youtube_service
from bot.services.youtube_service import YoutubeTrack

router = Router()
logger = logging.getLogger(__name__)


def _format_duration(seconds: int | None) -> str:
    if not seconds:
        return "?:??"
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}:{secs:02d}"


@router.message(F.text.func(youtube_service.is_youtube_url))
async def handle_youtube_link(message: Message) -> None:
    status = await message.answer("Se descarcă...")
    await _download_and_deliver(message, status, youtube_service.download(message.text.strip()))


@router.message(F.text & ~F.text.startswith("/"))
async def handle_search(message: Message) -> None:
    text = message.text.strip()
    if not text:
        return

    status = await message.answer("Caut...")
    try:
        candidates = await youtube_service.search_candidates(text, limit=5)
    except Exception:
        logger.exception("YouTube search failed for query: %s", text)
        await status.edit_text("Căutarea a eșuat. Încearcă din nou.")
        return

    candidates = [c for c in candidates if c.get("id")]
    if not candidates:
        await status.edit_text("Nu am găsit nimic pentru căutarea asta.")
        return

    buttons = [
        [
            InlineKeyboardButton(
                text=f"{(c.get('title') or 'Fără titlu')[:50]} ({_format_duration(c.get('duration'))})",
                callback_data=f"yt_dl:{c['id']}",
            )
        ]
        for c in candidates
    ]
    await status.edit_text(
        "Alege piesa:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data.startswith("yt_dl:"))
async def handle_selection(callback: CallbackQuery) -> None:
    await callback.answer()
    video_id = callback.data.split(":", 1)[1]
    status = callback.message
    await status.edit_text("Se descarcă...", reply_markup=None)
    await _download_and_deliver(status, status, youtube_service.download_video_id(video_id))


async def _download_and_deliver(
    reply_target: Message, status: Message, fetch: Awaitable[YoutubeTrack]
) -> None:
    try:
        track = await fetch
    except Exception:
        logger.exception("YouTube download failed")
        await status.edit_text("Nu am putut descărca piesa. Încearcă alt link sau altă căutare.")
        return

    if track.duration and track.duration > settings.max_duration_seconds:
        await status.edit_text(
            f"Piesa este prea lungă ({track.duration // 60} min). "
            f"Limita este {settings.max_duration_seconds // 60} min."
        )
        _cleanup(track.file_path)
        return

    tagging.apply_tags(track.file_path, title=track.title, artist=track.artist, cover_url=track.thumbnail_url)

    try:
        await reply_target.answer_audio(
            FSInputFile(track.file_path),
            title=track.title,
            performer=track.artist,
        )
    finally:
        await status.delete()
        _cleanup(track.file_path)


def _cleanup(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception:
        logger.warning("Could not remove temp file %s", path)
