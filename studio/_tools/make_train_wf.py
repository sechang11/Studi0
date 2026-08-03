#!/usr/bin/env python3
"""Write workflows/33_train_character_lora.json.

ComfyUI ships native training nodes - TrainLoraNode, MakeTrainingDataset, SaveLoRA,
LoadImageTextDataSetFromFolder - and nothing in this project has ever used one. The
capability folder for LoRA training has said "not-explored" since it was written, and
`32_train_character_lora` was listed as a TODO in _write_caps.py rather than existing as
a file.

    LoadImageTextDataSetFromFolder(folder)  -> IMAGE, STRING
    CheckpointLoaderSimple                  -> MODEL, CLIP, VAE
    MakeTrainingDataset(images, vae, clip, texts) -> LATENT, CONDITIONING
    TrainLoraNode(model, latents, positive, ...)  -> LORA_MODEL
    SaveLoRA(lora, prefix)

WHY THIS IS THE POINT OF THE WHOLE CAST IDEA

Every consistency mechanism here so far is a workaround for not having this. Tags
describe a person and do not make the same face twice. IPAdapter refines a face from one
reference, and a weight sweep on this box found the character was "already recognisable
at ZERO" - the single sheet was doing far less than assumed. A character that is a PROMPT
cannot reliably be the same person. A character that is a trained LoRA can.

DEFAULTS, AND WHY THEY ARE NOT THE NODE'S

TrainLoraNode defaults to steps=16, which is a smoke test - it will produce a file that
changes nothing. A small character set of 16-40 images wants roughly 800-1500 steps.
rank 16 rather than 8, because a face needs more capacity than a style. learning_rate is
left at the node default; it is the parameter most likely to need tuning against actual
output, and guessing a "better" one without measuring would be exactly the mistake this
project keeps writing down.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
WF = os.path.join(ROOT, "workflows")

wf = {
    "_doc": ("Train a character LoRA from a folder of images+captions under "
             "ComfyUI/input. Set 1.inputs.folder to the dataset, 5.inputs.steps to the "
             "budget, 6.inputs.prefix to where it lands. Driven by "
             "studio/_tools/train_character.py."),

    "1": {"class_type": "LoadImageTextDataSetFromFolder",
          "inputs": {"folder": "viro_train"},
          "_note": "the dropdown lists directories under ComfyUI/input only. A dataset "
                   "anywhere else is invisible to this node however well formed."},

    "2": {"class_type": "CheckpointLoaderSimple",
          "inputs": {"ckpt_name": "animagine-xl-4.0.safetensors"},
          "_note": "train against the SAME checkpoint the films render on. A LoRA is a "
                   "delta on specific weights; trained against one base and applied to "
                   "another it degrades or does nothing."},

    "3": {"class_type": "MakeTrainingDataset",
          "inputs": {"images": ["1", 0], "texts": ["1", 1],
                     "vae": ["2", 2], "clip": ["2", 1]}},

    "5": {"class_type": "TrainLoraNode",
          "inputs": {
              "model": ["2", 0],
              "latents": ["3", 0],
              "positive": ["3", 1],
              "batch_size": 1,
              "grad_accumulation_steps": 1,
              # the node default is 16, which is a smoke test and produces a LoRA that
              # changes nothing. 16-40 images wants ~800-1500.
              "steps": 1000,
              "learning_rate": 0.0005,
              # a face needs more capacity than a style; 8 is the node default
              "rank": 16,
              "optimizer": "AdamW",
              "loss_function": "MSE",
              "seed": 7311,
              "training_dtype": "bf16",
              "lora_dtype": "bf16",
              "quantized_backward": False,
              "algorithm": "LoRA",
              # 32 GB is comfortable for SDXL at rank 16, but checkpointing costs little
              # and removes the OOM class of failure entirely
              "gradient_checkpointing": True,
              "checkpoint_depth": 1,
              "offloading": False,
              "existing_lora": "[None]",
              "bucket_mode": False,
              "bypass_mode": False,
          }},

    "6": {"class_type": "SaveLoRA",
          "inputs": {"lora": ["5", 0], "prefix": "loras/character_viro"}},
}

out = os.path.join(WF, "33_train_character_lora.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(wf, f, indent=2, ensure_ascii=False)
    f.write("\n")
print("wrote", out)
print("  dataset -> MakeTrainingDataset -> TrainLoraNode -> SaveLoRA")
print("  steps %d, rank %d, lr %s, base %s" % (
    wf["5"]["inputs"]["steps"], wf["5"]["inputs"]["rank"],
    wf["5"]["inputs"]["learning_rate"], wf["2"]["inputs"]["ckpt_name"]))
