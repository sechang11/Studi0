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
import argparse, collections, hashlib, json, os, sys

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
    ("checkpoint",  ("movie",   "animagine-xl-4.0.safetensors", "anime SDXL model")),
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
    ("cue",         ("any",     "",          "studio/cues/*.json - music under this scene")),
    ("silence",     ("scene",   False,       "drop all score. use before an impact")),
    ("wear",        ("any",     0,           "damage continuity 0-4. never decreases")),
    ("characters",  ("scene",   [],          "who is in it. must be declared in studio/characters/")),
    ("pace",        ("scene",   "normal",    "slow / normal / fast - scales shot lengths")),
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
            cur_sc["beats"].append({"shot": v})
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

            for i, b in enumerate(sc["beats"]):
                bid = f"{ch['id']}_{sc['id']}_{i:02d}"
                tmpl = b.get("shot", "speak" if b.get("text") else "insert")
                d = collections.OrderedDict(
                    id=bid, template=tmpl,
                    clip_secs=6, intensity=round(1.0 / scale, 3),
                    camera=cam["id"] if cam.get("status") == "ready" else "static",
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
                        e = lib("emotions", emo)
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
                bits += [v["tags"], look["tags"], v["mood"], v["place"], v["time"], Q]
                d["tags"] = ", ".join(x for x in bits if x)
                d["prompt"] = d["tags"]
                d["motion"] = "Slow deliberate movement only."
                if b.get("text"):
                    d["line"] = {"who": who, "text": b["text"]}
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
        engine="higgs_v3", keyframe_engine="anime",
        anime_ckpt=movie["vars"].get("checkpoint", "animagine-xl-4.0.safetensors"),
        ipadapter_weight=float(movie["vars"].get("face_weight", 0.6)),
        style=movie["vars"].get("tags", ""),
        # The four registries short.py reads off the film. Their absence is exactly
        # what made every earlier .movie file uncompilable into a render.
        anime_sheets=sheets,
        sheets=sheets,
        characters={c: c for c in used},
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
