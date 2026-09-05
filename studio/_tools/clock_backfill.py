#!/usr/bin/env python3
"""Put a face clock on every take the studio has already made.

The hold curve arrived today, so only takes rendered since carry one and the table built
from them is too thin to advise from.  This measures the rest: nine points through each
clip with the head box carried through the camera as measured at that moment, stored on the
take, no renders and no GPU.

    python3 clock_backfill.py                     # every film, picked takes
    python3 clock_backfill.py --all builder-test  # every take of one film
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "_tools"))
import cammeasure as CM
import compose as C
from PIL import Image

PY = os.path.expanduser("~/ComfyUI/venv/bin/python")
FILMS = os.path.join(ROOT, "films")
BATCH = 12


def head_box(src):
    if src.get("framing") == "close":
        return [0.30, 0.03, 0.70, 0.60]
    try:
        p = C.plate_for(src["place"], src.get("plate") or None)
        if isinstance(p, tuple):
            p = p[0]
        im = Image.open(p).convert("RGB")
        W, H = im.size
        y, th, _ = C.place_by_depth(im, C.depth_for_plate(p), float(src.get("stand", 0.3)),
                                    float(src.get("cx", 0.45)))
        hw = th * 0.16
        cx = float(src.get("cx", 0.45)) * W
        return [(cx - hw * .75) / W, (y - th) / H, (cx + hw * .75) / W, (y - th + hw * 1.25) / H]
    except Exception:
        return None


def jobs_for(fid, every=False):
    fp = os.path.join(FILMS, fid, "film.json")
    if not os.path.exists(fp):
        return [], []
    film = json.load(open(fp, encoding="utf-8"))
    jobs, where = [], []
    for sid, sh in sorted(film["shots"].items()):
        src = sh.get("anchor_source") or {}
        cid = src.get("character")
        if not cid:
            continue
        portrait = os.path.join(ROOT, "foundry", "characters", cid, "base_portrait.png")
        if not os.path.exists(portrait):
            continue
        for t in sh.get("takes") or []:
            if not every and t["id"] != sh.get("picked"):
                continue
            if ((t.get("identity") or {}).get("hold_curve")):
                continue
            v = os.path.join(FILMS, fid, t.get("file") or "")
            if not t.get("file") or not os.path.exists(v):
                continue
            m = CM.measure(v, framing=src.get("framing"))
            cam = t.get("cam_measured") or {}
            post = cam.get("post") or {}
            jobs.append({"id": "%s|%s|%s" % (fid, sid, t["id"]), "portrait": portrait, "video": v,
                         "box": head_box(src), "close": src.get("framing") == "close",
                         "cam": {k: m.get(k) for k in ("zoom", "pan", "tilt")},
                         "window0": ({"zoom": post.get("zoom_start", 1.0), "cx": post.get("cx_start", 0.5),
                                      "cy": post.get("cy_start", 0.5)} if post else None),
                         "post_curve": post.get("window"), "curve": True, "cam_curve": m.get("curve")})
            where.append((fid, sid, t["id"]))
    return jobs, where


def run(jobs):
    jp = "/tmp/clock_backfill_jobs.json"
    json.dump(jobs, open(jp, "w"))
    p = subprocess.run([PY, os.path.join(ROOT, "_tools", "identity.py"), jp],
                       capture_output=True, text=True, cwd=os.path.expanduser("~/ComfyUI"))
    out = {}
    for line in p.stdout.splitlines():
        try:
            d = json.loads(line)
            out[d.get("id")] = d
        except Exception:
            pass
    if not out and p.returncode:
        print("   identity failed:", p.stderr[-200:].strip())
    return out


def store(fid, results):
    fp = os.path.join(FILMS, fid, "film.json")
    film = json.load(open(fp, encoding="utf-8"))
    n = 0
    for key, res in results.items():
        f2, sid, tid = key.split("|")
        if f2 != fid or not res or res.get("error") or not res.get("hold_curve"):
            continue
        sh = film["shots"].get(sid) or {}
        t = next((x for x in sh.get("takes") or [] if x["id"] == tid), None)
        if not t:
            continue
        ident = t.get("identity") or {}
        ident["hold_curve"] = res["hold_curve"]
        for k in ("start", "end", "verdict_start", "verdict_end"):
            if ident.get(k) is None and res.get(k) is not None:
                ident[k] = res[k]
        t["identity"] = ident
        n += 1
    if n:
        json.dump(film, open(fp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return n


if __name__ == "__main__":
    every = "--all" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    films = args or sorted(d for d in os.listdir(FILMS)
                           if os.path.exists(os.path.join(FILMS, d, "film.json")))
    total = 0
    for fid in films:
        jobs, where = jobs_for(fid, every)
        if not jobs:
            print("%-22s nothing to do" % fid, flush=True)
            continue
        t0 = time.time()
        done = 0
        for i in range(0, len(jobs), BATCH):
            res = run(jobs[i:i + BATCH])
            done += store(fid, res)
            print("   %s  %d/%d (%.0fs)" % (fid, min(i + BATCH, len(jobs)), len(jobs), time.time() - t0), flush=True)
        print("%-22s clocked %d of %d takes (%.0fs)" % (fid, done, len(jobs), time.time() - t0), flush=True)
        total += done
    print("\ntakes clocked:", total)
