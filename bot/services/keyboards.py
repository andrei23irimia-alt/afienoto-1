from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def actions_keyboard(video_id: str, is_favorite: bool) -> InlineKeyboardMarkup:
    fav_label = "💔 Scoate din favorite" if is_favorite else "❤️ Favorite"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=fav_label, callback_data=f"yt_fav:{video_id}"),
                InlineKeyboardButton(text="✂️ Ringtone 30s", callback_data=f"yt_ring:{video_id}"),
            ]
        ]
    )
