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
    # One hero shot per library item. Every action is a FORCE with a DIRECTION - the
    # thing that separated the torture shots that worked from the one that did not.
    "library": [
        ("atlas", "a worn olive canvas backpack on a rock at altitude, wide mountain light",
         "a hand grabs the top strap and swings the pack up out of frame, grit falling off it",
         "canvas creaking, buckles knocking, wind over rock"),
        ("lumen", "a minimal black desk lamp on an empty desk in a dark room, single warm pool of light",
         "the lamp arm is pulled down towards the desk and the pool of light slides across the wood",
         "a metal arm hinge creaking, a switch click"),
        ("northwind", "loose black tea leaves spilling from a paper packet beside a glass teapot on a kitchen counter",
         "hot water pours into the teapot and the leaves lift and swirl as the water darkens",
         "water pouring, a low boil, a spoon touching glass"),
        ("pace", "a single running shoe on wet tarmac at dawn, close, cold light",
         "a running shoe slams down into the puddle beside it and water sheets outward across the tarmac",
         "a hard footfall in water, spray, distant traffic"),
        ("slowsunday", "an unmade bed with morning light across the sheets, empty room, curtain at the window",
         "the curtain lifts on a draught and the band of sunlight slides across the sheets",
         "fabric moving, a room tone, birds outside"),
        ("tidewater", "a plain unlabelled glass bottle on a wet stone surface, soft grey light",
         "a wave washes across the stone and past the bottle, foaming and draining away",
         "a wave breaking and water draining over stone"),

        ("door", "an ordinary door at the end of a dim corridor, single light overhead",
         "the door swings open and light floods out across the corridor floor",
         "a latch, a door swinging, a low room tone"),
        ("garden", "a bare winter allotment with dark empty soil, grey morning light",
         "rain begins to fall and darkens the soil, drops striking and pooling",
         "rain starting, drops on soil, wind in a hedge"),
        ("library", "a vast dim library interior with towering shelves and shafts of light",
         "a book slides out from a shelf and dust lifts through the shaft of light",
         "a book sliding on wood, a deep quiet, a distant footstep"),
        ("lift", "an old civic building lobby with terrazzo floors and brass fittings, lift doors closed",
         "the brass lift doors slide apart and light spills out across the terrazzo",
         "a lift chime, doors rolling open, an echoing lobby"),
        ("signal", "an enormous radio dish against a grey moorland sky, wide shot",
         "the dish rotates slowly across the sky as the grass flattens in the wind",
         "a heavy motor turning, wind across an open moor"),
        ("lowtide", "a harbour at low tide with boats resting on wet mud, grey morning",
         "the tide floods back across the mud and the boats lift and swing on their moorings",
         "water moving over mud, ropes creaking, gulls"),

        ("caffeine", "a small white cup on a steel counter under a espresso machine spout",
         "dark espresso pours into the cup and the crema swirls and settles",
         "an espresso machine hissing, liquid filling a cup"),
        ("creatine", "a steel scoop heaped with fine white powder above a clean steel surface",
         "the scoop tips and the powder cascades down onto the steel in a soft heap",
         "a fine dry powder falling on metal"),
        ("fibre", "a rustic wholegrain loaf on a wooden board, knife beside it",
         "two hands tear the loaf apart and crumbs scatter across the board",
         "a crust tearing, crumbs falling on wood"),
        ("magnesium", "several small glass jars of white powder in a row on a pale surface",
         "a hand sweeps in and lifts one jar out of the row, the others rocking",
         "glass touching glass, a jar set down"),
        ("omega3", "a fillet of oily fish on crushed ice on a steel counter, close",
         "ice slides down around the fillet and meltwater runs off the steel edge",
         "ice shifting and water dripping onto metal"),
        ("protein", "eggs, chicken, lentils and yoghurt arranged on a wooden board",
         "an egg is cracked against the board and the yolk falls into a bowl",
         "a shell cracking, yolk dropping into a bowl"),
        ("sleep", "a dark bedroom with a single bedside lamp on, warm pool of light",
         "the lamp dims down to nothing and the room falls into darkness",
         "a switch turning, a room settling into silence"),
        ("vitamind", "low winter sun through a bare window onto a wooden floor, long shadows",
         "the band of sunlight slides across the floorboards and dust turns through it",
         "a quiet room, a faint creak of floorboards"),
        ("morningoat", "a white ceramic bowl of oats on a pale wooden counter, bright kitchen",
         "milk pours into the bowl and splashes up the side of the oats",
         "milk pouring, a spoon against ceramic"),
        ("paperlight", "a slim pale notebook lying closed on a seamless white surface",
         "the notebook falls open and the pages fan out and settle completely flat",
         "paper riffling and settling"),
        ("trailhead", "a running shoe pressing into a dirt trail, sunlit, dust in the air",
         "the shoe pushes off hard and dirt sprays backwards out of frame",
         "a foot pushing off gravel, dust, an outdoor ambience"),
    ],
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
