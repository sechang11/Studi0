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
    ("wear", "Wear rung (0 clean - 4 ruined)"),
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


# The card libraries a facet browses into. A facet is a recipe field; a KIND is the folder
# of cards that field names. Browsing by kind answers "what looks do I own", which the item
# grid cannot: the grid shows generations, and one look with 300 frames drowns one with 3.
KINDS = {"model": "models",
         "look": "looks", "place": "places", "style": "styles", "emotion": "emotions",
         "character": "characters", "motion": "motions", "camera": "cameras"}
FAVS = os.path.join(STUDIO, "favourites.json")


def favourites():
    try:
        return set(json.load(open(FAVS, encoding="utf-8")).get("ids") or [])
    except Exception:
        return set()


def star(item_id, on=True):
    """Starring is a plain id list on disk. No database, and no per-user anything - one
    person uses this box. Written whole each time because the file is a few kilobytes and a
    partial write of a favourites list is a worse problem than rewriting it."""
    ids = favourites()
    if on:
        ids.add(item_id)
    else:
        ids.discard(item_id)
    with open(FAVS, "w", encoding="utf-8") as f:
        json.dump({"ids": sorted(ids)}, f, indent=1)
    return {"id": item_id, "starred": on, "total": len(ids)}


REJECTED = os.path.join(SAMPLES, "_rejected")

# Which axes make a SET for each kind, in the order a person wants to see them. Framing
# first for a character because "does the face hold at a wide" is the first question; the
# clean plate first for a place because that is the only view that is actually the place.
SET_AXES = {
    "character": [("framing", 4), ("style", 6), ("place", 8)],
    "place": [("pure", 3), ("style", 3), ("look", 4)],
    "style": [("pure", 1), ("place", 4)],
    "emotion": [("pure", 2), ("style", 2)],
    "motion": [("style", 3)],
    "camera": [("style", 3)],
}

# NAMED SLOTS, so a set means the SAME THING for every card of a kind.
#
# The greedy cover gave each character whatever four framings it happened to own, in
# whatever order they were newest. Two characters side by side were therefore not
# comparable - one led with a close-up, the other with a wide, and a missing angle looked
# identical to an angle that simply sorted late. Fixed slots make the shape of a set a
# property of the KIND rather than of the card's render history, and a slot nobody filled
# comes back EMPTY instead of silently shrinking the set.
FIXED_SLOTS = {
    "character": (
        [("framing", v) for v in ("close-up", "medium close-up", "medium shot", "wide shot")]
        + [("style", None)] * 6
        + [("place", None)] * 8
    ),
    "place": [("pure", None)] * 3 + [("style", None)] * 3 + [("look", None)] * 4,
    "style": [("pure", None)] + [("place", None)] * 4,
    "emotion": [("pure", None)] * 2 + [("style", None)] * 2,
    "motion": [("style", None)] * 3,
    "camera": [("style", None)] * 3,
}


def packset(facet, value):
    """The frames that make a COMPLETE SET for one card, in order, then everything else.

    Greedy cover: walk the axes in order and take the frame that adds a value not yet
    represented, preferring the purest and then the newest. The result is that the first
    handful of pictures ARE the set - every framing, then a spread of styles, then a spread
    of places - rather than a wall sorted by one number where four close-ups sit at the top
    because they happened to be cleanest.

    Anything not needed for the cover comes after, in any order, because at that point it
    is extra rather than evidence.
    """
    axes = SET_AXES.get(facet)
    if not axes:
        return None
    d = payload()
    its = [x for x in d["items"] if str(x.get(facet) or "") == str(value)]
    if not its:
        return {"facet": facet, "value": value, "set": [], "extra": [], "axes": []}
    its.sort(key=lambda x: ((x.get("purity") or {}).get(facet, 9), -x["mtime"]))

    # Walk the FIXED slot list. A slot with a named value takes only that value; an
    # unnamed one takes the next value on that axis not already used. Either way slot n
    # means the same thing for every card of this kind, and an unfillable slot stays empty
    # rather than being quietly dropped.
    slots = FIXED_SLOTS.get(facet) or [(a, None) for a, n in axes for _ in range(n)]
    chosen, seen_ids, used = [], set(), {}
    for axis, want in slots:
        used.setdefault(axis, set())
        pick = None
        for it in its:
            if it["id"] in seen_ids:
                continue
            if axis == "pure":
                if (it.get("purity") or {}).get(facet) != 0:
                    continue
                pick, key, why = it, it["id"], "nothing else in the frame"
                break
            v = it.get(axis)
            if not v:
                continue
            if want is not None:
                if v != want:
                    continue
            elif v in used[axis]:
                continue
            pick, key, why = it, v, "%s: %s" % (axis, v)
            break
        if pick is None:
            chosen.append({"id": None, "url": None, "kind": None, "axis": axis,
                           "why": ("%s: %s" % (axis, want)) if want else axis,
                           "empty": True})
            continue
        used[axis].add(key)
        seen_ids.add(pick["id"])
        chosen.append({"id": pick["id"], "url": pick["url"], "kind": pick["kind"],
                       "axis": axis, "why": why, "empty": False})
    extra = [x for x in its if x["id"] not in seen_ids]
    filled = [c for c in chosen if not c.get("empty")]
    per = {}
    for c in chosen:
        per.setdefault(c["axis"], [0, 0])
        per[c["axis"]][1] += 1
        if not c.get("empty"):
            per[c["axis"]][0] += 1
    return {"facet": facet, "value": value,
            "set": chosen, "slots": len(chosen), "filled": len(filled),
            "empty_slots": [c["why"] for c in chosen if c.get("empty")],
            "extra_count": len(extra),
            "extra_ids": [x["id"] for x in extra],
            "axes": [{"axis": a, "want": v[1], "got": v[0]} for a, v in per.items()],
            "complete": len(filled) == len(chosen)}


# WHY A LIST AND NOT A TEXT BOX. A typed reason is a note; a chosen reason is DATA. Once
# every rejection carries the same handful of slugs they can be counted and crossed against
# the recipe - "subject_missing happens at wide shot four times as often as at close-up" is
# a fact the library can find on its own, and free text never will be.
#
# Each one names a FIX, not a feeling. "ugly" is deliberately last and deliberately vague,
# because a bucket for "I just don't want it" stops people forcing a real reason onto a
# frame that simply is not good.
REASONS = [
    ("subject_missing", "Character tagged but not in frame",
     "the recipe names a character and nobody is there - usually the framing or the place "
     "opened up too wide for a person to survive"),
    ("wrong_subject", "Wrong person, or two of them",
     "a different face than the card, or the duplicate-subject leak"),
    ("place_not_recognisable", "Place did not render",
     "the place card's nouns did not arrive - it could be anywhere"),
    ("style_not_landed", "Style did not land",
     "looks like the no-style control, or like a different style entirely"),
    ("framing_wrong", "Framing is not what was asked",
     "asked for a wide and got a close-up, or the reverse"),
    ("occluded", "Subject blocked by something",
     "an object across the frame - the painting over the train carriage"),
    ("text_garbled", "Lettering is gibberish",
     "for the typography cards: the quoted string did not come out"),
    ("anatomy", "Hands, face or body broken", "the usual failure"),
    ("emotion_not_read", "Expression is not the emotion",
     "the face is doing something else, or nothing"),
    ("motion_wrong", "Clip does not do what the motion says",
     "for video: the movement is not the shape the card claims"),
    ("ugly", "Just not good enough",
     "nothing structurally wrong, it is simply not worth keeping"),
]


def reject_report():
    """What gets rejected, and what it correlates with.

    This is the point of the slugs. For each reason it reports the recipe fields that show
    up disproportionately - so a pattern like "subject_missing is mostly wide shots in
    open places" surfaces without anyone going looking for it.
    """
    import collections
    rows = []
    for f in glob.glob(os.path.join(REJECTED, "**", "*.json"), recursive=True):
        try:
            rows.append(json.load(open(f, encoding="utf-8")))
        except Exception:
            pass
    if not rows:
        return {"total": 0, "reasons": [], "note": "nothing rejected yet"}

    base = collections.Counter()
    for it in payload()["items"]:
        for k in ("framing", "place", "style", "character", "engine"):
            if it.get(k):
                base["%s=%s" % (k, it[k])] += 1
    n_lib = max(1, payload()["total"])

    out = []
    by_reason = collections.defaultdict(list)
    for r in rows:
        by_reason[r.get("rejected_reason") or "unspecified"].append(r)
    for slug, rs in sorted(by_reason.items(), key=lambda kv: -len(kv[1])):
        c = collections.Counter()
        for r in rs:
            for k in ("framing", "place", "style", "character", "engine"):
                if r.get(k):
                    c["%s=%s" % (k, r[k])] += 1
        # Lift: how much more common a field is among these rejections than in the library.
        lift = []
        for key, cnt in c.most_common(20):
            share = cnt / len(rs)
            libshare = base.get(key, 0) / n_lib
            if libshare > 0 and share > libshare * 1.8 and cnt >= 2:
                lift.append({"field": key, "in_rejects": round(share * 100),
                             "in_library": round(libshare * 100, 1),
                             "times": round(share / libshare, 1)})
        out.append({"reason": slug, "count": len(rs), "over_represented": lift[:6]})
    return {"total": len(rows), "reasons": out}


def reject(rel, reason="", note=""):
    """Move a frame out of the library. MOVED, never deleted.

    A picture you reject is evidence: "the train carriage place puts a painting across half
    the frame" is a fact about that card worth keeping, and it is gone forever if the file
    is unlinked. So the media and its recipe go to samples/_rejected/ with the reason and a
    timestamp written into the recipe, the index stops showing it, and it can be put back.

    The same argument as keeping .orig beside a normalised effect: a change you cannot undo
    is a change you cannot check.
    """
    src = os.path.normpath(os.path.join(STUDIO, rel))
    if not os.path.abspath(src).startswith(os.path.abspath(SAMPLES)):
        return None
    if not os.path.isfile(src):
        return None
    stem = os.path.splitext(src)[0]
    d = os.path.join(REJECTED, time.strftime("%Y%m%d"))
    os.makedirs(d, exist_ok=True)
    moved = []
    for p in (src, stem + ".json"):
        if not os.path.isfile(p):
            continue
        dst = os.path.join(d, os.path.basename(p))
        n = 1
        while os.path.exists(dst):
            b, e = os.path.splitext(os.path.basename(p))
            dst = os.path.join(d, "%s_%d%s" % (b, n, e))
            n += 1
        if p.endswith(".json"):
            try:
                r = json.load(open(p, encoding="utf-8"))
                r["rejected_reason"] = reason
                if note:
                    r["rejected_note"] = note
                r["rejected_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                r["rejected_from"] = rel
                json.dump(r, open(dst, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
                os.remove(p)
                moved.append(dst)
                continue
            except Exception:
                pass
        os.replace(p, dst)
        moved.append(dst)
    # The cache is now wrong about a file that is no longer there. Drop it rather than let
    # the page keep offering a 404.
    try:
        os.remove(CACHE)
    except OSError:
        pass
    return {"id": rel, "moved": len(moved), "to": os.path.relpath(d, STUDIO),
            "reason": reason}


def browse(kind):
    """One representative frame per CARD of this kind, plus the alternates.

    Every card is returned, INCLUDING ones with no frame at all. A browse view that hides
    the cards it has no picture for would quietly under-report the library and hide exactly
    the gap worth filling.

    The representative is the purest frame - the one where this card is most alone - then
    the newest among equals. `alts` carries the next few so the page can rotate through
    them rather than pretending one seed is the whole card.
    """
    facet = next((f for f, d in KINDS.items() if d == kind or f == kind), None)
    if not facet:
        return None
    folder = KINDS[facet]
    d = payload()
    by = {}
    for it in d["items"]:
        v = it.get(facet)
        if v in (None, ""):
            continue
        by.setdefault(str(v), []).append(it)

    out = []
    for p in sorted(glob.glob(os.path.join(STUDIO, folder, "*.json"))):
        base = os.path.basename(p)
        if base.startswith("_"):
            continue
        try:
            card = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        cid = card.get("id") or base[:-5]
        frames = sorted(by.get(cid, []),
                        key=lambda x: ((x.get("purity") or {}).get(facet, 9), -x["mtime"]))
        out.append({
            "id": cid,
            "name": card.get("name") or cid.replace("_", " "),
            "desc": (card.get("desc") or card.get("means") or card.get("prose") or "")[:180],
            "status": card.get("status") or "",
            "frames": len(frames),
            "purest": ((frames[0].get("purity") or {}).get(facet) if frames else None),
            "cover": frames[0]["url"] if frames else None,
            "cover_id": frames[0]["id"] if frames else None,
            "alts": [f["url"] for f in frames[1:6]],
            "alt_ids": [f["id"] for f in frames[1:6]],
            # Model cards are read, not glanced at - the browse view renders the whole
            # card face (role, dialect, size, reachability), so it travels along.
            "card": card if folder == "models" else None,
        })
    # Cards with nothing to show sort last, but they are still on the page - that is the
    # coverage gap, and it is the thing worth acting on.
    out.sort(key=lambda c: (c["cover"] is None, c["purest"] if c["purest"] is not None else 9,
                            -c["frames"]))
    return {"kind": folder, "facet": facet, "cards": out,
            "total": len(out), "empty": sum(1 for c in out if not c["cover"])}


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
        if base.startswith("_") or "/_rejected/" in rp.replace("\\", "/"):
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
                  "framing", "motion", "camera", "seed", "width", "height", "prompt",
                  "wear"):
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
        # How many CARDS exist per kind, which is what the sidebar promises when you click
        # it. The facet counts below are distinct values PRESENT IN FRAMES - 9 motions have
        # been used, 34 motions exist - and showing the smaller number next to a link that
        # opens the larger list is a small lie repeated on every page load.
        "kind_counts": {f: len([x for x in glob.glob(os.path.join(STUDIO, d, "*.json"))
                                if not os.path.basename(x).startswith("_")])
                        for f, d in KINDS.items()},
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
    # frame_check (Gemma-4 VLM description vs the recipe's nouns) - "how do I know the
    # image is doing what it is supposed to?" answered by an instrument, right under the
    # prompt: what the model SAW, and whether the asked-for nouns were in it.
    fc = r.get("frame_check")
    if isinstance(fc, dict):
        fields.insert(1, {"key": "frame_check_desc", "label": "What a VLM saw",
                          "value": fc.get("description", "")})
        fields.insert(2, {"key": "frame_check_seen",
                          "label": "Asked-for nouns seen",
                          "value": ("yes: " + ", ".join(fc.get("hits") or []))
                                   if fc.get("seen") else
                                   "NO - none of %s" % ", ".join(
                                       (fc.get("expect") or [])[:5])})
    shown = {k for k, _ in DETAIL} | {"frame_check"}
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
        # 12_ltx23_i2v_audio.json is what render_job.render_video actually loads
        # (render_job.py:207). This said 11_ltx23_i2v.json, which does not exist - so the
        # workflow panel named a ghost file for every video in the library.
        out["file"] = {"video": "12_ltx23_i2v_audio.json"}.get(dom) or "see studio/domains/"
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
