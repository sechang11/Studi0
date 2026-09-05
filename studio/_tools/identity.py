#!/usr/bin/env python3
"""Is it still the same person?  Measured with the encoder the box already has.

There is no face detector on this box (checked: cv2 has none, insightface,
facexlib, mediapipe absent).  What there is: the pack's portrait, the compose
geometry that says where the figure stands, and CLIP-ViT-H (ComfyUI's own
clip_vision loader, run on CPU so a render is never disturbed).

For a take:
    start  cosine(portrait, head crop of the first frame)   - did the composite keep the face?
    end    cosine(portrait, head crop of the last frame)    - did the engine keep it?
    hold   cosine(first-frame head, last-frame head)        - how much the head changed
The head box comes from the shot's anchor_source (stand, cx) through the
plate's depth pass, or, for a close-up, from the portrait placement; the last
frame's box is the first frame's box carried through the measured camera.

Calibrated 2026-09-05 00:04 on 14 packs: portrait vs own front-view head
median 0.77 (min 0.40 with a crude crop); different people median 0.31
(max 0.78 for two drawn characters who share a face by design).  Read:
  >= 0.62 same person, 0.50-0.62 uncertain, < 0.50 a different face.

Run with ComfyUI's python (torch):
    ~/ComfyUI/venv/bin/python identity.py jobs.json      -> results.json beside it
jobs.json: [{"portrait": ..., "video": ..., "box": [x0,y0,x1,y1] fractions or null,
             "close": bool, "cam": {"zoom":..,"pan":..,"tilt":..} or null, "id": ...}]
"""
import json
import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
COMFY = os.path.expanduser("~/ComfyUI")
sys.path.insert(0, COMFY)
import numpy as np  # noqa: E402
import torch  # noqa: E402
from comfy.cli_args import args as _cargs  # noqa: E402
_cargs.cpu = True
import comfy.model_management  # noqa: E402,F401
import comfy.clip_vision as cv  # noqa: E402
from PIL import Image  # noqa: E402
import io as _io  # noqa: E402
import subprocess  # noqa: E402

MODEL = os.path.join(COMFY, "models", "clip_vision", "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors")
SAME, UNSURE = 0.62, 0.50
_M = None


def model():
    global _M
    if _M is None:
        _M = cv.load(MODEL)
    return _M


def embed(im):
    im = im.convert("RGB").resize((336, 336))
    t = torch.from_numpy(np.asarray(im).astype(np.float32) / 255.0)[None]
    with torch.no_grad():
        out = model().encode_image(t)
    v = out.image_embeds if getattr(out, "image_embeds", None) is not None else out.penultimate_hidden_states.mean(1)
    v = v.float().flatten()
    return v / v.norm()


def _frame(path, args):
    p = subprocess.run(["ffmpeg", "-v", "error"] + args + ["-i", path, "-frames:v", "1", "-f", "image2pipe",
                        "-vcodec", "png", "-"], capture_output=True).stdout
    return Image.open(_io.BytesIO(p)).convert("RGB") if p else None


def frames_first_last(path):
    """first and last frames over ffmpeg pipes (ComfyUI's python has no cv2)"""
    first = _frame(path, [])
    last = _frame(path, ["-sseof", "-0.15"]) or _frame(path, ["-sseof", "-0.5"])
    return first, last


def carry_box(box, cam):
    """the first frame's box after the measured camera: zoom about the centre, then pan/tilt"""
    if not cam:
        return box
    z = float(cam.get("zoom", 1.0) or 1.0)
    pan, tilt = float(cam.get("pan", 0.0) or 0.0), float(cam.get("tilt", 0.0) or 0.0)
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = (x1 - x0) * z, (y1 - y0) * z
    cx = 0.5 + (cx - 0.5) * z - pan
    cy = 0.5 + (cy - 0.5) * z - tilt
    return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]


def crop(im, box):
    W, H = im.size
    x0, y0, x1, y1 = box
    x0, x1 = sorted((max(0.0, min(1.0, x0)), max(0.0, min(1.0, x1))))
    y0, y1 = sorted((max(0.0, min(1.0, y0)), max(0.0, min(1.0, y1))))
    if x1 - x0 < 0.03 or y1 - y0 < 0.03:
        return None
    return im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))


def verdict(s):
    if s is None:
        return "unmeasured"
    if s >= SAME:
        return "same person"
    if s >= UNSURE:
        return "uncertain"
    return "a different face"


def run(job):
    out = {"id": job.get("id")}
    try:
        portrait = Image.open(job["portrait"])
        first, last = frames_first_last(job["video"])
        if first is None:
            return {**out, "error": "could not decode the video"}
        box = job.get("box") or ([0.28, 0.02, 0.72, 0.62] if job.get("close") else [0.35, 0.05, 0.65, 0.45])
        c0 = crop(first, box)
        if c0 is None:
            return {**out, "error": "the head box left the frame"}
        cam = job.get("cam") or {}
        cb = carry_box(box, cam)
        # how much of the carried box is still inside the frame
        ix0, iy0, ix1, iy1 = max(0.0, cb[0]), max(0.0, cb[1]), min(1.0, cb[2]), min(1.0, cb[3])
        inside = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0) / max(1e-6, (cb[2] - cb[0]) * (cb[3] - cb[1]))
        too_far = float(cam.get("zoom", 1.0) or 1.0) > 1.6 or inside < 0.6
        c1 = None if too_far else crop(last, cb)
        p, e0 = embed(portrait), embed(c0)
        start = float((p * e0).sum())
        out.update({"start": round(start, 3), "verdict_start": verdict(start), "box": [round(b, 3) for b in box]})
        if c1 is None:
            out.update({"end": None, "hold": None, "verdict_end": "unmeasured (the camera moved too much to follow the head)"})
        else:
            e1 = embed(c1)
            end, hold = float((p * e1).sum()), float((e0 * e1).sum())
            out.update({"end": round(end, 3), "hold": round(hold, 3), "verdict_end": verdict(end)})
        return out
    except Exception as e:
        return {**out, "error": str(e)[:160]}


if __name__ == "__main__":
    src = sys.argv[1]
    jobs = json.load(open(src, encoding="utf-8"))
    res = [run(j) for j in jobs]
    dst = sys.argv[2] if len(sys.argv) > 2 else src[:-5] + "_results.json"
    json.dump(res, open(dst, "w", encoding="utf-8"), indent=1)
    for r in res:
        print(json.dumps(r))
