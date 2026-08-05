#!/usr/bin/env python3
"""demo_films.py - author, check, render and LOOK AT the demo films.

    python3 studio/_tools/demo_films.py --list
    python3 studio/_tools/demo_films.py --write-reel      # emit the six style panels
    python3 studio/_tools/demo_films.py --check           # compile + per-beat motion table
    python3 studio/_tools/demo_films.py --render          # compile + scripts/short.py
    python3 studio/_tools/demo_films.py --verify          # every stage, artifact by artifact
    python3 studio/_tools/demo_films.py --strips          # frame strips to look at
    python3 studio/_tools/demo_films.py --reel            # concat the style panels
    python3 studio/_tools/demo_films.py --collect         # copy the films where the app serves them
    python3 studio/_tools/demo_films.py --index           # index.json for a gallery route

Scope: it only ever touches studio/movies/demo_*.movie, their compiled .json, and
studio/samples/demo_films/. It never writes a card, a workflow or a library file.

THIS TOOL DOES NOTHING UNTIL YOU ASK IT TO. Seventeen of the sixty tools in this directory
have no argparse and run their entire job when handed any argument at all, `--help`
included - one of them overwrote ten style cards during a health audit that was only
trying to read their usage lines. Every action here is behind an explicit flag, nothing
runs at import, and `--help` prints and exits.

WHY --check EXISTS, AND WHY IT RUNS BEFORE THE GPU DOES

The standing defect this demo set was written against: 21 of the 29 beats across the three
earlier films resolve to a motion HOLD, so the video model is asked to keep the picture
still and every frame of the beat is the keyframe. It is not a renderer bug. It is that
the shot lines describe COMPOSITIONS - "two figures standing apart on the terrace" - and
compose.derive_motion() needs a MOVER, an ACTION VERB and a PATH before it can build the
one string LTX reads.

compile.py prints the ratio at the end of a compile. That is the right number and it comes
too late and without names. --check compiles every demo film, reads `motion` and
`motion_src` off each beat of the emitted .json, and prints one line per beat saying where
that beat's motion came from and what it says - so a shot line can be rewritten for free,
before the clip pass, which costs about 8x the keyframe.

A film is reported PASS when no beat falls to `hold` UNLESS the author asked for one by
naming a stillness card. An unnamed hold is a defect; a named hold is a decision.
"""
import argparse
import collections
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
MOVIES = os.path.join(STUDIO, "movies")
SAMPLES = os.path.join(STUDIO, "samples", "demo_films")
COMFY = os.environ.get("COMFY_ROOT") or os.path.expanduser("~/ComfyUI")
SHORTS = os.path.join(COMFY, "output", "claude-generated", "12-shorts")

# Motion cards whose whole content is stillness. Naming one of these is an authoring
# DECISION and is not counted against a film; falling to `hold` without naming one is the
# defect this tool exists to catch. Read off the cards' own family/mover field rather than
# hardcoded, so a new stillness card is picked up without editing this list.
def stillness_ids():
    d = os.path.join(STUDIO, "motions")
    out = set()
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            c = json.load(open(os.path.join(d, fn), encoding="utf-8"))
        except Exception:
            continue
        fam = str(c.get("mover") or c.get("family") or "").lower()
        if fam in ("stillness", "none"):
            out.add(c.get("id") or fn[:-5])
    return out


# Every keyscale ComfyUI's TextEncodeAceStepAudio1.5 will accept, built the same way the
# node builds it (comfy_extras/nodes_ace.py): 17 roots x 2 qualities.
#
# WHY THIS IS CHECKED HERE. studio/cues/*.json carry a `key` that scripts/short.py writes
# straight into that combo input. Three of the 22 cues spell it in words - "B flat minor",
# "B flat major", "E flat minor" - and the node only knows "Bb minor". A film that uses one
# fails prompt validation and short.py aborts, and it aborts in the MUSIC stage, which runs
# AFTER every keyframe and every clip is on disk. demo_landscape.movie lost a completed
# 12-beat render that way. Catching it costs a set lookup.
ACE_KEYSCALES = {"%s %s" % (root, q) for q in ("major", "minor")
                 for root in ("C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb",
                              "G", "G#", "Ab", "A", "A#", "Bb", "B")}


def bad_cue_keys(film):
    """Cues this film schedules whose key the audio node will refuse.

    The compiled film carries the key on the music entry itself (compile.py copies it off
    the cue card), so the key is read from there and the cue NAME is recovered from the
    `prefix`, which is <cue id>_<NN>.
    """
    bad = []
    for m in film.get("music") or []:
        k = m.get("key")
        if k and k not in ACE_KEYSCALES:
            name = re.sub(r"_\d+$", "", str(m.get("prefix") or m.get("id") or "?"))
            bad.append((name, k))
    return bad


# ---------------------------------------------------------------------------
# the six style panels
# ---------------------------------------------------------------------------
#
# A .movie file can only carry ONE style: `style` is a movie-level variable because it
# picks the engine, and the two engines want opposite prompt formats, so a film cannot
# change style between chapters. A style-range demo therefore CANNOT be one film. It is six
# two-and-a-bit-beat films with byte-identical content, cut together afterwards by --reel.
#
# The three things that make it a controlled comparison rather than six pretty pictures:
#
#   1. SAME seed_root, SAME chapter id, SAME scene ids, SAME beat order. compile.py derives
#      each beat's seed from sha256(root|chapter|scene|index), never from position, so all
#      six panels render beat 1 on the same seed, beat 2 on the same seed, beat 3 on the
#      same seed. The only difference between the panels is the style layer.
#   2. NOBODY IS IN THEM. A reference sheet imports its style as hard as its identity - the
#      qwen edit path fed an anime sheet returned flat cel illustration in 4 of 4 places
#      even with "waist-up photograph" in the prompt. Put a cast member in a style demo and
#      the sheet, not the style card, decides what you are looking at.
#   3. Three of the six route to `anime` (animagine-xl-4.0, danbooru tags) and three to
#      `qwen` (Qwen-Image 2512, prose). All six are status `ready` and compose-class `safe`
#      in studio/styles/, i.e. none of them is one of the cards measured to rebuild the
#      scene or to do nothing at all.
#
# Content: an element mover, a person-shaped mover with no character card behind it, and an
# element insert - so all three beats derive and none of them holds.
REEL_STYLES = [
    ("cel_anime_90s", "anime", "the house style - flat cel, hard shadow terminator"),
    ("ukiyo_e",       "anime", "woodblock: keyline, flat colour, no cast shadow at all"),
    ("watercolour",   "anime", "wet edges and paper tooth - a MEDIUM, not a subject"),
    ("film_35mm",     "qwen",  "photographic, the other engine entirely"),
    ("pixar_3d",      "qwen",  "3D render - qwen can be moved off photography by a style"),
    ("noir_comic",    "qwen",  "high-contrast ink on the prose engine"),
]

REEL_BODY = """
MOVIE demo_style_{n:02d}
  title: DEMO STYLE {n:02d} {up}
  logline: One road, one traveller, one afternoon - rendered {desc}.
  canvas: 1920x1080
  fps: 24
  engine: {engine}
  style: {style}
  seed_root: demo-style-reel
  clip_secs: 6
  tags: cinematic

CHAPTER the_road
  look: golden
  place: a wide upland valley of terraced fields, a pale dirt road, dry stone walls, tall grass
  pace: normal
  cue: quiet_dawn

  SCENE the_valley
    transition: fade_black
    camera: static
    shot: establish | cloud shadow sliding across a wide valley of terraced fields, a pale dirt road winding through them, no humans, extreme wide shot

  SCENE the_traveller
    transition: cut
    camera: static
    shot: master | a lone traveller walking forward along a dirt road, tall grass on both sides, a bundle on one shoulder, full body

  // The place is overridden to a CLOSE one here. A chapter-level place card describing a
  // whole valley on an `insert` makes compose report place_vs_shot - "your place and your
  // shot ask for different pictures: scenery against close-up" - and whichever comes
  // earlier in the prompt wins, which is the valley, which is not what an insert is for.
  SCENE the_leaves
    transition: cut
    place: a pale dirt road surface, loose grit, dry grass at the verge
    camera: static
    shot: insert | dry leaves blowing across the road surface, no humans, close-up
"""

REEL_HEADER = """// DEMO 4 of 5, PANEL {n} OF {total} - THE STYLE RANGE REEL.
//
// This file is one panel of a controlled style comparison and is NOT meant to be watched
// on its own. All {total} panels carry byte-identical content, the same seed_root and the
// same scene ids, so compile.py hands every panel the same three seeds. The only variable
// between them is this line:
//
//     style: {style}        engine: {engine}
//     {desc}
//
// WHY IT IS {total} FILES AND NOT ONE. `style` is a movie-level variable in compile.py
// because it is what DERIVES THE ENGINE, and the two engines want opposite prompt formats
// - danbooru tags for animagine, prose for Qwen-Image. A film cannot change engine
// mid-reel without changing every face in it, so the format refuses to let style vary
// below the movie. A style-range demo is therefore N films and a concatenation, and
// pretending otherwise would mean shipping a knob that quietly does nothing.
//
// NOBODY IS IN IT, deliberately. A reference sheet imports its style as hard as its
// identity - measured, the qwen edit path fed an anime sheet returned flat cel
// illustration in 4 of 4 places even when the prompt asked for a photograph. A cast member
// in a style demo would mean the sheet, not the style card, decided what you are looking
// at.
//
// All three shot lines are ACTIONS - cloud shadow SLIDING across a valley, a traveller
// WALKING along a road, leaves BLOWING across the surface - so all three derive a motion
// and none of them falls to a hold. That is also what makes the panels comparable in
// MOTION and not only in colour.
//
// Written by studio/_tools/demo_films.py --write-reel. Edit the body there, not here, or
// the panels will drift apart and stop being a comparison.
"""


def write_reel():
    os.makedirs(MOVIES, exist_ok=True)
    written = []
    for i, (style, engine, desc) in enumerate(REEL_STYLES, 1):
        head = REEL_HEADER.format(n=i, total=len(REEL_STYLES), style=style,
                                  engine=engine, desc=desc)
        body = REEL_BODY.format(n=i, up=style.upper().replace("_", " "),
                                style=style, engine=engine, desc=desc)
        p = os.path.join(MOVIES, "demo_style_%02d_%s.movie" % (i, style))
        with open(p, "w", encoding="utf-8") as f:
            f.write(head + body)
        written.append(p)
        print("wrote %s" % os.path.relpath(p, ROOT))
    return written


# ---------------------------------------------------------------------------
# discovery + compile
# ---------------------------------------------------------------------------

def films(only=None):
    """Every demo .movie, in a deliberate order: the three set pieces first, then the
    style panels, which are a reel and not films."""
    if not os.path.isdir(MOVIES):
        return []
    named = sorted(x for x in os.listdir(MOVIES)
                   if x.startswith("demo_") and x.endswith(".movie"))
    lead = [x for x in named if not x.startswith("demo_style_")]
    panels = [x for x in named if x.startswith("demo_style_")]
    out = [os.path.join(MOVIES, x) for x in lead + panels]
    if only:
        out = [p for p in out if only in os.path.basename(p)]
    return out


def run(cmd, cwd=ROOT, capture=True):
    r = subprocess.run(cmd, cwd=cwd, text=True,
                       stdout=subprocess.PIPE if capture else None,
                       stderr=subprocess.STDOUT if capture else None)
    return r.returncode, (r.stdout or "")


def compile_one(path):
    rc, out = run([sys.executable, os.path.join(STUDIO, "compile.py"), path])
    return rc, out, os.path.splitext(path)[0] + ".json"


def slug_of(film_json):
    return json.load(open(film_json, encoding="utf-8"))["title"].lower().replace(" ", "-")


# ---------------------------------------------------------------------------
# --check : the motion table, before a single frame is rendered
# ---------------------------------------------------------------------------

def cmd_check(args):
    still = stillness_ids()
    total = collections.Counter()
    bad_films = []
    for mv in films(args.only):
        rc, out, js = compile_one(mv)
        name = os.path.basename(mv)
        print("\n" + "=" * 78)
        print(name)
        print("=" * 78)
        if rc != 0:
            print("  COMPILE FAILED\n" + out)
            bad_films.append(name)
            continue
        warns = [l for l in out.splitlines() if l.strip().startswith("!")]
        film = json.load(open(js, encoding="utf-8"))
        beats = film["beats"]
        unnamed_hold = []
        print("  %-34s %-7s %-22s %s" % ("beat", "tmpl", "motion source", "the string LTX reads"))
        for b in beats:
            src = b.get("motion_src", "")
            kind = src.split(":", 1)[0]
            mid = src.split(":", 1)[1] if ":" in src else ""
            total[kind] += 1
            flag = " "
            if kind == "hold":
                # A hold is only acceptable when the AUTHOR named a stillness card. When
                # the resolver falls to rung 4 by itself, motion_src is hold:<the reason it
                # found nothing>, not hold:<card id>.
                if mid.strip() in still:
                    flag = "."
                else:
                    flag = "X"
                    unnamed_hold.append(b["id"])
            print("  %s %-32s %-7s %-22s %s"
                  % (flag, b["id"][:32], b.get("template", "")[:7],
                     (kind + (":" + mid.split(":")[0] if kind in ("card", "hold") and mid else ""))[:22],
                     b.get("motion", "")[:60]))
        n = len(beats)
        held = len(unnamed_hold)
        keys = bad_cue_keys(film)
        verdict = "PASS" if held == 0 else "HOLDS %d/%d" % (held, n)
        if held:
            bad_films.append(name)
        if keys:
            verdict += "  +  AUDIO STAGE WILL ABORT"
            bad_films.append(name)
            for cid, k in keys:
                print("  X cue '%s' key %r is not one of the 34 keyscales "
                      "TextEncodeAceStepAudio1.5 accepts - it wants e.g. 'Bb minor'. "
                      "short.py dies here AFTER all keyframes and clips are rendered."
                      % (cid, k))
        print("  ---- %d beats, %s" % (n, verdict))
        if unnamed_hold:
            print("       unnamed holds: " + ", ".join(unnamed_hold))
        for w in warns:
            print("   " + w.strip())
    print("\n" + "=" * 78)
    print("ALL DEMO BEATS: " + ", ".join("%s %d" % (k, v) for k, v in total.most_common()))
    print("films with an UNNAMED hold: " + (", ".join(bad_films) or "none"))
    return 1 if bad_films else 0


# ---------------------------------------------------------------------------
# --render
# ---------------------------------------------------------------------------

def cmd_render(args):
    """Compile then render, one film at a time. Serialised on purpose - there is one GPU
    and two LTX passes in flight would just swap each other out of VRAM."""
    os.makedirs(SAMPLES, exist_ok=True)
    logdir = os.path.join(SAMPLES, "_logs")
    os.makedirs(logdir, exist_ok=True)
    for mv in films(args.only):
        name = os.path.basename(mv)[:-6]
        rc, out, js = compile_one(mv)
        if rc != 0:
            print("COMPILE FAILED %s\n%s" % (name, out))
            continue
        log = os.path.join(logdir, name + ".log")
        print(">>> %s -> %s" % (name, log))
        with open(log, "w", encoding="utf-8") as f:
            f.write(out + "\n" + "=" * 60 + "\n")
            f.flush()
            r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "short.py"), js],
                               cwd=ROOT, text=True, stdout=f, stderr=subprocess.STDOUT)
        print("    exit %d" % r.returncode)
    return 0


# ---------------------------------------------------------------------------
# --verify : did every stage produce a real artifact
# ---------------------------------------------------------------------------

MIN = {"keyframes": 60_000, "clips": 120_000, "voice": 4_000, "music": 20_000,
       "film": 1_000_000}


def ffprobe(path, entries):
    rc, out = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                   "-show_entries", entries, "-of", "default=nw=1", path])
    d = {}
    for line in out.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            d[k] = v
    return d


def cmd_verify(args):
    """Count and MEASURE every artifact each stage was supposed to produce.

    This project has a standing habit of stages that look like they ran: a 0-byte mp4 and a
    36 MB one both make `ls` print a filename. So every check here is a size and, for the
    finished film, a duration and a frame count off ffprobe.
    """
    bad = 0
    for mv in films(args.only):
        js = os.path.splitext(mv)[0] + ".json"
        if not os.path.exists(js):
            print("%-34s NOT COMPILED" % os.path.basename(mv))
            bad += 1
            continue
        film = json.load(open(js, encoding="utf-8"))
        slug = film["title"].lower().replace(" ", "-")
        out = os.path.join(SHORTS, slug)
        beats = film["beats"]
        want_v = sum(1 for b in beats if b.get("line"))
        want_m = len(film.get("music") or [])
        print("\n%s   %s" % (os.path.basename(mv), out))
        rows = [("keyframes", "keyframes", len(beats)),
                ("clips", "clips", len(beats)),
                ("voice", "voice", want_v),
                ("music", "music", want_m)]
        for label, sub, want in rows:
            d = os.path.join(out, sub)
            got = []
            if os.path.isdir(d):
                got = [os.path.join(d, x) for x in sorted(os.listdir(d))
                       if not x.startswith(".") and os.path.isfile(os.path.join(d, x))]
            small = [x for x in got if os.path.getsize(x) < MIN.get(label, 1)]
            sizes = [os.path.getsize(x) for x in got]
            status = "ok"
            if want and len(got) < want:
                status = "SHORT %d of %d" % (len(got), want)
                bad += 1
            if small:
                status = "%d UNDERSIZE" % len(small)
                bad += 1
            print("  %-10s %3d files  want %3d  %8s..%-8s  %s"
                  % (label, len(got), want,
                     min(sizes) if sizes else 0, max(sizes) if sizes else 0, status))
            for x in small[:4]:
                print("      undersize: %s (%d bytes)" % (os.path.basename(x), os.path.getsize(x)))
        mp4 = os.path.join(out, slug + ".mp4")
        if not os.path.exists(mp4):
            print("  FILM       MISSING %s" % mp4)
            bad += 1
            continue
        sz = os.path.getsize(mp4)
        pr = ffprobe(mp4, "stream=width,height,nb_frames,duration")
        aud = run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                   "-show_entries", "stream=codec_name,duration", "-of", "default=nw=1", mp4])[1]
        ok = sz >= MIN["film"] and float(pr.get("duration", 0) or 0) > 5
        if not ok:
            bad += 1
        print("  FILM       %s  %s bytes  %sx%s  %s frames  %ss  audio[%s]  %s"
              % (os.path.basename(mp4), sz, pr.get("width"), pr.get("height"),
                 pr.get("nb_frames"), pr.get("duration"),
                 " ".join(aud.split()) or "NONE", "ok" if ok else "BAD"))
    print("\n%s" % ("VERIFY: all stages produced real artifacts" if not bad
                    else "VERIFY: %d problems" % bad))
    return 1 if bad else 0


# ---------------------------------------------------------------------------
# --strips : make something to LOOK at
# ---------------------------------------------------------------------------

def cmd_strips(args):
    """A frame strip per finished film, and a per-beat strip per generated clip.

    ffmpeg's `tile=` with a glob input silently DROPS cells when the inputs differ in size,
    which is how a strip can come back looking complete and be missing a third of the film.
    So every strip here is built from explicit -i arguments through hstack, and the cell
    count is asserted against the number of inputs before the file is accepted.
    """
    os.makedirs(SAMPLES, exist_ok=True)
    made = []
    for mv in films(args.only):
        js = os.path.splitext(mv)[0] + ".json"
        if not os.path.exists(js):
            continue
        film = json.load(open(js, encoding="utf-8"))
        slug = film["title"].lower().replace(" ", "-")
        out = os.path.join(SHORTS, slug)
        mp4 = os.path.join(out, slug + ".mp4")
        if os.path.exists(mp4):
            p = os.path.join(SAMPLES, slug + "_film.png")
            if strip_from_video(mp4, p, args.cells, height=200):
                made.append(p)
        cd = os.path.join(out, "clips")
        if os.path.isdir(cd):
            for fn in sorted(os.listdir(cd)):
                if not fn.endswith(".mp4"):
                    continue
                base = re.sub(r"_\d+_\.mp4$", "", fn)
                p = os.path.join(SAMPLES, "%s__%s.png" % (slug, base))
                if strip_from_video(os.path.join(cd, fn), p, 6, height=180):
                    made.append(p)
    for p in made:
        print("  %s  %d bytes" % (os.path.relpath(p, ROOT), os.path.getsize(p)))
    print("%d strips" % len(made))
    return 0


def strip_from_video(src, dst, cells, height=180):
    d = ffprobe(src, "stream=duration")
    try:
        dur = float(d.get("duration") or 0)
    except ValueError:
        dur = 0
    if dur <= 0:
        rc, o = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=nw=1:nk=1", src])
        try:
            dur = float(o.strip())
        except ValueError:
            return False
    if dur <= 0:
        return False
    tmp = dst + ".d"
    os.makedirs(tmp, exist_ok=True)
    grabs = []
    for i in range(cells):
        # Sample INSIDE the clip, never at 0 and never at the last frame - the first frame
        # of an i2v clip is the keyframe itself and the last is where drift is worst, so a
        # strip taken at the ends says least about what the beat does.
        t = dur * (i + 0.5) / cells
        p = os.path.join(tmp, "%02d.png" % i)
        rc, _ = run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % t, "-i", src,
                     "-frames:v", "1", "-vf", "scale=-2:%d" % height, p])
        if rc == 0 and os.path.exists(p) and os.path.getsize(p) > 1000:
            grabs.append(p)
    if not grabs:
        return False
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for p in grabs:
        cmd += ["-i", p]
    if len(grabs) == 1:
        cmd += ["-frames:v", "1", dst]
    else:
        cmd += ["-filter_complex", "hstack=inputs=%d" % len(grabs), "-frames:v", "1", dst]
    rc, _ = run(cmd)
    ok = rc == 0 and os.path.exists(dst) and os.path.getsize(dst) > 2000
    if ok:
        # ASSERT THE CELL COUNT. A silently short strip is the failure this project has
        # already paid for once with a tile= glob.
        w = int(ffprobe(dst, "stream=width").get("width") or 0)
        one = int(ffprobe(grabs[0], "stream=width").get("width") or 1)
        n = round(w / one) if one else 0
        if n != len(grabs):
            print("  STRIP SHORT %s: %d cells for %d inputs" % (dst, n, len(grabs)))
            ok = False
    for p in grabs:
        try:
            os.remove(p)
        except OSError:
            pass
    try:
        os.rmdir(tmp)
    except OSError:
        pass
    return ok


# ---------------------------------------------------------------------------
# --reel : cut the style panels together
# ---------------------------------------------------------------------------

def cmd_reel(args):
    """Concatenate the finished style panels into one piece.

    -c copy, so every panel must share fps and canvas - which is exactly why compile.py
    locks both at movie level. The panels are checked for that before the concat rather
    than after, because a mismatched concat produces a file that plays and then desyncs.
    """
    os.makedirs(SAMPLES, exist_ok=True)
    parts, meta = [], []
    for mv in films("demo_style_"):
        js = os.path.splitext(mv)[0] + ".json"
        if not os.path.exists(js):
            continue
        film = json.load(open(js, encoding="utf-8"))
        slug = film["title"].lower().replace(" ", "-")
        mp4 = os.path.join(SHORTS, slug, slug + ".mp4")
        if not os.path.exists(mp4):
            print("  missing panel %s" % mp4)
            continue
        pr = ffprobe(mp4, "stream=width,height,r_frame_rate,duration")
        meta.append((os.path.basename(mv), pr))
        parts.append(mp4)
    if not parts:
        print("no panels rendered yet")
        return 1
    keys = {(m[1].get("width"), m[1].get("height"), m[1].get("r_frame_rate")) for m in meta}
    if len(keys) != 1:
        print("PANELS DISAGREE - concat -c copy would desync: %s" % keys)
        return 1
    lst = os.path.join(SAMPLES, "_reel.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for p in parts:
            f.write("file '%s'\n" % p)
    dst = os.path.join(SAMPLES, "demo_style_reel.mp4")
    rc, out = run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                   "-i", lst, "-c", "copy", dst])
    if rc != 0 or not os.path.exists(dst):
        print("concat failed: %s" % out)
        return 1
    pr = ffprobe(dst, "stream=width,height,nb_frames,duration")
    print("%s  %d bytes  %sx%s  %ss  from %d panels"
          % (os.path.relpath(dst, ROOT), os.path.getsize(dst), pr.get("width"),
             pr.get("height"), pr.get("duration"), len(parts)))
    strip_from_video(dst, os.path.join(SAMPLES, "demo_style_reel.png"), 3 * len(parts), 190)
    return 0


# ---------------------------------------------------------------------------

def cmd_collect(args):
    """Copy each finished film into studio/samples/demo_films/.

    Not tidiness. studio/serve.py serves everything under studio/samples/ at /samples/...,
    so a film that lives only in ~/ComfyUI/output/claude-generated/12-shorts/ can be played
    by nobody without an ssh session, and a film sitting next to its own frame strips can
    be opened in a browser at http://<box>:8777/samples/demo_films/<slug>.mp4.

    COPY, not symlink: the two trees are on the same disk but the output tree is where
    ComfyUI writes and where a re-render silently replaces things, and a link into it would
    make the demo set change under the user without anybody touching it.
    """
    os.makedirs(SAMPLES, exist_ok=True)
    n = 0
    for mv in films(args.only):
        js = os.path.splitext(mv)[0] + ".json"
        if not os.path.exists(js):
            continue
        slug = slug_of(js)
        src = os.path.join(SHORTS, slug, slug + ".mp4")
        if not os.path.exists(src):
            print("  not rendered: %s" % slug)
            continue
        dst = os.path.join(SAMPLES, slug + ".mp4")
        if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
            print("  up to date  %s" % os.path.basename(dst))
            n += 1
            continue
        shutil.copyfile(src, dst)
        ok = os.path.getsize(dst) == os.path.getsize(src)
        print("  %s  %d bytes  %s" % (os.path.basename(dst), os.path.getsize(dst),
                                      "ok" if ok else "SIZE MISMATCH"))
        n += ok
    print("%d films in %s  ->  http://<box>:8777/samples/demo_films/" % (n, os.path.relpath(SAMPLES, ROOT)))
    return 0


def cmd_index(args):
    """One machine-readable record per demo film: what it demonstrates, where the mp4 is,
    how long it runs, where its strips are, and the motion-source census that is the whole
    point of the set. Written so a gallery route can render this without re-deriving any
    of it - nothing in the app consumes it yet.
    """
    still = stillness_ids()
    out = {"generated": None, "films": []}
    import datetime
    out["generated"] = datetime.datetime.now().isoformat(timespec="seconds")
    for mv in films(args.only):
        js = os.path.splitext(mv)[0] + ".json"
        if not os.path.exists(js):
            continue
        film = json.load(open(js, encoding="utf-8"))
        slug = film["title"].lower().replace(" ", "-")
        mp4 = os.path.join(SHORTS, slug, slug + ".mp4")
        src = collections.Counter()
        named_hold = unnamed_hold = 0
        for b in film["beats"]:
            k, _, mid = b.get("motion_src", "").partition(":")
            src[k] += 1
            # A stillness card reached through the CARD rung is an author's decision and
            # shows up as motion_src "card:hold_frame", not "hold:...". Both spellings are
            # counted as a named hold; only rung 4 arrived at by failing to derive
            # anything counts against the film.
            if mid.strip() in still:
                named_hold += 1
            elif k == "hold":
                unnamed_hold += 1
        rec = {
            "movie": os.path.relpath(mv, ROOT),
            "compiled": os.path.relpath(js, ROOT),
            "title": film["title"],
            "slug": slug,
            "engine": film.get("keyframe_engine"),
            "beats": len(film["beats"]),
            "cast": sorted(film.get("characters") or {}),
            "motion_sources": dict(src),
            "named_holds": named_hold,
            "unnamed_holds": unnamed_hold,
            "film": mp4 if os.path.exists(mp4) else None,
            "bytes": os.path.getsize(mp4) if os.path.exists(mp4) else 0,
        }
        if os.path.exists(mp4):
            pr = ffprobe(mp4, "stream=width,height,nb_frames,duration")
            rec["seconds"] = float(pr.get("duration") or 0)
            rec["canvas"] = "%sx%s" % (pr.get("width"), pr.get("height"))
        strip = os.path.join(SAMPLES, slug + "_film.png")
        rec["strip"] = os.path.relpath(strip, ROOT) if os.path.exists(strip) else None
        rec["beat_strips"] = sorted(
            os.path.relpath(os.path.join(SAMPLES, x), ROOT)
            for x in (os.listdir(SAMPLES) if os.path.isdir(SAMPLES) else [])
            if x.startswith(slug + "__"))
        out["films"].append(rec)
    reel = os.path.join(SAMPLES, "demo_style_reel.mp4")
    if os.path.exists(reel):
        pr = ffprobe(reel, "stream=duration")
        out["style_reel"] = {"file": os.path.relpath(reel, ROOT),
                             "bytes": os.path.getsize(reel),
                             "seconds": float(pr.get("duration") or 0),
                             "panels": [s for s, _, _ in REEL_STYLES]}
    os.makedirs(SAMPLES, exist_ok=True)
    p = os.path.join(SAMPLES, "index.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=2)
    print("%s  %d films" % (os.path.relpath(p, ROOT), len(out["films"])))
    for r in out["films"]:
        print("  %-22s %2d beats  %5.1fs  holds named=%d unnamed=%d  %s"
              % (r["slug"], r["beats"], r.get("seconds") or 0,
                 r["named_holds"], r["unnamed_holds"], r["film"] or "NOT RENDERED"))
    return 0


def cmd_list(args):
    still = stillness_ids()
    print("stillness cards (a hold on one of these is a decision, not a defect): %s"
          % ", ".join(sorted(still)))
    for mv in films(args.only):
        js = os.path.splitext(mv)[0] + ".json"
        n = "-"
        if os.path.exists(js):
            n = len(json.load(open(js, encoding="utf-8"))["beats"])
        print("  %-40s beats=%s" % (os.path.relpath(mv, ROOT), n))
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="author / check / render / verify the demo films",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--list", action="store_true", help="what demo films exist")
    ap.add_argument("--write-reel", action="store_true",
                    help="(re)emit the six style panel .movie files")
    ap.add_argument("--check", action="store_true",
                    help="compile and print the per-beat motion table. NO GPU")
    ap.add_argument("--render", action="store_true", help="compile then scripts/short.py")
    ap.add_argument("--verify", action="store_true", help="measure every stage's artifacts")
    ap.add_argument("--strips", action="store_true", help="frame strips to look at")
    ap.add_argument("--reel", action="store_true", help="concat the style panels")
    ap.add_argument("--collect", action="store_true",
                    help="copy finished films into studio/samples/demo_films/")
    ap.add_argument("--index", action="store_true",
                    help="write studio/samples/demo_films/index.json")
    ap.add_argument("--only", default=None, help="substring filter on the .movie filename")
    ap.add_argument("--cells", type=int, default=12, help="frames per film strip")
    a = ap.parse_args()
    did = 0
    rc = 0
    for flag, fn in (("write_reel", lambda _a: (write_reel(), 0)[1]),
                     ("list", cmd_list), ("check", cmd_check), ("render", cmd_render),
                     ("verify", cmd_verify), ("strips", cmd_strips), ("reel", cmd_reel),
                     ("collect", cmd_collect), ("index", cmd_index)):
        if getattr(a, flag):
            did += 1
            rc = fn(a) or rc
    if not did:
        ap.print_help()
    return rc


if __name__ == "__main__":
    sys.exit(main())
