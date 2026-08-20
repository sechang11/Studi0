#!/usr/bin/env python3
"""THE COLLECTOR - a death-god who takes bags at the end of their life.

    "there's a scene in deathnote anime where the shinigami can see the remaining lifespan
     of humans left. can we somehow use that for bags?... he even goes to claim the life
     of a bag, where an 'accident' happens to human eyes but he retrieves the soul of the
     bag. how this would transition to lifetime bag i don't know"

THE TRANSITION IS THE WHOLE AD, and it falls out of the premise once the character has a
job. He does not sell bags. He COLLECTS them - he is the one who profits when a bag dies,
which makes him planned obsolescence with a face. So the payoff is the bag he can never
have: he reaches for the ATLAS, cannot take it, and sits down on the kerb to wait. The
last line writes itself.

    ATLAS. Some things you don't get to collect.

ON THE SOURCE. The grammar is borrowed - a figure only one person can see, numbers hanging
over things, an ordinary street with a supernatural observer standing in it - and the
character is not. THE COLLECTOR is a tall gaunt figure in a long charcoal coat, ash-grey,
hollow-eyed, with a leather satchel of taken things. That is a death-figure out of folklore
rather than anyone's design, and this project already has the rule from the Dragon Ball
work: take the shot grammar, never the frames.

HOW HE STAYS THE SAME PERSON across nine shots: an identical, heavily specified character
clause in every keyframe prompt at a fixed seed. This project measured that route - naming
a character in words holds better than a reference image alone, because "IPAdapter
reinforces an identity the prompt is already asking for; it does not supply one". ref2va is
downloading in case words are not enough.

EVERY ACTION IS A FORCE WITH A DIRECTION, per the library set: something acts on something,
laterally or with gravity. Never toward the camera - that is the axis a still cannot imply
and it is why `mud` failed.
"""
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
COMFY = os.path.expanduser("~/ComfyUI")
OUT = os.path.expanduser("~/shared/COLLECTOR")

# One clause, byte-identical in every prompt that contains him.
HIM = ("a tall gaunt pale figure in a long charcoal coat, ash-grey skin, hollow dark-ringed "
       "eyes, lank black hair, unnaturally long fingers, expressionless, a worn leather "
       "satchel at his hip")
LOOK = ("cinematic film still, anamorphic, teal and amber grade, rain-wet city, shallow "
        "depth of field, sharp focus, high detail")

SHOTS = [
    ("01_street",
     "%s stands motionless in the middle of a crowded rush-hour pavement while commuters "
     "stream past on both sides, none of them looking at him, wet city street, dusk. %s"
     % (HIM, LOOK),
     "the crowd streams past him on both sides and his head turns slowly to follow a bag",
     "a busy street, footsteps and traffic, one low sustained tone underneath", None),

    ("02_numbers",
     "over-the-shoulder past %s towards a crowd of commuters seen from behind, each "
     "carrying a different bag, wet city street, dusk. %s" % (HIM, LOOK),
     "the commuters walk away from camera down the street and their bags sway with the walk",
     "a crowd walking, muffled city noise", None),

    ("03_fray",
     "extreme close up of a frayed nylon backpack strap under load, threads splitting one "
     "by one, city crowd blurred behind, dusk. %s" % LOOK,
     "the strap fibres split one after another and the last threads pull apart",
     "fabric tearing thread by thread, a low tick like a clock", "19"),

    ("04_snap",
     "a black nylon backpack falling onto a wet pavement, contents spilling sideways across "
     "the paving, commuter legs around it, dusk. %s" % LOOK,
     "the backpack hits the pavement and its contents skid sideways across the wet stone",
     "a thud, objects scattering on wet stone, a gasp from the crowd", None),

    ("05_claim",
     "%s crouched over a broken black backpack lying on wet pavement, one long hand "
     "reaching into it, a small warm ember of light between his fingers, commuters walking "
     "past unaware. %s" % (HIM, LOOK),
     "he draws the ember of light up out of the broken bag and it brightens in his fingers",
     "a soft rising chime, the crowd noise dropping away", None),

    ("06_pocket",
     "%s standing upright on a wet pavement, dropping a small glowing ember into the "
     "leather satchel at his hip, crowd blurred around him, dusk. %s" % (HIM, LOOK),
     "he drops the ember into the satchel and the light snuffs out as the flap falls shut",
     "a leather flap closing, the chime cutting off, street noise returning", None),

    ("07_sees",
     "%s turned sharply to look at a worn olive canvas backpack on a stranger's shoulder in "
     "the crowd, the pack sun-faded and patched and intact, dusk. %s" % (HIM, LOOK),
     "he turns his head sharply towards the worn canvas pack as its wearer walks across frame",
     "the street noise dropping to almost nothing, one low note", None),

    ("08_reach",
     "close on the long pale hand of %s reaching towards a worn olive canvas backpack, the "
     "hand stopping short, wet city light. %s" % (HIM, LOOK),
     "the hand reaches towards the canvas and stops, the fingers closing on nothing",
     "silence, then a single failed chime", "∞"),

    ("09_wait",
     "%s sitting alone on a wet kerb with his satchel beside him, watching a figure with a "
     "worn olive canvas backpack walk away down the street, dusk, rain starting. %s"
     % (HIM, LOOK),
     "the figure with the canvas pack walks away down the street and rain begins to fall on "
     "the seated collector",
     "rain starting on stone, footsteps receding, a long low tone", None),
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
            (r.stderr or r.stdout or "")[-160:])


def main():
    os.makedirs(OUT, exist_ok=True)
    made = []
    for sid, setup, action, sound, card in SHOTS:
        print("  %-11s %s" % (sid, setup[:54]), flush=True)
        kf, err = run("01_qwen_t2i_turbo.json", [
            ("10.inputs.text", setup),
            ("12.inputs.width", 768), ("12.inputs.height", 1344),
            ("13.inputs.seed", 7),            # fixed, so he is the same person throughout
            ("15.inputs.filename_prefix", "claude-generated/collector/%s" % sid)])
        if not kf:
            print("      keyframe FAILED %s" % err)
            continue
        staged = "coll_%s.png" % sid
        sh("cp", kf, os.path.join(COMFY, "input", staged))
        clip, err = run("60_minimax_h3_i2v.json", [
            ("8.inputs.image", staged),
            ("20.inputs.prompt", "%s. Sound: %s." % (action, sound)),
            ("20.inputs.length", 124), ("33.inputs.noise_seed", 7),
            ("51.inputs.filename_prefix", "claude-generated/collector/clip_%s" % sid)])
        if not clip:
            print("      clip FAILED %s" % err)
            continue
        dst = os.path.join(OUT, "%s.mp4" % sid)
        # the number card, burnt in over the shot it belongs to
        if card:
            tmp = dst + ".card.mp4"
            sh("ffmpeg", "-y", "-v", "error", "-i", clip, "-vf",
               "drawtext=fontfile='/usr/share/fonts/liberation-sans-fonts/"
               "LiberationSans-Bold.ttf':text='%s':fontcolor=white:fontsize=190:"
               "x=(w-text_w)/2:y=(h-text_h)/2:borderw=6:bordercolor=black@0.85" % card,
               "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
               "-c:a", "copy", tmp)
            sh("mv", tmp, dst)
        else:
            sh("cp", clip, dst)
        made.append((sid, dst))
        print("      ok")

    if len(made) > 1:
        lst = "/tmp/_coll.txt"
        with io.open(lst, "w") as f:
            for sid, p in made:
                lab = "/tmp/_cl_%s.mp4" % sid
                sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf", "scale=540:-2",
                   "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
                   "-c:a", "aac", "-b:a", "128k", lab)
                if os.path.exists(lab):
                    f.write("file '%s'\n" % lab)
        reel = os.path.join(OUT, "collector.mp4")
        sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
           "-c", "copy", reel)
        print("\nreel: %s" % reel)
    print("%d/%d shots" % (len(made), len(SHOTS)))


if __name__ == "__main__":
    main()
