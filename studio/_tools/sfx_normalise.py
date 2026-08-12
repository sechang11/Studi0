#!/usr/bin/env python3
"""studio/_tools/sfx_normalise.py - measure the SFX library, and level it.

    python3 studio/_tools/sfx_normalise.py --measure          just report
    python3 studio/_tools/sfx_normalise.py --apply            normalise in place (keeps .orig)

WHAT WAS MEASURED, AND HOW IT DIFFERS FROM WHAT THE BACKLOG ASSUMED.

Backlog #46 recorded "a bang and a footstep arrived 20 dB apart". Measured with ffmpeg
loudnorm, the note is right and if anything understated:

    20 preset effects alone   spread  7.8 dB  (-14.4 to  -6.6 LUFS, median  -9.9)
    all 32 rendered effects   spread 26.5 dB  (-33.2 to  -6.6 LUFS, median -11.6)

Measuring only the presets makes the problem look half its size; the rolled effects are
where the tail lives. The measurement also turned up something the note missed, which
matters more:

    20 OF 21 SFX FILES PEAK ABOVE -1.0 dBTP, up to +4.5 dBTP.

They are clipping. A true peak above 0 dBFS means the waveform was driven past what the
format can represent - the damage is baked into the file, and every later gain stage
inherits it. That is not a mix problem to be solved by a fader in epic.py; it is damage at
generation time. Stable Audio output was written straight to disk with no limiter.

WHY BOTH TARGETS. SFX_LUFS (-30) is where epic.py wants effects to SIT in a film. That is a
mix decision and belongs in the mix. What belongs in the LIBRARY is a file that is not
clipped and is consistent with its neighbours, so the mix has something predictable to work
with. So this normalises to a library level with real headroom (-20 LUFS, -6 dBTP) and
leaves the -30 placement to epic.py, which already does it.

The originals are kept as .orig next to each file. A normalisation that cannot be undone is
a normalisation you cannot check.
"""
import argparse, glob, json, os, shutil, statistics, subprocess, sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)

LIB_LUFS = -20.0
LIB_TP = -6.0
PRESETS = ["studio/samples/domains/sfx__*.mp3"]
ROLLED = ["studio/samples/rolled/**/*sfx*.mp3",
          "studio/samples/fill_run/**/*sfx*.mp3"]
# Default to the presets. The rolled directories are written by a live generation run, and
# rewriting a file while the roller is still producing into that tree invites a half-written
# mp3 that measures fine and plays as a click.
PATTERNS = PRESETS


def loud(path, full=False):
    """Measure with loudnorm. ALL FOUR measured values, not two.

    The first version passed real measured_I and measured_TP but INVENTED measured_LRA and
    measured_thresh. loudnorm's linear mode solves for a gain using all four, so feeding it
    two made-up numbers made it miss by 5 LU and leave the true peak above target - which
    the verification pass caught, reporting -15.0 LUFS against a -20 target and +0.5 dBTP.
    Fabricated inputs produce a confident wrong answer; that is the whole lesson here.
    """
    r = subprocess.run(["ffmpeg", "-i", path, "-af", "loudnorm=print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    try:
        j = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
        if full:
            return {k: float(j[k]) for k in
                    ("input_i", "input_tp", "input_lra", "input_thresh")}
        return float(j["input_i"]), float(j["input_tp"])
    except Exception:
        return (None if full else (None, None))


def files(root):
    out = []
    for p in PATTERNS:
        out += glob.glob(os.path.join(root, p), recursive=True)
    return sorted(set(f for f in out if not f.endswith(".orig")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--root", default=os.path.dirname(STUDIO))
    ap.add_argument("--include-rolled", action="store_true",
                    help="also level the rolled/fill_run effects - only when no generation "
                         "run is writing into those trees")
    a = ap.parse_args()

    global PATTERNS
    if a.include_rolled:
        PATTERNS = PRESETS + ROLLED
    fs = files(a.root)
    if not fs:
        print("  no sfx files found")
        return 0
    rows = []
    for f in fs:
        i, tp = loud(f)
        if i is not None:
            rows.append([f, i, tp])
    if not rows:
        print("  nothing measurable")
        return 1

    vals = [r[1] for r in rows]
    clip = [r for r in rows if r[2] > -1.0]
    print("  %d files | %.1f to %.1f LUFS (spread %.1f dB, median %.1f)"
          % (len(rows), min(vals), max(vals), max(vals) - min(vals),
             statistics.median(vals)))
    print("  %d peak above -1.0 dBTP%s"
          % (len(clip), " - these are clipped" if clip else ""))
    for f, i, tp in sorted(clip, key=lambda r: -r[2])[:5]:
        print("    %+5.1f dBTP  %s" % (tp, os.path.basename(f)))

    if not a.apply:
        print("\n  --apply to normalise to %.0f LUFS / %.0f dBTP (keeps .orig)"
              % (LIB_LUFS, LIB_TP))
        return 0

    done = 0
    for f, i, tp in rows:
        orig = f + ".orig"
        if not os.path.exists(orig):
            shutil.copy2(f, orig)
        tmp = f + ".tmp.mp3"
        # Two-pass loudnorm: the single-pass filter does not hit a target, which this
        # project already learned when a one-pass master missed by several LU. Measure,
        # then apply the measured offset with a limiter holding the true peak.
        m = loud(orig, full=True)
        if not m:
            print("  FAILED to measure %s" % os.path.basename(f))
            continue
        r = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", orig,
             "-af", "loudnorm=I=%.1f:TP=%.1f:LRA=11:linear=true:measured_I=%.2f:"
                    "measured_TP=%.2f:measured_LRA=%.2f:measured_thresh=%.2f,"
                    # level=disabled IS THE WHOLE FIX. ffmpeg's alimiter auto-levels its
                    # output by default, which took a correctly normalised -20.9 LUFS /
                    # -5.2 dBTP file back up to -14.9 LUFS / +1.0 dBTP - undoing the
                    # normalisation and REINTRODUCING the clipping the limiter was added
                    # to prevent. Measured on sfx__preset-keyboard: loudnorm alone -20.9,
                    # with default alimiter -14.9, with level=disabled -20.9.
                    "alimiter=limit=%.4f:level=disabled:attack=1:release=50"
                    % (LIB_LUFS, LIB_TP, m["input_i"], m["input_tp"],
                       m["input_lra"], m["input_thresh"], 10 ** (LIB_TP / 20.0)),
             "-c:a", "libmp3lame", "-b:a", "192k", tmp],
            capture_output=True, text=True)
        if r.returncode != 0 or not os.path.isfile(tmp):
            print("  FAILED %s: %s" % (os.path.basename(f), r.stderr.strip()[-120:]))
            continue
        os.replace(tmp, f)
        done += 1

    # Re-measure. A normalisation that is not verified is a claim, not a result - and this
    # project has shipped enough of those.
    after = [loud(f)[0:2] for f, _i, _tp in rows]
    ai = [x[0] for x in after if x[0] is not None]
    atp = [x[1] for x in after if x[1] is not None]
    print("\n  normalised %d" % done)
    print("  after: %.1f to %.1f LUFS (spread %.1f dB), worst peak %+.1f dBTP"
          % (min(ai), max(ai), max(ai) - min(ai), max(atp)))
    if max(atp) > LIB_TP + 1.0:
        print("  !! peaks still above target - the limiter did not take")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
