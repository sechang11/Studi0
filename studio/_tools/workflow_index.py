#!/usr/bin/env python3
"""studio/_tools/workflow_index.py - the workflow library: what each graph is and does.

    python3 studio/_tools/workflow_index.py

45 graphs sit in workflows/ and until now the only way to know what one was, was to open
the JSON. This reads each one and reports what can be known without opening it: how many
nodes, which models it loads, which capability claims it, which code runs it, and whether
it is reachable at all.

FORMAT MATTERS AND IS REPORTED. These are API-format graphs - numeric node ids with a
class_type, the shape ComfyUI's /prompt endpoint accepts. That is not the shape the
ComfyUI EDITOR opens; the editor wants the UI format with its node positions and links.
So the page offers what genuinely works with an API graph - download it, copy it where
ComfyUI can see it, or queue it straight onto the render queue - rather than an "open in
ComfyUI" button that would quietly fail.
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
WF = os.path.join(ROOT, "workflows")
OUT = os.path.join(STUDIO, "samples", "_workflows.json")
WEIGHT = re.compile(r"\.(safetensors|gguf|pt|bin|sft|ckpt|pth|onnx)$", re.I)

# what a graph is FOR, inferred from the classes it uses - crude, and only used as a
# hint beside the real facts
HINTS = [("video", ("LTXV", "WanImageToVideo", "HunyuanVideo", "VHS_", "SaveWEBM",
                    "CreateVideo", "SaveVideo")),
         ("audio", ("EmptyLatentAudio", "SaveAudio", "ACEStep", "TTS", "VoiceClone")),
         ("3d", ("Hunyuan3D", "TripoS", "VoxelTo", "SaveGLB")),
         ("image", ("KSampler", "EmptyLatentImage", "SaveImage", "VAEDecode"))]


def describe(path):
    try:
        g = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return {"error": str(e)}
    if not isinstance(g, dict):
        return {"error": "not an object"}
    # API format means "there are nodes in node shape", not "the first key looks like a
    # number". Most of these graphs open with a `_comment` holding their own docs, and
    # testing the first five keys put a false "not API format" warning on 40 of 45.
    nodes = {k: v for k, v in g.items()
             if not str(k).startswith("_") and isinstance(v, dict)}
    api = any(str(k).isdigit() and "class_type" in v for k, v in nodes.items())
    classes, models = {}, set()
    for node in nodes.values():
        if not isinstance(node, dict):
            continue
        ct = node.get("class_type")
        if ct:
            classes[ct] = classes.get(ct, 0) + 1
        for v in (node.get("inputs") or {}).values():
            if isinstance(v, str) and WEIGHT.search(v):
                models.add(v)
    kind = "other"
    for k, keys in HINTS:
        if any(any(c.startswith(x) or x in c for x in keys) for c in classes):
            kind = k
            break
    return {"api_format": api, "nodes": len(nodes), "models": sorted(models),
            "notes": g.get("_comment") if isinstance(g.get("_comment"), str) else None,
            "classes": sorted(classes, key=lambda c: -classes[c])[:8], "kind": kind}


def main():
    # who claims each graph, from the catalogue
    claimed, used_by = {}, {}
    try:
        cat = json.load(open(os.path.join(STUDIO, "capabilities.json"), encoding="utf-8"))
        for c in cat.get("capabilities") or []:
            for w in (c.get("workflows") or []):
                fn = w.get("file") if isinstance(w, dict) else str(w)
                if fn:
                    claimed[fn] = c.get("id")
                    if isinstance(w, dict) and w.get("used_by"):
                        used_by[fn] = w["used_by"]
    except Exception:
        pass
    # and who runs it, from the code, for the ones the catalogue does not mention
    src = []
    for pat in ("scripts/*.py", "studio/*.py", "studio/_tools/*.py"):
        for p in glob.glob(os.path.join(ROOT, pat)):
            try:
                src.append((os.path.relpath(p, ROOT),
                            open(p, encoding="utf-8", errors="ignore").read()))
            except OSError:
                pass

    rows = []
    for p in sorted(glob.glob(os.path.join(WF, "*.json"))):
        fn = os.path.basename(p)
        d = describe(p)
        runners = used_by.get(fn) or [rp for rp, t in src if fn in t]
        rows.append(dict(file=fn, size_kb=round(os.path.getsize(p) / 1024, 1),
                         capability=claimed.get(fn), used_by=sorted(set(runners)),
                         **d))
    doc = {
        "generated": __import__("time").strftime("%Y-%m-%d %H:%M"),
        "generator": "studio/_tools/workflow_index.py",
        "note": ("Every graph in workflows/, read rather than guessed at. These are "
                 "API-format graphs - the shape ComfyUI's /prompt endpoint accepts, not "
                 "the shape its editor opens - so the actions offered are download, copy "
                 "to ComfyUI's folder, and queue, which all work on this format."),
        "comfy_url": os.environ.get("COMFY_URL", "http://127.0.0.1:8188"),
        "workflows": rows,
        "totals": {"workflows": len(rows),
                   "claimed": sum(1 for r in rows if r.get("capability")),
                   "run_by_code": sum(1 for r in rows if r.get("used_by")),
                   "orphan": sum(1 for r in rows
                                 if not r.get("capability") and not r.get("used_by"))},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(doc, open(OUT, "w", encoding="utf-8"), indent=1)
    t = doc["totals"]
    print("%d workflows · %d claimed by a capability · %d run by code · %d neither"
          % (t["workflows"], t["claimed"], t["run_by_code"], t["orphan"]))
    for r in rows:
        if not r.get("capability") and not r.get("used_by"):
            print("   orphan: %-34s %2d nodes  %s" % (r["file"], r.get("nodes", 0),
                                                      r.get("kind")))
    print("-> %s" % OUT)
    return 0


def main_quiet():
    import contextlib
    import io as _io
    with contextlib.redirect_stdout(_io.StringIO()):
        return main()


if __name__ == "__main__":
    sys.exit(main())
