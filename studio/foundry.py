#!/usr/bin/env python3
"""The foundry - assets built from selectors, compiled to hidden prompts.

    import foundry
    a = foundry.new_asset("character", "Jin", "anime",
                          {"archetype": "human_female", "hair_color": "white", ...})
    print(a["compiled"]["clause"])     # the prompt nobody had to write

An asset is film-independent and lives in studio/foundry/<type>s/<id>/ - the same set can
shoot two different films, the way real sets do. asset.json is the truth (selections +
compiled clauses + which seed images exist); the images beside it are a cache.

COMPILATION is fragment assembly from dictionary.json. Selections in, clauses out:
a character compiles to the appearance clause the /film editor's cast system already
speaks, a place compiles to location + ambience + palette, a costume compiles to a wear
clause that can replace a character's default outfit, music compiles to ACE-Step tags.
The prompts ride along with the media, hidden unless asked for.

SEED PACKS are the "generate all angles and concepts" step: each asset type has a plan of
views to render (a character gets portrait, full body, and turnaround angles through the
multiple-angles LoRA; a place gets three angles at every selected time of day), and those
images are what anchors, keyframes and identity routes hang on later.
"""
import json, os, re, time

HERE = os.path.dirname(os.path.abspath(__file__))
FOUNDRY = os.path.join(HERE, "foundry")
DICT_PATH = os.path.join(FOUNDRY, "dictionary.json")

TYPES = ("character", "place", "costume", "prop", "music")


def load_dict():
    return json.load(open(DICT_PATH, encoding="utf-8"))


def _slug(s):
    return re.sub(r"[^a-z0-9-]+", "-", (s or "").lower()).strip("-") or "asset"


def asset_dir(atype, aid):
    return os.path.join(FOUNDRY, atype + "s", aid)


def load_asset(atype, aid):
    p = os.path.join(asset_dir(atype, aid), "asset.json")
    if not os.path.exists(p):
        raise KeyError("%s/%s" % (atype, aid))
    return json.load(open(p, encoding="utf-8"))


def save_asset(a):
    d = asset_dir(a["type"], a["id"])
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, "asset.json.tmp")
    json.dump(a, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, os.path.join(d, "asset.json"))


def list_assets(atype):
    base = os.path.join(FOUNDRY, atype + "s")
    out = []
    if os.path.isdir(base):
        for aid in sorted(os.listdir(base)):
            try:
                out.append(load_asset(atype, aid))
            except (KeyError, ValueError):
                continue
    return out


def new_asset(atype, name, style, selections, notes=""):
    if atype not in TYPES:
        raise ValueError(atype)
    aid = _slug(name)
    if os.path.exists(os.path.join(asset_dir(atype, aid), "asset.json")):
        raise ValueError("%s %r exists" % (atype, aid))
    a = {"type": atype, "id": aid, "name": name, "style": style,
         "selections": selections, "notes": notes,
         "created": time.strftime("%Y-%m-%d %H:%M"),
         "compiled": compile_asset(atype, style, selections, notes),
         "images": {}, "assignments": {}}
    save_asset(a)
    return a


def recompile(a):
    a["compiled"] = compile_asset(a["type"], a["style"], a["selections"],
                                  a.get("notes", ""))
    save_asset(a)
    return a


# ── fragment lookup ─────────────────────────────────────────────────────────────────

def _frag(D, entity, sub, sel):
    """Fragment(s) for a selection; multi-selects come in as lists."""
    spec = D[entity]["subs"].get(sub) or {}
    opts = {o["id"]: o for o in spec.get("options", [])}
    if isinstance(sel, list):
        return [opts[s]["frag"] for s in sel if s in opts and opts[s]["frag"]]
    o = opts.get(sel)
    return (o or {}).get("frag", "")


def _optmeta(D, entity, sub, sel, key):
    spec = D[entity]["subs"].get(sub) or {}
    for o in spec.get("options", []):
        if o["id"] == sel:
            return o.get(key, "")
    return ""


def style_info(style):
    return load_dict()["style"]["options"].get(style) or \
        load_dict()["style"]["options"]["cinematic"]


# ── compilers ───────────────────────────────────────────────────────────────────────

def compile_asset(atype, style, sel, notes=""):
    D = load_dict()
    fn = {"character": _c_character, "place": _c_place, "costume": _c_costume,
          "prop": _c_prop, "music": _c_music}[atype]
    return fn(D, style, sel, notes)


def _join(parts, sep=", "):
    return sep.join(p for p in parts if p)


def _c_character(D, style, sel, notes):
    g = lambda sub: _frag(D, "character", sub, sel.get(sub, ""))
    arche = g("archetype") or "a person"
    art, _, noun = arche.partition(" ")
    adjs = _join([g("height"), g("build")])
    lead = ("%s %s %s" % (art, adjs, noun)) if adjs else arche
    head = _join([g("face_shape"), g("eye_color"), g("eye_shape"), g("brows")])
    hair_c = g("hair_color")
    hair_s = g("hair_style")
    hair = ("%s %s" % (hair_c, hair_s)).strip() if (hair_c or hair_s) else ""
    marks = _join(_frag(D, "character", "marks", sel.get("marks", [])))
    pers = g("personality")
    clause = _join([lead, g("age"), g("skin"), head, hair, g("facial_hair"), marks,
                    pers, notes])
    # the re-identification short: the two most distinctive things they carry
    short_bits = [b for b in (hair, marks.split(",")[0] if marks else "",
                              g("eye_color")) if b]
    short = _join(short_bits[:2]) or arche
    delivery = _optmeta(D, "character", "personality",
                        sel.get("personality", ""), "delivery") or "level"
    # danbooru-ish tags for the animagine route
    tag_arche = {"human_female": "1girl, solo", "human_male": "1boy, solo",
                 "human_androgynous": "1other, solo, androgynous",
                 "beast": "no humans, solo, animal focus, full body",
                 "spirit": "no humans, solo, spirit, translucent",
                 "robot": "solo, robot, humanoid robot"}.get(
                     sel.get("archetype", ""), "solo")
    tags = _join([tag_arche,
                  ("%s hair" % hair_c) if hair_c else "",
                  {"short_messy": "short hair, messy hair",
                   "short_neat": "short hair", "bob": "bob cut",
                   "shoulder": "medium hair", "long_straight": "long hair, straight "
                   "hair", "long_wavy": "long hair, wavy hair",
                   "ponytail": "ponytail", "braid": "braid", "topknot": "topknot",
                   "undercut": "undercut", "bald": "bald",
                   "mane": "mane"}.get(sel.get("hair_style", ""), ""),
                  ("%s" % g("eye_color")) if g("eye_color") else "",
                  marks,
                  # age and facial hair must be explicit tags: silver hair alone
                  # reads as a young bishounen to animagine, never as an elder
                  {"child": "child", "teen": "teenager",
                   "middle": ("mature female"
                              if sel.get("archetype") == "human_female"
                              else "mature male"),
                   "old": ("old woman, elderly, wrinkles"
                           if sel.get("archetype") == "human_female"
                           else "old man, elderly, wrinkles")}.get(
                      sel.get("age", ""), ""),
                  {"stubble": "stubble", "beard": "beard", "moustache": "mustache",
                   "goatee": "goatee"}.get(sel.get("facial_hair", ""), ""),
                  notes])
    return {"clause": clause, "short": short, "tags": tags, "delivery": delivery,
            "voice": sel.get("voice", ""),
            "voice_desc": "a %s voice" % delivery}


# each base carries the continuous sound bed the sound doctrine demands
_PLACE_AMB = {
    "school": "distant hallway echoes and a ticking wall clock",
    "classroom": "chalk on a board somewhere and chairs shifting",
    "park": "birdsong and leaves moving, a far-off dog",
    "house": "a settling house, a clock, a kettle far off",
    "boat": "water against the hull and rigging knocking",
    "cityscape": "layered traffic and signage hum",
    "library": "a deep carried quiet with one far footstep",
    "market": "a low gas burner and a market murmuring, one distant scooter",
    "rooftops": "wind over tiles and the city far below",
    "alley": "dripping water and the muffled street beyond",
    "temple": "a steady wind through pine trees, never stopping",
    "beach": "waves arriving and drawing back, gulls",
    "forest": "a high canopy moving and unseen birds",
    "bridge": "slow water under the arches and wind",
    "station": "rails ticking and a tannoy too far away to read",
    "diner": "a refrigerator hum and a coffee machine ticking",
}
_WEATHER_AMB = {"rain": "steady rain on every surface",
                "storm": "wind-driven rain and far thunder",
                "snow": "the pressed hush of falling snow",
                "wind": "a hard wind working at everything loose",
                "fog": "a fog-damped stillness"}


def _c_place(D, style, sel, notes):
    g = lambda sub: _frag(D, "place", sub, sel.get(sub, ""))
    base = sel.get("base", "")
    desc = _join([g("base"), g("condition"), g("weather"), notes])
    amb = _join([_PLACE_AMB.get(base, "a quiet ambient bed"),
                 _WEATHER_AMB.get(sel.get("weather", ""), "")])
    times = sel.get("time_of_day") or ["day"]
    if not isinstance(times, list):
        times = [times]
    return {"description": desc, "ambience": amb, "palette": g("palette"),
            "crowd": g("crowd"), "times": times,
            "time_frags": {t: _frag(D, "place", "time_of_day", t) for t in times}}


def _c_costume(D, style, sel, notes):
    g = lambda sub: _frag(D, "costume", sub, sel.get(sub, ""))
    colors = _join([g("primary"), g("secondary")], " with ") if g("secondary") \
        else g("primary")
    acc = _join(_frag(D, "costume", "accessories", sel.get("accessories", [])))
    wear = _join([("%s %s" % (colors, g("category"))).strip(),
                  g("material"), g("condition"), g("closure"), acc, notes])
    return {"wear_clause": wear}


def _c_prop(D, style, sel, notes):
    g = lambda sub: _frag(D, "prop", sub, sel.get(sub, ""))
    clause = _join([g("category"), g("material"), g("condition"), g("aura"), notes])
    return {"clause": clause}


def _c_music(D, style, sel, notes):
    g = lambda sub: _frag(D, "music", sub, sel.get(sub, ""))
    inst = _join(_frag(D, "music", "instruments", sel.get("instruments", [])))
    tags = _join([g("mood"), g("tempo"), inst, notes,
                  "instrumental, no vocals, continuous throughout"])
    return {"tags": tags}


# ── seed pack plans ─────────────────────────────────────────────────────────────────

CHAR_VIEWS = [
    ("portrait", "head and shoulders portrait, facing the camera, plain background"),
    ("fullbody", "full body, standing, facing the camera, plain background"),
]
CHAR_TURNS = [
    ("threequarter", "Turn the camera 45 degrees: the same person seen in three-quarter "
     "view, same clothing, same plain background, full body"),
    ("side", "Turn the camera 90 degrees: the same person seen exactly from the side in "
     "profile, same clothing, same plain background, full body"),
    ("back", "Turn the camera 180 degrees: the same person seen exactly from behind, "
     "same clothing, same plain background, full body"),
]
PLACE_ANGLES = [
    ("wide", "a wide establishing view of"),
    ("reverse", "a wide view from the opposite end of"),
    ("detail", "a ground-level medium view inside"),
]
PROP_VIEWS = [
    ("hero", "a hero product shot of"),
    ("macro", "an extreme close macro detail of"),
]


def seed_plan(a):
    """Which images this asset's pack should hold, as (key, kind, prompt-ish)."""
    t = a["type"]
    if t == "character":
        return ([("base_" + k, "direct", p) for k, p in CHAR_VIEWS]
                + [("turn_" + k, "turnaround", p) for k, p in CHAR_TURNS])
    if t == "place":
        out = []
        for tkey, tfrag in a["compiled"]["time_frags"].items():
            for akey, aprompt in PLACE_ANGLES:
                out.append(("%s_%s" % (tkey, akey), "direct",
                            "%s %s, %s" % (aprompt, a["compiled"]["description"],
                                           tfrag)))
        return out
    if t == "costume":
        return [("card", "direct",
                 "the outfit alone, displayed on a simple headless dress stand, "
                 "plain grey background: " + a["compiled"]["wear_clause"])]
    if t == "prop":
        return [(k, "direct", "%s %s, plain background" %
                 (p, a["compiled"]["clause"])) for k, p in PROP_VIEWS]
    return []


if __name__ == "__main__":
    import sys
    if "selftest" in sys.argv:
        D = load_dict()
        sel = {"archetype": "human_female", "age": "twenties", "height": "short",
               "build": "slight", "skin": "pale", "face_shape": "heart",
               "eye_color": "green", "eye_shape": "narrow", "brows": "thin",
               "hair_style": "short_messy", "hair_color": "white",
               "marks": ["tattoo_neck", "earring"], "personality": "wry",
               "voice": "female_03_alice"}
        c = compile_asset("character", "anime", sel)
        print("clause:", c["clause"])
        print("short :", c["short"])
        print("tags  :", c["tags"])
        p = compile_asset("place", "anime",
                          {"base": "market", "condition": "festival",
                           "time_of_day": ["night", "dawn"], "weather": "clear",
                           "crowd": "busy", "palette": "warm"})
        print("place :", p["description"])
        print("amb   :", p["ambience"])
        m = compile_asset("music", "anime",
                          {"mood": "wistful", "tempo": "slow",
                           "instruments": ["guzheng", "flute", "bells"]})
        print("music :", m["tags"])
        print("selftest ok")
