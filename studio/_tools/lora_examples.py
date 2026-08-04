#!/usr/bin/env python3
"""Render an example for every image LoRA, so a LoRA can be chosen by looking.

    python3 studio/_tools/lora_examples.py
    python3 studio/_tools/lora_examples.py illustration
    python3 studio/_tools/lora_examples.py --sheets-only     # rebuild sheets, no rendering

A LoRA'S EXAMPLE HAS TO BE A PAIR. A LoRA is a delta on the base model's weights, so a
single "with the LoRA" image says nothing at all - you cannot tell what the LoRA did from
it. Every example here is therefore a strength LADDER at a fixed seed and a fixed prompt:
0.0 (the control) alongside the working strengths. The 0.0 cell IS the evidence.

This is the same isolation discipline the rest of the project runs on, and the same one it
has broken before: 133 of 134 capability cards once varied the subject alongside the
variable and so demonstrated nothing.

WHY A LADDER RATHER THAN ON/OFF. Strength is the whole usable range of a style LoRA and the
useful setting is rarely 1.0. Measured on this box: illustration-1.0-qwen-image is a clear
painted illustration at 1.0 and a full watercolour drawing at 1.5 - two genuinely different
looks from one file. An on/off pair would have hidden that.

WHAT THIS DOES NOT COVER, deliberately:
  edit LoRAs   (Relight, multiple-angles, Light-Migration) need a source image and a
               different graph. studio/_tools/qwen_character.py covers those.
  video LoRAs  (ltx-*, wan-*, CausVid) need a clip, not a frame, and belong with the
               video-sample pass that is still outstanding.
  Flux2Turbo   no Flux checkpoint is installed, so it cannot be run at all here.
  gemma-*      a language-model LoRA. Not an image LoRA. Nothing to render.
Each of those is reported as skipped WITH ITS REASON rather than silently omitted - a tool
that quietly renders 6 of 20 and prints "done" is how a gap becomes invisible.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, HOST          # noqa: E402

OUT = os.path.join(STUDIO, "samples", "loras")
SEED = 5150

# The held-constant subject, in each engine's dialect. Same scene both sides so a qwen LoRA
# and an SDXL LoRA are still being judged on the same picture. Deliberately contains a face,
# a garment with folds and a receding street: the three places a rendering change shows.
SUBJ_PROSE = ("a young woman in a wool coat and red scarf standing on a city street, "
              "buildings receding behind her, overcast daylight, facing the camera")
SUBJ_TAGS = ("1girl, solo, upper body, long dark hair, red scarf, wool coat, standing, "
             "looking at viewer, city street, buildings, overcast")
Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG_QWEN = "lowres, bad anatomy, watermark, text"
NEG_ANIME = "lowres, worst quality, bad anatomy, bad hands, watermark, text, signature"

# id, file, engine, strengths, trigger, why this ladder
LADDERS = [
    ("illustration_qwen", "illustration-1.0-qwen-image.safetensors", "qwen",
     [0.0, 0.6, 1.0, 1.5], "",
     "The one that does what no prompt could: Qwen cannot be steered off photography by "
     "prompt at any cfg, but this takes it to painted illustration. 0.6 is included "
     "because the gap between 1.0 and 1.5 was large and the low end was never sampled."),
    ("modern_anime_qwen", "qwen_image_modern_anime_lora.safetensors", "qwen",
     [0.0, 1.0, 1.5], "modern anime style",
     "Did nothing at 1.0 when first measured. The trigger phrase is added here, and 1.5 "
     "sampled, to find out whether it is inert or merely untriggered."),
    ("storybook_anime_qwen", "qwen_image_2512_storybook_anime_lora.safetensors", "qwen",
     [0.0, 0.8, 1.2], "",
     "The one that has been silently ON at 0.8 in every qwen keyframe this project has "
     "ever rendered. 0.8 is therefore not a sample - it is what the project has been "
     "shipping. The 0.0 cell shows what it has been doing all along."),
    ("character_viro", "character_viro_00001_.safetensors", "anime",
     [0.0, 0.5, 0.85], "",
     "Trained on this box from a turnaround. Included as the reference for what a CHARACTER "
     "LoRA looks like next to a style LoRA. Note 0.85 was previously measured to degrade "
     "the setting, which is why 0.5 is sampled."),
]

SKIPPED = [
    ("Qwen-Image-Edit-2509-Relight", "edit LoRA - needs a source image and the edit graph; "
     "covered by studio/_tools/qwen_character.py"),
    ("qwen-image-edit-2511-multiple-angles-lora", "edit LoRA - needs a source image; "
     "covered by studio/_tools/qwen_character.py"),
    ("Qwen-Image-Edit-2509-Light-Migration", "edit LoRA - needs a source image"),
    ("Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16", "speedup for the EDIT model; its "
     "effect is step count, not appearance"),
    ("Qwen-Image-2512-Lightning-4steps-V1.0-fp32", "speedup - it is what makes a qwen frame "
     "take 4 steps instead of 20. Its example is a step-count comparison, not a strength "
     "ladder, and it is load-bearing for every render here"),
    ("ltx_2.3_22b_distilled_1.1_lora_dynamic_fro09_avg_rank_111_bf16", "video"),
    ("ltx-2.3-22b-ic-lora-union-control-ref0.5", "video"),
    ("ltx-2.3-id-lora-talkvid-3k", "video"),
    ("ltx2.3-transition", "video"),
    ("Wan21_CausVid_14B_T2V_lora_rank32", "video"),
    ("wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise", "video"),
    ("wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise", "video"),
    ("Flux2TurboComfyv2", "no Flux checkpoint is installed on this box - cannot be run"),
    ("gemma-3-12b-it-abliterated_lora_rank64_bf16", "a language-model LoRA, not an image one"),
    ("removal_timestep_alpha-2-1740", "purpose not established - left untested rather than "
     "guessed at"),
]


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def build(engine, lora, strength, trigger):
    if engine == "qwen":
        wf = load_wf("13_qwen_t2i_styled.json")
        prose = SUBJ_PROSE
        if trigger and strength > 0:
            prose = trigger + ". " + prose
        set_path(wf, "10.inputs.text", prose)
        set_path(wf, "11.inputs.text", NEG_QWEN)
        set_path(wf, "12.inputs.width", 1024)
        set_path(wf, "12.inputs.height", 1024)
        set_path(wf, "13.inputs.seed", SEED)
        # node 7 is the style-LoRA slot. Setting the name even at strength 0 keeps the
        # graph identical between cells, so the control differs ONLY by strength.
        set_path(wf, "7.inputs.lora_name", lora)
        set_path(wf, "7.inputs.strength_model", strength)
        return wf, "15.inputs.filename_prefix"

    wf = load_wf("22_anime_kf_ipadapter.json")
    set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
    set_path(wf, "4.inputs.weight", 0.0)
    tags = SUBJ_TAGS
    if trigger and strength > 0:
        tags = trigger + ", " + tags
    set_path(wf, "5.inputs.text", tags + ", " + Q)
    set_path(wf, "6.inputs.text", NEG_ANIME)
    set_path(wf, "8.inputs.seed", SEED)
    for n in ("7", "10"):
        set_path(wf, "%s.inputs.width" % n, 1024)
        set_path(wf, "%s.inputs.height" % n, 1024)
    if strength > 0:
        wf["90"] = {"class_type": "LoraLoaderModelOnly",
                    "inputs": {"model": ["1", 0], "lora_name": lora,
                               "strength_model": strength}}
        for nid, node in list(wf.items()):
            if nid in ("1", "90") or not isinstance(node, dict):
                continue
            for k, v in (node.get("inputs") or {}).items():
                if isinstance(v, list) and len(v) == 2 and v[0] == "1" and v[1] == 0:
                    node["inputs"][k] = ["90", 0]
    return wf, "11.inputs.filename_prefix"


def sheet(lid, cells, why):
    """One row per LoRA, control leftmost, so the delta reads left to right."""
    tmp = "/tmp/_lx_%s" % lid
    os.system("rm -rf %s && mkdir -p %s" % (tmp, tmp))
    for i, (label, path) in enumerate(cells):
        sh("ffmpeg", "-y", "-v", "error", "-i", path, "-vf",
           "scale=520:-1,drawtext=text='%s':fontcolor=yellow:fontsize=21:x=6:y=6:"
           "box=1:boxcolor=black@0.85:boxborderw=6" % label.replace(":", "\\:"),
           os.path.join(tmp, "%02d.png" % i))
    dst = os.path.join(OUT, "%s__ladder.jpg" % lid)
    sh("ffmpeg", "-y", "-v", "error", "-pattern_type", "glob",
       "-i", os.path.join(tmp, "*.png"), "-filter_complex",
       "tile=%dx1:margin=5:padding=5:color=0x111111" % len(cells),
       "-frames:v", "1", "-q:v", "3", dst)
    os.system("rm -rf %s" % tmp)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("only", nargs="?")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    made = 0
    for lid, lfile, engine, strengths, trigger, why in LADDERS:
        if a.only and not lid.startswith(a.only):
            continue
        print("\n%s  (%s, %s)" % (lid, engine, lfile))
        print("  %s" % why)
        cells = []
        for s in strengths:
            tag = "%s_%03d" % (lid, int(s * 100))
            dst = os.path.join(OUT, "%s.webp" % tag)
            if not os.path.exists(dst) or a.force:
                wf, prefix = build(engine, lfile, s, trigger)
                set_path(wf, prefix, "claude-generated/studio_loras/%s" % tag)
                try:
                    _, outs = run(HOST, wf, quiet=True)
                except Exception as e:
                    print("    %.2f  FAILED %s" % (s, str(e)[:70]))
                    continue
                if not outs:
                    print("    %.2f  no output" % s)
                    continue
                loc = ensure_local(outs[0], "/tmp/_lx_%s.png" % tag, required=False)
                if not loc:
                    continue
                sh("ffmpeg", "-y", "-v", "error", "-i", loc, "-vf", "scale=680:-1",
                   "-quality", "82", dst)
                try:
                    os.remove(loc)
                except OSError:
                    pass
                made += 1
            if os.path.exists(dst):
                lab = "OFF (control)" if s == 0 else "strength %.2f" % s
                if trigger and s > 0:
                    lab += " +trigger"
                cells.append((lab, dst))
                print("    %.2f  ok" % s, flush=True)
        if cells:
            print("  -> %s" % sheet(lid, cells, why))

    print("\n%d frames rendered." % made)
    print("\nNOT COVERED HERE, with reasons - so the gaps stay visible:")
    for name, reason in SKIPPED:
        print("  %-46s %s" % (name[:46], reason))
    print("\nNOW LOOK AT THE LADDERS. The 0.0 cell is the evidence; a LoRA image without "
          "its control proves nothing.")


if __name__ == "__main__":
    main()
