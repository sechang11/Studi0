#!/usr/bin/env python3
"""studio/compose.py - THE LAYER COMPOSITION RESOLVER.

    python3 studio/compose.py --demo            # run the resolver over real combinations
    python3 studio/compose.py --style shojo_soft --place pine_forest --character VIRO

WHAT THIS IS FOR

A picture in this studio is assembled out of layers - a style, a place, a character, a
look, a damage level, a lighting preset, a weather preset - and the layers are not
independent. Some of them fight. shojo_soft does not re-render your forest in a shojo
idiom, it DELETES your forest and puts the subject in a field of flowers. looks/noir sets
saturation to exactly zero after the render, which silently destroys any style whose whole
identity is colour. A trained character LoRA is a delta on animagine weights and cannot
apply on the qwen path at all, so choosing a qwen style throws the character training away
without a word.

Every one of those was measured by rendering and looking (studio/_tools/style_examples.py,
studio/styles/*.json `verdict`), and every one of them was, until this file existed,
invisible to the author until the render came back wrong.

So: this module takes a layer SELECTION and returns the assembled prompt plus an explicit
list of what is going to fight. It is pure - it reads the card libraries and returns a
dict. It renders nothing, writes nothing, and raises nothing.

    resolve(libs, sel) -> dict

It is the SAME code path used by both callers, deliberately:

    studio/compile.py   compiling an authored .movie file
    studio/serve.py     POST /api/compose, backing the wizard

If those two ever disagree about what a selection means, the wizard is lying to the author
about what their film will look like. That is why the engine-derivation logic was MOVED
here out of compile.py rather than copied.

WHAT IT KNOWS, AND HOW IT KNOWS IT

Nearly everything below is read off the cards at runtime rather than hardcoded, because
the cards carry the measurements:

    style.compose     safe / replaces / injects / inert - assigned per card from pixels
    style.status      ready / weak / unavailable
    style.engine      which model can render this idiom at all
    style.lora        an optional style LoRA this card recommends, honoured when the
                      author has not picked one - see resolve_style_lora()
    lora.base_model   the weights a LoRA is a delta ON. The one field in any library here
                      that decides whether a file is handed to the renderer at all
    look.grade        an ffmpeg filter string; the saturation number is parsed out of it
    place.family      interior / urban / nature / ... (the interior test)
    place.time_of_day an authored allowlist of times this location can read as
    tags/*.json       89 cards, each with a `fights_with` array - a machine-readable
                      conflict lexicon that needs no new authoring

Five small tables ARE hardcoded, and each says why at its definition. They exist where a
property is real and measured but has no field on the card to hold it.

WHAT IS HONEST ABOUT `contributed`

Every layer reports the exact text it put into the prompt. When a layer put nothing in, it
says so in a sentence rather than returning "". An inert style, a place on a path that
cannot use it, a wear level with nobody to wear it - those are the failures this project
keeps calling out (compile.py: "a knob that quietly has no effect is worse than no knob")
and an empty string in a UI reads as "fine" rather than as "nothing happened".

WHAT THIS MODULE DOES NOT DO

It does not raise. Callers that need to fail hard (compile.py fails on an unknown card id,
because a typo should not compile) test the `code` on a conflict and raise themselves.

It does not touch the renderer. `negative` is assembled and returned, but scripts/short.py
has no negative input plumbed on either keyframe workflow today, so a style's
`negative_add` currently reaches nothing - see the D2 conflict below, which says exactly
that rather than pretending.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Constants that used to live in compile.py. They live HERE now and compile.py
# imports them, so the prompt the wizard previews and the prompt the film
# compiles cannot drift apart.
# ---------------------------------------------------------------------------

# The checkpoint card calls these load-bearing: dropping them measurably degrades the
# output. They compete with nothing, which is why they go last.
Q = "masterpiece, best quality, very aesthetic, absurdres"

# Fallback subject tags for a character card that does not carry its own `base_tags`.
# This whole project can currently only render men, which is a real limitation and not a
# design choice - a character card may now override it with `base_tags`. Left as the
# default rather than deleted because dropping it from every existing prompt is a visual
# change nobody has rendered and looked at.
MALE = "male focus, mature male, masculine"

# Damage continuity. Appended to a character's tags and never allowed to decrease, so a
# torn shirt cannot un-tear itself in the next scene. A character card may override this
# with its own `wear_tags` list - a soldier and a child should not share one damage
# vocabulary.
WEAR = ["clean uniform, neat hair",
        "sweaty, damp hair, flushed",
        "sweaty, dirt on uniform, messy hair, breathing hard",
        "torn uniform, dirt and grass stains, exhausted, dishevelled",
        "torn bloodied uniform, cut on face, utterly exhausted, trembling"]

# Templates whose whole point is that there is no face in frame.
NO_PERSON = {"pillow", "insert", "establish"}

ENGINES = ("anime", "qwen")

GROUPS = ("styles", "places", "characters", "looks", "lighting", "weather",
          "emotions", "tags", "checkpoints", "loras")

_LIB_CACHE = {}


# ---------------------------------------------------------------------------
# library loading
# ---------------------------------------------------------------------------

def load_libs(root=None, groups=GROUPS):
    """Every card in every library this resolver reads, as {group: {id: card}}.

    Cached, because serve.py calls resolve() on every keystroke in the wizard and
    compile.py calls it once per beat. Loading is lazy and happens on the first call -
    importing this module reads no files and has no side effects, so it is safe to import
    from anything.

    A card file that will not parse is SKIPPED rather than fatal. serve.py:232 has the
    opposite behaviour today (/api/cards has no try/except, so one malformed file 500s the
    whole endpoint) and that is the bug this avoids: a broken style card should not take
    the composer down for every other layer.
    """
    root = root or HERE
    key = (root, tuple(groups))
    if key in _LIB_CACHE:
        return _LIB_CACHE[key]
    out = {}
    for g in groups:
        d = os.path.join(root, g)
        cards = {}
        if os.path.isdir(d):
            for fn in sorted(os.listdir(d)):
                if not fn.endswith(".json"):
                    continue
                try:
                    with open(os.path.join(d, fn), encoding="utf-8") as fh:
                        c = json.load(fh)
                except (ValueError, OSError):
                    continue
                if isinstance(c, dict):
                    cards[str(c.get("id") or fn[:-5])] = c
        out[g] = cards
    _LIB_CACHE[key] = out
    return out


def clear_cache():
    """Drop the library cache. serve.py can call this after a card is edited on disk."""
    _LIB_CACHE.clear()


# ---------------------------------------------------------------------------
# measured tables that have no field on a card to live in
# ---------------------------------------------------------------------------

# Five look cards name a PLACE in their prompt tags, not just a colour. That matters
# because a look is normally thought of as a post-process grade, so an author does not
# expect `look: neon` to relocate their locker room to a wet city street - but it does,
# and in the old tag order it did it from an EARLIER position than the place card, which
# means it won.
#
# The fix is two-part: place now precedes look in the tag stack, and when a place is
# actually chosen these specific nouns are dropped from the look so only its light and
# colour survive. Derived by reading all 25 look tag strings; the other 20 name no place.
LOOK_PLACE_NOUNS = {
    "neon":         ["city street", "wet pavement"],
    "sodium":       ["city street", "street light", "lamppost"],
    "fluorescent":  ["indoors", "office"],
    "hospital":     ["hospital", "indoors"],
    "underwater":   ["underwater"],
    # Three more, found by dumping all 25 tag strings rather than trusting the count
    # above: the comment used to claim "the other 20 name no place" and that was wrong.
    # `campfire` is the sharpest of them - under this project's governing rule the model
    # renders nouns, so look: firelight over place: locker_room draws an actual campfire
    # in the locker room. The light and colour words are kept; only the object goes.
    "firelight":    ["campfire", "fire", "dark background"],
    "day_for_night": ["floodlights"],
    "blockbuster":  ["orange sky"],
}

# The group name a layer is called in a message, because the library folders are plural
# and chopping the "s" off mangles two of them.
LAYER_SINGULAR = {
    "styles": "style", "places": "place", "looks": "look", "characters": "character",
    "emotions": "emotion", "lighting": "lighting", "weather": "weather",
    "cameras": "camera", "transitions": "transition",
}

# 16 of the 64 place cards open their tag string with "scenery, no humans", because a
# place was authored as an empty establishing shot of a location. Put a character in one
# and the prompt says "1boy, solo" and "no humans" in the same breath -
# tags/1boy.json lists exactly those two among the things a count tag fights, and warns
# that losing the count is the fastest way to get two half-drawn people. So the emptiness
# claim is dropped when somebody is actually in the shot. FOUND BY RUNNING THIS RESOLVER:
# the token check below flagged it on the very first real combination tried.
PLACE_EMPTY_NOUNS = ["scenery", "no humans"]

# Seven look cards also name a TIME OF DAY, which is a second thing the author did not
# ask this layer for. `golden` was considered and left out: "golden hour" reads as either
# dawn or dusk and would produce a false conflict either way.
LOOK_TIME = {"dawn": "dawn", "day_for_night": "night", "moonlit": "night",
             "neon": "night", "night": "night", "sodium": "night", "sunset": "dusk"}

# Styles that are not styles. Each of these claims a slot that another layer already
# owns, and because the style text sits late in the stack it silently overrides the layer
# that was supposed to own it. Every entry is quoted from the card's own measured verdict.
SHOT_PROPERTY_STYLES = {
    "drone_aerial":      ("moves the camera, not the drawing - an aerial is a camera "
                          "position", "put the height in the shot's camera field"),
    "tilt_shift":        ("squeezes the subject into a letterboxed strip instead of "
                          "changing the rendering", "crop in the edit instead"),
    "macro_photography": ("tightens the crop but produces no macro optics",
                          "ask for a close-up framing on the shot instead"),
    "sakuga_impact":     ("rewrites the pose - arm thrown at camera, scarf streaming",
                          "describe the action in the shot line instead"),
    "american_comic":    ("rewrites the pose into a dynamic action stance",
                          "describe the pose you want in the shot line"),
}

# Styles whose whole identity is COLOUR. A desaturating grade runs after generation, in
# ffmpeg, deterministically - so it always wins, and the money spent on the style is
# thrown away. Judged from each card's `means` and `verdict`; there is no
# colour-dependence field to read, which is why this is a list.
CHROMATIC_STYLES = {
    "byzantine_icon", "ukiyo_e", "ukiyo_e_shin_hanga", "airbrush_70s", "arcane_magitech",
    "cyberpunk_neon", "neo_noir", "solarpunk", "psychedelic_60s", "illuminated_manuscript",
    "vaporwave", "pop_art", "y2k_chrome", "idol_bright", "cross_processed",
}

# A style is monochrome by construction if it says so in its own tags, prose or means.
# Computed rather than listed - this regex reproduces exactly the 13 cards a hand audit
# found, so there is nothing to keep in sync.
_MONO_RE = re.compile(r"monochrom|greyscale|grayscale|black.and.white", re.I)

# `works_for` is free prose, not an enum, and there is no video_safe boolean anywhere in
# the schema, so this has to be a regex over the sentence the author wrote. Marked
# low-confidence in the message it produces, and the card's own "INFERRED, not measured"
# wording is carried through where it is present.
_VIDEO_RISK_RE = re.compile(
    r"\bnot viable\b|\bboil|\bcrawl|\bstrobe|\bswim\b|\bwill flicker\b|\bworst\b|"
    r"\bpoorly\b|\bwill pop\b", re.I)

# Weather nouns that a place card may already have baked into its own tags. Deliberately
# tight (no \w* suffixes) - a loose version matched "window" for "wind" and "sandal" for
# "sand" and flagged 37 of 64 places instead of 13.
_WEATHER_RE = re.compile(
    r"\b(rain|rainfall|raining|snow|snowing|snowfall|fog|foggy|mist|misty|overcast|"
    r"storm|stormy|blizzard|sleet|hail|dust|ash|haze|hazy|drizzle|cloudy|clouds|"
    r"downpour|sandstorm)\b", re.I)

# Colour words, for the one prose entry in tags/monochrome.json's fights_with list -
# "every tag naming a colour" cannot be matched as a token, so it needs its own predicate.
_COLOUR_RE = re.compile(
    r"\b(red|orange|yellow|green|blue|purple|violet|pink|magenta|cyan|teal|gold|golden|"
    r"silver|brown|crimson|scarlet|azure|amber|colou?rful|saturated|pastel colou?rs?)\b",
    re.I)

# Layers whose text the author did not choose. Excluded from the token-level fight check,
# because warning that the mandatory quality tokens disagree with the style the author
# picked is noise they can do nothing about.
_UNCHECKED_LAYERS = {"quality"}

# A LoRA's base_model -> which of THIS PROJECT's two keyframe engines it can attach to,
# or None for "neither, it belongs to some other model on the box".
#
# THE ONE TABLE IN THIS FILE THAT DECIDES WHETHER A FILE IS LOADED AT ALL. A LoRA is a
# delta on specific weights: an animagine-trained one does nothing on qwen and a
# qwen-trained one does nothing on animagine. That was proved from pixels here (qwen rows
# with the animagine character LoRA force-loaded are identical to rows with it dropped)
# and again from the ComfyUI log, where the same file reports "1168 patches attached" on
# SDXL and rejects every one of its keys immediately after a QwenImage load.
#
# It is derived from `base_model` rather than read off the card's own `engine` field
# because base_model is the physically load-bearing one - engine is a convenience copy
# and a copy can be wrong. Where the two disagree the card is reported, not obeyed.
#
# qwen_edit is deliberately NOT "qwen". Qwen-Image-Edit-2511 and Qwen-Image-2512 are
# different checkpoints; workflows/13 (no reference) runs 2512 and workflows/14 (with a
# reference sheet) runs Edit-2511, and node 7 of both is this slot. Nobody on this box has
# rendered an edit-trained style LoRA on the t2i model or the reverse, so it routes to
# neither rather than being guessed into one.
LORA_ENGINE = {
    "animagine":   "anime",
    "illustrious": "anime",
    "sdxl":        "anime",
    "qwen":        "qwen",
    "qwen_edit":   None,
    "ltx":         None,
    "wan":         None,
    "flux":        None,
    "other":       None,
}

# What a base_model that routes nowhere is actually FOR, so the error can name it instead
# of saying "not supported". Keyed by the same strings as LORA_ENGINE.
LORA_BASE_MEANS = {
    "qwen_edit": "Qwen-Image-Edit, which is a different checkpoint from the Qwen-Image "
                 "2512 this slot patches",
    "ltx":       "LTX-2.3, which is the video model",
    "wan":       "Wan, which is a video model",
    "flux":      "FLUX, which nothing in this studio's keyframe path loads",
    "other":     "a model this studio does not draw keyframes with",
}

# Values of `kind` that belong in the style slot. Anything else on the right base still
# loads - it is only a warning - because a LoRA does not know what it was filed under.
LORA_STYLE_KINDS = {"style"}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _one_line(s):
    """Collapse to a single line.

    LOAD-BEARING ACROSS A PROCESS BOUNDARY. serve.py shells out to compile.py and
    re-derives the warning list by scraping stdout for lines that start with "!"
    (studio/serve.py:393). A message containing a newline scrapes as two warnings and the
    second one arrives in the UI without its marker, as a fragment.
    """
    return re.sub(r"\s+", " ", str(s if s is not None else "")).strip()


def _conflict(severity, layers, message, fix, code):
    return {"severity": severity, "layers": list(layers),
            "message": _one_line(message), "fix": _one_line(fix), "code": code}


_SEVERITY_ORDER = {"error": 0, "warning": 1, "note": 2}


def _sort_conflicts(cs):
    """Worst first, insertion order preserved inside a severity."""
    return sorted(cs, key=lambda c: _SEVERITY_ORDER.get(c["severity"], 3))


def _tokens(s):
    """A danbooru tag string split into the comma-separated terms the model actually sees."""
    return [t.strip().lower() for t in str(s or "").split(",") if t.strip()]


def _join_tags(slots):
    return ", ".join(t for _, t in slots if t)


def _join_prose(slots):
    parts = [str(t).strip(" .,") for _, t in slots if str(t).strip(" .,")]
    return (". ".join(parts) + ".") if parts else ""


def _wear_level(v):
    try:
        return max(0, int(float(v)))
    except (TypeError, ValueError):
        return 0


def _card(libs, group, ident):
    """Look a card up, tolerating case. Returns None rather than raising."""
    if not ident:
        return None
    cards = libs.get(group) or {}
    for k in (str(ident), str(ident).upper(), str(ident).lower()):
        if k in cards:
            return cards[k]
    return None


def _name(card, fallback=""):
    if not card:
        return fallback
    return card.get("name") or card.get("id") or fallback


def _grade_saturation(grade):
    """Saturation multiplier an ffmpeg grade string applies, or None if it sets none.

    Two spellings occur in studio/looks/: `eq=...:saturation=N` and `hue=s=N`, and noir
    uses the second to reach exactly zero. Both are multiplied together because a look may
    legitimately carry both.
    """
    g = str(grade or "")
    vals = [float(m) for m in re.findall(r"saturation=([0-9.]+)", g)]
    vals += [float(m) for m in re.findall(r"hue=s=([0-9.]+)", g)]
    if not vals:
        return None
    out = 1.0
    for v in vals:
        out *= v
    return round(out, 3)


def _is_monochrome_style(style):
    if not style:
        return False
    blob = " ".join(str(style.get(k, "")) for k in ("tags", "prose", "means", "verdict"))
    return bool(_MONO_RE.search(blob))


def _strip_tokens(tagstr, drop):
    """Remove exact comma-terms from a tag string. Substring matching is deliberately not
    used - dropping "close-up" must not also eat "extreme close-up"."""
    drop = {d.strip().lower() for d in drop}
    keep = [t for t in str(tagstr or "").split(",")
            if t.strip().lower() not in drop and t.strip()]
    return ", ".join(t.strip() for t in keep)


# ---------------------------------------------------------------------------
# engine derivation - MOVED here out of compile.py
# ---------------------------------------------------------------------------

def resolve_engine(libs, style_id="", engine_hint=""):
    """Which image model renders this, and why.

    An image is always in some style, and that choice decides which model can render it at
    all - the two families here want opposite prompt formats, and asking the anime
    checkpoint for photorealism is a contradiction it cannot resolve. So `style` is
    authored and `engine` is derived from it, rather than the author having to know which
    model does what.

    An explicit engine still wins, because a style card can be wrong and an author who has
    looked at the output should be able to override it. When they disagree, say so rather
    than silently picking one - 27 of the first 64 style cards shipped routed to the wrong
    engine and returned abstract colour shapes or plain photographs, so this is not a
    hypothetical.

    Returns {"engine", "style", "style_id", "reason", "conflicts"}. Never raises: an
    unknown style or an unknown engine comes back as a conflict carrying the code
    "style_unknown" / "engine_unknown", and a caller that wants to die on that (compile.py
    does, because a typo in a .movie must not compile) tests the code and raises itself.
    """
    conflicts = []
    style_id = str(style_id or "").strip()
    hint = str(engine_hint or "").strip().lower()
    style = None

    if style_id:
        style = _card(libs, "styles", style_id)
        if style is None:
            have = ", ".join(sorted(k for k in (libs.get("styles") or {})))
            conflicts.append(_conflict(
                "error", ["style"],
                "there is no style called %r." % style_id,
                "pick one of: %s" % (have or "(the styles library is empty)"),
                "style_unknown"))
        # _control is the held-constant baseline every other example is read against, not
        # a style. It is also the only card in the library with no `compose` field, so
        # every rule below would fall through or KeyError on it. Treat it as no style.
        elif style.get("family") == "control" or style.get("id") == "_control":
            style = None

    engine = hint
    if style and not hint:
        engine = str(style.get("engine", "anime")).lower()
        if engine == "either":
            reason = ("the style %r renders on both engines; using anime, which is this "
                      "project's illustration engine" % _name(style, style_id))
            engine = "anime"
        else:
            reason = "the style %r is authored for the %s engine" % (
                _name(style, style_id), engine)
    elif style and hint and style.get("engine") not in (hint, "either"):
        # EXACT legacy wording, preserved from compile.py so an existing film's warning
        # text does not change when this moved out of that file.
        conflicts.append(_conflict(
            "warning", ["style", "engine"],
            "style '%s' wants engine '%s' but the film sets engine '%s'. Using '%s' as "
            "authored - drop the engine line to follow the style."
            % (style_id, style.get("engine"), hint, hint),
            "delete the engine line and let the style choose, or keep it if you have "
            "looked at the render and the style card is wrong.",
            "engine_override"))
        reason = ("you set the engine to %s by hand, overriding the style %r which asks "
                  "for %s" % (hint, _name(style, style_id), style.get("engine")))
    elif hint:
        reason = "you chose the %s engine by hand" % hint
    else:
        reason = ("nothing chose an engine, so this falls back to anime - danbooru tags "
                  "through animagine-xl-4.0")

    engine = engine or "anime"
    if engine not in ENGINES:
        conflicts.append(_conflict(
            "error", ["engine"],
            "there is no engine called %r." % engine,
            "anime = danbooru tags plus IPAdapter faces (animagine-xl-4.0); "
            "qwen = prose prompts, photographic (Qwen-Image 2512).",
            "engine_unknown"))
        engine = "anime"
        reason = "unknown engine, falling back to anime"

    if style and style.get("strength") == "weak":
        # EXACT legacy wording, preserved from compile.py.
        conflicts.append(_conflict(
            "warning", ["style"],
            "style '%s' is marked weak: %s" % (style_id, str(style.get("note", ""))[:150]),
            "this idiom is subtle by design - expect a small difference from the control, "
            "and reach for a stronger card in the same family if you need it to read.",
            "style_strength_weak"))

    if engine != "anime":
        # EXACT legacy wording, preserved from compile.py.
        conflicts.append(_conflict(
            "warning", ["engine", "character"],
            "engine 'qwen': character faces are held by reference SHEETS through "
            "Qwen-Edit rather than IPAdapter, which is a weaker lock - expect more drift "
            "between shots than the anime path gives you",
            "if holding one face across a whole film matters more than the style, use an "
            "anime-engine style instead.",
            "qwen_face_lock"))

    return {"engine": engine, "style": style, "style_id": style_id if style else "",
            "reason": _one_line(reason), "conflicts": conflicts}


# Ways to say "no style LoRA on this one" when the style card recommends one. Without a
# sentinel a recommendation could only be refused by editing the style card, which is a
# change to every film that uses it.
_LORA_OFF = {"none", "off", "no", "false", "-", "0"}


def resolve_style_lora(libs, engine, style, lora_id="", strength=None, character=None):
    """Which STYLE LoRA is loaded on top of the picture, at what strength, and why not.

    This is the one layer in this studio that is not words. Every other layer adds text
    and the model decides what to do with it; a LoRA is arithmetic on the weights, and it
    is the only thing measured here that made qwen stop being photographic - the same
    watercolour prose at the same seed came back a photograph with no LoRA and a genuine
    painted illustration with illustration-1.0-qwen-image at 1.0. That is why the slot
    exists at all.

    It is also the layer with the sharpest failure mode. A LoRA is a delta on SPECIFIC
    weights: put an animagine-trained one on qwen and it does not error, it does not warn,
    it simply attaches to nothing. So `base_model` on the card decides whether the file is
    handed to the renderer at all, and a mismatch is an error rather than a note.

    Arguments:
        engine      "anime" | "qwen", already derived by resolve_engine()
        style       the resolved style CARD (not its id), or None
        lora_id     a studio/loras/*.json id, or a bare .safetensors filename, or one of
                    none/off/no/false/-/0 to refuse a style card's recommendation
        strength    explicit strength, or None to take the recommended one
        character   the resolved character card, for the reference-path note only

    Returns {"id", "file", "strength", "active", "reason", "source", "card", "conflicts"}.
    `file` is None whenever nothing should be loaded and `strength` is 0.0 to match, so a
    caller can wire both straight into a workflow without re-deciding anything. Never
    raises - a caller that wants a typo to be fatal tests the code on the conflict.
    """
    conflicts = []
    libs = libs or load_libs()
    shelf = libs.get("loras") or {}
    style = style or {}

    want = str(lora_id or "").strip()
    rec = str(style.get("lora") or "").strip()
    explicit = bool(want)
    source = "you chose it by hand"

    def _out(file=None, ident="", card=None, s=0.0, active=False, reason=""):
        # file None and strength 0.0 move together, always. A caller that wires both into
        # a workflow without reading `active` must get a slot that is off - that is the
        # whole point of returning a resolved answer rather than a recommendation.
        return {"id": ident, "file": file if active else None,
                "strength": round(float(s or 0.0), 3) if active else 0.0,
                "active": bool(active), "reason": _one_line(reason), "source": source,
                "card": card, "conflicts": conflicts}

    # ---- which one, if any -------------------------------------------------
    if want.lower() in _LORA_OFF:
        return _out(reason=(
            "no style LoRA - %s recommends %s and you turned it off by hand."
            % (_name(style), rec)) if rec else
            "no style LoRA - you turned it off by hand.")
    if not want and rec:
        want, explicit = rec, False
        source = "the %s style card asks for it" % _name(style)
    if not want:
        return _out(reason="no style LoRA - this style is words only.")

    # An id, or the .safetensors filename off the card - films on this box were writing
    # the filename into their own JSON long before there was a library to name.
    card = shelf.get(want) or _card(libs, "loras", want)
    if card is None:
        card = next((c for c in shelf.values()
                     if str(c.get("file") or "") == want), None)
    ident = str((card or {}).get("id") or want)
    file = str((card or {}).get("file") or (want if card is None else "")) or None

    # ---- how hard ----------------------------------------------------------
    # Explicit beats the style card's recommendation beats the LoRA card's own default.
    # A style card's lora_strength is only honoured when its lora is the one in use -
    # otherwise picking a different LoRA would silently inherit a number tuned for a file
    # that is not loaded.
    s, s_from = None, ""
    if strength is not None and str(strength).strip() != "":
        try:
            s, s_from = float(strength), "you set it"
        except (TypeError, ValueError):
            conflicts.append(_conflict(
                "warning", ["style_lora"],
                "the style LoRA strength %r is not a number, so the recommended strength "
                "is used instead." % strength,
                "write a number, like 0.8.",
                "style_lora_strength_bad"))
    if s is None and not explicit and style.get("lora_strength") is not None:
        try:
            s, s_from = float(style["lora_strength"]), "%s recommends it" % _name(style)
        except (TypeError, ValueError):
            pass
    if s is None and card and card.get("strength") is not None:
        try:
            s, s_from = float(card["strength"]), "its own card recommends it"
        except (TypeError, ValueError):
            pass
    if s is None:
        s, s_from = 1.0, "nothing recommended a strength, so it runs at full"

    # ---- a strength that cannot load ---------------------------------------
    # This function promises above that `file` is None whenever nothing should be loaded
    # and that `strength` is 0.0 to match. Strength 0 broke that promise: it returned the
    # filename, active=True, and a reason reading "is loaded on top of the qwen model at
    # 0.0 - a change to the weights". That is false. ComfyUI's LoraLoader short-circuits
    # at 0 and hands the model straight back untouched, so a style LoRA at 0.0 is not a
    # faint style LoRA, it is no style LoRA at all. Telling the author their weights
    # changed when they did not is the one lie this layer must not tell, because the whole
    # reason the slot exists is that a LoRA failing to apply is otherwise invisible.
    #
    # It hid especially well on qwen-storybook-anime, the only card whose strength_range
    # starts at 0.0 - so even the out-of-range note could not fire, and a film compiled
    # with that LoRA at 0 printed nothing at all to say it would do nothing.
    #
    # Note what is NOT refused here: a NEGATIVE strength stays active. Inverting a LoRA is
    # a real technique, the strength_range note already flags it as out of range, and
    # nobody on this box has rendered one to say what it does.
    if s != s or s in (float("inf"), float("-inf")):
        _bad = _name(card) if card else want
        conflicts.append(_conflict(
            "error", ["style_lora"],
            "the style LoRA strength resolved to %s, which is not a number a sampler can "
            "use, so %s is not loaded." % (s, _bad),
            "write an ordinary number, like 1.0.",
            "style_lora_strength_bad"))
        return _out(file=None, ident=ident, s=0.0, active=False, reason=(
            "%s is not loaded - the strength resolved to %s, which is not usable."
            % (_bad, s)))
    if s == 0:
        _bad = _name(card) if card else want
        conflicts.append(_conflict(
            "warning", ["style_lora"],
            "%s is named but its strength is 0 (%s), and a LoRA at 0 is not applied at "
            "all - the renderer hands the model back untouched. The picture will be "
            "exactly what it would have been with no style LoRA named." % (_bad, s_from),
            "raise the strength, or write style_lora: none so the film says plainly that "
            "there is no style LoRA.",
            "style_lora_strength_zero"))
        return _out(file=None, ident=ident, s=0.0, active=False, reason=(
            "%s is not loaded - its strength is 0 (%s), and a LoRA at 0 changes nothing."
            % (_bad, s_from)))

    # ---- no card at all ----------------------------------------------------
    if card is None:
        if want.lower().endswith(".safetensors"):
            # Passed through rather than refused: this is how every film on this box
            # already names a style LoRA, and refusing it would break them. But the whole
            # value of this layer is the base check, and there is nothing here to check.
            conflicts.append(_conflict(
                "warning", ["style_lora"],
                "%s is a weights file with no card in studio/loras/, so nothing here "
                "knows which model it was trained on - and a LoRA on the wrong base does "
                "not fail, it just quietly attaches to nothing." % want,
                "write studio/loras/<id>.json for it carrying base_model, then name the "
                "card instead of the file.",
                "style_lora_uncarded"))
            return _out(file=want, ident=ident, s=s, active=True, reason=(
                "%s is loaded at %s (%s), unchecked - it has no card, so whether it "
                "matches the %s engine is unknown." % (want, s, s_from, engine)))
        have = ", ".join(sorted(shelf))
        conflicts.append(_conflict(
            "error", ["style_lora"],
            "there is no style LoRA called %r." % want,
            "pick one of: %s" % (have or "(nothing is authored in studio/loras/ yet)"),
            "style_lora_unknown"))
        return _out(ident=ident, s=s, reason=(
            "no style LoRA - there is no card called %r, so nothing is loaded." % want))

    nm = _name(card, ident)

    if not file:
        conflicts.append(_conflict(
            "error", ["style_lora"],
            "the card for %s does not name a weights file, so there is nothing to load."
            % nm,
            "add a file field to studio/loras/%s.json carrying the exact .safetensors "
            "name as it appears in ComfyUI's models/loras directory." % ident,
            "style_lora_no_file"))
        return _out(file=None, ident=ident, card=card, s=s, reason=(
            "%s is not loaded - its card does not name a weights file." % nm))

    # ---- the base model, which is the whole point --------------------------
    base = str(card.get("base_model") or "").strip().lower()
    routes = LORA_ENGINE.get(base, "?")
    if not base:
        conflicts.append(_conflict(
            "error", ["style_lora", "engine"],
            "the card for %s does not say which model it was trained on, and a LoRA on "
            "the wrong one does not fail - it attaches to nothing and you pay for it in "
            "render time and get the picture you would have got anyway." % nm,
            "add base_model to studio/loras/%s.json - one of: %s."
            % (ident, ", ".join(sorted(LORA_ENGINE))),
            "style_lora_no_base"))
        return _out(file=None, ident=ident, card=card, s=s, reason=(
            "%s is not loaded - its card does not say which model it was trained on."
            % nm))
    if routes == "?":
        conflicts.append(_conflict(
            "error", ["style_lora", "engine"],
            "the card for %s says it was trained on %r, which is not a base model this "
            "studio knows how to route." % (nm, base),
            "base_model on studio/loras/%s.json must be one of: %s."
            % (ident, ", ".join(sorted(LORA_ENGINE))),
            "style_lora_base_unknown"))
        return _out(file=None, ident=ident, card=card, s=s, reason=(
            "%s is not loaded - %r is not a base model this studio can route." % (nm, base)))
    if routes is None:
        fix = ("pick a LoRA whose card says base_model %s, or drop the style LoRA."
               % ("animagine, illustrious or sdxl" if engine == "anime" else "qwen"))
        if base == "qwen_edit":
            # Worth spelling out, because this is the one "wrong base" that is only half
            # wrong: a beat WITH a reference sheet renders through workflows/14, which is
            # Qwen-Image-Edit-2511, and node 7 there is this same slot. The same file
            # would be on the right base in the shots with a face in them and the wrong
            # one in the shots without, and nobody has rendered either.
            fix += (" It would be on the right base only in the shots that have a "
                    "reference sheet, which is half a film, so it is refused rather than "
                    "half-applied.")
        conflicts.append(_conflict(
            "error", ["style_lora", "engine"],
            "%s is trained on %s, so it cannot attach to the %s engine at all. It would "
            "load without an error and change nothing in the picture."
            % (nm, LORA_BASE_MEANS.get(base, base), engine),
            fix, "style_lora_wrong_base"))
        return _out(file=None, ident=ident, card=card, s=s, reason=(
            "%s is not loaded - it is trained on %s and this is the %s engine."
            % (nm, base, engine)))
    if routes != engine:
        conflicts.append(_conflict(
            "error", ["style_lora", "engine"],
            "%s is trained on %s, which is the %s engine's model, and the trained weights "
            "cannot attach to the %s engine - they are a modification of specific weights "
            "that are not there. Nothing warns you at render time: the file is passed "
            "through and quietly never read." % (nm, base, routes, engine),
            "switch the engine to %s, or pick a style LoRA whose card says base_model %s."
            % (routes, "qwen" if engine == "qwen" else "animagine, illustrious or sdxl"),
            "style_lora_wrong_base"))
        return _out(file=None, ident=ident, card=card, s=s, reason=(
            "%s is not loaded - it is trained on %s, which is the %s engine's model, and "
            "this is the %s engine." % (nm, base, routes, engine)))

    # base_model and the card's own convenience copy of the engine disagree. Reported
    # rather than obeyed, because base_model is the one the loader actually cares about.
    ceng = str(card.get("engine") or "").strip().lower()
    if ceng and ceng != routes:
        conflicts.append(_conflict(
            "warning", ["style_lora"],
            "the card for %s says engine %r but base_model %r, which routes to %r. The "
            "base model is the one that decides, so it is being treated as %s."
            % (nm, ceng, base, routes, routes),
            "fix whichever field is wrong on studio/loras/%s.json." % ident,
            "style_lora_card_disagrees"))

    # ---- things that are true even on the right base ------------------------
    if str(card.get("status") or "").strip().lower() == "unavailable":
        conflicts.append(_conflict(
            "error", ["style_lora"],
            "%s is marked unavailable: %s" % (nm, _one_line(card.get("verdict") or
                                                            card.get("note") or
                                                            "the card does not say why")),
            "pick another style LoRA, or drop it and let the style's words do the work.",
            "style_lora_unavailable"))
        return _out(file=None, ident=ident, card=card, s=s, reason=(
            "%s is not loaded - its card marks it unavailable." % nm))

    kind = str(card.get("kind") or "").strip().lower()
    if kind and kind not in LORA_STYLE_KINDS:
        conflicts.append(_conflict(
            "warning", ["style_lora"],
            "%s is a %s LoRA, not a style one, and this is the style slot. It is on the "
            "right base so it will load and it will change the picture - just not in the "
            "way the slot is named." % (nm, kind),
            "that is fine if you meant it. If you did not, pick a card whose kind is "
            "style.",
            "style_lora_wrong_kind"))

    st = str(card.get("status") or "").strip().lower()
    if st in ("untested", "weak"):
        conflicts.append(_conflict(
            "note", ["style_lora"],
            "%s is marked %s: %s" % (nm, st, _one_line(
                card.get("verdict") or card.get("note") or
                ("nobody has rendered it here yet" if st == "untested" else
                 "it was rendered and barely moved the picture"))[:220]),
            "render one keyframe with it and look, before committing a film to it.",
            "style_lora_%s" % st))

    # A trigger word is not optional decoration: a LoRA trained with one and rendered
    # without it is the leading explanation for a file that "does nothing", and nothing in
    # this studio puts a trigger into a prompt - the style's own words are all that reach
    # the model. "unknown" is the library's honest sentinel for "the file does not say and
    # nobody has found it", which is a different thing from "there is none" and gets its
    # own sentence rather than being printed as if it were the word to type.
    trig = str(card.get("trigger") or "").strip()
    if trig.lower() in ("unknown", "?"):
        conflicts.append(_conflict(
            "note", ["style_lora", "style"],
            "nobody knows whether %s has a trigger word - its card says unknown. If it "
            "was trained with one, no prompt here will ever contain it, and the LoRA will "
            "look weaker than it is." % nm,
            "if it under-performs, that is the first thing to suspect, not the strength.",
            "style_lora_trigger_unknown"))
    elif trig and trig.lower() not in ("none", "-", "n/a"):
        conflicts.append(_conflict(
            "note", ["style_lora", "style"],
            "%s was trained with the trigger phrase %r, and nothing in this studio puts a "
            "trigger into the prompt - the style's own words are all that reach it."
            % (nm, trig),
            "put %r into the style's prose, or into the film's tags, if the LoRA looks "
            "weaker than it should." % trig,
            "style_lora_trigger"))

    # ---- the two engines, and what each of them does with the slot ----------
    if engine == "anime":
        # workflows/22_anime_kf_ipadapter.json has eleven nodes and not one LoraLoader:
        # short.py SYNTHESISES node "90" for the trained character LoRA and nothing else.
        # So an anime-base style LoRA resolves clean and is then never loaded, which is
        # exactly the silent nothing this resolver exists to end.
        conflicts.append(_conflict(
            "warning", ["style_lora", "engine"],
            "%s is on the right base for the anime engine, but the anime keyframe path "
            "has no style-LoRA slot wired - workflows/22 loads a trained character LoRA "
            "and nothing else - so this file would be resolved and then never loaded."
            % nm,
            "nothing to do at your end. The qwen path is the one with the slot; on anime, "
            "the style's danbooru tags are what you have.",
            "style_lora_anime_unwired"))
        return _out(file=None, ident=ident, card=card, s=s, reason=(
            "%s is not loaded - the anime keyframe path has no style-LoRA slot." % nm))

    if character and character.get("sheet"):
        # short.py picks the workflow per beat: a beat with a reference goes to
        # workflows/14 (Qwen-Image-Edit-2511) and one without goes to workflows/13
        # (Qwen-Image 2512). Node 7 of both is this slot, so the same file lands on two
        # different checkpoints depending on whether anyone is in the shot.
        conflicts.append(_conflict(
            "note", ["style_lora", "character"],
            "shots with %s in them are rendered through the reference workflow, which "
            "runs Qwen-Image-EDIT rather than the text-to-image model %s was trained "
            "against. It is the same architecture and it will load, but nobody here has "
            "rendered it - expect the style to read differently in the shots with a face "
            "in them." % (_name(character, "your character"), nm),
            "render one keyframe with the character and one without, at the same seed, "
            "and look at them side by side before committing a film.",
            "style_lora_on_edit_model"))

    # Last, and only here: a strength that is out of range only means anything on the one
    # path where the strength is going to be used. Said any earlier it fires alongside
    # "this is not loaded at all", which is advice about a number nothing will read.
    rng = card.get("strength_range")
    if isinstance(rng, (list, tuple)) and len(rng) == 2:
        try:
            lo, hi = float(rng[0]), float(rng[1])
        except (TypeError, ValueError):
            lo = hi = None
        if lo is not None and not (lo <= s <= hi):
            conflicts.append(_conflict(
                "note", ["style_lora"],
                "%s is being run at %g and its card says it is only useful between %g "
                "and %g." % (nm, s, lo, hi),
                "move it back inside that range, or edit the range on "
                "studio/loras/%s.json if you have looked at a render outside it." % ident,
                "style_lora_strength_range"))

    return _out(file=file, ident=ident, card=card, s=s, active=True, reason=(
        "%s is loaded on top of the qwen model at %s (%s) - a change to the weights, not "
        "words in the prompt, which is the only thing measured here that moves this "
        "engine off photography." % (nm, s, s_from)))


# ---------------------------------------------------------------------------
# the conflict predicates
# ---------------------------------------------------------------------------

def _check_style(engine, style, place_card, place_text, character, template, camera,
                 output, conflicts):
    """Everything that depends on the style card alone or on style x one other layer."""
    if not style:
        return
    sid = style.get("id", "?")
    nm = _name(style, sid)
    compose = style.get("compose", "")
    status = style.get("status", "")
    verdict = _one_line(style.get("verdict", ""))
    has_person = bool(character) and template not in NO_PERSON

    # C10 - the engine cannot do this at all. The verdict says WHY, which is what stops
    # the author retrying at a different cfg.
    if status == "unavailable":
        conflicts.append(_conflict(
            "error", ["style"],
            "%s does not work. It was rendered and looked at, and this is what came back: "
            "%s" % (nm, verdict or "it did not produce the idiom it describes."),
            "pick a different style - this one is kept in the library as a record of what "
            "was tried, not as something to use.",
            "style_unavailable"))

    # status=unavailable already quotes the card's verdict, which is the same sentence the
    # compose rules below would quote. Saying it twice makes the list look longer than the
    # problem is.
    already_said = status == "unavailable"

    # C9 - indistinguishable from the control. The purest violation of this project's own
    # rule that a knob which quietly has no effect is worse than no knob.
    if compose == "inert" and not already_said:
        conflicts.append(_conflict(
            "error", ["style"],
            "%s makes no visible difference. Rendered against the no-style control at the "
            "same seed it came back the same picture. %s" % (nm, verdict),
            "choose another style; if you want this look, the card's note usually names "
            "the one that actually produces it.",
            "style_inert"))

    # C11 - status weak is a DIFFERENT field from strength weak. compile.py only ever
    # checked `strength`, so all 25 status=weak cards compiled silently.
    if status == "weak":
        conflicts.append(_conflict(
            "warning", ["style"],
            "%s barely worked when it was rendered. %s" % (nm, verdict),
            "you will pay a full generation for a small change. Look at "
            "/samples/styles/%s__%s.webp before you commit a whole film to it."
            % (sid, engine),
            "style_status_weak"))

    # C7 - the style owns the background. 16 cards, and every one of them is status=ready,
    # which is what makes this dangerous: it fires only on the good cards.
    if compose == "replaces" and (place_card or place_text):
        where = _name(place_card, place_text or "your place")
        # MEASURED, and it corrected this very message. studio/samples/layers/sheet_C.jpg
        # puts shojo_soft, wasteland, cottagecore and solarpunk over place: locker_room -
        # and all four left the locker room standing: lockers, benches, tiled floor,
        # ceiling lights and end window intact, recoloured but not replaced. sheet_G.jpg
        # isolates why. The style VERDICTS were measured by _tools/style_examples.py,
        # whose entire setting is three loose tags ("city street, buildings, overcast"),
        # and against that thin setting the styles DO delete the location - cottagecore
        # swapped the city street for a village lane. So `replaces` is conditional on how
        # many nouns the place brings, which is this project's own governing rule doing
        # exactly what it says: nouns win. A dense place card beats the style.
        dense = 0
        if place_card:
            dense = len([t for t in str(place_card.get("tags", "")).split(",")
                         if t.strip()])
        if dense >= 6:
            conflicts.append(_conflict(
                "note", ["style", "place"],
                "%s is a style that builds its own background, but %s brings %d "
                "concrete nouns and a place that specific has been measured to win. "
                "Expect the location to survive and be re-coloured rather than replaced."
                % (nm, where, dense),
                "look at studio/samples/layers/sheet_C.jpg - four of these styles over a "
                "place card, none of which deleted the room. Checked on 4 of the 16 "
                "replaces styles at one seed, so treat a style that draws a literal "
                "frame or border (art_nouveau, illuminated_manuscript) as still unproven.",
                "style_replaces_place_outweighed"))
        else:
            conflicts.append(_conflict(
                "warning", ["style", "place"],
                "%s builds its own background, and %s is thin enough that it will "
                "probably not survive. %s" % (nm, where, verdict),
                "name the setting with concrete nouns - a place CARD carries about a "
                "dozen and has been measured to hold its ground against these styles - "
                "or drop the place and let the style own the setting.",
                "style_replaces_place"))

    # C8(i) - the noun in the style's NAME gets drawn as an object, usually into the
    # subject's hands. pulp_cover deliberately named no genre furniture to test whether
    # that was the cause. It was not: the noun in the name is enough.
    # A few of the injects cards are really mis-filed camera moves, and the shot-property
    # rule below describes those far more accurately than "it adds a prop" does.
    if compose == "injects" and not already_said and sid not in SHOT_PROPERTY_STYLES:
        if has_person and status != "ready":
            conflicts.append(_conflict(
                "error", ["style", "character"],
                "%s puts an object in the frame instead of changing how the frame is "
                "drawn, usually straight into the character's hands. %s" % (nm, verdict),
                "use this only on a shot with nobody in it, or pick a different style.",
                "style_injects_prop"))
        elif has_person:
            conflicts.append(_conflict(
                "warning", ["style", "character"],
                "%s tends to add an object to the shot. %s" % (nm, verdict),
                "if the object is not in your shot description it will break continuity "
                "with the shots either side of it - check the render.",
                "style_injects_prop"))
        else:
            conflicts.append(_conflict(
                "note", ["style"],
                "%s adds an object to the frame. %s" % (nm, verdict),
                "there is nobody in this shot, so the object has nowhere awkward to land - "
                "but it will still be in the picture.",
                "style_injects_prop"))

    # C8(ii) - these are not styles. They claim a slot another layer owns, and because the
    # style text sits late in the stack it wins silently.
    if sid in SHOT_PROPERTY_STYLES:
        claims, belongs = SHOT_PROPERTY_STYLES[sid]
        sev = "warning" if not camera or camera == "static" else "error"
        conflicts.append(_conflict(
            sev, ["style", "shot"],
            "%s %s. That is a property of the SHOT, not of the drawing, so it quietly "
            "overrules what you asked the shot for." % (nm, claims),
            "%s." % belongs,
            "style_claims_shot"))

    # C21a - chibi collapses head-to-body proportion AND forces a wider framing, so it
    # cannot be a mid-shot, and tags/chibi.json lists "every character build tag" among
    # the things it fights.
    if sid == "chibi" and character:
        conflicts.append(_conflict(
            "warning", ["style", "character", "shot"],
            "chibi collapses the body to roughly two heads tall and forces a wider "
            "framing, so it cannot be a close-up or a mid-shot, and it overrides the "
            "build described on the character card.",
            "use it for a whole-body gag shot, not for coverage.",
            "style_chibi_framing"))

    # C22 - the expensive failure. A keyframe costs about 4 seconds; the clip that follows
    # it costs about 32. Catching this at selection time is roughly 8x cheaper than
    # catching it at playback.
    if output == "video":
        wf = str(style.get("works_for", ""))
        if _VIDEO_RISK_RE.search(wf):
            inferred = "INFERRED" in wf
            conflicts.append(_conflict(
                "warning", ["style"],
                "%s is expected to be unstable once it moves: %s%s"
                % (nm, _one_line(wf)[:220],
                   " (the card says this was reasoned, not measured)" if inferred else ""),
                "render the keyframes first and look at them, then commit to clips - the "
                "clip stage costs about eight times what the keyframe does.",
                "style_video_risk"))

    # D2 - measured and live: every sample image in the style library was rendered WITH
    # the card's negative_add, and every film renders WITHOUT it, because short.py sets no
    # negative on either keyframe workflow. The library's own evidence therefore does not
    # match what the pipeline produces.
    if style.get("negative_add"):
        conflicts.append(_conflict(
            "note", ["style"],
            "%s asks for extra words in the negative prompt (%s) but the renderer has no "
            "negative input wired, so those words do not reach the picture."
            % (nm, _one_line(style["negative_add"])),
            "nothing to do at your end - the sample image in the library had them and "
            "your render will not, so expect it to be slightly less clean.",
            "negative_unwired"))


def _check_engine_x_style(engine, style, conflicts):
    """C2 - the chosen engine has no text to work with."""
    if not style:
        return
    nm = _name(style)
    if engine == "anime" and not str(style.get("tags", "")).strip():
        conflicts.append(_conflict(
            "error", ["style", "engine"],
            "%s has no words for the anime engine, so choosing it changes nothing at all - "
            "you get the picture you would have got with no style." % nm,
            "this card is written for the qwen engine. Either switch the engine to qwen "
            "or pick a style that renders on anime.",
            "style_no_text_for_engine"))
    if engine == "qwen" and not str(style.get("prose", "")).strip():
        conflicts.append(_conflict(
            "error", ["style", "engine"],
            "%s has no words for the qwen engine, so choosing it changes nothing at all." % nm,
            "switch the engine to anime, or pick a style written for qwen.",
            "style_no_text_for_engine"))
    # THE HARD CEILING, measured: 20 steps at cfg 4.0 with the Lightning LoRA disabled and
    # "painting, illustration" in the negative still returned a photograph. There is no
    # prompt-side fix for this, so the message must not offer one.
    if engine == "qwen" and style.get("engine") == "anime":
        conflicts.append(_conflict(
            "warning", ["style", "engine"],
            "%s is a drawn or painted idiom and the qwen engine only makes photographs. "
            "It cannot be talked out of that - it has been tried at every setting." % nm,
            "switch the engine to anime, which is the illustration engine here and does "
            "watercolour, woodcut, ukiyo-e and oil paint.",
            "qwen_cannot_illustrate"))


def _check_character(engine, character, char_id, conflicts):
    """C4, C5, C20c, C20e - identity, and the two ways it silently fails."""
    if not character:
        return
    nm = _name(character, char_id)
    lora = character.get("lora")
    sheet = character.get("sheet")

    # C4 - THE CROSS-LAYER CONSTRAINT. short.py loads film["character_loras"] inside
    # anime_keyframe() only; the qwen branch never reads the key. compile.py emits it
    # regardless of engine, so the payload is there and nothing reads it. No crash, no
    # warning, just a worse film.
    if engine == "qwen" and lora:
        if not sheet:
            conflicts.append(_conflict(
                "error", ["character", "engine"],
                "%s has trained face weights but they only work on the anime engine, and "
                "%s has no reference sheet either - so on this engine there is nothing at "
                "all holding their face and they will be a different person every shot."
                % (nm, nm),
                "switch the engine to anime to use the trained weights, or make a "
                "reference sheet with scripts/make_sheets.py.",
                "lora_dead_no_sheet"))
        else:
            conflicts.append(_conflict(
                "warning", ["character", "engine"],
                "%s has trained face weights (%s) and they are thrown away on the qwen "
                "engine - trained weights only attach to the anime checkpoint. The face "
                "falls back to the reference sheet, which drifts more." % (nm, lora),
                "switch to an anime-engine style if holding this face matters more than "
                "the look you picked.",
                "lora_dead_on_qwen"))

    # C5 - a missing sheet is invisible until playback: IPAdapter drops to weight 0.0 and
    # the face drifts every shot.
    if engine == "anime" and not sheet:
        conflicts.append(_conflict(
            "warning", ["character"],
            "%s has no reference sheet, so nothing is holding their face and it will "
            "change between shots." % nm,
            "generate one with scripts/make_sheets.py.",
            "sheet_missing"))

    # C20c - the fallback damage ladder dresses everybody in a uniform. MANAGER is a
    # manager in a tracksuit and will be rendered in a uniform at every wear level.
    if not character.get("wear_tags"):
        conflicts.append(_conflict(
            "warning", ["character", "wear"],
            "%s has no clothes of their own on their card, so any damage level falls back "
            "to the generic ladder, which puts them in a uniform." % nm,
            "add a wear_tags list to studio/characters/%s.json describing their own "
            "clothes at each damage level." % character.get("id", char_id),
            "wear_tags_missing"))

    # C20e - "1man" is not a danbooru count tag; the count that registers is 1boy, with
    # age carried separately by "mature male". tags/1boy.json calls this out by name.
    tags = str(character.get("tags", ""))
    if re.match(r"^\s*1man\b", tags):
        conflicts.append(_conflict(
            "warning", ["character"],
            "%s starts with '1man', which the image model does not recognise as a count. "
            "Nothing tells it how many people are in the frame, so it may draw two." % nm,
            "change it to '1boy, solo, mature male' in "
            "studio/characters/%s.json." % character.get("id", char_id),
            "count_tag_wrong"))


def _check_world(engine, place_card, place_text, place_id, look, look_id, weather,
                 weather_id, lighting, lighting_id, time_txt, style, look_ids, conflicts):
    """C12-C15 - the four layers that all think they own the background."""
    place_named = _name(place_card, place_text or place_id)

    # C12 - five looks name a place. In the old tag order look sat BEFORE place, so
    # `look: neon` plus `place: locker_room` rendered a wet neon city street and the
    # place card lost. Place now goes first, and the place nouns are stripped out of the
    # look, but the author should still be told.
    if look_id in LOOK_PLACE_NOUNS and (place_card or place_text):
        conflicts.append(_conflict(
            "note", ["look", "place"],
            "the %s look also describes a location (%s). Those words were removed so %s "
            "survives; its colour and light are kept."
            % (look_id, ", ".join(LOOK_PLACE_NOUNS[look_id]), place_named),
            "nothing to do - but if you wanted the street rather than your place, drop "
            "the place instead.",
            "look_names_place"))

    # C13 - time is claimed by three layers. place.time_of_day is an authored allowlist
    # that nothing in the codebase read until now.
    tod = place_card.get("time_of_day") if place_card else None
    tl = str(time_txt or "").strip().lower()
    if tod and tl and tl not in [str(t).lower() for t in tod]:
        conflicts.append(_conflict(
            "warning", ["place", "time"],
            "%s was written for %s, and you asked for %s."
            % (place_named, " or ".join(str(t) for t in tod), tl),
            "this may still work - the card lists the times the location reads as, not a "
            "rule. Look at the render.",
            "place_time_of_day"))
    if look_id in LOOK_TIME:
        lt = LOOK_TIME[look_id]
        if tl and tl != lt:
            conflicts.append(_conflict(
                "warning", ["look", "time"],
                "the %s look puts %s in the prompt and you asked for %s, so the picture is "
                "being told two different times of day." % (look_id, lt, tl),
                "drop the time, or pick a look that does not carry one.",
                "look_time_vs_time"))
        if tod and lt not in [str(t).lower() for t in tod]:
            conflicts.append(_conflict(
                "note", ["look", "place"],
                "the %s look implies %s and %s was written for %s."
                % (look_id, lt, place_named, " or ".join(str(t) for t in tod)),
                "look at the render before committing a whole scene to it.",
                "look_time_vs_place"))

    # C14 - weather double-claims with a place that already has weather in it, and fires
    # indoors, where it either rains inside or the model relocates the scene outdoors.
    if weather:
        wid = weather.get("id", weather_id)
        if place_card:
            baked = sorted(set(m.lower() for m in
                               _WEATHER_RE.findall(str(place_card.get("tags", "")))))
            if baked:
                conflicts.append(_conflict(
                    "warning", ["weather", "place"],
                    "%s already has weather written into it (%s) and you have also asked "
                    "for %s." % (place_named, ", ".join(baked), wid),
                    "drop the weather layer and let the place carry it, or pick a place "
                    "that does not.",
                    "weather_vs_place"))
            if place_card.get("family") == "interior" and wid != "clear":
                conflicts.append(_conflict(
                    "warning", ["weather", "place"],
                    "%s is indoors, so asking for %s either puts the weather inside the "
                    "room or moves the whole shot outside." % (place_named, wid),
                    "leave the weather off an interior, or put it outside a window in the "
                    "shot description.",
                    "weather_indoors"))
        # Honest about how far this layer actually reaches.
        conflicts.append(_conflict(
            "note", ["weather"],
            "weather '%s' reaches the picture only as words in the prompt. Its numbers - "
            "intensity, wind, visibility, ground state - are read by no renderer." % wid,
            "nothing to do; the words are the part that works.",
            "weather_partial"))

    if lighting:
        lid = lighting.get("id", lighting_id)
        conflicts.append(_conflict(
            "note", ["lighting"],
            "lighting '%s' reaches the picture only as words in the prompt. Its ratio, "
            "direction and colour temperature are read by no renderer." % lid,
            "nothing to do; the words are the part that works.",
            "lighting_partial"))

    # C17 / C18 - the grade is deterministic ffmpeg applied AFTER generation, so it always
    # wins. These two are computed from the grade string, not from anyone's opinion.
    sat = _grade_saturation(look.get("grade")) if look else None
    if style and sat is not None:
        if sat < 0.7 and style.get("id") in CHROMATIC_STYLES:
            conflicts.append(_conflict(
                "warning", ["look", "style"],
                "the %s look drains the colour out of the picture after it is drawn "
                "(saturation %.2f), and %s is a style whose whole point is its colour."
                % (look_id, sat, _name(style)),
                "pick a look that keeps colour - neutral, golden, sunset, firelight - or "
                "pick a style that reads in monochrome.",
                "grade_kills_style"))
        if sat > 1.0 and _is_monochrome_style(style):
            conflicts.append(_conflict(
                "warning", ["look", "style"],
                "the %s look boosts colour (saturation %.2f) but %s draws in black and "
                "white, so there is no colour there to boost and the look does nothing."
                % (look_id, sat, _name(style)),
                "use a look that changes contrast or brightness instead - bleach, "
                "bleach_bypass or blockbuster.",
                "grade_noop_on_mono"))

    # C16 - suits_looks is an authored allowlist and it is far too sparse to gate on:
    # 87 percent of style x look pairs are simply unlisted. So an endorsement is worth
    # saying and an absence is worth nothing.
    if style and look_id and look_id in (style.get("suits_looks") or []):
        conflicts.append(_conflict(
            "note", ["style", "look"],
            "%s and the %s look were checked together and they go." % (_name(style), look_id),
            "",
            "style_look_endorsed"))

    # C23 D1 - a data bug, not a runtime condition: 19 style cards endorse a look called
    # `warm` which does not exist in studio/looks/.
    if style:
        dangling = [L for L in (style.get("suits_looks") or [])
                    if L and L not in (look_ids or set())]
        if dangling and look_ids:
            conflicts.append(_conflict(
                "note", ["style"],
                "%s recommends looks that do not exist: %s. That is a mistake on the card."
                % (_name(style), ", ".join(sorted(set(dangling)))),
                "ignore it, or fix studio/styles/%s.json." % style.get("id"),
                "suits_looks_dangling"))


def _check_shot(engine, character, emotion, wear, desc, template, conflicts):
    """C20a, C20b, C21d - the character-internal contests."""
    d = str(desc or "").lower()

    # C21d - these cannot both be true of one frame. tags/1boy.json lists "no humans" and
    # "scenery" among the things a count tag fights.
    if character and re.search(r"\bno humans\b|\bscenery\b", d):
        conflicts.append(_conflict(
            "error", ["character", "shot"],
            "this shot has a character in it and the description asks for an empty frame "
            "(%s)." % ("no humans" if "no humans" in d else "scenery"),
            "either take the character off this shot, or take 'no humans' out of the "
            "description. A shot meant to be empty should use the pillow, insert or "
            "establish template, which drop the character automatically.",
            "empty_frame_with_person"))

    if not emotion:
        return

    # C20a - the damage state owns the posture above wear 0, so the emotion's body tag is
    # dropped. That is correct, and it used to happen silently.
    if wear > 0 and emotion.get("body"):
        conflicts.append(_conflict(
            "note", ["emotion", "wear"],
            "the posture from %s (%s) was dropped because the damage level is %d and the "
            "torn-clothes description already describes how they are standing."
            % (emotion.get("id", "the emotion"), _one_line(emotion["body"]), wear),
            "set wear to 0 if the posture matters more than the damage.",
            "emotion_body_dropped"))

    # C20b - the shot description is the more specific claim about THIS frame, and it sits
    # later in the stack than the emotion, so the emotion wins a fight it should lose.
    mouth = _one_line(emotion.get("mouth", ""))
    if mouth and re.search(r"\bmouth\b|shouting|smil|teeth|lips|screaming", d):
        conflicts.append(_conflict(
            "warning", ["emotion", "shot"],
            "%s sets the mouth to '%s' and this shot describes the mouth as well, so the "
            "two disagree." % (emotion.get("id", "the emotion"), mouth),
            "the shot line is about this one frame and should win - either drop the "
            "emotion on this shot, or take the mouth out of the description.",
            "emotion_mouth_vs_shot"))


def _check_tokens(slots, libs, conflicts):
    """C24 - the highest-value check in the file, and it needs no new authoring.

    studio/tags/ holds 89 cards and every one of them carries a `fights_with` array
    written by someone who had looked at the render. After the prompt is assembled it is
    split back into its comma-separated terms and checked pairwise against that table.

    Two rules make it usable rather than noisy:
      - only CROSS-LAYER pairs are reported, and the message names the two LAYERS. "your
        lighting and your look disagree" is actionable; "backlighting fights overcast flat
        lighting" is not.
      - layers the author did not choose (the mandatory quality tokens) are skipped,
        because a warning you can do nothing about is worse than no warning.

    Six fights_with entries are prose rather than terms ("every tag naming a colour") and
    cannot match a token. The one that matters - monochrome against colour - has its own
    predicate below; the rest are left unchecked and that is a known gap.
    """
    fights = {}
    for card in (libs.get("tags") or {}).values():
        term = str(card.get("term", "")).strip().lower()
        if term:
            fights.setdefault(term, set()).update(
                str(f).strip().lower() for f in (card.get("fights_with") or []))

    seen = []          # (layer, token)
    for layer, text in slots:
        if layer in _UNCHECKED_LAYERS:
            continue
        for t in _tokens(text):
            seen.append((layer, t))

    # Grouped BY LAYER PAIR, not by term pair. One place card against one character card
    # produced three separate warnings on the first real combination this was run on
    # (scenery/1boy, no humans/1boy, no humans/solo) and they are all the same problem
    # said three ways.
    pairs = {}
    for i, (la, ta) in enumerate(seen):
        for lb, tb in seen[i + 1:]:
            if la == lb:
                continue
            if tb in fights.get(ta, ()) or ta in fights.get(tb, ()):
                key = tuple(sorted([la, lb]))
                terms = pairs.setdefault(key, [])
                pair = "'%s' against '%s'" % (ta, tb) if key[0] == la else \
                       "'%s' against '%s'" % (tb, ta)
                if pair not in terms:
                    terms.append(pair)
    for (la, lb), terms in pairs.items():
        shown = ", ".join(terms[:3])
        more = " and %d more" % (len(terms) - 3) if len(terms) > 3 else ""
        conflicts.append(_conflict(
            "warning", [la, lb],
            "your %s and your %s ask for different pictures: %s%s."
            % (la, lb, shown, more),
            "drop one side. Whichever comes earlier in the prompt wins if you do "
            "nothing, and that is usually not the one you meant.",
            "tags_fight"))

    # tags/monochrome.json fights "every tag naming a colour", which is prose and needs
    # its own predicate.
    mono_layers = [l for l, t in seen if "monochrome" in t or "greyscale" in t]
    if mono_layers:
        for layer, text in slots:
            if layer in _UNCHECKED_LAYERS or layer in mono_layers:
                continue
            hit = _COLOUR_RE.findall(str(text or ""))
            if hit:
                names = ", ".join(sorted(set(h.lower() for h in hit))[:4])
                if layer == "character":
                    # Not the same problem. A character's hair and eye colour are their
                    # identity and cannot be dropped - what happens is that the picture
                    # loses the thing that tells one character from another.
                    # studio/lighting/silhouette.json documents the same effect from the
                    # other direction: crushing the face to shape kills those tags too.
                    conflicts.append(_conflict(
                        "note", ["look", "character"],
                        "this is a black and white picture, so the colours on the "
                        "character card (%s) will not show - and colour is often how one "
                        "character is told from another." % names,
                        "nothing to do if you want monochrome; just be aware the cast may "
                        "get harder to tell apart.",
                        "mono_hides_identity"))
                else:
                    conflicts.append(_conflict(
                        "warning", sorted(set(mono_layers + [layer])),
                        "your %s asks for a black and white picture and your %s names "
                        "colours (%s)." % (mono_layers[0], layer, names),
                        "drop one of them - a greyscale image cannot show the colours.",
                        "mono_vs_colour"))
                break


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------

def _assemble_anime(ctx):
    """Danbooru tag order for animagine-xl-4.0. EARLIER AND MORE SPECIFIC WINS.

    That is measured, not assumed. With the jersey described as pristine in a character's
    `tags` and the damage appended later as "torn bloodied uniform", wear:4 rendered a
    COMPLETELY CLEAN uniform - the model resolved the contradiction in favour of the
    earlier, more specific claim. The fix was to move the garment into wear_tags so the
    damage modifies the garment noun itself, and that is why slot 5 below is one clause
    rather than a garment followed by a damage suffix.

    craft/ANIME_MODELS.md states the checkpoint's own preference as "subject first, then
    camera, then scene", which is the same shape.

    THE ONE CHANGE FROM WHAT compile.py USED TO EMIT: place now comes BEFORE look. It used
    to come after, and five of the 25 look cards name a location in their tags, so
    `look: neon` plus `place: locker_room` put a wet neon city street on screen and the
    author's place card lost from a position it could not win from.

    Returns a list of (layer, text) rather than a string, so the token conflict check can
    still tell which layer each term came from.
    """
    s = []
    ch = ctx["character"]
    if ch:
        s.append(("character", ch.get("tags", "")))
        # A card may carry its own base_tags. The global male constant is the fallback and
        # not a design choice - see MALE above.
        s.append(("character", ch.get("base_tags") or MALE))
    emo = ctx["emotion"]
    if ch and emo:
        s.append(("emotion", emo.get("face", "")))
        s.append(("emotion", emo.get("eyes", "")))
        s.append(("emotion", emo.get("mouth", "")))
        if ctx["wear"] == 0:
            # at wear 0 nothing else is describing the body, so the emotion's posture is
            # free to. above 0 the damage state owns it and two posture claims would fight.
            s.append(("emotion", emo.get("body", "")))
    if ch:
        s.append(("wear", ctx["wear_text"]))
    s.append(("shot", ctx["desc"]))
    s.append(("place", ctx["place_tags"]))
    s.append(("time", ctx["time"]))
    s.append(("weather", ctx["weather_tags"]))
    s.append(("lighting", ctx["lighting_tags"]))
    s.append(("look", ctx["look_tags"]))
    s.append(("style", ctx["style_tags"]))
    s.append(("house", ctx["house_tags"]))
    s.append(("mood", ctx["mood"]))
    s.append(("quality", Q))
    return [(l, t) for l, t in s if str(t).strip()]


def _assemble_qwen(ctx):
    """Prose flow for Qwen-Image 2512.

    The text encoder is Qwen2.5-VL-7B, a real vision-language model, so it parses
    SENTENCES and spatial language. Comma-separated tag soup does close to nothing here
    and spends the context budget, which is why four of the libraries below arrive as a
    clause rather than as tags and why the mandatory quality tokens are NOT appended -
    studio/checkpoints/qwen_image_2512.json ships quality_tags as "" on purpose.

    PROMPTING.md gives the structure this follows: subject and what it is doing, then
    setting and time of day, then lighting, then camera and lens, then colour palette,
    then medium and finish.

    THE ONE CHANGE FROM WHAT compile.py USED TO EMIT: the person now comes before the
    action. Leading with the action and then naming who is doing it is an SDXL habit; a
    VLM reads the subject first.

    KNOWN GAP: there is no camera/lens slot, because no library card carries focal length
    or depth of field, and PROMPTING.md rates focal length one of the two highest-leverage
    words in a photographic prompt. That is exactly the slot drone_aerial, tilt_shift and
    macro_photography were wrongly filed into as styles.
    """
    s = []
    ch = ctx["character"]
    if ch:
        # `prose` is a VISUAL description; `desc` on a character card is the narrative one
        # ("Has never beaten his rival"), which tells an image model nothing it can draw.
        # Fall back to the danbooru tags rather than to desc - tags at least name things
        # that exist in frame.
        s.append(("character", ch.get("prose") or ch.get("tags", "")))
    s.append(("shot", ctx["desc"]))
    emo = ctx["emotion"]
    if ch and emo:
        s.append(("emotion", ", ".join(x for x in (emo.get("face", ""), emo.get("eyes", ""),
                                                   emo.get("mouth", "")) if x)))
    if ch:
        s.append(("wear", ctx["wear_text"]))
    s.append(("place", ctx["place_prose"]))
    s.append(("time", ctx["time"]))
    s.append(("weather", ctx["weather_tags"]))
    s.append(("lighting", ctx["lighting_tags"]))
    s.append(("look", ctx["look_prose"]))
    # The film's house style is appended only if it does not contradict the engine -
    # "cel shading" on a photoreal render is the author asking for two different pictures
    # at once.
    house = ctx["house_tags"]
    if house and not any(w in house.lower() for w in
                         ("anime", "cel shad", "manga", "danbooru")):
        s.append(("house", house))
    s.append(("mood", ctx["mood"]))
    s.append(("style", ctx["style_prose"]))
    return [(l, t) for l, t in s if str(t).strip()]


# ---------------------------------------------------------------------------
# the public entry point
# ---------------------------------------------------------------------------

def resolve(libs, sel):
    """Compose one shot out of its layers.

    `sel` is the layer selection. Every key is optional and None means "not chosen":

        style       studio/styles/*.json id            chooses the engine
        style_lora  studio/loras/*.json id             a weights patch under the style.
                    Blank takes the style card's own recommendation; "none" refuses it.
        style_lora_strength   how hard, 0-1.5. Blank takes the recommended one.
        place       studio/places/*.json id, OR free text
        character   studio/characters/*.json id
        look        studio/looks/*.json id             prompt words AND an ffmpeg grade
        wear        damage level 0-4
        lighting    studio/lighting/*.json id
        weather     studio/weather/*.json id
        engine      "anime" | "qwen"                   overrides the style

    compile.py passes six more, which the wizard does not have to:

        emotion     studio/emotions/*.json id
        desc        what is happening in this shot - the single most important string
        template    shot template name, so the no-person templates drop the character
        camera      camera id, for the styles that are really camera moves
        tags        the film's free house tags
        mood        free tags
        time        night / dawn / day / dusk
        negative    the film's negative prompt
        output      "video" (default) or "still" - video adds the temporal-stability check

    Returns the POST /api/compose response shape, plus four extra keys the compiler needs:
    `tags` (the danbooru string), `prose` (the qwen string), `grade` (the look's ffmpeg
    filter) and `cards` (the resolved card dicts, so a caller does not look them up twice).

    NOTE FOR serve.py: drop `cards` before sending the response. It is JSON-safe but it is
    the full text of up to seven library cards and it would multiply the payload of an
    endpoint the wizard calls on every click.

    Every conflict message is guaranteed to be a single line, because serve.py re-derives
    the warning list for the UI by scraping compile.py stdout for lines beginning "!".
    """
    sel = dict(sel or {})
    libs = libs or load_libs()
    look_ids = set(libs.get("looks") or {})

    eng = resolve_engine(libs, sel.get("style"), sel.get("engine"))
    engine, style = eng["engine"], eng["style"]
    conflicts = list(eng["conflicts"])

    # ---- resolve the cards -------------------------------------------------
    look_id = str(sel.get("look") or "").strip()
    look = _card(libs, "looks", look_id) or {}
    lighting_id = str(sel.get("lighting") or "").strip()
    lighting = _card(libs, "lighting", lighting_id)
    weather_id = str(sel.get("weather") or "").strip()
    weather = _card(libs, "weather", weather_id)
    emotion_id = str(sel.get("emotion") or "").strip()
    emotion = _card(libs, "emotions", emotion_id)
    char_id = str(sel.get("character") or "").strip()
    character = _card(libs, "characters", char_id)
    template = str(sel.get("template") or "").strip()
    camera = str(sel.get("camera") or "").strip()
    output = str(sel.get("output") or "video").strip().lower()
    wear = _wear_level(sel.get("wear"))

    for group, ident, card in (("looks", look_id, look or None),
                               ("lighting", lighting_id, lighting),
                               ("weather", weather_id, weather),
                               ("emotions", emotion_id, emotion),
                               ("characters", char_id, character)):
        if ident and card is None:
            have = ", ".join(sorted(libs.get(group) or {}))
            # NOT group[:-1]. A blind chop turns "lighting" into "lightin" and "weather"
            # into "weathe" - which is misspelt to the author, produces codes no consumer
            # matches on, and hands the wizard a layer name it cannot colour, so the band
            # that is actually wrong never gets outlined. compile.py's lib() has the same
            # quirk and this file was written around it once already.
            one = LAYER_SINGULAR.get(group, group)
            conflicts.append(_conflict(
                "error", [one],
                "there is no %s called %r." % (one, ident),
                "pick one of: %s" % (have or "(none authored)"),
                "%s_unknown" % one))

    # `place` is an id OR free text, and it always has been - VARS documents it as
    # "studio/places/*.json id, or free text" but until now only the free-text half was
    # implemented, so a place: airship_deck landed in the prompt as the literal token
    # "airship_deck" and the card's 11 hand-tuned tags were thrown away in silence.
    place_raw = str(sel.get("place") or "").strip()
    place_card = _card(libs, "places", place_raw) if place_raw else None
    place_text = "" if place_card else place_raw

    # Free text is legitimate here, so an unknown place cannot simply be an error the way
    # an unknown look is. But "locker_rom" is not a description of anywhere - it is a
    # typo, and until now it sailed into the prompt as a literal token with no conflict
    # at all, which is the one silent failure this whole resolver exists to end. A value
    # shaped like an id (lowercase, underscores, no spaces) that is not IN the library is
    # judged a typo; anything with a space is taken as the free text it looks like.
    if place_text and re.match(r"^[a-z0-9_]+$", place_text):
        near = [p for p in sorted(libs.get("places") or {})
                if p.startswith(place_text[:4]) or place_text[:4] in p][:5]
        conflicts.append(_conflict(
            "warning", ["place"],
            "there is no place card called %r, so it goes into the prompt as that "
            "literal word." % place_text,
            ("did you mean %s?" % ", ".join(near)) if near else
            "write a description with spaces in it if you meant free text, or pick a "
            "card from studio/places/.",
            "place_looks_like_typo"))

    # A character on a no-person template is not in the shot. Those templates exist
    # precisely so the cutaway can be of a thing whose surroundings are out of frame.
    if character and template in NO_PERSON:
        character = None

    # ---- the text each layer contributes -----------------------------------
    wear_tags = (character.get("wear_tags") if character else None) or WEAR
    wear_text = wear_tags[min(wear, len(wear_tags) - 1)] if character else ""

    look_tags = str(look.get("tags", "")) if look else ""
    stripped = []
    if look_id in LOOK_PLACE_NOUNS and (place_card or place_text):
        stripped = LOOK_PLACE_NOUNS[look_id]
        look_tags = _strip_tokens(look_tags, stripped)
    look_prose = (look.get("prose") or look_tags) if look else ""

    place_tags = place_card.get("tags", "") if place_card else place_text
    place_emptied = []
    if character and place_card:
        present = [t for t in PLACE_EMPTY_NOUNS if t in _tokens(place_tags)]
        if present:
            place_emptied = present
            place_tags = _strip_tokens(place_tags, present)

    ctx = {
        "character": character,
        "emotion": emotion if character else None,
        "wear": wear,
        "wear_text": wear_text,
        "desc": str(sel.get("desc") or "").strip() or ("close-up" if character
                                                       else "scenery, no humans"),
        "place_tags": place_tags,
        "place_prose": (place_card.get("prose") or place_card.get("tags", "")
                        if place_card else place_text),
        "time": str(sel.get("time") or "").strip(),
        "weather_tags": str(weather.get("tags", "")) if weather else "",
        "lighting_tags": str(lighting.get("key", "")) if lighting else "",
        "look_tags": look_tags,
        "look_prose": look_prose,
        "style_tags": str(style.get("tags", "")) if style else "",
        "style_prose": str(style.get("prose", "")) if style else "",
        "house_tags": str(sel.get("tags") or "").strip(),
        "mood": str(sel.get("mood") or "").strip(),
    }

    anime_slots = _assemble_anime(ctx)
    qwen_slots = _assemble_qwen(ctx)
    tag_string = _join_tags(anime_slots)
    prose_string = _join_prose(qwen_slots)

    # On the qwen path the tag string is not the prompt, so the style's danbooru marks do
    # not belong in it - they would be dead text carried through the film JSON. This
    # matches what compile.py emitted before and is why `tags` is engine-conditional.
    if engine != "anime":
        tag_string = _join_tags([(l, t) for l, t in anime_slots if l != "style"])

    # ---- conflicts ---------------------------------------------------------
    _check_style(engine, style, place_card, place_text, character, template, camera,
                 output, conflicts)
    _check_engine_x_style(engine, style, conflicts)
    _check_character(engine, character, char_id, conflicts)
    _check_world(engine, place_card, place_text, place_raw, look, look_id, weather,
                 weather_id, lighting, lighting_id, ctx["time"], style, look_ids,
                 conflicts)
    _check_shot(engine, character, ctx["emotion"], wear, ctx["desc"], template, conflicts)
    _check_tokens(anime_slots if engine == "anime" else qwen_slots, libs, conflicts)

    if place_emptied:
        conflicts.append(_conflict(
            "note", ["place", "character"],
            "%s is written as an empty location (it says %s) and there is a character in "
            "this shot, so those words were removed - otherwise the picture is told there "
            "is one person in it and nobody in it at the same time."
            % (_name(place_card), " and ".join("'%s'" % t for t in place_emptied)),
            "nothing to do. If you wanted the location empty, use the pillow, insert or "
            "establish template, which take the character out.",
            "place_empty_with_person"))

    # An emotion with nobody to wear it is dropped in silence today - the whole emotion
    # block in compile.py sits inside `if who:`, so a scene that sets an emotion and
    # declares no cast loses it without a word.
    #
    # Not said on a no-person template: pillow, insert and establish exist precisely to be
    # shots with nobody in them, so dropping the emotion there is the template working,
    # not a mistake, and saying it once per cutaway drowns the case that IS a mistake.
    if emotion_id and emotion and not character and template not in NO_PERSON:
        conflicts.append(_conflict(
            "note", ["emotion", "character"],
            "the emotion '%s' does nothing here because there is nobody in this shot to "
            "feel it." % emotion_id,
            "put a character in the shot, or drop the emotion.",
            "emotion_no_character"))

    # C6 - four libraries speak only danbooru. On the qwen path their comma lists are fed
    # to a language model that wants sentences: the nouns still land, the qualities do
    # not, and the context budget is spent either way.
    if engine == "qwen":
        tagonly = [n for n, c in (("look", look if look_id else None),
                                  ("weather", weather), ("lighting", lighting),
                                  ("emotion", ctx["emotion"]))
                   if c and not c.get("prose")]
        if tagonly:
            conflicts.append(_conflict(
                "note", tagonly,
                "these layers are written as keyword lists for the drawing engine and this "
                "engine wants sentences: %s. The things they name still land; the moods "
                "and qualities mostly do not." % ", ".join(tagonly),
                "nothing to do at your end - those cards need prose written on them.",
                "tagonly_on_qwen"))
        # D3 - the fast qwen path runs the Lightning LoRA at cfg 1.0, and a CFG-distilled
        # model nearly ignores its negative prompt. Inherent to the distillation.
        if style and style.get("negative_add"):
            conflicts.append(_conflict(
                "note", ["style", "engine"],
                "on the fast qwen setting the negative prompt is nearly ignored anyway - "
                "that is built into the speed-up, not a bug.",
                "drop the Lightning LoRA and run 20 steps at cfg 2.5-4.0 if the negative "
                "has to bite; it costs about 20 seconds a frame instead of 4.5.",
                "qwen_negative_ignored"))

    # C19 - a look is applied TWICE: once as prompt words asking for the colour, once as a
    # deterministic ffmpeg grade forcing it. That is worth knowing, and it is the reason
    # authors are surprised when a look moves their location. It is NOT a conflict, so it
    # is reported in the look layer's `contributed` line ("... + the colour grade ...")
    # rather than here - as a conflict it fired on every film that sets a look, which is
    # every film, and buried the warnings that meant something.

    # ---- the LoRA ----------------------------------------------------------
    lora = character.get("lora") if character else None
    if not lora:
        lora_active, lora_reason = False, (
            "%s has no trained face weights - their face is held by the reference sheet."
            % _name(character) if character else "no character in this shot.")
    elif engine != "anime":
        # THE CROSS-LAYER CONSTRAINT, and it is the one this whole file exists to surface.
        lora_active = False
        lora_reason = ("the trained weights for %s are a modification of the anime "
                       "checkpoint and cannot attach to the qwen engine, so they are not "
                       "in play. Nothing warns you about this during a render - the file "
                       "is passed through and quietly never read." % _name(character))
    else:
        lora_active = True
        lora_reason = ("the trained weights for %s are applied on top of the anime "
                       "checkpoint, which holds their face far better than a reference "
                       "sheet does." % _name(character))

    # ---- the STYLE LoRA ----------------------------------------------------
    # Sits directly under the style, because it is the same decision made in weights
    # instead of words - and because the style card is where the recommendation comes
    # from when the author has not picked one. Its conflicts join the same list; nothing
    # about it is a separate channel.
    # `style_strength` is accepted as a second spelling of style_lora_strength because it
    # is the name the film JSON and scripts/short.py already use, and the name the wizard
    # holds in its own state. One concept, two established spellings, and rejecting one of
    # them would only mean a caller silently losing the strength they set.
    slora = resolve_style_lora(
        libs, engine, style, sel.get("style_lora"),
        sel.get("style_lora_strength") if sel.get("style_lora_strength") not in (None, "")
        else sel.get("style_strength"), character)
    conflicts.extend(slora["conflicts"])

    # ---- the negative ------------------------------------------------------
    # Order: the film's own negative, then the style's additions. The workflow file has
    # its own baseline negative in node 6 which is not visible from here.
    neg_parts = [str(sel.get("negative") or "").strip()]
    if style and style.get("negative_add"):
        neg_parts.append(str(style["negative_add"]).strip())
    negative = ", ".join(p for p in neg_parts if p)

    # A term in BOTH the positive and the negative is the picture being told to do a thing
    # and not to do it in the same breath. It happens without anyone noticing, because the
    # two halves are written by different people on different cards: shojo_soft puts
    # "monochrome" in its negative and looks/noir puts "monochrome" in its positive, and
    # picking both is an entirely reasonable-looking thing to do.
    neg_terms = set(_tokens(negative))
    if neg_terms:
        clash = {}
        for layer, text in (anime_slots if engine == "anime" else qwen_slots):
            if layer in _UNCHECKED_LAYERS:
                continue
            for t in _tokens(text):
                if t in neg_terms:
                    clash.setdefault(t, layer)
        if clash:
            who_asks = sorted(set(clash.values()))
            conflicts.append(_conflict(
                "warning", who_asks + ["negative"],
                "your %s asks for %s and the negative prompt asks to keep the same thing "
                "out, so the picture is being told to do it and not to do it."
                % (" and your ".join(who_asks),
                   ", ".join("'%s'" % t for t in sorted(clash))),
                "those words are coming out of the style card's own negative list. Pick a "
                "style or a look that does not fight itself.",
                "positive_vs_negative"))

    # ---- what each layer actually contributed ------------------------------
    slots = anime_slots if engine == "anime" else qwen_slots
    got = {}
    for layer, text in slots:
        got[layer] = (got[layer] + ", " + text) if layer in got else text

    def _contrib(layer, present, empty_reason):
        if not present:
            return None
        return got.get(layer) or empty_reason

    layers = []
    if style:
        empty = ("nothing - this style has no words for the %s engine, so the picture is "
                 "the same as it would be with no style at all" % engine)
        if style.get("compose") == "inert":
            empty = ("nothing - this style was rendered against the control and produced "
                     "no visible difference")
        layers.append({"layer": "style", "id": style.get("id", ""), "name": _name(style),
                       "contributed": _contrib("style", True, empty)})
    elif sel.get("style"):
        # This branch is reached BOTH for _control and for an id that does not exist, and
        # it used to describe the second as the first - so `style: watercolor` (the
        # American spelling, which watercolour's own card tells you to write in the
        # prompt) got a confident "this is the no-style control" alongside the error
        # saying no such style exists. The layer panel contradicted the conflict list.
        _sid = str(sel.get("style"))
        _known = _card(libs, "styles", _sid) is not None
        layers.append({"layer": "style", "id": _sid, "name": "",
                       "contributed": ("nothing - this is the no-style control, the "
                                       "baseline every style example is read against")
                       if _known else
                       ("nothing - there is no style card called %r, so this render is "
                        "the no-style control by accident rather than by choice" % _sid)})
    if slora["id"] or slora["file"]:
        # Directly under the style, because that is where it belongs in the reading order
        # and, half the time, where it came from. `contributed` says the strength, since
        # for this layer the strength IS the contribution - the same file at 0.0 and at
        # 1.5 are two different pictures.
        layers.append({
            "layer": "style_lora", "id": slora["id"],
            "name": _name(slora["card"], slora["id"]),
            "contributed": (
                "%s at strength %g (%s) - a change to the model's weights, not words in "
                "the prompt" % (slora["file"], slora["strength"], slora["source"])
                if slora["active"] else "nothing - " + slora["reason"])})
    if place_card or place_text:
        pnote = ""
        if place_emptied:
            pnote = " (%s removed, because there is a character in this shot)" % (
                " and ".join(place_emptied))
        layers.append({
            "layer": "place",
            "id": place_card.get("id", "") if place_card else "",
            "name": _name(place_card, place_text),
            "contributed": (_contrib("place", True, "nothing - this place card has no "
                                                    "words for this engine") + pnote)})
    if character:
        layers.append({"layer": "character", "id": character.get("id", char_id),
                       "name": _name(character, char_id),
                       "contributed": _contrib("character", True, "nothing")})
    elif char_id:
        layers.append({"layer": "character", "id": char_id, "name": char_id,
                       "contributed": "nothing - the %s template is a shot with nobody in "
                                      "it, so the character was left out" % template
                                      if template in NO_PERSON else "nothing"})
    if emotion_id:
        layers.append({"layer": "emotion", "id": emotion_id, "name": emotion_id,
                       "contributed": _contrib(
                           "emotion", True,
                           "nothing - there is nobody in this shot to feel it")})
    if character:
        layers.append({"layer": "wear", "id": str(wear), "name": "damage level %d" % wear,
                       "contributed": _contrib("wear", True, "nothing")})
    elif sel.get("wear"):
        layers.append({"layer": "wear", "id": str(wear), "name": "damage level %d" % wear,
                       "contributed": "nothing - damage describes a person's clothes and "
                                      "there is nobody in this shot"})
    if look_id:
        note = ""
        if stripped:
            note = " (the location words %s were removed so your place survives)" % (
                ", ".join(stripped))
        grade = look.get("grade", "")
        layers.append({
            "layer": "look", "id": look_id, "name": look_id,
            "contributed": ((got.get("look") or "no prompt words") + note +
                            (" + the colour grade %s" % grade if grade else ""))})
    if lighting:
        layers.append({"layer": "lighting", "id": lighting.get("id", lighting_id),
                       "name": lighting.get("id", lighting_id),
                       "contributed": _contrib("lighting", True, "nothing")})
    if weather:
        layers.append({"layer": "weather", "id": weather.get("id", weather_id),
                       "name": weather.get("id", weather_id),
                       "contributed": _contrib("weather", True, "nothing")})

    return {
        "engine": engine,
        "engine_reason": eng["reason"],
        "prompt": tag_string if engine == "anime" else prose_string,
        "negative": negative,
        "layers": layers,
        "conflicts": _sort_conflicts(conflicts),
        "lora": lora,
        "lora_active": lora_active,
        "lora_reason": _one_line(lora_reason),
        # The style LoRA, in the same shape as the character one above: the FILE the
        # renderer should load, the strength it should load it at, whether it is in play,
        # and one sentence saying why. `style_lora` is None and `style_lora_strength` is
        # 0.0 whenever nothing should be loaded, so a caller can wire both into a workflow
        # without re-deciding anything - which is the whole reason node 7 was allowed to
        # sit at 0.8 unnoticed for the life of this project.
        "style_lora": slora["file"],
        "style_lora_id": slora["id"],
        "style_lora_strength": slora["strength"],
        "style_lora_active": slora["active"],
        "style_lora_reason": slora["reason"],
        # ---- beyond the API contract, for compile.py ----
        "tags": tag_string,
        "prose": prose_string,
        "grade": look.get("grade", "") if look else "",
        "cards": {"style": style, "place": place_card, "character": character,
                  "look": look or None, "emotion": emotion, "lighting": lighting,
                  "weather": weather, "style_lora": slora["card"]},
    }


# ---------------------------------------------------------------------------
# self test
# ---------------------------------------------------------------------------

DEMOS = [
    ("a safe style, a place and a character with trained weights",
     {"style": "watercolour", "place": "pine_forest", "character": "VIRO",
      "look": "memory", "wear": 2, "desc": "walking away between the trunks, wide shot"}),
    ("a style that rebuilds the background, over a place",
     {"style": "shojo_soft", "place": "locker_room", "character": "VIRO", "look": "dawn"}),
    ("a style that puts a prop in frame",
     {"style": "graffiti", "place": "alley_behind_bar", "character": "RASK",
      "desc": "leaning on the wall, upper body"}),
    ("a style that does nothing at all",
     {"style": "unreal_render", "place": "rooftop_night", "character": "VIRO"}),
    ("a qwen style with a character who has trained weights",
     {"style": "cinematic_film_still", "place": "petrol_station_night", "character": "VIRO",
      "look": "sodium", "wear": 3, "desc": "standing under the canopy, medium shot"}),
    ("an anime style with a place written as free text",
     {"style": "manga_inked", "place": "empty night stadium, confetti on wet grass",
      "character": "MANAGER", "look": "golden", "emotion": "grief"}),
    ("a monochrome style under a look that boosts colour",
     {"style": "street_bw", "look": "golden", "place": "shopping_arcade",
      "character": "RASK"}),
    ("a colour style under a look that removes all colour",
     {"style": "cyberpunk_neon", "look": "noir", "place": "neon_backstreet",
      "character": "RASK", "engine": "anime"}),
    ("weather indoors, and a look that names a different place",
     {"place": "locker_room", "look": "neon", "weather": "downpour",
      "lighting": "backlit", "character": "VIRO", "time": "day"}),
    ("a style that is really a camera move",
     {"style": "drone_aerial", "place": "sea_cliff", "camera": "push"}),
    ("an anime style card that has no anime words on it",
     {"style": "comic_halftone", "place": "dive_bar", "character": "RASK"}),
    ("a qwen style forced onto the anime engine, where it has nothing to say",
     {"style": "documentary_photo", "engine": "anime", "place": "subway_platform",
      "character": "VIRO"}),
    ("a shot with nobody in it, on a template that says so",
     {"style": "ink_wash", "place": "wine_cellar", "character": "VIRO",
      "template": "insert", "emotion": "grief", "wear": 4,
      "desc": "a single dusty bottle on its side, close-up"}),
    ("nothing selected at all",
     {}),
]


def _lora_demos(libs):
    """Style-LoRA demos built from whatever is actually in studio/loras/.

    Written this way rather than as fixed ids because the library is authored separately
    from this resolver: with nothing on the shelf these produce no lines at all, and the
    moment cards exist they exercise the matching case and every mismatching one without
    anyone remembering to come back and edit a list. One demo per DISTINCT base_model,
    because base_model is the field the routing turns on.
    """
    shelf = libs.get("loras") or {}
    if not shelf:
        return []
    first = {}
    for ident, c in sorted(shelf.items()):
        first.setdefault(str(c.get("base_model") or "").strip().lower() or "(blank)",
                         ident)
    out = []
    q = first.get("qwen")
    if q:
        out.append(("a qwen style LoRA on the qwen engine - the case the slot is for",
                    {"style": "cinematic_film_still", "place": "petrol_station_night",
                     "style_lora": q}))
        out.append(("the same qwen LoRA forced onto the anime engine",
                    {"style": "watercolour", "place": "pine_forest", "style_lora": q}))
        out.append(("a qwen style LoRA in a shot with a character who has a sheet",
                    {"style": "cinematic_film_still", "place": "petrol_station_night",
                     "character": "VIRO", "style_lora": q}))
        out.append(("a qwen style LoRA run outside the strength its card allows",
                    {"style": "cinematic_film_still", "place": "dive_bar",
                     "style_lora": q, "style_lora_strength": 3.0}))
    for base, ident in sorted(first.items()):
        if base == "qwen":
            continue
        engine = "anime" if LORA_ENGINE.get(base) == "anime" else "qwen"
        style = "watercolour" if engine == "anime" else "cinematic_film_still"
        out.append(("%s %s LoRA in the style slot, on the %s engine"
                    % ("an" if base[0] in "aeiou" else "a", base, engine),
                    {"style": style, "place": "dive_bar", "style_lora": ident}))
    out.append(("a weights file named directly, with no card behind it",
                {"style": "cinematic_film_still", "place": "dive_bar",
                 "style_lora": "some_unlisted_thing.safetensors"}))
    out.append(("a style LoRA id that does not exist",
                {"style": "cinematic_film_still", "place": "dive_bar",
                 "style_lora": "no_such_lora"}))
    return out


def _demo():
    libs = load_libs()
    for title, sel in DEMOS + _lora_demos(libs):
        r = resolve(libs, sel)
        print("=" * 78)
        print(title.upper())
        print("  sel        ", json.dumps(sel))
        print("  engine     ", r["engine"], "-", r["engine_reason"])
        print("  lora       ", r["lora"], "active=%s" % r["lora_active"], "-", r["lora_reason"])
        print("  style lora ", r["style_lora"], "@%s" % r["style_lora_strength"],
              "active=%s" % r["style_lora_active"], "-", r["style_lora_reason"])
        print("  prompt     ", r["prompt"][:400])
        if r["negative"]:
            print("  negative   ", r["negative"])
        for L in r["layers"]:
            print("  layer %-10s %-22s %s" % (L["layer"], L["id"], L["contributed"][:150]))
        for c in r["conflicts"]:
            print("  [%-7s] %s" % (c["severity"], c["message"]))
            if c["fix"]:
                print("            -> %s" % c["fix"])
        print()


def main():
    import argparse
    ap = argparse.ArgumentParser(description="resolve a layer selection into a prompt")
    ap.add_argument("--demo", action="store_true", help="run over real combinations")
    ap.add_argument("--json", action="store_true", help="print the raw response")
    for k in ("style", "place", "character", "look", "wear", "lighting", "weather",
              "engine", "emotion", "desc", "template", "camera", "tags", "mood", "time",
              "style_lora", "style_lora_strength"):
        ap.add_argument("--" + k.replace("_", "-"), dest=k, default=None)
    a = ap.parse_args()
    if a.demo:
        return _demo()
    sel = {k: v for k, v in vars(a).items()
           if v is not None and k not in ("demo", "json")}
    r = resolve(load_libs(), sel)
    if a.json:
        print(json.dumps({k: v for k, v in r.items() if k != "cards"},
                         indent=2, ensure_ascii=False))
        return
    print("engine      %s - %s" % (r["engine"], r["engine_reason"]))
    print("lora        %s (active=%s) - %s" % (r["lora"], r["lora_active"], r["lora_reason"]))
    print("style lora  %s @%s (active=%s) - %s"
          % (r["style_lora"], r["style_lora_strength"], r["style_lora_active"],
             r["style_lora_reason"]))
    print("prompt      %s" % r["prompt"])
    print("negative    %s" % r["negative"])
    for L in r["layers"]:
        print("layer %-10s %-20s %s" % (L["layer"], L["id"], L["contributed"]))
    for c in r["conflicts"]:
        print("[%-7s] %s" % (c["severity"], c["message"]))
        if c["fix"]:
            print("          -> %s" % c["fix"])


if __name__ == "__main__":
    main()
