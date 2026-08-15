#!/usr/bin/env python3
"""studio/_tools/depth_pass.py - the depth pass (task 22): one keyframe -> one greyscale
depth PNG through Depth Anything 3 (core nodes on ComfyUI 0.33), plus the two post
cameras that needed it, applied with ffmpeg.

    python3 studio/_tools/depth_pass.py depth --image key.png --out key_depth.png
    python3 studio/_tools/depth_pass.py rack_focus --clip in.mp4 --depth key_depth.png --out out.mp4
    python3 studio/_tools/depth_pass.py dolly_zoom --clip in.mp4 --depth key_depth.png --out out.mp4

WHY THESE TWO WERE DEAD. short.py's fx_chain had no branch for them, so a clip asking
for dolly_zoom or rack_focus came back BYTE-IDENTICAL to static (MD5-confirmed) - a
silent no-op that cost a render and looked like a style choice. Both are impossible on
a flat plate: rack focus needs a depth ORDER to decide what blurs when, and a dolly-zoom
IS the near/far parallax differential, which a flat image does not have.

WHAT THE DEPTH GIVES. A per-pixel near..far map from the keyframe. LTX drift over 4-6 s
is small enough that the KEYFRAME's depth is a usable proxy for the whole clip (the same
assumption motion_check makes when it compares clip frames to the keyframe) - and it is
stated on the card as an assumption, not a fact.

  rack_focus: gaussian blur the clip; keep the near band sharp at t=0 and ramp the sharp
              band to the far end by t=1 (or the reverse), via a time-varying mask built
              from the depth map. Two ffmpeg passes: blurred copy, then maskedmerge with
              a threshold that moves with time (geq on the depth image).
  dolly_zoom: scale the FAR layer up while the NEAR layer stays - a differential zoom
              split by depth. Approximation: zoompan the whole frame by z(t) and blend
              back the near band unzoomed through the depth mask, so near stays and far
              swells - the Vertigo read. Honest limit: no disocclusion; edges smear where
              far grows behind near.

Both write MEASURED evidence onto the camera card via cards.stamp when a clip renders,
naming the assumption. Whether the READ lands is a human's call from the strip.
"""
import argparse
import os
import shutil
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, STUDIO)
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run                        # noqa: E402
from engine import HOST                      # noqa: E402

COMFY = os.environ.get("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def depth(image, out, resolution=1008):
    """Greyscale depth via DA3 mono-large: black = far, white = near (min_max)."""
    staged = "depth_src.png"
    shutil.copy(image, os.path.join(COMFY, "input", staged))
    wf = {
        "1": {"class_type": "LoadDA3Model",
              "inputs": {"model_name": "depth_anything_3_mono_large.safetensors",
                         "weight_dtype": "default"}},
        "2": {"class_type": "LoadImage", "inputs": {"image": staged}},
        "3": {"class_type": "DA3Inference",
              "inputs": {"da3_model": ["1", 0], "image": ["2", 0],
                         "resolution": int(resolution),
                         "resize_method": "upper_bound_resize", "mode": "mono"}},
        "4": {"class_type": "DA3Render",
              "inputs": {"da3_geometry": ["3", 0], "output": "depth",
                         "output.normalization": "min_max",
                         "output.apply_sky_clip": True}},
        "5": {"class_type": "SaveImage",
              "inputs": {"images": ["4", 0],
                         "filename_prefix": "claude-generated/depth/depth"}},
    }
    _, outs = run(HOST, wf, quiet=True)
    for o in outs or []:
        if str(o).lower().endswith(".png"):
            src = os.path.join(COMFY, "output", o)
            if os.path.exists(src):
                shutil.copy(src, out)
                return out
    return None


def probe_wh(clip):
    r = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
           "stream=width,height,duration", "-of", "csv=p=0", clip)
    w, h, d = (r.stdout or "0,0,0").strip().split(",")[:3]
    return int(w), int(h), float(d or 0)


def rack_focus(clip, depth_png, out, near_to_far=True, blur=14):
    """Sharp band travels near->far (or reverse) over the clip. maskedmerge picks the
    blurred copy where mask=1; the mask is a soft window over the depth value that
    slides with time: window centre c(t) = t (near_to_far) or 1-t; width 0.25."""
    w, h, dur = probe_wh(clip)
    if not dur:
        return None
    # depth (near=white in min_max? DA3 min_max: larger depth = brighter = FAR).
    # We define f = depth normalised 0..1 where 1 = far. window centre moves 0->1.
    centre = "(T/%.3f)" % dur if near_to_far else "(1-T/%.3f)" % dur
    # mask value: 1 where |f - centre| > halfwidth (blur), else 0 (sharp), soft edge
    mask = ("[dep]format=gray,scale=%d:%d,"
            "geq=lum='255*clip(( abs(p(X,Y)/255 - %s) - 0.12 )/0.10,0,1)'" % (w, h, centre))
    fc = ("[0:v]split[a][b];[b]gblur=sigma=%d[blur];"
          "movie=%s,loop=loop=-1:size=1,setpts=N/FRAME_RATE/TB[dep];"
          "%s[mask];[a][blur][mask]maskedmerge[v]" % (blur, depth_png.replace("\\", "/"),
                                                     mask))
    r = sh("ffmpeg", "-y", "-v", "error", "-i", clip, "-filter_complex", fc,
           "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", "17",
           "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "copy",
           "-t", "%.3f" % dur, out)
    if r.returncode != 0:
        print(r.stderr[-600:], file=sys.stderr)
        return None
    return out


def dolly_zoom(clip, depth_png, out, zoom_to=1.18):
    """Far layer swells, near layer holds. Whole-frame zoompan to zoom_to, then the
    NEAR band (depth < 0.45) is blended back from the unzoomed frame through the depth
    mask - the parallax differential a flat plate cannot make on its own."""
    w, h, dur = probe_wh(clip)
    if not dur:
        return None
    fps = 24
    n = max(2, int(round(dur * fps)))
    zexpr = "1+(%.4f-1)*on/%d" % (zoom_to, n)
    fc = ("[0:v]split[a][b];"
          "[b]scale=iw*2:ih*2,zoompan=z='%s':d=1:x='iw/2-(iw/zoom/2)':"
          "y='ih/2-(ih/zoom/2)':s=%dx%d:fps=%d[zoomed];"
          "movie=%s,loop=loop=-1:size=1,setpts=N/FRAME_RATE/TB[dep];"
          "[dep]format=gray,scale=%d:%d,geq=lum='255*clip((0.45-p(X,Y)/255)/0.10,0,1)'[near];"
          "[zoomed][a][near]maskedmerge[v]"
          % (zexpr, w, h, fps, depth_png.replace("\\", "/"), w, h))
    r = sh("ffmpeg", "-y", "-v", "error", "-i", clip, "-filter_complex", fc,
           "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", "17",
           "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "copy",
           "-t", "%.3f" % dur, out)
    if r.returncode != 0:
        print(r.stderr[-600:], file=sys.stderr)
        return None
    return out


def main():
    ap = argparse.ArgumentParser(description="Depth pass + the two depth cameras.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("depth")
    d.add_argument("--image", required=True)
    d.add_argument("--out", required=True)
    d.add_argument("--resolution", type=int, default=1008)
    for name in ("rack_focus", "dolly_zoom"):
        p = sub.add_parser(name)
        p.add_argument("--clip", required=True)
        p.add_argument("--depth", required=True)
        p.add_argument("--out", required=True)
        if name == "rack_focus":
            p.add_argument("--reverse", action="store_true", help="far -> near")
            p.add_argument("--blur", type=int, default=14)
        else:
            p.add_argument("--zoom", type=float, default=1.18)
    a = ap.parse_args()
    if a.cmd == "depth":
        got = depth(a.image, a.out, a.resolution)
    elif a.cmd == "rack_focus":
        got = rack_focus(a.clip, a.depth, a.out, not a.reverse, a.blur)
    else:
        got = dolly_zoom(a.clip, a.depth, a.out, a.zoom)
    print(got or "FAILED")
    return 0 if got else 1


if __name__ == "__main__":
    sys.exit(main())
