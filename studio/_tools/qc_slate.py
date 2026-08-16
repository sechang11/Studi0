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
  frozen tail     compares the last second against the second before it. A held final
                  frame is legitimate as an outro, but a LONG one means the film ran out
                  of picture, and that is worth seeing rather than discovering on a phone.

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


def frozen_tail(p, dur):
    """How many of the last 2 seconds are a still frame, by frame-to-frame difference."""
    if not dur or dur < 3:
        return 0.0
    r = sh("ffmpeg", "-v", "error", "-ss", "%.2f" % (dur - 2.0), "-i", p,
           "-vf", "select='gt(scene,0.0006)',metadata=print:file=-", "-an", "-f", "null", "-")
    hits = len(re.findall(r"pts_time:", r.stdout or ""))
    # 2s at 24fps = 48 frames; a live tail changes on most of them
    return round(max(0.0, 1.0 - hits / 40.0) * 2.0, 2)


def main():
    files = sorted(glob.glob(os.path.join(SHORTS, "*", "*.mp4")))
    if not files:
        print("nothing delivered under %s" % SHORTS, file=sys.stderr)
        return 0
    print("%-34s %6s %6s %8s %8s %6s" % ("film", "video", "audio", "LUFS", "dBTP", "frozen"))
    bad = []
    for p in files:
        name = os.path.basename(p)[:34]
        v, a = probe_streams(p)
        i, tp = loudness(p)
        fz = frozen_tail(p, v)
        flags = []
        if v and a and abs(v - a) > 0.35:
            flags.append("A/V %.2fs apart" % abs(v - a))
        if tp is not None and tp > -0.5:
            flags.append("true peak %.2f" % tp)
        if i is not None and i > -7.0:
            flags.append("hot %.1f LUFS" % i)
        if fz > 1.5:
            flags.append("frozen tail %.1fs" % fz)
        print("%-34s %6.1f %6.1f %8s %8s %6.1f  %s"
              % (name, v or 0, a or 0,
                 "%.2f" % i if i is not None else "-",
                 "%.2f" % tp if tp is not None else "-", fz,
                 "; ".join(flags)))
        if flags:
            bad.append((name, flags))
    print("\n%d masters, %d with something to look at" % (len(files), len(bad)))
    for n, f in bad:
        print("   %-34s %s" % (n, "; ".join(f)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
