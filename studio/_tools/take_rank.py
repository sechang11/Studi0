#!/usr/bin/env python3
"""studio/_tools/take_rank.py - read every take of a shot script and suggest the picks, by measurement.

For each take of each shot (shot_/h3_/pv_/pvb_/sd_<id>_s<seed>.mp4):

  face     each character's head on the LAST frame against the same character's head in the shot's
           own start frame - the yardstick §98.5b settled on (the studio-lit reference measures the
           lighting, not the face). CLIP-ViT-H cosine through identity.py. Close-ups and mediums only.
  line     if the shot has a `line`, the take's audio through the local Granite speech model; the
           share of the line's words that come back.
  sound    mean and peak level (volumedetect): a take with no sound is a fault.
  camera   what cammeasure measured (fight.py --score must have run), against the ask: a shot that
           asks for a static camera and pushes in by a quarter is flagged.

A FAULT blocks a pick (face drifted, line not heard, silence); a NOTE does not (the studio's one pick
rule, §96.5). The pick is the take with no faults and the highest score; with every take faulted,
the fewest faults. Writes ranked.json beside the takes and picks.txt in fight.py's --picks format.

    ~/ComfyUI/venv/bin/python3 studio/_tools/take_rank.py --sequence house-rules
"""
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
TOOLS = os.path.join(ROOT, "studio", "_tools")
sys.path.insert(0, TOOLS)
import fight                                  # noqa: E402  (reads --sequence off argv)
import newmodels_test as nm                   # noqa: E402

from PIL import Image                         # noqa: E402

FACE_FAULT = 0.60      # head-to-head against the take's own start frame: the same face reads 0.75-0.89
LINE_FAULT = 0.60
SILENT_DB = -55.0


def takes_of(sid):
    out = []
    for f in sorted(os.listdir(fight.OUT)):
        m = re.match(r"^(shot|h3|pv|pvb|sd)_%s_s(\d+)\.mp4$" % sid, f)
        if m:
            out.append((m.group(1), int(m.group(2)), os.path.join(fight.OUT, f)))
    return out


def token(stem, seed):
    return str(seed) if stem == "shot" else "%s:%d" % (stem, seed)


def _crop(im, box, path, pad=0.4):
    w, h = im.size
    x0, y0, x1, y1 = box
    side = max((x1 - x0) * w, (y1 - y0) * h) * (1 + pad)
    cx, cy = (x0 + x1) / 2 * w, (y0 + y1) / 2 * h
    l, t = max(0, cx - side / 2), max(0, cy - side / 2)
    im.crop((int(l), int(t), int(min(w, l + side)), int(min(h, t + side)))).save(path)
    return path


def yardstick(s):
    """The heads in the shot's own start frame, one file per character."""
    anchor = os.path.join(fight.OUT, "anchor_%s.png" % s["id"])
    face = s.get("face", "medium")
    chars = fight._unique([r for r in s["refs"] if r in fight.CAST])
    if face in ("none", "wide") or not chars or not os.path.exists(anchor):
        return {}
    work = os.path.join(fight.OUT, "_score")
    os.makedirs(work, exist_ok=True)
    im = Image.open(anchor).convert("RGB")
    yard = {}
    if len(chars) == 1:
        import headbox
        try:
            box = headbox.head_box(anchor)
        except Exception:
            box = None
        if box and face == "close" and (box[3] - box[1]) < 0.12:
            box = None
        if not box:
            box = [0.28, 0.02, 0.72, 0.62] if face == "close" else [0.35, 0.05, 0.65, 0.45]
        yard[chars[0]] = _crop(im, box, os.path.join(work, "_yard_%s_%s.png" % (s["id"], chars[0])))
    else:
        boxes = nm.heads_in(anchor, work)
        for who, side in zip(chars, ("left", "right")):     # the scripts put reference one on the left
            if side in boxes:
                yard[who] = _crop(im, boxes[side], os.path.join(work, "_yard_%s_%s.png" % (s["id"], who)))
    return yard


def loudness(v):
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", v, "-af", "volumedetect", "-vn", "-f", "null", "-"],
                       capture_output=True, text=True)
    mean = re.search(r"mean_volume:\s*(-?[\d.]+)", r.stderr)
    peak = re.search(r"max_volume:\s*(-?[\d.]+)", r.stderr)
    return (float(mean.group(1)) if mean else None, float(peak.group(1)) if peak else None)


def words(t):
    return re.findall(r"[a-z0-9']+", (t or "").lower().replace("’", "'"))


def line_hit(expected, heard):
    want = words(expected)
    got = set(words(heard))
    if not want:
        return None
    return round(sum(1 for w in want if w in got) / len(want), 2)


def camera_note(s, m):
    if not m or m.get("zoom") is None:
        return None
    asks_static = "static camera" in s["prompt"].lower() or "almost still" in s["prompt"].lower()
    z, p, t = float(m.get("zoom") or 1), abs(float(m.get("pan") or 0)), abs(float(m.get("tilt") or 0))
    if asks_static and (z > 1.25 or z < 0.8 or p > 0.15 or t > 0.15):
        return "camera moved (%s) where the shot asked for stillness" % m.get("camera")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sequence", required=True)
    ap.add_argument("--no-asr", action="store_true")
    ap.add_argument("--only-shots", default="", help="rank just these shots (the editor); the rest stay as ranked")
    ap.add_argument("--replace-picks", action="store_true",
                    help="overwrite picks.txt with the ranker's picks (default: only fill shots with no pick)")
    a = ap.parse_args()
    only = {x.strip() for x in a.only_shots.split(",") if x.strip()}
    measured = {}
    mp = os.path.join(fight.OUT, "measured.json")
    if os.path.exists(mp):
        measured = json.load(open(mp))
    work = os.path.join(fight.OUT, "_score")
    os.makedirs(work, exist_ok=True)
    report, asr_jobs = {}, {}
    for s in fight.SHOTS:
        sid = s["id"]
        if only and sid not in only:
            continue
        tk = takes_of(sid)
        if not tk:
            continue
        yard = yardstick(s)
        rows = []
        for stem, seed, v in tk:
            n, fps = nm.nframes(v)
            last = nm.frame_at(v, max(0.0, n / (fps or 24) - 1.5 / (fps or 24)),
                               os.path.join(work, "_last_%s.png" % os.path.basename(v)[:-4]))
            faces = fight.score_faces(last, s, yard=yard, tag="take_%s" % os.path.basename(v)[:-4]) if yard else {}
            mean_db, peak_db = loudness(v)
            row = {"take": os.path.basename(v), "token": token(stem, seed), "engine": stem,
                   "frames": n, "faces": faces, "mean_db": mean_db, "peak_db": peak_db,
                   "camera": (measured.get(os.path.basename(v)) or {}).get("camera")}
            if s.get("line") and not a.no_asr:
                wav = os.path.join(work, "_asr_%s.wav" % os.path.basename(v)[:-4])
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", v, "-vn", "-ac", "1", "-ar", "16000", wav],
                               capture_output=True)
                if os.path.exists(wav):
                    asr_jobs[wav] = (sid, len(rows))
            rows.append(row)
            print("  %s %-26s faces %-28s %s dB" % (sid, row["take"], json.dumps(faces), mean_db), flush=True)
        report[sid] = {"title": s["title"], "face": s.get("face"), "line": s.get("line"),
                       "engine_asked": s.get("engine", "ltx"), "takes": rows}
    if asr_jobs:
        import post
        post.make_room(need_gb=8.0, budget=120)
        import film_audio
        heard = film_audio._asr_local(list(asr_jobs))
        for wav, (sid, i) in asr_jobs.items():
            row = report[sid]["takes"][i]
            row["heard"] = heard.get(wav, "")
            row["line_hit"] = line_hit(report[sid]["line"], row["heard"])
            print("  %s %-26s heard %r  (%s)" % (sid, row["take"], row["heard"][:70], row["line_hit"]), flush=True)
    picks = []
    for s in fight.SHOTS:
        sid = s["id"]
        if sid not in report:
            continue
        for row in report[sid]["takes"]:
            faults, notes = [], []
            f = row["faces"]
            if f and min(f.values()) < FACE_FAULT:
                faults.append("face drifted (%.2f against its start frame)" % min(f.values()))
            if s.get("line") and row.get("line_hit") is not None and row["line_hit"] < LINE_FAULT:
                faults.append("line not heard (%d%% of its words)" % int(100 * row["line_hit"]))
            if row["mean_db"] is not None and row["mean_db"] < SILENT_DB:
                faults.append("silent (%.0f dB)" % row["mean_db"])
            cn = camera_note(s, measured.get(row["take"]))
            if cn:
                notes.append(cn)
            score = (sum(f.values()) / len(f)) if f else 0.7
            if row.get("line_hit") is not None:
                score += 0.25 * row["line_hit"]
            if cn:
                score -= 0.05
            row.update({"faults": faults, "notes": notes, "score": round(score, 3)})
        rows = report[sid]["takes"]
        best = sorted(rows, key=lambda r: (len(r["faults"]), -r["score"]))[0]
        report[sid]["pick"] = best["token"]
        report[sid]["why"] = ("no faults, highest score %.3f" % best["score"] if not best["faults"]
                              else "every take faulted; fewest faults (%s)" % "; ".join(best["faults"]))
        picks.append("%s=%s" % (sid, best["token"]))
        print("%s  pick %-8s %s" % (sid, best["token"], report[sid]["why"]), flush=True)
    # merge: shots not ranked this time keep their record
    rp = os.path.join(fight.OUT, "ranked.json")
    old = json.load(open(rp)) if os.path.exists(rp) else {}
    old.update(report)
    ordered = {s["id"]: old[s["id"]] for s in fight.SHOTS if s["id"] in old}
    json.dump(ordered, open(rp, "w"), indent=1)
    # picks.txt is the CUT, which a person may have chosen: the ranker only fills a shot with no pick
    pp = os.path.join(fight.OUT, "picks.txt")
    cur = {}
    if os.path.exists(pp) and not a.replace_picks:
        cur = dict(kv.split("=", 1) for kv in open(pp).read().strip().split(",") if "=" in kv)
    for kv in picks:
        sid, tok = kv.split("=", 1)
        if a.replace_picks or sid not in cur:
            cur[sid] = tok
    line = ",".join("%s=%s" % (s["id"], cur[s["id"]]) for s in fight.SHOTS if s["id"] in cur)
    open(pp, "w").write(line + "\n")
    print("PICKS " + line, flush=True)


if __name__ == "__main__":
    main()
