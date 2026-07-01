from __future__ import annotations

QUALITY_LABELS = {"192": "🔉 Normal (192kbps)", "320": "🔊 Înaltă (320kbps)"}
DEFAULT_QUALITY = "192"

# Per-chat quality preference, in memory (resets on bot restart).
_chat_quality: dict[int, str] = {}


def quality_for(chat_id: int) -> str:
    return _chat_quality.get(chat_id, DEFAULT_QUALITY)


def set_quality(chat_id: int, quality: str) -> None:
    _chat_quality[chat_id] = quality
