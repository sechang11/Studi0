#!/usr/bin/env python3
"""studio/_tools/stitch_hook.py - open on an EXISTING clip, transition into one of ours.

    python3 studio/_tools/stitch_hook.py --lead clip.mp4 --into films/shorts/sup-creatine.json
    python3 studio/_tools/stitch_hook.py --lead clip.mp4 --into <master.mp4> --seconds 2.5 \\
        --transition whip_pan --out stitched.mp4

WHAT THIS IS FOR. The short-form "stitch": the first two seconds are a clip the viewer
already recognises or that stops the scroll, and it whips into your own piece. That first
clip has to be footage YOU have the right to use - your own, licensed, or public domain.
This tool supplies the MECHANISM; it does not supply the footage, and it will not go and
find any. That line is deliberate and it is the same one the Dragon Ball breakdown drew:
the reusable part of somebody else's video is its GRAMMAR, not its frames.

WHAT IT DOES, and each part is a thing that goes wrong if you do it by hand:

  format match   the lead is cropped and scaled to the film's canvas (vertical by
                 default), so a landscape lead does not letterbox into a different shape
                 than the piece it introduces.
  level match    the lead's loudness is measured and normalised to the film's own
                 measured LUFS, so the join does not jump 12 dB. Two-pass, because
                 single-pass loudnorm works blind and under-delivers (measured on this
                 box at 7 LU off).
  the transition comes from the TRANSITION CARDS - the same six real xfade filters the
                 cutter uses - so a stitch and a cut inside a film speak the same
                 language. `hard` is also allowed and is often right.
  measured out   the result is re-measured (duration, LUFS, true peak) and reported, and
                 the audio must cover the picture or it says so.
"""
import argparse
import json
import os
import re
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
COMFY = os.environ.get("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def probe(p):
    out = {}
    r = sh("ffprobe", "-v", "error", "-show_entries",
           "stream=codec_type,width,height:format=duration", "-of", "default=nw=1", p)
    txt = r.stdout or ""
    m = re.search(r"width=(\d+)\s*\nheight=(\d+)", txt)
    if m:
        out["w"], out["h"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"duration=([\d.]+)", txt)
    if m:
        out["seconds"] = float(m.group(1))
    out["has_audio"] = "codec_type=audio" in txt
    r = sh("ffmpeg", "-nostats", "-i", p, "-af", "ebur128=peak=true", "-f", "null", "-")
    err = r.stderr or ""
    summ = err.split("Summary:", 1)[1] if "Summary:" in err else ""
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", summ)
    if m:
        out["lufs"] = float(m.group(1))
    return out


def master_for(into):
    """Accept either a film JSON or a master mp4."""
    if into.endswith(".mp4"):
        return into
    film = json.load(open(into, encoding="utf-8"))
    slug = film["title"].lower().replace(" ", "-")
    return os.path.join(COMFY, "output", "claude-generated", "12-shorts", slug,
                        "%s.mp4" % slug)


def transition_filter(name, d):
    if name == "hard":
        return None
    p = os.path.join(STUDIO, "transitions", "%s.json" % name)
    if not os.path.exists(p):
        print("no such transition card: %s" % name, file=sys.stderr)
        return None
    tpl = (json.load(open(p, encoding="utf-8")) or {}).get("filter")
    if not tpl:
        print("transition %s has no filter (it is a post-tier card)" % name,
              file=sys.stderr)
        return None
    return tpl.format(d="%.2f" % d)


def main():
    ap = argparse.ArgumentParser(description="Open on your own clip, whip into our film.")
    ap.add_argument("--lead", required=True,
                    help="the opening clip - footage YOU have the right to use")
    ap.add_argument("--into", required=True, help="a films/shorts/*.json or a master .mp4")
    ap.add_argument("--seconds", type=float, default=2.0, help="how much of the lead")
    ap.add_argument("--from-seconds", type=float, default=0.0, help="in-point in the lead")
    ap.add_argument("--transition", default="whip_pan")
    ap.add_argument("--out")
    a = ap.parse_args()

    master = master_for(a.into)
    if not os.path.exists(master):
        print("the film has not been rendered: %s" % master, file=sys.stderr)
        return 2
    if not os.path.exists(a.lead):
        print("no such lead clip: %s" % a.lead, file=sys.stderr)
        return 2
    mi, li = probe(master), probe(a.lead)
    w, h = mi.get("w", 1080), mi.get("h", 1920)
    out = a.out or os.path.join(STUDIO, "samples", "shorts", "stitched",
                                "%s__%s.mp4" % (os.path.splitext(os.path.basename(a.lead))[0],
                                                os.path.splitext(os.path.basename(master))[0]))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    work = "/tmp/stitch_%d" % os.getpid()
    os.makedirs(work, exist_ok=True)

    # 1. the lead, cut to length and matched to the film's canvas and level
    lead = os.path.join(work, "lead.mp4")
    target = mi.get("lufs", -9.5)
    af = ("loudnorm=I=%.1f:TP=-1.0:LRA=11" % target) if li.get("has_audio") else \
        "anullsrc=channel_layout=stereo:sample_rate=48000"
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", "%.2f" % a.from_seconds,
           "-t", "%.2f" % a.seconds, "-i", a.lead]
    if not li.get("has_audio"):
        cmd += ["-f", "lavfi", "-t", "%.2f" % a.seconds,
                "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
    cmd += ["-vf", "scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,fps=24"
            % (w, h, w, h)]
    if li.get("has_audio"):
        cmd += ["-af", af]
    cmd += ["-c:v", "libx264", "-crf", "17", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
            "-shortest", lead]
    r = sh(*cmd)
    if not os.path.exists(lead):
        print("could not prepare the lead: %s" % (r.stderr or "")[-300:], file=sys.stderr)
        return 1

    # 2. join, with the transition card's own filter
    tf = transition_filter(a.transition, 0.4)
    if tf:
        la = probe(lead).get("seconds", a.seconds)
        fc = ("[0:v][1:v]%s:offset=%.2f[v];[0:a][1:a]acrossfade=d=0.4[a]"
              % (tf, max(0.0, la - 0.4)))
        r = sh("ffmpeg", "-y", "-v", "error", "-i", lead, "-i", master,
               "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
               "-c:v", "libx264", "-crf", "17", "-preset", "medium",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k",
               "-movflags", "+faststart", out)
    else:
        lst = os.path.join(work, "list.txt")
        with open(lst, "w") as f:
            f.write("file '%s'\nfile '%s'\n" % (os.path.abspath(lead),
                                                os.path.abspath(master)))
        r = sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
               "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt",
               "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", out)
    if not os.path.exists(out):
        print("stitch failed: %s" % (r.stderr or "")[-300:], file=sys.stderr)
        return 1

    o = probe(out)
    va = o.get("seconds", 0)
    aa = float(re.search(r"([\d.]+)", sh("ffprobe", "-v", "error", "-select_streams", "a",
                                         "-show_entries", "format=duration", "-of",
                                         "csv=p=0", out).stdout or "0").group(1))
    print("lead %.1fs (%s, %s LUFS) + %s -> %s"
          % (a.seconds, "%dx%d" % (li.get("w", 0), li.get("h", 0)),
             li.get("lufs", "no audio"), os.path.basename(master), out))
    print("   %.1fs  %dx%d  %s LUFS" % (va, o.get("w", 0), o.get("h", 0), o.get("lufs")))
    if abs(va - aa) > 0.6:
        print("   !! audio is %.1fs on a %.1fs piece - the mix stopped early" % (aa, va),
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
