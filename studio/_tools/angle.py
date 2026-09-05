#!/usr/bin/env python3
"""A low angle, done by the studio: the plate seen from a camera that moved.

The engines treat "low angle" the way they treat every camera word - as a suggestion.
Measured on the encyclopedia's own low-angle entry: the prose asked to look up and the
picture came back at eye level.  So the angle joins the camera move and the time-lapse in
the set of things the studio performs itself, deterministically, on the plate, BEFORE the
engine ever sees it - because a plate is what the engine copies.

A real low angle is two things at once, and doing only one of them looks wrong:

  1. THE CAMERA DROPPED.  Near things rise in the frame more than far things.  That is
     parallax and it is what makes the change feel like a camera and not a filter.  With
     a depth map it is one line: dy = k / depth.  The near ground opens out, the far
     background barely moves.

  2. THE CAMERA TILTED UP.  The world's verticals converge toward the top of the frame.
     That is a rotation, a homography, and it is what a viewer actually names when they
     say "low angle".

This does both, in that order, and then fills the sliver of nothing that step 1 uncovers
at the frame edge.  The result is measured by anglemeasure, which reads a synthetic pitch
to within 0.01, so the studio can promise the angle it was asked for.

    python3 angle.py plate.png out.png 0.35          # look up
    python3 angle.py plate.png out.png -0.3          # look down
    from angle import warp; im, moved = warp(plate_p, depth_p, pitch=0.35)

`moved` maps a point on the original plate to where it ended up, so the compositor can put
a figure's feet on the same piece of ground it would have used before the angle changed.
"""
import math
import os
import sys

import cv2
import numpy as np

MAX_PITCH = 0.8
PARALLAX = 0.16        # frame heights of near-point travel at pitch 1.0
FRAMING = 0.13         # frame heights the view rises at pitch 1.0 (the tilt itself)


def _depth01(depth_path, size):
    """depth as 0 (far) .. 1 (near), at the plate's size"""
    d = cv2.imread(depth_path, cv2.IMREAD_GRAYSCALE)
    if d is None:
        return None
    if (d.shape[1], d.shape[0]) != size:
        d = cv2.resize(d, size, interpolation=cv2.INTER_LINEAR)
    d = d.astype(np.float32) / 255.0
    lo, hi = float(np.percentile(d, 1)), float(np.percentile(d, 99))
    if hi - lo < 1e-3:
        return None
    return np.clip((d - lo) / (hi - lo), 0.0, 1.0)


def _keystone_M(w, h, pitch):
    """the homography of a camera tilted by `pitch` (positive = up)"""
    k = max(-0.45, min(0.45, pitch * 0.5))
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dx = abs(k) * w * 0.5
    if k >= 0:
        dst = np.float32([[dx, 0], [w - dx, 0], [w + dx, h], [-dx, h]])
    else:
        dst = np.float32([[-dx, 0], [w + dx, 0], [w - dx, h], [dx, h]])
    return cv2.getPerspectiveTransform(src, dst)


def warp(plate_path, depth_path, pitch=0.35, parallax=None, fill=True):
    """-> (BGR image, moved(x, y) -> (x, y))

    pitch: positive looks up (a low angle), negative looks down.  Clamped to +-0.8; past
    that the keystone eats the frame and the fill is inventing more than it is moving."""
    im = cv2.imread(plate_path, cv2.IMREAD_COLOR)
    if im is None:
        raise SystemExit("no plate at %s" % plate_path)
    h, w = im.shape[:2]
    pitch = max(-MAX_PITCH, min(MAX_PITCH, float(pitch)))
    amt = PARALLAX if parallax is None else float(parallax)
    d = _depth01(depth_path, (w, h)) if depth_path and os.path.exists(depth_path) else None

    # 1. the camera drops (or rises): near pixels travel further up (or down) the frame
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    if d is not None and amt:
        # a point at depth d moves by amt * pitch * d frame-heights; sampling is inverse,
        # so the SOURCE for output row y is y + shift (we pull from where it came from)
        # a camera that DROPS sees near things lower in the frame, far things barely moving.
        # The first version had this the other way round and the two halves of the effect
        # fought each other: the tilt said "looking up" while the parallax said "standing
        # taller", and the picture read as neither.
        shift = (amt * pitch * h) * d
        map_y = ys - shift
    else:
        shift = np.zeros((h, w), np.float32)
        map_y = ys
    moved_par = cv2.remap(im, xs, map_y, interpolation=cv2.INTER_LANCZOS4,
                          borderMode=cv2.BORDER_REPLICATE)
    if fill and d is not None and amt:
        # where the pull came from outside the plate, mark it and let inpaint close it
        bad = ((map_y < 0) | (map_y > h - 1)).astype(np.uint8) * 255
        if bad.any():
            bad = cv2.dilate(bad, np.ones((3, 3), np.uint8), iterations=1)
            moved_par = cv2.inpaint(moved_par, bad, 4, cv2.INPAINT_TELEA)

    # 2. the camera tilts: verticals converge
    M = _keystone_M(w, h, pitch)
    # 3. and the tilt looks higher (or lower): the window travels, inside a zoom that
    #    gives it the room, so no pixel outside the plate is ever asked for
    z = 1.0 + 2.0 * FRAMING * abs(pitch)
    dy = FRAMING * pitch * h
    T = np.array([[z, 0.0, (1 - z) * w / 2.0],
                  [0.0, z, (1 - z) * h / 2.0 + dy * z]], dtype=np.float64)
    M3 = np.vstack([T, [0.0, 0.0, 1.0]]).dot(M)
    out = cv2.warpPerspective(moved_par, M3, (w, h), flags=cv2.INTER_LANCZOS4,
                              borderMode=cv2.BORDER_REFLECT101)

    def moved(x, y):
        """where a point of the ORIGINAL plate ends up"""
        yy = float(y)
        if d is not None and amt:
            xi = int(max(0, min(w - 1, round(x))))
            yi = int(max(0, min(h - 1, round(y))))
            yy = float(y) + float(shift[yi, xi])       # forward is the inverse of the pull
        p = np.array([[[float(x), yy]]], dtype=np.float32)
        q = cv2.perspectiveTransform(p, M3)[0][0]
        return float(q[0]), float(q[1])

    return out, moved


def apply_to_plate(plate_path, out_path, pitch=0.35, depth_path=None, parallax=None):
    dp = depth_path or (plate_path[:-4] + "_depth.png")
    im, moved = warp(plate_path, dp if os.path.exists(dp) else None, pitch, parallax)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    cv2.imwrite(out_path, im)
    return {"file": out_path, "pitch": round(pitch, 3),
            "depth": os.path.basename(dp) if os.path.exists(dp) else None}


MARK = "__angle"      # a derived plate, not one that was rendered


def angled_plate(plate_path, pitch, force=False):
    """Write (once) the same place seen from `pitch`, beside its plate, with a depth map
    warped the same way so the compositor stands a figure on the same ground.

    -> (plate path, plate key) or (original, original key) when the pitch is negligible."""
    key = os.path.basename(plate_path)[:-4]
    if abs(float(pitch)) < 0.06:
        return plate_path, key
    tag = "%s%s%02d" % (MARK, "u" if pitch > 0 else "d", round(abs(pitch) * 100))
    dst = plate_path[:-4] + tag + ".png"
    dkey = key + tag
    ddst = dst[:-4] + "_depth.png"
    if os.path.exists(dst) and os.path.exists(ddst) and not force:
        return dst, dkey
    src_depth = plate_path[:-4] + "_depth.png"
    im, _moved = warp(plate_path, src_depth if os.path.exists(src_depth) else None, pitch)
    cv2.imwrite(dst, im)
    if os.path.exists(src_depth):
        # the depth map is a picture of the same scene: it takes the same geometry, so the
        # horizon the compositor reads off it stays the horizon of the angled picture
        d = cv2.imread(src_depth, cv2.IMREAD_COLOR)
        dwarp, _m2 = warp(src_depth, src_depth, pitch)
        cv2.imwrite(ddst, dwarp)
    return dst, dkey


VIEW_FOR = {"low": "pres_low", "high": "turn_front"}


def view_for_pitch(pitch, have):
    """which of the pack's views is closest to being seen from this angle"""
    if pitch > 0.18 and "pres_low" in have:
        return "pres_low"
    return None


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        print(__doc__)
        sys.exit(1)
    src, dst = a[0], a[1]
    p = float(a[2]) if len(a) > 2 else 0.35
    print(apply_to_plate(src, dst, p))
