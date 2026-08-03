#!/usr/bin/env python3
"""
idea.py - one line in, art-directed image out.

Qwen3.5-2B (local) writes the prompt, Qwen-Image 2512 renders it. Roughly 6 s
end to end on the 5090. The prompt the LLM actually wrote is saved next to the
image as a .txt sidecar, so good accidents are reproducible.

    python3 scripts/idea.py "a deep-sea welder repairing a drowned cathedral bell"
    python3 scripts/idea.py "a fox librarian closing up" -n 4
    python3 scripts/idea.py "brutalist bus shelter in heavy snow" --size 1328x1328
    python3 scripts/idea.py "..." --prefix claude-generated/my-set/shot
    python3 scripts/idea.py "..." --dry-run        # prompt only, no render

-n renders N variations. Each one re-rolls the LLM seed as well as the image
seed, so you get genuinely different compositions rather than the same picture
with reshuffled noise.
"""
import argparse
import json
import os
import random
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
WF = os.path.join(KIT, "workflows", "16_llm_to_image.json")
OUTPUT_ROOT = os.path.expanduser("~/ComfyUI/output")

sys.path.insert(0, HERE)
from comfy import api, run, DEFAULT_HOST  # noqa: E402

IDEA_MARKER = "\n\nIDEA: "


def build(wf, idea, llm_seed, img_seed, width, height, prefix, max_len):
    wf = json.loads(json.dumps(wf))  # deep copy
    base = wf["2"]["inputs"]["prompt"].split(IDEA_MARKER)[0]
    wf["2"]["inputs"]["prompt"] = base + IDEA_MARKER + idea
    wf["2"]["inputs"]["sampling_mode.seed"] = llm_seed
    wf["2"]["inputs"]["max_length"] = max_len
    if "19" in wf:  # image half present (not --dry-run)
        wf["19"]["inputs"]["seed"] = img_seed
        wf["18"]["inputs"]["width"] = width
        wf["18"]["inputs"]["height"] = height
        wf["21"]["inputs"]["filename_prefix"] = prefix
    return wf


def main():
    p = argparse.ArgumentParser()
    p.add_argument("idea")
    p.add_argument("-n", type=int, default=1, help="how many variations")
    p.add_argument("--size", default="1664x928", help="WxH, must be multiples of 16")
    p.add_argument("--prefix", default="claude-generated/13-llm-prompt-studio/idea")
    p.add_argument("--seed", type=int, default=None, help="base seed; omit for random")
    p.add_argument("--max-length", type=int, default=400)
    p.add_argument("--dry-run", action="store_true", help="write the prompt, skip the render")
    p.add_argument("--host", default=DEFAULT_HOST)
    a = p.parse_args()

    width, height = (int(v) for v in a.size.lower().split("x"))
    for dim, name in ((width, "width"), (height, "height")):
        if dim % 16:
            p.error(f"{name}={dim} is not a multiple of 16")

    with open(WF) as f:
        base_wf = json.load(f)
    # keys starting with "_" are documentation, not nodes
    base_wf = {k: v for k, v in base_wf.items() if not k.startswith("_")}

    if a.dry_run:
        # keep only the LLM half so nothing is sampled
        base_wf = {k: v for k, v in base_wf.items() if k in ("1", "2", "3")}

    base_seed = a.seed if a.seed is not None else random.randrange(1 << 30)

    for i in range(a.n):
        llm_seed = base_seed + i * 1000
        img_seed = base_seed + i
        wf = build(base_wf, a.idea, llm_seed, img_seed,
                   width, height, a.prefix, a.max_length)

        label = f"[{i + 1}/{a.n}]" if a.n > 1 else ""
        print(f"{label} idea={a.idea!r} llm_seed={llm_seed} img_seed={img_seed}",
              file=sys.stderr)

        _elapsed, files = run(a.host, wf, quiet=True)

        text = None
        hist = api(a.host, "/history?max_items=1")
        for _pid, entry in hist.items():
            for _nid, out in entry.get("outputs", {}).items():
                if "text" in out and out["text"]:
                    text = out["text"][0]

        if text:
            print("-" * 70)
            print(text)
            print("-" * 70)

        for rel in files or []:
            full = os.path.join(OUTPUT_ROOT, rel)
            print(f"  -> {rel}")
            if text:
                side = os.path.splitext(full)[0] + ".txt"
                try:
                    with open(side, "w") as f:
                        f.write(f"idea: {a.idea}\n")
                        f.write(f"llm_seed: {llm_seed}\nimage_seed: {img_seed}\n")
                        f.write(f"size: {width}x{height}\n\nprompt:\n{text}\n")
                except OSError as e:
                    print(f"  (could not write sidecar: {e})", file=sys.stderr)


if __name__ == "__main__":
    main()
