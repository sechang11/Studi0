#!/usr/bin/env python3
"""Generate a sample for every preset that renders today, so the app shows what each one IS.

    python3 studio/make_samples.py
    python3 studio/make_samples.py --only looks,cameras

Most of this needs no GPU. Camera moves and transitions are pure ffmpeg, and looks are
colour grades applied to one base image - so a handful of generations produces samples for
the whole ready library.

    shots        one keyframe each, showing the framing that shot type implies   [GPU]
    looks        one base image, each grade applied                              [ffmpeg]
    cameras      the base image with the move applied, as a short mp4            [ffmpeg]
    transitions  two base images, the transition between them, as an mp4         [ffmpeg]
    pacing       a strip showing shot lengths at that pace                       [ffmpeg]

Presets marked `partial` are deliberately skipped: a sample would imply the variable is
fully honoured when it is not. They are listed in studio/roadmap/FINISH-PARTIAL.md instead.
"""
import argparse, io, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
# Default to the LOCAL ComfyUI. This used to hardcode 192.168.1.46, which broke
# when DHCP moved the box to .45, and which also sent every render request across
# a NIC measured dropping 10% of packets. Nothing here needs the network: these
# scripts run ON the box. Set COMFY_HOST to drive a remote instance.
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

OUT = f"{HERE}/samples"
W, H = 768, 432
Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG = ("1girl, female, lowres, worst quality, bad anatomy, bad hands, watermark, text, "
       "multiple views, photorealistic, 3d, western comic, motion blur, blurry")

# framing that each shot template implies, so the sample teaches the vocabulary
SHOT_PROMPT = {
 "establish": "no humans, wide shot, vast night stadium interior, scenery, establishing shot",
 "master":    "2boys, full body, wide shot, two soccer players facing each other on a pitch",
 "speak":     "1boy, solo, medium close-up, talking, mouth open, looking at viewer",
 "react":     "1boy, solo, close-up, listening, silent, subtle expression, no dialogue",
 "pillow":    "no humans, empty stadium seat at night, still life, quiet, scenery",
 "insert":    "no humans, extreme close-up, a soccer ball on grass, macro, detail shot",
 "build":     "1boy, solo, running, dynamic angle, from below, tension, speed lines",
 "sakuga":    "1boy, solo, explosive action pose, motion lines, dramatic angle, impact",
 "hold_silent": "1boy, solo, standing completely still, wide shot, small in frame, silence",
}
BASE = ("1boy, solo, male focus, dark red hair, undercut, yellow eyes, black soccer jersey, "
        "standing, night stadium, floodlights, crowd, medium shot")
BASE_B = ("1boy, solo, male focus, long dark brown curly hair, ponytail, teal soccer jersey, "
          "running, night stadium, floodlights, crowd, medium shot")


def sh(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"failed: {' '.join(a[:3])}\n{(r.stderr or '')[-500:]}")


def load(group):
    d = f"{HERE}/{group}"
    return [json.load(open(f"{d}/{f}", encoding="utf-8"))
            for f in sorted(os.listdir(d)) if f.endswith(".json")]


def gen(prompt, dest, seed=4242):
    """One anime keyframe via ComfyUI."""
    from comfy import run, set_path
    from epic import ensure_local, COMFY, HOST
    if os.path.exists(dest):
        return dest
    tag = os.path.splitext(os.path.basename(dest))[0]
    wf = {"1": {"class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "animagine-xl-4.0.safetensors"}},
          "2": {"class_type": "EmptyLatentImage",
                "inputs": {"width": 1344, "height": 768, "batch_size": 1}},
          "3": {"class_type": "CLIPTextEncode",
                "inputs": {"clip": ["1", 1], "text": f"{prompt}, {Q}"}},
          "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": NEG}},
          "5": {"class_type": "KSampler",
                "inputs": {"model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0],
                           "latent_image": ["2", 0], "seed": seed, "steps": 28, "cfg": 5.0,
                           "sampler_name": "euler_ancestral", "scheduler": "normal",
                           "denoise": 1.0}},
          "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
          "7": {"class_type": "SaveImage",
                "inputs": {"images": ["6", 0],
                           "filename_prefix": f"claude-generated/studio_samples/{tag}"}}}
    print(f"    gen {tag}", flush=True)
    run(HOST, wf, quiet=True)
    tmp = f"{COMFY}/output/claude-generated/studio_samples/{tag}_00001_.png"
    ensure_local(f"claude-generated/studio_samples/{tag}_00001_.png", tmp, required=True)
    sh("ffmpeg", "-y", "-v", "error", "-i", tmp, "-vf", f"scale={W}:{H}", dest)
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    want = set(x.strip() for x in a.only.split(",") if x.strip())

    for g in ("shots", "looks", "cameras", "transitions", "pacing"):
        os.makedirs(f"{OUT}/{g}", exist_ok=True)

    base_a, base_b = f"{OUT}/_base_a.png", f"{OUT}/_base_b.png"
    if not (want and not ({"looks", "cameras", "transitions", "pacing"} & want)):
        gen(BASE, base_a)
        gen(BASE_B, base_b, seed=777)

    # ── shots: one keyframe each ──────────────────────────────────────────────
    if not want or "shots" in want:
        print("  shots")
        for p in load("shots"):
            if p.get("status") != "ready":
                continue
            gen(SHOT_PROMPT.get(p["id"], p["id"]), f"{OUT}/shots/{p['id']}.png")

    # ── looks: same image, each grade ─────────────────────────────────────────
    if not want or "looks" in want:
        print("  looks")
        for p in load("looks"):
            if p.get("status") != "ready":
                continue
            sh("ffmpeg", "-y", "-v", "error", "-i", base_a, "-vf", p["grade"],
               f"{OUT}/looks/{p['id']}.png")

    # ── cameras: the move, as a 2s mp4 ────────────────────────────────────────
    if not want or "cameras" in want:
        print("  cameras")
        from short import fx_chain
        for p in load("cameras"):
            if p.get("status") != "ready":
                continue
            chain = fx_chain([p["id"]], W, H, 24, length=2.0) or "null"
            sh("ffmpeg", "-y", "-v", "error", "-loop", "1", "-t", "2", "-i", base_a,
               "-vf", f"scale={W}:{H},{chain},format=yuv420p", "-r", "24",
               "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
               f"{OUT}/cameras/{p['id']}.mp4")

    # ── transitions: A -> B, as an mp4 ────────────────────────────────────────
    if not want or "transitions" in want:
        print("  transitions")
        for p in load("transitions"):
            if p.get("status") != "ready":
                continue
            dur = max(p.get("frames", 0), 1) / 24.0
            dst = f"{OUT}/transitions/{p['id']}.mp4"
            if not p.get("filter"):          # a hard cut has no filter
                sh("ffmpeg", "-y", "-v", "error",
                   "-loop", "1", "-t", "1", "-i", base_a,
                   "-loop", "1", "-t", "1", "-i", base_b,
                   "-filter_complex",
                   f"[0]scale={W}:{H},format=yuv420p[a];[1]scale={W}:{H},format=yuv420p[b];"
                   f"[a][b]concat=n=2:v=1:a=0",
                   "-r", "24", "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", dst)
            else:
                f = p["filter"].format(d=f"{dur:.2f}")
                sh("ffmpeg", "-y", "-v", "error",
                   "-loop", "1", "-t", "1.6", "-i", base_a,
                   "-loop", "1", "-t", "1.6", "-i", base_b,
                   "-filter_complex",
                   f"[0]scale={W}:{H},format=yuv420p[a];[1]scale={W}:{H},format=yuv420p[b];"
                   f"[a][b]{f}:offset=0.9",
                   "-r", "24", "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", dst)

    # ── pacing: a strip of cuts at that rate ──────────────────────────────────
    if not want or "pacing" in want:
        print("  pacing")
        for p in load("pacing"):
            if p.get("status") != "ready":
                continue
            unit = 0.55 * float(p.get("scale", 1.0))
            parts = []
            for i in range(6):
                src = base_a if i % 2 == 0 else base_b
                t = unit * (1.0 if p.get("rhythm") == "steady"
                            else (1.0 - i * 0.12 if p["rhythm"] == "accelerating"
                                  else 1.0 + i * 0.12))
                q = f"{OUT}/pacing/_p{i}.mp4"
                sh("ffmpeg", "-y", "-v", "error", "-loop", "1", "-t", f"{max(t,0.12):.2f}",
                   "-i", src, "-vf", f"scale={W}:{H},format=yuv420p", "-r", "24",
                   "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", q)
                parts.append(q)
            lst = f"{OUT}/pacing/_list.txt"
            io.open(lst, "w").write("".join(
                f"file '{os.path.abspath(x)}'\n" for x in parts).replace("\\", "/"))
            sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
               "-c", "copy", f"{OUT}/pacing/{p['id']}.mp4")
            for x in parts:
                os.remove(x)
            os.remove(lst)

    n = sum(len(os.listdir(f"{OUT}/{g}")) for g in
            ("shots", "looks", "cameras", "transitions", "pacing")
            if os.path.isdir(f"{OUT}/{g}"))
    print(f"\n{n} samples in {OUT}")


if __name__ == "__main__":
    main()
