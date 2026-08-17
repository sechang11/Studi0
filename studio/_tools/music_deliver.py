#!/usr/bin/env python3
"""studio/_tools/music_deliver.py - the music library as a folder you can open.

    python3 studio/_tools/music_deliver.py

The library lives in the app, which is right for picking a cue while scoring a film and
wrong for every other way people use music: dragging a track into an editor, listening on
a phone, sending one to somebody. So the whole thing is copied to ~/shared/MUSIC - which
is Z:\\shared\\MUSIC from Windows - filed by genre family, with the length in the filename
so the folder sorts usefully without opening anything.

Named on the way out. `bluegrass_lp.mp3` tells you nothing at a glance;
`bluegrass__loop_150bpm_G-major.mp3` tells you whether it is the one you want before you
click. The card id stays in the INDEX so a file can always be traced back.

Alternate takes keep their __v2 suffix and sit next to the original, because the point of
a second take is comparing it to the first.
"""
import glob
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
SRC = os.path.join(STUDIO, "samples", "songs")
CARDS = os.path.join(STUDIO, "songs")
OUT = os.path.expanduser("~/shared/MUSIC")


def clean(s):
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(s or "")).strip("-")


def main():
    cards = {}
    for p in glob.glob(os.path.join(CARDS, "*.json")):
        try:
            c = json.load(open(p, encoding="utf-8"))
            cards[c["id"]] = c
        except Exception:
            pass

    os.makedirs(OUT, exist_ok=True)
    rows, n = [], 0
    for src in sorted(glob.glob(os.path.join(SRC, "*", "*.mp3"))):
        stem = os.path.splitext(os.path.basename(src))[0]
        base = stem.split("__v")[0]
        c = cards.get(base) or {}
        fam = c.get("genre_family") or os.path.basename(os.path.dirname(src))
        take = "__v" + stem.split("__v")[1] if "__v" in stem else ""
        name = "%s__%s_%sbpm_%s%s.mp3" % (
            clean(c.get("genre", base)), clean(c.get("length", "")),
            c.get("bpm", 0), clean(c.get("key", "")), take)
        d = os.path.join(OUT, clean(fam))
        os.makedirs(d, exist_ok=True)
        shutil.copy(src, os.path.join(d, name))
        rows.append((fam, name, c, stem))
        n += 1

    rows.sort()
    md = ["# Music library", "",
          "%d tracks, filed by genre family. Generated on this machine with ACE-Step 1.5."
          % n, "",
          "The filename carries what you need to choose: genre, length, tempo, key. "
          "`__v2` is a second take of the same piece on a different seed - same tags, "
          "same key, same tempo, a different performance.", "",
          "| family | file | mood | vocal | id |", "|---|---|---|---|---|"]
    for fam, name, c, stem in rows:
        md.append("| %s | %s | %s | %s | `%s` |"
                  % (fam, name, (c.get("mood") or "")[:34],
                     c.get("vocal") if c.get("vocal") != "none" else "instrumental",
                     stem))
    lyric = [(f, n_, c) for f, n_, c, _ in rows if c.get("lyrics")]
    if lyric:
        md += ["", "## Songs with words", "",
               "These have sung vocals. Lyrics are original.", ""]
        for fam, name, c in lyric:
            md += ["### %s — %s" % (c.get("title") or "", fam), "",
                   "`%s`" % name, "", "```", c["lyrics"].strip(), "```", ""]
    open(os.path.join(OUT, "INDEX.md"), "w", encoding="utf-8").write("\n".join(md))

    import collections
    fams = collections.Counter(r[0] for r in rows)
    print("%d tracks -> %s" % (n, OUT))
    print("%d families, %d with sung words" % (len(fams), len(lyric)))
    for f, k in sorted(fams.items()):
        print("   %-14s %d" % (f, k))
    return 0


if __name__ == "__main__":
    sys.exit(main())
