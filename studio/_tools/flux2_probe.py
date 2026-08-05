#!/usr/bin/env python3
"""Turn FLUX.2 dev from 34 GB of unused disk into a measured, routable studio engine.

WHY THIS EXISTS. flux2_dev_fp8mixed.safetensors, its flux2-vae, its Mistral-3-Small text
encoder and a Turbo distill LoRA have been on this box since July and the app cannot reach
any of them. One image had ever been rendered on it. Before compose.py can route an engine
we need the numbers: does it fit in 32 GB, what does it cost, what settings, and on which
jobs does it actually beat Qwen-Image. This tool produces those numbers and the pixels
behind them.

WHAT IT KNOWS THAT YOU MIGHT NOT.

  THERE IS NO NEGATIVE PROMPT. FLUX.2 runs through BasicGuider, which takes one
  conditioning. Not "the negative is ignored" like Qwen at cfg 1.0 - there is nowhere to
  put one. Negation has to be written as a positive fact: "a plain white wall behind her".

  THE DIALECT IS MISTRAL, NOT CLIP. Complete natural sentences. Danbooru tags degrade it.
  This is the fourth dialect on this box, after CLIP/SDXL, Qwen2.5-VL and Qwen3-4B.

  TURBO IS A SEPARATE PATH, NOT A SETTING. --no-turbo rewires BasicGuider straight to the
  UNETLoader so the LoRA node has no consumer and never executes, and raises the step
  count. It is a different graph, not a strength of 0.

  Flux2Scheduler AND EmptyFlux2LatentImage MUST AGREE ON SIZE. The scheduler computes a
  resolution-dependent sigma schedule. Mismatch degrades the image silently, no error.
  --size sets both from one flag; do not patch them separately.

  RENDER ALL FLUX WORK BEFORE ANY QWEN WORK. 34 GB of DiT plus a 16.8 GB encoder does not
  co-reside with Qwen-Image on 32 GB. --mode ab therefore renders every FLUX cell first and
  every Qwen cell second, deliberately, and it is not an accident of loop order.

MODES
  settings   step/guidance/turbo sweep on one prompt and one seed. The timing table.
  spread     a spread of subjects chosen to expose where the model is strong and weak.
  ab         matched prompts and seeds, FLUX.2 against Qwen-Image 2512. The verdict.
  size       resolution ladder, wall clock per size. Where it stops being affordable.
  one        a single ad-hoc prompt, for when you just want a picture.

    python3 studio/_tools/flux2_probe.py --mode settings
    python3 studio/_tools/flux2_probe.py --mode ab --seed 5150
    python3 studio/_tools/flux2_probe.py --mode one --prompt "..." --size 1216x832

--batch EXISTS BECAUSE THIS BOX IS SHARED, AND IT WAS ADDED MID-RUN FOR A REASON. The
default is one-at-a-time, which is what you want for timing: each render is submitted,
waited on and clocked alone. But another agent's HunyuanVideo job landed in the queue at
13 minutes per clip with five more behind it, and one-at-a-time means every one of our
cells goes to the BACK of that queue - four cells became four hours. --batch submits every
cell of the mode up front so they stay contiguous, costs one model load instead of N, and
gives up per-cell wall clock (the ledger records seconds: null). Use it whenever the box
is busy and you care about pixels rather than timings.

    python3 studio/_tools/flux2_probe.py --mode ab --engines qwen --batch

Every render appends a row to studio/samples/flux2/_measured.json - prompt, seed, steps,
guidance, turbo, size, wall clock, output path. Nothing is measured that is not written
down, and nothing is claimed here that was not measured.
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
SAMPLES = os.path.join(ROOT, "studio", "samples", "flux2")
LEDGER = os.path.join(SAMPLES, "_measured.json")

sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run as comfy_run, set_path  # noqa: E402

HOST = os.environ["COMFY_HOST"]
WF_FLUX = os.path.join(ROOT, "workflows", "40_flux2_t2i.json")
WF_QWEN = os.path.join(ROOT, "workflows", "02_qwen_t2i_quality.json")

# Qwen's own template negative, kept for the A/B so Qwen is shown at its best rather than
# handicapped. FLUX.2 has no equivalent field and that asymmetry is the point.
QWEN_NEG = "blurry, low quality, watermark, deformed text, misspelled, jpeg artifacts"


def load(path):
    return {k: v for k, v in json.load(open(path)).items() if not k.startswith("_")}


def parse_size(s):
    w, _, h = s.lower().partition("x")
    return int(w), int(h)


def flux_wf(prompt, seed, steps, guidance, size, turbo, prefix):
    wf = load(WF_FLUX)
    w, h = size
    wf["6"]["inputs"]["text"] = prompt
    wf["7"]["inputs"]["guidance"] = float(guidance)
    wf["9"]["inputs"].update(steps=int(steps), width=w, height=h)
    wf["11"]["inputs"]["noise_seed"] = int(seed)
    wf["12"]["inputs"].update(width=w, height=h)
    wf["15"]["inputs"]["filename_prefix"] = prefix
    if not turbo:
        # Bypass the Turbo LoRA entirely: node 3 loses its only consumer, so ComfyUI
        # never executes it and never loads the LoRA.
        wf["8"]["inputs"]["model"] = ["1", 0]
    return wf


def qwen_wf(prompt, seed, steps, cfg, size, prefix):
    wf = load(WF_QWEN)
    w, h = size
    wf["10"]["inputs"]["text"] = prompt
    wf["11"]["inputs"]["text"] = QWEN_NEG
    wf["12"]["inputs"].update(width=w, height=h)
    wf["13"]["inputs"].update(seed=int(seed), steps=int(steps), cfg=float(cfg))
    wf["15"]["inputs"]["filename_prefix"] = prefix
    return wf


def ledger_append(row):
    os.makedirs(SAMPLES, exist_ok=True)
    rows = []
    if os.path.exists(LEDGER):
        try:
            rows = json.load(open(LEDGER))
        except ValueError:
            rows = []
    rows.append(row)
    with open(LEDGER, "w") as f:
        json.dump(rows, f, indent=1)
        f.write("\n")


def render(wf, meta, dest_dir, dest_name):
    """Run one workflow, time it, copy the PNG next to the ledger, record the row."""
    t0 = time.time()
    try:
        elapsed, outs = comfy_run(HOST, wf)
    except SystemExit:
        row = dict(meta, seconds=round(time.time() - t0, 1), file=None, error="comfy error")
        ledger_append(row)
        print(f"  !! FAILED {dest_name}", flush=True)
        return None
    local = None
    if outs:
        src = os.path.join(OUT, outs[0])
        os.makedirs(dest_dir, exist_ok=True)
        local = os.path.join(dest_dir, dest_name + ".png")
        if os.path.exists(src):
            shutil.copyfile(src, local)
    row = dict(meta, seconds=round(elapsed, 1),
               file=os.path.relpath(local, ROOT) if local else None)
    ledger_append(row)
    print(f"  {dest_name}: {elapsed:.1f}s -> {local}", flush=True)
    return local


# --------------------------------------------------------------------------- batching
_PENDING = []


def _api(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"http://{HOST}{path}", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def queue(wf, meta, dest_dir, dest_name):
    """Submit now, collect later. Pairs with drain()."""
    pid = _api("/prompt", {"prompt": wf, "client_id": "flux2_probe"})["prompt_id"]
    _PENDING.append((pid, meta, dest_dir, dest_name))
    print(f"  queued {dest_name} as {pid}", flush=True)
    return pid


def drain(label="cells"):
    """Wait for everything queue() submitted, then copy and record it.

    Deliberately does NOT report per-cell wall clock. The whole point of batching is that
    the cells are contiguous and share one model load, so a per-cell number would be the
    load amortised across the batch rather than the cost of one render - a misleading
    figure, and this project has a rule about not writing down numbers you did not
    measure. seconds comes out null and the batch total is printed instead.
    """
    global _PENDING
    jobs, _PENDING = _PENDING, []
    left = {pid: (meta, d, n) for pid, meta, d, n in jobs}
    t0, last = time.time(), -1
    while left:
        time.sleep(6)
        try:
            hist = _api("/history?max_items=600")
        except Exception:
            continue
        for pid in list(left):
            e = hist.get(pid)
            if not e:
                continue
            st = e.get("status", {})
            if not (st.get("completed") or st.get("status_str") == "error"):
                continue
            meta, dest_dir, dest_name = left.pop(pid)
            outs = [f"{f.get('subfolder','')}/{f['filename']}".lstrip("/")
                    for o in e.get("outputs", {}).values() for f in o.get("images", [])]
            local = None
            if outs:
                src = os.path.join(OUT, outs[0])
                os.makedirs(dest_dir, exist_ok=True)
                local = os.path.join(dest_dir, dest_name + ".png")
                if os.path.exists(src):
                    shutil.copyfile(src, local)
            ledger_append(dict(meta, seconds=None, batched=True,
                               file=os.path.relpath(local, ROOT) if local else None))
            print(f"  {dest_name} -> {local}", flush=True)
        done = len(jobs) - len(left)
        if done != last:
            print(f"  [{time.time()-t0:6.0f}s] {label} {done}/{len(jobs)}", flush=True)
            last = done


# --------------------------------------------------------------------------- settings
# One prompt, one seed, everything else swept. The prompt is deliberately full of small
# checkable physical facts so a drop in step count shows up as detail loss rather than as
# a different picture.
SWEEP_PROMPT = (
    "A close-up photograph of a watchmaker's bench, taken from slightly above. An open "
    "pocket watch lies face up with its movement exposed, brass wheels and a blued steel "
    "spring visible. Beside it are three tiny screwdrivers laid in a row, a loupe on its "
    "side, and a saucer of screws. The bench top is scarred oak with old ink stains. Light "
    "comes from a window to the left, raking across the surface. Natural colour, shot on "
    "medium format at f5.6, fine grain, no vignette."
)


def mode_settings(a):
    d = os.path.join(SAMPLES, "settings")
    cells = []
    # Turbo step ladder at the template guidance.
    for st in (4, 6, 8, 10, 12):
        cells.append((f"turbo_s{st:02d}_g4.0", True, st, 4.0))
    # Guidance sweep at the working step count.
    for g in (2.0, 2.5, 6.0, 8.0):
        cells.append((f"turbo_s08_g{g}", True, 8, g))
    # The undistilled path. Slow; this is the whole question of whether Turbo costs quality.
    for st in (20, 28):
        cells.append((f"noturbo_s{st:02d}_g4.0", False, st, 4.0))
    for g in (2.5, 6.0):
        cells.append((f"noturbo_s20_g{g}", False, 20, g))

    print(f"settings sweep: {len(cells)} cells at {a.size}", flush=True)
    for name, turbo, st, g in cells:
        wf = flux_wf(SWEEP_PROMPT, a.seed, st, g, parse_size(a.size), turbo,
                     "claude-generated/40-flux2/settings")
        render(wf, dict(mode="settings", cell=name, engine="flux2", turbo=turbo,
                        steps=st, guidance=g, size=a.size, seed=a.seed,
                        prompt=SWEEP_PROMPT), d, name)


# ----------------------------------------------------------------------------- spread
# Chosen to hit the things this studio has measured problems with, plus the things FLUX.2
# is claimed to win. Every one is a job someone here has actually needed.
SPREAD = [
    ("face_closeup", "1024x1024",
     "A close portrait of a woman in her late thirties, head and shoulders filling the "
     "frame, looking just past the camera. Her skin has real texture - open pores across "
     "the nose, a faint scar through one eyebrow, fine lines at the corners of the eyes. "
     "Dark curly hair pulled back, a few strands loose. Soft north light from a window "
     "camera-left, a catch light in each eye, deep falloff on the shadow side. Plain warm "
     "grey wall behind her. 85mm at f2, natural colour, fine grain."),

    ("face_fullbody", "832x1216",
     "A full-length photograph of a woman in her late thirties standing in a bare studio, "
     "her whole body in frame from shoes to the top of her head. She wears a charcoal wool "
     "coat over a cream shirt and dark trousers, hands in her pockets, weight on one hip. "
     "Dark curly hair pulled back. Soft north light from camera-left, plain warm grey "
     "seamless behind her. 50mm at f4, natural colour, fine grain."),

    ("hands", "1024x1024",
     "A photograph of two hands tying a fishing fly in a small vice, seen from directly "
     "above. Ten fingers total across both hands, each finger distinct and correctly "
     "jointed. The left hand holds a spool of red thread, the right hand pinches a pinch "
     "of grey hackle against the hook shank. Short clean nails, one knuckle scraped. Bright "
     "diffuse daylight, a scarred wooden bench beneath. Macro lens at f8, natural colour."),

    ("text_sign", "1216x832",
     "A photograph of a hand-painted enamel shop sign mounted above a doorway. The sign is "
     "deep green with cream serif lettering that reads exactly NORTHWIND SUPPLY CO. and "
     "below it in smaller capitals EST 1904. The paint is chipped at the corners and the "
     "brass mounting rivets have gone green. Rain-wet brick wall behind, warm light from a "
     "window off frame right. 85mm at f2.8, natural colour."),

    ("text_paperwork", "1024x1024",
     "A photograph of a handwritten index card pinned to a cork board, shot straight on. "
     "The card reads, in block capitals in blue ballpoint, TUESDAY: FEED THE CHICKENS. "
     "Below it a second card in the same hand reads BUY NAILS. The cork is scuffed and "
     "there are old pin holes around them. Flat overcast daylight from a window. 50mm at "
     "f4, natural colour, fine grain."),

    ("multi_subject", "1216x832",
     "A photograph of three people in a workshop, evenly spaced across the frame. On the "
     "left, an old man in a brown leather apron files a piece of metal held in a vice. In "
     "the centre, a young woman in a red boilersuit holds a clipboard and looks toward him. "
     "On the right, a teenage boy in a blue hoodie sweeps the floor with a broom, his back "
     "half turned. Afternoon sun through a high dusty window falls across the middle of the "
     "room. 35mm at f4, natural colour."),

    ("complex_scene", "1216x832",
     "A photograph of a crowded fishmonger's stall at a covered market in the morning. "
     "Crushed ice banked up with whole fish laid in rows, price cards stuck into the ice, "
     "a set of brass scales at the left end of the counter, a stack of newspaper beneath. "
     "The fishmonger stands behind in a striped apron with wet hands. Cold fluorescent "
     "light overhead mixed with daylight from the market entrance behind. 35mm at f4."),

    ("illustration", "1024x1024",
     "A watercolour illustration on cold-pressed paper of a fox asleep curled in a bed of "
     "autumn leaves. Visible brush strokes, pigment pooling at the edges of each wash, the "
     "white of the paper left bare for the highlights on its flank. Loose graphite under "
     "drawing still showing through in places. Muted ochre, rust and grey-green. No "
     "photographic detail, no digital gradients."),

    ("anime_check", "832x1216",
     "A cel-shaded anime illustration of a teenage girl in a school uniform standing on a "
     "railway platform in the evening, drawn in the style of a hand-painted 1990s animation "
     "background with flat colour fills, clean black line art and hard-edged shadows. Long "
     "dark hair, a red scarf, a satchel over one shoulder. Warm sodium platform lights "
     "behind her, a painted sky graduating from orange to deep blue."),

    ("product", "1024x1024",
     "A product photograph of a matte black ceramic teapot on a pale grey seamless "
     "background, three-quarter view, the spout pointing to the left of frame. A single "
     "large soft box above and slightly behind creates a long specular highlight down the "
     "shoulder of the pot and a soft gradient shadow beneath. The lid sits fractionally "
     "ajar. 100mm macro at f11, natural colour, no reflections of the studio."),

    ("hex_colour", "1024x1024",
     "A flat vector poster, two colours only: a background of exactly #12303F and a large "
     "circle in exactly #E8B04B occupying the centre, its edge crisp with no gradient and "
     "no texture. Nothing else in the frame. No text."),

    ("json_prompt", "1216x832",
     json.dumps({
         "scene": "a lighthouse keeper's kitchen at first light",
         "subjects": [{"description": "an elderly man in a knitted jumper",
                       "position": "seated at the table on the left third of the frame",
                       "action": "pouring tea from an enamel pot into a chipped mug"}],
         "style": "documentary photography",
         "color_palette": ["#2B3A42", "#C8B99C", "#E1E5E8"],
         "lighting": "low sun through a small salt-stained window camera-right",
         "background": "a cast-iron stove, a shelf of tins, a barometer on the wall",
         "composition": "wide, subject on the left third, empty table filling the right",
         "camera": {"angle": "eye level", "lens": "35mm", "depth_of_field": "deep, f8"},
     }, indent=1)),
]


def mode_spread(a):
    d = os.path.join(SAMPLES, "spread")
    print(f"spread: {len(SPREAD)} subjects", flush=True)
    for name, size, prompt in SPREAD:
        wf = flux_wf(prompt, a.seed, a.steps, a.guidance, parse_size(size), not a.no_turbo,
                     "claude-generated/40-flux2/spread")
        render(wf, dict(mode="spread", cell=name, engine="flux2", turbo=not a.no_turbo,
                        steps=a.steps, guidance=a.guidance, size=size, seed=a.seed,
                        prompt=prompt), d, name)


# --------------------------------------------------------------------------------- ab
# Same prompt, same seed, same pixel count, both engines at their own recommended
# settings. Not the same settings - that would be meaningless across two schedulers.
AB = [
    ("portrait_skin", "1024x1024",
     "A close portrait of a fisherman in his sixties on a harbour wall, head and shoulders "
     "filling the frame. Weathered skin with broken capillaries across the cheeks, three "
     "days of white stubble, pale blue eyes with reddened rims. A navy watch cap. Flat "
     "overcast light, the grey harbour out of focus behind him. 85mm at f2, natural "
     "colour, fine grain, no retouching."),

    ("hands_tool", "1024x1024",
     "A photograph of a pair of hands kneading bread dough on a floured wooden counter, "
     "seen from above at a slight angle. Both hands fully in frame, ten distinct fingers, "
     "flour caked in the creases of the knuckles and under the nails. Warm side light from "
     "a window. 50mm at f4, natural colour."),

    ("text_sign", "1216x832",
     "A photograph of a hand-painted enamel shop sign mounted above a doorway. The sign is "
     "deep green with cream serif lettering that reads exactly NORTHWIND SUPPLY CO. and "
     "below it in smaller capitals EST 1904. The paint is chipped at the corners and the "
     "brass mounting rivets have gone green. Rain-wet brick wall behind, warm light from a "
     "window off frame right. 85mm at f2.8, natural colour."),

    ("instruction_follow", "1216x832",
     "A photograph of a kitchen table shot straight down from above. On the left half of "
     "the table sit exactly three green apples in a row. On the right half sits a single "
     "white enamel jug with a chipped rim. Between them, running from the top edge to the "
     "bottom edge of the frame, lies a wooden spoon. Nothing else is on the table. Flat "
     "overcast daylight from a window out of frame. 35mm, deep focus."),

    ("multi_subject", "1216x832",
     "A photograph of three people in a workshop, evenly spaced across the frame. On the "
     "left, an old man in a brown leather apron files a piece of metal held in a vice. In "
     "the centre, a young woman in a red boilersuit holds a clipboard and looks toward him. "
     "On the right, a teenage boy in a blue hoodie sweeps the floor with a broom, his back "
     "half turned. Afternoon sun through a high dusty window falls across the middle of the "
     "room. 35mm at f4, natural colour."),

    ("illustration", "1024x1024",
     "A watercolour illustration on cold-pressed paper of a fox asleep curled in a bed of "
     "autumn leaves. Visible brush strokes, pigment pooling at the edges of each wash, the "
     "white of the paper left bare for the highlights on its flank. Loose graphite under "
     "drawing still showing through in places. Muted ochre, rust and grey-green. No "
     "photographic detail, no digital gradients."),

    # The measured fact this exists to re-test: "Qwen cannot be steered off photography by
    # prompt at any cfg." FLUX.2 returned a competent cel-shaded frame for this same
    # prompt in --mode spread, so the two need to be seen side by side before anyone
    # claims a third engine can carry non-photographic work.
    ("anime_style", "832x1216",
     "A cel-shaded anime illustration of a teenage girl in a school uniform standing on a "
     "railway platform in the evening, drawn in the style of a hand-painted 1990s animation "
     "background with flat colour fills, clean black line art and hard-edged shadows. Long "
     "dark hair, a red scarf, a satchel over one shoulder. Warm sodium platform lights "
     "behind her, a painted sky graduating from orange to deep blue."),
]


def mode_ab(a):
    d = os.path.join(SAMPLES, "ab")
    cells = [c for c in AB if not a.only or c[0] in a.only.split(",")]
    go = queue if a.batch else render
    print(f"ab: {len(cells)} prompts, engines={a.engines}, batch={a.batch}. "
          f"ALL FLUX FIRST, then all Qwen - never interleaved.", flush=True)
    if a.engines in ("both", "flux2"):
        for name, size, prompt in cells:
            wf = flux_wf(prompt, a.seed, a.steps, a.guidance, parse_size(size), True,
                         "claude-generated/40-flux2/ab")
            go(wf, dict(mode="ab", cell=name, engine="flux2", turbo=True, steps=a.steps,
                        guidance=a.guidance, size=size, seed=a.seed, prompt=prompt),
               d, name + "__flux2")
        if a.batch:
            drain("flux2 cells")
    if a.engines in ("both", "qwen"):
        print("  -- switching model family, expect one long load --", flush=True)
        for name, size, prompt in cells:
            wf = qwen_wf(prompt, a.seed, 20, 2.5, parse_size(size),
                         "claude-generated/40-flux2/ab_qwen")
            go(wf, dict(mode="ab", cell=name, engine="qwen", turbo=False, steps=20,
                        guidance=2.5, size=size, seed=a.seed, prompt=prompt),
               d, name + "__qwen")
        if a.batch:
            drain("qwen cells")


# ------------------------------------------------------------------------------- size
def mode_size(a):
    d = os.path.join(SAMPLES, "size")
    for size in ("768x768", "1024x1024", "1216x832", "1536x1024", "1536x1536", "2048x1152"):
        wf = flux_wf(SWEEP_PROMPT, a.seed, a.steps, a.guidance, parse_size(size), True,
                     "claude-generated/40-flux2/size")
        render(wf, dict(mode="size", cell=size, engine="flux2", turbo=True, steps=a.steps,
                        guidance=a.guidance, size=size, seed=a.seed, prompt=SWEEP_PROMPT),
               d, size)


# -------------------------------------------------------------------------------- one
def mode_one(a):
    if not a.prompt:
        sys.exit("--mode one needs --prompt")
    d = os.path.join(SAMPLES, "one")
    wf = flux_wf(a.prompt, a.seed, a.steps, a.guidance, parse_size(a.size), not a.no_turbo,
                 "claude-generated/40-flux2/one")
    render(wf, dict(mode="one", cell=a.name or "one", engine="flux2", turbo=not a.no_turbo,
                    steps=a.steps, guidance=a.guidance, size=a.size, seed=a.seed,
                    prompt=a.prompt), d, a.name or f"one_{a.seed}")


# ------------------------------------------------------------------------------ turbo
# The Turbo LoRA question, asked on subjects that matter rather than on one still life.
# Turbo is NOT a faster route to the same picture - at one seed it composes a different
# frame - so these pairs answer "which of the two do I want", not "how much did I lose".
TURBO_AB = [
    ("face", "1024x1024", SPREAD[0][2]),
    ("text", "1216x832", SPREAD[3][2]),
    ("crowd", "1216x832", SPREAD[5][2]),
    ("machine", "1024x1024", SWEEP_PROMPT),
]


def mode_turbo(a):
    d = os.path.join(SAMPLES, "turbo")
    go = queue if a.batch else render
    for name, size, prompt in TURBO_AB:
        for turbo, st in ((True, 8), (False, 20)):
            cell = f"{name}__{'turbo08' if turbo else 'noturbo20'}"
            wf = flux_wf(prompt, a.seed, st, a.guidance, parse_size(size), turbo,
                         "claude-generated/40-flux2/turbo")
            go(wf, dict(mode="turbo", cell=cell, engine="flux2", turbo=turbo, steps=st,
                        guidance=a.guidance, size=size, seed=a.seed, prompt=prompt),
               d, cell)
    if a.batch:
        drain("turbo cells")


# ------------------------------------------------------------------------------- face
# A FACE IS A PIXEL PROBLEM is a measured fact on this project: at 832x1216 full-body the
# face lands around 90 px and looks bad at any weights. FLUX.2 stayed coherent at 2.4 MP
# in the size ladder, which means the fix might be "render it bigger" rather than "reframe
# it". Same prompt, same seed, four frame sizes, all the same 2:3 aspect so the face
# occupies the same FRACTION and only the pixel count changes.
FACE_PROMPT = SPREAD[1][2]


def mode_face(a):
    d = os.path.join(SAMPLES, "face")
    go = queue if a.batch else render
    for size in ("832x1216", "1024x1536", "1152x1728", "1280x1920"):
        wf = flux_wf(FACE_PROMPT, a.seed, a.steps, a.guidance, parse_size(size), True,
                     "claude-generated/40-flux2/face")
        go(wf, dict(mode="face", cell=size, engine="flux2", turbo=True, steps=a.steps,
                    guidance=a.guidance, size=size, seed=a.seed, prompt=FACE_PROMPT),
           d, size)
    if a.batch:
        drain("face cells")


MODES = {"settings": mode_settings, "spread": mode_spread, "ab": mode_ab,
         "size": mode_size, "one": mode_one, "turbo": mode_turbo, "face": mode_face}


def main():
    p = argparse.ArgumentParser(
        description="Measure FLUX.2 dev on this box and render the evidence.")
    p.add_argument("--mode", choices=sorted(MODES), default="settings")
    p.add_argument("--seed", type=int, default=5150)
    p.add_argument("--steps", type=int, default=8,
                   help="8 with Turbo, 20-28 without (default: 8)")
    p.add_argument("--guidance", type=float, default=4.0,
                   help="FluxGuidance, NOT cfg. 4.0 is the template value.")
    p.add_argument("--size", default="1024x1024", help="WxH, sets scheduler AND latent")
    p.add_argument("--no-turbo", action="store_true",
                   help="bypass the Turbo LoRA; remember to raise --steps")
    p.add_argument("--prompt", help="--mode one only")
    p.add_argument("--name", help="--mode one only, output filename stem")
    p.add_argument("--engines", choices=("both", "flux2", "qwen"), default="both",
                   help="--mode ab only: render one side of the comparison")
    p.add_argument("--only", default="",
                   help="--mode ab only: comma-separated cell names to redo")
    p.add_argument("--batch", action="store_true",
                   help="submit all cells up front; contiguous queue, no per-cell timing")
    a = p.parse_args()
    os.makedirs(SAMPLES, exist_ok=True)
    t0 = time.time()
    MODES[a.mode](a)
    print(f"\n{a.mode} finished in {time.time()-t0:.0f}s. ledger: {LEDGER}")


if __name__ == "__main__":
    main()
