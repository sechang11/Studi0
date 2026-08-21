#!/usr/bin/env python3
"""studio/_tools/polish.py - the finishing pass: 24 -> 48 fps, audio kept.

LTX-2.5 delivers at 24 fps. FILM interpolation doubles that for about 2.6x realtime on
this box - 39 s for a 15 s clip - and on the hardest case available (a wok fireball, all
turbulence and occlusion, which is where optical flow usually tears) the intermediate
frames came out clean. It is the cheapest real quality gain left.

THE CATCH THAT MAKES THIS A TOOL RATHER THAN A ONE-LINER: workflow 07 rebuilds the video
through CreateVideo with no audio input, so interpolating a talking scene silently throws
the dialogue away. The clip comes back looking better and saying nothing. Every output here
is re-muxed against the original's audio, and the result is checked for both streams before
it is kept.
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
COMFY = os.path.expanduser("~/ComfyUI")


# Interpolation has an envelope of its own, and it is much tighter than generation's:
# FrameInterpolate holds every frame of the clip AND every frame it invents. An 83 s
# assembled film at 1472x832 is ~2000 frames in and ~4000 out, and it killed the ComfyUI
# process outright. Polish the SCENES, then assemble - never the finished film.
MAX_SECONDS = 25


def sh(*a, **kw):
    return subprocess.run(a, capture_output=True, text=True, **kw)


def streams(path):
    r = sh("ffprobe", "-v", "error", "-show_entries", "stream=codec_type,r_frame_rate",
           "-of", "csv=p=0", path)
    return (r.stdout or "").split()


def duration(path):
    r = sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "csv=p=0", path)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def polish(src, dst, multiplier=2, fps=48):
    if not os.path.exists(src):
        return None, "missing %s" % src
    d = duration(src)
    if d > MAX_SECONDS:
        return None, ("%.0fs is past the %ds interpolation ceiling - polish the scenes, "
                      "not the assembled film" % (d, MAX_SECONDS))
    staged = "polish_%s" % os.path.basename(src)
    sh("cp", src, os.path.join(COMFY, "input", staged))
    r = sh(sys.executable, os.path.join(ROOT, "scripts", "comfy.py"), "run",
           os.path.join(ROOT, "workflows", "07_video_interpolate.json"),
           "-s", "1.inputs.file=%s" % staged,
           "-s", "4.inputs.multiplier=%d" % multiplier,
           "-s", "7.inputs.fps=%s" % float(fps),
           "-s", "8.inputs.filename_prefix=claude-generated/polish/%s"
           % os.path.splitext(os.path.basename(src))[0], cwd=ROOT)
    m = re.search(r"-> (\S+\.mp4)", r.stdout or "")
    if not m:
        return None, (r.stderr or r.stdout or "")[-200:]
    mute = os.path.join(COMFY, "output", m.group(1))
    # workflow 07 has no audio path - re-mux or the dialogue is silently lost
    sh("ffmpeg", "-y", "-v", "error", "-i", mute, "-i", src,
       "-map", "0:v", "-map", "1:a?", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
       "-shortest", dst)
    if not os.path.exists(dst):
        return None, "mux failed"
    s = streams(dst)
    if not any(x.startswith("audio") for x in s) and \
       any(x.startswith("audio") for x in streams(src)):
        return None, "audio lost in the mux"
    return dst, " ".join(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--fps", type=int, default=48)
    ap.add_argument("--multiplier", type=int, default=2)
    ap.add_argument("--suffix", default="_48")
    a = ap.parse_args()
    for f in a.files:
        src = os.path.expanduser(f)
        dst = "%s%s.mp4" % (os.path.splitext(src)[0], a.suffix)
        print("  %-26s" % os.path.basename(src), end=" ", flush=True)
        out, info = polish(src, dst, a.multiplier, a.fps)
        print("-> %s  %s" % (os.path.basename(dst) if out else "FAILED", info))


if __name__ == "__main__":
    main()
