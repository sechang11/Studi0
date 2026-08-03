#!/usr/bin/env python3
"""Render every option of every renderable card in studio/cards_spec.json.

    python3 studio/gen_cards.py                 # everything not already rendered
    python3 studio/gen_cards.py --only shot     # one namespace
    python3 studio/gen_cards.py --dry           # what it would do, no GPU

Each panel uses the SAME subject sentence and the SAME seed. Only the option clause
changes, so any visible difference is the variable and nothing else.

FIXES APPLIED TO THE AUTHORED SPECS, from the review pass:

  * NEGATION DOES NOT EXIST in an SDXL positive prompt. A clause of "no lens flare" adds
    lens flare - the model sees the tokens, not the "no". Every option whose value means
    "absent" (none / off / flat / straight / neutral where it is the null case) therefore
    gets an EMPTY clause and renders the untouched subject. That panel is the control, and
    it is the honest way to show absence.
  * Options that fight the fixed subject sentence (framing_type asking for 3boys while the
    subject says "1boy, solo") drop the conflicting part of the subject instead of stacking
    a contradiction the model resolves at random.
"""
import argparse, io, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_ROOT", "Z:/ComfyUI")
# Default to the LOCAL ComfyUI. This used to hardcode 192.168.1.46, which broke
# when DHCP moved the box to .45, and which also sent every render request across
# a NIC measured dropping 10% of packets. Nothing here needs the network: these
# scripts run ON the box. Set COMFY_HOST to drive a remote instance.
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

OUT = f"{HERE}/samples/vars"
CARDS = f"{HERE}/cards"
W, H = 640, 360
SEED = 9001
Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG = ("1girl, female, lowres, worst quality, bad anatomy, bad hands, watermark, text, "
       "multiple views, photorealistic, 3d, western comic, blurry")
SUBJ = ("1boy, solo, male focus, dark red hair, undercut, yellow eyes, black soccer jersey, "
        "number 9, soccer stadium, floodlights, crowd")
SUBJ_NOSOLO = SUBJ.replace("1boy, solo, ", "").replace("male focus, ", "male focus, ")

# option values that mean "this thing is absent" - they must render the untouched control
NULLS = {"none", "off", "no", "false", "disabled", "flat", "neutral", "static", "straight"}


def sh(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"failed {' '.join(a[:4])}\n{(r.stderr or '')[-400:]}")


def clean(card, opt):
    """Return the prompt for one panel, with the review's fixes applied."""
    val = str(opt.get("value", "")).strip().lower()
    clause = (opt.get("clause") or "").strip()
    # absence renders as the control, never as a negation the model cannot parse
    if val in NULLS or re.match(r"^(no|without)[\s_]", clause.lower()):
        clause = ""
    subj = SUBJ
    # a card about how many people are in frame must be allowed to change that
    if re.search(r"\d\s*boys|multiple|group|crowd|two_shot|three_shot|over_shoulder",
                 val + " " + clause):
        subj = SUBJ_NOSOLO
    return ", ".join(x for x in (subj, clause, Q) if x), (clause == "")


def gen(prompt, dest, tag):
    from comfy import run
    from epic import ensure_local, COMFY, HOST
    wf = {"1": {"class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "animagine-xl-4.0.safetensors"}},
          "2": {"class_type": "EmptyLatentImage",
                "inputs": {"width": 1344, "height": 768, "batch_size": 1}},
          "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": prompt}},
          "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": NEG}},
          "5": {"class_type": "KSampler",
                "inputs": {"model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0],
                           "latent_image": ["2", 0], "seed": SEED, "steps": 28, "cfg": 5.0,
                           "sampler_name": "euler_ancestral", "scheduler": "normal",
                           "denoise": 1.0}},
          "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
          "7": {"class_type": "SaveImage",
                "inputs": {"images": ["6", 0],
                           "filename_prefix": f"claude-generated/studio_cards/{tag}"}}}
    run(HOST, wf, quiet=True)
    tmp = f"{COMFY}/output/claude-generated/studio_cards/{tag}_00001_.png"
    ensure_local(f"claude-generated/studio_cards/{tag}_00001_.png", tmp, required=True)
    sh("ffmpeg", "-y", "-v", "error", "-i", tmp, "-vf", f"scale={W}:{H}", dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    spec = json.load(io.open(f"{HERE}/cards_spec.json", encoding="utf-8"))
    os.makedirs(CARDS, exist_ok=True)

    todo = [c for c in spec if c.get("renderable")
            and (not a.only or c["variable"].startswith(a.only))]
    total = sum(len(c.get("options", [])) for c in todo)
    print(f"{len(todo)} cards, {total} panels")
    done = 0
    for c in todo:
        slug = c["variable"].replace(".", "_")
        d = f"{OUT}/{slug}"
        os.makedirs(d, exist_ok=True)
        panels = []
        for opt in c.get("options", []):
            val = re.sub(r"[^a-z0-9_]+", "_", str(opt.get("value", "x")).lower())
            dest = f"{d}/{val}.png"
            prompt, is_control = clean(c, opt)
            if not a.dry and not os.path.exists(dest):
                gen(prompt, dest, f"{slug}__{val}")
            done += 1
            panels.append({"value": opt.get("value"), "clause": opt.get("clause", ""),
                           "control": is_control,
                           "sample": f"/samples/vars/{slug}/{val}.png"})
            if done % 40 == 0:
                print(f"  {done}/{total}", flush=True)
        card = {"variable": c["variable"], "claim": c.get("claim", ""),
                "method": "identical subject sentence and seed in every panel; only the "
                          "option clause changes. panels marked control render the "
                          "untouched subject, because SDXL cannot express absence.",
                "model": "animagine-xl-4.0, 28 steps, cfg 5.0, euler_ancestral",
                "panels": panels}
        if c.get("review"):
            card["review"] = c["review"]
        if not a.dry:
            io.open(f"{CARDS}/{slug}.json", "w", encoding="utf-8").write(
                json.dumps(card, indent=2, ensure_ascii=False) + "\n")

    # the non-visual ones get a card too - stating WHY there is nothing to show
    for c in spec:
        if c.get("renderable"):
            continue
        slug = c["variable"].replace(".", "_")
        if not a.dry:
            io.open(f"{CARDS}/{slug}.json", "w", encoding="utf-8").write(json.dumps(
                {"variable": c["variable"], "claim": c.get("claim", ""),
                 "not_visual": c.get("skip_reason", "cannot be shown in a still image"),
                 "options": [o.get("value") for o in c.get("options", [])],
                 "panels": []}, indent=2, ensure_ascii=False) + "\n")
    print(f"\n{done} panels, {len([f for f in os.listdir(CARDS) if f.endswith('.json')])} cards")


if __name__ == "__main__":
    main()
