from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

router = Router()

WELCOME_TEXT = (
    "Salut! Trimite-mi:\n"
    "- un link YouTube, sau un text de căutare (ex: <i>nume artist - piesă</i>)\n"
    "- un link de track Spotify (open.spotify.com/track/...)\n\n"
    "și îți trimit înapoi piesa ca fișier audio, cu tag-uri și copertă.\n\n"
    "Bot pentru uz personal — respectă drepturile de autor ale conținutului pe care îl descarci."
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(WELCOME_TEXT)
