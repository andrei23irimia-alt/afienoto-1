from __future__ import annotations

from difflib import SequenceMatcher

from bot.services import youtube_service
from bot.services.spotify_service import SpotifyTrack


def _score(candidate: dict, track: SpotifyTrack) -> float:
    title_similarity = SequenceMatcher(
        None, candidate.get("title", "").lower(), f"{track.artist} {track.title}".lower()
    ).ratio()
    candidate_duration = candidate.get("duration") or 0
    duration_diff = abs(candidate_duration - track.duration_seconds)
    duration_penalty = min(duration_diff / max(track.duration_seconds, 1), 1.0)
    return title_similarity - duration_penalty * 0.5


async def find_best_match(track: SpotifyTrack) -> dict | None:
    query = f"{track.artist} {track.title}"
    candidates = await youtube_service.search_candidates(query, limit=5)
    if not candidates:
        return None
    return max(candidates, key=lambda c: _score(c, track))
