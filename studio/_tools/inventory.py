#!/usr/bin/env python3
"""studio/_tools/inventory.py - what this studio can run, derived from the files, never typed.

Writes two documents and prints one report:

  workflows/INDEX.md   every API graph in workflows/: family, engine, the model files it names,
                       the tools that drive it, its first `_comment` line, and whether it is a
                       PAID partner node (Seedance, Nano Banana...) or local weights.
  docs/MODELS.md       every model file under ComfyUI/models with its size and the workflows that
                       name it - and the ORPHANS, files no graph uses (the review clock's list).
  (report)             the templates ComfyUI ships that no workflow here mirrors: a template
                       whose node classes or model files appear in none of ours is a capability
                       the box could have and does not. This is how Krea 2, Qwen-Image-2.1 and
                       Wan Animate 2 were found sitting in the installed template set on
                       2026-09-27, two months after they shipped.

    python3 studio/_tools/inventory.py            # write both documents, print the report
    python3 studio/_tools/inventory.py --check    # print only; exit 3 if any unmirrored template

Reads only: workflows/*.json (API), the installed template package (UI JSON, subgraphs and all),
ComfyUI/models/*, and the studio's own .py/.sh files for the drivers. Nothing here submits a job.
"""
import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COMFY = os.path.expanduser("~/ComfyUI")
WF = os.path.join(ROOT, "workflows")
MODEL_DIRS = ("diffusion_models", "checkpoints", "loras", "text_encoders", "vae", "upscale_models",
              "clip_vision", "controlnet", "audio_encoders", "latent_upscale_models", "model_patches",
              "detection", "background_removal", "frame_interpolation", "ipadapter", "TTS", "tts",
              "geometry_estimation")
WEIGHT_EXT = (".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".onnx", ".gguf")

# where the studio's graphs get driven from (a filename mention counts)
DRIVER_GLOBS = ("studio/_tools/*.py", "studio/*.py", "scripts/*.py", "scripts/*.sh", "films/*.py",
                "bin/*")

# families by the model file or node class that defines them, first match wins
FAMILIES = [
    ("Seedance / ByteDance (paid)", r"ByteDance"),
    ("Nano Banana / Gemini (paid)", r"Gemini"),
    ("Kling (paid)", r"Kling"),
    ("LTX-2.5", r"ltx-2\.5|ltx2\.5"),
    ("LTX-2.3", r"ltx-2\.3|ltx_2\.3|ltx2\.3"),
    ("LTX (other)", r"LTXV|ltx"),
    ("MiniMax H3", r"minimax_h3|MiniMaxH3"),
    ("MiniMax Music", r"minimax_music|MiniMaxMusic"),
    ("Wan Animate 2", r"wan_animate_2|WanAnimate2"),
    ("Wan VACE", r"vace|WanVace"),
    ("Wan 2.x", r"wan2|Wan"),
    ("HunyuanVideo 1.5", r"hunyuanvideo1\.5|HunyuanImageToVideo"),
    ("Hunyuan 3D", r"hunyuan_3d|Hunyuan3D"),
    ("Krea 2", r"krea2"),
    ("Qwen-Image-2.1", r"qwen_image_2\.1|QwenImage21"),
    ("Qwen-Image / Edit", r"qwen_image|QwenImage"),
    ("Flux 2", r"flux2|Flux2"),
    ("Flux 1", r"flux\.1|flux1"),
    ("Z-Image", r"z_image"),
    ("SDXL (anime / photoreal)", r"animagine|Illustrious|RealVis|sdxl|IPAdapter"),
    ("ACE-Step", r"acestep|ace_step|ACEStep"),
    ("Stable Audio", r"stable_audio|StableAudio"),
    ("Voice / TTS", r"chatterbox|Chatterbox|indextts|IndexTTS|higgs|Higgs|TTS"),
    ("Segment / matte / depth / pose", r"sam3|birefnet|BiRefNet|SAM3|moge|MoGe|depth_anything|DA3|sdpose|SDPose"),
    ("Upscale / interpolate", r"RealESRGAN|ESRGAN|Upscale|film_net|FILM|seedvr|SeedVR"),
    ("LLM / prompt", r"TextGenerate|gemma|Gemma"),
    ("3D", r"triposplat|TripoSplat|Hunyuan3D"),
]
PAID_RE = re.compile(r"ByteDance|Gemini|Kling|Veo|Sora|Runway|Luma|Recraft|Ideogram|Vidu|Grok|"
                     r"Minimax(Hailuo|H3Max)|OpenAI|Topaz|Meshy|HappyHorse|Api$|Api[A-Z]")
# node classes that say nothing about WHAT a graph does
GENERIC = re.compile(r"^(Load|Save|Preview|Primitive|Get|Resize|Image|Empty|Create|VAE|CLIPText|CLIPLoader|"
                     r"UNETLoader|LoraLoader|KSampler|Sampler|Basic|Random|Manual|ModelSampling|"
                     r"Conditioning|Comfy|Markdown|Note|Reroute|String|Math|Resolution|Repeat|Batch|"
                     r"Trim|Rebatch|Start|End|Item|List|Switch|Video|Latent|Upscale|Checkpoint|"
                     r"Canny|Crop|Pad|Text|Int|Float|Bool|Json|Select|Flux|Guider|Scheduler|Noise|"
                     r"CFG|Clip|Audio|Mask|Grow|Invert|Blend|Composite|Stitch|Compare|Any|Split|"
                     r"Set|Frame|Context)")


def _walk_strings(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from _walk_strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk_strings(v)
    elif isinstance(o, str):
        yield o


def our_workflows():
    out = []
    for p in sorted(glob.glob(os.path.join(WF, "*.json"))):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception as e:
            out.append({"file": os.path.basename(p), "error": str(e)[:80]})
            continue
        nodes = {k: v for k, v in d.items() if not k.startswith("_") and isinstance(v, dict)
                 and "class_type" in v}
        classes = sorted({v["class_type"] for v in nodes.values()})
        files = sorted({s for v in nodes.values() for s in _walk_strings(v.get("inputs", {}))
                        if s.lower().endswith(WEIGHT_EXT)})
        comment = d.get("_comment", "")
        if isinstance(comment, list):
            comment = " ".join(str(c) for c in comment)
        comment = re.sub(r"\s+", " ", str(comment)).strip()
        out.append({"file": os.path.basename(p), "classes": classes, "files": files,
                    "comment": comment, "paid": any(PAID_RE.search(c) for c in classes)})
    return out


def family_of(w):
    hay = " ".join(w.get("files", []) + w.get("classes", []) + [w["file"]])
    for name, pat in FAMILIES:
        if re.search(pat, hay):
            return name
    return "other"


def drivers():
    """workflow filename -> tools that mention it."""
    idx = {}
    for g in DRIVER_GLOBS:
        for p in glob.glob(os.path.join(ROOT, g)):
            try:
                t = open(p, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            rel = os.path.relpath(p, ROOT)
            for m in re.finditer(r"\b(\d\d[a-z]?_[A-Za-z0-9_\.]+?\.json)\b|\b(\d\d[a-z]?_[a-z0-9_]+)\b", t):
                key = (m.group(1) or m.group(2))
                if key.endswith(".json"):
                    key = key[:-5]
                idx.setdefault(key, set()).add(rel)
    return idx


def models_on_disk():
    out = {}
    for d in MODEL_DIRS:
        base = os.path.join(COMFY, "models", d)
        if not os.path.isdir(base):
            continue
        for root, _, files in os.walk(base):
            for f in files:
                if f.lower().endswith(WEIGHT_EXT) and not f.startswith("put_"):
                    p = os.path.join(root, f)
                    try:
                        size = os.path.getsize(p)
                    except OSError:
                        continue
                    out[f] = {"dir": d, "size": size, "link": os.path.islink(p)}
    return out


def templates_dir():
    for pat in ("venv/lib*/python*/site-packages/comfyui_workflow_templates_json/templates",
                "venv/lib*/python*/site-packages/comfyui_workflow_templates/templates"):
        hits = glob.glob(os.path.join(COMFY, pat))
        if hits:
            return hits[0]
    return None


def template_nodes(d):
    out = []
    for n in d.get("nodes", []):
        t = n.get("type")
        if t:
            out.append(t)
    for sg in (d.get("definitions") or {}).get("subgraphs", []):
        out += template_nodes(sg)
    return out


def templates():
    tdir = templates_dir()
    if not tdir:
        return [], None
    idx = {}
    ip = os.path.join(tdir, "index.json")
    if os.path.exists(ip):
        def walk(o):
            if isinstance(o, dict):
                if isinstance(o.get("name"), str) and ("title" in o or "mediaType" in o):
                    idx[o["name"]] = (o.get("title", ""), o.get("date", ""))
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        try:
            walk(json.load(open(ip, encoding="utf-8")))
        except Exception:
            pass
    out = []
    for p in sorted(glob.glob(os.path.join(tdir, "*.json"))):
        name = os.path.basename(p)[:-5]
        if name == "index":
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(d, dict):          # a few shipped files are bare lists, not graphs
            continue
        text = open(p, encoding="utf-8", errors="replace").read()
        files = sorted({os.path.basename(u) for u in re.findall(r"https://huggingface\.co/[^\s\"')]+", text)
                        if u.lower().endswith(WEIGHT_EXT)})
        classes = sorted({t for t in template_nodes(d) if len(t) < 48 and not re.match(r"^[0-9a-f-]{36}$", t)})
        title, date = idx.get(name, ("", ""))
        out.append({"name": name, "title": title, "date": date, "classes": classes, "files": files,
                    "paid": name.startswith("api_")})
    return out, tdir


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return "%.1f %s" % (n, u)
        n /= 1024.0
    return "%.2f TB" % n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report only; exit 3 if a recent template is unmirrored")
    ap.add_argument("--days", type=int, default=180, help="how far back a template counts as recent (0 = all)")
    a = ap.parse_args()
    if a.days <= 0:
        a.days = 100000

    wfs = our_workflows()
    drv = drivers()
    disk = models_on_disk()
    tpls, tdir = templates()

    our_classes = {c for w in wfs for c in w.get("classes", [])}
    our_files = {f for w in wfs for f in w.get("files", [])}
    used_by = {}
    for w in wfs:
        for f in w.get("files", []):
            used_by.setdefault(f, []).append(w["file"])
    # The review clock's rule, not a looser one: a tool that BUILDS a graph or CASTS a model counts
    # as a user (film_routes, compose, post, the trainers, identity/headbox), as do the LoRA cards,
    # the legacy cast cards and a pack's adopted face. A tool that merely mentions a model does not.
    try:
        sys.path.insert(0, os.path.join(ROOT, "studio", "_tools"))
        import review_clock as rc
        builders = list(getattr(rc, "GRAPH_BUILDERS", ()))
    except Exception:
        builders = []
    extra_sources = [os.path.join(ROOT, b) for b in builders]
    for pat in ("studio/loras/*.json", "studio/characters/*.json", "studio/foundry/*/*/asset.json"):
        extra_sources += glob.glob(os.path.join(ROOT, pat))
    for p in extra_sources:
        try:
            t = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        rel = os.path.relpath(p, ROOT)
        for f in disk:
            if f in t and rel not in used_by.get(f, []):
                used_by.setdefault(f, []).append(rel)

    # ---------------------------------------------------------------- workflows/INDEX.md
    by_fam = {}
    for w in wfs:
        if "error" in w:
            continue
        by_fam.setdefault(family_of(w), []).append(w)
    lines = ["# Workflows - the index", "",
             "*Generated by `studio/_tools/inventory.py` from the files themselves; do not edit by hand.*",
             "*API-format graphs, drivable with `python3 scripts/comfy.py run workflows/<file> -s node.inputs.key=value`.*",
             "", "| # | file | family | drives it | weights it names | what it is |", "|---|---|---|---|---|---|"]
    order = [f for f, _ in FAMILIES] + ["other"]
    for fam in sorted(by_fam, key=lambda f: order.index(f) if f in order else 999):
        for w in sorted(by_fam[fam], key=lambda x: x["file"]):
            key = w["file"][:-5]
            tools = sorted(drv.get(key, set()))
            missing = [f for f in w["files"] if f not in disk]
            weights = ", ".join("`%s`%s" % (f, " **(missing)**" if f in missing else "") for f in w["files"]) or "-"
            paid = " **PAID**" if w["paid"] else ""
            lines.append("| %s | `%s` | %s%s | %s | %s | %s |" % (
                w["file"].split("_")[0], w["file"], fam, paid,
                ", ".join("`%s`" % t for t in tools) or "-", weights,
                (w["comment"][:160] + ("…" if len(w["comment"]) > 160 else "")).replace("|", "\\|")))
    lines += ["", "## Reading the table", "",
              "- **drives it**: a studio tool or script that names the graph. A graph nobody drives is",
              "  either a manual recipe (fine) or a capability nobody has picked up yet (check §96.10).",
              "- **PAID**: a ComfyUI partner node - charges per call and needs the Comfy account token",
              "  the frontend supplies after login. These are wired and switched off by default (§96.4).",
              "- **(missing)**: the graph names a weight that is not on disk. It will fail validation.", ""]
    if not a.check:
        open(os.path.join(WF, "INDEX.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")

    # ---------------------------------------------------------------- docs/MODELS.md
    orphans = sorted((f, m) for f, m in disk.items() if f not in used_by and not m["link"])
    mlines = ["# Models on the box - and who uses them", "",
              "*Generated by `studio/_tools/inventory.py`; sizes from disk, users from the graphs in `workflows/`.*",
              "*Weights are never in git; this is the manifest. Total: %s in %d files.*" % (
                  human(sum(m["size"] for m in disk.values())), len(disk)),
              "", "| folder | file | size | used by |", "|---|---|---|---|"]
    for f, m in sorted(disk.items(), key=lambda kv: (kv[1]["dir"], kv[0])):
        users = ", ".join("`%s`" % u for u in used_by.get(f, [])) or ("*(symlink)*" if m["link"] else "**orphan**")
        mlines.append("| %s | `%s` | %s | %s |" % (m["dir"], f, human(m["size"]), users))
    mlines += ["", "## Orphans - on disk, named by no graph", "",
               "The review clock (playbook §0) lists these too. Each needs a verdict with a date: wire",
               "it, measure it, or say why not.", ""]
    for f, m in orphans:
        mlines.append("- `%s/%s` - %s" % (m["dir"], f, human(m["size"])))
    if not a.check:
        os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
        open(os.path.join(ROOT, "docs", "MODELS.md"), "w", encoding="utf-8").write("\n".join(mlines) + "\n")

    # ---------------------------------------------------------------- the report
    print("%d workflows, %d model files (%s), %d orphans, %d templates in %s" % (
        len(wfs), len(disk), human(sum(m["size"] for m in disk.values())), len(orphans), len(tpls), tdir))
    unmirrored = []
    for t in tpls:
        if t["paid"]:
            continue
        novel_classes = [c for c in t["classes"] if c not in our_classes and not GENERIC.match(c)]
        novel_files = [f for f in t["files"] if f not in our_files and f not in disk]
        if novel_classes or (novel_files and not any(f in disk for f in t["files"] if f.lower().endswith(".safetensors"))):
            unmirrored.append((t, novel_classes, novel_files))
    # The shipped set goes back to 2025's SD3.5 and SVD examples; what a review needs is what
    # arrived SINCE the engines in use were chosen. Recent ones in full, the rest as a count.
    import datetime as dt
    cutoff = (dt.date.today() - dt.timedelta(days=a.days)).isoformat()
    recent = [x for x in unmirrored if x[0]["date"] >= cutoff]
    older = [x for x in unmirrored if x[0]["date"] < cutoff]
    print("\nTEMPLATES SHIPPED WITH THIS COMFYUI THAT NO WORKFLOW HERE MIRRORS - dated since %s (local weights only):" % cutoff)
    for t, nc, nf in sorted(recent, key=lambda x: x[0]["date"], reverse=True):
        print("  %-52s %-10s %s" % (t["name"][:52], t["date"], t["title"][:40]))
        if nc:
            print("      new node classes: %s" % ", ".join(nc[:6]))
        if nf:
            print("      weights not on disk: %s" % ", ".join(nf[:4]))
    print("\n%d recent unmirrored; %d older ones (--days 0 lists everything). A template on this list is a "
          "capability the box could have and does not." % (len(recent), len(older)))
    if a.check and recent:
        sys.exit(3)


if __name__ == "__main__":
    main()
