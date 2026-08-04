#!/usr/bin/env python3
"""cast_voice.py - GIVE A CHARACTER A VOICE, AND MEASURE THE ONE YOU GAVE HER.

    ~/ComfyUI/venv/bin/python3 studio/_tools/cast_voice.py audition
    ~/ComfyUI/venv/bin/python3 studio/_tools/cast_voice.py emotion
    ~/ComfyUI/venv/bin/python3 studio/_tools/cast_voice.py lines
    ~/ComfyUI/venv/bin/python3 studio/_tools/cast_voice.py measure
    ~/ComfyUI/venv/bin/python3 studio/_tools/cast_voice.py asr
    ~/ComfyUI/venv/bin/python3 studio/_tools/cast_voice.py sheet
    ~/ComfyUI/venv/bin/python3 studio/_tools/cast_voice.py all

Run under the ComfyUI venv - librosa, numpy and matplotlib all live there and system
python3 on this box has none of them.

WHY THIS TOOL EXISTS

Every cast member in this project got a voice by somebody picking a wav off a list. NIKA
is `female_03_alice`, VIRO is `vex`, BRACK is `male_02`, and not one card says why, what
else was tried, or what the render actually sounded like. The image half of a character is
measured to death - sheets, turnarounds, LoRA strength sweeps, style verdicts - and the
audio half is a filename.

So this does for the voice what turnaround.py and cast_proof.py do for the face:

  ONE LINE, EVERY CANDIDATE, ONE SEED, ONE ENGINE. The line is the character's own, so
  the audition tests the voice against the part rather than against a neutral sentence.
  Held seed and held engine mean any difference between two files is the reference voice
  and nothing else - the same discipline as a matched-seed LoRA check.

  THEN LOOK AT THE RENDER. The project rule is that a render is judged by looking at it,
  not by trusting the parameters. Audio has no equivalent of opening the jpg from an
  agent's seat, so this gets as close as the box allows: duration, peak, clipping, the
  silence map, median pitch and range, spectral centroid, onset rate - and an ASR pass
  that reads the words back off the audio. ASR is the honest part. It cannot tell you a
  read is beautiful, but it can tell you the engine dropped half the sentence, and a
  dropped sentence is the failure that actually happens.

  ALL OF IT IS WRITTEN DOWN. measurements.json next to the audio, so the next character
  is cast against numbers instead of against a hunch.

WHAT IT CANNOT DO, STATED SO NOBODY READS MORE INTO THE OUTPUT THAN IS THERE: nothing in
here is a pair of ears. It cannot hear warmth, sincerity, an accent that is wrong for the
part, or a read that is technically clean and emotionally dead. It rejects the broken and
ranks the plausible. A human still has to play the four files at the end.
"""
import argparse, glob, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "studio"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, COMFY, HOST   # noqa: E402

CHAR = "TERRA"
OUT = os.path.join(ROOT, "studio", "samples", "cast", "terra_voice")
GEN = "claude-generated/terra_voice"
SEED = 7411

# ── the audition line ───────────────────────────────────────────────────────────
# Terra's own words, not a neutral sentence. Her card says "the one who does not know
# what she is ... moves like she is waiting to be told she is allowed", so the line is
# built to make a voice show whether it can be uncertain: a flat statement, a shorter
# clause that gives away, and a sentence that trails into a reason nobody asked for.
# Roughly nine seconds, which is long enough that pitch range and pause structure mean
# something and short enough to render every candidate cheaply.
LINE = ("I don't know what I am. Nobody will say it out loud. "
        "And I stopped asking, because asking makes them look away.")

# ── the candidates ──────────────────────────────────────────────────────────────
# EVERY castable voice in the library that could plausibly read a young woman, plus two
# deliberate controls at the edges. Blocked packs are excluded by construction, not by
# filtering: the four real-person clones are not in this list and this tool has no code
# path that can reach them. The three `unsupported` packs are excluded too - the
# UnifiedTTSTextNode dropdown does not accept their paths, so picking one fails mid-run.
CANDIDATES = [
    ("female_03_alice", "voices_examples/female/female_03_alice.wav",
     "young conversational, hedged. ALREADY CAST AS NIKA."),
    ("female_04_maya",  "voices_examples/female/female_04_maya.wav",
     "warm technical narrator, the strongest cloning reference in the library at 27.2s"),
    ("female_01",       "voices_examples/female/female_01.wav",
     "level audiobook narrator, flattest female delivery here"),
    ("female_02",       "voices_examples/female/female_02.wav",
     "brisk formal, reads a finding aloud"),
    ("en_woman",        "voices_examples/higgs_audio/en_woman.wav",
     "neutral instructional, second-shortest reference at 6.4s"),
    ("mabel",           "voices_examples/higgs_audio/mabel.wav",
     "bright teasing, the brightest voice in the library"),
    ("vex",             "voices_examples/higgs_audio/vex.wav",
     "CONTROL, high end. High youthful drawl, ALREADY CAST AS VIRO"),
    ("belinda",         "voices_examples/higgs_audio/belinda.wav",
     "CONTROL, low end. Excited child - included to prove the audition can tell a "
     "young woman from a girl rather than just picking whatever is highest"),
]

# ── the dossier line set ────────────────────────────────────────────────────────
# Four registers, because a character in a film is not one delivery. Each is written the
# way the TEXT would have to carry it on an engine with no emotion control, which is the
# case worth measuring: this is what a director actually has to hand.
#
# THE VECTORS BELOW ARE THE SECOND SET. The first set - Angry 0.9 on the shout, Afraid
# 0.7 + Angry 0.35 on the strain - was rendered before the sweep existed, and the sweep
# then showed it was miles past the break: both came back at 408 Hz median off a 182 Hz
# voice, which is not a directed performance, it is a stranger. That first pass is kept
# at samples/cast/terra_voice/lines_indextts2_unbounded/ as the evidence for why these
# numbers are what they are, exactly as the LoRA sweeps keep their 0.85 column.
LINES = [
    ("dialogue", "You keep saying I am half of something. "
                 "Nobody will tell me which half.",
     {}),
    ("whisper",  "Don't wake them. I only want to look at it once, "
                 "and then I will put it back. I promise.",
     {"Afraid": 0.4}),
    ("shout",    "Stop! Get away from her! I said get away from her, now!",
     {"Angry": 0.4}),
    ("strain",   "I can hold it. I can hold it, I just -- I need you to go. Go, now, "
                 "please, I have it!",
     {"Afraid": 0.8}),
]

# ── the missing mapping, drafted ────────────────────────────────────────────────
# UNRENDERED AND UNVERIFIED. This is a proposal, not a measurement, and it is written
# down here rather than onto the 27 emotion cards because those cards are not this task's
# to edit and because a number nobody has listened to should not arrive looking official.
#
# The problem it solves: every emotion card carries a voice_style ADJECTIVE - hollow,
# wistful, guarded, clipped, flustered, roaring - and IndexTTS-2 takes eight NAMED FLOATS.
# There is no automatic path between the two. This is the same wall the image half of the
# project keeps hitting: the model renders nouns, not adjectives. A hand-written table is
# the only bridge, exactly as the styles library needed one.
#
# EVERY VALUE HERE RESPECTS THE MEASURED CEILINGS in emotion_sweep: Angry never above
# 0.4, Afraid never above 0.8. The six other dimensions are UNSWEPT, so their values are
# guesses held deliberately low - whoever renders this should sweep Sad and Surprised
# first, since the probe showed Sad 1.0 producing a 26.7-semitone range and 42% silence,
# which is either a beautiful broken delivery or a malfunction, and only listening will
# say which.
#
# voice_rate is NOT mapped, because IndexTTSEngineNode exposes no rate or duration input.
# Twenty-seven cards carry a rate from 0.75 to 1.35 and there is nothing on this box to
# send it to.
EMOTION_MAP = {
    "angry":       {"Angry": 0.40},
    "awe":         {"Surprised": 0.35, "Calm": 0.30},
    "cold":        {"Calm": 0.45},
    "contempt":    {"Disgusted": 0.35, "Angry": 0.15},
    "defiance":    {"Angry": 0.35},
    "despair":     {"Sad": 0.55, "Melancholic": 0.35},
    "determined":  {"Angry": 0.15, "Calm": 0.30},
    "doubt":       {"Afraid": 0.30},
    "embarrassed": {"Afraid": 0.35, "Surprised": 0.20},
    "exhausted":   {"Melancholic": 0.40, "Calm": 0.25},
    "fear":        {"Afraid": 0.70},
    "focus":       {"Calm": 0.40},
    "grief":       {"Sad": 0.60, "Melancholic": 0.30},
    "joy":         {"Happy": 0.55},
    "longing":     {"Melancholic": 0.50},
    "neutral":     {},
    "panic":       {"Afraid": 0.80, "Surprised": 0.30},
    "pride":       {"Happy": 0.35, "Calm": 0.25},
    "rage":        {"Angry": 0.40},          # capped: 0.4 is the break point, not a choice
    "relief":      {"Calm": 0.45, "Happy": 0.20},
    "resignation": {"Melancholic": 0.40, "Sad": 0.25},
    "resolve":     {"Calm": 0.35, "Angry": 0.15},
    "shame":       {"Sad": 0.40, "Afraid": 0.25},
    "shock":       {"Surprised": 0.60},
    "smug":        {"Happy": 0.30, "Disgusted": 0.15},
    "suspicion":   {"Disgusted": 0.20, "Afraid": 0.20},
    "tender":      {"Calm": 0.40, "Happy": 0.20},
}
# NOTE ON rage AND angry LANDING ON THE SAME VECTOR. That is not laziness, it is the
# measurement: the ceiling that keeps a voice recognisable is 0.4 on Angry, so rage
# cannot be louder than angry through this dimension. If a character needs to be angrier
# than 0.4 allows, that is a second reference wav, not a bigger number.

# ── the emotion-vector probe ────────────────────────────────────────────────────
# The 27 emotion cards each carry `voice_style` and `voice_rate` and compile.py warns
# that neither is routed to TTS. That warning describes the STUDIO, not the ENGINE, and
# the two are different claims. This probe settles the engine half: same voice, same
# text, same seed, only the IndexTTS-2 emotion vector moves. If the bytes come back
# identical the vector is dead and the warning is the whole story. If they move, the
# capability exists and the missing piece is a mapping nobody has written.
PROBE_LINE = "You keep saying I am half of something. Nobody will tell me which half."
PROBE = [
    ("v_zero",   {}),
    ("v_afraid", {"Afraid": 1.0}),
    ("v_angry",  {"Angry": 1.0}),
    ("v_sad",    {"Sad": 1.0}),
    ("v_calm",   {"Calm": 1.0}),
]


def _dir(*p):
    d = os.path.join(OUT, *p)
    os.makedirs(d, exist_ok=True)
    return d


def _higgs(text, voice, prefix, seed):
    wf = load_wf("17_higgs_v3_voice.json")
    set_path(wf, "30.inputs.text", text)
    set_path(wf, "30.inputs.narrator_voice", voice)
    set_path(wf, "30.inputs.seed", seed)
    set_path(wf, "40.inputs.filename_prefix", prefix)
    return wf


def _index(text, voice, prefix, seed, emo):
    wf = load_wf("16_indextts2_voice.json")
    for k in ("Happy", "Angry", "Sad", "Surprised", "Afraid", "Disgusted",
              "Calm", "Melancholic"):
        set_path(wf, f"20.inputs.{k}", float(emo.get(k, 0.0)))
    set_path(wf, "30.inputs.text", text)
    set_path(wf, "30.inputs.narrator_voice", voice)
    set_path(wf, "30.inputs.seed", seed)
    set_path(wf, "40.inputs.filename_prefix", prefix)
    return wf


def _render(wf, dest, label):
    """Render one line and land it locally. RAW - deliberately not loudness-normalised.

    short.py normalises every film line to -18 LUFS with a compressor in front, which is
    correct for a mix and wrong for an audition: it would erase exactly the level and
    peak defects this tool exists to catch, and flatten the loudness difference between
    a whisper and a shout into nothing.
    """
    if os.path.exists(dest):
        print(f"  = {label} (have it)", flush=True)
        return dest
    print(f"  > {label}", flush=True)
    try:
        _, outs = run(HOST, wf, quiet=True)
    except SystemExit:
        print(f"    !! FAILED {label}", flush=True)
        return None
    if not outs:
        print(f"    !! NO OUTPUT {label}", flush=True)
        return None
    return ensure_local(outs[0], dest, required=True)


# ────────────────────────────────────────────────────────────────────── stages
def audition():
    print("\n=== AUDITION: one line, %d voices, higgs_v3, seed %d ===" %
          (len(CANDIDATES), SEED))
    print(f'    "{LINE}"')
    d = _dir("audition")
    for vid, wav, _why in CANDIDATES:
        _render(_higgs(LINE, wav, f"{GEN}/aud_{vid}", SEED),
                f"{d}/{vid}.mp3", vid)


def emotion():
    """Is the IndexTTS-2 emotion vector alive on this box, or a slider wired to nothing?"""
    print("\n=== EMOTION PROBE: one voice, one line, one seed, vector varies ===")
    d = _dir("emotion_probe")
    voice = _cast_wav()
    for name, emo in PROBE:
        _render(_index(PROBE_LINE, voice, f"{GEN}/{name}", SEED, emo),
                f"{d}/{name}.mp3", f"{name}  {emo or 'all zero'}")


def sweep():
    """HOW HARD CAN YOU PUSH THE EMOTION VECTOR BEFORE IT STOPS BEING HER?

    Written after the probe came back: at Angry 1.0 the median pitch of a 182 Hz voice
    went to 494 Hz. That is not a directed performance, it is a different person, and it
    is the same shape as the finding that governs the image half of this project - a
    strength knob at its maximum destroys the thing it is modulating. 0.85 collapsed
    NIKA's field to a grey void and TERRA's snow forest to flat beige; 1.0 on an emotion
    vector collapses a voice to a shriek.

    So this is the LoRA strength sweep, for audio. One voice, one line, one seed, one
    dimension, five values. The number it produces is written on the card the same way
    lora_strength_measured is, and for the same reason: it is a property of the engine
    and the reference, not of any one film.
    """
    print("\n=== EMOTION STRENGTH SWEEP: Angry 0.2 -> 1.0, everything else held ===")
    d = _dir("emotion_sweep")
    voice = _cast_wav()
    for v in (0.2, 0.4, 0.6, 0.8, 1.0):
        tag = f"angry_{int(v * 100):03d}"
        _render(_index(PROBE_LINE, voice, f"{GEN}/{tag}", SEED, {"Angry": v}),
                f"{d}/{tag}.mp3", tag)
    for v in (0.2, 0.4, 0.6, 0.8, 1.0):
        tag = f"afraid_{int(v * 100):03d}"
        _render(_index(PROBE_LINE, voice, f"{GEN}/{tag}", SEED, {"Afraid": v}),
                f"{d}/{tag}.mp3", tag)


def lines():
    """The dossier set, rendered TWICE - once per engine - because the interesting
    question is not what a shout sounds like but which layer produces one."""
    print("\n=== DOSSIER LINES: 4 registers x 2 engines ===")
    voice = _cast_wav()
    dh, di = _dir("lines_higgs"), _dir("lines_indextts2")
    for i, (name, text, emo) in enumerate(LINES):
        _render(_higgs(text, voice, f"{GEN}/h_{name}", SEED + i * 17),
                f"{dh}/{name}.mp3", f"higgs      {name}")
    for i, (name, text, emo) in enumerate(LINES):
        _render(_index(text, voice, f"{GEN}/i_{name}", SEED + i * 17, emo),
                f"{di}/{name}.mp3", f"indextts2  {name}  {emo}")


def _cast_wav():
    """The reference wav for whoever is cast. Read off the card so this tool cannot
    disagree with the card, and hard-fail rather than guess if the card says nothing."""
    p = os.path.join(ROOT, "studio", "characters", f"{CHAR}.json")
    c = json.load(open(p, encoding="utf-8"))
    raw = c.get("voice")
    if not raw:
        raise SystemExit(
            f"{CHAR}.json has no voice yet - run `audition`, then `measure`, look at the "
            f"numbers and the sheet, cast one with `cast <voice_id>`, then come back.")
    return str(raw).split()[-1]


# ──────────────────────────────────────────────────────────────────── measuring
def _measure_one(path):
    import numpy as np, librosa
    y, sr = librosa.load(path, sr=None, mono=True)
    if y.size == 0:
        return {"error": "empty file"}
    dur = len(y) / sr
    peak = float(np.max(np.abs(y)))
    rms_all = float(np.sqrt(np.mean(y ** 2)))
    db = lambda v: (20 * np.log10(v)) if v > 1e-9 else -120.0

    # frame energy, and a silence map relative to this file's own peak
    hop = 512
    fr = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
    fdb = 20 * np.log10(np.maximum(fr, 1e-9))
    thresh = db(peak) - 35.0
    quiet = fdb < thresh
    sil_frac = float(quiet.mean())
    # longest run of quiet frames, in seconds
    longest, cur = 0, 0
    for q in quiet:
        cur = cur + 1 if q else 0
        longest = max(longest, cur)
    longest_pause = longest * hop / sr
    lead = 0
    for q in quiet:
        if not q:
            break
        lead += 1
    tail = 0
    for q in quiet[::-1]:
        if not q:
            break
        tail += 1

    # pitch. pyin is slow but these files are seconds long.
    f0, voiced, _ = librosa.pyin(y, sr=sr, fmin=60.0, fmax=1000.0,
                                 frame_length=2048)
    f0v = f0[~np.isnan(f0)] if f0 is not None else np.array([])
    if f0v.size > 8:
        p10, p50, p90 = [float(np.percentile(f0v, q)) for q in (10, 50, 90)]
        semis = float(12 * np.log2(p90 / p10)) if p10 > 0 else 0.0
        voiced_frac = float(np.mean(~np.isnan(f0)))
    else:
        p10 = p50 = p90 = semis = voiced_frac = 0.0

    cen = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    roll = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)))
    flat = float(np.mean(librosa.feature.spectral_flatness(y=y)))
    onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time")
    speech = max(dur * (1 - sil_frac), 1e-6)

    return {
        "seconds": round(dur, 2),
        "sample_rate": int(sr),
        "peak_dbfs": round(db(peak), 2),
        "rms_dbfs": round(db(rms_all), 2),
        "crest_db": round(db(peak) - db(rms_all), 2),
        "clipped_samples": int(np.sum(np.abs(y) >= 0.999)),
        "silence_frac": round(sil_frac, 3),
        "longest_pause_s": round(longest_pause, 2),
        "lead_silence_s": round(lead * hop / sr, 2),
        "tail_silence_s": round(tail * hop / sr, 2),
        "pitch_median_hz": round(p50, 1),
        "pitch_p10_hz": round(p10, 1),
        "pitch_p90_hz": round(p90, 1),
        "pitch_range_semitones": round(semis, 1),
        "voiced_frac": round(voiced_frac, 3),
        "centroid_hz": round(cen, 0),
        "rolloff85_hz": round(roll, 0),
        "flatness": round(flat, 4),
        "onsets_per_sec_speech": round(len(onsets) / speech, 2),
    }


def _defects(m, expect_words):
    """Anything a pair of ears would catch instantly and a filename never will."""
    bad = []
    if m.get("error"):
        return [m["error"]]
    if m["seconds"] < 0.4:
        bad.append("SILENT/STUB - under 0.4s")
    if m["clipped_samples"] > 0:
        bad.append(f"CLIPPED - {m['clipped_samples']} samples at full scale")
    if m["peak_dbfs"] > -0.2:
        bad.append(f"AT CEILING - peak {m['peak_dbfs']} dBFS")
    if m["rms_dbfs"] < -45:
        bad.append(f"NEAR-SILENT - rms {m['rms_dbfs']} dBFS")
    if m["silence_frac"] > 0.55:
        bad.append(f"MOSTLY SILENCE - {m['silence_frac']:.0%}")
    if m["longest_pause_s"] > 2.0:
        bad.append(f"DEAD AIR - {m['longest_pause_s']}s gap")
    if m["tail_silence_s"] > 1.5:
        bad.append(f"LONG TAIL - {m['tail_silence_s']}s of nothing at the end")
    # a rough words-per-second sanity check catches truncation the ASR pass confirms
    wps = expect_words / max(m["seconds"] * (1 - m["silence_frac"]), 1e-6)
    if wps > 6.5:
        bad.append(f"TRUNCATED? {wps:.1f} words/sec of speech is too fast to be real")
    return bad


def measure():
    print("\n=== MEASURE ===")
    out = {}
    for sub, text in (("audition", LINE),
                      ("emotion_probe", PROBE_LINE),
                      ("emotion_sweep", PROBE_LINE),
                      ("lines_higgs", None),
                      ("lines_indextts2", None),
                      # the over-driven first pass, kept and measured so the numbers the
                      # card cites for it are on disk rather than only in prose
                      ("lines_indextts2_unbounded", None)):
        d = os.path.join(OUT, sub)
        if not os.path.isdir(d):
            continue
        print(f"\n-- {sub}")
        for p in sorted(glob.glob(f"{d}/*.mp3")):
            name = os.path.basename(p)[:-4]
            src = text
            if src is None:
                src = dict((n, t) for n, t, _ in LINES).get(name, "")
            m = _measure_one(p)
            m["md5"] = subprocess.run(["md5sum", p], capture_output=True,
                                      text=True).stdout.split()[0]
            m["defects"] = _defects(m, len(src.split()))
            m["expected_text"] = src
            out.setdefault(sub, {})[name] = m
            print(f"  {name:16} {m['seconds']:5.2f}s  "
                  f"pk {m['peak_dbfs']:6.1f}  rms {m['rms_dbfs']:6.1f}  "
                  f"f0 {m['pitch_median_hz']:6.1f}Hz  rng {m['pitch_range_semitones']:4.1f}st  "
                  f"cen {m['centroid_hz']:6.0f}  sil {m['silence_frac']:.0%}  "
                  f"{'  '.join(m['defects']) or 'clean'}")
    _merge_json("measurements.json", out)


def _merge_json(fn, new):
    p = os.path.join(OUT, fn)
    old = {}
    if os.path.exists(p):
        try:
            old = json.load(open(p, encoding="utf-8"))
        except Exception:
            old = {}
    # Merge PER FILE, not per stage. A shallow old[stage].update(new[stage]) replaces each
    # file's whole record, which silently threw away the asr_text and wer fields every
    # time `measure` ran after `asr` - the transcripts survived on disk in asr/*.txt so
    # nothing was lost, but measurements.json quietly lost the only column that says the
    # words are actually there. Caught by counting wer==0 entries and getting zero.
    for stage, files in new.items():
        if isinstance(files, dict) and isinstance(old.get(stage), dict):
            for name, rec in files.items():
                if isinstance(rec, dict) and isinstance(old[stage].get(name), dict):
                    old[stage][name].update(rec)
                else:
                    old[stage][name] = rec
        else:
            old[stage] = files
    json.dump(old, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\n  wrote {p}")


# ─────────────────────────────────────────────────────────────────────────── asr
def asr():
    """Read the words back off the audio with the Granite ASR already on this box.

    This is the nearest thing to listening that an agent has. It does not judge a
    performance. It judges whether the performance contains the sentence, which is the
    failure mode that actually turns up: a TTS engine that drops a clause, repeats a
    word, or stops early sounds fine in isolation and destroys a scene.
    """
    inp = os.path.join(COMFY, "input", "terra_voice_asr")
    os.makedirs(inp, exist_ok=True)
    jobs = []
    for sub in ("audition", "emotion_probe", "emotion_sweep",
                "lines_higgs", "lines_indextts2"):
        for p in sorted(glob.glob(os.path.join(OUT, sub, "*.mp3"))):
            name = f"{sub}__{os.path.basename(p)[:-4]}"
            shutil.copyfile(p, os.path.join(inp, name + ".mp3"))
            jobs.append(name)
    print(f"\n=== ASR: {len(jobs)} files through GraniteASR ===")
    got = {}
    for name in jobs:
        # Re-scoring is free; re-transcribing is not. A transcript already on disk is
        # reused, so `asr` can be run again after `measure` to restore the wer column
        # without putting 31 more jobs through the engine.
        have = os.path.join(OUT, "asr", name + ".txt")
        if os.path.exists(have):
            got[name] = open(have, encoding="utf-8").read().strip()
            continue
        wf = {
            "5":  {"class_type": "LoadAudio",
                   "inputs": {"audio": f"terra_voice_asr/{name}.mp3"}},
            "10": {"class_type": "GraniteASREngineNode", "inputs": _defaults_for(
                       "GraniteASREngineNode")},
            "20": {"class_type": "UnifiedASRTranscribeNode",
                   "inputs": {"engine": ["10", 0], "audio": ["5", 0],
                              "language": "English", "task": "transcribe",
                              "timestamps": "none", "enable_asr_cache": False}},
            "30": {"class_type": "SaveText",
                   "inputs": {"text": ["20", 0],
                              "filename_prefix": f"{GEN}/asr/{name}",
                              "format": "txt"}},
        }
        print(f"  > {name}", flush=True)
        try:
            run(HOST, wf, quiet=True)
        except SystemExit:
            print(f"    !! ASR FAILED {name}")
            continue
        # comfy.run() only collects image/audio/video outputs, so the SaveText result is
        # picked up off disk instead. Safe here and only here: this tool runs ON the box,
        # so COMFY is a local path, not the SMB share that has been measured lagging.
        d = _dir("asr")
        hits = sorted(glob.glob(os.path.join(
            COMFY, "output", GEN, "asr", f"{name}_*.txt")))
        if not hits:
            print(f"    !! NO TRANSCRIPT {name}")
            continue
        shutil.copyfile(hits[-1], f"{d}/{name}.txt")
        got[name] = open(hits[-1], encoding="utf-8").read().strip()
    _score_asr(got)


_INFO = {}


def _defaults_for(node):
    import urllib.request
    if not _INFO:
        _INFO.update(json.load(urllib.request.urlopen(
            f"http://{HOST}/object_info", timeout=180)))
    out = {}
    for k, v in (_INFO[node]["input"].get("required") or {}).items():
        if isinstance(v, list) and len(v) > 1 and isinstance(v[1], dict) and "default" in v[1]:
            out[k] = v[1]["default"]
        elif isinstance(v, list) and isinstance(v[0], list) and v[0]:
            out[k] = v[0][0]
    return out


def _norm(s):
    return [w for w in "".join(c.lower() if (c.isalnum() or c == " ") else " "
                              for c in s).split() if w]


def _wer(ref, hyp):
    r, h = _norm(ref), _norm(hyp)
    if not r:
        return None
    d = [[0] * (len(h) + 1) for _ in range(len(r) + 1)]
    for i in range(len(r) + 1):
        d[i][0] = i
    for j in range(len(h) + 1):
        d[0][j] = j
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1,
                          d[i - 1][j - 1] + (r[i - 1] != h[j - 1]))
    return d[len(r)][len(h)] / len(r)


def _score_asr(got):
    print("\n-- word error rate against the line that was asked for")
    out = {}
    for name, hyp in sorted(got.items()):
        sub, _, base = name.partition("__")
        ref = LINE if sub == "audition" else (
            PROBE_LINE if sub in ("emotion_probe", "emotion_sweep") else
            dict((n, t) for n, t, _ in LINES).get(base, ""))
        w = _wer(ref, hyp)
        out.setdefault(sub, {})[base] = {"asr_text": hyp,
                                         "wer": None if w is None else round(w, 3)}
        flag = "" if (w is not None and w <= 0.15) else "  <-- LOOK AT THIS"
        print(f"  {sub:16} {base:16} wer {w if w is None else round(w,3)}{flag}")
        print(f"      {hyp}")
    p = os.path.join(OUT, "measurements.json")
    cur = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    for sub, rows in out.items():
        for base, v in rows.items():
            cur.setdefault(sub, {}).setdefault(base, {}).update(v)
    json.dump(cur, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"  merged ASR into {p}")


# ───────────────────────────────────────────────────────────────────────── sheet
def sheet():
    """One PNG per stage: waveform over mel spectrogram, same axes for every row.

    The point is that a human can open this and SEE what the numbers claim - a truncated
    line, a clipped peak, a whisper that is actually just quiet, a shout that is actually
    just clipped. Held axes are the whole trick; unheld ones make every row look the same.
    """
    import numpy as np, librosa, librosa.display
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    for sub, title in (("audition", f"{CHAR} VOICE AUDITION - one line, one seed, "
                                    "higgs_v3, RAW (not normalised)"),
                       ("emotion_probe", f"{CHAR} - IndexTTS-2 emotion vector probe, "
                                         "one voice / one line / one seed"),
                       ("emotion_sweep", f"{CHAR} - HOW HARD CAN THE VECTOR BE PUSHED? "
                                         "Angry then Afraid, 0.2 to 1.0"),
                       ("lines_higgs", f"{CHAR} dossier lines - higgs_v3 "
                                       "(text is the only direction available)"),
                       ("lines_indextts2", f"{CHAR} dossier lines - IndexTTS-2 "
                                           "(text plus emotion vector)")):
        files = sorted(glob.glob(os.path.join(OUT, sub, "*.mp3")))
        if not files:
            continue
        order = [v for v, _, _ in CANDIDATES] if sub == "audition" else \
                ([n for n, _ in PROBE] if sub == "emotion_probe" else
                 ([f"{e}_{v:03d}" for e in ("angry", "afraid")
                   for v in (20, 40, 60, 80, 100)] if sub == "emotion_sweep" else
                  [n for n, _, _ in LINES]))
        idx = {n: i for i, n in enumerate(order)}
        files.sort(key=lambda p: idx.get(os.path.basename(p)[:-4], 99))
        n = len(files)
        maxdur = max(librosa.get_duration(path=p) for p in files)
        fig, ax = plt.subplots(n, 2, figsize=(15, 1.7 * n), squeeze=False)
        for i, p in enumerate(files):
            name = os.path.basename(p)[:-4]
            y, sr = librosa.load(p, sr=22050, mono=True)
            t = np.arange(len(y)) / sr
            a = ax[i][0]
            a.plot(t, y, lw=0.4, color="#1a3d6d")
            a.axhline(1.0, color="#c0392b", lw=0.5)
            a.axhline(-1.0, color="#c0392b", lw=0.5)
            a.set_xlim(0, maxdur)
            a.set_ylim(-1.05, 1.05)
            a.set_ylabel(name, fontsize=8, rotation=0, ha="right", va="center")
            a.set_yticks([])
            if i < n - 1:
                a.set_xticks([])
            S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=96, fmax=8000)
            b = ax[i][1]
            librosa.display.specshow(librosa.power_to_db(S, ref=np.max), sr=sr,
                                     x_axis="time", y_axis="mel", fmax=8000,
                                     ax=b, cmap="magma", vmin=-70, vmax=0)
            b.set_xlim(0, maxdur)
            b.set_ylabel("")
            if i < n - 1:
                b.set_xlabel("")
                b.set_xticks([])
        fig.suptitle(title, fontsize=11)
        fig.tight_layout(rect=[0, 0, 1, 0.97])
        dst = os.path.join(OUT, f"{sub}_sheet.png")
        fig.savefig(dst, dpi=110)
        plt.close(fig)
        print(f"  wrote {dst}")


# ──────────────────────────────────────────────────────────────────── the card
def cast(voice_id=None, engine="higgs_v3"):
    """Write the casting onto the character card, and ONLY the voice fields.

    Read-modify-write against the file as it is on disk right now, touching the `voice`
    key and keys prefixed `voice_`. Everything else on the card - tags, costumes, lora,
    every verdict - is carried through untouched, because other work is happening on this
    same card at the same time and a whole-file rewrite would silently revert it.
    """
    if not voice_id:
        raise SystemExit("cast needs a voice id, e.g. `cast female_04_maya`")
    lib = os.path.join(ROOT, "studio", "voices", f"{voice_id}.json")
    if not os.path.exists(lib):
        raise SystemExit(f"no such voice card: {lib}")
    v = json.load(open(lib, encoding="utf-8"))
    # The one hard rule in this project. Enforced in code, not in a comment, because a
    # comment does not stop the next tool.
    if v.get("status") != "ready":
        raise SystemExit(
            f"REFUSING to cast {voice_id}: status is {v.get('status')!r}, not 'ready'. "
            f"The four real-person clones are status 'blocked' and must never be cast; "
            f"three more are 'unsupported' and fail mid-render.")
    p = os.path.join(ROOT, "studio", "characters", f"{CHAR}.json")
    c = json.load(open(p, encoding="utf-8"))
    c["voice"] = f"{engine} {v['file']}"
    json.dump(c, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"  {CHAR}.voice = {c['voice']}")


STAGES = {"audition": audition, "emotion": emotion, "sweep": sweep, "lines": lines,
          "measure": measure, "asr": asr, "sheet": sheet, "cast": cast}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", nargs="*", default=["all"])
    a = ap.parse_args()
    if a.stage and a.stage[0] == "cast":
        cast(*a.stage[1:])
        raise SystemExit(0)
    want = a.stage
    if "all" in want:
        want = ["audition", "emotion", "sweep", "lines", "measure", "asr", "sheet"]
    for s in want:
        if s not in STAGES:
            raise SystemExit(f"unknown stage {s}; pick from {list(STAGES)} or all")
        STAGES[s]()
    print("\nevidence under", OUT)
