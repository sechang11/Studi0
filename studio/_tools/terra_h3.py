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
Q = "masterpiece, best quality, dynamic lighting, detailed"

LISTS = {
    # FIVE ELEMENTS. Each one a single decisive burst, radial or upward - never a glow
    # that simply persists, which is what made `wind` the weakest of the first four.
    "magic": [
        ("earth", "%s, standing with both palms slammed down towards the ground, rocky "
                  "canyon floor, dust rising, %s" % (TAGS, Q),
         "slabs of stone erupt upward out of the ground around her and dust blasts outward",
         "a deep rumble, stone cracking and grinding upward, debris falling"),
        ("fire", "%s, standing with one arm thrown out to the side, embers around her, "
                 "dark ruined hall, %s" % (TAGS, Q),
         "a column of fire bursts upward from her outstretched hand and rolls outward "
         "across the frame",
         "a heavy whoosh of ignition and a roaring column of flame"),
        ("water", "%s, standing on wet stone with both arms sweeping up, a river behind "
                  "her, %s" % (TAGS, Q),
         "a wall of water rises behind her and curls over sideways across the frame",
         "water surging and rising, a heavy crash of a breaking wave"),
        ("ice", "%s, standing with one hand extended low, frost forming on the ground, "
                "frozen lake, %s" % (TAGS, Q),
         "jagged ice spikes shoot up out of the ground in a line racing away from her hand",
         "a sharp crystalline crack and ice splitting in sequence"),
        ("windmagic", "%s, standing with both hands raised overhead, leaves and grit "
                      "lifting off the ground, open plain, %s" % (TAGS, Q),
         "a vortex of wind tears up around her, throwing leaves and grit outward in a ring",
         "a rising howl of wind and debris whipping past"),
    ],

    # FIVE POSES. Cute is a gesture, not an expression - each of these MOVES.
    "poses": [
        ("wave", "%s, standing, both hands raised beside her face, smiling, sunlit meadow, %s"
         % (TAGS, Q),
         "she swings both hands out into a big two-handed wave and her hair swings with it",
         "a light breeze and a soft cloth rustle"),
        ("spin", "%s, standing mid-turn with her skirt beginning to flare, flower field, %s"
         % (TAGS, Q),
         "she spins right around on the spot and her skirt and hair flare out in a full circle",
         "cloth whipping round and a light laugh"),
        ("peace", "%s, leaning to one side with one hand near her face, bright plaza, %s"
         % (TAGS, Q),
         "she leans further to the side and snaps her hand up into a peace sign, hair "
         "swinging across",
         "a quick cloth movement and a cheerful chime"),
        ("hearts", "%s, standing with both hands together in front of her chest, soft pink "
                   "light, %s" % (TAGS, Q),
         "she claps her hands together and a burst of small glowing hearts scatters upward "
         "and outward",
         "a soft clap and a sparkling chime rising"),
        ("curtsy", "%s, standing at the top of a stone stair, holding the edge of her skirt, %s"
         % (TAGS, Q),
         "she sweeps into a deep curtsy and her long hair falls forward across her shoulder",
         "cloth sweeping and a single soft bell"),
    ],

    # FIVE FEATS. The somersault proved rotation works, so these commit harder.
    "feats": [
        ("cartwheel", "%s, standing side-on with one arm raised, stone courtyard, %s"
         % (TAGS, Q),
         "she throws herself sideways into a cartwheel across the frame and lands upright",
         "hands slapping stone, cloth snapping, a landing step"),
        ("frontflip", "%s, crouched low ready to spring forward, temple rooftop, %s"
         % (TAGS, Q),
         "she springs forward, tucks into a front flip and lands hard in a crouch",
         "a push off tile, a rush of air, a heavy landing"),
        ("slash", "%s, holding a thin sword low behind her, ruined courtyard, %s" % (TAGS, Q),
         "she steps in and swings the sword up across the frame in one committed slash",
         "a footstep, a steel blade cutting air, a sharp ring"),
        ("sprint", "%s, side-on in a low sprint start, long road, %s" % (TAGS, Q),
         "she drives forward into a sprint and runs left to right out of frame, hair "
         "streaming behind",
         "hard fast footfalls and wind past the mic"),
        ("kick", "%s, standing braced with weight on the back foot, training hall, %s"
         % (TAGS, Q),
         "she snaps a high kick up and across the frame and drops back into her stance",
         "cloth snapping, a sharp exhale, a foot landing on wood"),
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
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", default="magic")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    shots = LISTS.get(a.list) or sys.exit("no list %r" % a.list)
    want = set(x for x in a.only.split(",") if x)
    os.makedirs(OUT, exist_ok=True)
    made = []
    for sid, prompt, action, sound in shots:
        if want and sid not in want:
            continue
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
        reel = os.path.join(OUT, "terra_%s.mp4" % a.list)
        sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
           "-c", "copy", reel)
        print("\nreel: %s" % reel)
    print("%d/%d" % (len(made), len(shots)))


if __name__ == "__main__":
    main()
