#!/usr/bin/env python3
"""
cartoon.py - narrative short with characters, dialogue, voices and burnt-in captions.

    python3 cartoon.py films/last-light.json
    python3 cartoon.py films/last-light.json --stage keyframes   # just the stills
    python3 cartoon.py films/last-light.json --stage edit        # re-cut only

Stages (each resumable, each skips work that already exists):

  1 keyframes  Qwen-Image renders every shot.       ~5 s/shot
  2 clips      LTX-2.3 i2v animates each keyframe   ~17 s/shot   (Wan would be ~130 s)
               and generates an ambient audio bed in the same pass.
  3 voices     Chatterbox speaks each line of        ~3 s/line
               dialogue; per-character pitch shift
               gives each one a distinct timbre.
  4 edit       ffmpeg: cross-dissolves, title cards,
               dialogue mixed under picture, captions
               burnt in from measured audio durations.

Character consistency comes from two things: a `characters` block whose descriptions are
substituted verbatim into every shot prompt via {NAME}, and a shared `style` string
appended to all of them. LTX i2v then animates from that fixed keyframe, so the design
cannot drift mid-shot.

Captions are built from the REAL duration of each rendered voice clip (ffprobe), not from
speech recognition. We already know the text; measuring is exact where ASR would guess.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# Set COMFY_ROOT when driving the box from another machine over the SMB share
# (e.g. COMFY_ROOT=Z:/ComfyUI from Windows). Defaults to the local install.
COMFY = os.environ.get("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
sys.path.insert(0, HERE)
from comfy import run, set_path  # noqa: E402

HOST = os.environ.get("COMFY_HOST", "127.0.0.1:8188")
AR = {"16:9": (1664, 928), "9:16": (928, 1664), "1:1": (1328, 1328)}
VID = {"16:9": (768, 512), "16:9-hd": (1280, 704)}

NEG_IMG = ("blurry, low quality, watermark, text, caption, signature, jpeg artifacts, "
           "deformed, extra limbs, photorealistic human, live action")


def _find_font():
    """A real font file for drawtext / libass.

    Both resolve font *names* through fontconfig. On Windows fontconfig has no default
    config, and supplying one made this ffmpeg build segfault outright - so pass an
    actual file instead. Override with CARD_FONT if you want a different typeface.
    """
    if os.environ.get("CARD_FONT"):
        return os.environ["CARD_FONT"]
    for p in ("C:/Windows/Fonts/arialbd.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return p
    return ""          # fall back to fontconfig (fine on a normal Linux box)


FONT = _find_font()


def fgpath(p):
    """Escape a path for use *inside* an ffmpeg filtergraph (drive-letter colons)."""
    return p.replace("\\", "/").replace(":", r"\:")


def sh(*a, **kw):
    r = subprocess.run(a, capture_output=True, text=True, **kw)
    if r.returncode:
        print(r.stderr[-2500:], file=sys.stderr)
        raise SystemExit(f"failed: {a[0]}")
    return r.stdout


def dur(path):
    return float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=nw=1:nk=1", path).strip())


def wait_for(path, timeout=180):
    """Block until a file the server just wrote is actually readable here.

    Only needed when COMFY_ROOT is an SMB share: the ComfyUI API reports a job
    complete as soon as the server has written the file, but the client's view of
    the share can lag well over a minute behind. Reading straight through would
    raise a spurious 'no such file'. Locally this returns on the first check.
    """
    for _ in range(timeout):
        if os.path.exists(path):
            return path
        time.sleep(1)
    raise SystemExit(f"timed out waiting for {path} to appear")


def load_wf(name):
    return {k: v for k, v in json.load(open(f"{ROOT}/workflows/{name}")).items()
            if not k.startswith("_")}


def expand(text, chars):
    """substitute {PIP} etc. with the full character description"""
    for name, desc in chars.items():
        text = text.replace("{" + name + "}", desc)
    return text


# ------------------------------------------------------------------ stage 1
def keyframes(film, outdir, seed0):
    w, h = AR[film.get("ar", "16:9")]
    chars, style = film.get("characters", {}), film.get("style", "")
    print(f"\n=== STAGE 1: {len(film['shots'])} keyframes @ {w}x{h} ===")
    for i, s in enumerate(film["shots"]):
        if os.path.exists(f"{outdir}/keyframes/{s['id']}_00001_.png"):
            print(f"  = {s['id']}")
            continue
        # `quality: true` swaps the 4-step Lightning LoRA for the 20-step path.
        # Worth it for any shot where the pose or expression fights the style block:
        # a strong "appealing character design" style will otherwise pull every shot
        # back toward the same front-facing hero portrait, and 4 steps has far less
        # prompt adherence to resist it with. Costs ~30 s instead of ~4.5 s.
        hard = bool(s.get("quality"))
        wf = load_wf("02_qwen_t2i_quality.json" if hard
                     else "01_qwen_t2i_turbo.json")
        set_path(wf, "10.inputs.text", f"{expand(s['prompt'], chars)}, {style}")
        # Negatives compose: the built-in baseline, then a film-wide `neg_all`, then
        # the per-shot `neg`. `neg_all` is what holds a whole-film style that the model
        # fights - for 2D anime you must repeat "3d render, photorealistic, cgi" on
        # every single shot or Qwen drifts back to a 3D render within a few shots.
        neg = ", ".join(x for x in (NEG_IMG, film.get("neg_all"), s.get("neg")) if x)
        set_path(wf, "11.inputs.text", neg)
        set_path(wf, "12.inputs.width", w)
        set_path(wf, "12.inputs.height", h)
        set_path(wf, "13.inputs.seed", s.get("seed", seed0 + i * 7))
        set_path(wf, "15.inputs.filename_prefix",
                 f"{outdir.split('output/')[1]}/keyframes/{s['id']}")
        print(f"  > {s['id']}{'  [20-step]' if hard else ''}")
        run(HOST, wf, quiet=True)


# ------------------------------------------------------------------ stage 2
def shot_len(s, film, fps):
    """LTX needs 8n+1 frames. Per-shot `seconds` overrides the film default -
    varying shot length is what gives the cut a rhythm instead of a metronome."""
    secs = float(s.get("seconds", film.get("seconds", 4)))
    return max(9, int(round(secs * fps / 8)) * 8 + 1)


def clips(film, outdir, seed0, hd=False):
    vw, vh = VID["16:9-hd" if hd else "16:9"]
    fps = int(film.get("fps", 24))
    chars = film.get("characters", {})
    lens = [shot_len(s, film, fps) for s in film["shots"]]
    print(f"\n=== STAGE 2: {len(film['shots'])} clips @ {vw}x{vh} via LTX-2.3 i2v "
          f"({min(lens)}-{max(lens)}f, {sum(lens)/fps:.0f}s total) ===")
    for i, s in enumerate(film["shots"]):
        length = lens[i]
        if os.path.exists(f"{outdir}/clips/{s['id']}_00001_.mp4"):
            print(f"  = {s['id']}")
            continue
        kf = f"{outdir}/keyframes/{s['id']}_00001_.png"
        if not os.path.exists(kf):
            raise SystemExit(f"missing keyframe {kf}")
        staged = f"cartoon_{s['id']}.png"
        shutil.copy(kf, f"{COMFY}/input/{staged}")

        wf = load_wf("12_ltx23_i2v_audio.json")
        set_path(wf, "8.inputs.image", staged)
        set_path(wf, "10.inputs.text", expand(s["motion"], chars))
        set_path(wf, "20.inputs.width", vw)
        set_path(wf, "20.inputs.height", vh)
        set_path(wf, "20.inputs.length", length)
        set_path(wf, "21.inputs.frames_number", length)
        set_path(wf, "32.inputs.noise_seed", seed0 + i * 13)
        set_path(wf, "43.inputs.filename_prefix",
                 f"{outdir.split('output/')[1]}/clips/{s['id']}")
        print(f"  > {s['id']}  ({i+1}/{len(film['shots'])}) {length}f")
        run(HOST, wf, quiet=True)


# --------------------------------------------------------------- stage 2b
def sfx(film, outdir, seed0):
    """Per-shot sound design from Stable Audio 3, layered over LTX's own ambience.
    LTX generates *a* soundscape but it has no idea what a ticket punch is; naming
    the sound explicitly is what makes a cut feel designed rather than generated."""
    want = [s for s in film["shots"] if s.get("sfx")]
    if not want:
        return
    print(f"\n=== STAGE 2b: {len(want)} sound effects ===")
    os.makedirs(f"{outdir}/sfx", exist_ok=True)
    fps = int(film.get("fps", 24))
    for i, s in enumerate(want):
        if os.path.exists(f"{outdir}/sfx/{s['id']}_00001.mp3"):
            print(f"  = {s['id']}")
            continue
        secs = max(6.0, shot_len(s, film, fps) / fps + 1.5)
        wf = load_wf("10_stableaudio_sfx.json")
        set_path(wf, "3.inputs.text", s["sfx"] + ", no music, no speech")
        set_path(wf, "5.inputs.seconds", round(secs, 1))
        set_path(wf, "6.inputs.seed", seed0 + i * 31)
        set_path(wf, "8.inputs.filename_prefix",
                 f"{outdir.split('output/')[1]}/sfx/{s['id']}")
        print(f"  > {s['id']}: {s['sfx'][:56]}...")
        run(HOST, wf, quiet=True)


# --------------------------------------------------------------- stage 2c
def music(film, outdir, seed0):
    """Multiple cues instead of one bed. A single 90-second loop cannot be tense
    during the investigation and warm at the reveal - three cues can."""
    cues = film.get("music", [])
    if not cues:
        return
    print(f"\n=== STAGE 2c: {len(cues)} music cues ===")
    for i, c in enumerate(cues):
        if os.path.exists(f"{outdir}/music/{c['prefix']}_00001.mp3"):
            print(f"  = {c['prefix']}")
            continue
        wf = load_wf("06_acestep_music.json")
        set_path(wf, "10.inputs.tags", c["tags"])
        set_path(wf, "10.inputs.lyrics", c.get("lyrics", ""))
        set_path(wf, "10.inputs.bpm", int(c.get("bpm", 90)))
        set_path(wf, "10.inputs.keyscale", c.get("key", "C minor"))
        set_path(wf, "10.inputs.duration", float(c.get("seconds", 40)))
        set_path(wf, "11.inputs.seconds", float(c.get("seconds", 40)))
        set_path(wf, "10.inputs.seed", seed0 + i * 41)
        set_path(wf, "12.inputs.seed", seed0 + i * 41)
        set_path(wf, "14.inputs.filename_prefix",
                 f"{outdir.split('output/')[1]}/music/{c['prefix']}")
        print(f"  > {c['prefix']} @ {c.get('at',0)}s ({c.get('seconds',40)}s)")
        run(HOST, wf, quiet=True)


# ------------------------------------------------------------------ stage 3
def voices(film, outdir, seed0):
    vo = film.get("voices", {})
    lines = [(s["id"], s["line"]) for s in film["shots"] if s.get("line")]
    print(f"\n=== STAGE 3: {len(lines)} voice lines ===")
    os.makedirs(f"{outdir}/voice", exist_ok=True)
    for i, (sid, line) in enumerate(lines):
        final = f"{outdir}/voice/{sid}.mp3"
        if os.path.exists(final):
            print(f"  = {sid} ({line['who']})")
            continue
        cfg = vo.get(line["who"], {})

        # Clamp to ChatterboxTTS's declared ranges. An out-of-range value is a hard
        # server-side validation error (HTTP 500) that aborts the entire run - and
        # exaggeration's floor of 0.25 is very easy to undershoot by accident when
        # you are reaching for a flat, affectless delivery.
        def clamp(key, default, lo, hi):
            return max(lo, min(hi, float(cfg.get(key, default))))

        wf = load_wf("08_chatterbox_tts.json")
        set_path(wf, "1.inputs.text", line["text"])
        set_path(wf, "1.inputs.exaggeration", clamp("exaggeration", 0.5, 0.25, 2.0))
        set_path(wf, "1.inputs.cfg_weight", clamp("cfg_weight", 0.45, 0.2, 1.0))
        set_path(wf, "1.inputs.temperature", clamp("temperature", 0.8, 0.05, 5.0))
        set_path(wf, "1.inputs.seed", seed0 + i * 17)
        set_path(wf, "2.inputs.filename_prefix",
                 f"{outdir.split('output/')[1]}/voice/raw_{sid}")
        print(f"  > {sid} ({line['who']}): {line['text'][:52]}...")
        _, outs = run(HOST, wf, quiet=True)
        raw = wait_for(os.path.join(COMFY, "output", outs[0]))

        # Chatterbox ships a single voice pack, so characters are differentiated by
        # pitch. Use rubberband: it shifts pitch WITHOUT touching duration.
        #
        # Do not do this with asetrate/atempo. asetrate needs the file's real sample
        # rate, and Chatterbox writes 24 kHz - hardcoding 44100 here made every line
        # play 1.84x too fast, which silently wrecked the caption timings too.
        p = float(cfg.get("pitch", 1.0))
        rate = float(cfg.get("rate", 1.0))          # <1 = slower delivery
        chain = []
        if abs(p - 1.0) >= 0.01:
            chain.append(f"rubberband=pitch={p}")
        if abs(rate - 1.0) >= 0.01:
            chain.append(f"rubberband=tempo={rate}")
        # an arbitrary extra ffmpeg chain per character - e.g. band-limit plus
        # bit-crush to make a voice sound like it is coming over a radio
        if cfg.get("filter"):
            chain.append(cfg["filter"])
        chain.append("dynaudnorm=f=250:g=7")
        sh("ffmpeg", "-y", "-v", "error", "-i", raw,
           "-af", ",".join(chain), "-ar", "48000", "-b:a", "256k", final)
    return lines


# ------------------------------------------------------------------ stage 4
def srt_time(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    # NB: format the float directly. int(s) here would silently truncate every
    # cue to a whole second (and .000 milliseconds), which is easy to miss.
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def wrap(text, width=42):
    words, out, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    out.append(cur)
    return "\n".join(out[:2]) if len(out) <= 2 else "\n".join([out[0], " ".join(out[1:])])


def edit(film, outdir, hd=False):
    vw, vh = VID["16:9-hd" if hd else "16:9"]
    fps = int(film.get("fps", 24))
    trans = float(film.get("transition", 0.5))
    work = f"{outdir}/_work"
    os.makedirs(work, exist_ok=True)

    def card(text, sub, seconds, path):
        fsz, ssz = max(30, vw // 20), max(16, vw // 48)
        esc = lambda t: t.replace("'", "").replace(":", r"\:")
        a = (f"if(lt(t,0.7),t/0.7,if(lt(t,{seconds-0.7}),1,({seconds}-t)/0.7))")
        ff = f"fontfile='{fgpath(FONT)}':" if FONT else ""
        vf = (f"drawtext={ff}text='{esc(text)}':fontcolor=white:fontsize={fsz}:"
              f"x=(w-text_w)/2:y=(h-text_h)/2-{vh//28}:alpha='{a}'")
        if sub:
            vf += (f",drawtext={ff}text='{esc(sub)}':fontcolor=0xAAAAAA:fontsize={ssz}:"
                   f"x=(w-text_w)/2:y=(h+text_h)/2+{vh//20}:alpha='{a}'")
        sh("ffmpeg", "-y", "-v", "error", "-f", "lavfi",
           "-i", f"color=c=black:s={vw}x{vh}:d={seconds}:r={fps}",
           "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo:d={seconds}",
           "-vf", vf, "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", path)

    # --- assemble the segment list, and the caption timeline alongside it -----
    segs, cues, t = [], [], 0.0
    title = f"{work}/000_title.mp4"
    card(film["title"], film.get("subtitle", ""), 3.0, title)
    segs.append(title)
    t += 3.0 - trans

    for s in film["shots"]:
        src = f"{outdir}/clips/{s['id']}_00001_.mp4"
        if not os.path.exists(src):
            print(f"  ! missing clip {s['id']}", file=sys.stderr)
            continue
        dst = f"{work}/{s['id']}.mp4"
        vpath = f"{outdir}/voice/{s['id']}.mp3"

        spath = f"{outdir}/sfx/{s['id']}_00001.mp3"
        has_v, has_s = os.path.exists(vpath), os.path.exists(spath)
        cd = dur(src)
        lead, tail = 0.35, 0.45

        ins = ["-i", src]
        mix, n = [], 1
        if has_s:
            ins += ["-i", spath]
            sfx_i = n
            n += 1
        if has_v:
            ins += ["-i", vpath]
            vo_i = n
            n += 1

        # A 4 s shot cannot hold a 5.5 s line. Rather than re-render the clip,
        # freeze the last frame for the shortfall - keeps picture and dialogue in
        # sync for free, and these shots are near-static anyway.
        vd = dur(vpath) if has_v else 0.0
        need = lead + vd + tail if has_v else cd
        pad = max(0.0, need - cd)
        total_a = max(cd, need)
        vfilt = f"tpad=stop_mode=clone:stop_duration={pad:.2f}" if pad > 0.05 else "null"

        # Optional "on twos" cadence. Hand-drawn animation is usually shot on twos or
        # threes - 12 or 8 distinct drawings per second - and that stepped motion is a
        # large part of why anime does not read as live action. Decimating to `step_print`
        # fps and then back up to `fps` duplicates frames to reproduce it. Only do this
        # for a 2D style; on the 3D films it just looks like dropped frames.
        step = int(film.get("step_print", 0))
        if step and step < fps:
            vfilt += f",fps={step},fps={fps}"

        # LTX's own audio sits lowest, then the designed SFX, then dialogue on top.
        amb_lvl = 0.16 if has_s else (0.28 if has_v else 0.55)
        mix.append(f"[0:a]volume={amb_lvl},apad=pad_dur={pad + 0.2:.2f}[amb]")
        labels = ["[amb]"]
        if has_s:
            mix.append(f"[{sfx_i}:a]atrim=0:{total_a:.2f},asetpts=N/SR/TB,"
                       f"volume={0.55 if has_v else 0.9},"
                       f"afade=t=out:st={max(0.1, total_a-0.6):.2f}:d=0.6[sx]")
            labels.append("[sx]")
        if has_v:
            ms = int(lead * 1000)
            mix.append(f"[{vo_i}:a]volume=1.8,adelay={ms}|{ms}[vo]")
            labels.append("[vo]")
        if len(labels) == 1:
            mix.append("[amb]anull[a]")
        else:
            mix.append("".join(labels) +
                       f"amix=inputs={len(labels)}:duration=longest:normalize=0[a]")

        sh("ffmpeg", "-y", "-v", "error", *ins, "-filter_complex",
           f"[0:v]{vfilt}[v];" + ";".join(mix),
           "-map", "[v]", "-map", "[a]", "-t", f"{total_a:.2f}",
           "-r", str(fps), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", dst)

        if has_v:
            cues.append((t + lead, t + lead + vd + 0.3, s["line"]["who"],
                         s["line"]["text"], film.get("voices", {})
                         .get(s["line"]["who"], {}).get("radio", False)))
        segs.append(dst)
        t += dur(dst) - trans

    end = f"{work}/999_end.mp4"
    card("fin", "", 3.0, end)
    segs.append(end)

    # --- write the SRT -------------------------------------------------------
    srt = f"{outdir}/{film['title'].lower().replace(' ', '-')}.srt"
    with open(srt, "w", encoding="utf-8") as f:
        for i, (a, b, who, text, radio) in enumerate(cues, 1):
            body = wrap(text)
            # subtitle convention: an off-screen / radio voice is italicised
            line = f"<i>{who}: {body}</i>" if radio else f"{who}: {body}"
            f.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{line}\n\n")
    print(f"  captions -> {srt} ({len(cues)} cues)")

    # --- xfade chain ---------------------------------------------------------
    durs = [dur(p) for p in segs]
    args = []
    for p in segs:
        args += ["-i", p]
    filt, prev, ap, off = [], "0:v", "0:a", 0.0
    for i in range(1, len(segs)):
        off += durs[i - 1] - trans
        filt.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={trans}:"
                    f"offset={off:.3f}[x{i}]")
        filt.append(f"[{ap}][{i}:a]acrossfade=d={trans}[y{i}]")
        prev, ap = f"x{i}", f"y{i}"
    total = sum(durs) - trans * (len(segs) - 1)

    slug = film["title"].lower().replace(" ", "-")
    nosub = f"{outdir}/{slug}_nosubs.mp4"
    filt.append(f"[{prev}]fade=t=in:st=0:d=1,fade=t=out:st={total-1.2:.3f}:d=1.2,"
                f"format=yuv420p[v]")
    print(f"\n=== STAGE 4: {len(segs)} segments -> {total:.1f}s ===")
    sh("ffmpeg", "-y", "-v", "error", *args,
       "-filter_complex", ";".join(filt), "-map", "[v]", "-map", f"[{ap}]",
       "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", nosub)

    # --- lay the music cues in at their timecodes ----------------------------
    cuelist = film.get("music", [])
    have = [(c, f"{outdir}/music/{c['prefix']}_00001.mp3") for c in cuelist]
    have = [(c, p) for c, p in have if os.path.exists(p)]
    if have:
        scored = f"{outdir}/{slug}_scored.mp4"
        ins, filt, labels = ["-i", nosub], [], ["[base]"]
        filt.append("[0:a]volume=1.0[base]")
        for i, (c, p) in enumerate(have, 1):
            ins += ["-i", p]
            at = float(c.get("at", 0))
            cd2 = dur(p)
            # fade each cue in and out so consecutive cues overlap rather than cut
            filt.append(
                f"[{i}:a]volume={c.get('level', 0.30)},"
                f"afade=t=in:st=0:d=2.0,"
                f"afade=t=out:st={max(0.1, cd2 - 3.0):.2f}:d=3.0,"
                f"adelay={int(at*1000)}|{int(at*1000)}[m{i}]")
            labels.append(f"[m{i}]")
        filt.append("".join(labels) +
                    f"amix=inputs={len(labels)}:duration=first:normalize=0,"
                    f"dynaudnorm=f=300:g=9[a]")
        sh("ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(filt),
           "-map", "0:v", "-map", "[a]", "-c:v", "copy",
           "-c:a", "aac", "-b:a", "256k", "-t", f"{total:.2f}",
           "-movflags", "+faststart", scored)
        print(f"  music: {len(have)} cues laid in")
        nosub = scored

    # --- burn the captions in ------------------------------------------------
    # A wordless film produces no cues. libass on an empty SRT is a hard failure,
    # and there would be nothing to draw anyway, so the scored cut IS the deliverable.
    if not cues:
        print(f"\n>>> {nosub}   ({total:.1f}s, {vw}x{vh}) - wordless, no captions")
        return nosub

    final = f"{outdir}/{slug}_captioned.mp4"
    # libass matches on family name, so the name has to agree with whatever FONT is.
    fontname = os.environ.get(
        "CARD_FONT_NAME",
        "Arial" if FONT.lower().endswith(("arial.ttf", "arialbd.ttf")) else "DejaVu Sans")
    style = (f"FontName={fontname},Fontsize=19,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,"
             "Alignment=2,MarginV=28,Bold=1")
    subarg = f"subtitles={os.path.basename(srt)}"
    if FONT:
        subarg += f":fontsdir='{fgpath(os.path.dirname(FONT))}'"
    subarg += f":force_style='{style}'"
    # Pass the SRT as a bare filename with cwd=outdir. An absolute path inside a
    # filtergraph has to have its separators escaped, and on Windows the drive-letter
    # colon in "Z:/..." parses as the filter's own option separator and fails outright.
    sh("ffmpeg", "-y", "-v", "error", "-i", nosub, "-vf", subarg,
       "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p",
       "-c:a", "copy", "-movflags", "+faststart", final, cwd=outdir)
    print(f"\n>>> {final}   ({total:.1f}s, {vw}x{vh})")
    print(f">>> {nosub}   (same cut, no burnt-in captions)")
    return final


def main():
    p = argparse.ArgumentParser()
    p.add_argument("film")
    p.add_argument("--stage", default="all",
                   choices=["all", "keyframes", "clips", "sfx", "music",
                            "voices", "audio", "edit"])
    p.add_argument("--seed", type=int, default=3000)
    p.add_argument("--hd", action="store_true", help="1280x704 clips instead of 768x512")
    a = p.parse_args()

    film = json.load(open(a.film))
    slug = film["title"].lower().replace(" ", "-")
    outdir = f"{COMFY}/output/claude-generated/11-short-film/{slug}"
    for d in ("keyframes", "clips", "voice", "sfx", "music"):
        os.makedirs(f"{outdir}/{d}", exist_ok=True)

    if a.stage in ("all", "keyframes"):
        keyframes(film, outdir, a.seed)
    if a.stage in ("all", "clips"):
        clips(film, outdir, a.seed, a.hd)
    # audio stages are grouped: each loads a different model, so running them
    # back to back pays each model load once instead of once per shot
    if a.stage in ("all", "audio", "sfx"):
        sfx(film, outdir, a.seed)
    if a.stage in ("all", "audio", "music"):
        music(film, outdir, a.seed)
    if a.stage in ("all", "audio", "voices"):
        voices(film, outdir, a.seed)
    if a.stage in ("all", "edit"):
        edit(film, outdir, a.hd)


if __name__ == "__main__":
    main()
