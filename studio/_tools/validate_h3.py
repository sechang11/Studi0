#!/usr/bin/env python3
"""studio/_tools/validate_h3.py - do workflows 83 (H3 multi-frame reference) and 84 (H3 Fun
ControlNet union, pose) RUN on this box, with our own pictures? One render each, a strip for
the eye, no claim about quality: the orphan rule (§0) asks that a downloaded weight be wired
and shown to run, with a date, and the pin battery (§29, §62) and the pose battery (§97.2) are
the measurements that would let either into the pipeline.

    ~/ComfyUI/venv/bin/python3 studio/_tools/validate_h3.py [--seed 11]

83: four frames of an existing take (shot_010_s11, ash-court) pinned at 0 / 1.5 / 3 / 3.9 s.
84: koval's H3 take (h3_010_s3003) as the pose source, the same words as its shot.
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
TOOLS = os.path.join(STUDIO, "_tools")
sys.path.insert(0, TOOLS)
import newmodels_test as nm   # noqa: E402  (submit, collect, strip, to_input, make_room)

FIGHT = os.path.join(STUDIO, "samples", "fight", "ash-court")
OUT = os.path.join(STUDIO, "samples", "newmodels-2026-09-27", "h3_validate")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    rep = {}
    nm.make_room(26)

    # ---- 83: multi-frame reference - four frames of one take, pinned where they came from
    src = os.path.join(FIGHT, "shot_010_s11.mp4")
    for i, t in enumerate((0.0, 1.5, 3.0, 3.9), 1):
        f = nm.frame_at(src, t, os.path.join(OUT, "pin_%d.png" % i))
        nm.to_input(f, "h3_frame_ref_%d.png" % i)
    wf = nm.load_wf("83_h3_multiframe.json")
    wf["138"]["inputs"]["value"] = (
        "subject_definitions:\n<Subject 1> is the young woman in <Picture 1>, very short dark hair, grey vest, "
        "hand wraps. <Subject 2> is the heavy bald man in <Picture 1>, long dark grey coat.\n"
        "<Picture 1> is the first frame of [Shot 1]; <Picture 2>, <Picture 3> and <Picture 4> are later "
        "frames of the same shot.\n[Shot 1] Inside a ruined stone arena at dawn, <Subject 1> and <Subject 2> "
        "face each other; he speaks a short line, she listens. Static camera. Ambient sound of a large empty "
        "hall; no music.")
    wf["132"]["inputs"]["value"] = 4.0            # seconds
    for nid, t in (("154", 1.5), ("160", 3.0), ("168", 3.9)):
        wf[nid]["inputs"]["value"] = t
    # the noise seed lives on a RandomNoise node
    for k, v in wf.items():
        if v["class_type"] == "RandomNoise":
            v["inputs"]["noise_seed"] = a.seed
    wf["92"]["inputs"]["filename_prefix"] = "claude-generated/h3_multiframe/validate_s%d" % a.seed
    t0 = time.time()
    outs, secs = nm.submit(wf, "83 multiframe")
    v = nm.collect(outs, os.path.join(OUT, "multiframe_s%d.mp4" % a.seed), kinds=(".mp4",))
    rep["83"] = {"ok": bool(v), "secs": round(secs, 1), "file": v,
                 "frames": nm.nframes(v)[0] if v else None,
                 "strip": nm.strip(v, os.path.join(OUT, "multiframe_s%d_strip.jpg" % a.seed)) if v else None}
    print("83 multiframe:", rep["83"], flush=True)

    # ---- 84: pose control from koval's take
    nm.to_input(os.path.join(FIGHT, "h3_010_s3003.mp4"), "dancer_field_pose.mp4")
    wf = nm.load_wf("84_h3_fun_control.json")
    wf["138"]["inputs"]["value"] = (
        "Inside a ruined circular stone arena at dawn, a heavy bald man in a long dark grey coat stands "
        "square and planted, arms folded, then unfolds them and steps forward once. Static camera. Ambient "
        "sound of a large empty hall; no music.")
    wf["132"]["inputs"]["value"] = 3.5
    for k, v in wf.items():
        if v["class_type"] == "RandomNoise":
            v["inputs"]["noise_seed"] = a.seed
    wf["707"]["inputs"]["filename_prefix"] = "claude-generated/h3_fun_control/validate_s%d" % a.seed
    outs, secs = nm.submit(wf, "84 fun control")
    v = nm.collect(outs, os.path.join(OUT, "fun_control_s%d.mp4" % a.seed), kinds=(".mp4",))
    rep["84"] = {"ok": bool(v), "secs": round(secs, 1), "file": v,
                 "frames": nm.nframes(v)[0] if v else None,
                 "strip": nm.strip(v, os.path.join(OUT, "fun_control_s%d_strip.jpg" % a.seed)) if v else None}
    print("84 fun control:", rep["84"], flush=True)
    json.dump(rep, open(os.path.join(OUT, "measured.json"), "w"), indent=1)
    print("summary ->", os.path.join(OUT, "measured.json"))


if __name__ == "__main__":
    main()
