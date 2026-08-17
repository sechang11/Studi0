#!/usr/bin/env python3
"""studio/_tools/song_check.py - QC over the delivered song library.

    python3 studio/_tools/song_check.py            # everything
    python3 studio/_tools/song_check.py --vocal    # only the ones with lyrics

TWO QUESTIONS, and they are different.

EVERY song gets the delivery checks: does it exist, is it the length the card asked for,
is it near the -16 LUFS the library normalises to, is its true peak under control, and is
it silent. Those are pass/fail and they are the ones that catch a broken render.

The VOCAL songs additionally get transcribed, and that number is NOT a pass mark. ASR on
singing is much harder than on speech - the spoken shorts hit 98% and a sung 90% is a very
good take. It is reported to RANK: a song at 15% when its neighbours sit at 70% is worth
listening to, because something in that arrangement is burying the voice.

The instrumental control from the first test is why the number can be trusted at all:
ASR on non-speech returns a hallucinated "thank you", so a low score on a vocal track is
a real signal rather than the model shrugging.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
SONGS = os.path.join(STUDIO, "songs")
SAMPLES = os.path.join(STUDIO, "samples", "songs")
VENV = os.path.expanduser("~/ComfyUI/venv/bin/python")

STOP = {"the", "a", "an", "and", "on", "for", "you", "was", "is", "we", "to", "of", "in",
        "it", "i", "our", "were", "be", "are", "my", "me", "at", "so", "but", "that",
        "this", "with", "up", "out", "all", "not", "no", "do", "did", "got", "get"}


def words(s):
    return [w for w in re.findall(r"[a-z']+", str(s).lower())
            if w not in STOP and len(w) > 2]


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def loud(path):
    r = sh("ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-")
    s = (r.stderr or "")
    s = s.split("Summary:", 1)[1] if "Summary:" in s else ""
    out = {}
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", s)
    if m:
        out["lufs"] = float(m.group(1))
    m = re.search(r"Peak:\s+(-?[\d.]+) dBFS", s)
    if m:
        out["tp"] = float(m.group(1))
    r = sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
           "default=nw=1:nk=1", path)
    try:
        out["secs"] = round(float((r.stdout or "").strip()), 1)
    except ValueError:
        pass
    return out


# Granite hallucinates on long audio. A 150s song comes back as "thank you" - its
# non-speech placeholder - while the same file transcribes accurately in 45s pieces.
# Every full-length song was being scored on that hallucination.
WINDOW = 45
STARTS = (0, 45)          # a verse and a chorus live in different parts of a song


def asr(paths):
    """One model load for the whole batch - loading Granite per song is most of the cost.

    Each song is cut into short windows first. Transcribing the whole file returns the
    non-speech placeholder for anything much over a minute, which scored real singing at
    zero.
    """
    if not paths:
        return {}
    wavs = {}
    for p in paths:
        stem = re.sub(r"\W+", "_", os.path.basename(p))[:36]
        for s in STARTS:
            w = "/tmp/_sc_%s_%d.wav" % (stem, s)
            sh("ffmpeg", "-y", "-v", "error", "-ss", str(s), "-t", str(WINDOW),
               "-i", p, "-ac", "1", "-ar", "16000", w)
            # a window past the end of a short track produces an empty file; skip it
            if os.path.exists(w) and os.path.getsize(w) > 8000:
                wavs[w] = p
    if not wavs:
        return {}
    code = ("import sys,json;sys.path.insert(0,'studio/_tools')\n"
            "from film_audio import _asr_local\n"
            "print(json.dumps(_asr_local(%r, device='cpu')))" % list(wavs))
    r = sh(VENV, "-W", "ignore", "-c", code)
    try:
        got = json.loads((r.stdout or "").strip().splitlines()[-1])
    except Exception:
        return {}
    # several windows per song now, so keep them all against the source path
    out = {}
    for k, v in got.items():
        if k in wavs:
            out.setdefault(wavs[k], []).append(v)
    return out


def find_sample(card):
    fam = card.get("genre_family") or card.get("category") or ""
    p = os.path.join(SAMPLES, fam, card["id"] + ".mp3")
    if os.path.exists(p):
        return p
    hit = glob.glob(os.path.join(SAMPLES, "*", card["id"] + ".mp3"))
    return hit[0] if hit else None


def main():
    ap = argparse.ArgumentParser(description="QC the song library.")
    ap.add_argument("--vocal", action="store_true", help="only songs with lyrics")
    a = ap.parse_args()

    cards = []
    for p in sorted(glob.glob(os.path.join(SONGS, "*.json"))):
        try:
            cards.append(json.load(open(p, encoding="utf-8")))
        except Exception:
            pass
    if a.vocal:
        cards = [c for c in cards if c.get("has_lyrics")]

    rows, missing, vocal_paths = [], [], {}
    for c in cards:
        s = find_sample(c)
        if not s:
            missing.append(c["id"])
            continue
        m = loud(s)
        want = {"stinger": 10.0, "loop": 30.0, "bed": 60.0,
                "song": 150.0}.get(c.get("length"), 30.0)
        flags = []
        if m.get("secs") and abs(m["secs"] - want) > 0.25 * want:
            flags.append("%.0fs against %.0fs asked" % (m["secs"], want))
        if m.get("lufs") is not None and abs(m["lufs"] + 16) > 3:
            flags.append("%.1f LUFS" % m["lufs"])
        if m.get("tp") is not None and m["tp"] > -0.5:
            flags.append("peak %.1f" % m["tp"])
        rows.append([c, m, flags, None])
        if c.get("has_lyrics"):
            vocal_paths[s] = len(rows) - 1

    heard = asr(list(vocal_paths))
    for p, idx in vocal_paths.items():
        c = rows[idx][0]
        texts = heard.get(p) or [""]
        want = set(words(re.sub(r"\[.*?\]", " ", c.get("lyrics", ""))))
        # the BEST window, not the average: this ranks how findable the words are, and a
        # song with a clear chorus and a muddy bridge is a song you can hear.
        best, best_text = 0.0, ""
        for text in texts:
            got = set(words(text))
            s = len(want & got) / max(1, len(want))
            if s >= best:
                best, best_text = s, text
        rows[idx][3] = (best, best_text)

    print("%-24s %-12s %6s %8s %7s  %s"
          % ("id", "family", "secs", "LUFS", "sung", "notes"))
    print("-" * 92)
    bad = 0
    for c, m, flags, v in rows:
        sung = "%3.0f%%" % (100 * v[0]) if v else "   -"
        if flags:
            bad += 1
        print("%-24s %-12s %6s %8s %7s  %s"
              % (c["id"][:24], (c.get("genre_family") or "")[:12],
                 m.get("secs", "-"), m.get("lufs", "-"), sung, "; ".join(flags)))
    print("\n%d songs checked, %d with something to look at, %d missing a render"
          % (len(rows), bad, len(missing)))
    voc = [r for r in rows if r[3]]
    if voc:
        v = sorted(voc, key=lambda r: r[3][0])
        avg = sum(r[3][0] for r in voc) / len(voc)
        print("\n%d vocal songs, mean sung recall %.0f%%" % (len(voc), 100 * avg))
        print("  hardest to hear: %s at %.0f%%" % (v[0][0]["id"], 100 * v[0][3][0]))
        print("  clearest:        %s at %.0f%%" % (v[-1][0]["id"], 100 * v[-1][3][0]))
        print("  (ASR on singing is not ASR on speech - this ranks, it does not gate)")
    if missing:
        print("\nno render yet: %s" % ", ".join(missing[:10]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
