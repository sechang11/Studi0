#!/usr/bin/env python3
"""studio/_tools/identity_proof.py - render each character by each identity METHOD, so a
human can cross out the ones that are not them, and the method carries the blame.

WHY. The two-character test found that IPAdapter alone does not carry an invented
character - TERRA held because animagine already knows "terra branford", BRACK only
arrived once his description was in the prompt. That was one comparison on two people.
This turns it into a standing check across the whole cast.

THE POINT IS THE VERDICT COLUMN. Every sample records the METHOD and the WORKFLOW that
produced it, so rejections accumulate against a path rather than against a picture. A
method that collects crosses is a method to rework - which is the difference between "that
render is bad" and "that approach does not work", and only the second one is actionable.

    python3 studio/_tools/identity_proof.py --generate
    python3 studio/_tools/identity_proof.py --sheet        contact sheet to look at
    python3 studio/_tools/identity_proof.py --report       tally by method

THE METHODS, which are the three ways this project can ask for a face:

    sheet    IPAdapter off the reference sheet, GENERIC prompt. Tests the image alone.
    tags     the card's tags in the prompt, NO IPAdapter. Tests the words alone.
    both     tags AND the sheet. What the pipeline actually does when it has both.

A character with no sheet cannot be asked for `sheet` or `both`; one with no tags cannot
be asked for `tags`. Those are recorded as skipped rather than silently missing, because
"we never tested it" and "it failed" are different facts and the app must not confuse them.

The verdicts are written by a person through /identity in the app, or with --mark. Nothing
here judges a face; there is no instrument on this box that can, and guessing would be
worse than the empty column.
"""
import argparse
import glob
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
CHARS = os.path.join(STUDIO, "characters")
OUT = os.path.join(STUDIO, "samples", "identity")
MANIFEST = os.path.join(STUDIO, "identity_proof.json")
# Below this many human judgements a method gets no verdict at all. One
# click should not condemn a path; see the docstring on why this exists.
MIN_JUDGED = 4
COMFY = os.path.expanduser(os.environ.get("COMFY_ROOT", "~/ComfyUI"))

WF_IPA = "workflows/22_anime_kf_ipadapter.json"
GENERIC = "1person, solo, standing, full body, masterpiece, best quality"
NEG = ("motion blur, blurry, overexposed, washed out, lowres, bad anatomy, "
       "extra limbs, watermark, signature, text")


def sh(*a, **kw):
    return subprocess.run(a, capture_output=True, text=True, **kw)


def cast():
    out = []
    for p in sorted(glob.glob(os.path.join(CHARS, "*.json"))):
        d = json.loads(io.open(p, encoding="utf-8").read())
        name = os.path.splitext(os.path.basename(p))[0]
        sheet = d.get("sheet")
        has_sheet = bool(sheet) and os.path.exists(os.path.join(COMFY, "input", sheet))
        out.append({"name": name, "sheet": sheet if has_sheet else None,
                    "tags": (d.get("tags") or "").strip() or None,
                    "lora": d.get("lora")})
    return out


def run_wf(wf_path, sets, prefix):
    cmd = [sys.executable, os.path.join(ROOT, "scripts", "comfy.py"), "run", wf_path]
    for k, v in sets:
        cmd += ["-s", "%s=%s" % (k, v)]
    r = sh(*cmd, cwd=ROOT)
    m = re.search(r"-> (\S+\.png)", r.stdout or "")
    if not m:
        return None, (r.stderr or r.stdout or "").strip()[-200:]
    return os.path.join(COMFY, "output", m.group(1)), None


def graph_no_ipadapter():
    """Workflow 22 with the IPAdapter taken out - the KSampler reads the raw checkpoint.

    Written to a temp file rather than added to workflows/, because it exists only to
    isolate one variable in this test and a graph nobody renders from is an orphan.
    """
    g = json.loads(io.open(os.path.join(ROOT, WF_IPA), encoding="utf-8").read())
    g = {k: v for k, v in g.items() if not k.startswith("_")}
    g["8"]["inputs"]["model"] = ["1", 0]          # straight from the checkpoint
    for dead in ("2", "3", "4"):
        g.pop(dead, None)
    p = "/tmp/_ident_notags.json"
    io.open(p, "w", encoding="utf-8").write(json.dumps(g, indent=1))
    return p


def generate(only=None, seed=11):
    os.makedirs(OUT, exist_ok=True)
    rows = load()
    have = {(r["character"], r["method"]) for r in rows}
    no_ipa = graph_no_ipadapter()

    for c in cast():
        if only and c["name"] not in only:
            continue
        plans = [
            ("sheet", bool(c["sheet"]), WF_IPA, GENERIC),
            ("tags", bool(c["tags"]), no_ipa, c["tags"] or ""),
            ("both", bool(c["sheet"] and c["tags"]), WF_IPA, c["tags"] or ""),
        ]
        for method, possible, wf, prompt in plans:
            key = (c["name"], method)
            if key in have:
                continue
            if not possible:
                why = ("no reference sheet" if method in ("sheet", "both") and not c["sheet"]
                       else "no tags on the card")
                rows.append({"id": "%s__%s" % (c["name"], method),
                             "character": c["name"], "method": method,
                             "workflow": os.path.basename(wf), "skipped": why,
                             "image": None, "verdict": None})
                print("  %-12s %-6s SKIPPED - %s" % (c["name"], method, why))
                continue
            sets = [("5.inputs.text", prompt), ("6.inputs.text", NEG),
                    ("8.inputs.seed", seed),
                    ("11.inputs.filename_prefix",
                     "claude-generated/identity/%s_%s" % (c["name"], method))]
            if c["sheet"] and method in ("sheet", "both"):
                sets.append(("2.inputs.image", c["sheet"]))
            src, err = run_wf(wf, sets, None)
            if not src or not os.path.exists(src):
                print("  %-12s %-6s FAILED %s" % (c["name"], method, err or ""))
                continue
            dst = os.path.join(OUT, "%s__%s.png" % (c["name"], method))
            sh("cp", src, dst)
            rows.append({"id": "%s__%s" % (c["name"], method),
                         "character": c["name"], "method": method,
                         "workflow": os.path.basename(wf) if wf == WF_IPA
                                     else "22_anime_kf_ipadapter.json (IPAdapter removed)",
                         "prompt": prompt[:200], "seed": seed,
                         "image": os.path.relpath(dst, STUDIO),
                         "verdict": None})
            print("  %-12s %-6s ok" % (c["name"], method))
    save(rows)
    return rows


def load():
    if os.path.exists(MANIFEST):
        return json.loads(io.open(MANIFEST, encoding="utf-8").read()).get("samples", [])
    return []


def save(rows):
    io.open(MANIFEST, "w", encoding="utf-8", newline="\n").write(json.dumps({
        "generator": "studio/_tools/identity_proof.py",
        "note": ("One render per character per identity METHOD. `verdict` is set by a "
                 "person - 'ok' or 'x' - and nothing automatic writes it, because no "
                 "instrument on this box can tell whether a face is the right person. "
                 "Crosses tally against the METHOD, so a path that keeps failing can be "
                 "reworked rather than a picture re-rolled."),
        "verdicts": {"null": "not looked at yet", "ok": "that is them", "x": "not them"},
        "samples": rows}, indent=1, ensure_ascii=False) + "\n")


def report():
    rows = [r for r in load() if not r.get("skipped")]
    if not rows:
        print("nothing generated yet")
        return
    by = {}
    for r in rows:
        m = by.setdefault(r["method"],
                          {"n": 0, "ok": 0, "close": 0, "x": 0, "unseen": 0})
        m["n"] += 1
        v = r.get("verdict")
        # `close` is a verdict a person made, not an absence of one. Counting it
        # as unseen understated how much of the page had been judged.
        m["ok" if v == "ok" else "close" if v == "close"
          else "x" if v == "x" else "unseen"] += 1
    print("%-8s %5s %5s %6s %5s %8s   %s"
          % ("method", "n", "ok", "close", "x", "unseen", "verdict"))
    for m, s in sorted(by.items()):
        judged = s["ok"] + s["close"] + s["x"]
        # A verdict needs something under it. One cross out of sixteen, with fifteen
        # never looked at, briefly had this printing REWORK - which is the exact
        # over-reading the tool exists to prevent.
        if not judged:
            verdict = "not looked at yet"
        elif judged < MIN_JUDGED:
            verdict = "too early - %d of %d judged" % (judged, s["n"])
        elif s["x"] > judged / 2:
            verdict = "REWORK - %d of %d judged are not them" % (s["x"], judged)
        elif s["x"] or s["close"]:
            # `close` counts FOR the method: the identity arrived and a detail was wrong,
            # which is the card's tags to fix, not the path's.
            verdict = "partial - %d wrong, %d close" % (s["x"], s["close"])
        else:
            verdict = "holds - %d of %d kept" % (s["ok"], judged)
        print("%-8s %5d %5d %6d %5d %8d   %s"
              % (m, s["n"], s["ok"], s["close"], s["x"], s["unseen"], verdict))
    skipped = [r for r in load() if r.get("skipped")]
    if skipped:
        print("\n%d combinations could not be tested at all:" % len(skipped))
        seen = {}
        for r in skipped:
            seen.setdefault(r["skipped"], []).append(r["character"])
        for why, who in seen.items():
            print("  %-20s %s" % (why, ", ".join(sorted(set(who)))))


def contact():
    rows = [r for r in load() if r.get("image")]
    if not rows:
        print("nothing to sheet")
        return
    rows.sort(key=lambda r: (r["character"], r["method"]))
    tiles = []
    for r in rows:
        p = os.path.join(STUDIO, r["image"])
        t = "/tmp/_ip_%s.png" % r["id"]
        label = "%s / %s" % (r["character"], r["method"])
        sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
           "scale=200:266:force_original_aspect_ratio=decrease,"
           "pad=200:266:(ow-iw)/2:(oh-ih)/2:color=black,"
           "pad=iw:ih+26:0:26:color=black,"
           "drawtext=text='%s':fontcolor=white:fontsize=15:x=5:y=4" % label,
           "-frames:v", "1", t)
        if os.path.exists(t):
            tiles.append(t)
    per = 8
    rowimgs = []
    for i in range(0, len(tiles), per):
        chunk = tiles[i:i + per]
        o = "/tmp/_iprow%d.png" % i
        sh(*(["ffmpeg", "-y", "-v", "error"] + sum([["-i", c] for c in chunk], [])
             + ["-filter_complex", "hstack=%d" % len(chunk) if len(chunk) > 1 else "null",
                "-frames:v", "1", o]))
        if os.path.exists(o):
            rowimgs.append(o)
    dst = os.path.join(OUT, "_contact.png")
    if len(rowimgs) == 1:
        sh("cp", rowimgs[0], dst)
    else:
        sh(*(["ffmpeg", "-y", "-v", "error"] + sum([["-i", r] for r in rowimgs], [])
             + ["-filter_complex", "vstack=%d" % len(rowimgs), "-frames:v", "1", dst]))
    print("contact sheet: %s (%d samples)" % (dst, len(tiles)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true")
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--mark", nargs=2, metavar=("ID", "VERDICT"),
                    help="set a verdict from the CLI: ok | x | clear")
    a = ap.parse_args()
    only = set(x for x in a.only.split(",") if x)
    if a.mark:
        rows = load()
        for r in rows:
            if r["id"] == a.mark[0]:
                r["verdict"] = None if a.mark[1] == "clear" else a.mark[1]
                print("%s -> %s" % (r["id"], r["verdict"]))
        save(rows)
    if a.generate:
        generate(only or None)
    if a.sheet:
        contact()
    if a.report or not (a.generate or a.sheet or a.mark):
        report()


if __name__ == "__main__":
    main()
