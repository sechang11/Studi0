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
             "close": bool, "cam": {"zoom":..,"pan":..,"tilt":..} or null, "id": ...,
             "plate": <the scene's plate, optional -> place_hold/place_verdict/place_start>,
             "box_at": [[seconds, box], ...] - heads found in the picture at those moments;
                        the curve reads between them instead of carrying a box through the camera,
             "box_end": the head box in the LAST frame, found there rather than carried - see
                        _tools/headbox.py; when given, the camera curve is not used for it,
             "still": <a picture instead of a video> -> only `start` is measured,
    A head under MIN_HEAD_PX pixels comes back unmeasured rather than judged: measured by
    rendering one shot at two distances, 135 px of head scores 0.66 and 65 px scores 0.30 for
    the same person, so a verdict there is about the pixels and not about the face.
             "window0": {"zoom", "cx", "cy"} - the studio's post move at the first frame, so the
                        anchor-frame head box is carried into the cropped frame,
             "post_curve": [[zoom, cx, cy], ...] - the studio's own move window at nine
                        moments, used in preference to the measured camera because it is exact,
             "curve": true + "cam_curve": cammeasure's per-step [[zoom,pan,tilt], ...] ->
                        "hold_curve": the face scored at nine times through the clip, with
                        holds_until / lost_at in seconds}]
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
# Measured by rendering the same shot at two distances: at 135 px of head the face scores
# 0.655-0.675, at 65 px the same face scores 0.27-0.32.  Below this the encoder is looking at
# a smudge and any verdict it gives is about the pixels, not the person.
MIN_HEAD_PX = 100
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


def _frames_at(path, times):
    """decode one frame at each timestamp (seconds) over ffmpeg pipes"""
    out = []
    for t in times:
        out.append(_frame(path, ["-ss", "%.3f" % max(0.0, t)]))
    return out


def duration(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    try:
        return float(p)
    except Exception:
        return 0.0


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


def _between(anchors, t):
    """the box at time t, linearly between the found ones (and held at the ends)"""
    if t <= anchors[0][0]:
        return list(anchors[0][1])
    if t >= anchors[-1][0]:
        return list(anchors[-1][1])
    for (t0, b0), (t1, b1) in zip(anchors, anchors[1:]):
        if t0 <= t <= t1:
            f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return [b0[k] * (1 - f) + b1[k] * f for k in range(4)]
    return list(anchors[-1][1])


def hold_curve(job, box, portrait_emb, close, cam_curve, dur, n=9):
    """cosine against the portrait at n times through the clip, with the head box carried
    through the camera as measured AT THAT TIME (cammeasure's per-step [zoom, pan, tilt]).

    Returns {"times": [...], "scores": [...], "holds_until": seconds or None, "holds": bool}
    where holds_until is the last moment before the score falls below the band and stays
    below.  A face that is lost at 3.4 s of a 6 s take is not a take to throw away: it is a
    take to cut at 3.4 s, and this is the number that says where."""
    if dur <= 0:
        return None
    times = [dur * i / (n - 1) for i in range(n)]
    times[-1] = max(0.0, dur - 0.12)
    frames = _frames_at(job["video"], times)
    # boxes found in the picture beat boxes carried through a camera transform: a head does
    # not teleport, so a line between the ones we have is closer than a guess from the camera
    anchors = [(t, b) for t, b in (job.get("box_at") or []) if b]
    same, unsure = (SAME, UNSURE) if close else (0.56, 0.46)
    scores, kept = [], []
    for i, (t, im) in enumerate(zip(times, frames)):
        if im is None:
            scores.append(None)
            continue
        if anchors:
            b = _between(anchors, t)
            cr = crop(im, b)
            if cr is None:
                scores.append(None)
                continue
            sc = float((portrait_emb * embed(cr)).sum())
            scores.append(round(sc, 3))
            kept.append((t, sc))
            continue
        pw = job.get("post_curve")
        if pw:
            # the studio's own window, sampled at nine moments: a source point (x, y) shows
            # at ((x - cx) * zoom + 0.5, (y - cy) * zoom + 0.5)
            u = (t / dur) if dur else 0.0
            pos = u * (len(pw) - 1)
            j2 = int(pos)
            f2 = pos - j2
            if j2 >= len(pw) - 1:
                zz, cxx, cyy = pw[-1]
            else:
                a2, b3 = pw[j2], pw[j2 + 1]
                zz, cxx, cyy = [a2[k] * (1 - f2) + b3[k] * f2 for k in range(3)]
            b = [(box[0] - cxx) * zz + 0.5, (box[1] - cyy) * zz + 0.5,
                 (box[2] - cxx) * zz + 0.5, (box[3] - cyy) * zz + 0.5]
        elif close or not cam_curve:
            b = list(box)
        else:
            # cam_curve is sampled evenly over the clip; read it at this fraction
            u = (t / dur) if dur else 0.0
            pos = u * (len(cam_curve) - 1)
            j = int(pos)
            f = pos - j
            if j >= len(cam_curve) - 1:
                c = cam_curve[-1]
            else:
                a, b2 = cam_curve[j], cam_curve[j + 1]
                c = [a[k] * (1 - f) + b2[k] * f for k in range(3)]
            b = carry_box(box, {"zoom": c[0], "pan": c[1], "tilt": c[2]})
        cr = crop(im, b)
        if cr is None:
            scores.append(None)
            continue
        sc = float((portrait_emb * embed(cr)).sum())
        scores.append(round(sc, 3))
        kept.append((t, sc))
    # how long it holds: walk from the end back while the score is under the "same" band
    holds_until, lost_at = None, None
    good = [(t, sc) for t, sc in kept if sc >= unsure]
    if kept:
        last_good = None
        for t, sc in kept:
            if sc >= unsure:
                last_good = t
            elif last_good is not None and all(s2 < unsure for t2, s2 in kept if t2 > t):
                lost_at = t
                break
        holds_until = last_good
    return {"times": [round(t, 2) for t in times], "scores": scores,
            "holds_until": round(holds_until, 2) if holds_until is not None else None,
            "lost_at": round(lost_at, 2) if lost_at is not None else None,
            "holds": bool(kept) and all(sc >= unsure for _, sc in kept),
            "duration": round(dur, 2)}


def verdict(s, close=False):
    """the bands depend on how big the head is: in a wide or medium framing the head crop is
    a few dozen pixels and the same person scores 0.56-0.72 against the portrait (measured on
    composed anchors, where the face is the portrait by construction); in a close-up 0.74-0.78"""
    if s is None:
        return "unmeasured"
    same, unsure = (SAME, UNSURE) if close else (0.56, 0.46)
    if s >= same:
        return "same person"
    if s >= unsure:
        return "uncertain"
    return "a different face"


def run(job):
    out = {"id": job.get("id")}
    try:
        portrait = Image.open(job["portrait"])
        if job.get("still"):
            # an anchor is a picture, and scoring it costs a second against the minutes a
            # render costs.  Same box, same crop, same encoder - only the source differs.
            im = Image.open(job["still"]).convert("RGB")
            box = job.get("box") or ([0.28, 0.02, 0.72, 0.62] if job.get("close") else [0.35, 0.05, 0.65, 0.45])
            c = crop(im, box)
            if c is None:
                return {**out, "error": "the head box left the picture"}
            v = float((embed(portrait) * embed(c)).sum())
            return {**out, "start": round(v, 3), "verdict_start": verdict(v, job.get("close")),
                    "box": [round(b, 3) for b in box], "still": True}
        first, last = frames_first_last(job["video"])
        if first is None:
            return {**out, "error": "could not decode the video"}
        box = job.get("box") or ([0.28, 0.02, 0.72, 0.62] if job.get("close") else [0.35, 0.05, 0.65, 0.45])
        w0 = job.get("window0")
        if w0 and float(w0.get("zoom", 1.0) or 1.0) != 1.0 or (w0 and (abs(float(w0.get("cx", 0.5)) - 0.5) > 1e-3 or abs(float(w0.get("cy", 0.5)) - 0.5) > 1e-3)):
            # the studio's move cropped the first frame: a source point (x, y) shows at
            # ((x - cx) * zoom + 0.5, (y - cy) * zoom + 0.5); carry the anchor-frame box there
            z, cx, cy = float(w0.get("zoom", 1.0) or 1.0), float(w0.get("cx", 0.5)), float(w0.get("cy", 0.5))
            box = [(box[0] - cx) * z + 0.5, (box[1] - cy) * z + 0.5, (box[2] - cx) * z + 0.5, (box[3] - cy) * z + 0.5]
        c0 = crop(first, box)
        if c0 is None:
            return {**out, "error": "the head box left the frame"}
        head_px = min(c0.size)
        if head_px < MIN_HEAD_PX:
            # not a verdict: the head is too few pixels for the encoder to say anything
            return {**out, "start": None, "end": None,
                    "verdict_start": "unmeasured (the head is only %d px in the frame)" % head_px,
                    "verdict_end": "unmeasured (the head is only %d px in the frame)" % head_px,
                    "head_px": head_px, "box": [round(b, 3) for b in box]}
        cam = job.get("cam") or {}
        given_end = job.get("box_end")
        if given_end:
            # the head was found in the last frame itself: no carrying, no assumption about
            # what the body did between the two
            cb, too_far = list(given_end), False
        elif job.get("close"):
            # a face that fills the frame IS what the camera ruler follows, so the measured
            # "camera" is the head; the face stays in the same box, and that is what is compared
            cb, too_far = list(box), False
        else:
            cb = carry_box(box, cam)
            # how much of the carried box is still inside the frame
            ix0, iy0, ix1, iy1 = max(0.0, cb[0]), max(0.0, cb[1]), min(1.0, cb[2]), min(1.0, cb[3])
            inside = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0) / max(1e-6, (cb[2] - cb[0]) * (cb[3] - cb[1]))
            too_far = float(cam.get("zoom", 1.0) or 1.0) > 1.6 or inside < 0.6
        c1 = None if too_far else crop(last, cb)
        p, e0 = embed(portrait), embed(c0)
        start = float((p * e0).sum())
        out.update({"start": round(start, 3), "verdict_start": verdict(start, job.get("close")),
                    "head_px": head_px, "box": [round(b, 3) for b in box]})
        if c1 is None:
            out.update({"end": None, "hold": None, "verdict_end": "unmeasured (the camera moved too much to follow the head)"})
        else:
            e1 = embed(c1)
            end, hold = float((p * e1).sum()), float((e0 * e1).sum())
            out.update({"end": round(end, 3), "hold": round(hold, 3), "verdict_end": verdict(end, job.get("close"))})
        if job.get("curve"):
            try:
                hc = hold_curve(job, box, p, job.get("close"), job.get("cam_curve"), duration(job["video"]))
                if hc:
                    out["hold_curve"] = hc
            except Exception as e:
                out["hold_curve_error"] = str(e)[:120]
        # the place: did the whole frame stay the same picture from first to last?  (the plate
        # against the first frame is framing-dependent - a medium on a person scores 0.48 against
        # its own empty plate - so it is reported, not judged)
        f0, f1 = embed(first), embed(last)
        hold = float((f0 * f1).sum())
        out.update({"place_hold": round(hold, 3),
                    "place_verdict": ("held" if hold >= 0.85 else "changed" if hold < 0.70 else "drifted")})
        if job.get("plate") and os.path.exists(job["plate"]):
            pl = embed(Image.open(job["plate"]))
            out["place_start"] = round(float((pl * f0).sum()), 3)
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
