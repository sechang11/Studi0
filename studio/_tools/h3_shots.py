#!/usr/bin/env python3
"""studio/_tools/h3_shots.py - a shot list through MiniMax H3, keyframe and action together.

H3 can hold a subject through real physical action - a car rolling over a bag, spray on
contact, the thing crushed and springing back - which is what the rest of this library
cannot do. So the unit of work changes: not "a beat with a motion string" but a SHOT, with
a keyframe that sets the situation and an action that happens in it.

THE ONE RULE, learned three times the hard way today: THE PROMPT MUST DESCRIBE WHAT IS IN
THE KEYFRAME. Ask a backpack-on-a-rock keyframe for "fingers pulling a bootlace" and H3
will cheerfully build a different scene, which measures as motion 16.4 and reads as the
model ignoring the plate. It is not ignoring it; it is obeying you.

So a shot here is a PAIR, written together:

    setup   what the frame contains before anything happens
    action  what happens IN that frame, physically, with a beginning and an end
    sound   H3 generates native audio in the same pass, so the sound is part of the
            prompt rather than something laid under it afterwards

    python3 studio/_tools/h3_shots.py --list torture
    python3 studio/_tools/h3_shots.py --list torture --only mud,river
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
COMFY = os.path.expanduser("~/ComfyUI")
OUT = os.path.expanduser("~/shared/H3")

STYLE = ("cinematic film still, documentary realism, available light, weathered materials, "
         "shallow depth of field, sharp focus, high detail")

# The director's concept B: "a bag gets tossed... run over by a car... dragged in an army
# training camp... the worst conditions, and survives them all. then Atlas is revealed."
LISTS = {
    "torture": [
        ("toss", "a worn olive canvas backpack in mid-air above a concrete loading dock, "
                 "thrown, tumbling, industrial background, overcast",
         "the backpack tumbles through the air and slams onto the concrete, bouncing once "
         "and sliding to a stop",
         "a heavy thud on concrete and a scrape of canvas"),

        ("mud", "a worn olive canvas backpack half sunk in thick brown mud on a military "
                "obstacle course, rope attached, boots and barbed wire behind",
         "the rope pulls tight and drags the backpack through the mud towards the camera, "
         "mud sheeting off it",
         "wet sucking mud, a taut rope creaking, distant shouted orders"),

        ("river", "a worn olive canvas backpack floating in fast white water between rocks, "
                  "spray, mountain river",
         "the backpack is pulled under by the current, tumbles between the rocks and "
         "surfaces again downstream",
         "roaring whitewater and rocks knocking"),

        ("gravel", "a worn olive canvas backpack lying on a gravel track behind a parked "
                   "pickup truck, dust, dry heat",
         "the truck pulls away and drags the backpack over the gravel in a cloud of dust",
         "gravel spraying, an engine revving, canvas grinding on stone"),

        ("snow", "a worn olive canvas backpack half buried in deep snow, only the top flap "
                 "visible, blizzard, grey light",
         "snow blows across the drift and a gloved hand digs the backpack out and lifts it "
         "free",
         "howling wind and snow crunching underfoot"),

        ("sparks", "a worn olive canvas backpack on a steel workshop floor beneath a "
                   "welding bench, sparks falling, dark industrial interior",
         "a shower of welding sparks rains down onto the canvas and bounces off it, the "
         "fabric smoking faintly but not catching",
         "the crack and hiss of an arc welder, sparks pattering on fabric"),

        ("reveal", "a worn olive canvas backpack standing on a clean workbench in warm "
                   "light, scuffed and stained but completely intact, tools behind it",
         "the light rises across the worn canvas and the last of the dust settles off it",
         "a quiet workshop, one distant metallic tap"),
    ],
}


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
            (r.stderr or r.stdout or "")[-160:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", default="torture")
    ap.add_argument("--only", default="")
    ap.add_argument("--seconds", type=float, default=5.2)
    ap.add_argument("--seed", type=int, default=4200)
    a = ap.parse_args()
    shots = LISTS.get(a.list)
    if not shots:
        sys.exit("no list %r" % a.list)
    want = set(x for x in a.only.split(",") if x)
    os.makedirs(OUT, exist_ok=True)

    n = max(5, round(a.seconds * 24))
    length = n + (5 - (n % 17))          # H3 wants 17k+5
    print("%d shots, %d frames each (%.1fs)\n" % (len(shots), length, length / 24.0))

    made = []
    for sid, setup, action, sound in shots:
        if want and sid not in want:
            continue
        print("  %-8s %s" % (sid, setup[:58]), flush=True)
        kf, err = run("01_qwen_t2i_turbo.json", [
            ("10.inputs.text", "%s. %s" % (setup, STYLE)),
            ("12.inputs.width", 768), ("12.inputs.height", 1344),
            ("13.inputs.seed", a.seed),
            ("15.inputs.filename_prefix", "claude-generated/h3shots/%s" % sid)])
        if not kf:
            print("      keyframe FAILED %s" % err)
            continue
        staged = "h3shot_%s.png" % sid
        sh("cp", kf, os.path.join(COMFY, "input", staged))
        # the action and the sound go in together - H3 makes both in one pass
        clip, err = run("60_minimax_h3_i2v.json", [
            ("8.inputs.image", staged),
            ("20.inputs.prompt", "%s. Sound: %s." % (action, sound)),
            ("20.inputs.length", length),
            ("33.inputs.noise_seed", a.seed),
            ("51.inputs.filename_prefix", "claude-generated/h3shots/clip_%s" % sid)])
        if not clip:
            print("      clip FAILED %s" % err)
            continue
        dst = os.path.join(OUT, "%s.mp4" % sid)
        sh("cp", clip, dst)
        made.append((sid, dst))
        print("      ok")

    if len(made) > 1:
        lst = "/tmp/_h3reel.txt"
        with io.open(lst, "w") as f:
            for sid, p in made:
                lab = os.path.join("/tmp", "_h3lab_%s.mp4" % sid)
                sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
                   "scale=540:-2,drawtext=text='%s':fontcolor=white:fontsize=30:x=18:"
                   "y=18:borderw=3:bordercolor=black@0.8" % sid,
                   "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
                   "-c:a", "aac", "-b:a", "128k", lab)
                if os.path.exists(lab):
                    f.write("file '%s'\n" % lab)
        reel = os.path.join(OUT, "%s_reel.mp4" % a.list)
        sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
           "-c", "copy", reel)
        print("\nreel: %s" % reel)
    print("%d shots in %s" % (len(made), OUT))


if __name__ == "__main__":
    main()
