#!/usr/bin/env python3
"""/shorts - watch the slate, with what each film measures beside it.

    "have the next version for me and i'll give you pointers"

There has never been a page for the films. Reviewing them has meant a network share, a
file manager and remembering which one was which, and the pointers that came back were
necessarily about whichever ones got opened. This puts all of them on one page, playing,
each labelled with its look template and its measurements, so a note can be attached to a
film rather than to an impression.

WHAT IS SHOWN, and deliberately only what has an instrument behind it:

    luma        mean brightness 0-255 over every frame (dark_slate)
    saturation  mean HSV saturation over sampled frames (vibrancy)
    shots       delivered cuts, from the cutter's own slice files - not detected
    look        the director's-note template the film wears

No quality score. Nothing here knows whether a film is good, and a number pretending to
would be worse than the empty column - the whole point of the page is to get a human
verdict that no instrument can supply.
"""
import io
import json
import os
import re
import subprocess

STUDIO = "studio"
V5 = os.path.expanduser("~/shared/SHORTS-v5")
OUT = os.path.join(STUDIO, "samples", "shorts_v5")
INDEX = os.path.join(STUDIO, "samples", "shorts_v5.json")
WORK = os.path.expanduser("~/ComfyUI/output/claude-generated/12-shorts")
SLICE = re.compile(r"^\d{4}_.+_\d+\.mp4$")


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def luma_and_sat(path):
    import colorsys
    from PIL import Image
    r = sh("ffprobe", "-v", "error", "-f", "lavfi",
           "-i", "movie=%s,signalstats" % path.replace(":", "\\:"),
           "-show_entries", "frame_tags=lavfi.signalstats.YAVG",
           "-of", "default=nw=1:nk=1")
    ys = [float(x) for x in (r.stdout or "").split() if x.strip()]
    sats = []
    for t in (2, 6, 10):
        f = "/tmp/_ss.png"
        sh("ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1", f)
        if not os.path.exists(f):
            continue
        im = Image.open(f).convert("RGB").resize((120, 160))
        px = list(im.getdata())
        s = [colorsys.rgb_to_hsv(a / 255.0, b / 255.0, c / 255.0)[1] for a, b, c in px]
        sats.append(sum(s) / len(s))
    return (sum(ys) / len(ys) if ys else None,
            sum(sats) / len(sats) if sats else None)


def shots_of(title):
    d = os.path.join(WORK, title, "_work")
    if not os.path.isdir(d):
        return None
    return len([f for f in os.listdir(d) if SLICE.match(f)]) or None


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for p in sorted(os.listdir(V5)) if os.path.isdir(V5) else []:
        if not p.endswith(".mp4"):
            continue
        slug = p[:-4]
        src = os.path.join(V5, p)
        spec = os.path.join("films", "shorts", slug + ".json")
        film = (json.loads(io.open(spec, encoding="utf-8").read())
                if os.path.exists(spec) else {})
        title = (film.get("title") or slug).lower().replace(" ", "-")
        # a poster and a web-sized copy; the originals are 5-17 MB each
        poster = os.path.join(OUT, slug + ".jpg")
        sh("ffmpeg", "-y", "-v", "error", "-ss", "2", "-i", src, "-vf", "scale=360:-2",
           "-frames:v", "1", poster)
        web = os.path.join(OUT, slug + ".mp4")
        if not os.path.exists(web):
            sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vf", "scale=540:-2",
               "-c:v", "libx264", "-crf", "30", "-preset", "veryfast",
               "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", web)
        lu, sa = luma_and_sat(src)
        rows.append({
            "slug": slug, "title": film.get("title") or slug,
            "hook": film.get("hook", ""),
            "look": film.get("look_template"),
            "kind": ("hook" if slug.startswith("hook") else
                     "supplement" if slug.startswith("sup") else "commercial"),
            "video": "/samples/shorts_v5/%s.mp4" % slug,
            "poster": "/samples/shorts_v5/%s.jpg" % slug,
            "luma": round(lu, 1) if lu else None,
            "sat": round(sa, 3) if sa else None,
            "shots": shots_of(title),
            "lines": [str((b.get("line") or {}).get("text") or "")
                      for b in film.get("beats", []) if (b.get("line") or {}).get("text")],
        })
        print("  %-22s luma %-6s sat %-6s shots %s"
              % (slug, rows[-1]["luma"], rows[-1]["sat"], rows[-1]["shots"]))

    io.open(INDEX, "w", encoding="utf-8", newline="\n").write(json.dumps({
        "note": ("The delivered slate, with what each film measures. No quality score - "
                 "nothing here knows whether a film is good."),
        "films": rows}, indent=1, ensure_ascii=False) + "\n")
    print("\n%d films -> %s" % (len(rows), INDEX))


if __name__ == "__main__":
    main()
