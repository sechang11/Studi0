#!/usr/bin/env python3
"""studio/_tools/set_measure.py - does a shot stay in the place? Measured against the set, not by eye.

A set (previz_blender.py --scene set) knows, for every shot, which pixels are which SURFACE - the cafe's
ochre wall, its awning's red stripes, the tower's stone, the sky - from its ID masks (masks/s_NNNN.png,
and masks/m_NNNN.png for whole landmarks). So every start frame and every take of the shot, made from
the set or made some other way, can be scored on two things:

  FIT        how much of the picture's colour the set's map of surfaces explains: 1 - (the colour
             variance left inside each surface / the picture's whole colour variance), in CIELAB at
             320 px wide. When the geometry lands where the set says, every surface is one material and
             the map explains most of the picture; when a building has moved, the map cuts across it.
             Texture lowers every score alike. "chance" is the same picture under the OTHER shots' maps
             - what a picture of the same town seen from somewhere else scores.
  APPEARANCE the mean colour (CIELAB) of each key surface where the set says it is, against the same
             surface in the plate (dE vs plate), and its spread across shots (the largest dE between two
             shots that show it).

A take is scored at the frames the masks were rendered for (every 8th), matched by time; "hold" is the
fit at its last frame over the fit at its first.

    python3 studio/_tools/set_measure.py --truth plaza-set --arms plaza-set plaza-words
        -> studio/samples/fight/<truth>/measure.json, boards in .../measure/
"""
import argparse
import glob
import json
import os
import re

import cv2
import numpy as np
from PIL import Image, ImageDraw
from skimage.color import deltaE_ciede2000, rgb2lab

ROOT = os.path.expanduser("~/shared/comfy-studio")
FIGHT = os.path.join(ROOT, "studio", "samples", "fight")
W, H = 1280, 704
SW, SH, STEP = 320, 176, 4
# the surfaces whose colour says "the same building": walls, roofs, the tower, the awning, the water, the tree
KEY_SURFACES = ["tower/stone", "tower/copper", "tower/clock", "fountain/stone", "fountain/water", "cafe/cafe",
                "cafe/awning_red", "cafe/sign", "hall/hall", "hall/roof", "yellow/yellow", "yellow/shutter_green",
                "white/white", "white/shutter_blue", "pink/pink", "bakery/bakery", "arch/stone", "tree/leaf",
                "ground/paving",
                # things added to the square, and a character standing in it (set_plaza_market, --figure-name)
                "stall/canopy_yellow", "bicycle/bike_red", "pots/terracotta", "terra/figure"]


def to704(im):
    """Any start frame or take frame on the 1280x704 canvas the set rendered: a 1280x720 frame loses its
    top and bottom 8 rows (with the lens fitted to the width, 704 is exactly the middle of 720)."""
    im = im.convert("RGB")
    if im.width != W:
        im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
    if im.height != H:
        t = (im.height - H) // 2
        im = im.crop((0, t, W, t + H)) if t >= 0 else im.resize((W, H), Image.LANCZOS)
    return im


def decode(png, palette):
    """An ID-colour mask -> (labels, names): label i is palette name i, -1 the sky (black)."""
    names = list(palette)
    m = np.asarray(Image.open(png).convert("RGB")).astype(np.int32)
    pal = np.array([palette[n] for n in names], dtype=np.int32)
    lab = np.full(m.shape[:2], -1, np.int32)
    flat = m.reshape(-1, 3)
    best = np.full(flat.shape[0], 1 << 30, np.int64)
    idx = np.full(flat.shape[0], -1, np.int32)
    for i, c in enumerate(pal):                      # nearest colour, one palette entry at a time (memory)
        d = ((flat - c) ** 2).sum(1)
        better = d < best
        best[better] = d[better]
        idx[better] = i
    idx[flat.sum(1) < 30] = -1
    lab.reshape(-1)[:] = idx
    return lab, names


def fit(im, labels):
    """1 - within-surface colour variance / total colour variance (CIELAB, 320x176)."""
    small = cv2.resize(np.asarray(im), (SW, SH), interpolation=cv2.INTER_AREA)
    X = rgb2lab(small.astype(np.float32) / 255.0).reshape(-1, 3).astype(np.float64)
    L = labels[STEP // 2::STEP, STEP // 2::STEP][:SH, :SW].reshape(-1) + 1        # sky -> 0
    n = np.bincount(L)
    keep = n > 0
    within = 0.0
    for c in range(3):
        s1 = np.bincount(L, weights=X[:, c])[keep]
        s2 = np.bincount(L, weights=X[:, c] ** 2)[keep]
        within += float((s2 - s1 ** 2 / n[keep]).sum())
    total = float(((X - X.mean(0)) ** 2).sum())
    return round(1.0 - within / total, 3) if total else 0.0


def de(a, b):
    return float(deltaE_ciede2000(np.asarray(a)[None, None, :], np.asarray(b)[None, None, :])[0, 0])


def surface_colours(im, labels, names, want=KEY_SURFACES, erode=3, min_px=500):
    lab = rgb2lab(np.asarray(im).astype(np.float32) / 255.0)
    k = np.ones((2 * erode + 1, 2 * erode + 1), np.uint8)
    out = {}
    for n in want:
        if n not in names:
            continue
        mk = cv2.erode((labels == names.index(n)).astype(np.uint8), k) > 0
        if mk.sum() >= min_px:
            out[n] = lab[mk].mean(0)
    return out


def video_frames(path, rel):
    """Frames of a video at relative times 0..1 (first frame = 0, last = 1)."""
    cap = cv2.VideoCapture(path)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    out = []
    for t in rel:
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(n - 1, max(0, round(t * (n - 1)))))
        ok, fr = cap.read()
        out.append(Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)) if ok else None)
    cap.release()
    return out, n


class Truth:
    """The set's side of a shot: its render and its ID masks at every mask frame."""

    def __init__(self, truth_seq, sid):
        self.sid = sid
        self.dir = os.path.join(FIGHT, truth_seq, "previz_%s" % sid)
        info = json.load(open(os.path.join(self.dir, "previz.json")))
        self.frames = info["frames"]
        self.groups = {k: tuple(v) for k, v in info.get("groups", {}).items()}
        self.surfaces = {k: tuple(v) for k, v in info.get("surfaces", {}).items()}
        self.landmarks = info.get("landmarks", [])
        self.mask_frames = info.get("mask_frames") or [1]
        self.rel = [(f - 1) / max(1, self.frames - 1) for f in self.mask_frames]
        self._cache = {}

    def render(self, f):
        return Image.open(os.path.join(self.dir, "frames", "f_%04d.png" % f)).convert("RGB")

    def surf(self, f):
        if ("s", f) not in self._cache:
            self._cache[("s", f)] = decode(os.path.join(self.dir, "masks", "s_%04d.png" % f), self.surfaces)
        return self._cache[("s", f)]

    def groups_at(self, f):
        if ("m", f) not in self._cache:
            self._cache[("m", f)] = decode(os.path.join(self.dir, "masks", "m_%04d.png" % f), self.groups)
        return self._cache[("m", f)]


def score_image(truth, f, im, plate_cols, others=()):
    im = to704(im)
    labels, names = truth.surf(f)
    g = {"fit": fit(im, labels)}
    if others:
        g["chance"] = round(float(np.mean([fit(im, o.surf(1)[0]) for o in others])), 3)
    cols = surface_colours(im, labels, names)
    g["dE_plate"] = {n: round(de(c, plate_cols[n]), 1) for n, c in cols.items() if n in plate_cols}
    g["dE_plate_mean"] = round(float(np.mean(list(g["dE_plate"].values()))), 1) if g["dE_plate"] else None
    return g, cols


def plate_colours(truth_seq, plate_png, first_shot):
    """The key surfaces' colours in the plate - or, for a scene whose start frames were composed by
    set_test.py cast and never had a plate, in its first shot's start frame."""
    t = Truth(truth_seq, first_shot)
    labels, names = t.surf(1)
    if not os.path.exists(plate_png):
        plate_png = os.path.join(FIGHT, truth_seq, "anchor_%s.png" % first_shot)
    return surface_colours(to704(Image.open(plate_png)), labels, names)


def spread(per_shot):
    """surface -> the largest dE between two shots that show it."""
    out = {}
    for n in sorted(set(n for c in per_shot.values() for n in c)):
        vals = [c[n] for c in per_shot.values() if n in c]
        if len(vals) >= 2:
            out[n] = round(max(de(a, b) for i, a in enumerate(vals) for b in vals[i + 1:]), 1)
    return out


def takes_of(arm_dir, sid):
    """Every take a shot has in an arm, in the order it was GENERATED (pv_ drawn from the set with a start
    frame, pvb_ from the set's depth alone, pve_ pinned at both ends, shot_ / h3_ prompted); the reversed
    copies (pvr_, pver_) are skipped."""
    out = []
    for pat in ("pv_%s_s*.mp4", "pvb_%s_s*.mp4", "pve_%s_s*.mp4", "shot_%s_s*.mp4", "h3_%s_s*.mp4"):
        out += [p for p in sorted(glob.glob(os.path.join(arm_dir, pat % sid))) if re.search(r"_s\d+\.mp4$", p)]
    return out


def _script(seq):
    return json.load(open(os.path.join(ROOT, "studio", "shotscripts", seq + ".json")))


def reversed_against(truth_shot, arm_shot):
    """True when the arm's take runs the other way from the set's render: the set drew the move backwards
    ("reverse": the film plays it forwards) and the arm prompted it the way the film plays it."""
    return bool((truth_shot.get("previz") or {}).get("reverse")) and arm_shot.get("engine") != "previz"


def measure(truth_seq, arms):
    seq = _script(truth_seq)
    tshots = {s["id"]: s for s in seq["shots"]}
    shots = [s["id"] for s in seq["shots"]]
    truths = {sid: Truth(truth_seq, sid) for sid in shots}
    plate = os.path.join(FIGHT, truth_seq, "ref_%s.png" % seq["place"]["id"])
    pcols = plate_colours(truth_seq, plate, shots[0])
    rep = {"truth": truth_seq, "plate": os.path.relpath(plate, ROOT), "plate_surfaces": sorted(pcols),
           "self_fit": {sid: fit(truths[sid].render(1), truths[sid].surf(1)[0]) for sid in shots}, "arms": {}}
    for arm in arms:
        adir = os.path.join(FIGHT, arm)
        ashots = {s["id"]: s for s in _script(arm)["shots"]}
        A = {"shots": {}}
        start_cols = {}
        for sid in shots:
            tr = truths[sid]
            rev = reversed_against(tshots[sid], ashots.get(sid, {}))
            f0 = tr.frames if rev else 1                 # the set's frame this arm's start frame shows
            others = [truths[o] for o in shots if o != sid]
            row = {"takes": {}, "reversed": rev}
            sp = os.path.join(adir, "anchor_%s.png" % sid)
            if os.path.exists(sp):
                g, cols = score_image(tr, f0, Image.open(sp), pcols, others)
                row["start"] = g
                start_cols[sid] = cols
            # generation time t -> the set's frame at t, or at 1 - t when the arm runs the other way
            pairs = list(zip(reversed(tr.mask_frames) if rev else tr.mask_frames, tr.rel))
            for tp in takes_of(adir, sid):
                frames, n = video_frames(tp, [t for _, t in pairs])
                per = []
                for (f, _), im in zip(pairs, frames):
                    if im is not None:
                        g, _ = score_image(tr, f, im, pcols)
                        per.append({"f": f, "fit": g["fit"], "dE_plate_mean": g["dE_plate_mean"]})
                if not per:
                    continue
                fs = [p["fit"] for p in per]
                dEs = [p["dE_plate_mean"] for p in per if p["dE_plate_mean"] is not None]
                row["takes"][os.path.basename(tp)] = {
                    "frames": n, "fit_first": fs[0], "fit_last": fs[-1], "fit_mean": round(float(np.mean(fs)), 3),
                    "fit_min": round(float(np.min(fs)), 3), "hold": round(fs[-1] / fs[0], 2) if fs[0] > 0 else None,
                    "dE_mean": round(float(np.mean(dEs)), 1) if dEs else None, "per_frame": per}
            A["shots"][sid] = row
        A["start_spread"] = spread(start_cols)
        st = [r["start"] for r in A["shots"].values() if "start" in r]
        tk = [t for r in A["shots"].values() for t in r["takes"].values()]
        A["summary"] = {
            "start_fit_mean": round(float(np.mean([s["fit"] for s in st])), 3) if st else None,
            "start_chance_mean": round(float(np.mean([s["chance"] for s in st])), 3) if st else None,
            "start_dE_plate_mean": round(float(np.mean([s["dE_plate_mean"] for s in st
                                                        if s["dE_plate_mean"] is not None])), 1) if st else None,
            "start_spread_mean": round(float(np.mean(list(A["start_spread"].values()))), 1) if A["start_spread"] else None,
            "take_fit_mean": round(float(np.mean([t["fit_mean"] for t in tk])), 3) if tk else None,
            "take_hold_mean": round(float(np.mean([t["hold"] for t in tk if t["hold"]])), 2) if tk else None,
        }
        rep["arms"][arm] = A
    return rep


# ---------------------------------------------------------------- boards
def _label(dr, xy, text):
    x, y = xy
    dr.rectangle([x, y, x + 7 * len(text) + 8, y + 16], fill=(0, 0, 0))
    dr.text((x + 4, y + 2), text, fill=(240, 240, 240))


def overlay(labels, im):
    """The picture in grey with the set's surface borders over it in red: where a border misses the
    picture's own edge, the geometry moved."""
    im = to704(im)
    g = np.asarray(im.convert("L").convert("RGB")).astype(np.float32) * 0.8
    b = np.zeros(labels.shape, bool)
    b[:, 1:] |= labels[:, 1:] != labels[:, :-1]
    b[1:, :] |= labels[1:, :] != labels[:-1, :]
    b = cv2.dilate(b.astype(np.uint8), np.ones((2, 2), np.uint8)) > 0
    g[b] = (255, 40, 40)
    return Image.fromarray(g.astype(np.uint8))


def board_starts(truth_seq, arms, rep, dst, tw=426):
    seq = _script(truth_seq)
    ashots = {arm: {s["id"]: s for s in _script(arm)["shots"]} for arm in arms}
    th = round(tw * H / W)
    cols = 1 + 2 * len(arms)
    sheet = Image.new("RGB", (cols * (tw + 6) + 6, len(seq["shots"]) * (th + 6) + 30), (16, 16, 20))
    dr = ImageDraw.Draw(sheet)
    heads = ["the set's render"] + sum([[arm + ": start frame", arm + ": the set's borders over it"] for arm in arms], [])
    for c, h in enumerate(heads):
        dr.text((6 + c * (tw + 6) + 4, 8), h, fill=(200, 200, 210))
    for r, s in enumerate(seq["shots"]):
        sid = s["id"]
        tr = Truth(truth_seq, sid)
        y = 26 + r * (th + 6)
        sheet.paste(tr.render(1).resize((tw, th)), (6, y))
        _label(dr, (6, y), "%s %s" % (sid, s["name"]))
        for a, arm in enumerate(arms):
            sp = os.path.join(FIGHT, arm, "anchor_%s.png" % sid)
            if not os.path.exists(sp):
                continue
            im = Image.open(sp)
            f0 = tr.frames if reversed_against(s, ashots[arm].get(sid, {})) else 1
            x = 6 + (1 + 2 * a) * (tw + 6)
            sheet.paste(to704(im).resize((tw, th)), (x, y))
            sheet.paste(overlay(tr.surf(f0)[0], im).resize((tw, th)), (x + tw + 6, y))
            st = rep["arms"][arm]["shots"][sid].get("start") or {}
            _label(dr, (x + tw + 6, y), "fit %.2f (chance %.2f)  dE %s" % (st.get("fit", 0), st.get("chance", 0),
                                                                          st.get("dE_plate_mean")))
    sheet.save(dst, quality=88)


def board_takes(truth_seq, arms, picks, dst, tw=300):
    """Each shot's picked take in each arm at its first, middle and last frame, beside the set's render."""
    seq = json.load(open(os.path.join(ROOT, "studio", "shotscripts", truth_seq + ".json")))
    th = round(tw * H / W)
    groups = 1 + len(arms)
    sheet = Image.new("RGB", (groups * 3 * (tw + 4) + groups * 8 + 6, len(seq["shots"]) * (th + 4) + 30), (16, 16, 20))
    dr = ImageDraw.Draw(sheet)
    for g, name in enumerate(["the set's render"] + list(arms)):
        dr.text((6 + g * (3 * (tw + 4) + 8) + 4, 8), name + ": first | middle | last", fill=(200, 200, 210))
    for r, s in enumerate(seq["shots"]):
        sid = s["id"]
        tr = Truth(truth_seq, sid)
        y = 26 + r * (th + 4)
        row = [("set", [tr.render(f) for f in (1, tr.frames // 2 + 1, tr.frames)])]
        for arm in arms:
            p = (picks.get(arm) or {}).get(sid)
            if p and os.path.exists(os.path.join(FIGHT, arm, p)):
                row.append((p, video_frames(os.path.join(FIGHT, arm, p), [0.0, 0.5, 1.0])[0]))
            else:
                row.append(("", []))
        for g, (name, ims) in enumerate(row):
            x0 = 6 + g * (3 * (tw + 4) + 8)
            for k, im in enumerate(ims):
                if im is not None:
                    sheet.paste(to704(im).resize((tw, th)), (x0 + k * (tw + 4), y))
            if name:
                _label(dr, (x0, y), "%s %s" % (sid, name))
    sheet.save(dst, quality=86)


def board_landmarks(truth_seq, arms, dst, cell=150):
    """Every landmark cut out of every shot's start frame, one row per landmark per arm: the same building
    should look the same all along its row."""
    seq = _script(truth_seq)
    tshots = {s["id"]: s for s in seq["shots"]}
    ashots = {arm: {s["id"]: s for s in _script(arm)["shots"]} for arm in arms}
    shots = [s["id"] for s in seq["shots"]]
    truths = {sid: Truth(truth_seq, sid) for sid in shots}
    lms = truths[shots[0]].landmarks
    rows = [(lm, arm) for lm in lms for arm in arms]
    sheet = Image.new("RGB", (170 + len(shots) * (cell + 4), len(rows) * (cell + 4) + 26), (16, 16, 20))
    dr = ImageDraw.Draw(sheet)
    for c, sid in enumerate(shots):
        dr.text((170 + c * (cell + 4) + 4, 6), sid, fill=(200, 200, 210))
    for r, (lm, arm) in enumerate(rows):
        y = 24 + r * (cell + 4)
        dr.text((6, y + cell // 2 - 12), lm, fill=(235, 235, 235))
        dr.text((6, y + cell // 2 + 2), arm, fill=(150, 150, 165))
        for c, sid in enumerate(shots):
            sp = os.path.join(FIGHT, arm, "anchor_%s.png" % sid)
            if not os.path.exists(sp):
                continue
            f0 = truths[sid].frames if reversed_against(tshots[sid], ashots[arm].get(sid, {})) else 1
            labels, names = truths[sid].groups_at(f0)
            if lm not in names:
                continue
            mk = labels == names.index(lm)
            if mk.sum() < 800:
                continue
            ys, xs = np.nonzero(mk)
            x0, x1, y0, y1 = np.percentile(xs, 1), np.percentile(xs, 99), np.percentile(ys, 1), np.percentile(ys, 99)
            side = max(x1 - x0, y1 - y0) + 10
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            box = tuple(int(v) for v in (max(0, cx - side / 2), max(0, cy - side / 2), min(W, cx + side / 2),
                                          min(H, cy + side / 2)))
            crop = to704(Image.open(sp)).crop(box)
            crop.thumbnail((cell, cell))
            sheet.paste(crop, (170 + c * (cell + 4), y))
    sheet.save(dst, quality=86)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--truth", default="plaza-set")
    ap.add_argument("--arms", nargs="+", default=["plaza-set", "plaza-words"])
    ap.add_argument("--picks", default="", help="arm:shot=take.mp4,... for the takes board")
    a = ap.parse_args()
    rep = measure(a.truth, a.arms)
    out = os.path.join(FIGHT, a.truth, "measure")
    os.makedirs(out, exist_ok=True)
    json.dump(rep, open(os.path.join(FIGHT, a.truth, "measure.json"), "w"), indent=1)
    board_starts(a.truth, a.arms, rep, os.path.join(out, "starts.jpg"))
    board_landmarks(a.truth, a.arms, os.path.join(out, "landmarks.jpg"))
    picks = {}
    for item in filter(None, a.picks.split(",")):
        arm, rest = item.split(":", 1)
        sid, take = rest.split("=", 1)
        picks.setdefault(arm, {})[sid] = take
    if picks:
        board_takes(a.truth, a.arms, picks, os.path.join(out, "takes.jpg"))
    print("self-fit (the set's own render):", json.dumps(rep["self_fit"]))
    for arm, A in rep["arms"].items():
        print("%-12s %s" % (arm, json.dumps(A["summary"])))
        print("   spread:", json.dumps(A["start_spread"]))
        for sid, row in A["shots"].items():
            st = row.get("start") or {}
            tk = "  ".join("%s fit %.2f->%.2f (min %.2f, hold %s, dE %s)" % (
                k[:-4], v["fit_first"], v["fit_last"], v["fit_min"], v["hold"], v["dE_mean"])
                for k, v in row["takes"].items())
            print("   %s start fit %s (chance %s) dE %s | %s" % (sid, st.get("fit"), st.get("chance"),
                                                               st.get("dE_plate_mean"), tk))


if __name__ == "__main__":
    main()
