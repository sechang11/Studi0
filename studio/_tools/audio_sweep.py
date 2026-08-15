#!/usr/bin/env python3
"""audio_sweep.py - the audio kinds get MEASURED evidence: cues, sfx, voices.

    python3 studio/_tools/audio_sweep.py [--kind cues|sfx|voices] [--only ID] [--limit N]

WHY. 20 cues, 13 sfx and 17 voices are `ready` and UNVERIFIED - the honest debt list
from Phase 4. Every one of them is measurable BY INSTRUMENT without ears: rendered,
non-silent, the right length, sane loudness, and (cues) tonal rather than noise. That is
not "it sounds good"; it is "it exists and is not broken", which is exactly what
MEASURED means here. Whether a cue is beautiful stays a human's call, and the sample is
written next to the card so the human can play it.

WHAT IT DOES per kind:
  cues    render through 06_acestep_music (tags/bpm/key from the card, keyscale-guarded,
          20s to keep the sweep under an hour), then measure.
  sfx     render through 10_stableaudio_sfx at the card's own seconds; measure.
  voices  the reference file itself: exists, mono/stereo, seconds, LUFS, non-silent, f0
          median (librosa pyin in the ComfyUI venv). No render - a voice pack's evidence
          is the pack.

MEASUREMENTS (ffmpeg, all real): integrated LUFS + true peak (ebur128), duration, silent
fraction (silencedetect at -50 dB), and for cues spectral flatness proxy (librosa) - a
cue that is white noise fails its own claim.

VERDICTS: MEASURED with the numbers in the note. status changes ONLY on hard failure
(no output, silent, >50% silence, or a duration off by more than 40%) -> weak, saying
what failed. Nothing is promoted by instrument alone.
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, STUDIO)
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run, set_path                    # noqa: E402
from engine import load_wf, HOST, keyscale         # noqa: E402
import cards                                       # noqa: E402

COMFY = os.environ.get("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
VENV_PY = os.path.join(COMFY, "venv", "bin", "python")
VOICE_ROOT = os.path.join(COMFY, "custom_nodes", "TTS-Audio-Suite")


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def measure(path):
    """LUFS/TP/duration/silent-fraction from ffmpeg. NOT -v error: ebur128 and
    silencedetect report on stderr and quieting it reads as silence (the memory)."""
    out = {}
    r = sh("ffprobe", "-v", "error", "-show_entries", "stream=channels,sample_rate:format=duration",
           "-of", "default=nw=1", path)
    for ln in (r.stdout or "").splitlines():
        k, _, v = ln.partition("=")
        if k == "duration":
            out["seconds"] = round(float(v), 2)
        elif k == "channels":
            out["channels"] = int(v)
        elif k == "sample_rate":
            out["sample_rate"] = int(v)
    r = sh("ffmpeg", "-nostats", "-i", path, "-af",
           "ebur128=peak=true,silencedetect=n=-50dB:d=0.3", "-f", "null", "-")
    err = r.stderr or ""
    # READ THE SUMMARY BLOCK ONLY. ebur128 prints a running `I:` on every frame line
    # before the summary; the first match is the first frame (-70 = "nothing yet"), and
    # the first version of this parser demoted seventeen good voice packs on it.
    summ = err.split("Summary:", 1)[1] if "Summary:" in err else ""
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", summ)
    if m:
        out["lufs"] = float(m.group(1))
    m = re.search(r"Peak:\s+(-?[\d.]+) dBFS", summ)
    if m:
        out["true_peak"] = float(m.group(1))
    # An instrument that contradicts itself must say so, not judge: a file at -60 LUFS
    # cannot have a peak above -20 dBFS.
    if out.get("lufs") is not None and out.get("true_peak") is not None             and out["lufs"] < -60 and out["true_peak"] > -20:
        raise RuntimeError("ebur128 parse contradiction on %s: I=%s TP=%s"
                           % (path, out["lufs"], out["true_peak"]))
    sil = sum(float(x) for x in re.findall(r"silence_duration:\s*([\d.]+)", err))
    out["silent_seconds"] = round(sil, 2)
    if out.get("seconds"):
        out["silent_fraction"] = round(sil / out["seconds"], 2)
    return out


def tonality(path):
    """Spectral flatness (0 = tonal, 1 = white noise) and f0 median, via the ComfyUI
    venv's librosa. Returns {} if the venv is missing."""
    if not os.path.exists(VENV_PY):
        return {}
    code = r'''
import sys, json, numpy as np, librosa
y, sr = librosa.load(sys.argv[1], sr=22050, mono=True, duration=30)
flat = float(np.mean(librosa.feature.spectral_flatness(y=y)))
f0 = None
try:
    f, vf, _ = librosa.pyin(y, fmin=60, fmax=600, sr=sr)
    v = f[~np.isnan(f)]
    if v.size: f0 = float(np.median(v))
except Exception: pass
print(json.dumps({"flatness": round(flat, 4), "f0_median": round(f0, 1) if f0 else None}))
'''
    r = subprocess.run([VENV_PY, "-c", code, path], capture_output=True, text=True,
                       timeout=180)
    try:
        return json.loads((r.stdout or "").strip().splitlines()[-1])
    except Exception:
        return {}


def render_cue(card, seconds, seed):
    wf = load_wf("06_acestep_music.json")
    set_path(wf, "10.inputs.tags", card.get("tags", ""))
    set_path(wf, "10.inputs.lyrics", "")
    try:
        set_path(wf, "10.inputs.bpm", int(float(card.get("bpm") or 0)) or 100)
    except ValueError:
        pass
    ks = keyscale(card.get("key", ""))
    if ks:
        set_path(wf, "10.inputs.keyscale", ks)
    set_path(wf, "10.inputs.duration", float(seconds))
    set_path(wf, "10.inputs.seed", seed)
    set_path(wf, "11.inputs.seconds", float(seconds))
    set_path(wf, "12.inputs.seed", seed)
    set_path(wf, "14.inputs.filename_prefix", "claude-generated/cues/%s" % card["id"])
    _, outs = run(HOST, wf, quiet=True)
    for o in outs or []:
        if str(o).lower().endswith((".mp3", ".flac", ".wav")):
            return os.path.join(COMFY, "output", o)
    return None


def render_sfx(card, seed):
    wf = load_wf("10_stableaudio_sfx.json")
    set_path(wf, "3.inputs.text", card.get("prompt", ""))
    if card.get("negative"):
        set_path(wf, "4.inputs.text", card["negative"])
    set_path(wf, "5.inputs.seconds", float(card.get("seconds") or 3))
    set_path(wf, "6.inputs.seed", seed)
    try:
        set_path(wf, "6.inputs.steps", int(card.get("steps") or 8))
        set_path(wf, "6.inputs.cfg", float(card.get("cfg") or 1.0))
    except ValueError:
        pass
    set_path(wf, "8.inputs.filename_prefix", "claude-generated/sfx/%s" % card["id"])
    _, outs = run(HOST, wf, quiet=True)
    for o in outs or []:
        if str(o).lower().endswith((".mp3", ".flac", ".wav")):
            return os.path.join(COMFY, "output", o)
    return None


def judge(kind, card, m, want_secs):
    """(status_or_None, note). status None = keep; 'weak' = hard failure."""
    fails = []
    if not m.get("seconds"):
        fails.append("no audio")
    else:
        if m.get("silent_fraction", 0) > 0.5:
            fails.append("%.0f%% silent" % (100 * m["silent_fraction"]))
        if m.get("lufs") is not None and m["lufs"] < -45:
            fails.append("%.1f LUFS - effectively silent" % m["lufs"])
        if want_secs and abs(m["seconds"] - want_secs) > 0.4 * want_secs:
            fails.append("%.1fs against %.1fs asked" % (m["seconds"], want_secs))
        if kind == "cues" and m.get("flatness") is not None and m["flatness"] > 0.5:
            fails.append("spectral flatness %.2f - noise, not music" % m["flatness"])
    nums = ", ".join("%s=%s" % (k, m[k]) for k in ("seconds", "lufs", "true_peak",
                                                  "silent_fraction", "flatness",
                                                  "f0_median", "channels")
                     if m.get(k) is not None)
    if fails:
        return "weak", "FAILED: %s [%s]" % ("; ".join(fails), nums)
    return None, "renders and is not broken [%s]" % nums


def main():
    ap = argparse.ArgumentParser(description="Instrument evidence for cues/sfx/voices.")
    ap.add_argument("--kind", choices=("cues", "sfx", "voices"))
    ap.add_argument("--only")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--cue-seconds", type=float, default=20.0)
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--fresh", action="store_true", help="re-render even if a sample exists")
    a = ap.parse_args()
    kinds = [a.kind] if a.kind else ["voices", "sfx", "cues"]
    tally = {}
    for kind in kinds:
        outdir = os.path.join(STUDIO, "samples", kind)
        os.makedirs(outdir, exist_ok=True)
        n = 0
        for cid, card in sorted(cards.load(kind).items()):
            if cid.startswith("_"):
                continue
            if a.only and cid != a.only:
                continue
            if card.get("status") in ("blocked", "unsupported", "unavailable"):
                continue           # blocked voices are never touched; the rule stands
            if a.limit and n >= a.limit:
                break
            n += 1
            want = None
            if kind == "voices":
                src = card.get("file", "")
                path = src if os.path.isabs(src) else os.path.join(VOICE_ROOT, src)
                if not os.path.exists(path):
                    cards.stamp(kind, cid, "MEASURED", "audio_sweep: reference file",
                                note="FAILED: reference file missing: %s" % src)
                    _set_status(kind, cid, "unavailable")
                    tally[(kind, "missing")] = tally.get((kind, "missing"), 0) + 1
                    print("%-8s %-24s MISSING %s" % (kind, cid, src))
                    continue
                m = measure(path)
                m.update(tonality(path))
            else:
                sample = os.path.join(outdir, cid + ".mp3")
                if a.fresh or not os.path.exists(sample):
                    got = (render_cue(card, a.cue_seconds, a.seed) if kind == "cues"
                           else render_sfx(card, a.seed))
                    if got and os.path.exists(got):
                        shutil.copy(got, sample)
                    else:
                        cards.stamp(kind, cid, "MEASURED", "audio_sweep: render",
                                    note="FAILED: the graph produced no audio")
                        _set_status(kind, cid, "weak")
                        tally[(kind, "norender")] = tally.get((kind, "norender"), 0) + 1
                        print("%-8s %-24s NO RENDER" % (kind, cid))
                        continue
                want = a.cue_seconds if kind == "cues" else float(card.get("seconds") or 0)
                m = measure(sample)
                if kind == "cues":
                    m.update(tonality(sample))
                # the recipe beside the sample, like every other artefact here
                json.dump({"kind": kind, "id": cid, "card": card, "seed": a.seed,
                           "measured": m, "workflow": ("06_acestep_music.json" if kind == "cues"
                                                        else "10_stableaudio_sfx.json")},
                          open(os.path.join(outdir, cid + ".json"), "w"), indent=1)
            status, note = judge(kind, card, m, want)
            method = ("audio_sweep: %s" % ("reference file measured" if kind == "voices"
                                            else "rendered + measured (ffmpeg ebur128/"
                                                 "silencedetect, librosa flatness)"))
            cards.stamp(kind, cid, "MEASURED", method, note=note)
            if status:
                _set_status(kind, cid, status)
            tally[(kind, "weak" if status else "ok")] = tally.get(
                (kind, "weak" if status else "ok"), 0) + 1
            print("%-8s %-24s %s" % (kind, cid, note[:110]))
    print("\n" + json.dumps({"%s/%s" % k: v for k, v in sorted(tally.items())}))
    return 0


def _set_status(kind, cid, status):
    p = os.path.join(STUDIO, kind, cid + ".json")
    c = json.load(open(p, encoding="utf-8"))
    if c.get("status") != status:
        c["status_before_sweep"] = c.get("status")
        c["status"] = status
        with open(p, "w", encoding="utf-8") as f:
            json.dump(c, f, indent=2, ensure_ascii=False)
            f.write("\n")


if __name__ == "__main__":
    sys.exit(main())
