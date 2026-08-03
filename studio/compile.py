#!/usr/bin/env python3
"""studio/compile.py - compile a MOVIE > CHAPTER > SCENE file into a render job.

    python3 studio/compile.py studio/movies/derby-ep1.movie
    python3 studio/compile.py studio/movies/derby-ep1.movie --timeline
    python3 studio/compile.py --vars            # every variable, its default and status

THE MODEL

    MOVIE     one film. Locks the things that must not change (fps, canvas, checkpoint).
     +- CHAPTER   an act. Sets mood, look and score for everything inside it.
         +- SCENE   a unit of story in one place. This is where you do most of your work.
             +- SHOT    a single image. Usually you let the scene generate these.

Every level sets the same variables. A scene inherits from its chapter, which inherits from
the movie. Set `look: night` once on a chapter and every scene in it is night; override it
on one scene and only that scene changes.

    tags are APPENDED down the tree, everything else OVERRIDES.

That asymmetry is deliberate. If tags overrode, one scene tag would silently wipe the whole
film's art direction - the classic inheritance footgun.

THE LIBRARY

Everything selectable lives in studio/ as its own file, so it can be reused and edited
without touching code:

    transitions/   cut, dissolve, fade_black, flash, whip_pan, iris, smash, l_cut ...
    cameras/       static, push, pull, pan_l, pan_r, tilt_u, tilt_d, handheld ...
    looks/         neutral, night, golden, cold, memory, bleach ...
    shots/         establish, master, speak, react, pillow, insert, build, sakuga ...
    cues/          music and sfx presets
    characters/    one card per character: tags, sheet, voice, wear vocabulary
    places/        one card per location, so "rooftop" and "roof" cannot drift apart

Adding a transition means adding a file. No code change.

NOTHING SILENTLY DOES NOTHING

Any variable the renderer cannot honour yet still compiles - it warns once, falls back to a
named alternative, and points at studio/roadmap/ where the path to implementing it is
written down. A knob that quietly has no effect is worse than no knob.
"""
import argparse, collections, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from scene_templates import expand as expand_template   # noqa: E402

Q = "masterpiece, best quality, very aesthetic, absurdres"
MALE = "male focus, mature male, masculine"

# Damage continuity. Appended to a character's tags and never allowed to decrease,
# so a torn shirt cannot un-tear itself in the next scene. A character card may
# override this with its own `wear_tags` list - a soldier and a child should not
# share one damage vocabulary.
WEAR = ["clean uniform, neat hair",
        "sweaty, damp hair, flushed",
        "sweaty, dirt on uniform, messy hair, breathing hard",
        "torn uniform, dirt and grass stains, exhausted, dishevelled",
        "torn bloodied uniform, cut on face, utterly exhausted, trembling"]

# name -> (level it may be set at, default, what it does)
VARS = collections.OrderedDict([
    ("title",       ("movie",   None,        "film name. also seeds the render id")),
    ("fps",         ("movie",   24,          "LOCKED at movie level: concat -c copy breaks on mixed fps")),
    ("canvas",      ("movie",   "1920x1080", "LOCKED at movie level, same reason")),
    ("checkpoint",  ("movie",   "animagine-xl-4.0.safetensors", "anime SDXL model (engine: anime only)")),
    ("style",       ("movie",   "",          "studio/styles/*.json - HOW it is drawn. "
                                             "Sets the engine unless you override it")),
    ("engine",      ("movie",   "",          "anime = danbooru tags + IPAdapter faces. "
                                             "qwen = prose prompts, photoreal or "
                                             "illustrated. Normally comes from the style")),
    ("face_weight", ("movie",   0.6,         "IPAdapter strength. per-scene changes make faces drift")),
    ("seed_root",   ("movie",   None,        "stable seed base. defaults to hash(title)")),
    ("logline",     ("movie",   "",          "one sentence. if you can't write it, the film has no spine")),
    ("look",        ("any",     "neutral",   "studio/looks/*.json - prompt tags AND colour grade")),
    ("mood",        ("any",     "",          "free tags folded into every prompt at this level")),
    ("emotion",     ("any",     "",          "studio/emotions/*.json - PHYSICAL face tags, not a feeling word")),
    ("tags",        ("any",     "",          "APPENDED down the tree, never replaced")),
    ("negative",    ("any",     "bad hands, extra digits, watermark, text", "appended")),
    ("place",       ("any",     "",          "studio/places/*.json id, or free text")),
    ("time",        ("any",     "",          "night / dawn / day / dusk")),
    ("camera",      ("any",     "static",    "studio/cameras/*.json - default move for shots here")),
    ("fx",          ("any",     "",          "punch shake aberr glow flash hot ramp smear whiteout")),
    ("transition",  ("scene",   "cut",       "studio/transitions/*.json - how we ENTER this scene")),
    ("audio_lead",  ("any",     0,           "seconds to shift dialogue against picture. NEGATIVE = hear it early")),
    ("cue",         ("any",     "",          "studio/cues/*.json - music under this scene")),
    ("silence",     ("scene",   False,       "drop all score. use before an impact")),
    ("wear",        ("any",     0,           "damage continuity 0-4. never decreases")),
    ("characters",  ("scene",   [],          "who is in it. must be declared in studio/characters/")),
    ("pace",        ("scene",   "normal",    "slow / normal / fast - scales shot lengths")),
    ("clip_secs",   ("any",     6,           "seconds of video generated per shot, 1-10. "
                                             "per-shot: `shot: sakuga @8s | ...`")),
    ("type",        ("scene",   "dialogue",  "dialogue / action / montage / quiet / reveal")),
    ("captions",    ("any",     True,        "burnt-in subtitles on/off")),
    ("lipsync",     ("any",     False,       "ROADMAP: studio/roadmap/lipsync.md")),
    ("blocking",    ("scene",   "",          "ROADMAP: studio/roadmap/blocking.md")),
])

PACE = {"slow": 1.35, "normal": 1.0, "fast": 0.7}


def lib(kind, name):
    p = f"{HERE}/{kind}/{name}.json"
    if not os.path.exists(p):
        have = sorted(x[:-5] for x in os.listdir(f"{HERE}/{kind}"))
        raise SystemExit(f"unknown {kind[:-1]} {name!r}\n  available: {', '.join(have)}\n"
                         f"  (add one by creating {HERE}/{kind}/{name}.json)")
    return json.load(open(p, encoding="utf-8"))


def liblist(kind):
    """Every card in a library, by id. Missing directory is not an error - an empty
    library just means nothing of that kind has been authored yet."""
    d = f"{HERE}/{kind}"
    if not os.path.isdir(d):
        return {}
    out = {}
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".json"):
            out[fn[:-5]] = json.load(open(f"{d}/{fn}", encoding="utf-8"))
    return out


def clamp_secs(secs, bid, warns):
    """How long the generated CLIP is, in seconds.

    LTX-2.3 quantises to 8n+1 frames at 24fps, so short.py computes
    max(9, ceil(secs*24/8)*8+1) and you land on the nearest step of 1/3 s. Its practical
    ceiling before the picture drifts is about 10s (FRAME_CAP 241) - past that you chain
    from the previous frame instead.

    Cost is nearly FLAT in length: 193 frames measured 13.7s against 97 frames at 13.5s.
    So a longer clip is very nearly free, while an extra shot costs a whole keyframe plus
    a whole clip. Asking for more seconds is usually the cheap way to buy the edit room.
    """
    try:
        s = float(secs)
    except (TypeError, ValueError):
        warns.append(f"{bid}: clip_secs {secs!r} is not a number -> using 6")
        return 6.0
    if s < 1:
        warns.append(f"{bid}: clip_secs {s} is below 1s -> using 1")
        return 1.0
    if s > 10:
        warns.append(f"{bid}: clip_secs {s} exceeds LTX's ~10s drift ceiling -> clamped "
                     f"to 10. For longer, chain shots with from_prev rather than asking "
                     f"one clip to hold.")
        return 10.0
    return s


def beat_seconds(beat):
    """How long a beat actually runs once its template is expanded.

    Used to place music cues on the REAL timeline. Cue start times used to be written
    by hand (`MUSIC ep_act1 @120 240s`), which silently went wrong the moment a scene
    was inserted above them - the score kept its old offsets and drifted out of sync
    with the picture it was written for.
    """
    cuts, impact = expand_template(beat, float(beat.get("clip_secs", 4)))
    return sum(float(c["len"]) for c in cuts) + (2.0 / 24 if impact else 0.0)


def stable_seed(root, chapter, scene, i):
    """Seed derived from WHERE a shot is, never from its position in the file.

    The old scheme was `seed0 + index*7`. Inserting one scene at the top therefore re-rolled
    every keyframe after it and forced a full re-render - which makes editing expensive and
    quietly punishes exactly the authoring this format is for. Hashing the identity instead
    means adding a scene leaves every other shot byte-identical and cached.
    """
    h = hashlib.sha256(f"{root}|{chapter}|{scene}|{i}".encode()).hexdigest()
    return int(h[:8], 16)


def parse(path):
    """Indentation-free block format: `KEY: value` lines, `MOVIE/CHAPTER/SCENE id` headers."""
    movie, chapters = {}, []
    cur_ch = cur_sc = None
    for raw in open(path, encoding="utf-8"):
        line = raw.split("//")[0].strip()
        if not line:
            continue
        head = line.split()[0].upper()
        if head in ("MOVIE", "CHAPTER", "SCENE"):
            name = line.split(None, 1)[1].strip() if " " in line else ""
            if head == "MOVIE":
                movie = {"id": name, "vars": {}, }
            elif head == "CHAPTER":
                cur_ch = {"id": name, "vars": {}, "scenes": []}
                chapters.append(cur_ch)
                cur_sc = None
            else:
                cur_sc = {"id": name, "vars": {}, "beats": []}
                (cur_ch or chapters[-1])["scenes"].append(cur_sc)
            continue
        if ":" not in line:
            continue
        raw_k, _, v = line.partition(":")
        raw_k, v = raw_k.strip(), v.strip()
        k = raw_k.lower()
        target = cur_sc or cur_ch or movie
        # A bare `NAME: line of dialogue` inside a scene is DIALOGUE, not a variable.
        # Test the ORIGINAL case: an earlier version lowercased first and then asked
        # isupper(), which is always false, so every line of dialogue in the film was
        # silently swallowed and scenes compiled to zero beats.
        if cur_sc is not None and raw_k.isupper() and k not in VARS:
            cur_sc["beats"].append({"who": raw_k, "text": v})
            continue
        if k in ("shot", "beat"):
            # `shot: TEMPLATE | what is happening`
            #
            # The description is the single most important thing on the line and it did
            # not exist until now. Without it a beat's entire prompt was identity + wear
            # + look + place, so an anime checkpoint given nothing but a character
            # description renders the only thing it can: a portrait of that character
            # standing still. Every shot in the first film compiled from this format came
            # back a posed close-up, INCLUDING the sakuga beat that is supposed to be the
            # money shot of the episode.
            #
            # screenplay.py has always had this as the line under a shot; the .movie
            # format simply lost it. Same field, same purpose.
            # `shot: TEMPLATE [@camera] | what is happening`
            #
            # The optional @camera is a PER-SHOT move, overriding the scene's. Without it
            # every beat in a scene inherited one camera, so a scene could not open on a
            # static wide and then push on the reaction - which is most of what shot-level
            # direction IS. 19 of the 20 authored templates specify per-shot cameras and
            # every one of them was being silently discarded: noir_interrogation asks for
            # push / static / push / static and compiled to four statics, losing the only
            # movement the scene was built around.
            #
            # short.py has always honoured beat["camera"] (it strips the template's move
            # fx and substitutes this one). The gap was only that nothing could express it.
            tmpl, _, desc = v.partition("|")
            # `shot: TEMPLATE [@camera] [@Ns] | what is happening`
            #
            # @-tokens in any order: a camera name, or a duration like @8s. Duration is
            # how long the CLIP is generated for, which is the thing that decides how much
            # room the edit has to cut inside. It was hardcoded at 6s for every shot in
            # every film.
            tmpl, cam_, secs_ = tmpl.strip(), "", None
            while "@" in tmpl:
                tmpl, _, tok = tmpl.rpartition("@")
                tmpl, tok = tmpl.strip(), tok.strip()
                m = re.fullmatch(r"(\d+(?:\.\d+)?)s?", tok)
                if m:
                    secs_ = float(m.group(1))
                elif tok:
                    cam_ = tok
            b = {"shot": tmpl, "desc": desc.strip(), "camera": cam_}
            if secs_:
                b["clip_secs"] = secs_
            cur_sc["beats"].append(b)
            continue
        # ENFORCE the movie-level locks this file documents. They were described as
        # "LOCKED, compile error if set at chapter/scene" from the beginning and were
        # never actually checked - resolve() happily let a scene override fps, which
        # then did nothing, because film-level fps is read from movie["vars"] alone.
        # A knob that silently has no effect is exactly what this format exists to
        # prevent, and mixed fps specifically breaks `concat -c copy` AFTER the whole
        # render is spent.
        if k in VARS and VARS[k][0] == "movie" and target is not movie:
            where = "scene" if cur_sc is not None else "chapter"
            raise SystemExit(
                f"{k!r} is locked at MOVIE level and cannot be set on a {where}.\n"
                f"  found: {raw_k}: {v}\n"
                f"  why: {VARS[k][2]}")
        target["vars"][k] = v
    return movie, chapters


def resolve(movie, ch, sc):
    """scene <- chapter <- movie. tags append; everything else overrides."""
    out = {k: d for k, (_, d, _) in VARS.items()}
    tags = []
    for src in (movie["vars"], ch["vars"], sc["vars"]):
        for k, v in src.items():
            if k == "tags":
                tags.append(v)
            else:
                out[k] = v
    out["tags"] = ", ".join(t for t in tags if t)
    out["wear"] = max(int(movie["vars"].get("wear", 0)),
                      int(ch["vars"].get("wear", 0)),
                      int(sc["vars"].get("wear", 0)))
    return out


# Templates whose whole point is that there is no face in frame. Giving these a
# character reference wastes an IPAdapter pass and, worse, invites the model to put
# a person in a shot that was supposed to be a detail or an empty room.
#
# "Coverage is faked by scale contrast, not by matching" - no video model here has a
# persistent 3D space, so the cutaway MUST be of a thing whose surroundings are out
# of frame. See craft/CINEMATOGRAPHY.md.
NO_PERSON = {"pillow", "insert", "establish"}


def compile_movie(path):
    movie, chapters = parse(path)
    warns = []
    root = movie["vars"].get("seed_root") or movie["vars"].get("title", "untitled")
    cast = liblist("characters")
    cuelib = liblist("cues")
    # Which image family renders the keyframes. Movie-level, because the two want
    # opposite prompt formats and mixing them mid-film would change every face anyway.
    # STYLE COMES FIRST, and it chooses the engine.
    #
    # An image is always in some style, and that choice decides which model can render it
    # at all - the two families here want opposite prompt formats and asking the anime
    # checkpoint for photorealism is a contradiction it cannot resolve. So `style` is
    # authored and `engine` is derived from it, rather than the author having to know
    # which model does what.
    #
    # An explicit engine still wins, because a style card can be wrong and an author who
    # has looked at the output should be able to override it. When they disagree, say so
    # rather than silently picking one.
    style_id = str(movie["vars"].get("style", "")).strip()
    style = lib("styles", style_id) if style_id else {}
    engine = str(movie["vars"].get("engine", "")).strip().lower()
    if style and not engine:
        engine = str(style.get("engine", "anime")).lower()
        if engine == "either":
            engine = "anime"
    elif style and engine and style.get("engine") not in (engine, "either"):
        warns.append(f"style '{style_id}' wants engine '{style.get('engine')}' but the "
                     f"film sets engine '{engine}'. Using '{engine}' as authored - drop "
                     f"the engine line to follow the style.")
    engine = engine or "anime"
    if engine not in ("anime", "qwen"):
        raise SystemExit(f"unknown engine {engine!r}\n"
                         f"  anime  danbooru tags + IPAdapter faces (animagine-xl-4.0)\n"
                         f"  qwen   prose prompts, photoreal or illustrated (Qwen-Image 2512)")
    if style and style.get("strength") == "weak":
        warns.append(f"style '{style_id}' is marked weak: {style.get('note','')[:150]}")
    if engine != "anime":
        warns.append("engine 'qwen': character faces are held by reference SHEETS through "
                     "Qwen-Edit rather than IPAdapter, which is a weaker lock - expect more "
                     "drift between shots than the anime path gives you")
    beats = []
    used = []                 # character ids actually referenced, in first-seen order
    spoke = set()             # character ids that have a spoken line
    timeline = []             # (scene_start_s, scene_len_s, cue_id, level, silent)
    clock = 0.0

    for ch in chapters:
        for sc in ch["scenes"]:
            v = resolve(movie, ch, sc)
            look = lib("looks", v["look"])
            tr = lib("transitions", v.get("transition", "cut"))
            if tr.get("status") == "roadmap":
                warns.append(f"{sc['id']}: transition '{tr['id']}' is not implemented yet "
                             f"-> falling back to 'cut'. see studio/{tr['roadmap']}")
            cam = lib("cameras", v["camera"])
            if cam.get("status") == "roadmap":
                warns.append(f"{sc['id']}: camera '{cam['id']}' is not implemented yet "
                             f"-> falling back to 'static'. see studio/{cam['roadmap']}")
            if str(v.get("lipsync")).lower() in ("true", "yes", "1"):
                warns.append(f"{sc['id']}: lipsync is not implemented yet. "
                             f"see studio/roadmap/lipsync.md")

            # ---- cast declared on this scene -------------------------------------
            declared = [c.strip().upper() for c in str(v.get("characters", "")).split(",")
                        if c.strip()] if not isinstance(v.get("characters"), list) \
                else [str(c).strip().upper() for c in v.get("characters") or []]
            for c in declared:
                if c not in cast:
                    raise SystemExit(
                        f"{sc['id']}: unknown character {c!r}\n"
                        f"  known: {', '.join(sorted(cast)) or '(none)'}\n"
                        f"  add one by creating {HERE}/characters/{c}.json")
                if c not in used:
                    used.append(c)

            wear = int(v.get("wear", 0))
            scale = PACE.get(str(v.get("pace", "normal")), 1.0)
            scene_start, scene_len = clock, 0.0
            spoken_in_scene = False   # only the scene's FIRST line gets the boundary lead

            for i, b in enumerate(sc["beats"]):
                bid = f"{ch['id']}_{sc['id']}_{i:02d}"
                tmpl = b.get("shot", "speak" if b.get("text") else "insert")
                # A per-shot @camera beats the scene's. Validated here rather than passed
                # through, so a typo or a roadmap move fails at compile time instead of
                # quietly rendering static.
                bcam = cam
                if b.get("camera"):
                    bcam = lib("cameras", b["camera"])
                    if bcam.get("status") == "roadmap":
                        warns.append(f"{bid}: camera '{bcam['id']}' is not implemented yet "
                                     f"-> falling back to the scene's '{cam['id']}'. "
                                     f"see studio/{bcam.get('roadmap','roadmap/')}")
                        bcam = cam
                d = collections.OrderedDict(
                    id=bid, template=tmpl,
                    # per-shot @Ns wins, else the scene/chapter/movie value, else 6.
                    # LTX quantises to 8n+1 frames at 24fps and drifts past ~10s, so
                    # anything above that is clamped rather than silently mangled.
                    clip_secs=clamp_secs(b.get("clip_secs") or v.get("clip_secs") or 6,
                                         bid, warns),
                    intensity=round(1.0 / scale, 3),
                    camera=bcam["id"] if bcam.get("status") == "ready" else "static",
                    transition=tr["id"] if tr.get("status") == "ready" else "cut",
                    grade=look["grade"],
                    seed=stable_seed(root, ch["id"], sc["id"], i))

                # ---- who is in this shot ----------------------------------------
                # The speaker owns their own line; otherwise the scene's first
                # declared character carries the shot, unless the template is one
                # whose point is that nobody is in it.
                who = None
                if b.get("text"):
                    who = str(b["who"]).upper()
                    if who not in cast:
                        raise SystemExit(
                            f"{bid}: {who!r} speaks but has no character card.\n"
                            f"  short.py voices() would KeyError on cfg['voice'] mid-render.\n"
                            f"  add {HERE}/characters/{who}.json")
                    if who not in used:
                        used.append(who)
                    spoke.add(who)
                elif declared and tmpl not in NO_PERSON:
                    who = declared[0]

                card = cast.get(who or "", {})
                emo_card = {}          # the qwen prose path reads this too
                wear_tags = card.get("wear_tags") or WEAR
                if who:
                    d["ref"] = [who]
                    wear_tags = card.get("wear_tags") or WEAR
                    # ORDER IS THE WHOLE TRICK. Earlier, more specific tags win when they
                    # conflict, so: identity, then the FACE, then the garment in its
                    # damaged state, then the world.
                    #
                    # An emotion is expanded into its physical parts - "wide-eyed,
                    # parted lips, sweat" - never the feeling word. Verified: `mood:
                    # melancholy, defeat` rendered the character smiling, while the same
                    # emotion written as face tags lands reliably. The model renders
                    # nouns, not adjectives.
                    bits = [card.get("tags", ""), MALE]
                    emo = str(v.get("emotion", "")).strip()
                    if emo:
                        e = emo_card = lib("emotions", emo)
                        bits += [e.get("face", ""), e.get("eyes", ""), e.get("mouth", "")]
                        if wear == 0:
                            # at wear 0 nothing else is describing the body, so the
                            # emotion's posture is free to. above 0 the damage state
                            # owns it and two posture claims would fight.
                            bits.append(e.get("body", ""))
                        if e.get("status") == "partial" and e.get("voice_style"):
                            warns.append(
                                f"{bid}: emotion '{emo}' renders as face tags, but its "
                                f"voice_style '{e['voice_style']}' is not routed to TTS yet")
                    bits.append(wear_tags[min(wear, len(wear_tags) - 1)])
                else:
                    bits = []
                # WHAT IS HAPPENING. Placed exactly where screenplay.py places it: after
                # identity and garment-state, before the world. Until this existed a
                # beat's whole prompt was identity + wear + look + place, and an anime
                # checkpoint handed nothing but a character description renders the only
                # thing it can - that character, posed, standing still. Every shot of the
                # first film compiled from this format came back a portrait, including
                # the sakuga beat meant to be the money shot.
                #
                # A shot with no description gets a framing hint rather than nothing, so
                # the model is at least told how close to stand.
                desc = (b.get("desc") or "").strip()
                if not desc:
                    desc = "close-up" if who else "scenery, no humans"
                bits.append(desc)
                bits += [v["tags"], look["tags"], v["mood"], v["place"], v["time"], Q]
                d["tags"] = ", ".join(x for x in bits if x)
                # TWO PROMPTS, because the two model families want OPPOSITE formats and
                # feeding one the other's is how you get abstract colour shapes.
                #
                #   tags   danbooru, comma separated, for the anime SDXL path
                #   prompt prose, for the Qwen path (13_qwen_t2i_styled / 14_qwen_edit_ref)
                #
                # These used to be the same string, which was harmless only because
                # keyframe_engine was hardcoded to "anime" and the Qwen branch was
                # unreachable from an authored film. Now that a film can choose, they
                # have to differ. The character's human-readable `desc` is used here
                # rather than its danbooru tags, for the same reason.
                if engine == "anime":
                    # the style's marks sit with the other tags; on this path tags ARE
                    # the prompt
                    if style.get("tags"):
                        d["tags"] = d["tags"] + ", " + style["tags"]
                    d["prompt"] = d["tags"]
                else:
                    # `prose` on a character is a VISUAL description; `desc` is the
                    # narrative one ("Has never beaten his rival"), which tells an image
                    # model nothing it can draw. Fall back to the danbooru tags rather
                    # than to desc - tags at least name things that exist in frame.
                    who_prose = (card.get("prose") or card.get("tags", "")) if who else ""
                    emo_prose = ""
                    if who and emo_card:
                        emo_prose = ", ".join(x for x in (emo_card.get("face", ""),
                                                          emo_card.get("eyes", ""),
                                                          emo_card.get("mouth", "")) if x)
                    wear_prose = wear_tags[min(wear, len(wear_tags) - 1)] if who else ""
                    parts = [desc, who_prose, emo_prose, wear_prose,
                             v["place"], v["time"], v["mood"],
                             look.get("prose") or look.get("tags", "")]
                    # The film's house style is appended LAST and only if it does not
                    # contradict the engine - "cel shading" on a photoreal render is the
                    # author asking for two different pictures at once.
                    # NOTE the name: `house_tags`, not `style`. `style` is the style CARD
                    # resolved once for the whole film, and rebinding it here would
                    # clobber it for every later beat.
                    house_tags = v["tags"]
                    if house_tags and not any(w in house_tags.lower() for w in
                                              ("anime", "cel shad", "manga", "danbooru")):
                        parts.append(house_tags)
                    if style.get("prose"):
                        parts.append(style["prose"])
                    d["prompt"] = ". ".join(x.strip(" .,") for x in parts if x.strip(" .,")) + "."
                d["motion"] = "Slow deliberate movement only."
                if b.get("text"):
                    d["line"] = {"who": who, "text": b["text"]}
                    # Audio/picture offset. An explicit `audio_lead` always wins; the
                    # l_cut / j_cut transitions are sugar for -0.6s applied to the FIRST
                    # spoken beat of the scene, i.e. the boundary, which is the only
                    # place the overlap means anything.
                    #
                    # TERMINOLOGY WARNING: studio/transitions/l_cut.json and j_cut.json
                    # define these the OPPOSITE way round from standard film usage.
                    # Standard: an L-cut is the OUTGOING audio lagging into the next shot;
                    # a J-cut is the INCOMING audio leading its own picture. The presets
                    # say the reverse. Both are implemented here as "bring this line in
                    # early" because that is the only movement the mixer needs - the
                    # voice already plays its full length past its own shot, so the
                    # lagging half happens for free. Rename the presets if you want them
                    # to match how a cutting room would say it.
                    try:
                        lead = float(v.get("audio_lead", 0) or 0)
                    except (TypeError, ValueError):
                        lead = 0.0
                    if not lead and tr["id"] in ("l_cut", "j_cut") and not spoken_in_scene:
                        lead = -0.6
                    if lead:
                        d["audio_lead"] = round(lead, 3)
                    spoken_in_scene = True
                beats.append(d)
                scene_len += beat_seconds(d)

            clock += scene_len
            silent = str(v.get("silence")).lower() in ("true", "yes", "1")
            cue_id = str(v.get("cue", "")).strip()
            if cue_id and cue_id not in cuelib:
                raise SystemExit(f"{sc['id']}: unknown cue {cue_id!r}\n"
                                 f"  available: {', '.join(sorted(cuelib)) or '(none)'}")
            timeline.append((scene_start, scene_len, cue_id, silent))

    # ---- score: merge consecutive scenes asking for the same cue -----------------
    # Placed against the MEASURED timeline, never hand-written offsets. ACE-Step has no
    # hit-point conditioning and cannot spot to picture, so each cue is generated a
    # little long and the mix trims it in. See craft/SOUND.md.
    music, run = [], None
    for start, length, cue_id, silent in timeline:
        active = cue_id if (cue_id and not silent and
                            not cuelib.get(cue_id, {}).get("silent")) else ""
        if run and run["cue"] == active:
            run["end"] = start + length
            continue
        if run and run["cue"]:
            music.append(run)
        run = {"cue": active, "start": start, "end": start + length} if active else None
    if run and run["cue"]:
        music.append(run)

    cues_out = []
    for n, r in enumerate(music):
        c = cuelib[r["cue"]]
        span = max(4.0, r["end"] - r["start"])
        cues_out.append(collections.OrderedDict(
            prefix=f"{r['cue']}_{n:02d}", tags=c["tags"],
            seconds=int(round(span)) + 2,       # generate long, trim in the mix
            at=round(r["start"], 2), level=float(c.get("level", 1.0)),
            bpm=int(c.get("bpm", 0) or 140), key=c.get("key") or "D minor"))

    # ---- consistency warnings ---------------------------------------------------
    # This file's own rule is NOTHING SILENTLY DOES NOTHING, and a missing sheet is
    # the loudest example: IPAdapter drops to weight 0.0 and the face drifts every
    # shot, which is invisible until playback.
    for c in used:
        if not cast[c].get("sheet"):
            warns.append(f"character '{c}' has no reference sheet -> IPAdapter weight 0.0 "
                         f"on every shot of them, so their face will drift between shots. "
                         f"generate one with scripts/make_sheets.py")
        if c in spoke and not cast[c].get("voice"):
            raise SystemExit(f"character '{c}' speaks but has no voice in "
                             f"{HERE}/characters/{c}.json")

    cw, ch_ = str(movie["vars"].get("canvas", "1920x1080")).lower().split("x")
    sheets = {c: cast[c]["sheet"] for c in used if cast[c].get("sheet")}
    film = collections.OrderedDict(
        title=movie["vars"].get("title", movie["id"]),
        fps=int(movie["vars"].get("fps", 24)), canvas=[int(cw), int(ch_)],
        engine="higgs_v3", keyframe_engine=engine,
        anime_ckpt=movie["vars"].get("checkpoint", "animagine-xl-4.0.safetensors"),
        ipadapter_weight=float(movie["vars"].get("face_weight", 0.6)),
        style=movie["vars"].get("tags", ""),
        # The four registries short.py reads off the film. Their absence is exactly
        # what made every earlier .movie file uncompilable into a render.
        anime_sheets=sheets,
        sheets=sheets,
        characters={c: c for c in used},
        # Trained character LoRAs, for the cast members that have one. short.py inserts
        # these between the checkpoint and the sampler per beat. A sheet is a hint; a
        # trained LoRA is a change to the weights, and it holds in scenes the sheet
        # never covered.
        character_loras={c: cast[c]["lora"] for c in used if cast[c].get("lora")},
        voices={c: {"engine": cast[c]["voice"].split()[0],
                    "voice": cast[c]["voice"].split()[-1]}
                for c in used if cast[c].get("voice")},
        music=cues_out,
        beats=beats)
    return film, chapters, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?")
    ap.add_argument("--timeline", action="store_true")
    ap.add_argument("--vars", action="store_true")
    a = ap.parse_args()
    if a.vars:
        print(f"{'variable':13}{'level':8}{'default':32}what it does")
        for k, (lvl, dflt, why) in VARS.items():
            print(f"{k:13}{lvl:8}{str(dflt):32}{why}")
        return
    if not a.path:
        ap.error("give a .movie file, or --vars")
    film, chapters, warns = compile_movie(a.path)
    out = os.path.splitext(a.path)[0] + ".json"
    json.dump(film, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    for w in warns:
        print(f"  ! {w}")
    print(f"compiled {a.path} -> {out}")
    print(f"  {len(chapters)} chapters, "
          f"{sum(len(c['scenes']) for c in chapters)} scenes, {len(film['beats'])} beats")
    if a.timeline:
        print(f"\n{'chapter':16}{'scene':18}{'beats':>6}  look / transition")
        for c in chapters:
            for s in c["scenes"]:
                n = sum(1 for b in film["beats"] if b["id"].startswith(f"{c['id']}_{s['id']}_"))
                print(f"{c['id']:16}{s['id']:18}{n:6}  "
                      f"{s['vars'].get('look', c['vars'].get('look','neutral'))} / "
                      f"{s['vars'].get('transition','cut')}")


if __name__ == "__main__":
    main()
