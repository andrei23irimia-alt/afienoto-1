from __future__ import annotations

from pathlib import Path

import urllib.request
from mutagen.id3 import APIC, ID3, ID3NoHeaderError, TALB, TIT2, TPE1
from mutagen.mp3 import MP3


def apply_tags(
    file_path: Path,
    title: str,
    artist: str,
    album: str | None = None,
    cover_url: str | None = None,
) -> None:
    audio = MP3(file_path)
    try:
        tags = ID3(file_path)
    except ID3NoHeaderError:
        tags = ID3()

    tags["TIT2"] = TIT2(encoding=3, text=title)
    tags["TPE1"] = TPE1(encoding=3, text=artist)
    if album:
        tags["TALB"] = TALB(encoding=3, text=album)

    if cover_url:
        try:
            with urllib.request.urlopen(cover_url, timeout=10) as response:
                cover_data = response.read()
            tags["APIC"] = APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=cover_data,
            )
        except Exception:
            pass

    tags.save(file_path)
    audio.save()
