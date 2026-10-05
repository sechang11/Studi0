#!/usr/bin/env python3
"""studio/_tools/set_test.py - a scene shot inside a 3D set: render, plate, start frames, takes.

For a shot script whose shots are cameras in a set ("engine": "previz", "previz": {"scene": "set", ...};
see studio/shotscripts/_make_plaza_test_0930.py), in stages:

  render   every shot from the set (previz_blender.py --scene set): the move's frames and control
           video, the landmark ID masks, a still of the first frame on the 1280x720 start-frame canvas,
           and a map of the set with every camera drawn on it (map.jpg)
  plate    the establishing shot's still dressed as a photograph (Qwen-Image-2.1), several seeds, for a
           person to pick; --pick S makes it the place's reference (ref_<place>.png) here and in the
           sequences named by --also, and the establishing shot's start frame
  dress    every other shot's still dressed as a photograph, from the render ALONE (with the plate as a
           second picture, Qwen-Image-2.1 returned the plate's view for 7 of 7 shots), several seeds; the
           candidate the set's map of surfaces fits best (set_measure.fit) becomes anchor_<id>.png
  match    (optional) each building's colour held from shot to shot by the set's surface masks: every key
           surface pulled toward its colour in the plate, or in the first shot that shows it
  draw     each shot's takes through previz_shot.py: LTX-2.3 + IC-LoRA reading the render's depth
  ends     for a move that reveals what its start frame never showed: the move's LAST frame dressed too
  pin      those moves drawn again pinned at both ends (pve_<id>_s<seed>.mp4): the depth carries the
           shapes, only a dressed frame carries the look - unpinned, the orbit's cafe came back pink
  cast     a character standing in the set (figure_glb at figure_at): the place dressed without her, and
           the view of her character sheet facing the camera pasted in where the set projects her feet
           and head (the dress itself redraws her at her reference's size, not the set's)
  key      KEY POSES (LTX_PLAYBOOK §100.10): each of a shot's "keys" painted into its own frame by
           Qwen-Image-2.1 edit - {"at": <take frame, or "end">, "from": "start" | "end" | <an earlier
           key's frame>, "erase": <words, optional, run first>, "pose": <words>, "fx": <words, optional,
           run last: the impact flash at the contact>, "seed": <the pick>} - on
           every seed, graded to the start frame, onto keys_<id>/keys.jpg with each one's detail against
           its source (over x3.5: the editor restyled the whole frame). Look, then set "seed".
  take     H3 first-last (workflow 65) between the shot's two frames, its keys anchored by
           MiniMaxH3AddGuide at their frames and an "end" key as the last frame: h3k_<id>_s<seed>.mp4
           (h3f_ without keys). The numbered beat list stays the words: keys fix pose and frame only.

    python3 studio/_tools/set_test.py --sequence plaza-set render
    python3 studio/_tools/set_test.py --sequence plaza-set plate --seeds 11 202 3003 4242
    python3 studio/_tools/set_test.py --sequence plaza-set plate --pick 202 --also plaza-words
    python3 studio/_tools/set_test.py --sequence plaza-set dress
    python3 studio/_tools/set_test.py --sequence plaza-set draw --seeds 11 202
    python3 studio/_tools/set_test.py --sequence forest-duel key --only F10 --seeds 11 202
    python3 studio/_tools/set_test.py --sequence forest-duel take --only F10 --seeds 11 202
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.expanduser("~/shared/comfy-studio")
TOOLS = os.path.join(ROOT, "studio", "_tools")
sys.path.insert(0, TOOLS)
import fight                      # noqa: E402  (reads --sequence off argv)
import previz_shot as ps          # noqa: E402
import set_measure as sm          # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

OUT = fight.OUT
PLACE = fight.PLACE_ID


def pdir(sid):
    return os.path.join(OUT, "previz_%s" % sid)


def still(sid):
    return os.path.join(pdir(sid), "still720", "frames", "f_0001.png")


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-1500:], r.stderr[-1500:], flush=True)
        raise SystemExit("failed: %s" % " ".join(cmd[:6]))
    return r


def stage_render(force=False, only=()):
    for s in fight.SHOTS:
        if only and s["id"] not in only:
            continue
        d = pdir(s["id"])
        t0 = time.time()
        if not os.path.exists(os.path.join(d, "previz.mp4")) or force:
            _run(ps.blender_cmd(s, d))
        # the first frame again on the 1280x720 canvas every start frame is drawn on - not for a shot drawn
        # between two frames (its frames are the empty place, rendered by cast)
        if not s["previz"].get("endpoints") and (not os.path.exists(still(s["id"])) or force):
            one = dict(s, previz=dict(s["previz"], frames=1, masks=0))
            _run(ps.blender_cmd(one, os.path.join(d, "still720")) + ["--height=720"])
        print("  %s rendered  %.0fs" % (s["id"], time.time() - t0), flush=True)
    draw_map()


def draw_map():
    """The set from straight above, north up, with every shot's camera path and where it looks."""
    d = os.path.join(OUT, "map")
    across = 96.0
    if not os.path.exists(os.path.join(d, "frames", "f_0001.png")):
        _run(["python3", os.path.join(TOOLS, "previz_blender.py"), "--out", d, "--scene", "set",
              "--set=%s" % fight.SHOTS[0]["previz"].get("set", "plaza"), "--frames=1", "--cam=0,0,150",
              "--look=0,0.01,0", "--ortho=%s" % across, "--width=1024", "--height=1024"])
    mp = Image.open(os.path.join(d, "frames", "f_0001.png")).convert("RGB")
    dr = ImageDraw.Draw(mp)
    px = lambda x, y: (512 + x / across * 1024, 512 - y / across * 1024)
    for s in fight.SHOTS:
        if not os.path.exists(os.path.join(pdir(s["id"]), "previz.json")):
            continue                    # not rendered yet: a script being rendered a few shots at a time
        cams = json.load(open(os.path.join(pdir(s["id"]), "previz.json")))["camera"]
        pts = [px(c["cam"][0], c["cam"][1]) for c in cams]
        if len(pts) > 1:
            dr.line(pts, fill=(255, 50, 50), width=4)
        for c in (cams[0], cams[-1]):
            x, y = px(c["cam"][0], c["cam"][1])
            lx, ly = px(c["look"][0], c["look"][1])
            n = math.hypot(lx - x, ly - y) or 1.0
            dr.line([(x, y), (x + (lx - x) / n * 44, y + (ly - y) / n * 44)], fill=(255, 225, 40), width=3)
        x, y = pts[0]
        dr.ellipse([x - 8, y - 8, x + 8, y + 8], fill=(255, 50, 50))
        dr.rectangle([x + 9, y - 18, x + 40, y - 4], fill=(0, 0, 0))
        dr.text((x + 12, y - 17), s["id"], fill=(255, 255, 255))
    mp.save(os.path.join(OUT, "map.jpg"), quality=90)
    print("  map -> %s" % os.path.join(OUT, "map.jpg"), flush=True)


def dress_words(s):
    """The shot's dress words and grade. The render goes in ALONE: with the plate as a second picture,
    Qwen-Image-2.1 returned the plate's view instead of the render's for 7 of 7 shots (2026-09-30)."""
    return (s["previz"].get("dress") or "") + " " + (s["previz"].get("grade") or fight.GRADE)


def cast_refs(s):
    """The pictures of the characters in a shot (their reference, ref_<id>.png): <image2> onward. A
    character's picture is not a view of the place, so it cannot pull the dress to another framing."""
    return [os.path.join(OUT, "ref_%s.png" % r) for r in fight._unique(s.get("refs") or [])
            if r in fight.CAST and os.path.exists(os.path.join(OUT, "ref_%s.png" % r))]


def plate_words():
    return dress_words(fight.SHOTS[0])


def dress_one(src, dst, seed, words, refs=()):
    """Qwen-Image-2.1 (workflow 80): <image1> is the canvas and the layout, further images are looks."""
    wf = {k: v for k, v in fight.load_wf("80_qwen21_edit_refs.json").items()
          if isinstance(v, dict) and "class_type" in v}
    for k in ("21", "22", "23"):
        wf.pop(k, None)
    for k in list(wf["6"]["inputs"]):
        if k.startswith("images."):
            del wf["6"]["inputs"][k]
    for i, p in enumerate([src] + list(refs), 1):
        name = "set_dress_%d.png" % i
        shutil.copy(p, os.path.join(fight.COMFY, "input", name))
        wf["d%d" % i] = {"class_type": "LoadImage", "inputs": {"image": name}}
        wf["6"]["inputs"]["images.image_%d" % i] = ["d%d" % i, 0]
    wf["6"]["inputs"]["prompt"] = words
    wf["6"]["inputs"]["negative_prompt"] = fight.AVOID + ", 3d render, cgi, flat colours, untextured, cartoon"
    wf["10"]["inputs"]["seed"] = int(seed)
    wf["12"]["inputs"]["filename_prefix"] = "claude-generated/fight/set_dress_s%d" % seed
    if fight.collect(fight.submit(wf, "dress %s s%d" % (os.path.basename(dst), seed)), dst):
        return fight._to_canvas(dst, (1280, 720))
    return None


def board(paths, dst, labels, tw=640):
    th = round(tw * 720 / 1280)
    cols = 2
    rows = (len(paths) + 1) // 2
    sheet = Image.new("RGB", (cols * (tw + 6) + 6, rows * (th + 6) + 6), (16, 16, 20))
    dr = ImageDraw.Draw(sheet)
    for i, (p, lab) in enumerate(zip(paths, labels)):
        x, y = 6 + (i % cols) * (tw + 6), 6 + (i // cols) * (th + 6)
        sheet.paste(Image.open(p).convert("RGB").resize((tw, th)), (x, y))
        dr.rectangle([x, y, x + 8 + 7 * len(lab), y + 16], fill=(0, 0, 0))
        dr.text((x + 4, y + 2), lab, fill=(240, 240, 240))
    sheet.save(dst, quality=88)


def stage_plate(seeds, pick=None, also=()):
    first = fight.SHOTS[0]["id"]
    src = still(first)
    if not pick:
        fight.wait_for_queue()
        ps._room(20.0, 180)
        made = []
        for q in seeds:
            dst = os.path.join(OUT, "plate_s%d.png" % q)
            if not os.path.exists(dst):
                t0 = time.time()
                if not dress_one(src, dst, q, plate_words(), cast_refs(fight.SHOTS[0])):
                    print("  plate s%d FAILED" % q, flush=True)
                    continue
                print("  plate s%-5d %4.0fs" % (q, time.time() - t0), flush=True)
            made.append(dst)
        board([src] + made, os.path.join(OUT, "plate_board.jpg"), ["the set's render"] +
              [os.path.basename(p) for p in made])
        print("  pick one: --pick SEED  (board: %s)" % os.path.join(OUT, "plate_board.jpg"), flush=True)
        return
    p = os.path.join(OUT, "plate_s%d.png" % pick)
    for seq in (fight.FILM,) + tuple(also):
        d = os.path.join(ROOT, "studio", "samples", "fight", seq)
        os.makedirs(d, exist_ok=True)
        shutil.copy(p, os.path.join(d, "ref_%s.png" % PLACE))
        print("  ref_%s.png <- plate s%d  (%s)" % (PLACE, pick, seq), flush=True)
    # the establishing shot starts on the plate itself (its middle 704 rows)
    sm.to704(Image.open(p)).save(os.path.join(OUT, "anchor_%s.png" % first))
    print("  anchor_%s.png <- the plate" % first, flush=True)


def stage_dress(seeds=(11, 202), force=False):
    plate = os.path.join(OUT, "ref_%s.png" % PLACE)
    if not os.path.exists(plate):
        sys.exit("plate first: %s" % plate)
    pcols = sm.plate_colours(fight.FILM, plate, fight.SHOTS[0]["id"])
    fight.wait_for_queue()
    ps._room(20.0, 180)
    record_p = os.path.join(OUT, "dress.json")
    record = json.load(open(record_p)) if os.path.exists(record_p) else {}
    for s in fight.SHOTS[1:]:
        sid = s["id"]
        tr = sm.Truth(fight.FILM, sid)
        cands = {}
        for q in seeds:
            p = os.path.join(OUT, "anchor_%s_pvdress_s%d.png" % (sid, q))
            if not os.path.exists(p) or force:
                t0 = time.time()
                if not dress_one(still(sid), p, q, dress_words(s), cast_refs(s)):
                    print("  %s dress s%d FAILED" % (sid, q), flush=True)
                    continue
                sm.to704(Image.open(p)).save(p)           # the LTX-2.3 canvas: the middle 704 rows
                print("  %s dress s%-5d %4.0fs" % (sid, q, time.time() - t0), flush=True)
            g, _ = sm.score_image(tr, 1, Image.open(p), pcols)
            cands["s%d" % q] = {"file": os.path.basename(p), "fit": g["fit"], "dE_plate_mean": g["dE_plate_mean"]}
        if not cands:
            continue
        # the geometry decides; a candidate within 0.02 of the best fit wins if its colours are closer to the plate
        best = max(cands.values(), key=lambda c: c["fit"])
        close = [c for c in cands.values() if best["fit"] - c["fit"] <= 0.02]
        pick = min(close, key=lambda c: c["dE_plate_mean"] if c["dE_plate_mean"] is not None else 99)
        shutil.copy(os.path.join(OUT, pick["file"]), os.path.join(OUT, "anchor_%s.png" % sid))
        record[sid] = {"candidates": cands, "chosen": pick["file"]}
        print("  anchor_%s <- %s   %s" % (sid, pick["file"], "  ".join(
            "%s fit %.3f dE %s" % (k, c["fit"], c["dE_plate_mean"]) for k, c in sorted(cands.items()))), flush=True)
    json.dump(record, open(record_p, "w"), indent=1)


def stage_match(apply=False, l_share=0.5, sigma=6.0):
    """Hold each building's colour from shot to shot with the set's surface masks: every key surface of
    every start frame is pulled toward its colour in a look book - the plate, then the first shot that
    shows it - a and b fully, L by half (the light and shade stay), feathered. Writes
    anchor_<id>_matched.png; --apply makes them the start frames (the originals stay as _unmatched).
    Measured on the plaza test's stills: dE against the plate 10.7 -> 4.6, the spread between shots
    14.6 -> 6.9. Water and paving are left alone: how much of them shows depends on the view."""
    import cv2
    import numpy as np
    from skimage.color import lab2rgb, rgb2lab
    want = [n for n in sm.KEY_SURFACES if n not in ("ground/paving", "fountain/water")]
    first = fight.SHOTS[0]["id"]
    plate = sm.to704(Image.open(os.path.join(OUT, "ref_%s.png" % PLACE)))
    book = sm.surface_colours(plate, *sm.Truth(fight.FILM, first).surf(1), want=want)
    for s in fight.SHOTS[1:]:
        sid = s["id"]
        src = os.path.join(OUT, "anchor_%s.png" % sid)
        if os.path.exists(os.path.join(OUT, "anchor_%s_unmatched.png" % sid)):
            src = os.path.join(OUT, "anchor_%s_unmatched.png" % sid)
        labels, names = sm.Truth(fight.FILM, sid).surf(1)
        im = sm.to704(Image.open(src))
        cols = sm.surface_colours(im, labels, names, want=want)
        lab = rgb2lab(np.asarray(im).astype(np.float32) / 255.0)
        shift = np.zeros_like(lab)
        weight = np.zeros(lab.shape[:2], np.float32)
        moved = []
        for n, c in cols.items():
            if n not in book:
                book[n] = c
                continue
            d = book[n] - c
            d[0] *= l_share
            mk = labels == names.index(n)
            shift[mk] = d
            weight[mk] = 1.0
            moved.append("%s %.1f" % (n, sm.de(c, book[n])))
        ws = cv2.GaussianBlur(weight, (0, 0), sigma)
        ss = np.stack([cv2.GaussianBlur((shift[:, :, k] * weight).astype(np.float32), (0, 0), sigma)
                       for k in range(3)], -1)
        field = ss / np.maximum(ws, 1e-3)[:, :, None] * np.clip(ws, 0, 1)[:, :, None]
        out = Image.fromarray((np.clip(lab2rgb(lab + field), 0, 1) * 255).round().astype(np.uint8))
        out.save(os.path.join(OUT, "anchor_%s_matched.png" % sid))
        if apply:
            if not os.path.exists(os.path.join(OUT, "anchor_%s_unmatched.png" % sid)):
                shutil.copy(src, os.path.join(OUT, "anchor_%s_unmatched.png" % sid))
            out.save(os.path.join(OUT, "anchor_%s.png" % sid))
        print("  %s matched: %s" % (sid, ", ".join(moved) or "nothing to match"), flush=True)


def stage_ends(ids, seeds=(11, 202, 3003), force=False):
    """The LAST frame of a move dressed as well: a move that reveals part of the place its start frame never
    showed (an orbit coming round to the cafe, a crane rising over the awning) has only the set's DEPTH for
    it, and the engine invents the look - the cafe came back pink. So the set's own render of the move's
    last frame is dressed like any start frame (render alone, several seeds, best fit to the set) and
    becomes anchor_<id>_end.png, for `pin`."""
    for sid in ids:
        s = fight.shot(sid)
        n = json.load(open(os.path.join(pdir(sid), "previz.json")))["frames"]
        d = os.path.join(pdir(sid), "end720")
        last = os.path.join(d, "frames", "f_%04d.png" % n)
        if not os.path.exists(last) or force:
            _run(ps.blender_cmd(dict(s, previz=dict(s["previz"], masks=0)), d) + ["--height=720"])
        labels = sm.Truth(fight.FILM, sid).surf(n)[0]
        cands = {}
        for q in seeds:
            p = os.path.join(OUT, "anchor_%s_end_s%d.png" % (sid, q))
            if not os.path.exists(p) or force:
                t0 = time.time()
                if not dress_one(last, p, q, dress_words(s), cast_refs(s)):
                    continue
                sm.to704(Image.open(p)).save(p)
                print("  %s end dress s%-5d %4.0fs" % (sid, q, time.time() - t0), flush=True)
            cands[p] = sm.fit(sm.to704(Image.open(p)), labels)
        if cands:
            best = max(cands, key=cands.get)
            shutil.copy(best, os.path.join(OUT, "anchor_%s_end.png" % sid))
            print("  anchor_%s_end <- %s   %s" % (sid, os.path.basename(best), "  ".join(
                "%s fit %.3f" % (os.path.basename(k)[-9:-4], v) for k, v in cands.items())), flush=True)


def stage_pin(ids, seeds):
    """Takes pinned at both ends: the dressed start frame, the set's depth for every frame between, and
    the dressed LAST frame as a keyframe guide at frame -1 (previz_shot.draw(end=...)). pve_<id>_s<seed>."""
    ps._room(26.0, 240)
    for sid in ids:
        s = fight.shot(sid)
        pv = os.path.join(pdir(sid), "previz.mp4")
        frames = ps.nm.nframes(pv)[0]
        start = os.path.join(OUT, "anchor_%s.png" % sid)
        end = os.path.join(OUT, "anchor_%s_end.png" % sid)
        for q in seeds:
            dst = os.path.join(OUT, "pve_%s_s%d.mp4" % (sid, q))
            if os.path.exists(dst):
                continue
            v, secs = ps.draw(s, pv, frames, start, q, dst, False, end=end, stem="pve")
            if v:
                fight.strip(v, v[:-4] + "_strip.jpg")
                if (s.get("previz") or {}).get("reverse"):
                    ps.reverse(v, os.path.join(OUT, "pver_%s_s%d.mp4" % (sid, q)))
            print("  %s %4.0fs  motion r=%s" % (os.path.basename(dst), secs,
                                                ps.nm.motion_agreement(pv, v).get("r") if v else "FAILED"), flush=True)


# her character sheet's eight turnaround views, by where the camera stands relative to her front (degrees,
# clockwise seen from above: +90 = the camera at her right side, where she faces screen-right). The sheets name a
# view by the way the CAMERA went round her: "turn_right" = the camera orbited to the right, so it stands at her
# LEFT and she faces screen-left. Until 2026-10-05 this table read the names the other way and every side and
# three-quarter view went in mirrored - forest-duel D07's last frame had Terra facing away from the jester.
VIEWS8 = [(0, "turn_front"), (45, "turn_front_l"), (90, "turn_left"), (135, "turn_back_l"), (180, "turn_back"),
          (-135, "turn_back_r"), (-90, "turn_right"), (-45, "turn_front_r")]


def _project(cam, look, lens, p, w=1280, h=720):
    """A point in the set to a pixel of the camera's frame (Blender's: 36 mm sensor fitted to the width)."""
    import numpy as np
    c, l, q = (np.array(v, float) for v in (cam, look, p))
    f = (l - c) / np.linalg.norm(l - c)
    r = np.cross(f, [0.0, 0.0, 1.0])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    d = q - c
    k = lens / 36.0 * w
    return w / 2 + (d @ r) / (d @ f) * k, h / 2 - (d @ u) / (d @ f) * k


def _cut(sheet, view):
    """One of her sheet's turnaround views cut out of its grey (BiRefNet, the sheets' own matte), cached. A
    three-quarter view that faces the same way as its twin on the other side is the twin mirrored: Terra's sheet
    drew turn_front_l facing the way turn_front_r does (6.6 grey levels apart, 18.3 from _r mirrored), the jester's
    turn_back pair too (4.4 vs 10.4) - 2026-10-05; the "_r" picture is taken as drawn."""
    dst = os.path.join(OUT, "cut_%s_%s.png" % (os.path.basename(sheet.rstrip("/")), view))
    if not os.path.exists(dst):
        src = os.path.join(ROOT, sheet, "views", view + ".png")
        twin = src[:-len("_l.png")] + "_r.png" if view.endswith("_l") else None
        if twin and os.path.exists(twin) and _same_facing(src, twin):
            from PIL import ImageOps
            ImageOps.mirror(Image.open(_cut(sheet, view[:-2] + "_r"))).save(dst)
            return dst
        import sheets_routes
        sheets_routes.E().matte(src, dst, "cast_" + view)
    return dst


def _same_facing(a, b):
    """Two twin views (left and right three-quarters) drawn facing the same way: `a` is nearer `b` than `b`
    mirrored (mean grey difference at 128x192, by a clear margin)."""
    import numpy as np
    from PIL import ImageOps
    g = lambda im: np.asarray(im.convert("L").resize((128, 192)), dtype=np.float32)
    x, y = g(Image.open(a)), Image.open(b)
    return float(np.abs(x - g(y)).mean()) < 0.75 * float(np.abs(x - g(ImageOps.mirror(y))).mean())


DEPTH_FAR = 80.0          # previz_blender --depth: 16-bit grey, 0 at the lens, 1 at DEPTH_FAR m


def _depth_m(png):
    """A --depth render as metres along the camera's axis (the 1280x720 canvas the empty place is drawn on)."""
    import numpy as np
    im = Image.open(png)
    a = np.asarray(im, dtype=np.float32)
    if a.ndim == 3:
        a = a[:, :, 0]
    top = 65535.0 if a.max() > 255 else 255.0
    return a / top * DEPTH_FAR


def _view_z(cam, look, p):
    import numpy as np
    c, l, q = (np.array(v, float) for v in (cam, look, p))
    f = (l - c) / np.linalg.norm(l - c)
    return float((q - c) @ f)


def _paste(bg_png, cut_png, feet, height_px, shadow=0.35, occlude=None):
    """Her cut-out, scaled so she is height_px tall, standing on `feet`, with a soft contact shadow. With
    `occlude` = (depth in metres, her distance), every pixel where the set is nearer to the camera than she is
    (by more than 35 cm) hides her - a fallen trunk in front of the jester (forest-duel E07, 2026-10-01)."""
    from PIL import ImageFilter
    bg = (Image.open(bg_png) if isinstance(bg_png, str) else bg_png).convert("RGBA")
    fig = Image.open(cut_png).convert("RGBA")
    fig = fig.crop(fig.getchannel("A").point(lambda a: 255 if a > 24 else 0).getbbox())
    k = height_px / fig.height
    fig = fig.resize((max(1, round(fig.width * k)), max(1, round(fig.height * k))), Image.LANCZOS)
    sh = Image.new("L", bg.size, 0)
    wid = fig.width * 0.55
    e = max(4.0, wid * 0.18)
    ImageDraw.Draw(sh).ellipse([feet[0] - wid / 2, feet[1] - e / 2, feet[0] + wid / 2, feet[1] + e / 2],
                               fill=int(255 * shadow))
    bg = Image.composite(Image.new("RGBA", bg.size, (20, 20, 30, 255)), bg, sh.filter(ImageFilter.GaussianBlur(e / 3)))
    layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    layer.paste(fig, (round(feet[0] - fig.width / 2), round(feet[1] - fig.height)), fig)
    if occlude is not None:
        import numpy as np
        depth, her_z = occlude
        if depth.shape[:2] != (bg.size[1], bg.size[0]):
            depth = np.asarray(Image.fromarray(depth).resize(bg.size, Image.BILINEAR), dtype=np.float32)
        seen = (depth >= her_z - 0.35).astype(np.float32)
        alpha = np.asarray(layer.getchannel("A"), dtype=np.float32) * seen
        layer.putalpha(Image.fromarray(alpha.clip(0, 255).astype(np.uint8)))
    return Image.alpha_composite(bg, layer).convert("RGB")


def _still_place(pz, a_png, b_png, tol=2.5):
    """A still camera (no cam_to / look_to / arc) and the set's two empty renders all but identical."""
    if any(pz.get(k) for k in ("cam_to", "look_to", "arc")):
        return False
    import numpy as np
    a = np.asarray(Image.open(a_png).convert("L").resize((320, 180)), np.float32)
    b = np.asarray(Image.open(b_png).convert("L").resize((320, 180)), np.float32)
    return float(np.abs(a - b).mean()) < tol


def stage_cast(ids, seeds=(11, 202, 3003), ends=False, force=False, same_bg=False, occlude=False):
    """A character placed by the set: the dress redraws a character from her reference at the reference's own
    size and framing (Terra came back full-length and centred wherever the set had her cut by the frame), so
    the place is dressed WITHOUT her, and her picture is put in exactly where the set says she stands - her
    feet and head projected through the shot's camera, the view of her sheet nearest the camera's side of
    her, a soft shadow under her - for the start frame (and with `ends`, the last frame too)."""
    for sid in ids:
        s = fight.shot(sid)
        pz = s["previz"]
        info = json.load(open(os.path.join(pdir(sid), "previz.json")))
        n = info["frames"]
        # the characters: a set's choreography records each one's place at its first and last frames
        # (info["figures"]); a single statue comes from the shot's own figure_* keys
        figs = info.get("figures") or ([{
            "name": pz.get("figure_name", "figure"), "sheet": pz["figure_sheet"],
            "height": pz.get("figure_height", 1.66),
            "start": {"at": pz["figure_at"], "turn": pz.get("figure_turn", 0)},
            "end": {"at": pz["figure_at"], "turn": pz.get("figure_turn", 0)}}] if pz.get("figure_sheet") else [])
        # (no figures and no statue: nobody in the shot - ember-thief 120, the pendant alone in the sky)
        empty, chosen = {}, {}
        for tag, f in [("start", 1)] + ([("end", n)] if ends else []):
            d = os.path.join(pdir(sid), "%s720_empty" % tag)
            bg_src = os.path.join(d, "frames", "f_%04d.png" % (1 if tag == "start" else n))
            if not os.path.exists(bg_src) or force:
                place = {k: v for k, v in pz.items() if not k.startswith("figure")}
                place.update({"masks": 0, "hide_figures": 1} if tag == "end" else {"frames": 1, "masks": 0, "hide_figures": 1})
                _run(ps.blender_cmd(dict(s, previz=place), d) + ["--height=720", "--depth=1"])
            labels = sm.Truth(fight.FILM, sid).surf(f)[0]
            empty[tag] = bg_src
            dpng = os.path.join(d, "depth", "d_%04d.png" % (1 if tag == "start" else n))
            # opt-in: the painter can leave out what the depth says stands in front of her (E07's fallen oak),
            # and she would vanish behind a trunk nobody can see
            depth = _depth_m(dpng) if occlude and os.path.exists(dpng) else None
            if tag == "end" and same_bg and chosen.get("start") and _still_place(pz, empty["start"], bg_src):
                # the camera stands still and nothing in the place has moved: both frames are the same painting,
                # so the take cannot morph one painting into another (dressed apart, a still shot's two frames
                # came back as different woods - forest-duel E01, 2026-10-01)
                bg = chosen["start"]
            else:
                cands = {}
                for q in seeds:
                    p = os.path.join(OUT, "bg_%s_%s_s%d.png" % (sid, tag, q))
                    if not os.path.exists(p) or force:
                        if not dress_one(bg_src, p, q, (pz.get("dress_place") or "") + " " + (pz.get("grade") or fight.GRADE)):
                            continue
                    cands[p] = sm.fit(sm.to704(Image.open(p)), labels)
                if not cands:
                    continue
                bg = max(cands, key=cands.get)
            chosen[tag] = bg
            cam = info["camera"][f - 1]
            out = Image.open(bg)
            said = []
            # the farthest character first, so a nearer one stands in front of it
            for fg in sorted(figs, key=lambda q: -math.dist(cam["cam"], q[tag]["at"])):
                if fg[tag].get("hidden"):
                    # out of the shot at this end (a close-up on the other one; thrown out of the clearing)
                    continue
                at = fg[tag]["at"]
                feet = _project(cam["cam"], cam["look"], cam["lens"], at)
                head = _project(cam["cam"], cam["look"], cam["lens"], (at[0], at[1], at[2] + fg["height"]))
                face = 180.0 - float(fg[tag]["turn"])
                rel = (math.degrees(math.atan2(cam["cam"][0] - at[0], cam["cam"][1] - at[1])) - face + 540) % 360 - 180
                view = min(VIEWS8, key=lambda a: abs(((rel - a[0] + 540) % 360) - 180))[1]
                occ = (depth, _view_z(cam["cam"], cam["look"], at)) if depth is not None else None
                out = _paste(out, _cut(fg["sheet"], view), feet, feet[1] - head[1], occlude=occ)
                said.append("%s %s %d px at (%d, %d), camera %+.0f deg" % (fg["name"], view, feet[1] - head[1],
                                                                            feet[0], feet[1], rel))
            dst = os.path.join(OUT, "anchor_%s.png" % sid if tag == "start" else "anchor_%s_end.png" % sid)
            sm.to704(out).save(dst)
            print("  %s %-5s <- %s + %s" % (sid, tag, os.path.basename(bg), "; ".join(said)), flush=True)


def stage_draw(seeds):
    for s in fight.SHOTS:
        t0 = time.time()
        r = subprocess.run(["python3", os.path.join(TOOLS, "previz_shot.py"), "--sequence", fight.FILM,
                            "--shot", s["id"], "--seeds"] + [str(q) for q in seeds] + ["--bypass-seeds"],
                           capture_output=True, text=True)
        lines = [l for l in r.stdout.splitlines() if "motion r=" in l or "FAILED" in l or "DONE" in l]
        print("  %s  %.0fs  %s" % (s["id"], time.time() - t0, " | ".join(l.strip() for l in lines)), flush=True)
        if r.returncode != 0:
            print(r.stdout[-1200:], r.stderr[-1200:], flush=True)


def h3_len(frames):
    """A set shot's frame count rounded up to H3's 17n+5."""
    return 17 * max(1, -(-(frames - 6) // 17)) + 5


def anchors(sid):
    return os.path.join(OUT, "anchor_%s.png" % sid), os.path.join(OUT, "anchor_%s_end.png" % sid)


def keydir(sid):
    return os.path.join(OUT, "keys_%s" % sid)


def key_file(sid, at, seed, kind=""):
    """keys_<id>/k<at>_s<seed>.png - the graded key a take anchors; kind "raw" / "erased" for its steps."""
    tag = "end" if at == "end" else "k%d" % int(at)
    return os.path.join(keydir(sid), "%s%s_s%d.png" % (tag, "_" + kind if kind else "", int(seed)))


def _detail(p):
    """Fine detail: mean absolute Laplacian of the grey frame at 640 px. On some frames one seed of the editor
    repaints the WHOLE frame in a more detailed hand - its seed's doing on that frame, not the words' (workflow 80
    samples at CFG 1, so no negative prompt reaches it: a different negative gave the identical picture)."""
    import cv2
    import numpy as np
    g = cv2.cvtColor(cv2.resize(cv2.imread(p), (640, 352)), cv2.COLOR_BGR2GRAY).astype(np.float32)
    return float(np.abs(cv2.Laplacian(g, cv2.CV_32F)).mean())


def _graded(src, ref, dst):
    """src graded to ref, LAB mean and spread: a second edit pass adds contrast."""
    import cv2
    import numpy as np
    k = cv2.cvtColor(cv2.imread(src), cv2.COLOR_BGR2LAB).astype(np.float32)
    r = cv2.cvtColor(cv2.resize(cv2.imread(ref), k.shape[1::-1]), cv2.COLOR_BGR2LAB).astype(np.float32)
    out = (k - k.mean((0, 1))) / (k.std((0, 1)) + 1e-6) * r.std((0, 1)) + r.mean((0, 1))
    cv2.imwrite(dst, cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR))
    return dst


def stage_key(ids, seeds, force=False):
    for s in fight.SHOTS:
        if (ids and s["id"] not in ids) or not s.get("keys"):
            continue
        sid = s["id"]
        start, end = anchors(sid)
        os.makedirs(keydir(sid), exist_ok=True)
        rows = []
        for k in s["keys"]:
            row = []
            frm = k.get("from", "start")
            for q in seeds:
                base = start if frm == "start" else end if frm == "end" else \
                    key_file(sid, frm, next(x for x in s["keys"] if x["at"] == frm).get("seed", q))
                dst, raw = key_file(sid, k["at"], q), key_file(sid, k["at"], q, "raw")
                if force or not os.path.exists(dst):
                    t0 = time.time()
                    src = base
                    if k.get("erase"):
                        src = key_file(sid, k["at"], q, "erased")
                        dress_one(base, src, q, k["erase"])
                        sm.to704(Image.open(src)).save(src)
                    dress_one(src, raw, q, k["pose"])
                    sm.to704(Image.open(raw)).save(raw)
                    painted = raw
                    fxs = k.get("fx") or []
                    for i, fx in enumerate([fxs] if isinstance(fxs, str) else fxs):
                        # a second edit for the battle dialect: a dense flurry's keys went calm without it, and
                        # the flash at the contact only kept the energy on the hits (LTX_PLAYBOOK §100.10); a list
                        # runs in order - e.g. the flash, then the copy of a character a pose left behind removed
                        nxt = key_file(sid, k["at"], q, "fxraw" if i == 0 else "fxraw%d" % (i + 1))
                        dress_one(painted, nxt, q, fx)
                        sm.to704(Image.open(nxt)).save(nxt)
                        painted = nxt
                    _graded(painted, start, dst)
                    print("  %s key %s s%d %4.0fs" % (sid, k["at"], q, time.time() - t0), flush=True)
                # 2026-10-01, judged by eye: restyled keys x4.4-5.9 their source's detail, kept ones x0.9-2.6
                ratio = _detail(raw) / _detail(base)
                row.append((dst, "key %s s%d   detail x%.2f%s" % (k["at"], q, ratio,
                                                                 "  RESTYLED?" if ratio > 3.5 else "")))
            rows.append(row)
        paths = [p for row in rows for p, _ in row]
        board(paths, os.path.join(keydir(sid), "keys.jpg"), [lab for row in rows for _, lab in row])
        print("  %s: keys -> %s (set each key's \"seed\" in the shot script)" % (
            sid, os.path.join(keydir(sid), "keys.jpg")), flush=True)


def stage_take(ids, seeds, force=False):
    for s in fight.SHOTS:
        if ids and s["id"] not in ids:
            continue
        sid = s["id"]
        start, end = anchors(sid)
        if not (os.path.exists(start) and os.path.exists(end)):
            print("  %s: no frames yet (cast --ends)" % sid, flush=True)
            continue
        keys = s.get("keys", [])
        if any("seed" not in k for k in keys):
            print("  %s: a key has no picked seed - look at keys_%s/keys.jpg" % (sid, sid), flush=True)
            continue
        n = h3_len(int(s["previz"]["frames"]))
        for k in keys:
            if k["at"] == "end":
                end = key_file(sid, "end", k["seed"])
        for q in seeds:
            dst = os.path.join(OUT, "%s_%s_s%d.mp4" % ("h3k" if keys else "h3f", sid, q))
            if os.path.exists(dst) and not force:
                continue
            tag = "set_take_%s_s%d" % (sid, q)
            wf = {k: v for k, v in fight.load_wf("65_minimax_h3_fl_turbo_v4.json").items()
                  if isinstance(v, dict) and "class_type" in v}
            for node, p, name in (("8", start, "a"), ("9", end, "b")):
                shutil.copy(p, os.path.join(fight.COMFY, "input", "%s_%s.png" % (tag, name)))
                wf[node]["inputs"]["image"] = "%s_%s.png" % (tag, name)
            wf["20"]["inputs"].update({"prompt": s["prompt"], "width": 1280, "height": 704, "length": n})
            prev = ["20", 0]
            for i, k in enumerate(x for x in keys if x["at"] != "end"):
                name = "%s_k%d.png" % (tag, i)
                shutil.copy(key_file(sid, k["at"], k["seed"]), os.path.join(fight.COMFY, "input", name))
                wf["k%d" % i] = {"class_type": "LoadImage", "inputs": {"image": name}}
                wf["g%d" % i] = {"class_type": "MiniMaxH3AddGuide",
                                 "inputs": {"positive": prev, "latent": ["20", 1], "vae": ["3", 0],
                                            "frame_idx": min(int(k["at"]), n - 1), "image": ["k%d" % i, 0]}}
                prev = ["g%d" % i, 0]
            wf["30"]["inputs"]["conditioning"] = prev
            wf["33"]["inputs"]["noise_seed"] = int(q)
            wf["51"]["inputs"]["filename_prefix"] = "claude-generated/fight/" + tag
            fight.wait_for_queue()
            ps._room(26.0, 240)
            t0 = time.time()
            ok = fight.collect(fight.submit(wf, tag), dst, kinds=(".mp4",))
            print("  %s s%d %d keys %4.0fs %s" % (sid, q, len(keys), time.time() - t0, "ok" if ok else "FAILED"),
                  flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["render", "plate", "dress", "match", "draw", "ends", "pin", "cast", "key",
                                      "take"])
    ap.add_argument("--ends", action="store_true", help="cast: the last frame too (for a pinned move)")
    ap.add_argument("--same-bg", action="store_true",
                    help="cast --ends: a still camera over an unchanged place gets one painting for both frames")
    ap.add_argument("--occlude", action="store_true",
                    help="cast: hide a character where the set's depth is nearer the camera than she is")
    ap.add_argument("--apply", action="store_true", help="match: make the matched frames the start frames")
    ap.add_argument("--only", nargs="*", default=[], help="ends/pin: these shots")
    ap.add_argument("--sequence", required=True)
    ap.add_argument("--seeds", type=int, nargs="+", default=None)
    ap.add_argument("--pick", type=int, default=0)
    ap.add_argument("--also", nargs="*", default=[])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.stage == "render":
        stage_render(only=a.only, force=a.force)
    elif a.stage == "plate":
        stage_plate(a.seeds or [11, 202, 3003, 4242], a.pick, a.also)
    elif a.stage == "dress":
        stage_dress(tuple(a.seeds or (11, 202, 3003)), a.force)
    elif a.stage == "match":
        stage_match(a.apply)
    elif a.stage == "ends":
        stage_ends(a.only, tuple(a.seeds or (11, 202, 3003)), a.force)
    elif a.stage == "pin":
        stage_pin(a.only, a.seeds or [11, 202])
    elif a.stage == "cast":
        stage_cast(a.only, tuple(a.seeds or (11, 202, 3003)), a.ends, a.force, a.same_bg, a.occlude)
    elif a.stage == "key":
        stage_key(a.only, tuple(a.seeds or (11, 202)), a.force)
    elif a.stage == "take":
        stage_take(a.only, tuple(a.seeds or (11, 202)), a.force)
    else:
        stage_draw(a.seeds or [11, 202])


if __name__ == "__main__":
    main()
