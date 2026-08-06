#!/usr/bin/env python3
"""film_cut.py - the FINISHING room for THE COAT: cut, sound, poster, contact sheet.

WHY THIS EXISTS AND NOT `short.py --stage cut`
----------------------------------------------
It was tried first, and it cannot finish this film. Three measured reasons:

  1. It crashes before it starts. `cut()` clears its work directory with a bare
     `os.remove()` over `os.listdir()`, and this film's work directory contains a
     SUBDIRECTORY (`_work/picture`, left by the picture-cut pass). Receipt:
         IsADirectoryError: [Errno 21] Is a directory: .../the-coat/_work/picture

  2. Even patched past that it would ship a SILENT film. Its mix takes exactly two
     things - `{out}/voice/{beat}.mp3` and `{out}/music/{cue}_00001.mp3` - and BOTH
     directories for this film are empty. With no labels it falls through to
     `shutil.copy(vertical, final)`, i.e. picture with no audio at all, and reports
     success.

  3. It could not take this film's sound even if those directories were full. The
     authored track is 26 levelled stems under studio/samples/the_film_audio/ - a
     five-movement cello score, two IndexTTS lines, nineteen effects and four ambience
     beds, on five buses with a duck. short.py's STAGES dict has no SFX stage, no stem
     levelling and no ducking; its `music` list is compile.py's ORIGINAL cue set (an
     unmetered cue turned into 140 bpm), not the score that was written and rendered.

So the mix here is done with ffmpeg directly, and this docstring is the SAYING SO.
Picture slicing still goes through short.make_cut() so the grade and camera machinery
are byte-identical to the house pipeline; only the assembly and the sound are local.

WHAT CHANGED IN THE EDIT, and why (all of it is in EDL below, one `why` per shot)
--------------------------------------------------------------------------------
The rendered picture cut was 20 beats / 66.74s. This is 17 shots / ~52s of picture.
Three beats are DROPPED, nine are RE-SLICED to land on material the shipped slice
missed, and one pair is REORDERED. Every decision was made after looking at eight
frames from every source clip (sheets/src_g*.jpg) - not from the shot lines.

Stages, all idempotent:  picture -> audio -> mux -> sheets
"""
import argparse
import json
import os
import subprocess
import sys

H = os.path.expanduser("~")
sys.path.insert(0, f"{H}/shared/comfy-studio/scripts")
os.environ.setdefault("COMFY_ROOT", f"{H}/ComfyUI")
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

D = f"{H}/shared/comfy-studio/studio/samples/the_film"
FINAL = f"{D}/final"
CLIPS = f"{H}/ComfyUI/output/claude-generated/12-shorts/the-coat/clips"
AUD = f"{H}/shared/comfy-studio/studio/samples/the_film_audio"
STEMS = f"{AUD}/stems"
WORK = f"{FINAL}/work"
FONT = "/usr/share/fonts/google-noto-vf/NotoSerif[wght].ttf"

W, HGT, FPS = 1280, 704, 24
TITLE_LEN = 2.20          # black head card
TAIL_LEN = 1.60           # black tail after the last fade
FADE_OUT = 1.10           # picture fade at the end of the last shot

# ── grade repairs applied ON TOP of the beat's authored grade ───────────────────
#
# Act one renders at 5-11% mean luma and nothing in the film asked for night. The
# render pass measured it and left it; it is a COLOUR TIMING problem, which is an
# edit-room job, so it is fixed here rather than by re-rendering. Measured YAVG of
# the graded shot is printed by the `picture` stage so this is auditable.
LIFT_HARD = ",eq=gamma=1.85:brightness=0.055:contrast=0.98:saturation=1.25"
LIFT_SOFT = ",eq=gamma=1.30:brightness=0.020:saturation=1.10"

# ── THE EDIT DECISION LIST ─────────────────────────────────────────────────────
# beat  = 1-based beat number in terra_field_coat.json (its grade + clip come from there)
# at/len= slice out of the SOURCE clip, in seconds
# fx    = short.py camera move for this shot
# lift  = extra grade appended
EDL = [
    # ---- I. ISSUED --------------------------------------------------------------
    dict(beat=1, at=2.45, ln=2.60, fx=[], lift=LIFT_SOFT, act="I",
         label="hands pull the strap",
         why="SHIPPED SLICE WAS 0.60-2.40 AND CONTAINED NO HANDS. The clip is an empty "
             "courtyard to 1.6s, morphs through a pale mask-like face at 1.9s, and only "
             "from 2.4s onward is it the authored shot - two gloved hands pulling a strap "
             "across a crimson torso. The film's first image was the morph. Now it is the "
             "hands: she is being dressed by other people and we never see them."),
    dict(beat=2, at=1.20, ln=2.20, fx=["push"], lift=LIFT_SOFT, act="I",
         label="her face above the gorget",
         why="The clip is dead still for its whole 6s, so length buys nothing. Cut from "
             "2.60s to 2.20s and keep the push, which is the only motion in the shot."),
    dict(beat=3, at=3.40, ln=2.40, fx=[], lift=LIFT_HARD, act="I",
         label="the courtyard, banners",
         why="Was 4.20s of a near-black frame (measured 5-11% luma). Halved, moved late "
             "where the banners actually flap, and lifted hard so it is a dusk courtyard "
             "rather than an underexposed one."),
    dict(beat=4, at=2.60, ln=3.40, fx=[], lift=LIFT_SOFT, act="I",
         label="sent: she recedes into the snow",
         why="THE BIGGEST RECOVERY IN THE FILM. The render pass cut at 3.90s to stop her "
             "'collapsing to a distant figure at 4.2s'. Looked at, that collapse IS the "
             "shot: she walks away until she is a speck in a white field. At that size "
             "identity is not a risk, it is the point. Slice moved to 2.60-6.00."),
    dict(beat=5, at=0.50, ln=1.70, fx=[], lift=LIFT_HARD, act="I",
         label="the gauntlet in the snow",
         why="Kept short and lifted hard - the object morphs into something else after "
             "3.4s and was unreadable at the shipped level. Act one now ends on a "
             "discarded piece of armour, which act two will rhyme with."),
    # ---- II. DECIDED ------------------------------------------------------------
    # BEAT 6 (the hall establisher) IS DROPPED - see DROPPED below.
    dict(beat=7, at=0.40, ln=4.80, fx=[], lift="", act="II", silent=True,
         label="she stands in the empty hall",
         why="The best shot in the film and the authored silence; it now opens the act "
             "instead of following a wide of a different room with a man in a cardigan "
             "walking through it. Trimmed 5.50 -> 4.80 on the second watch: it carries no "
             "score (silence:true) and 5.5s of near-silence at the top of an act was "
             "0.7s more than the composition can hold."),
    dict(beat=8, at=0.30, ln=4.00, fx=[], lift="", act="II", voice=1, voice_at=0.60,
         label='"Nobody will say which half."',
         why="Extended from 3.20s to 4.00s so the shot reaches 4.3s in the clip, where "
             "her hand arrives at her mouth. The line now has a gesture to end on."),
    dict(beat=10, at=0.60, ln=2.60, fx=["push"], lift="", act="II",
         label="her fist closes on the table",
         why="MOVED BEFORE THE GLOVE. It is her answer to what was decided, so it belongs "
             "next to the line, not after an aftermath insert."),
    dict(beat=9, at=0.60, ln=1.90, fx=[], lift="", act="II",
         label="the white glove on the flagstones",
         why="MOVED TO THE END OF THE ACT. Act one ends on a dropped gauntlet; act two now "
             "ends on a dropped glove. Two movements, two pieces of somebody else's "
             "uniform left on the ground. The rhyme was already in the material and the "
             "original order threw it away."),
    # ---- III. THE ROAD ----------------------------------------------------------
    dict(beat=11, at=2.60, ln=3.40, fx=["handheld"], lift="", act="III",
         label="she walks out of frame",
         why="Shipped slice was 0.30-3.90 and she never left. She exits frame right "
             "between 4.2s and 5.7s. Slice moved to 2.60-6.00 so the act opens on a "
             "departure instead of a hold."),
    # BEAT 12 (the sash) IS DROPPED - see DROPPED below.
    dict(beat=13, at=2.10, ln=3.90, fx=["handheld"], lift="", act="III",
         label="the ford: she goes down and gets up",
         why="THE BUILD TEMPLATE WAS THROWING THIS AWAY. It chopped the clip into three "
             "snippets (1.4s/1.0s/0.7s) and cut at 4.90s - exactly where she pushes up off "
             "one hand and strides out of the water. Replaced with ONE continuous 3.90s "
             "take, 2.10-6.00, which is the only complete dramatic action in the film."),
    # BEAT 14 (the purse) IS DROPPED - see DROPPED below.
    dict(beat=15, at=0.60, ln=2.40, fx=["handheld"], lift="", act="III",
         label="what it cost",
         why="Trimmed 0.2s. A static close on her face with something gold held at her "
             "chest; it carries the act's ending on the face alone now that the two "
             "inserts around it are gone."),
    # ---- IV. CHOSEN -------------------------------------------------------------
    dict(beat=16, at=0.50, ln=3.90, fx=[], lift="", act="IV", voice=2, voice_at=0.90,
         label="the coat on the hook, and the town below it",
         why="TWO FIXES IN ONE SHOT. (a) The shipped 2.43s stopped at 3.03s and missed the "
             "camera tilting down at 3.4s to reveal the whole yellow border town - the "
             "establishing shot act four never had. (b) TERRA'S SECOND LINE IS MOVED HERE "
             "FROM BEAT 17. She is already wearing the coat in every frame of beat 17, so "
             "asking its price there was nonsense. Spoken over the coat on the hook, "
             "before we ever see it on her, the line does what it was written to do."),
    dict(beat=18, at=3.30, ln=2.70, fx=["push"], lift="", act="IV", silent=True,
         label="the sleeve, and a hand at the cuff",
         why="Shipped slice was 0.60-4.11 and was mostly the back of her head; the coat "
             "sleeve with a hand coming out of the cuff only exists from 3.30s. Now it is "
             "its own insert, and it sits between the question and her face."),
    dict(beat=17, at=0.40, ln=2.60, fx=[], lift="", act="IV",
         label="she has it",
         why="Cut from 4.32s to 2.60s and stripped of its line. It is the only shot in the "
             "film where she smiles, so it is now a reveal rather than a speech."),
    dict(beat=19, at=1.20, ln=2.20, fx=[], lift="", act="IV",
         label="the street",
         why="Cut from 4.86s to 2.20s. The render pass confirmed identity holds here for "
             "the full 8s, but she does not measurably approach the camera, so it is a "
             "held medium. On the second watch it was also the THIRD consecutive shot of "
             "her standing in the coat, so it is now a passing beat between her face and "
             "the last image rather than a third statement of the same fact."),
    dict(beat=20, at=0.70, ln=4.40, fx=[], lift="", act="IV", last=True,
         label="the coat, and nothing else moving",
         why="Cut from 7.42s to 4.40s. The coat billows open at ~1.0s and settles by 2.5s; "
             "everything after that was a still frame. 4.40s keeps the billow, the settle "
             "and enough stillness to end on, then fades."),
]

DROPPED = [
    (6, "ii_decided_the_hall_00",
     "A MAN IN A BEIGE CARDIGAN AND GLASSES WALKS THE FULL WIDTH OF THE FRAME, and he is "
     "in every one of the eight frames sampled across the clip - there is no clean window "
     "to slice. The film's stated premise is that we never see who decides; this shot "
     "shows a modern man crossing the room. It also establishes the WRONG ROOM: it is a "
     "warm timber hall with a gable roof, and beat 7 is a green gothic hall with pointed "
     "arches. Dropping it means act two opens by cutting from a gauntlet in the snow "
     "straight to her standing in a court gown, which is a better cut than the one it "
     "replaces."),
    (12, "iii_the_road_the_sash_00",
     "It is a dark curved band moving across a grey sky. It is not red, it is not cloth, "
     "and at no point in 6s does it read as a sash. 1.8s of unreadable abstraction between "
     "two shots that both work. The wear-ladder continuity it was carrying survives "
     "anyway: her forearms are visibly bandaged in the ford shot."),
    (14, "iii_the_road_the_purse_00",
     "A giant green-skinned open palm in the rain, which at 3.4s grows a second pink hand "
     "and a green coil over it. No purse ever drops. It reads as a monster's hand and it "
     "sat immediately before the film's emotional close-up."),
]

# ── SOUND ──────────────────────────────────────────────────────────────────────
# The stems are already levelled to their bus targets by film_audio.py (dialogue -20,
# hero -20, designed -24, ambience -28, score -26). Here they are only PLACED, trimmed,
# faded and ducked, then the sum is taken to delivery.
SFX_FOR_BEAT = {
    1: [("sfx__strap_pull.wav", 0.00, 1.00)],
    2: [("sfx__throat_buckle.wav", 0.10, 1.00)],
    3: [("sfx__banners.wav", 0.00, 1.00)],
    4: [("sfx__snow_steps.wav", 0.00, 1.00)],
    5: [("sfx__gauntlet_snow.wav", 0.00, 1.00)],
    10: [("sfx__fist_table.wav", 0.30, 1.00)],
    9: [("sfx__glove_stone.wav", 0.20, 1.00)],
    13: [("sfx__ford_water.wav", 0.00, 1.00)],
    15: [("sfx__purse_grip.wav", 0.30, 1.00)],
    16: [("sfx__coat_hook.wav", 0.10, 1.00)],
    18: [("sfx__sleeve.wav", 0.20, 1.00)],
    19: [("sfx__cobble_steps.wav", 0.00, 1.00)],
    20: [("sfx__coat_flap.wav", 0.40, 1.00)],
}

# AMBIENCE IS A SPAN, NOT A PER-SHOT EFFECT - and the first version of this mix got that
# wrong. Placing hall_tone and market_tone once per shot gave every bed its own 0.25s fade
# in and 0.6s fade out, so the room breathed in and out at EVERY CUT: seven retriggers
# across acts two and four. A bed belongs to a PLACE, and the place does not change when
# the camera does. Each span below is one continuous placement with one fade at each end.
#
# Every span is also shorter than its bed (the beds are 11.98s), so nothing has to loop
# and no loop seam can appear. hall_tone deliberately stops at the end of shot 08 rather
# than running to the end of the act: shot 09 is the glove on the flagstones, which is
# outdoors, and carrying interior room tone over it would put her back inside.
# (file, first shot index, last shot index, gain)
AMBIENCE = [
    ("sfx__hall_tone.wav", 5, 7, 1.00),      # shots 06-08: the court movement, interior
    ("sfx__moor_wind.wav", 9, 11, 1.00),     # shots 10-12: the whole road movement
    ("sfx__market_tone.wav", 12, 15, 1.00),  # shots 13-16: the border town
    ("sfx__moor_wind.wav", 16, 16, 0.75),    # shot 17: open ground again, quieter
]
SCORE_FOR_ACT = {"I": "score__coat_i_issued.wav", "II": "score__coat_ii_decided.wav",
                 "III": "score__coat_iii_road.wav", "IV": "score__coat_iv_market.wav"}
CODA = "score__coat_coda_moor.wav"
VOICE = {1: "voice__ii_decided_she_says_it_00.wav",
         2: "voice__iv_chosen_she_asks_00.wav"}
LINES = {1: "Nobody will say which half.", 2: "How much for the brown one."}
DUCK_DB = 5.0             # score under dialogue
TARGET_LUFS = -16.0
TARGET_TP = -1.5


def sh(*a, **kw):
    r = subprocess.run(a, capture_output=True, text=True, **kw)
    if r.returncode:
        raise RuntimeError(" ".join(a[:6]) + "\n" + r.stderr[-2500:])
    return r


def probe(p, entries="format=duration"):
    return subprocess.run(["ffprobe", "-v", "error", "-show_entries", entries,
                           "-of", "csv=p=0", p], capture_output=True,
                          text=True).stdout.strip()


def dur(p):
    return float(probe(p))


def yavg(p):
    """Mean luma of a video, 0-255, via signalstats. The act-one darkness check."""
    # the metadata filter prints at INFO level, so -v error silently returns nothing
    tmp = f"{WORK}/_yavg.txt"
    os.makedirs(WORK, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf",
                    f"signalstats,metadata=mode=print:key=lavfi.signalstats.YAVG:file={tmp}",
                    "-f", "null", "-"], capture_output=True, text=True)
    vals = [float(l.split("=")[1]) for l in open(tmp) if "YAVG=" in l]
    return sum(vals) / len(vals) if vals else -1.0


def timeline():
    """The one source of truth for where everything sits. Built from the REAL duration
    of every rendered piece, never from the requested length - the requested lengths
    accumulated ~0.35s of drift across the picture cut, which would put every sound
    effect in this film late by the end of act three."""
    film = json.load(open(f"{D}/terra_field_coat.json", encoding="utf-8"))
    beats = {i: b for i, b in enumerate(film["beats"], 1)}
    rows, t = [], TITLE_LEN
    for n, e in enumerate(EDL):
        p = f"{WORK}/pic/{n:02d}_b{e['beat']:02d}.mp4"
        ln = dur(p) if os.path.exists(p) else e["ln"]
        rows.append(dict(e, n=n, path=p, start=t, end=t + ln, real=ln,
                         bid=beats[e["beat"]]["id"]))
        t += ln
    return rows, t, beats


# ══ STAGE: picture ═════════════════════════════════════════════════════════════
def stage_picture():
    import short
    film = json.load(open(f"{D}/terra_field_coat.json", encoding="utf-8"))
    beats = {i: b for i, b in enumerate(film["beats"], 1)}
    os.makedirs(f"{WORK}/pic", exist_ok=True)
    print("=== PICTURE: slicing to the EDL ===")
    for n, e in enumerate(EDL):
        b = beats[e["beat"]]
        src = f"{CLIPS}/{b['id']}_00001_.mp4"
        dst = f"{WORK}/pic/{n:02d}_b{e['beat']:02d}.mp4"
        grade = (b.get("grade") or "") + e["lift"]
        short.make_cut(src, e["at"], e["ln"], e["fx"], dst, seed=n, grade=grade)
        print(f"  {n:02d} act{e['act']:<4s} beat{e['beat']:>3d} {e['at']:5.2f}+{e['ln']:4.2f}"
              f"  -> {dur(dst):4.2f}s  luma {yavg(dst):5.1f}  {e['label']}")
    rows, total, _ = timeline()
    print(f"  {len(rows)} shots, {total - TITLE_LEN:.2f}s of picture "
          f"(+{TITLE_LEN}s head, +{TAIL_LEN}s tail)")
    return rows, total


# ══ STAGE: audio ═══════════════════════════════════════════════════════════════
def _seg(src, seek, take, gain, at, fin, fout, tag, idx, filt, labels, ins):
    """One placed stem: trim -> fade -> gain -> delay. Everything is explicit so the
    graph can be read back off the report."""
    ins += ["-ss", f"{seek:.3f}", "-t", f"{take:.3f}", "-i", src]
    ms = int(round(at * 1000))
    f = (f"[{idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
         f"afade=t=in:st=0:d={fin:.2f},"
         f"afade=t=out:st={max(0.0, take - fout):.2f}:d={fout:.2f},"
         f"volume={gain:.4f}")
    if ms > 0:
        f += f",adelay={ms}|{ms}"
    f += f"[{tag}]"
    filt.append(f)
    labels.append(f"[{tag}]")


def stage_audio():
    rows, total, _ = timeline()
    film_end = total + TAIL_LEN
    os.makedirs(f"{WORK}/aud", exist_ok=True)
    ins, filt, labels, idx = [], [], [], 0
    placed = []

    # --- score: one movement per act, with the two authored holes -----------------
    acts = {}
    for r in rows:
        a = acts.setdefault(r["act"], [r["start"], r["end"]])
        a[1] = r["end"]
    acts["I"][0] = 0.0                       # the head card is scored
    # the coda takes over on the last shot
    last = [r for r in rows if r.get("last")][0]
    acts["IV"][1] = last["start"]
    cues = [(SCORE_FOR_ACT[a], acts[a][0], acts[a][1]) for a in ("I", "II", "III", "IV")]
    cues.append((CODA, last["start"], film_end - 0.3))
    holes = [(r["start"], r["end"]) for r in rows if r.get("silent")]
    for f_, s, e in cues:
        spans = [(s, e)]
        for hs, he in holes:                  # subtract every authored silence
            nxt = []
            for a, b in spans:
                if he <= a or hs >= b:
                    nxt.append((a, b))
                else:
                    if a < hs:
                        nxt.append((a, hs))
                    if he < b:
                        nxt.append((he, b))
            spans = nxt
        for si, (a, b) in enumerate(spans):
            if b - a < 0.5:
                continue
            _seg(f"{STEMS}/{f_}", a - s, b - a, 1.0, a, 0.6, 0.9,
                 f"sc{idx}", idx, filt, labels, ins)
            placed.append(("score", f_, round(a, 2), round(b - a, 2), 1.0))
            idx += 1

    # --- ambience: one continuous bed per place -----------------------------------
    for name, a, b, g in AMBIENCE:
        src = f"{STEMS}/{name}"
        st, en = rows[a]["start"], rows[b]["end"]
        take = min(en - st + 0.5, dur(src))
        _seg(src, 0.0, take, g, st, 0.8, 1.2, f"am{idx}", idx, filt, labels, ins)
        placed.append(("ambience", name, round(st, 2), round(take, 2), g))
        idx += 1

    # --- effects: per shot --------------------------------------------------------
    for r in rows:
        for name, off, g in SFX_FOR_BEAT.get(r["beat"], []):
            src = f"{STEMS}/{name}"
            sl = dur(src)
            take = min(r["real"] - off + 0.45, sl)
            if take < 0.3:
                continue
            _seg(src, 0.0, take, g, r["start"] + off, 0.25, min(0.6, take / 2),
                 f"fx{idx}", idx, filt, labels, ins)
            placed.append((name.split("__")[0], name, round(r["start"] + off, 2),
                           round(take, 2), g))
            idx += 1

    # --- dialogue -----------------------------------------------------------------
    vcues = []
    for r in rows:
        if not r.get("voice"):
            continue
        src = f"{STEMS}/{VOICE[r['voice']]}"
        at = r["start"] + r["voice_at"]
        vd = dur(src)
        _seg(src, 0.0, vd, 1.0, at, 0.02, 0.05, f"vo{idx}", idx, filt, labels, ins)
        placed.append(("voice", VOICE[r["voice"]], round(at, 2), round(vd, 2), 1.0))
        vcues.append((at, vd, LINES[r["voice"]]))
        idx += 1

    # --- duck the score under the two lines ---------------------------------------
    # 26 stems is past the point where a sidechain per pair is readable, and the key is
    # only 4.5s of the film. A gain envelope on the summed score is the same result and
    # can be checked by eye in the report.
    mix = "".join(labels) + f"amix=inputs={len(labels)}:duration=longest:normalize=0"
    duck = 10 ** (-DUCK_DB / 20.0)
    for at, vd, _ in vcues:
        mix += (f",volume=enable='between(t,{at - 0.35:.2f},{at + vd + 0.5:.2f})'"
                f":volume={duck:.3f}")
    mix += ",apad[mix]"
    filt.append(mix)
    raw = f"{WORK}/aud/_raw.wav"
    sh("ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(filt),
       "-map", "[mix]", "-c:a", "pcm_s24le", "-ar", "48000", "-t", f"{film_end:.3f}", raw)

    # --- delivery: two-pass loudnorm, then a true-peak limiter --------------------
    m = _ln_json(raw)
    mixf = f"{FINAL}/the_coat_mix.wav"
    sh("ffmpeg", "-y", "-v", "error", "-i", raw, "-af",
       ("loudnorm=I=%.1f:TP=%.1f:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:"
        "measured_thresh=%s:linear=true:print_format=summary,"
        # the limiter sits 0.5 dB BELOW the true-peak target: at exactly -1.5 the
        # delivered master measured -1.42 dBTP, i.e. inter-sample peaks past the ceiling
        "alimiter=limit=%.4f:level=disabled"
        % (TARGET_LUFS, TARGET_TP, m["input_i"], m["input_tp"], m["input_lra"],
           m["input_thresh"], 10 ** ((TARGET_TP - 0.5) / 20.0))),
       "-c:a", "pcm_s24le", "-ar", "48000", mixf)
    out = _ln_json(mixf)
    json.dump(dict(placed=placed, cues=[(a, d, t) for a, d, t in vcues],
                   film_end=film_end, measured=out),
              open(f"{FINAL}/mix_report.json", "w"), indent=1)
    print("=== AUDIO ===")
    print(f"  {len(labels)} placed stems -> {mixf}")
    print(f"  {out['input_i']} LUFS / {out['input_tp']} dBTP / LRA {out['input_lra']}"
          f"  over {dur(mixf):.2f}s")
    return mixf


def _ln_json(p):
    # loudnorm's JSON block prints at INFO level - `-v error` swallows it entirely
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", p, "-af",
                        "loudnorm=I=%.1f:TP=%.1f:LRA=11:print_format=json"
                        % (TARGET_LUFS, TARGET_TP), "-f", "null", "-"],
                       capture_output=True, text=True)
    s = r.stderr + r.stdout
    return json.loads(s[s.rindex("{"):s.rindex("}") + 1])


# ══ STAGE: mux ═════════════════════════════════════════════════════════════════
def ffesc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’")


def stage_mux():
    rows, total, _ = timeline()
    film_end = total + TAIL_LEN
    os.makedirs(f"{WORK}/mux", exist_ok=True)
    # head and tail black, generated at the exact codec params so concat -c copy works
    for name, ln in (("head", TITLE_LEN), ("tail", TAIL_LEN)):
        sh("ffmpeg", "-y", "-v", "error", "-f", "lavfi",
           "-i", f"color=c=black:s={W}x{HGT}:r={FPS}:d={ln:.3f}",
           "-vf", "format=yuv420p", "-c:v", "libx264", "-crf", "16",
           "-preset", "veryfast", f"{WORK}/mux/_{name}.mp4")
    lst = f"{WORK}/mux/list.txt"
    with open(lst, "w", encoding="utf-8") as f:
        f.write(f"file '{WORK}/mux/_head.mp4'\n")
        for r in rows:
            f.write(f"file '{r['path']}'\n")
        f.write(f"file '{WORK}/mux/_tail.mp4'\n")
    joined = f"{WORK}/mux/_joined.mp4"
    sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
       "-c", "copy", joined)

    # title, subtitles, tail fade. No caption boxes: this film has 11 words in it and a
    # black-boxed caption band under every shot would be louder than the film.
    ff = f"fontfile='{FONT}':"
    vf = [f"drawtext={ff}text='THE COAT':fontcolor=white@0.92:fontsize=76:"
          f"x=(w-text_w)/2:y=(h-text_h)/2-10:"
          f"alpha='if(lt(t,0.45),t/0.45,if(lt(t,{TITLE_LEN - 0.55:.2f}),1,"
          f"max(0,({TITLE_LEN:.2f}-t)/0.55)))':enable='lt(t,{TITLE_LEN:.2f})'"]
    rep = json.load(open(f"{FINAL}/mix_report.json", encoding="utf-8"))
    for at, vd, txt in rep["cues"]:
        # No caption box. 38px with a real outline instead of a drop shadow: at 34px
        # over the market street the shadow alone lost the line against the bunting.
        vf.append(f"drawtext={ff}text='{ffesc(txt)}':fontcolor=white:fontsize=38:"
                  f"borderw=2:bordercolor=black@0.75:"
                  f"x=(w-text_w)/2:y=h*0.845:shadowcolor=black@0.6:shadowx=2:shadowy=2:"
                  f"enable='between(t,{at - 0.10:.2f},{at + vd + 0.55:.2f})'")
    vf.append(f"fade=t=out:st={total - FADE_OUT:.2f}:d={FADE_OUT:.2f}")
    picture = f"{WORK}/mux/_picture.mp4"
    sh("ffmpeg", "-y", "-v", "error", "-i", joined, "-vf", ",".join(vf),
       "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
       "-an", picture)

    final = f"{FINAL}/THE_COAT.mp4"
    sh("ffmpeg", "-y", "-v", "error", "-i", picture, "-i", f"{FINAL}/the_coat_mix.wav",
       "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
       "-shortest", "-movflags", "+faststart", final)
    va = dur(final)
    aa = float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                               "-show_entries", "stream=duration", "-of", "csv=p=0", final],
                              capture_output=True, text=True).stdout.strip() or 0)
    print("=== MUX ===")
    print(f"  {final}\n  {va:.2f}s picture / {aa:.2f}s audio / {len(rows)} shots")
    if abs(va - aa) > 0.5:
        print("  !! audio does not cover the picture", file=sys.stderr)
    return final


# ══ STAGE: sheets ══════════════════════════════════════════════════════════════
def stage_sheets():
    from PIL import Image, ImageDraw, ImageFont
    rows, total, _ = timeline()
    final = f"{FINAL}/THE_COAT.mp4"
    os.makedirs(f"{WORK}/sheet", exist_ok=True)

    def grab(ts, dst, w=640):
        sh("ffmpeg", "-y", "-v", "error", "-ss", f"{ts:.3f}", "-i", final,
           "-frames:v", "1", "-vf", f"scale={w}:-2", "-q:v", "2", dst)

    def load(p):
        try:
            return ImageFont.truetype(p, 20), ImageFont.truetype(p, 30)
        except OSError:
            return ImageFont.load_default(), ImageFont.load_default()
    fs, fb = load(FONT)

    # --- contact sheet: one cell per shot ----------------------------------------
    cw, chh, pad, cols = 480, 264, 58, 4
    n = len(rows)
    rowsn = (n + cols - 1) // cols
    top = 96
    img = Image.new("RGB", (cw * cols, top + rowsn * (chh + pad)), (14, 14, 16))
    d = ImageDraw.Draw(img)
    d.text((22, 24), "THE COAT", fill=(240, 236, 226), font=fb)
    d.text((24, 62), f"{n} shots  /  {total + TAIL_LEN:.1f}s  /  4 movements  "
                     f"/  cel_anime_90s  /  TERRA", fill=(150, 150, 158), font=fs)
    for i, r in enumerate(rows):
        f = f"{WORK}/sheet/cell_{i:02d}.jpg"
        grab(r["start"] + r["real"] * 0.45, f, cw)
        cx, cy = (i % cols) * cw, top + (i // cols) * (chh + pad)
        img.paste(Image.open(f).convert("RGB").resize((cw, chh)), (cx, cy))
        d.rectangle([cx, cy + chh, cx + cw, cy + chh + pad], fill=(14, 14, 16))
        d.text((cx + 8, cy + chh + 4),
               f"{i + 1:02d}  {r['act']}   {r['start']:5.1f}s  {r['real']:.1f}s",
               fill=(226, 190, 110), font=fs)
        d.text((cx + 8, cy + chh + 24), r["label"][:52], fill=(160, 162, 170), font=fs)
    img.save(f"{FINAL}/THE_COAT_contact_sheet.jpg", quality=90)
    print(f"  contact sheet -> {FINAL}/THE_COAT_contact_sheet.jpg  {img.size}")

    # --- poster candidates, then the poster --------------------------------------
    cands = []
    for r in rows:
        for fr in (0.25, 0.5, 0.75):
            p = f"{WORK}/sheet/pc_{r['n']:02d}_{int(fr * 100)}.jpg"
            grab(r["start"] + r["real"] * fr, p, 640)
            cands.append((r["n"], fr, p))
    W2, H2 = 320, 176
    g = Image.new("RGB", (W2 * 6, ((len(cands) + 5) // 6) * (H2 + 18)), (14, 14, 16))
    dd = ImageDraw.Draw(g)
    for i, (bn, fr, p) in enumerate(cands):
        x, y = (i % 6) * W2, (i // 6) * (H2 + 18)
        g.paste(Image.open(p).convert("RGB").resize((W2, H2)), (x, y + 18))
        dd.text((x + 4, y + 2), f"shot{bn + 1:02d} @{fr:.2f}", fill=(226, 190, 110), font=fs)
    g.save(f"{FINAL}/poster_candidates.jpg", quality=88)
    print(f"  poster candidates -> {FINAL}/poster_candidates.jpg")

    # --- watch strips: 4 frames per shot -----------------------------------------
    for gi in range(0, len(rows), 5):
        sel = rows[gi:gi + 5]
        W3, H3, p3 = 480, 264, 26
        im = Image.new("RGB", (W3 * 4, (H3 + p3) * len(sel)), (18, 18, 18))
        dr = ImageDraw.Draw(im)
        for j, r in enumerate(sel):
            for c, fr in enumerate((0.08, 0.36, 0.64, 0.92)):
                p = f"{WORK}/sheet/st_{r['n']:02d}_{c}.jpg"
                grab(r["start"] + r["real"] * fr, p, W3)
                im.paste(Image.open(p).convert("RGB").resize((W3, H3)),
                         (c * W3, j * (H3 + p3) + p3))
            dr.text((6, j * (H3 + p3) + 5),
                    f"{r['n'] + 1:02d} act{r['act']} beat{r['beat']} "
                    f"{r['start']:.2f}-{r['end']:.2f}s  {r['label']}",
                    fill=(255, 220, 120), font=fs)
        im.save(f"{FINAL}/sheets_watch_{gi // 5 + 1}.jpg", quality=88)
    print(f"  watch strips -> {FINAL}/sheets_watch_*.jpg")


def stage_poster(shot, frac):
    rows, _, _ = timeline()
    r = [x for x in rows if x["n"] == shot][0]
    ts = r["start"] + r["real"] * frac
    sh("ffmpeg", "-y", "-v", "error", "-ss", f"{ts:.3f}", "-i", f"{FINAL}/THE_COAT.mp4",
       "-frames:v", "1", "-vf", "scale=1920:-2:flags=lanczos", "-q:v", "2",
       f"{FINAL}/THE_COAT_poster.jpg")
    print(f"  poster from shot {shot + 1} @ {ts:.2f}s -> {FINAL}/THE_COAT_poster.jpg")


def stage_report():
    rows, total, beats = timeline()
    rep = json.load(open(f"{FINAL}/mix_report.json", encoding="utf-8"))
    L = []
    L.append("THE COAT - final cut\n")
    L.append(f"{len(rows)} shots, {total + TAIL_LEN:.2f}s "
             f"(from 20 beats / 66.74s of rendered picture)\n")
    L.append("SHOT LIST")
    for r in rows:
        L.append(f"  {r['n'] + 1:02d}  {r['act']:<3s} beat{r['beat']:>3d}  "
                 f"{r['start']:6.2f}-{r['end']:6.2f}  ({r['real']:4.2f}s)  "
                 f"src {r['at']:.2f}+{r['ln']:.2f}  {r['label']}")
        L.append(f"      why: {r['why']}")
    L.append("\nDROPPED")
    for n, bid, why in DROPPED:
        L.append(f"  beat {n} {bid}\n      {why}")
    L.append("\nSOUND (placed stems)")
    for kind, name, at, ln, g in rep["placed"]:
        L.append(f"  {kind:9s} {at:6.2f}s +{ln:5.2f}s  x{g:.2f}  {name}")
    L.append(f"\nMASTER  {rep['measured']['input_i']} LUFS  "
             f"{rep['measured']['input_tp']} dBTP  LRA {rep['measured']['input_lra']}")
    open(f"{FINAL}/CUT_REPORT.txt", "w", encoding="utf-8").write("\n".join(L))
    print(f"  report -> {FINAL}/CUT_REPORT.txt")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", default="all",
                    choices=["all", "picture", "audio", "mux", "sheets", "poster",
                             "report", "plan"])
    ap.add_argument("--poster-shot", type=int, default=16)   # 0-based: the last shot
    ap.add_argument("--poster-frac", type=float, default=0.50)
    a = ap.parse_args()
    os.makedirs(FINAL, exist_ok=True)
    if a.stage == "plan":
        rows, total, _ = timeline()
        for r in rows:
            print(f"{r['n'] + 1:02d} {r['act']:<3s} beat{r['beat']:>3d} "
                  f"{r['start']:6.2f}-{r['end']:6.2f} {r['label']}")
        print(f"total {total + TAIL_LEN:.2f}s")
        return
    if a.stage in ("all", "picture"):
        stage_picture()
    if a.stage in ("all", "audio"):
        stage_audio()
    if a.stage in ("all", "mux"):
        stage_mux()
    if a.stage in ("all", "sheets"):
        stage_sheets()
    if a.stage in ("all", "poster"):
        stage_poster(a.poster_shot, a.poster_frac)
    if a.stage in ("all", "report"):
        stage_report()


if __name__ == "__main__":
    main()
