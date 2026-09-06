#!/usr/bin/env python3
"""Give a character pack a LoRA, end to end, and only adopt it if it is better.

Dataset from the pack's own views, captions from a narrow vision ask, training, then the same
four-route comparison that established the method - a prompt alone, the reference-image path
the studio uses today, the LoRA, and both - scored against the pack portrait on a head found
by the matte.  Adopted only if the LoRA beats the reference path, and always alone, because
measured on two packs the combination is a coin flip.

    python3 pack_lora.py renji jin terra
    python3 pack_lora.py --steps 1500 the-ferryman
    python3 pack_lora.py --dry jin            # say what it would do

One pack at a time on a shared card: training queues behind whatever else is running, and
three of these at once turns twelve minutes into seventy.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
TOOLS = os.path.join(STUDIO, "_tools")
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from comfy import set_path  # noqa: E402
from epic import COMFY, HOST, load_wf, submit  # noqa: E402
import headbox as HB  # noqa: E402

PY = os.path.expanduser("~/ComfyUI/venv/bin/python")
CHARS = os.path.join(STUDIO, "foundry", "characters")
STRENGTH = 0.85
SEEDS = (4242, 7, 913)      # one rendered comparison is the seed lottery this project avoids
NEG_F = ("1boy, male, lowres, bad anatomy, bad hands, text, error, missing fingers, "
         "worst quality, low quality, jpeg artifacts, watermark, blurry")
NEG_M = NEG_F.replace("1boy, male,", "1girl, female,")


def wait(pid, budget=3600):
    t0 = time.time()
    while time.time() - t0 < budget:
        time.sleep(8)
        try:
            h = json.load(urllib.request.urlopen("http://%s/history/%s" % (HOST, pid), timeout=30))
        except Exception:
            continue
        if h.get(pid):
            return (h[pid].get("status") or {}).get("status_str"), time.time() - t0
    return "timeout", time.time() - t0


def close_up(pack, trigger, tags, lora, ipa, tag, seed=4242):
    wf = load_wf("22_anime_kf_ipadapter.json")
    ref = "packlora_ref_%s.png" % trigger
    shutil.copy(os.path.join(CHARS, pack, "base_portrait.png"), os.path.join(COMFY, "input", ref))
    set_path(wf, "2.inputs.image", ref)
    set_path(wf, "4.inputs.weight", float(ipa))
    pre_words = ("%s, " % trigger) if lora else ""
    set_path(wf, "5.inputs.text", "%s%s, a close portrait of the face, facing the camera, "
             "plain neutral background, masterpiece, best quality" % (pre_words, tags))
    set_path(wf, "6.inputs.text", NEG_M if "1girl" in tags else NEG_F)
    for n in ("7", "10"):
        set_path(wf, "%s.inputs.width" % n, 896)
        set_path(wf, "%s.inputs.height" % n, 1152)
    set_path(wf, "8.inputs.seed", seed)
    pre = "claude-generated/packlora/%s_%s" % (trigger, tag)
    set_path(wf, "11.inputs.filename_prefix", pre)
    if lora:
        wf["packlora"] = {"class_type": "LoraLoader",
                          "inputs": {"lora_name": lora, "strength_model": STRENGTH,
                                     "strength_clip": STRENGTH, "model": ["1", 0], "clip": ["1", 1]}}
        set_path(wf, "3.inputs.model", ["packlora", 0])
        set_path(wf, "5.inputs.clip", ["packlora", 1])
        set_path(wf, "6.inputs.clip", ["packlora", 1])
    wait(submit(wf))
    g = sorted(glob.glob(os.path.join(COMFY, "output", pre + "*.png")), key=os.path.getmtime)
    return g[-1] if g else None


def score(pack, files):
    port = os.path.join(CHARS, pack, "base_portrait.png")
    jobs = []
    for tag, p in files.items():
        if not p:
            continue
        try:
            box = HB.head_box(p)
        except Exception:
            box = None
        jobs.append({"id": tag, "portrait": port, "still": p, "box": box, "close": True})
    jp = "/tmp/packlora_%s.json" % pack
    json.dump(jobs, open(jp, "w"))
    r = subprocess.run([PY, os.path.join(TOOLS, "identity.py"), jp], capture_output=True,
                       text=True, cwd=os.path.expanduser("~/ComfyUI"))
    out = {}
    for line in r.stdout.splitlines():
        try:
            d = json.loads(line)
            out[d["id"]] = d.get("start")
        except Exception:
            pass
    return out


def do(pack, steps, rank, dry=False):
    a = json.load(open(os.path.join(CHARS, pack, "asset.json"), encoding="utf-8"))
    if a.get("style") != "anime":
        print("%s: %s, not anime - the trainer's base is the anime checkpoint" % (pack, a.get("style")))
        return None
    trigger = pack.replace("-", "")
    tags = (a.get("compiled") or {}).get("tags") or "1girl, solo"
    tags = ", ".join(t.strip() for t in tags.split(",")[:6] if t.strip())
    folder = "%s_train" % trigger
    print("\n=== %s (trigger %r) ===" % (pack, trigger), flush=True)
    if dry:
        print("  would build %s, caption it, train %d steps rank %d, then compare four routes"
              % (folder, steps, rank))
        return None
    subprocess.run([sys.executable, os.path.join(TOOLS, "pack_dataset.py"), pack], check=False)
    subprocess.run([sys.executable, os.path.join(TOOLS, "caption_wear.py"), folder], check=False)
    t0 = time.time()
    subprocess.run([sys.executable, os.path.join(TOOLS, "train_pack_lora.py"), folder,
                    "--steps", str(steps), "--rank", str(rank)], check=False)
    src = os.path.join(COMFY, "output", "loras", "character_%s_00001_.safetensors" % trigger)
    dst_name = "character_%s_b6.safetensors" % trigger
    dst = os.path.expanduser("~/ComfyUI/models/loras/%s" % dst_name)
    if not os.path.exists(src):
        print("  ! no trained file at %s" % src)
        return None
    shutil.move(src, dst)
    print("  trained in %.0fs -> %s" % (time.time() - t0, dst_name), flush=True)
    import statistics
    got = {"ipadapter": [], "lora": []}
    for seed in SEEDS:
        files = {"ipadapter": close_up(pack, trigger, tags, None, 0.6, "ipa%d" % seed, seed),
                 "lora": close_up(pack, trigger, tags, dst_name, 0.0, "lora%d" % seed, seed)}
        sc = score(pack, files)
        for k in got:
            if sc.get(k) is not None:
                got[k].append(sc[k])
        print("    seed %d: reference %s | the LoRA %s" % (
            seed, ("%.3f" % sc["ipadapter"]) if sc.get("ipadapter") else "-",
            ("%.3f" % sc["lora"]) if sc.get("lora") else "-"), flush=True)
    ipa = statistics.mean(got["ipadapter"]) if got["ipadapter"] else None
    lora = statistics.mean(got["lora"]) if got["lora"] else None
    spread = (max(got["lora"]) - min(got["lora"])) if len(got["lora"]) > 1 else 0.0
    print("  reference path %s | the LoRA %s (spread %.3f over %d seeds)" % (
        ("%.3f" % ipa) if ipa else "-", ("%.3f" % lora) if lora else "-",
        spread, len(got["lora"])), flush=True)
    # the margin has to beat the seed noise, not just a fixed number
    better = (lora or 0) > (ipa or 0) + max(0.02, spread / 2.0)
    if better:
        a["lora"] = {"file": dst_name, "trigger": trigger, "trained": time.strftime("%Y-%m-%d"),
                     "steps": steps, "rank": rank,
                     "seeds": len(got["lora"]),
                     "measured": "a close-up scores %.3f against the pack portrait where the "
                                 "reference-image path scores %.3f, averaged over %d seeds "
                                 "(spread %.3f)" % (lora or 0, ipa or 0, len(got["lora"]), spread)}
        json.dump(a, open(os.path.join(CHARS, pack, "asset.json"), "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)
        print("  ADOPTED", flush=True)
    else:
        # a decline is a measurement too: without it the pack looks untried, and the next
        # person spends the same twelve minutes of card reaching the same tie
        a["lora_withdrawn"] = {"file": dst_name, "trigger": trigger,
                               "trained": time.strftime("%Y-%m-%d"), "steps": steps, "rank": rank,
                               "measured": "a close-up scored %.3f against the pack portrait where "
                                           "the reference-image path scored %.3f, so it was not kept"
                                           % (lora or 0, ipa or 0)}
        a.pop("lora", None)
        json.dump(a, open(os.path.join(CHARS, pack, "asset.json"), "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)
        print("  not adopted: the LoRA did not beat the reference path", flush=True)
    return {"pack": pack, "ipadapter": ipa, "lora": lora, "adopted": bool(better)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("packs", nargs="+")
    ap.add_argument("--steps", type=int, default=1200)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    rows = []
    for p in args.packs:
        try:
            r = do(p, args.steps, args.rank, args.dry)
            if r:
                rows.append(r)
        except Exception as e:
            print("%s FAILED: %s" % (p, str(e)[:200]), flush=True)
    if rows:
        print("\n%-20s %10s %10s  %s" % ("pack", "reference", "LoRA", ""))
        for r in rows:
            print("%-20s %10s %10s  %s" % (
                r["pack"], ("%.3f" % r["ipadapter"]) if r["ipadapter"] else "-",
                ("%.3f" % r["lora"]) if r["lora"] else "-", "adopted" if r["adopted"] else "kept the old way"))
        json.dump(rows, open(os.path.join(STUDIO, "pack_loras.json"), "w"), indent=1)
    print("PACK LORA DONE", flush=True)
