#!/usr/bin/env python3
"""studio/_tools/post.py - the finish: one grade on every shot, and an optional 2x master.

    "The generation is the shoot - the edit is the movie."  Post is the half of the film this
    studio was not doing.  Assembly normalised, concatenated, mixed music and levelled loudness,
    and delivered 1472x832 with no grade at all.

TWO JOBS, both deterministic, both ffmpeg-honest:

  grade     One filter line applied to the whole assembled film in its final encode.  That is
            "one grade line, every shot" for free: every take gets the identical treatment, and
            it is applied AFTER the cuts, so nothing can drift between shots.  The named grades
            below were measured on ten frames from two delivered films with vibrancy.py
            (mean saturation, 90th-percentile saturation, mean value, share of blown pixels) and
            then LOOKED at on a contact sheet, because the strongest one by the numbers -
            `vibrance`, +49% saturation - blew ten times the highlights and turned every yellow
            to poster paint.  The tool's own rule: a grade that wins by clipping has not won.

  upscale   RealESRGAN x4 on every frame, resampled to 2x - 1472x832 becomes 2944x1664 - with
            the take's own audio re-muxed.  Runs the model directly through spandrel in the
            ComfyUI venv rather than through a workflow, because pushing three hundred frames
            one at a time through the HTTP API is the wrong shape for a video.  film_routes runs
            under system python3, which has no torch, so it calls this file as a subprocess.

THE CARD IS SHARED, and the first attempt forgot it.  ComfyUI keeps LTX-2.5 resident after a
render - 27.8 GB of 31.4 - and every frame of the first finish failed with 500 MB free.  So the
upscaler first asks ComfyUI to release its models (/free, honoured between prompts, never
mid-render) and waits for the memory to actually appear, and then works in TILES so the x4
intermediates never need gigabytes at once.  The next render re-stages the model in under a
minute, which is the right trade at finish time.

    ~/ComfyUI/venv/bin/python3 studio/_tools/post.py upscale IN.mp4 OUT.mp4 [--scale 2]
    python3 studio/_tools/post.py grades                       # the named grades and their basis
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COMFY = os.path.expanduser("~/ComfyUI")
COMFY_HOST = os.environ.get("COMFY_HOST", "127.0.0.1:8188")
ESRGAN = os.path.join(COMFY, "models", "upscale_models", "RealESRGAN_x4plus.safetensors")
NEED_GB = 6.0          # what a tiled x4 pass comfortably needs; measured OOM at 0.5 free

# name -> (ffmpeg -vf, what a person needs to know).  Measured 2026-09-07 on ten frames from
# two delivered films (angles-and-mass, lenga2) against no grade at all.
GRADES = {
    "none":   (None,
               "no grade - the film exactly as the engines made it"),
    "soft":   ("eq=contrast=1.06:saturation=1.12",
               "the old base: +7% saturation, brightness unchanged - barely visible"),
    "filmic": ("curves=all='0/0.02 0.22/0.26 0.5/0.58 0.78/0.88 1/0.995',"
               "eq=saturation=1.22,colorbalance=gm=-0.05:rm=0.05:bh=0.03",
               "opens the shadows and warms the mids: +11% saturation, +20% brightness, "
               "few blown pixels - the default"),
    "punchy": ("curves=all='0/0.02 0.22/0.28 0.5/0.60 0.78/0.88 1/0.995',eq=saturation=1.42",
               "+17% saturation, +27% brightness - for daylight and anime; skin can go orange"),
}
DEFAULT_GRADE = "filmic"


def sh(*a, **kw):
    return subprocess.run(a, capture_output=True, text=True, **kw)


def grade_filter(name):
    """the -vf string for a named grade, or None for no grade; unknown names fall to default"""
    return GRADES.get(name or DEFAULT_GRADE, GRADES[DEFAULT_GRADE])[0]


def probe(path):
    r = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
           "stream=width,height,r_frame_rate", "-of", "json", path)
    try:
        s = json.loads(r.stdout)["streams"][0]
        num, den = s["r_frame_rate"].split("/")
        return int(s["width"]), int(s["height"]), float(num) / float(den)
    except Exception:
        return None


def free_gb():
    import torch
    if not torch.cuda.is_available():
        return 0.0
    free, _total = torch.cuda.mem_get_info()
    return free / 2 ** 30


def make_room(need_gb=NEED_GB, budget=150):
    """Ask ComfyUI to drop its resident models and wait until the memory is really there.

    /free sets a flag the queue honours between prompts, so a render in flight finishes first
    and is never interrupted; this waits for the memory rather than trusting the request."""
    have = free_gb()
    if have >= need_gb:
        return have, "already free"
    try:
        req = urllib.request.Request(
            "http://%s/free" % COMFY_HOST,
            data=json.dumps({"unload_models": True, "free_memory": True}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=20).read()
    except Exception as e:
        return have, "ComfyUI /free not reachable (%s)" % str(e)[:60]
    t0 = time.time()
    while time.time() - t0 < budget:
        time.sleep(3)
        have = free_gb()
        if have >= need_gb:
            return have, "ComfyUI released its models after %.0fs" % (time.time() - t0)
    return have, "waited %.0fs and only %.1f GB came free" % (budget, have)


def tiled(model, x, tile=384, overlap=24, scale=4):
    """Run an image model over one NCHW tensor in overlapping tiles and stitch the centres.

    Peak memory is set by the tile, not the frame: a 1472x832 frame through a x4 network wants
    gigabytes for its intermediates in one go and a few hundred megabytes tile by tile."""
    import torch
    _, _, h, w = x.shape
    out = torch.zeros((x.shape[0], 3, h * scale, w * scale), dtype=x.dtype, device=x.device)
    step = tile - overlap
    # grid positions, with the last tile pulled back so it is a full tile ending at the edge
    ys = sorted({min(y, max(h - tile, 0)) for y in range(0, h, step)})
    xs = sorted({min(v, max(w - tile, 0)) for v in range(0, w, step)})
    m = overlap // 2
    for y0 in ys:
        for x0 in xs:
            y1, x1 = min(y0 + tile, h), min(x0 + tile, w)
            patch = model(x[:, :, y0:y1, x0:x1])          # (1, 3, (y1-y0)*scale, (x1-x0)*scale)
            # keep the centre of each tile; half the overlap belongs to each neighbour, so
            # adjacent centres abut exactly on the grid and the clamped last tile overwrites
            cy0 = 0 if y0 == 0 else m
            cx0 = 0 if x0 == 0 else m
            cy1 = (y1 - y0) if y1 == h else (y1 - y0) - m
            cx1 = (x1 - x0) if x1 == w else (x1 - x0) - m
            out[:, :, (y0 + cy0) * scale:(y0 + cy1) * scale,
                (x0 + cx0) * scale:(x0 + cx1) * scale] = \
                patch[:, :, cy0 * scale:cy1 * scale, cx0 * scale:cx1 * scale]
    return out


def upscale(src, dst, scale=2, fine=False):
    """RealESRGAN x4 per frame in tiles, resampled to `scale`x, audio re-muxed from the source.

    fast (default): the frame is halved first and the x4 network delivers 2x directly - 0.35 s
    a frame on this card.  fine: x4 on the full frame, then resampled down - 2.15 s a frame,
    carrying detail below the half-resolution grid instead of re-synthesising it.

    Frames stream through ffmpeg as raw RGB in both directions: no intermediate files, no PNG
    codec.  The first working version wrote and read a PNG per frame and spent most of its
    4m43 on a four-second take doing that."""
    import numpy as np
    import torch
    import spandrel
    if not os.path.exists(src):
        return None, "missing %s" % src
    if not os.path.exists(ESRGAN):
        return None, "no upscale model at %s" % ESRGAN
    info = probe(src)
    if not info:
        return None, "cannot probe %s" % src
    w, h, fps = info
    tw, th = (w * scale) // 2 * 2, (h * scale) // 2 * 2
    have, why = make_room()
    if have < 2.0:
        return None, "not enough GPU memory to master (%.1f GB free; %s)" % (have, why)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    desc = spandrel.ModelLoader().load_from_file(ESRGAN).eval().to(dev)
    half = dev == "cuda" and bool(getattr(desc, "supports_half", False))
    if half:
        desc.model.half()
    mscale = int(getattr(desc, "scale", 4) or 4)
    # fast: shrink the input so the network's own scale lands on the wanted size (x4 on a half
    # frame is 2x); fine: full frame through the network, resampled down afterwards
    pre = 1.0 if (fine or mscale <= scale) else float(scale) / float(mscale)
    tile = 768
    vid = dst + "_v.mp4"
    reader = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE, bufsize=10 ** 8)
    writer = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", "%dx%d" % (tw, th), "-r", "%.6f" % fps, "-i", "-",
         "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", vid],
        stdin=subprocess.PIPE)
    nbytes = w * h * 3
    n = 0
    try:
        with torch.no_grad():
            while True:
                buf = reader.stdout.read(nbytes)
                if len(buf) < nbytes:
                    break
                arr = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 3)
                x = torch.from_numpy(arr.copy()).to(dev).permute(2, 0, 1).unsqueeze(0)
                x = (x.half() if half else x.float()) / 255.0
                if pre != 1.0:
                    # fast path: the network's x4 lands exactly on the wanted size
                    x = torch.nn.functional.interpolate(x.float(), scale_factor=pre, mode="area")
                    x = x.half() if half else x
                while True:
                    try:
                        y = tiled(desc, x, tile=tile, scale=mscale).clamp_(0, 1)
                        break
                    except torch.OutOfMemoryError:
                        torch.cuda.empty_cache()
                        if tile <= 96:
                            raise
                        tile //= 2          # the same recovery ComfyUI's own upscale node uses
                if y.shape[2] != th or y.shape[3] != tw:
                    y = torch.nn.functional.interpolate(y.float(), size=(th, tw), mode="bicubic",
                                                        antialias=True, align_corners=False)
                y = (y.clamp_(0, 1) * 255.0).round().byte()[0].permute(1, 2, 0).contiguous()
                writer.stdin.write(y.cpu().numpy().tobytes())
                n += 1
                del x, y
    finally:
        reader.stdout.close()
        reader.wait()
        writer.stdin.close()
        writer.wait()
        if dev == "cuda":
            torch.cuda.empty_cache()
    if n == 0 or not os.path.exists(vid):
        return None, "no frames encoded"
    # the take's own audio, untouched
    sh("ffmpeg", "-y", "-v", "error", "-i", vid, "-i", src, "-map", "0:v", "-map", "1:a?",
       "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", dst)
    try:
        os.remove(vid)
    except OSError:
        pass
    if not os.path.exists(dst):
        return None, "mux failed"
    out = probe(dst)
    return dst, ("%d frames %dx%d -> %dx%d, %s, tile %d, %s"
                 % (n, w, h, out[0], out[1], "fine" if pre == 1.0 else "fast", tile, why)) \
        if out else "?"


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("upscale")
    u.add_argument("src")
    u.add_argument("dst")
    u.add_argument("--scale", type=int, default=2)
    u.add_argument("--fine", action="store_true",
                   help="x4 on the full frame then down (2.15 s/frame) instead of half-then-x4 "
                        "(0.35 s/frame)")
    sub.add_parser("grades")
    a = ap.parse_args()
    if a.cmd == "grades":
        for k, (vf, note) in GRADES.items():
            print("%-7s %s%s\n        %s" % (k, "(default) " if k == DEFAULT_GRADE else "",
                                            vf or "-", note))
        return
    try:
        out, info = upscale(a.src, a.dst, a.scale, fine=a.fine)
    except Exception as e:           # a traceback on stderr is invisible to the caller's log
        out, info = None, "%s: %s" % (type(e).__name__, str(e)[:160])
    print(("-> %s  %s" % (out, info)) if out else ("FAILED: %s" % info), flush=True)
    sys.exit(0 if out else 1)


if __name__ == "__main__":
    main()
