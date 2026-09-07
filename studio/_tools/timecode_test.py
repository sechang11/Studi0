#!/usr/bin/env python3
"""Does LTX-2.5 read timecodes, or the word CUT, or neither?

RUN 1 (2 seeds, asked 2 s / 8 s of 12) and what looking at it taught:

  ordinal   "Shot 1: ... Shot 2: ... Shot 3: ..."     no spikes on either seed
  timecoded "0-2s: ... 2-8s: CUT to ... 8-12s: CUT to"  a hard cut at 8.0 (seed 1234);
                                                        clusters at ~3.5 and ~8.4 (seed 77)

The detector said the ordinal prompt produced no cuts.  The frames say something else: the
ordinal clip contains all three beats in order, at nearly the SAME times as the timecoded one
(deck to ~2.5 s, wheel to ~7.5 s, sky after) - it DISSOLVED between them instead of cutting.
So run 1 could not tell what did the work.  Two variables moved together: the numbers, and the
word CUT.  And the second asked time, 8 s, sat exactly on the thirds grid, so a model dividing
the clip evenly and a model reading the ask both land there.

RUN 2 separates them.  Four prompts, same three beats, same key, same seed, 12 s:

  A  ordinal, no CUT        "Shot 1: ... Shot 2: ... Shot 3: ..."                (the studio today)
  B  timecodes + CUT        "0-3s: ... 3-9s: CUT to ... 9-12s: CUT to ..."
  C  timecodes, no CUT      "0-3s: ... 3-9s: ... 9-12s: ..."
  D  ordinal + CUT          "Shot 1: ... CUT to Shot 2: ... CUT to Shot 3: ..."

Asked boundaries 3 and 9 sit a full second off the thirds grid (4 and 8) at BOTH positions.
  - if B and C put boundaries near 3 and 9 while A and D sit near 4 and 8: the NUMBERS move pacing
  - if B and D cut hard while A and C dissolve, regardless of timing: the WORD makes the cut
  - both can be true, and that is the useful outcome: pacing from numbers, transition from the word

THE JUDGE reads two things off 8 fps frame differences, each against the clip's own median+MAD:
  hard cut    one sampled frame far above (k=6) its neighbours            -> multishot.cuts()
  dissolve    a run of >= 3 sampled frames moderately above (k=2.5)      -> soft()
Every boundary is reported with its kind and its time, then the distance to what was asked and
to the thirds grid.  Look at the strips anyway; a judge is a summary of frames, not a replacement.

    ~/ComfyUI/venv/bin/python3 timecode_test.py --seeds 2
    ~/ComfyUI/venv/bin/python3 timecode_test.py --cuts 3 9 --seeds 2 --variants A B C D
"""
import argparse
import json
import os
import shutil
import statistics
import sys
import time

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
TOOLS = os.path.join(STUDIO, "_tools")
sys.path.insert(0, TOOLS)
sys.path.insert(0, STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run, set_path            # noqa: E402
from engine import load_wf, HOST           # noqa: E402
import multishot as MS                     # noqa: E402  (cuts, COMFY, aspect_for, sh)

COMFY = MS.COMFY
KEY = os.path.join(STUDIO, "samples", "isolation", "places", "clean_airship_deck_0.png")
OUT = os.path.join(STUDIO, "samples", "timecode")
SECONDS = 12
ASKED = [3.0, 9.0]

# Three beats on an airship deck, no named characters: the question is pacing and transition,
# and a face would add a variable (identity across the cut) this test is not about.
BEATS = [
    "a wide shot of the empty airship deck at dawn, rope rails, the sky brightening, "
    "the camera slowly drifting forward",
    "a close shot of the ship's wheel, brass worn bright, turning a little on its own, "
    "the camera holding still",
    "a wide shot looking straight up at the great canvas envelope overhead, clouds sliding "
    "past behind it, a slow tilt",
]
TAIL = (" The shots are connected: the same place, the same lighting and the same visual "
        "style across every cut.")


def prompts(asked):
    c1, c2 = int(asked[0]), int(asked[1])
    b = BEATS
    return {
        "A": " ".join("Shot %d: %s." % (i + 1, x) for i, x in enumerate(b)) + TAIL,
        "B": ("0-%ds: %s. %d-%ds: CUT to %s. %d-%ds: CUT to %s."
              % (c1, b[0], c1, c2, b[1], c2, SECONDS, b[2])) + TAIL,
        "C": ("0-%ds: %s. %d-%ds: %s. %d-%ds: %s."
              % (c1, b[0], c1, c2, b[1], c2, SECONDS, b[2])) + TAIL,
        "D": ("Shot 1: %s. CUT to Shot 2: %s. CUT to Shot 3: %s." % tuple(b)) + TAIL,
    }


NAMES = {"A": "A_ordinal", "B": "B_time+CUT", "C": "C_time_noCUT", "D": "D_ordinal+CUT"}


def render(prompt, seed, tag):
    wf = load_wf("51_ltx25_i2v.json")
    staged = "timecode_key.png"
    shutil.copy(KEY, os.path.join(COMFY, "input", staged))
    set_path(wf, "395.inputs.image", staged)
    set_path(wf, "376.inputs.value", prompt)
    set_path(wf, "383.inputs.value", False)          # no LLM expander: it would rewrite the ask
    set_path(wf, "362.inputs.value", int(SECONDS))
    set_path(wf, "403.inputs.aspect_ratio", MS.aspect_for(KEY))
    set_path(wf, "339.inputs.noise_seed", seed)
    set_path(wf, "338.inputs.noise_seed", seed)
    set_path(wf, "75.inputs.filename_prefix", "claude-generated/timecode/%s" % tag)
    _, outs = run(HOST, wf, quiet=True)
    for o in outs or []:
        if str(o).lower().endswith((".mp4", ".webm", ".mov")):
            src = os.path.join(COMFY, "output", o)
            if os.path.exists(src):
                dst = os.path.join(OUT, "%s.mp4" % tag)
                shutil.copy(src, dst)
                return dst
    return None


def soft(diffs, fps=8, k=2.5, run_len=3):
    """dissolves: runs of >= run_len sampled frames moderately above the clip's own baseline.
    Returns the centre time of each run.  A hard cut is one frame; a dissolve is a plateau."""
    if len(diffs) < run_len + 2:
        return []
    med = statistics.median(diffs)
    mad = statistics.median([abs(x - med) for x in diffs]) or 1e-6
    thr = med + k * mad
    hot = [x > thr for x in diffs]
    out, i = [], 0
    while i < len(hot):
        if hot[i]:
            j = i
            while j < len(hot) and hot[j]:
                j += 1
            if j - i >= run_len:
                out.append(round(((i + j) / 2.0 + 1) / fps, 2))
            i = j
        else:
            i += 1
    return out


def boundaries(clip):
    """every transition the clip contains, as (time, kind); hard cuts win a tie with a dissolve"""
    hard, diffs = MS.cuts(clip)
    dis = [t for t in soft(diffs) if not any(abs(t - h) < 0.8 for h in hard)]
    b = [(t, "cut") for t in hard] + [(t, "dissolve") for t in dis]
    return sorted(b), diffs


def nearest(times, asked):
    return [round(min(abs(t - a) for t in times), 2) if times else None for a in asked]


def strip(clip, dest, fps=1):
    """one frame a second, for looking"""
    from PIL import Image, ImageDraw
    d = dest + "_frames"
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    MS.sh("ffmpeg", "-y", "-v", "error", "-i", clip, "-vf", "fps=%d,scale=240:-2" % fps,
          os.path.join(d, "f%03d.png"))
    fs = sorted(os.path.join(d, f) for f in os.listdir(d))
    if not fs:
        return None
    w, h = Image.open(fs[0]).size
    sheet = Image.new("RGB", (w * len(fs), h + 14), (16, 16, 20))
    dr = ImageDraw.Draw(sheet)
    for i, f in enumerate(fs):
        sheet.paste(Image.open(f).convert("RGB"), (i * w, 14))
        dr.text((i * w + 3, 1), "t=%ds" % i, fill=(220, 220, 225))
    sheet.save(dest, quality=85)
    shutil.rmtree(d, ignore_errors=True)
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--cuts", nargs=2, type=float, default=None,
                    help="where the timecoded prompts put their boundaries (default 3 9); keep "
                         "both a second off the thirds grid or the test cannot tell listening "
                         "from luck")
    ap.add_argument("--variants", nargs="+", default=["A", "B", "C", "D"])
    a = ap.parse_args()
    asked = list(a.cuts) if a.cuts else ASKED
    thirds = [SECONDS / 3.0, 2 * SECONDS / 3.0]
    ps = prompts(asked)
    tagsuf = "_%d_%d" % (int(asked[0]), int(asked[1]))
    os.makedirs(OUT, exist_ok=True)
    seeds = [1234, 77, 4096][:max(1, min(a.seeds, 3))]
    rows = []
    for seed in seeds:
        for v in a.variants:
            label = NAMES[v]
            t0 = time.time()
            tag = "%s%s_%d" % (label, tagsuf, seed)
            clip = render(ps[v], seed, tag)
            if not clip:
                print("%s seed %d: NO OUTPUT" % (label, seed), flush=True)
                continue
            b, _ = boundaries(clip)
            times = [t for t, _ in b]
            strip(clip, os.path.join(OUT, tag + "_strip.jpg"))
            row = {"variant": v, "label": label, "seed": seed,
                   "clip": os.path.relpath(clip, STUDIO), "boundaries": b,
                   "asked": asked, "to_asked": nearest(times, asked),
                   "to_thirds": nearest(times, thirds),
                   "hard": sum(1 for _, k in b if k == "cut"),
                   "soft": sum(1 for _, k in b if k == "dissolve"),
                   "secs": round(time.time() - t0)}
            rows.append(row)
            print("%-14s seed %-5d %s | to asked%s %s | to thirds(4,8) %s"
                  % (label, seed, " ".join("%s@%.1f" % (k, t) for t, k in b) or "no boundary",
                     tuple(int(x) for x in asked), row["to_asked"], row["to_thirds"]),
                  flush=True)
    json.dump({"prompts": ps, "asked": asked, "seconds": SECONDS, "rows": rows},
              open(os.path.join(OUT, "timecode_test%s.json" % tagsuf), "w"), indent=1)
    print("TIMECODE DONE", flush=True)


if __name__ == "__main__":
    main()
