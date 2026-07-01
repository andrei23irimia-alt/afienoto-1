from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from bot.config import settings

_connection: sqlite3.Connection | None = None


def _get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(settings.db_path, check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _init_schema(_connection)
    return _connection


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            video_id TEXT NOT NULL,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            file_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_downloads_chat ON downloads(chat_id, id DESC);

        CREATE TABLE IF NOT EXISTS favorites (
            chat_id INTEGER NOT NULL,
            video_id TEXT NOT NULL,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            file_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (chat_id, video_id)
        );

        CREATE TABLE IF NOT EXISTS video_cache (
            video_id TEXT NOT NULL,
            quality TEXT NOT NULL,
            file_id TEXT NOT NULL,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            duration INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (video_id, quality)
        );
        """
    )
    conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_download(chat_id: int, video_id: str, title: str, artist: str, file_id: str) -> None:
    conn = _get_connection()
    conn.execute(
        "INSERT INTO downloads (chat_id, video_id, title, artist, file_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (chat_id, video_id, title, artist, file_id, _now()),
    )
    conn.commit()


def get_history(chat_id: int, limit: int = 10) -> list[sqlite3.Row]:
    conn = _get_connection()
    cur = conn.execute(
        "SELECT * FROM downloads WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
        (chat_id, limit),
    )
    return cur.fetchall()


def add_favorite(chat_id: int, video_id: str, title: str, artist: str, file_id: str) -> None:
    conn = _get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO favorites (chat_id, video_id, title, artist, file_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (chat_id, video_id, title, artist, file_id, _now()),
    )
    conn.commit()


def remove_favorite(chat_id: int, video_id: str) -> None:
    conn = _get_connection()
    conn.execute("DELETE FROM favorites WHERE chat_id = ? AND video_id = ?", (chat_id, video_id))
    conn.commit()


def is_favorite(chat_id: int, video_id: str) -> bool:
    conn = _get_connection()
    cur = conn.execute(
        "SELECT 1 FROM favorites WHERE chat_id = ? AND video_id = ?", (chat_id, video_id)
    )
    return cur.fetchone() is not None


def get_favorites(chat_id: int) -> list[sqlite3.Row]:
    conn = _get_connection()
    cur = conn.execute(
        "SELECT * FROM favorites WHERE chat_id = ? ORDER BY created_at DESC", (chat_id,)
    )
    return cur.fetchall()


def cache_get(video_id: str, quality: str) -> sqlite3.Row | None:
    conn = _get_connection()
    cur = conn.execute(
        "SELECT * FROM video_cache WHERE video_id = ? AND quality = ?", (video_id, quality)
    )
    return cur.fetchone()


def cache_set(
    video_id: str, quality: str, file_id: str, title: str, artist: str, duration: int = 0
) -> None:
    conn = _get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO video_cache (video_id, quality, file_id, title, artist, duration) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (video_id, quality, file_id, title, artist, duration),
    )
    conn.commit()


def find_cached(video_id: str) -> sqlite3.Row | None:
    conn = _get_connection()
    cur = conn.execute("SELECT * FROM video_cache WHERE video_id = ? LIMIT 1", (video_id,))
    return cur.fetchone()


def stats_for(chat_id: int) -> dict:
    conn = _get_connection()
    total = conn.execute(
        "SELECT COUNT(*) AS c FROM downloads WHERE chat_id = ?", (chat_id,)
    ).fetchone()["c"]
    favorites = conn.execute(
        "SELECT COUNT(*) AS c FROM favorites WHERE chat_id = ?", (chat_id,)
    ).fetchone()["c"]
    top_artist_row = conn.execute(
        "SELECT artist, COUNT(*) AS c FROM downloads WHERE chat_id = ? "
        "GROUP BY artist ORDER BY c DESC LIMIT 1",
        (chat_id,),
    ).fetchone()
    return {
        "total": total,
        "favorites": favorites,
        "top_artist": top_artist_row["artist"] if top_artist_row else None,
        "top_artist_count": top_artist_row["c"] if top_artist_row else 0,
    }
