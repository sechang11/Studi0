#!/usr/bin/env python3
"""studio/_tools/ltx_film.py - the new house template. LTX-2.5, one pass, real cuts.

WHAT THIS REPLACES AND WHY. Everything built before tonight worked around a model that
could only hold about eight seconds:

    chained H3          four generations, a frame handed between them - the cook became a
                        different man at a different stall
    anchored chain      held a face, never held a place
    Wan context windows one unbroken pass and rock-solid continuity, but Wan has no audio
    pinned-ends H3      kept the audio, still segmented, still wobbled

LTX-2.5 makes all of it unnecessary. Measured on this box: 30.04 s in a SINGLE sampling
pass, 1280x704, 24 fps, joint stereo audio, 165 s to generate. There is no chain, so there
is nothing to drift. It is also about four times faster than H3 was for worse output.

    5 s -> 37 s      10 s -> 47 s      20 s -> 94 s      30 s -> 165 s

AND IT CUTS. LTX-2.5 does native multishot: several framings joined by real hard cuts
inside one generation, holding the character across them. That is the thing this project
has never had. A wide establishing, a medium with the flame, a close on the pour - one
render, one continuous soundtrack.

THE PROMPT FORMAT IS LOAD-BEARING, and it is not the obvious one. Writing "Shot 1 ... CUT
TO Shot 2 ..." produced no cuts at all - fifteen seconds of one continuous take. The
official guide is explicit that a multishot prompt must be ONE CHRONOLOGICAL PARAGRAPH
with the transition named in prose, and that is what worked:

    * name the transition                "A hard cut transitions to..."
    * re-establish scale and angle       "...a medium side-on shot of..."
    * RE-IDENTIFY the character          "...the same cook in the black shirt..."
      (an unidentified character does not survive a cut)
    * state audio continuity             "...continue unbroken across both cuts."
    * two to four shots per generation, each with one clear job

`beats()` below assembles exactly that shape from structured beats, so the format cannot
drift back into slug lines the next time someone writes a shot.

The keyframe still comes from this project's own art direction - Qwen for photoreal,
animagine plus a character sheet for anime - because that is where the look is decided and
LTX only has to move it.
"""
import argparse
import io
import os
import re
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
COMFY = os.path.expanduser("~/ComfyUI")
OUT = os.path.expanduser("~/shared/LTX-FILM")

PHOTO = ("photoreal cinematic film still, 35mm, deep focus, sharp throughout, high "
         "detail, colour photograph, filmic grade")
ANIME = ("masterpiece, best quality, anime key visual, 2D cel shaded anime, hand drawn "
         "animation, clean line art, flat cel shading, detailed background art")
NEG_PHOTO = ("blurry, low quality, watermark, text, signature, cgi, 3d render, deformed, "
             "extra limbs, extra fingers, nudity, nsfw")
NEG_ANIME = ("photorealistic, photograph, 3d render, cgi, realistic skin, blurry, lowres, "
             "bad anatomy, bad hands, extra limbs, watermark, signature, text, "
             "multiple views, nudity, nsfw")

# LTX's own negative, kept because it is tuned for this model
LTX_NEG = "pc game, console game, video game, cartoon, childish, ugly"

SHOTS = ("wide establishing shot", "medium shot", "close-up", "tight close-up",
         "over-the-shoulder shot", "low-angle shot", "overhead view")


def beats(opening, cuts, audio, audio_continues=True):
    """Assemble ONE chronological paragraph in the shape LTX-2.5 actually cuts on.

    opening : the first shot, written out in full prose.
    cuts    : [(transition, framing, who, what)] - `who` MUST re-identify the character,
              because an unnamed character does not survive a cut.
    """
    p = [opening.rstrip(". ") + "."]
    for i, (trans, framing, who, what) in enumerate(cuts):
        p.append("%s %s of %s, %s." % (trans, framing, who, what.rstrip(". ")))
    tail = "Sound: %s." % audio.rstrip(". ")
    if cuts and audio_continues:
        n = "both cuts" if len(cuts) == 2 else ("the cut" if len(cuts) == 1
                                                else "all %d cuts" % len(cuts))
        tail = ("Sound: %s, continuing unbroken across %s."
                % (audio.rstrip(". "), n))
    p.append(tail)
    return " ".join(p)


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
            (r.stderr or r.stdout or "")[-240:])


def keyframe(sid, engine, scene, w, h, seed=12, sheet=None, tags="", ipa=0.6):
    """Art direction stays where this project already does it well.

    ipa is the IPAdapter weight, and it needs lowering for anything that is not a portrait.
    PLUS FACE biases the COMPOSITION as well as the identity: at 0.6 a reference sheet
    turned "a wide shot on a ruined bridge at night facing a huge wolf-beast" into a close
    portrait on a blank background, with no bridge, no night and no wolf. Around 0.3 the
    scene description wins and the face still holds.
    """
    if engine == "anime":
        return run("22_anime_kf_ipadapter.json", [
            ("2.inputs.image", sheet or "sheet_liwen.png"),
            ("4.inputs.weight", ipa if sheet else 0.0),
            ("5.inputs.text", "%s, %s, %s" % (tags, scene, ANIME)),
            ("6.inputs.text", NEG_ANIME),
            ("7.inputs.width", w), ("7.inputs.height", h),
            ("8.inputs.seed", seed),
            ("10.inputs.width", w), ("10.inputs.height", h),
            ("11.inputs.filename_prefix", "claude-generated/ltxfilm/%s_key" % sid)])
    return run("01_qwen_t2i_turbo.json", [
        ("10.inputs.text", "%s. %s" % (scene, PHOTO)),
        ("11.inputs.text", NEG_PHOTO),
        ("12.inputs.width", w), ("12.inputs.height", h), ("13.inputs.seed", seed),
        ("15.inputs.filename_prefix", "claude-generated/ltxfilm/%s_key" % sid)])


def render(sid, prompt, seconds, megapixels=0.9, seed=11, fps=24, aspect=None,
           start=None, neg=LTX_NEG, enhance=True):
    """enhance runs the prompt through the gemma enhancer before sampling.

    It was ON by accident all through the first night - `-s ...=false` set a truthy STRING
    - and once the runner could actually pass a boolean, the comparison was worth making
    rather than assuming. On a dialogue scene the enhanced version speaks in four bursts
    spread across the shot; the exact-script version delivers the same lines with long dead
    air between them. So it is kept ON by default, on evidence, and turned off when a shot
    needs the prompt honoured literally.
    """
    sets = [("sg1_376.inputs.value", prompt),
            ("sg1_383.inputs.value", "true" if enhance else "false"),
            ("sg1_373.inputs.text", neg),
            ("sg1_362.inputs.value", seconds),
            ("sg1_361.inputs.value", fps),
            ("403.inputs.megapixels", megapixels),
            ("sg1_339.inputs.noise_seed", seed),
            ("75.inputs.filename_prefix", "claude-generated/ltxfilm/%s" % sid)]
    if aspect:
        sets.append(("403.inputs.aspect_ratio", aspect))
    if start:
        sets.append(("395.inputs.image", start))
    return run("70_ltx25_i2v.json", sets)


# MEASURED ENVELOPE on this 5090 with 60 GB of system RAM. Past it the ComfyUI PROCESS IS
# KILLED - there is no exception to catch, the socket simply closes mid-run, which is why a
# whole batch comes back as identical "Connection refused" lines.
#
# A SINGLE PRODUCT DOES NOT PREDICT THE CLIFF, which is worth stating because that was the
# first guess and it was wrong. (4*MP)*frames scores 2596 for 0.9MP/30s, which runs, and
# 2599 for 1.8MP/15s, which dies. Higher base resolution costs more than linearly - the
# refine pass runs at 2x and the tiled decode carries its own spatial overhead - so the
# guard below is a table of points that were actually measured, not a curve fitted to them.
#
#   ran     0.9MP/30s   1.2MP/20s   1.5MP/12s   2.0MP/8s
#   killed  1.5MP/20s   1.8MP/15s   1.5MP/25s   2.5MP/8s
SAFE = [(1.0, 30), (1.2, 20), (1.5, 12), (2.0, 8)]      # (max megapixels, max seconds)


def too_big(megapixels, seconds, fps=24):
    for mp, secs in SAFE:
        if megapixels <= mp:
            return seconds > secs
    return True                                          # past 2.0 MP nothing survived


def comfy_up():
    import urllib.request
    try:
        urllib.request.urlopen("http://127.0.0.1:8188/system_stats", timeout=5).read()
        return True
    except Exception:
        return False


def ensure_comfy(tries=3):
    """A killed ComfyUI must be brought back or every remaining scene fails identically."""
    import time
    for _ in range(tries):
        if comfy_up():
            return True
        print("   ComfyUI is down - restarting", flush=True)
        sh("bash", os.path.join(ROOT, "scripts", "restart-comfy.sh"))
        for _ in range(60):
            if comfy_up():
                time.sleep(3)
                return True
            time.sleep(5)
    return False


def probe(path):
    r = sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-show_entries", "stream=width,height", "-of", "csv=p=0", path)
    return " ".join((r.stdout or "").split())


def main():
    ap = argparse.ArgumentParser(description="render a film spec through LTX-2.5")
    ap.add_argument("--spec", required=True, help="python file defining FILM")
    ap.add_argument("--only", default="")
    ap.add_argument("--keys-only", action="store_true")
    a = ap.parse_args()
    ns = {"beats": beats, "PHOTO": PHOTO, "ANIME": ANIME}
    exec(compile(io.open(a.spec, encoding="utf-8").read(), a.spec, "exec"), ns)
    film = ns["FILM"]
    want = [x for x in a.only.split(",") if x]
    os.makedirs(OUT, exist_ok=True)

    made = []
    for s in film["scenes"]:
        sid = s["id"]
        if want and sid not in want:
            continue
        w, h = s.get("size", (1216, 832))
        print("== %-14s %ss  %s" % (sid, s["seconds"], s.get("note", "")), flush=True)
        staged = "ltxf_%s.png" % sid
        if s.get("image"):
            # an already-approved keyframe. Art direction that has been LOOKED AT is worth
            # more than a fresh roll of the dice.
            src = os.path.expanduser(s["image"])
            if not os.path.exists(src):
                print("   image missing: %s" % src)
                continue
            sh("cp", src, os.path.join(COMFY, "input", staged))
            sh("cp", src, os.path.join(OUT, "%s_key.png" % sid))
        else:
            kf, err = keyframe(sid, s.get("engine", "photo"), s["keyframe"], w, h,
                               seed=s.get("kseed", 12), sheet=s.get("sheet"),
                               tags=s.get("tags", ""), ipa=s.get("ipa", 0.6))
            if not kf:
                print("   keyframe FAILED %s" % err)
                continue
            sh("cp", kf, os.path.join(OUT, "%s_key.png" % sid))
            sh("cp", kf, os.path.join(COMFY, "input", staged))
        if a.keys_only:
            print("   key ok")
            continue
        if not ensure_comfy():
            print("   ComfyUI will not come back up - stopping")
            break
        if too_big(s.get("megapixels", 0.9), s["seconds"]):
            print("   REFUSED: %.1f MP x %ss is outside the measured envelope %s - past "
                  "it the ComfyUI process is killed rather than raising"
                  % (s.get("megapixels", 0.9), s["seconds"], SAFE))
            continue
        clip, err = render(sid, s["prompt"], s["seconds"],
                           megapixels=s.get("megapixels", 0.9),
                           seed=s.get("seed", 11), aspect=s.get("aspect"),
                           start=staged, neg=s.get("neg", LTX_NEG),
                           enhance=s.get("enhance", True))
        if not clip:
            print("   clip FAILED %s" % err)
            continue
        dst = os.path.join(OUT, "%s.mp4" % sid)
        sh("cp", clip, dst)
        made.append(dst)
        print("   -> %s  %s" % (os.path.basename(dst), probe(dst)))

    if len(made) > 1 and film.get("assemble"):
        lst = "/tmp/_ltxfilm.txt"
        with io.open(lst, "w") as f:
            for p in made:
                f.write("file '%s'\n" % p)
        dst = os.path.join(OUT, "%s.mp4" % film["assemble"])
        sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
           "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", dst)
        print("\nFILM: %s  %s" % (dst, probe(dst)))


if __name__ == "__main__":
    main()
