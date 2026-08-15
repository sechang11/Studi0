#!/usr/bin/env python3
"""frame_check.py - does the frame contain what its recipe says? A VLM answers.

    python3 studio/_tools/frame_check.py --kind places [--limit N] [--only ID]
    python3 studio/_tools/frame_check.py --image X.png --expect "sand dunes, desert"

WHY. The user asked the question directly: "how do I know if the image is doing what it
is supposed to?" The reject taxonomy's top reasons are place_not_recognisable and
subject_missing - both are "the noun the recipe asked for is not in the pixels". Until
now only a human could say. ComfyUI 0.33's TextGenerate + the (ungated) Gemma-4 e2b
encoder is a vision-language model that DESCRIBES a frame in ~2s on core nodes; a
description is checkable text.

HOW (and the measured limitation that shaped it): asked "answer YES or NO, is there
rigging?" the model says NO about a frame it had just described as "prominent rigging" -
the LTX prompt-expander template collapses yes/no. So the instrument never asks yes/no.
It asks for a description and checks the recipe's nouns against it: place card name +
family + the first noun phrases of its tags; character card name/desc nouns. A hit on
any of the place's key nouns = place seen; none = place_not_seen. Synonyms are the weak
point and are stated as such - a MISS is a flag for a human, not a delete.

OUTPUT: per recipe a `frame_check` block written into the recipe JSON beside the frame:
{"seen": true/false, "hits": [...], "description": "...", "model": "gemma4-e2b"}. The
library's reject-reason lift report can read it; nothing is deleted by this tool.
For a kind sweep it also stamps the CARD with MEASURED evidence: N of M isolation
frames describe as the place.
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys
import urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, STUDIO)
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run                       # noqa: E402
from engine import HOST                     # noqa: E402
import cards                                # noqa: E402

COMFY = os.environ.get("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
ENCODER = "gemma4_e2b_it_bf16.safetensors"
STOP = {"the", "a", "an", "of", "in", "on", "at", "and", "with", "no", "humans", "scenery",
        "shot", "close", "up", "medium", "wide", "view", "from", "to", "over", "under",
        "into", "through", "one", "two", "very", "long", "high", "low", "light", "dark",
        "detailed", "background", "foreground", "focus", "quality", "best", "masterpiece"}


def describe(image_path, max_length=90):
    staged = "frame_check_%d.png" % (abs(hash(image_path)) % 100000)
    shutil.copy(image_path, os.path.join(COMFY, "input", staged))
    wf = {
        "1": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": ENCODER, "type": "ltxv", "device": "default"}},
        "2": {"class_type": "LoadImage", "inputs": {"image": staged}},
        "3": {"class_type": "TextGenerate",
              "inputs": {"clip": ["1", 0], "image": ["2", 0],
                         "prompt": "Describe this image in two sentences: the setting, "
                                   "the main objects, and any people.",
                         "max_length": int(max_length), "sampling_mode": "off",
                         "thinking": False, "use_default_template": True}},
        "4": {"class_type": "PreviewAny", "inputs": {"source": ["3", 0]}},
    }
    run(HOST, wf, quiet=True)
    h = json.load(urllib.request.urlopen("http://%s/history" % HOST))
    k = sorted(h, key=lambda x: h[x].get("status", {}).get("completed", 0))[-1]
    try:
        return str(h[k]["outputs"]["4"]["text"][0]).strip()
    except (KeyError, IndexError, TypeError):
        return ""


def nouns_of(*texts, limit=12):
    """Key words from card text: lower-cased tokens minus stopwords, singularised
    crudely (dunes->dune) so a description saying 'dune' still hits 'dunes'."""
    out = []
    for t in texts:
        for w in re.findall(r"[a-z][a-z\-]+", str(t or "").lower()):
            if w in STOP or len(w) < 4:
                continue
            w = w[:-1] if w.endswith("s") and not w.endswith("ss") else w
            if w not in out:
                out.append(w)
    return out[:limit]


# Synonyms the VLM uses for words this place library uses. Grown from misses that were
# LOOKED AT (empty_motorway -> "highway"); every entry should trace to a real false miss.
SYN = {
    "motorway": ("highway", "freeway", "expressway", "road"),
    "carriage": ("train", "railcar", "coach", "compartment", "wagon"),
    "airship": ("ship", "zeppelin", "blimp", "vessel", "dirigible"),
    "courtyard": ("square", "plaza", "quadrangle", "yard"),
    "alley": ("alleyway", "lane", "passage", "backstreet", "street"),
    "tavern": ("pub", "inn", "bar", "saloon"),
    "forest": ("wood", "woodland", "tree"),
    "cliff": ("bluff", "precipice", "rock face", "escarpment"),
    "harbour": ("harbor", "port", "dock", "marina", "wharf", "quay"),
    "shore": ("beach", "coast", "coastline", "seaside"),
    "meadow": ("field", "grassland", "pasture"),
    "lab": ("laboratory",), "laboratory": ("lab",),
    "subway": ("metro", "underground", "station", "platform"),
    "rooftop": ("roof",), "roof": ("rooftop",),
    "stadium": ("arena", "pitch", "field", "stand"),
    "shrine": ("temple",), "temple": ("shrine",),
    "cavern": ("cave",), "cave": ("cavern", "grotto"),
    "dune": ("sand",), "desert": ("sand", "arid"),
    "palace": ("hall", "castle", "manor", "mansion"),
    "castle": ("fortress", "citadel", "keep", "palace"),
    "market": ("bazaar", "stall", "vendor"),
    "night": ("dark", "evening", "nighttime"),
    "snow": ("snowy", "frozen", "ice", "winter"),
    "ruin": ("ruined", "crumbling", "abandoned", "derelict"),
    "spaceship": ("spacecraft", "starship"), "corridor": ("hallway", "hall", "passage"),
    "kitchen": ("stove", "counter"), "bedroom": ("bed",), "attic": ("loft", "rafters"),
    "greenhouse": ("glasshouse", "conservatory"), "library": ("bookshelf", "book"),
    "canyon": ("gorge", "ravine"), "waterfall": ("fall", "cascade"),
    "lighthouse": ("beacon", "tower"), "bridge": ("span", "overpass"),
    "tunnel": ("underpass", "passage"), "funicular": ("cable car", "railway", "tram"),
    "roost": ("nest", "perch", "lair"), "dragon": ("creature", "beast", "wing"),
}


def check(description, expect_words):
    d = description.lower()
    d_words = set(re.findall(r"[a-z][a-z\-]+", d))
    d_stems = {(w[:-1] if w.endswith("s") and not w.endswith("ss") else w) for w in d_words}
    hits = []
    for w in expect_words:
        if w in d_stems or w in d:
            hits.append(w)
            continue
        for s in SYN.get(w, ()):
            if s in d_stems or s in d:
                hits.append("%s~%s" % (w, s))
                break
    return hits


def main():
    ap = argparse.ArgumentParser(description="VLM check: does the frame contain its recipe's nouns?")
    ap.add_argument("--kind", choices=("places", "characters"))
    ap.add_argument("--only")
    ap.add_argument("--limit", type=int, default=0, help="frames per card (0 = all)")
    ap.add_argument("--image")
    ap.add_argument("--expect", help="comma list of words for a single --image check")
    ap.add_argument("--recheck", action="store_true",
                    help="re-judge SAVED descriptions with the current checker; no VLM")
    a = ap.parse_args()

    if a.image:
        desc = describe(a.image)
        want = nouns_of(a.expect or "")
        hits = check(desc, want)
        print(json.dumps({"description": desc, "expect": want, "hits": hits,
                          "seen": bool(hits)}, indent=1))
        return 0
    if not a.kind:
        ap.error("--kind or --image")

    lib = cards.load(a.kind)
    iso = os.path.join(STUDIO, "samples", "isolation", a.kind)
    tally = {"seen": 0, "miss": 0}
    for cid, card in sorted(lib.items()):
        if cid.startswith("_") or (a.only and cid != a.only):
            continue
        # character files are char_<lower id>_N.png; place files clean_<id>_N.png
        frames = sorted(set(glob.glob(os.path.join(iso, "*%s*.png" % cid)))
                        | set(glob.glob(os.path.join(iso, "*%s*.png" % cid.lower()))))
        if a.limit:
            frames = frames[:a.limit]
        if not frames:
            continue
        if a.kind == "places":
            want = nouns_of(card.get("name"), card.get("family"),
                            (card.get("tags") or "").split(",")[:6],
                            (card.get("prose") or "")[:120])
        else:
            # A character's VISUAL identity lives in tags/prose (hair, eyes, clothing);
            # `desc` is voice/character prose ("Fifty-six. Thirty years...") and matched
            # nothing - the first pass reported 0/6 on characters the VLM had described
            # perfectly. Person words are always in: a frame with no person at all is
            # subject_missing whatever the outfit says.
            want = nouns_of((card.get("tags") or "").split(",")[:10],
                            (card.get("prose") or "")[:220],
                            "person woman man girl boy figure character people "
                            "portrait face", limit=18)
        seen = 0
        for fp in frames:
            rp = os.path.splitext(fp)[0] + ".json"
            try:
                rec = json.load(open(rp, encoding="utf-8"))
            except Exception:
                rec = {}
            if a.recheck:
                prior = rec.get("frame_check") or {}
                if not prior.get("description"):
                    continue
                desc = prior["description"]
            else:
                desc = describe(fp)
            hits = check(desc, want)
            no_person = False
            if a.kind == "characters":
                # Two questions, kept apart. (1) Is ANYONE there? A frame with no person
                # is the wave-4 disease and the one hard failure (grow_thrane_7798_0: "a
                # photograph on a white card" - found by this check). (2) Do the identity
                # words match? Cards describe identity in adjectives (heavyset, weathered)
                # a VLM rarely repeats, so a person WITHOUT identity hits is "seen,
                # identity unverified", not a miss - the honest middle.
                person = check(desc, ["person", "woman", "man", "girl", "boy", "figure",
                                      "character", "people", "portrait", "face", "lady",
                                      "gentleman", "child", "warrior", "soldier",
                                      "swordsman", "sailor", "knight", "elderly", "male",
                                      "female", "someone"])
                if not person:
                    no_person = True
                    hits = []
                elif not hits:
                    hits = ["<person present; identity words not repeated>"]
            rec["frame_check"] = {"seen": bool(hits), "hits": hits[:6],
                                  "expect": want, "description": desc[:400],
                                  "model": "gemma4-e2b via TextGenerate"}
            if a.kind == "characters":
                rec["frame_check"]["no_person"] = no_person
            with open(rp, "w", encoding="utf-8") as f:
                json.dump(rec, f, indent=1, ensure_ascii=False)
            seen += bool(hits)
        n = len(frames)
        tally["seen"] += seen
        tally["miss"] += n - seen
        note = ("%d of %d isolation frames describe as this %s (VLM: nouns %s)"
                % (seen, n, a.kind[:-1], ", ".join(want[:5])))
        cards.stamp(a.kind, cid, "MEASURED",
                    "frame_check: Gemma-4 description vs card nouns", note=note)
        print("%-24s %2d/%2d  %s" % (cid, seen, n, ("" if seen == n else "MISS on %d"
                                                    % (n - seen))))
    print(json.dumps(tally))
    return 0


if __name__ == "__main__":
    sys.exit(main())
