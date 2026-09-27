#!/usr/bin/env python3
"""studio/_tools/compositor_ab.py - which local compositor makes the better START FRAME?

The whole video path is image-to-video, so the start frame decides most of what reads as
quality (§96.4). Two local compositors now take the same three pictures - the plate, character
one, character two - and the same words: Flux 2 with three chained references (workflow 75,
what fight.py uses for its anchors) and Qwen-Image-2.1 with its reference images (workflow 80,
2026-09-27). This renders one shot's anchor both ways on the same seeds and scores each frame
with the instruments the studio already trusts:

    identity   each character's head against their own reference head (identity.py, CLIP-ViT-H
               cosine; in a medium framing >= 0.56 is the same person, 0.46-0.56 uncertain)
    room       the border band against the plate (§98.1: 11-19 the same room, 73 unrelated)
    seconds    wall-clock per frame

    ~/ComfyUI/venv/bin/python3 studio/_tools/compositor_ab.py --film ash-court --shot 010 \
        --seeds 11 202 3003

The shot's `anchor` text is used as written for Flux 2 ("the woman of reference one") and with
"reference N" rewritten as "<imageN>" for Qwen 2.1, which is how each model names its pictures.
The adoption rule is the studio's (§95): a compositor is preferred only if it wins by more than
max(0.02, spread/2) on the identity that matters, on every seed's average.
"""
import argparse
import json
import os
import re
import shutil
import sys
import time

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
TOOLS = os.path.join(STUDIO, "_tools")
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run                       # noqa: E402
import newmodels_test as nm                 # noqa: E402  (the instruments)

HOST = os.environ["COMFY_HOST"]
COMFY = os.path.expanduser("~/ComfyUI")
WF = os.path.join(ROOT, "workflows")
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}


def load_wf(name):
    d = json.load(open(os.path.join(WF, name), encoding="utf-8"))
    return {k: v for k, v in d.items() if isinstance(v, dict) and "class_type" in v}


def qwen_words(text):
    return re.sub(r"reference (one|two|three|four|five|[1-5])",
                  lambda m: "<image%d>" % WORDS[m.group(1).lower()], text, flags=re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--film", default="ash-court")
    ap.add_argument("--shot", default="010")
    ap.add_argument("--seeds", type=int, nargs="+", default=[11, 202, 3003])
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    seq = json.load(open(os.path.join(STUDIO, "shotscripts", a.film + ".json"), encoding="utf-8"))
    shot = next(x for x in seq["shots"] if x["id"] == a.shot)
    if not shot.get("anchor"):
        sys.exit("shot %s has no anchor text (it starts on the plate)" % a.shot)
    fight = os.path.join(STUDIO, "samples", "fight", a.film)
    out = a.out or os.path.join(STUDIO, "samples", "compositor_ab", "%s_%s" % (a.film, a.shot))
    os.makedirs(out, exist_ok=True)
    refs = [os.path.join(fight, "ref_%s.png" % r) for r in shot["refs"]]
    for p in refs:
        if not os.path.exists(p):
            sys.exit("missing %s - run fight.py --cast first" % p)
    place_id = seq["place"].get("id", "court")
    plate = os.path.join(fight, "ref_%s.png" % place_id)
    cast = [r for r in shot["refs"] if r != place_id]
    heads = {}
    for who in dict.fromkeys(cast):
        dst = os.path.join(out, "_head_%s.png" % who)
        if not os.path.exists(dst):
            nm.head_crop_file(os.path.join(fight, "ref_%s.png" % who), dst)
        heads[who] = dst
    rep = {"film": a.film, "shot": a.shot, "refs": shot["refs"], "anchor": shot["anchor"],
           "qwen_words": qwen_words(shot["anchor"]), "flux2": [], "qwen21": []}
    items = []

    # Flux 2 ref3 (75) - exactly as fight.stage_anchors builds it
    for i, p in enumerate(refs, 1):
        shutil.copy(p, os.path.join(COMFY, "input", "fight_ref%d.png" % i))
    for s in a.seeds:
        wf = load_wf("75_flux2_ref3.json")
        wf["sg1_6"]["inputs"]["text"] = shot["anchor"]
        wf["sg1_25"]["inputs"]["noise_seed"] = s
        wf["9"]["inputs"]["filename_prefix"] = "claude-generated/compositor_ab/flux2_s%d" % s
        outs, secs = nm.submit(wf, "flux2 s%d" % s)
        f = nm.collect(outs, os.path.join(out, "flux2_s%d.png" % s))
        if not f:
            rep["flux2"].append({"seed": s, "error": "no output"})
            continue
        sc = nm.score_pair(f, heads, out, "flux2_s%d" % s)
        sc.update({"seed": s, "secs": round(secs, 1), "file": f, "place": nm.place_hold(f, plate)})
        rep["flux2"].append(sc)
        items.append(("Flux 2 ref3 s%d %.0fs  %s room %.0f" % (
            s, secs, " ".join("%s %.2f" % (w[:3], (sc[w]["score"] or 0)) for w in heads), sc["place"]), f))
        print("  flux2 s%d %.0fs %s room %s" % (s, secs, {w: sc[w]["score"] for w in heads}, sc["place"]), flush=True)

    nm.make_room(20)
    # Qwen-Image-2.1 (80) - the same pictures, image_1 = the plate so the canvas is the plate's
    order = [place_id] + [r for r in shot["refs"] if r != place_id]
    idx = {}
    for i, r in enumerate(order, 1):
        shutil.copy(os.path.join(fight, "ref_%s.png" % r), os.path.join(COMFY, "input", "qwen21_ref%d.png" % i))
        idx[r] = i
    # the shot's words number the pictures in the shot's order; renumber to the plate-first order
    words = shot["anchor"]
    for n, r in enumerate(shot["refs"], 1):
        words = re.sub(r"reference (%s|%d)\b" % (["one", "two", "three", "four", "five"][n - 1], n),
                       "<image%d>" % idx[r], words, flags=re.I)
    rep["qwen_words"] = words
    for s in a.seeds:
        wf = load_wf("80_qwen21_edit_refs.json")
        for k in ("21", "22", "23"):
            wf.pop(k, None)
        for k in list(wf["6"]["inputs"]):
            if k.startswith("images."):
                del wf["6"]["inputs"][k]
        for r, i in idx.items():
            wf["2%d" % i] = {"class_type": "LoadImage", "inputs": {"image": "qwen21_ref%d.png" % i}}
            wf["6"]["inputs"]["images.image_%d" % i] = ["2%d" % i, 0]
        wf["6"]["inputs"]["prompt"] = words
        wf["6"]["inputs"]["negative_prompt"] = seq["avoid"]
        wf["10"]["inputs"]["seed"] = s
        wf["12"]["inputs"]["filename_prefix"] = "claude-generated/compositor_ab/qwen21_s%d" % s
        outs, secs = nm.submit(wf, "qwen21 s%d" % s)
        f = nm.collect(outs, os.path.join(out, "qwen21_s%d.png" % s))
        if not f:
            rep["qwen21"].append({"seed": s, "error": "no output"})
            continue
        sc = nm.score_pair(f, heads, out, "qwen21_s%d" % s)
        sc.update({"seed": s, "secs": round(secs, 1), "file": f, "place": nm.place_hold(f, plate)})
        rep["qwen21"].append(sc)
        items.append(("Qwen-2.1 s%d %.0fs  %s room %.0f" % (
            s, secs, " ".join("%s %.2f" % (w[:3], (sc[w]["score"] or 0)) for w in heads), sc["place"]), f))
        print("  qwen21 s%d %.0fs %s room %s" % (s, secs, {w: sc[w]["score"] for w in heads}, sc["place"]), flush=True)

    # the verdict, by the studio's rule
    verdict = {}
    for who in heads:
        fa = [t[who]["score"] for t in rep["flux2"] if t.get(who, {}).get("score") is not None]
        qa = [t[who]["score"] for t in rep["qwen21"] if t.get(who, {}).get("score") is not None]
        if fa and qa:
            mf, mq = sum(fa) / len(fa), sum(qa) / len(qa)
            spread = max(max(fa) - min(fa), max(qa) - min(qa))
            margin = max(0.02, spread / 2)
            win = "qwen21" if mq - mf > margin else ("flux2" if mf - mq > margin else "tie")
            verdict[who] = {"flux2_mean": round(mf, 3), "qwen21_mean": round(mq, 3), "spread": round(spread, 3),
                            "margin": round(margin, 3), "winner": win}
    rep["verdict"] = verdict
    nm.contact(items, os.path.join(out, "contact.jpg"), cols=len(a.seeds), cell=(426, 240),
               title="the same three pictures and words: Flux 2 ref3 (top) vs Qwen-Image-2.1 (bottom)")
    json.dump(rep, open(os.path.join(out, "measured.json"), "w"), indent=1)
    print(json.dumps(verdict, indent=1))
    print("->", out)


if __name__ == "__main__":
    main()
