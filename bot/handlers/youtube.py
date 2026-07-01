from __future__ import annotations

import html
import logging
from pathlib import Path
from typing import Awaitable

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.config import settings
from bot.services import preferences, tagging, youtube_service
from bot.services.youtube_service import YoutubeTrack

router = Router()
logger = logging.getLogger(__name__)


def _format_duration(seconds: int | None) -> str:
    if not seconds:
        return "?:??"
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}:{secs:02d}"


@router.message(Command("calitate"))
async def cmd_quality(message: Message) -> None:
    current = preferences.quality_for(message.chat.id)
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{'✅ ' if key == current else ''}{label}",
                callback_data=f"yt_quality:{key}",
            )
        ]
        for key, label in preferences.QUALITY_LABELS.items()
    ]
    await message.answer(
        "🎚️ Alege calitatea audio pentru descărcări:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("yt_quality:"))
async def handle_quality_choice(callback: CallbackQuery) -> None:
    quality = callback.data.split(":", 1)[1]
    preferences.set_quality(callback.message.chat.id, quality)
    label = preferences.QUALITY_LABELS.get(quality, quality)
    await callback.answer(f"Calitate setată: {label}")
    await callback.message.edit_text(f"✅ Calitate setată: {label}")


@router.message(F.text.func(youtube_service.is_youtube_playlist_url))
async def handle_youtube_playlist(message: Message) -> None:
    url = message.text.strip()
    status = await message.answer("📃 Citesc playlist-ul...")

    try:
        playlist = await youtube_service.list_playlist(url, settings.max_playlist_items)
    except Exception:
        logger.exception("Playlist listing failed for: %s", url)
        await status.edit_text("Nu am putut citi playlist-ul. Verifică link-ul.")
        return

    entries = playlist["entries"]
    if not entries:
        await status.edit_text("Playlist-ul e gol sau nu am putut citi piesele din el.")
        return

    quality = preferences.quality_for(message.chat.id)
    total = len(entries)
    playlist_title = html.escape(playlist["title"])
    await status.edit_text(f"📃 <b>{playlist_title}</b>\nDescarc {total} piese...")

    sent = 0
    for index, entry in enumerate(entries, start=1):
        entry_title = html.escape((entry.get("title") or "")[:60])
        await status.edit_text(f"📃 <b>{playlist_title}</b>\n⬇️ {index}/{total}: {entry_title}")
        try:
            track = await youtube_service.download_video_id(entry["id"], quality=quality)
        except Exception:
            logger.exception("Playlist track download failed: %s", entry.get("id"))
            continue

        if track.duration and track.duration > settings.max_duration_seconds:
            _cleanup(track.file_path)
            continue

        tagging.apply_tags(track.file_path, title=track.title, artist=track.artist, cover_url=track.thumbnail_url)
        try:
            await message.answer_audio(FSInputFile(track.file_path), title=track.title, performer=track.artist)
            sent += 1
        finally:
            _cleanup(track.file_path)

    await status.edit_text(f"✅ Gata! Trimise {sent}/{total} piese din playlist.")


@router.message(F.text.func(youtube_service.is_youtube_url))
async def handle_youtube_link(message: Message) -> None:
    status = await message.answer("⬇️ Se descarcă...")
    quality = preferences.quality_for(message.chat.id)

    async def on_progress(pct: int) -> None:
        await _safe_edit(status, f"⬇️ Se descarcă... {pct}%")

    await _download_and_deliver(
        message, status, youtube_service.download(message.text.strip(), quality, on_progress)
    )


@router.message(F.text & ~F.text.startswith("/"))
async def handle_search(message: Message) -> None:
    text = message.text.strip()
    if not text:
        return

    status = await message.answer("🔎 Caut...")
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
                text=f"🎵 {(c.get('title') or 'Fără titlu')[:50]} ({_format_duration(c.get('duration'))})",
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
    quality = preferences.quality_for(status.chat.id)
    await status.edit_text("⬇️ Se descarcă... 0%", reply_markup=None)

    async def on_progress(pct: int) -> None:
        await _safe_edit(status, f"⬇️ Se descarcă... {pct}%")

    await _download_and_deliver(
        status, status, youtube_service.download_video_id(video_id, quality, on_progress)
    )


async def _download_and_deliver(
    reply_target: Message, status: Message, fetch: Awaitable[YoutubeTrack]
) -> None:
    try:
        track = await fetch
    except Exception:
        logger.exception("YouTube download failed")
        await status.edit_text("❌ Nu am putut descărca piesa. Încearcă alt link sau altă căutare.")
        return

    if track.duration and track.duration > settings.max_duration_seconds:
        await status.edit_text(
            f"⏱️ Piesa este prea lungă ({track.duration // 60} min). "
            f"Limita este {settings.max_duration_seconds // 60} min."
        )
        _cleanup(track.file_path)
        return

    await _safe_edit(status, "🏷️ Adaug tag-uri și copertă...")
    tagging.apply_tags(track.file_path, title=track.title, artist=track.artist, cover_url=track.thumbnail_url)

    try:
        await _safe_edit(status, "📤 Trimit fișierul...")
        await reply_target.answer_audio(
            FSInputFile(track.file_path),
            title=track.title,
            performer=track.artist,
        )
    finally:
        await status.delete()
        _cleanup(track.file_path)


async def _safe_edit(message: Message, text: str) -> None:
    try:
        await message.edit_text(text)
    except Exception:
        pass


def _cleanup(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception:
        logger.warning("Could not remove temp file %s", path)
