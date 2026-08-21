#!/usr/bin/env python3
"""studio/_tools/h3_long.py - long H3 shots that keep their scene, and keep their sound.

    "let's try them with H3. make some more examples"

THE WAN CONTEXT-WINDOW ROUTE SOLVED CONTINUITY BY GIVING UP AUDIO. This is the other half
of that trade: H3 keeps its native stereo, and the drift is bounded a different way.

TWO CHANGES FROM THE CHAINED VERSION, AND THE SECOND MATTERS MORE THAN THE FIRST.

1. BOTH ENDS ARE PINNED. The checkpoint has been `minimax_h3_fl2va` - first-last to video
   and audio - since it was transcribed, and the node has always exposed an optional
   `last_frame`. Nothing was ever connected to it. Every H3 clip made here ran with one
   end tied and the other free, which is most of why they wandered. Workflow 62 ties both.

2. THE WAYPOINTS ARE ALL MADE UP FRONT, FROM ONE IMAGE. This is the real fix. Chaining
   accumulated error because waypoint N+1 was derived from waypoint N, so every mistake
   was inherited and compounded. Here every waypoint is an edit of the SAME base keyframe -
   they are siblings, not descendants. Nothing downstream can drift, because there is no
   downstream: the whole shot's continuity is decided before a single frame of video is
   sampled.

       base ──┬── waypoint 0 ──┐
              ├── waypoint 1 ──┼─ segment 0 = (wp0 -> wp1)   each segment bounded at BOTH
              ├── waypoint 2 ──┼─ segment 1 = (wp1 -> wp2)   ends by a sibling of the base
              ├── waypoint 3 ──┼─ segment 2 = (wp2 -> wp3)
              └── waypoint 4 ──┘  segment 3 = (wp3 -> wp4)

Because segment N ends exactly where segment N+1 begins, the joins need no crossfade - the
duplicate frame is dropped and the cut is invisible, as before.

Subjects are chosen for what H3 is actually good at. `busker` is deliberate: pitch was the
one audio result that measured clean - a cello note came out at a stable 124 Hz - so a
street musician over 30 seconds is the honest test of whether that survives length.
"""
import argparse
import io
import os
import re
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
COMFY = os.path.expanduser("~/ComfyUI")
OUT = os.path.expanduser("~/shared/H3-LONG")

REAL = ("photoreal cinematic film still, 35mm, deep focus, everything sharp from "
        "foreground to background, high detail, colour photograph, filmic grade")
NEG = ("blurry, low quality, watermark, text, signature, cgi, 3d render, deformed, "
       "extra limbs, extra fingers, nudity, nsfw")

SEG = 209                # 8.7s, the measured ceiling
WIDE = (1216, 832)
TALL = (896, 1216)

# id -> (size, base keyframe, [waypoint moment x5], [(action, sound) x4])
SHOTS = {
    "market_wok": (WIDE,
     "a night street food market, a cook in a black shirt side-on over a huge steel wok on "
     "a roaring gas burner in the foreground, behind him a long lane of lit stalls with "
     "dozens of individual customers standing, walking and eating, hanging bulbs, "
     "everyone in the background clearly resolved. " + REAL,
     ["the cook holding the wok handle with the burner flaring, crowd behind him",
      "the cook mid-toss with the noodles lifted in an arc above the wok, crowd behind",
      "the cook tipping the wok down towards a bowl on the counter, crowd behind",
      "the cook handing the full bowl across the counter, crowd behind",
      "the cook back at the burner with a fresh handful in his hand, crowd behind"],
     [("the cook heaves the wok up and around and the noodles arc into a fireball, while "
       "behind him the whole market moves at once, customers walking both ways along the "
       "lane, a couple turning to each other, a vendor handing over a bowl",
       "a roaring gas burner, a whoomph of flame, steel scraping, a dense crowd of "
       "overlapping voices, footsteps"),
      ("the cook stirs hard and tips the wok down towards the bowl, the crowd still "
       "flowing past behind him in both directions",
       "steel scraping, noodles hitting a bowl, a busy crowd talking, a scooter behind"),
      ("the cook lifts the bowl and passes it across the counter, and behind him people "
       "keep crossing the lane in both directions",
       "a bowl set down, coins, overlapping voices, a crowd in a covered lane"),
      ("the cook throws a fresh handful into the wok and it flares up, the market behind "
       "him still moving in every direction",
       "a handful hitting hot steel, a hard sizzle, a flare of gas, a crowd, a radio")]),

    "blacksmith": (WIDE,
     "a blacksmith in a leather apron side-on at an anvil in a dark forge, a bar of steel "
     "glowing orange on the anvil, a heavy hammer in his hand, the forge fire burning "
     "bright behind him, tools on the wall, sparks in the air. " + REAL,
     ["the smith with the hammer raised high above his head over the glowing bar",
      "the smith with the hammer just struck down onto the bar, sparks spraying sideways",
      "the smith holding the bar in tongs above the anvil, the steel dulling to red",
      "the smith pushing the bar back into the bright coals of the forge fire",
      "the smith lifting the white-hot bar back out of the fire with the tongs"],
     [("he drops his whole bodyweight down through the hammer onto the glowing steel and "
       "sparks spray sideways across the frame",
       "a heavy ringing hammer strike on steel, sparks, a fire roaring, a grunt"),
      ("he strikes three more times in a steady rhythm, turning the bar between blows with "
       "the tongs",
       "three ringing hammer blows on steel, tongs scraping, a roaring fire"),
      ("he lifts the bar with the tongs and pushes it deep into the glowing coals, and the "
       "fire flares up around it",
       "coals shifting, a bellows breath, fire flaring, metal scraping"),
      ("he draws the white-hot bar out of the fire in a shower of sparks and lays it back "
       "down on the anvil",
       "a rush of fire, sparks crackling, hot steel set down on an anvil")]),

    "busker": (TALL,
     "a street musician sitting on a wooden stool playing a cello in a stone underpass, "
     "open case on the ground in front of him, warm light from one end, a few people "
     "standing listening and others walking past behind him. " + REAL,
     ["the cellist with the bow resting on the strings, listeners behind him",
      "the cellist drawing the bow across the strings, head bowed, listeners behind",
      "the cellist mid-phrase with the bow near the tip and his left hand high on the neck",
      "the cellist leaning into a heavy stroke, bow pressed into the strings",
      "the cellist lifting the bow clear of the strings at the end of the phrase"],
     [("he draws the bow slowly across the strings and his left hand shifts on the neck, "
       "while behind him people walk through the underpass in both directions",
       "a deep sustained cello note played slowly, warm and resonant, echoing in a stone "
       "underpass, footsteps passing"),
      ("he plays on into a slow low phrase, rocking with the bow, listeners standing still "
       "and others passing behind",
       "a slow low cello melody continuing, resonant in a stone tunnel, distant footsteps"),
      ("he leans into a heavy stroke and the note swells, and a passer-by stops to listen",
       "the cello swelling louder, a rich low note sustained, an echoing underpass"),
      ("he finishes the phrase, lifts the bow clear of the strings and looks up, and a "
       "listener drops a coin into the open case",
       "a final cello note fading, a coin landing in a case, quiet applause, footsteps")]),

    "campfire": (WIDE,
     "four friends sitting on logs around a burning campfire at night in a forest "
     "clearing, faces lit orange by the flames, a billy can on a rack over the fire, "
     "tents behind them in the dark, sparks rising. " + REAL,
     ["the four of them sitting round the fire, one leaning forward with a stick",
      "one of them pushing a log into the fire and sparks bursting upward",
      "all four laughing together, faces lit by the flames",
      "one of them lifting the billy can off the rack over the fire",
      "the four of them sitting back with cups, the fire settling low"],
     [("one of them leans in and pushes a log into the fire and a burst of sparks whirls "
       "up into the dark, while the others shift and react around the circle",
       "a log dropping into a fire, a rush of sparks, wood cracking, night insects"),
      ("they all break into laughter together and rock back on the logs, the firelight "
       "jumping across their faces",
       "four people laughing together, a fire crackling, a forest at night"),
      ("one of them reaches out and lifts the billy can off the rack over the flames and "
       "sets it down on a stone",
       "a metal can lifted off a rack, water sloshing, a fire crackling"),
      ("they pass cups round the circle and settle back, and the fire burns down lower",
       "cups passed, quiet talking, a fire settling, an owl somewhere")]),
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
    ap.add_argument("--only", default="")
    ap.add_argument("--segments", type=int, default=4)
    a = ap.parse_args()
    want = [x for x in a.only.split(",") if x] or list(SHOTS)
    os.makedirs(OUT, exist_ok=True)

    for sid in want:
        if sid not in SHOTS:
            print("no shot %r" % sid)
            continue
        (w, h), base, moments, beats = SHOTS[sid]
        nseg = min(a.segments, len(beats), len(moments) - 1)
        print("== %s  %d x 8.7s" % (sid, nseg), flush=True)

        kf, err = run("01_qwen_t2i_turbo.json", [
            ("10.inputs.text", base), ("11.inputs.text", NEG),
            ("12.inputs.width", w), ("12.inputs.height", h), ("13.inputs.seed", 12),
            ("15.inputs.filename_prefix", "claude-generated/h3long/%s_base" % sid)])
        if not kf:
            print("   base FAILED %s" % err)
            continue
        sh("cp", kf, os.path.join(OUT, "%s_base.png" % sid))
        sh("cp", kf, os.path.join(COMFY, "input", "h3l_%s_base.png" % sid))

        # EVERY waypoint is an edit of the BASE, never of the previous waypoint. Siblings,
        # not descendants - so no error is inherited and there is nothing to compound.
        wps = []
        for i, moment in enumerate(moments[:nseg + 1]):
            if i == 0:
                wps.append(kf)
                continue
            wp, err = run("14_qwen_edit_ref.json", [
                ("8.inputs.image", "h3l_%s_base.png" % sid),
                ("9.inputs.image", "h3l_%s_base.png" % sid),
                ("10.inputs.prompt",
                 "Keep the exact same place, the same people, the same clothing, the same "
                 "objects and the same camera position as the reference image. Change only "
                 "the pose and the moment: %s. %s. %s" % (moment, base, REAL)),
                ("11.inputs.prompt", NEG),
                ("20.inputs.width", w), ("20.inputs.height", h), ("13.inputs.seed", 12 + i),
                ("15.inputs.filename_prefix",
                 "claude-generated/h3long/%s_wp%d" % (sid, i))])
            if not wp:
                print("   waypoint %d FAILED %s" % (i, err))
                break
            wps.append(wp)
        if len(wps) < nseg + 1:
            print("   only %d waypoints - skipping" % len(wps))
            continue
        for i, p in enumerate(wps):
            sh("cp", p, os.path.join(OUT, "%s_wp%d.png" % (sid, i)))

        segs = []
        for i in range(nseg):
            action, sound = beats[i]
            f0 = "h3l_%s_f%d.png" % (sid, i)
            f1 = "h3l_%s_f%d.png" % (sid, i + 1)
            sh("cp", wps[i], os.path.join(COMFY, "input", f0))
            sh("cp", wps[i + 1], os.path.join(COMFY, "input", f1))
            print("   seg %d  %s" % (i + 1, action[:50]), flush=True)
            clip, err = run("62_minimax_h3_fl.json", [
                ("8.inputs.image", f0), ("9.inputs.image", f1),
                ("20.inputs.prompt", "%s. %s. Sound: %s." % (action, REAL, sound)),
                ("20.inputs.width", w), ("20.inputs.height", h),
                ("20.inputs.length", SEG), ("33.inputs.noise_seed", 12 + i),
                ("51.inputs.filename_prefix",
                 "claude-generated/h3long/%s_seg%d" % (sid, i))])
            if not clip:
                print("      seg FAILED %s" % err)
                break
            segs.append(clip)
        if len(segs) < 2:
            print("   only %d segment(s)" % len(segs))
            continue

        parts = []
        for i, p in enumerate(segs):
            q = "/tmp/_h3l_%s_%d.mp4" % (sid, i)
            vf = "scale=%d:%d" % (w, h)
            if i:                       # segment N+1 opens where segment N closed
                vf = "select=gte(n\\,1),setpts=PTS-STARTPTS," + vf
            sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf", vf,
               "-af", "afade=t=in:st=0:d=0.10",
               "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
               "-c:a", "aac", "-b:a", "160k", "-ar", "48000", q)
            if os.path.exists(q):
                parts.append(q)
        lst = "/tmp/_h3l_%s.txt" % sid
        with io.open(lst, "w") as f:
            for q in parts:
                f.write("file '%s'\n" % q)
        dst = os.path.join(OUT, "%s_long.mp4" % sid)
        sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
           "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
           "-c:a", "aac", "-b:a", "160k", "-ar", "48000", dst)
        if os.path.exists(dst):
            d = sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "csv=p=0", dst).stdout.strip()
            print("   -> %s  %ss" % (dst, d))
        else:
            print("   join FAILED")


if __name__ == "__main__":
    main()
