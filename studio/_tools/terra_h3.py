#!/usr/bin/env python3
"""studio/_tools/terra_h3.py - rebuilt for scenes rather than solo effects.

    "be more creative with each. spend a little more time designing the scene. the magic is
     cast on an enemy beast, party, or object... the athletic moves, have it interact with
     the same beast... or a longer sequence like a dance routine. the acting cute, make it
     a bit longer and be more intentional, like a wink, blowing a kiss, blushing, kawaii"

THREE THINGS THAT HAD TO CHANGE IN THE RUNNER, each of them a lesson from a failed shot:

  `solo` COMES OUT OF HER TAGS when there is a target in frame. Her tag string is
  "terra branford (final fantasy vi), 1girl, SOLO, long wavy green hair..." and solo is a
  danbooru tag that actively suppresses a second subject. Asking that prompt for a beast
  is asking it to fight itself - the same shape as STYLE_KITCHEN saying "morning light"
  and "muted" in one breath.

  LENGTH IS PER SHOT. A dance or gymnastics routine cannot happen in 5.2s. 209 frames
  (8.7s) is the measured ceiling before the kernel OOMs at 43 GB, so the routines get it
  and the rest stay at 124.

  FRAMING IS PER SHOT. A wink is a face. Every previous cute shot was full-body, which put
  her eyes about forty pixels tall - the gesture was correct and invisible.

AND EVERY ACTION STILL OBEYS THE THREE RULES THE FAILURES ESTABLISHED:
  one big committed event, not a gentle continuous one       (`wind`)
  motion across the frame or with gravity, never toward camera (`mud`)
  rotation stays in the frame's plane                        (`cartwheel` rolled the camera)
"""
import argparse
import io
import os
import re
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
COMFY = os.path.expanduser("~/ComfyUI")
OUT = os.path.expanduser("~/shared/TERRA-H3")

# WITH and WITHOUT `solo`. The second is for any frame containing something else alive.
SOLO = ("terra branford (final fantasy vi), 1girl, solo, long wavy green hair, very long "
        "hair, green eyes, red hair ribbon")
WITH = ("terra branford (final fantasy vi), 1girl, long wavy green hair, very long hair, "
        "green eyes, red hair ribbon")
NEG = ("blurry, lowres, bad anatomy, bad hands, extra limbs, watermark, signature, text, "
       "multiple views, cropped")
Q = "masterpiece, best quality, detailed, dynamic lighting, anime key visual"

LONG = 209      # 8.7s - the measured ceiling before the kernel OOMs
SHORT = 124     # 5.2s

# (id, tags, keyframe, action, sound, length)
LISTS = {
    # Magic with a TARGET. The spell has to arrive somewhere and something has to react.
    "spells": [
        ("fire_wolf", WITH,
         "%s, standing braced with one arm thrown forward, facing a huge snarling black "
         "wolf-beast with burning orange eyes lunging at her across a ruined stone bridge, "
         "night, %s" % (WITH, Q),
         "a wall of fire bursts from her hand into the lunging wolf and the beast is thrown "
         "sideways out of frame, embers scattering",
         "a roar, an ignition whoosh, a heavy impact and a yelp", SHORT),

        ("ice_bridge", SOLO,
         "%s, standing at the edge of a deep chasm with one hand extended over the drop, "
         "mist below, mountain pass, %s" % (SOLO, Q),
         "a bridge of ice crystallises outward across the chasm from her hand, spreading in "
         "jagged plates until it reaches the far side",
         "a crystalline crackle spreading, ice groaning, wind in a chasm", SHORT),

        ("stone_wall", WITH,
         "%s, crouched low with both palms pressed to the ground, a towering moss-covered "
         "stone golem raising one huge fist above her, forest ruins, %s" % (WITH, Q),
         "a slab of rock erupts up out of the ground between her and the golem and the fist "
         "smashes into it, chunks flying sideways",
         "stone grinding upward, a huge impact, rubble scattering", SHORT),

        ("heal_knight", WITH,
         "%s, kneeling beside a wounded armoured knight slumped against a broken wall, both "
         "her hands held over him, green light in her palms, battlefield dusk, %s"
         % (WITH, Q),
         "green light flows from her hands down into the knight and he pushes himself "
         "upright against the wall",
         "a soft rising chime, armour shifting, a sharp breath", SHORT),

        ("chain_lightning", WITH,
         "%s, standing with one arm raised, surrounded at a distance by a ring of small "
         "shadowy four-legged creatures with white eyes, dark marsh, %s" % (WITH, Q),
         "lightning arcs from her hand and leaps between the shadow creatures in a chain, "
         "each one bursting apart as it is struck",
         "a sharp electrical crack and a rapid chain of bursts", SHORT),
    ],

    # Athletic, with a target or as a routine. Rotation stays in the frame's plane.
    "action": [
        ("vault_beast", WITH,
         "%s, sprinting towards a huge charging boar-beast side-on, low camera, dust, "
         "canyon floor, %s" % (WITH, Q),
         "she plants one hand on the charging beast's back, vaults over it and lands "
         "running on the far side",
         "thundering hooves, a hand slap on hide, a landing skid", SHORT),

        ("duel_claw", WITH,
         "%s, side-on holding a thin sword in a high guard, a huge scaled clawed arm "
         "swinging down towards her, ruined hall, %s" % (WITH, Q),
         "she parries the descending claw with her blade in a shower of sparks and steps "
         "through into a rising counter-slash",
         "a heavy claw swing, a metallic clash and sparks, a blade ringing", SHORT),

        ("gym_routine", SOLO,
         "%s, standing at the corner of a sunlit wooden gymnasium floor, arms raised in an "
         "opening pose, %s" % (SOLO, Q),
         "she runs across the floor, springs into a front handspring, lands, immediately "
         "into a second front flip, lands and finishes with both arms raised",
         "running footfalls on wood, hands slapping the floor, two landings, applause", LONG),

        ("dance", SOLO,
         "%s, standing centre on a lantern-lit stone plaza at night, arms low, %s"
         % (SOLO, Q),
         "she sweeps into a dance - a turn with her skirt flaring, a step to the side, arms "
         "carving up and across, then a final spin and a held pose",
         "a rhythmic drum and string melody, cloth whipping, footfalls on stone", LONG),

        ("staff_flourish", SOLO,
         "%s, holding a long slender staff angled across her body, temple courtyard, %s"
         % (SOLO, Q),
         "she spins the staff in a fast figure-of-eight across her body, steps through and "
         "snaps it to a stop under one arm",
         "a staff whistling through air in fast arcs and a sharp final snap", SHORT),
    ],

    # Cute, and CLOSE. A wink is a face; every earlier attempt framed her full-length.
    "kawaii": [
        ("wink", SOLO,
         "%s, upper body portrait, close on her face, smiling warmly at the viewer, soft "
         "sunlit background, %s" % (SOLO, Q),
         "she closes one eye in a slow deliberate wink and her smile widens, tilting her "
         "head slightly",
         "a soft sparkle chime and a gentle breeze", SHORT),

        ("kiss", SOLO,
         "%s, upper body portrait, one hand raised near her lips, warm pink background, %s"
         % (SOLO, Q),
         "she presses her fingers to her lips and sweeps her hand outward blowing a kiss, "
         "small glowing hearts trailing off her fingertips",
         "a soft kiss, a rising sparkle chime", SHORT),

        ("blush", SOLO,
         "%s, upper body portrait, wide-eyed and startled, hands beginning to rise, warm "
         "interior, %s" % (SOLO, Q),
         "a deep blush spreads across her cheeks and she claps both hands over her face, "
         "then peeks out between her fingers",
         "a small surprised gasp and a soft chime", SHORT),

        ("pout", SOLO,
         "%s, upper body portrait, cheeks puffed and eyes narrowed in mock annoyance, arms "
         "folded, soft background, %s" % (SOLO, Q),
         "she puffs her cheeks further and turns her face away, then glances back and breaks "
         "into a laugh",
         "a small huff, then a light laugh", SHORT),

        ("kawaii", SOLO,
         "%s, upper body portrait, both hands raised beside her cheeks framing her face, "
         "sparkles in the air, pastel background, %s" % (SOLO, Q),
         "she tilts her head, opens both hands beside her face and a burst of sparkles "
         "scatters outward around her",
         "a bright sparkling chime and a cheerful hum", SHORT),
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
            (r.stderr or r.stdout or "")[-200:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", default="spells")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    shots = LISTS.get(a.list)
    if not shots:
        sys.exit("no list %r - have %s" % (a.list, ", ".join(LISTS)))
    want = set(x for x in a.only.split(",") if x)
    os.makedirs(OUT, exist_ok=True)

    made = []
    for sid, _tags, prompt, action, sound, length in shots:
        if want and sid not in want:
            continue
        print("  %-16s %.0fs  %s" % (sid, length / 24.0, action[:48]), flush=True)
        kf, err = run("22_anime_kf_ipadapter.json", [
            ("2.inputs.image", "sheet_anime_terra.png"),
            ("5.inputs.text", prompt), ("6.inputs.text", NEG),
            ("7.inputs.width", 768), ("7.inputs.height", 1344),
            ("8.inputs.seed", 11),
            ("10.inputs.width", 768), ("10.inputs.height", 1344),
            ("11.inputs.filename_prefix", "claude-generated/terrav2/%s" % sid)])
        if not kf:
            print("      keyframe FAILED %s" % err)
            continue
        staged = "terrav2_%s.png" % sid
        sh("cp", kf, os.path.join(COMFY, "input", staged))
        clip, err = run("60_minimax_h3_i2v.json", [
            ("8.inputs.image", staged),
            ("20.inputs.prompt", "%s. Anime animation. Sound: %s." % (action, sound)),
            ("20.inputs.length", length), ("33.inputs.noise_seed", 11),
            ("51.inputs.filename_prefix", "claude-generated/terrav2/clip_%s" % sid)])
        if not clip:
            print("      clip FAILED %s" % err)
            continue
        dst = os.path.join(OUT, "%s.mp4" % sid)
        sh("cp", clip, dst)
        made.append((sid, dst))
        print("      ok")

    if len(made) > 1:
        lst = "/tmp/_tv2_%s.txt" % a.list
        with io.open(lst, "w") as f:
            for sid, p in made:
                lab = "/tmp/_tv2_%s.mp4" % sid
                sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
                   "scale=540:-2,drawtext=text='%s':fontcolor=white:fontsize=28:x=18:y=18:"
                   "borderw=3:bordercolor=black@0.8" % sid,
                   "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
                   "-c:a", "aac", "-b:a", "128k", lab)
                if os.path.exists(lab):
                    f.write("file '%s'\n" % lab)
        reel = os.path.join(OUT, "terra_%s.mp4" % a.list)
        sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
           "-c", "copy", reel)
        print("\nreel: %s" % reel)
    print("%d/%d" % (len(made), len(shots)))


if __name__ == "__main__":
    main()
