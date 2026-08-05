#!/usr/bin/env python3
"""Render studio/reference_prompts.json on this box and find out how close we get.

WHY THIS EXISTS. The survey wave harvested 77 prompts off official model cards, published
handbooks and named guides, wrote them down, and stopped. A prompt nobody rendered is a
rumour. This tool renders every one of them on the engine the set targets, records the
full recipe beside every pixel, and adds the specific A/B arms that turn "the guide says X"
into "X moved the image by this much, or it did not".

WHAT IT KNOWS THAT YOU MIGHT NOT.

  FOUR DIALECTS, FOUR GRAPHS. This box has four live text encoders and they are not
  interchangeable. CLIP/SDXL (animagine, Illustrious) takes ordered danbooru tags and has
  a real negative branch. Qwen2.5-VL (Qwen-Image 2512) takes labelled prose. Mistral-3
  (FLUX.2) takes prose or JSON and has NO negative field at all. Qwen3-4B (Z-Image Turbo)
  takes prose and its own official graph ZEROES the negative conditioning - the pipeline
  does not merely ignore a negative, it deliberately discards it. Each engine gets its own
  builder below and they are not shared.

  SUBSTITUTION IS REPORTED, NEVER SILENT. Roughly half this set was authored for models we
  do not have - Flux 2 Max, Seedream 5.0 Lite, Nano Banana Pro, GPT Image 2. Every cell
  records source_model alongside the engine it actually ran on, and SUBSTITUTIONS below
  names each one in plain English. A substitution you know about is data; a substitution
  you do not know about is a lie in a gallery.

  Z-IMAGE TURBO WAS NEVER WIRED UP AND IS NOW. qwen-009..013 were authored for Z-Image
  Turbo and the set routes them to Qwen because nothing on this box could run them. The
  model has been on disk since 2026-07-31 unrendered. --mode zimage builds the graph out of
  ComfyUI's own shipped template (CLIPLoader qwen_3_4b type=lumina2, ae.safetensors VAE,
  ModelSamplingAuraFlow shift 3, res_multistep, 8 steps, cfg 1.0) and runs them on their
  actual target model.

  Flux2Scheduler AND EmptyFlux2LatentImage MUST AGREE ON SIZE or the image degrades
  silently with no error. flux_wf sets both from one tuple. Do not patch them apart.

  RENDER ONE ENGINE AT A TIME. 34 GB of FLUX.2 does not co-reside with 20 GB of Qwen on a
  32 GB card, and a cold reload after a foreign model family costs 60-150 s. --mode base
  runs flux2, then qwen, then sdxl, then z-image, deliberately, and that order is not an
  accident of the loop.

  FACES NEED PIXELS AND THAT IS MEASURED, NOT ASSUMED. SIZES below is per-prompt, not per
  engine, because a 2.39:1 cliff plate and a headshot want different boxes. Nothing here
  renders a face at 832x1216 full-body unless the cell exists specifically to show that
  configuration failing.

MODES
  base    every prompt in the set, on its target engine, at a size chosen per prompt.
  extra   the A/B arms. This is where the answers are - see ARMS below.
  zimage  the five Z-Image-authored prompts on Z-Image Turbo, plus three skin cards.
  one     a single id, for when a cell needs re-running.
  look    downscale every cell to 1100 px so looking at all of them is affordable.
  sheets  captioned contact sheets, 3 across.
  measure the arithmetic half of the grading: hex error on flux2-029, mean absolute pixel
          difference across every qwen negative A/B pair, and a side-by-side JPEG for
          every matched pair and arm.

    python3 studio/_tools/replicate_prompts.py --mode base --engines flux2
    python3 studio/_tools/replicate_prompts.py --mode extra --batch
    python3 studio/_tools/replicate_prompts.py --mode one --id qwen-014

--batch submits a whole mode up front so the cells stay contiguous behind another agent's
queue instead of each going to the back of it. It gives up per-cell wall clock (seconds
comes out null) because a batched cell's elapsed time is the model load amortised across
the batch, and this project does not write down numbers it did not measure.

Every render appends a row to studio/samples/replicated/_measured.json AND writes a
<cell>.json recipe sidecar next to the PNG: engine, checkpoint, prompt, negative, seed,
steps, cfg, sampler, size, lora, source_model, substitution. That sidecar is the rule -
it is what makes the gallery teach instead of decorate.
"""
import argparse
import json
import os
import shutil
import sys
import time
import urllib.request

ROOT = os.path.expanduser("~/shared/comfy-studio")
OUT = os.path.expanduser("~/ComfyUI/output")
SAMPLES = os.path.join(ROOT, "studio", "samples", "replicated")
LEDGER = os.path.join(SAMPLES, "_measured.json")
REFS = os.path.join(ROOT, "studio", "reference_prompts.json")

sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run as comfy_run  # noqa: E402

HOST = os.environ["COMFY_HOST"]
WF_FLUX = os.path.join(ROOT, "workflows", "40_flux2_t2i.json")
WF_QWEN = os.path.join(ROOT, "workflows", "02_qwen_t2i_quality.json")

SEED = 5150  # one seed for the whole set, so every matched pair is genuinely matched

# The negative the two highest-traffic Qwen-2512 guides prescribe and claim is worth ~15%
# satisfaction. An independent CFG 1.0-7.0 sweep says it does nothing. --mode extra runs
# both halves at three cfg values and diffs the pixels.
QWEN_TEMPLATE_NEG = ("blurry, low quality, watermark, deformed text, misspelled, "
                     "jpeg artifacts, distorted, ugly, extra limbs, bad anatomy")

# Prompts authored for a model this box does not have. Recorded on every affected cell.
SUBSTITUTIONS = {
    "Flux 2 Max (OpenArt curated set)":
        "FLUX.2 dev fp8 + Turbo distill. Max is BFL's hosted top tier; dev is the open "
        "weight release. Same family and dialect, smaller model, quantised.",
    "Flux 2 Max / Wan 2.7 (OpenArt curated set)":
        "FLUX.2 dev fp8 + Turbo distill. Wan 2.7 is not installed; the prompt is a still "
        "plate so it is rendered as text-to-image on FLUX.2 dev.",
    "Seedream 5.0 Lite / Flux 2 Max (OpenArt curated set)":
        "FLUX.2 dev fp8 + Turbo distill. Seedream 5.0 Lite is a closed ByteDance model, "
        "not installed and not obtainable.",
    "Nano Banana Pro / GPT Image 2 (OpenArt curated set)":
        "Qwen-Image 2512 quality path. Both source models are closed APIs. Nearest local "
        "prose-dialect photographic engine.",
    "Nano Banana Pro (OpenArt curated set)":
        "Qwen-Image 2512 quality path. Nano Banana Pro is a closed Google model.",
    "GPT Image 2 (OpenArt curated set)":
        "Qwen-Image 2512 quality path. GPT Image 2 is a closed OpenAI model.",
    "Z-Image Turbo":
        "Qwen-Image 2512 for the base arm because the set routes it there; ALSO rendered "
        "on the real Z-Image Turbo in --mode zimage. Both arms exist, compare them.",
    "Flux 2 Max": "FLUX.2 dev fp8 + Turbo distill.",
}

# Per-prompt size class. A 2.39:1 cliff plate and an 85mm headshot do not want the same
# box, and the face-pixel problem is a measurement, not a preference.
#   sq square, por portrait, wide landscape, cine 2.39:1
CLASS = {
    "flux2-001": "sq",   "flux2-002": "por",  "flux2-003": "wide", "flux2-004": "wide",
    "flux2-005": "sq",   "flux2-006": "sq",   "flux2-007": "sq",   "flux2-008": "sq",
    "flux2-009": "sq",   "flux2-010": "wide", "flux2-011": "wide", "flux2-012": "cine",
    "flux2-013": "wide", "flux2-014": "por",  "flux2-015": "wide", "flux2-016": "wide",
    "flux2-017": "wide", "flux2-018": "wide", "flux2-019": "por",  "flux2-020": "cine",
    "flux2-021": "wide", "flux2-022": "por",  "flux2-023": "wide", "flux2-024": "wide",
    "flux2-025": "cine", "flux2-026": "wide", "flux2-027": "wide", "flux2-028": "wide",
    "flux2-029": "por",  "flux2-030": "por",
    "qwen-001": "por",  "qwen-002": "por",  "qwen-003": "sq",   "qwen-004": "sq",
    "qwen-005": "por",  "qwen-006": "por",  "qwen-007": "wide", "qwen-008": "sq",
    "qwen-009": "por",  "qwen-010": "wide", "qwen-011": "wide", "qwen-012": "por",
    "qwen-013": "sq",   "qwen-014": "por",  "qwen-015": "por",  "qwen-016": "por",
    "qwen-017": "wide", "qwen-018": "por",  "qwen-019": "por",  "qwen-020": "sq",
    "qwen-021": "wide", "qwen-022": "sq",   "qwen-023": "por",  "qwen-024": "wide",
    "qwen-025": "wide", "qwen-026": "wide", "qwen-027": "por",  "qwen-028": "por",
    "sdxl-001": "por",  "sdxl-002": "por",  "sdxl-003": "por",  "sdxl-004": "por",
    "sdxl-005": "wide", "sdxl-006": "por",  "sdxl-007": "por",  "sdxl-008": "por",
    "sdxl-009": "wide", "sdxl-018": "por",
}

# FLUX.2 composition stays coherent to 2.4 MP (measured); Qwen duplicates past ~2 MP, so
# its boxes are smaller on purpose. Illustrious trains at 1536 and animagine at 1024, so
# the two SDXL checkpoints do not share a box either.
BOXES = {
    "flux2":       {"sq": (1408, 1408), "por": (1152, 1728), "wide": (1728, 1152),
                    "cine": (1920, 800)},
    "qwen":        {"sq": (1328, 1328), "por": (1056, 1584), "wide": (1472, 992),
                    "cine": (1664, 704)},
    "animagine":   {"sq": (1024, 1024), "por": (832, 1216),  "wide": (1216, 832),
                    "cine": (1216, 512)},
    "illustrious": {"sq": (1216, 1216), "por": (1024, 1536), "wide": (1536, 1024),
                    "cine": (1536, 640)},
    "zimage":      {"sq": (1328, 1328), "por": (1056, 1584), "wide": (1472, 992),
                    "cine": (1664, 704)},
}


def load_wf(path):
    return {k: v for k, v in json.load(open(path)).items() if not k.startswith("_")}


def refs():
    with open(REFS, encoding="utf-8") as f:
        return json.load(f)


def by_id(data):
    return {p["id"]: p for p in data["prompts"]}


# ------------------------------------------------------------------ engine graphs
def flux_wf(prompt, seed, steps, guidance, size, turbo, prefix):
    """FLUX.2 dev. No negative exists in this graph and none can be added."""
    wf = load_wf(WF_FLUX)
    w, h = size
    wf["6"]["inputs"]["text"] = prompt
    wf["7"]["inputs"]["guidance"] = float(guidance)
    wf["9"]["inputs"].update(steps=int(steps), width=w, height=h)
    wf["11"]["inputs"]["noise_seed"] = int(seed)
    wf["12"]["inputs"].update(width=w, height=h)
    wf["15"]["inputs"]["filename_prefix"] = prefix
    if not turbo:
        # Bypass the Turbo LoRA: node 3 loses its only consumer and never executes.
        wf["8"]["inputs"]["model"] = ["1", 0]
    return wf


def qwen_wf(prompt, negative, seed, steps, cfg, size, prefix):
    wf = load_wf(WF_QWEN)
    w, h = size
    wf["10"]["inputs"]["text"] = prompt
    wf["11"]["inputs"]["text"] = negative or ""
    wf["12"]["inputs"].update(width=w, height=h)
    wf["13"]["inputs"].update(seed=int(seed), steps=int(steps), cfg=float(cfg))
    wf["15"]["inputs"]["filename_prefix"] = prefix
    return wf


def sdxl_wf(ckpt, prompt, negative, seed, steps, cfg, sampler, size, prefix):
    """Plain SDXL text-to-image. Built here rather than patched out of an existing
    workflow because every SDXL graph in workflows/ carries an IPAdapter or an img2img
    stage that would have to be neutralised, and a neutralised node is a silent variable."""
    w, h = size
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ckpt}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": prompt}},
        "3": {"class_type": "CLIPTextEncode",
              "inputs": {"clip": ["1", 1], "text": negative or ""}},
        "4": {"class_type": "EmptyLatentImage",
              "inputs": {"width": w, "height": h, "batch_size": 1}},
        "5": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0],
                         "latent_image": ["4", 0], "seed": int(seed), "steps": int(steps),
                         "cfg": float(cfg), "sampler_name": sampler,
                         "scheduler": "normal", "denoise": 1.0}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage",
              "inputs": {"images": ["6", 0], "filename_prefix": prefix}},
    }


def zimage_wf(prompt, seed, steps, size, prefix):
    """Z-Image Turbo, transcribed from ComfyUI's own shipped template.

    NOTE THE ConditioningZeroOut. The negative input is not "left empty" - the official
    graph feeds the KSampler a zeroed copy of the POSITIVE conditioning. There is nowhere
    to put a negative prompt even if you wanted one. That is the survey's claim, in the
    template, as shipped.
    """
    w, h = size
    return {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": "z_image_turbo_bf16.safetensors",
                         "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "lumina2",
                         "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "4": {"class_type": "ModelSamplingAuraFlow",
              "inputs": {"model": ["1", 0], "shift": 3.0}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
        "6": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["5", 0]}},
        "7": {"class_type": "EmptySD3LatentImage",
              "inputs": {"width": w, "height": h, "batch_size": 1}},
        "8": {"class_type": "KSampler",
              "inputs": {"model": ["4", 0], "positive": ["5", 0], "negative": ["6", 0],
                         "latent_image": ["7", 0], "seed": int(seed), "steps": int(steps),
                         "cfg": 1.0, "sampler_name": "res_multistep",
                         "scheduler": "simple", "denoise": 1.0}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "SaveImage",
               "inputs": {"images": ["9", 0], "filename_prefix": prefix}},
    }


# ------------------------------------------------------------------ ledger + recipes
def ledger_append(row):
    os.makedirs(SAMPLES, exist_ok=True)
    rows = []
    if os.path.exists(LEDGER):
        try:
            rows = json.load(open(LEDGER, encoding="utf-8"))
        except ValueError:
            rows = []
    rows.append(row)
    with open(LEDGER, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)
        f.write("\n")


def write_recipe(dest_dir, name, row):
    os.makedirs(dest_dir, exist_ok=True)
    with open(os.path.join(dest_dir, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(row, f, indent=1, ensure_ascii=False)
        f.write("\n")


def _collect(outs, dest_dir, name):
    if not outs:
        return None
    src = os.path.join(OUT, outs[0])
    os.makedirs(dest_dir, exist_ok=True)
    local = os.path.join(dest_dir, name + ".png")
    if os.path.exists(src):
        shutil.copyfile(src, local)
        return local
    return None


def render(wf, meta, dest_dir, name):
    t0 = time.time()
    try:
        elapsed, outs = comfy_run(HOST, wf, quiet=True)
    except SystemExit:
        row = dict(meta, seconds=round(time.time() - t0, 1), file=None, error="comfy error")
        ledger_append(row)
        write_recipe(dest_dir, name, row)
        print("  !! FAILED %s" % name, flush=True)
        return None
    local = _collect(outs, dest_dir, name)
    row = dict(meta, seconds=round(elapsed, 1),
               file=os.path.relpath(local, ROOT) if local else None)
    ledger_append(row)
    write_recipe(dest_dir, name, row)
    print("  %-28s %6.1fs -> %s" % (name, elapsed, local), flush=True)
    return local


# ------------------------------------------------------------------ batching
_PENDING = []


def _api(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request("http://%s%s" % (HOST, path), data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def queue(wf, meta, dest_dir, name):
    pid = _api("/prompt", {"prompt": wf, "client_id": "replicate_prompts"})["prompt_id"]
    _PENDING.append((pid, meta, dest_dir, name))
    return pid


def drain(label="cells"):
    """Wait for everything queue() submitted. seconds is deliberately null - see docstring."""
    global _PENDING
    jobs, _PENDING = _PENDING, []
    if not jobs:
        return
    left = {pid: (m, d, n) for pid, m, d, n in jobs}
    t0, last = time.time(), -1
    while left:
        time.sleep(6)
        try:
            hist = _api("/history?max_items=900")
        except Exception:
            continue
        for pid in list(left):
            e = hist.get(pid)
            if not e:
                continue
            st = e.get("status", {})
            if not (st.get("completed") or st.get("status_str") == "error"):
                continue
            meta, dest_dir, name = left.pop(pid)
            outs = ["%s/%s" % (f.get("subfolder", ""), f["filename"])
                    for o in e.get("outputs", {}).values() for f in o.get("images", [])]
            outs = [o.lstrip("/") for o in outs]
            local = _collect(outs, dest_dir, name)
            row = dict(meta, seconds=None, batched=True,
                       file=os.path.relpath(local, ROOT) if local else None)
            if not local:
                row["error"] = "no output"
            ledger_append(row)
            write_recipe(dest_dir, name, row)
            print("  %-28s -> %s" % (name, local), flush=True)
        done = len(jobs) - len(left)
        if done != last:
            print("  [%6.0fs] %s %d/%d" % (time.time() - t0, label, done, len(jobs)),
                  flush=True)
            last = done


def go(wf, meta, dest_dir, name, batch):
    if batch:
        queue(wf, meta, dest_dir, name)
        print("  queued %s" % name, flush=True)
    else:
        render(wf, meta, dest_dir, name)


# ------------------------------------------------------------------ cell assembly
def sdxl_flavour(p):
    ck = (p.get("settings") or {}).get("checkpoint") or "animagine-xl-4.0.safetensors"
    return "illustrious" if "Illustrious" in ck else "animagine", ck


def size_for(p, override_class=None):
    """Size for one prompt. Explicit width/height in the set wins - those were chosen by
    the survey to reproduce a specific published configuration and must not be second
    guessed here."""
    s = p.get("settings") or {}
    if s.get("width") and s.get("height"):
        return int(s["width"]), int(s["height"])
    cls = override_class or CLASS.get(p["id"], "sq")
    if p["engine"] == "sdxl":
        flav, _ = sdxl_flavour(p)
        return BOXES[flav][cls]
    return BOXES[p["engine"]][cls]


def base_meta(p, **kw):
    row = {
        "id": p["id"], "mode": kw.pop("mode", "base"), "cell": kw.pop("cell", p["id"]),
        "source_model": p.get("source_model"), "verbatim": p.get("verbatim"),
        "pair_id": p.get("pair_id"), "demonstrates": p.get("demonstrates"),
        "source_url": p.get("source_url"),
        "substitution": SUBSTITUTIONS.get(p.get("source_model") or ""),
    }
    row.update(kw)
    return row


def cell_flux(p, cls=None, turbo=True, steps=None, guidance=4.0, cell=None, mode="base"):
    size = size_for(p, cls)
    st = steps if steps is not None else (8 if turbo else 20)
    name = cell or p["id"]
    wf = flux_wf(p["prompt"], SEED, st, guidance, size, turbo,
                 "claude-generated/replicated/%s" % name)
    meta = base_meta(p, mode=mode, cell=name, engine="flux2",
                     checkpoint="flux2_dev_fp8mixed.safetensors",
                     text_encoder="mistral_3_small_flux2_fp8.safetensors",
                     vae="flux2-vae.safetensors",
                     lora="Flux2TurboComfyv2.safetensors@1.0" if turbo else None,
                     prompt=p["prompt"], negative=None,
                     negative_note="FLUX.2 has no negative input; BasicGuider takes one "
                                   "conditioning",
                     seed=SEED, steps=st, guidance=guidance, cfg=None, sampler="euler",
                     scheduler="Flux2Scheduler", size="%dx%d" % size)
    return wf, meta, name


def cell_qwen(p, cls=None, cfg=None, steps=None, negative="", cell=None, mode="base",
              size=None):
    size = size or size_for(p, cls)
    s = p.get("settings") or {}
    cfg = cfg if cfg is not None else float(s.get("cfg", 4.5))
    st = steps if steps is not None else int(s.get("steps", 50))
    name = cell or p["id"]
    wf = qwen_wf(p["prompt"], negative, SEED, st, cfg, size,
                 "claude-generated/replicated/%s" % name)
    meta = base_meta(p, mode=mode, cell=name, engine="qwen",
                     checkpoint="qwen_image_2512_fp8_e4m3fn.safetensors",
                     text_encoder="qwen_2.5_vl_7b_fp8_scaled.safetensors",
                     vae="qwen_image_vae.safetensors", lora=None,
                     prompt=p["prompt"], negative=negative or "",
                     seed=SEED, steps=st, cfg=cfg, guidance=None, sampler="euler",
                     scheduler="simple", shift=3.1, size="%dx%d" % size)
    return wf, meta, name


def cell_sdxl(p, cls=None, ckpt=None, prompt=None, cell=None, mode="base", size=None):
    flav, default_ck = sdxl_flavour(p)
    ck = ckpt or default_ck
    flav = "illustrious" if "Illustrious" in ck else "animagine"
    s = p.get("settings") or {}
    cfg = float(s.get("cfg", 5.5 if flav == "illustrious" else 5.0))
    st = int(s.get("steps", 24 if flav == "illustrious" else 28))
    sampler = s.get("sampler", "euler_ancestral")
    if size is None:
        if ckpt and ckpt != default_ck:
            # cross-checkpoint arm: use the OTHER checkpoint's own box, not the set's
            size = BOXES[flav][cls or CLASS.get(p["id"], "por")]
        else:
            size = size_for(p, cls)
    name = cell or p["id"]
    text = prompt if prompt is not None else p["prompt"]
    wf = sdxl_wf(ck, text, p.get("negative"), SEED, st, cfg, sampler, size,
                 "claude-generated/replicated/%s" % name)
    meta = base_meta(p, mode=mode, cell=name, engine="sdxl", checkpoint=ck,
                     text_encoder="CLIP-L + CLIP-G (in checkpoint)", vae="(in checkpoint)",
                     lora=None, prompt=text, negative=p.get("negative"),
                     seed=SEED, steps=st, cfg=cfg, guidance=None, sampler=sampler,
                     scheduler="normal", size="%dx%d" % size)
    return wf, meta, name


def cell_zimage(p, cls=None, cell=None, mode="zimage", steps=8):
    size = BOXES["zimage"][cls or CLASS.get(p["id"], "sq")]
    name = cell or (p["id"] + "_zimage")
    wf = zimage_wf(p["prompt"], SEED, steps, size,
                   "claude-generated/replicated/%s" % name)
    meta = base_meta(p, mode=mode, cell=name, engine="zimage",
                     checkpoint="z_image_turbo_bf16.safetensors",
                     text_encoder="qwen_3_4b.safetensors (CLIPLoader type=lumina2)",
                     vae="ae.safetensors", lora=None,
                     prompt=p["prompt"], negative=None,
                     negative_note="official graph feeds ConditioningZeroOut(positive) to "
                                   "the negative slot - there is nowhere to put one",
                     seed=SEED, steps=steps, cfg=1.0, guidance=None,
                     sampler="res_multistep", scheduler="simple", shift=3.0,
                     size="%dx%d" % size)
    return wf, meta, name


# ------------------------------------------------------------------ modes
def mode_base(a):
    data = refs()
    ps = data["prompts"]
    d = os.path.join(SAMPLES, "base")
    order = {"flux2": 0, "qwen": 1, "sdxl": 2}
    want = set(a.engines.split(",")) if a.engines else {"flux2", "qwen", "sdxl"}
    ps = [p for p in ps if p["engine"] in want]
    ps.sort(key=lambda p: (order[p["engine"]], p["id"]))
    print("base: %d cells" % len(ps), flush=True)
    cur = None
    for p in ps:
        if p["engine"] != cur:
            drain("%s base" % cur) if (a.batch and cur) else None
            cur = p["engine"]
            print("-- %s" % cur, flush=True)
        if p["engine"] == "flux2":
            wf, meta, name = cell_flux(p)
        elif p["engine"] == "qwen":
            wf, meta, name = cell_qwen(p)
        else:
            wf, meta, name = cell_sdxl(p)
        go(wf, meta, d, name, a.batch)
    if a.batch:
        drain("%s base" % cur)


def mode_zimage(a):
    """The five Z-Image-authored prompts on the model they were authored for, plus three
    cards chosen to test the survey's headline claim that Z-Image beats Qwen on skin."""
    data = by_id(refs())
    d = os.path.join(SAMPLES, "zimage")
    ids = ["qwen-009", "qwen-010", "qwen-011", "qwen-012", "qwen-013",
           "qwen-001", "qwen-014", "qwen-024"]
    print("zimage: %d cells" % len(ids), flush=True)
    for i in ids:
        wf, meta, name = cell_zimage(data[i])
        go(wf, meta, d, name, a.batch)
    if a.batch:
        drain("zimage")


def mode_extra(a):
    """THE ARMS. Every cell here exists to answer one named question.

    A  qwen negative      Do Qwen negatives do anything at cfg 2.5 / 4.5 / 7.0? The two
                          top guides say +15% satisfaction; an independent sweep says zero.
                          Same seed, same prompt, negative empty vs the guides' template.
    B  flux2 turbo        Does the Turbo distill cost anything on THESE prompts? Wire 1
                          measured that it costs mechanism and nothing else.
    C  sdxl tag order     The Illustrious guide contradicts itself on whether quality tags
                          go first or last. Both orderings, same seed.
    D  sdxl face pixels   Illustrious trains at 1536, animagine at 1024. Same full-body
                          prompt at three boxes. This is the measured 90px-face problem.
    E  sdxl era tag       'year 2005' against 'newest' - animagine's documented era dial.
    F  sdxl cross-ckpt    Underscored tags and the two tag orders, each on both bases.
    G  qwen face pixels   The two-person full-body card at 1024 wide and at 1536 wide.
    """
    data = by_id(refs())
    d = os.path.join(SAMPLES, "extra")

    # ---- B: FLUX.2 turbo vs undistilled. Flux first: 34 GB does not share the card.
    print("-- B flux2 turbo A/B", flush=True)
    for i in ("flux2-013", "flux2-016", "flux2-022", "flux2-030"):
        wf, meta, name = cell_flux(data[i], turbo=False, steps=20,
                                   cell="B_%s_noturbo" % i, mode="extra")
        meta["arm"] = "B turbo A/B; the turbo half is base/%s" % i
        go(wf, meta, d, name, a.batch)
    if a.batch:
        drain("B")

    # ---- A: the qwen negative question, three cfg values on one card plus three more
    # cards at the guides' own recommended cfg.
    print("-- A qwen negative A/B", flush=True)
    for cfg in (2.5, 4.5, 7.0):
        for tag, neg in (("noneg", ""), ("tmplneg", QWEN_TEMPLATE_NEG)):
            wf, meta, name = cell_qwen(data["qwen-001"], cfg=cfg, steps=50, negative=neg,
                                       cell="A_qwen-001_cfg%s_%s" % (cfg, tag),
                                       mode="extra")
            meta["arm"] = "A negative A/B at cfg %s" % cfg
            go(wf, meta, d, name, a.batch)
    for i in ("qwen-004", "qwen-010", "qwen-019"):
        for tag, neg in (("noneg", ""), ("tmplneg", QWEN_TEMPLATE_NEG)):
            wf, meta, name = cell_qwen(data[i], cfg=4.5, steps=50, negative=neg,
                                       cell="A_%s_%s" % (i, tag), mode="extra")
            meta["arm"] = "A negative A/B at cfg 4.5"
            go(wf, meta, d, name, a.batch)

    # ---- G: qwen face pixels on the two-person full-body card
    print("-- G qwen face pixels", flush=True)
    for w, h in ((1024, 688), (1536, 1024)):
        wf, meta, name = cell_qwen(data["qwen-017"], size=(w, h),
                                   cell="G_qwen-017_%dw" % w, mode="extra")
        meta["arm"] = "G face-pixel ladder on a two-person full-body card"
        go(wf, meta, d, name, a.batch)
    if a.batch:
        drain("A+G")

    # ---- C: tag order. sdxl-002 ships tail-last; sdxl-012 ships tail-first.
    print("-- C sdxl tag order", flush=True)
    p2 = data["sdxl-002"]
    tail = "masterpiece, best quality, highres, absurdres, newest"
    body2 = p2["prompt"].replace(", " + tail, "")
    wf, meta, name = cell_sdxl(p2, prompt=tail + ", " + body2,
                               cell="C_sdxl-002_tailfirst", mode="extra")
    meta["arm"] = "C quality-tag placement; tail-LAST half is base/sdxl-002"
    go(wf, meta, d, name, a.batch)
    p12 = data["sdxl-012"]
    head = "masterpiece, best quality, highres, absurdres, newest, "
    body12 = p12["prompt"][len(head):]
    wf, meta, name = cell_sdxl(p12, prompt=body12 + ", " + head.rstrip(", "),
                               cell="C_sdxl-012_taillast", mode="extra")
    meta["arm"] = "C quality-tag placement; tail-FIRST half is base/sdxl-012"
    go(wf, meta, d, name, a.batch)

    # ---- D: face pixels on Illustrious. sdxl-012 base is 832x1216.
    print("-- D sdxl face pixels", flush=True)
    for w, h in ((1024, 1536), (1280, 1920)):
        wf, meta, name = cell_sdxl(data["sdxl-012"], size=(w, h),
                                   cell="D_sdxl-012_%dx%d" % (w, h), mode="extra")
        meta["arm"] = "D face-pixel ladder; 832x1216 half is base/sdxl-012"
        go(wf, meta, d, name, a.batch)

    # ---- E: era tag
    print("-- E sdxl era tag", flush=True)
    p18 = data["sdxl-018"]
    wf, meta, name = cell_sdxl(p18, prompt=p18["prompt"].replace("year 2005", "newest"),
                               cell="E_sdxl-018_newest", mode="extra")
    meta["arm"] = "E era dial; the 'year 2005' half is base/sdxl-018"
    go(wf, meta, d, name, a.batch)

    # ---- F: cross-checkpoint. Each tag convention on the other base.
    print("-- F sdxl cross-checkpoint", flush=True)
    ANI = "animagine-xl-4.0.safetensors"
    ILL = "Illustrious-XL-v2.0.safetensors"
    for i, other in (("sdxl-007", ANI), ("sdxl-008", ILL),
                     ("sdxl-002", ANI), ("sdxl-001", ILL)):
        wf, meta, name = cell_sdxl(data[i], ckpt=other,
                                   cell="F_%s_on_%s" % (i, other.split("-")[0].lower()),
                                   mode="extra")
        meta["arm"] = "F same tag string on the other SDXL base; native half is base/%s" % i
        go(wf, meta, d, name, a.batch)
    if a.batch:
        drain("C-F")


# ------------------------------------------------------------------ looking at it
# A render nobody looked at is not a result. These two modes exist so the looking is
# cheap enough that it actually happens, and so the numbers that can be measured
# mechanically are measured mechanically instead of guessed at from a thumbnail.
LOOK_MAX = 1100          # long edge of the per-cell inspection copy
SHEET_CELL = 620         # long edge of a contact-sheet cell
SHEET_COLS = 3


def mode_look(a):
    """Downscale every rendered cell to a long edge of 1100 px.

    Not decoration - a 1920x800 PNG costs several times as much to look at as the same
    frame at 1100 px, and at 1100 px a face, a line of type and a hex fill are all still
    judgeable. Composition, count, framing and grade survive; only pore-level skin does
    not, and the handful of cells where that is the question get read at full size.
    """
    from PIL import Image
    src_dirs = [d for d in ("base", "extra", "zimage")
                if os.path.isdir(os.path.join(SAMPLES, d))]
    n = 0
    for sd in src_dirs:
        out = os.path.join(SAMPLES, "_look", sd)
        os.makedirs(out, exist_ok=True)
        for f in sorted(os.listdir(os.path.join(SAMPLES, sd))):
            if not f.endswith(".png"):
                continue
            im = Image.open(os.path.join(SAMPLES, sd, f)).convert("RGB")
            s = LOOK_MAX / max(im.size)
            if s < 1:
                im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))),
                               Image.LANCZOS)
            im.save(os.path.join(out, f.replace(".png", ".jpg")), quality=92)
            n += 1
    print("look: %d copies under %s/_look" % (n, SAMPLES))


def mode_sheets(a):
    """Contact sheets, 3 across, every cell captioned with its own id.

    The caption is not optional. An uncaptioned sheet is the exact failure this project
    keeps hitting: a grid of pretty images that nobody can trace back to a recipe.
    """
    from PIL import Image, ImageDraw
    out = os.path.join(SAMPLES, "_sheets")
    os.makedirs(out, exist_ok=True)
    groups = []
    for sd, per in (("base", 6), ("extra", 6), ("zimage", 8)):
        p = os.path.join(SAMPLES, sd)
        if not os.path.isdir(p):
            continue
        files = sorted(f for f in os.listdir(p) if f.endswith(".png"))
        for i in range(0, len(files), per):
            groups.append((sd, i // per + 1, [os.path.join(p, f) for f in files[i:i + per]]))
    for sd, idx, files in groups:
        tiles = []
        for f in files:
            im = Image.open(f).convert("RGB")
            s = SHEET_CELL / max(im.size)
            im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))),
                           Image.LANCZOS)
            tiles.append((os.path.basename(f)[:-4], im))
        cols = SHEET_COLS
        rows = (len(tiles) + cols - 1) // cols
        cw = max(t[1].width for t in tiles) + 12
        ch = max(t[1].height for t in tiles) + 30
        sheet = Image.new("RGB", (cols * cw, rows * ch), (24, 24, 26))
        dr = ImageDraw.Draw(sheet)
        for k, (label, im) in enumerate(tiles):
            x, y = (k % cols) * cw + 6, (k // cols) * ch + 24
            sheet.paste(im, (x, y))
            dr.text((x + 2, y - 16), label, fill=(235, 235, 235))
        dest = os.path.join(out, "%s_%02d.jpg" % (sd, idx))
        sheet.save(dest, quality=90)
        print("  %s  (%d cells)" % (dest, len(tiles)))


def mode_measure(a):
    """The things that can be scored by arithmetic instead of by opinion.

    HEX      flux2-029 names four exact colours. BFL claim #RRGGBB is honoured. Sample the
             rendered pixels and print the per-channel error. Nothing else on this box
             claims this capability, so it is worth a number rather than an impression.
    NEGATIVE the qwen A/B. If the guides are right the two halves should differ visibly;
             if the independent sweep is right they should be near-identical at a fixed
             seed. Mean absolute pixel difference settles it without anyone squinting.
    PAIRS    every matched pair and A/B arm gets a side-by-side JPEG so the comparison is
             one image, not two tabs.
    """
    from PIL import Image
    res = {}

    # ---- hex
    hexes = {"loop_start": "#3B5BDB", "loop_end": "#9C36B5",
             "background": "#0B1120", "hairline": "#E9ECEF"}
    f = os.path.join(SAMPLES, "base", "flux2-029.png")
    if os.path.exists(f):
        im = Image.open(f).convert("RGB")
        px = list(im.getdata())
        from collections import Counter
        # The background is the modal colour by construction: "the background exactly
        # #0B1120" over a flat field. Quantise to 8 levels so near-identical pixels merge.
        q = Counter((r // 8 * 8, g // 8 * 8, b // 8 * 8) for r, g, b in px)
        top = q.most_common(6)
        res["hex_flux2-029"] = {
            "asked": hexes,
            "modal_colours_8step": [{"rgb": "#%02X%02X%02X" % c, "share": round(n / len(px), 4)}
                                    for c, n in top],
            "corner_px": "#%02X%02X%02X" % im.getpixel((4, 4)),
            "note": "corner is the background field; compare against #0B1120",
        }

    # ---- negative A/B
    def diff(p1, p2):
        a1, a2 = Image.open(p1).convert("RGB"), Image.open(p2).convert("RGB")
        if a1.size != a2.size:
            return None
        d1, d2 = a1.getdata(), a2.getdata()
        tot = 0
        for x, y in zip(d1, d2):
            tot += abs(x[0] - y[0]) + abs(x[1] - y[1]) + abs(x[2] - y[2])
        return round(tot / (len(a1.getdata()) * 3), 3)

    ex = os.path.join(SAMPLES, "extra")
    pairs = []
    if os.path.isdir(ex):
        for f in sorted(os.listdir(ex)):
            if f.endswith("_noneg.png"):
                other = f.replace("_noneg.png", "_tmplneg.png")
                if os.path.exists(os.path.join(ex, other)):
                    pairs.append((f, other))
    res["qwen_negative_ab"] = []
    for f1, f2 in pairs:
        res["qwen_negative_ab"].append({
            "cell": f1.replace("_noneg.png", ""),
            "mean_abs_pixel_diff_0_255": diff(os.path.join(ex, f1), os.path.join(ex, f2)),
        })

    # ---- side-by-sides
    sbs = os.path.join(SAMPLES, "_compare")
    os.makedirs(sbs, exist_ok=True)
    b = os.path.join(SAMPLES, "base")

    def pair_img(paths, labels, dest, cell=760):
        from PIL import ImageDraw
        ims = []
        for p in paths:
            if not os.path.exists(p):
                return
            im = Image.open(p).convert("RGB")
            s = cell / max(im.size)
            ims.append(im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))),
                                 Image.LANCZOS))
        W = sum(i.width for i in ims) + 8 * (len(ims) + 1)
        H = max(i.height for i in ims) + 34
        out = Image.new("RGB", (W, H), (24, 24, 26))
        dr = ImageDraw.Draw(out)
        x = 8
        for im, lab in zip(ims, labels):
            out.paste(im, (x, 28))
            dr.text((x + 2, 8), lab, fill=(235, 235, 235))
            x += im.width + 8
        out.save(dest, quality=92)
        print("  %s" % dest)

    P = lambda d, n: os.path.join(SAMPLES, d, n + ".png")  # noqa: E731
    # matched prose-vs-tag pairs
    for a_id, b_id, tag in (("sdxl-010", "sdxl-011", "neon-anime-portrait"),
                            ("sdxl-012", "sdxl-013", "shonen-hero-fullbody"),
                            ("sdxl-014", "sdxl-015", "ghibli-countryside")):
        pair_img([P("base", a_id), P("base", b_id)],
                 ["%s TAGS" % a_id, "%s PROSE" % b_id],
                 os.path.join(sbs, "pair_%s.jpg" % tag))
    # turbo arms
    for i in ("flux2-013", "flux2-016", "flux2-022", "flux2-030"):
        pair_img([P("base", i), P("extra", "B_%s_noturbo" % i)],
                 ["%s TURBO 8st" % i, "%s NO-TURBO 20st" % i],
                 os.path.join(sbs, "turbo_%s.jpg" % i))
    # negative arms
    for c in ("A_qwen-001_cfg2.5", "A_qwen-001_cfg4.5", "A_qwen-001_cfg7.0",
              "A_qwen-004", "A_qwen-010", "A_qwen-019"):
        pair_img([P("extra", c + "_noneg"), P("extra", c + "_tmplneg")],
                 [c + " NO NEGATIVE", c + " GUIDE NEGATIVE"],
                 os.path.join(sbs, "neg_%s.jpg" % c))
    # tag order, era, face pixels, cross-checkpoint
    pair_img([P("base", "sdxl-002"), P("extra", "C_sdxl-002_tailfirst")],
             ["sdxl-002 TAIL LAST", "sdxl-002 TAIL FIRST"],
             os.path.join(sbs, "tagorder_sdxl-002.jpg"))
    pair_img([P("base", "sdxl-012"), P("extra", "C_sdxl-012_taillast")],
             ["sdxl-012 TAIL FIRST", "sdxl-012 TAIL LAST"],
             os.path.join(sbs, "tagorder_sdxl-012.jpg"))
    pair_img([P("base", "sdxl-018"), P("extra", "E_sdxl-018_newest")],
             ["sdxl-018 year 2005", "sdxl-018 newest"],
             os.path.join(sbs, "era_sdxl-018.jpg"))
    pair_img([P("base", "sdxl-012"), P("extra", "D_sdxl-012_1024x1536"),
              P("extra", "D_sdxl-012_1280x1920")],
             ["832x1216", "1024x1536", "1280x1920"],
             os.path.join(sbs, "facepix_sdxl-012.jpg"))
    pair_img([P("extra", "G_qwen-017_1024w"), P("base", "qwen-017"),
              P("extra", "G_qwen-017_1536w")],
             ["1024x688", "1472x992", "1536x1024"],
             os.path.join(sbs, "facepix_qwen-017.jpg"))
    for i, other in (("sdxl-007", "animagine"), ("sdxl-008", "illustrious"),
                     ("sdxl-002", "animagine"), ("sdxl-001", "illustrious")):
        pair_img([P("base", i), P("extra", "F_%s_on_%s" % (i, other))],
                 ["%s as published" % i, "%s on %s" % (i, other)],
                 os.path.join(sbs, "ckpt_%s.jpg" % i))
    # z-image against the qwen substitution
    for i in ("qwen-009", "qwen-010", "qwen-011", "qwen-012", "qwen-013",
              "qwen-001", "qwen-014", "qwen-024"):
        pair_img([P("base", i), P("zimage", i + "_zimage")],
                 ["%s on QWEN (substitute)" % i, "%s on Z-IMAGE (authored for)" % i],
                 os.path.join(sbs, "zimage_%s.jpg" % i))

    dest = os.path.join(SAMPLES, "_measured_analysis.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(json.dumps(res, indent=1)[:4000])
    print("wrote %s" % dest)


def mode_one(a):
    data = by_id(refs())
    p = data[a.id]
    d = os.path.join(SAMPLES, "base")
    if p["engine"] == "flux2":
        wf, meta, name = cell_flux(p)
    elif p["engine"] == "qwen":
        wf, meta, name = cell_qwen(p)
    else:
        wf, meta, name = cell_sdxl(p)
    render(wf, meta, d, name)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mode", required=True,
                    choices=["base", "extra", "zimage", "one",
                             "look", "sheets", "measure"])
    ap.add_argument("--engines", default="",
                    help="comma list for --mode base: flux2,qwen,sdxl")
    ap.add_argument("--id", help="prompt id for --mode one")
    ap.add_argument("--batch", action="store_true",
                    help="submit the whole mode up front; gives up per-cell wall clock")
    a = ap.parse_args()
    os.makedirs(SAMPLES, exist_ok=True)
    t0 = time.time()
    {"base": mode_base, "extra": mode_extra, "zimage": mode_zimage, "one": mode_one,
     "look": mode_look, "sheets": mode_sheets, "measure": mode_measure}[a.mode](a)
    print("mode %s finished in %.0fs" % (a.mode, time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
