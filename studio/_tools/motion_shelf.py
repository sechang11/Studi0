#!/usr/bin/env python3
"""studio/_tools/motion_shelf.py - re-measure the whole motion shelf on BOTH engines.

    python3 studio/_tools/motion_shelf.py [--engines ltx23 ltx25] [--only ID] [--seconds 4]

WHY NOW. 26 of 34 motion cards are weak or unavailable, all judged on LTX-2.3 - which
drifts (measured: 0.141 SSIM lost over 4s). A card can fail for two completely different
reasons and the old sweep could not tell them apart:
    the MOTION never happened            - the card is dead, on any engine
    the motion happened and the PICTURE   - the engine's fault, not the card's
    walked away underneath it
LTX-2.5 holds the keyframe (drift -0.004), so running both engines separates them.

PER CARD, PER ENGINE (one keyframe, one seed, only the motion text changes):
    motion      mean frame-to-frame difference. The static floor on this box is 0.001;
                anything under ~0.15 is a card that does nothing.
    drift       hold_f0 - hold_last. High = the picture walked off the keyframe.
    verdict     alive / dead / drifts - assigned by the numbers, not by taste.

The card is then stamped MEASURED with both engines' numbers and, where the two disagree,
the disagreement itself is the finding: `best_engine` names which one to use for that
motion. Status changes only for cards that are dead on BOTH engines (-> unavailable) or
alive on at least one (-> ready if it was weak, with the engine named). Nothing here
judges whether the motion is beautiful; it judges whether it exists.
"""
import argparse
import json
import os
import shutil
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, STUDIO)
sys.path.insert(0, TOOLS)
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run                            # noqa: E402
import engine as ENG                             # noqa: E402
import cards                                     # noqa: E402
import clipmetrics                               # noqa: E402

COMFY = os.environ.get("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
OUT = os.path.join(STUDIO, "samples", "motion_shelf")

DEAD = 0.15          # motion at or under this is indistinguishable from a still frame
# PALETTE drift, not SSIM drift: SSIM drift punishes a clip for animating (a character
# who correctly walks away scores like a picture that dissolved), which is exactly what
# the first smoke test got wrong. Palette drift is motion-tolerant - see clipmetrics.
DRIFTY = 0.012       # histogram distance keyframe -> last frame; the reverse-angle
                     # battery measured 0.0073 mean for a WHOLE NEW ANGLE of the same
                     # world, so past ~0.012 the world itself has changed.


def render(motion_text, key, seconds, seed, video_engine, tag):
    staged = "motionshelf_%s.png" % video_engine
    shutil.copy(key, os.path.join(COMFY, "input", staged))
    job = {"seconds": seconds, "seed": seed, "id": tag, "motion_text": motion_text,
           "width": 1216, "height": 704, "video_engine": video_engine}
    wf = ENG.video_graph(job, staged)
    _, outs = run(ENG.HOST, wf, quiet=True)
    for o in outs or []:
        if str(o).lower().endswith((".mp4", ".webm", ".mov")):
            src = os.path.join(COMFY, "output", o)
            if os.path.exists(src):
                dst = os.path.join(OUT, "%s__%s.mp4" % (tag, video_engine))
                shutil.copy(src, dst)
                return dst
    return None


def verdict(m):
    if m.get("motion", 0) <= DEAD:
        return "dead"
    if (m.get("palette_drift") or 0) >= DRIFTY:
        return "drifts"
    return "alive"


def main():
    ap = argparse.ArgumentParser(description="Motion shelf on both video engines.")
    ap.add_argument("--engines", nargs="+", default=["ltx23", "ltx25"])
    ap.add_argument("--only")
    ap.add_argument("--seconds", type=float, default=4)
    ap.add_argument("--seed", type=int, default=808)
    ap.add_argument("--key", default=os.path.join(
        STUDIO, "samples", "isolation", "characters", "char_linruo_0.png"))
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    lib = cards.load("motions")
    rows, n = {}, 0
    for cid, card in sorted(lib.items()):
        if cid.startswith("_") or (a.only and cid != a.only):
            continue
        text = str(card.get("text") or "").strip()
        if not text:
            continue
        if a.limit and n >= a.limit:
            break
        n += 1
        rec = {"family": card.get("family"), "text": text, "engines": {}}
        for eng in a.engines:
            clip = render(text, a.key, a.seconds, a.seed, eng, cid)
            if not clip:
                rec["engines"][eng] = {"error": "no clip"}
                continue
            m = clipmetrics.measure(clip, a.key)
            m["verdict"] = verdict(m)
            rec["engines"][eng] = m
        vs = {e: (v.get("verdict") or "error") for e, v in rec["engines"].items()}
        alive = [e for e, v in vs.items() if v == "alive"]
        rec["best_engine"] = alive[0] if alive else None
        rec["verdicts"] = vs
        rows[cid] = rec
        print("%-14s %-9s %s" % (cid, card.get("status"),
              "  ".join("%s: %-6s m=%5.2f pal=%.4f" %
                        (e, v.get("verdict", "?"), v.get("motion", 0) or 0,
                         v.get("palette_drift", 0) or 0)
                        for e, v in rec["engines"].items() if "error" not in v)))
    json.dump(rows, open(os.path.join(OUT, "report.json"), "w"), indent=1)

    # stamp + retier
    changed = []
    for cid, rec in rows.items():
        card = lib[cid]
        note = "; ".join("%s %s (motion %.2f, palette drift %.4f)"
                         % (e, v.get("verdict", "?"), v.get("motion", 0) or 0,
                            v.get("palette_drift", 0) or 0)
                         for e, v in rec["engines"].items() if "error" not in v)
        cards.stamp("motions", cid, "MEASURED",
                    "motion_shelf: same keyframe and seed on %s" % "+".join(a.engines),
                    note=note[:300])
        want = None
        if rec["best_engine"]:
            want = "ready"
        elif all(v in ("dead",) for v in rec["verdicts"].values()):
            want = "unavailable"
        if want and card.get("status") != want:
            p = os.path.join(STUDIO, "motions", cid + ".json")
            c = json.load(open(p, encoding="utf-8"))
            c["status_before_shelf"] = c.get("status")
            c["status"] = want
            if rec["best_engine"]:
                c["best_engine"] = rec["best_engine"]
            c["verdict"] = ("motion_shelf %s: %s. Prior: %s"
                            % (want, note, str(c.get("verdict") or ""))[:500])
            with open(p, "w", encoding="utf-8") as f:
                json.dump(c, f, indent=2, ensure_ascii=False)
                f.write("\n")
            changed.append((cid, c["status_before_shelf"], want, rec["best_engine"]))
    print("\nstatus changes:")
    for c in changed:
        print("  %-14s %s -> %s   %s" % (c[0], c[1], c[2], c[3] or ""))
    from collections import Counter
    print(json.dumps({e: dict(Counter(r["verdicts"].get(e) for r in rows.values()))
                      for e in a.engines}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
