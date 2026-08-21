#!/usr/bin/env python3
"""studio/_tools/anime_ep.py - FIRST LIGHT, a short anime episode through H3.

    "use h3 to make some 30 sec anime scenes. how about a short episode of something"

An episode is a harder test than a batch of scenes, and that is why it is worth doing: the
same character has to survive across four SEPARATE locations, which nothing here has been
asked to do. Continuity inside a shot is now solved twice over; continuity between shots
is not solved at all, and this is the thing that finds out how bad it is.

CASTING. Bai Liwen, from the character library - `provenance: invented`, so no real person
and no existing work is referenced. She has a reference sheet and she is a swordswoman,
which is a story you can tell in four wordless scenes. The stranger is an archetype
described purely in the prompt - black travelling robe, wide conical straw hat shadowing
the face - because a silhouette that specific holds without a sheet.

THE STACK, all of it earned earlier tonight:

  keyframes   animagine + her sheet through IPAdapter + her tags. The identity test scored
              this the strongest combination in the project.
  waypoints   ALL siblings of the scene's base image, never derived from each other, so no
              error is inherited. The storybook anime LoRA is switched ON in the edit -
              it sits at strength 0.0 in the template - because a Qwen edit left to itself
              walks a drawing back toward photography.
  segments    workflow 62, BOTH ends pinned. `last_frame` had never been connected to
              anything before today.
  style       defended in every video prompt. A style survives motion only when the video
              prompt keeps asking for it.
  tags        `solo` is dropped in the duel scene. It is a danbooru tag that actively
              suppresses a second subject, which is why an earlier beast refused to appear.

Scene 3 is written knowing that H3 duplicates a fast limb swung against a static torso.
There is not one parry from a planted stance in it - every exchange is a body committing
through the movement, which is what stopped the blacksmith's hammer ghosting.
"""
import argparse
import io
import os
import re
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
COMFY = os.path.expanduser("~/ComfyUI")
OUT = os.path.expanduser("~/shared/EPISODE")

TITLE = "FIRST LIGHT"

# Her card, verbatim. `solo` is present here and removed per-scene where it must be.
LW = ("1girl, solo, long black hair, very long hair, straight hair, jade hairpin, brown "
      "eyes, pale skin, delicate features, white and jade-green hanfu, flowing silk "
      "sleeves, wide sash, layered robes, straight sword")
LW2 = LW.replace("1girl, solo, ", "1girl, ")          # duel scene: two people in frame
HAT = ("1boy, tall broad-shouldered man, entirely black clothing, long black travelling "
       "robe, black sash, black gloves, a wide dark conical straw hat pulled low, face "
       "completely hidden in deep shadow under the hat brim, faceless, no visible face, "
       "straight sword")

ANIME = ("masterpiece, best quality, anime key visual, 2D cel shaded anime, hand drawn "
         "animation, clean line art, flat cel shading, detailed background art")
VDEF = ("Anime animation, 2D cel-shaded hand-drawn anime throughout, flat cel shading, "
        "clean line art")
NEG = ("twins, matching outfits, the man in white, the man in green, the man in a "
       "hanfu, two women, both faces visible under hats, photorealistic, photograph, 3d render, cgi, realistic skin, blurry, lowres, bad "
       "anatomy, bad hands, extra limbs, watermark, signature, text, multiple views, "
       "nudity, nsfw")

SEG = 209
W, H = 1216, 832

# Scenes with BOTH characters in frame. One IPAdapter each, separated by attention
# masks (workflow 45) - a single PLUS FACE reference is applied to every face in the
# frame, which is why the stranger kept coming back as a second Liwen in a hat. Her
# sheet drives the LEFT half, his the RIGHT.
TWO = {"s3_duel", "s4_firstlight"}
STRANGER_SHEET = "sheet_stranger.png"   # cut from the s2 arrival, which drew him well

# id -> (ipa_weight, tags, base scene, [waypoint moment x5], [(action, sound) x4])
SCENES = [
 ("s1_dawn", 0.6, LW,
  "%s, standing alone in the middle of a wide empty flagstone courtyard of a mountain "
  "sword school at dawn, thick mist, pine trees and a tiled gate behind her, sword drawn "
  "and held low, %s" % (LW, ANIME),
  ["standing still with the sword held low, mist around her ankles",
   "stepping forward into a long sweeping cut, sleeves flaring wide",
   "turned fully around mid-form with her hair and sleeves trailing behind her",
   "dropped low in a deep lunge with the blade extended straight out",
   "risen upright with the blade drawn back beside her head, still, breathing"],
  [("she steps forward and sweeps the sword up across the frame in one long cut, her wide "
    "sleeves flaring out with the movement, mist rolling across the flagstones around her",
    "a blade cutting through air in a long arc, silk sleeves snapping, a single footfall on "
    "wet stone, wind through pines, a distant temple bell"),
   ("she turns her whole body through a second cut and her long black hair and sleeves "
    "trail around after her, mist swirling in her wake",
    "cloth whipping round, a blade slicing air, a measured footstep, mountain wind"),
   ("she drives forward and drops into a deep lunge, the blade punching straight out ahead "
    "of her, and the mist parts away from the movement",
    "a hard step on stone, a sharp exhale, a blade thrusting through air"),
   ("she rises upright and draws the blade back beside her head and holds absolutely "
    "still, only her sleeves and hair settling",
    "silk settling, a slow breath, wind through pines, one temple bell")]),

 ("s2_arrival", 0.55, HAT + ", solo",
  "%s across his back, climbing a long flight of worn stone steps cut into a misty pine "
  "mountainside, seen from above and behind, lanterns on posts, %s" % (HAT, ANIME),
  ["low on the steps, one foot raised, mist below him",
   "halfway up the steps, robe blown sideways by the wind",
   "near the top of the steps with the tiled gate visible above",
   "standing at the top step directly before the closed tiled gate",
   "one hand raised and laid flat against the timber of the gate"],
  [("he climbs the stone steps one heavy stride at a time and the mist rolls down past him "
    "the other way, his black robe dragging in the wind",
    "slow heavy footsteps on wet stone, a robe snapping in wind, mist, a crow calling"),
   ("the wind gusts hard across the mountainside and throws his robe and the hanging "
    "lanterns sideways as he keeps climbing",
    "a hard gust of wind, cloth cracking, lantern chains rattling, footsteps"),
   ("he reaches the top of the steps and stops dead in front of the closed timber gate, "
    "the mist streaming past him",
    "a last footstep, wind dropping away, silence, a rope creaking"),
   ("he raises one hand and lays it flat on the gate, and the timber shifts under it",
    "a hand on wet timber, wood groaning, a heavy latch shifting, wind")]),

 ("s3_duel", 0.55, LW2,
  "2people, on the LEFT %s standing side-on with her blade raised, and on the RIGHT %s "
  "standing opposite her, a wide flagstone courtyard between them, dead pine needles "
  "blowing across the ground, mist, %s" % (LW2, HAT, ANIME),
  ["the two of them standing far apart across the courtyard, blades low",
   "the two of them rushing at each other across the flagstones, blades back",
   "the two of them locked blade to blade in the centre, sparks between them",
   "the two of them having passed through each other, backs turned, blades out",
   "the two of them standing still at opposite sides, blades lowered"],
  [("the two of them break from standing and run straight at each other across the "
    "courtyard, dead pine needles thrown up from under their feet",
    "two sets of running footfalls on stone, robes cracking in the air, a rising note"),
   ("they crash together in the centre and their blades lock hard, sparks bursting off the "
    "steel between them, both of them driving forward",
    "a violent steel clash, sparks, blades grinding, two hard exhales"),
   ("they break the bind and both step through past each other to opposite sides of the "
    "frame, blades scraping apart, hair and robes swinging round after them",
    "steel scraping apart, fast footsteps on stone, cloth snapping"),
   ("they come to a stop back to back with their blades held out, and stand absolutely "
    "still as the pine needles settle around them",
    "footsteps stopping, silence falling, cloth settling, wind through pines")]),

 ("s4_firstlight", 0.55, LW2,
  "2people, on the LEFT %s standing with her sword lowered, and on the RIGHT %s standing "
  "opposite her with his sword sheathed, a wide flagstone courtyard, the sun just "
  "breaking over a mountain ridge behind them, mist burning off, %s" % (LW2, HAT, ANIME),
  ["the two of them standing apart, blades lowered, mist still thick",
   "the stranger bowing low with both hands together, she watching him",
   "the stranger turning away towards the gate, she standing still",
   "the stranger gone through the gate, she alone in the courtyard",
   "she alone with the sun full over the ridge, sheathing the sword"],
  [("the stranger lowers his head and bows deeply to her with both hands together, and she "
    "stands watching him without moving",
    "cloth folding, a long breath, wind easing, a temple bell"),
   ("he turns and walks away across the courtyard towards the gate, his robe swinging, and "
    "she stays exactly where she is",
    "receding footsteps on stone, a robe swinging, wind through pines"),
   ("the first sunlight breaks over the ridge and floods across the courtyard, burning the "
    "mist off the flagstones around her",
    "a low warm swell, wind, birds starting, a temple bell"),
   ("she slides the sword back into its scabbard in one movement and lifts her head into "
    "the sunlight",
    "a blade sliding home into a scabbard, a single clean note, birdsong, wind")]),
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
    ap.add_argument("--keys-only", action="store_true",
                    help="stop after keyframes and waypoints so they can be LOOKED AT")
    ap.add_argument("--assemble", action="store_true",
                    help="only rebuild the episode from scenes already rendered")
    a = ap.parse_args()
    want = [x for x in a.only.split(",") if x]
    os.makedirs(OUT, exist_ok=True)

    if not a.assemble:
        for sid, ipa, tags, base, moments, beats in SCENES:
            if want and sid not in want:
                continue
            print("== %s" % sid, flush=True)
            if sid in TWO:
                kf, err = run("45_anime_two_char_ipadapter.json", [
                    ("2.inputs.image", "sheet_liwen.png"),        # left half
                    ("12.inputs.image", STRANGER_SHEET),          # right half
                    ("20.inputs.width", W), ("20.inputs.height", H),
                    ("21.inputs.width", W // 2), ("21.inputs.height", H),
                    ("23.inputs.x", W // 2),
                    ("4.inputs.weight", 0.6), ("14.inputs.weight", 0.6),
                    ("5.inputs.text", base), ("6.inputs.text", NEG),
                    ("7.inputs.width", W), ("7.inputs.height", H),
                    ("8.inputs.seed", 31),
                    ("10.inputs.width", W), ("10.inputs.height", H),
                    ("11.inputs.filename_prefix",
                     "claude-generated/ep/%s_base" % sid)])
            else:
                kf, err = run("22_anime_kf_ipadapter.json", [
                    ("2.inputs.image", "sheet_liwen.png"),
                    ("4.inputs.weight", ipa),
                    ("5.inputs.text", base), ("6.inputs.text", NEG),
                    ("7.inputs.width", W), ("7.inputs.height", H),
                    ("8.inputs.seed", 31),
                    ("10.inputs.width", W), ("10.inputs.height", H),
                    ("11.inputs.filename_prefix",
                     "claude-generated/ep/%s_base" % sid)])
            if not kf:
                print("   base FAILED %s" % err)
                continue
            sh("cp", kf, os.path.join(OUT, "%s_base.png" % sid))
            sh("cp", kf, os.path.join(COMFY, "input", "ep_%s_base.png" % sid))

            wps = [kf]
            for i, moment in enumerate(moments[1:5], start=1):
                wp, err = run("14_qwen_edit_ref.json", [
                    ("8.inputs.image", "ep_%s_base.png" % sid),
                    ("9.inputs.image", "ep_%s_base.png" % sid),
                    # the storybook anime LoRA sits at 0.0 in the template; a Qwen edit
                    # left alone walks a drawing back toward photography
                    ("7.inputs.strength_model", 0.9),
                    ("10.inputs.prompt",
                     "Keep the exact same anime drawing style, the same characters, the "
                     "same clothing, the same place and the same camera as the reference. "
                     "Change only the pose and the moment: %s. %s. %s"
                     % (moment, tags, ANIME)),
                    ("11.inputs.prompt", NEG),
                    ("20.inputs.width", W), ("20.inputs.height", H),
                    ("13.inputs.seed", 31 + i),
                    ("15.inputs.filename_prefix",
                     "claude-generated/ep/%s_wp%d" % (sid, i))])
                if not wp:
                    print("   waypoint %d FAILED %s" % (i, err))
                    break
                wps.append(wp)
            if len(wps) < 5:
                print("   only %d waypoints" % len(wps))
                continue
            for i, p in enumerate(wps):
                sh("cp", p, os.path.join(OUT, "%s_wp%d.png" % (sid, i)))
            if a.keys_only:
                print("   keys ok")
                continue

            segs = []
            for i in range(4):
                action, sound = beats[i]
                f0, f1 = "ep_%s_f%d.png" % (sid, i), "ep_%s_f%d.png" % (sid, i + 1)
                sh("cp", wps[i], os.path.join(COMFY, "input", f0))
                sh("cp", wps[i + 1], os.path.join(COMFY, "input", f1))
                print("   seg %d  %s" % (i + 1, action[:48]), flush=True)
                clip, err = run("62_minimax_h3_fl.json", [
                    ("8.inputs.image", f0), ("9.inputs.image", f1),
                    ("20.inputs.prompt", "%s. %s. Sound: %s." % (action, VDEF, sound)),
                    ("20.inputs.width", W), ("20.inputs.height", H),
                    ("20.inputs.length", SEG), ("33.inputs.noise_seed", 31 + i),
                    ("51.inputs.filename_prefix",
                     "claude-generated/ep/%s_seg%d" % (sid, i))])
                if not clip:
                    print("      seg FAILED %s" % err)
                    break
                segs.append(clip)
            if len(segs) < 2:
                print("   only %d segments" % len(segs))
                continue
            parts = []
            for i, p in enumerate(segs):
                q = "/tmp/_ep_%s_%d.mp4" % (sid, i)
                vf = "scale=%d:%d" % (W, H)
                if i:
                    vf = "select=gte(n\\,1),setpts=PTS-STARTPTS," + vf
                sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf", vf,
                   "-af", "afade=t=in:st=0:d=0.10",
                   "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
                   "-c:a", "aac", "-b:a", "160k", "-ar", "48000", q)
                if os.path.exists(q):
                    parts.append(q)
            lst = "/tmp/_ep_%s.txt" % sid
            with io.open(lst, "w") as f:
                for q in parts:
                    f.write("file '%s'\n" % q)
            dst = os.path.join(OUT, "%s.mp4" % sid)
            sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
               "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
               "-c:a", "aac", "-b:a", "160k", "-ar", "48000", dst)
            d = sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "csv=p=0", dst).stdout.strip()
            print("   -> %s  %ss" % (dst, d))

    # ---- assemble the episode -----------------------------------------------------
    have = [s[0] for s in SCENES if os.path.exists(os.path.join(OUT, "%s.mp4" % s[0]))]
    if len(have) < 2:
        print("only %d scenes - not assembling" % len(have))
        return
    font = (sh("fc-match", "-f", "%{file}", "serif").stdout or "").strip()
    card = "/tmp/_ep_card.mp4"
    sh("ffmpeg", "-y", "-v", "error",
       "-f", "lavfi", "-i", "color=c=black:s=%dx%d:d=3.2:r=24" % (W, H),
       "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo:d=3.2",
       "-vf", ("drawtext=fontfile='%s':text='%s':fontcolor=white:fontsize=96:"
               "x=(w-text_w)/2:y=(h-text_h)/2-20:alpha='min(1,max(0,(t-0.3)*1.6))',"
               "drawtext=fontfile='%s':text='a Cloud Terrace short':fontcolor=white@0.65:"
               "fontsize=32:x=(w-text_w)/2:y=(h-text_h)/2+70:"
               "alpha='min(1,max(0,(t-1.0)*1.4))'" % (font, TITLE, font)),
       "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest", card)
    lst = "/tmp/_ep_all.txt"
    with io.open(lst, "w") as f:
        if os.path.exists(card):
            f.write("file '%s'\n" % card)
        for sid in have:
            f.write("file '%s'\n" % os.path.join(OUT, "%s.mp4" % sid))
    ep = os.path.join(OUT, "FIRST_LIGHT.mp4")
    sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
       "-c:v", "libx264", "-crf", "19", "-preset", "veryfast", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "160k", "-ar", "48000", ep)
    d = sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "csv=p=0", ep).stdout.strip()
    print("\nEPISODE: %s  %ss  (%d scenes)" % (ep, d, len(have)))


if __name__ == "__main__":
    main()
