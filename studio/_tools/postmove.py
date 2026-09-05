#!/usr/bin/env python3
"""A camera move done by us, on a take the engine already made.

The engines cannot be asked for a camera move - measured again on 2026-09-04:
"locked off on a tripod, nothing gets closer" still pushed in on three of three
takes.  So the shot is rendered with the camera as still as the engine will
hold it, and the move the director asked for is applied afterwards as
arithmetic: a window that travels and scales through the frame with an eased
or spring curve, exactly as the camrig does for stills.  The same parameters
always give the same pixels; the measured camera equals the requested camera.

Moves (all with `seconds` = the clip, `ease` = smoothstep unless stated):
    push      zoom 1.0 -> amount             (amount 1.05-1.6)
    pull      zoom amount -> 1.0 (start tight, open out)
    pan       window travels left/right by `amount` of the frame width, at zoom `z`
    tilt      window travels up/down by `amount` of the frame height, at zoom `z`
    orbit     a gentle lateral drift with a counter-zoom - the 2D stand-in for an arc
    roll      a Dutch tilt that arrives: 0 -> `amount` degrees (default 8)
    whip      a whip pan: the travel in the middle third, fast; `amount` = fraction of the width
    handheld  a static frame with small correlated shake (amp px, hz)
    stabilise given a measured zoom curve, the compensating crop that holds the
              framing constant (the price is the end frame's crop everywhere)

    python3 postmove.py in.mp4 out.mp4 push 1.15
    python3 postmove.py in.mp4 out.mp4 pan right 0.12 --zoom 1.12
    from postmove import apply; apply(src, dst, {"move": "push", "amount": 1.15})

Audio is carried over untouched.  Pull and pan/tilt need room: they run at zoom
`z` >= the travel, so nothing outside the frame is ever asked for.
"""
import json
import math
import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np


def _smooth(u):
    return u * u * (3 - 2 * u)


def _spring(n, zeta=0.7, settle=0.55, over_ok=True):
    """A unit step through a second-order system, sampled n times over the clip.

    Returns a list from 0 to about 1: the position of a mass on a spring that is told,
    at t=0, to be at 1.  `settle` is the fraction of the clip the drive takes; a smaller
    settle means a faster shove and a longer ring-out.  Integrated with a small fixed
    step so the shape does not depend on how many frames the clip happens to have."""
    zeta = max(0.15, min(3.0, float(zeta)))
    settle = max(0.12, min(0.95, float(settle)))
    # omega chosen so that a critically damped system is within 2% at `settle` of the clip
    omega = 4.0 / settle
    sub = 24
    x, v = 0.0, 0.0
    out = [0.0]
    dt = 1.0 / (max(2, n - 1) * sub)
    for _i in range((n - 1) * sub):
        a = -2.0 * zeta * omega * v - omega * omega * (x - 1.0)
        v += a * dt
        x += v * dt
        if (_i + 1) % sub == 0:
            out.append(x)
    if not over_ok:
        out = [min(1.0, y) for y in out]
    # land exactly on the mark: a move that ends at 0.998 measures as a move that missed
    if abs(out[-1] - 1.0) < 0.06:
        out[-1] = 1.0
    return out


def _ease_curve(kind, n, ease, zeta, settle):
    """the 0..1 shape every move travels along"""
    if ease == "spring":
        return _spring(n, zeta, settle)
    if ease is False or ease == "linear":
        return [i / max(1, n - 1) for i in range(n)]
    return [_smooth(i / max(1, n - 1)) for i in range(n)]


def _curve(kind, n, amount, ease=True, z=None, amp=0.0, hz=1.2, seed=7, curve=None,
           zeta=0.7, settle=0.55):
    """per-frame (cx_frac, cy_frac, zoom, roll_deg)"""
    out = []
    shape = _ease_curve(kind, n, ease, zeta, settle)
    rng = np.random.RandomState(seed)
    # correlated shake: sum of two slow sines with random phases plus filtered noise
    ph = rng.uniform(0, 2 * math.pi, 4)
    noise = rng.normal(0, 1, (n + 8, 2))
    k = np.ones(9) / 9.0
    nx = np.convolve(noise[:, 0], k, mode="same")[:n]
    ny = np.convolve(noise[:, 1], k, mode="same")[:n]
    for i in range(n):
        u = i / max(1, n - 1)
        e = shape[i] if i < len(shape) else shape[-1]
        cx, cy, zoom, roll = 0.5, 0.5, 1.0, 0.0
        if kind == "push":
            zoom = 1.0 + (amount - 1.0) * e
        elif kind == "pull":
            zoom = amount - (amount - 1.0) * e
        elif kind in ("pan", "tilt"):
            zoom = z or max(1.0, 1.0 + abs(amount))
            room = (1.0 - 1.0 / zoom) / 2.0          # how far the window centre may travel
            travel = min(abs(amount), 2 * room)
            d = (e - 0.5) * travel * (1 if amount > 0 else -1)
            if kind == "pan":
                cx = 0.5 + d
            else:
                cy = 0.5 + d
        elif kind == "orbit":
            zoom = (z or 1.12) - 0.04 * math.sin(math.pi * e)
            room = (1.0 - 1.0 / zoom) / 2.0
            cx = 0.5 + min(abs(amount), 2 * room) * (e - 0.5) * (1 if amount > 0 else -1)
            roll = 0.6 * math.sin(math.pi * e) * (1 if amount > 0 else -1)
        elif kind == "roll":
            # a Dutch tilt that arrives: roll from 0 to `amount` degrees at a zoom that hides the corners
            zoom = z or (1.0 + abs(amount) / 40.0 + 0.04)
            roll = amount * e
        elif kind == "whip":
            # a whip pan: the travel happens in the middle third, fast, linear, with the frame
            # otherwise still; `amount` is the fraction of the frame width, sign = direction
            zoom = z or 1.16
            room = (1.0 - 1.0 / zoom) / 2.0
            travel = min(abs(amount), 2 * room)
            if ease == "spring":
                d = -travel / 2 + travel * e      # the shove and the ring-out do the work
            elif u < 0.35:
                d = -travel / 2
            elif u > 0.65:
                d = travel / 2
            else:
                d = -travel / 2 + travel * (u - 0.35) / 0.30
            cx = 0.5 + d * (1 if amount > 0 else -1)
        elif kind == "handheld":
            zoom = z or 1.06
            t = i / 24.0
            # breathing (slow, near 0.25 Hz), the operator's sway at `hz`, and filtered
            # noise for the micro-corrections a hand makes to hold a frame
            breath = 0.35 * math.sin(2 * math.pi * 0.25 * t + ph[3])
            cx = 0.5 + (amp / 1000.0) * (0.5 * math.sin(2 * math.pi * hz * t + ph[0]) + 0.5 * nx[i])
            cy = 0.5 + (amp / 1000.0) * (0.5 * math.sin(2 * math.pi * hz * 0.8 * t + ph[1]) + 0.5 * ny[i] + breath)
            roll = (amp / 60.0) * math.sin(2 * math.pi * hz * 0.5 * t + ph[2])
        elif kind == "stabilise":
            # curve: measured cumulative [zoom, pan, tilt] per sampled step (or bare zooms);
            # the frame is held at the END frame's view: crop by final/so-far zoom and shift
            # the window by the pan and tilt still to come
            c = curve or [[1.0, 0.0, 0.0]]
            c = [[x, 0.0, 0.0] if not isinstance(x, (list, tuple)) else list(x) for x in c]
            zf, pf, tf = c[-1]
            pos = u * (len(c) - 1)
            j = int(math.floor(pos)); f = pos - j
            if j >= len(c) - 1:
                zi, pi, ti = c[-1]
            else:
                zi = c[j][0] * (1 - f) + c[j + 1][0] * f
                pi = c[j][1] * (1 - f) + c[j + 1][1] * f
                ti = c[j][2] * (1 - f) + c[j + 1][2] * f
            zoom = max(1.0, zf / max(zi, 1e-6))
            # the scene still has to move left by (pf - pi) of the frame: look there now
            cx = 0.5 + (pf - pi)
            cy = 0.5 + (tf - ti)
        out.append((cx, cy, zoom, roll))
    return out


def apply(src, dst, move, fps=None, crf=16):
    """apply a move to a video; returns a dict with what was done"""
    cap = cv2.VideoCapture(src)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = fps or (cap.get(cv2.CAP_PROP_FPS) or 24.0)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()
    n = len(frames)
    if n < 2:
        raise SystemExit("could not decode %s" % src)
    kind = move.get("move", "push")
    amount = float(move.get("amount", 1.12 if kind in ("push", "pull") else 0.1))
    if kind in ("pan", "tilt", "whip") and str(move.get("direction", "")).lower() in ("left", "up"):
        amount = -abs(amount)
    if kind == "roll" and move.get("amount") is None:
        amount = 8.0
    traj = _curve(kind, n, amount, ease=move.get("ease", True), z=move.get("zoom"),
                  amp=float(move.get("amp", 14)), hz=float(move.get("hz", 1.2)),
                  seed=int(move.get("seed", 7)), curve=move.get("curve"),
                  zeta=float(move.get("zeta", 0.7)), settle=float(move.get("settle", 0.55)))
    tmp = tempfile.mkdtemp(prefix="postmove_")
    for i, (fr, (cx, cy, zoom, roll)) in enumerate(zip(frames, traj)):
        vw, vh = W / zoom, H / zoom
        x = min(max(cx * W, vw / 2), W - vw / 2)
        y = min(max(cy * H, vh / 2), H - vh / 2)
        # a similarity warp: rotate about the window centre, scale, translate to the output frame
        M = cv2.getRotationMatrix2D((x, y), roll, zoom)
        M[0, 2] += W / 2 - x
        M[1, 2] += H / 2 - y
        out = cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT101)
        cv2.imwrite(os.path.join(tmp, "f%05d.png" % i), out)
    silent = os.path.join(tmp, "video.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", "%.3f" % fps, "-i", os.path.join(tmp, "f%05d.png"),
                    "-c:v", "libx264", "-crf", str(crf), "-pix_fmt", "yuv420p", silent], check=True)
    has_audio = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_name",
                                "-of", "csv=p=0", src], capture_output=True, text=True).stdout.strip() != ""
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    if has_audio:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", silent, "-i", src, "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "copy", "-shortest", dst], check=True)
    else:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", silent, "-c", "copy", dst], check=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    z0, z1 = traj[0][2], traj[-1][2]
    return {"move": kind, "amount": amount, "frames": n, "fps": round(fps, 2),
            "ease": ("spring" if move.get("ease") == "spring" else
                     ("linear" if move.get("ease") in (False, "linear") else "smooth")),
            "zeta": round(float(move.get("zeta", 0.7)), 2) if move.get("ease") == "spring" else None,
            "settle": round(float(move.get("settle", 0.55)), 2) if move.get("ease") == "spring" else None,
            "zoom_start": round(z0, 3), "zoom_end": round(z1, 3),
            "cx_start": round(traj[0][0], 4), "cy_start": round(traj[0][1], 4),
            "travel": round((traj[-1][0] - traj[0][0]), 3) if kind in ("pan", "orbit") else round((traj[-1][1] - traj[0][1]), 3),
            "file": dst}


def _cli():
    a = sys.argv[1:]
    if len(a) < 3:
        print(__doc__); sys.exit(1)
    src, dst, kind = a[0], a[1], a[2]
    move = {"move": kind}
    rest = a[3:]
    if kind in ("pan", "tilt", "whip") and rest and rest[0] in ("left", "right", "up", "down"):
        move["direction"] = rest.pop(0)
    if rest and not rest[0].startswith("--"):
        move["amount"] = float(rest.pop(0))
    while rest:
        k = rest.pop(0)
        if k == "--zoom": move["zoom"] = float(rest.pop(0))
        elif k == "--amp": move["amp"] = float(rest.pop(0))
        elif k == "--hz": move["hz"] = float(rest.pop(0))
        elif k == "--linear": move["ease"] = False
        elif k == "--spring": move["ease"] = "spring"
        elif k == "--zeta": move["zeta"] = float(rest.pop(0))
        elif k == "--settle": move["settle"] = float(rest.pop(0))
        elif k == "--curve": move["curve"] = json.loads(rest.pop(0))
    print(json.dumps(apply(src, dst, move)))


if __name__ == "__main__":
    _cli()
