#!/usr/bin/env python3
"""
sweep.py - vary ONE input across a list of values and render each.

The workhorse for learning what a knob actually does, and for building
style/variation sheets. Every render gets a .txt sidecar recording the value that
produced it, so a sheet stays self-explaining after you forget what you ran.

    # style range: same subject, twelve media
    python3 scripts/sweep.py workflows/01_qwen_t2i_turbo.json 10.inputs.text \
        --from-file sweeps/styles.txt \
        --prefix claude-generated/16-style-range/style

    # what a knob does: LoRA strength
    python3 scripts/sweep.py workflows/01_qwen_t2i_turbo.json 4.inputs.strength_model \
        --values 0.5,0.75,1.0,1.25 \
        --prefix claude-generated/17-lora-mechanics/strength

    # hold a second input constant across the whole sweep
    python3 scripts/sweep.py workflows/01_qwen_t2i_turbo.json 13.inputs.steps \
        --values 4,8,20 -s 13.inputs.seed=99 \
        --prefix claude-generated/17-lora-mechanics/steps

--from-file reads one value per line. Lines that are blank or start with # are
skipped. A line may be `label :: value` - the label goes in the sidecar and the
filename, which is what makes a style sheet readable later.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_ROOT = os.path.expanduser("~/ComfyUI/output")

sys.path.insert(0, HERE)
from comfy import run, set_path, DEFAULT_HOST  # noqa: E402


def slug(text, limit=40):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit] or "value"


def load_values(a, parser):
    if a.from_file:
        path = a.from_file
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(HERE), path)
        out = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                label, sep, value = line.partition("::")
                out.append((label.strip(), value.strip()) if sep
                           else (slug(line), line))
        return out
    if a.values:
        return [(slug(v.strip()), v.strip()) for v in a.values.split(",")]
    parser.error("give --values or --from-file")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("workflow")
    p.add_argument("target", help="dotted path, e.g. 10.inputs.text")
    p.add_argument("--values", help="comma-separated list")
    p.add_argument("--from-file", help="one value per line; 'label :: value' supported")
    p.add_argument("--prefix", required=True, help="SaveImage filename_prefix base")
    p.add_argument("--save-node", default=None,
                   help="node id of the SaveImage/SaveVideo to retarget (default: autodetect)")
    p.add_argument("-s", "--set", action="append", default=[],
                   help="extra constant override, repeatable")
    p.add_argument("--host", default=DEFAULT_HOST)
    a = p.parse_args()

    values = load_values(a, p)

    with open(a.workflow, encoding="utf-8") as f:
        base = json.load(f)
    base = {k: v for k, v in base.items() if not k.startswith("_")}

    save_node = a.save_node
    if save_node is None:
        saves = [nid for nid, n in base.items()
                 if n.get("class_type", "").startswith(("SaveImage", "SaveVideo", "SaveAudio"))]
        if len(saves) != 1:
            p.error(f"found {len(saves)} save nodes {saves}; pass --save-node")
        save_node = saves[0]

    print(f"sweeping {a.target} over {len(values)} value(s); "
          f"writing via node {save_node}", file=sys.stderr)

    total = 0.0
    for i, (label, value) in enumerate(values, 1):
        wf = json.loads(json.dumps(base))
        set_path(wf, a.target, value)
        for kv in a.set:
            k, _, v = kv.partition("=")
            set_path(wf, k, v)
        prefix = f"{a.prefix}_{i:02d}_{label}"
        set_path(wf, f"{save_node}.inputs.filename_prefix", prefix)

        shown = value if len(str(value)) < 70 else str(value)[:67] + "..."
        print(f"[{i}/{len(values)}] {label} = {shown}", file=sys.stderr)

        elapsed, files = run(a.host, wf, quiet=True)
        total += elapsed
        for rel in files or []:
            side = os.path.splitext(os.path.join(OUTPUT_ROOT, rel))[0] + ".txt"
            try:
                with open(side, "w", encoding="utf-8") as f:
                    f.write(f"label: {label}\n{a.target}: {value}\n")
                    for kv in a.set:
                        f.write(f"{kv}\n")
            except OSError as e:
                print(f"  (sidecar failed: {e})", file=sys.stderr)

    print(f"\nsweep done: {len(values)} renders in {total:.1f}s "
          f"({total/max(len(values),1):.1f}s each)", file=sys.stderr)


if __name__ == "__main__":
    main()
