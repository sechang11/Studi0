#!/usr/bin/env python3
"""studio/_tools/score_casting.py - casting a film's score by ear (craft/SOUND.md section 0).

Music is cast the way a film casts an actor:
  AUDITIONS   round 1: a bank of short samples for one scene, as different from each other as the brief allows
  CALLBACKS   every later round: new samples written closer to the picks - the same idiom on new seeds, a nudge
              in tempo, an instrument traded - until the shortlist is right
  SHORTLIST   the samples marked keep along the way
  FINALISTS   each shortlisted sample made into the full piece for the scene - the EXACT take, extended by an
              edit of its own bars if the picture is longer (never a new render unless --fresh) - mixed under
              its picture
  CAST        the finalist the director chooses goes into the film
  UNDERSTUDIES the other finalists, kept beside it, ready to swap in

The director listens to every sample on a sheet (sheet_r<N>.html: every sample playable, its recipe, its parent);
nothing in here chooses by a number. All samples are levelled to -16 LUFS so they compare fairly.

    python3 studio/_tools/score_casting.py new    --film F --scene S --secs 32 --brief "..." [--video V --sfx A]
    python3 studio/_tools/score_casting.py round  --film F --scene S --recipes round.json
    python3 studio/_tools/score_casting.py vary   --film F --scene S --from r1-02 [--n 6] [--step 0.04] [--out r2.json]
    python3 studio/_tools/score_casting.py pick   --film F --scene S r1-02 r1-05 [--keep r1-07 r1-02]
    python3 studio/_tools/score_casting.py final  --film F --scene S r3-01 r2-04 [--seeds 2]
    python3 studio/_tools/score_casting.py final  --film F --scene S r2-03 --secs 184 --video <long cut> --sfx <its
                                                  takes-only audio> --label "the 3:04 cut"   (a longer version)
    python3 studio/_tools/score_casting.py develop --film F --scene S f-03 --plan plan.json [--sfx <takes' audio>]
                                                  (a long finalist re-orchestrated section by section instead of
                                                  looped: covers of its own edit, switched on bar lines)

The director's two ticks: PICK = go this direction (the next round's callbacks are built from it); KEEP = a
favourite (it goes on the shortlist and becomes a full piece). Both on one sample is common.
    python3 studio/_tools/score_casting.py cast   --film F --scene S f-02 --to <film OUT>/score.mp3
    python3 studio/_tools/score_casting.py status --film F --scene S

A recipe - written by hand for auditions, by `vary` (or by hand) for callbacks:
    {"engine": "mm3", "name": "J-rock fight", "caption": "Global Metadata: ...\\n\\nVocal Details: ...\\n\\n
     Arrangement: ...", "lyrics": "[Intro]\\n\\n[Instrumental]\\n\\n[Outro]", "seed": 222}
    {"engine": "ace", "name": "J-rock fight", "tags": "...", "bpm": 164, "key": "E minor", "seed": 222}
    {"engine": "cover", "name": "Orchestral", "source": "studio/samples/music3/TerraTheme.mp3", "start": 5,
     "tags": "...", "bpm": 81, "key": "Ab minor", "strength": 1.0, "seed": 222}
  + "parent": "r1-02", "note": "what changed" on a callback.
cover = the source's melody and harmony re-played from silence in a new style (ACE-Step 1.5's cover mode; strength
the share of the steps that follow the source). remix = the source's own recording re-coloured (denoise the dial).
mm3 = MiniMax Music 3 (ComfyUI's template audio_minimax_music_3.json; caption in three parts, Global Metadata ->
Vocal Details -> Arrangement; structure only from the lyrics' section tags; up to ~5 minutes).
ace = ACE-Step 1.5 turbo (workflow 06; tempo and key ALWAYS set; one idiom, named instruments; ~45 s at most).
notes = the source's NOTES played again (studio/_tools/notes_cover.py: transcribed once with `prepare`, rendered on
sampled instruments in a style at any speed); with "polish" ACE-Step then covers that render (2026-10-05: covers of
a recording are half the old sound; covers of the right instruments are not):
    {"engine": "notes", "name": "Solo piano", "song": "terra", "style": "piano", "source":
     "studio/samples/music3/TerraTheme.mp3", "start": 6.9, "secs": 48, "stretch": 1.0, "seed": 1,
     "polish": {"tags": "...", "denoise": 0.6, "strength": 0.5, "bpm": 81, "key": "Ab minor", "seed": 4242}}

Files: studio/samples/casting/<film>/<scene>/ - casting.json (every sample, its recipe, its parent, the picks),
r<N>/<id>.mp3 (levelled), finals/<id>.mp3 and <id>_mix.mp4 (under the picture, the score ducked under the
takes' own sound), sheet_r<N>.html / sheet_finals.html (self-contained: open anywhere, or send).
"""
import argparse
import base64
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.expanduser("~/shared/comfy-studio")
COMFY = os.path.expanduser("~/ComfyUI")
HOST = "127.0.0.1:8188"
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import comfy  # noqa: E402

TARGET = -16.0
MM3_LYRICS = "[Intro]\n\n[Instrumental]\n\n[Instrumental]\n\n[Outro]"
ENGINE_NAME = {"mm3": "MiniMax Music 3", "ace": "ACE-Step 1.5", "remix": "Remix (ACE-Step)",
               "cover": "Cover (ACE-Step 1.5)", "notes": "Notes (sampled instruments)",
               "musicgen": "MusicGen-Melody - NON-COMMERCIAL", "file": "Reference"}
NOTES_TOOL = os.path.join(ROOT, "studio", "_tools", "notes_cover.py")
MUSIC_TOOLS = os.path.expanduser("~/music-tools")     # notes_cover's libraries, instruments and lead sheets


# ------------------------------------------------------------------------------------------------ the casting file
def base(film, scene):
    return os.path.join(ROOT, "studio", "samples", "casting", film, scene)


def load(film, scene):
    p = os.path.join(base(film, scene), "casting.json")
    if not os.path.exists(p):
        sys.exit("no casting for %s / %s - start one with `new`" % (film, scene))
    return json.load(open(p, encoding="utf-8"))


def save(c):
    d = base(c["film"], c["scene"])
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "casting.json")
    json.dump(c, open(p + ".tmp", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)


def find(c, sid):
    for r in c["rounds"]:
        for s in r["samples"]:
            if s["id"] == sid:
                return s
    for f in c.get("finals", []):
        if f["id"] == sid:
            return f
    sys.exit("no sample %s" % sid)


# ------------------------------------------------------------------------------------------------ rendering
def wait_for_queue(budget=3600):
    t0 = time.time()
    while time.time() - t0 < budget:
        try:
            q = json.load(urllib.request.urlopen("http://%s/queue" % HOST, timeout=20))
            if not q["queue_running"] and not q["queue_pending"]:
                return
        except Exception:
            return
        print("  someone else's job is running - waiting", flush=True)
        time.sleep(15)


def prep_source(recipe, secs):
    """The stretch of the director's own recording a remix starts from, cut to the sample's length into ComfyUI's
    input folder."""
    src = recipe["source"] if os.path.isabs(recipe["source"]) else os.path.join(ROOT, recipe["source"])
    start = float(recipe.get("start", 0.0))
    # "stretch": the source at another speed, its pitch kept (rubberband), before it is covered - 0.8 a slower
    # version, 1.25 a faster one; the recipe's bpm is the new tempo (2026-10-05)
    stretch = float(recipe.get("stretch", 1.0))
    stem = re.sub(r"[^a-z0-9]+", "", os.path.basename(src).lower())[:24]
    name = "casting_src_%s_%d_%d%s.wav" % (stem, int(start * 10), int(secs * 10),
                                          "_x%03d" % round(stretch * 100) if stretch != 1.0 else "")
    dst = os.path.join(COMFY, "input", name)
    if not os.path.exists(dst) or recipe.get("fresh_source"):     # a refine's first pass is new every time
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", "%.2f" % start, "-t", "%.2f" % (secs * stretch), "-i", src]
        if stretch != 1.0:
            cmd += ["-af", "rubberband=tempo=%.4f" % stretch]
        subprocess.run(cmd + ["-ac", "2", "-ar", "44100", "-t", "%.2f" % secs, dst], check=True)
    return name


def remix_graph(recipe, secs, prefix, seed):
    """Your own recording, re-played: ACE-Step audio-to-audio from the recording's own latent. `denoise` is the dial
    - about 0.3 keeps the recording and changes its colour, 0.6 and up keeps little more than its shape."""
    name = prep_source(recipe, secs)
    den = float(recipe.get("denoise", 0.45))
    if recipe.get("model", "ace15") == "ace1":
        wf = json.load(open(os.path.join(ROOT, "workflows", "31_acestep_remix.json")))
        wf = {k: v for k, v in wf.items() if isinstance(v, dict) and "class_type" in v}
        wf["2"]["inputs"]["audio"] = name
        wf["4"]["inputs"].update({"tags": recipe["tags"], "lyrics": ""})
        wf["5"]["inputs"].update({"seed": seed, "denoise": den})
        wf["7"]["inputs"]["filename_prefix"] = prefix
        return wf
    wf = json.load(open(os.path.join(ROOT, "workflows", "06_acestep_music.json")))
    wf = {k: v for k, v in wf.items() if isinstance(v, dict) and "class_type" in v}
    wf["10"]["inputs"].update({"tags": recipe["tags"], "lyrics": "", "bpm": int(recipe.get("bpm") or 90),
                               "keyscale": recipe.get("key") or "C major", "duration": float(secs), "seed": seed,
                               "generate_audio_codes": False})   # the node's own advice when the audio is given
    wf["50"] = {"class_type": "LoadAudio", "inputs": {"audio": name}}
    wf["51"] = {"class_type": "VAEEncodeAudio", "inputs": {"audio": ["50", 0], "vae": ["3", 0]}}
    wf.pop("11", None)
    wf["12"]["inputs"].update({"latent_image": ["51", 0], "denoise": den, "seed": seed})
    wf["14"]["inputs"]["filename_prefix"] = prefix
    return wf


# 2026-10-05: ACE-Step 1.5 (the smaller model) plays the key it is TOLD only for some spellings. Measured from
# silence, one prompt, every black-key root in both spellings (work/music/key_spelling_probe.py): C#, F# major and
# minor and G# minor play true; Db, Eb, Gb, Bb in either spelling, D#, A#, G# major and Ab minor play another key
# ("Ab minor" -> D major / Eb major). Every TerraTheme cover was told "Ab minor": the tune kept, the harmony under it
# from a key the model invented (the director: "something else was wrong, I can't really describe it"). A key is
# told as itself when that label plays true, else as its relative (the same notes) when that one does.
_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
       "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
_TRUE = {(1, "major"): "C# major", (1, "minor"): "C# minor", (6, "major"): "F# major", (6, "minor"): "F# minor",
         (8, "minor"): "G# minor"}
_WHITE = {0: "C", 2: "D", 4: "E", 5: "F", 7: "G", 9: "A", 11: "B"}


def key_label(key):
    """The label to tell ACE-Step 1.5 for a key: one it plays true - the key itself, or its relative."""
    root, q = key.split()
    pc = _PC[root]
    for p_, q_ in ((pc, q), ((pc + 3) % 12, "major") if q == "minor" else ((pc - 3) % 12, "minor")):
        if (p_, q_) in _TRUE:
            return _TRUE[(p_, q_)]
        if p_ in _WHITE:
            return "%s %s" % (_WHITE[p_], q_)
    return key


def cover_graph(recipe, secs, prefix, seed):
    """A COVER (Suno's word; a reimagining): the source's melody, harmony and form kept, every sound new. ACE-Step
    1.5 reads the source's own semantic codes (its 5 Hz tokens: what is played, and when) and plays them again from
    silence in the style the tags ask for - denoise 1.0, so none of the recording's sound survives (a remix keeps it,
    which is why the TerraTheme remixes sounded thin and noisy). `strength` is the share of the steps that follow
    the source (ACE-Step's audio_cover_strength): 1.0 every step; 0.5 the source's shape for the first half, then
    the model's own detail on it."""
    if not (recipe.get("bpm") and recipe.get("key")):
        sys.exit("a cover recipe needs the source's bpm and key")
    name = prep_source(recipe, secs)
    st = max(0.0, min(1.0, float(recipe.get("strength", 1.0))))
    # denoise 1.0 = from silence, the hints alone (2026-10-01: on this model they keep the source's rhythm and
    # sections but not its tune); below 1.0 = from the source's own latent, renoised - ACE-Step's
    # cover_noise_strength (= 1 - denoise) - so the tune survives while the hints hold the structure
    den = max(0.05, min(1.0, float(recipe.get("denoise", 1.0))))
    xl = recipe.get("model") == "xl"
    # XL-SFT (2026-10-05, the director approved the download): the 4B DiT, not distilled - Comfy-Org's template
    # audio_ace_step1_5_xl_sft: 50 steps at CFG 7 (euler, simple), AuraFlow shift 3, the negative its own
    # conditioning zeroed (which keeps a cover's hints in the negative too, so CFG steers only the style)
    steps = int(recipe.get("steps", 50 if xl else 20))
    cfg = float(recipe.get("cfg", 7.0 if xl else 1.0))
    wf = json.load(open(os.path.join(ROOT, "workflows", "06_acestep_music.json")))
    wf = {k: v for k, v in wf.items() if isinstance(v, dict) and "class_type" in v}
    model = ["1", 0]
    if xl:
        wf["1"]["inputs"]["unet_name"] = "acestep_v1.5_xl_sft_bf16.safetensors"
        wf["2"]["inputs"]["clip_name2"] = "qwen_4b_ace15.safetensors"
        wf["16"] = {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.0}}
        model = ["16", 0]
    wf["10"]["inputs"].update({"tags": recipe["tags"], "lyrics": recipe.get("lyrics", ""), "bpm": int(recipe["bpm"]),
                               "keyscale": key_label(recipe["key"]), "duration": float(secs), "seed": seed,
                               "generate_audio_codes": False})   # the node's own advice when the audio is given
    wf["11"]["inputs"]["seconds"] = float(secs)
    wf["50"] = {"class_type": "LoadAudio", "inputs": {"audio": name}}
    wf["51"] = {"class_type": "VAEEncodeAudio", "inputs": {"audio": ["50", 0], "vae": ["3", 0]}}
    if recipe.get("codes") and secs > 30.5:
        # 2026-10-05: on a 47.9 s source this wiring crashed ComfyUI for everyone (CUDA device-side assert, "scatter
        # gather kernel index out of bounds", the server aborted; restarted with scripts/restart-comfy.sh). It ran
        # clean on 30 s sources. Not again past 30 s until the node is understood.
        sys.exit("cover with \"codes\": 30 s at most (it crashed ComfyUI on 47.9 s, 2026-10-05)")
    if recipe.get("codes"):
        # 2026-10-05: the source's semantic codes WITHOUT its timbre. "Set Reference Audio" makes the recording both
        # the cover's codes and the timbre the encoder imitates - every cover so far was told to sound like the
        # original while its tags asked for other instruments ("something else was wrong, I can't describe it").
        # AceStep15SourceCodes (ComfyUI/custom_nodes/ace15_source_codes) hands the model the codes alone.
        wf["52"] = {"class_type": "AceStep15SourceCodes", "inputs": {"model": ["1", 0], "conditioning": ["10", 0],
                                                                      "latent": ["51", 0]}}
    else:
        wf["52"] = {"class_type": "ReferenceTimbreAudio", "inputs": {"conditioning": ["10", 0], "latent": ["51", 0]}}
    # the negatives: at CFG 1 (turbo) never read; at CFG 7 (XL) each conditioning zeroed
    wf["53"] = {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["52", 0]}}
    wf["54"] = {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["10", 0]}}
    neg_cover, neg_plain = (["53", 0], ["54", 0]) if xl else (["52", 0], ["10", 0])
    latent = ["51", 0] if den < 1.0 else ["11", 0]
    s0 = int(round(steps * (1.0 - den)))              # the first step sampled (0 from silence)
    k = s0 + int(round((steps - s0) * st))            # the hints guide steps s0..k, the tags alone k..steps
    common = {"model": model, "noise_seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler",
              "scheduler": "simple"}
    if k <= s0:                                       # strength 0: no hints at all (a plain remix)
        wf["12"] = {"class_type": "KSamplerAdvanced", "inputs": dict(
            common, add_noise="enable", positive=["10", 0], negative=neg_plain, latent_image=latent,
            start_at_step=s0, end_at_step=10000, return_with_leftover_noise="disable")}
    else:
        wf["12"] = {"class_type": "KSamplerAdvanced", "inputs": dict(
            common, add_noise="enable", positive=["52", 0], negative=neg_cover, latent_image=latent,
            start_at_step=s0, end_at_step=k if k < steps else 10000,
            return_with_leftover_noise="enable" if k < steps else "disable")}
        if k < steps:
            wf["15"] = {"class_type": "KSamplerAdvanced", "inputs": dict(
                common, add_noise="disable", positive=["10", 0], negative=neg_plain, latent_image=["12", 0],
                start_at_step=k, end_at_step=10000, return_with_leftover_noise="disable")}
            wf["13"]["inputs"]["samples"] = ["15", 0]
    wf["14"]["inputs"]["filename_prefix"] = prefix
    return wf


def graph(recipe, secs, prefix):
    seed = int(recipe.get("seed", 222))
    if recipe["engine"] == "remix":
        return remix_graph(recipe, secs, prefix, seed)
    if recipe["engine"] == "cover":
        return cover_graph(recipe, secs, prefix, seed)
    if recipe["engine"] == "mm3":
        return {
            "6": {"class_type": "UNETLoader", "inputs": {"unet_name": "minimax_music3_dit_fp16.safetensors",
                                                         "weight_dtype": "default"}},
            "3": {"class_type": "CLIPLoader", "inputs": {
                "clip_name": "minimax_music3_text_encoder_pruned_int8_convrot.safetensors", "type": "minimax",
                "device": "default"}},
            "7": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_music3_dav.safetensors"}},
            "13": {"class_type": "MiniMaxMusic3TextEncode", "inputs": {
                "clip": ["3", 0], "caption": recipe["caption"].strip(), "lyrics": (recipe.get("lyrics") or MM3_LYRICS).strip(),
                "seed": seed, "max_duration": float(secs), "cfg_scale": 1.7, "top_k": 50}},
            "10": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["13", 0]}},
            "15": {"class_type": "EmptyMiniMaxMusic3LatentAudio", "inputs": {"seconds": ["13", 1], "batch_size": 1}},
            "9": {"class_type": "KSampler", "inputs": {
                "model": ["6", 0], "positive": ["13", 0], "negative": ["10", 0], "latent_image": ["15", 0],
                "seed": seed, "steps": 30, "cfg": 1.7, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
            "12": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["9", 0], "vae": ["7", 0]}},
            "35": {"class_type": "SaveAudioMP3", "inputs": {"audio": ["12", 0], "filename_prefix": prefix,
                                                           "quality": "320k"}},
        }
    if recipe["engine"] == "ace":
        if not (recipe.get("bpm") and recipe.get("key")):
            sys.exit("an ACE-Step recipe needs bpm and key: left unset, the workflow plays 64 BPM in D minor")
        wf = json.load(open(os.path.join(ROOT, "workflows", "06_acestep_music.json")))
        wf = {k: v for k, v in wf.items() if isinstance(v, dict) and "class_type" in v}
        wf["10"]["inputs"].update({"tags": recipe["tags"], "lyrics": recipe.get("lyrics", ""), "bpm": int(recipe["bpm"]),
                                   "keyscale": key_label(recipe["key"]), "duration": float(secs), "seed": seed})
        wf["11"]["inputs"]["seconds"] = float(secs)
        wf["12"]["inputs"]["seed"] = seed
        wf["14"]["inputs"]["filename_prefix"] = prefix
        return wf
    sys.exit("unknown engine %r (mm3 or ace)" % recipe["engine"])


def render(recipe, secs, dst):
    """One sample. A cover with "refine" is made twice: the first pass, then a cover OF that pass (the refine's
    own denoise / strength / tags) - the second pass starts from audio the model made, not from the recording,
    so less of the recording's own sound survives into it (2026-10-05)."""
    if recipe.get("engine") == "notes":
        return _render_notes(recipe, secs, dst)
    if recipe.get("engine") == "musicgen":
        return _render_musicgen(recipe, secs, dst)
    if recipe.get("engine") == "file":           # a reference clip put on a sheet as it is (an A/B, a diagnosis)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(ROOT, recipe["path"]), "-t", "%.2f" % secs,
                        "-b:a", "320k", dst], check=True)
        return 0.01
    took = _render_once(recipe, secs, dst)
    if took and recipe.get("engine") == "cover" and recipe.get("refine"):
        first = dst[:-4] + "_pass1" + dst[-4:]
        shutil.copy(dst, first)
        r2 = dict(recipe, **recipe["refine"])
        r2.pop("refine", None)
        r2.update({"source": os.path.abspath(first), "start": 0.0, "fresh_source": True})
        t2 = _render_once(r2, secs, dst)
        took = took + t2 if t2 else None
    return took


def _render_notes(recipe, secs, dst):
    """engine "notes": notes_cover.py plays the song's lead sheet as a style (secs of output = secs * stretch of
    the original, at speed `stretch`); with "polish", ACE-Step covers that render - the instruments already the right
    ones, so the model re-plays them rather than morphing the recording. "layers" mix styles, each with its own
    polish, gain_db and entry ("from": original seconds; silent before it but for a fill) - a real piano with a
    polished band joining at bar 9. "mode": "major" plays the tune in the major key (its 3rd, 6th, 7th raised)."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    t0 = time.time()
    speed = float(recipe.get("stretch", 1.0))
    layers = recipe.get("layers") or [{"style": recipe["style"], "polish": recipe.get("polish")}]
    env = dict(os.environ, PYTHONPATH=os.path.join(MUSIC_TOOLS, "lib"))
    parts = []
    for i, L in enumerate(layers):
        if L.get("file"):                    # a finished part laid in as it is (a sung vocal over the real piano)
            parts.append((L["file"], float(L.get("gain_db", 0.0)), None))
            continue
        wav = dst[:-4] + "_L%d_%s.wav" % (i, L["style"])
        cmd = ["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=6G", VENV_PY, NOTES_TOOL, "render",
               recipe["song"], L["style"], "%.3f" % float(recipe["start"]), "%.3f" % (secs * speed), "%.4f" % speed,
               wav, "--seed", str(int(L.get("seed", recipe.get("seed", 1))))]
        if L.get("from") is not None:
            cmd += ["--from", "%.3f" % float(L["from"])]
        if recipe.get("mode"):
            cmd += ["--mode", recipe["mode"]]
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=900)
        if r.returncode or not os.path.exists(wav):
            print("  notes render failed: %s" % (r.stderr or r.stdout)[-300:], flush=True)
            return None
        part = wav
        if L.get("polish"):
            p = dict(L["polish"])
            p.update({"engine": "cover", "source": os.path.abspath(wav), "start": 0.0, "fresh_source": True,
                      "secs": secs})
            part = wav[:-4] + "_polished.mp3"
            if not _render_once(p, secs, part):
                return None
        # a layer entering later stays silent until its lead-in fill (~4 eighths) - an AI pass may whisper there
        gate = (float(L["from"]) - float(recipe["start"]) - 1.6) / speed if L.get("from") is not None else None
        parts.append((part, float(L.get("gain_db", 0.0)), gate))
    if len(parts) == 1 and parts[0][1] == 0.0 and parts[0][2] is None:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", parts[0][0], "-b:a", "320k", dst], check=True)
    else:
        ins, fl = [], []
        for k, (p, g, gate) in enumerate(parts):
            ins += ["-i", p]
            chain = "aresample=44100,aformat=channel_layouts=stereo,volume=%.1fdB" % g
            if gate is not None and gate > 0:
                chain += ",volume=enable='lt(t,%.2f)':volume=0,afade=t=in:st=%.2f:d=0.25" % (gate, gate)
            fl.append("[%d:a]%s[a%d]" % (k, chain, k))
        fl.append("%samix=inputs=%d:normalize=0:duration=longest,alimiter=limit=0.89:level=false" % (
            "".join("[a%d]" % k for k in range(len(parts))), len(parts)))
        subprocess.run(["ffmpeg", "-v", "error", "-y"] + ins + ["-filter_complex", ";".join(fl), "-b:a", "320k",
                        dst], check=True)
    return time.time() - t0


def _render_musicgen(recipe, secs, dst):
    """engine "musicgen": MusicGen-Melody (Meta; the weights are CC BY-NC 4.0 - NON-COMMERCIAL ONLY, and the sheet
    says so on every card) writes an arrangement from scratch around the song's melody: notes_cover renders the
    melody alone as its guide (secs of output = secs * stretch of the original, at speed `stretch`; 30 s at most, the
    last 2.5 s faded). MusicGen is seed-sensitive: "seeds" [1, 2, 3] are all made and the take that best holds the
    original's harmony (harmony_held) is kept.
    {"engine": "musicgen", "song": "terra", "source": ..., "start": 6.93, "secs": 24, "stretch": 1.0,
     "prompt": "a lush string orchestra ...", "seeds": [1, 2, 3], "cfg": 3.0}"""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    t0 = time.time()
    speed = float(recipe.get("stretch", 1.0))
    gen = min(30.0, secs + 2.0)
    env = dict(os.environ, PYTHONPATH=os.path.join(MUSIC_TOOLS, "lib"))
    guide = dst[:-4] + "_guide.wav"
    r = subprocess.run(["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=6G", VENV_PY, NOTES_TOOL, "render",
                        recipe["song"], "melody", "%.3f" % float(recipe["start"]), "%.3f" % (gen * speed),
                        "%.4f" % speed, guide], env=env, capture_output=True, text=True, timeout=900)
    if r.returncode or not os.path.exists(guide):
        print("  melody guide failed: %s" % (r.stderr or r.stdout)[-300:], flush=True)
        return None
    seeds = [int(s) for s in (recipe.get("seeds") or [recipe.get("seed", 1)])]
    jobs = [{"guide": guide, "out": dst[:-4] + "_mg_s%d.wav" % s, "prompt": recipe["prompt"], "secs": gen, "seed": s,
             "cfg": float(recipe.get("cfg", 3.0))} for s in seeds]
    jf = dst[:-4] + "_mg_jobs.json"
    json.dump(jobs, open(jf, "w"))
    wait_for_queue()                                   # MusicGen shares the GPU with ComfyUI
    r = subprocess.run([VENV_PY, NOTES_TOOL, "musicgen", "--jobs", jf], env=env, capture_output=True, text=True,
                       timeout=2400)
    takes = [j["out"] for j in jobs if os.path.exists(j["out"])]
    if not takes:
        print("  musicgen failed: %s" % (r.stderr or r.stdout)[-300:], flush=True)
        return None
    ref = os.path.join(COMFY, "input", prep_source(recipe, secs))
    best, best_h = takes[0], -9.0
    for tk in takes:
        h = harmony_held(ref, tk)
        if h and h[0] > best_h:
            best, best_h = tk, h[0]
    print("  musicgen: kept %s (harmony %.3f) of %d seeds" % (os.path.basename(best), best_h, len(takes)), flush=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", best, "-t", "%.2f" % (secs + 1.5), "-af",
                    "afade=t=out:st=%.2f:d=2.5" % max(0.0, secs - 1.0), "-ac", "2", "-ar", "44100", "-b:a", "320k",
                    dst], check=True)
    return time.time() - t0


def _render_once(recipe, secs, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    wait_for_queue()
    t0 = time.time()
    for attempt in range(3):
        try:
            _, outs = comfy.run(HOST, graph(recipe, secs, "claude-generated/casting/%s" % os.path.basename(dst)[:-4]),
                                quiet=True)
            got = [o for o in outs or [] if str(o).lower().endswith((".mp3", ".flac", ".wav"))]
            if got:
                shutil.copy(os.path.join(COMFY, "output", got[0]), dst)
                return time.time() - t0
        except Exception as e:  # the box drops a socket now and then
            print("  render attempt %d failed: %s" % (attempt + 1, str(e)[:120]), flush=True)
            time.sleep(10)
    return None


def measure(p):
    o = subprocess.run(["ffmpeg", "-hide_banner", "-i", p, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    i = re.findall(r"I:\s+(-?[0-9.]+) LUFS", o)
    pk = re.findall(r"Peak:\s+(-?[0-9.]+) dBFS", o)
    return (float(i[-1]) if i else None), (float(pk[-1]) if pk else None)


def duration(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout.strip() or 0)


def level(src, dst, preview=None):
    """To -16 LUFS by a measured gain and a limiter (peaks under -2 dBFS) - not loudnorm's linear mode, which
    falls back to dynamic and left samples 1.5 LU apart (craft/SOUND.md 0.1)."""
    i0, _ = measure(src)
    g = TARGET - (i0 if i0 is not None else TARGET)
    i1 = None
    for _ in range(3):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af",
                        "volume=%.2fdB,alimiter=limit=0.79:level=false" % g, "-ar", "44100", "-b:a", "320k", dst],
                       check=True)
        i1, _ = measure(dst)
        if i1 is None or abs(i1 - TARGET) < 0.3:
            break
        g += TARGET - i1
    if preview:
        os.makedirs(os.path.dirname(preview), exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", dst, "-b:a", "128k", preview], check=True)
    return i1


# ------------------------------------------------------------------------------------------------ the sheet
def summary(r):
    if r["engine"] == "cover":
        den = float(r.get("denoise", 1.0))
        rf = r.get("refine")
        st = float(r.get("stretch", 1.0))
        return "%scover of %s from %.0f s%s · %s · its structure guiding %d%% of the steps%s · %s BPM · %s · %s" % (
            "ACE-Step 1.5 XL-SFT · " if r.get("model") == "xl" else "", os.path.basename(r["source"]),
            float(r.get("start", 0)), " at %d%% speed" % round(100 * st) if st != 1.0 else "",
            "re-played from silence" if den >= 1.0 else "re-played from the recording at denoise %.2f" % den,
            round(100 * float(r.get("strength", 1.0))),
            " · then covered again from that first pass at denoise %.2f" % float(rf.get("denoise", 0.55)) if rf else "",
            r.get("bpm"), r.get("key"), r["tags"][:140])
    if r["engine"] == "notes":
        st = float(r.get("stretch", 1.0))
        layers = r.get("layers") or [{"style": r["style"], "polish": r.get("polish")}]

        def one(L):
            if L.get("file"):
                return "%s%s" % (L.get("label") or os.path.basename(L["file"]),
                                 " at %+.0f dB" % float(L["gain_db"]) if L.get("gain_db") else "")
            p = L.get("polish")
            return "%s%s%s%s" % (L["style"], " from %.0f s" % float(L["from"]) if L.get("from") is not None else "",
                                 " at %+.0f dB" % float(L["gain_db"]) if L.get("gain_db") else "",
                                 " re-played by ACE-Step (denoise %.2f: %s)" % (float(p.get("denoise", 0.6)),
                                                                                p["tags"][:90]) if p else
                                 " (sampled, no AI)")
        return "the notes of %s from %.0f s (transcribed: melody, chords, bass)%s, played on sampled instruments%s: %s" % (
            os.path.basename(r["source"]), float(r.get("start", 0)),
            " in a MAJOR key" if r.get("mode") == "major" else "",
            " at %d%% speed" % round(100 * st) if st != 1.0 else " at its own speed", " + ".join(one(L) for L in layers))
    if r["engine"] == "musicgen":
        st = float(r.get("stretch", 1.0))
        return ("NON-COMMERCIAL (MusicGen weights, CC BY-NC 4.0) · MusicGen-Melody wrote this from scratch around the "
                "melody of %s from %.0f s (the transcribed notes, played alone as its guide)%s · seed %s · %s" % (
                    os.path.basename(r["source"]), float(r.get("start", 0)),
                    " at %d%% speed" % round(100 * st) if st != 1.0 else " at its own speed",
                    "/".join(str(s) for s in (r.get("seeds") or [r.get("seed", 1)])) + " (the best kept)",
                    r["prompt"][:140]))
    if r["engine"] == "file":
        return "a reference clip, as it is: %s" % os.path.basename(r["path"])
    if r["engine"] == "remix":
        return "remix of %s from %.0f s · denoise %.2f · %s · %s" % (
            os.path.basename(r["source"]), float(r.get("start", 0)), float(r.get("denoise", 0.45)),
            "ACE-Step v1" if r.get("model") == "ace1" else "ACE-Step 1.5", r["tags"][:140])
    if r["engine"] == "ace":
        return "%s · %s BPM · %s" % (r["tags"][:150], r.get("bpm"), r.get("key"))
    first = r["caption"].strip().split("\n")[0]
    first = re.sub(r"^Global Metadata:\s*", "", first)
    return first[:220] + ("…" if len(first) > 220 else "")


def sheet(c, which):
    d = base(c["film"], c["scene"])
    if which == "finals":
        items, title, note = c.get("finals", []), "finalists", ""
    else:
        r = c["rounds"][int(which) - 1]
        items, title = r["samples"], ("auditions" if r["n"] == 1 else "callbacks, round %d" % r["n"])
        note = r.get("note", "")     # what this round changed, in a sentence or two (round --note)
    cards = []
    for k, s in enumerate(items, 1):
        prev = os.path.join(d, s.get("preview") or s["file"])
        data = base64.b64encode(open(prev, "rb").read()).decode() if os.path.exists(prev) else ""
        lineage = ""
        if s.get("parent"):
            lineage = "from <b>%s</b>%s" % (html.escape(s["parent"]), " - " + html.escape(s["note"]) if s.get("note") else "")
        elif s.get("note"):
            lineage = html.escape(s["note"])
        if s.get("kept") is not None:
            lineage += "%stune kept <b>%.2f</b> (1 = the original; about 0.57 = the tune gone)" % (
                " · " if lineage else "", s["kept"])
        if s.get("harmony"):
            lineage += "%sharmony held <b>%.2f</b>, weakest two bars %.2f" % (
                " · " if lineage else "", s["harmony"][0], s["harmony"][1])
        cards.append("""<article class="card" data-id="%(id)s">
  <header><span class="num">%(k)d</span><span class="id">%(id)s</span><span class="name">%(name)s</span>
  <span class="eng">%(eng)s · %(secs).0f s</span></header>
  <audio controls preload="none" src="data:audio/mpeg;base64,%(data)s"></audio>
  <p class="sum">%(sum)s</p><p class="lin">%(lin)s</p>
  <div class="acts"><label><input type="checkbox" class="pick"> pick</label>
  <label><input type="checkbox" class="keep"> keep</label></div>
</article>""" % {"id": html.escape(s["id"]), "k": k, "name": html.escape(s.get("name", "")),
                 "eng": ENGINE_NAME.get(s["recipe"]["engine"], s["recipe"]["engine"]), "secs": s.get("secs") or 0,
                 "data": data, "sum": html.escape(summary(s["recipe"])), "lin": lineage})
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Score casting · %(scene)s</title>
<style>
:root{--bg:#f6f4ef;--ink:#1d1b18;--muted:#6b665d;--card:#fff;--line:#e2ddd3;--accent:#b24a1f}
@media (prefers-color-scheme:dark){:root{--bg:#161513;--ink:#ece8e1;--muted:#a39d92;--card:#201f1c;--line:#34312c;--accent:#e0794d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,sans-serif}
main{max-width:980px;margin:0 auto;padding:20px 16px 120px}h1{font-size:22px;margin:0 0 4px}
.brief{color:var(--muted);margin:0 0 18px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.note{background:var(--card);border-left:3px solid var(--accent);border-radius:6px;padding:10px 12px;margin:0 0 18px;font-size:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}
.card.picked{outline:2px solid var(--accent)}header{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:baseline}
.num{font-weight:700;font-size:18px;color:var(--accent)}.id{font-family:ui-monospace,monospace;color:var(--muted)}
.name{font-weight:600}.eng{color:var(--muted);font-size:13px;width:100%%}audio{width:100%%;margin:8px 0}
.sum{font-size:13px;margin:4px 0}.lin{font-size:12px;color:var(--muted);margin:0}.acts{display:flex;gap:16px;margin-top:8px}
footer{position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--line);padding:10px 16px}
footer div{max-width:980px;margin:0 auto;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
code{font-family:ui-monospace,monospace}button{font:inherit;padding:6px 12px;border-radius:8px;border:1px solid var(--line);
background:var(--bg);color:var(--ink);cursor:pointer}#copied{color:var(--muted);font-size:13px}
</style></head><body><main>
<h1>Score casting · %(film)s / %(scene)s · %(title)s</h1>
<p class="brief">%(brief)s - every sample at -16 LUFS. Tick <b>pick</b> for what the next round should be closer to,
<b>keep</b> for the shortlist; then tell me the line at the bottom.</p>
%(note)s<div class="grid">%(cards)s</div></main>
<footer><div><span>Reply with:</span><code id="line">nothing ticked yet</code><button id="copy">copy</button>
<span id="copied"></span></div></footer>
<script>
function line(){const p=[],k=[];document.querySelectorAll('.card').forEach(c=>{const id=c.dataset.id;
 const pk=c.querySelector('.pick').checked,kp=c.querySelector('.keep').checked;c.classList.toggle('picked',pk);
 if(pk)p.push(id);if(kp)k.push(id)});
 const t=(p.length?'pick '+p.join(' '):'')+(k.length?(p.length?'; ':'')+'keep '+k.join(' '):'');
 document.getElementById('line').textContent=t||'nothing ticked yet';return t}
document.querySelectorAll('input').forEach(i=>i.addEventListener('change',line));
document.getElementById('copy').addEventListener('click',()=>{const t=line();
 if(navigator.clipboard)navigator.clipboard.writeText(t).then(()=>{document.getElementById('copied').textContent='copied'});});
document.querySelectorAll('audio').forEach(a=>a.addEventListener('play',()=>document.querySelectorAll('audio').forEach(b=>{if(b!==a)b.pause()})));
</script></body></html>""" % {"film": html.escape(c["film"]), "scene": html.escape(c["scene"]), "title": title,
                               "brief": html.escape(c.get("brief", "")), "cards": "\n".join(cards),
                               "note": '<p class="note">%s</p>\n' % html.escape(note) if note else ""}
    out = os.path.join(d, "sheet_%s.html" % ("finals" if which == "finals" else "r%s" % which))
    open(out, "w", encoding="utf-8").write(page)
    return out


# ------------------------------------------------------------------------------------------------ stages
def cmd_new(a):
    if os.path.exists(os.path.join(base(a.film, a.scene), "casting.json")) and not a.force:
        sys.exit("a casting exists for %s / %s (--force to start over)" % (a.film, a.scene))
    c = {"film": a.film, "scene": a.scene, "secs": float(a.secs), "brief": a.brief, "video": a.video, "sfx": a.sfx,
         "rounds": [], "keep": [], "finals": [], "cast": None, "understudies": []}
    save(c)
    print("casting started:", base(a.film, a.scene))


def audition_secs(c):
    """A sample long enough to hear the arrangement and an ending; for a short scene, the scene itself."""
    return round(min(c["secs"] + 2.0, 34.0), 1)


def cmd_round(a):
    c = load(a.film, a.scene)
    recipes = json.load(open(a.recipes, encoding="utf-8"))
    n = len(c["rounds"]) + 1
    d = base(c["film"], c["scene"])
    secs = audition_secs(c)
    rnd = {"n": n, "samples": [], "picks": [], "note": a.note or ""}
    for k, r in enumerate(recipes, 1):
        sid = "r%d-%02d" % (n, k)
        raw = os.path.join(d, "r%d" % n, "_raw", sid + ".mp3")
        secs = float(r.get("secs") or audition_secs(c))    # a recipe may ask for its own length (a whole theme)
        took = render(r, secs, raw)
        if not took:
            print("  %s FAILED" % sid, flush=True)
            continue
        f, pv = os.path.join("r%d" % n, sid + ".mp3"), os.path.join("r%d" % n, "preview", sid + ".mp3")
        lufs = level(raw, os.path.join(d, f), os.path.join(d, pv))
        s = {"id": sid, "name": r.get("name", ""), "recipe": {k2: v for k2, v in r.items() if k2 not in ("parent", "note")},
             "parent": r.get("parent"), "note": r.get("note", ""), "file": f, "preview": pv,
             "secs": round(duration(os.path.join(d, f)), 1), "lufs": lufs}
        if r["engine"] in ("remix", "cover", "notes", "musicgen") or (r["engine"] == "file" and r.get("source")):
            src = os.path.join(COMFY, "input", prep_source(r, secs))
            s["kept"] = tune_kept(src, os.path.join(d, f))
            s["harmony"] = harmony_held(src, os.path.join(d, f))
        rnd["samples"].append(s)
        print("  %s %-28s %-15s %4.0fs render, %.1f s long" % (sid, s["name"][:28], ENGINE_NAME[r["engine"]], took,
                                                               s["secs"]), flush=True)
        c["rounds"] = [x for x in c["rounds"] if x["n"] != n] + [rnd]
        save(c)
    print("sheet ->", sheet(c, n))


def cmd_vary(a):
    """Callbacks closer to a pick: the same recipe on new seeds, and the tempo nudged either way. Edit the output
    before rendering - a director's word ("heavier drums", "less busy") goes in as a hand-written variant."""
    c = load(a.film, a.scene)
    p = find(c, a.frm)
    r0 = dict(p["recipe"])
    out = []
    seed0 = int(r0.get("seed", 222))

    def key(r):
        return (r["engine"], r.get("caption") or r.get("tags"), r.get("bpm"), r.get("key"), int(r.get("seed", 0)),
                r.get("source"), r.get("start"), r.get("denoise"), r.get("strength"))
    # a callback must never re-render a sample the casting already has (the same recipe on the same seed)
    used = {key(s["recipe"]) for rr in c["rounds"] for s in rr["samples"]}
    nseeds = max(1, a.n - 2)
    seed = seed0
    for i in range(nseeds):
        seed += 7919
        while key(dict(r0, seed=seed)) in used:
            seed += 7919
        r = dict(r0, seed=seed, parent=p["id"], note="same recipe, a new seed")
        used.add(key(r))
        r["name"] = "%s · seed %d" % (p.get("name", "").split(" · ")[0], r["seed"])
        out.append(r)
    step = a.step
    if r0["engine"] == "remix":
        # a remix's nudge is its dial: closer to the director's own recording, or further from it
        for dd, word in ((-0.1, "closer to the original"), (+0.1, "further from the original")):
            if len(out) >= a.n:
                break
            den = round(min(0.9, max(0.15, float(r0.get("denoise", 0.45)) + dd)), 2)
            r = dict(r0, parent=p["id"], seed=seed0, denoise=den, note="%s: denoise %.2f" % (word, den))
            if key(r) in used or den == float(r0.get("denoise", 0.45)):
                continue
            used.add(key(r))
            r["name"] = "%s · %s" % (p.get("name", "").split(" · ")[0], word)
            out.append(r)
    if r0["engine"] == "cover":
        # a cover's nudge is its strength: the source's own notes held for more of the steps, or for fewer
        for dd, word in ((+0.15, "closer to the source"), (-0.15, "freer")):
            if len(out) >= a.n:
                break
            st = round(min(1.0, max(0.2, float(r0.get("strength", 1.0)) + dd)), 2)
            r = dict(r0, parent=p["id"], seed=seed0, strength=st, note="%s: strength %.2f" % (word, st))
            if key(r) in used or st == float(r0.get("strength", 1.0)):
                continue
            used.add(key(r))
            r["name"] = "%s · %s" % (p.get("name", "").split(" · ")[0], word)
            out.append(r)
    for sign, word in ((+1, "faster"), (-1, "slower")):
        if len(out) >= a.n or r0["engine"] in ("remix", "cover"):
            break
        r = dict(r0, parent=p["id"], seed=seed0)
        if r0["engine"] == "ace":
            r["bpm"] = int(round(int(r0["bpm"]) * (1 + step * sign)))
            r["note"] = "tempo %s: %d BPM, the same seed" % (word, r["bpm"])
        else:
            m = re.search(r"(\d+)\s*BPM", r0["caption"])
            if not m:
                continue
            bpm = int(round(int(m.group(1)) * (1 + step * sign)))
            r["caption"] = r0["caption"].replace(m.group(0), "%d BPM" % bpm, 1)
            r["note"] = "tempo %s: %d BPM, the same seed" % (word, bpm)
        if key(r) in used:
            continue
        used.add(key(r))
        r["name"] = "%s · %s" % (p.get("name", "").split(" · ")[0], word)
        out.append(r)
    txt = json.dumps(out, indent=1, ensure_ascii=False)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(txt)
        print("%d callbacks -> %s" % (len(out), a.out))
    else:
        print(txt)


def cmd_pick(a):
    c = load(a.film, a.scene)
    if not c["rounds"]:
        sys.exit("no rounds yet")
    for sid in list(a.ids) + list(a.keep or []):
        find(c, sid)
    c["rounds"][-1]["picks"] = list(a.ids)
    for sid in a.keep or []:
        if sid not in c["keep"]:
            c["keep"].append(sid)
    save(c)
    print("round %d picks: %s | shortlist: %s" % (c["rounds"][-1]["n"], " ".join(a.ids) or "-", " ".join(c["keep"]) or "-"))


def mix_under(video, sfx, score, secs, dst):
    """The finalist under its picture: the takes' own sound leads, the score ducks under it."""
    if not (video and sfx):
        return None
    graph_ = ("[2:a]volume=0.55,afade=t=out:st=%.2f:d=1.5[m];[1:a]asplit=2[sc][fx];"
              "[m][sc]sidechaincompress=threshold=0.03:ratio=6:attack=8:release=350[md];"
              "[fx][md]amix=inputs=2:duration=first:dropout_transition=0,loudnorm=I=-15:TP=-1.5:LRA=11[a]"
              % max(0.0, secs - 1.5))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", sfx, "-i", score, "-filter_complex",
                    graph_, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    dst], check=True)
    return dst


VENV_PY = os.path.join(COMFY, "venv", "bin", "python3")     # librosa lives in ComfyUI's venv


def tune_kept(src, out):
    """How much of the source's notes a remix or cover kept: pitch-class (chroma) agreement, time-aligned, 1.0 the
    original itself. Calibrated on TerraTheme 2026-10-01: a remix at denoise 0.45 keeps 0.87; music in the same key
    with the tune gone sits near 0.57."""
    r = subprocess.run([VENV_PY, os.path.abspath(__file__), "_chroma", src, out], capture_output=True, text=True)
    try:
        return round(float(r.stdout.strip().splitlines()[-1]), 3)
    except (ValueError, IndexError):
        return None


def _chroma_impl(src, out):
    import numpy as np
    import librosa
    sr, hop = 22050, 2048
    dur = librosa.get_duration(path=src)
    a = librosa.feature.chroma_cqt(y=librosa.load(src, sr=sr)[0], sr=sr, hop_length=hop)
    b = librosa.feature.chroma_cqt(y=librosa.load(out, sr=sr, duration=dur)[0], sr=sr, hop_length=hop)
    best = 0.0
    for off in range(-5, 6):                                 # best of +-0.46 s
        x, y = (a[:, off:], b) if off >= 0 else (a, b[:, -off:])
        m = min(x.shape[1], y.shape[1])
        cos = (x[:, :m] * y[:, :m]).sum(0) / (np.linalg.norm(x[:, :m], axis=0) * np.linalg.norm(y[:, :m], axis=0) + 1e-9)
        best = max(best, float(cos.mean()))
    print("%.4f" % best)


def harmony_held(src, out):
    """Whether a cover keeps the source's harmony phrase by phrase: the correlation of the two clips' average pitch
    classes over each 6 s window (two bars at 81 BPM), the mean and the weakest window. 2026-10-05: the TerraTheme
    covers told "Ab minor" kept the tune but turned whole phrases into Ab major or F minor - a clip's average hides
    that, its weakest two bars show it. Returns [mean, weakest] or None."""
    r = subprocess.run([VENV_PY, os.path.abspath(__file__), "_harmony", src, out], capture_output=True, text=True)
    try:
        m, w = r.stdout.strip().splitlines()[-1].split()
        return [round(float(m), 3), round(float(w), 3)]
    except (ValueError, IndexError):
        return None


def _harmony_impl(src, out, win=6.0):
    import numpy as np
    import librosa
    sr, hop = 22050, 512
    dur = librosa.get_duration(path=src)
    ys, yo = librosa.load(src, sr=sr)[0], librosa.load(out, sr=sr, duration=dur)[0]
    a = librosa.feature.chroma_cqt(y=librosa.effects.harmonic(ys), sr=sr, hop_length=hop)
    b = librosa.feature.chroma_cqt(y=librosa.effects.harmonic(yo), sr=sr, hop_length=hop)
    e = librosa.feature.rms(y=ys, hop_length=hop)[0]
    n, w = min(a.shape[1], b.shape[1], len(e)), int(win * sr / hop)
    windows = [i for i in range(0, max(1, n - w + 1), w // 2)]
    loud = max(e[i:i + w].mean() for i in windows)
    cs = [float(np.corrcoef(a[:, i:i + w].mean(1), b[:, i:i + w].mean(1))[0, 1]) for i in windows
          if e[i:i + w].mean() > loud / 30]                # a near-silent stretch of the source has no harmony to hold
    print("%.4f %.4f" % (np.mean(cs), np.min(cs)) if cs else "nan nan")


def extend_exact(src, dst, target):
    """The director's EXACT take, made the length the picture needs (2026-10-01: "it should be extensions of the exact
    song I selected, not a new round with longer songs"). Shorter: the take itself, faded at the length. Longer: an
    extended edit - the take plays, jumps back at a bar line to a matching point and loops that stretch of its own
    music, then plays its own ending. Every note is from the take. Returns a note on what was done."""
    r = subprocess.run([VENV_PY, os.path.abspath(__file__), "_extend", src, dst, "%.3f" % target],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("extend failed: %s" % (r.stderr or r.stdout)[-600:])
    return r.stdout.strip().splitlines()[-1]


def _extend_impl(src, dst, target):
    import numpy as np
    import librosa
    sr = 44100
    y, _ = librosa.load(src, sr=sr, mono=False)
    if y.ndim == 1:
        y = np.vstack([y, y])
    n = y.shape[1]
    length = n / sr
    if target <= length + 0.05:
        out = y[:, :int(target * sr)].copy()
        fade = int(min(1.5, target / 4) * sr)
        if target < length - 0.25:
            out[:, -fade:] *= np.linspace(1.0, 0.0, fade)[None, :]
        note = "the take itself%s" % (", faded at %.1f s" % target if target < length - 0.25 else "")
    else:
        mono = librosa.to_mono(y)
        _, beats = librosa.beat.beat_track(y=mono, sr=sr, units="samples")
        beats = np.asarray(beats, dtype=int)
        hop = 512
        chroma = librosa.feature.chroma_cqt(y=mono, sr=sr, hop_length=hop)
        mfcc = librosa.feature.mfcc(y=mono, sr=sr, n_mfcc=13, hop_length=hop)
        mfcc = (mfcc - mfcc.mean(1, keepdims=True)) / (mfcc.std(1, keepdims=True) + 1e-9)
        feat = np.vstack([chroma * 3.0, mfcc * 0.5])
        beat_len = int(np.median(np.diff(beats))) if len(beats) > 2 else sr // 2
        span = max(4, (2 * beat_len) // hop)

        def win(s):
            f0 = int(s) // hop
            return feat[:, f0:f0 + span]
        # a loop is scored on three things (calibrated on the duel's two takes, 2026-10-01): how seamless the jump
        # is (d, the music after the two points compared - 1.3 smooth to 2.7 rough), how often the listener hears it
        # again (0.06 a repeat: a 3-minute edit of #5 loops its whole 22 s middle 7 times rather than 11 s 14 times),
        # and how far the take's own ending is pushed past the picture (0.1 a second: a 30-second fight gets a 5 s
        # loop, not an 11 s one that pushes the ending out of the picture)
        need = target - length
        best = None
        for L in (64, 48, 40, 32, 24, 16, 8):
            for a in range(2, len(beats) - L):
                b = a + L
                if beats[b] > n - 2 * sr:          # leave the take's own ending after the loop
                    break
                wa, wb = win(beats[a]), win(beats[b])
                m = min(wa.shape[1], wb.shape[1])
                if m < 4:
                    continue
                d = float(np.linalg.norm(wa[:, :m] - wb[:, :m]) / np.sqrt(m))
                loop = (beats[b] - beats[a]) / sr
                k = max(1, int(np.ceil(need / loop)))
                score = d + 0.06 * k + 0.1 * (k * loop - need)
                if best is None or score < best[0]:
                    best = (score, a, b, L)
        if best is None:                           # too short to find bars: loop the whole take
            ta, tb, L = 0, n, 0
        else:
            ta, tb, L = beats[best[1]], beats[best[2]], best[3]
        k = max(1, int(np.ceil((target - length) / ((tb - ta) / sr))))
        xf = int(0.04 * sr)
        ramp = np.sin(np.linspace(0, np.pi / 2, xf))[None, :]
        out = y[:, :tb].copy()
        for _ in range(k):
            nxt = y[:, ta:tb]
            out[:, -xf:] = out[:, -xf:] * ramp[:, ::-1] + nxt[:, :xf] * ramp
            out = np.concatenate([out, nxt[:, xf:]], axis=1)
        out = np.concatenate([out, y[:, tb:]], axis=1)
        note = ("extended to %.0f s: bars of the take from %.1f to %.1f s (%d beats) looped %d time%s, then its own "
                "ending" % (out.shape[1] / sr, ta / sr, tb / sr, L, k, "" if k == 1 else "s"))
    pcm = np.clip(out.T, -1.0, 1.0).astype(np.float32).tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "2", "-i", "-",
                    "-b:a", "320k", dst], input=pcm, check=True)
    print(note)


def _develop_impl(spec_path):
    """develop's worker (ComfyUI's venv): the stems - the finalist's own edit ("take") and its covers, all the
    edit's length and in time with it - put through the plan's sections, each switch on a bar line, crossfaded."""
    import numpy as np
    import librosa
    spec = json.load(open(spec_path, encoding="utf-8"))
    sr = 44100
    stems = {}
    for name, p in spec["stems"].items():
        y, _ = librosa.load(p, sr=sr, mono=False)
        stems[name] = np.vstack([y, y]) if y.ndim == 1 else y
    n = min(y.shape[1] for y in stems.values())
    take = stems["take"][:, :n]
    ref = float(np.sqrt(np.mean(take ** 2)) + 1e-9)
    hop = 256
    mono = librosa.to_mono(take)
    on_t = librosa.onset.onset_strength(y=mono, sr=sr, hop_length=hop)
    lags = {}
    for name in list(stems):
        y = stems[name][:, :n]
        y = y * (ref / float(np.sqrt(np.mean(y ** 2)) + 1e-9))       # every stem at the take's level first
        if name != "take":                                            # a cover should already sit in time with
            on_c = librosa.onset.onset_strength(y=librosa.to_mono(y), sr=sr, hop_length=hop)   # the edit: check
            m = min(len(on_t), len(on_c))
            best = max(range(-10, 11), key=lambda L: float(np.dot(on_t[max(0, L):m + min(0, L)],
                                                                  on_c[max(0, -L):m - max(0, L)])))
            lags[name] = best * hop * 1000.0 / sr
            if best:                                                  # and nudge it in if it is not
                y = np.roll(y, best * hop, axis=1)
                if best > 0:
                    y[:, :best * hop] = 0.0
                else:
                    y[:, best * hop:] = 0.0
        stems[name] = y
    # bar lines: the beats, and the phase of four whose beats hit hardest in the low end (a crude downbeat)
    _, beats = librosa.beat.beat_track(y=mono, sr=sr, units="samples")
    low = librosa.onset.onset_strength(y=mono, sr=sr, hop_length=hop, fmax=200)
    phase = max(range(4), key=lambda p: float(np.mean([low[min(len(low) - 1, b // hop)] for b in beats[p::4]] or [0])))
    bars = np.asarray(beats[phase::4], dtype=int)
    secs = sorted(spec["sections"], key=lambda s: float(s["at"]))
    starts = []
    for i, s in enumerate(secs):
        at = int(float(s["at"]) * sr)
        starts.append(0 if i == 0 else int(bars[np.argmin(np.abs(bars - at))]) if len(bars) else at)
    starts.append(n)
    out = np.zeros((2, n), dtype=np.float64)
    t = np.arange(n)
    for i, s in enumerate(secs):
        a0, a1 = starts[i], starts[i + 1]
        if a1 <= a0:
            continue
        xin = int(float(s.get("xfade", spec.get("xfade", 0.25))) * sr) if i else 0
        xout = int(float(secs[i + 1].get("xfade", spec.get("xfade", 0.25))) * sr) if i + 1 < len(secs) else 0
        env = np.zeros(n)
        lo, hi = max(0, a0 - xin // 2), min(n, a1 + xout // 2)
        env[lo:hi] = 1.0
        if xin:                      # equal-gain (raised cosine): the stems play the same notes at the same time
            r = (t[lo:a0 + xin // 2] - (a0 - xin // 2)) / max(1, xin)
            env[lo:a0 + xin // 2] = 0.5 - 0.5 * np.cos(np.pi * np.clip(r, 0, 1))
        if xout:
            r = (t[a1 - xout // 2:hi] - (a1 - xout // 2)) / max(1, xout)
            env[a1 - xout // 2:hi] = 0.5 + 0.5 * np.cos(np.pi * np.clip(r, 0, 1))
        g0 = float(s.get("gain_db", 0.0))
        g1 = float(s.get("gain_db_end", g0))
        gain = np.ones(n) * 10 ** (g0 / 20)
        gain[a0:a1] = 10 ** (np.linspace(g0, g1, a1 - a0) / 20)
        gain[a1:] = 10 ** (g1 / 20)
        out += stems[s["use"]][:, :n] * (env * gain)[None, :]
    pk = float(np.max(np.abs(out)))
    if pk > 0.98:
        out *= 0.98 / pk
    pcm = out.T.astype(np.float32).tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "2", "-i", "-", "-b:a", "320k",
                    spec["out"]], input=pcm, check=True)
    print(json.dumps({"lags_ms": {k: round(v) for k, v in lags.items()},
                      "switches": [[round(starts[i] / sr, 2), s["use"]] for i, s in enumerate(secs)]}))


def long_form(recipe, secs):
    """MiniMax Music 3 sizes a piece by its STRUCTURE, not by max_duration (2026-10-01, asked for 187 s): the
    audition's own 4 section tags gave 28 and 35 s, 9 tags 64 and 88 s, 23 tags 134 s - about 6 s a tag; a form
    written out in bars gave only 72 s. So a long piece gets one section tag per ~6 s and a sentence naming the
    whole form. ACE-Step stops near 45 s whatever it is asked: long pieces are mm3's."""
    if recipe["engine"] != "mm3" or secs < 60:
        return recipe
    n = max(4, int(round(secs / 6.0)))
    body = ["[Bridge]" if i == (n - 2) // 2 else "[Instrumental]" for i in range(n - 2)]
    mm, ss = divmod(int(round(secs)), 60)
    form = (" Form: one continuous %d:%02d piece - an intro, the main theme, a development section that builds, a "
            "breakdown, the theme returning bigger, a climax and an outro; it keeps going to the very end." % (mm, ss))
    return dict(recipe, caption=recipe["caption"].rstrip() + form, lyrics="\n\n".join(["[Intro]"] + body + ["[Outro]"]))


def cmd_final(a):
    """Each shortlisted sample made into the full piece for a picture. By default the director's EXACT take
    (extend_exact): the take itself when the picture is no longer than it, an extended edit of the take's own bars
    when it is. --secs / --video / --sfx / --label make a version for another cut (the long film). --fresh instead
    renders the recipe anew at the length - different music, a new performance - for when that is what's wanted."""
    c = load(a.film, a.scene)
    d = base(c["film"], c["scene"])
    picture = a.secs if a.secs_given else c["secs"]
    video, sfx = a.video or c.get("video"), a.sfx or c.get("sfx")
    label = a.label or ("%.0f s" % picture)
    k = len(c["finals"])
    for sid in a.ids:
        src = find(c, sid)
        for j in range(a.seeds if a.fresh else 1):
            k += 1
            fid = "f-%02d" % k
            raw = os.path.join(d, "finals", "_raw", fid + ".mp3")
            os.makedirs(os.path.dirname(raw), exist_ok=True)
            t0 = time.time()
            if a.fresh:
                secs = round(picture + 3.0, 1)
                r = long_form(dict(src["recipe"], seed=int(src["recipe"].get("seed", 222)) + 7919 * j), secs)
                if not render(r, secs, raw):
                    print("  %s FAILED" % fid, flush=True)
                    continue
                note = "a fresh render of the recipe for %s (new music, not the take)" % label
            else:
                r = dict(src["recipe"])
                note = extend_exact(os.path.join(d, src["file"]), raw, picture + 1.0)
            took = time.time() - t0
            f, pv = os.path.join("finals", fid + ".mp3"), os.path.join("finals", "preview", fid + ".mp3")
            lufs = level(raw, os.path.join(d, f), os.path.join(d, pv))
            mix = mix_under(video, sfx, os.path.join(d, f), picture, os.path.join(d, "finals", fid + "_mix.mp4"))
            c["finals"].append({"id": fid, "name": "%s · %s" % (src.get("name", ""), label), "recipe": r, "parent": sid,
                                "note": note, "file": f, "preview": pv, "mix": os.path.relpath(mix, d) if mix else None,
                                "picture": video, "sfx": sfx, "for_secs": picture,
                                "secs": round(duration(os.path.join(d, f)), 1), "lufs": lufs})
            save(c)
            print("  %s from %s (%s) %4.0fs: %s%s" % (fid, sid, label, took, note,
                                                     ", mixed under the picture" if mix else ""), flush=True)
    print("sheet ->", sheet(c, "finals"))


def cmd_develop(a):
    """A finalist DEVELOPED instead of looped (2026-10-01, the director on f-03: "audibly looping - can it be extended
    not by straight looping but by reimagining what it would sound like if it was orchestrated further?"). The
    finalist's own extended edit is covered once per arrangement in the plan (ACE-Step 1.5's hybrid cover: the tune
    kept, every instrument re-played), each cover the edit's full length and beat for beat in time with it. The
    piece then moves from arrangement to arrangement at the plan's times - each switch on a bar line, crossfaded -
    so a switch is the same moment of the same tune in a richer orchestration, never a jump. The take as picked
    opens it; the plan's arc follows the film's acts. A plan:
        {"bpm": 185, "key": "C major",
         "covers": {"strings": {"tags": "...", "denoise": 0.62, "strength": 0.5, "seed": 4242}, ...},
         "sections": [{"at": 0, "use": "take"}, {"at": 34.7, "use": "strings", "gain_db": 0, "gain_db_end": 1},
                      {"at": 157.4, "use": "soft", "gain_db": -6, "xfade": 1.5}, ...]}"""
    c = load(a.film, a.scene)
    d = base(c["film"], c["scene"])
    src = find(c, a.ids[0])
    plan = json.load(open(a.plan, encoding="utf-8"))
    edit = os.path.join(d, "finals", "_raw", src["id"] + ".mp3")       # the finalist's exact edit, before levelling
    secs = round(duration(edit), 2)
    fid = "f-%02d" % (len(c["finals"]) + 1)
    work = os.path.join(d, "finals", "_develop", fid)
    os.makedirs(work, exist_ok=True)
    stems, kept = {"take": edit}, {}
    for name, cv in plan["covers"].items():
        r = dict(cv, engine="cover", source=os.path.abspath(edit), start=0.0, bpm=plan["bpm"], key=plan["key"])
        raw = os.path.join(work, name + ".mp3")
        if not os.path.exists(raw):
            t0 = time.time()
            if not render(r, secs, raw):
                sys.exit("the %s cover failed" % name)
            print("  %-10s covered in %.0fs" % (name, time.time() - t0), flush=True)
        stems[name] = raw
        kept[name] = tune_kept(os.path.join(COMFY, "input", prep_source(r, secs)), raw)
    spec = {"stems": stems, "sections": plan["sections"], "xfade": plan.get("xfade", 0.25),
            "out": os.path.join(d, "finals", "_raw", fid + ".mp3")}
    sp = os.path.join(work, "spec.json")
    json.dump(spec, open(sp, "w", encoding="utf-8"), indent=1)
    r = subprocess.run([VENV_PY, os.path.abspath(__file__), "_develop", sp], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("develop failed: %s" % (r.stderr or r.stdout)[-800:])
    got = json.loads(r.stdout.strip().splitlines()[-1])
    f, pv = os.path.join("finals", fid + ".mp3"), os.path.join("finals", "preview", fid + ".mp3")
    lufs = level(spec["out"], os.path.join(d, f), os.path.join(d, pv))
    video, sfx = a.video or src.get("picture"), a.sfx or src.get("sfx")
    picture = src.get("for_secs") or c["secs"]
    mix = mix_under(video, sfx, os.path.join(d, f), picture, os.path.join(d, "finals", fid + "_mix.mp4"))
    arc = ", ".join("%d:%02d %s" % (int(t // 60), int(t % 60), u) for t, u in got["switches"])
    note = ("%s developed, not looped: its own edit re-orchestrated section by section (%s); every cover keeps the "
            "tune (%s)" % (src["id"], arc, ", ".join("%s %.2f" % (k, v) for k, v in kept.items() if v is not None)))
    c["finals"].append({"id": fid, "name": "%s · developed" % src.get("name", "").split(" · ")[0], "recipe": src["recipe"],
                        "parent": src.get("parent"), "from": src["id"], "plan": plan, "note": note, "file": f,
                        "preview": pv, "mix": os.path.relpath(mix, d) if mix else None, "picture": video, "sfx": sfx,
                        "for_secs": picture, "secs": round(duration(os.path.join(d, f)), 1), "lufs": lufs,
                        "lags_ms": got["lags_ms"]})
    save(c)
    print("  %s: %s%s" % (fid, note, ", mixed under the picture" if mix else ""))
    print("  covers' timing against the edit (ms):", got["lags_ms"])
    print("sheet ->", sheet(c, "finals"))


def cmd_cast(a):
    c = load(a.film, a.scene)
    d = base(c["film"], c["scene"])
    pick = find(c, a.id)
    os.makedirs(os.path.dirname(os.path.abspath(a.to)), exist_ok=True)
    shutil.copy(os.path.join(d, pick["file"]), a.to)
    under = os.path.join(os.path.dirname(os.path.abspath(a.to)), "understudies", c["scene"])
    os.makedirs(under, exist_ok=True)
    c["understudies"] = []
    for f in c["finals"]:
        if f["id"] != a.id:
            dst = os.path.join(under, "%s_%s.mp3" % (f["id"], re.sub(r"[^a-z0-9]+", "-", f.get("name", "").lower()).strip("-")))
            shutil.copy(os.path.join(d, f["file"]), dst)
            c["understudies"].append({"id": f["id"], "file": dst})
    c["cast"] = {"id": a.id, "to": os.path.abspath(a.to), "when": time.strftime("%Y-%m-%d %H:%M")}
    save(c)
    print("cast %s -> %s; %d understudies in %s" % (a.id, a.to, len(c["understudies"]), under))


def cmd_status(a):
    c = load(a.film, a.scene)
    print("%s / %s: %.0f s - %s" % (c["film"], c["scene"], c["secs"], c.get("brief", "")))
    for r in c["rounds"]:
        print("  round %d: %d samples, picks %s" % (r["n"], len(r["samples"]), " ".join(r["picks"]) or "-"))
    print("  shortlist:", " ".join(c["keep"]) or "-")
    print("  finalists:", " ".join(f["id"] for f in c["finals"]) or "-")
    print("  cast:", (c["cast"] or {}).get("id", "-"), "| understudies:", len(c.get("understudies", [])))


def main():
    if len(sys.argv) == 5 and sys.argv[1] == "_extend":    # extend_exact's worker, run under ComfyUI's venv
        _extend_impl(sys.argv[2], sys.argv[3], float(sys.argv[4]))
        return
    if len(sys.argv) == 4 and sys.argv[1] == "_chroma":    # tune_kept's worker, run under ComfyUI's venv
        _chroma_impl(sys.argv[2], sys.argv[3])
        return
    if len(sys.argv) == 4 and sys.argv[1] == "_harmony":   # harmony_held's worker, run under ComfyUI's venv
        _harmony_impl(sys.argv[2], sys.argv[3])
        return
    if len(sys.argv) == 3 and sys.argv[1] == "_develop":   # develop's worker, run under ComfyUI's venv
        _develop_impl(sys.argv[2])
        return
    ap = argparse.ArgumentParser(description="cast a film's score by ear")
    ap.add_argument("stage", choices=["new", "round", "vary", "pick", "final", "develop", "cast", "status", "sheet"])
    ap.add_argument("--plan", help="develop: the arrangements and the sections (see cmd_develop)")
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--film", required=True)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--secs", type=float, default=None)
    ap.add_argument("--label", default=None, help="final: what this version is for, e.g. 'the 3:04 cut'")
    ap.add_argument("--step", type=float, default=0.08, help="vary: the tempo nudge (0.08 = 8%%; smaller later)")
    ap.add_argument("--brief", default="")
    ap.add_argument("--note", default="", help="round: what this round changed, shown at the top of its sheet")
    ap.add_argument("--video", default=None)
    ap.add_argument("--sfx", default=None)
    ap.add_argument("--recipes")
    ap.add_argument("--from", dest="frm")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--out")
    ap.add_argument("--keep", nargs="*")
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--fresh", action="store_true",
                    help="final: render the recipe anew at the length (new music) instead of extending the take")
    ap.add_argument("--to")
    ap.add_argument("--round", type=int)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    a.secs_given = a.secs is not None
    if a.secs is None:
        a.secs = 30.0
    if a.stage == "new":
        cmd_new(a)
    elif a.stage == "round":
        cmd_round(a)
    elif a.stage == "vary":
        cmd_vary(a)
    elif a.stage == "pick":
        cmd_pick(a)
    elif a.stage == "final":
        cmd_final(a)
    elif a.stage == "develop":
        if not (a.ids and a.plan):
            sys.exit("develop <finalist id> --plan plan.json")
        cmd_develop(a)
    elif a.stage == "cast":
        if not (a.ids and a.to):
            sys.exit("cast <finalist id> --to <path>")
        a.id = a.ids[0]
        cmd_cast(a)
    elif a.stage == "sheet":
        c = load(a.film, a.scene)
        print(sheet(c, "finals" if a.round is None and c["finals"] else (a.round or len(c["rounds"]))))
    else:
        cmd_status(a)


if __name__ == "__main__":
    main()
