#!/usr/bin/env python3
"""Story / chapter / scene / take - the model behind the scene-by-scene editor.

    import story
    st = story.load("the-salt-road")
    sc = st.scene("01/010-table")
    print(sc.resolved())          # every input, with the level that supplied it
    t = sc.new_take(seed=1234)    # immutable; rendering fills it in

WHY THIS EXISTS. A film is currently rendered from one JSON in one go, which is right for
a first pass and wrong for every pass after it: to improve shot 34 of 59 you re-roll the
whole hour and change 58 shots you liked. The unit people actually judge is one shot, so
the unit of work here is a TAKE - one attempt at one scene - and the rest of the model
exists to serve it.

THE THREE INVARIANTS, which everything else follows from:

  1. story.json is the truth; the folder tree is a cache. Anything under takes/ can be
     deleted and rebuilt. Nothing unrebuildable lives outside a .json.
  2. A take is immutable. Changing an input never edits a take, it makes a new one - which
     is what makes "render four and pick one" and "go back to Tuesday's" the same feature.
  3. A scene stores only what it OVERRIDES. It never stores an inherited value, or changing
     the chapter would change a default nothing reads any more.

INHERITANCE resolves story -> chapter -> scene -> take, nearest wins, and every resolved
value remembers which level supplied it. Not knowing why a shot looks the way it does is
the most expensive thing in a long project, so `resolved()` returns provenance, not just
values.
"""
import hashlib, json, os, re, shutil, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STORIES = os.path.join(ROOT, "stories")

# Fields that flow down the chain. Anything not listed is local to its level - a scene's
# prompt is not something a chapter can supply.
INHERITED = ("style", "look", "engine", "ar", "fps", "style_lora", "style_strength",
             "id_lora", "id_strength", "seconds", "transition", "negative", "lipsync",
             "title_scale", "subtitle_scale")

# ── RULES ARE THE ROOT OF THE INHERITANCE TREE ──────────────────────────────────────
# craft/VIDEO_RULES.md sits ABOVE every story, so the chain is really
#
#     rules -> story -> chapter -> scene -> take
#
# and rules are simply the level nobody owns. That is the right shape rather than a
# coincidence: a rule exists because something broke once, and a lesson that only applies
# to the story you were working on when you learned it is worth almost nothing.
#
# Rules do two jobs at this level. They SUPPLY DEFAULTS, so a brand new story is already
# obeying every measured finding without anyone typing anything. And they VALIDATE, so a
# story that overrides one is told what it is overriding.
#
# An override is allowed. A rule is a default and a warning, not a cage - the film that
# genuinely wants a 0.3 title scale should be able to have one. But because every rule was
# paid for with a real failure, an override is recorded with its provenance and reported,
# never silently absorbed.
RULE_DEFAULTS = {
    "title_scale": 0.075,      # PICTURE-01: scale is a fraction of frame height
    "subtitle_scale": 0.034,   # PICTURE-01
    "transition": "cut",
    "lipsync": False,          # inverts the picture/voice dependency - opt in per scene
}
BANNED = {
    "look": {"night"},                                    # PICTURE-05: clips to black
    "camera": {"dolly_zoom", "orbit", "rack_focus"},      # PICTURE-04: identical to static
}

# A change to any of these means a rendered take no longer matches its inputs. Deliberately
# NOT the whole scene: editing a note or a title must not invalidate an hour of picture.
HASHED = ("prompt", "motion", "style", "look", "engine", "negative", "characters",
          "style_lora", "style_strength", "id_lora", "id_strength", "seconds", "ar")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def _read(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {} if default is None else default


def _write(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.write("\n")


class Take:
    """One attempt at one scene. Immutable once rendered."""

    def __init__(self, scene, tid):
        self.scene, self.id = scene, tid
        self.dir = os.path.join(scene.dir, "takes", tid)
        self.meta = _read(os.path.join(self.dir, "inputs.json"))

    @property
    def keyframe(self):
        return os.path.join(self.dir, "keyframe.png")

    @property
    def clip(self):
        return os.path.join(self.dir, "clip.mp4")

    def has(self, what="keyframe"):
        return os.path.exists(self.keyframe if what == "keyframe" else self.clip)

    def stale(self):
        """True when the scene's inputs have moved on since this take was rendered.

        The old picture is still there and still watchable - it is flagged, never deleted.
        Silently dropping a take because a parent changed is how you lose the shot you
        liked and cannot get back.
        """
        return bool(self.meta) and self.meta.get("inputs_hash") != self.scene.inputs_hash()

    def save(self, **kw):
        self.meta.update(kw)
        _write(os.path.join(self.dir, "inputs.json"), self.meta)
        return self


class Scene:
    def __init__(self, chapter, sid):
        self.chapter, self.id = chapter, sid
        self.dir = os.path.join(chapter.dir, "scenes", sid)
        self.data = _read(os.path.join(self.dir, "scene.json"))

    # ---- inheritance ---------------------------------------------------------------
    def resolved(self):
        """Every input, with the level that supplied it.

        Returns {field: {"value": v, "from": "story|chapter|scene"}}. The provenance is the
        point: a UI can grey out what is inherited and say where it came from, and a person
        can tell at a glance what this scene actually decides for itself.
        """
        out = {}
        # Level 0. Everything below can override it, and will be told that it did.
        for k, v in RULE_DEFAULTS.items():
            out[k] = {"value": v, "from": "rules"}
        for level, data in (("story", self.chapter.story.data),
                            ("chapter", self.chapter.data),
                            ("scene", self.data)):
            for k in INHERITED:
                if data.get(k) not in (None, ""):
                    out[k] = {"value": data[k], "from": level}
        # Local fields are the scene's own by definition.
        for k in ("prompt", "motion", "say", "who", "sfx", "titles", "note"):
            if self.data.get(k) not in (None, ""):
                out[k] = {"value": self.data[k], "from": "scene"}
        # The cast is a story-level fact, filtered to whoever this scene names.
        cast = self.chapter.story.data.get("characters") or {}
        named = self.data.get("characters") or [c for c in cast if c in
                                                str(self.data.get("prompt", ""))]
        if named:
            out["characters"] = {"value": sorted(named), "from": "story"}
        return out

    def flat(self):
        return {k: v["value"] for k, v in self.resolved().items()}

    def rule_violations(self):
        """What this scene does that the rules say not to, and what it overrides.

        Separated on purpose: a BANNED value is a measured dud and is reported as a
        violation; an overridden default is a legitimate choice and is reported as a
        divergence. Conflating the two would either nag about deliberate decisions or hide
        real mistakes among them.
        """
        r, out = self.resolved(), {"violations": [], "overrides": []}
        for field, bad in BANNED.items():
            v = r.get(field, {}).get("value")
            if v in bad:
                out["violations"].append(
                    {"field": field, "value": v, "from": r[field]["from"]})
        for k, v in RULE_DEFAULTS.items():
            got = r.get(k)
            if got and got["from"] != "rules" and got["value"] != v:
                out["overrides"].append({"field": k, "rule_default": v,
                                         "value": got["value"], "from": got["from"]})
        # A title scale written as if it were a multiplier is the one that actually shipped.
        for tt in (self.data.get("titles") or []):
            if float(tt.get("scale", 0.045)) > 0.15:
                out["violations"].append(
                    {"field": "title.scale", "value": tt.get("scale"), "from": "scene"})
        return out

    def inputs_hash(self):
        f = self.flat()
        blob = json.dumps({k: f.get(k) for k in HASHED}, sort_keys=True)
        return hashlib.sha1(blob.encode()).hexdigest()[:12]

    # ---- takes ---------------------------------------------------------------------
    def takes(self):
        d = os.path.join(self.dir, "takes")
        return [Take(self, t) for t in sorted(os.listdir(d))] if os.path.isdir(d) else []

    def new_take(self, seed=None):
        n = len(self.takes()) + 1
        while os.path.exists(os.path.join(self.dir, "takes", "t%02d" % n)):
            n += 1
        t = Take(self, "t%02d" % n)
        os.makedirs(t.dir, exist_ok=True)
        return t.save(id=t.id, seed=seed, created=time.strftime("%Y-%m-%dT%H:%M:%S"),
                      inputs_hash=self.inputs_hash(), status="pending",
                      inputs=self.flat())

    @property
    def selected_id(self):
        p = os.path.join(self.dir, "SELECTED")
        return open(p).read().strip() if os.path.exists(p) else None

    def selected(self):
        tid = self.selected_id
        if tid and os.path.isdir(os.path.join(self.dir, "takes", tid)):
            return Take(self, tid)
        # Fall back to the first rendered take rather than nothing, so an un-curated story
        # still exports.
        for t in self.takes():
            if t.has("keyframe"):
                return t
        return None

    def select(self, tid):
        if not os.path.isdir(os.path.join(self.dir, "takes", tid)):
            raise KeyError("no take %s in %s" % (tid, self.id))
        # A pointer, never a copy. Copying the winner into place is how the two drift apart.
        with open(os.path.join(self.dir, "SELECTED"), "w") as f:
            f.write(tid + "\n")
        return tid

    @property
    def locked(self):
        return bool(self.data.get("locked"))

    def save(self):
        _write(os.path.join(self.dir, "scene.json"), self.data)


class Chapter:
    def __init__(self, story, cid):
        self.story, self.id = story, cid
        self.dir = os.path.join(story.dir, "chapters", cid)
        self.data = _read(os.path.join(self.dir, "chapter.json"))

    def scene_ids(self):
        d = os.path.join(self.dir, "scenes")
        order = self.data.get("scenes")
        found = sorted(os.listdir(d)) if os.path.isdir(d) else []
        # An explicit order wins, but anything on disk and not in the list still shows up -
        # a scene must never become invisible because someone forgot to list it.
        return ([s for s in order if s in found] + [s for s in found if s not in (order or [])]
                if order else found)

    def scenes(self):
        return [Scene(self, s) for s in self.scene_ids()]

    def scene(self, sid):
        return Scene(self, sid)

    def transitions(self):
        d = os.path.join(self.dir, "transitions")
        return [_read(os.path.join(d, f)) for f in sorted(os.listdir(d))] if os.path.isdir(d) else []

    def transition(self, a, b):
        p = os.path.join(self.dir, "transitions", "%s__%s.json" % (a, b))
        t = _read(p)
        if not t:
            # Default is a cut, and a cut is free. The UI must distinguish an ffmpeg
            # transition from a generated one or people will wait for something instant.
            t = {"from": a, "to": b, "kind": self.data.get("transition", "cut"),
                 "seconds": 0.0, "generated": False}
        return t

    def set_transition(self, a, b, **kw):
        p = os.path.join(self.dir, "transitions", "%s__%s.json" % (a, b))
        t = self.transition(a, b)
        t.update(kw)
        _write(p, t)
        return t

    def save(self):
        _write(os.path.join(self.dir, "chapter.json"), self.data)


class Story:
    def __init__(self, sid):
        self.id = sid
        self.dir = os.path.join(STORIES, sid)
        self.data = _read(os.path.join(self.dir, "story.json"))

    def chapter_ids(self):
        d = os.path.join(self.dir, "chapters")
        order = self.data.get("chapters")
        found = sorted(os.listdir(d)) if os.path.isdir(d) else []
        return ([c for c in order if c in found] + [c for c in found if c not in (order or [])]
                if order else found)

    def chapters(self):
        return [Chapter(self, c) for c in self.chapter_ids()]

    def chapter(self, cid):
        return Chapter(self, cid)

    def scene(self, path):
        """`01/010-table` or `01-the-door/010-table`."""
        cid, sid = path.split("/", 1)
        if cid not in self.chapter_ids():
            match = [c for c in self.chapter_ids() if c.startswith(cid)]
            if not match:
                raise KeyError("no chapter %r" % cid)
            cid = match[0]
        return Chapter(self, cid).scene(sid)

    def all_scenes(self):
        return [s for c in self.chapters() for s in c.scenes()]

    def save(self):
        _write(os.path.join(self.dir, "story.json"), self.data)


def load(sid):
    st = Story(sid)
    if not st.data:
        raise KeyError("no story %r in %s" % (sid, STORIES))
    return st


def create(title, **kw):
    sid = slug(title)
    st = Story(sid)
    if st.data:
        return st
    st.data = {"id": sid, "title": title,
               "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "ar": "16:9", "fps": 24, "characters": {}, "voices": {},
               "chapters": []}
    st.data.update(kw)
    os.makedirs(st.dir, exist_ok=True)
    st.save()
    return st


def add_chapter(st, title, **kw):
    cid = "%02d-%s" % (len(st.chapter_ids()) + 1, slug(title))
    ch = Chapter(st, cid)
    ch.data = {"id": cid, "title": title, "scenes": []}
    ch.data.update(kw)
    os.makedirs(ch.dir, exist_ok=True)
    ch.save()
    st.data.setdefault("chapters", []).append(cid)
    st.save()
    return ch


def add_scene(ch, sid, **kw):
    sc = Scene(ch, sid)
    sc.data = {"id": sid}
    sc.data.update(kw)
    os.makedirs(sc.dir, exist_ok=True)
    sc.save()
    if sid not in (ch.data.get("scenes") or []):
        ch.data.setdefault("scenes", []).append(sid)
        ch.save()
    return sc


# ── THE .story FILE ─────────────────────────────────────────────────────────────────
# One portable document holding an entire story: settings, cast, chapters, scenes,
# transitions, and which take was chosen for each scene. Load it, edit it, save it, hand it
# to someone else.
#
# WHAT IT DELIBERATELY DOES NOT CONTAIN: pixels. No keyframes, no clips. A story with six
# takes on fifty scenes is gigabytes of picture, and picture is a CACHE - it can always be
# rebuilt from the inputs, which is exactly what the inputs_hash is for. What the file does
# carry is every take's METADATA: its id, seed and hash. So a reloaded story still knows
# that scene 040 had a chosen take at seed 2601, and can say so, and can rebuild it. You
# lose the bytes, never the provenance.
#
# The exploded folder tree stays the working format and the render cache. The .story file is
# the thing you copy, version, and email.
FORMAT = "comfy-studio/story"
VERSION = 1


def to_doc(st):
    """Whole story as one document."""
    doc = {"format": FORMAT, "version": VERSION, "id": st.id,
           "saved": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "story": st.data, "chapters": []}
    for ch in st.chapters():
        c = {"id": ch.id, "data": ch.data, "scenes": [],
             "transitions": ch.transitions()}
        for sc in ch.scenes():
            c["scenes"].append({
                "id": sc.id, "data": sc.data, "selected": sc.selected_id,
                # Metadata only - the picture is a cache, the provenance is not.
                "takes": [{"id": t.id, "seed": t.meta.get("seed"),
                           "inputs_hash": t.meta.get("inputs_hash"),
                           "status": t.meta.get("status"),
                           "note": t.meta.get("note", "")} for t in sc.takes()],
            })
        doc["chapters"].append(c)
    return doc


def from_doc(doc, new_id=None):
    """Write a document out as a story tree. Returns the Story.

    Takes come back as records with status `missing` rather than being dropped: the scene
    still says it had a chosen take at a known seed, and `plan` can then tell you exactly
    what needs re-rendering. Silently forgetting them would turn a portable story into a
    lossy one.
    """
    if doc.get("format") != FORMAT:
        raise ValueError("not a %s file" % FORMAT)
    sid = new_id or doc.get("id") or slug(doc["story"].get("title", "untitled"))
    st = Story(sid)
    st.data = dict(doc["story"], id=sid)
    os.makedirs(st.dir, exist_ok=True)
    st.data["chapters"] = [c["id"] for c in doc.get("chapters", [])]
    st.save()
    for c in doc.get("chapters", []):
        ch = Chapter(st, c["id"])
        ch.data = c["data"]
        os.makedirs(ch.dir, exist_ok=True)
        ch.save()
        for s in c.get("scenes", []):
            sc = Scene(ch, s["id"])
            sc.data = s["data"]
            os.makedirs(sc.dir, exist_ok=True)
            sc.save()
            for tk in s.get("takes", []):
                t = Take(sc, tk["id"])
                os.makedirs(t.dir, exist_ok=True)
                t.save(id=tk["id"], seed=tk.get("seed"),
                       inputs_hash=tk.get("inputs_hash"),
                       status="missing" if not os.path.exists(t.keyframe)
                       else tk.get("status", "rendered"),
                       note=tk.get("note", ""))
            if s.get("selected"):
                try:
                    sc.select(s["selected"])
                except KeyError:
                    pass
        for tr in c.get("transitions", []):
            if tr.get("from") and tr.get("to"):
                ch.set_transition(tr["from"], tr["to"],
                                  **{k: v for k, v in tr.items()
                                     if k not in ("from", "to")})
    return st


def next_scene_id(ch, name=""):
    """Scenes are numbered in tens so one can always be slipped between two others."""
    nums = []
    for s in ch.scene_ids():
        m = re.match(r"^(\d+)", s)
        if m:
            nums.append(int(m.group(1)))
    n = (max(nums) + 10) if nums else 10
    return "%03d%s" % (n, ("-" + slug(name)) if name else "")
