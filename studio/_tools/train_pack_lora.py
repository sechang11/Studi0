#!/usr/bin/env python3
"""Train a character LoRA from a foundry pack's own views.

The studio's existing trainer wants a card from the older cast format, which a foundry pack
does not have, so this drives the same workflow directly.  Everything else is the same: the
graph is 33_train_character_lora.json, the base is the anime checkpoint the drawn packs were
made with, and the dataset is a folder of image-and-caption pairs under ComfyUI/input.

    python3 train_pack_lora.py bailiwen_train --steps 1200 --rank 16
"""
import argparse
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.expanduser("~/shared/comfy-studio")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from comfy import set_path  # noqa: E402
from epic import COMFY, HOST, load_wf, submit  # noqa: E402

WF = "33_train_character_lora.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--steps", type=int, default=1200)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--lr", type=float)
    ap.add_argument("--name")
    a = ap.parse_args()

    d = os.path.join(COMFY, "input", a.folder)
    if not os.path.isdir(d):
        raise SystemExit("no dataset at %s" % d)
    imgs = sorted(f for f in os.listdir(d) if f.endswith(".png"))
    pairs = [f for f in imgs if os.path.exists(os.path.join(d, f[:-4] + ".txt"))]
    name = a.name or a.folder.replace("_train", "")
    print("dataset : %s" % d)
    print("          %d images, %d with captions" % (len(imgs), len(pairs)))
    if len(pairs) < 8:
        raise SystemExit("%d pairs is too thin to train on" % len(pairs))
    caps = [open(os.path.join(d, f[:-4] + ".txt"), encoding="utf-8").read().strip() for f in pairs]
    print("\ncaptions - whatever these do NOT name is welded onto %r:" % name)
    for c in caps[:3]:
        print("    %s" % c[:140])
    print("    ... %d more" % max(0, len(caps) - 3))
    named = set()
    for c in caps:
        named.update(w.strip().lower() for w in c.split(","))
    named.discard("")
    print("  %d distinct phrases across %d captions" % (len(named), len(caps)))

    wf = load_wf(WF)
    set_path(wf, "1.inputs.folder", a.folder)
    set_path(wf, "5.inputs.steps", int(a.steps))
    set_path(wf, "5.inputs.rank", int(a.rank))
    if a.lr:
        set_path(wf, "5.inputs.learning_rate", float(a.lr))
    prefix = "loras/character_%s" % name
    set_path(wf, "6.inputs.prefix", prefix)
    print("\nsteps %d, rank %d, lr %s -> %s" % (a.steps, a.rank, wf["5"]["inputs"]["learning_rate"], prefix))

    t0 = time.time()
    pid = submit(wf)
    print("  prompt %s; this is minutes, not seconds" % pid, flush=True)
    last = ""
    while time.time() - t0 < 7200:
        time.sleep(20)
        try:
            h = json.load(urllib.request.urlopen("http://%s/history/%s" % (HOST, pid), timeout=30))
        except Exception:
            continue
        e = h.get(pid)
        if not e:
            q = json.load(urllib.request.urlopen("http://%s/queue" % HOST, timeout=30))
            n = len(q.get("queue_running", [])) + len(q.get("queue_pending", []))
            msg = "  %.0fs, still training (%d in the queue)" % (time.time() - t0, n)
            if msg[:12] != last[:12]:
                print(msg, flush=True)
                last = msg
            continue
        st = (e.get("status") or {}).get("status_str")
        print("  -> %s after %.0fs" % (st, time.time() - t0), flush=True)
        if st == "error":
            for m in (e.get("status") or {}).get("messages", [])[-4:]:
                print("     %s" % str(m)[:220], flush=True)
        break
    out = os.path.join(COMFY, "output", "loras")
    if os.path.isdir(out):
        made = sorted((os.path.getmtime(os.path.join(out, f)), f) for f in os.listdir(out)
                      if f.endswith(".safetensors"))
        print("\nin ComfyUI/output/loras:")
        for mt, f in made[-3:]:
            print("   %s  %.1f MB" % (f, os.path.getsize(os.path.join(out, f)) / 1e6))
    print("TRAIN DONE", flush=True)


if __name__ == "__main__":
    main()
