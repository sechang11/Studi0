#!/usr/bin/env python3
"""studio/_tools/songsmith.py - one command, one song.

    python3 studio/_tools/songsmith.py "a slow blues about a broken lift" \\
        --genre "slow blues" --vocal male --lyrics-file words.txt

    python3 studio/_tools/songsmith.py "warm acoustic bed for a kitchen advert" \\
        --genre "acoustic corporate" --length loop --bpm 100

The library route is right when you are building a catalogue: author a card, render the
lot, browse by genre. It is the wrong shape when you want ONE song now. This is that
shape - describe it, get a card and a finished take, and the card stays so the song is
reproducible and shows up in the library like everything else.

WHAT IT WILL AND WILL NOT DO FOR YOU. It writes the tags, picks a sane bpm and key for
the genre if you do not, names the vocal correctly (the measured recipe: name it once,
describe it never), and renders two takes so there is a choice. It does NOT write your
lyrics. A small local model can produce lyric-shaped text but not lyrics worth singing,
and a song with filler words in it is worse than an instrumental - so lyrics come from a
file or a flag, and without them you get an instrumental, which is honest.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
SONGS = os.path.join(STUDIO, "songs")

# a sane starting point per family, so --bpm and --key are optional rather than homework
DEFAULTS = {
    "blues": (72, "A minor"), "rock": (128, "E minor"), "pop": (112, "C major"),
    "folk": (92, "G major"), "jazz": (96, "F major"), "soul": (84, "Eb major"),
    "country": (110, "D major"), "metal": (150, "E minor"), "punk": (170, "A minor"),
    "electronic": (124, "A minor"), "house": (122, "F minor"), "techno": (130, "A minor"),
    "lofi": (78, "F minor"), "ambient": (10, "D major"), "cinematic": (72, "D minor"),
    "classical": (88, "G minor"), "world": (108, "A minor"), "game": (140, "C major"),
    "advertising": (108, "C major"), "gospel": (96, "Bb major"),
}


def guess(genre):
    g = (genre or "").lower()
    for k, v in DEFAULTS.items():
        if k in g:
            return v
    return (110, "C major")


def main():
    ap = argparse.ArgumentParser(description="Describe a song, get a song.")
    ap.add_argument("idea", help="what the song is for, in plain words")
    ap.add_argument("--genre", required=True, help='e.g. "slow blues", "indie folk"')
    ap.add_argument("--instruments", default="",
                    help="named instruments; the model renders nouns, so this matters "
                         "more than any adjective you could write")
    ap.add_argument("--mood", default="")
    ap.add_argument("--vocal", default="none",
                    choices=("none", "female", "male", "duet", "choir"))
    ap.add_argument("--lyrics-file", help="a text file with [verse]/[chorus] tags")
    ap.add_argument("--lyrics", help="lyrics inline")
    ap.add_argument("--length", default="song",
                    choices=("stinger", "loop", "bed", "song"))
    ap.add_argument("--bpm", type=int)
    ap.add_argument("--key")
    ap.add_argument("--id")
    ap.add_argument("--takes", type=int, default=2)
    a = ap.parse_args()

    lyrics = a.lyrics or ""
    if a.lyrics_file:
        lyrics = open(a.lyrics_file, encoding="utf-8").read()
    if lyrics.strip() and a.vocal == "none":
        print("! you gave lyrics but --vocal none; nothing will sing them.\n"
              "  pick --vocal female|male|duet|choir", file=sys.stderr)
        return 2

    bpm, key = guess(a.genre)
    sid = a.id or re.sub(r"[^a-z0-9]+", "_", a.idea.lower())[:40].strip("_")
    fam = re.sub(r"[^a-z0-9]+", "_", a.genre.lower().split()[-1])
    card = {
        "id": sid, "title": a.idea[:60],
        "genre_family": fam, "category": fam, "subcategory": a.length,
        "genre": a.genre,
        "instruments": a.instruments or a.genre,
        "mood": a.mood or a.idea[:40],
        "vocal": a.vocal, "bpm": a.bpm or bpm, "key": a.key or key,
        "length": a.length, "language": "en", "timesignature": "4",
        "lyrics": lyrics.strip(), "has_lyrics": bool(lyrics.strip()),
        "status": "weak", "seed": 4242 + (abs(hash(sid)) % 9000),
        "desc": a.idea,
        "note": "Written by songsmith from a one-line brief.",
        "evidence": {"verdict": "UNVERIFIED", "method": "authored by songsmith",
                     "date": "2026-08-17", "note": ""},
    }
    os.makedirs(SONGS, exist_ok=True)
    p = os.path.join(SONGS, sid + ".json")
    json.dump(card, open(p, "w", encoding="utf-8"), indent=2)
    print("card  -> %s" % p)
    print("tags  -> genre %s | %s | %s bpm | %s | vocal %s"
          % (a.genre, card["instruments"], card["bpm"], card["key"], a.vocal))
    if not lyrics.strip():
        print("       instrumental (no lyrics given)")

    cmd = [sys.executable, os.path.join(HERE, "songwriter.py"), "--only", sid,
           "--variants", str(max(1, a.takes)), "--fresh"]
    r = subprocess.run(cmd, cwd=os.path.dirname(STUDIO))
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
