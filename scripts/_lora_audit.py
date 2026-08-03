#!/usr/bin/env python3
"""Audit which LoRA files the built-in templates expect, and which we have.

Throwaway helper used to build the verified shopping list in LORAS.md.
Run: python3 scripts/_lora_audit.py
"""
import json
import os

TPL = os.path.expanduser(
    "~/ComfyUI/venv/lib/python3.14/site-packages/"
    "comfyui_workflow_templates_json/templates"
)
LORA_DIR = os.path.expanduser("~/ComfyUI/models/loras")

refs = {}


def scan(nodes, src):
    for n in nodes:
        if "ora" not in n.get("type", ""):          # LoraLoader, LoraLoaderModelOnly, ...
            continue
        for v in n.get("widgets_values") or []:
            if isinstance(v, str) and v.endswith(".safetensors"):
                refs.setdefault(v, set()).add(src)


for fn in sorted(os.listdir(TPL)):
    if not fn.endswith(".json") or fn == "index.json":
        continue
    try:
        d = json.loads(open(os.path.join(TPL, fn), encoding="utf-8").read())
    except Exception:
        continue
    if not isinstance(d, dict):   # a few templates are bare lists
        continue
    stem = fn[:-5]
    scan(d.get("nodes", []), stem)
    for sg in d.get("definitions", {}).get("subgraphs", []) or []:
        scan(sg.get("nodes", []), stem)

have = set(os.listdir(LORA_DIR)) if os.path.isdir(LORA_DIR) else set()

print(f"{len(refs)} distinct LoRA files referenced by built-in templates")
print(f"{len(have & set(refs))} of them installed\n")
for name in sorted(refs, key=lambda n: (n not in have, n.lower())):
    mark = "HAVE" if name in have else " -- "
    users = sorted(refs[name])
    shown = ", ".join(users[:3]) + (f" (+{len(users) - 3})" if len(users) > 3 else "")
    print(f"[{mark}] {name}")
    print(f"        {shown}")
