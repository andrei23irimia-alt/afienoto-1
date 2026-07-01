from __future__ import annotations

import logging
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, FSInputFile

from bot.config import settings
from bot.services import tagging, youtube_service

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text)
async def handle_youtube_or_search(message: Message) -> None:
    text = message.text.strip()

    status = await message.answer("Se descarcă...")
    try:
        track = await youtube_service.download(text)
    except Exception:
        logger.exception("YouTube download failed for query: %s", text)
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
        await message.answer_audio(
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
