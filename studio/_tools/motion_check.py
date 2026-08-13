#!/usr/bin/env python3
"""studio/_tools/motion_check.py - did the clip do what the card said, or just move?

    python3 studio/_tools/motion_check.py clip.mp4
    python3 studio/_tools/motion_check.py --sweep            every clip with a motion card
    python3 studio/_tools/motion_check.py --sweep --json

WHY A SCALAR IS NOT ENOUGH. The motion cards already carry a `motion` number - mean frame
difference - and walk_in's own description says the trap out loud: "on a close shot it does
nothing at all while its number goes up". A book gyrating on a table and a person walking
at the lens can produce the same magnitude. Magnitude says SOMETHING MOVED. It cannot say
what.

So this measures the SHAPE of the movement, which is different per card:

    pan          the whole frame slides sideways. Every region translates together.
    tilt         the same, vertically.
    push / pull  the frame EXPANDS from the centre: the left edge moves left, the right
                 edge moves right. Regions diverge.
    static       nothing translates anywhere.
    walk_in      the CENTRE moves and the EDGES do not. A subject approaching grows in
                 place; the room behind it stays put.

Those are four distinguishable signatures, and a gyrating book fails walk_in on all of them:
it has no sustained centre expansion and no edge stillness to contrast against.

HOW IT MEASURES. Phase correlation on the FFT cross-power spectrum gives the translation
between two frames without any tracking or model. Run it on the whole frame for global
motion, then on five regions - centre and four edges - and the RELATIONSHIP between those
five vectors is the signature. numpy only; no OpenCV, no optical-flow library.

WHAT IT WILL NOT DO. It does not say the clip is good. It says whether the movement matches
the claim on the card. A clip can pass this and still be ugly, and that is a separate
judgement made by looking.
"""
import argparse, glob, json, os, re, subprocess, sys, tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)

# What each card claims, as a testable shape. `pan` is horizontal translation in pixels per
# second at the analysis width, `div` is how much the edges pull apart from the centre.
# Thresholds are deliberately loose: the question is "is this the right KIND of movement",
# not "is it exactly 12 pixels".
EXPECT = {
    "pan_l":  {"pan_x": "neg", "why": "the frame should slide right as the camera pans left"},
    "pan_r":  {"pan_x": "pos", "why": "the frame should slide left as the camera pans right"},
    "tilt_d": {"pan_y": "pos", "why": "the frame should slide up as the camera tilts down"},
    "tilt_u": {"pan_y": "neg", "why": "the frame should slide down as the camera tilts up"},
    "push":   {"div": "pos",   "why": "everything should expand outward from the centre"},
    "pull":   {"div": "neg",   "why": "everything should contract toward the centre"},
    "static": {"still": True,  "why": "the camera should not move at all"},
    "orbit":  {"pan_x": "any", "why": "the frame should travel sideways as the camera arcs"},
    "walk_in": {"centre_over_edge": True,
                "why": "the subject should grow in the centre while the room behind stays put"},
    "walk_out": {"centre_over_edge": True,
                 "why": "the subject should shrink in the centre while the room stays put"},
}
MIN_PAN = 1.5      # px/sec at 256 wide - below this nothing meaningful translated
MIN_DIV = 0.8


def frames(path, n=12, w=256):
    """n greyscale frames as numpy arrays, evenly spaced."""
    import numpy as np
    d = tempfile.mkdtemp(prefix="mc_")
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-vf",
         "scale=%d:-1,format=gray,fps=%d/%s" % (w, n, _dur(path) or 1),
         "-frames:v", str(n), os.path.join(d, "%03d.png")],
        capture_output=True, text=True)
    from PIL import Image
    out = []
    for f in sorted(glob.glob(os.path.join(d, "*.png"))):
        out.append(np.asarray(Image.open(f).convert("L"), dtype=float))
    for f in glob.glob(os.path.join(d, "*.png")):
        os.remove(f)
    os.rmdir(d)
    return out


def _dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return None


def shift(a, b):
    """Translation from a to b by phase correlation. (dx, dy) in pixels.

    The cross-power spectrum of two FFTs has its peak at the shift between them. No
    tracking, no features, no model - just where the correlation lands.
    """
    import numpy as np
    if a.shape != b.shape:
        return 0.0, 0.0
    win = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    fa = np.fft.fft2(a * win)
    fb = np.fft.fft2(b * win)
    cps = fa * np.conj(fb)
    mag = np.abs(cps)
    mag[mag == 0] = 1e-9
    r = np.fft.ifft2(cps / mag).real
    peak = np.unravel_index(np.argmax(r), r.shape)
    dy, dx = peak
    if dy > a.shape[0] // 2:
        dy -= a.shape[0]
    if dx > a.shape[1] // 2:
        dx -= a.shape[1]
    return float(dx), float(dy)


def analyse(path):
    import numpy as np
    fs = frames(path)
    if len(fs) < 3:
        return {"error": "could not read enough frames"}
    dur = _dur(path) or 1.0
    h, w = fs[0].shape

    def region(im, name):
        ch, cw = h // 3, w // 3
        return {"centre": im[ch:2 * ch, cw:2 * cw],
                "left": im[:, :cw], "right": im[:, 2 * cw:],
                "top": im[:ch, :], "bottom": im[2 * ch:, :]}[name]

    gx = gy = 0.0
    reg = {k: [0.0, 0.0] for k in ("centre", "left", "right", "top", "bottom")}
    for i in range(len(fs) - 1):
        dx, dy = shift(fs[i], fs[i + 1])
        gx += dx
        gy += dy
        for k in reg:
            rdx, rdy = shift(region(fs[i], k), region(fs[i + 1], k))
            reg[k][0] += rdx
            reg[k][1] += rdy

    per = lambda v: round(v / dur, 2)
    # Divergence: do the left and right edges pull APART? That is a zoom, not a pan. A pan
    # moves both edges the same way, so their difference cancels.
    # SIGN VALIDATED AGAINST SYNTHETIC CLIPS, not reasoned about. Built a known pan-right
    # and a known zoom-in with ffmpeg and measured both: the pan read +64.5 as expected,
    # and the zoom read NEGATIVE divergence under the first version of this formula - the
    # opposite of what the docstring claimed. phase correlation reports the shift that
    # ALIGNS the frames, which is the negative of how the content travelled, so expansion
    # came out contracting. Flipped here so positive div means the frame is expanding, and
    # re-checked against the same two clips.
    div = per((reg["left"][0] - reg["right"][0]) / 2.0
              + (reg["top"][1] - reg["bottom"][1]) / 2.0)
    edge = sum(abs(reg[k][0]) + abs(reg[k][1]) for k in ("left", "right", "top", "bottom"))
    centre = abs(reg["centre"][0]) + abs(reg["centre"][1])
    # How much of the movement is in the middle of the frame rather than at its edges. A
    # subject walking at a static camera is centre-heavy; a camera move is not.
    # A ratio against a near-zero denominator is meaningless, not enormous: one clip
    # reported centre_over_edge = 38,000,000 because NOTHING moved at the edges and the
    # epsilon did the dividing. When the whole frame is still there is no ratio to report.
    e4 = edge / 4.0
    ratio = None if (e4 < 0.05 and centre < 0.05) else round(centre / max(e4, 0.05), 2)
    return {"seconds": round(dur, 2), "frames": len(fs),
            "pan_x": per(gx), "pan_y": per(gy), "div": div,
            "centre_over_edge": ratio,
            "edge_motion": round(edge / 4.0 / dur, 2),
            "centre_motion": round(centre / dur, 2)}


def verdict(m, card):
    """Does the measurement match what this card claims?"""
    e = EXPECT.get(card)
    if not e:
        return {"card": card, "known": False,
                "note": "no signature recorded for this card - measured only"}
    fails = []
    if e.get("still"):
        if abs(m["pan_x"]) > MIN_PAN or abs(m["pan_y"]) > MIN_PAN or abs(m["div"]) > MIN_DIV:
            fails.append("the camera moved (pan %.1f/%.1f, div %.1f)"
                         % (m["pan_x"], m["pan_y"], m["div"]))
    for axis, key in (("pan_x", "pan_x"), ("pan_y", "pan_y"), ("div", "div")):
        want = e.get(key)
        if not want:
            continue
        v = m[axis]
        lim = MIN_DIV if axis == "div" else MIN_PAN
        if want == "any":
            if abs(v) < lim:
                fails.append("%s barely moved (%.1f)" % (axis, v))
        elif want == "pos" and v < lim:
            fails.append("%s should be positive, measured %.1f" % (axis, v))
        elif want == "neg" and v > -lim:
            fails.append("%s should be negative, measured %.1f" % (axis, v))
    if e.get("centre_over_edge"):
        # The book test. A subject approaching a locked camera moves the middle and leaves
        # the edges alone. A book gyrating, or a camera drifting, does not produce that.
        if m["centre_over_edge"] is None:
            fails.append("nothing moved anywhere - no subject crossed the frame")
        elif m["centre_over_edge"] < 1.3:
            fails.append("movement is not centre-weighted (ratio %.2f) - the whole frame "
                         "is moving, so this is a camera move rather than a subject "
                         "crossing the room" % m["centre_over_edge"])
        if m["edge_motion"] > 3.0:
            fails.append("the background is moving too (%.1f px/s at the edges)"
                         % m["edge_motion"])
    return {"card": card, "known": True, "pass": not fails,
            "fails": fails, "why": e["why"]}


def clips():
    out = []
    for f in glob.glob(os.path.join(STUDIO, "samples", "**", "*.json"), recursive=True):
        if os.path.basename(f).startswith("_") or "/_rejected/" in f.replace("\\", "/"):
            continue
        try:
            r = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(r, dict) or r.get("domain") != "video":
            continue
        for ext in (".mp4", ".webm"):
            p = f[:-5] + ext
            if os.path.isfile(p):
                out.append((p, r))
                break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip", nargs="?")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--card", help="check against this card instead of the recipe's")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    rows = []
    if a.clip:
        m = analyse(a.clip)
        rows.append((a.clip, a.card or "", m, verdict(m, a.card or "") if a.card else None))
    elif a.sweep:
        cs = clips()
        if a.limit:
            cs = cs[:a.limit]
        print("  %d clip(s) with a recipe" % len(cs))
        for p, r in cs:
            card = r.get("camera") if r.get("camera") in EXPECT else r.get("motion") or ""
            m = analyse(p)
            if "error" in m:
                print("  %-34s %s" % (os.path.basename(p)[:34], m["error"]))
                continue
            v = verdict(m, card) if card else None
            rows.append((p, card, m, v))
            mark = "" if not v or not v.get("known") else ("PASS" if v["pass"] else "FAIL")
            print("  %-30s %-9s pan %6.1f/%-6.1f div %6.1f c/e %5.2f  %s"
                  % (os.path.basename(p)[:30], card[:9], m["pan_x"], m["pan_y"],
                     m["div"], (m["centre_over_edge"] if m["centre_over_edge"] is not None
                                else float("nan")), mark))
            if v and v.get("known") and not v["pass"]:
                for f in v["fails"][:2]:
                    print("       %s" % f)
    else:
        ap.error("give a clip or --sweep")

    if a.json:
        print(json.dumps([{"file": p, "card": c, "measured": m, "verdict": v}
                          for p, c, m, v in rows], indent=1))
        return 0
    known = [r for r in rows if r[3] and r[3].get("known")]
    if known:
        ok = sum(1 for r in known if r[3]["pass"])
        print("\n  %d of %d clips match their card. %d have no recorded signature."
              % (ok, len(known), len(rows) - len(known)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
