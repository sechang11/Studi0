#!/usr/bin/env python3
"""studio/_tools/qc_slate.py - the last look at the delivered masters, by instrument.

Everything here is measured off the DELIVERED file, not the working copy, because the
delivered file is the one that gets posted and this project has shipped a defect that
existed only after the copy before.

Checks, and why each one is here rather than assumed:

  duration        picture vs audio stream length. They must match: a master written with
                  -t <picture> truncates a voice that starts near the end, which is how
                  the last line went missing in six films and nothing noticed.
  loudness        integrated LUFS. -9.5 or so is the short-form target; the platforms
                  turn you down rather than up, so being quiet costs more than being hot.
  true peak       dBTP. Under -1.0 is the ask. Anything above -0.5 is close enough to
                  clipping that a lossy re-encode on the platform's side can push it over,
                  which is the actual failure - it sounds fine here and crunches there.
  tail motion     clipmetrics motion over the last 2 seconds, against the static
                  floor of 0.001 this project measured. A held final frame is legitimate
                  as an outro, but a film that ran out of picture sits ON the floor, and
                  that is worth seeing rather than discovering on a phone. Uses
                  clipmetrics rather than a fresh measure, because the first version of
                  this check invented one and flagged four healthy films.

Prints one line per film and a count of what is out of range. Exit 0 always - this
reports, it does not gate, because the person reading it is the gate.
"""
import glob
import json
import os
import re
import subprocess
import sys

SHORTS = os.path.expanduser("~/shared/comfy-studio/studio/samples/shorts")


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def probe_streams(p):
    r = sh("ffprobe", "-v", "error", "-show_entries",
           "stream=codec_type,duration:format=duration", "-of", "json", p)
    try:
        d = json.loads(r.stdout or "{}")
    except Exception:
        return None, None
    v = a = None
    for s in d.get("streams", []):
        if s.get("codec_type") == "video" and s.get("duration"):
            v = float(s["duration"])
        if s.get("codec_type") == "audio" and s.get("duration"):
            a = float(s["duration"])
    fmt = float((d.get("format") or {}).get("duration") or 0) or None
    return (v or fmt), (a or fmt)


def loudness(p):
    r = sh("ffmpeg", "-nostats", "-i", p, "-af", "ebur128=peak=true", "-f", "null", "-")
    err = r.stderr or ""
    # ONLY the Summary block. The running per-frame I: lines start at -70 LUFS and
    # parsing the first one demoted 17 good voice packs earlier tonight.
    summ = err.split("Summary:", 1)[1] if "Summary:" in err else ""
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", summ)
    tp = re.search(r"Peak:\s+(-?[\d.]+) dBFS", summ)
    return (float(i.group(1)) if i else None), (float(tp.group(1)) if tp else None)


# The static floor this project measured for clipmetrics motion is 0.001. A held frame
# sits on it; anything an order of magnitude above is moving.
STATIC_FLOOR = 0.001
FROZEN_BELOW = 0.01


def tail_motion(p, dur):
    """Motion in the last 2 seconds, via clipmetrics - NOT a new instrument.

    The first version of this counted ffmpeg scene-change hits above a threshold I
    guessed, and it flagged four healthy supplement films for a "frozen tail" that
    measures 0.179 on clipmetrics against a 0.001 static floor - 179x the floor, i.e.
    an ordinary calm ending to a 28-second read.

    That is the third time in this project a hand-rolled measure has produced a
    confident wrong verdict while a calibrated one sat in the repo unused (see the
    SSIM-drift and ebur128 mistakes). A QC pass that flags healthy work is worse than
    none, because it teaches you to skip the real flags. So this asks clipmetrics.
    """
    if not dur or dur < 3:
        return None
    tmp = "/tmp/_qc_tail_%d.mp4" % os.getpid()
    sh("ffmpeg", "-y", "-v", "error", "-sseof", "-2.0", "-i", p, "-an", tmp)
    if not os.path.exists(tmp):
        return None
    r = sh(sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "clipmetrics.py"), tmp)
    os.remove(tmp)
    m = re.search(r"motion=([\d.]+)", (r.stdout or "") + (r.stderr or ""))
    return float(m.group(1)) if m else None


def main():
    files = sorted(glob.glob(os.path.join(SHORTS, "*", "*.mp4")))
    if not files:
        print("nothing delivered under %s" % SHORTS, file=sys.stderr)
        return 0
    print("%-34s %6s %6s %8s %8s %8s"
          % ("film", "video", "audio", "LUFS", "dBTP", "tail mot"))
    bad = []
    for p in files:
        name = os.path.basename(p)[:34]
        v, a = probe_streams(p)
        i, tp = loudness(p)
        fz = tail_motion(p, v)
        flags = []
        if v and a and abs(v - a) > 0.35:
            flags.append("A/V %.2fs apart" % abs(v - a))
        if tp is not None and tp > -0.5:
            flags.append("true peak %.2f" % tp)
        if i is not None and i > -7.0:
            flags.append("hot %.1f LUFS" % i)
        if fz is not None and fz < FROZEN_BELOW:
            flags.append("frozen tail (motion %.4f, floor %.3f)" % (fz, STATIC_FLOOR))
        print("%-34s %6.1f %6.1f %8s %8s %8s  %s"
              % (name, v or 0, a or 0,
                 "%.2f" % i if i is not None else "-",
                 "%.2f" % tp if tp is not None else "-",
                 "%.3f" % fz if fz is not None else "-",
                 "; ".join(flags)))
        if flags:
            bad.append((name, flags))
    print("\n%d masters, %d with something to look at" % (len(files), len(bad)))
    for n, f in bad:
        print("   %-34s %s" % (n, "; ".join(f)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
