#!/usr/bin/env python3
"""How long does a face last, by what the shot asks the person to do?

Gathered from every take on the box that carries a hold curve.  The point is not the table
itself but what the builder does with it: a director who asks for eight seconds of a walk
toward the camera should be told, before anything renders, that the face has never survived
more than about four.

    python3 face_clock.py            # rebuild studio/face_clock.json from the films
"""
import json
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILMS = os.path.join(ROOT, "films")
OUT = os.path.join(ROOT, "face_clock.json")


def gather():
    rows = []
    for fid in sorted(os.listdir(FILMS)):
        fp = os.path.join(FILMS, fid, "film.json")
        if not os.path.exists(fp):
            continue
        try:
            film = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        for sid, sh in (film.get("shots") or {}).items():
            beats = sh.get("beats") or [{}]
            motion = (beats[0].get("motion") or "").strip().lower() or "still"
            framing = ((sh.get("anchor_source") or {}).get("framing") or "").lower() or "?"
            for t in sh.get("takes") or []:
                hc = ((t.get("identity") or {}).get("hold_curve") or {})
                if not hc or not hc.get("duration"):
                    continue
                rows.append({"film": fid, "shot": sid, "take": t["id"], "motion": motion,
                             "framing": framing, "duration": hc["duration"],
                             "holds": bool(hc.get("holds")),
                             "holds_until": hc.get("holds_until"),
                             "lost_at": hc.get("lost_at")})
    return rows


def table(rows):
    by = {}
    for r in rows:
        by.setdefault(r["motion"], []).append(r)
    out = {}
    for motion, rs in sorted(by.items()):
        lost = [r for r in rs if r["lost_at"] is not None]
        held = [r for r in rs if r["holds"]]
        holds_until = [r["holds_until"] for r in rs if r["holds_until"] is not None]
        out[motion] = {
            "takes": len(rs),
            "held_throughout": len(held),
            "lost_the_face": len(lost),
            "median_hold": round(statistics.median(holds_until), 2) if holds_until else None,
            "shortest_loss": round(min([r["lost_at"] for r in lost]), 2) if lost else None,
            "median_length": round(statistics.median([r["duration"] for r in rs]), 2),
            # the length at which three quarters of takes still held the face: a survival
            # number, so one unlucky take cannot speak for a whole motion
            "safe_seconds": _survives(rs, 0.75),
            "unfollowable": motion.replace(" ", "_") in HEAD_MOVERS,
        }
    return out


HEAD_MOVERS = {"crouch", "kneel", "sit", "sit_down", "bow", "lie", "lie_down",
               "stand_up", "fall", "duck", "pick_up"}


def _survives(rs, frac):
    """the longest T at which at least `frac` of these takes still held the face"""
    held = []
    for r in rs:
        if r["holds"]:
            held.append(r["duration"])
        elif r["holds_until"] is not None:
            held.append(r["holds_until"])
    if len(held) < 4:
        return None
    held.sort()
    i = int((1.0 - frac) * len(held))
    return round(held[min(i, len(held) - 1)], 1)


if __name__ == "__main__":
    rows = gather()
    t = table(rows)
    json.dump({"takes": len(rows), "by_motion": t}, open(OUT, "w", encoding="utf-8"), indent=1)
    print("A face is 'recognisable' while it stays inside the band where the studio can")
    print("still tell who it is - a wider line than the one the end verdict uses.")
    print("")
    print("%-12s %5s %6s %5s %9s %9s %8s" % ("motion", "takes", "recog", "lost", "med hold", "first loss", "advise"))
    for m, d in sorted(t.items(), key=lambda kv: -kv[1]["takes"]):
        print("%-12s %5d %6d %5d %9s %9s %8s" % (
            m[:12], d["takes"], d["held_throughout"], d["lost_the_face"],
            d["median_hold"] if d["median_hold"] is not None else "-",
            d["shortest_loss"] if d["shortest_loss"] is not None else "-",
            d["safe_seconds"] if d["safe_seconds"] is not None else "-"))
    print("\nwritten:", OUT)
