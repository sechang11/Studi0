#!/usr/bin/env python3
"""Does H3 ref2va carry a character from a REFERENCE PICTURE, with no composited start frame?

docs/WHERE-WE-STAND.md says the multi-reference row is an architectural gap: "nothing takes N
tagged identities".  That was written without looking in comfy_extras: MiniMaxH3ReferenceToVideo
takes up to nine reference images, addressed in the prompt as <Picture 1>, <Picture 2> ..., and
the 19.5 GB ref2va weights have been on disk since the collector was built - "in case words are
not enough".  Nobody wired them.  This wires them once and measures.

THE TEST.  The method's worked example, shot 1: Terra at the foot of the forest-shrine steps at
dawn, wide, static.  The i2v route rendered it from a composited start frame and the studio read
identity 0.65 at the first frame (same person).  Here the engine gets Terra's portrait as
<Picture 1> and the dawn plate as <Picture 2>, a paragraph, and NO start frame.  If the first and
last frames score as the same person against her portrait, the reference route exists and the
comparison table is wrong in our favour.  If they score as strangers, ref2va "reinforces an
identity the prompt already asks for; it does not supply one" - the IPAdapter lesson again - and
the row stands with a footnote.

    ~/ComfyUI/venv/bin/python3 ref2va_test.py [--steps 4] [--no-lora] [--seed 4200]
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
TOOLS = os.path.join(STUDIO, "_tools")
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run, set_path            # noqa: E402
from epic import COMFY, HOST, load_wf      # noqa: E402
import headbox as HB                       # noqa: E402

PY = os.path.expanduser("~/ComfyUI/venv/bin/python3")
OUT = os.path.join(STUDIO, "samples", "ref2va")
PORTRAIT = os.path.join(STUDIO, "foundry", "characters", "terra", "base_portrait.png")
PLATE = os.path.join(STUDIO, "foundry", "places", "forest-shrine", "dawn_wide.png")

PROMPT = ("<Picture 1> stands at the foot of the shrine steps in <Picture 2>, at dawn, and slowly "
          "raises her eyes to the gate. Wide shot, the camera static. Wind moves the cedar "
          "branches; a single bell far off; no music.")


def frame(video, t, dest):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "%.2f" % t, "-i", video, "-frames:v", "1", dest],
                   capture_output=True)
    return dest if os.path.exists(dest) else None


def score(stills):
    jobs = []
    for tag, p in stills.items():
        try:
            box = HB.head_box(p)
        except Exception:
            box = None
        jobs.append({"id": tag, "portrait": PORTRAIT, "still": p, "box": box, "close": False})
    jp = os.path.join(OUT, "score_jobs.json")
    json.dump(jobs, open(jp, "w"))
    r = subprocess.run([PY, os.path.join(TOOLS, "identity.py"), jp], capture_output=True, text=True,
                       cwd=os.path.expanduser("~/ComfyUI"))
    out = {}
    for line in r.stdout.splitlines():
        try:
            d = json.loads(line)
            out[d["id"]] = (d.get("start"), d.get("verdict_start"))
        except Exception:
            pass
    return out, jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=4)
    ap.add_argument("--no-lora", action="store_true", help="drop the fl2v turbo LoRA (needs ~40 steps)")
    ap.add_argument("--seed", type=int, default=4200)
    ap.add_argument("--length", type=int, default=124)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    shutil.copy(PORTRAIT, os.path.join(COMFY, "input", "ref2va_pic1.png"))
    shutil.copy(PLATE, os.path.join(COMFY, "input", "ref2va_pic2.png"))
    wf = load_wf("63_minimax_h3_ref2va.json")
    set_path(wf, "20.inputs.prompt", PROMPT)
    set_path(wf, "20.inputs.length", int(a.length))
    set_path(wf, "32.inputs.steps", int(a.steps))
    set_path(wf, "33.inputs.noise_seed", int(a.seed))
    tag = "ref_%s_s%d_%d" % ("nolora" if a.no_lora else "turbo", a.steps, a.seed)
    set_path(wf, "51.inputs.filename_prefix", "claude-generated/h3_ref2va/" + tag)
    if a.no_lora:
        # bypass the LoRA: the sigma shift reads the base model directly
        set_path(wf, "6.inputs.model", ["1", 0])
        del wf["5"]
    # The card is shared and ComfyUI keeps the last video model resident (LTX, ~24 GB). Loading the
    # 20 GB ref2va model on top of it killed the ComfyUI process on the first attempt - no
    # traceback, the socket just closed. Ask for the memory back and wait for it, as post.py does.
    import post
    have, why = post.make_room(need_gb=26.0, budget=180)
    print("GPU before submit: %.1f GB free (%s)" % (have, why), flush=True)
    t0 = time.time()
    _, outs = run(HOST, wf, quiet=True)
    dt = time.time() - t0
    vids = [o for o in outs or [] if str(o).lower().endswith((".mp4", ".webm", ".mov"))]
    if not vids:
        print("NO VIDEO OUTPUT after %.0fs: %s" % (dt, outs), flush=True)
        sys.exit(1)
    src = os.path.join(COMFY, "output", vids[0])
    dst = os.path.join(OUT, tag + ".mp4")
    shutil.copy(src, dst)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", dst], capture_output=True, text=True).stdout.strip() or 0)
    stills = {"first": frame(dst, 0.05, os.path.join(OUT, tag + "_first.png")),
              "last": frame(dst, max(dur - 0.15, 0), os.path.join(OUT, tag + "_last.png"))}
    sc, jobs = score({k: v for k, v in stills.items() if v})
    # a strip to look at, one frame a second
    d = os.path.join(OUT, tag + "_frames")
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", dst, "-vf", "fps=1,scale=256:-2",
                    os.path.join(d, "f%03d.png")], capture_output=True)
    from PIL import Image
    fs = sorted(os.listdir(d))
    ims = [Image.open(os.path.join(d, f)).convert("RGB") for f in fs]
    if ims:
        w, h = ims[0].size
        S = Image.new("RGB", (w * len(ims), h), (16, 16, 20))
        for i, im in enumerate(ims):
            S.paste(im, (i * w, 0))
        S.save(os.path.join(OUT, tag + "_strip.jpg"), quality=86)
    shutil.rmtree(d, ignore_errors=True)
    report = {"tag": tag, "seconds": round(dt), "duration": dur, "prompt": PROMPT,
              "identity": {k: {"score": v[0], "verdict": v[1]} for k, v in sc.items()},
              "head_boxes": {j["id"]: j["box"] for j in jobs},
              "i2v_reference": {"shot": "the-method---worked-example/060", "identity_start": 0.65,
                                "note": "the same beat rendered from a composited start frame"}}
    json.dump(report, open(os.path.join(OUT, tag + ".json"), "w"), indent=1)
    print("%s: %.0fs render, %.1fs clip" % (tag, dt, dur))
    for k, (v, verdict) in sc.items():
        print("  identity %-5s %s  %s" % (k, ("%.3f" % v) if v is not None else "-", verdict or ""))
    print("  i2v route on the same beat: 0.65 at the first frame (same person)")
    print("REF2VA DONE", flush=True)


if __name__ == "__main__":
    main()
