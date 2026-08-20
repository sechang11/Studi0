#!/usr/bin/env python3
"""studio/_tools/duo_h3.py - LIWEN and MERIBEL through H3, photoreal.

    "let's do the same with a real life character. bai liwen and meribel cruz. use minimax
     to make them perform feats of athleticism, like a fist fight or sword fight, them
     acting cute, and sword magic"

WHY THIS DOES NOT REUSE THE TERRA PATH. TERRA's keyframes come from animagine plus her
reference sheet through IPAdapter. LIWEN has a trained LoRA but it is an ANIME LoRA, and
MERIBEL has no sheet at all - her package_check still reads `sheet 0/1`. Neither identity
route survives the crossing to photoreal, so both are rebuilt here on the Qwen side:

    one casting portrait each, fixed seed          -> ~/ComfyUI/input/cast_*.png
    every shot keyframe is an EDIT of that portrait via 14_qwen_edit_ref

That workflow takes TWO references, which is what makes a two-hander possible at all -
both faces go in and the scene comes out with both of them in it. It is also the measured
identity route for this project: a reference reinforces an identity the prompt is already
asking for, so the appearance clause is repeated verbatim in every prompt as well.

THE ONE DESIGN RULE THAT SHAPED EVERY FIGHT BEAT BELOW. The last batch established:

    H3 HOLDS A WHOLE BODY TRAVELLING AND DUPLICATES A FAST LIMB SWUNG AGAINST A STATIC
    TORSO.

`duel_claw` (a parry from a standing guard) and `staff_flourish` (a figure-of-eight spun
across the body) both rendered two arms and two blades. `gym_routine` and `dance`, where
the whole body went with the motion, held cleanly for 8.7 seconds.

So there is not a single swing in this file that is performed from a planted stance. Every
strike is a body committing through it - driving off the back foot, stepping through the
bind, turning under the arm, springing off the rock. The sword form is written as a
travelling routine for the same reason, which is the shape that already worked.

The older rules still apply: one big committed event, never a gentle continuous one;
motion lateral or with gravity, never toward camera; rotation stays in the frame's plane;
and cute needs a CLOSE frame, because a wink at full length is forty pixels of eye.

PROVENANCE. Both characters are `invented` on their cards and no real person is
referenced, used as a likeness source, or named in any prompt here.
"""
import argparse
import io
import os
import re
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
COMFY = os.path.expanduser("~/ComfyUI")
OUT = os.path.expanduser("~/shared/DUO-H3")

# Repeated verbatim in every prompt that contains her, alongside her reference image.
L = ("a young east asian woman with long straight black hair held with a carved jade "
     "hairpin, warm brown eyes, pale skin, in a white and jade-green layered silk robe "
     "with wide sleeves and a broad sash")
M = ("a young latina woman with short black hair shaved into an undercut, sharp dark eyes, "
     "a small matte black cybernetic implant along her left ear, in a cropped weatherproof "
     "jacket over harness straps and fingerless gloves")

LOOK = ("photoreal cinematic film still, 35mm, natural light, shallow depth of field, "
        "sharp focus, high detail, colour photograph, filmic grade")
NEG = ("blurry, low quality, watermark, text, signature, anime, illustration, painting, "
       "cgi, 3d render, plastic skin, deformed, extra limbs, extra fingers, nudity, nsfw, exposed chest, open jacket, cleavage, undressed")

LONG = 209      # 8.7s - the measured ceiling before the kernel OOMs at 43 GB
SHORT = 124     # 5.2s

WIDE = (1216, 832)      # fights and feats: lateral travel needs the width
TALL = (896, 1216)      # portraits

# (id, refs, size, keyframe, action, sound, length)
LISTS = {
    # BOTH OF THEM. Two references in, two people out. Not one swing from a planted stance.
    "duel": [
        ("fists_charge", ("liwen", "meribel"), WIDE,
         "%s stands braced side-on in a wide courtyard of wet flagstones at dawn, facing "
         "%s who is low in a sprinter's crouch several paces away, mist, side view. %s"
         % (L, M, LOOK),
         "the woman in the jacket drives forward off her back foot and slams her shoulder "
         "into the woman in the robe, and both of them are carried sideways across the "
         "frame by the impact",
         "fast footfalls on wet stone, a heavy body impact, a hard exhale", SHORT),

        ("sword_bind", ("liwen", "meribel"), WIDE,
         "%s and %s side-on in a ruined stone hall, their straight swords crossed and "
         "locked hilt to hilt between them, sparks, shafts of dusty light. %s"
         % (L, M, LOOK),
         "they shove against the locked blades, break the bind and both step through past "
         "each other to the opposite sides of the frame, blades scraping apart",
         "steel grinding on steel, boots scuffing stone, two sharp breaths", SHORT),

        ("hip_throw", ("liwen", "meribel"), WIDE,
         "%s bent forward low at the waist with her knees bent, and %s lying face up "
         "across her lower back and hip, lifted completely off the ground, both feet in "
         "the air, a training yard of packed earth, side view, dust. %s" % (L, M, LOOK),
         "the lifted woman is thrown on over and down off her back and slams flat into "
         "the dirt, and the woman in the robe straightens up",
         "cloth snapping, a body arcing through air, a heavy flat impact and dust", SHORT),

        ("sword_light", ("liwen", "meribel"), WIDE,
         "%s low to the ground with her front knee deeply bent and her back leg straight "
         "and stretched out far behind her, her torso leaning forward over the front "
         "knee, her straight sword held back at arm's length behind her with pale white "
         "light running along the blade, and %s far away at the other side of the frame "
         "braced with both arms raised, a misty mountain terrace, side view. %s"
         % (L, M, LOOK),
         "she drives forward out of the lunge and sweeps the glowing blade up across the "
         "frame, and a crescent of white light travels off it and hurls the other woman "
         "backwards out of frame",
         "a rising hum along steel, a sharp release, a rush of air and a heavy landing",
         SHORT),
    ],

    # SOLO ATHLETICS. Every one of these is the whole body travelling.
    "feats": [
        ("rooftop_leap", ("meribel", "meribel"), WIDE,
         "%s sprinting side-on across a flat city rooftop towards its edge, a gap and a "
         "second rooftop beyond, low sun, side view. %s" % (M, LOOK),
         "she runs to the edge and launches out across the gap, sails over it and lands "
         "rolling on the far roof",
         "hard running footfalls on gravel, a push off concrete, wind, a rolling landing",
         SHORT),

        ("wall_run", ("meribel", "meribel"), WIDE,
         "%s running side-on at a high brick wall in a narrow alley, one arm reaching, wet "
         "ground, neon reflections, side view. %s" % (M, LOOK),
         "she runs up the face of the wall for three strides, pushes off sideways and drops "
         "down to land in a crouch on the alley floor",
         "boots striking brick, a scrape, a landing thud, dripping water", SHORT),

        ("sword_form", ("liwen", "liwen"), WIDE,
         "%s standing at the near corner of a wide empty flagstone terrace at dawn, her "
         "straight sword held low in one hand, mountains behind, mist, side view. %s"
         % (L, LOOK),
         "she steps forward into a sweeping cut, turns full around through a second cut, "
         "advances across the terrace in a low lunge, rises and finishes with the blade "
         "drawn back and still",
         "cloth and sleeves snapping, a blade cutting air in long arcs, measured footfalls "
         "on stone, wind", LONG),

        ("river_vault", ("liwen", "liwen"), WIDE,
         "%s running side-on along flat river stones towards a large boulder, water either "
         "side, spray, morning light, side view. %s" % (L, LOOK),
         "she plants one hand on the boulder, vaults over it turning sideways in the air "
         "and lands running on the stones beyond, throwing up spray",
         "running on wet stone, a hand slap on rock, water spraying, a landing", SHORT),
    ],

    # CLOSE. Both of them are written as people who are bad at being soft, which is the
    # only version of cute either card supports.
    "charm": [
        ("liwen_smile", ("liwen", "liwen"), TALL,
         "close upper body portrait of %s, looking away off to one side, lips pressed "
         "together, warm afternoon light, soft green background. %s" % (L, LOOK),
         "she glances back towards the camera, tries to keep a straight face and loses it, "
         "breaking into a small embarrassed smile and looking down",
         "a quiet courtyard, a soft breath of laughter, birds", SHORT),

        ("liwen_hairpin", ("liwen", "liwen"), TALL,
         "close upper body portrait of %s with one hand raised to the jade hairpin at the "
         "back of her head, lamplight, dark warm background. %s" % (L, LOOK),
         "she draws the hairpin out and her long black hair falls down across her shoulder, "
         "then she looks up at the camera",
         "a soft slide of wood through hair, cloth settling, a quiet room", SHORT),

        ("meribel_wink", ("meribel", "meribel"), TALL,
         "close upper body portrait of %s facing the camera with one eyebrow slightly "
         "raised, neon signage out of focus behind her, night. %s" % (M, LOOK),
         "one corner of her mouth pulls into a smirk and she closes one eye in a slow "
         "deliberate wink, then tips her chin up",
         "distant street traffic, a low neon hum", SHORT),

        ("meribel_laugh", ("meribel", "meribel"), TALL,
         "tight head and shoulders portrait of %s, cropped at the collarbone, arms "
         "folded, a flat unimpressed expression, wearing a high-necked weatherproof "
         "jacket zipped fully closed to the throat over a crew-neck shirt, warm "
         "interior, blurred background. %s" % (M, LOOK),
         "she holds the flat expression, then cracks, throwing her head back into a real "
         "laugh and putting one hand over her eyes, her jacket staying closed",
         "a room tone, a snort and a genuine laugh", SHORT),
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
            (r.stderr or r.stdout or "")[-220:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", default="duel")
    ap.add_argument("--only", default="")
    ap.add_argument("--keys-only", action="store_true",
                    help="render keyframes and stop - so they can be LOOKED AT first")
    a = ap.parse_args()
    shots = LISTS.get(a.list)
    if not shots:
        sys.exit("no list %r - have %s" % (a.list, ", ".join(LISTS)))
    want = set(x for x in a.only.split(",") if x)
    os.makedirs(OUT, exist_ok=True)

    made = []
    keys = 0
    for sid, refs, (w, h), prompt, action, sound, length in shots:
        if want and sid not in want:
            continue
        print("  %-15s %.1fs  %s" % (sid, length / 24.0, action[:46]), flush=True)
        kf, err = run("14_qwen_edit_ref.json", [
            ("8.inputs.image", "cast_%s.png" % refs[0]),
            ("9.inputs.image", "cast_%s.png" % refs[1]),
            ("10.inputs.prompt", prompt), ("11.inputs.prompt", NEG),
            ("20.inputs.width", w), ("20.inputs.height", h),
            ("13.inputs.seed", 21),
            ("15.inputs.filename_prefix", "claude-generated/duo/%s" % sid)])
        if not kf:
            print("      keyframe FAILED %s" % err)
            continue
        sh("cp", kf, os.path.join(OUT, "%s_key.png" % sid))
        if a.keys_only:
            keys += 1
            print("      key ok")
            continue
        staged = "duo_%s.png" % sid
        sh("cp", kf, os.path.join(COMFY, "input", staged))
        clip, err = run("60_minimax_h3_i2v.json", [
            ("8.inputs.image", staged),
            ("20.inputs.prompt", "%s. Sound: %s." % (action, sound)),
            ("20.inputs.length", length), ("33.inputs.noise_seed", 21),
            ("51.inputs.filename_prefix", "claude-generated/duo/clip_%s" % sid)])
        if not clip:
            print("      clip FAILED %s" % err)
            continue
        dst = os.path.join(OUT, "%s.mp4" % sid)
        sh("cp", clip, dst)
        made.append((sid, dst))
        print("      ok")

    if len(made) > 1:
        lst = "/tmp/_duo_%s.txt" % a.list
        with io.open(lst, "w") as f:
            for sid, p in made:
                lab = "/tmp/_duo_%s.mp4" % sid
                sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
                   "scale=854:-2,drawtext=text='%s':fontcolor=white:fontsize=28:x=18:y=18:"
                   "borderw=3:bordercolor=black@0.8" % sid,
                   "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
                   "-c:a", "aac", "-b:a", "128k", lab)
                if os.path.exists(lab):
                    f.write("file '%s'\n" % lab)
        reel = os.path.join(OUT, "duo_%s.mp4" % a.list)
        sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
           "-c", "copy", reel)
        print("\nreel: %s" % reel)
    n = keys if a.keys_only else len(made)
    print("%d/%d %s" % (n, len(shots), "keyframes" if a.keys_only else "clips"))


if __name__ == "__main__":
    main()
