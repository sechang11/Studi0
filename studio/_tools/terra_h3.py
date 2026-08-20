#!/usr/bin/env python3
"""studio/_tools/terra_h3.py - TERRA through MiniMax H3. Two unknowns at once.

Everything H3 has done here is photoreal: bags, water, powder, espresso, a man in a coat.
TERRA is an anime illustration off animagine with an IPAdapter reference sheet, and nothing
has asked H3 to animate a drawing. That is unknown one.

Unknown two is harder. Every successful shot so far has been an OBJECT acted upon - a bag
struck, a scoop tipped, a wave washing through. A somersault is a body rotating through its
own axis with weight and timing, which is the thing video models fail at most visibly. If
it works, character animation is open; if it tears, the finding is that H3 does props and
not people, and that is worth knowing before anything is built on it.

FOUR ACTIONS, written the way the library set was - a force with a direction, never toward
the camera:

    magic       light expands OUT of her hands, hair lifting        (radial, in-plane)
    cute        head tilts, hair swings across, hand comes up        (lateral)
    somersault  springs, rotates backwards, lands in a crouch        (rotation + gravity)
    wind        wind lifts her hair and skirt sideways               (lateral, cloth)

`wind` is the control. It is the easiest thing H3 could possibly be asked for on a figure,
so if the somersault fails and the wind works, the limit is body mechanics rather than
anime.

Her keyframes come from the anime path that already holds her - animagine plus her own
reference sheet plus her tags, which the identity test scored as the strongest combination
this project has. H3 only has to move what that gives it.
"""
import io
import os
import re
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
COMFY = os.path.expanduser("~/ComfyUI")
OUT = os.path.expanduser("~/shared/TERRA-H3")

TAGS = ("terra branford (final fantasy vi), 1girl, solo, long wavy green hair, very long "
        "hair, green eyes, red hair ribbon")
NEG = ("blurry, lowres, bad anatomy, bad hands, extra limbs, watermark, signature, text, "
       "multiple views, cropped")

SHOTS = [
    ("magic",
     "%s, standing, both hands raised in front of her chest, a sphere of pale green light "
     "gathering between her palms, wind lifting her hair, dark forest clearing at night, "
     "masterpiece, best quality, dynamic lighting" % TAGS,
     "the sphere of green light expands outward from her palms and her hair and clothes lift "
     "in the blast",
     "a rising magical hum, then a soft concussive whoomph and wind"),

    ("cute",
     "%s, standing, head tilted slightly, one hand half raised, smiling, sunlit meadow "
     "background, masterpiece, best quality" % TAGS,
     "she tilts her head further to one side and her long hair swings across her shoulder, "
     "then her raised hand opens in a small wave",
     "a light breeze, a soft cloth rustle, gentle birdsong"),

    ("somersault",
     "%s, crouched low with knees bent ready to spring, arms back, stone courtyard, "
     "masterpiece, best quality, dynamic pose" % TAGS,
     "she springs off the ground, rotates backwards through a full somersault and lands "
     "in a crouch",
     "a sharp push off stone, cloth snapping through the air, a landing thud"),

    ("wind",
     "%s, standing on a cliff edge, long hair and skirt streaming sideways, wide sky "
     "behind, masterpiece, best quality" % TAGS,
     "the wind gusts harder from the side and her hair and skirt stream out across the frame",
     "a strong steady wind, cloth snapping, distant sea"),
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
    os.makedirs(OUT, exist_ok=True)
    made = []
    for sid, prompt, action, sound in SHOTS:
        print("  %-11s %s" % (sid, action[:56]), flush=True)
        # her own path: animagine + her sheet through IPAdapter + her tags
        kf, err = run("22_anime_kf_ipadapter.json", [
            ("2.inputs.image", "sheet_anime_terra.png"),
            ("5.inputs.text", prompt), ("6.inputs.text", NEG),
            ("7.inputs.width", 768), ("7.inputs.height", 1344),
            ("8.inputs.seed", 11),
            ("10.inputs.width", 768), ("10.inputs.height", 1344),
            ("11.inputs.filename_prefix", "claude-generated/terrah3/%s" % sid)])
        if not kf:
            print("      keyframe FAILED %s" % err)
            continue
        staged = "terrah3_%s.png" % sid
        sh("cp", kf, os.path.join(COMFY, "input", staged))
        clip, err = run("60_minimax_h3_i2v.json", [
            ("8.inputs.image", staged),
            ("20.inputs.prompt", "%s. Anime animation. Sound: %s." % (action, sound)),
            ("20.inputs.length", 124), ("33.inputs.noise_seed", 11),
            ("51.inputs.filename_prefix", "claude-generated/terrah3/clip_%s" % sid)])
        if not clip:
            print("      clip FAILED %s" % err)
            continue
        dst = os.path.join(OUT, "%s.mp4" % sid)
        sh("cp", clip, dst)
        sh("cp", kf, os.path.join(OUT, "%s_key.png" % sid))
        made.append((sid, dst))
        print("      ok")

    if len(made) > 1:
        lst = "/tmp/_terra.txt"
        with io.open(lst, "w") as f:
            for sid, p in made:
                lab = "/tmp/_tl_%s.mp4" % sid
                sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
                   "scale=540:-2,drawtext=text='%s':fontcolor=white:fontsize=30:x=18:y=18:"
                   "borderw=3:bordercolor=black@0.8" % sid,
                   "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
                   "-c:a", "aac", "-b:a", "128k", lab)
                if os.path.exists(lab):
                    f.write("file '%s'\n" % lab)
        reel = os.path.join(OUT, "terra_reel.mp4")
        sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
           "-c", "copy", reel)
        print("\nreel: %s" % reel)
    print("%d/%d" % (len(made), len(SHOTS)))


if __name__ == "__main__":
    main()
