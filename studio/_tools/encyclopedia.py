#!/usr/bin/env python3
"""studio/_tools/encyclopedia.py - one reference joining capabilities, workflows, models.

    python3 studio/_tools/encyclopedia.py            # build + print coverage
    python3 studio/_tools/encyclopedia.py --quiet    # build only

WHY THIS EXISTS. The studio knows three things about itself and keeps them in three
places that never meet:

    35 capabilities   studio/capabilities.json   what the box can do, in prose
    45 workflows      workflows/*.json           the graphs that actually do it
    52 model cards    studio/models/*.json       the weights those graphs load

Every link between them already exists in the data - a capability names its workflows, a
workflow's nodes name their model files, a model card knows its filename. Nothing had
ever walked the chain. That is how LTX-2.5 sat verified-and-unpublished, and how four of
its model cards still said "gated download pending" while a workflow was loading them.

WHAT IT JOINS, and the direction matters. The chain is walked FORWARD from capability to
workflow to model, and then BACKWARD to find what nothing reaches:

    orphan workflows   a graph on disk that no capability claims
    orphan models      a card whose weights no workflow loads

Both are legitimate - a workflow can be scratch, a model can be a dependency of a node
rather than a graph - but they should be a decision, not a surprise.

MODEL RESOLUTION IS BY FILENAME, and that is deliberate. Card ids use underscores and
filenames use hyphens (ltx_2_5_video_vae_bf16 vs ltx-2.5-video-vae-bf16.safetensors);
matching on the id is what produced three confident wrong answers in one night. This
matches on the `file` field the cards already carry, and reports anything a workflow
loads that no card describes.
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
OUT = os.path.join(STUDIO, "samples", "_encyclopedia.json")

WEIGHT = re.compile(r"\.(safetensors|gguf|pt|bin|sft|ckpt|pth|onnx)$", re.I)


def model_files(wf_path):
    """Every weights filename a workflow loads, from its node inputs."""
    try:
        g = json.load(open(wf_path, encoding="utf-8"))
    except Exception:
        return []
    out = set()
    for node in (g.values() if isinstance(g, dict) else []):
        if not isinstance(node, dict):
            continue
        for v in (node.get("inputs") or {}).values():
            if isinstance(v, str) and WEIGHT.search(v):
                out.add(v)
    return sorted(out)


def main():
    ap = argparse.ArgumentParser(description="Join capabilities, workflows and models.")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    cat = json.load(open(os.path.join(STUDIO, "capabilities.json"), encoding="utf-8"))
    caps = cat.get("capabilities") or []

    # model cards, indexed the only way that works: by the filename they declare
    by_file, cards = {}, {}
    for p in glob.glob(os.path.join(STUDIO, "models", "*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        cards[d.get("id")] = d
        if d.get("file"):
            by_file[d["file"]] = d

    seen_wf, seen_model = set(), set()
    entries = []
    for c in caps:
        wfs = []
        for w in (c.get("workflows") or []):
            fn = w.get("file") if isinstance(w, dict) else str(w)
            if not fn:
                continue
            seen_wf.add(fn)
            path = os.path.join(ROOT, "workflows", fn)
            mods = []
            for f in model_files(path):
                card = by_file.get(f)
                if card:
                    seen_model.add(card.get("id"))
                mods.append({
                    "file": f,
                    "card": card.get("id") if card else None,
                    "status": card.get("status") if card else None,
                    "size_gb": card.get("size_gb") if card else None,
                    "engine": card.get("engine") if card else None,
                })
            wfs.append({"file": fn, "exists": os.path.exists(path),
                        "used_by": (w.get("used_by") or []) if isinstance(w, dict) else [],
                        "models": mods})
        entries.append({
            "id": c.get("id"), "number": c.get("number"), "name": c.get("name"),
            "what_it_does": c.get("what_it_does"), "why_it_matters": c.get("why_it_matters"),
            "status": c.get("status"), "verdict": c.get("verdict"),
            "model": c.get("model"), "vram": c.get("vram"), "cost": c.get("cost"),
            "released": c.get("released"),
            "exposure": c.get("exposure"), "app_page": c.get("app_page"),
            "strong": c.get("strong"), "weak": c.get("weak"), "limits": c.get("limits"),
            "alternatives": c.get("alternatives"), "next_steps": c.get("next_steps"),
            "sample": c.get("sample"),
            "workflows": wfs,
            "gb": round(sum(m["size_gb"] or 0 for w in wfs for m in w["models"]), 1),
        })

    entries.sort(key=lambda e: str(e.get("number") or "zz"))

    on_disk = sorted(os.path.basename(p)
                     for p in glob.glob(os.path.join(ROOT, "workflows", "*.json")))
    orphan_wf = []
    for fn in on_disk:
        if fn in seen_wf:
            continue
        mods = model_files(os.path.join(ROOT, "workflows", fn))
        orphan_wf.append({"file": fn, "models": mods})
    # Every model any workflow on disk loads, INCLUDING the ones no capability claims.
    # Without this pass a card is called orphaned when it is really its workflow that is
    # undeclared - the first run of this tool said animagine_xl_4_0 was loaded by nothing.
    reached_any, unclaimed_only = set(), {}
    for fn in on_disk:
        for f in model_files(os.path.join(ROOT, "workflows", fn)):
            card = by_file.get(f)
            if not card:
                continue
            reached_any.add(card.get("id"))
            if fn not in seen_wf:
                unclaimed_only.setdefault(card.get("id"), []).append(fn)
    orphan_models = sorted(cid for cid in cards if cid and cid not in reached_any)
    # loaded, but only through a workflow that no capability declares
    via_unclaimed = sorted(cid for cid in unclaimed_only if cid not in seen_model)

    doc = {
        "generated": __import__("time").strftime("%Y-%m-%d %H:%M"),
        "generator": "studio/_tools/encyclopedia.py",
        "note": ("One reference over three libraries that never met: capabilities say "
                 "what the box can do, workflows are the graphs that do it, model cards "
                 "are the weights they load. Models resolve BY FILENAME, because card "
                 "ids use underscores and files use hyphens."),
        "capabilities": entries,
        "orphan_workflows": orphan_wf,
        "orphan_models": orphan_models,
        "models_via_unclaimed_workflow": {k: unclaimed_only[k] for k in via_unclaimed},
        "totals": {"capabilities": len(entries), "workflows_on_disk": len(on_disk),
                   "workflows_claimed": len(seen_wf), "model_cards": len(cards),
                   "models_reached": len(seen_model)},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(doc, open(OUT, "w", encoding="utf-8"), indent=1)

    if a.quiet:
        return 0
    t = doc["totals"]
    print("capabilities %d   workflows %d on disk, %d claimed by a capability"
          % (t["capabilities"], t["workflows_on_disk"], t["workflows_claimed"]))
    print("model cards  %d   %d via a declared capability, %d only via an "
          "undeclared workflow, %d by no workflow at all"
          % (t["model_cards"], t["models_reached"], len(via_unclaimed),
             len(orphan_models)))
    unknown = sorted({m["file"] for e in entries for w in e["workflows"]
                      for m in w["models"] if not m["card"]})
    if unknown:
        print("\n%d weights loaded by a workflow with NO model card:" % len(unknown))
        for f in unknown[:12]:
            print("   %s" % f)
    if orphan_wf:
        print("\n%d workflows no capability claims:" % len(orphan_wf))
        for w in orphan_wf[:12]:
            print("   %-34s %d weights" % (w["file"], len(w["models"])))
    if via_unclaimed:
        print("\n%d model cards reached ONLY through a workflow with no capability "
              "(the workflow needs declaring, not the model):" % len(via_unclaimed))
        for cid in via_unclaimed[:10]:
            print("   %-38s <- %s" % (cid, ", ".join(unclaimed_only[cid][:2])))
    if orphan_models:
        print("\n%d model cards NO workflow loads:" % len(orphan_models))
        print("   " + ", ".join(orphan_models[:10]))
    print("\n-> %s" % OUT)
    return 0


def main_quiet():
    """Rebuild the index without printing. Used by serve.py per request."""
    import contextlib
    import io as _io
    with contextlib.redirect_stdout(_io.StringIO()):
        sys.argv = [sys.argv[0], "--quiet"]
        return main()


if __name__ == "__main__":
    sys.exit(main())
