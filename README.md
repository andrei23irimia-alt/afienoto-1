# afienoto-1 — bot de muzică pentru Telegram

Bot Telegram (Python, [aiogram](https://docs.aiogram.dev/) 3.x) care descarcă audio de pe YouTube și, pentru linkuri Spotify, preia metadatele (titlu/artist/album/copertă) prin Spotify Web API și descarcă audio-ul corespunzător de pe YouTube.

> Bot pentru uz personal/privat. Datele de pe Spotify sunt folosite doar pentru metadate (titlu, artist, copertă) prin API-ul oficial — niciun conținut audio sau protejat DRM nu e accesat de la Spotify. Descărcarea de pe YouTube poate intra în conflict cu Termenii de Utilizare ai YouTube în funcție de jurisdicție și context de folosire; respectă drepturile de autor ale conținutului pe care îl descarci și nu distribui public/la scară acest bot.

## Funcționalități

- Trimite un link YouTube → primești piesa ca fișier audio, taghată (titlu/artist), cu progres live al descărcării (%).
- Trimite un text de căutare (ex: `artist - piesă`) → botul îți arată până la 5 rezultate ca butoane, alegi unul și primești fișierul.
- Trimite un link de **playlist YouTube** → botul descarcă primele piese din el (limită configurabilă, implicit 10) și le trimite pe rând, cu progres.
- Trimite un link de track Spotify (`open.spotify.com/track/...`) → botul ia metadatele de pe Spotify, găsește cea mai bună potrivire pe YouTube, descarcă și trimite piesa taghată cu titlu/artist/album/copertă corecte.
- `/calitate` — alegi calitatea audio (192kbps sau 320kbps) printr-un meniu cu butoane; preferința se ține minte per conversație.
- `/istoric` — ultimele 10 piese descărcate, cu buton de retrimitere **instant** (fără să redescarce, refolosește fișierul deja trimis pe Telegram).
- `/favorite` — piesele salvate la favorite (❤️ sub orice piesă trimisă), cu retrimitere instant și opțiune de ștergere.
- `/statistici` — câte piese ai descărcat, câte favorite ai și artistul tău cel mai ascultat.
- ✂️ **Ringtone 30s** — buton sub orice piesă trimisă, taie un fragment de 30 de secunde și îl trimite separat.
- ⚡ **Cache automat** — dacă aceeași piesă (același video YouTube + aceeași calitate) e cerută din nou, oricând, de oricine, botul o retrimite instant din cache, fără să mai descarce.
- Meniul de comenzi din Telegram (`/start`, `/calitate`, `/istoric`, `/favorite`, `/statistici`, `/help`) e setat automat la pornirea botului.
- Mesaje cu emoji și formatare, ca să fie clar în ce stadiu e descărcarea (🔎 caut / ⬇️ descarc / 🏷️ taghez / 📤 trimit).
- Limită configurabilă de durată (implicit 15 min) pentru a evita descărcări foarte mari.
- Dacă `ffmpeg` nu e instalat pe sistem, botul folosește automat binarul inclus în pachetul Python `imageio-ffmpeg` — nu mai trebuie instalat manual.

## Setup

1. Instalează [ffmpeg](https://ffmpeg.org/) pe sistem (necesar pentru conversia audio):
   ```bash
   sudo apt-get install ffmpeg   # Debian/Ubuntu
   ```
2. Creează un mediu virtual și instalează dependențele:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copiază `.env.example` în `.env` și completează:
   - `BOT_TOKEN` — token de la [@BotFather](https://t.me/BotFather).
   - `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` — dintr-o aplicație creată pe [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) (modul Development e suficient; acceptă până la 5 utilizatori).
4. Rulează botul:
   ```bash
   python -m bot.main
   ```

## Testare

```bash
pip install -r requirements-dev.txt
pytest
```

Testele acoperă logica pură (recunoașterea linkurilor YouTube/Spotify, scorul de potrivire dintre un track Spotify și rezultatele YouTube) — nu fac cereri reale către YouTube/Spotify.

## Descărcare fără instalare (APK / executabile PC)

La fiecare push pe branch, GitHub Actions construiește automat și publică pe pagina **Releases** a repo-ului:

- **Android** (release `android-latest`): un APK minim (`afienoto-launcher.apk`) care doar deschide chat-ul cu botul în Telegram — nu conține logica de descărcare, doar un shortcut. Înainte de build, username-ul botului se setează în `android/gradle.properties` (`botUsername=...`).
- **PC** (release `desktop-latest`): executabile de sine stătătoare (`afienoto-bot-windows.exe`, `afienoto-bot-macos`, `afienoto-bot-linux`) care pornesc botul fără să mai instalezi Python manual. Ai nevoie totuși de un fișier `.env` lângă executabil (vezi `.env.example`).

Compilarea reală (SDK Android, PyInstaller per-OS) se face pe infrastructura GitHub Actions, nu local.

## Structură proiect

```
bot/
├── main.py                  # entrypoint (polling)
├── config.py                # setări din .env
├── handlers/
│   ├── start.py             # /start, /help
│   ├── spotify.py           # linkuri de track Spotify
│   └── youtube.py           # linkuri YouTube / playlist / căutare / istoric / favorite / ringtone
└── services/
    ├── youtube_service.py   # yt-dlp: căutare + descărcare + conversie mp3 + progres
    ├── spotify_service.py   # spotipy: metadate track
    ├── matcher.py           # potrivește track Spotify cu rezultatul YouTube corect
    ├── tagging.py           # mutagen: tag-uri ID3 + copertă
    ├── db.py                 # SQLite: istoric, favorite, cache de fișiere (bot_data.db)
    ├── preferences.py       # preferința de calitate audio per conversație
    └── keyboards.py         # butoanele ❤️ / ✂️ atașate sub piesele trimise
tests/                       # teste pentru logica pură (fără rețea)
android/                     # aplicație Android minimă (shortcut către bot)
run.py                       # entrypoint pentru build-uri PyInstaller (PC)
```

Baza de date SQLite (`bot_data.db`, configurabil via `DB_PATH`) se creează automat la prima rulare, lângă bot — nu necesită niciun server extern.

## Idei pentru extinderi viitoare (nu sunt încă implementate)

- Descărcare albume complete de pe Spotify, cu progres live (playlist-urile YouTube merg deja).
- Inline mode (`@bot piesă` în orice chat).
- Auto-detect: orice link YouTube/Spotify forwardat e procesat automat, fără comandă.
- Alegere format (opus / FLAC) pe lângă MP3 (calitatea 192/320kbps merge deja din `/calitate`).
- Recunoaștere piesă dintr-o notă vocală (stil Shazam, via `shazamio`).
- Limită zilnică de cereri per utilizator.
- Deployment cu Docker + webhook în loc de polling.
- App Android/desktop independentă (fără Telegram) — momentan APK-ul e doar un shortcut spre bot, iar executabilele PC doar rulează botul local.

*Notă:* recomandări automate tip "radio" nu sunt incluse — API-ul Spotify nu mai oferă acces la endpoint-ul de recomandări pentru aplicații noi.
