#!/usr/bin/env python3
"""Show the CLAIM, not the category.

    "why do i want to see 2 second clips of a man and a dirty shoe? what's the selling
     point? what's supposed to grab my attention?"

Right, and my hook study asked the wrong question. I tested SHOT TYPES - product, hands,
figure, macro, toward, face - as if attention were a framing problem. It is not. A dirty
shoe is the category. Nobody stops for a category.

WHAT MAKES THIS WORSE: the claims already exist. The copy in these films argues:

    "Most notebooks do not close flat."
    "Most desk lamps have one setting: on."
    "The first mile is easy. Anyone can sell you the first mile."
    "The shelf is full of bottles with twenty ingredients."

Every one of those is a proposition with a villain in it. And the pictures show: a
notebook on a table, a lamp on a desk, a runner running, a bottle. The words do the
arguing and the images depict the product sitting still. The film never SHOWS what it is
claiming.

SO THIS IS A CONTROLLED PAIR, twice over. Same product, same style, same grade, same seed.
The only difference is whether the image depicts the SUBJECT or dramatises the CLAIM:

    paperlight   claim: "most notebooks do not close flat"
      subject    a notebook on a table                       <- what we ship
      claim      a stack of notebooks springing open, one lying perfectly flat beside them

    lumen        claim: "most desk lamps have one setting: on"
      subject    a desk lamp on a desk                       <- what we ship
      claim      a harsh white lamp glaring over a desk, everything else in hard shadow

A claim shot has a villain and a resolution in the frame. That is what there is to look
at: not a thing, but an argument you can see.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
COMFY = os.path.expanduser("~/ComfyUI")
OUT = os.path.expanduser("~/shared/CLAIMS")
GRADE = ("curves=all='0/0.02 0.22/0.28 0.5/0.60 0.78/0.88 1/0.995',"
         "vibrance=intensity=0.60,eq=saturation=1.12")

PAIRS = [
    ("paperlight_subject", "clean product photography, seamless white background",
     "a closed notebook lying on a white table, nothing else in frame",
     "the light shifts slowly across the cover"),
    ("paperlight_claim", "clean product photography, seamless white background",
     "three thick notebooks with their covers springing open and pages fanning upward, "
     "and beside them one slim notebook lying perfectly flat and open",
     "the stacked notebooks spring open and their pages fan up, the flat one stays open"),
    ("lumen_subject", "clean modern product photography, soft diffused daylight",
     "a black desk lamp switched on above a wooden desk with a notebook",
     "the light shifts slowly across the desk"),
    ("lumen_claim", "clean modern product photography",
     "a bare white desk lamp glaring straight down, the desk beneath it blown out white "
     "and everything past its circle in hard black shadow",
     "the glare flares brighter and the shadows around it deepen"),
]


def sh(*a, **kw):
    return subprocess.run(a, capture_output=True, text=True, **kw)


def run(wf, sets):
    cmd = [sys.executable, os.path.join(ROOT, "scripts", "comfy.py"), "run",
           os.path.join(ROOT, "workflows", wf)]
    for k, v in sets:
        cmd += ["-s", "%s=%s" % (k, v)]
    r = sh(*cmd, cwd=ROOT)
    m = re.search(r"-> (\S+\.(?:png|mp4))", r.stdout or "")
    return os.path.join(COMFY, "output", m.group(1)) if m else None


def main():
    os.makedirs(OUT, exist_ok=True)
    made = []
    for sid, style, subject, motion in PAIRS:
        print("  %-20s %s" % (sid, subject[:56]), flush=True)
        kf = run("01_qwen_t2i_turbo.json", [
            ("10.inputs.text", "%s. %s, sharp focus, high detail" % (subject, style)),
            ("12.inputs.width", 928), ("12.inputs.height", 1664),
            ("13.inputs.seed", 4200),
            ("15.inputs.filename_prefix", "claude-generated/claims/%s" % sid)])
        if not kf:
            print("      keyframe FAILED")
            continue
        staged = "claim_%s.png" % sid
        sh("cp", kf, os.path.join(COMFY, "input", staged))
        clip = run("12_ltx23_i2v_audio.json", [
            ("8.inputs.image", staged), ("10.inputs.text", motion),
            ("20.inputs.width", 704), ("20.inputs.height", 1280),
            ("20.inputs.length", 97), ("21.inputs.frames_number", 97),
            ("32.inputs.noise_seed", 4200),
            ("43.inputs.filename_prefix", "claude-generated/claims/clip_%s" % sid)])
        if not clip:
            print("      clip FAILED")
            continue
        cut = os.path.join(OUT, "%s.mp4" % sid)
        sh("ffmpeg", "-y", "-v", "error", "-t", "2.2", "-i", clip, "-vf", GRADE,
           "-an", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
           "-pix_fmt", "yuv420p", cut)
        made.append((sid, cut))

    # posters side by side, subject above claim, so the difference is one glance
    tiles = []
    for sid, cut in made:
        t = "/tmp/_cl_%s.png" % sid
        lab = sid.replace("_", " ")
        sh("ffmpeg", "-y", "-v", "error", "-i", cut, "-frames:v", "1", "-update", "1",
           "-vf", "scale=300:-2,pad=iw:ih+30:0:30:color=black,"
                  "drawtext=text='%s':fontcolor=white:fontsize=20:x=6:y=4" % lab, t)
        if os.path.exists(t):
            tiles.append(t)
    if len(tiles) >= 4:
        sh(*(["ffmpeg", "-y", "-v", "error"] + sum([["-i", t] for t in tiles[:2]], [])
             + ["-filter_complex", "hstack=2", "-frames:v", "1", "-update", "1",
                "/tmp/_cr1.png"]))
        sh(*(["ffmpeg", "-y", "-v", "error"] + sum([["-i", t] for t in tiles[2:4]], [])
             + ["-filter_complex", "hstack=2", "-frames:v", "1", "-update", "1",
                "/tmp/_cr2.png"]))
        sheet = os.path.join(OUT, "claim_vs_subject.png")
        sh("ffmpeg", "-y", "-v", "error", "-i", "/tmp/_cr1.png", "-i", "/tmp/_cr2.png",
           "-filter_complex", "vstack", "-frames:v", "1", "-update", "1", sheet)
        print("\nsheet: %s" % sheet)
    print("%d clips in %s" % (len(made), OUT))


if __name__ == "__main__":
    main()
