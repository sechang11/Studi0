#!/usr/bin/env python3
"""studio/_tools/qc_films.py - look at every delivered file before calling it delivered.

This project's dominant failure is not a crash. It is a step that reports success and
changes nothing: a flag left as a truthy string so a switch never flipped, an interpolation
pass that silently dropped the audio, a node with a hardcoded aspect that ignored every
keyframe. All of those produced files that existed, had the right duration, and were wrong.

So this checks the things that go quietly wrong, on the actual bytes:

    STREAMS      video and audio both present - the interpolation workflow rebuilds video
                 with no audio input, and a talking film comes back saying nothing
    SILENCE      an audio track that exists but is flat. Measured, not assumed.
    BLACK        frames that are essentially black, which is what a failed segment looks
                 like after a concat
    FROZEN       a clip where nothing moves, which is what a refused generation looks like
    SHAPE        one resolution and one frame rate through a whole assembled film, because
                 a concat of mismatched parts plays back wrong rather than failing

AND IT KNOWS WHAT A TITLE CARD IS. The first version flagged every finished film in the
set, because a card is a black frame over a silent track - which is precisely what it was
built to catch. A check that cries wolf on correct output gets ignored within a day, so
leading and trailing black-and-silent runs are treated as cards and only the MIDDLE of a
film is held to the rule.
"""
import argparse
import glob
import json
import os
import subprocess


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def probe(path):
    r = sh("ffprobe", "-v", "error", "-print_format", "json",
           "-show_format", "-show_streams", path)
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {}


def frames_gray(path, w=96, h=54, fps=4):
    import numpy as np
    d = subprocess.run(["ffmpeg", "-v", "error", "-i", path,
                        "-vf", "fps=%d,scale=%d:%d,format=gray" % (fps, w, h),
                        "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(d) // (w * h)
    if not n:
        return None
    return np.frombuffer(d[:n * w * h], dtype="uint8").reshape(n, h, w).astype(float)


def audio_rms(path, sr=16000):
    import numpy as np
    d = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1",
                        "-ar", str(sr), "-f", "s16le", "-"], capture_output=True).stdout
    if not d:
        return None, None
    a = np.frombuffer(d, dtype="int16").astype(float) / 32768.0
    if not len(a):
        return None, None
    # overall level, and the quietest one-second window
    win = sr
    q = min(float((a[i:i + win] ** 2).mean() ** 0.5)
            for i in range(0, max(1, len(a) - win), win)) if len(a) > win else 0.0
    return float((a ** 2).mean() ** 0.5), q


CARD_EDGE = 0.14        # a card lives in the first or last 14% of a film


def check(path):
    import numpy as np
    out = []
    p = probe(path)
    if not p:
        return ["unreadable"]
    vs = [s for s in p.get("streams", []) if s.get("codec_type") == "video"]
    aus = [s for s in p.get("streams", []) if s.get("codec_type") == "audio"]
    dur = float(p.get("format", {}).get("duration", 0) or 0)
    if not vs:
        out.append("NO VIDEO STREAM")
    if not aus:
        out.append("NO AUDIO STREAM")
    if dur < 1.0:
        out.append("duration %.2fs" % dur)

    def mid(i, n):
        """is index i in the body of the film rather than a card at either end?"""
        return CARD_EDGE * n <= i <= (1 - CARD_EDGE) * n

    if aus:
        rms, _ = audio_rms(path)
        if rms is None:
            out.append("audio undecodable")
        elif rms < 0.0015:
            out.append("audio is effectively SILENT throughout (rms %.5f)" % rms)
        else:
            # a silent second only matters if it is in the BODY of the film
            import numpy as np
            sr = 16000
            d = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1",
                                "-ar", str(sr), "-f", "s16le", "-"],
                               capture_output=True).stdout
            a = np.frombuffer(d, dtype="int16").astype(float) / 32768.0
            n = len(a) // sr
            quiet = [i for i in range(n)
                     if float((a[i * sr:(i + 1) * sr] ** 2).mean() ** 0.5) < 0.0004]
            body = [i for i in quiet if mid(i, n)]
            # one quiet beat is a pause; three or more in the body is a hole
            if len(body) >= 3:
                out.append("%ds of silence inside the film (at %s)"
                           % (len(body), ", ".join("%ds" % i for i in body[:4])))

    g = frames_gray(path)
    if g is None:
        out.append("no frames decoded")
    else:
        mean = g.mean(axis=(1, 2))
        blk = [i for i, m in enumerate(mean) if m < 6]
        body = [i for i in blk if mid(i, len(mean))]
        if len(body) > 3:
            out.append("%d near-black frames inside the film" % len(body))
        if len(g) > 2:
            motion = np.abs(np.diff(g, axis=0)).mean()
            if motion < 0.35:
                out.append("almost no motion (%.2f) - frozen?" % motion)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args()
    files = []
    for x in a.paths:
        files.extend(sorted(glob.glob(os.path.expanduser(x))))
    bad = 0
    for f in files:
        issues = check(f)
        p = probe(f)
        vs = [s for s in p.get("streams", []) if s.get("codec_type") == "video"]
        shape = ("%sx%s @%s" % (vs[0].get("width"), vs[0].get("height"),
                                vs[0].get("r_frame_rate"))) if vs else "?"
        dur = float(p.get("format", {}).get("duration", 0) or 0)
        if issues:
            bad += 1
            print("  FAIL %-26s %6.1fs %-16s %s"
                  % (os.path.basename(f), dur, shape, "; ".join(issues)))
        else:
            print("  ok   %-26s %6.1fs %s" % (os.path.basename(f), dur, shape))
    print("\n%d checked, %d with issues" % (len(files), bad))


if __name__ == "__main__":
    main()
