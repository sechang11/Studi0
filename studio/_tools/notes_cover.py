#!/usr/bin/env python3
"""studio/_tools/notes_cover.py - a cover made from a song's NOTES, not from its sound (2026-10-05).

Five rounds of ACE-Step covers of TerraTheme (score casting r1-r5) re-coloured the recording itself: its latent
half-erased and repainted with the new instruments, so every sample was half the old orchestra and half a new
piano - the director: "the remixes do not sound good". Erase further and the tune goes. The same cover engine
sounded fine on the duel's music because that source was the model's own clean take. So this tool takes the
song's notes out of the recording and plays them again:

  prepare SONG SOURCE   split the recording into stems (Hybrid Demucs - torchaudio's HDEMUCS_HIGH_MUSDB_PLUS, on
                        the GPU in 10 s chunks, under a memory cap), transcribe the instrument and bass stems
                        (Spotify's Basic Pitch, ONNX), write the LEAD SHEET (the beat grid, bar lines from the bass,
                        the melody, one chord a bar or half bar, the bass line), and check it: the notes played
                        plainly on piano, measured against the recording (tune kept / harmony held, score_casting's
                        own measures). TerraTheme's reduction: tune 0.86, harmony 0.93.
  render SONG STYLE START SECS SPEED OUT [--seed N] [--from T]
                        the lead sheet's notes from START for SECS (seconds of the ORIGINAL), at SPEED (1.0 its own
                        tempo; 0.8 slower; 1.25 faster - exact, no time-stretching), as STYLE on sampled instruments:
                        reduction | piano (the Salamander grand: a rolling left hand under the pedal, the melody
                        legato with a chord tone under its long notes) | strings (violin on the moving notes,
                        tremolo strings on the held ones, slow strings, pizzicato, cello, double bass, harp sweeps)
                        | band (saw lead re-striking its held notes in sixteenths, distortion guitar with vibrato an
                        octave down, power chords, pick bass, synth strings, drums) | band_backing (the band without
                        a lead - "a bit of 90s rock" under another instrument) | piano_voice (the piano, the tune an
                        octave down on a voice patch: the guide an AI pass with lyrics sings from) | musicbox |
                        chillhop (Rhodes, 7th chords, swung eighths, jazz kit). --from T: a LAYER that enters at T.
                        --mode major: the tune in its parallel major (3rd, 6th, 7th raised; chords re-spelled).
  stem IN OUT [--keep vocals]   one stem of a finished take (Demucs) - an AI singer lifted off its accompaniment
  musicgen GUIDE OUT --prompt P [--secs S --seed N --cfg 3]   MusicGen-Melody writes an arrangement from scratch
                        around GUIDE's melody (render the guide with style "melody"). NON-COMMERCIAL weights
                        (CC BY-NC 4.0): tell the director whenever a take uses it. ~/music-tools/models.
  roll SONG START END OUT.png   the transcription drawn over the stems' spectrum, to look at

score_casting's engine "notes" calls `render` and, with "polish", has ACE-Step cover THAT render (denoise 0.6):
the instruments are already right, so the model re-plays them for realism instead of morphing an orchestra.
A recipe's "layers" mix styles (a real piano and a polished band entering at bar 9; a real piano and the singer
of a lyric pass). A held note must MOVE in anything the AI re-plays (tremolo, re-struck, vibrato): held still it
comes back as a steady metallic hum (round 6, the opening bar of the polished strings and band).

Data: ~/music-tools/work/<song>/ (source.wav, stems/, leadsheet.json) - outside the repo, with the instruments
(~/music-tools/sf: the Salamander Grand Piano V3, CC-BY 3.0, Alexander Holm; GeneralUser GS, S. Christian
Collins) and the libraries (~/music-tools/lib: basic-pitch, pretty_midi, mido, mir_eval, tinysoundfont). Run as
    PYTHONPATH=~/music-tools/lib ~/ComfyUI/venv/bin/python3 studio/_tools/notes_cover.py ...
Model work (`prepare`) re-runs itself under `systemd-run --user --scope -p MemoryMax=8G` (box-oom rule).
A song someone else wrote stays a test: its notes are its melody.
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np

MT = os.path.expanduser("~/music-tools")
SR = 44100
PIANO = os.path.join(MT, "sf", "SalamanderGrandPiano-SF2-V3+20200602", "SalamanderGrandPiano-V3+20200602.sf2")
GM = os.path.join(MT, "sf", "GeneralUser-GS.sf2")
CASTING = os.path.join(os.path.dirname(os.path.abspath(__file__)), "score_casting.py")
NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
THIRD = {"": 4, "m": 3}


def song_dir(song):
    return os.path.join(MT, "work", song)


def capped(argv, mem="8G"):
    """Re-run this command under a memory cap unless it already is (the box's OOM killer takes ComfyUI first)."""
    if os.environ.get("NOTES_COVER_CAPPED"):
        return False
    env = dict(os.environ, NOTES_COVER_CAPPED="1")
    r = subprocess.run(["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=" + mem, sys.executable,
                        os.path.abspath(__file__)] + argv, env=env)
    sys.exit(r.returncode)


# ------------------------------------------------------------------------------------------------ SFZ sampler
VSCO = os.path.join(MT, "sf", "vsco", "VSCO-2-CE-1.1.0")   # Versilian VSCO-2 Community Edition - CC0


class Sfz:
    """A small SFZ player for recorded instruments (VSCO-2 CE): regions by key and velocity range, round robins
    (seq_position / lorand), each note the nearest recording pitch-shifted (soxr) to its key, the sample's own
    attack, released over ampeg_release. Real strings - the GM ones sounded "muffled, unnatural" (round 8)."""
    _files = None

    def __init__(self, sfz):
        if Sfz._files is None:          # the .sfz paths' case differs from the disk's: resolve case-insensitively
            Sfz._files = {}
            for dp, _, fs in os.walk(VSCO):
                for f in fs:
                    full = os.path.join(dp, f)
                    Sfz._files[os.path.relpath(full, VSCO).lower()] = full
        self.regions, self.cache, self.rr = [], {}, {}
        glob_op, group_op, path, cur, hdr = {}, {}, "", None, None
        for raw in open(os.path.join(VSCO, sfz), encoding="utf-8", errors="ignore"):
            line = raw.split("//")[0].strip()
            if not line:
                continue
            for tok in ("<control>", "<global>", "<group>", "<region>", "<master>"):
                if line.startswith(tok):
                    if cur is not None:
                        self.regions.append(cur)
                    cur = None
                    if tok == "<region>":
                        cur = dict(glob_op, **group_op)
                    elif tok == "<group>":
                        group_op = {}
                    line = line[len(tok):].strip()
                    hdr = tok
                    break
            if not line:
                continue
            if line.startswith(("sample=", "default_path=")):     # paths run to the end of the line (spaces)
                k0 = line.split("=", 1)[0]
                kv = [(k0, line[len(k0) + 1:].strip())]
            else:
                kv = [tuple(x.split("=", 1)) for x in line.split() if "=" in x]
            for k, v in kv:
                if k == "default_path":
                    path = v.replace("\\", "/")
                elif cur is not None:
                    cur[k] = v
                elif hdr == "<group>":
                    group_op[k] = v
                else:
                    glob_op[k] = v
        if cur is not None:
            self.regions.append(cur)
        for r in self.regions:
            r["file"] = Sfz._files.get((path + r["sample"].replace("\\", "/")).lower())
        self.norm = None

    def calibrate(self, rng, target=0.02):
        """the instruments' raw levels differ ~4x (round 9: the violins under the violas): each player brought to
        the same RMS for a held note at velocity 90, sampled over its range"""
        keys = sorted({int(r.get("pitch_keycenter", 60)) for r in self.regions if r.get("file")})
        keys = [keys[len(keys) // 4], keys[len(keys) // 2], keys[3 * len(keys) // 4]] if len(keys) >= 4 else keys
        self.norm = 1.0
        rms = []
        for k in keys:
            y = self.note(k, 90, 1.0, rng)
            if y is not None:
                rms.append(float(np.sqrt((y[: SR] ** 2).mean())))
        self.norm = target / max(1e-6, float(np.mean(rms))) if rms else 1.0
        return self.norm

    def _load(self, f):
        if f not in self.cache:
            import soundfile as sf
            y, sr = sf.read(f, dtype="float32", always_2d=True)
            if y.shape[1] == 1:
                y = np.repeat(y, 2, axis=1)
            self.cache[f] = (y, sr)
        return self.cache[f]

    def note(self, key, vel, dur, rng):
        """the note's audio at SR (stereo), dur seconds held, then the release"""
        import soxr
        cand = [r for r in self.regions if r.get("file") and int(r.get("lokey", 0)) <= key <= int(r.get("hikey", 127))
                and int(r.get("lovel", 0)) <= vel <= int(r.get("hivel", 127))]
        if not cand:
            return None
        if any("seq_position" in r for r in cand):
            n = self.rr.get(key, 0)
            self.rr[key] = n + 1
            seq = [r for r in cand if int(r.get("seq_position", 1)) == n % int(cand[0].get("seq_length", 1)) + 1]
            cand = seq or cand
        elif any("lorand" in r for r in cand):
            x = rng.random()
            cand = [r for r in cand if float(r.get("lorand", 0)) <= x < float(r.get("hirand", 1))] or cand
        r = cand[0]
        y, sr = self._load(r["file"])
        semis = key - int(r.get("pitch_keycenter", key)) + float(r.get("tune", 0)) / 100.0
        ratio = 2.0 ** (semis / 12.0)
        rel = float(r.get("ampeg_release", 0.5))
        need = int((dur + rel) * sr * ratio) + 16
        y = y[:need]
        y = soxr.resample(y, sr * ratio, SR, quality="HQ") if (abs(ratio - 1) > 1e-6 or sr != SR) else y.copy()
        hold, reln = int(dur * SR), int(rel * SR)
        env = np.ones(len(y), dtype=np.float32)
        if len(y) > hold:
            n = min(reln, len(y) - hold)
            env[hold:hold + n] = np.exp(-5.0 * np.linspace(0, 1, n))
            env[hold + n:] = 0.0
        f = min(int(0.004 * SR), len(y))
        env[:f] *= np.linspace(0, 1, f)
        gain = 10 ** ((float(r.get("volume", 0)) - 12.0) / 20.0) * (vel / 127.0) ** 1.4 * (self.norm or 1.0)
        return y * env[:, None] * gain


# ------------------------------------------------------------------------------------------------ prepare
def separate(src_wav, out):
    """Hybrid Demucs on the GPU in 10 s chunks with a 1 s crossfade (~1.6 GB of VRAM for a 4-minute song)."""
    import soundfile as sf
    import torch
    from torchaudio.pipelines import HDEMUCS_HIGH_MUSDB_PLUS
    from torchaudio.transforms import Fade
    os.makedirs(out, exist_ok=True)
    torch.cuda.set_per_process_memory_fraction(0.25)
    model = HDEMUCS_HIGH_MUSDB_PLUS.get_model().to("cuda").eval()
    sr = HDEMUCS_HIGH_MUSDB_PLUS.sample_rate
    y, fs = sf.read(src_wav, dtype="float32", always_2d=True)
    assert fs == sr
    wav = torch.from_numpy(y.T.copy()).to("cuda")
    ref = wav.mean(0)
    mean, std = ref.mean(), ref.std()
    mix = ((wav - mean) / std)[None]
    n = mix.shape[-1]
    chunk, ov = int(sr * 11.0), int(sr * 1.0)
    fade = Fade(fade_in_len=0, fade_out_len=ov, fade_shape="linear")
    final = torch.zeros(1, len(model.sources), 2, n, device="cuda")
    start, end = 0, chunk
    with torch.no_grad():
        while start < n - ov:
            part = fade(model(mix[:, :, start:end]))
            final[:, :, :, start:start + part.shape[-1]] += part
            if start == 0:
                fade.fade_in_len = ov
                start += chunk - ov
            else:
                start += chunk
            end += chunk
            if end >= n:
                fade.fade_out_len = 0
    final = final * std + mean
    for i, name in enumerate(model.sources):
        s = final[0, i].cpu().numpy().T
        sf.write(os.path.join(out, name + ".wav"), s, sr)
        print("  stem %-7s rms %.4f" % (name, float(np.sqrt((s ** 2).mean()))))


def transcribe(stems):
    """Basic Pitch on the instrument stem and the bass stem -> <stem>_notes.json ([start, end, MIDI pitch, amp])."""
    from basic_pitch import ICASSP_2022_MODEL_PATH
    from basic_pitch.inference import predict
    for stem, lo, hi in (("other", 80.0, 2500.0), ("bass", 30.0, 300.0)):
        _, midi, events = predict(os.path.join(stems, stem + ".wav"), ICASSP_2022_MODEL_PATH, onset_threshold=0.5,
                                  frame_threshold=0.3, minimum_note_length=100.0, minimum_frequency=lo,
                                  maximum_frequency=hi, melodia_trick=True, multiple_pitch_bends=False)
        notes = sorted([[round(float(s), 4), round(float(e), 4), int(p), round(float(a), 4)]
                        for s, e, p, a, _ in events])
        json.dump(notes, open(os.path.join(stems, stem + "_notes.json"), "w"))
        midi.write(os.path.join(stems, stem + "_notes.mid"))
        print("  %-5s %4d notes" % (stem, len(notes)))


def lead_sheet(d):
    """The beat grid (the tracker's eighth-note pulse), bar lines where the bass changes pitch (8 eighths a bar),
    the melody (the top voice of the loud notes, a held note re-struck in sixteenths read as one long note),
    one chord a bar (two when the half bars clearly differ), the bass line, the inner voices."""
    import librosa
    stems = os.path.join(d, "stems")
    other = json.load(open(os.path.join(stems, "other_notes.json")))
    bass = json.load(open(os.path.join(stems, "bass_notes.json")))
    y, sr = librosa.load(os.path.join(d, "source.wav"), sr=22050, mono=True)
    dur = len(y) / sr
    oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=256)
    _, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=256, start_bpm=162, tightness=400,
                                       units="time")
    beats = list(beats)
    step = float(np.median(np.diff(beats)))
    while beats[0] - step > 0:
        beats.insert(0, beats[0] - step)
    while beats[-1] + step < dur:
        beats.append(beats[-1] + step)
    beats = np.array(beats)
    phase, prev = np.zeros(8), None
    for s, e, p, a in bass:
        if p > 55 or a < 0.2:
            continue
        if prev is not None and p % 12 != prev % 12:
            i = int(np.argmin(np.abs(beats - s)))
            if abs(beats[i] - s) < 0.15:
                phase[i % 8] += 1.0
        prev = p
    ph = int(np.argmax(phase))
    grid = np.sort(np.concatenate([beats, (beats[:-1] + beats[1:]) / 2]))

    def q(t):
        return float(grid[int(np.argmin(np.abs(grid - t)))])

    def quant(notes, lo=0, hi=127, min_amp=0.0):
        res = []
        for s, e, p, a in notes:
            if lo <= p <= hi and a >= min_amp:
                qs, qe = q(s), q(e)
                if qe <= qs:
                    qe = float(grid[min(len(grid) - 1, int(np.searchsorted(grid, qs)) + 1)])
                res.append([qs, qe, p, a])
        return res

    def top_line(notes, pick_high=True, rel=0.55):
        seq = []
        for k in range(len(grid) - 1):
            t = grid[k]
            act = [(i, n) for i, n in enumerate(notes) if n[0] <= t < n[1]]
            if not act:
                seq.append(None)
                continue
            loud = max(n[3] for _, n in act)
            cand = [(i, n) for i, n in act if n[3] >= rel * loud]
            seq.append((max if pick_high else min)(cand, key=lambda x: x[1][2])[0])
        line, cur, start = [], None, None
        for k, i in enumerate(seq + [None]):
            if i != cur:
                if cur is not None:
                    n = notes[cur]
                    line.append([float(grid[start]), float(grid[k]), n[2], n[3]])
                cur, start = i, k
        return line

    def clean(line, max_leap=7):
        out = []
        for j, n in enumerate(line):
            prev_p = line[j - 1][2] if j else n[2]
            next_p = line[j + 1][2] if j + 1 < len(line) else n[2]
            if n[1] - n[0] < step * 0.75 and abs(n[2] - prev_p) > max_leap and abs(n[2] - next_p) > max_leap:
                continue
            out.append(list(n))
        for j in range(len(out) - 1):
            if 0 < out[j + 1][0] - out[j][1] <= step * 0.6:
                out[j][1] = out[j + 1][0]
        return out

    def merge_repeats(notes, gap=0.07):
        by = {}
        for s, e, p, a in sorted(notes):
            r = by.setdefault(p, [])
            if r and s - r[-1][1] <= gap:
                r[-1][1], r[-1][3] = max(r[-1][1], e), max(r[-1][3], a)
            else:
                r.append([s, e, p, a])
        return sorted(n for r in by.values() for n in r)

    oq = quant(other, lo=40, min_amp=0.18)
    melody = clean(top_line(quant(merge_repeats([n for n in other if n[2] >= 64 and n[3] >= 0.3]))))
    bq = quant(bass, hi=55, min_amp=0.15)
    bassline = clean(top_line(bq, pick_high=False, rel=0.5), max_leap=12)
    tpl = {}
    for r in range(12):
        for qual, third in (("", 4), ("m", 3)):
            v = np.zeros(12)
            v[r], v[(r + third) % 12], v[(r + 7) % 12] = 1.0, 0.8, 0.8
            tpl[(r, qual)] = v / np.linalg.norm(v)

    def best_chord(a, b):
        pc, low = np.zeros(12), np.zeros(12)
        for s, e, p, amp in oq:
            ov = min(e, b) - max(s, a)
            if ov > 0:
                pc[p % 12] += ov * amp
        for s, e, p, amp in bq:
            ov = min(e, b) - max(s, a)
            if ov > 0:
                low[p % 12] += ov * amp
        pc = pc + 2 * low
        if pc.sum() == 0:
            return None, 0.0
        v = pc / np.linalg.norm(pc)
        broot = int(np.argmax(low)) if low.sum() > 0 else None
        sc = {k: float(v @ t) + (0.08 if broot == k[0] else 0.0) for k, t in tpl.items()}
        k = max(sc, key=sc.get)
        return k, sc[k]

    bars = [float(beats[i]) for i in range(ph, len(beats), 8)]
    first_sound = min(n[0] for n in other)
    while bars and bars[0] < first_sound - step:          # no chord before the music starts
        bars.pop(0)
    bars.append(dur)
    chords = []
    for a, b in zip(bars[:-1], bars[1:]):
        mid = (a + b) / 2
        whole, sw = best_chord(a, b)
        h1, s1 = best_chord(a, mid)
        h2, s2 = best_chord(mid, b)
        if h1 and h2 and h1 != h2 and (s1 + s2) / 2 > sw + 0.04:
            chords += [[a, mid, h1[0], h1[1]], [mid, b, h2[0], h2[1]]]
        elif whole:
            chords.append([a, b, whole[0], whole[1]])
    merged = []
    for c in chords:
        if merged and merged[-1][2:] == c[2:] and abs(merged[-1][1] - c[0]) < 1e-6:
            merged[-1][1] = c[1]
        else:
            merged.append(c)
    if merged and merged[0][0] > 0:
        merged[0][0] = 0.0
    mel_at = lambda t: next((n[2] for n in melody if n[0] <= t < n[1]), 127)
    inner = [n for n in oq if 48 <= n[2] < mel_at(n[0]) and n[3] >= 0.25 and n[1] - n[0] >= step * 0.9]
    sheet = {"duration": dur, "eighth": step, "bpm_quarter": round(30.0 / step, 2), "downbeat_phase": ph,
             "beats": [round(float(b), 4) for b in beats], "bars": [round(b, 4) for b in bars[:-1]],
             "melody": melody, "bass": bassline, "inner": inner,
             "chords": [[round(a, 4), round(b, 4), r, qual, NAMES[r] + qual] for a, b, r, qual in merged]}
    json.dump(sheet, open(os.path.join(d, "leadsheet.json"), "w"), indent=0)
    print("  %.2f BPM (quarter), %d bars, melody %d notes, bass %d, %d chords" % (
        sheet["bpm_quarter"], len(bars) - 1, len(melody), len(bassline), len(merged)))
    print("  chords: " + "  ".join("%.1f %s" % (c[0], c[4]) for c in sheet["chords"][:24]))
    return sheet


def cmd_prepare(a):
    capped(sys.argv[1:])
    d = song_dir(a.song)
    os.makedirs(d, exist_ok=True)
    src = os.path.join(d, "source.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.source, "-ac", "2", "-ar", str(SR), src], check=True)
    if a.force or not os.path.exists(os.path.join(d, "stems", "other.wav")):
        print("separating")
        separate(src, os.path.join(d, "stems"))
    if a.force or not os.path.exists(os.path.join(d, "stems", "other_notes.json")):
        print("transcribing")
        transcribe(os.path.join(d, "stems"))
    print("lead sheet")
    sh = lead_sheet(d)
    # the check: the notes played plainly against the recording, one minute from the first bar
    t0 = sh["bars"][1] if len(sh["bars"]) > 1 else 0.0
    secs = min(60.0, sh["duration"] - t0 - 1)
    red, ref = os.path.join(d, "check_reduction.wav"), os.path.join(d, "check_original.wav")
    render(sh, "reduction", t0, secs, 1.0, red)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % t0, "-t", "%.3f" % secs, "-i", src, ref], check=True)
    py = sys.executable
    tune = subprocess.run([py, CASTING, "_chroma", ref, red], capture_output=True, text=True).stdout.split()
    harm = subprocess.run([py, CASTING, "_harmony", ref, red], capture_output=True, text=True).stdout.split()
    print("check (%.1f-%.1f s, plain piano vs the recording): tune kept %s, harmony held %s (weakest two bars %s)"
          % (t0, t0 + secs, tune[-1] if tune else "?", harm[-2] if len(harm) > 1 else "?",
             harm[-1] if harm else "?"))


# ------------------------------------------------------------------------------------------------ render
STYLES = ("reduction", "piano", "strings", "band", "band_backing", "piano_voice", "musicbox", "chillhop", "melody",
          "vsco_strings")
REVERB = {"reduction": (1.4, 0.18), "piano": (1.9, 0.24), "strings": (2.4, 0.32), "band": (1.2, 0.16), "melody": (0.8, 0.05),
          "vsco_strings": (2.2, 0.22),
          "band_backing": (1.2, 0.16), "piano_voice": (1.9, 0.24), "musicbox": (2.6, 0.34), "chillhop": (1.1, 0.18)}


def to_major(sh):
    """The tune in its parallel MAJOR key: the minor's 3rd, 6th and 7th raised a half step in the melody and the
    bass; the chords re-spelled to the major's own (i -> I, iv -> IV, v -> V, bIII -> iii, bVI -> vi, and bVII ->
    V, its diminished twin being no chord to hold for a bar). The tonic: the minor chord that sounds longest."""
    weight = np.zeros(12)
    for c in sh["chords"]:
        if c[3] == "m":
            weight[c[2]] += c[1] - c[0]
    tonic = int(np.argmax(weight))
    raised = {3, 8, 10}

    def up(p):
        return p + (1 if (p - tonic) % 12 in raised else 0)

    CH = {(0, "m"): (0, ""), (5, "m"): (5, ""), (7, "m"): (7, ""), (3, ""): (4, "m"), (8, ""): (9, "m"),
          (10, ""): (7, "")}
    out = dict(sh)
    out["melody"] = [[s, e, up(p), a] for s, e, p, a in sh["melody"]]
    out["bass"] = [[s, e, up(p), a] for s, e, p, a in sh["bass"]]
    chords = []
    for c in sh["chords"]:
        rel = (c[2] - tonic) % 12
        if (rel, c[3]) in CH:
            r2, q2 = CH[(rel, c[3])]
            root = (tonic + r2) % 12
        else:
            root, q2 = up(c[2]) % 12, c[3]
        chords.append([c[0], c[1], root, q2, NAMES[root] + q2])
    out["chords"] = chords
    return out


def render(sh, style, start, secs, speed, out, seed=1, from_t=None, mode=None):
    """from_t: a LAYER that enters later (original seconds) - nothing of it sounds before then, except a drum fill
    leading in. mode "major": the tune in its parallel major (to_major)."""
    import scipy.signal
    import soundfile as sf
    import tinysoundfont
    rng = np.random.default_rng(seed)
    end = start + secs
    eighth = sh["eighth"]
    if mode == "major":
        sh = to_major(sh)

    def T(t):
        return (t - start) / speed

    def within(notes):
        res = []
        for n in notes:
            s, e = max(n[0], start), min(n[1], end)
            if e - s > 0.02:
                res.append([s, e] + list(n[2:]))
        return res

    chords, melody, bass = within(sh["chords"]), within(sh["melody"]), within(sh["bass"])
    beats = [b for b in sh["beats"] if start - 1e-6 <= b < end - 1e-6]
    bars = [b for b in sh["bars"] if start - 1e-6 <= b < end - 1e-6]
    if not bars or bars[0] > start + 0.01:
        bars.insert(0, start)

    def chord_at(t):
        for c in chords:
            if c[0] <= t < c[1]:
                return c
        return chords[-1] if t >= chords[-1][1] else chords[0]

    def tones(c):
        return [c[2], (c[2] + THIRD[c[3]]) % 12, (c[2] + 7) % 12]

    def place(pc, lo):
        return lo + ((pc - lo) % 12)

    def beats_in(a, b):
        return [x for x in beats if a - 1e-6 <= x < b - 1e-6]

    ev, bends = [], []

    def note(ch, key, s, e, vel, jitter=0.0, fill=False):
        if from_t is not None and s < from_t - 1e-6 and not fill:
            return
        j = rng.normal(0, jitter) if jitter else 0.0
        s2, e2 = max(0.0, T(s) + j), T(e) + j
        if e2 - s2 > 0.01 and 0 <= key <= 127:
            ev.append((s2, ch, int(key), int(max(1, min(127, vel + rng.normal(0, 3)))), e2))

    def mel_vel(n, base):
        return base + (n[2] - 76) * 0.6 + min(8, (n[1] - n[0]) / eighth * 1.2)

    def legato(k, n, overlap, cap):
        nxt = melody[k + 1][0] if k + 1 < len(melody) else n[1]
        return max(n[1], min(nxt + overlap * speed, n[1] + cap))

    def held(n):
        return n[1] - n[0] >= 3 * eighth

    def shimmer(ch, n, e, vel, jitter=0.004):
        """A held note re-struck in sixteenths - how the original's top line plays its long notes. Held still,
        the AI pass renders such a note as a steady metallic hum (round 6: "this metallic sound")."""
        sub, t, k = eighth / 2, n[0], 0
        while t < n[1] - 1e-6:
            last = t + sub >= n[1] - sub * 0.5
            note(ch, n[2], t, e if last else t + sub * 0.92, vel - (0 if k % 4 == 0 else 7), jitter)
            if last:
                break
            t, k = t + sub, k + 1

    def vibrato(ch, s, e, cents=22, rate=5.4, delay=0.3):
        """pitch-bend vibrato on a held note (a 2-semitone bend range: 8192 +- 4096 per semitone)"""
        a, b = T(s) + delay, T(e)
        t = a
        while t < b:
            depth = min(1.0, (t - a) / 0.6)
            bends.append((t, ch, int(8192 + 4096 * cents / 100.0 * depth * np.sin(2 * np.pi * rate * (t - a)))))
            t += 0.02
        bends.append((b, ch, 8192))

    def swing(b):
        """the off-beat eighths late by a third of an eighth"""
        i = sh["beats"].index(b) if b in sh["beats"] else 0
        return b + (eighth / 3 if (i - sh["downbeat_phase"]) % 2 == 1 else 0.0)

    def drums_rock(kit_vel=1.0, crash_every=4, entry=None):
        allb = sh["beats"]
        for b in beats:
            pos = (allb.index(b) - sh["downbeat_phase"]) % 8
            nb = b + eighth * 0.5
            note(9, 42, b, nb, (70 if pos % 2 == 0 else 54) * kit_vel)
            if pos in (0, 4, 5):
                note(9, 36, b, nb, (104 if pos != 5 else 88) * kit_vel)
            if pos in (2, 6):
                note(9, 38, b, nb, 100 * kit_vel)
        for k, b in enumerate(bars):
            if k % crash_every == 0 or (entry is not None and abs(b - entry) < 0.05):
                note(9, 49, b, b + eighth * 4, 96 * kit_vel)
            if k % crash_every == crash_every - 1:
                for x, p in zip(beats_in(b, b + 8 * eighth)[-2:], (45, 41)):
                    note(9, p, x, x + eighth * 0.5, 96 * kit_vel)
                    note(9, p, x + eighth * 0.5, x + eighth, 90 * kit_vel)
        if entry is not None:     # a fill into the entry: snare sixteenths over the last half bar
            for x in beats_in(entry - 4 * eighth, entry):
                for h in (0.0, 0.5):
                    note(9, 38, x + h * eighth, x + (h + 0.5) * eighth, 70 + 6 * (x - entry + 4 * eighth) / eighth,
                         fill=True)

    programs, sfz_programs, sustained, sfz_gain = {}, {}, set(), {}
    if style == "reduction":
        programs = {0: ("piano", 0, 0, False)}
        for n in melody:
            note(0, n[2], n[0], n[1], 92)
        for c in chords:
            for pc in tones(c):
                note(0, place(pc, 60), c[0], c[1], 52)
            note(0, place(c[2], 36), c[0], c[1], 70)
    else:
        PIANO_P = ("piano", 0, 0, False)

        def piano_part(ch_rh=0, ch_lh=1, rh_base=84):
            """right hand: the melody legato, a chord tone under its long notes; left hand: a rolling arpeggio a
            chord, held by the pedal until the chord changes"""
            for k, n in enumerate(melody):
                e, v = legato(k, n, 0.04, 0.3), mel_vel(n, rh_base)
                note(ch_rh, n[2], n[0], e, v, jitter=0.006)
                if held(n):
                    under = [p for p in range(n[2] - 9, n[2] - 2) if p % 12 in tones(chord_at(n[0] + 0.01))]
                    if under:
                        note(ch_rh, max(under), n[0], e, v - 24, jitter=0.006)
            for c in chords:
                root = place(c[2], 36)
                pat = [0, 7, 12, 12 + THIRD[c[3]], 19, 12 + THIRD[c[3]], 12, 7]
                ts = beats_in(c[0], c[1])
                for i, b in enumerate(ts):
                    note(ch_lh, root + pat[i % 8], b, c[1] + 0.05, 62 if i == 0 else (52 if i % 4 == 0 else 46),
                         jitter=0.01)
                if ts and c[1] - c[0] > 6 * eighth:
                    note(ch_lh, root - 12 if root - 12 >= 28 else root, ts[0], c[1] + 0.05, 50, jitter=0.01)

        if style == "piano":
            programs = {0: PIANO_P, 1: PIANO_P}
            piano_part()
        elif style == "melody":
            # the tune alone on a flute, legato - a clean melody for a model that follows one (MusicGen-Melody
            # reads the loudest pitch class of each frame)
            programs = {0: ("gm", 0, 73, False)}
            for k, n in enumerate(melody):
                note(0, n[2], n[0], legato(k, n, 0.03, 0.3), 96)
        elif style == "piano_voice":
            # the guide an AI pass with lyrics sings from: the piano (its melody soft) and the tune an octave down,
            # where a voice sits, on a voice patch
            programs = {0: PIANO_P, 1: PIANO_P, 6: ("gm", 0, 53, False)}
            piano_part(rh_base=66)
            for k, n in enumerate(melody):
                note(6, n[2] - 12, n[0], legato(k, n, 0.05, 0.3), mel_vel(n, 98), jitter=0.006)
                if held(n):
                    vibrato(6, n[0], n[1], cents=18)
        elif style == "strings":
            programs = {0: ("gm", 0, 40, False), 1: ("gm", 0, 49, False), 2: ("gm", 0, 45, False),
                        3: ("gm", 0, 42, False), 4: ("gm", 0, 43, False), 5: ("gm", 0, 46, False),
                        6: ("gm", 0, 44, False)}
            for k, n in enumerate(melody):
                e = legato(k, n, 0.06, 0.3)
                # a held note bowed tremolo (the original shimmers on it); the moving notes on the violin
                note(6 if held(n) else 0, n[2], n[0], e, mel_vel(n, 92), jitter=0.008)
                note(1, n[2] - 12, n[0], e, mel_vel(n, 55), jitter=0.01)
            for c in chords:
                tl = tones(c)
                for pc in tl[1:]:
                    note(1, place(pc, 55), c[0], c[1] + 0.08, 54, jitter=0.01)
                note(3, place(c[2], 36), c[0], c[1] + 0.08, 70, jitter=0.01)
                note(4, place(c[2], 28), c[0], c[1] + 0.08, 64, jitter=0.01)
                pz = [place(tl[0], 48), place(tl[2], 48), place(tl[1], 55), place(tl[2], 55)]
                for i, b in enumerate(beats_in(c[0], c[1])):
                    note(2, pz[i % 4], b, b + eighth * 0.9, 58 if i % 4 == 0 else 50, jitter=0.008)
                for j, p in enumerate([place(tl[0], 48), place(tl[1], 52), place(tl[2], 55), place(tl[0], 60),
                                       place(tl[1], 64), place(tl[2], 67)]):
                    note(5, p, c[0] + j * 0.06 * speed, c[0] + eighth * 6, 46, jitter=0.004)
        elif style in ("band", "band_backing"):
            programs = {0: ("gm", 0, 81, False), 1: ("gm", 0, 30, False), 2: ("gm", 0, 29, False),
                        3: ("gm", 0, 34, False), 4: ("gm", 0, 50, False), 9: ("gm", 128, 0, True)}
            light = style == "band_backing"           # "a bit of 90s rock" under another lead
            if not light:
                for k, n in enumerate(melody):
                    e = legato(k, n, 0.03, 0.2)
                    note(0, n[2], n[0], e, mel_vel(n, 96), jitter=0.004)
                    if held(n):     # held notes sing - vibrato on the lead and the guitar (still, they hum)
                        if os.environ.get("NOTES_BAND_SHIMMER"):
                            shimmer(0, n, e, mel_vel(n, 96))
                        vibrato(0, n[0], n[1], cents=25)
                        vibrato(1, n[0], n[1])
                    note(1, n[2] - 12, n[0], e, mel_vel(n, 74), jitter=0.006)
            for c in chords:
                root = place(c[2], 40)
                for i, b in enumerate(beats_in(c[0], c[1])):
                    for p in (root, root + 7, root + 12):
                        v = (78 if i % 4 == 0 else 66) - (10 if light else 0)
                        note(2, p, b, b + eighth * (0.45 if i % 4 else 0.9), v, jitter=0.004)
                for pc in tones(c):
                    note(4, place(pc, 60), c[0], c[1] + 0.05, 40 if light else 48)
            for n in bass:
                note(3, place(n[2] % 12, 28), n[0], n[1] - 0.02, 88 if light else 92, jitter=0.004)
            drums_rock(kit_vel=0.85 if light else 1.0, entry=from_t)
        elif style == "vsco_strings":
            # recorded strings (VSCO-2 CE, CC0): violins on the tune, violas the inner harmony, cellos and a
            # double bass the roots, pizzicato eighths (the original's moving figure), a harp at each chord
            sfz_programs = {0: "ViolinEnsSusVib.sfz", 1: "ViolinEnsSusVib.sfz", 2: "ViolaEnsSusVib.sfz",
                            3: "CelloEnsSusVib.sfz", 4: "ContrabassSusVB.sfz", 5: "CelloEnsPizz.sfz",
                            6: "Harp.sfz"}
            sustained = {0, 1, 2, 3, 4}
            # the section's balance (dB), each instrument first calibrated to the same level: the tune in front
            sfz_gain = {0: 3.0, 1: -6.0, 2: -5.0, 3: -3.0, 4: -6.0, 5: -9.0, 6: -5.0}
            for k, n in enumerate(melody):
                e = legato(k, n, 0.08, 0.35)
                note(0, n[2] - 12, n[0], e, mel_vel(n, 88), jitter=0.006)       # the violins, an octave down
                if held(n):
                    note(1, n[2] - 24 if n[2] - 24 >= 55 else n[2] - 12, n[0], e, mel_vel(n, 58), jitter=0.01)
            for c in chords:
                tl = tones(c)
                for pc in tl[1:]:
                    note(2, place(pc, 55), c[0], c[1] + 0.1, 64, jitter=0.01)
                note(3, place(c[2], 36), c[0], c[1] + 0.1, 74, jitter=0.01)
                note(4, place(c[2], 28), c[0], c[1] + 0.1, 70, jitter=0.01)
                pz = [place(tl[0], 48), place(tl[2], 48), place(tl[1], 55), place(tl[2], 55)]
                for i, b in enumerate(beats_in(c[0], c[1])):
                    note(5, pz[i % 4], b, b + eighth * 0.9, 66 if i % 4 == 0 else 56, jitter=0.008)
                for j, p in enumerate([place(tl[0], 48), place(tl[1], 52), place(tl[2], 55), place(tl[0], 60),
                                       place(tl[1], 64), place(tl[2], 67)]):
                    note(6, p, c[0] + j * 0.07 * speed, c[0] + eighth * 6, 58, jitter=0.004)
        elif style == "musicbox":
            programs = {0: ("gm", 0, 10, False), 1: ("gm", 0, 8, False), 2: ("gm", 0, 46, False),
                        3: ("gm", 0, 49, False)}
            for k, n in enumerate(melody):
                e = legato(k, n, 0.05, 0.4)
                note(0, n[2], n[0], e, mel_vel(n, 90), jitter=0.006)
                if held(n):         # a music box plucks: a long note comes round again every quarter, softer
                    t, v = n[0] + 2 * eighth, mel_vel(n, 74)
                    while t < n[1] - eighth:
                        note(0, n[2], t, min(n[1], t + 2 * eighth), v, jitter=0.006)
                        t, v = t + 2 * eighth, v - 6
                    note(1, n[2] - 12, n[0], e, mel_vel(n, 58), jitter=0.006)
            for c in chords:
                tl = tones(c)
                arp = [place(tl[0], 48), place(tl[2], 55), place(tl[1], 60), place(tl[2], 62)]
                for i, b in enumerate(beats_in(c[0], c[1])[::2]):
                    note(2, arp[i % 4], b, b + 3 * eighth, 54 if i % 4 == 0 else 46, jitter=0.008)
                for pc in tl:
                    note(3, place(pc, 55), c[0], c[1] + 0.1, 36)
        elif style == "chillhop":
            programs = {0: ("gm", 0, 4, False), 1: ("gm", 0, 4, False), 2: ("gm", 0, 33, False),
                        3: ("gm", 0, 11, False), 9: ("gm", 128, 32, True)}
            for k, n in enumerate(melody):
                e = legato(k, n, 0.03, 0.25)
                note(0, n[2] - 12, n[0], e, mel_vel(n, 80), jitter=0.01)
                note(3, n[2] - 12, n[0], min(e, n[0] + 4 * eighth), mel_vel(n, 50), jitter=0.01)
            allb = sh["beats"]
            for c in chords:
                r, q3 = c[2], THIRD[c[3]]
                seventh = 10 if c[3] == "m" else 11
                voicing = [place(r, 48), place((r + q3) % 12, 55), place((r + seventh) % 12, 58),
                           place((r + 14) % 12, 62)]
                for b in beats_in(c[0], c[1]):
                    pos = (allb.index(b) - sh["downbeat_phase"]) % 8
                    if pos in (0, 3, 6):
                        dur = {0: 2.5, 3: 1.5, 6: 1.8}[pos] * eighth
                        for p in voicing:
                            note(1, p, swing(b), swing(b) + dur, 60 if pos == 0 else 52, jitter=0.008)
                    if pos in (0, 3, 4, 6):
                        p = place(r, 28) if pos != 4 else place((r + 7) % 12, 28)
                        note(2, p, swing(b), swing(b) + eighth * (1.8 if pos in (0, 4) else 0.9),
                             84 if pos == 0 else 72, jitter=0.006)
            for b in beats:
                pos = (allb.index(b) - sh["downbeat_phase"]) % 8
                sb = swing(b)
                note(9, 42, sb, sb + eighth * 0.4, 52 if pos % 2 == 0 else 40, jitter=0.006)
                if pos in (0, 3):
                    note(9, 36, sb, sb + eighth * 0.5, 92 if pos == 0 else 72)
                if pos == 4:
                    note(9, 38, sb, sb + eighth * 0.5, 82)
        else:
            sys.exit("style: " + " | ".join(STYLES))

    total = secs / speed + 4.0
    if sfz_programs:
        dry = np.zeros((int(total * SR), 2), dtype=np.float32)
        players = {}
        for f in set(sfz_programs.values()):
            players[f] = Sfz(f)
            players[f].calibrate(np.random.default_rng(0))
        for s, ch, key, vel, e in sorted(ev):
            y = players[sfz_programs[ch]].note(key, vel, e - s, rng)
            if y is None:
                continue
            y = y * 10 ** (sfz_gain.get(ch, 0.0) / 20.0)
            if ch in sustained and e - s > 0.8:      # a bow's life: in a little, swell, ease off
                n = len(y)
                hold = min(n, int((e - s) * SR))
                sw = np.ones(n, dtype=np.float32)
                x = np.linspace(0, 1, hold)
                sw[:hold] = 0.82 + 0.18 * np.sin(np.pi * np.minimum(1, x * 1.25)) ** 0.8
                sw[hold:] = sw[hold - 1] if hold else 1.0
                y = y * sw[:, None]
            a = int(s * SR)
            n = min(len(y), len(dry) - a)
            if n > 0:
                dry[a:a + n] += y[:n]
        return _finish(dry, style, secs, speed, out, ev)
    synth = tinysoundfont.Synth(samplerate=SR, gain=-12)
    fonts = {"piano": synth.sfload(PIANO), "gm": synth.sfload(GM)}
    for ch, (font, bank, preset, drums) in programs.items():
        synth.program_select(ch, fonts[font], bank, preset, is_drums=drums)
    events = sorted([(s, 1, ch, k, v) for s, ch, k, v, e in ev] + [(e, 0, ch, k, 0) for s, ch, k, v, e in ev] +
                    [(s, 2, ch, v, 0) for s, ch, v in bends], key=lambda x: (x[0], x[1]))
    total = secs / speed + 4.0
    chunks, t_cur = [], 0.0
    for t, on, ch, key, vel in events:
        n = int(round(t * SR)) - int(round(t_cur * SR))
        if n > 0:
            chunks.append(np.frombuffer(synth.generate_simple(n), dtype=np.float32).reshape(-1, 2).copy())
            t_cur = t
        if on == 2:
            synth.pitchbend(ch, key)
        elif on:
            synth.noteon(ch, key, vel)
        else:
            synth.noteoff(ch, key)
    for ch in programs:
        synth.notes_off(ch)
    n = int(round(total * SR)) - int(round(t_cur * SR))
    if n > 0:
        chunks.append(np.frombuffer(synth.generate_simple(n), dtype=np.float32).reshape(-1, 2).copy())
    dry = np.concatenate(chunks)[: int(total * SR)]
    return _finish(dry, style, secs, speed, out, ev)


def _finish(dry, style, secs, speed, out, ev):
    """a hall (decaying stereo noise, darkened, convolved), the cut's ring-out and fade, -1 dBFS"""
    import scipy.signal
    import soundfile as sf
    # a hall: decaying stereo noise, darkened, convolved
    rt60, wet_mix = REVERB[style]
    m = int(SR * rt60 * 1.1)
    h = np.random.default_rng(7).standard_normal((m, 2)) * np.exp(-6.91 * np.arange(m) / SR / rt60)[:, None]
    h = scipy.signal.lfilter([0.45], [1, -0.55], h, axis=0)
    h = np.concatenate([np.zeros((int(0.02 * SR), 2)), h])
    h /= np.sqrt((h ** 2).sum(0))
    wet = np.stack([scipy.signal.fftconvolve(dry[:, c], h[:, c])[: len(dry)] for c in range(2)], 1)
    mix = dry * (1 - wet_mix) + wet * wet_mix * 2.0
    mix = mix[: int((secs / speed + 1.5) * SR)]           # the cut rings on 1.5 s, the last 2.5 s faded
    fade_n = int(2.5 * SR)
    mix[-fade_n:] *= np.linspace(1, 0, fade_n)[:, None] ** 1.5
    mix *= 0.89 / (np.abs(mix).max() + 1e-9)
    sf.write(out, mix, SR)
    print("%s: %d notes, %.1f s -> %s" % (style, len(ev), len(mix) / SR, out))


def cmd_render(a):
    sh = json.load(open(os.path.join(song_dir(a.song), "leadsheet.json")))
    render(sh, a.style, a.start, a.secs, a.speed, a.out, a.seed, a.from_t, a.mode)


def cmd_stem(a):
    """One stem of a finished take (Hybrid Demucs): an AI pass's singer lifted off its own accompaniment, to lay
    over the real piano."""
    capped(sys.argv[1:])
    import soundfile as sf
    tmp = a.out + ".in.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.inp, "-ac", "2", "-ar", str(SR), tmp], check=True)
    d = a.out + ".stems"
    separate(tmp, d)
    y, sr = sf.read(os.path.join(d, a.keep + ".wav"), always_2d=True)
    sf.write(a.out, y, sr)
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))
    os.rmdir(d)
    os.remove(tmp)


# ------------------------------------------------------------------------------------------------ musicgen
MUSICGEN = os.path.join(MT, "models", "musicgen-melody")


def cmd_musicgen(a):
    """MusicGen-Melody (Meta, 2023; the weights CC BY-NC 4.0 - NON-COMMERCIAL ONLY): a new arrangement written from
    scratch around a guide melody (it reads the loudest pitch class of each frame of GUIDE - render it with
    `render SONG melody ...`) in the style the prompt describes. 32 kHz mono, at most 30 s a take. On the GPU, under
    a memory cap; the caller waits for ComfyUI's queue to be empty first."""
    capped(sys.argv[1:], mem="16G")
    import librosa
    import soundfile as sf
    import torch
    from transformers import AutoProcessor, MusicgenMelodyForConditionalGeneration
    proc = AutoProcessor.from_pretrained(MUSICGEN)
    import functools
    model = MusicgenMelodyForConditionalGeneration.from_pretrained(MUSICGEN, torch_dtype=torch.bfloat16)
    model = model.to("cuda").eval()
    # transformers 5.x creates the (empty) cache BEFORE the first step, and MusicGen-Melody drops its conditioning
    # (prompt + melody) whenever a cache exists - so it ignored both and improvised (2026-10-05: four prompts and two
    # guidance scales gave bit-identical takes). Keep the conditioning on the first step.
    orig = model.prepare_inputs_for_generation

    @functools.wraps(orig)
    def first_step_keeps_conditioning(decoder_input_ids, encoder_hidden_states=None, past_key_values=None, **kw):
        out = orig(decoder_input_ids, encoder_hidden_states=encoder_hidden_states, past_key_values=past_key_values,
                   **kw)
        if encoder_hidden_states is not None and past_key_values is not None and past_key_values.get_seq_length() == 0:
            out["encoder_hidden_states"] = encoder_hidden_states
        return out
    model.prepare_inputs_for_generation = first_step_keeps_conditioning
    jobs = json.load(open(a.jobs)) if a.jobs else [{"guide": a.guide, "out": a.out, "prompt": a.prompt,
                                                     "secs": a.secs, "seed": a.seed, "cfg": a.cfg}]
    for j in jobs:
        mel, _ = librosa.load(j["guide"], sr=32000, mono=True)
        secs = min(30.0, j.get("secs") or len(mel) / 32000.0)
        torch.manual_seed(int(j.get("seed", 1)))
        inputs = proc(audio=mel, sampling_rate=32000, text=[j["prompt"]], padding=True, return_tensors="pt")
        inputs = {k: (v.to("cuda", dtype=torch.bfloat16) if v.dtype.is_floating_point else v.to("cuda"))
                  for k, v in inputs.items()}
        with torch.no_grad():
            audio = model.generate(**inputs, do_sample=True, guidance_scale=float(j.get("cfg", 3.0)),
                                   max_new_tokens=int(secs * 50), top_k=int(j.get("top_k", 250)),
                                   temperature=float(j.get("temperature", 1.0)))
        y = audio[0, 0].float().cpu().numpy()
        sf.write(j["out"], y, model.config.audio_encoder.sampling_rate)
        print("musicgen: %.1f s -> %s" % (len(y) / model.config.audio_encoder.sampling_rate, j["out"]), flush=True)


# ------------------------------------------------------------------------------------------------ roll
def cmd_roll(a):
    import librosa
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    stems = os.path.join(song_dir(a.song), "stems")
    fig, axes = plt.subplots(2, 1, figsize=(18, 13), gridspec_kw={"height_ratios": [3, 1.2]})
    for ax, stem, lo, hi in ((axes[0], "other", 40, 92), (axes[1], "bass", 24, 62)):
        y, sr = librosa.load(os.path.join(stems, stem + ".wav"), sr=22050, mono=True, offset=a.start,
                             duration=a.end - a.start)
        C = librosa.amplitude_to_db(np.abs(librosa.cqt(y, sr=sr, hop_length=256, fmin=librosa.midi_to_hz(lo),
                                                       n_bins=(hi - lo) * 3, bins_per_octave=36)), ref=np.max)
        ax.imshow(C, origin="lower", aspect="auto", cmap="gray_r", vmin=-60, vmax=0,
                  extent=[a.start, a.end, lo - 0.5, hi - 0.5])
        for s, e, p, amp in json.load(open(os.path.join(stems, stem + "_notes.json"))):
            if a.start <= e and s <= a.end:
                ax.add_patch(plt.Rectangle((s, p - 0.4), e - s, 0.8, color=plt.cm.autumn(1 - min(1, amp * 1.6)),
                                           alpha=0.75))
        ax.set_ylim(lo - 0.5, hi - 0.5)
        ax.set_yticks(range(lo, hi, 2))
        ax.set_yticklabels([librosa.midi_to_note(m, unicode=False) for m in range(lo, hi, 2)], fontsize=7)
        ax.set_title("%s: transcribed notes (red = loud) over its spectrum" % stem, loc="left")
    plt.tight_layout()
    plt.savefig(a.out, dpi=60)


def main():
    ap = argparse.ArgumentParser(description="a cover from the song's notes")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("song")
    p.add_argument("source")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("render")
    p.add_argument("song")
    p.add_argument("style")
    p.add_argument("start", type=float)
    p.add_argument("secs", type=float)
    p.add_argument("speed", type=float)
    p.add_argument("out")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--from", dest="from_t", type=float, default=None,
                   help="a layer entering later: nothing before this time of the original (a drum fill leads in)")
    p.add_argument("--mode", choices=["major"], default=None, help="the tune in its parallel major key")
    p = sub.add_parser("stem")
    p.add_argument("inp")
    p.add_argument("out")
    p.add_argument("--keep", default="vocals", choices=["drums", "bass", "other", "vocals"])
    p = sub.add_parser("musicgen")
    p.add_argument("guide", nargs="?")
    p.add_argument("out", nargs="?")
    p.add_argument("--jobs", help="a JSON list of {guide, out, prompt, secs, seed, cfg, top_k, temperature}")
    p.add_argument("--prompt")
    p.add_argument("--secs", type=float, default=None)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--cfg", type=float, default=3.0)
    p = sub.add_parser("roll")
    p.add_argument("song")
    p.add_argument("start", type=float)
    p.add_argument("end", type=float)
    p.add_argument("out")
    a = ap.parse_args()
    {"prepare": cmd_prepare, "render": cmd_render, "stem": cmd_stem, "musicgen": cmd_musicgen,
     "roll": cmd_roll}[a.cmd](a)


if __name__ == "__main__":
    main()
