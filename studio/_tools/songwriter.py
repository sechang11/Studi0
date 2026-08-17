#!/usr/bin/env python3
"""studio/_tools/songwriter.py - render a song card through ACE-Step 1.5.

    python3 studio/_tools/songwriter.py --only dawn_shift
    python3 studio/_tools/songwriter.py --hours 6 --deadline-safe

WHAT THIS BOX CAN DO THAT NOBODY HAD ASKED IT TO. The 32 cues in the library all pass
lyrics="" - instrumental beds. ACE-Step 1.5's encoder has taken a `lyrics` input the whole
time, along with bpm, keyscale, timesignature and language. That is the entire feature set
people mean when they say Suno, and it was sitting unused.

Proven before anything was built on it: a lyric take came back with ASR reading
"i counted in" out of a written line, while the instrumental control returned the
hallucinated "thank you" that ASR always gives non-speech. It sings.

THE HOUSE RECIPE, measured over six tag variants on one lyric and one seed:

    plain (no vocal words)                              10%  intelligible
    "clear female lead vocal"                           90%
    sparse arrangement + clear lead vocal               90%
    + "mixed loud and up front, intelligible diction"   30%
    + "polished studio pop, crisp consonants"           40%

NAME THE VOICE, THEN STOP. Adding one noun phrase takes intelligibility from 10% to 90%;
piling adjectives about the mix on top drops it to 30%. That is this project's oldest
finding in a new medium - the model renders nouns, not adjectives - and it is why the
VOCAL constant below is four words rather than a sentence.

ASR ON SINGING IS NOT ASR ON SPEECH. The spoken shorts hit 98% recall; a sung 90% is a
very good song. The number is used to RANK recipes, never as a pass mark.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, STUDIO)
from comfy import run                      # noqa: E402
from engine import load_wf                 # noqa: E402

HOST = os.environ.get("COMFY_HOST", "127.0.0.1:8188")
COMFY_OUT = os.path.expanduser(os.environ.get("COMFY_ROOT", "~/ComfyUI")) + "/output"
SONGS = os.path.join(STUDIO, "songs")
SAMPLES = os.path.join(STUDIO, "samples", "songs")

# The measured recipe: name the voice, do not describe the mix.
VOCAL = {"female": "clear female lead vocal",
         "male": "clear male lead vocal",
         "duet": "clear female and male lead vocals",
         "choir": "full choir vocals",
         "none": ""}

# The 34 spellings ACE-Step's keyscale combo accepts, from the node's own spec. Hard
# coded rather than fetched so a future mismatch shows up as a visible fallback instead
# of a network call inside the render path.
KEYS = {"%s %s" % (n, m)
        for m in ("major", "minor")
        for n in ("C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#",
                  "Ab", "A", "A#", "Bb", "B")}


def keyscale(want, sid=""):
    """A written key as one ACE-Step will accept.

    "B flat major" is how a musician writes it and is not in the enum; "Bb major" is.
    Two songs were rejected outright for that. A key that cannot be resolved falls back
    to C and says so - quietly transposing someone's song is worse than complaining.
    """
    k = str(want or "").strip()
    k = k.replace("-", " ")
    low = k.lower()
    for word, sym in ((" flat", "b"), (" sharp", "#")):
        low = low.replace(word, sym)
    parts = low.split()
    if not parts:
        return "C major"
    note = parts[0][:1].upper() + parts[0][1:].replace("B", "b")
    mode = "minor" if any(p.startswith("min") for p in parts[1:]) else "major"
    cand = "%s %s" % (note, mode)
    if cand in KEYS:
        return cand
    if k in KEYS:
        return k
    print("  ! %s: key %r is not one ACE-Step accepts - using C %s"
          % (sid or "?", want, mode))
    return "C %s" % mode


# Length is a real axis, not a slider: these are the four things a film actually needs.
LENGTHS = {"stinger": 10.0, "loop": 30.0, "bed": 60.0, "song": 150.0}


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def tags_for(card):
    """genre + instruments + key + mood + the vocal noun. Order matters less than the
    rule that the vocal is named ONCE and nothing argues with it afterwards."""
    bits = [card.get("genre", ""), card.get("instruments", ""),
            card.get("mood", "")]
    v = VOCAL.get(card.get("vocal", "none"), "")
    if v:
        bits.append(v)
    else:
        bits.append("instrumental")
    return ", ".join(b.strip() for b in bits if b and b.strip())


def render(card, seed=None, seconds=None):
    g = load_wf("06_acestep_music.json")
    secs = float(seconds or LENGTHS.get(card.get("length", "loop"), 30.0))
    sd = int(seed if seed is not None else card.get("seed", 4242))
    g["10"]["inputs"].update(
        tags=tags_for(card), lyrics=card.get("lyrics", "") or "",
        # ACE-Step's floor is 10. Cards written as bpm 0 mean "unmetered", and that
        # intent lives in the tags ("no drums") rather than in a number the model rejects.
        seed=sd, bpm=max(10, int(card.get("bpm", 100) or 0)), duration=secs,
        keyscale=keyscale(card.get("key"), card.get("id", "")),
        timesignature=str(card.get("timesignature", "4")),
        language=card.get("language", "en"))
    g["11"]["inputs"]["seconds"] = secs
    g["12"]["inputs"]["seed"] = sd
    g["14"]["inputs"]["filename_prefix"] = "claude-generated/songs/" + card["id"]
    _, outs = run(HOST, g, quiet=True)
    if not outs:
        return None
    p = outs[0]
    return p if os.path.isabs(p) else os.path.join(COMFY_OUT, p)


def measure(path):
    r = sh("ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-")
    err = r.stderr or ""
    s = err.split("Summary:", 1)[1] if "Summary:" in err else ""
    out = {}
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", s)
    if m:
        out["lufs"] = float(m.group(1))
    m = re.search(r"Peak:\s+(-?[\d.]+) dBFS", s)
    if m:
        out["true_peak"] = float(m.group(1))
    r = sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
           "default=nw=1:nk=1", path)
    try:
        out["seconds"] = round(float((r.stdout or "").strip()), 1)
    except ValueError:
        pass
    return out


def deliver(card, src):
    """File it by genre, peak-limited, beside its record - the same rules as the rest of
    the sound library. The audition copy gets a ceiling because the raw render routinely
    lands above 0 dBTP and a hot audition is how a good take gets rejected."""
    sub = card.get("genre_family") or card.get("genre", "other").split(",")[0].strip()
    sub = re.sub(r"[^a-z0-9_]+", "_", sub.lower()).strip("_") or "other"
    d = os.path.join(SAMPLES, sub)
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, card["id"] + ".mp3")
    # NORMALISED FOR AUDITION. Raw takes came back 12 dB apart (-25.2 next to -13.7);
    # both are good, but browsing a library where every click jumps in level is not. Two
    # pass loudnorm to -16 LUFS, then a true-peak ceiling. The unnormalised render stays
    # in ComfyUI's output if the original dynamics are ever wanted.
    r = sh("ffmpeg", "-y", "-v", "error", "-i", src, "-af",
           "loudnorm=I=-16:TP=-1.5:LRA=11,"
           "aresample=192000,alimiter=limit=0.71:attack=1:release=50:level=disabled,"
           "aresample=48000", "-c:a", "libmp3lame", "-q:a", "2", dst)
    if not os.path.exists(dst):
        return None
    m = measure(dst)
    json.dump({"kind": "songs", "id": card["id"], "card": card,
               "tags_sent": tags_for(card), "measured": m,
               "workflow": "06_acestep_music.json",
               "rendered": time.strftime("%Y-%m-%d %H:%M")},
              open(os.path.splitext(dst)[0] + ".json", "w", encoding="utf-8"), indent=1)
    return dst, m


def _note_failure(card, why):
    """Write the reason onto the card. A failure nobody can see is a card that looks
    merely unrendered, and this library is too big to re-derive that by hand."""
    p = os.path.join(SONGS, card["id"] + ".json")
    try:
        c = json.load(open(p, encoding="utf-8"))
        c["last_failure"] = {"why": why, "at": time.strftime("%Y-%m-%d %H:%M")}
        json.dump(c, open(p, "w", encoding="utf-8"), indent=2)
    except OSError:
        pass


def cards():
    for p in sorted(glob.glob(os.path.join(SONGS, "*.json"))):
        if os.path.basename(p).startswith("_"):
            continue
        try:
            yield json.load(open(p, encoding="utf-8"))
        except Exception as e:
            print("  ! unreadable %s: %s" % (p, e))


def main():
    ap = argparse.ArgumentParser(description="Render song cards through ACE-Step.")
    ap.add_argument("--only")
    ap.add_argument("--hours", type=float, default=0, help="stop after this long")
    ap.add_argument("--fresh", action="store_true", help="re-render even if delivered")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    end = time.time() + a.hours * 3600 if a.hours else None

    todo = [c for c in cards() if not a.only or c["id"] == a.only]
    done = skipped = failed = 0
    for i, c in enumerate(todo):
        if a.limit and done >= a.limit:
            break
        if end and time.time() > end:
            print("deadline reached, stopping cleanly")
            break
        sub = re.sub(r"[^a-z0-9_]+", "_",
                     (c.get("genre_family") or "other").lower()).strip("_") or "other"
        out = os.path.join(SAMPLES, sub, c["id"] + ".mp3")
        if os.path.exists(out) and not a.fresh:
            skipped += 1
            continue
        t0 = time.time()
        # GUARDED. comfy.run calls sys.exit(1) on a rejected graph, so without catching
        # SystemExit one malformed card ends the run - which is exactly what happened on
        # the first batch: card 5 took the remaining 39 with it.
        try:
            src = render(c)
        except SystemExit:
            src = None
            why = "ComfyUI rejected the graph"
        except Exception as e:
            src = None
            why = str(e)[:200]
        else:
            why = "the graph produced no audio"
        if not src or not os.path.exists(src):
            print("%-26s NO RENDER - %s" % (c["id"], why))
            _note_failure(c, why)
            failed += 1
            continue
        got = deliver(c, src)
        if not got:
            print("%-26s NO DELIVERY" % c["id"])
            failed += 1
            continue
        dst, m = got
        done += 1
        print("%-26s %-9s %-14s %5.1fs  %5.1fs render  %s LUFS"
              % (c["id"], c.get("length"), (c.get("genre_family") or "")[:14],
                 m.get("seconds", 0), time.time() - t0, m.get("lufs")))
    print("\n%d rendered, %d already there, %d failed" % (done, skipped, failed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
