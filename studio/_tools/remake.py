#!/usr/bin/env python3
"""studio/_tools/remake.py - flag a sound as bad, throw the take away, render another.

    python3 studio/_tools/remake.py --audit                 which ones measure as static
    python3 studio/_tools/remake.py --flag ui_click --reason "scratchy"
    python3 studio/_tools/remake.py --list
    python3 studio/_tools/remake.py --run                   re-render everything flagged
    python3 studio/_tools/remake.py --unflag ui_click

WHY. Generated sound effects fail in a specific, recognisable way: they come back as
broadband hiss - "scratching static" - instead of the thing that was asked for. Until now
the only recourse was to re-run the whole sweep with --fresh, which re-rolls the good
ones too and gives you a different library rather than a better one.

THE TAKE IS ARCHIVED, NOT DELETED. This follows the same rule as reject() in
library_index: a bad render is evidence about a prompt. The old audio and its render
record move to samples/_rejected/<kind>/ with the reason and a timestamp, so "the ui
prompts keep coming back as noise" stays a fact you can point at, and a remake that turns
out worse can be put back by hand.

THE AUDIT IS A CANDIDATE LIST, NOT A VERDICT. Spectral flatness measures how noise-like a
signal is (0 tonal, 1 white noise), and for SFX a high number is NOT automatically wrong:
wind, rain, crowd and whoosh are SUPPOSED to be broadband. So the audit compares flatness
against what the CATEGORY should sound like - a click, a bark or a bell that measures like
static is a real defect; a rain bed that does is rain. It ranks and suggests. Your ears
decide, which is why --flag is a separate, manual step.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
SAMPLES = os.path.join(STUDIO, "samples")
REJECTED = os.path.join(SAMPLES, "_rejected")
VENV_PY = os.path.expanduser("~/ComfyUI/venv/bin/python")

# What a category is SUPPOSED to sound like. Broadband categories are exempt from the
# noise flag because noise is the deliverable; transient/tonal ones are not.
EXPECT_NOISY = {"weather", "ambience", "crowd", "elements", "transitions"}
# above this, a signal is essentially hiss
NOISE_FLOOR = 0.20


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def flatness(path):
    """Spectral flatness via the ComfyUI venv's librosa. 0 tonal, 1 white noise."""
    if not os.path.exists(VENV_PY):
        return None
    code = ("import sys,json,numpy as np,librosa\n"
            "y,sr=librosa.load(sys.argv[1],sr=22050,mono=True,duration=30)\n"
            "f=float(np.mean(librosa.feature.spectral_flatness(y=y)))\n"
            "c=float(np.max(np.abs(y))/(np.sqrt(np.mean(y**2))+1e-9))\n"
            "print(json.dumps({'flatness':round(f,4),'crest':round(c,2)}))")
    r = sh(VENV_PY, "-c", code, path)
    try:
        return json.loads((r.stdout or "").strip().splitlines()[-1])
    except Exception:
        return None


def cards_of(kind):
    for p in sorted(glob.glob(os.path.join(STUDIO, kind, "*.json"))):
        if os.path.basename(p).startswith("_"):
            continue
        try:
            yield p, json.load(open(p, encoding="utf-8"))
        except Exception:
            continue


def sample_of(kind, card):
    """Where this card's audio actually lives, filed or flat."""
    cid = card.get("id")
    sub = card.get("category")
    for cand in ([os.path.join(SAMPLES, kind, str(sub), cid + ".mp3")] if sub else []) + \
                [os.path.join(SAMPLES, kind, cid + ".mp3")] + \
                glob.glob(os.path.join(SAMPLES, kind, "*", cid + ".mp3")):
        if os.path.exists(cand):
            return cand
    return None


def audit(kind):
    rows = []
    for _p, card in cards_of(kind):
        s = sample_of(kind, card)
        if not s:
            continue
        m = flatness(s) or {}
        cat = card.get("category") or "-"
        f = m.get("flatness")
        if f is None:
            continue
        exempt = cat in EXPECT_NOISY
        suspect = (not exempt) and f >= NOISE_FLOOR
        rows.append((f, m.get("crest"), cat, card["id"], exempt, suspect,
                     bool(card.get("remake"))))
    rows.sort(key=lambda r: -r[0])
    print("%-22s %-12s %8s %7s  %s" % ("id", "category", "flatness", "crest", "verdict"))
    print("-" * 74)
    for f, c, cat, cid, exempt, suspect, flagged in rows:
        v = ("FLAGGED" if flagged else
             "SUSPECT - noise where structure was asked for" if suspect else
             "noise is the point here" if exempt and f >= NOISE_FLOOR else "")
        print("%-22s %-12s %8.4f %7s  %s" % (cid, cat, f, c if c is not None else "-", v))
    n = sum(1 for r in rows if r[5])
    print("\n%d measured, %d suspect. Listen to those, then --flag the ones you agree with."
          % (len(rows), n))
    print("Flatness above %.2f is essentially hiss; %s are exempt because broadband IS "
          "the deliverable." % (NOISE_FLOOR, "/".join(sorted(EXPECT_NOISY))))
    return 0


def flag(kind, cid, reason, on=True):
    p = os.path.join(STUDIO, kind, cid + ".json")
    if not os.path.exists(p):
        print("no such card: %s/%s" % (kind, cid), file=sys.stderr)
        return 1
    card = json.load(open(p, encoding="utf-8"))
    if on:
        card["remake"] = {"reason": reason or "flagged by hand",
                          "at": time.strftime("%Y-%m-%d %H:%M")}
        print("flagged %s/%s - %s" % (kind, cid, reason or "no reason given"))
    else:
        card.pop("remake", None)
        print("unflagged %s/%s" % (kind, cid))
    json.dump(card, open(p, "w", encoding="utf-8"), indent=2)
    return 0


def listing():
    n = 0
    for kind in ("sfx", "cues"):
        for _p, card in cards_of(kind):
            r = card.get("remake")
            if r:
                n += 1
                print("%-6s %-22s %s  (%s)" % (kind, card["id"], r.get("reason", ""),
                                               r.get("at", "")))
    print("%d flagged for remake" % n)
    return 0


def archive(kind, card, sample, reason):
    """Move the take out of the library. MOVED - a bad render is evidence about a prompt."""
    d = os.path.join(REJECTED, kind)
    os.makedirs(d, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = os.path.join(d, "%s_%s.mp3" % (card["id"], stamp))
    shutil.move(sample, dst)
    side = os.path.splitext(sample)[0] + ".json"
    if os.path.exists(side):
        rec = json.load(open(side, encoding="utf-8"))
        rec["rejected"] = {"reason": reason, "at": stamp}
        json.dump(rec, open(os.path.splitext(dst)[0] + ".json", "w", encoding="utf-8"),
                  indent=1)
        os.remove(side)
    return dst


def run(seed):
    """Re-render every flagged card, on a NEW seed. Same seed would return the same take."""
    sys.path.insert(0, HERE)
    done = fail = 0
    for kind in ("sfx", "cues"):
        for p, card in cards_of(kind):
            r = card.get("remake")
            if not r:
                continue
            cid = card["id"]
            s = sample_of(kind, card)
            if s:
                dst = archive(kind, card, s, r.get("reason", ""))
                print("  archived %s -> %s" % (cid, os.path.relpath(dst, SAMPLES)))
            # a different seed, or the model returns the take you just threw away
            new_seed = seed + (abs(hash(cid)) % 9000)
            cmd = [sys.executable, os.path.join(HERE, "audio_sweep.py"),
                   "--kind", kind, "--only", cid, "--seed", str(new_seed), "--fresh"]
            out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
            tail = [l for l in (out.stdout or "").splitlines() if cid in l]
            print("  %s" % (tail[-1] if tail else "no output for %s" % cid))
            if tail and "FAILED" not in tail[-1] and "NO RENDER" not in tail[-1]:
                card = json.load(open(p, encoding="utf-8"))
                hist = card.get("remake_history") or []
                hist.append({**r, "seed": new_seed, "done": time.strftime("%Y-%m-%d %H:%M")})
                card["remake_history"] = hist[-8:]
                card.pop("remake", None)
                json.dump(card, open(p, "w", encoding="utf-8"), indent=2)
                done += 1
            else:
                fail += 1
    print("\n%d remade, %d still flagged (they failed - the flag stays so you see them)"
          % (done, fail))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Flag bad takes and render replacements.")
    ap.add_argument("--audit", action="store_true", help="rank by how noise-like it is")
    ap.add_argument("--kind", default="sfx", choices=("sfx", "cues"))
    ap.add_argument("--flag")
    ap.add_argument("--unflag")
    ap.add_argument("--reason", default="")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--seed", type=int, default=8801)
    a = ap.parse_args()
    if a.audit:
        return audit(a.kind)
    if a.flag:
        return flag(a.kind, a.flag, a.reason, True)
    if a.unflag:
        return flag(a.kind, a.unflag, "", False)
    if a.list:
        return listing()
    if a.run:
        return run(a.seed)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
