#!/usr/bin/env python3
"""Score every shot in a film on objective proxies for the things that make it unwatchable.

    python3 scripts/analyze_shots.py films/berserk.json
    python3 scripts/analyze_shots.py films/berserk.json --worst 20

Why this exists: quality was being judged by whatever happened to be measurable - loudness,
freeze frames, duration - none of which say whether a shot is any good. Meanwhile "the
shots barely move" went unmeasured for a whole film. These are cheap proxies that correlate
with real failure modes, so a bad shot gets caught at the shot level instead of after it is
baked into twenty minutes.

METRICS

  motion      mean frame-to-frame luma difference (ffmpeg signalstats YDIF).
              LOW = a still with a slow zoom, which is the single most common failure of
              image-to-video and reads as boring however pretty the frame is.
              HIGH is not automatically good - see `churn`.

  churn       standard deviation of that difference over time.
              Very high with high motion suggests morphing or flicker rather than coherent
              movement: real motion is fairly steady, hallucinated motion thrashes.

  frozen      seconds of literally static frames (freezedetect).
              Anything above zero is a still image in a film that is supposed to move.

  secs        shot duration. Long AND low-motion is the worst combination in the set -
              that is a held shot with nothing to hold on to.

  DEAD score  secs x (1 / motion). Ranks shots by how much screen time they waste.
              This is the list to fix first.

Read the output as a work list, not a verdict. The numbers find suspects; you still have to
look at the shot.
"""
import argparse, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# Default to the LOCAL install, matching epic.py and short.py. This used to default to
# "Z:/ComfyUI", which is only correct when driving the box from Windows over the SMB
# share. epic.py:50 reads COMFY_ROOT at import time, so ANY module that imported
# analyze_shots before epic silently got COMFY = a path that exists nowhere on Linux.
# Nothing raised: every exists()/glob() just returned empty, so renders succeeded and
# the tool reported its own output missing. That cost terra_wardrobe.py a 40-render
# pass. Set COMFY_ROOT explicitly to drive a remote/Windows instance.
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
# Default to the LOCAL ComfyUI. This used to hardcode 192.168.1.46, which broke
# when DHCP moved the box to .45, and which also sent every render request across
# a NIC measured dropping 10% of packets. Nothing here needs the network: these
# scripts run ON the box. Set COMFY_HOST to drive a remote instance.
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from epic import clip_parts, COMFY, dur   # noqa: E402


def motion(path):
    """(mean, stdev) of per-frame luma difference. Cheap and surprisingly discriminating."""
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", path, "-vf",
         "scale=320:-2,signalstats,metadata=print:key=lavfi.signalstats.YDIF",
         "-f", "null", "-"], capture_output=True, text=True)
    # NOTE: signalstats prints small values in scientific notation
    # (YDIF=8.87784e-05). [\d.]+ matched that as "8.87784", so a FROZEN clip
    # measured ~1.31 instead of ~0.001 - a 1300x overstatement, verified on a
    # still encoded to h264. That defeated this script's whole purpose: the DEAD
    # score is secs*(1/motion), so a dead shot scored LOW and never surfaced.
    vals = [float(m) for m in re.findall(r"YDIF=([-+0-9.eE]+)", r.stderr or "")]
    if not vals:
        return 0.0, 0.0
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    return mean, var ** 0.5


def frozen_seconds(path):
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", path, "-vf", "freezedetect=n=-60dB:d=0.5",
         "-map", "0:v", "-f", "null", "-"], capture_output=True, text=True)
    return sum(float(x) for x in
               re.findall(r"freeze_duration: ([\d.]+)", r.stderr or ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film")
    ap.add_argument("--worst", type=int, default=15)
    a = ap.parse_args()

    film = json.load(open(a.film, encoding="utf-8"))
    slug = film["title"].lower().replace(" ", "-")
    out = f"{COMFY}/output/claude-generated/11-short-film/{slug}"

    rows = []
    for s in film["shots"]:
        parts = [p for p in clip_parts(out, s) if os.path.exists(p)]
        if not parts:
            continue
        m = st = fz = 0.0
        secs = 0.0
        for p in parts:
            mm, ss = motion(p)
            d = dur(p)
            m += mm * d
            st += ss * d
            secs += d
            fz += frozen_seconds(p)
        m /= max(secs, 0.01)
        st /= max(secs, 0.01)
        rows.append({"id": s["id"], "secs": round(secs, 1), "motion": round(m, 2),
                     "churn": round(st, 2), "frozen": round(fz, 1),
                     "silent": not s.get("say"),
                     "dead": round(secs / max(m, 0.05), 1)})
        print(f"  {s['id']:24} {secs:5.1f}s  motion {m:6.2f}  churn {st:5.2f}"
              f"  frozen {fz:4.1f}", flush=True)

    if not rows:
        raise SystemExit("no clips found - has this film been rendered?")

    rows.sort(key=lambda r: -r["dead"])
    tot = sum(r["secs"] for r in rows)
    mm = sum(r["motion"] * r["secs"] for r in rows) / tot
    print(f"\n{'='*70}\n{len(rows)} shots, {tot/60:.1f} min, mean motion {mm:.2f}")
    print(f"frozen anywhere: {sum(1 for r in rows if r['frozen'] > 0)} shots, "
          f"{sum(r['frozen'] for r in rows):.1f}s total")
    low = [r for r in rows if r["motion"] < mm * 0.5]
    print(f"shots under half mean motion: {len(low)}  "
          f"({sum(r['secs'] for r in low)/tot*100:.0f}% of screen time)")

    print(f"\nDEADEST {a.worst} SHOTS (long + low motion = wasted screen time)")
    print(f"{'shot':24} {'secs':>6} {'motion':>7} {'churn':>6} {'dead':>7}  silent")
    for r in rows[:a.worst]:
        print(f"{r['id']:24} {r['secs']:6.1f} {r['motion']:7.2f} {r['churn']:6.2f} "
              f"{r['dead']:7.1f}  {'yes' if r['silent'] else ''}")

    p = f"{out}/shot_scores.json"
    json.dump(rows, open(p, "w"), indent=1)
    print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
