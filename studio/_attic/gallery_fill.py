#!/usr/bin/env python3
"""gallery_fill.py - render studio/_tools/prompt_recipes.json into an art gallery.

    python3 studio/_tools/gallery_fill.py --engine qwen  --seeds 8
    python3 studio/_tools/gallery_fill.py --engine anime --seeds 8 --hires
    python3 studio/_tools/gallery_fill.py --sheets                 # contact sheets
    python3 studio/_tools/gallery_fill.py --drop id1 id2 ...       # bin the failures

WHAT THIS IS FOR

prompt_recipes.json shipped 60 recipes and its own header says every one of them is a
PREDICTION, not a measurement: "These become facts when someone renders them and looks at
them." This renders them, several seeds deep, and writes every artifact next to the exact
recipe that made it.

THE RULE THIS OBEYS

Every image in studio/samples/gallery_art carries a manifest record with the literal
positive prompt, the literal RESOLVED negative (the @token expanded, not the token), the
seed, steps, cfg, sampler, scheduler, size, checkpoint or unet+clip+vae, and every LoRA
with its strength. Anything a second person needs to reproduce the pixel is in the record.
Nothing is graded, nothing is upscaled after the fact: the only post-step is PNG -> WEBP,
recorded as `post`, so what you see is what the settings produced.

WHY THE GRAPHS ARE BUILT HERE INSTEAD OF LOADED

The two graphs are assembled in this file rather than patched from workflows/*.json, for
two reasons. The qwen path needs 02_qwen_t2i_quality's 20-step cfg-2.5 sampler, which is
the settings block every qwen recipe asks for, but with a LoRA slot that graph has not
got. The anime path needs 22_anime_kf_ipadapter WITHOUT its IPAdapter - the studio's own
gallery_gen.py reaches for that graph and then sets weight 0.0, which loads a CLIPVision
and an IPAdapter model to multiply by zero. Building the graph here keeps this tool from
editing files it does not own, and every node id below is checked against /object_info
before a single job is queued (--check does it on its own).

RESUMABLE

Record ids are deterministic: <recipe_id>__s<seed>[__hires]. An id already in the manifest
is skipped, so this can be killed and restarted, and a second pass with a larger --seeds
only renders what is new.

THE RATIO IS THE POINT

--sheets builds labelled contact sheets so the failures can be found by LOOKING, and
--drop moves them to _dropped/ and flips keep=false in the manifest rather than deleting
them. Rendered vs kept is the honest number and it stays computable from the manifest.
"""
import argparse
import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
HOST = os.environ.get("COMFY_HOST", "127.0.0.1:8188")

RECIPES = os.path.join(HERE, "prompt_recipes.json")
OUT = os.path.join(STUDIO, "samples", "gallery_art")
DROPPED = os.path.join(OUT, "_dropped")
SHEETS = os.path.join(OUT, "_sheets")
MANIFEST = os.path.join(OUT, "manifest.jsonl")

# One seed set shared by every recipe, so any two recipes are comparable at seed n and a
# re-run with a bigger --seeds is additive rather than a reshuffle.
SEEDS = [7311, 20250805, 424242, 8888, 13337, 555, 991733, 60606,
         31415, 271828, 161803, 141421,
         # Extended after measuring seed variance: the illustration engine moves a median
         # 60.3 mean-abs-diff between seeds of one recipe against qwen's 35.8, so extra
         # seeds buy real compositional diversity there and very little on qwen.
         2718, 1618, 1414, 5772, 6180, 3010, 4669, 8091,
         1234, 9001, 4242, 7777, 3141, 2024, 8765, 5150]

QWEN_UNET = "qwen_image_2512_fp8_e4m3fn.safetensors"
QWEN_CLIP = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
QWEN_VAE = "qwen_image_vae.safetensors"
ANIME_CKPT = "animagine-xl-4.0.safetensors"

PREFIX = "claude-generated/gallery_art"

# Node classes this file emits. Checked against /object_info before anything is queued,
# because a graph that references a missing class fails at submit with a wall of JSON.
NEEDED = ["UNETLoader", "CLIPLoader", "VAELoader", "ModelSamplingAuraFlow", "CFGNorm",
          "CLIPTextEncode", "EmptySD3LatentImage", "KSampler", "VAEDecode", "SaveImage",
          "CheckpointLoaderSimple", "EmptyLatentImage", "LatentUpscale",
          "LoraLoaderModelOnly", "LoraLoader"]


# ---------------------------------------------------------------- comfy client

def api(path, payload=None, timeout=120):
    url = "http://%s%s" % (HOST, path)
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def submit(graph):
    r = api("/prompt", {"prompt": graph})
    if "error" in r:
        raise RuntimeError(json.dumps(r["error"])[:600])
    return r["prompt_id"]


def fetch(rel, dest):
    """Pull an output over /view. Never read ComfyUI's output dir off the share - it has
    been measured minutes behind the API, which looks exactly like a failed render."""
    sub, _, name = rel.rpartition("/")
    q = urllib.parse.urlencode({"filename": name, "subfolder": sub, "type": "output"})
    with urllib.request.urlopen("http://%s/view?%s" % (HOST, q), timeout=300) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    return dest


# ---------------------------------------------------------------- recipe layer

def load_recipes():
    d = json.load(open(RECIPES, encoding="utf-8"))
    return d["_meta"], d["recipes"]


def resolve_negative(meta, r):
    """@token -> the literal string. The manifest stores what the sampler actually saw."""
    neg = r.get("negative") or ""
    if neg.startswith("@"):
        neg = meta["negatives"].get(neg[1:], meta["negatives"].get(neg, ""))
    add = r.get("negative_add")
    if add:
        neg = (neg.rstrip().rstrip(",") + ", " + add) if neg.strip() else add
    return neg


def loras_of(r):
    """Normalise the optional lora field to a list of {name, strength}."""
    lo = r.get("lora")
    if not lo:
        return []
    if isinstance(lo, dict):
        lo = [lo]
    out = []
    for x in lo:
        if isinstance(x, str):
            out.append({"name": x, "strength": 1.0})
        else:
            out.append({"name": x.get("name") or x.get("lora_name"),
                        "strength": float(x.get("strength",
                                               x.get("strength_model", 1.0)))})
    return [x for x in out if x["name"]]


# ---------------------------------------------------------------- graph builders

def qwen_graph(prompt, negative, w, h, seed, steps, cfg, sampler, scheduler,
               loras, prefix, shift=3.1):
    """02_qwen_t2i_quality's topology - no Lightning LoRA, 20 steps at cfg 2.5 - with a
    LoRA chain spliced between the UNET and ModelSamplingAuraFlow."""
    g = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": QWEN_UNET, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": QWEN_CLIP, "type": "qwen_image",
                         "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": QWEN_VAE}},
        "10": {"class_type": "CLIPTextEncode",
               "inputs": {"clip": ["2", 0], "text": prompt}},
        "11": {"class_type": "CLIPTextEncode",
               "inputs": {"clip": ["2", 0], "text": negative}},
        "12": {"class_type": "EmptySD3LatentImage",
               "inputs": {"width": w, "height": h, "batch_size": 1}},
        "14": {"class_type": "VAEDecode",
               "inputs": {"samples": ["13", 0], "vae": ["3", 0]}},
        "15": {"class_type": "SaveImage",
               "inputs": {"images": ["14", 0], "filename_prefix": prefix}},
    }
    src = ["1", 0]
    for i, lo in enumerate(loras):
        nid = "40%d" % i
        g[nid] = {"class_type": "LoraLoaderModelOnly",
                  "inputs": {"model": src, "lora_name": lo["name"],
                             "strength_model": lo["strength"]}}
        src = [nid, 0]
    g["5"] = {"class_type": "ModelSamplingAuraFlow",
              "inputs": {"model": src, "shift": shift}}
    g["6"] = {"class_type": "CFGNorm", "inputs": {"model": ["5", 0], "strength": 1.0}}
    g["13"] = {"class_type": "KSampler",
               "inputs": {"model": ["6", 0], "positive": ["10", 0],
                          "negative": ["11", 0], "latent_image": ["12", 0],
                          "seed": seed, "steps": steps, "cfg": cfg,
                          "sampler_name": sampler, "scheduler": scheduler,
                          "denoise": 1.0}}
    return g


def anime_graph(prompt, negative, w, h, seed, steps, cfg, sampler, scheduler,
                loras, prefix, hires=None, method="bislerp"):
    """22_anime_kf_ipadapter's sampler settings with the IPAdapter branch removed.

    hires = (width, height, denoise, steps). SDXL is bucket-trained: asking for 1024x1536
    in one pass invites a second head. Sampling at the trained bucket and resampling an
    upscaled latent is the way to spend pixels on a face without breaking the anatomy.

    MEASURED, not assumed: the denoise on that second pass is the whole ballgame on a cel
    checkpoint. Too low and you get a blurred latent with nothing rebuilt; too high and
    the second pass re-invents the picture. See --tag ladders in the manifest.
    """
    g = {
        "1": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": ANIME_CKPT}},
        "7": {"class_type": "EmptyLatentImage",
              "inputs": {"width": w, "height": h, "batch_size": 1}},
        "11": {"class_type": "SaveImage",
               "inputs": {"images": ["9", 0], "filename_prefix": prefix}},
    }
    model, clip = ["1", 0], ["1", 1]
    for i, lo in enumerate(loras):
        nid = "40%d" % i
        g[nid] = {"class_type": "LoraLoader",
                  "inputs": {"model": model, "clip": clip, "lora_name": lo["name"],
                             "strength_model": lo["strength"],
                             "strength_clip": lo["strength"]}}
        model, clip = [nid, 0], [nid, 1]
    g["5"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": clip, "text": prompt}}
    g["6"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": clip, "text": negative}}
    g["8"] = {"class_type": "KSampler",
              "inputs": {"model": model, "positive": ["5", 0], "negative": ["6", 0],
                         "latent_image": ["7", 0], "seed": seed, "steps": steps,
                         "cfg": cfg, "sampler_name": sampler, "scheduler": scheduler,
                         "denoise": 1.0}}
    tail = ["8", 0]
    if hires:
        hw, hh, hden, hsteps = hires
        g["20"] = {"class_type": "LatentUpscale",
                   "inputs": {"samples": ["8", 0], "upscale_method": method,
                              "width": hw, "height": hh, "crop": "disabled"}}
        g["21"] = {"class_type": "KSampler",
                   "inputs": {"model": model, "positive": ["5", 0],
                              "negative": ["6", 0], "latent_image": ["20", 0],
                              "seed": seed, "steps": hsteps, "cfg": cfg,
                              "sampler_name": sampler, "scheduler": scheduler,
                              "denoise": hden}}
        tail = ["21", 0]
    g["9"] = {"class_type": "VAEDecode", "inputs": {"samples": tail, "vae": ["1", 2]}}
    return g


# ---------------------------------------------------------------- job planning

def hires_target(w, h, factor):
    """Round to /8 so the latent upscale is exact."""
    return (int(round(w * factor / 8)) * 8, int(round(h * factor / 8)) * 8)


def plan(meta, recipes, engine, families, nseeds, hires, only, factor,
         hden=0.45, hsteps=None, method="bislerp", tag="", exclude=None):
    jobs = []
    for r in recipes:
        if engine and r["engine"] != engine:
            continue
        if families and r["family"] not in families:
            continue
        if only and r["id"] not in only:
            continue
        if exclude and r["id"] in exclude:
            continue
        s = r.get("settings", {})
        w, h = r["size"]
        neg = resolve_negative(meta, r)
        los = loras_of(r)
        if r["engine"] == "qwen":
            steps = int(s.get("steps", 20))
            cfg = float(s.get("cfg", 2.5))
            sampler = s.get("sampler") or "euler"
            sched = s.get("scheduler") or "simple"
        else:
            steps = int(s.get("steps", 28))
            cfg = float(s.get("cfg", 5.0))
            sampler = s.get("sampler") or "euler_ancestral"
            sched = s.get("scheduler") or "normal"
        hi = None
        if hires and r["engine"] == "anime":
            hw, hh = hires_target(w, h, factor)
            hi = (hw, hh, hden, hsteps or max(10, steps // 2), method)
        base = s.get("seed")
        seeds = list(SEEDS[:nseeds])
        if base is not None and base not in seeds:
            seeds = [base] + seeds[:max(0, nseeds - 1)]
        for sd in seeds:
            rid = "%s__s%d%s%s" % (r["id"], sd, "__hires" if hi else "",
                                   ("__" + tag) if tag else "")
            jobs.append({
                "id": rid, "recipe": r, "seed": sd, "w": w, "h": h,
                "steps": steps, "cfg": cfg, "sampler": sampler, "scheduler": sched,
                "negative": neg, "loras": los, "hires": hi, "tag": tag,
            })
    return jobs


def graph_for(j):
    r = j["recipe"]
    prefix = "%s/%s" % (PREFIX, j["id"])
    if r["engine"] == "qwen":
        return qwen_graph(r["prompt"], j["negative"], j["w"], j["h"], j["seed"],
                          j["steps"], j["cfg"], j["sampler"], j["scheduler"],
                          j["loras"], prefix)
    hi = j["hires"]
    return anime_graph(r["prompt"], j["negative"], j["w"], j["h"], j["seed"],
                       j["steps"], j["cfg"], j["sampler"], j["scheduler"],
                       j["loras"], prefix, hires=hi[:4] if hi else None,
                       method=hi[4] if hi else "bislerp")


def record(j, rel, webp, elapsed, stats):
    r = j["recipe"]
    rec = {
        "id": j["id"],
        "recipe_id": r["id"],
        "title": r.get("title"),
        "family": r.get("family"),
        "engine": r["engine"],
        "file": os.path.relpath(webp, ROOT).replace("\\", "/"),
        "keep": True,
        "rendered": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "seconds": round(elapsed, 1),
        # --- the recipe, complete, literal, resolved -------------------------
        "models": ({"unet": QWEN_UNET, "clip": QWEN_CLIP, "vae": QWEN_VAE,
                    "shift": 3.1, "cfg_norm": 1.0}
                   if r["engine"] == "qwen"
                   else {"checkpoint": ANIME_CKPT}),
        "prompt": r["prompt"],
        "negative_token": r.get("negative"),
        "negative": j["negative"],
        "seed": j["seed"],
        "steps": j["steps"],
        "cfg": j["cfg"],
        "sampler": j["sampler"],
        "scheduler": j["scheduler"],
        "size": [j["w"], j["h"]],
        "loras": j["loras"],
        "hires": ({"width": j["hires"][0], "height": j["hires"][1],
                   "upscale": "LatentUpscale " + j["hires"][4],
                   "denoise": j["hires"][2],
                   "steps": j["hires"][3]} if j["hires"] else None),
        "tag": j.get("tag") or None,
        "final_size": stats.get("size"),
        "post": "PNG -> WEBP quality 92. No grade, no post upscale, no face pass.",
        "source_png": rel,
        # --- the claim the recipe made, kept next to the result --------------
        "style": r.get("style"), "look": r.get("look"), "place": r.get("place"),
        "technique": r.get("technique"),
        "why_predicted": r.get("why"),
        "risk_predicted": r.get("risk"),
        # --- cheap self-audit so flat or crushed frames surface without eyes -
        "luma_mean": stats.get("luma"), "luma_sd": stats.get("sd"),
        "flag": stats.get("flag"),
    }
    return rec


# ---------------------------------------------------------------- image helpers

def to_webp(png_path, dst):
    from PIL import Image
    im = Image.open(png_path).convert("RGB")
    im.save(dst, "WEBP", quality=92, method=4)
    return im


def measure(im):
    """Mean luma and spread, without numpy - the system python3 on this box has PIL but
    no numpy, which is what stops seven other tools in this directory from running."""
    g = im.convert("L").resize((128, 128))
    px = list(g.getdata())
    n = len(px)
    mean = sum(px) / n
    var = sum((p - mean) ** 2 for p in px) / n
    sd = var ** 0.5
    flag = None
    if mean < 12:
        flag = "near-black"
    elif mean > 243:
        flag = "blown"
    elif sd < 8:
        flag = "flat"
    return {"luma": round(mean, 1), "sd": round(sd, 1), "flag": flag,
            "size": list(im.size)}


# ---------------------------------------------------------------- manifest

def read_manifest():
    recs = []
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        recs.append(json.loads(line))
                    except ValueError:
                        pass
    return recs


def append_manifest(rec):
    os.makedirs(OUT, exist_ok=True)
    with open(MANIFEST, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def rewrite_manifest(recs):
    tmp = MANIFEST + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, MANIFEST)


# ---------------------------------------------------------------- the run loop

def wait_for(pid, timeout=1800):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            h = api("/history/%s" % pid, timeout=30)
        except Exception:
            time.sleep(3)
            continue
        if pid in h:
            e = h[pid]
            st = e.get("status", {})
            if st.get("status_str") == "error":
                return None, st
            if st.get("completed"):
                outs = []
                for _, out in e.get("outputs", {}).items():
                    for f in out.get("images", []):
                        outs.append(("%s/%s" % (f.get("subfolder", ""),
                                                f["filename"])).lstrip("/"))
                return outs, None
        time.sleep(2)
    return None, {"timeout": True}


def run(args):
    meta, recipes = load_recipes()
    only = set(args.only.split(",")) if args.only else None
    fams = set(args.family.split(",")) if args.family else None
    jobs = plan(meta, recipes, args.engine, fams, args.seeds, args.hires, only,
                args.hires_factor, args.hires_denoise, args.hires_steps,
                args.hires_method, args.tag,
                set(args.exclude.split(",")) if args.exclude else None)
    done = {r["id"] for r in read_manifest()}
    jobs = [j for j in jobs if j["id"] not in done]
    if args.shuffle:
        jobs.sort(key=lambda j: hashlib.md5(j["id"].encode()).hexdigest())
    if args.limit:
        jobs = jobs[:args.limit]
    print("PLAN %d jobs (%d already in manifest)" % (len(jobs), len(done)), flush=True)
    if args.dry:
        for j in jobs[:40]:
            print("  ", j["id"], j["w"], "x", j["h"],
                  ("hires->%dx%d" % (j["hires"][0], j["hires"][1])) if j["hires"] else "")
        return 0

    os.makedirs(OUT, exist_ok=True)
    scratch = os.path.join(OUT, "_png")
    os.makedirs(scratch, exist_ok=True)

    # Queue depth. ComfyUI runs one job at a time but a filled queue means the GPU never
    # waits on this script's round trips. Depth is small so a kill loses little.
    depth = args.depth
    inflight = []          # [(prompt_id, job, t_submitted)]
    kept = failed = 0
    t_start = time.time()
    qi = 0
    while qi < len(jobs) or inflight:
        while qi < len(jobs) and len(inflight) < depth:
            j = jobs[qi]
            qi += 1
            try:
                pid = submit(graph_for(j))
            except Exception as e:
                print("SUBMIT-FAIL %s %s" % (j["id"], str(e)[:300]), flush=True)
                failed += 1
                continue
            inflight.append((pid, j, time.time()))
        if not inflight:
            break
        pid, j, t0 = inflight.pop(0)
        outs, err = wait_for(pid)
        if not outs:
            print("FAIL %s %s" % (j["id"], json.dumps(err)[:300]), flush=True)
            failed += 1
            continue
        rel = outs[0]
        png = os.path.join(scratch, j["id"] + ".png")
        webp = os.path.join(OUT, j["id"] + ".webp")
        try:
            fetch(rel, png)
            im = to_webp(png, webp)
            stats = measure(im)
        except Exception as e:
            print("POST-FAIL %s %s" % (j["id"], str(e)[:300]), flush=True)
            failed += 1
            continue
        finally:
            if os.path.exists(png) and not args.keep_png:
                try:
                    os.remove(png)
                except OSError:
                    pass
        append_manifest(record(j, rel, webp, time.time() - t0, stats))
        kept += 1
        el = time.time() - t_start
        print("OK  %-52s %5.1fs  %sx%s luma=%s%s  [%d/%d  %.0fs elapsed]"
              % (j["id"], time.time() - t0, stats["size"][0], stats["size"][1],
                 stats["luma"], (" FLAG=" + stats["flag"]) if stats["flag"] else "",
                 kept + failed, len(jobs), el), flush=True)
    print("RUN DONE rendered=%d failed=%d in %.0fs" % (kept, failed,
                                                       time.time() - t_start),
          flush=True)
    return 0


# ---------------------------------------------------------------- contact sheets

def sheets(args):
    from PIL import Image, ImageDraw, ImageFont
    recs = [r for r in read_manifest() if r.get("keep", True)]
    if args.family:
        fams = set(args.family.split(","))
        recs = [r for r in recs if r.get("family") in fams]
    if args.engine:
        recs = [r for r in recs if r.get("engine") == args.engine]
    if args.only:
        want = set(args.only.split(","))
        recs = [r for r in recs if r.get("recipe_id") in want]
    recs.sort(key=lambda r: (r.get("recipe_id", ""), r.get("seed", 0)))
    os.makedirs(SHEETS, exist_ok=True)
    font = None
    for p in ("/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            font = ImageFont.truetype(p, 15)
            break
    if font is None:
        font = ImageFont.load_default()
    cw, ch, lab = args.cell, args.cell, 22
    cols = args.cols
    per = cols * args.rows
    made = []
    for page in range(0, (len(recs) + per - 1) // per):
        chunk = recs[page * per:(page + 1) * per]
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cw, rows * (ch + lab)), (22, 22, 24))
        d = ImageDraw.Draw(sheet)
        for i, r in enumerate(chunk):
            x, y = (i % cols) * cw, (i // cols) * (ch + lab)
            p = os.path.join(ROOT, r["file"])
            if os.path.exists(p):
                im = Image.open(p).convert("RGB")
                im.thumbnail((cw - 6, ch - 6))
                sheet.paste(im, (x + 3 + (cw - 6 - im.size[0]) // 2,
                                 y + 3 + (ch - 6 - im.size[1]) // 2))
            tag = "%s s%s%s%s" % (r.get("recipe_id"), r.get("seed"),
                                  (" " + r["tag"]) if r.get("tag") else "",
                                  (" " + r["flag"]) if r.get("flag") else "")
            d.text((x + 5, y + ch + 3), tag[:int(cw / 7.4)], font=font,
                   fill=(235, 235, 240))
        name = "sheet_%s%s_%02d.png" % (args.engine or "all",
                                        ("_" + args.family.replace(",", "-"))
                                        if args.family else "", page + 1)
        dst = os.path.join(SHEETS, name)
        sheet.save(dst)
        made.append(dst)
        print("SHEET", dst, len(chunk), "cells", flush=True)
    print("%d sheets over %d kept images" % (len(made), len(recs)))
    return 0


# ---------------------------------------------------------------- judging

def drop(args):
    """Bin by record id OR by recipe_id (drops every seed of that recipe)."""
    ids = set()
    for a in args.drop:
        ids |= {x.strip() for x in a.split(",") if x.strip()}
    recs = read_manifest()
    os.makedirs(DROPPED, exist_ok=True)
    n = 0
    for r in recs:
        if not r.get("keep", True):
            continue
        if r["id"] in ids or r.get("recipe_id") in ids:
            src = os.path.join(ROOT, r["file"])
            dst = os.path.join(DROPPED, os.path.basename(src))
            if os.path.exists(src):
                os.replace(src, dst)
            r["keep"] = False
            r["dropped_reason"] = args.reason or "failed review by eye"
            r["file"] = os.path.relpath(dst, ROOT).replace("\\", "/")
            n += 1
    rewrite_manifest(recs)
    print("dropped %d records" % n)
    return stats_cmd(args)


def stats_cmd(args):
    recs = read_manifest()
    kept = [r for r in recs if r.get("keep", True)]
    print("rendered %d   kept %d   dropped %d   keep-rate %.0f%%"
          % (len(recs), len(kept), len(recs) - len(kept),
             100.0 * len(kept) / max(1, len(recs))))
    by = {}
    for r in recs:
        k = (r.get("engine"), r.get("family"))
        b = by.setdefault(k, [0, 0])
        b[0] += 1
        b[1] += 1 if r.get("keep", True) else 0
    for k in sorted(by, key=lambda x: (x[0] or "", x[1] or "")):
        t, kp = by[k]
        print("  %-8s %-14s rendered %4d  kept %4d  (%.0f%%)"
              % (k[0], k[1], t, kp, 100.0 * kp / max(1, t)))
    # NOT GPU time. `seconds` is submit-to-download latency, and at --depth 3 each job
    # spends most of that waiting behind two others, so this sum overcounts by roughly
    # the queue depth. It also inflates whenever another process shares the GPU - a
    # second agent was rendering LTX video on this box during the qwen wave. Reported as
    # what it is rather than dressed up as a compute figure.
    secs = sum(r.get("seconds", 0) for r in recs)
    print("  summed job latency: %.1f h  (submit->download, NOT exclusive GPU time;"
          " overcounts by ~the queue depth)" % (secs / 3600.0))
    return 0


def index(args):
    """Emit index.json - the kept corpus grouped by recipe, ready for a gallery route.

    manifest.jsonl is the record of everything that happened, dropped frames included.
    index.json is the SHIPPABLE view: kept images only, grouped by recipe, each group
    carrying the recipe once instead of once per image. Nothing consumes it yet; it
    exists so that wiring a page is a template job and not an archaeology job.
    """
    meta, recipes = load_recipes()
    by_id = {r["id"]: r for r in recipes}
    recs = read_manifest()
    kept = [r for r in recs if r.get("keep", True)]
    groups = {}
    for r in kept:
        groups.setdefault(r["recipe_id"], []).append(r)
    out = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "source": "studio/_tools/prompt_recipes.json",
           "tool": "studio/_tools/gallery_fill.py",
           "rendered": len(recs), "kept": len(kept),
           "keep_rate": round(100.0 * len(kept) / max(1, len(recs)), 1),
           "note": ("Every image carries the complete recipe that made it. The only "
                    "post-step is PNG -> WEBP quality 92: no grade, no post upscale, "
                    "no face pass. Dropped frames stay in manifest.jsonl with "
                    "keep=false and a reason, so the keep rate is recomputable."),
           "recipes": []}
    for rid in sorted(groups):
        g = sorted(groups[rid], key=lambda r: r.get("seed", 0))
        src = by_id.get(rid, {})
        g0 = g[0]
        out["recipes"].append({
            "recipe_id": rid, "title": g0.get("title"), "engine": g0.get("engine"),
            "family": g0.get("family"),
            "technique": g0.get("technique"),
            "why_predicted": g0.get("why_predicted"),
            "risk_predicted": g0.get("risk_predicted"),
            "style": g0.get("style"), "look": g0.get("look"), "place": g0.get("place"),
            "prompt": g0.get("prompt"), "negative": g0.get("negative"),
            "negative_token": g0.get("negative_token"),
            "models": g0.get("models"), "steps": g0.get("steps"), "cfg": g0.get("cfg"),
            "sampler": g0.get("sampler"), "scheduler": g0.get("scheduler"),
            "size": g0.get("size"), "hires": g0.get("hires"), "loras": g0.get("loras"),
            "kept": len(g),
            "rendered": len([r for r in recs if r["recipe_id"] == rid]),
            "images": [{"file": r["file"], "seed": r["seed"],
                        "size": r.get("final_size"), "id": r["id"]} for r in g],
        })
    dst = os.path.join(OUT, "index.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("wrote %s - %d recipes, %d kept images"
          % (dst, len(out["recipes"]), len(kept)))
    return 0


def check(args):
    info = api("/object_info", timeout=120)
    missing = [n for n in NEEDED if n not in info]
    print("object_info: %d classes; missing from this graph set: %s"
          % (len(info), missing or "none"))
    meta, recipes = load_recipes()
    print("recipes: %d" % len(recipes))
    fams = {}
    for r in recipes:
        fams[(r["engine"], r["family"])] = fams.get((r["engine"], r["family"]), 0) + 1
    for k in sorted(fams):
        print("  %-6s %-14s %d" % (k[0], k[1], fams[k]))
    return 1 if missing else 0


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--engine", choices=["qwen", "anime"])
    p.add_argument("--family", help="probe,photographic,illustration,typographic")
    p.add_argument("--only", help="comma separated recipe ids")
    p.add_argument("--exclude",
                   help="comma separated recipe ids to skip - use it to stop re-rendering "
                        "a recipe already judged a total failure")
    p.add_argument("--seeds", type=int, default=1)
    p.add_argument("--hires", action="store_true",
                   help="anime only: latent upscale + resample pass")
    p.add_argument("--hires-factor", type=float, default=1.35)
    p.add_argument("--hires-denoise", type=float, default=0.45)
    p.add_argument("--hires-steps", type=int)
    p.add_argument("--hires-method", default="bislerp",
                   choices=["bislerp", "nearest-exact", "bilinear", "area", "bicubic"])
    p.add_argument("--tag", default="",
                   help="suffix on the record id, so a settings ladder does not collide")
    p.add_argument("--depth", type=int, default=3, help="queue depth")
    p.add_argument("--limit", type=int)
    p.add_argument("--shuffle", action="store_true",
                   help="spread recipes through the run so an early kill still samples wide")
    p.add_argument("--keep-png", action="store_true")
    p.add_argument("--dry", action="store_true")
    p.add_argument("--sheets", action="store_true")
    p.add_argument("--cols", type=int, default=4)
    p.add_argument("--rows", type=int, default=4)
    p.add_argument("--cell", type=int, default=460)
    p.add_argument("--drop", nargs="+")
    p.add_argument("--reason")
    p.add_argument("--stats", action="store_true")
    p.add_argument("--index", action="store_true")
    p.add_argument("--check", action="store_true")
    a = p.parse_args()
    if a.check:
        return check(a)
    if a.index:
        return index(a)
    if a.stats:
        return stats_cmd(a)
    if a.drop:
        return drop(a)
    if a.sheets:
        return sheets(a)
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
