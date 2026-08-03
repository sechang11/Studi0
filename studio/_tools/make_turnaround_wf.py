#!/usr/bin/env python3
"""Write workflows/32_qwen_turnaround.json - one image of a person, many angles of them.

Derived from 22_qwen_edit_2511 by chaining a SECOND model LoRA:

    UNETLoader -> LoraLoaderModelOnly(Lightning 4-step) -> LoraLoaderModelOnly(angles)
               -> ModelSamplingAuraFlow -> CFGNorm -> KSampler

qwen-image-edit-2511-multiple-angles-lora has been sitting on disk unused. It is the
piece that turns "a picture of a character" into "a character", because it re-poses the
SAME person rather than generating a new one that merely matches the description.

That matters twice over:
  - a multi-angle reference sheet locks identity far better than a single portrait
  - it is also the training set for a character LoRA, which is the only way identity
    truly holds. Producing 20-40 consistent views of one person by hand is the reason
    character training normally does not happen.

Accelerator LoRAs have ONE correct strength - 1.0. It is sampler configuration, not a
taste dial, and 1.3 is damage rather than more style. The angles LoRA is a style/behaviour
LoRA and sits lower; 0.85 is the starting point here and is exposed so it can be tuned
against actual output rather than guessed once.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
WF = os.path.join(ROOT, "workflows")

src = json.load(open(os.path.join(WF, "22_qwen_edit_2511.json"), encoding="utf-8"))
wf = {k: v for k, v in src.items() if not k.startswith("_")}

# node 4 is the Lightning accelerator. Insert the angles LoRA after it and re-point
# whatever consumed node 4's model at the new node instead.
ANGLES = "qwen-image-edit-2511-multiple-angles-lora.safetensors"
NEW = "40"
wf[NEW] = {
    "class_type": "LoraLoaderModelOnly",
    "inputs": {"model": ["4", 0], "lora_name": ANGLES, "strength_model": 0.85},
    "_note": "multiple-angles LoRA. Chained AFTER the 4-step accelerator, which must "
             "stay at strength 1.0 - it is sampler config, not style.",
}
for nid, node in wf.items():
    if nid in ("4", NEW) or not isinstance(node, dict):
        continue
    for key, val in (node.get("inputs") or {}).items():
        if isinstance(val, list) and len(val) == 2 and val[0] == "4":
            node["inputs"][key] = [NEW, val[1]]

wf["17"]["inputs"]["filename_prefix"] = "claude-generated/studio_cast/turnaround"
wf["10"]["inputs"]["prompt"] = "side view of the same person, facing left"
wf["15"]["inputs"]["seed"] = 11
wf["_doc"] = ("Turnaround: re-pose ONE person into many views. Set 7.inputs.image to the "
              "source, 10.inputs.prompt to the view you want, 15.inputs.seed per view, "
              "17.inputs.filename_prefix to where it lands. Keep 4.strength_model at 1.0; "
              "tune 40.strength_model if identity drifts (lower) or the pose does not "
              "change (higher).")

out = os.path.join(WF, "32_qwen_turnaround.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(wf, f, indent=2, ensure_ascii=False)
    f.write("\n")
print("wrote", out)
print("  angles LoRA on node", NEW, "at strength", wf[NEW]["inputs"]["strength_model"])
print("  rewired consumers of node 4 ->", NEW)
