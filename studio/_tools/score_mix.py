#!/usr/bin/env python3
"""studio/_tools/score_mix.py - a SCORE under a cut, music forward (2026-10-05).

The casting tool's mix_under() lets the takes' own sound lead and ducks the score hard under it (sidechain ratio 6 from
a threshold of 0.03 - everything ducks it). Under THE FIRE ESPER, whose cut also carries three sound beds (a rumble, a
forest fire, wind in ash), the score sat ~15 dB under the effects and pumped with them; the director: "it doesn't
sound like music as I'm used to - there's some sound effect stuff going on in there". Here the score leads:
  music  levelled to MUSIC_LUFS (-16), faded out at its end or the picture's
  sfx    the takes' own sound ALONE (glue_cut.py's <film>_sfx.wav - no beds: under music the music is the glue),
         SFX_DB under its own level (-1: the score sits ~5 dB over the effects on average)
  duck   a gentle sidechain from the sfx (ratio 2 from -18 dBFS): only the big hits push the music down, a few dB
then the whole levelled to -15 LUFS, true peak -1.5, the picture copied.
    python3 studio/_tools/score_mix.py VIDEO SFX.wav MUSIC OUT.mp4 [--music-lufs -16] [--sfx-db -1] [--duck 2]
"""
import argparse
import json
import subprocess
import sys


def sh(*cmd):
    try:
        r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        sys.exit("timed out: %s" % " ".join(str(c) for c in cmd[:6]))
    if r.returncode != 0:
        sys.exit("failed: %s\n%s" % (" ".join(str(c) for c in cmd[:6]), r.stderr[-1200:]))
    return r


def dur(p):
    return float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p).stdout.strip())


def lufs(p, af=""):
    r = subprocess.run(["ffmpeg", "-v", "info", "-nostats", "-i", p, "-af", (af + "," if af else "") + "ebur128",
                        "-f", "null", "-"], capture_output=True, text=True)
    for line in r.stderr.splitlines()[::-1]:
        if line.strip().startswith("I:"):
            return float(line.split()[1])
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("sfx")
    ap.add_argument("music")
    ap.add_argument("out")
    ap.add_argument("--music-lufs", type=float, default=-16.0)
    ap.add_argument("--sfx-db", type=float, default=-1.0, help="the takes' sound against its own level (-1: the "
                    "score ~5 dB over it on average, the hits still through)")
    ap.add_argument("--duck", type=float, default=2.0, help="sidechain ratio (1 = no ducking)")
    ap.add_argument("--fade", type=float, default=2.5)
    a = ap.parse_args()
    total = dur(a.video)
    end = min(total, dur(a.music))
    graph = ("[2:a]aformat=sample_rates=48000:channel_layouts=stereo,loudnorm=I=%.1f:TP=-2:LRA=14,"
             "afade=t=out:st=%.3f:d=%.2f[m];"
             "[1:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=%.1fdB,asplit=2[sc][fx];"
             "[m][sc]sidechaincompress=threshold=0.125:ratio=%.2f:attack=20:release=300[md];"
             "[fx][md]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-15:TP=-1.5:LRA=11,aresample=48000[a]" % (
                 a.music_lufs, max(0.0, end - a.fade), a.fade, a.sfx_db, max(1.0, a.duck)))
    sh("ffmpeg", "-y", "-v", "error", "-i", a.video, "-i", a.sfx, "-i", a.music, "-filter_complex", graph,
       "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t",
       "%.3f" % total, a.out)
    # how the two sit against each other before the final levelling (integrated loudness of each, as mixed)
    m = lufs(a.music, "aformat=channel_layouts=stereo,loudnorm=I=%.1f:TP=-2:LRA=14" % a.music_lufs)
    s = lufs(a.sfx, "volume=%.1fdB" % a.sfx_db)
    print(json.dumps({"out": a.out, "music_lufs": m, "sfx_lufs": s,
                      "music_over_sfx_db": round(m - s, 1) if (m is not None and s is not None) else None}))


if __name__ == "__main__":
    main()
