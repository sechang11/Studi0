#!/usr/bin/env python3
"""Does a depth guide make LTX-2.3 perform a camera move it will not perform from words?

THE CLAIM (r/comfyui "RTX 5090 vs. ComfyUI", 2026-09): the LTX 2.3 IC-LoRA union-control workflow
gives the control over movement that prompting does not. The LoRA has been on this box since July
and no workflow ever named it (docs/STATE.md: "yes | nothing").

THE GAP IT WOULD FILL, already measured here: studio/samples/motion_lib asked LTX for camera moves
in words. cammeasure reads the push as "push in 54%", and the pull back and the track left as
STATIC, and the rise as "pan right 7%". Only the push - the move LTX makes unasked - came back.

THE TEST. A pull back with an exact ground truth: cafe-morning's day plate, cropped from 1.35x down
to 1.0x over 121 frames with an ease in-out - arithmetic, no model. Its first frame is the start
frame for both arms, so the guide and the picture agree at frame 0.

    words   start frame + "The camera pulls back slowly and steadily ..."       no guide
    guide   the same + the rig clip's MoGe-2 depth through the IC-LoRA           workflow 74

Three seeds each. cammeasure on every take, against cammeasure on the rig clip itself.

    ~/ComfyUI/venv/bin/python3 studio/_tools/ic_lora_test.py [--seeds 11 202 3003] [--measure-only]
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

from PIL import Image

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
TOOLS = os.path.join(STUDIO, "_tools")
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run                      # noqa: E402
from epic import COMFY, HOST, load_wf      # noqa: E402

OUT = os.path.join(STUDIO, "samples", "ic_lora")
PLATE = os.path.join(STUDIO, "foundry", "places", "cafe-morning", "day_wide.png")
WF = "74_ltx23_ic_lora_control.json"
W, H, FRAMES, FPS = 1280, 704, 121, 25
Z0, Z1 = 1.35, 1.0
ARMS = ("words", "guide")
GUIDE_ONLY = ("sg1_115", "sg1_106", "sg1_195", "sg1_196", "sg2_32", "199", "sg2_70", "sg2_37",
              "sg2_36", "sg2_40", "sg2_42", "sg2_53", "sg2_13", "sg2_25")


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def rig():
    """The ground-truth pull back, frame by frame, sub-pixel."""
    os.makedirs(OUT, exist_ok=True)
    im = Image.open(PLATE).convert("RGB")
    pw, ph = im.size
    aspect = W / H
    cw, chh = (int(ph * aspect), ph) if pw / ph > aspect else (pw, int(pw / aspect))
    x, y = (pw - cw) // 2, (ph - chh) // 2
    base = im.crop((x, y, x + cw, y + chh)).resize((W * 2, H * 2), Image.LANCZOS)
    tmp = tempfile.mkdtemp()
    for i in range(FRAMES):
        e = 0.5 - 0.5 * math.cos(math.pi * i / (FRAMES - 1))
        z = Z0 + (Z1 - Z0) * e
        vw, vh = base.width / z, base.height / z
        x0, y0 = (base.width - vw) / 2, (base.height - vh) / 2
        fr = base.transform((W, H), Image.EXTENT, (x0, y0, x0 + vw, y0 + vh), Image.BICUBIC)
        fr.save(os.path.join(tmp, "f%04d.png" % i))
        if i == 0:
            fr.save(os.path.join(OUT, "start.png"))
    clip = os.path.join(OUT, "rig_pull_back.mp4")
    sh("ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "f%04d.png"),
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "12", clip)
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.copy(clip, os.path.join(COMFY, "input", "iclora_control.mp4"))
    shutil.copy(os.path.join(OUT, "start.png"), os.path.join(COMFY, "input", "iclora_start.png"))
    n = sh("ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
           "stream=nb_read_frames", "-of", "csv=p=0", clip).stdout.strip()
    print("rig: %s, %s frames, zoom %.2f -> %.2f" % (clip, n, Z0, Z1), flush=True)
    return clip


def graph(arm, seed):
    wf = {k: v for k, v in load_wf(WF).items() if isinstance(v, dict) and "class_type" in v}
    if arm == "words":
        wf["sg1_704"]["inputs"]["model"] = ["distill", 0]
        wf["sg1_704"]["inputs"]["positive"] = ["sg1_109", 0]
        wf["sg1_704"]["inputs"]["negative"] = ["sg1_109", 1]
        wf["sg1_119"]["inputs"]["video_latent"] = ["sg1_198", 0]
        wf["sg1_105"]["inputs"]["samples"] = ["sg1_121", 0]
        for k in GUIDE_ONLY:
            del wf[k]
    wf["sg1_704"]["inputs"]["seed"] = int(seed)
    wf["68"]["inputs"]["filename_prefix"] = "claude-generated/iclora/%s_s%d" % (arm, seed)
    return wf


def queue_empty(budget=3600):
    import urllib.request
    t0 = time.time()
    while time.time() - t0 < budget:
        q = json.load(urllib.request.urlopen("http://%s/queue" % HOST, timeout=20))
        if not q["queue_running"] and not q["queue_pending"]:
            return True
        print("  ComfyUI is busy - waiting", flush=True)
        time.sleep(30)
    return False


def render(seeds):
    import post
    tp = os.path.join(OUT, "times.json")
    times = json.load(open(tp)) if os.path.exists(tp) else {}
    first = True
    for seed in seeds:
        for arm in ARMS:
            tag = "%s_s%d" % (arm, seed)
            dst = os.path.join(OUT, tag + ".mp4")
            if os.path.exists(dst):
                continue
            queue_empty()
            if first:
                have, why = post.make_room(need_gb=28.0, budget=240)
                print("GPU before the first submit: %.1f GB free (%s)" % (have, why), flush=True)
                first = False
            t0 = time.time()
            _, outs = run(HOST, graph(arm, seed), quiet=True)
            vids = [o for o in outs or [] if str(o).lower().endswith(".mp4")]
            if not vids:
                print("  %s: NO VIDEO (%s)" % (tag, outs), flush=True)
                continue
            shutil.copy(os.path.join(COMFY, "output", vids[0]), dst)
            times[tag] = round(time.time() - t0, 1)
            json.dump(times, open(tp, "w"), indent=1)
            print("  %-10s %5.0fs" % (tag, times[tag]), flush=True)


def cam(path):
    r = sh("python3", os.path.join(TOOLS, "cammeasure.py"), path)
    for line in r.stdout.splitlines():
        try:
            return json.loads(line)
        except Exception:
            pass
    return {}


def strip(video, dst, n=6, h=140):
    dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                   video).stdout.strip() or 0)
    ims = []
    for i in range(n):
        p = dst + ".%d.png" % i
        sh("ffmpeg", "-y", "-v", "error", "-ss", "%.2f" % (dur * i / max(1, n - 1) * 0.98), "-i", video,
           "-frames:v", "1", "-vf", "scale=-2:%d" % h, p)
        if os.path.exists(p):
            ims.append(Image.open(p).convert("RGB"))
            os.remove(p)
    if ims:
        s = Image.new("RGB", (sum(i.width for i in ims), h))
        x = 0
        for im in ims:
            s.paste(im, (x, 0))
            x += im.width
        s.save(dst, quality=86)


def rmse(a, b, ch):
    n = min(len(a), len(b))
    if not n:
        return None
    return round(math.sqrt(sum((a[i][ch] - b[i][ch]) ** 2 for i in range(n)) / n), 4)


def measure(seeds):
    clip = os.path.join(OUT, "rig_pull_back.mp4")
    truth = cam(clip)
    strip(clip, os.path.join(OUT, "rig_strip.jpg"))
    rows = {}
    for seed in seeds:
        for arm in ARMS:
            tag = "%s_s%d" % (arm, seed)
            v = os.path.join(OUT, tag + ".mp4")
            if not os.path.exists(v):
                continue
            m = cam(v)
            strip(v, os.path.join(OUT, tag + "_strip.jpg"))
            rows[tag] = {"arm": arm, "seed": seed, "zoom": m.get("zoom"), "pan": m.get("pan"),
                         "tilt": m.get("tilt"), "camera": m.get("camera"), "confidence": m.get("confidence"),
                         "zoom_error": round(abs((m.get("zoom") or 0) - (truth.get("zoom") or 0)), 3),
                         "curve_rmse_zoom": rmse(m.get("curve") or [], truth.get("curve") or [], 0),
                         "curve": m.get("curve")}
    summary = {}
    for arm in ARMS:
        rs = [r for r in rows.values() if r["arm"] == arm]
        if rs:
            zs = [r["zoom"] for r in rs]
            summary[arm] = {"zoom_mean": round(sum(zs) / len(zs), 3), "zoom_min": min(zs), "zoom_max": max(zs),
                            "zoom_error_mean": round(sum(r["zoom_error"] for r in rs) / len(rs), 3),
                            "curve_rmse_zoom_mean": round(sum(r["curve_rmse_zoom"] or 0 for r in rs) / len(rs), 4),
                            "reads": [r["camera"] for r in rs]}
    report = {"rig": {"zoom_from": Z0, "zoom_to": Z1, "frames": FRAMES, "fps": FPS, "measured": truth},
              "summary": summary, "takes": rows,
              "times": json.load(open(os.path.join(OUT, "times.json"))) if os.path.exists(os.path.join(OUT, "times.json")) else {}}
    json.dump(report, open(os.path.join(OUT, "results.json"), "w"), indent=1)
    print("\nground truth (the rig clip): zoom %.3f pan %+.3f tilt %+.3f -> %s" % (
        truth.get("zoom", 0), truth.get("pan", 0), truth.get("tilt", 0), truth.get("camera")))
    print("%-10s %7s %7s %7s  %-9s %s" % ("take", "zoom", "pan", "tilt", "rmse(z)", "read"))
    for tag, r in rows.items():
        print("%-10s %7.3f %+7.3f %+7.3f  %-9s %s (%s)" % (tag, r["zoom"] or 0, r["pan"] or 0, r["tilt"] or 0,
                                                         r["curve_rmse_zoom"], r["camera"], r["confidence"]))
    for arm, s in summary.items():
        print("  %-6s zoom mean %.3f (%.3f..%.3f), error vs truth %.3f, curve rmse %.4f" % (
            arm, s["zoom_mean"], s["zoom_min"], s["zoom_max"], s["zoom_error_mean"], s["curve_rmse_zoom_mean"]))
    print("IC_LORA DONE", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[11, 202, 3003])
    ap.add_argument("--measure-only", action="store_true")
    a = ap.parse_args()
    if not a.measure_only:
        rig()
        render(a.seeds)
    measure(a.seeds)


if __name__ == "__main__":
    main()
