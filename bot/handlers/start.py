from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

router = Router()

WELCOME_TEXT = (
    "👋 <b>Salut! Ce pot să fac:</b>\n\n"
    "🎵 <b>YouTube</b>\n"
    "• trimite un link YouTube → ți-l descarc direct\n"
    "• trimite un text de căutare (ex: <i>nume artist - piesă</i>) → îți arăt câteva "
    "rezultate cu butoane, alegi unul\n"
    "• trimite un link de <b>playlist</b> YouTube → descarc primele piese din el\n\n"
    "🟢 <b>Spotify</b>\n"
    "• trimite un link de track Spotify (open.spotify.com/track/...) → găsesc piesa "
    "pe YouTube și ți-o trimit taghată corect (titlu, artist, album, copertă)\n\n"
    "⚙️ <b>Comenzi</b>\n"
    "/calitate — alegi calitatea audio (192kbps sau 320kbps)\n"
    "/istoric — ultimele tale piese, cu retrimitere instant\n"
    "/favorite — piesele tale salvate la favorite\n"
    "/statistici — câte piese ai descărcat și artistul tău preferat\n"
    "/help — acest mesaj\n\n"
    "Sub fiecare piesă primită ai butoane ❤️ (favorite) și ✂️ (ringtone de 30s).\n\n"
    "Primești mereu fișierul audio taghat, cu progres afișat live cât timp se descarcă.\n\n"
    "⚠️ Bot pentru uz personal — respectă drepturile de autor ale conținutului pe care îl descarci."
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(WELCOME_TEXT)
