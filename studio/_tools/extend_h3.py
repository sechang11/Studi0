#!/usr/bin/env python3
"""studio/_tools/extend_h3.py - 30 second clips out of an 8.7 second model.

    "can we extend these to create a whole 30 seconds clip for each?"
    "marketwok... what can we do to make the whole crowd be moving in the background
     simultaneously so it looks more realistic?"

HOW 30 SECONDS IS BUILT. H3 tops out at 209 frames - 8.7s - before the kernel OOMs at
43 GB. So each clip here is FOUR generations chained: the last frame of segment N is
extracted and becomes the input image of segment N+1. Four segments is 34.8s, and because
segment N+1 opens on a frame segment N already ended on, that duplicate frame is dropped
at the join and the cut is invisible.

Each segment gets its OWN beat rather than a repeat of the same action, so a 30s clip is a
small piece of structure instead of one gesture stretched thin.

WHAT DROVE THE market_wok REWRITE, which is the note the whole batch is built on:

    H3 ANIMATES WHAT THE ACTION CLAUSE NAMES, AND NOTHING ELSE.

The crowd behind the cook stood still because no sentence ever pointed at it - every word
of that prompt was about the wok. And the keyframe made it worse: `shallow depth of field`
rendered the crowd as a soft mass, and a soft mass has no individuals in it to move. So
every shot below that has a background now states DEEP FOCUS in the keyframe and gives the
background its own motion clause, with people moving in different directions at once,
because a crowd all drifting one way reads as a texture rather than as people.

The style clause is repeated into every segment's video prompt. Batch two established that
a style survives motion when the video prompt defends it, and a chain gives drift four
chances instead of one.
"""
import argparse
import io
import os
import re
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
COMFY = os.path.expanduser("~/ComfyUI")
OUT = os.path.expanduser("~/shared/LONG-H3")

NEG = ("blurry, low quality, watermark, text, signature, deformed, extra limbs, "
       "extra fingers, nudity, nsfw")

SEG = 209               # 8.7s, the measured ceiling
WIDE = (1216, 832)
TALL = (896, 1216)

# id -> (size, style, keyframe, [(action, sound) x4])
SHOTS = {
    # The crowd note, applied: deep focus, and the background gets its own clause in
    # every single beat.
    "market_wok": (WIDE,
     "photoreal cinematic film still, 35mm, deep focus, everything sharp from the wok to "
     "the far end of the market, high detail, colour photograph, filmic grade",
     "a night street food market, a cook side-on over a huge steel wok on a roaring gas "
     "burner in the foreground, and behind him a long lane of other lit stalls with dozens "
     "of individual customers standing, walking and eating, hanging bulbs overhead, "
     "everyone in the background clearly resolved and sharply in focus",
     [("the cook drops his weight and heaves the whole wok up and around and the noodles "
       "arc up in a fireball, while behind him the entire market is moving at once - "
       "customers walking left to right along the lane, a couple at the next stall turning "
       "to each other, a vendor leaning over to hand a bowl across his counter, a man "
       "crossing right to left in the far distance",
       "a roaring gas burner, a whoomph of flame, steel scraping, a dense crowd of "
       "overlapping voices, footsteps, distant clattering woks"),
      ("the cook tips the wok and pours the noodles out into a bowl on the counter, while "
       "behind him the crowd keeps flowing both ways down the lane, one group stopping at "
       "a stall and another walking on past them",
       "noodles hitting a bowl, a ladle scraping steel, a busy crowd talking, a scooter "
       "passing somewhere behind"),
      ("a waiting customer steps up to the counter and takes the bowl, and behind them the "
       "lane stays busy, people passing in both directions and a vendor pulling down a "
       "hanging bag of produce",
       "a bowl set down on wood, coins, overlapping voices, a crowd in a covered lane"),
      ("the cook turns back to the burner and throws a fresh handful into the wok and it "
       "flares, while the market behind him carries on moving in every direction",
       "a handful hitting hot steel, a hard sizzle, a flare of gas, a crowd, a distant "
       "radio")]),

    "tiltshift": (WIDE,
     "tilt-shift miniature effect, shallow band of focus across the middle, oversaturated "
     "colour, shot from high above, everything looks like a toy model",
     "a busy container harbour seen from high above with ships, gantry cranes, stacked "
     "containers and trucks on the quay roads, tilt-shift miniature look, bright midday",
     [("a container ship moves slowly across the harbour water from left to right while "
       "trucks run along the quay roads below and a gantry crane arm swings across",
       "a distant harbour, muffled machinery, gulls, a low ship horn"),
      ("a gantry crane lowers a container down onto a waiting truck and the truck pulls "
       "away along the quay, other traffic moving on the roads throughout",
       "a crane motor winding down, a heavy container landing, a truck engine, gulls"),
      ("a small tug crosses the water towards the ship, throwing a wake, while the stacks "
       "of containers below are worked by moving cranes",
       "a tug engine chugging, water washing, distant machinery, a horn"),
      ("the ship reaches the far side of the harbour and the quay traffic thins out as the "
       "cranes come to rest",
       "engines receding, a last horn, gulls, water lapping")]),

    "watercolour": (TALL,
     "loose watercolour painting on rough cotton paper, visible pigment blooms and hard "
     "edges, white paper showing through, wet washes",
     "a rain-wet city street painted in loose watercolour, a figure with a red umbrella "
     "standing in the middle distance, washes of grey and ochre, cars and shopfronts "
     "suggested in wet strokes",
     # every beat is a committed event - the last watercolour test kept its look and did
     # nothing, because it was written as a gentle continuous drift
     [("the figure with the red umbrella turns and walks away down the street and the wet "
       "grey wash floods outward across the paper behind them",
       "steady rain, footsteps splashing, a quiet street"),
      ("a bus pushes through the frame from left to right in one heavy wet stroke and "
       "throws a sheet of water up across the pavement",
       "a bus engine passing, a heavy splash of water, rain"),
      ("the rain hits harder and dark blooms of pigment burst across the whole street, the "
       "colours running down the paper",
       "rain intensifying hard, water running in gutters, thunder far off"),
      ("the red umbrella closes and the figure steps into a doorway, and the washes drain "
       "away to leave bare white paper around them",
       "an umbrella snapping shut, rain easing, a door")]),

    "bricks": (WIDE,
     "toy scene built from interlocking plastic construction bricks, glossy moulded studs, "
     "macro photography, deep focus, bright even light",
     "a small city street built entirely from interlocking plastic bricks, a brick car in "
     "the road, a brick bus behind it, blocky brick figures standing along both pavements, "
     "brick shopfronts, everything sharply in focus",
     [("the brick car drives across the street from left to right while the blocky figures "
       "on both pavements turn and walk in different directions",
       "hard plastic clattering, a toy motor hum, small plastic footsteps"),
      ("a brick tower at the end of the street topples sideways and bricks scatter across "
       "the road while the figures scatter away from it",
       "a rattling collapse of loose plastic bricks, clattering"),
      ("a brick fire engine drives in from the right and stops beside the fallen bricks and "
       "brick figures climb down off it",
       "a toy siren, plastic clicking, a motor hum"),
      ("the figures stack the scattered bricks back up into the tower piece by piece until "
       "it stands again",
       "plastic bricks clicking together one at a time, a final snap")]),

    "pixel": (WIDE,
     "16-bit pixel art, chunky visible square pixels, limited 32 colour palette, hard "
     "dithering, no antialiasing, side-scrolling game",
     "a pixel art side-scrolling scene of a small knight standing on a grass platform, "
     "pixel clouds, floating platforms, a pixel castle in the background",
     [("the pixel knight runs to the right along the platform and jumps a gap, landing on "
       "the next platform",
       "chiptune jump and footstep blips, a simple 8-bit melody"),
      ("a small pixel slime hops in from the right and the knight swings his sword and the "
       "slime bursts into pixels",
       "a chiptune sword swipe, a defeat blip, the melody continuing"),
      ("the knight climbs a ladder up to a higher platform and a row of pixel coins appears "
       "above him",
       "a climbing blip loop, coin pickup chimes, 8-bit music"),
      ("the knight runs right across the last platforms and reaches the castle gate, which "
       "opens",
       "running blips, a heavy gate chime, a triumphant 8-bit fanfare")]),

    "blueprint": (WIDE,
     "white line technical blueprint drawing on deep cyan paper, precise thin white "
     "linework, dimension arrows and annotations, absolutely flat, no shading, no "
     "photographic texture, not a photograph, engineering drawing only",
     "an exploded technical blueprint of a mechanical wristwatch movement, every gear, "
     "spring and plate drawn in thin white line on deep cyan blueprint paper, dimension "
     "arrows and callout numbers, flat engineering drawing",
     # this is the one style that drifted to photoreal, so the defence clause is blunt and
     # repeated hard in every segment
     [("the exploded parts drift together and the mainplate and barrel seat into position, "
       "drawn entirely in flat white line on blue",
       "fine mechanical ticking, tiny metal parts seating"),
      ("the gear train assembles tooth by tooth onto the plate and dimension arrows draw "
       "themselves in beside each wheel, still flat white line on blue",
       "a wound spring, delicate clicking, a pen scratching"),
      ("the balance wheel drops into place and begins to oscillate back and forth, the "
       "whole drawing still flat white line on blue paper",
       "a steady escapement ticking, a fine metallic beat"),
      ("the drawing rotates flat in the plane of the page and the completed movement turns "
       "with all its wheels running, flat white line on blue throughout",
       "steady mechanical ticking, a soft mechanical hum")]),

    "drumkit": (TALL,
     "photoreal cinematic film still, 35mm, warm rehearsal room light, deep focus, "
     "high detail, colour photograph",
     "a drummer seated at a full drum kit in a small rehearsal room, sticks raised over "
     "the snare, close three-quarter view, amps and a window behind, everything sharp",
     [("the drummer plays a steady mid-tempo rock beat, sticks striking the snare and "
       "hi-hat in time and the kick pedal working",
       "a steady mid-tempo rock drum beat, kick snare and hi-hat locked in time, a live "
       "room"),
      ("the drummer opens the hi-hat and rides it harder, driving the same steady beat "
       "louder",
       "the same steady rock beat continuing at the same tempo, an open hi-hat sizzling"),
      ("the drummer rolls around the toms in a fill and comes back onto the snare without "
       "losing the beat",
       "a tom fill around the kit, then back into the same steady rock beat"),
      ("the drummer hits a crash cymbal and plays the beat out, then stops dead on a final "
       "snare hit",
       "a crash cymbal, the steady beat continuing, one final snare hit and silence")]),
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


def build(sid, segs, w, h):
    """Concat the segments. Segment N+1 opens on the frame segment N closed on, so that
    duplicate is dropped or the join stutters."""
    parts = []
    for i, p in enumerate(segs):
        q = "/tmp/_ext_%s_%d.mp4" % (sid, i)
        vf = "scale=%d:%d" % (w, h)
        if i:                                   # drop the duplicated opening frame
            vf = "select=gte(n\\,1),setpts=PTS-STARTPTS," + vf
        sh("ffmpeg", "-y", "-v", "error", "-i", p,
           "-vf", vf, "-af", "afade=t=in:st=0:d=0.12",
           "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
           "-c:a", "aac", "-b:a", "160k", "-ar", "48000", q)
        if os.path.exists(q):
            parts.append(q)
    lst = "/tmp/_ext_%s.txt" % sid
    with io.open(lst, "w") as f:
        for q in parts:
            f.write("file '%s'\n" % q)
    dst = os.path.join(OUT, "%s_30s.mp4" % sid)
    sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
       "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
       "-c:a", "aac", "-b:a", "160k", "-ar", "48000", dst)
    return dst if os.path.exists(dst) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--segments", type=int, default=4)
    ap.add_argument("--anchor", action="store_true",
                    help="re-impose the original keyframe on each chain frame. Without "
                         "this the subject drifts - market_wok changed cook, shirt, stall "
                         "and food over 34.8s, because each hop re-interprets one frame "
                         "and the error compounds.")
    a = ap.parse_args()
    want = [x for x in a.only.split(",") if x] or list(SHOTS)
    os.makedirs(OUT, exist_ok=True)

    for sid in want:
        if sid not in SHOTS:
            print("no shot %r" % sid)
            continue
        (w, h), style, scene, beats = SHOTS[sid]
        print("== %s  %d x 8.7s" % (sid, a.segments), flush=True)
        kf, err = run("01_qwen_t2i_turbo.json", [
            ("10.inputs.text", "%s. %s" % (scene, style)), ("11.inputs.text", NEG),
            ("12.inputs.width", w), ("12.inputs.height", h), ("13.inputs.seed", 5),
            ("15.inputs.filename_prefix", "claude-generated/long/%s" % sid)])
        if not kf:
            print("   keyframe FAILED %s" % err)
            continue
        sh("cp", kf, os.path.join(OUT, "%s_key.png" % sid))

        segs, cur = [], kf
        for i in range(a.segments):
            action, sound = beats[i % len(beats)]
            staged = "long_%s_%d.png" % (sid, i)
            sh("cp", cur, os.path.join(COMFY, "input", staged))
            print("   seg %d  %s" % (i + 1, action[:52]), flush=True)
            clip, err = run("60_minimax_h3_i2v.json", [
                ("8.inputs.image", staged),
                ("20.inputs.prompt",
                 "%s. The whole shot stays in this style throughout: %s. Sound: %s."
                 % (action, style, sound)),
                ("20.inputs.width", w), ("20.inputs.height", h),
                ("20.inputs.length", SEG), ("33.inputs.noise_seed", 5 + i),
                ("51.inputs.filename_prefix",
                 "claude-generated/long/%s_seg%d" % (sid, i))])
            if not clip:
                print("      seg FAILED %s" % err)
                break
            segs.append(clip)
            # the chain: last frame out becomes the next segment's input
            nxt = "/tmp/_last_%s_%d.png" % (sid, i)
            sh("ffmpeg", "-y", "-v", "error", "-sseof", "-0.2", "-i", clip,
               "-update", "1", "-frames:v", "1", nxt)
            if not os.path.exists(nxt):
                print("      last-frame extract FAILED")
                break
            if a.anchor and i + 1 < a.segments:
                # THE ANCHOR. The chain frame carries the new pose but has drifted off the
                # subject, so it goes back through the two-reference edit with the ORIGINAL
                # keyframe beside it. Reference one says who this is, reference two says
                # where the action has got to.
                sh("cp", os.path.join(OUT, "%s_key.png" % sid),
                   os.path.join(COMFY, "input", "anch_%s_key.png" % sid))
                sh("cp", nxt, os.path.join(COMFY, "input", "anch_%s_%d.png" % (sid, i)))
                fixed, aerr = run("14_qwen_edit_ref.json", [
                    ("8.inputs.image", "anch_%s_key.png" % sid),
                    ("9.inputs.image", "anch_%s_%d.png" % (sid, i)),
                    ("10.inputs.prompt",
                     "Redraw the second image so that it keeps its exact composition, "
                     "poses and action, but restores the subject, wardrobe, colours and "
                     "lighting of the first image. Same place, same people, same clothing "
                     "as the first image. %s. %s" % (scene, style)),
                    ("11.inputs.prompt", NEG),
                    ("20.inputs.width", w), ("20.inputs.height", h),
                    ("13.inputs.seed", 5),
                    ("15.inputs.filename_prefix",
                     "claude-generated/long/%s_anchor%d" % (sid, i))])
                if fixed:
                    nxt = fixed
                    print("      anchored", flush=True)
                else:
                    print("      anchor FAILED %s" % aerr)
            cur = nxt
        if len(segs) < 2:
            print("   only %d segment(s) - nothing to join" % len(segs))
            continue
        dst = build(sid, segs, w, h)
        if dst:
            d = sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "csv=p=0", dst).stdout.strip()
            print("   -> %s  %ss" % (dst, d))
        else:
            print("   join FAILED")


if __name__ == "__main__":
    main()
