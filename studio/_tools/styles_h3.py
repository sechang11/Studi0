#!/usr/bin/env python3
"""studio/_tools/styles_h3.py - batch two: does H3 hold a STYLE through motion?

    "generate one more batch after this one"

Batch one was photoreal spectacle and it answered its questions. This one goes at the
unknown underneath all of them: every single thing H3 has animated in this project has
been photoreal or anime. Two looks, out of everything a film could be.

The question is whether the style survives the video pass or melts back toward photography
- which is exactly the failure Qwen has on the image side, where a style named after an
object gets the object drawn instead. If clay stays clay for five seconds, an enormous
amount of the look library becomes animatable. If everything drifts to photoreal, then H3
is a photography engine and the style has to be imposed after it.

    claymation, puppet, papercraft, bricks   MATERIALS that must not turn to skin
    ukiyoe, watercolour, oil, ink            PAINT, which has no frame-to-frame texture
    noir, vhs, silhouette, thermal           PROCESS looks - grain, scanlines, false colour
    pixel, blueprint                         hard quantised looks that any blur destroys
    tiltshift                                a lens lie about scale

And one carried question from batch one. `cello` asked H3 for a single sustained note to
match a bow it was drawing. `drumkit` here asks for something harder - a rhythm, where
being out of time is audible in a way a wrong timbre is not.

Style is stated in BOTH prompts. The keyframe has to render it and the video prompt has to
defend it, the same way the TERRA shots carried "Anime animation." into the action.

Aspect is passed explicitly. MiniMaxH3ImageToVideo carries its own hardcoded 768x1344 and
silently ignores the keyframe, which is how every clip made in this project before today
came out portrait.
"""
import argparse
import io
import os
import re
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
COMFY = os.path.expanduser("~/ComfyUI")
OUT = os.path.expanduser("~/shared/STYLES-H3")

NEG = ("blurry, low quality, watermark, text, signature, deformed, extra limbs, "
       "extra fingers, nudity, nsfw")

LONG = 209
SHORT = 124
WIDE = (1216, 832)
TALL = (896, 1216)

# (id, size, style_clause, keyframe, action, sound, length)
SHOTS = [
    # --- materials that must not turn to skin -----------------------------------------
    ("claymation", WIDE, "stop-motion clay animation, visible fingerprints in the clay, "
     "handmade plasticine set, shallow depth of field, film grain",
     "a small round plasticine man with a wide clay grin standing on a clay hillside, a "
     "clay tree beside him, painted card sky behind",
     "the clay man throws both arms up and topples over sideways down the hill, rolling",
     "a soft dull thump, a comic slide whistle, a wooden clack", SHORT),

    ("puppet", WIDE, "felt hand-puppet television, visible stitching and fabric fuzz, "
     "warm studio lighting, 4:3 era look",
     "a shaggy blue felt puppet with big plastic eyes behind a wooden counter, felt "
     "vegetables in front of it, painted kitchen backdrop",
     "the puppet swings its whole body down and sweeps the felt vegetables sideways off "
     "the counter with both arms, mouth flapping",
     "a comic whoosh, soft objects tumbling, muffled puppet babbling", SHORT),

    ("papercraft", WIDE, "layered cut-paper diorama, visible paper edges and drop shadows, "
     "matte coloured card, soft studio light",
     "a cut-paper forest in receding layers with a paper deer standing in a clearing, paper "
     "sun above",
     "the paper deer leaps sideways across the clearing and the layers of paper trees slide "
     "past one another",
     "paper sliding on paper, a soft rustle, a light wooden knock", SHORT),

    ("bricks", WIDE, "toy scene built from interlocking plastic construction bricks, glossy "
     "moulded studs, macro photography, bright even light",
     "a small city street built entirely from interlocking plastic bricks, a brick car in "
     "the road, blocky brick figures on the pavement",
     "the brick car drives across the street from left to right and a brick tower behind it "
     "collapses, bricks scattering sideways",
     "hard plastic clattering, a rattle of loose bricks, a toy motor hum", SHORT),

    # --- paint, which has no frame-to-frame texture ----------------------------------
    ("ukiyoe", WIDE, "japanese ukiyo-e woodblock print, flat colour areas, bold black "
     "outlines, visible paper grain, limited indigo and ochre palette",
     "a great cresting wave with clawed foam over a small wooden boat, a distant mountain, "
     "woodblock print",
     "the wave rears up and breaks over sideways across the print and the boat pitches",
     "a heavy wave breaking, water rushing, wind", SHORT),

    ("watercolour", TALL, "loose watercolour painting on rough cotton paper, visible "
     "pigment blooms and hard edges, white paper showing through",
     "a rain-wet city street painted in loose watercolour, a figure with a red umbrella, "
     "washes of grey and ochre",
     "the figure with the red umbrella walks away down the street and the wet washes bleed "
     "and spread outward across the paper",
     "steady rain, footsteps in water, a quiet street", SHORT),

    ("oil", TALL, "thick impasto oil painting, heavy visible brush strokes and palette "
     "knife marks, canvas weave, warm varnished tones",
     "a bowl of lemons on a dark table lit by one window, painted in heavy impasto oil",
     "the light from the window sweeps slowly across the table and the brush strokes catch "
     "and release the light as it passes",
     "a very quiet room, a clock ticking somewhere far off", SHORT),

    ("ink", WIDE, "sumi-e ink painting, black ink on wet rice paper, bleeding edges, vast "
     "empty white space",
     "a single bamboo stalk and two leaves in black ink at one side of an empty white page",
     "a heavy drop of black ink lands and blooms outward across the wet paper, and a second "
     "bamboo stalk grows in a single stroke across the page",
     "a soft wet brush on paper, a single drop falling, silence", SHORT),

    # --- process looks -----------------------------------------------------------------
    ("noir", TALL, "1940s black and white film noir, hard venetian blind shadows, heavy "
     "film grain, deep blacks, high contrast",
     "a man in a fedora and long coat standing in a dark office doorway, venetian blind "
     "shadows striping him, cigarette smoke",
     "he turns and walks away down the corridor into the dark and the blind shadows slide "
     "across him as he goes",
     "footsteps echoing on a hard floor, a door creaking, a distant city at night", SHORT),

    ("vhs", WIDE, "1987 VHS home video, heavy chroma bleed, tracking noise, scanlines, "
     "date stamp burned in the corner, soft blown highlights",
     "a suburban back garden with a paddling pool and a garden sprinkler, children's toys "
     "on the grass, harsh summer sun",
     "the sprinkler swings around and throws water in an arc across the garden and across "
     "the pool",
     "a sprinkler ticking around, water hitting plastic, distant lawnmower", SHORT),

    ("silhouette", WIDE, "high contrast silhouette against a burning orange sky, subjects "
     "as pure black shapes, no interior detail, cinematic",
     "a lone tree and a figure on horseback as pure black silhouettes on a ridge against an "
     "enormous orange sunset",
     "the horse and rider move off along the ridge from right to left across the sunset, "
     "the horse's legs working",
     "hooves on dry ground, wind over an open ridge, distant birds", SHORT),

    ("thermal", WIDE, "thermal infrared camera image, false colour, hot bodies white and "
     "yellow, cold background deep purple, low resolution sensor noise, HUD readout",
     "a thermal camera view of three deer standing in a cold open field at night, glowing "
     "white against a dark purple field",
     "the deer startle and bolt away sideways across the field, their glowing shapes "
     "streaming across the frame",
     "a faint electronic hiss, hooves on frozen ground, night wind", SHORT),

    # --- hard quantised looks ----------------------------------------------------------
    ("pixel", WIDE, "16-bit pixel art, chunky visible square pixels, limited 32 colour "
     "palette, hard dithering, no antialiasing",
     "a pixel art side-scrolling scene of a small knight standing on a grass platform, "
     "pixel clouds, a pixel castle behind",
     "the pixel knight runs to the right along the platform and jumps a gap, landing on the "
     "next platform",
     "chiptune jump and footstep blips, a simple 8-bit melody", SHORT),

    ("blueprint", WIDE, "white line technical blueprint on deep cyan paper, precise thin "
     "linework, dimension arrows and annotations, no shading",
     "an exploded technical blueprint of a mechanical wristwatch movement, gears and springs "
     "drawn in white line on blue",
     "the exploded parts of the watch draw together and assemble into the complete movement, "
     "the gears beginning to turn",
     "fine mechanical ticking, tiny metal parts seating, a wound spring", SHORT),

    ("tiltshift", WIDE, "tilt-shift miniature effect, extremely shallow band of focus, "
     "oversaturated colour, shot from high above, everything looks like a toy model",
     "a busy harbour seen from high above with container ships, cranes and trucks, "
     "tilt-shift miniature look, bright midday",
     "the trucks and a small boat move across the harbour below and a crane arm swings "
     "slowly across",
     "a distant harbour, muffled machinery, gulls, a low horn", LONG),

    # --- the carried audio question ----------------------------------------------------
    ("drumkit", TALL, "photoreal cinematic film still, 35mm, warm rehearsal room light, "
     "shallow depth of field, high detail",
     "a drummer seated at a full drum kit in a small rehearsal room, sticks raised over the "
     "snare, close three-quarter view",
     "the drummer plays a steady rock beat, sticks striking the snare and hi-hat in time and "
     "the kick pedal working",
     "a steady mid-tempo rock drum beat, kick snare and hi-hat in time, a live room", LONG),
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
    for sid, (w, h), style, scene, action, sound, length in SHOTS:
        if want and sid not in want:
            continue
        print("  %-13s %.1fs  %s" % (sid, length / 24.0, action[:44]), flush=True)
        kf, err = run("01_qwen_t2i_turbo.json", [
            ("10.inputs.text", "%s. %s" % (scene, style)), ("11.inputs.text", NEG),
            ("12.inputs.width", w), ("12.inputs.height", h),
            ("13.inputs.seed", 77),
            ("15.inputs.filename_prefix", "claude-generated/styles/%s" % sid)])
        if not kf:
            print("      keyframe FAILED %s" % err)
            continue
        sh("cp", kf, os.path.join(OUT, "%s_key.png" % sid))
        if a.keys_only:
            keys += 1
            print("      key ok")
            continue
        staged = "sty_%s.png" % sid
        sh("cp", kf, os.path.join(COMFY, "input", staged))
        # The style is repeated into the video prompt. The keyframe renders it; the action
        # prompt has to defend it, or the motion pass drifts back toward photography.
        clip, err = run("60_minimax_h3_i2v.json", [
            ("8.inputs.image", staged),
            ("20.inputs.prompt",
             "%s. The whole shot stays in this style throughout: %s. Sound: %s."
             % (action, style, sound)),
            ("20.inputs.width", w), ("20.inputs.height", h),
            ("20.inputs.length", length), ("33.inputs.noise_seed", 77),
            ("51.inputs.filename_prefix", "claude-generated/styles/clip_%s" % sid)])
        if not clip:
            print("      clip FAILED %s" % err)
            continue
        dst = os.path.join(OUT, "%s.mp4" % sid)
        sh("cp", clip, dst)
        made.append((sid, dst))
        print("      ok")

    if len(made) > 1:
        lst = "/tmp/_sty.txt"
        with io.open(lst, "w") as f:
            for sid, p in made:
                lab = "/tmp/_sty_%s.mp4" % sid
                sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
                   "scale=854:480:force_original_aspect_ratio=decrease,"
                   "pad=854:480:(ow-iw)/2:(oh-ih)/2,"
                   "drawtext=text='%s':fontcolor=white:fontsize=26:x=18:y=18:"
                   "borderw=3:bordercolor=black@0.8" % sid,
                   "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
                   "-c:a", "aac", "-b:a", "128k", "-ar", "48000", lab)
                if os.path.exists(lab):
                    f.write("file '%s'\n" % lab)
        reel = os.path.join(OUT, "styles.mp4")
        sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
           "-c", "copy", reel)
        print("\nreel: %s" % reel)
    n = keys if a.keys_only else len(made)
    print("%d/%d %s" % (n, len(SHOTS), "keyframes" if a.keys_only else "clips"))


if __name__ == "__main__":
    main()
