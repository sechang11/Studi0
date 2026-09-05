#!/usr/bin/env python3
"""What did the camera do?  Measured, not promised.

Frame-to-frame similarity transforms (scale, rotation, translation) over a
clip, estimated on the BORDER BAND of the frame - the outer part where the
background lives and the subject usually does not - and accumulated into a
zoom factor, a pan and a tilt as fractions of the frame, and a roll in degrees.
The full-frame estimate is kept beside it so the two can disagree, which is
what happens when a face fills the frame and the "camera" the features follow
is really the head.

Validated 2026-09-04 23:45 on builder-test: the still_push rig at zoom_end 1.12
measured 1.113; two LTX takes that "ended closer" measured 3.0x and 1.8x; an
empty wide on a static prompt measured 1.09x (LTX's own drift); a static take
measured 0.999.

    python3 cammeasure.py take.mp4 [take2.mp4 ...]      -> one JSON line each
    from cammeasure import measure; measure(path) -> dict

System python3 with cv2 (5.0 on the box). No GPU.
"""
import json
import math
import os
import sys

import cv2
import numpy as np

STEPS = 12            # transforms across the clip; 13 sampled frames
WORK_W = 640          # analysis width
BAND = 0.22           # border band width as a fraction of the frame
MIN_INLIERS = 24


def _sample(path, steps=STEPS, width=WORK_W):
    """`steps + 1` grey frames spread across the clip.  Every frame is decoded
    (containers lie about counts and seeks), downscaled on the way in."""
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        h, w = f.shape[:2]
        s = width / float(w)
        frames.append(cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (width, int(round(h * s)))))
    cap.release()
    if len(frames) < 2:
        frames, fps = _sample_ffmpeg(path, width)
    n = len(frames)
    if n < 2:
        return [], 0.0, fps
    idx = sorted(set(int(round(i * (n - 1) / steps)) for i in range(steps + 1)))
    return [frames[i] for i in idx], n / float(fps), fps


def _sample_ffmpeg(path, width=WORK_W):
    """the fallback when cv2's decoder will not open a file: grey frames over an ffmpeg pipe"""
    import subprocess
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                         "stream=width,height,r_frame_rate", "-of", "csv=p=0", path],
                        capture_output=True, text=True).stdout.strip().split(",")
    try:
        w, h = int(pr[0]), int(pr[1])
        num, den = pr[2].split("/")
        fps = float(num) / float(den or 1)
    except Exception:
        return [], 24.0
    hh = int(round(h * width / float(w)))
    hh += hh % 2
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", "scale=%d:%d" % (width, hh),
                          "-pix_fmt", "gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(raw) // (width * hh)
    frames = [np.frombuffer(raw[i * width * hh:(i + 1) * width * hh], np.uint8).reshape(hh, width) for i in range(n)]
    return frames, fps


def _band_mask(shape, band=BAND):
    h, w = shape
    m = np.zeros((h, w), np.uint8)
    bw, bh = int(w * band), int(h * band)
    m[:bh, :] = 255
    m[-bh:, :] = 255
    m[:, :bw] = 255
    m[:, -bw:] = 255
    return m


def _transform(a, b, mask=None):
    """Similarity transform a->b: (scale, rot_deg, tx, ty, inliers) or None."""
    orb = cv2.ORB_create(4000)
    ka, da = orb.detectAndCompute(a, mask)
    kb, db = orb.detectAndCompute(b, mask)
    if da is None or db is None or len(ka) < MIN_INLIERS or len(kb) < MIN_INLIERS:
        return None
    m = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(da, db)
    m = sorted(m, key=lambda x: x.distance)[:600]
    if len(m) < MIN_INLIERS:
        return None
    pa = np.float32([ka[x.queryIdx].pt for x in m])
    pb = np.float32([kb[x.trainIdx].pt for x in m])
    H, inl = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=3.0)
    if H is None or inl is None or int(inl.sum()) < MIN_INLIERS:
        return None
    s = math.hypot(H[0, 0], H[1, 0])
    rot = math.degrees(math.atan2(H[1, 0], H[0, 0]))
    return s, rot, float(H[0, 2]), float(H[1, 2]), int(inl.sum())


def _accumulate(frames, mask=None):
    """Chain the transforms; translation is measured about the frame centre so a
    zoom does not masquerade as a pan.  Returns the running zoom curve too."""
    if len(frames) < 2:
        return None
    h, w = frames[0].shape[:2]
    cx, cy = w / 2.0, h / 2.0
    scale, tx, ty, rot = 1.0, 0.0, 0.0, 0.0
    inliers, curve, failed = [], [[1.0, 0.0, 0.0]], 0
    for a, b in zip(frames, frames[1:]):
        t = _transform(a, b, mask)
        if not t:
            failed += 1
            curve.append(list(curve[-1]))
            continue
        s, r, x, y, n = t
        rr = math.radians(r)
        # where the centre went, minus where it was
        tx += (s * (math.cos(rr) * cx - math.sin(rr) * cy) + x) - cx
        ty += (s * (math.sin(rr) * cx + math.cos(rr) * cy) + y) - cy
        scale *= s
        rot += r
        inliers.append(n)
        curve.append([scale, -tx / w, -ty / h])
    if not inliers:
        return None
    return {"zoom": scale, "pan": -tx / w, "tilt": -ty / h, "roll": rot,
            "inliers_med": int(np.median(inliers)), "failed": failed, "curve": curve}


def describe(zoom, pan, tilt, roll, z_band=0.06, xy_band=0.06, roll_band=2.0):
    kind = []
    if zoom > 1 + z_band:
        kind.append("push in %d%%" % round((zoom - 1) * 100))
    elif zoom < 1 - z_band:
        kind.append("pull back %d%%" % round((1 - zoom) * 100))
    if abs(pan) > xy_band:
        kind.append("pan %s %d%%" % ("right" if pan > 0 else "left", round(abs(pan) * 100)))
    if abs(tilt) > xy_band:
        kind.append("tilt %s %d%%" % ("down" if tilt > 0 else "up", round(abs(tilt) * 100)))
    if abs(roll) > roll_band:
        kind.append("roll %.1f deg" % roll)
    return ", ".join(kind) or "static"


def measure(path, framing=None):
    """The camera's path through the clip, as numbers and as a sentence.

    Returns {duration, fps, zoom, pan, tilt, roll, camera, confidence, curve,
    full: {...}}.  `camera` and the headline numbers come from the border band
    when it has enough features; `full` is the whole-frame estimate.  When the
    two disagree badly (a subject that fills the frame), confidence is 'low'
    and the sentence says the frame is mostly subject."""
    frames, dur, fps = _sample(path)
    if len(frames) < 3:
        return {"error": "could not decode enough frames", "file": os.path.basename(path)}
    band = _accumulate(frames, _band_mask(frames[0].shape))
    full = _accumulate(frames, None)
    src, conf = band, "high"
    if band is None or band["inliers_med"] < MIN_INLIERS * 2 or band["failed"] > 3:
        src, conf = full, "low"
    if src is None:
        return {"error": "no features to follow", "file": os.path.basename(path)}
    if band and full and (abs(band["zoom"] - full["zoom"]) > 0.15 or abs(band["tilt"] - full["tilt"]) > 0.15):
        # a big push empties the border band of features; the larger zoom is the real one
        conf = "low"
        if abs(full["zoom"] - 1) > abs(band["zoom"] - 1) + 0.15:
            src = full
    if (framing or "").lower().startswith("close"):
        conf = "low"
    curve = src["curve"]
    if conf == "high" and band and full and len(band["curve"]) == len(full["curve"]):
        # both estimates trusted: average the zoom so neither the band's nor the frame's bias leads
        curve = [[(b[0] + f_[0]) / 2, b[1], b[2]] for b, f_ in zip(band["curve"], full["curve"])]
    out = {"file": os.path.basename(path), "duration": round(dur, 2), "fps": round(fps, 2),
           "zoom": round(src["zoom"], 3), "pan": round(src["pan"], 3), "tilt": round(src["tilt"], 3),
           "roll": round(src["roll"], 2), "confidence": conf,
           "curve": [[round(c[0], 3), round(c[1], 3), round(c[2], 3)] for c in curve],
           "camera": describe(src["zoom"], src["pan"], src["tilt"], src["roll"])}
    if (framing or "").lower().startswith("close"):
        out["camera"] += " (a face fills the frame; the camera is hard to tell from the head)"
    if full:
        out["full"] = {"zoom": round(full["zoom"], 3), "pan": round(full["pan"], 3),
                       "tilt": round(full["tilt"], 3), "roll": round(full["roll"], 2)}
    return out


def note(m):
    """the one-line QC note a take carries"""
    if not m or m.get("error"):
        return None
    tail = "" if m.get("confidence") == "high" else " (uncertain)"
    return "camera: %s%s" % (m["camera"], tail)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        m = measure(p)
        m.pop("curve", None)
        print(json.dumps(m))
