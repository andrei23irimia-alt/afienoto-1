import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher

from bot.config import settings
from bot.handlers import spotify, start, youtube


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    Path(settings.download_dir).mkdir(parents=True, exist_ok=True)

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()

    dispatcher.include_router(start.router)
    dispatcher.include_router(spotify.router)
    dispatcher.include_router(youtube.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
