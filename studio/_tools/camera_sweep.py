#!/usr/bin/env python3
"""Measure what every camera move actually does.

The camera-reliability table in the craft docs is INFERRED, never measured - the audit
that produced it said so explicitly and recommended running this sweep. It was never run,
and camera is the user's number-one complaint ("there seems to be a left pan for every
single video clip").

This is cheap to settle because the moves are NOT asked of the video model. short.py's
fx_chain() implements them as ffmpeg zoompan/crop operations applied to an already
generated clip. So one source clip plus N filter chains is a perfectly controlled
experiment: identical content, identical seed, only the move differs.

Output per move:
  samples/cameras/<move>.mp4        the moving clip, for the app
  samples/cameras/<move>.jpg        a 3-frame strip (start / middle / end) so the
                                    displacement is visible in a still

    python3 studio/_tools/camera_sweep.py [source.mp4]
"""
import os, subprocess, sys

import argparse
argparse.ArgumentParser(description='camera sweep').parse_args()
# ^ the CLI contract: --help exits HERE, before any work below runs.
HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from short import fx_chain, VID, FPS   # noqa: E402  the real implementation, not a copy

OUT = os.path.join(STUDIO, "samples", "cameras")
MOVES = ["static", "push", "pull", "pan_l", "pan_r", "tilt_u", "tilt_d", "handheld"]
SECS = 3.0


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def pick_source():
    """A STILL, not a clip.

    The first version of this swept a generated clip and produced eight panels that
    were, to the eye, identical. Measuring showed the moves were working perfectly
    (pan_l vs pan_r differed by 70.9 mean abs pixel value) - the problem was the
    source. That clip's own content changed by 78.6 between its first and last frame,
    a face becoming a ball becoming a dust cloud, which completely swamps a ~100px
    camera translation.

    A camera-move demonstration must hold content still, or the camera is not what
    you are looking at. So drive a KEYFRAME instead: content frozen, camera the only
    variable. This is the same reason the capability cards fix subject and seed and
    vary exactly one thing.
    """
    if len(sys.argv) > 1:
        return sys.argv[1]
    base = os.path.expanduser("~/ComfyUI/output/claude-generated/12-shorts")
    best = None
    for dirpath, _, names in os.walk(base):
        if not dirpath.endswith("/keyframes"):
            continue
        for n in sorted(names):
            if n.endswith(".png"):
                p = os.path.join(dirpath, n)
                if best is None or os.path.getsize(p) > os.path.getsize(best):
                    best = p
    return best


def main():
    src = pick_source()
    if not src or not os.path.isfile(src):
        raise SystemExit("no source clip found - pass one explicitly")
    print("source: %s" % src)
    os.makedirs(OUT, exist_ok=True)
    w, h = VID

    for mv in MOVES:
        chain = fx_chain([mv], w, h, FPS, seed=0, length=SECS)
        vf = ",".join(x for x in ["eq=contrast=1.06:saturation=1.12", chain] if x)
        clip = os.path.join(OUT, mv + ".mp4")
        still = src.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        pre = ["-loop", "1", "-framerate", str(FPS)] if still else []
        # a still must be scaled to the clip size first, or the move maths is off
        vf_full = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                   f"crop={w}:{h}," + vf) if still else vf
        r = sh("ffmpeg", "-y", "-v", "error", *pre, "-t", "%.2f" % SECS, "-i", src,
               "-vf", vf_full, "-an", "-r", str(FPS), "-c:v", "libx264", "-crf", "18",
               "-preset", "veryfast", "-pix_fmt", "yuv420p", clip)
        if r.returncode != 0:
            print("  %-9s FAILED: %s" % (mv, r.stderr.strip()[:160]))
            continue

        # 3-frame strip: the whole point is to make MOTION legible in a still.
        cells = []
        for i, t in enumerate((0.05, SECS / 2, SECS - 0.10)):
            c = "/tmp/_cam_%s_%d.png" % (mv, i)
            sh("ffmpeg", "-y", "-v", "error", "-ss", "%.2f" % t, "-i", clip,
               "-frames:v", "1", "-vf",
               "scale=380:-1,drawtext=text='%s  t=%.1fs':fontcolor=yellow:fontsize=17:"
               "x=6:y=6:box=1:boxcolor=black@0.75:boxborderw=4" % (mv, t), c)
            if os.path.exists(c):
                cells.append(c)
        if len(cells) == 3:
            strip = os.path.join(OUT, mv + ".jpg")
            sh("ffmpeg", "-y", "-v", "error", "-i", cells[0], "-i", cells[1], "-i", cells[2],
               "-filter_complex", "[0][1][2]hstack=inputs=3", "-q:v", "5", strip)
            for c in cells:
                os.remove(c)
        print("  %-9s %6.1f KB clip   chain: %s"
              % (mv, os.path.getsize(clip) / 1024, chain[:88] or "(none - static)"))

    print("\nwrote %d moves to %s" % (len(MOVES), OUT))


if __name__ == "__main__":
    main()
