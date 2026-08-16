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
    motions/       what the VIDEO model is asked for. hold_all, walk_in, hand_to_face_only,
                   confetti, cam_push ... This is the only major variable in the project
                   that had no library at all until now, and it is the one the video pass
                   actually reads - the string that decides whether the film moves.
    looks/         neutral, night, golden, cold, memory, bleach ...
    shots/         establish, master, speak, react, pillow, insert, build, sakuga ...
    cues/          music and sfx presets
    characters/    one card per character: tags, sheet, voice, wear vocabulary
    places/        one card per location, so "rooftop" and "roof" cannot drift apart
    loras/         one card per trained weights file, carrying the base model it is a
                   delta on - the field that decides whether it can be loaded at all

Adding a transition means adding a file. No code change.

NOTHING SILENTLY DOES NOTHING

Any variable the renderer cannot honour yet still compiles - it warns once, falls back to a
named alternative, and points at studio/roadmap/ where the path to implementing it is
written down. A knob that quietly has no effect is worse than no knob.

THE PROMPT IS NOT BUILT HERE

studio/compose.py takes the resolved layer selection for one shot and returns the assembled
prompt, plus a list of what those layers are going to do to each other. This file calls it;
so does the wizard, through POST /api/compose. That is the point - if the two built their
prompts separately the preview would eventually start lying about what the film will be,
and the only symptom would be a render that does not match what you were shown.

Everything about ORDER lives there too, with the measurements that established it.
"""
import argparse, collections, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
# APPEND, not insert: scripts/ has to keep priority so scene_templates resolves there.
if HERE not in sys.path:
    sys.path.append(HERE)

from scene_templates import expand as expand_template   # noqa: E402
import compose                                          # noqa: E402

# WHERE A PROMPT IS ACTUALLY BUILT: studio/compose.py, not here.
#
# This file used to assemble the prompt inline, and studio/serve.py's wizard had no way to
# show the author what their layer selection was going to produce without reimplementing
# the same concatenation - which is a copy that starts drifting the first time either side
# is touched, and drifts invisibly, because the only symptom is a preview that lies.
#
# So the ordering rules, the engine derivation, the conflict checks and the quality tokens
# all live in compose.py now, and both the wizard and this compiler call the same
# resolve(). What is left here is the .movie format: parsing, inheritance, seeds, timing,
# the score and the beat record.
Q, MALE, WEAR, NO_PERSON = compose.Q, compose.MALE, compose.WEAR, compose.NO_PERSON

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
    # The style LoRA. Movie level for the same reason `engine` is: short.py reads it off
    # the film once and patches node 7 of the qwen keyframe workflow with it, so it is one
    # slot for the whole film rather than a per-scene knob. Blank takes whatever the style
    # card recommends; "none" refuses that recommendation without editing the card.
    #
    # It is the only variable in this table that changes the WEIGHTS rather than the
    # words, and it is the only thing measured on this box that moved the qwen engine off
    # photography at all - see studio/compose.py resolve_style_lora().
    ("style_lora",  ("movie",   "",          "studio/loras/*.json id - a weights patch "
                                             "stacked under the style on the qwen "
                                             "keyframe. Normally comes from the style "
                                             "card; write 'none' to refuse it")),
    ("style_lora_strength", ("movie", "",    "how hard the style LoRA is applied, "
                                             "0-1.5. Blank takes the recommended one")),
    ("face_weight", ("movie",   0.6,         "IPAdapter strength. per-scene changes make faces drift")),
    ("seed_root",   ("movie",   None,        "stable seed base. defaults to hash(title)")),
    ("logline",     ("movie",   "",          "one sentence. if you can't write it, the film has no spine")),
    ("look",        ("any",     "neutral",   "studio/looks/*.json - prompt tags AND colour grade")),
    ("mood",        ("any",     "",          "free tags folded into every prompt at this level")),
    ("emotion",     ("any",     "",          "studio/emotions/*.json - PHYSICAL face tags, not a feeling word")),
    ("tags",        ("any",     "",          "APPENDED down the tree, never replaced")),
    ("negative",    ("any",     "bad hands, extra digits, watermark, text", "appended")),
    ("place",       ("any",     "",          "studio/places/*.json id, or free text")),
    # studio/lighting/ and studio/weather/ have been authored since this table was written
    # - 18 and 19 cards - and until now there was no variable to select one with, so
    # `lighting: neon` in a .movie file was stored and then read by nothing at all.
    # The PROMPT half of each card lands. Their numeric fields (ratio, temp, wind,
    # visibility) still reach no renderer, and compose.py says so on every use.
    ("lighting",    ("any",     "",          "studio/lighting/*.json - key light, as "
                                             "prompt words. its numbers are not wired")),
    ("weather",     ("any",     "",          "studio/weather/*.json - as prompt words. "
                                             "its numbers are not wired")),
    ("time",        ("any",     "",          "night / dawn / day / dusk")),
    ("camera",      ("any",     "static",    "studio/cameras/*.json - default move for shots here")),
    # THE ONE STRING THE VIDEO MODEL READS, and until this wave it was a constant.
    # Every beat of every film carried "Slow deliberate movement only." - measured at
    # 0.520 against an empty-prompt control of 0.614, i.e. stiller than saying nothing.
    # Per-shot: `shot: sakuga @confetti_fall | ...`, exactly like @camera and @Ns.
    ("motion",      ("any",     "",          "studio/motions/*.json id, or a sentence. "
                                             "Blank derives one from the shot line")),
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


def cam_renders(cam):
    """Can the renderer actually produce this move?

    Keyed off the card's own `renders` field rather than off `status`, because status is a
    UI word and this is a fact about scripts/short.py fx_chain(). The two came apart badly:
    dolly_zoom, orbit and rack_focus were status 'roadmap', which the per-shot dropdown
    disabled and the scene-level grid offered as a normal clickable choice - and the
    picker attached studio/samples/cameras/<id>.mp4 as a hover-playing thumbnail, which
    for those three IS static.mp4 byte for byte. A real video of nothing happening under
    the name of a camera move.

    `status` falls back for any card written before the field existed.
    """
    r = str(cam.get("renders") or "").strip()
    return r == "post" if r else cam.get("status") == "ready"


def cam_dead_warning(where, cam, fallback):
    """One line, naming the move, what you get instead, and why it cannot be built."""
    why = _one(cam.get("why_not") or cam.get("desc") or "")
    needs = _one(cam.get("needs") or "")
    doc = f" see studio/{cam['roadmap']}." if cam.get("roadmap") else ""
    return (f"{where}: camera '{cam['id']}' RENDERS NOTHING - fx_chain() has no branch for "
            f"it, so the clip would be byte-identical to static. Falling back to "
            f"'{fallback}'. {why}"
            + (f" TO BUILD IT: {needs}" if needs else "") + doc)


def _one(s):
    return " ".join(str(s or "").split())


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
            #
            # `shot: TEMPLATE [@camera] [@motion] [@Ns] | what is happening`
            #
            # A third kind of @-token: a MOTION card, which is the string the video model
            # reads. It shares the grammar with @camera rather than getting a syntax of
            # its own because they are the same kind of decision - how this shot moves -
            # made at two different tiers, and an author should not have to remember which
            # tier a name belongs to. Which library a token comes from is decided by
            # LOOKING, not by position: @push is a camera because studio/cameras/push.json
            # exists, @confetti_fall is a motion because studio/motions/ has it.
            tmpl, cam_, mot_, secs_ = tmpl.strip(), "", "", None
            while "@" in tmpl:
                tmpl, _, tok = tmpl.rpartition("@")
                tmpl, tok = tmpl.strip(), tok.strip()
                m = re.fullmatch(r"(\d+(?:\.\d+)?)s?", tok)
                if m:
                    secs_ = float(m.group(1))
                elif tok:
                    is_cam = os.path.exists(f"{HERE}/cameras/{tok}.json")
                    is_mot = os.path.exists(f"{HERE}/motions/{tok}.json")
                    if is_cam and is_mot:
                        raise SystemExit(
                            f"@{tok} is ambiguous - there is both a camera and a motion "
                            f"called {tok!r}.\n"
                            f"  rename one of studio/cameras/{tok}.json or "
                            f"studio/motions/{tok}.json.")
                    if is_mot:
                        mot_ = tok
                    else:
                        # Unknown names still land here, so lib("cameras", ...) below
                        # keeps raising the error that prints what IS available - with the
                        # motions list added, because a typo could have been either.
                        cam_ = tok
            b = {"shot": tmpl, "desc": desc.strip(), "camera": cam_, "motion": mot_}
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


# NO_PERSON is imported from compose.py at the top of this file. It holds the templates
# whose whole point is that there is no face in frame - giving those a character reference
# wastes an IPAdapter pass and, worse, invites the model to put a person in a shot that was
# supposed to be a detail or an empty room.
#
# "Coverage is faked by scale contrast, not by matching" - no video model here has a
# persistent 3D space, so the cutaway MUST be of a thing whose surroundings are out
# of frame. See craft/CINEMATOGRAPHY.md.

# Conflicts the resolver reports that THIS file already reports better. A missing sheet is
# a fact about a character across the whole film, and compile.py says it once per
# character at the end; the resolver can only see one shot at a time and would say it
# once per beat.
COMPOSE_CODES_SAID_ELSEWHERE = {"sheet_missing"}


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
    #
    # The derivation itself now lives in compose.py so the wizard and this compiler cannot
    # disagree about which model a style routes to. The warnings it returns are word for
    # word the ones this file used to emit, in the same order, because they are already
    # scraped out of stdout by studio/serve.py and shown in the UI.
    libs = compose.load_libs(HERE)
    style_id = str(movie["vars"].get("style", "")).strip()
    eng = compose.resolve_engine(libs, style_id,
                                 str(movie["vars"].get("engine", "")).strip().lower())
    engine_said = set()       # raw messages, so the per-beat dedupe still matches
    for c in eng["conflicts"]:
        # compose.py never raises - it is called from a web request too, where dying is
        # not an option. A typo in a .movie file IS fatal here, so the two codes that mean
        # "you named something that does not exist" are turned back into exits. lib() is
        # reused for the style one purely because it is the single place that prints the
        # list of what IS available.
        if c["code"] == "style_unknown":
            lib("styles", style_id)
        if c["code"] == "engine_unknown":
            # Name the value that is ACTUALLY wrong. The film's own engine var is None
            # whenever the bad value came off the style card instead, and printing that
            # told the author to go fix a line they never wrote while nothing anywhere
            # named the card that really carries it.
            authored = str(movie["vars"].get("engine", "")).strip()
            if authored:
                where = f"the film sets engine: {authored!r}"
            else:
                where = (f"studio/styles/{style_id}.json carries "
                         f"engine: {eng['style'].get('engine')!r}"
                         if eng.get("style") else "no engine was set")
            raise SystemExit(
                f"unknown engine - {where}\n"
                f"  anime  danbooru tags + IPAdapter faces (animagine-xl-4.0)\n"
                f"  qwen   prose prompts, photoreal or illustrated (Qwen-Image 2512)")
        # Same shape as the per-beat conflicts below. These used to append the bare
        # message, which dropped the fix sentence AND, because `said` is seeded from
        # this list, suppressed the per-beat copy that would have carried it - so the
        # qwen face-lock warning printed with no advice while every other line had some.
        _p = {"error": "BROKEN: ", "warning": "", "note": "fyi: "}.get(c["severity"], "")
        warns.append(_p + c["message"] + (f"  FIX: {c['fix']}" if c.get("fix") else ""))
        engine_said.add(c["message"])
    # Deliberately NOT binding a local called `style` here. eng["style"] is the style
    # CARD, and film["style"] a few hundred lines down is the movie's free house TAG
    # string - two different things one letter apart. The card is not needed again in
    # this function (compose.py does the assembling now), and this project has already
    # been bitten by that collision once.
    engine = eng["engine"]

    # ---- the style LoRA ---------------------------------------------------------
    # Resolved ONCE here, not per beat, because it is a movie-level slot: short.py patches
    # node 7 of the keyframe workflow with it and every beat gets the same one. The per-
    # beat resolve() below is still handed the same selection so the wizard and this
    # compiler cannot disagree about it - its conflicts are seeded into `said` so the
    # movie-level copy is the one that prints, exactly as the engine conflicts are.
    #
    # WHY THIS EXISTS AT ALL: node 7 of workflows/13_qwen_t2i_styled.json hard-loaded
    # qwen_image_2512_storybook_anime_lora at 0.8 on every render, and short.py only
    # overrode it when a film set style_lora, which no compiled film could - there was no
    # variable to set. Every qwen keyframe this project produced carried a style LoRA
    # nobody authored. The workflow default is now 0.0 and this is where the choice is
    # made instead.
    style_lora_id = str(movie["vars"].get("style_lora", "") or "").strip()
    slora = compose.resolve_style_lora(libs, engine, eng["style"], style_lora_id,
                                       movie["vars"].get("style_lora_strength"))
    for c in slora["conflicts"]:
        # Same rule as the style and engine ids above: compose.py reports a name that does
        # not exist as a conflict because it also answers web requests, and in a .movie
        # file a typo must not compile. lib() is not reused here because studio/loras/ may
        # not exist yet, and os.listdir on a missing directory would print a traceback
        # instead of the list of what IS available.
        if c["code"] == "style_lora_unknown":
            have = ", ".join(sorted(libs.get("loras") or {}))
            raise SystemExit(
                f"unknown style_lora {style_lora_id!r}\n"
                f"  available: {have or '(nothing is authored in studio/loras/ yet)'}\n"
                f"  (add one by creating {HERE}/loras/{style_lora_id}.json)")
        _p = {"error": "BROKEN: ", "warning": "", "note": "fyi: "}.get(c["severity"], "")
        warns.append(_p + c["message"] + (f"  FIX: {c['fix']}" if c.get("fix") else ""))
        engine_said.add(c["message"])

    # Conflicts the resolver finds per beat, collected by MESSAGE so a rule that is true
    # of the whole film is said once rather than once for each of its 12 shots. Measured:
    # derby-ep1 already emits 10 warnings and 8 of them are the same per-beat notice.
    compose_warns = collections.OrderedDict()
    said = set(engine_said)
    # Where each beat's motion came from. Printed at the end because the interesting
    # number is the RATIO - a film that derived two motions out of twenty has nineteen
    # shot lines describing a composition rather than an action, and that is a fact about
    # the writing, not about the compiler.
    motion_src_counts = collections.Counter()
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
            elif tr.get("status") == "needs_authoring":
                # THE CARD PROMISED THIS AND IT DID NOT EXIST. match_cut.json says "Set it
                # and the compiler reminds you to check the pair" - and the only status
                # this loop ever tested was "roadmap", so a needs_authoring card fell
                # straight through in silence and the beat's transition was quietly
                # rewritten to "cut" a few lines below. A card that describes a warning
                # nothing emits is the same failure as a knob that does nothing.
                warns.append(
                    f"{sc['id']}: transition '{tr['id']}' is an AUTHORING instruction, not "
                    f"an operation - nothing in the renderer can produce it. "
                    f"{tr.get('note') or ''} Check that the last shot of the previous "
                    f"scene and the first shot of this one actually rhyme; if they do not, "
                    f"this is a plain cut.")
            # Picture-identical to a cut and CORRECT that way: the whole content of these
            # cards is audio. Said once per scene so the compile log stops reading as if
            # something were broken. See studio/transitions/j_cut.json.
            if tr.get("picture") == "identical_to_cut" and tr.get("audio_lead"):
                warns.append(
                    f"fyi: {sc['id']}: transition '{tr['id']}' does nothing to the "
                    f"picture, which is correct - it is an audio edit, and it lands as a "
                    f"{tr['audio_lead']}s lead on this scene's first spoken line.")
            if tr.get("audio_drop") and not tr.get("audio_lead"):
                # smash declares audio_drop: 0.4 and NOTHING reads it - not compile.py,
                # not short.py, not epic.py. The card's own description says the contrast
                # is the whole effect, so the whole effect is missing.
                warns.append(
                    f"{sc['id']}: transition '{tr['id']}' declares audio_drop "
                    f"{tr['audio_drop']} and no renderer reads it, so the score does not "
                    f"dip across this boundary and the transition compiles to a plain "
                    f"cut. Put `silence: true` on the quiet side if you want the contrast "
                    f"today.")
            cam = lib("cameras", v["camera"])
            if not cam_renders(cam):
                warns.append(cam_dead_warning(sc["id"], cam, "static"))
                # DOWNGRADE HERE, not at the point of use. Leaving the dead card bound
                # made two downstream messages lie: a per-shot fallback announced it was
                # falling back TO dolly_zoom, and compose.py told the author their hold was
                # correct "because the camera move dolly_zoom does the moving" - a
                # sentence about a move that renders nothing at all.
                cam = lib("cameras", "static")
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
                    if not os.path.exists(f"{HERE}/cameras/{b['camera']}.json"):
                        # @-tokens can be either library, so an unknown one has to print
                        # both lists or the author is sent to fix the wrong file.
                        raise SystemExit(
                            f"{bid}: @{b['camera']} is neither a camera nor a motion.\n"
                            f"  cameras: {', '.join(sorted(x[:-5] for x in os.listdir(f'{HERE}/cameras')))}\n"
                            f"  motions: {', '.join(sorted(x[:-5] for x in os.listdir(f'{HERE}/motions'))) if os.path.isdir(f'{HERE}/motions') else '(none authored)'}")
                    bcam = lib("cameras", b["camera"])
                    if not cam_renders(bcam):
                        warns.append(cam_dead_warning(bid, bcam, cam["id"]))
                        bcam = cam
                d = collections.OrderedDict(
                    id=bid, template=tmpl,
                    # per-shot @Ns wins, else the scene/chapter/movie value, else 6.
                    # LTX quantises to 8n+1 frames at 24fps and drifts past ~10s, so
                    # anything above that is clamped rather than silently mangled.
                    clip_secs=clamp_secs(b.get("clip_secs") or v.get("clip_secs") or 6,
                                         bid, warns),
                    intensity=round(1.0 / scale, 3),
                    camera=bcam["id"] if cam_renders(bcam) else "static",
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

                if who:
                    d["ref"] = [who]

                # ---- the prompt --------------------------------------------------
                # ONE call, and it is the same call the wizard makes. Everything about
                # WHICH LAYER GOES WHERE - identity before the face before the garment
                # before the world, place before look, quality tokens last, prose flow on
                # the qwen path - lives in compose.py and is documented there with what
                # was measured to establish it.
                #
                # TWO PROMPTS come back, because the two model families want OPPOSITE
                # formats and feeding one the other's is how you get abstract colour
                # shapes:
                #   tags   danbooru, comma separated, for the anime SDXL path
                #   prompt whichever of the two this film's engine actually reads
                emo = str(v.get("emotion", "")).strip()
                # compose.py returns unknown ids as a conflict rather than dying, because
                # it also answers web requests. In a .movie file a typo must not compile.
                if emo and emo not in libs["emotions"]:
                    lib("emotions", emo)
                for key in ("lighting", "weather"):
                    want = str(v.get(key) or "").strip()
                    if want and want not in libs[key]:
                        raise SystemExit(
                            f"{bid}: unknown {key} {want!r}\n"
                            f"  available: {', '.join(sorted(libs[key])) or '(none)'}\n"
                            f"  (add one by creating {HERE}/{key}/{want}.json)")

                comp = compose.resolve(libs, {
                    "style": style_id, "engine": engine,
                    # Passed through even though the film-level answer is already in hand,
                    # because this is the call the wizard makes: if the compiler resolved
                    # the style LoRA and the resolver did not see it, the preview and the
                    # render would disagree about the one layer that changes the weights.
                    "style_lora": style_lora_id,
                    "style_lora_strength": movie["vars"].get("style_lora_strength"),
                    "place": v["place"], "time": v["time"], "mood": v["mood"],
                    "character": who, "emotion": emo, "wear": wear,
                    "look": v["look"], "lighting": v.get("lighting"),
                    "weather": v.get("weather"),
                    "desc": (b.get("desc") or "").strip(),
                    "template": tmpl, "camera": bcam.get("id"),
                    # A per-shot @motion beats the scene's, exactly as @camera does.
                    # The scene/chapter/movie value may be a card id OR a sentence; the
                    # per-shot @-token can only be a card id, because @-tokens cannot
                    # contain spaces.
                    "motion": (b.get("motion") or v.get("motion") or "").strip(),
                    "tags": v["tags"], "negative": v.get("negative"),
                    # a film always ends in clips, and the temporal-stability check is
                    # worth roughly 8x what it costs to run: a keyframe measured 4.1s a
                    # beat and the clip that follows it measured 32.1s.
                    "output": "video"})
                d["tags"] = comp["tags"]
                d["prompt"] = comp["prompt"]
                # ONTO THE BEAT, not only into the prompt. The emotion reached the
                # composer - which is why the face renders - and stopped there, so no
                # compiled film carried it and the voice stage had nothing to look up.
                if emo:
                    d["emotion"] = emo
                for c in comp["conflicts"]:
                    if c["code"] in COMPOSE_CODES_SAID_ELSEWHERE:
                        continue
                    if c["message"] in said:
                        continue
                    compose_warns[c["message"]] = c

                # The emotion cards carry a voice_style that TTS does not read yet. This
                # one stays here rather than moving into the resolver because it names the
                # BEAT, and a warning that can point at one shot should.
                # This used to say voice_style "is not routed to TTS yet", which was
                # true and is now only half true: IndexTTS-2 takes an emotion vector and
                # the beat's emotion drives it. higgs_v3 has no such input, so the note
                # names the engine instead of claiming nothing acts on it.
                e = comp["cards"]["emotion"] or {}
                if who and e.get("voice_style"):
                    import sys as _sys
                    _sys.path.insert(0, f"{HERE}/_tools")
                    try:
                        import voice_emotion as _ve
                        known = _ve.vector(emo) is not None
                    except Exception:
                        known = False
                    if not known:
                        warns.append(
                            f"{bid}: emotion '{emo}' has a voice_style "
                            f"'{e['voice_style']}' but no entry in voice_emotion.TABLE, "
                            f"so the read will not change")
                # ---- what the VIDEO model is asked for ---------------------------
                # This line used to read:
                #
                #     d["motion"] = "Slow deliberate movement only."
                #
                # It was the ONLY assignment to `motion` in the compiler, so every beat of
                # every film ever produced here carried those five words. They measured
                # 0.520 against an empty-prompt control of 0.614 - one of the three
                # stillest cells in an 81-clip sweep. The app's stated purpose is precise
                # video generation and its video prompt was a constant that asked for
                # nothing, in a project where the video pass costs about 8x the keyframe.
                #
                # It now comes from compose.resolve(), which means the wizard's preview
                # and the thumbnail renderer answer the same question the same way. See
                # compose.resolve_motion() for the ladder and the measurements behind it.
                d["motion"] = comp["motion"]
                d["motion_src"] = (f"{comp['motion_source']}:{comp['motion_id']}"
                                   if comp["motion_id"] else
                                   f"{comp['motion_source']}:{comp['motion_reason']}")
                motion_src_counts[comp["motion_source"]] += 1
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
                    # Read off the CARD rather than off a hardcoded pair of names, so the
                    # -0.6 lives in one place - studio/transitions/*.json - and a new
                    # audio-edit transition is a file rather than a code change, which is
                    # what this library promises everywhere else.
                    if not lead and not spoken_in_scene:
                        try:
                            lead = float(tr.get("audio_lead") or 0)
                        except (TypeError, ValueError):
                            lead = 0.0
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
            bpm=int(c.get("bpm") or 0), key=c.get("key") or ""))

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

    # ---- what the layers do to each other ---------------------------------------
    # Last, and deduplicated, because these are properties of the SELECTION rather than
    # of one shot: a style that rebuilds the background does it in all twelve beats, and
    # twelve identical lines would bury the nine warnings above them. Severity is carried
    # in the text rather than in a separate channel because there is only one channel -
    # studio/serve.py scrapes these lines out of stdout by their "!" prefix.
    #
    # NOTHING HERE FAILS THE COMPILE, even at severity "error". A film that renders badly
    # is still a film the author may want to look at, and the alternative - refusing to
    # compile something that compiled yesterday - breaks every existing .movie the first
    # time a new rule is added. The wizard, which can offer a fix before anything is
    # spent, is where an error should stop you.
    for msg, c in compose_warns.items():
        prefix = {"error": "BROKEN: ", "warning": "", "note": "fyi: "}.get(c["severity"], "")
        warns.append(prefix + msg + (f"  FIX: {c['fix']}" if c["fix"] else ""))

    cw, ch_ = str(movie["vars"].get("canvas", "1920x1080")).lower().split("x")
    # A REFERENCE SHEET IMPORTS ITS STYLE AS FORCEFULLY AS ITS IDENTITY. Measured: the
    # qwen edit path fed the ANIME sheet returned flat cel illustration in 4 of 4 places
    # even with "waist-up photograph" in the prompt; fed a PHOTOGRAPHIC sheet of the same
    # character, same prompt and same seeds, it returned a photograph in 4 of 4 with the
    # place intact. The only difference was which png node 8 loads. So the sheet has to
    # follow the engine, and picking it by engine is the whole fix.
    def _sheet_for(c):
        card = cast[c]
        if engine == "qwen" and card.get("sheet_photo"):
            return card["sheet_photo"]
        return card.get("sheet")

    sheets = {c: _sheet_for(c) for c in used if _sheet_for(c)}
    # Nothing silently does nothing: a photographic film running off an anime sheet still
    # renders, it just renders illustration, and that is invisible until playback.
    if engine == "qwen":
        for c in used:
            if cast[c].get("sheet") and not cast[c].get("sheet_photo"):
                warns.append(
                    f"character '{c}' has only an ANIME reference sheet and this film "
                    f"renders on the qwen engine. A sheet imports its style as hard as its "
                    f"identity, so every shot of them will come back as illustration no "
                    f"matter what the prompt asks for - measured at 4 of 4 places.  "
                    f"FIX: build a photographic sheet with "
                    f"python3 studio/_tools/qwen_sheet.py {c}  and it will be used here.")
    film = collections.OrderedDict(
        title=movie["vars"].get("title", movie["id"]),
        fps=int(movie["vars"].get("fps", 24)), canvas=[int(cw), int(ch_)],
        engine="higgs_v3", keyframe_engine=engine,
        anime_ckpt=movie["vars"].get("checkpoint", "animagine-xl-4.0.safetensors"),
        ipadapter_weight=float(movie["vars"].get("face_weight", 0.6)),
        style=movie["vars"].get("tags", ""),
        # The style LoRA, and ONLY when it is actually going to be loaded. short.py reads
        # these two keys and patches node 7 of the qwen keyframe workflow with them; a
        # film that names one that cannot attach - wrong base, no card, anime engine -
        # emits nothing here, so the slot stays at the workflow's 0.0 rather than loading
        # a file that would do nothing but cost time. The compile still warns, loudly.
        # These are the key names films/*.json and scripts/epic.py, make_sheets.py and
        # style_ab.py already use, which is why `style_strength` is not `style_lora_...`.
        **({"style_lora": slora["file"], "style_strength": slora["strength"]}
           if slora["active"] else {}),
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
        # AND THE STRENGTH TO LOAD EACH AT, which until now no authored film could set.
        # short.py defaulted every character LoRA to 0.85; 0.85 was measured on this box to
        # collapse NIKA's sunlit field into a dark grey void, and 0.5 to keep both her face
        # and the scene. The number lives on the card as `lora_strength_measured` because
        # it is a property of the trained weights - of how far the training backdrop sits
        # from the target scene - not of the film. Absent, short.py keeps 0.85.
        character_lora_weights={c: float(cast[c]["lora_strength_measured"])
                                for c in used
                                if cast[c].get("lora")
                                and cast[c].get("lora_strength_measured") is not None},
        voices={c: {"engine": cast[c]["voice"].split()[0],
                    "voice": cast[c]["voice"].split()[-1]}
                for c in used if cast[c].get("voice")},
        music=cues_out,
        beats=beats)
    return film, chapters, warns, motion_src_counts


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
    film, chapters, warns, motion_src = compile_movie(a.path)
    out = os.path.splitext(a.path)[0] + ".json"
    json.dump(film, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    for w in warns:
        print(f"  ! {w}")
    print(f"compiled {a.path} -> {out}")
    print(f"  {len(chapters)} chapters, "
          f"{sum(len(c['scenes']) for c in chapters)} scenes, {len(film['beats'])} beats")
    # The video prompt, said out loud once per compile. It is the most expensive stage of
    # the render and it was a constant for the life of the project largely because nothing
    # ever printed it.
    if motion_src:
        WHERE = {"card": "from a motion card", "text": "written on the beat",
                 "desc": "derived from the shot line", "hold": "holding still"}
        print("  motion:  " + ",  ".join(
            f"{n} {WHERE.get(k, k)}" for k, n in motion_src.most_common()))
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
