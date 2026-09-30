#!/usr/bin/env python3
"""studio/_tools/previz_chain.py - one long choreographed camera move, drawn as a CHAIN of shots.

    python3 studio/_tools/previz_chain.py --sequence FILM --shots 103,104,105,106,107,108 \
        [--frames-per 121] [--seeds 11 202] [--start anchor_102.png] [--only-previz]

A 360-degree orbit is where a video engine gives up: asked in words it arcs a few degrees, and drawn
between two turned keyframes (flf_shots.py) it cross-fades the room, because every key invents the
room again. So the move is made the way previz_shot.py makes physics:

  1. the WHOLE move is rendered once in Blender (previz_blender.py, the first shot's "previz" block:
     scene, degrees, radius, lens, cam_z, look_z), so the camera is one continuous path;
  2. it is cut into overlapping pieces, one per shot - each piece's first frame is the one before's
     last - short enough for one LTX-2.3 generation (--frames-per, 8n+1);
  3. each shot is drawn by LTX-2.3 with the IC-LoRA union control (workflow 74, previz_shot.draw)
     reading its piece's depth. The first starts on --start (the master start frame); every later one
     starts on the LAST FRAME of the take before it, so a seed is one whole chain and the room that
     was painted is the room the next piece continues.

Takes land as pv_<id>_s<seed>.mp4 (fight.py --finish: "103=pv:11"). Per take: motion agreement (r)
against its piece. A board of every piece's first frame per chain: previz_<first>-<last>_chains.jpg.
"""
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.expanduser("~/shared/comfy-studio")
TOOLS = os.path.join(ROOT, "studio", "_tools")
sys.path.insert(0, TOOLS)
import fight                                  # noqa: E402  (reads --sequence off argv)
import newmodels_test as nm                   # noqa: E402
import previz_shot                            # noqa: E402
from flf_shots import frame as take_frame     # noqa: E402


def cut(src, first, last, dst):
    """Frames first..last of src, inclusive, as their own clip (re-encoded, frame-exact)."""
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vf",
                    "select=between(n\\,%d\\,%d),setpts=PTS-STARTPTS" % (first, last), "-fps_mode", "passthrough",
                    "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", dst], check=True)
    return dst


def match_colour(src, ref, dst, amount):
    """Each hop of a chain starts on the frame the last one ended on, and the engines drift - darker,
    bluer - a little every hop. So a start frame is pulled toward the FIRST start frame's colour and
    exposure (mean and spread per channel in Lab) before the next piece is drawn from it."""
    import numpy as np
    from PIL import Image
    from skimage import color
    a = color.rgb2lab(np.asarray(Image.open(src).convert("RGB")) / 255.0)
    b = color.rgb2lab(np.asarray(Image.open(ref).convert("RGB")) / 255.0)
    out = a.copy()
    for c in range(3):
        m1, s1, m2, s2 = a[..., c].mean(), a[..., c].std() + 1e-6, b[..., c].mean(), b[..., c].std()
        out[..., c] = (1 - amount) * a[..., c] + amount * ((a[..., c] - m1) * (s2 / s1) + m2)
    rgb = np.clip(color.lab2rgb(out), 0, 1)
    Image.fromarray((rgb * 255).round().astype("uint8")).save(dst)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sequence", required=True)
    ap.add_argument("--shots", required=True, help="the chain's shots, in order")
    ap.add_argument("--frames-per", type=int, default=121, help="frames per shot, 8n+1")
    ap.add_argument("--seeds", type=int, nargs="+", default=[11])
    ap.add_argument("--start", default="", help="the first shot's start frame (default its anchor)")
    ap.add_argument("--draw", default="", help="draw only these shots of the chain (the previz is still the whole move)")
    ap.add_argument("--backward", action="store_true",
                    help="draw them from the last back to the first: each piece reversed, --start is the frame the "
                         "move ENDS on, every take reversed back afterwards - so a loop closes exactly on it")
    ap.add_argument("--match", type=float, default=0.0,
                    help="pull each later start frame this far (0-1) toward the first one's colour and exposure")
    ap.add_argument("--only-previz", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    ids = [x.strip() for x in a.shots.split(",") if x.strip()]
    shots = [fight.shot(i) for i in ids]
    L = a.frames_per
    if (L - 1) % 8:
        sys.exit("--frames-per must be 8n+1")
    pz = dict(shots[0].get("previz") or {})
    total = len(ids) * (L - 1) + 1
    tag = "%s-%s" % (ids[0], ids[-1])
    pdir = os.path.join(fight.OUT, "previz_" + tag)
    pv = os.path.join(pdir, "previz.mp4")

    # 1. the whole move, once
    if not os.path.exists(pv) or a.force:
        t0 = time.time()
        cmd = ["python3", os.path.join(TOOLS, "previz_blender.py"), "--out", pdir, "--scene",
               pz.get("scene", "orbit"), "--frames", str(total), "--fps", "24"]
        for k in ("degrees", "radius", "lens", "cam_z", "look_z", "figure_glb"):
            if k in pz:
                v = pz[k]
                if k == "figure_glb" and not os.path.isabs(v):
                    v = os.path.join(ROOT, v)          # a path in the repo, e.g. studio/sheets/<id>/model.glb
                cmd += ["--" + k.replace("_", "-"), str(v)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if not os.path.exists(pv):
            print(r.stdout[-1500:], r.stderr[-1500:])
            sys.exit("the previz did not render")
        print("  previz %d frames in %.0fs -> %s" % (nm.nframes(pv)[0], time.time() - t0, pv), flush=True)
    nm.strip(pv, os.path.join(fight.OUT, "previz_%s_strip.jpg" % tag), n=12)

    # 2. the pieces, each starting on the frame the one before ends on
    pieces = []
    for k, sid in enumerate(ids):
        seg = os.path.join(pdir, "piece_%s.mp4" % sid)
        if not os.path.exists(seg) or a.force:
            cut(pv, k * (L - 1), k * (L - 1) + L - 1, seg)
        n = nm.nframes(seg)[0]
        if n != L:
            sys.exit("piece %s has %d frames, not %d" % (sid, n, L))
        pieces.append(seg)
    print("  %d pieces of %d frames" % (len(pieces), L), flush=True)
    if a.only_previz:
        return

    # 3. the chains, one per seed - forward, or backward from the frame the move must end on
    draw = [x for x in a.draw.split(",") if x] or ids
    order = [k for k, sid in enumerate(ids) if sid in draw]
    if a.backward:
        order = order[::-1]
        for k in order:
            rp_ = pieces[k][:-4] + "_rev.mp4"
            if not os.path.exists(rp_) or a.force:
                previz_shot.reverse(pieces[k], rp_)
    start0 = os.path.join(fight.OUT, a.start or "anchor_%s.png" % ids[0])
    if not os.path.exists(start0):
        sys.exit("no start frame %s" % start0)
    rp = os.path.join(fight.OUT, "previz_%s.json" % tag)
    rep = json.load(open(rp)) if os.path.exists(rp) else {}
    rep.update({"shots": ids, "frames_per": L, "previz": pv, "start": os.path.basename(start0)})
    chains = rep.setdefault("chains", {})
    for seed in a.seeds:
        start, rows = start0, []
        for k in order:
            sid, s = ids[k], shots[k]
            seg = pieces[k][:-4] + "_rev.mp4" if a.backward else pieces[k]
            dst = os.path.join(fight.OUT, "pv_%s_s%d.mp4" % (sid, seed))
            drawn = os.path.join(fight.OUT, "_pvback_%s_s%d.mp4" % (sid, seed)) if a.backward else dst
            if os.path.exists(dst) and not a.force:
                secs = 0.0
            else:
                t0 = time.time()
                v, _ = previz_shot.draw(s, seg, L, start, seed, drawn, False)
                if not v:
                    print("  pv_%s_s%d FAILED - the chain stops here" % (sid, seed), flush=True)
                    break
                if a.backward:
                    previz_shot.reverse(drawn, dst)       # back into the film's time
                secs = time.time() - t0
            ma = nm.motion_agreement(seg, drawn)
            rows.append({"take": os.path.basename(dst), "start": os.path.basename(start), "secs": round(secs, 1),
                         "frames": nm.nframes(dst)[0], "motion": ma})
            print("  %-18s %4.0fs  motion r=%s  (from %s)" % (os.path.basename(dst), secs, ma.get("r"),
                                                               os.path.basename(start)), flush=True)
            start = take_frame(fight.OUT, "end:" + os.path.basename(drawn))
            if a.match > 0:
                start = match_colour(start, start0, start[:-4] + "_m%02d.png" % round(a.match * 100), a.match)
        chains[str(seed)] = rows
        json.dump(rep, open(rp, "w"), indent=1)

    # a board: per chain, the frame each piece starts on, and the chain's last frame
    from PIL import Image, ImageDraw
    H = 160
    lines = []
    for seed in a.seeds:
        cells = []
        for sid in ids:
            p = os.path.join(fight.OUT, "pv_%s_s%d.mp4" % (sid, seed))
            if os.path.exists(p):
                f = os.path.join(pdir, "_first_%s_s%d.png" % (sid, seed))
                nm.frame_at(p, 0.0, f)
                cells.append(("%s s%d" % (sid, seed), f))
        last = os.path.join(fight.OUT, "pv_%s_s%d.mp4" % (ids[-1], seed))
        if os.path.exists(last):
            cells.append(("end s%d" % seed, take_frame(fight.OUT, "end:" + os.path.basename(last))))
        lines.append(cells)
    W = max([len(c) for c in lines] + [1]) * (int(H * 1280 / 704) + 4)
    b = Image.new("RGB", (W, len(lines) * (H + 18)), "white")
    d = ImageDraw.Draw(b)
    for r, cells in enumerate(lines):
        for c, (label, p) in enumerate(cells):
            im = Image.open(p).convert("RGB").resize((int(H * 1280 / 704), H))
            x, y = c * (im.width + 4), r * (H + 18)
            b.paste(im, (x, y + 16))
            d.text((x + 3, y + 2), label, fill="black")
    b.save(os.path.join(fight.OUT, "previz_%s_chains.jpg" % tag), quality=85)
    print("PREVIZ CHAIN DONE", flush=True)


if __name__ == "__main__":
    main()
