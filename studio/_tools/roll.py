#!/usr/bin/env python3
"""Roll a random job that is guaranteed to be worth rendering.

    python3 studio/_tools/roll.py image            # one image job as JSON
    python3 studio/_tools/roll.py video --seed 42  # reproducible
    python3 studio/_tools/roll.py image -n 5       # five of them
    python3 studio/_tools/roll.py --explain        # what it can draw from, and why

THE ANSWER TO "IS THERE A RANDOMIZER PROMPT". There is, and it is better than a random
sentence generator: THE LIBRARIES ARE THE RANDOMIZER. This project has 130 style cards of
which 91 were rendered, looked at and passed; 64 places each carrying prompts for both
engines; 25 colour grades, 27 emotions, 34 motions, 22 music cues, 20 sound presets and 21
castable voices. Drawing a combination from those is not a lucky dip - it is a draw from a
space where every element is known to work.

The arithmetic: 91 x 64 x 24 x 27 is 3,773,952 distinct image jobs before motions, cameras
or characters enter. Run --explain to have it counted from the cards rather than trusted
from this docstring.

WHY NOT AN LLM WRITING PROMPTS. It would produce fluent text describing things this box
cannot render, with no idea that `night` crushes to black or that a style named after an
object puts the object in the subject's hands. The cards carry that knowledge. A roll from
the cards inherits it for free.

*** EVERY QUALITY RULE THIS PROJECT MEASURED IS ENFORCED HERE, NOT LEFT TO LUCK. ***
  status=ready only. 24 weak and 12 unavailable style cards are never drawn - the
    unavailable ones are recorded failures, and shipping one is shipping a known dud.
  compose safe or replaces only. NEVER injects (the noun in the style's name becomes a prop
    in frame - graffiti hands the subject a spray can) and never inert (does nothing).
  `night` is never drawn. Measured transfer curve: luma 48 -> 0, 64 -> 1. It clips to black
    rather than darkening. moonlit, noir and cold are drawn instead.
  dolly_zoom, orbit and rack_focus are never drawn. All three are byte-identical to static -
    mean absolute pixel difference exactly 0.00.
  Framing is never full body. A full-body head at 832x1216 is ~90px, decided by an ~11x11
    latent patch, and no LoRA fixes it. close / medium-close / medium / wide only.
  Size is at least 1024 on the short edge for the same reason.
  The engine is DERIVED from the style through compose.resolve(), never guessed - 27 of the
    first 64 style cards shipped routed to the wrong engine and returned colour soup.
  A style that describes SKIN, EYES or "the subject" is given someone to draw. 16 of the 92
    drawable cards read this way; `photorealistic` over a `scenery, no humans` place put a
    man's face across 60% of an underwater city.
  Framing REPLACES the character card's own framing token rather than being prepended - two
    layers each emitting `close-up` is the same instruction twice.
  A cast character never gets a close framing over a vista place. Measured on one seed: the
    close-up first split into two subjects, then lost outright. The place wins; let it.
  Character count is enforced in the NEGATIVE. `solo` in the positive did not hold.

SEEDING. With no --seed the run seed comes from the clock, so running the same script again
gives different work. With --seed it is exactly reproducible, which is what you want when
something good comes out and you need it again.
"""
import argparse, hashlib, json, os, random, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, STUDIO)

GROUPS = ("styles", "places", "looks", "characters", "loras", "emotions", "cues",
          "weather", "lighting", "wear", "cameras", "transitions", "shots", "motions",
          "checkpoints", "sfx", "voices", "templates")

# Measured duds. Named individually so the reason travels with the exclusion.
BANNED_LOOKS = {"night"}                                   # clips to black, task #26
BANNED_CAMERAS = {"dolly_zoom", "orbit", "rack_focus"}     # byte-identical to static
FRAMINGS = ["close-up", "medium close-up", "medium shot", "wide shot"]
# Longest first so "medium close-up" is not half-matched as "close-up".
FRAMING_RE = re.compile(
    r"\b(medium close-up|medium shot|close-up|wide shot|full body|cowboy shot)\b", re.I)
SIZES = [(1024, 1536), (1216, 1664), (1536, 1024), (1664, 1216), (1344, 1344)]

# A style card that describes SKIN, EYES, HAIR or "the subject" is not describing a look -
# it is describing a person, and the model will draw one. Rolled `photorealistic` over the
# `underwater_city` place and got a sunken city with a man's face filling 60% of the frame,
# because the place said "scenery, no humans" and the style said "catchlights in the eyes"
# and the eyes won. This is the noun-as-prop rule one layer up from where we first met it.
# 16 of the 92 drawable cards read this way, so they are detected rather than listed - a new
# card written in the same voice is caught the day it lands.
SUBJECT_BOUND = re.compile(
    r"\b(skin|pores?|eyes?|eyelash|hair|face|facial|portrait|the subject|freckl|lips?"
    r"|cheek|complexion)\b", re.I)
STYLE_TEXT_FIELDS = ("prompt", "prose", "tags", "emits", "text", "qwen", "anime")


# A place written at landscape scale WINS against a framing token, measured twice on one
# seed. Asking `close-up` over `floating_islands` first produced Terra's face filling the
# left of the frame AND a second figure on a distant bridge - the model splitting the
# difference between a portrait and a vista. Adding a count to the negative removed the
# duplicate and the framing then lost outright: same seed, same cards, one figure at about
# 8% of frame height. The framing token never won either round.
#
# So the place is allowed to set the scale rather than being argued with. A vista gets a
# medium or wide shot, where it and the subject are not competing for the same canvas.
VISTA = re.compile(
    r"\b(horizon|vista|expanse|in the distance|far below|far above|sweeping|panoram\w*"
    r"|open sky|distant|valley|mountains?|desert|ocean|sea floor|skyline|plains?)\b", re.I)
PLACE_TEXT_FIELDS = ("prompt", "prose", "tags", "emits", "text", "qwen", "anime")


def is_vista(card):
    return bool(VISTA.search(
        " ".join(str(card.get(k) or "") for k in PLACE_TEXT_FIELDS)))


def wants_a_person(card):
    return bool(SUBJECT_BOUND.search(
        " ".join(str(card.get(k) or "") for k in STYLE_TEXT_FIELDS)))


def load_libs():
    libs = {}
    for g in GROUPS:
        d = os.path.join(STUDIO, g)
        libs[g] = {}
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(d, fn), encoding="utf-8") as f:
                    libs[g][fn[:-5]] = json.load(f)
            except Exception:
                pass
    return libs


def drawable_styles(libs):
    out = []
    for sid, c in libs["styles"].items():
        if sid == "_control":
            continue
        if c.get("status") != "ready":
            continue
        if c.get("compose") in ("injects", "inert"):
            continue
        out.append(sid)
    return sorted(out)


def drawable(libs, group, ready_only=True):
    out = []
    for i, c in libs.get(group, {}).items():
        if i.startswith("_"):
            continue
        if ready_only and c.get("status") in ("unavailable",):
            continue
        out.append(i)
    return sorted(out)


def _narrow(pool, want, libs, group):
    """Apply a user constraint to a pool, and REFUSE rather than silently ignoring it.

    A filter that quietly matches nothing is worse than an error: you get a full run of
    perfectly good output that is not what you asked for, and no way to tell. So an empty
    result raises here, at roll time, before any GPU is spent.
    """
    if not want:
        return pool
    want = [w.strip() for w in str(want).split(",") if w.strip()]
    got = [p for p in pool if p in want]
    if not got:
        raise SystemExit(
            "none of %s is a drawable %s.\n  drawable now: %s"
            % (", ".join(want), group, ", ".join(pool[:14]) + (" ..." if len(pool) > 14 else "")))
    return got


def roll_image(rng, libs, opt=None):
    import compose
    opt = opt or {}
    styles = drawable_styles(libs)
    if opt.get("engine"):
        # The engine is a PROPERTY OF THE STYLE, never a free choice - it is derived through
        # compose.resolve(). So asking for an engine filters the style pool rather than
        # overriding the routing, which is what stops a card going to a model that returns
        # colour soup for it.
        want = [e.strip() for e in str(opt["engine"]).split(",") if e.strip()]
        styles = [s for s in styles
                  if compose.resolve(libs, {"style": s}).get("engine") in want]
        if not styles:
            raise SystemExit("no drawable style routes to %s" % opt["engine"])
    style = rng.choice(_narrow(styles, opt.get("style"), libs, "style"))
    place = rng.choice(_narrow(drawable(libs, "places"), opt.get("place"), libs, "place"))
    looks = [l for l in drawable(libs, "looks") if l not in BANNED_LOOKS]
    look = rng.choice(looks) if rng.random() < 0.75 else None

    # Decide the SUBJECT before anything else, because the style may not leave a choice.
    cast = sorted(c for c, k in libs.get("characters", {}).items()
                  if not c.startswith("_") and k.get("status") == "ready")
    if opt.get("character"):
        cast = _narrow(cast, opt["character"], libs, "character")
    cast_rate = 1.0 if opt.get("character") else float(opt.get("cast_rate", 0.35))
    if opt.get("no_characters"):
        cast, cast_rate = [], 0.0
    needs = wants_a_person(libs["styles"][style])
    if needs and not cast:
        # No one to draw and a style that insists on a person: take a different style rather
        # than ship the collision.
        style = rng.choice([s for s in styles
                            if not wants_a_person(libs["styles"][s])] or [style])
        needs = False
    char = rng.choice(cast) if (cast and (needs or rng.random() < cast_rate)) else None

    # An emotion is a face direction. With nobody in frame it composes to nothing, so it is
    # only drawn when there is someone to wear it.
    emo = rng.choice(drawable(libs, "emotions")) if (char and rng.random() < 0.5) else None
    # A wide shot of a person puts the head in ~90px, so framing tightens when someone is
    # cast - but only as far as the place will allow. Over a vista a close-up does not hold.
    vista = is_vista(libs["places"][place])
    if char:
        allowed = ["medium shot", "wide shot"] if vista else FRAMINGS[:3]
    else:
        allowed = FRAMINGS
    framing = rng.choice(allowed)
    sizes = SIZES
    orient = opt.get("orientation")
    if orient == "portrait":
        sizes = [s for s in SIZES if s[0] < s[1]]
    elif orient == "landscape":
        sizes = [s for s in SIZES if s[0] > s[1]]
    elif orient == "square":
        sizes = [s for s in SIZES if s[0] == s[1]]
    w, h = rng.choice(sizes or SIZES)
    sel = {"style": style, "place": place, "look": look, "emotion": emo,
           "character": char}
    r = compose.resolve(libs, sel)
    errs = [c for c in r.get("conflicts", []) if c.get("severity") == "error"]
    prompt = r["prompt"]
    # REPLACE the framing, never add one. A character card carries its own framing token, so
    # prefixing produced `close-up, terra branford ... clean and unmarked, close-up,` - the
    # same instruction twice, once from each layer, which is how a layered system quietly
    # doubles up on itself.
    have = FRAMING_RE.search(prompt)
    if have:
        prompt = prompt[:have.start()] + framing + prompt[have.end():]
        framing_from = "replaced the card's own"
    elif r["engine"] == "anime":
        # Earlier and more specific wins on the tag path.
        prompt, framing_from = framing + ", " + prompt, "prefixed"
    else:
        prompt, framing_from = prompt + " " + framing.capitalize() + ".", "appended"

    neg = r.get("negative") or ""
    if char:
        # `1girl, solo` in the positive did not hold: a close-up of Terra over a wide vista
        # place came back with her face filling the left of the frame AND a second, different
        # figure standing on a bridge in the distance. A close framing and a landscape both
        # want the whole canvas, and the model settles the argument by drawing two subjects.
        # Stated in the negative as well, where a count is enforced rather than requested.
        neg = ("2girls, 2boys, multiple girls, multiple boys, multiple views, duplicate, "
               "crowd, background people, " + neg).strip(", ")
    return {
        "domain": "image", "engine": r["engine"], "style": style, "place": place,
        "look": look, "emotion": emo, "framing": framing, "character": char,
        "style_wants_a_person": needs, "place_is_vista": vista,
        # Only when compose says the weights are actually in play. A character LoRA is a
        # delta on specific base weights: TERRA's is trained on the anime checkpoint and
        # attaches to nothing on qwen, where the file is passed through and silently never
        # read. Carrying an inactive name into the recipe would be a lie on the gallery page.
        "character_lora": r.get("lora") if r.get("lora_active") else None,
        "character_lora_strength": (r.get("lora_strength")
                                    if r.get("lora_active") else None),
        "character_lora_reason": r.get("lora_reason", ""),
        "prompt": prompt, "negative": neg, "framing_from": framing_from,
        "width": w, "height": h,
        "style_lora": r.get("style_lora") if r.get("style_lora_active") else None,
        "style_lora_strength": r.get("style_lora_strength") if r.get("style_lora_active") else None,
        "engine_reason": r.get("engine_reason", ""),
        "errors": [c["message"] for c in errs],
    }


def roll_video(rng, libs, opt=None):
    opt = opt or {}
    job = roll_image(rng, libs, opt)
    motions = [m for m in libs.get("motions", {})
               if libs["motions"][m].get("status") == "ready"]
    if not motions:
        motions = list(libs.get("motions", {}))
    motions = _narrow(sorted(motions), opt.get("motion"), libs, "ready motion")
    cams = [c for c in drawable(libs, "cameras") if c not in BANNED_CAMERAS]
    cams = _narrow(cams, opt.get("camera"), libs, "camera")
    job["domain"] = "video"
    job["motion"] = rng.choice(motions) if motions else None
    job["motion_text"] = (libs["motions"].get(job["motion"], {}) or {}).get(
        "text") or (libs["motions"].get(job["motion"], {}) or {}).get("emits") or ""
    job["camera"] = rng.choice(cams) if cams else "static"
    # Capped at 8s on purpose: identity starts drifting past the measured ~10s ceiling, and
    # the cost of a clip is nearly flat in length, so a longer one buys drift, not value.
    job["seconds"] = _secs(rng, opt.get("seconds"), [4, 5, 6], 2, 8)
    return job


def _secs(rng, want, default_pool, lo, hi):
    """A duration the user asked for, clamped to what the model was measured to hold."""
    if want in (None, "", "any"):
        return rng.choice(default_pool)
    try:
        return max(lo, min(hi, int(float(want))))
    except (TypeError, ValueError):
        return rng.choice(default_pool)


def roll_music(rng, libs, opt=None):
    opt = opt or {}
    cues = _narrow(drawable(libs, "cues"), opt.get("cue"), libs, "cue")
    cue = rng.choice(cues) if cues else None
    c = libs.get("cues", {}).get(cue, {}) if cue else {}
    return {
        "domain": "music", "cue": cue,
        "prompt": c.get("tags") or c.get("prompt") or c.get("desc") or "instrumental cue",
        "seconds": _secs(rng, opt.get("seconds"), [30, 45, 60], 10, 240),
        "bpm": c.get("bpm") or 0, "key": c.get("key") or "",
    }


def roll_sfx(rng, libs, opt=None):
    opt = opt or {}
    pool = _narrow(drawable(libs, "sfx"), opt.get("preset"), libs, "sfx preset")
    s = rng.choice(pool) if pool else None
    c = libs.get("sfx", {}).get(s, {}) if s else {}
    return {"domain": "sfx", "preset": s,
            "prompt": c.get("prompt") or c.get("desc") or "a single sound",
            "seconds": _secs(rng, opt.get("seconds"), [2, 3, 4], 1, 20)}


LINES = [
    "I did not ask for any of this.", "Say it again, slower.",
    "There was a road here.", "You never told me the price.",
    "I can carry it. I have carried worse.", "Nobody is coming.",
    "It is colder than it looks.", "Put it down and walk away.",
    "I remember the shape of it, not the year.", "That is not what I said.",
]


def roll_voice(rng, libs, opt=None):
    opt = opt or {}
    castable = sorted(v for v, c in libs.get("voices", {}).items()
                      if c.get("status") not in ("blocked", "unavailable"))
    # A blocked voice cannot be requested back in. Four packs here clone real people; asking
    # for one by name reaches this filter first and finds it already gone from the pool.
    castable = _narrow(castable, opt.get("voice"), libs, "castable voice")
    v = rng.choice(castable) if castable else None
    lines = LINES
    if opt.get("lines"):
        custom = [l.strip() for l in str(opt["lines"]).split("|") if l.strip()]
        lines = custom or LINES
    return {"domain": "voice", "voice": v, "line": rng.choice(lines)}


ROLLERS = {"image": roll_image, "video": roll_video, "music": roll_music,
           "sfx": roll_sfx, "voice": roll_voice}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("domain", nargs="?", choices=sorted(ROLLERS) + ["any"], default="image")
    ap.add_argument("--seed", type=int, default=None,
                    help="omit for a clock seed - repeat runs then differ, which is the point")
    ap.add_argument("-n", type=int, default=1)
    ap.add_argument("--explain", action="store_true",
                    help="print the drawable space and the exclusions, render nothing")
    # Constraints. Each takes a comma-separated list and NARROWS the pool; naming something
    # undrawable is an error rather than a silent full-random run.
    ap.add_argument("--engine", help="anime, qwen or flux2 - filters the STYLE pool, since "
                                     "the engine is a property of the style, not a choice")
    ap.add_argument("--style"); ap.add_argument("--place")
    ap.add_argument("--character", help="cast this character in every image")
    ap.add_argument("--no-characters", action="store_true", help="scenery only")
    ap.add_argument("--cast-rate", type=float, default=0.35,
                    help="0-1, how often a character appears when none is named")
    ap.add_argument("--orientation", choices=["portrait", "landscape", "square", "any"])
    ap.add_argument("--motion"); ap.add_argument("--camera")
    ap.add_argument("--cue"); ap.add_argument("--preset"); ap.add_argument("--voice")
    ap.add_argument("--lines", help="pipe-separated lines to speak instead of the built-ins")
    ap.add_argument("--seconds", help="duration for video, music or sfx - clamped to what "
                                      "each model was measured to hold")
    a = ap.parse_args()

    opt = {k: v for k, v in vars(a).items()
           if k not in ("domain", "seed", "n", "explain") and v not in (None, False, "any")}

    libs = load_libs()
    seed = a.seed if a.seed is not None else int(time.time() * 1000) ^ os.getpid()
    rng = random.Random(seed)

    if a.explain:
        st = drawable_styles(libs)
        looks = [l for l in drawable(libs, "looks") if l not in BANNED_LOOKS]
        cams = [c for c in drawable(libs, "cameras") if c not in BANNED_CAMERAS]
        mot = [m for m in libs.get("motions", {}) if libs["motions"][m].get("status") == "ready"]
        print("DRAWABLE SPACE (measured-ready only)")
        print("  styles      %3d of %d   (weak and unavailable excluded, plus compose "
              "injects/inert)" % (len(st), len(libs["styles"]) - 1))
        print("  places      %3d" % len(drawable(libs, "places")))
        print("  looks       %3d of %d   (excluded: %s - clips to black)"
              % (len(looks), len(libs["looks"]), ", ".join(sorted(BANNED_LOOKS))))
        print("  emotions    %3d" % len(drawable(libs, "emotions")))
        print("  cameras     %3d of %d   (excluded: %s - byte-identical to static)"
              % (len(cams), len(libs["cameras"]), ", ".join(sorted(BANNED_CAMERAS))))
        print("  motions     %3d ready of %d" % (len(mot), len(libs.get("motions", {}))))
        print("  cues        %3d    sfx %3d    voices %3d castable"
              % (len(drawable(libs, "cues")), len(drawable(libs, "sfx")),
                 len([v for v, c in libs.get("voices", {}).items()
                      if c.get("status") not in ("blocked", "unavailable")])))
        combos = len(st) * len(drawable(libs, "places")) * max(1, len(looks)) * \
            max(1, len(drawable(libs, "emotions")))
        print("\n  distinct image jobs before motion or camera: %s" % f"{combos:,}")
        print("  blocked voices are never cast - four packs clone real people.")
        return

    for i in range(a.n):
        dom = a.domain
        if dom == "any":
            dom = rng.choice(sorted(ROLLERS))
        job = ROLLERS[dom](rng, libs, opt)
        job["seed"] = rng.randrange(1, 2 ** 31)
        job["roll_seed"] = seed
        job["rolled_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        job["id"] = hashlib.sha1(
            json.dumps(job, sort_keys=True).encode()).hexdigest()[:12]
        print(json.dumps(job, ensure_ascii=False))


if __name__ == "__main__":
    main()
