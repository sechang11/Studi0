#!/usr/bin/env python3
"""Film / scene / shot / take - the model behind the shot-by-shot editor at /film.

    import film
    f = film.load("the-courier")
    sh = f.shot("010")
    ctx = sh.resolved()             # every value, with the level that supplied it
    p = film.compile_shot(ctx, "ltx")   # the exact prompt that will be sent, plus warnings

WHY THIS EXISTS, when story.py already exists. story.py edits at SCENE granularity on the
2.3-era engines. Most movie shots are under six seconds, so the unit of work here is one
SHOT - a handful of layered inputs (framing, angle, camera move, subject, action,
background, dialogue, sfx) - rendered as TAKES across three engines (LTX-2.5, H3, Wan) so
the best one can be picked, and picked takes assemble into scenes and the scenes into the
film.

story.py's three invariants are kept, because they are right:
  1. film.json is the truth; everything under takes/ and assets/ is a cache.
  2. A take is immutable. Changing an input makes a new take, never edits one.
  3. A level stores only what it OVERRIDES.

THE CONTEXT SYSTEM. Three levels, film -> scene -> shot, nearest wins:

    FILM   cast, look (photoreal or anime + its style clause), grade, negatives, fps -
           the things that must survive the whole movie
    SCENE  location, time of day, weather, AMBIENCE (the continuous sound bed), palette,
           who is present, the scene anchor image - a scene is a new sub-context
    SHOT   the beats and layers - everything that is this shot's own

`resolved()` returns {key: {value, source}} so the editor can show, for any point on the
timeline, exactly what context is in force and which level put it there.

THE COMPILER IS WHERE THE RULEBOOK LIVES. Every rule the overnight runs paid for is
enforced here rather than remembered:

  LTX   one chronological paragraph; transitions named in prose; the subject RE-IDENTIFIED
        at every cut ("the same cook in the black shirt"); audio continuity stated; the
        scene ambience rendered as a bed that "runs under the whole shot and never stops"
        (a Sound clause written as an absence returns literal silence); dialogue quoted
        with the character's voice description; absences restated inside every cut when the
        frame must stay empty; anime defended with the cel clause in the video prompt; the
        measured envelope table enforced, because no single formula predicts the cliff.
  H3    one big committed event; the whole body goes with a swing or the limb ghosts;
        nothing toward camera; length is 17n+5 and 209 frames is the OOM ceiling; width
        and height must be passed or the node's hardcoded 768x1344 wins.
  Wan   silent, 16fps - offered as a variant engine because its motion reads differently,
        and the picker is the point.

Camera language is a small vocabulary, not free text, so the editor can offer it and the
compilers can place it: ANGLES x MOVES below.
"""
import json, os, re, shutil, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FILMS = os.path.join(HERE, "films")
CHARDIR = os.path.join(HERE, "characters")
TEMPLATES = os.path.join(HERE, "shot_templates")

# ── the camera vocabulary ───────────────────────────────────────────────────────────
# An angle is the first noun of every beat sentence. A move wraps it. Keeping these as a
# closed set is what lets the editor offer dropdowns and the compiler speak LTX's dialect
# (these phrasings are the ones the prompting guide uses and the ones that worked).
ANGLES = [
    "wide establishing shot", "wide shot", "medium shot", "medium two-shot",
    "close-up", "tight close-up", "extreme macro shot", "over-the-shoulder shot",
    "low-angle shot", "high-angle shot", "overhead view", "low tracking shot",
]
MOVES = {
    "static":       ("static", ""),
    "push in":      ("slow", "as the camera pushes in slowly"),
    "pull back":    ("slow", "as the camera pulls back"),
    "pan":          ("", "as the camera pans across"),
    "follow":       ("tracking", "with the camera following the subject"),
    "circle":       ("", "as the camera circles around the subject"),
    "handheld":     ("handheld", ""),
    "tilt up":      ("", "as the camera tilts upward"),
    "tilt down":    ("", "as the camera tilts downward"),
}
TRANSITIONS_IN = ["hard cut", "dissolve"]          # inside an LTX generation
TRANSITIONS_OUT = ["cut", "fade", "dissolve", "dip to black"]   # at assembly

# Portrait-ish angles flip the canvas and raise the IPAdapter weight; wide keeps it low.
# PLUS FACE biases COMPOSITION as well as identity - 0.6 turns a wide shot into a
# portrait on a blank ground, 0.3 lets the scene description win.
CLOSE_ANGLES = {"close-up", "tight close-up", "extreme macro shot"}

# ── engine envelopes, all measured ──────────────────────────────────────────────────
LTX_SAFE = [(0.9, 30), (1.2, 20), (1.5, 12), (2.0, 8)]   # (max MP, max seconds); 1.0x28 died in VAE decode - 0.9/30 is the MEASURED cell
H3_MAX_FRAMES = 209                                       # 8.7s; the kernel OOMs past it
WAN_FRAMES, WAN_FPS = 81, 16                              # ~5s, silent

LTX_NEG = "pc game, console game, video game, cartoon, childish, ugly"
NEG_PHOTO = ("blurry, low quality, watermark, text, signature, cgi, 3d render, deformed, "
             "extra limbs, extra fingers, nudity, nsfw")
NEG_ANIME = ("photorealistic, live action, 3d render, cgi, realistic skin, blurry, lowres, "
             "bad anatomy, bad hands, extra limbs, watermark, signature, text, nudity, nsfw")
LOOK_PHOTO = ("photoreal cinematic film still, 35mm, deep focus, high detail, colour "
              "photograph, filmic grade")
LOOK_ANIME = ("flat cel-shaded hand-drawn 2D anime with clean line art and painted "
              "background art")
CEL_DEFEND = ("The whole scene stays flat cel-shaded hand-drawn 2D anime with clean line "
              "art and painted background art throughout")
EMPTY_CLAUSE = "the frame completely empty of people and hands"

# Words that summon an agent into an empty frame, found one cat at a time.
AGENT_WORDS = re.compile(r"\b(hand|hands|finger|fingers|arm|arms|man|woman|person|people|"
                         r"figure|someone|barista|chef|worker|walker|hiker)\b", re.I)
TOWARD_CAMERA = re.compile(r"\btoward[s]? (the )?(camera|viewer|lens)\b", re.I)
LIMB_SWING = re.compile(r"\b(swings?|parr(?:y|ies)|flourish\w*|twirls?|spins? the "
                        r"(?:sword|staff|blade|weapon))\b", re.I)
BODY_COMMIT = re.compile(r"\b(steps?|lunges?|turns?|drives?|leaps?|drops?|throws? "
                         r"(?:himself|herself|themselves)|runs?|vaults?)\b", re.I)


# ── model ───────────────────────────────────────────────────────────────────────────

def _slug(s):
    return re.sub(r"[^a-z0-9-]+", "-", (s or "").lower()).strip("-") or "untitled"


def load(fid):
    p = os.path.join(FILMS, fid, "film.json")
    if not os.path.exists(p):
        raise KeyError(fid)
    return Film(fid, json.load(open(p, encoding="utf-8")))


def list_films():
    out = []
    if os.path.isdir(FILMS):
        for fid in sorted(os.listdir(FILMS)):
            try:
                out.append(load(fid))
            except (KeyError, ValueError):
                continue
    return out


def new_film(title, look="photoreal"):
    fid = _slug(title)
    d = os.path.join(FILMS, fid)
    if os.path.exists(os.path.join(d, "film.json")):
        raise ValueError("film %r exists" % fid)
    os.makedirs(os.path.join(d, "takes"), exist_ok=True)
    os.makedirs(os.path.join(d, "assets"), exist_ok=True)
    f = Film(fid, {
        "title": title, "created": time.strftime("%Y-%m-%d %H:%M"),
        "look": look,                       # photoreal | anime
        "look_clause": LOOK_PHOTO if look == "photoreal" else LOOK_ANIME,
        "grade": "", "negative": "", "fps": 24, "logline": "",
        "cast": {},                          # id -> {name, clause, short, sheet, ipa, voice, voice_desc}
        "scenes": [], "shots": {},
    })
    f.save()
    return f


class Film(object):
    def __init__(self, fid, data):
        self.id, self.data = fid, data
        self.dir = os.path.join(FILMS, fid)

    def save(self):
        tmp = os.path.join(self.dir, "film.json.tmp")
        json.dump(self.data, open(tmp, "w", encoding="utf-8"), indent=1)
        os.replace(tmp, os.path.join(self.dir, "film.json"))

    # scenes are ordered dicts in a list; shots are stored flat and referenced in order
    def scene(self, scid):
        for s in self.data["scenes"]:
            if s["id"] == scid:
                return s
        raise KeyError(scid)

    def new_scene(self, title, **kw):
        scid = "sc%02d" % (len(self.data["scenes"]) + 1)
        s = {"id": scid, "title": title, "location": "", "time_of_day": "",
             "weather": "", "ambience": "", "palette": "", "music": "",
             "cast_present": [], "no_people": False, "anchor": "", "shots": []}
        s.update(kw)
        self.data["scenes"].append(s)
        self.save()
        return s

    def shot(self, shid):
        return self.data["shots"][shid]

    def new_shot(self, scid, after=None, **kw):
        sc = self.scene(scid)
        n = 10 * (len(self.data["shots"]) + 1)
        shid = "%03d" % n
        while shid in self.data["shots"]:
            n += 1
            shid = "%03d" % n
        sh = {"id": shid, "scene": scid, "title": kw.pop("title", "shot %s" % shid),
              "duration": 6, "aspect": "wide",
              "anchor": "scene",              # scene | prev_last | file:<path> | none
              "keyframe_prompt": "",
              "beats": [{"framing": "wide shot", "move": "static", "transition_in": "",
                         "subject": "", "action": "", "background": "",
                         "dialogue": {"char": "", "line": "", "delivery": ""}}],
              "sfx": "", "no_people": None, "enhance": True,
              "transition_out": "cut", "takes": [], "picked": "",
              "engine_notes": ""}
        sh.update(kw)
        self.data["shots"][shid] = sh
        if after and after in sc["shots"]:
            sc["shots"].insert(sc["shots"].index(after) + 1, shid)
        else:
            sc["shots"].append(shid)
        self.save()
        return sh

    def ordered_shots(self):
        out = []
        for sc in self.data["scenes"]:
            for shid in sc["shots"]:
                if shid in self.data["shots"]:
                    out.append(self.data["shots"][shid])
        return out

    def prev_shot(self, shid):
        seq = self.ordered_shots()
        for i, sh in enumerate(seq):
            if sh["id"] == shid:
                return seq[i - 1] if i else None
        return None

    # ── the context system ─────────────────────────────────────────────────────────
    def resolved(self, shid):
        """Every value in force for this shot, each tagged with the level that set it.

        This is the payload behind 'click the timeline and see what context is present'.
        """
        sh = self.shot(shid)
        sc = self.scene(sh["scene"])
        out = {}

        def put(level, key, val):
            if val not in ("", None, []):
                out[key] = {"value": val, "source": level}

        for k in ("title", "look", "look_clause", "grade", "negative", "fps", "logline"):
            put("film", k, self.data.get(k))
        put("film", "cast", self.data.get("cast"))
        for k in ("location", "time_of_day", "weather", "ambience", "palette",
                  "music", "cast_present"):
            put("scene", k, sc.get(k))
        put("scene", "scene_anchor", sc.get("anchor"))
        put("scene", "scene_title", sc.get("title"))
        if sc.get("no_people"):
            put("scene", "no_people", True)
        for k in ("duration", "aspect", "anchor", "keyframe_prompt", "sfx",
                  "enhance", "transition_out", "beats"):
            put("shot", k, sh.get(k))
        if sh.get("no_people") is not None:
            put("shot", "no_people", sh["no_people"])
        put("shot", "shot_title", sh.get("title"))
        return out

    def flat(self, shid):
        out = {k: v["value"] for k, v in self.resolved(shid).items()}
        # `cam` is shot-local and not part of the film/scene/shot context table,
        # but compile_shot needs it or every cam shot compiles as the default rig
        cam = (self.shot(shid) or {}).get("cam")
        if cam:
            out["cam"] = cam
        # also shot-local: set when an anchor was BUILT by compositing a named
        # character into a named place, which is the only case we can be sure
        # the start frame contains the character
        src = (self.shot(shid) or {}).get("anchor_source")
        if src:
            out["anchor_source"] = src
        return out


# ── subject expansion ───────────────────────────────────────────────────────────────

class _CastTracker(object):
    """First mention gets the full appearance clause; every later mention gets
    'the same <short>' - the re-identification rule, applied automatically so it can
    never be forgotten at a cut again."""
    def __init__(self, cast):
        self.cast = cast or {}
        self.seen = set()

    def expand(self, ref):
        ref = (ref or "").strip()
        if not ref:
            return ""
        c = self.cast.get(ref)
        if not c:
            return ref                        # free text subject
        if ref in self.seen:
            return "the same %s" % (c.get("short") or c.get("name", ref))
        self.seen.add(ref)
        return c.get("clause") or c.get("name", ref)

    def voice_of(self, ref):
        c = self.cast.get(ref) or {}
        return c.get("voice_desc") or "a level voice"


def _framing_phrase(beat, first):
    ang = beat.get("framing") or "wide shot"
    adj, clause = MOVES.get(beat.get("move") or "static", ("", ""))
    art = "A" if first else "a"
    head = ("%s %s %s" % (art, adj, ang)).replace("  ", " ").strip()
    if head.lower().startswith("a e") or head.lower().startswith("a o"):
        head = ("An" if first else "an") + head[1:]
    return head, clause


def _sentence(*parts):
    s = " ".join(p.strip() for p in parts if p and p.strip())
    s = re.sub(r"\s+", " ", s).strip()
    if s and s[-1] not in ".!?\"":
        s += "."
    return s


# ── the compilers ───────────────────────────────────────────────────────────────────

def compile_shot(flat, engine):
    """flat = Film.flat(shot_id). Returns dict with everything a render job needs, plus
    `warnings` (lints from the rulebook) and `notes` (what the compiler decided)."""
    engine = engine.lower()
    if engine == "ltx":
        return _compile_ltx(flat)
    if engine == "h3":
        return _compile_h3(flat)
    if engine == "wan":
        return _compile_wan(flat)
    if engine == "cam":
        return _compile_cam(flat)
    raise ValueError(engine)


def _compile_cam(flat):
    """A camera rig has no prompt - the rig name, its preset and the plate ARE the spec.
    The verdict is surfaced as warnings so a rig that fails its own shape test says so in
    the editor rather than after a render."""
    cam = flat.get("cam") or {}
    rig = cam.get("rig") or "still_push"
    out = {"engine": "cam", "rig": rig, "preset": cam.get("preset") or "",
           "params": cam.get("params") or {}, "prompt": "", "negative": "",
           "warnings": [], "notes": []}
    try:
        import importlib.util
        sp = importlib.util.spec_from_file_location(
            "camrig", os.path.join(HERE, "_tools", "camrig.py"))
        cr = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(cr)
        p = cr.resolve(rig, cam.get("params") or {}, cam.get("preset") or None)
        d = cr.load_rig(rig)
        out["resolved"] = p
        out["seconds"] = p.get("seconds")
        out["notes"].append(d.get("summary", ""))
        out["notes"].append("%s px window, %s"
                            % (int(p.get("win_w", 0)),
                               "preset " + cam["preset"] if cam.get("preset")
                               else "no preset"))
        v = cr.verdict(rig, cam.get("params") or {}, cam.get("preset") or None)
        if v.get("pass") is False:
            out["warnings"].append(
                "camrig shape test FAILS - phase2 %s, phase3 %s"
                % (v.get("phase2_ok"), v.get("phase3_ok")))
        if v.get("settles_in_shot") is False:
            out["warnings"].append(
                "still moving when the shot ends - raise `seconds` or `damping`")
    except Exception as e:
        out["warnings"].append("camrig: %s" % str(e)[:160])
    return out



def _no_people(flat):
    v = flat.get("no_people")
    return bool(v)


def _style_bits(flat):
    if flat.get("look") == "anime":
        return "in flat cel-shaded 2D anime", CEL_DEFEND, NEG_ANIME
    look = flat.get("look_clause") or LOOK_PHOTO
    grade = flat.get("grade") or ""
    tail = (look + (", " + grade if grade else ""))
    return "", tail, NEG_PHOTO


def _scene_ground(flat):
    bits = [flat.get("location") or "", flat.get("time_of_day") or "",
            flat.get("weather") or ""]
    return ", ".join(b for b in bits if b)


def _dialogue_clause(beat, cast, warnings, look):
    d = beat.get("dialogue") or {}
    line = (d.get("line") or "").strip()
    if not line:
        return "", ""
    same = d.get("char") and d.get("char") == beat.get("subject")
    who = ("who" if same else
           (cast.expand(d.get("char")) if d.get("char") else "the speaker"))
    vd = cast.voice_of(d.get("char"))
    deliv = (d.get("delivery") or "").strip()
    deliv = (", " + deliv) if deliv else ""
    if look == "anime":
        # lip sync is photoreal only - the drawn mouth stays shut, so the line plays from
        # off screen over whatever this beat frames, the way limited animation cuts it
        poss = ("whose" if who == "who" else
                ("the character's" if who == "the speaker" else who + "'s"))
        speech = ('and %s voice says from off screen in %s%s, "%s"'
                  % (poss, vd, deliv, line))
        warnings.append("anime dialogue: line is written OFF SCREEN over this beat "
                        "(LTX voices anime but does not move a drawn mouth)")
    else:
        speech = ('%s says in %s%s, "%s"' % (who, vd, deliv, line))
    sound = "the voice speaking the line clearly"
    return speech, sound


def _sound_clause(flat, nbeats, extra_sounds, warnings):
    amb = (flat.get("ambience") or "").strip().rstrip(".")
    sfx = (flat.get("sfx") or "").strip().rstrip(".")
    parts = []
    if amb:
        parts.append("%s, running under the whole shot and never stopping" % amb)
    if sfx:
        parts.append(sfx)
    parts += [s for s in extra_sounds if s]
    if not parts:
        warnings.append("no ambience or sfx set - LTX generates the ambience the picture "
                        "implies, and a shot with nothing that makes noise returns "
                        "literal silence")
        return ""
    tail = ""
    if nbeats > 1:
        n = "the cut" if nbeats == 2 else "all %d cuts" % (nbeats - 1)
        tail = ", continuing unbroken across %s" % n
    quiet = re.search(r"\b(silence|silent|quiet|stillness)\b", amb + " " + sfx, re.I)
    if quiet and len(parts) == 1:
        warnings.append("the sound clause leans on an absence (%r) - name sources that "
                        "make noise, off screen if the frame has none" % quiet.group(0))
    return "Sound: %s%s." % (", ".join(parts), tail)


def _lint_action(txt, flat, warnings, engine):
    if TOWARD_CAMERA.search(txt or ""):
        warnings.append("motion toward the camera - the axis a still cannot imply; "
                        "it killed shots on every engine")
    if _no_people(flat) and AGENT_WORDS.search(txt or ""):
        warnings.append("agent noun (%s) in an empty-frame shot - naming a body part "
                        "grows a whole person" % AGENT_WORDS.search(txt).group(0))
    if engine == "h3" and LIMB_SWING.search(txt or "") and not BODY_COMMIT.search(txt or ""):
        warnings.append("H3: a swing from a planted stance ghosts the limb - write the "
                        "body committing through it (step, lunge, turn, drive)")


def _compile_ltx(flat):
    warnings, notes = [], []
    _cast = flat.get("cast") or {}
    _beats = flat.get("beats") or []
    # Measured (playbook 24): this is about the ANCHOR, not the cut. With a
    # composited anchor the character is in the start frame and survives the
    # transition - same face, same braid - while a plate anchor produced a
    # different woman entirely. So the warning is for anchors that do not
    # already contain the character.
    _anchored = bool(flat.get("anchor_source"))
    if (not _anchored and flat.get("look") != "anime" and len(_beats) > 1
            and any((b.get("subject") or "") in _cast for b in _beats)
            and any(_cast.get(b.get("subject") or "", {}).get("portrait")
                    for b in _beats)):
        warnings.append("identity: an internal cut re-derives faces from the scene "
                        "prior - the start frame's face does not survive it. Either "
                        "compose the anchor so the character is IN the start frame "
                        "(the cut then holds - measured), or use ONE-beat shots from "
                        "identity keyframes and cut at assembly")
    cast = _CastTracker(flat.get("cast"))
    beats = flat.get("beats") or []
    style_prefix, style_tail, neg_default = _style_bits(flat)
    empty = _no_people(flat)
    ground = _scene_ground(flat)
    sentences, dialogue_sounds = [], []

    for i, b in enumerate(beats[:4]):
        head, moveclause = _framing_phrase(b, i == 0)
        subj = cast.expand(b.get("subject"))
        speech, dsound = _dialogue_clause(b, cast, warnings, flat.get("look"))
        if dsound:
            dialogue_sounds.append(dsound)
        action = (b.get("action") or "").strip()
        _lint_action(action, flat, warnings, "ltx")
        bg = (b.get("background") or "").strip()
        if i == 0:
            head_full = head + (" " + style_prefix if style_prefix else "")
            body = []
            if subj:
                body.append(subj)
            if action:
                body.append(action)
            if speech:
                body.append(speech)
            if moveclause:
                body.append(moveclause)
            if bg:
                body.append(bg if bg.lower().startswith(("while", "as ", "and "))
                            else "while " + bg)
            if ground:
                body.append(ground)
            if empty:
                body.append(EMPTY_CLAUSE)
            sentences.append(_sentence(head_full + ":",
                                       ", ".join(body) if body else "the scene holds"))
        else:
            trans = b.get("transition_in") or "hard cut"
            tword = ("A %s transitions to" % trans) if i == 1 else                     ("Another %s transitions to" % trans)
            body = []
            if action:
                body.append(action)
            if speech:
                body.append(speech)
            if moveclause:
                body.append(moveclause)
            if bg:
                body.append(bg)
            if empty:
                body.append(EMPTY_CLAUSE)
            tail = ", ".join(body) if body else "the moment holds"
            sentences.append(_sentence("%s %s of %s," % (tword, head, subj or "the scene"),
                                       tail))

    if flat.get("look") == "anime":
        sentences.append(_sentence(CEL_DEFEND))
    elif style_tail:
        sentences.append(_sentence(style_tail[0].upper() + style_tail[1:]))
    snd = _sound_clause(flat, len(beats), dialogue_sounds, warnings)
    if snd:
        sentences.append(snd)
    prompt = " ".join(s for s in sentences if s)

    secs = int(flat.get("duration") or 6)
    if secs > LTX_SAFE[0][1]:
        warnings.append("duration clamped to %ds - the measured envelope is a table, not "
                        "a formula, and past it the ComfyUI process is killed"
                        % LTX_SAFE[0][1])
        secs = LTX_SAFE[0][1]
    mp = LTX_SAFE[0][0]
    for cap_mp, cap_s in LTX_SAFE:
        if secs <= cap_s:
            mp = cap_mp
    notes.append("%.1f MP, %ds - inside the measured envelope" % (mp, secs))

    neg = ", ".join(x for x in [LTX_NEG, neg_default, flat.get("negative") or "",
                                ("person, model, hands, arms, face, crowd, animal, cat, "
                                 "dog, bird" if empty else "")] if x)
    aspect = "9:16 (Portrait)" if flat.get("aspect") == "portrait" else "16:9 (Widescreen)"
    return {"engine": "ltx", "workflow": "70_ltx25_i2v.json", "prompt": prompt,
            "negative": neg, "seconds": secs, "megapixels": mp, "aspect": aspect,
            "enhance": bool(flat.get("enhance", True)),
            "warnings": warnings, "notes": notes}


def _compile_h3(flat):
    warnings, notes = [], []
    cast = _CastTracker(flat.get("cast"))
    beats = flat.get("beats") or []
    if len(beats) > 1:
        warnings.append("H3 renders beat 1 only - it has no multishot; the other %d "
                        "beat(s) are ignored on this engine" % (len(beats) - 1))
    b = beats[0] if beats else {}
    subj = cast.expand(b.get("subject"))
    action = (b.get("action") or "").strip() or "natural motion in the scene"
    _lint_action(action, flat, warnings, "h3")
    if (b.get("dialogue") or {}).get("line"):
        warnings.append("H3 dialogue is untested here - the line is left out of the "
                        "prompt; put dialogue shots on LTX")
    bg = (b.get("background") or "").strip()
    if not bg:
        warnings.append("no background action - H3 animates only what the clause names; "
                        "an unnamed background freezes")
    body = ", ".join(x for x in [subj and ("%s %s" % (subj, action)) or action, bg] if x)
    style = ("Anime animation. " if flat.get("look") == "anime" else "")
    amb = (flat.get("ambience") or "").strip()
    sfx = (flat.get("sfx") or "").strip()
    snd = ", ".join(x for x in [sfx, amb] if x) or "natural ambience"
    prompt = "%s. %s Sound: %s." % (body.rstrip("."), style, snd)

    secs = min(float(flat.get("duration") or 5), H3_MAX_FRAMES / 24.0)
    n = max(1, round((secs * 24 - 5) / 17.0))
    length = min(int(17 * n + 5), H3_MAX_FRAMES)
    notes.append("length %d frames (17n+5), %.1fs" % (length, length / 24.0))
    w, h = (896, 1216) if flat.get("aspect") == "portrait" else (1216, 832)
    return {"engine": "h3", "workflow": "60_minimax_h3_i2v.json", "prompt": prompt,
            "length": length, "width": w, "height": h,
            "warnings": warnings, "notes": notes}


def _compile_wan(flat):
    warnings, notes = [], []
    cast = _CastTracker(flat.get("cast"))
    beats = flat.get("beats") or []
    if len(beats) > 1:
        warnings.append("Wan renders beat 1 only")
    warnings.append("Wan is SILENT - audio would come from another engine or the mix")
    b = beats[0] if beats else {}
    subj = cast.expand(b.get("subject"))
    action = (b.get("action") or "").strip() or "gentle natural motion"
    _lint_action(action, flat, warnings, "wan")
    bg = (b.get("background") or "").strip()
    prompt = ". ".join(x for x in
                       [("%s %s" % (subj, action)).strip() if subj else action, bg] if x)
    notes.append("%d frames at %dfps (~%.1fs)" % (WAN_FRAMES, WAN_FPS,
                                                  WAN_FRAMES / WAN_FPS))
    return {"engine": "wan", "workflow": "04_wan22_i2v_turbo.json", "prompt": prompt,
            "negative": "static, still image, frozen, blurry, distorted, warping, "
                        "morphing, low quality, watermark",
            "frames": WAN_FRAMES, "fps": WAN_FPS,
            "warnings": warnings, "notes": notes}


# ── keyframe planning ───────────────────────────────────────────────────────────────

def keyframe_plan(film, shid):
    """How this shot's start image is obtained. The anchor doctrine: shots in a scene
    default to the SCENE anchor (one keyframe holds person, wardrobe, place and light
    together); 'prev_last' continues from the previous shot's picked take; 'generate'
    makes a shot-specific keyframe through the right identity path."""
    sh = film.shot(shid)
    sc = film.scene(sh["scene"])
    mode = sh.get("anchor") or "scene"
    if mode.startswith("file:"):
        return {"mode": "file", "path": mode[5:]}
    if mode == "prev_last":
        prev = film.prev_shot(shid)
        if not prev or not prev.get("picked"):
            return {"mode": "error",
                    "error": "prev_last needs a previous shot with a picked take"}
        take = next((t for t in prev["takes"] if t["id"] == prev["picked"]), None)
        return {"mode": "prev_last", "take_file": take and take.get("file")}
    if mode == "generate":
        flat = film.flat(shid)
        present = [c for c in (sc.get("cast_present") or []) if c in film.data["cast"]]
        first = (sh.get("beats") or [{}])[0]
        subj = first.get("subject") or ""
        if subj in film.data["cast"]:
            # the shot's own subject leads, and a close framing is THAT person's frame -
            # a second portrait in a close-up muddles both faces
            present = [subj] + [c for c in present if c != subj]
            if first.get("framing") in CLOSE_ANGLES:
                present = [subj]
        look = film.data.get("look")
        if look == "anime" and len(present) >= 2:
            wf = "45_anime_two_char_ipadapter.json"
        elif look == "anime":
            wf = "22_anime_kf_ipadapter.json"
        else:
            wf = "01_qwen_t2i_turbo.json"
        ipa = 0.6 if (first.get("framing") in CLOSE_ANGLES) else 0.3
        return {"mode": "generate", "workflow": wf, "ipa": ipa,
                "prompt": sh.get("keyframe_prompt") or "", "present": present}
    return {"mode": "scene", "path": sc.get("anchor") or ""}


# ── selftest ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys as _sys
    if "selftest" in _sys.argv:
        shutil.rmtree(os.path.join(FILMS, "selftest"), ignore_errors=True)
        f = new_film("Selftest", look="photoreal")
        f.data["cast"]["COOK"] = {
            "name": "the cook", "short": "cook in the black shirt",
            "clause": "the cook in his forties in a black shirt with a white towel over "
                      "his shoulder", "voice": "male_02", "voice_desc": "a dry, unhurried "
                      "American accent"}
        sc = f.new_scene("night stall", location="a night street food stall on a narrow "
                         "lane", time_of_day="late night", weather="",
                         ambience="a low gas burner and a quiet lane with one distant "
                         "scooter", cast_present=["COOK"])
        sh = f.new_shot(sc["id"], title="the line")
        sh["duration"] = 12
        sh["beats"] = [
            {"framing": "wide shot", "move": "static", "subject": "COOK",
             "action": "wipes down the steel counter under the hanging bulbs",
             "background": "the lane behind him stands nearly empty",
             "dialogue": {"char": "", "line": "", "delivery": ""}},
            {"framing": "close-up", "move": "static", "transition_in": "hard cut",
             "subject": "COOK",
             "action": "does not look up",
             "background": "",
             "dialogue": {"char": "COOK", "line": "I'm closed.", "delivery": "flat"}},
        ]
        sh["sfx"] = "a cloth wiping steel, a stool scraping"
        f.save()
        for eng in ("ltx", "h3", "wan", "cam"):
            c = compile_shot(f.flat(sh["id"]), eng)
            print("=== %s\n%s" % (eng.upper(), c["prompt"]))
            for w in c["warnings"]:
                print("  WARN", w)
            for nnote in c["notes"]:
                print("  note", nnote)
        r = f.resolved(sh["id"])
        print("=== context provenance sample")
        for k in ("ambience", "duration", "look_clause", "cast_present"):
            if k in r:
                print("  %-12s %-6s %s" % (k, r[k]["source"], str(r[k]["value"])[:60]))
        shutil.rmtree(os.path.join(FILMS, "selftest"), ignore_errors=True)
        print("selftest ok")
