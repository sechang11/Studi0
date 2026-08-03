#!/usr/bin/env python3
"""Build the reference audio library under output/claude-generated/.

    python3 scripts/make_audio_library.py            # everything
    python3 scripts/make_audio_library.py sfx music  # just those sections

Replaces the samples generated before 2026-07-30, which were made with
**classifier-free guidance switched off** (`cfg 1.0`) at draft step counts - 8 steps for
SFX, 20 for music. At cfg 1.0 the text prompt barely steers the render and the negative
prompt does nothing at all, which is why those beds sounded like loosely-guided noise and
why "no music, no speech" never took effect.

What changed, and why:

  SFX   8 steps / cfg 1.0 / lcm      ->  100 steps / cfg 7 / dpmpp_3m_sde
        Plus ONE SOUND PER BED. The old prompts asked for five things at once
        ("eruption, earth tearing, shockwave, buildings collapsing, roaring fire") in a
        six-second clip, so they arrived as mush. Short, concrete, single-source.
        Output is loudness-normalised because cfg 7 clips otherwise (measured).

  MUSIC v1.5 turbo, 20 steps, cfg 1.0 ->  v1 3.5B full model, 60 steps, cfg 5
        The turbo variant is built for speed at cfg 1.0; the full 7.7GB model was sitting
        unused in checkpoints/. Real guidance means the tags actually shape the cue.

  VOICE Chatterbox + rubberband      ->  TTS-Audio-Suite engines, one voice per character
        Pitch-shifting one voice pack by +/-30% wrecks formants. Now each character gets a
        genuinely different reference voice.

        The pack ships clones of real identifiable people (Clint Eastwood, David
        Attenborough, Morgan Freeman, Sophie Anderson). Those are deliberately NOT used
        here - impersonating real performers is not something to put in a film. Only the
        generic synthetic voices are cast.
"""
import json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("COMFY_ROOT", "Z:/ComfyUI")
# Default to the LOCAL ComfyUI. This used to hardcode 192.168.1.46, which broke
# when DHCP moved the box to .45, and which also sent every render request across
# a NIC measured dropping 10% of packets. Nothing here needs the network: these
# scripts run ON the box. Set COMFY_HOST to drive a remote instance.
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run, set_path                      # noqa: E402
from epic import norm_to, COMFY, HOST                # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = f"{COMFY}/output/claude-generated"
GEN = "claude-generated"


def wf_of(name):
    return {k: v for k, v in json.load(open(f"{ROOT}/workflows/{name}")).items()
            if not k.startswith("_")}


def clear(sub, why):
    """Remove superseded samples. Only ever touches the sample folders, never a film."""
    d = f"{OUT}/{sub}"
    if not os.path.isdir(d):
        return
    gone = 0
    for f in sorted(os.listdir(d)):
        p = f"{d}/{f}"
        if os.path.isfile(p):
            os.remove(p)
            gone += 1
    print(f"  cleared {gone} old file(s) from {sub}  ({why})")


# ───────────────────────────────────────────────────────────────── sound effects
# One sound per bed. Short and concrete beats long and atmospheric.
SFX = [
    ("bell_strike",    "A single huge bronze bell struck once, ringing out and decaying", 8),
    ("sword_clash",    "Two heavy steel blades striking each other once, hard", 5),
    ("sword_draw",     "A long steel sword drawn from a leather scabbard", 4),
    ("armour_footstep","Heavy armoured footsteps on wet stone", 6),
    ("rain_on_metal",  "Heavy rain falling on a metal roof", 10),
    ("fire_large",     "A large fire burning, close, crackling and roaring", 10),
    ("wind_desolate",  "Cold wind across an empty plain", 10),
    ("stone_crack",    "Stone cracking and splitting apart under pressure", 5),
    ("crowd_hubbub",   "A large crowd of people talking indistinctly in a stone hall", 10),
    ("horse_gallop",   "A single horse galloping past on packed earth", 6),
]
SFX_NEG = "music, melody, singing, speech, words, distortion, clipping"


def sfx():
    print("\n=== SOUND EFFECTS (100 steps, cfg 7, one sound per bed) ===")
    clear("09-sound-effects", "made at cfg 1.0 / 8 steps")
    base = wf_of("10_stableaudio_sfx.json")
    for i, (name, prompt, secs) in enumerate(SFX):
        wf = json.loads(json.dumps(base))
        set_path(wf, "3.inputs.text", prompt)
        set_path(wf, "4.inputs.text", SFX_NEG)
        set_path(wf, "5.inputs.seconds", float(secs))
        set_path(wf, "6.inputs.steps", 100)
        set_path(wf, "6.inputs.cfg", 7.0)
        set_path(wf, "6.inputs.sampler_name", "dpmpp_3m_sde")
        set_path(wf, "6.inputs.seed", 3300 + i * 17)
        set_path(wf, "8.inputs.filename_prefix", f"{GEN}/09-sound-effects/{name}")
        print(f"  > {name}", flush=True)
        run(HOST, wf, quiet=True)
    # cfg 7 pushes peaks over 0 dBFS (measured); give every sample headroom
    time.sleep(3)
    d = f"{OUT}/09-sound-effects"
    for f in sorted(os.listdir(d)):
        if f.endswith(".mp3") and not f.startswith("_"):
            p = f"{d}/{f}"
            norm_to(p, f"{d}/_n_{f}", -20.0, tp=-3.0)
            os.replace(f"{d}/_n_{f}", p)
    print("  normalised all beds to -20 LUFS / -3 dBTP")


# ─────────────────────────────────────────────────────────────────────── music
MUSIC = [
    ("epic_battle",   126, "C minor", "grand orchestral battle, hammered timpani, heroic brass over driving strings, wordless choir, enormous, instrumental"),
    ("grim_dread",     52, "D minor", "slow sacred dread, low sustained pipe organ, distant male choir on one held chord, tolling bell, cavernous, instrumental, no drums"),
    ("tender_piano",   58, "E minor", "tender melancholy, solo felt piano with warm sustained strings, distant music box, intimate, instrumental, no drums"),
    ("medieval_court", 88, "D minor", "medieval court dance, harpsichord ostinato, recorder and shawm, martial snare, modal, instrumental"),
    ("triumph_finale", 80, "C major", "triumphant bittersweet orchestral finale, soaring strings, glockenspiel, warm brass resolution, sweeping, instrumental"),
    ("primal_drums",  108, "E minor", "primal tribal percussion, huge log drums and taiko, bone flute, unison chanting, raw and driving, instrumental"),
]


def music():
    """ACE-Step 1.5 turbo, 20 steps, cfg 1.0 - chosen by listening test.

    This is the ORIGINAL setting, and it beat every "improvement" I tried: 60 steps,
    cfg 3-5, and the larger ACE-Step v1 3.5B model. It also beat Stable Audio 3.

    Two things I got wrong and had to walk back:

    * cfg 1.0 is NOT a bug here. ACE-Step 1.5 *turbo* is a DISTILLED model, exactly like
      the Lightning LoRA on the image side - distilled models are trained to run at cfg 1.0
      and raising CFG fights the distillation instead of adding guidance. The cfg-1.0 bug
      was real for Stable Audio SFX (not distilled); it was never a bug here.
    * v1 3.5B is not an upgrade over v1.5 turbo. v1 is the OLDER generation. 1.5 (Jan 2026)
      is the newer architecture and reportedly tops Suno v5 on SongEval. Bigger file,
      older model.

    The quality ceiling here is the prompt, not the sampler. Spend effort on naming
    instrumentation and register precisely; do not spend it on step counts.
    """
    print("\n=== MUSIC (ACE-Step 1.5 turbo, 20 steps, cfg 1.0 - chosen by ear) ===")
    clear("08-music", "regenerating at the setting that won the listening test")
    base = wf_of("06_acestep_music.json")
    for i, (name, bpm, key, tags) in enumerate(MUSIC):
        wf = json.loads(json.dumps(base))
        set_path(wf, "10.inputs.tags", tags)
        set_path(wf, "10.inputs.lyrics", "")
        set_path(wf, "10.inputs.bpm", bpm)
        set_path(wf, "10.inputs.keyscale", key)
        set_path(wf, "10.inputs.duration", 30.0)
        set_path(wf, "11.inputs.seconds", 30.0)
        set_path(wf, "10.inputs.seed", 5500 + i * 23)
        set_path(wf, "12.inputs.seed", 5500 + i * 23)
        set_path(wf, "12.inputs.steps", 20)
        set_path(wf, "12.inputs.cfg", 1.0)
        set_path(wf, "14.inputs.filename_prefix", f"{GEN}/08-music/{name}")
        print(f"  > {name}", flush=True)
        run(HOST, wf, quiet=True)


# ─────────────────────────────────────────────────────────────────────── voice
LINE = "Forty winters, and no dawn. I did not come up that road to be told what it costs."
# generic synthetic voices only - the celebrity clones that ship with the pack are excluded
CAST = [
    ("narrator_deep",  "voices_examples/higgs_audio/chadwick.wav"),
    ("hero_rough",     "voices_examples/male/male_01.wav"),
    ("calm_measured",  "voices_examples/male/male_02.wav"),
    ("woman_sharp",    "voices_examples/female/female_01.wav"),
    ("woman_warm",     "voices_examples/female/female_02.wav"),
    ("odd_character",  "voices_examples/higgs_audio/vex.wav"),
]
ENGINES = [
    ("vibevoice",  "VibeVoiceEngineNode"),
    ("higgs",      "HiggsAudioEngineNode"),
    ("f5",         "F5TTSEngineNode"),
    ("cosyvoice",  "CosyVoiceEngineNode"),
    ("moss",       "MossTTSEngineNode"),
    ("echo",       "EchoTTSEngineNode"),
]


def _defaults(node, info):
    out = {}
    for k, v in (info[node]["input"].get("required") or {}).items():
        if isinstance(v, list) and len(v) > 1 and isinstance(v[1], dict) and "default" in v[1]:
            out[k] = v[1]["default"]
        elif isinstance(v, list) and isinstance(v[0], list) and v[0]:
            out[k] = v[0][0]
    return out


def _speak(engine_node, info, voice, text, prefix, seed=11):
    return {
      "10": {"class_type": engine_node, "inputs": _defaults(engine_node, info)},
      "30": {"class_type": "UnifiedTTSTextNode", "inputs": {
              "TTS_engine": ["10", 0], "text": text, "narrator_voice": voice,
              "seed": seed, "enable_chunking": False, "max_chars_per_chunk": 400,
              "chunk_combination_method": "auto", "silence_between_chunks_ms": 100,
              "enable_audio_cache": False}},
      "40": {"class_type": "SaveAudioMP3", "inputs": {
              "audio": ["30", 0], "filename_prefix": prefix, "quality": "320k"}},
    }


def voice():
    print("\n=== VOICE (TTS-Audio-Suite) ===")
    clear("10-voice", "made with Chatterbox + rubberband pitch shifting")
    info = json.load(urllib.request.urlopen(f"http://{HOST}/object_info", timeout=180))
    print("  -- same line, same voice, one file per ENGINE (pick the engine) --")
    for tag, node in ENGINES:
        if node not in info:
            continue
        wf = _speak(node, info, "voices_examples/male/male_01.wav", LINE,
                    f"{GEN}/10-voice/engine_{tag}")
        print(f"  > engine_{tag}", flush=True)
        try:
            run(HOST, wf, quiet=True)
        except SystemExit:
            print(f"    (skipped {tag} - engine error)")
    print("  -- same line, one file per VOICE on VibeVoice (cast the characters) --")
    for tag, v in CAST:
        wf = _speak("VibeVoiceEngineNode", info, v, LINE, f"{GEN}/10-voice/cast_{tag}")
        print(f"  > cast_{tag}", flush=True)
        try:
            run(HOST, wf, quiet=True)
        except SystemExit:
            print(f"    (skipped {tag})")


def emotion():
    """IndexTTS-2 emotion control - the reason this engine is worth the dependency fight.

    Eight dimensions, 0.0-1.0 each, scaled by emotion_alpha. A character is DIRECTED rather
    than differentiated by timbre: same voice, same line, different performance. That is
    what the old pitch-shifting was a bad substitute for.

    Needs `pip install descript-audiotools` in the ComfyUI venv, and ComfyUI/temp/ to exist
    (the engine writes a scratch wav there and does not create the folder itself).
    """
    print("\n=== VOICE: IndexTTS-2 emotion direction ===")
    base = wf_of("16_indextts2_voice.json")

    DIRECTED = [
        ("emo_neutral",     {},                              "voices_examples/male/male_01.wav"),
        ("emo_angry",       {"Angry": 0.8},                  "voices_examples/male/male_01.wav"),
        ("emo_sad",         {"Sad": 0.8},                    "voices_examples/male/male_01.wav"),
        ("emo_afraid",      {"Afraid": 0.8},                 "voices_examples/male/male_01.wav"),
        ("emo_calm",        {"Calm": 0.8},                   "voices_examples/male/male_01.wav"),
        ("emo_melancholic", {"Melancholic": 0.8},            "voices_examples/male/male_01.wav"),
        # the same four characters as the films, cast by voice AND directed by emotion
        ("char_guts",       {"Angry": 0.5},                  "voices_examples/male/male_01.wav"),
        ("char_griffith",   {"Calm": 0.7},                   "voices_examples/male/male_02.wav"),
        ("char_casca",      {"Angry": 0.3, "Afraid": 0.2},   "voices_examples/female/female_01.wav"),
        ("char_narrator",   {"Calm": 0.3, "Melancholic": 0.2}, "voices_examples/higgs_audio/chadwick.wav"),
    ]
    for i, (name, emo, voice_ref) in enumerate(DIRECTED):
        wf = json.loads(json.dumps(base))
        for k in ("Happy", "Angry", "Sad", "Surprised", "Afraid", "Disgusted",
                  "Calm", "Melancholic"):
            set_path(wf, f"20.inputs.{k}", float(emo.get(k, 0.0)))
        set_path(wf, "30.inputs.text", LINE)
        set_path(wf, "30.inputs.narrator_voice", voice_ref)
        set_path(wf, "30.inputs.seed", 11 + i)
        set_path(wf, "40.inputs.filename_prefix", f"{GEN}/10-voice/{name}")
        tag = ", ".join(f"{k} {v}" for k, v in emo.items()) or "neutral"
        print(f"  > {name:16} ({tag})", flush=True)
        run(HOST, wf, quiet=True)


SECTIONS = {"sfx": sfx, "music": music, "voice": voice, "emotion": emotion}

if __name__ == "__main__":
    want = [a for a in sys.argv[1:] if a in SECTIONS] or list(SECTIONS)
    for s in want:
        SECTIONS[s]()
    print("\nlibrary built under", OUT)
