from __future__ import annotations

import re
from dataclasses import dataclass

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from bot.config import settings

SPOTIFY_TRACK_RE = re.compile(r"open\.spotify\.com/track/([a-zA-Z0-9]+)")

_client: spotipy.Spotify | None = None


def _get_client() -> spotipy.Spotify:
    global _client
    if _client is None:
        auth = SpotifyClientCredentials(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
        )
        _client = spotipy.Spotify(client_credentials_manager=auth)
    return _client


@dataclass
class SpotifyTrack:
    title: str
    artist: str
    album: str
    duration_seconds: int
    cover_url: str | None


def is_spotify_track_url(text: str) -> bool:
    return bool(SPOTIFY_TRACK_RE.search(text))


def extract_track_id(url: str) -> str | None:
    match = SPOTIFY_TRACK_RE.search(url)
    return match.group(1) if match else None


def get_track(track_id: str) -> SpotifyTrack:
    data = _get_client().track(track_id)
    images = data["album"].get("images") or []
    return SpotifyTrack(
        title=data["name"],
        artist=", ".join(a["name"] for a in data["artists"]),
        album=data["album"]["name"],
        duration_seconds=round(data["duration_ms"] / 1000),
        cover_url=images[0]["url"] if images else None,
    )
