#!/usr/bin/env python3
"""studio/_tools/engine_ab.py - put two video engines on the same keyframes and measure.

The project has routed exactly one video engine and every comparison so far has been an
anecdote: one clip, one prompt, one look. That is how LTX-2.5 got measured and it is how
the camera sweep produced four confident wrong answers. So this runs a MATRIX - every
keyframe through every engine at the same length, prompt and seed - and reports the four
numbers side by side plus a contact strip per clip, because the standing rule is that
video is judged by watching and the numbers only say where to look.

    python3 studio/_tools/engine_ab.py --out ~/shared/AB/hunyuan_vs_ltx
    python3 studio/_tools/engine_ab.py --engines hunyuan,ltx23 --frames 49

WHAT THE COLUMNS MEAN (clipmetrics owns the definitions):

    hold_f0     did the engine repaint the frame you approved
    drift       did the picture walk away from it - the film pipeline's real cost
    motion      is anything actually moving; ~0 means it froze
    evenness    mean step / max step. LOW is the "non fluid, jerky" complaint made
                numeric: 0.33 means one frame lurches three times the average.
    secs        wall clock, which is a quality of its own at 20 shots a film

An engine wins a keyframe on drift and evenness together. Neither alone is enough: a
frozen clip has perfect drift, and a clip that dissolves into noise has even motion.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
COMFY_OUT = os.path.expanduser("~/ComfyUI/output")
COMFY_IN = os.path.expanduser("~/ComfyUI/input")

# Each engine says which workflow to run and which dotted paths carry the four dials.
# Anything an engine does not have (LTX's audio latent) is set only when present.
ENGINES = {
    "hunyuan": {
        "wf": "workflows/42_hunyuan_i2v.json",
        "image": "8.inputs.image", "text": "10.inputs.text",
        "seed": "32.inputs.noise_seed", "prefix": "42.inputs.filename_prefix",
        "size": ("20.inputs.width", "20.inputs.height"), "length": ["20.inputs.length"],
        "quantum": 4,      # length must be 4n+1
        "label": "HunyuanVideo 1.5 720p i2v",
    },
    "ltx23": {
        "wf": "workflows/12_ltx23_i2v_audio.json",
        "image": "8.inputs.image", "text": "10.inputs.text",
        "seed": "32.inputs.noise_seed", "prefix": "43.inputs.filename_prefix",
        "size": ("20.inputs.width", "20.inputs.height"),
        "length": ["20.inputs.length", "21.inputs.frames_number"],
        "quantum": 8,      # length must be 8n+1
        "label": "LTX-2.3 22B i2v",
    },
}

# The shot types an ad is actually cut from. Deliberately not one flattering example:
# the complaint that started this was that the ads moved in repetitive lurches, and
# that shows up on hands and on product inserts differently.
#
# EVERY PROMPT NAMES ONLY WHAT IS IN THE PICTURE. The first version of this list was
# chosen by filename and two of the four keyframes did not contain their subject - an
# empty anime sky asked to show a person walking, an empty arena asked to show players.
# Both engines then spent the clip inventing a subject, which measures nothing. If you
# add a shot here, open the keyframe and look at it first.
SHOTS = [
    ("water", "short_06_water.png",
     "a running shoe splashes through shallow water, droplets scatter, sunlit meadow"),
    ("laces", "short_05_laces.png",
     "the fingers pull the bootlace tight, hands move, low golden sunlight"),
    ("hand", "short_07_hand.png",
     "the hand slides the notebook forward across the white table"),
    ("arena", "short_07_goal_00.png",
     "the arena lights flicker and the empty stands recede, slow forward drift"),
]


def sh(*a, **kw):
    return subprocess.run(a, capture_output=True, text=True, **kw)


def snap(want, quantum):
    """Nearest valid length at or below `want` for an engine's temporal compression."""
    n = (want - 1) // quantum
    return max(quantum + 1, n * quantum + 1)


def render(eng, key, text, seed, frames, width, height, prefix):
    """Queue one clip and return (seconds, absolute path) or (seconds, None)."""
    e = ENGINES[eng]
    cmd = [sys.executable, os.path.join(ROOT, "scripts", "comfy.py"), "run",
           os.path.join(ROOT, e["wf"]),
           "-s", "%s=%s" % (e["image"], key),
           "-s", "%s=%s" % (e["text"], text),
           "-s", "%s=%d" % (e["seed"], seed),
           "-s", "%s=%s" % (e["prefix"], prefix),
           "-s", "%s=%d" % (e["size"][0], width),
           "-s", "%s=%d" % (e["size"][1], height)]
    for path in e["length"]:
        cmd += ["-s", "%s=%d" % (path, snap(frames, e["quantum"]))]

    t0 = time.time()
    r = sh(*cmd, cwd=ROOT)
    secs = time.time() - t0
    m = re.search(r"-> (\S+\.mp4)", r.stdout or "")
    if not m:
        # the failure is the result too - print it rather than returning a silent None
        print("      FAILED: %s" % ((r.stderr or r.stdout or "").strip()[-300:]))
        return secs, None
    return secs, os.path.join(COMFY_OUT, m.group(1))


def measure(clip, key):
    r = sh(sys.executable, os.path.join(HERE, "clipmetrics.py"), clip,
           "--key", os.path.join(COMFY_IN, key))
    out = {}
    for tok in (r.stdout or "").split():
        k, _, v = tok.partition("=")
        try:
            out[k] = float(v)
        except ValueError:
            pass
    return out


def strip(clip, dest, n=6):
    """A contact strip, because the numbers only say where to look."""
    d = sh("ffprobe", "-v", "error", "-select_streams", "v:0",
           "-show_entries", "format=duration", "-of", "csv=p=0", clip)
    try:
        dur = float((d.stdout or "0").strip())
    except ValueError:
        return None
    step = max(dur / n, 0.01)
    sh("ffmpeg", "-y", "-v", "error", "-i", clip, "-vf",
       "fps=1/%.4f,scale=320:-2,tile=%dx1" % (step, n), "-frames:v", "1", dest)
    return dest if os.path.exists(dest) else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--engines", default="hunyuan,ltx23")
    p.add_argument("--frames", type=int, default=49)
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=704)
    p.add_argument("--seed", type=int, default=7701)
    p.add_argument("--shots", default="", help="comma-separated shot ids; default all")
    p.add_argument("--out", default=os.path.expanduser("~/shared/AB/engine_ab"))
    a = p.parse_args()

    engines = [e for e in a.engines.split(",") if e in ENGINES]
    want = set(x for x in a.shots.split(",") if x)
    shots = [s for s in SHOTS if not want or s[0] in want]
    os.makedirs(a.out, exist_ok=True)

    rows = []
    for sid, key, text in shots:
        if not os.path.exists(os.path.join(COMFY_IN, key)):
            print("  no keyframe: %s" % key)
            continue
        for eng in engines:
            print("  %-8s %-9s rendering" % (sid, eng), flush=True)
            secs, clip = render(eng, key, text, a.seed, a.frames,
                                a.width, a.height, "claude-generated/ab_%s_%s" % (sid, eng))
            if not clip or not os.path.exists(clip):
                rows.append({"shot": sid, "engine": eng, "secs": round(secs, 1),
                             "ok": False})
                continue
            keep = os.path.join(a.out, "%s_%s.mp4" % (sid, eng))
            sh("cp", clip, keep)
            m = measure(keep, key)
            strip(keep, os.path.join(a.out, "%s_%s.jpg" % (sid, eng)))
            row = {"shot": sid, "engine": eng, "secs": round(secs, 1), "ok": True,
                   "hold_f0": m.get("hold_f0"), "drift": m.get("drift"),
                   "motion": m.get("motion"),
                   "evenness": m.get("motion_evenness"),
                   "motion_max": m.get("motion_max"),
                   "luma": m.get("luma"), "luma_drop": m.get("luma_drop"),
                   "clip": keep}
            rows.append(row)
            # print from the row, not from a second lookup with different key names -
            # the two disagreed for a whole run and the live line reported 0.000
            print("      hold_f0=%s drift=%s motion=%s evenness=%s luma_drop=%s  %.0fs"
                  % tuple(["%.3f" % row[k] if row.get(k) is not None else "  --"
                           for k in ("hold_f0", "drift", "motion", "evenness",
                                     "luma_drop")] + [secs]))

    json.dump(rows, open(os.path.join(a.out, "results.json"), "w"), indent=1)

    print("\n%-9s %-9s %8s %8s %8s %9s %10s %7s" %
          ("shot", "engine", "hold_f0", "drift", "motion", "evenness", "luma_drop",
           "secs"))
    for r in rows:
        if not r.get("ok"):
            print("%-9s %-9s   FAILED after %ss" % (r["shot"], r["engine"], r["secs"]))
            continue
        print("%-9s %-9s %8.3f %8.3f %8.2f %9.3f %10.4f %7.0f" %
              (r["shot"], r["engine"], r["hold_f0"], r["drift"], r["motion"],
               r["evenness"], r.get("luma_drop") or 0.0, r["secs"]))

    # per-engine means, and the head-to-head count that decides a route
    print()
    for eng in engines:
        got = [r for r in rows if r["engine"] == eng and r.get("ok")]
        if not got:
            continue
        n = len(got)
        print("%-9s n=%d  drift %.3f  evenness %.3f  motion %.2f  luma_drop %+.4f  "
              "%.0fs/clip" %
              (eng, n, sum(r["drift"] for r in got) / n,
               sum(r["evenness"] for r in got) / n,
               sum(r["motion"] for r in got) / n,
               sum(r.get("luma_drop") or 0.0 for r in got) / n,
               sum(r["secs"] for r in got) / n))

    if len(engines) == 2:
        a_, b_ = engines
        wins = {a_: 0, b_: 0}
        for sid, _k, _t in shots:
            ra = next((r for r in rows if r["shot"] == sid and r["engine"] == a_
                       and r.get("ok")), None)
            rb = next((r for r in rows if r["shot"] == sid and r["engine"] == b_
                       and r.get("ok")), None)
            if not ra or not rb:
                continue
            # lower drift AND higher evenness, or it is not a win
            if ra["drift"] < rb["drift"] and ra["evenness"] > rb["evenness"]:
                wins[a_] += 1
            elif rb["drift"] < ra["drift"] and rb["evenness"] > ra["evenness"]:
                wins[b_] += 1
        print("\nclean wins (lower drift AND higher evenness): %s %d, %s %d, split %d"
              % (a_, wins[a_], b_, wins[b_], len(shots) - wins[a_] - wins[b_]))
    print("\nstrips + clips: %s" % a.out)


if __name__ == "__main__":
    main()
