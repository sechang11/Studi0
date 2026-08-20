#!/usr/bin/env python3
"""studio/_tools/random_h3.py - a wide random batch through H3.

    "let's make a random batch of generations with mini max h3"

Random here means VARIED, not arbitrary. The last arbitrary set drew "why do i want to see
2 second clips of a man and a dirty shoe" - so every shot below is something worth watching
on its own, and the spread is deliberate: each one puts H3 somewhere it has never been.

Everything H3 has done in this project is a person or a product. So this batch is chosen to
find the edges of that:

    hummingbird, dog_shake, horses      NON-HUMAN RIGS. wings, a spine twisting, four legs
    subway_doors, market_wok            MANY BODIES at once
    dominoes, glass_shatter, ice_crack  PHYSICS THAT PROPAGATES across the frame
    cello                               does the audio pass generate MUSIC, or only effects?
    rocket_launch, paraglide            SCALE far beyond a room
    pizza_oven, wave_barrel             materials - cheese, water - that deform continuously

`cello` is the one I most want the answer to. H3 makes native stereo audio in the same pass
and every shot so far has asked it for impacts and ambience. Nothing has asked it to play a
note in tune with a bow that the video is drawing. If that works it changes what the audio
department is for.

THE RULES ALL STILL APPLY, and they are why the shots are worded the way they are:
  a whole body travelling, never a fast limb against a static torso   (duel_claw ghosted)
  one big committed event, not a gentle continuous one                (`wind`)
  motion lateral or with gravity, never toward camera                 (`mud`)
  rotation stays in the frame's plane                                 (`cartwheel`)

`blacksmith` is the deliberate exception - a hammer swing is exactly the shape that ghosted,
so it is written as the smith dropping his whole weight through the blow. If it ghosts
anyway, that sharpens the rule; if it holds, the rule is about the BODY and not the tool.
"""
import argparse
import io
import os
import re
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
COMFY = os.path.expanduser("~/ComfyUI")
OUT = os.path.expanduser("~/shared/RANDOM-H3")

REAL = ("photoreal cinematic film still, 35mm, natural light, shallow depth of field, "
        "sharp focus, high detail, colour photograph, filmic grade")
NEG = ("blurry, low quality, watermark, text, signature, cgi, 3d render, plastic, "
       "deformed, extra limbs, extra fingers, nudity, nsfw")

LONG = 209      # 8.7s - measured ceiling before the kernel OOMs at 43 GB
SHORT = 124     # 5.2s

WIDE = (1216, 832)
TALL = (896, 1216)

# (id, size, keyframe, action, sound, length)
SHOTS = [
    # --- non-human rigs -------------------------------------------------------------
    ("hummingbird", WIDE,
     "extreme close macro of a green and violet hummingbird hovering beside a red trumpet "
     "flower, wings blurred, dark green background, morning light. " + REAL,
     "the hummingbird darts sideways to the flower, holds there with its bill in the throat "
     "of the bloom, then flicks away out of frame",
     "a dense insect-like wing hum, a rush of air, garden ambience", SHORT),

    ("dog_shake", WIDE,
     "a soaking wet golden retriever standing side-on in shallow lake water, fur heavy with "
     "water, low afternoon sun behind it, backlit spray. " + REAL,
     "the dog shakes violently from its head down through its whole body and water sprays "
     "outward in a huge ring, its ears and jowls whipping around",
     "a heavy wet shake, water spattering, a jingle of a collar tag, a snort", SHORT),

    ("horses", WIDE,
     "four dark horses galloping side-on through shallow water on a wide flat plain, spray "
     "flying from their hooves, low sun, side view. " + REAL,
     "the horses thunder across the frame from right to left, throwing sheets of spray up "
     "from every hoof strike",
     "heavy hooves striking water, spray, snorting breath, a wide open plain", LONG),

    # --- many bodies ----------------------------------------------------------------
    ("subway_doors", WIDE,
     "a crowded underground station platform seen side-on, a train stopped with its doors "
     "still shut, commuters packed along the platform edge, fluorescent light. " + REAL,
     "the train doors slide apart and the crowd surges sideways into the carriage, bodies "
     "pressing through the opening",
     "doors hissing open, a chime, a crowd moving, echoing announcements", SHORT),

    ("market_wok", WIDE,
     "a street food stall at night, a cook side-on over a huge steel wok on a roaring "
     "burner, noodles in the wok, crowd and hanging bulbs behind. " + REAL,
     "the cook drops his weight and heaves the whole wok up and around, and the noodles "
     "arc up into the air in a fireball before falling back",
     "a roaring gas burner, a whoomph of flame, steel scraping, a night market crowd",
     SHORT),

    # --- physics that propagates ----------------------------------------------------
    ("dominoes", WIDE,
     "a long curving line of black and white dominoes standing on a pale wooden table, "
     "shot low and close along the line, warm side light. " + REAL,
     "the first domino tips and the fall runs away down the whole curving line, one after "
     "another, all the way to the far end",
     "a rapid clattering run of falling tiles, close and dry", LONG),

    ("glass_shatter", WIDE,
     "a single empty wine glass standing on a black reflective surface, one hard rim light, "
     "black background. " + REAL,
     "the glass shatters and the fragments blow sideways across the frame in slow motion, "
     "the stem toppling",
     "a sharp crack, a spray of glass fragments skittering, then silence", SHORT),

    ("ice_crack", WIDE,
     "a wide flat frozen lake surface at dawn, pale blue ice with trapped bubbles, "
     "mountains far behind, low sun. " + REAL,
     "a crack tears across the ice from one side of the frame to the other, branching as it "
     "runs, plates lifting slightly along it",
     "a deep resonant boom, a long tearing crack racing away, groaning ice", SHORT),

    # --- the audio question ---------------------------------------------------------
    ("cello", TALL,
     "close on the strings and bridge of a cello with a bow resting across them, a "
     "musician's hand on the bow, warm dark concert hall light. " + REAL,
     "the bow draws slowly and steadily across the strings from the frog to the tip, the "
     "string trembling under it",
     "a single deep sustained cello note played slowly, warm and resonant, in a hall",
     SHORT),

    # --- the ghosting exception -----------------------------------------------------
    ("blacksmith", WIDE,
     "a blacksmith side-on at an anvil in a dark forge, a bar of steel glowing orange on "
     "the anvil, a heavy hammer raised high above his head, sparks. " + REAL,
     "he drops his whole bodyweight down through the hammer onto the glowing steel and a "
     "burst of sparks sprays sideways across the frame",
     "a heavy ringing hammer strike on steel, sparks, a fire roaring, a grunt", SHORT),

    # --- scale ----------------------------------------------------------------------
    ("rocket_launch", TALL,
     "a tall white rocket on a launch pad at night, floodlit, venting vapour, service tower "
     "beside it, wide shot. " + REAL,
     "the engines ignite and the rocket climbs upward out of the top of the frame on a "
     "column of white fire, the pad flooding with light and smoke",
     "a colossal low roar building, crackling exhaust, a long rumble", SHORT),

    ("paraglide", WIDE,
     "a paraglider pilot running side-on down a steep grassy ridge with the canopy just "
     "beginning to lift behind, a wide valley below, evening light. " + REAL,
     "the canopy fills and lifts and the pilot is drawn up off the slope and out sideways "
     "over the valley, legs swinging free",
     "wind across a ridge, fabric snapping taut, lines creaking, footsteps stopping",
     SHORT),

    # --- deforming materials --------------------------------------------------------
    ("pizza_oven", WIDE,
     "a wood-fired pizza oven mouth glowing orange, a long peel sliding a finished pizza "
     "out, close, dark kitchen. " + REAL,
     "the peel draws the pizza out of the oven and the cheese stretches and sags as it "
     "clears the mouth, steam pouring off it",
     "a fire roaring in a brick oven, a wooden peel scraping, a crust crackling", SHORT),

    ("wave_barrel", WIDE,
     "a surfer side-on inside the hollow of a large blue barrelling wave, spray at the lip, "
     "sunlight through the water wall, shot from the shoulder of the wave. " + REAL,
     "the barrel throws over the surfer and he races along inside it as the lip collapses "
     "behind him, spray blasting out of the tube",
     "a heavy wave roaring and collapsing, water rushing, spray", SHORT),

    ("neon_rain", TALL,
     "a narrow alley at night in heavy rain, dense neon signage on both walls, wet ground "
     "throwing reflections, a lone figure with a closed umbrella. " + REAL,
     "the figure opens the umbrella overhead in one sharp motion and rain bursts off the "
     "canopy in a ring of spray",
     "hard rain on a canopy, water running in a gutter, a low neon hum, distant traffic",
     SHORT),
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
            (r.stderr or r.stdout or "")[-220:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--keys-only", action="store_true")
    a = ap.parse_args()
    want = set(x for x in a.only.split(",") if x)
    os.makedirs(OUT, exist_ok=True)

    made, keys = [], 0
    for sid, (w, h), prompt, action, sound, length in SHOTS:
        if want and sid not in want:
            continue
        print("  %-15s %.1fs  %s" % (sid, length / 24.0, action[:46]), flush=True)
        kf, err = run("01_qwen_t2i_turbo.json", [
            ("10.inputs.text", prompt), ("11.inputs.text", NEG),
            ("12.inputs.width", w), ("12.inputs.height", h),
            ("13.inputs.seed", 33),
            ("15.inputs.filename_prefix", "claude-generated/rand/%s" % sid)])
        if not kf:
            print("      keyframe FAILED %s" % err)
            continue
        sh("cp", kf, os.path.join(OUT, "%s_key.png" % sid))
        if a.keys_only:
            keys += 1
            print("      key ok")
            continue
        staged = "rand_%s.png" % sid
        sh("cp", kf, os.path.join(COMFY, "input", staged))
        clip, err = run("60_minimax_h3_i2v.json", [
            ("8.inputs.image", staged),
            ("20.inputs.prompt", "%s. Sound: %s." % (action, sound)),
            ("20.inputs.width", w), ("20.inputs.height", h),
            ("20.inputs.length", length), ("33.inputs.noise_seed", 33),
            ("51.inputs.filename_prefix", "claude-generated/rand/clip_%s" % sid)])
        if not clip:
            print("      clip FAILED %s" % err)
            continue
        dst = os.path.join(OUT, "%s.mp4" % sid)
        sh("cp", clip, dst)
        made.append((sid, dst))
        print("      ok")

    if len(made) > 1:
        lst = "/tmp/_rand.txt"
        with io.open(lst, "w") as f:
            for sid, p in made:
                lab = "/tmp/_rand_%s.mp4" % sid
                sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
                   "scale=854:480:force_original_aspect_ratio=decrease,"
                   "pad=854:480:(ow-iw)/2:(oh-ih)/2,"
                   "drawtext=text='%s':fontcolor=white:fontsize=26:x=18:y=18:"
                   "borderw=3:bordercolor=black@0.8" % sid,
                   "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
                   "-c:a", "aac", "-b:a", "128k", "-ar", "48000", lab)
                if os.path.exists(lab):
                    f.write("file '%s'\n" % lab)
        reel = os.path.join(OUT, "random.mp4")
        sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
           "-c", "copy", reel)
        print("\nreel: %s" % reel)
    n = keys if a.keys_only else len(made)
    print("%d/%d %s" % (n, len(SHOTS), "keyframes" if a.keys_only else "clips"))


if __name__ == "__main__":
    main()
