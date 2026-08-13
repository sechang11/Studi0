#!/usr/bin/env python3
"""studio/_tools/library_index.py - every generation on disk, categorised.

    python3 studio/_tools/library_index.py                 a human summary
    python3 studio/_tools/library_index.py --build         (re)build the cache
    python3 studio/_tools/library_index.py --json          the payload /library reads

DISCOVERY, NOT A MANIFEST. /gallery reads studio/gallery/manifest.jsonl, an append-only
file a writer must remember to append to. It holds 1,828 lines; there are 3,612 media files
on disk with a recipe beside them. HALF THE LIBRARY WAS INVISIBLE - not lost, just never
registered, which is the quiet failure a manifest always eventually has.

So this walks studio/samples/ and pairs each recipe JSON with the media file of the same
stem. A run that writes its recipes correctly is indexed with no edit here, the same
contract model3d_index uses. Nothing needs to remember anything.

THE CACHE IS A CACHE, NOT THE TRUTH. Walking 3,600 pairs and stat-ing each takes a few
seconds, so the result is written to studio/samples/_library.json. It is rebuilt whenever
the newest recipe on disk is newer than the cache, so a fresh generation shows up on a
refresh rather than on a restart - and a stale cache can never outlive the thing it
describes.

CATEGORIES COME FROM THE RECIPES, NOT FROM A LIST HERE. Every facet below is collected by
reading what the recipes actually contain. Hardcoding the style names would mean this file
needs editing every time a card is authored, and would silently drop anything new.
"""
import argparse, glob, json, os, time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
SAMPLES = os.path.join(STUDIO, "samples")
CACHE = os.path.join(SAMPLES, "_library.json")

MEDIA = [".webp", ".png", ".jpg", ".jpeg", ".mp4", ".webm", ".mp3", ".wav", ".flac"]
KIND = {".webp": "image", ".png": "image", ".jpg": "image", ".jpeg": "image",
        ".mp4": "video", ".webm": "video",
        ".mp3": "audio", ".wav": "audio", ".flac": "audio"}

# The facets a person actually browses by. Each maps to a recipe field.
FACETS = ["domain", "engine", "style", "character", "place", "look", "emotion",
          "framing", "motion", "camera", "collection"]

# Recipe fields worth showing in full on the detail panel, in reading order. The prompt
# first, because that is what everyone came for.
DETAIL = [
    ("prompt", "Prompt"), ("negative", "Negative"),
    ("engine", "Engine"), ("engine_reason", "Why this engine"),
    ("style", "Style"), ("style_lora", "Style LoRA"),
    ("style_lora_strength", "Style LoRA strength"),
    ("character", "Character"), ("character_lora", "Character LoRA"),
    ("character_lora_strength", "Character LoRA strength"),
    ("character_lora_reason", "LoRA note"),
    ("place", "Place"), ("look", "Look"), ("emotion", "Emotion"),
    ("framing", "Framing"), ("framing_from", "Framing came from"),
    ("motion", "Motion"), ("motion_text", "Motion text"), ("camera", "Camera"),
    ("seed", "Seed"), ("width", "Width"), ("height", "Height"),
    ("seconds", "Seconds"), ("seconds_taken", "Render seconds"),
    ("bpm", "BPM"), ("key", "Key"), ("voice", "Voice"), ("line", "Line"),
    ("self_contained", "Self-contained style"),
    ("luma", "Mean luma"), ("sat", "Mean saturation"),
    ("rolled_at", "Rolled at"), ("id", "Job id"),
]


def _newest_recipe():
    newest = 0.0
    for p in glob.iglob(os.path.join(SAMPLES, "**", "*.json"), recursive=True):
        if os.path.basename(p).startswith("_"):
            continue
        try:
            newest = max(newest, os.path.getmtime(p))
        except OSError:
            pass
    return newest


# The layers that COMPETE for a frame. A card is best understood in a picture where as few
# of these as possible are also present - a place with nobody in it, a character against
# nothing. Style is not here: every image has one and it cannot be removed, so counting it
# would score every item identically and say nothing.
COMPETING = ["character", "place", "look", "emotion", "motion", "camera"]


def purity(item, facet):
    """How ALONE the given facet is in this picture. 0 = nothing else competing.

    This is the sort key behind "just the place" / "just the character". A place with a
    character, a mood grade and a camera move in it teaches you almost nothing about the
    place; the same place empty teaches you everything it can.

    Framing is deliberately not counted. A close-up of a character is not a less pure view
    of them than a wide - it is a different view, and the whole point of a character's own
    set is to see them at several scales.
    """
    n = 0
    for k in COMPETING:
        if k == facet:
            continue
        if item.get(k) not in (None, "", "static"):
            n += 1
    return n


def _made_at(recipe, fallback):
    """Creation time from the recipe, falling back to the file's mtime."""
    v = recipe.get("rolled_at") or recipe.get("created")
    if isinstance(v, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return int(time.mktime(time.strptime(v[:19], fmt)))
            except ValueError:
                pass
    return int(fallback)


def scan():
    items, facets = [], {f: {} for f in FACETS}
    for rp in glob.iglob(os.path.join(SAMPLES, "**", "*.json"), recursive=True):
        base = os.path.basename(rp)
        if base.startswith("_"):
            continue
        stem = rp[:-5]
        media = None
        for ext in MEDIA:
            if os.path.isfile(stem + ext):
                media = stem + ext
                break
        if not media:
            continue                      # a report or a card, not a generation
        try:
            r = json.load(open(rp, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(r, dict) or not r.get("prompt"):
            continue                      # no recipe, nothing to show

        rel = os.path.relpath(media, STUDIO).replace("\\", "/")
        # The run that produced it - samples/<collection>/... - which is the one facet the
        # recipes do not carry and the most useful way to find "that wuxia batch".
        parts = os.path.relpath(media, SAMPLES).replace("\\", "/").split("/")
        collection = parts[0] if len(parts) > 1 else "loose"
        ext = os.path.splitext(media)[1].lower()
        try:
            st = os.stat(media)
        except OSError:
            continue
        it = {
            "id": rel,
            "url": "/samples/" + os.path.relpath(media, SAMPLES).replace("\\", "/"),
            "recipe_url": "/api/library/recipe?id=" + rel,
            "kind": KIND.get(ext, "other"),
            "collection": collection,
            # WHEN IT WAS MADE, not when the file was last touched. Normalising the SFX
            # library rewrote every effect, which pushed 120 grey audio tiles to the top of
            # a newest-first view and buried 2,000 pictures. mtime answers "when did a
            # process last write this"; rolled_at answers the question actually being asked.
            "bytes": st.st_size, "mtime": _made_at(r, st.st_mtime),
            "file_mtime": int(st.st_mtime),
            "name": os.path.basename(stem),
        }
        for k in ("domain", "engine", "style", "character", "place", "look", "emotion",
                  "framing", "motion", "camera", "seed", "width", "height", "prompt"):
            if r.get(k) not in (None, ""):
                it[k] = r[k]
        it.setdefault("domain", it["kind"])
        # Precomputed here rather than in the browser: it is a handful of integers, and the
        # page already ships 4 MB without adding a loop over 3,600 items per keystroke.
        it["purity"] = {f: purity(it, f) for f in
                        ("character", "place", "style", "look", "emotion", "motion")}
        items.append(it)
        for f in FACETS:
            v = it.get(f) if f != "collection" else collection
            if v not in (None, ""):
                facets[f][str(v)] = facets[f].get(str(v), 0) + 1

    items.sort(key=lambda x: -x["mtime"])
    return {
        "items": items,
        "facets": {f: dict(sorted(v.items(), key=lambda kv: -kv[1])) for f, v in
                   facets.items() if v},
        "total": len(items),
        "built": int(time.time()),
        "newest_recipe": int(_newest_recipe()),
    }


def payload(force=False):
    """Cached, but never staler than the newest recipe on disk."""
    if not force and os.path.isfile(CACHE):
        try:
            d = json.load(open(CACHE, encoding="utf-8"))
            if d.get("newest_recipe", 0) >= int(_newest_recipe()):
                return d
        except Exception:
            pass
    d = scan()
    try:
        json.dump(d, open(CACHE, "w", encoding="utf-8"))
    except Exception:
        pass
    return d


def recipe(rel):
    """The full recipe for one item, plus which fields to show and in what order.

    Path is resolved and checked against SAMPLES before anything is opened - the id comes
    from a query string, so it is untrusted input.
    """
    p = os.path.normpath(os.path.join(STUDIO, rel))
    if not os.path.abspath(p).startswith(os.path.abspath(SAMPLES)):
        return None
    stem = os.path.splitext(p)[0]
    rp = stem + ".json"
    if not os.path.isfile(rp):
        return None
    try:
        r = json.load(open(rp, encoding="utf-8"))
    except Exception:
        return None
    fields = [{"key": k, "label": lab, "value": r[k]}
              for k, lab in DETAIL if r.get(k) not in (None, "", [])]
    shown = {k for k, _ in DETAIL}
    extra = {k: v for k, v in r.items()
             if k not in shown and v not in (None, "", []) and k != "file"}
    return {"id": rel, "fields": fields, "extra": extra, "raw": r,
            "workflow_url": "/api/library/workflow?id=" + rel}


# Which workflow file each engine/domain came out of. Recorded here only as the LABEL to
# show; the graph itself is rebuilt by render_job so it cannot drift from what really ran.
WORKFLOW_FILE = {
    "flux2": "40_flux2_t2i.json",
    "qwen": "13_qwen_t2i_styled.json",
    "anime": "22_anime_kf_ipadapter.json",
}


def workflow(rel):
    """The graph that produced this item, rebuilt from its recipe.

    REBUILT BY render_job.image_graph, not copied. A second implementation of the wiring
    would slowly stop matching the one that renders, and a gallery showing a workflow that
    is no longer the workflow is worse than showing none - it looks right.

    Only images can be reconstructed exactly today: video goes keyframe-then-LTX and audio
    is driven by a domain card, so those report the workflow FILE and say plainly that the
    graph is not reconstructed rather than inventing one.
    """
    r = recipe(rel)
    if not r:
        return None
    raw = r["raw"]
    dom = raw.get("domain") or "image"
    eng = raw.get("engine") or "anime"
    out = {"id": rel, "domain": dom, "engine": eng,
           "file": WORKFLOW_FILE.get(eng), "graph": None, "note": ""}
    if dom != "image":
        out["note"] = ("Only image graphs are reconstructed. A video is a keyframe followed "
                       "by an LTX image-to-video pass, and audio is driven by its domain "
                       "card - rebuilding either from the recipe alone would be a guess, so "
                       "the workflow file is named instead.")
        out["file"] = {"video": "11_ltx23_i2v.json"}.get(dom) or "see studio/domains/"
        return out
    import sys
    for p in (TOOLS, os.path.join(ROOT, "scripts")):
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        import render_job
        job = dict(raw)
        job.setdefault("id", os.path.basename(rel))
        out["graph"] = render_job.image_graph(job)
        out["nodes"] = len(out["graph"])
        out["note"] = ("Rebuilt from the recipe by render_job.image_graph - the same "
                       "function that renders, so this is the graph that ran.")
    except Exception as e:                                        # noqa: BLE001
        out["note"] = "could not rebuild the graph: %s: %s" % (type(e).__name__, e)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    d = payload(force=a.build)
    if a.json:
        print(json.dumps(d)[:2000])
        return 0
    print("  %d generations indexed" % d["total"])
    for f, vals in d["facets"].items():
        top = ", ".join("%s(%d)" % (k, v) for k, v in list(vals.items())[:4])
        print("    %-12s %3d distinct   %s" % (f, len(vals), top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
