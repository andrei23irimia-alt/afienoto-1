from __future__ import annotations

import logging
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, FSInputFile

from bot.config import settings
from bot.services import matcher, preferences, spotify_service, tagging, youtube_service

router = Router()
logger = logging.getLogger(__name__)


@router.message(
    F.text.func(spotify_service.is_spotify_url) & ~F.text.func(spotify_service.is_spotify_track_url)
)
async def handle_unsupported_spotify_link(message: Message) -> None:
    await message.answer(
        "Momentan suport doar linkuri de track Spotify (open.spotify.com/track/...). "
        "Playlist-urile și albumele vin într-o versiune viitoare."
    )


@router.message(F.text.func(spotify_service.is_spotify_track_url))
async def handle_spotify_track(message: Message) -> None:
    track_id = spotify_service.extract_track_id(message.text.strip())
    if not track_id:
        await message.answer("Nu am recunoscut linkul de Spotify.")
        return

    status = await message.answer("🔎 Caut piesa pe Spotify...")

    try:
        spotify_track = spotify_service.get_track(track_id)
    except Exception:
        logger.exception("Spotify metadata fetch failed for track_id: %s", track_id)
        await status.edit_text("❌ Nu am putut citi datele de pe Spotify. Verifică link-ul sau configurația botului.")
        return

    if spotify_track.duration_seconds > settings.max_duration_seconds:
        await status.edit_text(
            f"⏱️ Piesa este prea lungă ({spotify_track.duration_seconds // 60} min). "
            f"Limita este {settings.max_duration_seconds // 60} min."
        )
        return

    await status.edit_text("🔎 Caut cea mai bună potrivire pe YouTube...")
    best_match = await matcher.find_best_match(spotify_track)
    if not best_match:
        await status.edit_text("❌ Nu am găsit o potrivire pe YouTube pentru această piesă.")
        return

    quality = preferences.quality_for(message.chat.id)
    await status.edit_text("⬇️ Se descarcă... 0%")

    async def on_progress(pct: int) -> None:
        try:
            await status.edit_text(f"⬇️ Se descarcă... {pct}%")
        except Exception:
            pass

    try:
        yt_track = await youtube_service.download_video_id(best_match["id"], quality, on_progress)
    except Exception:
        logger.exception("YouTube download failed for matched video: %s", best_match.get("id"))
        await status.edit_text("❌ Am găsit piesa, dar descărcarea a eșuat. Încearcă din nou.")
        return

    await status.edit_text("🏷️ Adaug tag-uri și copertă...")
    tagging.apply_tags(
        yt_track.file_path,
        title=spotify_track.title,
        artist=spotify_track.artist,
        album=spotify_track.album,
        cover_url=spotify_track.cover_url,
    )

    try:
        await status.edit_text("📤 Trimit fișierul...")
        await message.answer_audio(
            FSInputFile(yt_track.file_path),
            title=spotify_track.title,
            performer=spotify_track.artist,
        )
    finally:
        await status.delete()
        _cleanup(yt_track.file_path)


def _cleanup(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception:
        logger.warning("Could not remove temp file %s", path)
