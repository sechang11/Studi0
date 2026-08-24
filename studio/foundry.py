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

TYPES = ("character", "place", "costume", "prop", "music", "motion",
         "camera")


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


def new_asset(atype, name, style, selections, notes="", level=3,
              parent="", overrides=None, tag_notes=""):
    if atype not in TYPES:
        raise ValueError(atype)
    aid = _slug(name)
    if os.path.exists(os.path.join(asset_dir(atype, aid), "asset.json")):
        raise ValueError("%s %r exists" % (atype, aid))
    a = {"type": atype, "id": aid, "name": name, "style": style,
         "selections": selections, "notes": notes,
         "level": int(level or 3), "parent": parent or "", "overrides": overrides or {},
         "created": time.strftime("%Y-%m-%d %H:%M"),
         "tag_notes": tag_notes,
         "compiled": compile_asset(atype, style, selections, notes, tag_notes),
         "images": {}, "assignments": {}}
    save_asset(a)
    return a


def recompile(a):
    a["compiled"] = compile_asset(a["type"], a["style"], a["selections"],
                                  a.get("notes", ""),
                                  a.get("tag_notes", ""))
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

def compile_asset(atype, style, sel, notes="", tag_notes=""):
    D = load_dict()
    fn = {"character": _c_character, "place": _c_place, "costume": _c_costume,
          "prop": _c_prop, "music": _c_music, "motion": _c_motion, "camera": _c_camera}[atype]
    try:
        return fn(D, style, sel, notes, tag_notes)
    except TypeError:
        return fn(D, style, sel, notes)   # types without a tag stack


def _join(parts, sep=", "):
    return sep.join(p for p in parts if p)


def _c_character(D, style, sel, notes, tag_notes=""):
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
    picked = [lead, g("age"), g("skin"), head, hair, g("facial_hair"), marks, pers]
    if notes and not any(p for p in picked[1:]) and not sel.get("archetype"):
        clause = notes          # described, not selected - the words are the character
    else:
        clause = _join(picked + [notes])
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
                  notes, tag_notes])
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


def _c_camera(D, style, sel, notes, tag_notes=""):
    """A camera selection. `enforced` says whether the engine will actually obey:
    only `pinned` does, because it is a generation method rather than a request."""
    g = lambda sub: _frag(D, "camera", sub, sel.get(sub, ""))
    move = sel.get("move", "")
    enforced = bool(_optmeta(D, "camera", "move", move, "enforced"))
    return {"framing": g("framing"), "move": g("move"),
            "move_id": move, "enforced": enforced,
            "needs_end_frame": move == "pinned",
            "clause": _join([g("framing"), g("move"), notes])}


def _c_motion(D, style, sel, notes, tag_notes=""):
    """A shot's movement, as a beat can consume it."""
    g = lambda sub: _frag(D, "motion", sub, sel.get(sub, ""))
    action = g("action")
    pace = g("pace")
    # camera moved out to its own variable; keep reading it if an older asset
    # still carries one so nothing silently loses its move
    legacy_cam = g("camera") if sel.get("camera") else ""
    # pace qualifies the action rather than trailing it, so "walks steadily
    # toward the camera, quickly" does not happen
    act = _join([a for a in (action, pace) if a]) if action else ""
    amb = _join(_frag(D, "motion", "ambient", sel.get("ambient", [])))
    return {"action": _join([act, notes]),
            "camera": legacy_cam,
            "ambient": amb,
            "clause": _join([act, legacy_cam, amb, notes])}


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


# ── how deep to build a character ───────────────────────────────────────────────────
# A character is a seed for a film, not a deliverable. Most need a face and a few
# angles; a lead that carries thirty shots earns a trained LoRA. Each level is a
# superset of the one below and its artefacts are literally the next level's input.
LEVELS = [
    {"n": 1, "key": "identity", "label": "Identity",
     "blurb": "Every angle, the face turned, expressions, a varied set and a mesh - "
              "built from the seed images. This is the floor: enough to drop the "
              "character into ANY film without generating them again.",
     "adds": ["turnaround", "face turnaround", "expressions", "presentation set",
              "3D mesh"],
     "castable": True, "lora": False, "mesh": True,
     "cost": "thirty to forty-five minutes"},
    {"n": 2, "key": "trained", "label": "Trained",
     "blurb": "The kit becomes a model. A character LoRA trained on the identity set "
              "holds the face where a reference degrades - angles you did not shoot, "
              "light you did not plan. The mesh is cleaned and rigged so pose can be "
              "driven rather than prompted.",
     "adds": ["character LoRA", "rigged mesh"],
     "castable": True, "lora": True, "mesh": True,
     "cost": "plus about twenty minutes"},
    {"n": 3, "key": "range", "label": "Range",
     "blurb": "Not more identity - more situations. Every costume rendered on them, "
              "plus states: ages, injuries, wet, filthy, formal, disguised. Any point "
              "in the character's arc is already built.",
     "adds": ["costumes rendered", "state variants"],
     "castable": True, "lora": True, "mesh": True,
     "cost": "a few minutes per costume or state"},
    {"n": 4, "key": "performance", "label": "Performance",
     "blurb": "The character can act. A voice bound and auditioned, delivery tied to "
              "personality, lip-sync references, and a keyframe per emotion so a shot "
              "can ask for them afraid at three-quarter and get it.",
     "adds": ["voice bound", "emotion keyframes", "lip-sync references"],
     "castable": True, "lora": True, "mesh": True,
     "cost": "plus about ten minutes"},
    {"n": 5, "key": "canon", "label": "Canon",
     "blurb": "Continuity above the film. A bible of relationships, history and verbal "
              "tics; a signature shot grammar - their framings, their palette, how they "
              "are lit; signature props; and a QC gate that checks new renders against "
              "the canon instead of against a prompt.",
     "adds": ["character bible", "shot grammar", "signature kit", "canon QC"],
     "castable": True, "lora": True, "mesh": True,
     "cost": "authored, not rendered"},
]

# The identity set: one person, ONE outfit, ONE light, many views. Locked on purpose.
CHAR_TURN_VIEWS = [
    ("front", "standing facing the camera straight on"),
    ("front_three_quarter", "turned 45 degrees, three-quarter view"),
    ("side", "turned 90 degrees, full profile from the side"),
    ("back_three_quarter", "turned 135 degrees, seen from behind at an angle"),
    ("back", "turned 180 degrees, seen directly from behind"),
]
# The face turned on its own - close enough that the head fills the frame.
CHAR_FACE_VIEWS = [
    ("face_front", "a tight head-and-shoulders portrait, facing the camera"),
    ("face_three_quarter", "a tight head-and-shoulders portrait, head turned 45 degrees"),
    ("face_side", "a tight head-and-shoulders portrait, full profile"),
]
# The presentation set: the SAME person deliberately varied. Never fed to training.
CHAR_PRESENTATION = [
    ("pres_hero", "a cinematic hero shot, dramatic side lighting, upper body"),
    ("pres_wide", "a full-length wide shot, even daylight, standing at ease"),
    ("pres_low", "a low-angle shot looking up at them, moody rim light"),
]

LEVEL_BY_N = {L["n"]: L for L in LEVELS}


def pack_report(a):
    """What a character HAS, against what level 1 demands. The cast page shows this,
    so it must describe the pack on disk and never the level that was requested."""
    imgs = set((a.get("images") or {}).keys())
    have = {
        "turnaround": sum(1 for k, _ in CHAR_TURN_VIEWS if "turn_" + k in imgs),
        "face": sum(1 for k, _ in CHAR_FACE_VIEWS if k in imgs),
        "expressions": sum(1 for k, _ in CHAR_EXPRESSIONS if "expr_" + k in imgs),
        "presentation": sum(1 for k, _ in CHAR_PRESENTATION if k in imgs),
        "mesh": 1 if a.get("mesh") else 0,
    }
    want = {"turnaround": len(CHAR_TURN_VIEWS), "face": len(CHAR_FACE_VIEWS),
            "expressions": len(CHAR_EXPRESSIONS),
            "presentation": len(CHAR_PRESENTATION), "mesh": 1}
    missing = [k for k in want if have[k] < want[k]]
    return {"have": have, "want": want, "missing": missing,
            "complete": not missing}


def level_of(a):
    """The level a character has actually REACHED. Level 1 is the casting floor, so
    anything short of a complete pack is 0 - a draft, not a rung."""
    if not pack_report(a)["complete"]:
        return 0
    n = 1
    if a.get("lora"):
        n = 2
    if n >= 2 and (a.get("assignments") or a.get("states")):
        n = 3
    if n >= 3 and a.get("voice_bound"):
        n = 4
    if n >= 4 and a.get("bible"):
        n = 5
    return n


CHAR_EXPRESSIONS = [
    ("neutral", "a level, unreadable expression, looking straight at the viewer"),
    ("joy", "laughing, eyes crinkled, plainly delighted"),
    ("anger", "furious, brows down, jaw set"),
    ("fear", "frightened, eyes wide, drawn back"),
    ("sorrow", "grieving, eyes down, mouth tight"),
    ("surprise", "caught off guard, brows up, mouth open"),
]

# The same six as danbooru tags. A drawn engine reads these; the prose above is
# for the photographic path. Measured: prose appended to a long tag string moved
# the face by 0.037 - indistinguishable from not asking at all.
EXPR_TAGS = {
    "neutral": "expressionless, closed mouth, looking at viewer",
    "joy": "laughing, open mouth, happy, closed eyes, smile",
    "anger": "angry, clenched teeth, v-shaped eyebrows, glaring",
    "fear": "scared, wide-eyed, trembling, open mouth, sweatdrop",
    "sorrow": "sad, tears, crying, downcast eyes, frown",
    "surprise": "surprised, wide-eyed, open mouth, shocked",
}
_EXPR = dict(CHAR_EXPRESSIONS)


def variant_selections(parent, overrides):
    """A variant is its parent plus named differences - never a fresh person."""
    sel = dict(parent.get("selections") or {})
    sel.update(overrides or {})
    return sel


def variant_summary(D, parent, overrides):
    """What actually differs, in words, for the card and the UI."""
    out = []
    for sub, val in (overrides or {}).items():
        label = ((D.get("character") or {}).get("subs", {})
                 .get(sub, {}).get("label", sub))
        def _say(v):
            f = _frag(D, "character", sub, v)
            return _join(f) if isinstance(f, (list, tuple)) else (f or "")

        was = _say((parent.get("selections") or {}).get(sub, ""))
        now = _say(val)
        out.append("%s: %s -> %s" % (label, was or "-", now or "-"))
    return "; ".join(out)


def seed_plan(a):
    """Which images this asset's pack should hold, as (key, kind, prompt-ish)."""
    t = a["type"]
    if t == "character":
        # Level 1 is all-or-nothing: the whole portable kit, every time. Higher
        # levels ADD to it (a LoRA, costumes, a voice) rather than changing it, so
        # the image plan is the same at every rung.
        out = [("base_portrait", "direct",
                "a head-and-shoulders portrait, neutral expression"),
               ("base_fullbody", "direct",
                "a full-length standing shot, arms at their sides")]
        out += [("turn_" + k, "turnaround", p) for k, p in CHAR_TURN_VIEWS]
        out += [(k, "direct", p) for k, p in CHAR_FACE_VIEWS]
        out += [("expr_" + k, "direct",
                 "a head-and-shoulders portrait, %s" % p)
                for k, p in CHAR_EXPRESSIONS]
        out += [(k, "direct", p) for k, p in CHAR_PRESENTATION]
        return out

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
