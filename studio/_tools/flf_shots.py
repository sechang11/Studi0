#!/usr/bin/env python3
"""flf_shots.py - shots that move the camera between two EXACT frames, and the keyframes of an orbit.

    python3 studio/_tools/flf_shots.py --sequence FILM keys  --from anchor_102.png --prefix orbit_k [--steps 8]
    python3 studio/_tools/flf_shots.py --sequence FILM render [--shots 103,104] [--engines ltx,h3] [--seeds 11 202]

A 360-degree orbit is where a generated character morphs: by the time the camera is behind her, the
coat has changed. So an orbit is not asked for - it is BUILT:

  keys     the master frame (the character in her set) turned to each azimuth by the multiple-angles
           LoRA in its own words ("<sks> back-right quarter view eye-level shot medium shot") - the
           whole scene turns, the character and the room together, the way studio/sheets.py turns a
           person or a place (craft/SHEETS.md). Each key is made FROM THE MASTER, not from the key
           before it, so the character never drifts further than one edit from the original.
  render   each segment of the orbit - and any other camera move between two framings (a tilt from an
           eye down to the hands, from the boots up to the face) - rendered between its two frames:
           LTX-2.5 first-last (workflow 72, both frames as guides) and/or H3 first-last turbo v4 (65).

A shot opts in with "engine": "flf" and "flf": {"first": FILE, "last": FILE} (files in the film's
output folder, e.g. anchor_111.png, orbit_k3.png). A frame can also be "end:<take.mp4>" - the LAST
frame of a take - so a move continues from where the shot before it ended: a tilt that starts from
the eye's start frame would jump back in time at the cut. Takes land as fl_<id>_s<seed>.mp4 (LTX) and
flh3_<id>_s<seed>.mp4 (H3) - which fight.py --finish picks as "fl:11" / "flh3:202" with no change.
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

AZIMUTHS8 = ["front-right quarter view", "right side view", "back-right quarter view", "back view",
             "back-left quarter view", "left side view", "front-left quarter view"]


def engine():
    spec = importlib.util.spec_from_file_location("studio_sheets_flf", os.path.join(STUDIO, "sheets.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fit(src, dst, size=(1280, 704)):
    """Every take in a cut must share one size; the keys come back at ~1 MP in the model's own shape."""
    from PIL import Image
    im = Image.open(src).convert("RGB")
    r = max(size[0] / im.width, size[1] / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    left, top = (im.width - size[0]) // 2, (im.height - size[1]) // 2
    im.crop((left, top, left + size[0], top + size[1])).save(dst)
    return dst


def keys(out, src, prefix, steps, elevation, distance):
    E = engine()
    master = os.path.join(out, src)
    if not os.path.exists(master):
        sys.exit("no %s - draw the master start frame first (fight.py --anchors)" % src)
    az = AZIMUTHS8 if steps == 8 else [AZIMUTHS8[i] for i in (1, 3, 5)]   # 8: every 45 degrees; 4: every 90
    made = []
    for i, a in enumerate(az, 1):
        dst = os.path.join(out, "%s%d.png" % (prefix, i))
        if os.path.exists(dst):
            made.append(dst)
            continue
        raw = os.path.join(out, "_%s%d_raw.png" % (prefix, i))
        t0 = time.time()
        E.edit([master], "<sks> %s %s %s" % (a, elevation, distance), 21, E.ANGLES, raw, "%s%d" % (prefix, i))
        fit(raw, dst)
        made.append(dst)
        print("  %s%d  %-26s %4.1fs" % (prefix, i, a, time.time() - t0), flush=True)
    # a board of the whole turn, master first
    from PIL import Image, ImageDraw
    cells = [("master", fit(master, os.path.join(out, "_%s0.png" % prefix)))] + \
            [("%s%d" % (prefix, i), p) for i, p in enumerate(made, 1)]
    H = 260
    row = [(l, Image.open(p).convert("RGB")) for l, p in cells]
    row = [(l, im.resize((int(im.width * H / im.height), H))) for l, im in row]
    per = 4
    W = sum(i.width + 6 for _, i in row[:per])
    board = Image.new("RGB", (W, ((len(row) + per - 1) // per) * (H + 20)), "white")
    d = ImageDraw.Draw(board)
    for n, (l, im) in enumerate(row):
        x, y = (n % per) * (im.width + 6), (n // per) * (H + 20)
        board.paste(im, (x, y + 18))
        d.text((x + 4, y + 3), l, fill="black")
    os.makedirs(os.path.join(out, "picks"), exist_ok=True)
    p = os.path.join(out, "picks", "%sboard.jpg" % prefix)
    board.save(p, quality=86)
    print("  board -> %s" % p, flush=True)


def frame(out, v):
    """A picture in the film's folder, or "end:<take.mp4>": that take's last frame, pulled once."""
    if not v.startswith("end:"):
        return os.path.join(out, v)
    take = os.path.join(out, v[4:])
    if not os.path.isfile(take):
        return take
    dst = os.path.join(out, "_end_%s.png" % os.path.basename(take)[:-4])
    if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(take):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-sseof", "-0.25", "-i", take, "-update", "1",
                        dst], check=True)
        fit(dst, dst)
    return dst


def ltx_flf(first, last, prompt, avoid, secs, seed, prefix):
    from epic import load_wf, COMFY
    wf = {k: v for k, v in load_wf("72_ltx25_flf2v.json").items() if isinstance(v, dict) and "class_type" in v}
    shutil.copy(first, os.path.join(COMFY, "input", "flf_first.png"))
    shutil.copy(last, os.path.join(COMFY, "input", "flf_last.png"))
    wf["31"]["inputs"]["image"] = "flf_first.png"          # frame_idx 0 (traced: sg1_206)
    wf["39"]["inputs"]["image"] = "flf_last.png"           # frame_idx -1 (sg1_204)
    wf["sg1_250"]["inputs"]["value"] = False               # the Gemma enhancer would rewrite the direction
    wf["sg1_252"]["inputs"]["value"] = prompt
    wf["sg1_217"]["inputs"]["text"] = avoid
    wf["sg1_198"]["inputs"]["value"] = int(secs)
    wf["sg1_215"]["inputs"]["value"] = 1280                # the size every take in the cut shares
    wf["sg1_216"]["inputs"]["value"] = 704
    wf["sg1_196"]["inputs"]["noise_seed"] = int(seed)
    for g in ("sg1_206", "sg1_204"):                       # the two frames are the point: hold them firmly
        wf[g]["inputs"]["strength"] = 0.9
    wf["68"]["inputs"]["filename_prefix"] = prefix
    return wf


def h3_flf(first, last, prompt, secs, seed, prefix):
    from epic import load_wf, COMFY
    wf = {k: v for k, v in load_wf("65_minimax_h3_fl_turbo_v4.json").items() if isinstance(v, dict) and "class_type" in v}
    shutil.copy(first, os.path.join(COMFY, "input", "flf_h3_first.png"))
    shutil.copy(last, os.path.join(COMFY, "input", "flf_h3_last.png"))
    wf["8"]["inputs"]["image"] = "flf_h3_first.png"
    wf["9"]["inputs"]["image"] = "flf_h3_last.png"
    n = max(1, (int(secs * 24) - 5) // 17)                 # H3 wants 17n + 5 frames
    wf["20"]["inputs"].update({"prompt": prompt, "width": 1280, "height": 704, "length": 17 * n + 5})
    wf["33"]["inputs"]["noise_seed"] = int(seed)
    wf["51"]["inputs"]["filename_prefix"] = prefix
    return wf


def render(out, script, only, engines, seeds, force):
    from comfy import run
    from epic import HOST, ensure_local
    shots = [s for s in script["shots"] if s.get("engine") == "flf" and (not only or s["id"] in only)]
    if not shots:
        sys.exit("no flf shots to render")
    for s in shots:
        f = s.get("flf") or {}
        first, last = frame(out, f.get("first", "")), frame(out, f.get("last", ""))
        missing = [os.path.basename(p) for p in (first, last) if not os.path.isfile(p)]
        if missing:
            print("  shot %s: no %s yet - skipped" % (s["id"], ", ".join(missing)), flush=True)
            continue
        for eng in engines:
            for seed in seeds:
                stem = "fl" if eng == "ltx" else "flh3"
                dst = os.path.join(out, "%s_%s_s%d.mp4" % (stem, s["id"], seed))
                if os.path.exists(dst) and not force:
                    print("  %s already there" % os.path.basename(dst), flush=True)
                    continue
                prefix = "claude-generated/fight/%s_%s_s%d" % (stem, s["id"], seed)
                wf = ltx_flf(first, last, s["prompt"], script.get("avoid", ""), s["secs"], seed, prefix) \
                    if eng == "ltx" else h3_flf(first, last, s["prompt"], s["secs"], seed, prefix)
                t0 = time.time()
                _, outs = run(HOST, wf, quiet=True)
                vid = next((o for o in outs if o.startswith("claude-generated/fight/%s_" % stem)
                            and o.lower().endswith(".mp4")), None)
                if not vid:
                    print("  %s: no video came back" % os.path.basename(dst), flush=True)
                    continue
                if os.path.exists(dst):
                    os.remove(dst)
                ensure_local(vid, dst)
                print("  %-22s %5.1fs  %s -> %s" % (os.path.basename(dst), time.time() - t0,
                                                   f["first"], f["last"]), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sequence", required=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keys")
    k.add_argument("--from", dest="src", required=True)
    k.add_argument("--prefix", default="orbit_k")
    k.add_argument("--steps", type=int, default=8, choices=[4, 8])
    k.add_argument("--elevation", default="eye-level shot")
    k.add_argument("--distance", default="medium shot")
    r = sub.add_parser("render")
    r.add_argument("--shots", default="")
    r.add_argument("--engines", default="ltx,h3")
    r.add_argument("--seeds", type=int, nargs="+", default=[11])
    r.add_argument("--force", action="store_true")
    a = ap.parse_args()
    out = os.path.join(STUDIO, "samples", "fight", a.sequence)
    script = json.load(open(os.path.join(STUDIO, "shotscripts", a.sequence + ".json"), encoding="utf-8"))
    if a.cmd == "keys":
        keys(out, a.src, a.prefix, a.steps, a.elevation, a.distance)
    else:
        render(out, script, [x for x in a.shots.split(",") if x], [e for e in a.engines.split(",") if e],
               a.seeds, a.force)


if __name__ == "__main__":
    main()
