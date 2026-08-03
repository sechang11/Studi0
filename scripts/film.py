#!/usr/bin/env python3
"""
film.py - multi-shot short film: keyframes -> clips -> edited cut.

    python3 film.py films/the-last-signal.json
    python3 film.py films/the-last-signal.json --res 480      # fast preview pass
    python3 film.py films/the-last-signal.json --stage clips  # resume
    python3 film.py films/the-last-signal.json --stage edit   # re-cut only

Why it's staged this way
------------------------
Qwen-Image (19 GB) and Wan 2.2 (2 x 13.3 GB) do not co-reside in 32 GB. Alternating
between them per shot forces a ~90 s model reload each way. So:

    stage 1  keyframes : Qwen loads once, renders every shot        (~5 s / shot)
    stage 2  clips     : Wan loads once, animates every keyframe    (~130 s / shot @720p)
    stage 3  edit      : ffmpeg cross-dissolves + titles, no GPU

On a 9-shot film that saves roughly 16 model swaps -> ~25 minutes.

Everything lands in ComfyUI/output/claude-generated/film-<slug>/
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COMFY = os.path.expanduser("~/ComfyUI")
sys.path.insert(0, HERE)
from comfy import run, set_path  # noqa: E402

HOST = os.environ.get("COMFY_HOST", "127.0.0.1:8188")

AR = {"1:1": (1328, 1328), "16:9": (1664, 928), "9:16": (928, 1664),
      "4:3": (1472, 1104), "3:2": (1584, 1056)}
VID = {"480": {"16:9": (832, 480), "9:16": (480, 832), "1:1": (640, 640)},
       "720": {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (960, 960)},
       "1080": {"16:9": (1920, 1088), "9:16": (1088, 1920), "1:1": (1440, 1440)}}

NEG_IMG = "blurry, low quality, watermark, text, caption, jpeg artifacts, oversaturated, deformed, people, faces, hands"
NEG_VID = ("static, still image, frozen, blurry, distorted, warping, morphing, flickering, "
           "low quality, jpeg artifacts, watermark, text, subtitles, sudden cuts")


def load_wf(name):
    return {k: v for k, v in json.load(open(f"{ROOT}/workflows/{name}")).items()
            if not k.startswith("_")}


def sh(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-3000:], file=sys.stderr)
        raise SystemExit(f"command failed: {a[0]}")
    return r.stdout


# ---------------------------------------------------------------- stage 1
def keyframes(film, outdir, ar, seed0):
    w, h = AR[ar]
    style = film.get("style", "")
    print(f"\n=== STAGE 1: {len(film['shots'])} keyframes @ {w}x{h} ===")
    t0 = time.time()
    for i, s in enumerate(film["shots"]):
        dst = f"{outdir}/keyframes/{s['id']}_00001_.png"
        if os.path.exists(dst):
            print(f"  = {s['id']} (present)")
            continue
        wf = load_wf("01_qwen_t2i_turbo.json")
        prompt = f"{s['prompt']}, {style}" if style else s["prompt"]
        set_path(wf, "10.inputs.text", prompt)
        set_path(wf, "11.inputs.text", NEG_IMG)
        set_path(wf, "12.inputs.width", w)
        set_path(wf, "12.inputs.height", h)
        set_path(wf, "13.inputs.seed", seed0 + i)
        set_path(wf, "15.inputs.filename_prefix", f"{outdir.split('output/')[1]}/keyframes/{s['id']}")
        print(f"  > {s['id']}")
        run(HOST, wf, quiet=True)
    print(f"=== keyframes done in {time.time()-t0:.0f}s ===")


# ---------------------------------------------------------------- stage 2
def clips(film, outdir, ar, res, fps, seconds, seed0):
    vw, vh = VID[res][ar]
    length = int(round(seconds * fps / 4)) * 4 + 1
    print(f"\n=== STAGE 2: {len(film['shots'])} clips @ {vw}x{vh} {length}f ({length/fps:.1f}s) ===")
    t0 = time.time()
    for i, s in enumerate(film["shots"]):
        dst = f"{outdir}/clips/{s['id']}_00001_.mp4"
        if os.path.exists(dst):
            print(f"  = {s['id']} (present)")
            continue
        # stage the keyframe into ComfyUI/input
        kf = f"{outdir}/keyframes/{s['id']}_00001_.png"
        if not os.path.exists(kf):
            raise SystemExit(f"missing keyframe {kf} - run stage 1 first")
        staged = f"film_{s['id']}.png"
        shutil.copy(kf, f"{COMFY}/input/{staged}")

        wf = load_wf("04_wan22_i2v_turbo.json")
        set_path(wf, "10.inputs.image", staged)
        set_path(wf, "11.inputs.text", s["motion"])
        set_path(wf, "12.inputs.text", NEG_VID)
        set_path(wf, "13.inputs.width", vw)
        set_path(wf, "13.inputs.height", vh)
        set_path(wf, "13.inputs.length", length)
        set_path(wf, "14.inputs.noise_seed", seed0 + i)
        set_path(wf, "18.inputs.filename_prefix", f"{outdir.split('output/')[1]}/clips/{s['id']}")
        print(f"  > {s['id']}  ({i+1}/{len(film['shots'])})")
        run(HOST, wf, quiet=True)
    print(f"=== clips done in {time.time()-t0:.0f}s ===")


# ---------------------------------------------------------------- stage 3
def title_card(text, sub, w, h, dur, path, fps):
    """Black card with centred text, rendered by ffmpeg (no GPU)."""
    fsz = max(28, w // 22)
    ssz = max(16, w // 55)
    esc = lambda t: t.replace("'", "").replace(":", "\\:")
    vf = (f"drawtext=text='{esc(text)}':fontcolor=white:fontsize={fsz}:"
          f"x=(w-text_w)/2:y=(h-text_h)/2-{h//30}:alpha='if(lt(t,0.8),t/0.8,if(lt(t,{dur-0.8}),1,({dur}-t)/0.8))'")
    if sub:
        vf += (f",drawtext=text='{esc(sub)}':fontcolor=0xAAAAAA:fontsize={ssz}:"
               f"x=(w-text_w)/2:y=(h+text_h)/2+{h//22}:"
               f"alpha='if(lt(t,0.8),t/0.8,if(lt(t,{dur-0.8}),1,({dur}-t)/0.8))'")
    sh("ffmpeg", "-y", "-v", "error", "-f", "lavfi",
       "-i", f"color=c=black:s={w}x{h}:d={dur}:r={fps}",
       "-vf", vf, "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", path)


def edit(film, outdir, res, ar, fps):
    vw, vh = VID[res][ar]
    trans = float(film.get("transition", 0.6))
    work = f"{outdir}/_work"
    os.makedirs(work, exist_ok=True)

    segs = []
    title = f"{work}/000_title.mp4"
    title_card(film["title"], film.get("subtitle", ""), vw, vh, 3.0, title, fps)
    segs.append(title)

    for s in film["shots"]:
        src = f"{outdir}/clips/{s['id']}_00001_.mp4"
        if not os.path.exists(src):
            print(f"  ! skipping missing clip {s['id']}", file=sys.stderr)
            continue
        dst = f"{work}/{s['id']}.mp4"
        # normalise: same codec/tbn/pix_fmt so xfade behaves
        sh("ffmpeg", "-y", "-v", "error", "-i", src,
           "-r", str(fps), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", dst)
        segs.append(dst)

    end = f"{work}/999_end.mp4"
    title_card("fin", "", vw, vh, 3.0, end, fps)
    segs.append(end)

    durs = []
    for p in segs:
        d = sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nw=1:nk=1", p).strip()
        durs.append(float(d))

    # build an xfade chain: each transition overlaps by `trans` seconds
    args = []
    for p in segs:
        args += ["-i", p]
    filt, prev, offset = [], "0:v", 0.0
    for i in range(1, len(segs)):
        offset += durs[i - 1] - trans
        out = f"x{i}"
        filt.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={trans}:offset={offset:.3f}[{out}]")
        prev = out
    total = sum(durs) - trans * (len(segs) - 1)
    # gentle fade from / to black on the whole piece
    filt.append(f"[{prev}]fade=t=in:st=0:d=1,fade=t=out:st={total-1.2:.3f}:d=1.2,format=yuv420p[v]")

    final = f"{outdir}/{film['title'].lower().replace(' ', '-')}_{res}p.mp4"
    print(f"\n=== STAGE 3: editing {len(segs)} segments -> {total:.1f}s ===")
    sh("ffmpeg", "-y", "-v", "error", *args,
       "-filter_complex", ";".join(filt), "-map", "[v]",
       "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p",
       "-movflags", "+faststart", final)
    print(f"\n>>> {final}  ({total:.1f}s, {vw}x{vh})")
    return final


def main():
    p = argparse.ArgumentParser()
    p.add_argument("film")
    p.add_argument("--res", default=None, choices=list(VID))
    p.add_argument("--stage", default="all", choices=["all", "keyframes", "clips", "edit"])
    p.add_argument("--seed", type=int, default=1000)
    a = p.parse_args()

    film = json.load(open(a.film))
    ar = film.get("ar", "16:9")
    res = a.res or film.get("res", "720")
    fps = int(film.get("fps", 16))
    seconds = float(film.get("seconds", 5))
    slug = film["title"].lower().replace(" ", "-")
    outdir = f"{COMFY}/output/claude-generated/11-short-film/{slug}"
    os.makedirs(f"{outdir}/keyframes", exist_ok=True)
    os.makedirs(f"{outdir}/clips", exist_ok=True)

    if a.stage in ("all", "keyframes"):
        keyframes(film, outdir, ar, a.seed)
    if a.stage in ("all", "clips"):
        clips(film, outdir, ar, res, fps, seconds, a.seed)
    if a.stage in ("all", "edit"):
        edit(film, outdir, res, ar, fps)


if __name__ == "__main__":
    main()
