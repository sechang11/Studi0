#!/usr/bin/env python3
"""studio/_tools/glue_cut.py - a cut whose shots are GLUED (LTX_PLAYBOOK §102, 2026-10-05).

A plain cut (set_film.py cut) puts the takes end to end and every shot starts fresh. The director: "there should be
an overlap of something to glue them together - the same background track playing through both, a physical frame in
the visuals, an object that remains constant while everything else changes". This cut builds those overlaps:

  sound    each shot's own sound can start before its picture (a J cut: "audio_in" earlier than "in") or run on
           after it (an L cut: "audio_out" later than "out"); a BED - a sound under several shots (a rumble rising
           through a spell, a forest fire) - runs through every cut in its range
  picture  a "dissolve" (time passing, the same thing changing) or a "flash" (a blast of light covering the cut)
           between two shots, or a plain "cut"
  object   an OVERLAY that stays while the shots change under it - embers drifting across the cuts of a spell -
           composited over a range of shots in one continuous pass, so it does not restart at a cut

    python3 studio/_tools/glue_cut.py PLAN.json [--picks]     --picks: each shot's take from picks.txt

PLAN (paths relative to the film's folder studio/samples/fight/<film>/):
  {"film": "fire-esper", "out": "fire-esper.mp4", "grade": "filmic",
   "title": {"lines": [["THE FIRE ESPER", 64], ["Terra and the jester", 28]], "secs": 3.0, "base": "anchor_010.png"},
   "end": {"lines": [["THE END", 60]], "secs": 3.0, "base": "anchor_230.png"},
   "shots": [{"id": "010", "take": "h3f_010_s11.mp4", "in": 0.0, "out": null, "audio_in": null, "audio_out": null,
              "next": {"video": "cut" | "dissolve" | "flash", "secs": 0.5}}, ...],
   "beds": [{"file": "bed_rumble.mp3", "from": "040", "to": "130", "gain_db": -12, "fade": 1.5}],
   "overlays": [{"kind": "embers", "from": "050", "to": "130", "density": 1.0, "seed": 7}]}
Writes <out>, <film>_final.mp4 (shots & specs plays it), <film>_timeline.json (where each shot sits in the cut) and
<film>_sfx.wav (the takes' own sound alone, for a score mix - "stems": false skips it); "final": false writes <out>
only (a trial).
"""
import json
import math
import os
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
sys.path.insert(0, os.path.join(ROOT, "studio", "_tools"))
import post  # noqa: E402
import shot_options  # noqa: E402

W, H, FPS, SR = 1280, 704, 24, 48000
CUT = 1.0 / FPS          # a "cut" is a one-frame blend: xfade needs a duration


def sh(*cmd):
    # a time limit on every call: two ffmpeg graphs here hung forever at 100% CPU on ffmpeg 8 (a looped input, an
    # apad'ed output without -t) and one ran on for four hours after its parent was killed
    try:
        r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=1500)
    except subprocess.TimeoutExpired:
        sys.exit("timed out (25 min): %s" % " ".join(str(c) for c in cmd[:6]))
    if r.returncode != 0:
        sys.exit("failed: %s\n%s" % (" ".join(str(c) for c in cmd[:6]), r.stderr[-1500:]))
    return r


def dur(p, stream="format"):
    if stream == "v":
        r = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
               "stream=nb_read_packets", "-of", "csv=p=0", p)
        return int(r.stdout.strip()) / float(FPS)
    return float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p).stdout.strip())


def font(size, bold=True):
    from PIL import ImageFont
    for f in ("/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-%s.otf" % ("Bold" if bold else "Medium"),
              "/usr/share/fonts/open-sans/OpenSans-%s.ttf" % ("Semibold" if bold else "Regular"),
              "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans%s.ttf" % ("-Bold" if bold else "")):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def card(spec, out_dir, name, vf=None):
    """A title or end card: the base frame blurred and darkened, the lines centred, silent."""
    from PIL import Image, ImageDraw, ImageFilter
    im = Image.open(os.path.join(out_dir, spec["base"])).convert("RGB").resize((W, H)).filter(ImageFilter.GaussianBlur(7))
    im = Image.eval(im, lambda v: int(v * 0.42))
    d = ImageDraw.Draw(im)
    y = H // 2 - sum(sz + 18 for _, sz in spec["lines"]) // 2
    for text, sz in spec["lines"]:
        f = font(sz, bold=sz > 40)
        w = d.textlength(text, font=f)
        d.text(((W - w) / 2 + 3, y + 3), text, font=f, fill=(0, 0, 0))
        d.text(((W - w) / 2, y), text, font=f, fill=(255, 236, 196) if sz > 40 else (225, 225, 225))
        y += sz + 18
    png = os.path.join(out_dir, "_glue_%s.png" % name)
    im.save(png)
    mp4 = png[:-4] + ".mp4"
    sh("ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", png, "-t", "%.3f" % spec["secs"], "-r", str(FPS),
       "-vf", (vf + ",format=yuv420p") if vf else "format=yuv420p", "-c:v", "libx264", "-crf", "14", mp4)
    return mp4


def embers(path, total, spans, seed=7, density=1.0):
    """The object glue: glowing embers drifting up, one continuous layer for the whole film (black where no span
    is), so the embers never restart at a cut. Blended over the picture with "screen"."""
    import numpy as np
    rng = np.random.default_rng(seed)
    n_frames = int(round(total * FPS))
    n = int(110 * density)
    xs, ys = rng.uniform(0, W, n), rng.uniform(0, H, n)
    vy, vx = rng.uniform(18, 70, n), rng.uniform(-12, 12, n)
    size = rng.uniform(1.2, 4.2, n)
    phase = rng.uniform(0, 6.28, n)
    bright = rng.uniform(0.45, 1.0, n)
    rad = 9
    yy, xx = np.mgrid[-rad:rad + 1, -rad:rad + 1]
    col = np.array([1.0, 0.55, 0.18])
    proc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", path],
                            stdin=subprocess.PIPE)
    for f in range(n_frames):
        t = f / float(FPS)
        level = 0.0
        for a, b in spans:                                      # fade in and out over half a second at each end
            if a - 0.5 <= t <= b + 0.5:
                level = max(level, min(1.0, (t - (a - 0.5)) / 0.5, ((b + 0.5) - t) / 0.5))
        img = np.zeros((H, W, 3), np.float32)
        if level > 0:
            px = (xs + vx * t + 14 * np.sin(phase + t * 1.3)) % W
            py = (ys - vy * t) % H
            flick = 0.65 + 0.35 * np.sin(phase * 3 + t * 9)
            for i in range(n):
                x0, y0 = int(px[i]), int(py[i])
                if x0 < rad or y0 < rad or x0 >= W - rad or y0 >= H - rad:
                    continue
                g = np.exp(-(xx ** 2 + yy ** 2) / (2 * size[i] ** 2)) * bright[i] * flick[i] * level
                img[y0 - rad:y0 + rad + 1, x0 - rad:x0 + rad + 1] += g[:, :, None] * col
        proc.stdin.write((np.clip(img, 0, 1) * 255).astype(np.uint8).tobytes())
    proc.stdin.close()
    proc.wait()
    return path


def main():
    plan = json.load(open(sys.argv[1], encoding="utf-8"))
    film = plan["film"]
    out_dir = os.path.join(ROOT, "studio", "samples", "fight", film)
    if "--picks" in sys.argv[2:]:
        # each shot cut from the take picked on shots & specs (picks.txt, "010=h3f:11,..."), the plan's trims kept
        pk = os.path.join(out_dir, "picks.txt")
        picks = dict(kv.split("=", 1) for kv in open(pk).read().strip().split(",") if "=" in kv)             if os.path.exists(pk) else {}
        for s in plan["shots"]:
            tok = picks.get(s["id"])
            if tok:
                eng, _, seed = tok.rpartition(":")
                s["take"] = "%s_%s_s%s.mp4" % (eng or "shot", s["id"], seed)
    work = os.path.join(out_dir, "_glue")
    os.makedirs(work, exist_ok=True)
    # SHOT OPTIONS (studio/shotscripts/<film>.options.json): a grade per shot, impact frames, beat sounds - only
    # where asked; with a grade option on anywhere, every shot is graded on its own (its look, or the film's)
    sp_ = os.path.join(ROOT, "studio", "shotscripts", film + ".json")
    by_sid = {x["id"]: x for x in (json.load(open(sp_, encoding="utf-8")).get("shots", []) if os.path.exists(sp_)
                                   else [])}
    opts = shot_options.load(film)
    film_grade = post.grade_filter(plan.get("grade", "filmic"))
    looks = {x["id"]: shot_options.grade_for(opts, by_sid[x["id"]]) for x in plan["shots"] if x["id"] in by_sid}
    per_shot = any(looks.values())
    card_vf = film_grade if per_shot else None
    # the items of the picture, in order: title card, shots, end card
    items = []
    if plan.get("title"):
        items.append({"id": "title", "v": card(plan["title"], out_dir, "title", card_vf), "a": None,
                      "next": {"video": "dissolve", "secs": 0.6}})
    for k, s in enumerate(plan["shots"]):
        take = os.path.join(out_dir, s["take"])
        full = dur(take)
        vin, vout = float(s.get("in") or 0.0), float(s.get("out") or full)
        ain = float(s["audio_in"]) if s.get("audio_in") is not None else vin
        aout = float(s["audio_out"]) if s.get("audio_out") is not None else vout
        ain, aout = max(0.0, ain), min(full, aout)
        v = os.path.join(work, "v_%s.mp4" % s["id"])
        a = os.path.join(work, "a_%s.wav" % s["id"])
        look = (looks.get(s["id"]) or film_grade) if per_shot else None
        sh("ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % vin, "-to", "%.3f" % vout, "-i", take, "-an", "-vf",
           "scale=%d:%d,fps=%d,%sformat=yuv420p" % (W, H, FPS, (look + ",") if look else ""), "-c:v", "libx264",
           "-crf", "14", v)
        sh("ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % ain, "-to", "%.3f" % aout, "-i", take, "-vn", "-ac", "2",
           "-ar", str(SR), a)
        items.append({"id": s["id"], "v": v, "a": a, "lead": vin - ain, "next": s.get("next") or {"video": "cut"},
                      "tail": aout - vout, "afade": s.get("audio_fade"), "gain": float(s.get("gain_db", 0.0)),
                      "vin": vin})
    if plan.get("end"):
        items[-1]["next"] = items[-1].get("next") if items[-1]["next"].get("video") != "cut" else {"video": "dissolve", "secs": 0.8}
        items.append({"id": "end", "v": card(plan["end"], out_dir, "end", card_vf), "a": None, "next": None})
    # the timeline: each item's start in the cut, the transitions eating into it
    t = 0.0
    for k, it in enumerate(items):
        it["len"] = dur(it["v"], "v")
        it["start"] = t
        nx = it["next"] or {}
        it["x"] = CUT if (nx.get("video") or "cut") == "cut" else float(nx.get("secs") or 0.5)
        if k + 1 < len(items):
            t += it["len"] - it["x"]
        else:
            t += it["len"]
    total = t
    # the picture: one xfade per join (fade = dissolve, fadewhite = flash, a one-frame fade = a cut)
    inputs, filt = [], []
    for it in items:
        inputs += ["-i", it["v"]]
    prev, length = "[0:v]", items[0]["len"]
    for k in range(1, len(items)):
        a = items[k - 1]
        kind = (a["next"] or {}).get("video") or "cut"
        tr = {"dissolve": "fade", "flash": "fadewhite", "cut": "fade"}[kind]
        lab = "[x%d]" % k
        filt.append("%s[%d:v]xfade=transition=%s:duration=%.4f:offset=%.4f%s" % (
            prev, k, tr, a["x"], length - a["x"], lab))
        length = length - a["x"] + items[k]["len"]
        prev = lab
    # the object glue: overlays composited across their spans in one continuous layer
    shots = {it["id"]: it for it in items}
    nin = len(items)
    for ov in plan.get("overlays", []):
        spans = [(shots[ov["from"]]["start"], shots[ov["to"]]["start"] + shots[ov["to"]]["len"])]
        layer = embers(os.path.join(work, "embers_%s_%s.mp4" % (ov["from"], ov["to"])), total, spans,
                       seed=int(ov.get("seed", 7)), density=float(ov.get("density", 1.0)))
        inputs += ["-i", layer]
        # screen in RGB: in YUV the blend would run on the chroma planes too and tint the whole picture
        filt.append("%sformat=gbrp[pa%d];[%d:v]format=gbrp[pb%d];[pa%d][pb%d]blend=all_mode=screen:shortest=1,"
                    "format=yuv420p[o%d]" % (prev, nin, nin, nin, nin, nin, nin))
        prev = "[o%d]" % nin
        nin += 1
    # impact frames (an option): a few frames of a stylised negative - or a white flash - on the hits asked for
    inv, flash = [], []
    for it in items:
        imp = shot_options.effective(opts, it["id"]).get("impact_frames") if it["id"] in by_sid else None
        for at_ in (imp or {}).get("at", []):
            t0 = it["start"] + float(at_) - it["vin"]
            if it["start"] <= t0 < it["start"] + it["len"]:
                (flash if imp.get("style") == "flash" else inv).append((t0, t0 + int(imp.get("frames", 2)) / float(FPS)))
    if inv:
        e = "+".join("between(t,%.3f,%.3f)" % w for w in inv)
        filt.append("%snegate=enable='%s',hue=s=0:enable='%s',eq=contrast=1.8:brightness=0.04:enable='%s'[imp]" % (
            prev, e, e, e))
        prev = "[imp]"
    if flash:
        e = "+".join("between(t,%.3f,%.3f)" % w for w in flash)
        filt.append("%seq=brightness=0.55:saturation=0.4:enable='%s'[flash]" % (prev, e))
        prev = "[flash]"
    grade = None if per_shot else film_grade                    # graded per shot already, or the film's one grade
    filt.append("%s%s[vout]" % (prev, grade if grade else "null"))
    # the sound: each shot's own at its place (minus its J lead), the beds across their ranges
    mix, sfx_parts = [], []
    for it in items:
        if not it["a"]:
            continue
        inputs += ["-i", it["a"]]
        at = max(0.0, it["start"] - it["lead"])
        alen = dur(it["a"])
        fo = max(0.02, min(0.25, it["x"] if it["x"] > CUT else 0.06))
        if it.get("afade") is not None:
            fo = float(it["afade"])
        elif it.get("tail", 0) > 0.1:                           # an L cut: the sound dies away under the next shot
            fo = it["tail"]
        fi = min(0.3, it["lead"]) if it["lead"] > 0.1 else 0.04  # a J cut: the sound swells in before its picture
        chain = "volume=%.1fdB,afade=t=in:d=%.3f,afade=t=out:st=%.3f:d=%.3f,adelay=%d|%d" % (
            it.get("gain", 0.0), fi, max(0.0, alen - fo), fo, int(at * 1000), int(at * 1000))
        filt.append("[%d:a]%s[s%d]" % (nin, chain, nin))
        sfx_parts.append((it["a"], chain))
        mix.append("[s%d]" % nin)
        nin += 1
    # beat sounds (an option): each made sound on its moment, over the take's own (shot_options.py sounds FILM)
    for it in items:
        bs = shot_options.effective(opts, it["id"]).get("beat_sounds") if it["id"] in by_sid else None
        for beat in (bs or {}).get("beats", []):
            f = shot_options.beat_file(film, it["id"], beat)
            if not beat.get("sound"):
                continue
            if not os.path.exists(f):
                print("  %s: a beat sound not made yet - run shot_options.py sounds %s (%s)" % (
                    it["id"], film, beat["sound"][:50]), flush=True)
                continue
            t0 = it["start"] + float(beat["at"]) - it["vin"]
            if t0 < 0 or t0 >= total:
                continue
            bl = dur(f)
            chain = ("aformat=sample_rates=%d:channel_layouts=stereo,volume=%.1fdB,afade=t=in:d=0.01,"
                     "afade=t=out:st=%.3f:d=0.15,adelay=%d|%d" % (SR, float(beat.get("gain_db", -3)),
                                                                max(0.0, bl - 0.15), int(t0 * 1000), int(t0 * 1000)))
            inputs += ["-i", f]
            filt.append("[%d:a]%s[e%d]" % (nin, chain, nin))
            sfx_parts.append((f, chain))
            mix.append("[e%d]" % nin)
            nin += 1
    for k, b in enumerate(plan.get("beds", [])):
        a0 = shots[b["from"]]["start"]
        a1 = shots[b["to"]]["start"] + shots[b["to"]]["len"]
        fade = float(b.get("fade", 1.5))
        # looped to length in its own pass: a "-stream_loop -1" input inside the big graph never ends (ffmpeg 8
        # kept decoding it after the trim, and the cut hung at 100% CPU)
        bed = os.path.join(work, "bed_%d.wav" % k)
        sh("ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", os.path.join(out_dir, b["file"]), "-t",
           "%.3f" % (a1 - a0), "-ac", "2", "-ar", str(SR), bed)
        inputs += ["-i", bed]
        filt.append("[%d:a]volume=%.1fdB,afade=t=in:d=%.2f,afade=t=out:st=%.3f:d=%.2f,adelay=%d|%d[b%d]" % (
                        nin, float(b.get("gain_db", -12)), fade, max(0.0, a1 - a0 - fade), fade,
                        int(a0 * 1000), int(a0 * 1000), nin))
        mix.append("[b%d]" % nin)
        nin += 1
    filt.append("%samix=inputs=%d:normalize=0:duration=longest,apad,atrim=0:%.3f,"
                "loudnorm=I=-15:TP=-1.5:LRA=11,aresample=%d[aout]" % ("".join(mix), len(mix), total, SR))
    dst = os.path.join(out_dir, plan.get("out", film + ".mp4"))
    script = os.path.join(work, "graph.txt")
    open(script, "w").write(";\n".join(filt))
    sh("ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex_script", script, "-map", "[vout]", "-map", "[aout]",
       "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", str(SR),
       "-t", "%.3f" % total, dst)
    if plan.get("stems", True):
        # the takes' own sound alone, placed as in the cut, no beds, not levelled: what a SCORE is mixed with
        # (studio/_tools/score_mix.py) - under music the beds go, the music is the glue (2026-10-05: a score
        # ducked hard under the takes and the beds read as "sound effect stuff", not music)
        ins, fl, mx = [], [], []
        for j, (a, chain) in enumerate(sfx_parts):
            ins += ["-i", a]
            fl.append("[%d:a]%s[t%d]" % (j, chain, j))
            mx.append("[t%d]" % j)
        # apad=whole_dur ends by itself; "apad,atrim" in an audio-only graph never ended on ffmpeg 8, even with -t
        fl.append("%samix=inputs=%d:normalize=0:duration=longest,apad=whole_dur=%.3f[sfx]" % ("".join(mx), len(mx),
                                                                                               total))
        sp = os.path.join(work, "graph_sfx.txt")
        open(sp, "w").write(";\n".join(fl))
        sh("ffmpeg", "-y", "-v", "error", *ins, "-filter_complex_script", sp, "-map", "[sfx]", "-c:a", "pcm_s16le",
           "-ar", str(SR), "-t", "%.3f" % total, os.path.join(out_dir, film + "_sfx.wav"))   # -t: apad never ends
    tl = [{"id": it["id"], "start": round(it["start"], 3), "len": round(it["len"], 3),
           "into_next": (it["next"] or {}).get("video"), "overlap": round(it["x"], 3)} for it in items]
    if plan.get("final", True):                                 # "final": false for a trial that must not replace it
        sh("cp", dst, os.path.join(out_dir, film + "_final.mp4"))
        json.dump({"total": round(total, 3), "items": tl}, open(os.path.join(out_dir, film + "_timeline.json"), "w"),
                  indent=1)
    print("glued %d shots -> %s (%.1f s)" % (len(plan["shots"]), dst, dur(dst)))


if __name__ == "__main__":
    main()
