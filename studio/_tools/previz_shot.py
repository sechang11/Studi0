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


def dress(s, pv_frame, dst, seed):
    """The previz frame, dressed as the film: previz first (the canvas), then the plate, then cast."""
    chars = fight._unique([r for r in s["refs"] if r in fight.CAST])
    pics = [pv_frame, os.path.join(fight.OUT, "ref_%s.png" % fight.PLACE_ID)] + \
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
    who = ""
    if chars:
        who = (" The grey standing figure far down the aisle is the man of <image3>, small in the "
               "distance.")
    wf["6"]["inputs"]["prompt"] = (
        "Turn <image1> into a still frame from a live-action film. Keep the camera, the perspective and "
        "the layout of <image1> exactly: every box stays exactly where it is. The brown boxes are "
        "towering stacks of old wooden shipping crates with stencilled planks and iron corners; the flat "
        "grey floor is the wet cracked concrete of the warehouse of <image2>, with its puddles, its "
        "hanging sodium lamps and the rain on its skylights; the far wall is the warehouse's far end in "
        "shadow." + who + " " + fight.GRADE)
    wf["6"]["inputs"]["negative_prompt"] = fight.AVOID + ", grey boxes, untextured, 3d render, cgi"
    wf["10"]["inputs"]["seed"] = int(seed)
    wf["12"]["inputs"]["filename_prefix"] = "claude-generated/fight/pv_dress_%s_s%d" % (s["id"], seed)
    if fight.collect(fight.submit(wf, "dress %s s%d" % (s["id"], seed)), dst):
        return fight._to_canvas(dst, (1280, 704))
    return None


def draw(s, pv_video, frames, start, seed, dst, bypass):
    wf = nm.load_wf("74_ltx23_ic_lora_control.json")
    shutil.copy(pv_video, os.path.join(COMFY, "input", "iclora_control.mp4"))
    if start:
        shutil.copy(start, os.path.join(COMFY, "input", "iclora_start.png"))
    wf["sg1_128"]["inputs"]["text"] = s["prompt"]
    wf["sg1_112"]["inputs"]["text"] = fight.AVOID
    wf["sg1_704"]["inputs"]["seed"] = int(seed)
    wf["sg1_198"]["inputs"]["bypass"] = bool(bypass)
    wf["sg1_108"]["inputs"]["length"] = frames
    wf["sg1_101"]["inputs"]["frames_number"] = frames
    wf["sg1_114"]["inputs"]["value"] = 24
    wf["68"]["inputs"]["filename_prefix"] = "claude-generated/fight/%s_%s_s%d" % (
        "pvb" if bypass else "pv", s["id"], seed)
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
        r = subprocess.run(["python3", os.path.join(TOOLS, "previz_blender.py"), "--out", pdir,
                            "--scene", pz.get("scene", "aisle"), "--seconds", str(pz.get("seconds", s["secs"])),
                            "--fps", "24"], capture_output=True, text=True)
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

    # 2. dress: two seeds, the anchor is the first (look at both on the board)
    import post
    post.make_room(need_gb=20.0, budget=180)
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
    post.make_room(need_gb=26.0, budget=240)
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
            rep["takes"].append({"take": os.path.basename(v), "secs": round(secs, 1),
                                 "frames": nm.nframes(v)[0], "motion": ma})
            print("  %-22s %4.0fs  motion r=%s" % (os.path.basename(v), secs, ma.get("r")), flush=True)
    json.dump(rep, open(os.path.join(out, "previz_%s.json" % s["id"]), "w"), indent=1)
    print("PREVIZ SHOT DONE", flush=True)


if __name__ == "__main__":
    main()
