#!/usr/bin/env python3
"""What angle is the camera at?  Measured from the picture, not from the prose.

The studio can already say what the camera DID (cammeasure).  This says where the camera
IS: below eye level looking up, at eye level, or above looking down.  A low angle is one
of the oldest things a director asks for and, like every camera word, the engines treat it
as a suggestion - so it needs a ruler before it can be promised.

HOW.  A real camera tilted up makes the world's vertical lines converge upward: door
frames, poles, walls and tree trunks all lean toward a vanishing point above the frame.
Tilted down, they converge below.  At eye level they stay parallel.  So:

  1. edges (Canny) -> long line segments (Hough)
  2. keep the near-vertical ones (within VERT_DEG of vertical)
  3. find the point closest to all their infinite lines (weighted least squares)
  4. that point is the vertical vanishing point; where it sits relative to the frame is
     the pitch

  vanishing point above the frame -> looking UP   (a low angle)
  below the frame                 -> looking DOWN (a high angle)
  far away in either direction     -> parallel verticals, eye level

REPORTED as `pitch`: 0 at eye level, positive looking up, negative looking down, and as a
word.  Calibrated against synthetic keystones of a known amount - see keystone().

    python3 anglemeasure.py picture.png
    from anglemeasure import measure, note
"""
import math
import os
import subprocess
import sys

import cv2
import numpy as np

VERT_DEG = 28.0        # a "vertical" line may lean this far and still count
MIN_LINES = 6
# Set from the population, not from theory: 102 readings over every plate and picked take
# on this box have quartiles 0.00 and +0.80 and a median of +0.39.  A street photographed at
# chest height converges upward whether or not anyone asked it to.
EYE_UP = 0.50          # below this, upward convergence is just photography
EYE_DOWN = -0.15       # downward is rare, so it takes less of it to mean something
STEEP_UP = 1.10        # the top tenth of the population
STEEP_DOWN = -0.55
EYE_LEVEL = EYE_UP     # kept: older callers read this name


def _first_frame(path):
    cap = cv2.VideoCapture(path)
    ok, f = cap.read()
    cap.release()
    if ok:
        return f
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-frames:v", "1",
                          "-f", "image2pipe", "-vcodec", "png", "-"],
                         capture_output=True).stdout
    if not raw:
        return None
    return cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)


def _gray(src):
    if isinstance(src, np.ndarray):
        im = src
    else:
        im = cv2.imread(src, cv2.IMREAD_COLOR)
        if im is None:
            im = _first_frame(src)
    if im is None:
        return None
    if im.ndim == 3:
        im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    return im


def vertical_lines(g):
    """long near-vertical segments as (x1, y1, x2, y2, length, lean), longest first"""
    h, w = g.shape
    scale = 900.0 / max(h, w)
    if scale < 1.0:
        g = cv2.resize(g, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        h, w = g.shape
    g = cv2.GaussianBlur(g, (3, 3), 0)
    edges = cv2.Canny(g, 60, 180, apertureSize=3)
    segs = cv2.HoughLinesP(edges, 1, np.pi / 360, threshold=60,
                           minLineLength=int(h * 0.12), maxLineGap=int(h * 0.02))
    out = []
    if segs is None:
        return out, (w, h)
    for x1, y1, x2, y2 in np.asarray(segs).reshape(-1, 4):
        dx, dy = float(x2 - x1), float(y2 - y1)
        if abs(dy) < 1e-6:
            continue
        lean = abs(math.degrees(math.atan2(dx, dy)))
        lean = min(lean, 180 - lean)
        if lean <= VERT_DEG:
            out.append((float(x1), float(y1), float(x2), float(y2), math.hypot(dx, dy), lean))
    out.sort(key=lambda s: -s[4])
    return out, (w, h)


def _inter(l1, l2):
    """intersection of two lines given as (a, b, c) with a x + b y = c"""
    a1, b1, c1 = l1
    a2, b2, c2 = l2
    d = a1 * b2 - a2 * b1
    if abs(d) < 1e-9:
        return None
    return ((c1 * b2 - c2 * b1) / d, (a1 * c2 - a2 * c1) / d)


def _lines(segs):
    out = []
    for x1, y1, x2, y2, ln, lean in segs:
        dx, dy = x2 - x1, y2 - y1
        n = math.hypot(dx, dy)
        a_, b_ = -dy / n, dx / n
        out.append((a_, b_, a_ * x1 + b_ * y1, ln))
    return out


def vanishing_point(segs, size):
    """The point most of the vertical lines actually agree on.

    Least squares was the first attempt and it was wrong in the one case that matters:
    on a picture whose verticals ARE parallel (eye level, the answer we most need to be
    able to say) a handful of outliers pull the solution to a nearby point and the ruler
    confidently reports a steep angle.  RANSAC asks instead which point the largest
    number of lines pass close to, and reports how many that is - so parallel verticals
    come back as a far-away point with a wide spread, which is what eye level looks like.

    -> (point, agreement, inlier fraction)"""
    if len(segs) < MIN_LINES:
        return None, 0.0, 0.0
    w, h = size
    L = _lines(segs[:60])
    tol = 0.02 * max(w, h)
    best, best_in = None, []
    n = len(L)
    for i in range(n):
        for j in range(i + 1, n):
            p = _inter(L[i][:3], L[j][:3])
            if p is None:
                continue
            if abs(p[0]) > 40 * w or abs(p[1]) > 40 * h:
                continue
            inl = [k for k in range(n)
                   if abs(L[k][0] * p[0] + L[k][1] * p[1] - L[k][2]) < tol]
            wsum = sum(L[k][3] for k in inl)
            if best is None or wsum > best[0]:
                best, best_in = (wsum, p), inl
    if best is None or len(best_in) < MIN_LINES:
        return None, 0.0, 0.0
    # refit on the inliers only
    A = np.asarray([[L[k][0] * L[k][3], L[k][1] * L[k][3]] for k in best_in])
    b = np.asarray([L[k][2] * L[k][3] for k in best_in])
    try:
        sol, _r, rank, _s = np.linalg.lstsq(A, b, rcond=None)
        if rank >= 2:
            best = (best[0], (float(sol[0]), float(sol[1])))
    except Exception:
        pass
    p = best[1]
    d = [abs(L[k][0] * p[0] + L[k][1] * p[1] - L[k][2]) for k in best_in]
    return p, float(np.median(d)) / max(size), len(best_in) / float(n)


def measure(src):
    """-> {pitch, angle, vy, lines, agreement, confidence}

    pitch: 0 at eye level, positive looking up (a low angle), negative looking down."""
    g = _gray(src)
    if g is None:
        return {"error": "could not read %s" % src, "pitch": 0.0,
                "angle": "eye level", "confidence": "none"}
    segs, (w, h) = vertical_lines(g)
    if len(segs) < MIN_LINES:
        return {"error": "not enough vertical lines (%d)" % len(segs), "lines": len(segs),
                "pitch": 0.0, "angle": "eye level", "confidence": "none"}
    vp, agree, frac = vanishing_point(segs, (w, h))
    if vp is None:
        return {"error": "no vanishing point", "lines": len(segs), "pitch": 0.0,
                "angle": "eye level", "confidence": "none"}
    vy = (vp[1] - h / 2.0) / h              # frame heights from the centre; negative = above
    # verticals that meet a long way off are parallel: that is eye level, not a steep angle
    pitch = 0.0 if abs(vy) < 0.35 else -1.0 / vy
    pitch = max(-3.0, min(3.0, pitch))
    conf = "high" if (len(segs) >= 12 and agree < 0.012 and frac >= 0.55) else (
        "low" if (agree > 0.03 or frac < 0.35 or len(segs) < 9) else "medium")
    return {"pitch": round(pitch, 3), "vy": round(vy, 3), "lines": len(segs),
            "inliers": round(frac, 2), "agreement": round(agree, 4), "confidence": conf,
            "angle": describe(pitch, conf), "size": [w, h]}


def describe(pitch, conf="medium"):
    """The absolute word.  For what the studio PROMISED, use describe_change against the
    plate the take was built on - an ordinary plate is not at zero."""
    if conf == "none":
        return "eye level"
    if pitch > STEEP_UP:
        return "a steep low angle"
    if pitch > EYE_UP:
        return "a low angle"
    if pitch < STEEP_DOWN:
        return "a steep high angle"
    if pitch < EYE_DOWN:
        return "a high angle"
    return "eye level"


def describe_change(pitch, base, conf="medium"):
    """What the camera did relative to the picture it started from, which is what a
    director asked for.  A keystone REPLACES a vanishing point rather than adding to it,
    so this is the take against its own plate, never a sum of two angles."""
    if conf == "none" or base is None:
        return describe(pitch, conf)
    d = pitch - base
    if d > 0.45:
        return "well below the plate's own eye line"
    if d > 0.15:
        return "below the plate's own eye line"
    if d < -0.45:
        return "well above the plate's own eye line"
    if d < -0.15:
        return "above the plate's own eye line"
    return "level with the plate"


def note(m):
    if not m:
        return None
    if m.get("confidence") == "none":
        return None
    n = "angle: %s (pitch %+.2f)" % (m.get("angle"), m.get("pitch", 0.0))
    if m.get("confidence") == "low":
        n += " (uncertain)"
    return n


def keystone(src, dst, pitch):
    """Synthetic ground truth: warp a picture the way a tilted camera would see it.

    Positive pitch = looking up, so the world's verticals converge toward the top.  Only
    used to calibrate the ruler and to test the compositor - the studio's real angle pass
    uses the depth map (see angle.py)."""
    im = cv2.imread(src, cv2.IMREAD_COLOR) if not isinstance(src, np.ndarray) else src
    h, w = im.shape[:2]
    k = max(-0.45, min(0.45, pitch * 0.5))
    src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dx = abs(k) * w * 0.5
    if k >= 0:      # looking up: the top of the world is further away, so it squeezes in
        dst_pts = np.float32([[dx, 0], [w - dx, 0], [w + dx, h], [-dx, h]])
    else:           # looking down: the bottom squeezes in
        dst_pts = np.float32([[-dx, 0], [w + dx, 0], [w - dx, h], [dx, h]])
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    out = cv2.warpPerspective(im, M, (w, h), flags=cv2.INTER_LANCZOS4,
                              borderMode=cv2.BORDER_REFLECT101)
    if dst:
        cv2.imwrite(dst, out)
    return out


if __name__ == "__main__":
    for p in sys.argv[1:]:
        m = measure(p)
        print("%-52s %-30s %-6s lines=%d" % (os.path.basename(p)[:52],
                                             note(m) or m.get("error"),
                                             m.get("confidence"), m.get("lines", 0)))
