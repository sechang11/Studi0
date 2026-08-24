#!/usr/bin/env python3
"""A STAND-IN PHOTOGRAPH for the head pipeline.

The head path takes a photograph of a real person. There is not one on this box, and the
point of the demonstration is the pipeline rather than the person - so this generates an
ordinary portrait of nobody in particular and drops it in studio/uploads, which is where
`bobble.py head` and the /three page both look.

Replace it with a real photo and nothing about the route changes. It is deliberately shot
the way a phone photo is - one soft key light, a plain wall, head and shoulders - so the
figurine pass in bobble.stage_stylize is doing the same work it would do on a real one.
"""
import os
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                                       # noqa: E402
from epic import load_wf, ensure_local, HOST                          # noqa: E402

PROMPT = (
    "A candid head-and-shoulders photograph of a smiling man in his late thirties, "
    "short dark tidy hair, light stubble, a plain navy crew-neck jumper, "
    "photographed against a plain off-white wall with one soft window light from the "
    "left, looking straight at the camera, natural skin texture, 50mm lens, "
    "shallow depth of field, ordinary snapshot")
NEG = ("illustration, painting, 3d render, cgi, cartoon, doll, figurine, "
       "watermark, text, logo, multiple people, blurry, distorted face")

dst = os.path.join(ROOT, "studio", "uploads", "stand_in_portrait.png")
wf = load_wf("01_qwen_t2i_turbo.json")
set_path(wf, "10.inputs.text", PROMPT)
set_path(wf, "11.inputs.text", NEG)
set_path(wf, "12.inputs.width", 1024)
set_path(wf, "12.inputs.height", 1280)
set_path(wf, "13.inputs.seed", 4242)
set_path(wf, "15.inputs.filename_prefix", "claude-generated/bobble/stand_in_portrait")
_, outs = run(HOST, wf, quiet=True)
if not outs:
    raise SystemExit("no output")
if os.path.exists(dst):
    os.remove(dst)
ensure_local(outs[0], dst)
print(dst)
