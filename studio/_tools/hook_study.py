#!/usr/bin/env python3
"""studio/_tools/hook_study.py - six ways to open the same advert, for a director to pick from.

The opening is where attention is won or lost - a feed gives one poster frame and about
half a second of motion - and every film in this slate opens the same way: the product,
alone, on a surface, holding still. Nobody chose that; it is what "01_open" has always
meant.

So: ONE product, SIX openings, two seconds each, everything else identical. Same style,
same grade, same seed, no audio, no captions. The only variable is what the shot IS.

    product      the thing alone on a surface           <- the control, what we do now
    hands        a person's hands using it, close
    figure       a person at distance in a landscape    <- named "the best one yet"
    macro        the texture, filling the frame
    toward       someone moving at the camera
    face         a face, looking

Each carries a motion string written the way the sweep says to write them - a subject, a
physical thing it does, and where it ends - because "gentle natural motion" measured 2.17
against 5.79 for a named action, and adjectives measured 0.84.

WHAT THE ANSWER IS FOR. Whichever one stops a thumb becomes a direction, and the opening
of every future commercial is built from it rather than from whatever "01_open" happened
to mean. This is the cheapest possible way to find that out: six two-second clips against
one guess repeated twenty-three times.

    python3 studio/_tools/hook_study.py --product "trail running shoes"
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
COMFY = os.path.expanduser("~/ComfyUI")
OUT = os.path.expanduser("~/shared/HOOKS")

STYLE = ("natural light outdoor photography, late afternoon sun, clear air, "
         "rich colour, sharp focus, high detail")

# (id, what the keyframe is, what physically happens)
SHOTS = [
    ("product", "a pair of worn trail running shoes on a flat rock, nothing else in frame",
     "the light moves across the shoes and a breeze stirs the laces"),
    ("hands", "close on two hands pulling a trail shoe's laces tight, grass behind",
     "the fingers pull the lace tight, tie it, and let go"),
    ("figure", "a lone runner far away on a green ridge under a wide sky",
     "the runner crests the ridge and drops out of sight"),
    ("macro", "extreme close up of a muddy trail shoe tread, filling the frame",
     "the tread turns slowly and dried mud crumbles off it"),
    ("toward", "a runner coming straight at the camera down a narrow trail",
     "the runner strides toward the camera and past it, out of frame"),
    ("face", "a runner's face at the top of a climb, breathing hard, sky behind",
     "the head lifts, the eyes open and look out over the valley"),
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
    return (os.path.join(COMFY, "output", m.group(1)) if m else None,
            (r.stderr or r.stdout or "")[-200:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", default="trail running shoes")
    ap.add_argument("--seed", type=int, default=4200)
    ap.add_argument("--secs", type=float, default=2.0)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    made = []
    for sid, subject, motion in SHOTS:
        print("  %-9s %s" % (sid, subject[:60]), flush=True)
        kf, err = run("01_qwen_t2i_turbo.json", [
            ("10.inputs.text", "%s. %s" % (subject, STYLE)),
            ("12.inputs.width", 928), ("12.inputs.height", 1664),
            ("13.inputs.seed", a.seed),
            ("15.inputs.filename_prefix", "claude-generated/hookstudy/%s" % sid)])
        if not kf:
            print("      keyframe FAILED %s" % err)
            continue
        staged = "hookstudy_%s.png" % sid
        sh("cp", kf, os.path.join(COMFY, "input", staged))
        clip, err = run("12_ltx23_i2v_audio.json", [
            ("8.inputs.image", staged), ("10.inputs.text", motion),
            ("20.inputs.width", 704), ("20.inputs.height", 1280),
            ("20.inputs.length", 97), ("21.inputs.frames_number", 97),
            ("32.inputs.noise_seed", a.seed),
            ("43.inputs.filename_prefix", "claude-generated/hookstudy/clip_%s" % sid)])
        if not clip:
            print("      clip FAILED %s" % err)
            continue
        # the first `secs` only - this is about the opening, graded the way films are
        cut = os.path.join(OUT, "%s.mp4" % sid)
        sh("ffmpeg", "-y", "-v", "error", "-t", "%.2f" % a.secs, "-i", clip,
           "-vf", "curves=all='0/0.02 0.22/0.28 0.5/0.60 0.78/0.88 1/0.995',"
                  "vibrance=intensity=0.60,eq=saturation=1.12",
           "-an", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
           "-pix_fmt", "yuv420p", cut)
        made.append((sid, cut))

    if not made:
        sys.exit("nothing rendered")

    # one file, labelled, so it can be watched once and answered in one line
    parts = []
    for sid, cut in made:
        lab = os.path.join(OUT, "_lab_%s.mp4" % sid)
        sh("ffmpeg", "-y", "-v", "error", "-i", cut, "-vf",
           "scale=540:-2,drawtext=text='%s':fontcolor=white:fontsize=34:x=18:y=18:"
           "borderw=3:bordercolor=black@0.8" % sid,
           "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", lab)
        if os.path.exists(lab):
            parts.append(lab)
    reel = os.path.join(OUT, "hook_study.mp4")
    lst = "/tmp/_hooklist.txt"
    with open(lst, "w") as f:
        for p in parts:
            f.write("file '%s'\n" % p)
    sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
       "-c", "copy", reel)

    # and a still contact sheet, for judging the POSTER frame - which is what a feed
    # actually shows before anything moves
    tiles = []
    for sid, cut in made:
        t = "/tmp/_ht_%s.png" % sid
        sh("ffmpeg", "-y", "-v", "error", "-i", cut, "-frames:v", "1", "-update", "1",
           "-vf", "scale=260:-2,pad=iw:ih+30:0:30:color=black,"
                  "drawtext=text='%s':fontcolor=white:fontsize=20:x=6:y=4" % sid, t)
        if os.path.exists(t):
            tiles.append(t)
    if tiles:
        sheet = os.path.join(OUT, "hook_posters.png")
        sh(*(["ffmpeg", "-y", "-v", "error"] + sum([["-i", t] for t in tiles], [])
             + ["-filter_complex", "hstack=%d" % len(tiles), "-frames:v", "1",
                "-update", "1", sheet]))
        print("\nposter frames: %s" % sheet)
    print("reel (%d openings, %.1fs each): %s" % (len(parts), a.secs, reel))


if __name__ == "__main__":
    main()
