#!/usr/bin/env python3
"""scripts/sound_dept.py - the ONE sound department (ARCHITECTURE Phase 6, task 47).

film_cut.py's docstring is the requirements list, written after short.py could not
finish THE COAT: no SFX stage, no stem levelling, no ducking. epic.py then built all
three inline for the episodes. This module is that proven machinery made shared:

    import sound_dept
    sound_dept.render_sfx(film, out, seed0)                 # the missing stage
    sound_dept.mix_master(work, vertical, total,
                          voices, musics, sfxs, final, slam) # levelled + ducked

Stems are NORMALISED to per-bus targets before any level trim (ACE-Step spreads >20 LU
between takes; Stable Audio arrived 20 dB apart between a bang and a footstep), and
everything that is not speech DUCKS under speech by sidechain - effects duck harder and
sooner than score, because a pad under a word is a mix choice and a door slam under a
word is a mistake. Mastering stays two-pass (measure, then apply): single-pass loudnorm
inside a filter_complex works blind and missed its target by 7 LU when it was tried.

epic.py still carries its inline copy - it is mid-run on the episode renders (task 55)
and stays untouched until they finish; folding it onto this module is the declared tail.
"""
import os
import subprocess
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)

VOICE_LUFS = -20.0
MUSIC_LUFS = -26.0
SFX_LUFS = -30.0
# The impact a hit is built around. Loud, and never ducked: ordinary SFX
# step aside for dialogue and should, but the one sound the cut exists for
# does not. Measured need - a quiet score cannot make a moment on its own.
HIT_SFX_LUFS = -19.0
# threshold, ratio - keyed off the dialogue bus
DUCK = {"mus": (0.15, 4), "sfx": (0.10, 8)}


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def adur(path):
    r = sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=nw=1:nk=1", path)
    try:
        return float((r.stdout or "").strip())
    except ValueError:
        return 0.0


def render_sfx(film, out, seed0):
    """Render every beat's named effect through 10_stableaudio_sfx - the stage
    short.py never had. A beat asks with {"sfx": "a heavy door slam", "sfx_at": 0.4,
    "sfx_secs": 2.0}; the text gets the standard no-music/no-speech guard."""
    from epic import load_wf, HOST
    from comfy import run, set_path
    want = [b for b in film["beats"] if b.get("sfx")]
    if not want:
        print("  no beats name an effect")
        return 0
    os.makedirs(f"{out}/sfx", exist_ok=True)
    made = 0
    for i, b in enumerate(want):
        dst = f"{out}/sfx/{b['id']}_00001.mp3"
        if os.path.exists(dst):
            print(f"  {b['id']:20s} exists")
            continue
        wf = load_wf("10_stableaudio_sfx.json")
        set_path(wf, "3.inputs.text", b["sfx"] + ", no music, no speech")
        # Measured node map for 10_stableaudio_sfx: 5=EmptyLatentAudio(seconds),
        # 6=KSampler(seed), 8=SaveAudioMP3(filename_prefix). The first draft guessed
        # 3/4/7 and rendered 30-second defaults - the dial law: set what the node HAS.
        set_path(wf, "5.inputs.seconds", float(b.get("sfx_secs", 2.0)))
        set_path(wf, "6.inputs.seed", seed0 + i)
        set_path(wf, "8.inputs.filename_prefix", f"claude-generated/sfx/{b['id']}")
        try:
            _, outs = run(HOST, wf, quiet=True)
        except TypeError:
            outs = run(HOST, wf)[-1]
        src = None
        for o in (outs or []):
            # run() returns paths RELATIVE to ComfyUI/output
            if str(o).endswith((".mp3", ".flac", ".wav")):
                from epic import COMFY
                src = os.path.join(COMFY, "output", str(o))
        if src and os.path.exists(src):
            import shutil
            shutil.copy(src, dst)
            made += 1
            print(f"  {b['id']:20s} ok  {adur(dst):.1f}s")
        else:
            print(f"  {b['id']:20s} FAILED", file=sys.stderr)
    return made


def _bus(work, tag, items, target, total):
    """Normalise each item to the bus target, lay at its timestamp, amix into one
    stem. items: [(at_seconds, level, path)]. Returns the stem path or None."""
    from epic import norm_to
    ins, filt, labels = [], [], []
    k = 0
    for at, level, p in items:
        if not os.path.exists(p):
            continue
        np_ = f"{work}/_{tag}{k}.wav"
        try:
            norm_to(p, np_, target, tp=-3.0)
        except Exception:
            np_ = p
        ins += ["-i", np_]
        ms = int(float(at) * 1000)
        filt.append(f"[{k}:a]volume={float(level):.3f},adelay={ms}|{ms}[x{k}]")
        labels.append(f"[x{k}]")
        k += 1
    if not labels:
        return None
    stem = f"{work}/_bus_{tag}.wav"
    filt.append("".join(labels)
                + f"amix=inputs={len(labels)}:duration=longest:normalize=0,"
                  f"apad=whole_dur={total:.2f}[a]")
    sh("ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(filt),
       "-map", "[a]", "-ar", "48000", "-ac", "2", "-t", f"{total:.2f}", stem)
    return stem if os.path.exists(stem) else None


# The duck value that reproduces the mix this module shipped before soundscapes were
# wired. It is the MEDIAN non-zero duck across the eight cards, not a preference:
# 0.5 0.6 0.6 0.6 0.7 0.7 0.8 -> 0.6. So a card at 0.6 changes nothing and every other
# card scales against a real anchor.
DUCK_ANCHOR = 0.6


def _scape_levels(scape):
    """(music_lufs_offset_db, duck_scale) from a soundscape card, or the no-op pair.

    Returns None for the music offset when the card asks for no score at all, which the
    caller turns into "drop the bus" rather than "drive it to -inf".
    """
    import math
    if not scape:
        return 0.0, 1.0
    lvl = scape.get("music_level")
    if lvl is None:
        off = 0.0
    elif float(lvl) <= 0:
        off = None
    else:
        off = 20.0 * math.log10(float(lvl))
    d = scape.get("duck")
    scale = 1.0 if d is None else (float(d) / DUCK_ANCHOR)
    return off, scale


# The shape of one hit, in seconds around it and gain multipliers.
# BUILD_IN  how long the climb lasts        BUILD_TO  where it climbs to
# BREATH    how long the drop before it     BREATH_TO how far it drops
# HIT_TO    the gain on the frame           HIT_DECAY how long it takes to settle
BUILD_IN, BUILD_TO = 1.60, 1.38
BREATH, BREATH_TO = 0.35, 0.16
HIT_TO, HIT_DECAY = 1.30, 1.40


def hit_curve(hits, total):
    """One ffmpeg `volume` fragment per hit; identity outside its own window.

    A hit is only big if the moment before it is small, so the drop is not decoration -
    it is the mechanism. Gains are relative to the bus's own level, which the mastering
    pass then normalises, so this shapes the score without changing how loud the film is.
    """
    out = []
    for T in sorted(float(h) for h in hits or []):
        if T <= 0 or T >= total:
            continue
        a = max(0.0, T - BUILD_IN)          # climb starts
        b = max(0.0, T - BREATH)            # climb ends, breath starts
        c = min(total, T + HIT_DECAY)       # settled again
        if b <= a:
            continue
        # THE HIT WINDOW IS TESTED FIRST. between() is inclusive at both ends, so a
        # breath window ending at T is true AT T - tested first it returned 0.16 on the
        # very frame the hit lands, and the score would have stayed dropped through the
        # cut. Order is the whole fix.
        expr = (
            "if(between(t,{T},{c}), {hit}-{fall}*(t-{T})/{decay},"
            "if(between(t,{b},{T}), {breath},"
            "if(between(t,{a},{b}), 1+{gain}*(t-{a})/{span}, 1)))"
        ).format(a="%.3f" % a, b="%.3f" % b, T="%.3f" % T, c="%.3f" % c,
                 gain="%.3f" % (BUILD_TO - 1.0), span="%.3f" % (b - a),
                 breath="%.3f" % BREATH_TO, hit="%.3f" % HIT_TO,
                 fall="%.3f" % (HIT_TO - 1.0), decay="%.3f" % max(c - T, 0.01))
        out.append("volume=eval=frame:volume='%s'" % expr)
    return out


# A smash transition's dip. Shorter and shallower than a hit's breath on purpose - a
# smash is punctuation between two shots, a hit is the film's moment, and if they wore
# the same shape the hit would stop reading as special.
DROP_LEAD, DROP_HOLD, DROP_BACK = 0.10, 0.55, 0.35


def drop_curve(drops, total):
    """One `volume` fragment per smash boundary; identity outside its own window.

    `audio_drop` is read as a TARGET - 0.4 means fall to 40% of level, not by 40%. A
    transition whose entire effect is contrast wants the bigger reading, and it is what
    makes the cut audible rather than merely labelled.
    """
    out = []
    for at, depth in sorted((float(a), float(d)) for a, d in (drops or [])):
        depth = max(0.0, min(1.0, depth))
        if at <= 0 or at >= total or depth >= 1.0:
            continue
        a = max(0.0, at - DROP_LEAD)
        b = min(total, at + DROP_HOLD)
        c = min(total, b + DROP_BACK)
        if b <= a:
            continue
        # the dip is tested before the recovery for the same inclusive-between reason
        # the hit window is tested first
        expr = ("if(between(t,{a},{b}), {depth},"
                "if(between(t,{b},{c}), {depth}+{span}*(t-{b})/{back}, 1))"
                ).format(a="%.3f" % a, b="%.3f" % b, c="%.3f" % c,
                         depth="%.3f" % depth, span="%.3f" % (1.0 - depth),
                         back="%.3f" % max(c - b, 0.01))
        out.append("volume=eval=frame:volume='%s'" % expr)
    return out


def mix_master(work, vertical, total, voices, musics, sfxs, final, slam,
               scape=None, hits=None, drops=None, hit_sfx=None):
    """Three levelled buses, score and effects sidechain-ducked under dialogue, mixed,
    two-pass mastered, muxed under the finished picture.

    voices: [(at, path)] - normalised to VOICE_LUFS, played whole (L-cuts happen by
    moving `at`, exactly as before). musics/sfxs: [(at, level, path)].
    Returns final on success, None when every bus is empty (the caller decides whether
    silence was DECLARED - this module never ships it silently)."""
    # A soundscape card, when the film names one, moves the score level and the ducking.
    # Everything else about this mix is unchanged, and a film with no soundscape takes
    # the same path it always did.
    mus_off, duck_scale = _scape_levels(scape)
    if scape:
        print(f"    soundscape {scape.get('id', '?')}: "
              + ("score off" if mus_off is None else f"score {mus_off:+.1f} dB")
              + f", duck x{duck_scale:.2f}")
    vbus = _bus(work, "voice", [(at, 1.0, p) for at, p in voices], VOICE_LUFS, total)
    mbus = (None if mus_off is None
            else _bus(work, "mus", musics, MUSIC_LUFS + mus_off, total))
    # THE SCORE GETS A SHAPE. Without this it is a bed at a fixed gain and the film has
    # no moment - measured across 23 delivered films, build ratio x1.03 and not one
    # climax on a cut. Applied to the score only: the dialogue must not swell, and the
    # impact that lands on the frame rides the SFX bus.
    # THE CURVE IS APPLIED LATER, IN THE GRAPH, AFTER THE DUCK. Shaping the bus file
    # here put the swell in front of the sidechain compressor, whose entire job is to
    # remove level differences - it flattened the hit on every film whose score is
    # quieter than its dialogue. Measured: three films moved by nothing at all while the
    # log cheerfully reported "score shaped".
    curve = hit_curve(hits, total) + drop_curve(drops, total)
    if curve:
        print(f"    score shaped after ducking: {len(hit_curve(hits, total))} hit(s) "
              f"(build x{BUILD_TO:.2f}, breath x{BREATH_TO:.2f}, hit x{HIT_TO:.2f}), "
              f"{len(drop_curve(drops, total))} smash dip(s)")
    sbus = _bus(work, "sfx", sfxs, SFX_LUFS, total)
    # The impact bus. Louder than ordinary effects and deliberately absent from the
    # ducking below - see HIT_SFX_LUFS.
    hbus = _bus(work, "hit", hit_sfx, HIT_SFX_LUFS, total) if hit_sfx else None
    if not any((vbus, mbus, sbus, hbus)):
        return None

    ins, filt, mix_labels = [], [], []
    idx = {}
    for name, p in (("voice", vbus), ("mus", mbus), ("sfx", sbus), ("hit", hbus)):
        if p:
            idx[name] = len(ins) // 2
            ins += ["-i", p]
    if vbus:
        # one sidechain key per ducked bus, plus the copy that gets mixed
        # `hit` is NOT keyed - it never ducks - so it is not counted here.
        need = sum(1 for b in ("mus", "sfx") if idx.get(b) is not None)
        filt.append(f"[{idx['voice']}:a]asplit={need + 1}"
                    + "".join(f"[k{b}]" for b in ("mus", "sfx") if b in idx)
                    + "[vmix]")
        mix_labels.append("[vmix]")
        for b in ("mus", "sfx"):
            if b in idx:
                thr, ratio = DUCK[b]
                # duck 0 on the card means "do not duck at all", so the sidechain is
                # bypassed rather than given ratio 1, which is not the same filter.
                if duck_scale <= 0:
                    if b == "mus" and curve:
                        filt.append(f"[{idx[b]}:a]{','.join(curve)}[dmusnd]")
                        mix_labels.append("[dmusnd]")
                    else:
                        mix_labels.append(f"[{idx[b]}:a]")
                    continue
                ratio = max(1.5, min(20.0, ratio * duck_scale))
                tail = f"[d{b}]" if not (b == "mus" and curve) else f"[d{b}pre]"
                filt.append(f"[{idx[b]}:a][k{b}]sidechaincompress=threshold={thr}:"
                            f"ratio={ratio}:attack=20:release=400{tail}")
                if b == "mus" and curve:
                    # the shape goes on LAST so the compressor cannot undo it
                    filt.append(f"[d{b}pre]{','.join(curve)}[d{b}]")
                mix_labels.append(f"[d{b}]")
    else:
        for b in ("mus", "sfx"):
            if b in idx:
                if b == "mus" and curve:
                    filt.append(f"[{idx[b]}:a]{','.join(curve)}[dmus]")
                    mix_labels.append("[dmus]")
                else:
                    mix_labels.append(f"[{idx[b]}:a]")

    # Straight to the mix, past every duck. This is the point of it.
    if "hit" in idx:
        mix_labels.append(f"[{idx['hit']}:a]")
    raw = f"{work}/_mix_raw.wav"
    filt.append("".join(mix_labels)
                + f"amix=inputs={len(mix_labels)}:duration=longest:normalize=0,"
                  f"apad[mix]")
    sh("ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(filt),
       "-map", "[mix]", "-c:a", "pcm_s24le", "-ar", "48000", "-t", f"{total:.2f}", raw)

    mastered = f"{work}/_mix_master.wav"
    slam(raw, mastered)

    sh("ffmpeg", "-y", "-v", "error", "-i", vertical, "-i", mastered,
       "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
       "-t", f"{total:.2f}", "-movflags", "+faststart", final)
    return final if os.path.exists(final) else None
