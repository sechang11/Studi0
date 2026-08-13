#!/usr/bin/env python3
"""studio/_tools/breakdown.py - take a video apart into a reusable SHOT GRAMMAR card.

    python3 studio/_tools/breakdown.py ref.mp4 --id upside_down_exit
    python3 studio/_tools/breakdown.py ref.mp4 --id foo --from 4.6 --to 8.8
    python3 studio/_tools/breakdown.py --list

WHAT IT TAKES, AND WHAT IT DELIBERATELY DOES NOT.

It takes STRUCTURE: how many shots, how long each one holds, where the cuts land relative
to motion, how much movement is in each shot, whether it gets brighter or darker. That is
film grammar - the same class of thing as a shot list or a beat sheet. It is what makes a
four-second sequence read as a backflip out of a window when no such action was ever
generated.

It does NOT take the pictures. No frame of the source is copied into the card, and the
card cannot reconstruct the source. The reference footage stays in _refs/ as a scratch
contact sheet for a human to look at while filling in the craft notes, and nothing in the
studio ever reads from it. What ships is timings and intent.

That distinction is the whole point. A sequence card says "five shots in 4.2 seconds, each
about 1.2s, cut on the fastest motion, scale tightening then releasing" - and that sentence
belongs to nobody. Your cast, your style, your place go in the slots.

WHAT IT MEASURES vs WHAT A PERSON FILLS IN. Cut times, durations, motion energy and
brightness are measured. Shot SCALE and what the subject is doing are not - estimating
"medium close-up" from pixels is a guess, and this project has enough tools that report
guesses as measurements. Those fields come back empty with a note, for whoever is looking
at the contact sheet to write.
"""
import argparse, glob, json, os, re, subprocess, sys, time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
CARDS = os.path.join(STUDIO, "sequences")
REFS = os.path.join(STUDIO, "samples", "_refs")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")[:48]


def ff(*a, **kw):
    return subprocess.run(["ffmpeg", "-hide_banner"] + list(a),
                          capture_output=True, text=True, **kw)


def probe(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=width,height,r_frame_rate", "-of", "json", path],
        capture_output=True, text=True)
    d = json.loads(r.stdout or "{}")
    st = (d.get("streams") or [{}])[0]
    num, _, den = (st.get("r_frame_rate") or "0/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 0.0
    return {"duration": float((d.get("format") or {}).get("duration") or 0),
            "width": st.get("width"), "height": st.get("height"),
            "fps": round(fps, 3)}


def cuts(path, thresh, t0, t1):
    """Scene-change timestamps. The threshold is recorded on the card, because a different
    threshold gives a different shot count and a card that does not say which was used
    cannot be reproduced."""
    # SCAN THE WHOLE FILE, then filter by range. Using -ss as an input seek makes the
    # reported pts_time ambiguous - some builds rebase it to zero, some keep the original
    # timeline - so adding t0 back is a guess that is wrong half the time. It was wrong
    # here: a range with four known cuts came back with none, and the card claimed the
    # 6.8-second sequence was a single unbroken shot. Scanning whole costs a few seconds
    # and cannot be misinterpreted.
    # NO -v error HERE. showinfo logs at INFO level, so quieting ffmpeg to `error`
    # silences the very output being parsed - the filter still runs, finds every cut, and
    # reports nothing. The card then claims a five-shot sequence is one unbroken take.
    # This project already has a checker for this exact pattern; I walked into it anyway.
    r = ff("-i", path, "-filter:v",
           "select='gt(scene,%s)',showinfo" % thresh, "-f", "null", "-")
    out = []
    for m in re.finditer(r"pts_time:([0-9.]+)", r.stderr or ""):
        c = round(float(m.group(1)), 3)
        if (t0 is None or c > t0) and (t1 is None or c < t1):
            out.append(c)
    return sorted(set(out))


def motion(path, a, b):
    """Mean absolute frame difference over a shot - 'how much is moving', 0-100.

    A cut that lands on high motion is the trick this whole card type exists to record:
    it is what lets five unrelated clips read as one impossible action.
    """
    r = ff("-v", "error", "-ss", str(a), "-t", str(max(0.1, b - a)), "-i", path,
           "-vf", "scale=160:-1,tblend=all_mode=difference,signalstats,"
                  "metadata=print:file=-", "-f", "null", "-")
    vals = [float(m.group(1)) for m in
            re.finditer(r"lavfi\.signalstats\.YAVG=([0-9.]+)", r.stdout or "")]
    return round(sum(vals) / len(vals), 2) if vals else None


def luma(path, a, b):
    r = ff("-v", "error", "-ss", str(a), "-t", str(max(0.1, b - a)), "-i", path,
           "-vf", "scale=160:-1,signalstats,metadata=print:file=-", "-f", "null", "-")
    vals = [float(m.group(1)) for m in
            re.finditer(r"lavfi\.signalstats\.YAVG=([0-9.]+)", r.stdout or "")]
    return round(sum(vals) / len(vals), 1) if vals else None


def sheet(path, shots, sid):
    """A contact sheet of the REFERENCE, for a human to look at while writing the craft
    notes. Scratch material: it lives outside the card and nothing reads it at render
    time."""
    os.makedirs(REFS, exist_ok=True)
    d = os.path.join(REFS, sid)
    os.makedirs(d, exist_ok=True)
    for i, s in enumerate(shots, 1):
        mid = (s["at"] + s["until"]) / 2.0
        ff("-v", "error", "-ss", str(mid), "-i", path, "-frames:v", "1",
           "-vf", "scale=360:-1", "-q:v", "4",
           os.path.join(d, "%02d.jpg" % i), "-y")
    n = len(shots)
    cols = min(6, max(1, n))
    rows = (n + cols - 1) // cols
    out = os.path.join(d, "_sheet.jpg")
    ff("-v", "error", "-i", os.path.join(d, "%02d.jpg"), "-frames:v", "1",
       "-vf", "scale=360:-1,tile=%dx%d:margin=3:padding=3:color=0x14161a" % (cols, rows),
       "-q:v", "4", out, "-y")
    return out if os.path.isfile(out) else None


def build(path, sid, thresh, t0, t1, note):
    info = probe(path)
    end = t1 or info["duration"]
    start = t0 or 0.0
    cs = [c for c in cuts(path, thresh, t0, t1) if start < c < end]
    bounds = [start] + cs + [end]
    shots = []
    for i in range(len(bounds) - 1):
        a, b = bounds[i], bounds[i + 1]
        if b - a < 0.15:
            continue
        shots.append({
            "n": len(shots) + 1,
            "at": round(a - start, 2), "until": round(b - start, 2),
            "seconds": round(b - a, 2),
            "motion": motion(path, a, b),
            "luma": luma(path, a, b),
            # Left for a person, with the reason. Guessing shot scale from pixels is a
            # guess, and a guess written into a measured field is how a library starts
            # lying to itself.
            "framing": "", "subject": "", "camera": "", "note": "",
        })
    if not shots:
        return None
    secs = [s["seconds"] for s in shots]
    secs_sorted = sorted(secs)
    med = secs_sorted[len(secs_sorted) // 2]
    return {
        "id": sid,
        "kind": "sequence",
        "shots": len(shots),
        "seconds": round(end - start, 2),
        "median_shot": round(med, 2),
        "mean_shot": round(sum(secs) / len(secs), 2),
        "shortest": round(min(secs), 2), "longest": round(max(secs), 2),
        "cuts_per_minute": round(len(shots) / ((end - start) / 60.0), 1),
        "beats": shots,
        "measured_with": {"scene_threshold": thresh, "source_fps": info["fps"],
                          "source_size": "%sx%s" % (info["width"], info["height"])},
        "note": note or "",
        "how_to_use": ("Each beat is a slot. Put your own character, style and place in it and "
                       "render each beat as its own clip at the given length, then cut them "
                       "together in order. The card carries TIMING AND INTENT ONLY - no "
                       "frame of the reference is in it, and it cannot reconstruct the "
                       "source."),
        "provenance": ("Structure measured from a reference the operator supplied. Shot "
                       "lengths and cut placement are craft, not content - the imagery, "
                       "characters and design of the source are NOT here and must not be "
                       "reproduced. Cast it with your own."),
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", nargs="?")
    ap.add_argument("--id")
    ap.add_argument("--from", dest="t0", type=float)
    ap.add_argument("--to", dest="t1", type=float)
    ap.add_argument("--threshold", type=float, default=0.30)
    ap.add_argument("--note", default="")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    os.makedirs(CARDS, exist_ok=True)
    if a.list or not a.video:
        cs = sorted(glob.glob(os.path.join(CARDS, "*.json")))
        for p in cs:
            c = json.load(open(p, encoding="utf-8"))
            print("  %-26s %2d shots  %5.1fs  median %.2fs  %s"
                  % (c["id"], c["shots"], c["seconds"], c["median_shot"],
                     (c.get("note") or "")[:44]))
        print("\n  %d sequence card(s)" % len(cs))
        return 0

    if not os.path.isfile(a.video):
        print("  no such video: %s" % a.video)
        return 1
    sid = slug(a.id or os.path.basename(a.video))
    card = build(a.video, sid, a.threshold, a.t0, a.t1, a.note)
    if not card:
        print("  no shots found - try a lower --threshold")
        return 1
    s = sheet(a.video, card["beats"], sid)
    card["reference_sheet"] = os.path.relpath(s, ROOT).replace("\\", "/") if s else None
    p = os.path.join(CARDS, sid + ".json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(card, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("  %s" % p)
    print("  %d shots over %.1fs | median %.2fs | %.0f cuts/min"
          % (card["shots"], card["seconds"], card["median_shot"],
             card["cuts_per_minute"]))
    for b in card["beats"]:
        print("    %2d  %5.2fs  motion %-6s luma %s"
              % (b["n"], b["seconds"], b["motion"], b["luma"]))
    if s:
        print("  reference sheet: %s" % s)
    print("\n  Now open the sheet and fill in framing/subject/camera per beat - those are "
          "judgement, not measurement.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
