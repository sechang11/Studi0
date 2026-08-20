#!/usr/bin/env python3
"""
epic.py - long-form NARRATED film. All motion: no still cards, no freeze-frame padding.

    python3 epic.py films/chrono.json                    # everything
    python3 epic.py films/chrono.json --stage narrate    # just the voice track
    python3 epic.py films/chrono.json --stage edit       # re-cut only

Four things differ from cartoon.py, and every one of them is forced by going long
and narrated rather than short and dialogued:

1. NARRATION FIRST, then picture sized to fit it.
   cartoon.py renders a fixed-length clip and, if the line overruns, freezes the last
   frame to cover the shortfall (`tpad=stop_mode=clone`). That is invisible on a 4-second
   dialogue beat and catastrophic over ten narrated minutes - it would produce minutes of
   still image. So stage 1 speaks every line, measures it with ffprobe, and stage 3
   derives each shot's frame count from that real duration. Nothing ever needs padding.

2. NO CARDS. Titles are drawn over moving footage, not over black.

3. CHUNKED EDIT. cartoon.py builds one xfade chain over every segment. At ~25 segments
   that is fine; at 90+ the filtergraph becomes enormous and ffmpeg's memory use with it.
   We build per-chunk reels and then join the reels - mathematically the same dissolve at
   every boundary, but no single graph is ever large.

4. LONG SHOTS ARE NEARLY FREE, so we use them. LTX charges about the same for 193 frames
   as for 97 (13.7s vs 13.5s measured), while each extra shot costs a whole keyframe plus
   a whole clip. Sizing shots to the narration therefore makes the film *cheaper* per
   minute than short-shot cutting would, not more expensive.

Style comes from a LoRA stacked on the Lightning LoRA (workflow 13), set per film via
`style_lora` / `style_strength`.
"""
import argparse
import collections
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COMFY = os.environ.get("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))

# Refuse to run if COMFY is not a real ComfyUI install. Every ComfyUI path in this repo is
# built by interpolating COMFY, and a wrong root fails SILENTLY: os.path.exists() returns
# False and glob() returns [] against a directory that is simply not there, so renders
# "succeed" while the tool reports its own output missing and its LoRAs gone. That is
# strictly worse than not starting. This is not hypothetical - any module that imported
# analyze_shots before epic used to inherit COMFY_ROOT="Z:/ComfyUI" (the Windows SMB path),
# which on Linux is a relative path existing nowhere; it cost terra_wardrobe.py a full
# 40-render pass. See the note in analyze_shots.py.
#
# The sentinel is models/ rather than models/loras: every ComfyUI install has models/,
# whereas a valid install that has never had a LoRA added would trip a models/loras check
# even though epic.py itself only ever writes to input/, output/ and temp/. models/ catches
# the real failure (root does not exist at all) with no false positives.
#
# This is checked even when COMFY_ROOT was set explicitly - an explicit but wrong value is
# exactly the failure being caught. Driving a genuine remote install still works: the check
# passes as long as that root is actually reachable at this path.
if not os.path.isdir(os.path.join(COMFY, "models")):
    _src = "COMFY_ROOT" if os.environ.get("COMFY_ROOT") else "the ~/ComfyUI default"
    raise SystemExit(f"""epic.py: COMFY_ROOT={COMFY!r} is not a ComfyUI install (no models/ directory).
  value came from: {_src}
  Refusing to import, because every path here derives from this root, and a bad root
  fails silently rather than loudly - empty globs, renders that report their own
  output missing.
  Fix: export COMFY_ROOT=/path/to/ComfyUI, or unset it to use ~/ComfyUI.""")
sys.path.insert(0, HERE)
from comfy import run, set_path  # noqa: E402

HOST = os.environ.get("COMFY_HOST", "127.0.0.1:8188")
AR = {"16:9": (1664, 928), "9:16": (928, 1664), "1:1": (1328, 1328)}
VID = {"16:9": (768, 512), "16:9-hd": (1280, 704)}

NEG_IMG = ("blurry, low quality, watermark, text, caption, signature, jpeg artifacts, "
           "deformed, extra limbs, photorealistic, photograph, 3d render, live action")

LEAD, TAIL = 0.30, 0.75      # default air before / after each line; `tail` overrides
FRAME_CAP = 241              # 10.0s at 24fps - LTX's practical ceiling before drift
CHUNK = 10                   # segments per reel in the chunked edit


def sh(*a, **kw):
    r = subprocess.run(a, capture_output=True, text=True, **kw)
    if r.returncode:
        print(r.stderr[-3000:], file=sys.stderr)
        raise SystemExit(f"failed: {a[0]}")
    return r.stdout


def dur(path):
    """Duration of the VIDEO stream when there is one.

    Do not use format=duration here: it is max(video, audio), and AAC encoder padding
    makes the audio stream up to ~20 ms longer than the picture in every segment. Summed
    across a chunk that drifts xfade offsets late, and on a finished master it made the
    computed total ~200 ms long - enough that `fade=t=out:st=total-1.5` lands past the end
    and the film silently has no fade-out at all.
    """
    out = sh("ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=duration", "-of", "default=nw=1:nk=1", path).strip()
    if out and out != "N/A":
        return float(out)
    return float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=nw=1:nk=1", path).strip())


def adur(path):
    """Duration of an audio-only file (narration, sfx, music)."""
    return float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=nw=1:nk=1", path).strip())


VOICE_LUFS = -20.0    # every narration line normalised to the same integrated loudness
MUSIC_LUFS = -26.0    # ACE-Step output spreads >20 LU; normalise, then trim with `level`
AMB_LUFS = -34.0      # LTX's own bed spreads ~39 dB across clips; pin it
AMB_LUFS_BARE = -28.0  # ... a little louder on shots with no narration over them
SFX_LUFS = -30.0      # designed effects. Open task #46: Stable Audio output was never
                      # normalised at all, so a bang and a footstep arrived 20 dB apart
                      # and the only control over either was one fixed multiplier.
# Sidechain settings per stem, keyed off the narration. Effects duck HARDER and start
# ducking SOONER than score: a pad under a word is a mix choice, a door slam under a word
# is a mistake. threshold, ratio.
DUCK = {"mus": (0.15, 4), "sfx": (0.10, 8)}


def measure(path, pre=""):
    """Two-pass loudnorm measurement. Returns the measured_* dict, or {} on failure.

    The measurement pass MUST include any filters that will be applied before loudnorm in
    the real render, or `linear=true` normalises against the wrong input and lands several
    dB off.
    """
    af = (pre + "," if pre else "") + "loudnorm=print_format=json"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", af, "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r'"(input_i|input_tp|input_lra|input_thresh)"\s*:\s*"([-\d.]+)"',
                   r.stderr or "")
    return dict(m) if len(m) == 4 else {}


def norm_to(src, dst, lufs, tp=-2.0, pre="", extra=""):
    """Normalise `src` to an exact integrated loudness with a genuine two-pass loudnorm.

    Single-pass loudnorm is adaptive: it rides the gain, misses the integrated target by
    ~1 dB, never honours LRA, and overshoots the true peak (measured +1.6 dBTP when asked
    for -1.5). Two-pass with linear=true hits it and stays linear.
    """
    d = measure(src, pre)
    ln = f"loudnorm=I={lufs}:TP={tp}:LRA=11"
    if d:
        ln += (f":linear=true:measured_I={d['input_i']}:measured_TP={d['input_tp']}"
               f":measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}")
    af = ",".join(x for x in [pre, ln, extra] if x)
    args = ["ffmpeg", "-y", "-v", "error", "-i", src, "-af", af, "-ar", "48000"]
    if dst.endswith(".wav"):
        args += ["-ac", "2"]
    else:
        args += ["-b:a", "256k"]
    sh(*args, dst)
    return dst


def audio_lufs(path):
    d = measure(path)
    return float(d["input_i"]) if d else None


def ensure_local(rel, dest, required=False):
    """Guarantee `dest` exists here, pulling it from the server if the share hasn't got it.

    Do not read server-written files straight off the SMB share. It has been measured
    minutes behind the API, and for some directories it never caught up at all inside a
    render - which silently looks identical to "the job failed". ComfyUI's /view endpoint
    is authoritative, so anything we need to read we fetch over HTTP and keep locally.

    `rel` is the path as ComfyUI reports it, e.g. "claude-generated/.../clips/x_00001_.mp4".
    """
    if os.path.exists(dest):
        return dest
    sub, _, name = rel.rpartition("/")
    q = urllib.parse.urlencode({"filename": name, "subfolder": sub, "type": "output"})
    try:
        with urllib.request.urlopen(f"http://{HOST}/view?{q}", timeout=300) as r:
            data = r.read()
    except Exception as e:
        if required:
            raise SystemExit(f"cannot fetch {rel} from the server: {e}")
        return None
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)
    return dest


def submit(wf):
    """Queue a workflow and return immediately with its prompt id."""
    req = urllib.request.Request(
        f"http://{HOST}/prompt",
        data=json.dumps({"prompt": wf, "client_id": "epic"}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())["prompt_id"]


def wait_all(pids, label="jobs"):
    """Wait for a whole batch of queued prompts.

    Submitting the batch up front rather than one-at-a-time matters when the box is
    shared: ComfyUI runs its queue FIFO, so a batch stays contiguous and the model loads
    once. Interleaving with another session's jobs of a different model family costs a
    25-90s reload on every single alternation, which over 100 clips dwarfs the render.
    """
    left, t0, last = dict.fromkeys(pids), time.time(), -1
    while left:
        time.sleep(6)
        try:
            h = json.load(urllib.request.urlopen(
                f"http://{HOST}/history?max_items=600", timeout=60))
        except Exception:
            continue
        for pid in list(left):
            e = h.get(pid)
            if not e:
                continue
            st = e.get("status", {})
            if st.get("status_str") == "error":
                print(f"  ! {pid} FAILED", file=sys.stderr)
                for m in st.get("messages", [])[-3:]:
                    print(f"    {m}", file=sys.stderr)
                left.pop(pid, None)
            elif st.get("completed"):
                left.pop(pid, None)
        done = len(pids) - len(left)
        if done != last:
            print(f"  [{time.time()-t0:6.0f}s] {label} {done}/{len(pids)}", flush=True)
            last = done


def load_wf(name):
    """Delegates to engine.load_wf (Phase 2 tail) - proven byte-identical over every
    workflow on disk before the inline read was deleted. short.py and cartoon.py import
    this name from here, so all twenty film-script call sites read the one copy."""
    sys.path.insert(0, f"{ROOT}/studio")
    from engine import load_wf as _load_wf
    return _load_wf(name)


def _set_neg(wf, text, positive=""):
    """The negative reaches the graph (see engine.set_negative). Lazy import keeps
    epic's own import surface unchanged for the tools that import FROM it."""
    sys.path.insert(0, f"{ROOT}/studio")
    from engine import set_negative
    return set_negative(wf, text, positive=positive)


def expand(text, chars):
    for name, desc in chars.items():
        text = text.replace("{" + name + "}", desc)
    return text


def _find_font():
    if os.environ.get("CARD_FONT"):
        return os.environ["CARD_FONT"]
    for p in ("C:/Windows/Fonts/arialbd.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf",
              "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if os.path.exists(p):
            return p
    # ASK the system rather than guess. All three original paths were absent here, so
    # FONT was "" and every text layer in every film fell back to whatever ffmpeg chose -
    # which draws latin text fine and drew THE LIFESPAN's infinity payoff as an empty box.
    try:
        import subprocess as _sp
        for q in ("DejaVu Sans:bold", "Liberation Sans:bold", "sans-serif"):
            r = _sp.run(["fc-match", "-f", "%{file}", q], capture_output=True, text=True)
            f = (r.stdout or "").strip()
            if f and os.path.exists(f):
                return f
    except Exception:
        pass
    return ""


FONT = _find_font()


def fgpath(p):
    return p.replace("\\", "/").replace(":", r"\:")


def ffesc(t):
    """escape text for drawtext"""
    return t.replace("\\", "").replace("'", "").replace(":", r"\:").replace("%", r"\%")


# ------------------------------------------------------------------ stage 1
def narrate(film, outdir, seed0):
    """Speak every line, then normalise and measure it. Must run before `clips`."""
    vo = film.get("voices", {})
    # ComfyUI wipes its temp dir on startup, and IndexTTS-2 writes a scratch wav there
    # without creating the folder - so every restart re-breaks it with a FileNotFoundError
    # on a tmp path that reads like a bug in the node. Recreate it before we start.
    try:
        os.makedirs(f"{COMFY}/temp", exist_ok=True)
    except Exception as e:
        print(f"  ! could not ensure {COMFY}/temp: {e}", file=sys.stderr)
    lines = [s for s in film["shots"] if s.get("say")]
    print(f"\n=== STAGE 1: {len(lines)} narration lines ===")
    os.makedirs(f"{outdir}/voice", exist_ok=True)
    for i, s in enumerate(lines):
        final = f"{outdir}/voice/{s['id']}.mp3"
        if os.path.exists(final):
            continue
        who = s.get("who", "NARRATOR")
        cfg = vo.get(who, {})
        # A character is cast by pointing at a distinct REFERENCE VOICE, never by
        # pitch-shifting one voice pack. Rubberband past about +/-10% wrecks formants, and
        # the first cut of this film used 0.70 and 0.55 - which is why five characters
        # sounded like one actor on a varispeed tape.
        engine = cfg.get("engine", film.get("engine", "higgs_v3"))
        if engine == "indextts2":
            # directed performance: 8 blendable emotion dimensions
            wf = load_wf("16_indextts2_voice.json")
            for k in ("Happy", "Angry", "Sad", "Surprised", "Afraid", "Disgusted",
                      "Calm", "Melancholic"):
                set_path(wf, f"20.inputs.{k}", float((cfg.get("emotion") or {}).get(k, 0.0)))
            set_path(wf, "10.inputs.emotion_alpha", float(cfg.get("emotion_alpha", 1.0)))
        else:
            wf = load_wf("17_higgs_v3_voice.json")   # house engine: most natural reads
        set_path(wf, "30.inputs.text", s["say"])
        set_path(wf, "30.inputs.narrator_voice", cfg["voice"])
        set_path(wf, "30.inputs.seed", seed0 + i * 17)
        set_path(wf, "40.inputs.filename_prefix",
                 f"{outdir.split('output/')[1]}/voice/raw_{s['id']}")
        print(f"  > {s['id']} ({who}/{engine}): {s['say'][:48]}...", flush=True)
        _, outs = run(HOST, wf, quiet=True)
        rel = outs[0] if outs else f"{outdir.split('output/')[1]}/voice/raw_{s['id']}_00001.mp3"
        raw = ensure_local(rel, f"{outdir}/voice/_raw_{s['id']}.mp3", required=True)

        chain = []
        if cfg.get("filter"):
            chain.append(cfg["filter"])
        # NOT dynaudnorm: it only has ~1s of context, and measured over 100 lines it made
        # line-to-line spread WORSE (3.9 -> 5.8 LU), hitting the short punchy lines
        # hardest - so "It works." and "Lavos answers." came out 3-4 dB under everything
        # else. Compress, then normalise to a fixed LUFS target so every line matches.
        chain.append("acompressor=threshold=-20dB:ratio=3:attack=5:release=140:makeup=1")
        norm_to(raw, final, VOICE_LUFS, tp=-4.0, pre=",".join(chain))
    # cache measured durations so later stages don't re-probe the share repeatedly
    durs = {s["id"]: round(dur(f"{outdir}/voice/{s['id']}.mp3"), 3) for s in lines}
    json.dump(durs, open(f"{outdir}/narration.json", "w"), indent=1)
    total = sum(durs.values())
    print(f"  narration total {total:.1f}s over {len(durs)} lines")
    return durs


def narration_durs(outdir):
    p = f"{outdir}/narration.json"
    return json.load(open(p)) if os.path.exists(p) else {}


def shot_frames(s, film, fps, ndur):
    """Frame count for a shot: enough to hold its narration, quantised to LTX's 8n+1."""
    if s["id"] in ndur:
        secs = LEAD + ndur[s["id"]] + float(film.get("tail", TAIL))
    else:
        secs = float(s.get("seconds", film.get("seconds", 5)))
    n = max(9, int(math.ceil(secs * fps / 8)) * 8 + 1)
    return min(n, FRAME_CAP)


# ------------------------------------------------------------------ stage 2
def part_frames(s, film, fps, ndur):
    """Frame counts for a shot, split across `chain` clips.

    A single LTX clip tops out around FRAME_CAP (241f / 10s) before it drifts. A chained
    shot deliberately exceeds that: each part starts from the previous part's LAST FRAME,
    so the motion runs straight through and the joins are invisible. `chain: 4` at 8s a
    part is a 32-second continuous take, which is what an action set-piece needs and what
    a single clip cannot give you.
    """
    n = max(1, int(s.get("chain", 1)))
    # `seconds` is a FLOOR, not an alternative. An action beat needs room to play whether
    # or not a line happens to sit over it, so an explicit `seconds` wins when it is longer
    # than the narration needs - otherwise a 30s chained fight with a 4-word line over it
    # would collapse to four seconds.
    need = 0.0
    if s["id"] in ndur:
        need = LEAD + ndur[s["id"]] + float(film.get("tail", TAIL))
    secs = max(need, float(s.get("seconds", film.get("seconds", 5))))
    if n == 1:
        f = min(max(9, int(math.ceil(secs * fps / 8)) * 8 + 1), FRAME_CAP)
        return [f]
    per = secs / n
    f = min(max(9, int(math.ceil(per * fps / 8)) * 8 + 1), FRAME_CAP)
    return [f] * n


def clip_parts(outdir, s):
    """Every clip file that makes up one shot, in order."""
    n = max(1, int(s.get("chain", 1)))
    out = [f"{outdir}/clips/{s['id']}_00001_.mp4"]
    out += [f"{outdir}/clips/{s['id']}__p{i}_00001_.mp4" for i in range(2, n + 1)]
    return out


def last_frame(clip, dest):
    """Grab the true final frame. -sseof -0.08 lands ~2 frames early at 24fps, which puts
    a visible hiccup at a join designed to be invisible; decode the last second and keep
    overwriting instead."""
    sh("ffmpeg", "-y", "-v", "error", "-sseof", "-1", "-i", clip,
       "-update", "1", "-frames:v", "100", dest)
    return dest


def keyframes(film, outdir, seed0):
    w, h = AR[film.get("ar", "16:9")]
    chars, style = film.get("characters", {}), film.get("style", "")
    lora = film.get("style_lora")
    print(f"\n=== STAGE 2: {len(film['shots'])} keyframes @ {w}x{h}"
          f"{' + ' + lora if lora else ''} ===")
    for i, s in enumerate(film["shots"]):
        if os.path.exists(f"{outdir}/keyframes/{s['id']}_00001_.png"):
            continue
        refs = s.get("ref") or []
        if refs:
            # Reference-locked: the character sheets carry the face so it is not
            # re-invented from words. Empty latent at target res, denoise 1.0 - a
            # VAEEncoded reference would force the output to the sheet's aspect.
            wf = load_wf("14_qwen_edit_ref.json")
            sheets = film.get("sheets", {})
            for n_, key in enumerate(refs[:3], start=1):
                img = sheets.get(key)
                if not img:
                    raise SystemExit(f"{s['id']}: no sheet registered for ref {key!r}")
                node = {1: "8", 2: "9", 3: "16"}[n_]
                if node not in wf:
                    wf[node] = {"class_type": "LoadImage",
                                "inputs": {"image": img, "upload": "image"}}
                set_path(wf, f"{node}.inputs.image", img)
                for enc in ("10", "11"):
                    wf[enc]["inputs"][f"image{n_}"] = [node, 0]
            for n_ in range(len(refs[:3]) + 1, 4):
                for enc in ("10", "11"):
                    wf[enc]["inputs"].pop(f"image{n_}", None)
            if lora:
                set_path(wf, "7.inputs.lora_name", lora)
                set_path(wf, "7.inputs.strength_model",
                         float(s.get("style_strength", film.get("style_strength", 0.0))))
            st_ = style[s.get("look", "default")] if isinstance(style, dict) else style
            set_path(wf, "10.inputs.prompt", f"{expand(s['prompt'], chars)}, {st_}")
            set_path(wf, "11.inputs.prompt", s.get("neg", NEG_IMG))
            set_path(wf, "20.inputs.width", w)
            set_path(wf, "20.inputs.height", h)
            set_path(wf, "13.inputs.seed", int(s.get("seed", seed0 + i * 7)))
            set_path(wf, "15.inputs.filename_prefix",
                     f"{outdir.split('output/')[1]}/keyframes/{s['id']}")
            print(f"  > {s['id']} ({i+1}/{len(film['shots'])}) ref={'+'.join(refs[:3])}",
                  flush=True)
            run(HOST, wf, quiet=True)
            continue
        wf = load_wf("13_qwen_t2i_styled.json" if lora else "01_qwen_t2i_turbo.json")
        if lora:
            set_path(wf, "7.inputs.lora_name", lora)
            # per-shot override: a storybook style LoRA at full strength hijacks the
            # palette of anything meant to be grey and dead, so cold acts run lower
            set_path(wf, "7.inputs.strength_model",
                     float(s.get("style_strength", film.get("style_strength", 0.9))))
        # `style` may be a dict of named variants; a shot picks one with "look".
        # One global style string ending in "vivid saturated colour, dramatic sky" is
        # asserted over every prompt and wins on exactly the shots that need it not to.
        st = style[s.get("look", "default")] if isinstance(style, dict) else style
        set_path(wf, "10.inputs.text", f"{expand(s['prompt'], chars)}, {st}")
        set_path(wf, "11.inputs.text", s.get("neg", NEG_IMG))
        set_path(wf, "12.inputs.width", w)
        set_path(wf, "12.inputs.height", h)
        # explicit per-shot seed, otherwise deleting a keyframe and re-running
        # reproduces it byte-identically and "re-roll this shot" is not an operation
        set_path(wf, "13.inputs.seed", int(s.get("seed", seed0 + i * 7)))
        if s.get("quality") and lora:
            # drop the 4-step Lightning LoRA and render properly: 4 steps at cfg 1.0
            # cannot resist a strong style block, and at cfg 1.0 the negative prompt
            # does nothing either. ~30s instead of ~5s - worth it on a hero frame.
            set_path(wf, "4.inputs.strength_model", 0.0)
            set_path(wf, "13.inputs.steps", 20)
            set_path(wf, "13.inputs.cfg", 2.5)
        set_path(wf, "15.inputs.filename_prefix",
                 f"{outdir.split('output/')[1]}/keyframes/{s['id']}")
        print(f"  > {s['id']} ({i+1}/{len(film['shots'])})", flush=True)
        run(HOST, wf, quiet=True)


# ------------------------------------------------------------------ stage 3
def i2v_wf(film, outdir, staged, motion, vw, vh, frames, seed, prefix):
    wf = load_wf("12_ltx23_i2v_audio.json")
    _set_neg(wf, str(film.get("negative") or ""), positive=str(motion or ""))
    set_path(wf, "8.inputs.image", staged)
    set_path(wf, "10.inputs.text", expand(motion, film.get("characters", {})))
    set_path(wf, "20.inputs.width", vw)
    set_path(wf, "20.inputs.height", vh)
    set_path(wf, "20.inputs.length", frames)
    set_path(wf, "21.inputs.frames_number", frames)
    set_path(wf, "32.inputs.noise_seed", seed)
    set_path(wf, "43.inputs.filename_prefix", prefix)
    idl = film.get("id_lora")
    if idl:
        # identity LoRA: holds a face through the clip, not just the keyframe. Matters most
        # on long chained takes and close-ups, which is exactly where drift would show.
        wf["50"] = {"class_type": "LoraLoaderModelOnly",
                    "inputs": {"model": wf["5"]["inputs"]["model"],
                               "lora_name": idl,
                               "strength_model": float(film.get("id_strength", 0.7))}}
        wf["5"]["inputs"]["model"] = ["50", 0]
    return wf


def clips(film, outdir, seed0, hd=True):
    vw, vh = VID["16:9-hd" if hd else "16:9"]
    fps = int(film.get("fps", 24))
    ndur = narration_durs(outdir)
    if not ndur:
        print("  ! no narration.json - run --stage narrate first", file=sys.stderr)
    plans = [part_frames(s, film, fps, ndur) for s in film["shots"]]
    tot = sum(sum(p) for p in plans)
    chained = sum(1 for p in plans if len(p) > 1)
    print(f"\n=== STAGE 3: {len(film['shots'])} shots @ {vw}x{vh} "
          f"({sum(len(p) for p in plans)} clips, {chained} chained, "
          f"{tot/fps:.0f}s of picture) ===")
    pids = []
    for i, s in enumerate(film["shots"]):
        if s.get("from_prev"):
            continue                      # needs the previous shot; done in stage 3b
        if os.path.exists(clip_parts(outdir, s)[0]):
            continue
        kf = ensure_local(f"{outdir.split('output/')[1]}/keyframes/{s['id']}_00001_.png",
                          f"{outdir}/keyframes/{s['id']}_00001_.png", required=True)
        staged = f"epic_{s['id']}.png"
        shutil.copy(kf, f"{COMFY}/input/{staged}")
        pids.append(submit(i2v_wf(film, outdir, staged, s["motion"], vw, vh, plans[i][0],
                                  seed0 + i * 13,
                                  f"{outdir.split('output/')[1]}/clips/{s['id']}")))
    print(f"  submitted {len(pids)} opening clips as one batch", flush=True)
    if pids:
        wait_all(pids, "clips")
    chain_stage(film, outdir, seed0, vw, vh, fps, ndur, plans)


def chain_stage(film, outdir, seed0, vw, vh, fps, ndur, plans):
    """Everything that has to start from an already-rendered frame.

    Two cases, same mechanism:
      * `chain: N`     - parts 2..N of one shot, each from the previous part's last frame,
                         giving a single continuous take far longer than one clip allows.
      * `from_prev`    - a shot that continues the PREVIOUS shot, so the cut between them
                         is invisible and one event reads unbroken across two shots.

    Necessarily sequential: each render needs the finished clip before it. That is the only
    reason these are not in the main batch.
    """
    rel = outdir.split("output/")[1]
    ids = [s["id"] for s in film["shots"]]
    work = []
    for i, s in enumerate(film["shots"]):
        if s.get("from_prev"):
            work.append((i, s, 1))                       # opening part, chained off prev shot
        for k in range(2, max(1, int(s.get("chain", 1))) + 1):
            work.append((i, s, k))
    if not work:
        return
    print(f"\n=== STAGE 3b: {len(work)} chained clips (each from a rendered frame) ===")
    for i, s, k in work:
        parts = clip_parts(outdir, s)
        out = parts[k - 1]
        if os.path.exists(out):
            continue
        if k == 1:
            j = ids.index(s["id"])
            if j == 0:
                raise SystemExit(f"{s['id']}: from_prev on the first shot")
            src_shot = film["shots"][j - 1]
            src = clip_parts(outdir, src_shot)[-1]
            srcname = src_shot["id"]
        else:
            src = parts[k - 2]
            srcname = f"{s['id']} part {k-1}"
        src = ensure_local(f"{rel}/clips/{os.path.basename(src)}", src, required=True)
        staged = f"epic_{s['id']}_p{k}.png"
        last_frame(src, f"{COMFY}/input/{staged}")
        frames = plans[i][min(k - 1, len(plans[i]) - 1)]
        suffix = "" if k == 1 else f"__p{k}"
        print(f"  > {s['id']}{suffix} <- last frame of {srcname} ({frames}f)", flush=True)
        wait_all([submit(i2v_wf(film, outdir, staged, s.get(f"motion{k}", s["motion"]),
                                vw, vh, frames, seed0 + 977 + i * 31 + k * 7,
                                f"{rel}/clips/{s['id']}{suffix}"))], f"{s['id']}{suffix}")


# ------------------------------------------------------------------ stage 4

def keyscale(want):
    """Delegates to engine.keyscale (Phase 2) - the two copies were diffed and
    identical but for this docstring. See SOUND-05 in craft/VIDEO_RULES.md."""
    sys.path.insert(0, os.path.join(ROOT, "studio"))
    from engine import keyscale as _keyscale
    return _keyscale(want)


def sfx(film, outdir, seed0):
    want = [s for s in film["shots"] if s.get("sfx")]
    if not want:
        return
    fps = int(film.get("fps", 24))
    ndur = narration_durs(outdir)
    print(f"\n=== STAGE 4: {len(want)} sound effects ===")
    os.makedirs(f"{outdir}/sfx", exist_ok=True)
    for i, s in enumerate(want):
        if os.path.exists(f"{outdir}/sfx/{s['id']}_00001.mp3"):
            continue
        secs = max(6.0, shot_frames(s, film, fps, ndur) / fps + 1.0)
        wf = load_wf("10_stableaudio_sfx.json")
        _set_neg(wf, ", ".join(x for x in (str(film.get("negative_audio") or ""),
                                           str(s.get("negative") or "")) if x))
        set_path(wf, "3.inputs.text", s["sfx"] + ", no music, no speech")
        set_path(wf, "5.inputs.seconds", round(min(secs, 20.0), 1))
        # Stable Audio is NOT a distilled model, so unlike ACE-Step its cfg 1.0 default
        # really did disable guidance - the prompt barely steered it and the negative
        # prompt did nothing at all. Real guidance, real step count.
        set_path(wf, "6.inputs.steps", 100)
        set_path(wf, "6.inputs.cfg", 7.0)
        set_path(wf, "6.inputs.sampler_name", "dpmpp_3m_sde")
        set_path(wf, "6.inputs.seed", seed0 + i * 31)
        set_path(wf, "8.inputs.filename_prefix",
                 f"{outdir.split('output/')[1]}/sfx/{s['id']}")
        print(f"  > {s['id']}: {s['sfx'][:52]}...", flush=True)
        run(HOST, wf, quiet=True)


def music(film, outdir, seed0):
    cues = film.get("music", [])
    if not cues:
        return
    print(f"\n=== STAGE 5: {len(cues)} music cues ===")
    os.makedirs(f"{outdir}/music", exist_ok=True)
    for i, c in enumerate(cues):
        if os.path.exists(f"{outdir}/music/{c['prefix']}_00001.mp3"):
            continue
        wf = load_wf("06_acestep_music.json")
        _set_neg(wf, ", ".join(x for x in (str(film.get("negative_audio") or ""),
                                           str(c.get("negative") or "")) if x))
        set_path(wf, "10.inputs.tags", c["tags"])
        set_path(wf, "10.inputs.lyrics", c.get("lyrics", ""))
        set_path(wf, "10.inputs.bpm", int(c.get("bpm", 90)))
        set_path(wf, "10.inputs.keyscale", keyscale(c.get("key")))
        set_path(wf, "10.inputs.duration", float(c.get("seconds", 60)))
        set_path(wf, "11.inputs.seconds", float(c.get("seconds", 60)))
        set_path(wf, "10.inputs.seed", seed0 + i * 41)
        set_path(wf, "12.inputs.seed", seed0 + i * 41)
        set_path(wf, "14.inputs.filename_prefix",
                 f"{outdir.split('output/')[1]}/music/{c['prefix']}")
        print(f"  > {c['prefix']} @ {c.get('at',0)}s ({c.get('seconds',60)}s)", flush=True)
        run(HOST, wf, quiet=True)


# ------------------------------------------------------------------ stage 6
def srt_time(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def wrap(text, width=46):
    words, out, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    out.append(cur)
    if len(out) <= 2:
        return "\n".join(out)
    mid = (len(out) + 1) // 2
    return "\n".join([" ".join(out[:mid]), " ".join(out[mid:])])


# How a shot is entered. A cut is the DEFAULT, because in film a cut is neutral and a
# dissolve is a statement - "time passed", "we are somewhere else". Dissolving every
# boundary the same way (the first version of this script did) flattens that distinction
# and a long film reads as one mushy slideshow. Set per shot with "in".
TRANSITIONS = {
    "cut":      (None,        0.00),   # concatenated, no overlap
    "soft":     ("fade",      0.28),   # barely-there blend inside a continuous scene
    "dissolve": ("fade",      0.70),   # scene change
    "fade":     ("fadeblack", 1.00),   # act break - dip through black
    "flash":    ("fadewhite", 0.50),   # a time gate: blow through white
}


def trans_of(shot, film):
    """(xfade name, duration) for the transition INTO this shot."""
    dflt = film.get("default_transition")
    if dflt is None:
        # a film written before per-shot transitions existed: honour its global float
        dflt = "dissolve" if film.get("transition") else "cut"
    name = shot.get("in", dflt)
    if name not in TRANSITIONS:
        raise SystemExit(f"{shot['id']}: unknown transition {name!r}")
    x, d = TRANSITIONS[name]
    if name == "dissolve" and "transition" in film and "in_dur" not in shot:
        d = float(film["transition"])
    return x, float(shot.get("in_dur", d))


def nframes(path):
    return int(sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
                  "-show_entries", "stream=nb_read_frames",
                  "-of", "default=nw=1:nk=1", path).strip())


def concat_copy(segs, out):
    """Hard-cut a run of segments together. Stream copy - no re-encode, no quality loss.

    Verified frame-exact on real segments. BUT the concat demuxer exits 0 on failure -
    a missing input, or one segment at a different resolution, produces a truncated or
    garbled file and a zero exit code. So the frame count is checked, not assumed.
    """
    if len(segs) == 1:
        shutil.copy(segs[0], out)
        return dur(out)
    lst = out + ".txt"
    with open(lst, "w", encoding="utf-8") as f:
        for p in segs:
            f.write("file '" + os.path.abspath(p).replace("\\", "/") + "'\n")
    sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
       "-c", "copy", out)
    want = sum(nframes(p) for p in segs)
    got = nframes(out)
    if got != want:
        raise SystemExit(f"concat lost frames in {out}: {got} != {want} "
                         f"(mismatched resolution or a missing input - concat exits 0 "
                         f"on both, so this check is the only thing that catches it)")
    return dur(out)


def _xfade_group(segs, bounds, out, fps):
    """Join segments with a real transition at each boundary.

    bounds[i] is (xfade_name, duration) for the transition INTO segs[i]; bounds[0] is
    ignored (it describes how this whole group is entered, which the caller handles).
    """
    if len(segs) == 1:
        shutil.copy(segs[0], out)
        return dur(out)
    durs = [dur(p) for p in segs]
    args = []
    for p in segs:
        args += ["-i", p]
    filt, pv, pa, off, used = [], "0:v", "0:a", 0.0, 0.0
    for i in range(1, len(segs)):
        name, d = bounds[i]
        off += durs[i - 1] - d
        filt.append(f"[{pv}][{i}:v]xfade=transition={name}:duration={d}:"
                    f"offset={off:.3f}[x{i}]")
        filt.append(f"[{pa}][{i}:a]acrossfade=d={max(d, 0.05)}[y{i}]")
        pv, pa = f"x{i}", f"y{i}"
        used += d
    sh("ffmpeg", "-y", "-v", "error", *args, "-filter_complex", ";".join(filt),
       "-map", f"[{pv}]", "-map", f"[{pa}]", "-r", str(fps),
       "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "256k", out)
    return sum(durs) - used


def mix_layer(items, total, out):
    """Mix (path, at_seconds, volume, extra_filter) into one 48k stereo track of `total`.

    Built in chunks: a 10-minute narrated film has ~100 lines, and putting 100 inputs
    through a single amix is both slow and fragile. Each chunk is laid over a silent bed
    so every partial is exactly `total` long and they can be summed flat.
    """
    parts, CH = [], 24
    for k in range(0, len(items), CH):
        grp = items[k:k + CH]
        p = f"{out}.part{k // CH}.wav"
        ins = ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=48000:cl=stereo"]
        filt, names = [], ["[0:a]"]
        for n, (path, at, vol, extra) in enumerate(grp, start=1):
            ins += ["-i", path]
            ms = int(max(0.0, at) * 1000)
            filt.append(f"[{n}:a]{extra}volume={vol},adelay={ms}|{ms}[x{n}]")
            names.append(f"[x{n}]")
        filt.append("".join(names) +
                    f"amix=inputs={len(names)}:duration=first:normalize=0[a]")
        sh("ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(filt),
           "-map", "[a]", "-ar", "48000", "-ac", "2", p)
        parts.append(p)
    if len(parts) == 1:
        shutil.move(parts[0], out)
        return out
    ins, names = [], []
    for n, p in enumerate(parts):
        ins += ["-i", p]
        names.append(f"[{n}:a]")
    sh("ffmpeg", "-y", "-v", "error", *ins, "-filter_complex",
       "".join(names) + f"amix=inputs={len(parts)}:duration=first:normalize=0[a]",
       "-map", "[a]", "-ar", "48000", "-ac", "2", out)
    return out


def join_mixed(segs, bounds, out, fps, chunk=10, depth=0):
    """Join with per-boundary transitions, chunked so no single filtergraph gets huge."""
    if len(segs) == 1:
        shutil.copy(segs[0], out)
        return dur(out)
    if len(segs) <= chunk:
        return _xfade_group(segs, bounds, out, fps)
    parts, pbounds, i, k = [], [], 0, 0
    while i < len(segs):
        j = min(i + chunk, len(segs))
        p = f"{out[:-4]}_d{depth}g{k:02d}.mp4"
        if not os.path.exists(p):
            _xfade_group(segs[i:j], bounds[i:j], p, fps)
        parts.append(p)
        pbounds.append(bounds[i])       # how this chunk is entered
        i, k = j, k + 1
    return join_mixed(parts, pbounds, out, fps, chunk, depth + 1)


def edit(film, outdir, hd=True):
    vw, vh = VID["16:9-hd" if hd else "16:9"]
    fps = int(film.get("fps", 24))
    ndur = narration_durs(outdir)
    work = f"{outdir}/_work"
    os.makedirs(work, exist_ok=True)
    ff = f"fontfile='{fgpath(FONT)}':" if FONT else ""

    # Pull anything the share is missing before we start cutting. A missing clip would
    # otherwise just silently drop that shot from the film.
    rel = outdir.split("output/")[1]
    print("  checking assets...", flush=True)
    for s in film["shots"]:
        for pth in clip_parts(outdir, s):
            ensure_local(f"{rel}/clips/{os.path.basename(pth)}", pth)
        if s.get("sfx"):
            ensure_local(f"{rel}/sfx/{s['id']}_00001.mp3",
                         f"{outdir}/sfx/{s['id']}_00001.mp3")
    for c in film.get("music", []):
        ensure_local(f"{rel}/music/{c['prefix']}_00001.mp3",
                     f"{outdir}/music/{c['prefix']}_00001.mp3")

    shots = [s for s in film["shots"] if os.path.exists(clip_parts(outdir, s)[0])]
    dropped = len(film["shots"]) - len(shots)
    if dropped:
        print(f"  ! {dropped} shot(s) have no clip and are being skipped", file=sys.stderr)

    # ---- build one finished segment per shot --------------------------------
    # `starts` lets a music cue anchor to a shot id ("at_shot") instead of a hand-guessed
    # timecode. Shot lengths depend on measured narration, so timecodes written by hand
    # drift the moment any line is re-rolled; a shot id cannot drift.
    segs, cues, starts, narr = [], [], {}, []
    for idx, s in enumerate(shots):
        # A chained shot is many clips that each begin on the previous one's last frame.
        # Concatenated they are one continuous take, so the shot behaves as a single long
        # source from here on and the joins are invisible.
        _parts = [p for p in clip_parts(outdir, s) if os.path.exists(p)]
        if len(_parts) > 1:
            src = f"{work}/_chain_{s['id']}.mp4"
            if not os.path.exists(src):
                concat_copy(_parts, src)
        else:
            src = _parts[0]
        dst = f"{work}/{s['id']}.mp4"
        vpath = f"{outdir}/voice/{s['id']}.mp3"
        spath = f"{outdir}/sfx/{s['id']}_00001.mp3"
        has_v, has_s = os.path.exists(vpath), os.path.exists(spath)
        cd = dur(src)
        nd = ndur.get(s["id"], dur(vpath) if has_v else 0.0)
        need = LEAD + nd + float(film.get("tail", TAIL)) if has_v else cd

        # Sized in stage 3 to fit, so this is normally a no-op. If a line still overruns
        # (narration re-rolled longer, or it hit FRAME_CAP), slow the picture to cover it
        # rather than freezing a frame - this film must never hold a still.
        stretch = max(1.0, need / cd) if cd > 0 else 1.0
        total = max(cd * stretch, need)
        vf = [f"setpts={stretch:.5f}*PTS"] if stretch > 1.001 else []
        if not os.path.exists(dst):
            # Picture + ambience + designed sfx ONLY. Narration is deliberately NOT baked
            # in here: `acrossfade` ramps an incoming segment's audio up from silence over
            # the transition duration, so a line starting at LEAD=0.30 inside a 0.70s
            # dissolve entered at 43% gain - the first word of narration ducked at all 31
            # dissolves. Narration is laid as one continuous track over the finished
            # picture instead (see the mix pass below), which also means changing a line
            # no longer requires rebuilding its segment.
            # Effects are NOT baked in here, for the same reason narration is not: anything
            # welded into the segment audio lands in [0:a] at the mix, where it cannot be
            # ducked independently of the ambience. A designed effect at a fixed 0.42
            # multiplier therefore played at full level straight through narration. It is
            # laid as its own sidechained stem over the finished picture instead.
            ins = ["-i", src]
            n = 1

            # LTX's own bed spans ~39 dB across clips (measured -51.2 to -12.2 LUFS), so
            # one fixed multiplier is wrong by up to 34 dB: it erased room tone on the
            # quiet clips and fought the score on the loudest - which happened to be the
            # biggest moments in the film. Measure each clip and hit a target instead.
            want = AMB_LUFS if has_v else AMB_LUFS_BARE
            cur = audio_lufs(src)
            amb = round(min(10 ** ((want - cur) / 20), 6.0), 4) if (cur and cur > -70) else 0.14
            mix = [f"[0:a]volume={amb},apad=pad_dur={total + 0.3:.2f}[amb]"]
            labels = ["[amb]"]
            mix.append("[amb]anull[a]" if len(labels) == 1 else
                       "".join(labels) +
                       f"amix=inputs={len(labels)}:duration=longest:normalize=0[a]")

            # titles are drawn over moving footage - there are no cards in this film
            for ov in s.get("titles", []):
                st, en = float(ov.get("at", 0.4)), float(ov.get("at", 0.4)) + float(ov.get("hold", 2.6))
                fsz = int(vw * float(ov.get("scale", 0.045)))
                al = (f"if(lt(t,{st}),0,if(lt(t,{st+0.6}),(t-{st})/0.6,"
                      f"if(lt(t,{en}),1,if(lt(t,{en+0.7}),({en+0.7}-t)/0.7,0))))")
                vf.append(f"drawtext={ff}text='{ffesc(ov['text'])}':fontcolor=white:"
                          f"fontsize={fsz}:x=(w-text_w)/2:"
                          f"y=h*{ov.get('y', 0.46)}:alpha='{al}':"
                          f"shadowcolor=black@0.85:shadowx=2:shadowy=2")
            vchain = ",".join(vf) if vf else "null"
            sh("ffmpeg", "-y", "-v", "error", *ins, "-filter_complex",
               f"[0:v]{vchain}[v];" + ";".join(mix),
               "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}", "-r", str(fps),
               "-c:v", "libx264", "-crf", "16", "-preset", "veryfast",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", dst)

        segs.append(dst)
        narr.append((s["id"], nd) if has_v else (s["id"], None))
        if (idx + 1) % 10 == 0:
            print(f"  segments {idx+1}/{len(shots)}", flush=True)

    slug = film["title"].lower().replace(" ", "-")

    # ---- timeline ----------------------------------------------------------
    # Each boundary eats a different amount of overlap now, so the caption and music
    # timeline has to be derived from the actual per-boundary transitions rather than
    # from one global value.
    bounds = [trans_of(s, film) for s in shots]
    segdurs = [dur(p) for p in segs]
    t = 0.0
    for i, s in enumerate(shots):
        starts[s["id"]] = t
        sid, nd = narr[i]
        if nd is not None:
            cues.append((t + LEAD, t + LEAD + nd + 0.25, s["say"]))
        nxt = bounds[i + 1][1] if i + 1 < len(shots) else 0.0
        t += segdurs[i] - nxt
    total_expected = t

    counts = collections.Counter(s.get("in", film.get("default_transition", "cut"))
                                 for s in shots[1:])
    print("  transitions: " + ", ".join(f"{k} x{v}" for k, v in counts.most_common()))

    # ---- captions ----------------------------------------------------------
    srt = f"{outdir}/{slug}.srt"
    with open(srt, "w", encoding="utf-8") as f:
        for i, (a, b, text) in enumerate(cues, 1):
            f.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{wrap(text)}\n\n")
    print(f"  captions -> {srt} ({len(cues)} cues)")

    # ---- assembly ----------------------------------------------------------
    # Runs of hard cuts are concatenated with a stream copy (instant, lossless); only
    # the real transitions cost an encode.
    #
    # The reel filename carries a hash of the transition layout. Reels are cached by
    # index and the index IS the layout, so without this, changing one shot's `in` and
    # re-running --stage edit silently reassembles the OLD grammar from stale reels.
    sig = hashlib.sha1(json.dumps(bounds).encode()).hexdigest()[:8]
    reels, rbounds, i = [], [], 0
    while i < len(segs):
        j = i + 1
        while j < len(segs) and bounds[j][0] is None:
            j += 1
        reel = f"{work}/reel_{sig}_{len(reels):03d}.mp4"
        if not os.path.exists(reel):
            concat_copy(segs[i:j], reel)
        reels.append(reel)
        rbounds.append(bounds[i])
        i = j
    print(f"\n=== STAGE 6: {len(segs)} segments -> {len(reels)} reels (layout {sig}) ===")

    joined = f"{work}/_joined_{sig}.mp4"
    total = join_mixed(reels, rbounds, joined, fps)
    print(f"  assembled {total:.1f}s (timeline predicted {total_expected:.1f}s)")

    # ---- one mix pass: narration + score over the assembled picture --------
    # An act break blacks the picture, but acrossfade sails the ambience straight through
    # it - which reads as a dropped frame rather than a break. Dip the bed at those points.
    fadeT = [starts[s["id"]] for s in shots[1:] if s.get("in") == "fade"]
    dip = "*".join(f"(1-0.8*exp(-pow((t-{T+0.5:.2f})/0.5\\,2)))" for T in fadeT) or "1"

    # voice files are already normalised to VOICE_LUFS by narrate(), so gain is 1.0 here.
    # It used to be 1.9, which pushed lines that already peaked at -0.5 dBFS to +5 dBFS -
    # clipping baked into the segment where no later loudness pass could undo it.
    narr_items = [(f"{outdir}/voice/{s['id']}.mp3", starts[s["id"]] + LEAD, 1.0, "")
                  for s in shots if s["id"] in ndur
                  and os.path.exists(f"{outdir}/voice/{s['id']}.mp3")]
    mus_items = []
    for c in film.get("music", []):
        p = f"{outdir}/music/{c['prefix']}_00001.mp3"
        if not os.path.exists(p):
            continue
        # ACE-Step output spans >20 LU between a dense orchestral cue and a solo piano one,
        # so `level` as a raw multiplier gave ~2 dB of control over a 20 dB variable and a
        # third of the cues would simply not have been audible. Normalise, then trim.
        np_ = f"{work}/_mus_{c['prefix']}.wav"
        if not os.path.exists(np_):
            norm_to(p, np_, MUSIC_LUFS, tp=-6.0)
        at, cd2 = starts.get(c.get("at_shot"), float(c.get("at", 0))), adur(np_)
        # `until_shot` lets a cue stop dead at a specific moment instead of running to the
        # next cue - which is how you get an intentional unscored silence.
        if c.get("until_shot") in starts:
            cd2 = max(4.0, starts[c["until_shot"]] - at)
        print(f"    {c['prefix']:16} at {at:6.1f}s  len {cd2:5.1f}s")
        mus_items.append((np_, at, float(c.get("level", 1.0)),
                          f"afade=t=in:st=0:d=2.5,"
                          f"afade=t=out:st={max(0.1, cd2-3.5):.2f}:d=3.5,"))

    # Designed effects, as their own stem. Normalised first: a raw level multiplier
    # over an un-normalised source gave about 2 dB of usable control over a 20 dB variable.
    sfx_items = []
    for s in shots:
        sp = f"{outdir}/sfx/{s['id']}_00001.mp3"
        if not s.get("sfx") or not os.path.exists(sp):
            continue
        nsp = f"{work}/_sfxn_{s['id']}.wav"
        if not os.path.exists(nsp):
            norm_to(sp, nsp, SFX_LUFS, tp=-6.0)
        sd = adur(nsp)
        sfx_items.append((nsp, starts.get(s["id"], 0.0), float(s.get("sfx_level", 1.0)),
                          f"afade=t=out:st={max(0.1, sd - 0.7):.2f}:d=0.7,"))

    ntrk = mix_layer(narr_items, total, f"{work}/_narr_{sig}.wav") if narr_items else None
    mtrk = mix_layer(mus_items, total, f"{work}/_mus_{sig}.wav") if mus_items else None
    strk = mix_layer(sfx_items, total, f"{work}/_sfx_{sig}.wav") if sfx_items else None

    tracks = ["-i", joined]
    lab = [f"[0:a]volume='{dip}':eval=frame[base]"]
    names = ["[base]"]
    k, nlab = 1, None
    if ntrk:
        tracks += ["-i", ntrk]; nlab = f"[{k}:a]"; k += 1
    # Every bed that is not speech ducks under speech. Fixed levels cannot serve a 72%
    # speech duty cycle, and keying off the finished programme does not work - the depth
    # wanders with ambience instead of speech - so the key is the narration stem itself.
    keyed = []
    for trk, tag in ((mtrk, "mus"), (strk, "sfx")):
        if trk:
            tracks += ["-i", trk]
            keyed.append((f"[{k}:a]", tag)); k += 1
    if nlab and keyed:
        # An ffmpeg filter output can be consumed exactly once, so the narration has to be
        # split explicitly: one copy per sidechain key, plus one for the mix itself.
        keys = [f"[nk{i}]" for i in range(len(keyed))]
        lab.append(f"{nlab}asplit={len(keyed) + 1}[nmix]" + "".join(keys))
        names.append("[nmix]")
        for (slab, tag), key in zip(keyed, keys):
            thr, ratio = DUCK[tag]
            lab.append(f"{slab}{key}sidechaincompress=threshold={thr}:ratio={ratio}:"
                       f"attack=20:release=350:makeup=1:link=maximum[d{tag}]")
            names.append(f"[d{tag}]")
    else:
        if nlab:
            names.append(nlab)
        names += [s for s, _ in keyed]
    lab.append("".join(names) +
               f"amix=inputs={len(names)}:duration=first:normalize=0[a]")
    mixed = f"{work}/_mixed_{sig}.mkv"
    sh("ffmpeg", "-y", "-v", "error", *tracks, "-filter_complex", ";".join(lab),
       "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "pcm_s16le",
       "-t", f"{total:.2f}", mixed)
    ducked = [t for t, k in (("score", mtrk), ("effects", strk)) if k and ntrk]
    print(f"  mixed {len(narr_items)} narration lines + {len(mus_items)} cues "
          f"+ {len(sfx_items)} effects"
          + (f" ({' and '.join(ducked)} ducked under speech)" if ducked else ""))

    # ---- loudness, fades, master -------------------------------------------
    # Two-pass loudnorm. A single adaptive pass rides the gain across ten minutes of
    # alternating quiet narration and loud sfx, which pumps audibly.
    d = measure(mixed)
    ln = "loudnorm=I=-16:TP=-1.5:LRA=11"
    if d:
        ln = (f"loudnorm=I=-16:TP=-1.5:LRA=11:linear=true:"
              f"measured_I={d['input_i']}:measured_TP={d['input_tp']}:"
              f"measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}")
        print(f"  loudness in: {d['input_i']} LUFS / {d['input_tp']} dBTP "
              f"-> linear normalise to -16")
    # loudnorm alone overshot the requested true peak by ~3 dB on both earlier films;
    # a real limiter after it is what actually guarantees the ceiling.
    nosub = f"{outdir}/{slug}_nosubs.mp4"
    sh("ffmpeg", "-y", "-v", "error", "-i", mixed,
       "-vf", f"fade=t=in:st=0:d=1.2,fade=t=out:st={total-1.5:.3f}:d=1.5,format=yuv420p",
       # alimiter caps SAMPLE peak, not TRUE peak. Inter-sample peaks still overshoot: a
       # 20-minute mix measured +0.48 dBTP with limit=0.891 (-1 dBFS) even though loudnorm
       # had been asked for -1.5. Give the limiter real headroom - 0.708 = -3 dBFS - and
       # verify dBTP on the master rather than trusting the requested value.
       "-af", f"{ln},alimiter=limit=0.708:level=disabled",
       "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", nosub)

    # ---- optional burnt-in captions ---------------------------------------
    final = f"{outdir}/{slug}_captioned.mp4"
    fontname = ("Arial" if FONT.lower().endswith(("arial.ttf", "arialbd.ttf"))
                else "DejaVu Sans")
    style = (f"FontName={fontname},Fontsize=18,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,"
             "Alignment=2,MarginV=26,Bold=1")
    subarg = f"subtitles={os.path.basename(srt)}"
    if FONT:
        subarg += f":fontsdir='{fgpath(os.path.dirname(FONT))}'"
    subarg += f":force_style='{style}'"
    sh("ffmpeg", "-y", "-v", "error", "-i", nosub, "-vf", subarg,
       "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
       "-c:a", "copy", "-movflags", "+faststart", final, cwd=outdir)

    m, sec = divmod(total, 60)
    print(f"\n>>> {final}   ({int(m)}m {sec:04.1f}s, {vw}x{vh})")
    print(f">>> {nosub}   (same cut, no burnt-in captions)")
    return final


def main():
    p = argparse.ArgumentParser()
    p.add_argument("film")
    p.add_argument("--stage", default="all",
                   choices=["all", "narrate", "keyframes", "clips", "sfx", "music",
                            "audio", "edit"])
    p.add_argument("--seed", type=int, default=9000)
    p.add_argument("--sd", action="store_true", help="768x512 clips instead of 1280x704")
    a = p.parse_args()

    film = json.load(open(a.film))
    slug = film["title"].lower().replace(" ", "-")
    outdir = f"{COMFY}/output/claude-generated/11-short-film/{slug}"
    for d in ("keyframes", "clips", "voice", "sfx", "music", "_work"):
        os.makedirs(f"{outdir}/{d}", exist_ok=True)
    hd = not a.sd

    if a.stage in ("all", "narrate"):
        narrate(film, outdir, a.seed)
    if a.stage in ("all", "keyframes"):
        keyframes(film, outdir, a.seed)
    if a.stage in ("all", "clips"):
        clips(film, outdir, a.seed, hd)
    if a.stage in ("all", "audio", "sfx"):
        sfx(film, outdir, a.seed)
    if a.stage in ("all", "audio", "music"):
        music(film, outdir, a.seed)
    if a.stage in ("all", "edit"):
        edit(film, outdir, hd)


if __name__ == "__main__":
    main()
