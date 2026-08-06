#!/usr/bin/env python3
"""film_audio.py - THE SOUND DEPARTMENT FOR ONE FILM: *THE COAT*.

    ~/ComfyUI/venv/bin/python3 studio/_tools/film_audio.py plan
    ~/ComfyUI/venv/bin/python3 studio/_tools/film_audio.py voice
    ~/ComfyUI/venv/bin/python3 studio/_tools/film_audio.py sweep
    ~/ComfyUI/venv/bin/python3 studio/_tools/film_audio.py score
    ~/ComfyUI/venv/bin/python3 studio/_tools/film_audio.py sfx
    ~/ComfyUI/venv/bin/python3 studio/_tools/film_audio.py ltx
    ~/ComfyUI/venv/bin/python3 studio/_tools/film_audio.py measure
    ~/ComfyUI/venv/bin/python3 studio/_tools/film_audio.py asr
    ~/ComfyUI/venv/bin/python3 studio/_tools/film_audio.py report

Run under the ComfyUI venv: librosa and numpy live there and system python3 has neither.

THIS TOOL HAS ARGPARSE AND A REQUIRED SUBCOMMAND, and it does nothing at import time.
Seventeen tools in this directory run their whole job on any argument including --help,
and ten of those write files at module level. That destroyed data once. `--help` here
prints help.

WHY IT EXISTS

studio/movies/terra_field_coat.movie is a 20-beat film with a fully measured picture
department and no sound at all. compile.py resolves a score off the real timeline, and
that score is seven cues pulled from five general-purpose library cards - it is a
placeholder, not a score. Nothing in the project has ever rendered a sound effect for a
named object in a named shot, and nobody has ever listened to the audio LTX emits for
free on every clip.

WHAT IS AND IS NOT VERIFIABLE FROM HERE, said once so nothing downstream reads more into
the output than is in it:

  I have no ears. Every claim this tool makes is a NUMBER off a waveform or a WORD off an
  ASR pass. It can prove a line contains its sentence, that a file is not silent, not
  clipped, not truncated, and that a bed is or is not tonal. It cannot tell you a cello
  entry is beautiful or that a read is emotionally dead. `measure` rejects the broken and
  ranks the plausible; a human still has to play the files.

  The ASR pass is the honest part and it is doing the work a pair of ears would do for
  the one failure that actually happens: a TTS engine dropping a clause. It runs on the
  Granite ASR weights already on this box - nothing is downloaded.

THE FOUR MOVEMENTS. The film's four chapters are its four costumes, and the score is
written as four movements plus a coda rather than as five unrelated library cues. One
lead instrument carries all of them (solo cello); the tonic is D throughout; the key
turns D minor -> D major at the coat, which is the same tonic finally in the major, and
is the only structural argument a text-to-music model can actually be asked to make.
ACE-Step cannot develop a motif and must not be asked to. It CAN hold an instrument, a
key and a tempo, so that is what the continuity is built out of.
"""
import argparse, glob, json, math, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "studio"))
sys.path.insert(0, HERE)
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run, set_path                                  # noqa: E402
from epic import (load_wf, ensure_local, measure as loudness,    # noqa: E402
                  norm_to, sh, COMFY, HOST)
from scene_templates import expand as expand_template            # noqa: E402

MOVIE = os.path.join(ROOT, "studio", "movies", "terra_field_coat.json")
OUT = os.path.join(ROOT, "studio", "samples", "the_film_audio")
GEN = "claude-generated/the_film_audio"
SEED = 4471

# ─────────────────────────────────────────────────────────── the two spoken lines
# Both are five words. She speaks twice in 66.7 seconds, which puts the speech duty
# cycle near 5% - the opposite end of the range from the narrated films craft/SOUND.md
# was written against (72%). Consequences for the mix are in `report`.
#
# The emotion vectors come from cast_voice.py's EMOTION_MAP, which is explicitly an
# UNRENDERED PROPOSAL. Two of its entries are used here and therefore stop being a
# proposal: `neutral` -> {} and `tender` -> Calm 0.40 + Happy 0.20. TERRA's card says
# the zero vector IS the direction for plain dialogue - "let the text do it" - so the
# court line is authored to that, not to a mood adjective.
#
# ALTERNATES EXIST SO THE CUT HAS A CHOICE. Three readings per line, two seeds each.
LINES = [
    dict(id="ii_decided_she_says_it_00", text="Nobody will say which half.",
         emotion="neutral", voice_style="calm", voice_rate=1.0,
         where="beat 8, the empty hall, medium close-up, hand to face",
         takes=[("asauthored", {}),
                ("hollow",     {"Melancholic": 0.40}),
                ("guarded",    {"Calm": 0.40, "Afraid": 0.15})]),
    dict(id="iv_chosen_she_asks_00", text="How much for the brown one.",
         emotion="tender", voice_style="gentle", voice_rate=0.85,
         where="beat 17, the market stall, medium close-up, hand reaching",
         takes=[("asauthored", {"Calm": 0.40, "Happy": 0.20}),
                ("tentative",  {"Calm": 0.35, "Afraid": 0.20}),
                ("plain",      {})]),
]
VOICE_SEEDS = [4471, 8812]

# ─────────────────────────────────────────── filling two unmeasured emotion dimensions
# TERRA's voice_direction records measured ceilings for Angry (0.4) and Afraid (0.8) and
# says in as many words that Happy, Sad, Surprised, Disgusted, Calm and Melancholic are
# UNMEASURED. This film's own dialogue depends on two of the six - Calm and Melancholic
# carry both readings above, and Happy carries the authored `tender` - so it is this
# film's business to measure them rather than inherit a guess. Same voice, same line,
# same seed; only the one dimension moves.
SWEEP_LINE = "How much for the brown one."
SWEEP = [("calm", "Calm"), ("happy", "Happy"), ("melancholic", "Melancholic")]
SWEEP_VALUES = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

# ───────────────────────────────────────────────────────────────────── the score
# Five cues: four movements and a coda. `chapter` is the chapter the cue belongs to and
# is what `plan` uses to measure its span off the compiled timeline - no hand-written
# offsets, same discipline as compile.py.
#
# EVERY CUE NAMES THE SAME LEAD INSTRUMENT. That is the whole continuity mechanism
# available: ACE-Step will not develop a theme, but it holds instrumentation, key and
# tempo, so the score's argument is carried by a solo cello that is present in all five
# and by a tonic that never moves off D except in the movement where she is furthest
# from herself.
#
# `no drums, no percussion` is in every tag string. The film has one percussive event in
# it (a gauntlet hitting snow) and it is a sound effect, not a downbeat.
CUES = [
    dict(id="coat_i_issued", chapter="i_issued", key="D minor", bpm=52, trim=0.0,
         desc="ISSUED. Armour, other people's hands. Cold, metallic, no melody yet.",
         tags="solo cello holding one low sustained note, cold sparse high strings, "
              "distant metallic taps like buckles and mail, airless, unresolved, "
              "film score, instrumental, no drums, no percussion"),
    dict(id="coat_ii_decided", chapter="ii_decided", key="D minor", bpm=60, trim=-1.0,
         desc="DECIDED. The same cello under a still string cluster. Formal, waiting.",
         tags="solo cello under a still high string cluster, single distant harpsichord "
              "notes, formal, airless, patient, waiting, tense, film score, "
              "instrumental, no drums, no percussion"),
    dict(id="coat_iii_road", chapter="iii_the_road", key="F minor", bpm=46, trim=0.0,
         desc="THE ROAD. The cello alone and off the tonic. Wide silences.",
         tags="solo cello completely alone, long silences between short phrases, "
              "low wind-like string drone far underneath, exhausted, desolate, very "
              "sparse, film score, instrumental, no drums, no percussion"),
    dict(id="coat_iv_market", chapter="iv_chosen", key="D major", bpm=60, trim=-1.0,
         desc="CHOSEN. Felt piano joins the cello. Tentative, first warmth in the film.",
         tags="soft felt piano and solo cello, tentative rising figure, warm string pad "
              "entering underneath, gentle, unhurried, hopeful but unsure, film score, "
              "instrumental, no drums, no percussion"),
    dict(id="coat_coda_moor", chapter="coda", key="D major", bpm=60, trim=0.0,
         desc="CODA. The moor again, in the coat. The only lift in the film.",
         tags="solo cello with full warm strings, slow theme resolving, soft swelling "
              "brass far behind, golden, open, unhurried, film score, instrumental, "
              "no drums, no percussion"),
]
CUE_SEEDS = [4471, 6203, 9137]
# The coda is not a chapter, it is the last SCENE of chapter four. Named here so `plan`
# can split iv_chosen at it instead of guessing.
CODA_SCENE = "iv_chosen_the_moor_again_00"

# ───────────────────────────────────────────────────────────────── sound effects
# ONE SOUND PER BED, concrete, close, dry - the discipline the SFX library already
# records, and the reason the pre-2026-07-30 beds were mush. Every entry names a thing
# the SCRIPT names; nothing here is atmosphere invented to fill space.
#
# `bus` decides where it sits in the mix and is not decoration:
#   hero      the 4-6 events the film is made of. They are the whole point of a beat.
#   designed  a real event, but support.
#   ambience  glue. If you can identify it as a sound it is too loud.
#
# `card` reuses a studio/sfx/*.json preset where one already says exactly this - the
# library is good and two of these were written for this exact action before this film
# existed. The rest are written here because a preset for "a steel gauntlet dropping into
# deep snow" does not exist and should not be invented as a general-purpose card off one
# film's needs.
SFX = [
    dict(id="strap_pull", beat=1, bus="hero", secs=4,
         where="beat 1, under the first frame of the film, before the score enters",
         prompt="a leather strap pulled hard through a steel buckle, one long creak "
                "under tension ending in a sharp catch, close microphone, dry",
         negative="music, tonal, melody, speech, reverb, wind, footsteps"),
    dict(id="throat_buckle", beat=2, bus="hero", secs=4,
         where="beat 2, on the push, the buckle closing under her jaw",
         prompt="a single steel buckle snapping closed, one sharp metallic click "
                "followed by a short rustle of chainmail, close microphone, dry",
         negative="music, tonal, melody, bell, ringing, speech, reverb, repeating"),
    dict(id="banners", beat=3, bus="ambience", secs=10,
         where="beat 3, the empty courtyard wide",
         prompt="heavy cloth banners snapping and rippling in strong wind on wooden "
                "poles, rope creaking against wood, outdoors, open air",
         negative="music, speech, voices, crowd, birds, rain, whistling"),
    dict(id="snow_steps", beat=4, bus="designed", secs=6,
         where="beat 4, she walks out of frame to the left",
         prompt="slow heavy footsteps compressing deep dry snow, an armoured weight on "
                "each step, crunching and squeaking, outdoors, no wind",
         negative="music, speech, wind, water, ice cracking, reverb"),
    dict(id="gauntlet_snow", beat=5, bus="hero", secs=4,
         where="beat 5, the aftermath insert - the last sound of act one",
         prompt="a heavy steel gauntlet dropped into deep soft snow, a dull muffled "
                "thud with a faint metal rattle inside it, then nothing, close, dry",
         negative="music, tonal, ringing, bell, speech, reverb, wind, repeating"),
    dict(id="hall_tone", beat=6, bus="ambience", secs=12,
         where="beats 6-10, the whole court movement, including under the silence",
         prompt="the room tone of a very large empty stone hall, faint low air movement, "
                "distant high stone resonance, nothing happening",
         negative="music, speech, voices, footsteps, wind, rain, machinery"),
    dict(id="chandelier", beat=6, bus="designed", secs=8,
         where="beat 6, the iron chandelier swinging on the pull-out",
         prompt="a heavy iron chandelier swinging slowly on a long chain, deep "
                "rhythmic chain creak, an occasional metal knock, large stone room",
         negative="music, tonal, melody, bell, speech, wind, footsteps"),
    dict(id="glove_stone", beat=9, bus="hero", secs=3,
         where="beat 9, the white glove landing. The quietest hero sound in the film.",
         prompt="a single soft leather glove landing on a bare stone floor, one very "
                "quiet dry slap of light fabric, dry rushes shifting once, close",
         negative="music, tonal, speech, reverb, impact, thud, metal, repeating"),
    dict(id="fist_table", beat=10, bus="hero", secs=4,
         where="beat 10, on the push, her fist closing on the table edge",
         prompt="a hand closing hard on the edge of a heavy oak table, knuckles and dry "
                "wood creaking under pressure, fabric pulling tight, very close",
         negative="music, tonal, speech, bang, slam, impact, reverb, repeating"),
    dict(id="moor_wind", beat=11, bus="ambience", secs=12, card="wind_open",
         where="beats 11-12, and again under beat 20 at a lower level",
         prompt=None, negative=None),
    dict(id="sash_flap", beat=12, bus="designed", secs=3,
         where="beat 12, the torn sash crossing frame",
         prompt="a single strip of torn cloth whipping past close to the microphone in "
                "one strong gust, a sharp fabric snap and away, outdoors",
         negative="music, speech, footsteps, reverb, rain, flag pole"),
    dict(id="ford_water", beat=13, bus="designed", secs=8,
         where="beat 13, stumbling through the ford",
         prompt="boots stumbling through shallow fast-running water over loose stones, "
                "splashing and stones knocking together, close, outdoors",
         negative="music, speech, waterfall, rain, thunder, reverb"),
    dict(id="purse_drop", beat=14, bus="hero", secs=4,
         where="beat 14, the reveal. The money that was not hers, one insert long.",
         prompt="a small leather purse full of coins dropped into an open palm, a soft "
                "leather slap and coins settling inside it, close microphone, dry",
         negative="music, tonal, speech, bell, cash register, jingling melody, reverb"),
    dict(id="purse_grip", beat=15, bus="designed", secs=3,
         where="beat 15, the turn of the film - her fingers closing over it",
         prompt="a hand closing tightly around a leather purse, leather creaking under "
                "the grip, coins shifting once inside, very close, dry",
         negative="music, tonal, speech, jingling, reverb, footsteps"),
    dict(id="coat_hook", beat=16, bus="designed", secs=5,
         where="beat 16, the object the film is named after, first seen",
         prompt="a heavy wool coat swinging on an iron hook, thick fabric moving "
                "slowly, the hook rattling once against an iron rail, close",
         negative="music, tonal, speech, bell, ringing, wind, footsteps"),
    dict(id="market_tone", beat=16, bus="ambience", secs=12,
         where="beats 16-19, the border town, under the whole fourth movement",
         prompt="the ambience of a small quiet early morning street market, wooden "
                "crates set down, footsteps far away, faint indistinct murmuring in "
                "the distance, outdoors, open air",
         negative="music, singing, shouting, clear speech, crowd roar, traffic, bells"),
    dict(id="sleeve", beat=18, bus="hero", secs=5, card="cloth_movement",
         where="beat 18, under silence. The loudest small sound in the film.",
         prompt=None, negative=None),
    dict(id="cobble_steps", beat=19, bus="designed", secs=8,
         where="beat 19, walking toward the camera between the stalls",
         prompt="unhurried footsteps in leather boots on wet cobblestones, walking "
                "steadily toward the microphone, outdoors",
         negative="music, speech, voices, crowd, horse, cart, reverb"),
    dict(id="coat_flap", beat=20, bus="hero", secs=8,
         where="beat 20, the last sound in the film - the only thing still moving",
         prompt="a heavy wool coat flapping in steady wind, thick fabric snapping and "
                "settling and snapping again, close, outdoors",
         negative="music, tonal, speech, flag pole, rope, footsteps, rain"),
]
SFX_SEEDS = [4471, 7703]          # heroes get both; everything else gets the first

# ─────────────────────────────────────────────────────────────── the LTX audio probe
# LTX-2.3 emits a synchronised audio track on every clip and this project has never
# played one. `ltx` answers three questions with numbers rather than with an opinion:
#   1. What level does it arrive at for THESE shots?  (craft/SOUND.md has the answer for
#      a different film: median -24.7 dB, 39 dB of spread, and it tracks the prompt.)
#   2. Is it room tone, or is it music, or is it people talking? Spectral flatness and
#      an ASR pass separate the three, and the ASR pass is the one that matters: an
#      invented voice under a film where the character speaks twice is not a bed, it is
#      a second cast member.
#   3. Does it cover the picture? (Measured on existing clips before anything was
#      rendered: it does not. See `report`.)
# Six beats, chosen to span the range the prompt-tracking finding predicts: two empty
# wides, two close inserts, one storm exterior, one street with a person in it.
LTX_PROBE = ["i_issued_dressed_00", "i_issued_dressed_02", "ii_decided_the_hall_00",
             "iii_the_road_the_ford_00", "iv_chosen_she_walks_00",
             "iv_chosen_the_moor_again_00"]
LTX_FRAMES = 97          # 8n+1, 4.04s at 24fps - long enough to characterise a bed
# THE AUDIO LATENT IS ALLOCATED AT THE WRONG FRAME RATE IN BOTH LTX WORKFLOWS.
# workflows/11 and 12 both say `LTXVEmptyLatentAudio.frame_rate: 25` while CreateVideo
# writes the picture at fps 24. 24/25 = 0.96, and measured across 838 rendered clips on
# this box the audio stream is 0.9453-0.9570 of the video stream, median 0.9550 - i.e.
# every clip this project has ever rendered has an audio track that stops about a quarter
# of a second before its picture does. `ltx` renders one beat both ways to settle it.
LTX_AUDIO_FPS = 25       # as shipped
LTX_AUDIO_FPS_FIX = 24   # matched to CreateVideo

# Reference anchors for the spectral comparison, so "flat 0.31" means something. Filled
# in by `ltx` from files this tool has already rendered.
ANCHORS = [("voice", "voice"), ("score", "score"), ("sfx_wind", "sfx")]


def _dir(*p):
    d = os.path.join(OUT, *p)
    os.makedirs(d, exist_ok=True)
    return d


def _film():
    if not os.path.exists(MOVIE):
        raise SystemExit(f"no compiled film at {MOVIE}\n"
                         f"  run: python3 studio/compile.py "
                         f"studio/movies/terra_field_coat.movie")
    return json.load(open(MOVIE, encoding="utf-8"))


def _beat_seconds(b):
    cuts, impact = expand_template(b, float(b.get("clip_secs", 4)))
    return sum(float(c["len"]) for c in cuts) + (2.0 / 24 if impact else 0.0)


def _timeline(film):
    """Start, length and chapter for every beat, off the same model compile.py uses."""
    rows, t = [], 0.0
    for b in film["beats"]:
        ln = _beat_seconds(b)
        rows.append(dict(id=b["id"], at=round(t, 3), len=round(ln, 3),
                         chapter=b["id"].split("_")[0] + "_" + b["id"].split("_")[1],
                         beat=b))
        t += ln
    return rows, t


def _spans(film):
    """Cue spans measured off the timeline: four chapters, with the coda split out."""
    rows, total = _timeline(film)
    # chapter id is everything before the scene name, and scene names vary in length, so
    # take it from the .movie's own chapter order instead of splitting on underscores.
    order, seen = [], set()
    for r in rows:
        ch = _chapter_of(r["id"])
        if ch not in seen:
            seen.add(ch)
            order.append(ch)
    spans = {}
    for ch in order:
        rs = [r for r in rows if _chapter_of(r["id"]) == ch and r["id"] != CODA_SCENE]
        if rs:
            spans[ch] = (rs[0]["at"], rs[-1]["at"] + rs[-1]["len"])
    coda = [r for r in rows if r["id"] == CODA_SCENE]
    if coda:
        spans["coda"] = (coda[0]["at"], coda[0]["at"] + coda[0]["len"])
    return rows, total, spans


CHAPTERS = ["i_issued", "ii_decided", "iii_the_road", "iv_chosen"]


def _chapter_of(bid):
    for c in CHAPTERS:
        if bid.startswith(c + "_"):
            return c
    return bid.split("_")[0]


# ──────────────────────────────────────────────────────────────────────── plan
def plan(a):
    """Print the real timeline and what sound sits where. Renders nothing."""
    film = _film()
    rows, total, spans = _spans(film)
    print(f"\n=== {film['title']}  {total:.2f}s, {len(rows)} beats ===\n")
    sfx_at = {}
    for s in SFX:
        sfx_at.setdefault(s["beat"], []).append(s["id"])
    print(f"{'#':>3} {'at':>7} {'len':>6}  {'beat':38} {'sound'}")
    for i, r in enumerate(rows, 1):
        b = r["beat"]
        bits = list(sfx_at.get(i, []))
        if b.get("line"):
            bits.insert(0, f"VOICE {b['line']['text']!r}")
        print(f"{i:>3} {r['at']:>7.2f} {r['len']:>6.2f}  {r['id']:38} "
              f"{', '.join(bits) or '-'}")
    print(f"\n--- score, measured off that timeline ---")
    for c in CUES:
        sp = spans.get(c["chapter"])
        if not sp:
            print(f"  ! {c['id']}: no span for chapter {c['chapter']}")
            continue
        st, en = sp
        print(f"  {c['id']:16} {st:6.2f} -> {en:6.2f}  ({en - st:5.2f}s)  "
              f"{c['key']:9} {c['bpm']:>3} bpm   render {_cue_secs(st, en)}s")
    print("\n--- the compiled placeholder score this replaces ---")
    for c in film.get("music", []):
        print(f"  {c['prefix']:20} at {c['at']:6.2f}  {c['seconds']:>3}s  "
              f"{c['key']:9} {c['bpm']:>3} bpm")
    return 0


def _cue_secs(st, en):
    """Generate long and trim in the mix. ACE-Step has no hit-point conditioning and
    cannot spot to picture, and a cue asked for its exact length ends abruptly."""
    return int(max(16, math.ceil(en - st) + 8))


# ─────────────────────────────────────────────────────────────────────── voice
def _index_wf(text, voice, prefix, seed, emo, rep=None):
    wf = load_wf("16_indextts2_voice.json")
    for k, v in emo.items():
        set_path(wf, f"20.inputs.{k}", float(v))
    set_path(wf, "30.inputs.text", text)
    set_path(wf, "30.inputs.narrator_voice", voice)
    set_path(wf, "30.inputs.seed", int(seed))
    if rep is not None:
        set_path(wf, "10.inputs.repetition_penalty", float(rep))
    set_path(wf, "40.inputs.filename_prefix", prefix)
    return wf


def _cast_voice():
    c = json.load(open(os.path.join(ROOT, "studio", "characters", "TERRA.json"),
                       encoding="utf-8"))
    raw = c.get("voice")
    if not raw:
        raise SystemExit("TERRA.json has no voice")
    return str(raw).split()[-1]


def _render(wf, dest, label):
    if os.path.exists(dest):
        return dest
    print(f"  > {label}", flush=True)
    try:
        _, outs = run(HOST, wf, quiet=True)
    except SystemExit:
        print(f"    !! RENDER FAILED {label}")
        return None
    if not outs:
        print(f"    !! NO OUTPUT {label}")
        return None
    got = ensure_local(outs[0], dest, required=False)
    if not got:
        print(f"    !! COULD NOT FETCH {label}")
    return got


def voice(a):
    """Both spoken lines, three readings each, two seeds. Nothing is post-processed
    here: `measure` needs the raw stem, and the levelled stem is written beside it."""
    v = _cast_voice()
    d = _dir("voice")
    print(f"\n=== VOICE: {len(LINES)} lines x {len(LINES[0]['takes'])} readings "
          f"x {len(VOICE_SEEDS)} seeds, voice={v} ===")
    for ln in LINES:
        for tag, emo in ln["takes"]:
            for s in VOICE_SEEDS:
                name = f"{ln['id']}__{tag}__s{s}"
                _render(_index_wf(ln["text"], v, f"{GEN}/voice/{name}", s, emo,
                                  rep=a.rep),
                        f"{d}/{name}.mp3", name)
    return 0


def sweep(a):
    """Calm, Happy and Melancholic, 0.0 to 1.0, one line, one seed.

    Three of the six dimensions TERRA's voice_direction records as UNMEASURED, and the
    three this film's dialogue actually leans on. Angry and Afraid are already swept and
    are deliberately not repeated."""
    v = _cast_voice()
    d = _dir("sweep")
    print(f"\n=== EMOTION SWEEP: {len(SWEEP)} dimensions x {len(SWEEP_VALUES)} values ===")
    for tag, dim in SWEEP:
        for val in SWEEP_VALUES:
            name = f"{tag}_{int(val * 100):03d}"
            _render(_index_wf(SWEEP_LINE, v, f"{GEN}/sweep/{name}", SEED,
                              {dim: val} if val else {}),
                    f"{d}/{name}.mp3", name)
    return 0


# ─────────────────────────────────────────────────────────────────────── score
def score(a):
    film = _film()
    _, _, spans = _spans(film)
    d = _dir("score")
    print(f"\n=== SCORE: {len(CUES)} cues x {len(CUE_SEEDS)} takes ===")
    for i, c in enumerate(CUES):
        sp = spans.get(c["chapter"])
        if not sp:
            print(f"  ! no span for {c['id']}")
            continue
        secs = _cue_secs(*sp)
        for j, s in enumerate(CUE_SEEDS):
            name = f"{c['id']}__t{j}"
            dest = f"{d}/{name}.mp3"
            if os.path.exists(dest):
                continue
            wf = load_wf("06_acestep_music.json")
            set_path(wf, "10.inputs.tags", c["tags"])
            set_path(wf, "10.inputs.lyrics", "")
            set_path(wf, "10.inputs.bpm", int(c["bpm"]))
            set_path(wf, "10.inputs.keyscale", c["key"])
            set_path(wf, "10.inputs.duration", float(secs))
            set_path(wf, "11.inputs.seconds", float(secs))
            set_path(wf, "10.inputs.seed", int(s))
            set_path(wf, "12.inputs.seed", int(s))
            set_path(wf, "14.inputs.filename_prefix", f"{GEN}/score/{name}")
            _render(wf, dest, f"{name}  {c['key']} {c['bpm']}bpm {secs}s")
    return 0


# ───────────────────────────────────────────────────────────────────────── sfx
def _sfx_card(cid):
    p = os.path.join(ROOT, "studio", "sfx", f"{cid}.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def sfx(a):
    d = _dir("sfx")
    print(f"\n=== SFX: {len(SFX)} beds ===")
    for i, s in enumerate(SFX):
        card = _sfx_card(s["card"]) if s.get("card") else None
        pos = s["prompt"] or (card or {}).get("prompt")
        neg = s["negative"] or (card or {}).get("negative") or ""
        if not pos:
            print(f"  ! {s['id']}: no prompt and no card")
            continue
        secs = float(card["seconds"]) if card and not s.get("secs") else float(s["secs"])
        seeds = SFX_SEEDS if s["bus"] == "hero" else SFX_SEEDS[:1]
        for j, seed in enumerate(seeds):
            name = f"{s['id']}__t{j}"
            dest = f"{d}/{name}.mp3"
            if os.path.exists(dest):
                continue
            wf = load_wf("10_stableaudio_sfx.json")
            set_path(wf, "3.inputs.text", pos)
            set_path(wf, "4.inputs.text", neg)
            set_path(wf, "5.inputs.seconds", secs)
            # Stable Audio 3 is NOT distilled, so cfg 1.0 really does disable guidance
            # and the negative prompt with it. 100/7/dpmpp_3m_sde is the measured setting.
            set_path(wf, "6.inputs.steps", 100)
            set_path(wf, "6.inputs.cfg", 7.0)
            set_path(wf, "6.inputs.sampler_name", "dpmpp_3m_sde")
            set_path(wf, "6.inputs.seed", int(seed) + i * 31)
            set_path(wf, "8.inputs.filename_prefix", f"{GEN}/sfx/{name}")
            _render(wf, dest, f"{name} [{s['bus']}] {secs:.0f}s")
    return 0


# ───────────────────────────────────────────────────────────────────────── ltx
def ltx(a):
    """Render the film's own beats through LTX t2v and keep the audio it invents.

    t2v rather than i2v on purpose: i2v needs a keyframe, the keyframes need the
    `costume:` fix that is not this task's to make, and the AUDIO does not depend on the
    start image - it is conditioned on the same text either way. This measures the bed
    for these shots without blocking on the picture department."""
    film = _film()
    beats = {b["id"]: b for b in film["beats"]}
    d = _dir("ltx")
    todo = [b for b in LTX_PROBE if b in beats]
    print(f"\n=== LTX AUDIO PROBE: {len(todo)} beats, {LTX_FRAMES} frames each ===")
    jobs = [(bid, LTX_AUDIO_FPS, bid) for bid in todo]
    # One A/B on the frame-rate mismatch, same beat, same seed, only the audio latent's
    # frame_rate moves. If coverage goes to 1.0 the workflows have a two-character bug.
    if todo:
        jobs.append((todo[0], LTX_AUDIO_FPS_FIX, todo[0] + "__afps24"))
    for i, (bid, afps, name) in enumerate(jobs):
        b = beats[bid]
        dest = f"{d}/{name}.mp4"
        if os.path.exists(dest):
            continue
        # The clip prompt is the beat's own prompt plus its motion line, which is what
        # short.py sends. Sending anything else would measure a bed for a shot that is
        # not in the film.
        txt = (b.get("motion", "") + " " + b["prompt"]).strip()
        wf = load_wf("11_ltx23_t2v_audio.json")
        set_path(wf, "10.inputs.text", txt)
        set_path(wf, "20.inputs.length", LTX_FRAMES)
        set_path(wf, "21.inputs.frames_number", LTX_FRAMES)
        set_path(wf, "21.inputs.frame_rate", int(afps))
        set_path(wf, "32.inputs.noise_seed", SEED + LTX_PROBE.index(bid) * 13)
        set_path(wf, "43.inputs.filename_prefix", f"{GEN}/ltx/{name}")
        _render(wf, dest, f"{name}  (audio latent at {afps} fps)")
    return 0


def survey(a):
    """Characterise every LTX bed this box has ever rendered. Renders nothing.

    Level was measured once before, on one film, in craft/SOUND.md. Nobody ever asked
    what is IN the bed, or whether it covers the shot."""
    import numpy as np, librosa
    root = os.path.join(COMFY, "output", "claude-generated")
    files = [f for f in sorted(glob.glob(root + "/**/clips/*.mp4", recursive=True))
             if "_work" not in f]
    print(f"\n=== LTX SURVEY: {len(files)} rendered clips on this box ===")
    rows = []
    for p in files:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "stream=codec_type,duration", "-of", "json", p],
                           capture_output=True, text=True)
        try:
            st = json.loads(r.stdout)["streams"]
            v = [s for s in st if s["codec_type"] == "video"][0]
            au = [s for s in st if s["codec_type"] == "audio"][0]
            rows.append((p, float(v["duration"]), float(au["duration"])))
        except (ValueError, KeyError, IndexError):
            continue
    cov = np.array([au / v for _, v, au in rows])
    print(f"  clips with an audio stream: {len(rows)}")
    print(f"  audio/video length ratio:  min {cov.min():.4f}  "
          f"median {np.median(cov):.4f}  max {cov.max():.4f}")
    print(f"  clips whose audio COVERS the picture: "
          f"{int((cov >= 0.999).sum())} of {len(rows)}")
    d = _dir("ltx_existing")
    import random
    random.seed(11)
    samp = random.sample(rows, min(a.n, len(rows)))
    res = []
    for p, vd, ad in samp:
        w = f"{d}/_tmp.wav"
        sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vn", "-ac", "1", "-ar", "32000", w)
        y, sr = librosa.load(w, sr=None, mono=True)
        if y.size < 1000:
            continue
        S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
        fr = librosa.fft_frequencies(sr=sr, n_fft=2048)
        tot = float(S.sum()) + 1e-9
        rms = float(np.sqrt(np.mean(y ** 2)))
        res.append(dict(f=os.path.relpath(p, root),
                        mean=round(20 * math.log10(max(rms, 1e-9)), 1),
                        flat=round(float(np.mean(
                            librosa.feature.spectral_flatness(S=S))), 5),
                        cent=round(float(np.mean(
                            librosa.feature.spectral_centroid(S=S, sr=sr))), 0),
                        speechband=round(float(
                            S[(fr >= 300) & (fr < 3400)].sum()) / tot, 3)))
    lv = np.array([r["mean"] for r in res])
    fl = np.array([r["flat"] for r in res])
    print(f"\n  mean level over {len(res)} sampled beds: min {lv.min():.1f}  "
          f"p10 {np.percentile(lv, 10):.1f}  median {np.median(lv):.1f}  "
          f"p90 {np.percentile(lv, 90):.1f}  max {lv.max():.1f}  "
          f"stdev {lv.std():.1f} dB")
    print(f"  spectral flatness:  median {np.median(fl):.5f}  "
          f"(broadband noise is ~0.1-0.5; a tonal bed is <0.01)")
    # keep the loudest handful so `asr` can ask whether there is a voice in them
    for r in sorted(res, key=lambda r: -r["mean"])[:a.keep]:
        src = os.path.join(root, r["f"])
        name = r["f"].replace("/", "__").replace(".mp4", "")
        sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vn", "-ac", "1",
           "-ar", "32000", f"{d}/{name}.wav")
    if os.path.exists(f"{d}/_tmp.wav"):
        os.remove(f"{d}/_tmp.wav")
    json.dump(res, open(f"{OUT}/ltx_survey.json", "w", encoding="utf-8"), indent=1)
    print(f"\n  -> {OUT}/ltx_survey.json, "
          f"{a.keep} loudest beds kept in ltx_existing/ for the ASR pass")
    return 0


# ─────────────────────────────────────────────────────────────────── measuring
def _probe(path):
    """Numbers off the waveform. Extends cast_voice's line probe with the things that
    matter for music and effects rather than for speech: integrated loudness, spectral
    flatness (tonal vs noise), and where the energy actually is."""
    import numpy as np, librosa
    y, sr = librosa.load(path, sr=None, mono=True)
    if y.size == 0:
        return {"error": "empty file"}
    db = lambda v: float(20 * np.log10(v)) if v > 1e-9 else -120.0
    peak = float(np.max(np.abs(y)))
    m = dict(seconds=round(len(y) / sr, 3), sample_rate=int(sr),
             peak_dbfs=round(db(peak), 2),
             rms_dbfs=round(db(float(np.sqrt(np.mean(y ** 2)))), 2),
             clipped_samples=int(np.sum(np.abs(y) >= 0.999)))
    m["crest_db"] = round(m["peak_dbfs"] - m["rms_dbfs"], 2)
    hop = 512
    fr = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
    fdb = 20 * np.log10(np.maximum(fr, 1e-9))
    quiet = fdb < (m["peak_dbfs"] - 35.0)
    m["silence_frac"] = round(float(quiet.mean()), 3)
    longest = cur = 0
    for q in quiet:
        cur = cur + 1 if q else 0
        longest = max(longest, cur)
    m["longest_pause_s"] = round(longest * hop / sr, 2)
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
    m["lead_silence_s"] = round(lead * hop / sr, 2)
    m["tail_silence_s"] = round(tail * hop / sr, 2)
    # TRUNCATION. A file that stops while it is still loud was cut off, not finished.
    # Measured as the level of the last 150 ms against the file's own median frame.
    n = max(1, int(0.15 * sr / hop))
    med = float(np.median(fdb))
    m["tail_150ms_db"] = round(float(np.mean(fdb[-n:])), 2)
    m["tail_vs_median_db"] = round(m["tail_150ms_db"] - med, 2)
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
    m["flatness"] = round(float(np.mean(librosa.feature.spectral_flatness(S=S))), 5)
    m["centroid_hz"] = round(float(np.mean(
        librosa.feature.spectral_centroid(S=S, sr=sr))), 1)
    m["rolloff85_hz"] = round(float(np.mean(
        librosa.feature.spectral_rolloff(S=S, sr=sr, roll_percent=0.85))), 1)
    # Energy in the speech band against everything else. A room-tone bed is bottom
    # heavy; anything with a voice or a melody in it puts energy in 300-3400 Hz.
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
    tot = float(np.sum(S)) + 1e-9
    band = lambda lo, hi: round(float(
        np.sum(S[(freqs >= lo) & (freqs < hi)])) / tot, 4)
    m["e_sub_120"] = band(0, 120)
    m["e_speech"] = band(300, 3400)
    m["e_hi_6k"] = band(6000, sr / 2)
    d = loudness(path)
    if d:
        m["lufs"] = float(d["input_i"])
        m["true_peak_dbtp"] = float(d["input_tp"])
        m["lra"] = float(d["input_lra"])
    return m


def _defects(m, kind, expect_words=0):
    bad = []
    if m.get("error"):
        return [m["error"]]
    if m["seconds"] < 0.4:
        bad.append("SILENT/STUB - under 0.4s")
    if m["rms_dbfs"] < -60:
        bad.append(f"SILENT - rms {m['rms_dbfs']} dBFS")
    if m["clipped_samples"] > 0:
        bad.append(f"CLIPPED - {m['clipped_samples']} samples at full scale")
    if m["peak_dbfs"] > -0.2:
        bad.append(f"AT CEILING - peak {m['peak_dbfs']} dBFS")
    if m["tail_vs_median_db"] > -3.0 and kind in ("voice", "sfx"):
        bad.append(f"TRUNCATED? still at {m['tail_vs_median_db']:+.1f} dB of its own "
                   f"median in the last 150 ms")
    if kind == "voice":
        if m["silence_frac"] > 0.55:
            bad.append(f"MOSTLY SILENCE - {m['silence_frac']:.0%}")
        if m["tail_silence_s"] > 1.5:
            bad.append(f"LONG TAIL - {m['tail_silence_s']}s of nothing")
        if expect_words:
            wps = expect_words / max(m["seconds"] * (1 - m["silence_frac"]), 1e-6)
            if wps > 6.5:
                bad.append(f"TRUNCATED? {wps:.1f} words/sec is too fast to be real")
    if kind == "sfx" and m["flatness"] < 0.0004 and m["e_speech"] > 0.5:
        bad.append("TONAL - reads as music, not as an object")
    return bad


KINDS = [("voice", "voice"), ("sweep", "voice"), ("score", "score"),
         ("sfx", "sfx"), ("ltx", "ltx"), ("ltx_existing", "ltx")]


def measure(a):
    out = _load_manifest()
    for sub, kind in KINDS:
        d = os.path.join(OUT, sub)
        if not os.path.isdir(d):
            continue
        files = sorted(glob.glob(f"{d}/*.mp3") + glob.glob(f"{d}/*.wav") +
                       glob.glob(f"{d}/*.mp4"))
        if not files:
            continue
        print(f"\n=== MEASURE {sub}: {len(files)} files ===")
        got = out.setdefault(sub, {})
        for p in files:
            name = os.path.splitext(os.path.basename(p))[0]
            src = p
            if p.endswith(".mp4"):
                src = f"{OUT}/{sub}/_a_{name}.wav"
                if not os.path.exists(src):
                    sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vn",
                       "-c:a", "pcm_s16le", src)
                got.setdefault(name, {})["video_seconds"] = _vdur(p)
            m = _probe(src)
            words = 0
            for ln in LINES:
                if name.startswith(ln["id"]):
                    words = len(ln["text"].split())
            m["defects"] = _defects(m, kind, words)
            prev = got.get(name, {})
            m = {**prev, **m}
            got[name] = m
            flag = "  !! " + "; ".join(m["defects"]) if m["defects"] else ""
            print(f"  {name:44} {m['seconds']:6.2f}s  peak {m['peak_dbfs']:7.2f}  "
                  f"rms {m['rms_dbfs']:7.2f}  lufs {m.get('lufs', 0):7.1f}  "
                  f"flat {m['flatness']:.5f}{flag}")
    _save_manifest(out)
    return 0


def _vdur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=duration", "-of",
                        "default=nw=1:nk=1", p], capture_output=True, text=True)
    try:
        return round(float(r.stdout.strip()), 3)
    except ValueError:
        return None


def _load_manifest():
    p = os.path.join(OUT, "measurements.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def _save_manifest(d):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "measurements.json")
    json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\n  -> {p}")


# ───────────────────────────────────────────────────────────────────────── asr
def _norm(s):
    import re
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).split()


def _wer(ref, hyp):
    r, h = _norm(ref), _norm(hyp)
    if not r:
        return 0.0
    prev = list(range(len(h) + 1))
    for i, rw in enumerate(r, 1):
        cur = [i]
        for j, hw in enumerate(h, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (rw != hw)))
        prev = cur
    return round(prev[-1] / len(r), 3)


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


GRANITE = os.path.join(COMFY, "models", "TTS", "granite_asr", "granite-speech-4.1-2b")


def _asr_local(paths, device=None):
    """Transcribe with the Granite speech weights already on this box.

    IN PROCESS, NOT THROUGH THE COMFYUI QUEUE, and that is deliberate. The queue is
    shared - measured, this run sat behind three LTX clips and two FLUX images for
    minutes on the FIRST of 49 files, and every job reloads the model. Loading it once
    here does the whole set in about the time one queued job takes to start. Nothing is
    downloaded: these weights are already in models/TTS."""
    import torch, torchaudio
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from transformers import (AutoProcessor,
                              GraniteSpeechForConditionalGeneration as G)
    proc = AutoProcessor.from_pretrained(GRANITE)
    tok = proc.tokenizer
    # The GPU is shared with whatever else is rendering. ComfyUI holding the 22B LTX
    # checkpoint leaves under 2 GiB free and this OOMs; CPU is slower and always there.
    dev = device or ("cuda" if torch.cuda.is_available() else "cpu")
    try:
        model = G.from_pretrained(GRANITE, dtype=torch.bfloat16, device_map=dev)
    except (torch.OutOfMemoryError, RuntimeError) as e:
        if dev != "cuda":
            raise
        print(f"    (GPU busy - {str(e)[:60]}; falling back to CPU)")
        dev = "cpu"
        model = G.from_pretrained(GRANITE, dtype=torch.float32, device_map=dev)
    chat = [{"role": "system", "content": "You are Granite, developed by IBM. You are "
                                          "a helpful AI assistant"},
            {"role": "user", "content": "<|audio|>can you transcribe the speech into a "
                                        "written format?"}]
    tmpl = tok.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
    out = {}
    for p in paths:
        wav, sr = torchaudio.load(p)
        wav = torchaudio.functional.resample(wav.mean(0, keepdim=True), sr, 16000)
        inp = proc(tmpl, wav, device=dev, return_tensors="pt").to(dev)
        gen = model.generate(**inp, max_new_tokens=200, do_sample=False, num_beams=1)
        n = inp["input_ids"].shape[-1]
        out[p] = tok.batch_decode(gen[:, n:], skip_special_tokens=True)[0].strip()
    return out


def asr(a):
    """Read the words back off every voice take - and off every LTX bed.

    On the voice takes this is the only check that catches a dropped clause. On the LTX
    beds it is the check that decides the whole question: if an ASR pass returns
    confident words from a shot with no dialogue in it, LTX has invented a speaker and
    the bed cannot be used under a film where the lead speaks twice."""
    d = _dir("asr")
    jobs = []
    for sub in ("voice", "sweep", "ltx", "ltx_existing"):
        s = os.path.join(OUT, sub)
        for p in sorted(glob.glob(f"{s}/*.mp3") + glob.glob(f"{s}/_a_*.wav") +
                        (glob.glob(f"{s}/*.wav") if sub == "ltx_existing" else [])):
            base = os.path.splitext(os.path.basename(p))[0]
            jobs.append((f"{sub}__{base}", p))
    todo = [(n, p) for n, p in jobs if not os.path.exists(f"{d}/{n}.txt")]
    print(f"\n=== ASR: {len(jobs)} files ({len(todo)} to transcribe) ===")
    if todo:
        got = _asr_local([p for _, p in todo])
        for n, p in todo:
            open(f"{d}/{n}.txt", "w", encoding="utf-8").write(got.get(p, ""))
            print(f"  {n[:60]:60} {got.get(p, '')[:50]!r}")
    man = _load_manifest()
    for name, _ in jobs:
        have = f"{d}/{name}.txt"
        if not os.path.exists(have):
            continue
        txt = open(have, encoding="utf-8").read().strip()
        sub, _, base = name.partition("__")
        base = base[3:] if base.startswith("_a_") else base
        rec = man.setdefault(sub, {}).setdefault(base, {})
        rec["asr_text"] = txt
        exp = None
        for ln in LINES:
            if base.startswith(ln["id"]):
                exp = ln["text"]
        if sub == "sweep":
            exp = SWEEP_LINE
        if exp:
            rec["expected_text"] = exp
            rec["wer"] = _wer(exp, txt)
        else:
            rec["asr_words"] = len(_norm(txt))
    _save_manifest(man)
    for sub in ("voice", "sweep"):
        for k, v in sorted(man.get(sub, {}).items()):
            if "wer" in v:
                mark = "" if v["wer"] == 0 else "   !! WORDS LOST"
                print(f"  {sub}/{k:44} wer {v['wer']:.3f}  {v['asr_text']!r}{mark}")
    for sub in ("ltx", "ltx_existing"):
        for k, v in sorted(man.get(sub, {}).items()):
            n = v.get("asr_words", 0)
            print(f"  {sub}/{k[:46]:46} {n:>3} words heard  "
                  f"{v.get('asr_text', '')[:64]!r}")
    return 0


# ────────────────────────────────────────────────────────────────────── report
def report(a):
    """Where every element sits, at what level, against the measured timeline."""
    film = _film()
    rows, total, spans = _spans(film)
    man = _load_manifest()
    print(f"\n=== {film['title']} - SOUND PLACEMENT ===")
    print(f"    {total:.2f}s, {len(rows)} beats, 2 spoken lines, "
          f"{len(CUES)} cues, {len(SFX)} effects\n")
    print("BUS TARGETS. craft/SOUND.md's table assumes wall-to-wall narration (72% duty")
    print("cycle). This film speaks for about 5% of its length, so the 'no narration'")
    print("column is the right one and the score does not need ducking except across the")
    print("two lines, where a 5 dB duck on a 66-second film is 4 seconds of duck.\n")
    for name, tgt in MIX:
        print(f"  {name:22} {tgt}")
    print("\n--- cues ---")
    for c in CUES:
        st, en = spans.get(c["chapter"], (0, 0))
        takes = [k for k in man.get("score", {}) if k.startswith(c["id"] + "__")]
        print(f"  {c['id']:16} {st:6.2f} -> {en:6.2f}  {c['key']:9} "
              f"{c['bpm']:>3}bpm  {len(takes)} takes")
        print(f"    {c['desc']}")
    print("\n--- effects ---")
    for s in SFX:
        r = rows[s["beat"] - 1]
        print(f"  {s['id']:16} beat {s['beat']:>2} @ {r['at']:6.2f}  "
              f"[{s['bus']}]  {s['where']}")
    print("\n--- lines ---")
    for ln in LINES:
        i = [j for j, r in enumerate(rows) if r["id"] == ln["id"]]
        at = rows[i[0]]["at"] if i else 0.0
        print(f"  {ln['id']:32} @ {at:6.2f}  {ln['text']!r}")
        print(f"    {ln['where']}; emotion {ln['emotion']} "
              f"-> vector {dict(ln['takes'][0][1])}")
    return 0


MIX = [
    ("Dialogue", "-20 LUFS, TP -4 dBFS, mixed at volume=1.0. Never a multiplier."),
    ("Hero SFX", "-20 LUFS. These ARE the beats; there is no narration to sit under."),
    ("Designed SFX", "-24 LUFS."),
    ("Ambience", "-28 LUFS. A floor, not a feature."),
    ("Score", "-26 LUFS, ducked to -31 across the two lines only."),
    ("LTX bed", "MUTED. See `ltx` - and short.py already drops it with -an."),
    ("Delivery", "-16 LUFS, -1.5 dBTP, two-pass loudnorm then alimiter."),
]
BUS_LUFS = {"dialogue": -20.0, "hero": -20.0, "designed": -24.0,
            "ambience": -28.0, "score": -26.0}
BUS_TP = {"dialogue": -4.0, "hero": -3.0, "designed": -3.0,
          "ambience": -6.0, "score": -6.0}


# ─────────────────────────────────────────────────────────────── choosing takes
def _pick(sub, stem, man):
    """The best take of an element, by the only criteria a machine can apply.

    Rejects outright: a silent render (ACE-Step returned one on this film - a completed
    job that produced 22 seconds of nothing) and a render whose peak is over full scale.
    Among what is left, take the LOUDEST, because ACE-Step renders sparse material very
    quietly and the quietest take of a sparse cue is usually the one where the model
    gave up rather than the one where it was restrained. THIS IS A RANKING, NOT A
    JUDGEMENT - every take is kept on disk and a human should play them."""
    got = [(k, v) for k, v in man.get(sub, {}).items()
           if k.startswith(stem + "__") and not v.get("error")]
    if not got:
        return None, "no takes"
    ok = [(k, v) for k, v in got
          if v.get("lufs", -99) > -45 and v.get("clipped_samples", 0) == 0]
    why = "clean"
    if not ok:
        ok = [(k, v) for k, v in got if v.get("lufs", -99) > -45]
        why = "every take clipped; picked on level and normalised down"
    if not ok:
        return None, "every take came back silent"
    ok.sort(key=lambda kv: -kv[1].get("lufs", -99))
    return ok[0][0], why


def _silent_windows():
    """The scenes the .movie marks `silence: true`, as (start, end) on the timeline.

    Parsed off the .movie source because compile.py resolves silence into the SCORE
    (it splits the cue run) and then does not write the flag onto the beat, so the
    compiled JSON no longer says which beats are meant to be silent. That is fine for
    the music stage and useless for anything else that needs to know."""
    src = MOVIE[:-5] + ".movie"
    if not os.path.exists(src):
        return []
    scene, silent = None, []
    for raw in open(src, encoding="utf-8"):
        line = raw.split("//")[0].strip()
        if line.startswith("SCENE "):
            scene = line.split()[1]
        elif scene and line.lower().replace(" ", "") in ("silence:true", "silence:yes"):
            silent.append(scene)
    rows, _, _ = _spans(_film())
    out = []
    for r in rows:
        for s in silent:
            if r["id"].endswith("_" + s + "_00") or r["id"].endswith(s + "_00"):
                out.append((r["at"], r["at"] + r["len"], r["id"]))
    return out


def _segments(start, end, holes):
    """A cue's span with the silent windows cut out of it."""
    segs = [(start, end)]
    for h0, h1, _ in holes:
        nxt = []
        for s, e in segs:
            if h1 <= s or h0 >= e:
                nxt.append((s, e))
                continue
            if s < h0:
                nxt.append((s, h0))
            if h1 < e:
                nxt.append((h1, e))
        segs = nxt
    return [(s, e) for s, e in segs if e - s > 0.5]


def level(a):
    """Normalise the chosen take of every element to its bus target.

    Two-pass loudnorm, never a multiplier. craft/SOUND.md's whole first section is the
    argument for this and this film reproduces it exactly: the five score cues came back
    spanning 39.8 LU and the sound effects came back 19 of 27 over full scale."""
    man = _load_manifest()
    d = _dir("stems")
    rows, total, spans = _spans(_film())
    holes = _silent_windows()
    stems = []
    print("\n=== LEVEL: choosing a take and normalising it to its bus ===")
    for ln in LINES:
        k, why = _pick("voice", f"{ln['id']}__{ln['takes'][0][0]}", man)
        # the authored reading is the one that gets levelled; the alternates stay raw
        if not k:
            print(f"  ! {ln['id']}: {why}")
            continue
        at = [r["at"] for r in rows if r["id"] == ln["id"]][0]
        src = f"{OUT}/voice/{k}.mp3"
        dst = f"{d}/voice__{ln['id']}.wav"
        pre = ""
        if abs(float(ln["voice_rate"]) - 1.0) > 0.01:
            # voice_rate off the emotion card, routed at last. rubberband TEMPO only -
            # no pitch shift, so no formant damage at all; craft/VOICE.md's +/-10% rule
            # is about PITCH and does not bind here.
            pre = f"rubberband=tempo={ln['voice_rate']}"
        norm_to(src, dst, BUS_LUFS["dialogue"], tp=BUS_TP["dialogue"], pre=pre)
        stems.append(dict(file=os.path.basename(dst), bus="dialogue", at=at,
                          source=k, why=why, rate=ln["voice_rate"],
                          kind="voice", text=ln["text"]))
        print(f"  voice  {ln['id']:32} <- {k}  ({why})")
    for c in CUES:
        k, why = _pick("score", c["id"], man)
        if not k:
            print(f"  ! {c['id']}: {why}")
            continue
        st, en = spans[c["chapter"]]
        src = f"{OUT}/score/{k}.mp3"
        dst = f"{d}/score__{c['id']}.wav"
        norm_to(src, dst, BUS_LUFS["score"], tp=BUS_TP["score"])
        stems.append(dict(file=os.path.basename(dst), bus="score", at=st,
                          until=en, segments=_segments(st, en, holes),
                          source=k, why=why, kind="score", cue=c["id"]))
        print(f"  score  {c['id']:32} <- {k}  ({why})")
    for s in SFX:
        k, why = _pick("sfx", s["id"], man)
        if not k:
            print(f"  ! {s['id']}: {why}")
            continue
        at = rows[s["beat"] - 1]["at"]
        src = f"{OUT}/sfx/{k}.mp3"
        dst = f"{d}/sfx__{s['id']}.wav"
        norm_to(src, dst, BUS_LUFS[s["bus"]], tp=BUS_TP[s["bus"]])
        stems.append(dict(file=os.path.basename(dst), bus=s["bus"], at=at,
                          source=k, why=why, kind="sfx", beat=s["beat"],
                          where=s["where"]))
        print(f"  {s['bus']:9} {s['id']:32} <- {k}  ({why})")
    man["stems"] = stems
    man["holes"] = [dict(at=h[0], until=h[1], beat=h[2]) for h in holes]
    man["total_seconds"] = total
    _save_manifest(man)
    for h in holes:
        print(f"  hole   {h[2]:32} {h[0]:.2f} -> {h[1]:.2f}  (score cut out)")
    return 0


def mix(a):
    """Assemble the whole 66.7 seconds as sound only, so it can be listened to.

    There is no picture yet - the keyframes are blocked on a fix that is not this task's
    to make - and a sound department that hands over 60 loose files has not shown anybody
    anything. This is the radio cut: every stem at its measured position and bus level,
    the score gated out of the two silent scenes, ducked under the two lines, one
    two-pass delivery loudness pass and a limiter after it."""
    man = _load_manifest()
    stems = man.get("stems")
    if not stems:
        raise SystemExit("run `level` first")
    total = float(man.get("total_seconds", 66.74))
    d = _dir("mix")
    work = _dir("mix", "_work")
    ins, filt, score_l, other_l, key_l = [], [], [], [], []
    k = 0
    for st in stems:
        p = f"{OUT}/stems/{st['file']}"
        if not os.path.exists(p):
            continue
        if st["kind"] == "score":
            for si, (s0, s1) in enumerate(st["segments"]):
                off, ln = s0 - st["at"], s1 - s0
                fi, fo = min(1.5, ln / 3), min(2.0, ln / 3)
                ins += ["-i", p]
                filt.append(
                    f"[{k}:a]atrim=start={max(off, 0):.3f}:end={off + ln:.3f},"
                    f"asetpts=PTS-STARTPTS,afade=t=in:st=0:d={fi:.2f},"
                    f"afade=t=out:st={ln - fo:.2f}:d={fo:.2f},"
                    f"adelay={int(s0 * 1000)}|{int(s0 * 1000)}[s{k}]")
                score_l.append(f"[s{k}]")
                k += 1
        elif st["bus"] == "ambience":
            # Ambience is glue and has to cover its whole span, so it loops. wind_open's
            # own card says it has no periodicity to seam on; the others are checked by
            # ear-substitute only, which is to say not at all - see the report.
            span = _amb_span(st, stems, total)
            looped = f"{work}/loop_{st['file']}"
            if not os.path.exists(looped):
                sh("ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", p,
                   "-t", f"{span:.2f}",
                   "-af", f"afade=t=in:st=0:d=1.0,afade=t=out:st={max(span - 1.5, 0):.2f}:d=1.5",
                   "-ar", "48000", "-ac", "2", looped)
            ins += ["-i", looped]
            filt.append(f"[{k}:a]adelay={int(st['at'] * 1000)}|"
                        f"{int(st['at'] * 1000)}[s{k}]")
            other_l.append(f"[s{k}]")
            k += 1
        else:
            ins += ["-i", p]
            ms = int(st["at"] * 1000)
            filt.append(f"[{k}:a]adelay={ms}|{ms},"
                        f"aresample=48000,aformat=channel_layouts=stereo[s{k}]")
            other_l.append(f"[s{k}]")
            if st["kind"] == "voice":
                filt.append(f"[{k}:a]adelay={ms}|{ms},aresample=48000,"
                            f"aformat=channel_layouts=stereo[key{k}]")
                key_l.append(f"[key{k}]")
                ins += ["-i", p]
                k += 1
            k += 1
    if not other_l and not score_l:
        raise SystemExit("nothing to mix")
    # THE SCORE BUS IS DUCKED OFF A DIALOGUE-ONLY KEY. craft/SOUND.md measured the
    # tempting shortcut - keying off the finished programme - and it ducks on explosions
    # and ignores quiet speech, which is precisely backwards. Two lines in 66.7s means
    # this duck is about 4 seconds long in total; it is here because a 5 dB dip under
    # five words is the difference between dialogue that sits in a film and dialogue
    # that sits on top of one.
    filt.append("".join(score_l) +
                (f"amix=inputs={len(score_l)}:duration=longest:normalize=0,"
                 if len(score_l) > 1 else "anull,") +
                "aresample=48000,aformat=channel_layouts=stereo[score]")
    if key_l:
        filt.append("".join(key_l) +
                    (f"amix=inputs={len(key_l)}:duration=longest:normalize=0,"
                     if len(key_l) > 1 else "anull,") +
                    "aresample=48000,aformat=channel_layouts=stereo,apad[vokey]")
        filt.append("[score][vokey]sidechaincompress=threshold=0.15:ratio=4:"
                    "attack=20:release=350:makeup=1:link=maximum[scored]")
    else:
        filt.append("[score]anull[scored]")
    filt.append("".join(other_l) + "[scored]" +
                f"amix=inputs={len(other_l) + 1}:duration=longest:normalize=0,"
                f"aresample=48000,aformat=channel_layouts=stereo,apad[premix]")
    raw = f"{work}/_premaster.wav"
    sh("ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(filt),
       "-map", "[premix]", "-c:a", "pcm_s24le", "-ar", "48000",
       "-t", f"{total:.2f}", raw)
    out = f"{d}/the_coat_sound_only.wav"
    dd = loudness(raw)
    ln = "loudnorm=I=-16:TP=-1.5:LRA=11"
    if dd:
        ln += (f":linear=true:measured_I={dd['input_i']}:measured_TP={dd['input_tp']}"
               f":measured_LRA={dd['input_lra']}:measured_thresh={dd['input_thresh']}")
    sh("ffmpeg", "-y", "-v", "error", "-i", raw, "-af",
       ln + ",alimiter=limit=0.891:level=disabled:attack=5:release=50",
       "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", out)
    mp3 = f"{d}/the_coat_sound_only.mp3"
    sh("ffmpeg", "-y", "-v", "error", "-i", out, "-b:a", "320k", mp3)
    m = loudness(out)
    print(f"\n>>> {out}")
    print(f"    {total:.2f}s, {len(other_l)} stems + {len(score_l)} score segments, "
          f"{m.get('input_i')} LUFS / {m.get('input_tp')} dBTP")
    print(f"    {mp3}")
    return 0


def _amb_span(st, stems, total):
    """An ambience bed runs until the next ambience bed starts, or to the end."""
    later = sorted(x["at"] for x in stems
                   if x["bus"] == "ambience" and x["at"] > st["at"] + 0.1)
    return round((later[0] if later else total) - st["at"], 2)

STAGES = {"plan": plan, "voice": voice, "sweep": sweep, "score": score, "sfx": sfx,
          "ltx": ltx, "survey": survey, "measure": measure, "asr": asr,
          "level": level, "mix": mix, "report": report}


def main():
    p = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("stage", choices=sorted(STAGES),
                   help="plan/report render nothing; the rest queue jobs on ComfyUI")
    p.add_argument("--n", type=int, default=70,
                   help="survey: how many existing LTX beds to analyse in full")
    p.add_argument("--keep", type=int, default=8,
                   help="survey: how many of the loudest beds to keep for the ASR pass")
    p.add_argument("--rep", type=float, default=None,
                   help="IndexTTS repetition_penalty override (house default 10.0; "
                        "craft/VOICE.md says drop to 2-4 if words are dropped)")
    a = p.parse_args()
    return STAGES[a.stage](a)


if __name__ == "__main__":
    sys.exit(main() or 0)
