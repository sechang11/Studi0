#!/usr/bin/env python3
"""studio/_tools/shorts_deliver.py - collect the finished slate into one folder a human
can open, and put it in the library.

    python3 studio/_tools/shorts_deliver.py [--out studio/samples/shorts]

WHAT IT MAKES
    shorts/
      supplement/ commercial/ hook/     the masters, named <id>__<TITLE>.mp4
      contact/                          a frame strip per film - the thing you scan first
      shorts.json                       one row per film: id, kind, title, hook, seconds,
                                        LUFS, shot count, spoken lines, captions, the
                                        script, and the path
      INDEX.md                          the same table, readable, with the scripts under it
      recipes beside every master        so the library indexes them like any other frame

The masters are COPIED, not moved: ComfyUI's output tree is where short.py archives
previous versions, and moving a master out from under that would break the
archive-not-clobber rule the cutter relies on.

Library: each master gets a recipe JSON beside it in samples/, which is what
library_index discovers - so the slate appears in /library filtered by collection
`shorts`, with its prompt, voice, cue and measurements on the detail panel, like
everything else this project makes.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
COMFY = os.environ.get("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
SHORTS_JSON = os.path.join(ROOT, "films", "shorts")
SHORTS_OUT = os.path.join(COMFY, "output", "claude-generated", "12-shorts")


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def probe(p):
    out = {}
    r = sh("ffprobe", "-v", "error", "-show_entries",
           "stream=codec_type,width,height:format=duration,size", "-of", "default=nw=1", p)
    txt = r.stdout or ""
    m = re.search(r"duration=([\d.]+)", txt)
    if m:
        out["seconds"] = round(float(m.group(1)), 1)
    m = re.search(r"width=(\d+)\s*\nheight=(\d+)", txt)
    if m:
        out["size"] = "%sx%s" % (m.group(1), m.group(2))
    m = re.search(r"size=(\d+)", txt)
    if m:
        out["mb"] = round(int(m.group(1)) / 1e6, 1)
    # loudness, from the summary block (the running I: line lies - see audio_sweep)
    r = sh("ffmpeg", "-nostats", "-i", p, "-af", "ebur128=peak=true", "-f", "null", "-")
    err = r.stderr or ""
    summ = err.split("Summary:", 1)[1] if "Summary:" in err else ""
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", summ)
    if m:
        out["lufs"] = float(m.group(1))
    m = re.search(r"Peak:\s+(-?[\d.]+) dBFS", summ)
    if m:
        out["true_peak"] = float(m.group(1))
    return out


STITCH_DOC = """# Hook transitions: open on an existing clip, whip into one of these

Two different things both get called a "hook", and you have both.

## 1. The six hook-* films in `hook/`

These are complete films that open on their own hook. The grammar of a stitch without
anybody else's footage in them - a cold first line, a hard turn, a payoff. Post them
as they are.

## 2. Putting a clip you already have in FRONT of any of these

That is `stitch_hook.py`, and it needs one thing this folder cannot contain: the lead
clip. It has to be footage you have the right to use - your own, licensed, or public
domain. The tool does not ship any and will not go looking. The reusable part of
somebody else's video is its grammar, not its frames.

    cd ~/shared/comfy-studio
    python3 studio/_tools/stitch_hook.py --lead /path/to/your_clip.mp4 \\
        --into films/shorts/ad-atlas-pack.json

Useful flags:

    --seconds 2.5        how much of the lead to use (default 2.0)
    --from-seconds 4     start that far into the lead, to skip a slate or a slow start
    --transition whip_pan   or dip_black, flash, cross, slide_l, slide_r, hard
    --out /path/out.mp4  default lands in studio/samples/shorts/stitched/

What it does for you, each one a thing that goes wrong by hand:

- **format match** - the lead is cropped and scaled to the film's canvas, so a landscape
  clip does not letterbox into a different shape than the piece it introduces
- **level match** - the lead is measured and normalised to the film's own loudness,
  two-pass. Single-pass loudnorm works blind and measured 7 LU off on this machine.
  Verified: a -19.7 LUFS lead joined a -9.8 LUFS film and came out at -10.0
- **one transition language** - the join uses the same transition cards the cutter uses
  inside a film, so a stitch and a cut are the same vocabulary
- **it re-measures the result** and tells you if the audio does not cover the picture

Tested end to end on our own deck3 clip into the ATLAS commercial: 13.2s, 1080x1920,
-10.0 LUFS.
"""


def main():
    ap = argparse.ArgumentParser(description="Collect and index the short-form slate.")
    ap.add_argument("--out", default=os.path.join(STUDIO, "samples", "shorts"))
    ap.add_argument("--share", default=os.path.expanduser("~/shared/SHORTS"),
                    help="flat copy on the SMB share (Z:/shared/SHORTS from Windows)")
    a = ap.parse_args()
    rows = []
    for fn in sorted(os.listdir(SHORTS_JSON)):
        if not fn.endswith(".json"):
            continue
        fid = fn[:-5]
        film = json.load(open(os.path.join(SHORTS_JSON, fn), encoding="utf-8"))
        slug = film["title"].lower().replace(" ", "-")
        master = os.path.join(SHORTS_OUT, slug, "%s.mp4" % slug)
        if not os.path.exists(master):
            rows.append({"id": fid, "kind": film.get("kind"), "title": film["title"],
                         "status": "not rendered"})
            continue
        kind = film.get("kind", "other")
        kd = os.path.join(a.out, kind)
        os.makedirs(kd, exist_ok=True)
        os.makedirs(os.path.join(a.out, "contact"), exist_ok=True)
        dst = os.path.join(kd, "%s__%s.mp4" % (fid, film["title"].replace(" ", "_")))
        shutil.copy(master, dst)
        strip = os.path.join(a.out, "contact", "%s.jpg" % fid)
        sh("ffmpeg", "-y", "-v", "error", "-i", dst, "-vf",
           "fps=1,scale=150:-2,tile=10x2", "-frames:v", "1", strip)
        m = probe(dst)
        lines = [b["line"]["text"] for b in film["beats"] if b.get("line")]
        caps = [b.get("caption") for b in film["beats"] if b.get("caption")]
        row = {"id": fid, "kind": kind, "title": film["title"],
               "hook": film.get("hook", "").replace("|", " / "),
               "status": "ready", "file": os.path.relpath(dst, STUDIO),
               "contact": os.path.relpath(strip, STUDIO),
               "beats": len(film["beats"]), "voice": film["voices"]["V"]["voice"],
               "music_tags": film["music"][0]["tags"][:80], "script": lines,
               "captions": caps, **m}
        rows.append(row)
        # the recipe the library indexes, beside the master
        rec = {"id": fid, "domain": "video", "collection": "shorts", "kind_of": kind,
               "title": film["title"], "prompt": " | ".join(caps),
               "engine": "qwen keyframes + LTX-2.3 i2v", "style": film["style"][:200],
               "voice": os.path.basename(film["voices"]["V"]["voice"]),
               "seconds": m.get("seconds"), "lufs": m.get("lufs"),
               "line": " ".join(lines)[:600], "rolled_at": None,
               "note": "short-form slate, %s" % kind}
        with open(os.path.splitext(dst)[0] + ".json", "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=1, ensure_ascii=False)
        print("%-22s %-11s %5.1fs %6.1f LUFS  %s" % (fid, kind, m.get("seconds") or 0,
                                                     m.get("lufs") or 0,
                                                     os.path.basename(dst)))

    json.dump(rows, open(os.path.join(a.out, "shorts.json"), "w"), indent=1)
    ready = [r for r in rows if r.get("status") == "ready"]
    md = ["# Short-form slate", "",
          "%d of %d rendered. Masters are vertical 1080x1920 with voice, score and "
          "effects mixed and mastered." % (len(ready), len(rows)), "",
          "| id | kind | title | secs | LUFS | hook |", "|---|---|---|---|---|---|"]
    for r in rows:
        md.append("| %s | %s | %s | %s | %s | %s |"
                  % (r["id"], r.get("kind", ""), r.get("title", ""),
                     r.get("seconds", "-"), r.get("lufs", "-"), r.get("hook", "")))
    md += ["", "## Scripts", ""]
    for r in ready:
        md += ["### %s - %s" % (r["id"], r["title"]), ""]
        md += ["- %s" % l for l in r["script"]]
        md += [""]
    io_path = os.path.join(a.out, "INDEX.md")
    open(io_path, "w", encoding="utf-8").write("\n".join(md))
    open(os.path.join(a.out, "STITCH.md"), "w", encoding="utf-8").write(STITCH_DOC)
    # A second, flat copy where a person will actually look for it.
    if a.share:
        for r in ready:
            src = os.path.join(STUDIO, r["file"])
            kd = os.path.join(a.share, r["kind"])
            os.makedirs(kd, exist_ok=True)
            shutil.copy(src, os.path.join(kd, os.path.basename(src)))
            s = os.path.join(STUDIO, r["contact"])
            if os.path.exists(s):
                cd = os.path.join(a.share, "contact")
                os.makedirs(cd, exist_ok=True)
                shutil.copy(s, os.path.join(cd, os.path.basename(s)))
        for extra in ("INDEX.md", "STITCH.md", "shorts.json"):
            p = os.path.join(a.out, extra)
            if os.path.exists(p):
                shutil.copy(p, os.path.join(a.share, extra))
        print("share copy: %s" % a.share)
    print("\n%d ready, %d not rendered -> %s" % (len(ready), len(rows) - len(ready), a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
