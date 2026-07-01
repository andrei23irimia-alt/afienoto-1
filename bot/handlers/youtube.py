from __future__ import annotations

import asyncio
import html
import logging
import uuid
from pathlib import Path

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
from bot.services import db, preferences, tagging, youtube_service
from bot.services.keyboards import actions_keyboard

router = Router()
logger = logging.getLogger(__name__)


def _format_duration(seconds: int | None) -> str:
    if not seconds:
        return "?:??"
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}:{secs:02d}"


# ---------------------------------------------------------------------------
# Quality settings
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Istoric / favorite / statistici
# ---------------------------------------------------------------------------


def _history_keyboard(rows) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"🎵 {row['title'][:45]} — {row['artist'][:20]}",
                callback_data=f"yt_resend:{row['video_id']}",
            )
        ]
        for row in rows
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _favorites_keyboard(rows) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text=f"🎵 {row['title'][:38]}", callback_data=f"yt_resend:{row['video_id']}"),
            InlineKeyboardButton(text="🗑️", callback_data=f"yt_unfav:{row['video_id']}"),
        ]
        for row in rows
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("istoric"))
async def cmd_history(message: Message) -> None:
    rows = db.get_history(message.chat.id, limit=10)
    if not rows:
        await message.answer("📜 Nu ai descărcat nimic încă. Trimite-mi un link sau o căutare!")
        return
    await message.answer("📜 <b>Ultimele tale descărcări</b> (apasă ca să retrimit instant):", reply_markup=_history_keyboard(rows))


@router.message(Command("favorite"))
async def cmd_favorites(message: Message) -> None:
    rows = db.get_favorites(message.chat.id)
    if not rows:
        await message.answer("❤️ Nu ai piese favorite încă. Apasă ❤️ sub orice piesă trimisă ca s-o salvezi.")
        return
    await message.answer("❤️ <b>Piesele tale favorite:</b>", reply_markup=_favorites_keyboard(rows))


@router.message(Command("statistici"))
async def cmd_stats(message: Message) -> None:
    s = db.stats_for(message.chat.id)
    text = f"📊 <b>Statisticile tale</b>\n\n🎵 Piese descărcate: {s['total']}\n❤️ Favorite: {s['favorites']}"
    if s["top_artist"]:
        text += f"\n🏆 Cel mai ascultat artist: <b>{html.escape(s['top_artist'])}</b> ({s['top_artist_count']}x)"
    await message.answer(text)


@router.callback_query(F.data.startswith("yt_resend:"))
async def handle_resend(callback: CallbackQuery) -> None:
    video_id = callback.data.split(":", 1)[1]
    await callback.answer("Trimit...")
    cached = db.find_cached(video_id)
    if not cached:
        await callback.message.answer("Nu mai am fișierul salvat pentru asta — trimite-l din nou ca link.")
        return
    chat_id = callback.message.chat.id
    await callback.message.answer_audio(
        cached["file_id"],
        title=cached["title"],
        performer=cached["artist"],
        reply_markup=actions_keyboard(video_id, db.is_favorite(chat_id, video_id)),
    )


@router.callback_query(F.data.startswith("yt_fav:"))
async def handle_favorite_toggle(callback: CallbackQuery) -> None:
    video_id = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id
    if db.is_favorite(chat_id, video_id):
        db.remove_favorite(chat_id, video_id)
        await callback.answer("Șters din favorite")
    else:
        cached = db.find_cached(video_id)
        if cached:
            db.add_favorite(chat_id, video_id, cached["title"], cached["artist"], cached["file_id"])
        await callback.answer("Adăugat la favorite ❤️")
    try:
        await callback.message.edit_reply_markup(
            reply_markup=actions_keyboard(video_id, db.is_favorite(chat_id, video_id))
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("yt_unfav:"))
async def handle_unfavorite(callback: CallbackQuery) -> None:
    video_id = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id
    db.remove_favorite(chat_id, video_id)
    await callback.answer("Șters din favorite")
    rows = db.get_favorites(chat_id)
    if not rows:
        await callback.message.edit_text("❤️ Nu mai ai piese favorite.")
        return
    await callback.message.edit_reply_markup(reply_markup=_favorites_keyboard(rows))


@router.callback_query(F.data.startswith("yt_ring:"))
async def handle_ringtone(callback: CallbackQuery) -> None:
    video_id = callback.data.split(":", 1)[1]
    await callback.answer("Fac ringtone-ul...")
    cached = db.find_cached(video_id)
    if not cached:
        await callback.message.answer("Nu (mai) am fișierul original pentru asta.")
        return

    status = await callback.message.answer("✂️ Tai un fragment de 30s...")
    src = Path(settings.download_dir) / f"{uuid.uuid4().hex}_src.mp3"
    dst = Path(settings.download_dir) / f"{uuid.uuid4().hex}_ring.mp3"
    try:
        file = await callback.bot.get_file(cached["file_id"])
        await callback.bot.download_file(file.file_path, destination=src)

        duration = cached["duration"] or 60
        start = min(30, max(0, duration - 30))
        proc = await asyncio.create_subprocess_exec(
            youtube_service.ffmpeg_path(),
            "-y", "-ss", str(start), "-t", "30", "-i", str(src), str(dst),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        if proc.returncode != 0 or not dst.exists():
            raise RuntimeError("ffmpeg trim failed")

        await status.edit_text("📤 Trimit ringtone-ul...")
        await callback.message.answer_audio(
            FSInputFile(dst),
            title=f"{cached['title']} (ringtone)",
            performer=cached["artist"],
        )
        await status.delete()
    except Exception:
        logger.exception("Ringtone creation failed for %s", video_id)
        await status.edit_text("❌ Nu am putut crea ringtone-ul.")
    finally:
        src.unlink(missing_ok=True)
        dst.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Playlist
# ---------------------------------------------------------------------------


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
        video_id = entry["id"]

        cached = db.cache_get(video_id, quality)
        if cached:
            sent_msg = await message.answer_audio(
                cached["file_id"], title=cached["title"], performer=cached["artist"],
                reply_markup=actions_keyboard(video_id, db.is_favorite(message.chat.id, video_id)),
            )
            db.record_download(message.chat.id, video_id, cached["title"], cached["artist"], cached["file_id"])
            sent += 1
            continue

        try:
            track = await youtube_service.download_video_id(video_id, quality=quality)
        except Exception:
            logger.exception("Playlist track download failed: %s", video_id)
            continue

        if track.duration and track.duration > settings.max_duration_seconds:
            _cleanup(track.file_path)
            continue

        tagging.apply_tags(track.file_path, title=track.title, artist=track.artist, cover_url=track.thumbnail_url)
        try:
            sent_msg = await message.answer_audio(
                FSInputFile(track.file_path), title=track.title, performer=track.artist,
                reply_markup=actions_keyboard(video_id, False),
            )
            file_id = sent_msg.audio.file_id
            db.cache_set(video_id, quality, file_id, track.title, track.artist, track.duration)
            db.record_download(message.chat.id, video_id, track.title, track.artist, file_id)
            sent += 1
        finally:
            _cleanup(track.file_path)

    await status.edit_text(f"✅ Gata! Trimise {sent}/{total} piese din playlist.")


# ---------------------------------------------------------------------------
# Link direct / căutare
# ---------------------------------------------------------------------------


@router.message(F.text.func(youtube_service.is_youtube_url))
async def handle_youtube_link(message: Message) -> None:
    video_id = youtube_service.extract_video_id(message.text.strip())
    quality = preferences.quality_for(message.chat.id)
    status = await message.answer("⬇️ Se descarcă...")

    if video_id:
        cached = db.cache_get(video_id, quality)
        if cached:
            await _send_cached(message, status, video_id, quality, cached)
            return

    async def on_progress(pct: int) -> None:
        await _safe_edit(status, f"⬇️ Se descarcă... {pct}%")

    await _download_and_deliver(
        message, status, youtube_service.download(message.text.strip(), quality, on_progress), quality
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

    cached = db.cache_get(video_id, quality)
    if cached:
        await status.edit_text("⚡ Găsit deja, trimit instant...", reply_markup=None)
        await _send_cached(status, status, video_id, quality, cached)
        return

    await status.edit_text("⬇️ Se descarcă... 0%", reply_markup=None)

    async def on_progress(pct: int) -> None:
        await _safe_edit(status, f"⬇️ Se descarcă... {pct}%")

    await _download_and_deliver(
        status, status, youtube_service.download_video_id(video_id, quality, on_progress), quality
    )


async def _send_cached(reply_target: Message, status: Message, video_id: str, quality: str, cached) -> None:
    chat_id = reply_target.chat.id
    await reply_target.answer_audio(
        cached["file_id"],
        title=cached["title"],
        performer=cached["artist"],
        reply_markup=actions_keyboard(video_id, db.is_favorite(chat_id, video_id)),
    )
    db.record_download(chat_id, video_id, cached["title"], cached["artist"], cached["file_id"])
    await status.delete()


async def _download_and_deliver(reply_target: Message, status: Message, fetch, quality: str) -> None:
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
        chat_id = reply_target.chat.id
        sent_msg = await reply_target.answer_audio(
            FSInputFile(track.file_path),
            title=track.title,
            performer=track.artist,
            reply_markup=actions_keyboard(track.video_id, False) if track.video_id else None,
        )
        if track.video_id:
            file_id = sent_msg.audio.file_id
            db.cache_set(track.video_id, quality, file_id, track.title, track.artist, track.duration)
            db.record_download(chat_id, track.video_id, track.title, track.artist, file_id)
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
