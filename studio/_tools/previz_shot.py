#!/usr/bin/env python3
"""studio/_tools/previz_shot.py - a shot whose physics is choreographed, not hoped for.

A shot-script shot with `"engine": "previz"` and `"previz": {"scene": ..., "seconds": ...}` is built
in three steps, and the take lands in the film folder as pv_<id>_s<seed>.mp4 so fight.py --finish
takes it with a pick like `070=pv:202`:

  1. SIMULATE   previz_blender.py renders the beat in Blender with rigid bodies and proxy geometry:
                where every crate lands, and when, is decided here. (Blender 5.2, headless.)
  2. DRESS      the simulation's FIRST frame becomes a photoreal start frame: Qwen-Image-2.1 (workflow
                80) is handed the previz frame as <image1> - so the canvas and the layout are the
                simulation's - with the place's plate and the cast as further references, and told to
                keep every box where it is. This is what makes the shot match the rest of the film.
  3. DRAW       LTX-2.3 with the IC-LoRA union control (workflow 74) reads the previz's DEPTH (MoGe) as
                a guide and starts on the dressed frame: the engine paints, the simulation moves.
                Arm `pv` uses the dressed start frame; arm `pvb` bypasses it (the 2026-09-27 route,
                measured r 0.84 / 0.71), kept as the fallback.

    python3 studio/_tools/previz_shot.py --sequence dead-stock --shot 070 --seeds 11 202 3003

Measured on each take: motion agreement (Pearson r of frame-to-frame energy) against the previz.

A camera move is previz too (previz_blender.py --scene street / canyon / orbit): the shot's "previz" block
carries the move (radius, lens, cam_z, look_z and their *_to ends; figure_glb, the figure's real shape
from her character sheet), and "reverse": true also writes pvr_<id>_s<seed>.mp4, the take backwards.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.expanduser("~/shared/comfy-studio")
TOOLS = os.path.join(ROOT, "studio", "_tools")
sys.path.insert(0, TOOLS)
import fight                                  # noqa: E402  (reads --sequence off argv)
import newmodels_test as nm                   # noqa: E402

COMFY = fight.COMFY
CAMERA_KEYS = ("degrees", "radius", "radius_to", "lens", "lens_to", "cam_z", "cam_z_to", "look_z", "look_z_to",
               "figure_glb", "figure_turn")


def _room(gb, budget):
    """Free VRAM before a big graph - unless asking torch how much is free is itself what fails (a new
    CUDA context on a full card): ComfyUI manages its own memory, so the draw goes ahead."""
    import post
    try:
        post.make_room(need_gb=gb, budget=budget)
    except Exception as e:
        print("  (make_room skipped: %s)" % str(e).splitlines()[0][:80], flush=True)


def reverse(src, dst):
    """A take played backwards - for a move that can only be drawn the other way round: a tilt UP to a
    face is drawn as a tilt DOWN from a start frame composed from her references, so the face the move
    ends on is hers, not one the engine invented on the way up."""
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vf", "reverse", "-af", "areverse",
                    "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", dst],
                   check=True)
    return dst


def dress_words(s, chars):
    """What the grey simulation becomes: the shot's own `previz.dress` (written for its place), or a
    general one - the proxies are crates, the rest is the place of <image2>, the figure <image3>."""
    pz = s.get("previz") or {}
    if pz.get("dress"):
        return pz["dress"].strip()
    who = " The grey standing figure is the person of <image3>." if chars else ""
    return ("Turn <image1> into a still frame from a live-action film. Keep the camera, the perspective and "
            "the layout of <image1> exactly: every box stays exactly where it is. The brown boxes are old "
            "wooden crates with stencilled planks and iron corners; the flat grey floor, the walls and the "
            "light are those of the place of <image2>." + who)


def dress(s, pv_frame, dst, seed):
    """The previz frame, dressed as the film: previz first (the canvas), then the plate, then cast."""
    # the shot's own place - the plate, or a second place the cast marks "place": true - is <image2>
    places = [r for r in s["refs"] if r == fight.PLACE_ID or (fight._seq["cast"].get(r) or {}).get("place")]
    place = places[0] if places else fight.PLACE_ID
    chars = fight._unique([r for r in s["refs"] if r in fight.CAST and r not in places])
    pics = [pv_frame, os.path.join(fight.OUT, "ref_%s.png" % place)] + \
           [os.path.join(fight.OUT, "ref_%s.png" % c) for c in chars]
    wf = {k: v for k, v in fight.load_wf("80_qwen21_edit_refs.json").items()
          if isinstance(v, dict) and "class_type" in v}
    for k in ("21", "22", "23"):
        wf.pop(k, None)
    for k in list(wf["6"]["inputs"]):
        if k.startswith("images."):
            del wf["6"]["inputs"][k]
    for i, p in enumerate(pics, 1):
        name = "pv_dress_%d.png" % i
        shutil.copy(p, os.path.join(COMFY, "input", name))
        wf["d%d" % i] = {"class_type": "LoadImage", "inputs": {"image": name}}
        wf["6"]["inputs"]["images.image_%d" % i] = ["d%d" % i, 0]
    wf["6"]["inputs"]["prompt"] = dress_words(s, chars) + " " + ((s.get("previz") or {}).get("grade") or fight.GRADE)
    wf["6"]["inputs"]["negative_prompt"] = fight.AVOID + ", grey boxes, untextured, 3d render, cgi"
    wf["10"]["inputs"]["seed"] = int(seed)
    wf["12"]["inputs"]["filename_prefix"] = "claude-generated/fight/pv_dress_%s_s%d" % (s["id"], seed)
    if fight.collect(fight.submit(wf, "dress %s s%d" % (s["id"], seed)), dst):
        return fight._to_canvas(dst, (1280, 704))
    return None


def draw(s, pv_video, frames, start, seed, dst, bypass, end=None, stem=None):
    wf = nm.load_wf("74_ltx23_ic_lora_control.json")
    # inputs named for this take: two drivers drawing at once (a chain and a shot) must not read each
    # other's control video or start frame out of ComfyUI's input folder
    tag = "%s_s%d" % (s["id"], seed)
    shutil.copy(pv_video, os.path.join(COMFY, "input", "iclora_control_%s.mp4" % tag))
    wf["199"]["inputs"]["file"] = "iclora_control_%s.mp4" % tag
    if start:
        shutil.copy(start, os.path.join(COMFY, "input", "iclora_start_%s.png" % tag))
        wf["200"]["inputs"]["image"] = "iclora_start_%s.png" % tag
    wf["sg1_128"]["inputs"]["text"] = s["prompt"]
    wf["sg1_112"]["inputs"]["text"] = fight.AVOID + (", " + s["avoid_extra"] if s.get("avoid_extra") else "")
    wf["sg1_704"]["inputs"]["seed"] = int(seed)
    wf["sg1_198"]["inputs"]["bypass"] = bool(bypass)
    wf["sg1_108"]["inputs"]["length"] = frames
    wf["sg1_101"]["inputs"]["frames_number"] = frames
    wf["sg1_114"]["inputs"]["value"] = 24
    if end:
        # the LAST frame pinned as well - a keyframe guide at frame -1 after the control guide, the way
        # the first-last workflow (72) pins its two frames: a piece that must start where one take ends
        # AND end where another begins (the seam where two halves of a chain meet)
        shutil.copy(end, os.path.join(COMFY, "input", "iclora_end_%s.png" % tag))
        wf["endimg"] = {"class_type": "LoadImage", "inputs": {"image": "iclora_end_%s.png" % tag}}
        wf["endg"] = {"class_type": "LTXVAddGuide", "inputs": {
            "frame_idx": -1, "strength": 1.0, "positive": ["sg1_115", 0], "negative": ["sg1_115", 1],
            "latent": ["sg1_115", 2], "vae": ["sg1_127", 2], "image": ["endimg", 0]}}
        for k, v in wf.items():
            if k == "endg" or not isinstance(v, dict):
                continue
            for name, src in v.get("inputs", {}).items():
                if isinstance(src, list) and len(src) == 2 and src[0] == "sg1_115":
                    v["inputs"][name] = ["endg", src[1]]
    wf["68"]["inputs"]["filename_prefix"] = "claude-generated/fight/%s_%s_s%d" % (
        stem or ("pvb" if bypass else "pv"), s["id"], seed)
    outs, secs = nm.submit(wf, "%s %s s%d" % ("pvb" if bypass else "pv", s["id"], seed))
    return nm.collect(outs, dst, kinds=(".mp4",)), secs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sequence", required=True)
    ap.add_argument("--shot", required=True)
    ap.add_argument("--seeds", type=int, nargs="+", default=[11, 202, 3003])
    ap.add_argument("--bypass-seeds", type=int, nargs="*", default=[11, 202])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    s = fight.shot(a.shot)
    pz = s.get("previz") or {}
    out = fight.OUT
    pdir = os.path.join(out, "previz_%s" % s["id"])
    pv = os.path.join(pdir, "previz.mp4")
    rep = {"shot": s["id"], "scene": pz.get("scene"), "takes": []}

    # 1. simulate
    if not os.path.exists(pv) or a.force:
        t0 = time.time()
        cmd = ["python3", os.path.join(TOOLS, "previz_blender.py"), "--out", pdir,
               "--scene", pz.get("scene", "aisle"), "--seconds", str(pz.get("seconds", s["secs"])), "--fps", "24"]
        for k in CAMERA_KEYS:                   # a camera move's own settings (previz_blender.py --help)
            if k in pz:
                v = pz[k]
                if k == "figure_glb" and not os.path.isabs(v):
                    v = os.path.join(ROOT, v)
                cmd += ["--" + k.replace("_", "-"), str(v)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        print(r.stdout[-600:], r.stderr[-600:], flush=True)
        if not os.path.exists(pv):
            sys.exit("the previz did not render")
        print("  previz %.0fs -> %s" % (time.time() - t0, pv), flush=True)
    info = json.load(open(os.path.join(pdir, "previz.json")))
    frames, _ = nm.nframes(pv)
    rep["previz"] = info
    nm.strip(pv, os.path.join(out, "previz_%s_strip.jpg" % s["id"]))
    f1 = os.path.join(pdir, "frame_first.png")
    nm.frame_at(pv, 0.0, f1)

    # 2. the start frame: a picture the film already has ("start" - e.g. the next shot's first frame, so the
    #    move lands exactly on it), or the simulation's first frame DRESSED as the film, two seeds
    if pz.get("start"):
        anchor = os.path.join(out, pz["start"])
        rep["start"] = pz["start"]
    else:
        import post
        _room(20.0, 180)
        dressed = []
        for q in (11, 202):
            p = os.path.join(out, "anchor_%s_pvdress_s%d.png" % (s["id"], q))
            if not os.path.exists(p) or a.force:
                t0 = time.time()
                if not dress(s, f1, p, q):
                    print("  dress s%d FAILED" % q, flush=True)
                    continue
                print("  dress s%d %.0fs" % (q, time.time() - t0), flush=True)
            dressed.append(p)
        anchor = os.path.join(out, "anchor_%s.png" % s["id"])
        if dressed and (not os.path.exists(anchor) or a.force):
            shutil.copy(dressed[0], anchor)
        rep["dressed"] = [os.path.basename(p) for p in dressed]

    # 3. draw: with the dressed start frame, and (fallback) without
    _room(26.0, 240)
    for bypass, seeds in ((False, a.seeds), (True, a.bypass_seeds)):
        for q in seeds:
            stem = "pvb" if bypass else "pv"
            dst = os.path.join(out, "%s_%s_s%d.mp4" % (stem, s["id"], q))
            if os.path.exists(dst) and not a.force:
                print("  %s already there" % os.path.basename(dst), flush=True)
                v, secs = dst, 0.0
            else:
                v, secs = draw(s, pv, frames, None if bypass else anchor, q, dst, bypass)
            if not v:
                print("  %s FAILED" % os.path.basename(dst), flush=True)
                continue
            ma = nm.motion_agreement(pv, v)
            fight.strip(v, v[:-4] + "_strip.jpg")
            if pz.get("reverse"):               # the film takes the backwards one: "310=pvr:11"
                rv = reverse(v, os.path.join(out, "%sr_%s_s%d.mp4" % (stem, s["id"], q)))
                print("  %s  (reversed)" % os.path.basename(rv), flush=True)
            rep["takes"].append({"take": os.path.basename(v), "secs": round(secs, 1),
                                 "frames": nm.nframes(v)[0], "motion": ma})
            print("  %-22s %4.0fs  motion r=%s" % (os.path.basename(v), secs, ma.get("r")), flush=True)
    json.dump(rep, open(os.path.join(out, "previz_%s.json" % s["id"]), "w"), indent=1)
    print("PREVIZ SHOT DONE", flush=True)


if __name__ == "__main__":
    main()
