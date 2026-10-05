#!/usr/bin/env python3
"""studio/_tools/shots_routes.py - the shot editor half of "shots & specs": /shots, /api/shots/*.

The page (studio/shots.html, also served at /specs) shows each shot's spec sheet - its promises,
through spec_routes - beside the controls here. A shot locked on its spec sheet is refused by every
route below that would change what the film shows for it: pick, anchor, upload, run, save.

A film here is a SHOT SCRIPT (studio/shotscripts/<film>.json): a cast, a place, and shots in order.
The page is an editor over it, the way a video editor is over clips: a timeline of shots, a player
that plays the cut (or the storyboard, where a shot has no take yet), and an inspector for the shot
you are on - its words, its references, the model that draws its start frame, the engine that
renders it and on which seeds, the takes, and which one is in the film. It runs the SAME tools the
three demo films of 2026-09-29 were made with (fight.py, previz_shot.py, take_rank.py,
film_cards.py) with the same flags, one job at a time; the log it shows is theirs.

    GET  /shots
    GET  /api/shots/editor?film=X    everything the editor draws, in one payload
    GET  /api/shots/list             every shot script
    GET  /api/shots/script?film=X    one script
    GET  /api/shots/tree?film=X      the outputs per pipeline stage (the older page's view)
    GET  /api/shots/status           the running job, its progress and log tail, and the queue
    GET  /api/shots/plan?film=X      what "make everything missing" would make, and roughly how long
    POST /api/shots/save    {film, script}                    write the script (schema-checked)
    POST /api/shots/new     {film, from?}                     a new script (skeleton, or a copy)
    POST /api/shots/run     {film, op, shots?, ...}           cast | anchors | takes | rank | music |
                                                              assemble | missing | seedance (paid) | stage (old)
    POST /api/shots/stop    {} | {queue_id} | {all: true}     stop the job, drop a waiting one, or both
    POST /api/shots/pick    {film, shot, token}               this take is in the film
    POST /api/shots/anchor  {film, shot, candidate}           this start frame is the shot's
    POST /api/shots/seedance {film, shot, prompt, secs, why}  keep this Seedance prompt on the shot
    POST /api/shots/upload  {film, kind, id, dataurl}         your own picture as a reference or start frame
    POST /api/shots/archive {film}  /  restore {film}         put a film away (shotscripts/_archive/), or back

One job at a time, on purpose: every stage holds the GPU, and two runs on one film would race each
other's files. A job asked for while another runs waits in a queue and starts by itself, in order.
Kept out of serve.py because it owns a child process.
"""
import base64
import glob
import io
import json
import os
import re
import shlex
import subprocess
import sys
import threading
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
SEQ_DIR = os.path.join(STUDIO, "shotscripts")
FIGHT = os.path.join(TOOLS, "fight.py")
REFSHEET = os.path.join(TOOLS, "refsheet.py")
PYVENV = os.path.expanduser("~/ComfyUI/venv/bin/python3")
FILM_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,30}$")
SHOT_RE = re.compile(r"^\d{3}$")
SEED_RE = re.compile(r"^\d{1,9}$")
PICK_RE = re.compile(r"^((h3|h3f|h3k|pv|pvb|sd):)?\d{1,9}$")
PICKS_RE = re.compile(r"^\d{3}=((h3|h3f|h3k|pv|pvb|sd):)?\d{1,9}(,\d{3}=((h3|h3f|h3k|pv|pvb|sd):)?\d{1,9})*$")
TAKE_RE = r"^(shot|h3|h3f|h3k|pv|pvb|sd)_%s_s(\d+)\.mp4$"       # sd = the paid engine, when somebody paid;
# h3f / h3k = a film shot in a 3D set (set_film.py): H3 between the set's two frames / with key poses

# The menus the inspector offers, with what each choice is FOR - measured, not advertised.
MODELS = {
    "cast": [
        {"id": "flux2", "label": "Flux 2", "wf": "40", "note": "made every cast so far: a clean full-length reference on grey"},
        {"id": "krea2", "label": "Krea 2 Turbo", "wf": "77", "note": "the most photographic look; reads a description its own way"},
        {"id": "qwen21", "label": "Qwen-Image-2.1", "wf": "79", "note": "the start-frame compositor's own idea of a face"},
    ],
    "compositor": [
        {"id": "qwen21", "label": "Qwen-Image-2.1", "wf": "80", "note": "default: won 19 of 20 face-scored shots, ~13 s a frame, draws your seeds"},
        {"id": "flux2", "label": "Flux 2 ref3", "wf": "75", "note": "keeps shot size better - inserts and true close-ups; ~33 s"},
        {"id": "best", "label": "Both, scored", "wf": "75+80", "note": "Flux 2 once and Qwen on your seeds; the best face is kept"},
    ],
    "engine": [
        {"id": "ltx", "label": "LTX-2.5", "wf": "70", "note": "default: sound, lip-sync, up to 30 s; a 4 s take in ~15 s"},
        {"id": "h3", "label": "MiniMax H3", "wf": "67", "note": "keeps the start frame; holds faces, clears effects; ~40 s a take"},
        {"id": "both", "label": "Both", "wf": "70+67", "note": "render on each and pick by measurement (H3 won 9 of 9 on 09-29)"},
        {"id": "previz", "label": "Blender physics", "wf": "74", "note": "a physical beat simulated in Blender, drawn through depth control"},
        {"id": "h3f", "label": "H3 between a set's two frames", "wf": "65", "note": "a film shot in a 3D set: set_film.py frames and takes (key poses: set_test.py key / take) - rendered by those tools, not from this page"},
    ],
    "previz": [
        {"id": "aisle", "label": "aisle collapse", "note": "a stack of crates pushed over across an aisle, a figure beyond"},
        {"id": "crates", "label": "ball into crates", "note": "a heavy ball rolled into a wall of crates, a figure watching"},
        {"id": "fall", "label": "column falls", "note": "a column of crates nudged over"},
    ],
    "face": [
        {"id": "close", "label": "close-up"}, {"id": "medium", "label": "medium"},
        {"id": "wide", "label": "wide"}, {"id": "none", "label": "no face"},
    ],
}

SKELETON = {
    "_comment": "A shot script: the story as data. Edit it on /shots or by hand; studio/_tools/fight.py runs it.",
    "film": "", "title": "", "logline": "",
    "grade": ("Cinematic film, cool blue-green base, one warm practical, filmic contrast, "
              "deep blacks with detail, fine grain, anamorphic."),
    "avoid": ("lowres, blurry, deformed limbs, fused fingers, extra fingers, extra limbs, doubled figure, two of "
              "the same person, melting face, morphing, warping, text, letters, subtitles, watermark, nsfw"),
    "score_tags": "sparse solo piano, room tone, slow, patient, instrumental, no percussion, no vocals",
    "score_tags_b": "",
    "realism": ("Unretouched photograph, available light, visible skin texture and pores, fine film grain, "
                "shallow depth of field, no retouching, no gloss."),
    "place": {"id": "room", "prompt": "Wide photograph of an empty place, nobody in it: ..."},
    "cast": {"someone": {"role": "the lead", "prompt": ("Full-length reference photograph of a person "
                                                        "against a plain mid-grey backdrop, even soft light, "
                                                        "standing still, facing the camera: ...")}},
    "shots": [
        {"id": "010", "title": "the place", "secs": 4, "refs": ["room"], "anchor": None, "engine": "ltx",
         "face": "none", "avoid_extra": "people, a person, a figure, a crowd, hands",
         "prompt": "Nothing moves but the light. Static camera. Room tone. No music."},
        {"id": "020", "title": "the look", "secs": 5, "refs": ["someone", "someone", "room"], "engine": "ltx",
         "face": "close",
         "anchor": "A still frame from a live-action film, a CLOSE-UP, the person of reference one in the "
                   "place of reference three, facing the camera.",
         "prompt": "They look up slowly and say, quietly: \"...\". Static camera. Room tone, their voice. No music."},
    ],
}

# The running job outlives this module: serve.py reloads a route module when its file changes, and a
# reload must not forget a render in flight (or let a second one start beside it).
_STATE = sys.modules.setdefault("_shots_routes_state", type(sys)("_shots_routes_state"))
if not hasattr(_STATE, "JOB"):
    _STATE.JOB = {"proc": None, "film": None, "op": None, "shots": [], "started": None, "log": None, "cmd": None,
                  "abort": False, "done": True, "rc": None}
    _STATE.LOCK = threading.Lock()
if not hasattr(_STATE, "QUEUE"):
    # jobs asked for while one runs wait here, in order, and start by themselves - one GPU, one at a time
    _STATE.QUEUE = []
_JOB, _LOCK, _QUEUE = _STATE.JOB, _STATE.LOCK, _STATE.QUEUE


# ------------------------------------------------------------------------------ helpers
def _out(film):
    return os.path.join(STUDIO, "samples", "fight", film)


def _url(path):
    if not path or not os.path.exists(path):
        return None
    rel = os.path.relpath(path, STUDIO).replace(os.sep, "/")
    if not rel.startswith("samples/"):
        return None
    return "/" + rel + "?v=%d" % int(os.path.getmtime(path))


def _films():
    if not os.path.isdir(SEQ_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(SEQ_DIR) if f.endswith(".json") and not f.startswith("_"))


def _load(film):
    p = os.path.join(SEQ_DIR, film + ".json")
    if not os.path.exists(p):
        return None
    return json.load(open(p, encoding="utf-8"))


def _write(film, s):
    os.makedirs(SEQ_DIR, exist_ok=True)
    json.dump(s, open(os.path.join(SEQ_DIR, film + ".json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def _json(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def _check(script):
    for k in ("film", "cast", "place", "shots"):
        if k not in script:
            return "the script needs a %r" % k
    if not FILM_RE.match(str(script["film"])):
        return "film must be a short slug: lowercase letters, digits, dashes"
    if not isinstance(script["cast"], dict):
        return "cast must be a list of characters"
    for who, c in script["cast"].items():
        if not ID_RE.match(who):
            return "character id %r must be a short slug" % who
        if not (isinstance(c, dict) and c.get("prompt")):
            return "character %r needs a description" % who
    if not (isinstance(script["place"], dict) and script["place"].get("prompt")):
        return "the place needs a description"
    if not ID_RE.match(str(script["place"].get("id", ""))):
        return "the place needs a short id"
    ids = set()
    known = set(script["cast"]) | {script["place"]["id"]}
    for s in script["shots"]:
        if not SHOT_RE.match(str(s.get("id", ""))):
            return "shot ids are three digits (010, 020...)"
        if s["id"] in ids:
            return "shot %s appears twice" % s["id"]
        ids.add(s["id"])
        if not s.get("prompt"):
            return "shot %s needs a prompt (what happens)" % s["id"]
        try:
            if not (1 <= float(s.get("secs", 0)) <= 30):
                return "shot %s: seconds must be 1-30" % s["id"]
        except (TypeError, ValueError):
            return "shot %s: seconds must be a number" % s["id"]
        if s.get("engine", "ltx") not in ("ltx", "h3", "both", "previz"):
            return "shot %s: engine is ltx, h3, both or previz" % s["id"]
        refs = s.get("refs") or []
        for r in refs:
            if r not in known:
                return "shot %s refers to %r, which is not in the cast or the place" % (s["id"], r)
        if s.get("anchor") is not None and not str(s["anchor"]).strip() and s.get("engine") != "previz":
            return "shot %s: describe the start frame, or start on the place's plate" % s["id"]
        if s.get("anchor") and len(refs) != 3:
            return ("shot %s: a composed start frame takes exactly three references - repeat one, e.g. "
                    "[who, who, place]" % s["id"])
        if s.get("engine") == "previz" and (s.get("previz") or {}).get("scene") not in \
                [m["id"] for m in MODELS["previz"]]:
            return "shot %s: a physics shot needs a scene (%s)" % (
                s["id"], ", ".join(m["id"] for m in MODELS["previz"]))
        tr = s.get("trim")
        if tr is not None:
            try:
                ok = (isinstance(tr, dict) and PICK_RE.match(str(tr.get("take", ""))) and
                      float(tr.get("in") or 0) >= 0 and
                      (not tr.get("out") or float(tr["out"]) >= float(tr.get("in") or 0) + 0.2))
            except (TypeError, ValueError):
                ok = False
            if not ok:
                return "shot %s: a trim is {take, in, out}, with out at least 0.2 s after in" % s["id"]
        if s.get("anchor") is None and s.get("engine") != "previz" and refs and refs[0] != script["place"]["id"]:
            return "shot %s: with no start-frame description the shot starts on the plate - make the place its first reference" % s["id"]
    for k in ("grade", "avoid", "score_tags"):
        if k not in script:
            return "the script needs %r (a string; the skeleton has one)" % k
    return None


def _picks(film):
    p = os.path.join(_out(film), "picks.txt")
    if not os.path.exists(p):
        return {}
    return dict(kv.split("=", 1) for kv in open(p).read().strip().split(",") if "=" in kv)


def _write_picks(film, picks, order):
    line = ",".join("%s=%s" % (sid, picks[sid]) for sid in order if sid in picks)
    open(os.path.join(_out(film), "picks.txt"), "w").write(line + "\n")
    return line


def _take_file(film, token, sid):
    engine, _, seed = token.rpartition(":")
    stem = {"": "shot"}.get(engine, engine)
    return os.path.join(_out(film), "%s_%s_s%s.mp4" % (stem, sid, seed))


def _tail(path, n=80):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-n:])
    except Exception:
        return ""


def _running():
    return not _JOB["done"]


def _seedance():
    sys.path.insert(0, TOOLS)
    import importlib
    import seedance_suggest
    return importlib.reload(seedance_suggest)


SPECS = os.path.join(STUDIO, "shotspecs")


def _spec(film, sid):
    """The shot's spec sheet as the checker reads it (the .json spec_routes writes beside the .md):
    its promises, its flair, and whether it is locked - and to which take."""
    d = _json(os.path.join(SPECS, film, sid + ".json"), {})
    return {"has": os.path.exists(os.path.join(SPECS, film, sid + ".md")),
            "n_invariants": len(d.get("invariants", [])), "n_flair": len(d.get("flair", d.get("flare", []))),
            "invariants": [{"title": i.get("title") or i.get("id"), "rule": i.get("rule", ""), "why": i.get("why", "")}
                           for i in d.get("invariants", [])],
            "locked": bool(d.get("locked")), "locked_take": d.get("locked_take", ""),
            "locked_at": d.get("locked_at", "")}


def _refuse_locked(film, sids, what):
    locked = [i for i in sids if _spec(film, i)["locked"]]
    if locked:
        return {"error": "shot %s is locked on its spec sheet - unlock it there to %s" % (", ".join(locked), what)}, 409
    return None


# ------------------------------------------------------------------------------ the editor payload
def editor(film):
    if not FILM_RE.match(film or ""):
        return {"error": "bad film"}, 400
    s = _load(film)
    if s is None:
        return {"error": "no script %s" % film}, 404
    out = _out(film)
    files = set(os.listdir(out)) if os.path.isdir(out) else set()
    place = s["place"]["id"]
    refs_rec = _json(os.path.join(out, "refs.json"), {})
    refs = {}
    for who, c in s["cast"].items():
        p = os.path.join(out, "ref_%s.png" % who)
        refs[who] = {"kind": "cast", "role": c.get("role", ""), "prompt": c.get("prompt", ""),
                     "url": _url(p), "made": refs_rec.get(who)}
    p = os.path.join(out, "ref_%s.png" % place)
    refs[place] = {"kind": "place", "role": "the place", "prompt": s["place"].get("prompt", ""), "url": _url(p),
                   "made": refs_rec.get(place)}
    anchors = _json(os.path.join(out, "anchors.json"), {})
    ranked = _json(os.path.join(out, "ranked.json"), {})
    measured = _json(os.path.join(out, "measured.json"), {})
    overrides = _json(os.path.join(out, "picks_overrides.json"), {})
    picks = _picks(film)
    sd = _seedance()
    shots = []
    t = 0.0
    for sh in s["shots"]:
        sid = sh["id"]
        a = anchors.get(sid) or {}
        cands = []
        for name, v in sorted((a.get("candidates") or {}).items()):
            cands.append({"name": name, "url": _url(os.path.join(out, v.get("file", ""))), "mean": v.get("mean"),
                          "faces": v.get("faces")})
        for f in sorted(files):                      # candidates on disk that no record names yet
            m = re.match(r"^anchor_%s_(.+)\.png$" % sid, f)
            if m and m.group(1) != "h3" and m.group(1) not in [c["name"] for c in cands]:
                cands.append({"name": m.group(1), "url": _url(os.path.join(out, f)), "mean": None, "faces": None})
        rrow = ranked.get(sid) or {}
        rt = {r["take"]: r for r in rrow.get("takes", [])}
        takes = []
        for f in sorted(files):
            m = re.match(TAKE_RE % sid, f)
            if not m:
                continue
            stem, seed = m.group(1), m.group(2)
            r = rt.get(f, {})
            me = measured.get(f, {})
            takes.append({"take": f, "token": seed if stem == "shot" else "%s:%s" % (stem, seed),
                          "engine": stem, "seed": int(seed), "url": _url(os.path.join(out, f)),
                          "strip": _url(os.path.join(out, f[:-4] + "_strip.jpg")),
                          "faces": r.get("faces"), "line_hit": r.get("line_hit"), "heard": r.get("heard"),
                          "mean_db": r.get("mean_db"), "faults": r.get("faults"), "notes": r.get("notes"),
                          "score": r.get("score"), "camera": me.get("camera") or r.get("camera"),
                          "frames": me.get("frames") or r.get("frames"), "ranked": bool(r)})
        pick = picks.get(sid)
        pick_file = _take_file(film, pick, sid) if pick else None
        secs = float(sh.get("secs", 4))
        take_secs = None
        if pick_file and os.path.exists(pick_file):
            fr = (measured.get(os.path.basename(pick_file)) or {}).get("frames")
            if fr:
                secs = fr / 24.0
            take_secs = secs
            tr = sh.get("trim") or {}
            if tr.get("take") == pick:                 # the cut keeps only part of the take
                t_in = max(0.0, float(tr.get("in") or 0))
                t_out = min(secs, float(tr.get("out") or 0) or secs)
                secs = max(0.2, t_out - t_in)
        spec = _spec(film, sid)
        spec["drifted"] = spec["locked"] and spec["locked_take"] != (pick or "")
        shots.append(dict(sh, **{
            "start": round(t, 3), "dur": round(secs, 3), "take_secs": take_secs, "spec": spec,
            "anchor_url": _url(os.path.join(out, "anchor_%s.png" % sid)),
            "anchors": {"chosen": a.get("chosen"), "why": a.get("why"), "candidates": cands},
            "takes": takes, "pick": pick if (pick_file and os.path.exists(pick_file)) else None,
            "pick_why": (overrides.get(sid) or {}).get("why") or (rrow.get("why") if rrow.get("pick") == pick else None),
            "ranker_pick": rrow.get("pick"), "ranker_why": rrow.get("why"),
            "suggest": sd.suggest(sh, place, s["cast"], rrow),
        }))
        t += secs
    outs = {}
    for key, name in (("final", "%s_final.mp4"), ("final2x", "%s_final_2x.mp4"), ("annotated", "%s_annotated.mp4"),
                      ("filmic", "%s_filmic.mp4")):
        outs[key] = _url(os.path.join(out, name % film))
    outs["score"] = _url(os.path.join(out, "score.mp3"))
    return {"film": film, "script": s, "refs": refs, "shots": shots, "runtime": round(t, 3), "outputs": outs,
            "models": MODELS, "films": _films(), "job": status()}, 200


# ------------------------------------------------------------------------------ older GET views
STAGE_WRITES = {"cast": ["ref_*.png"], "sheet": ["sheet_*.png"], "anchors": ["anchor_*.png"],
                "shots": ["shot_*_s*.mp4"], "h3": ["h3_*_s*.mp4"], "score": ["measured.json"],
                "sheets": ["picks/*.jpg"], "music": ["score.mp3"], "finish": ["*_filmic.mp4"]}


ARCHIVE = os.path.join(SEQ_DIR, "_archive")


def _poster(film, s):
    """A picture for the film switcher: the first shot's start frame, else the place."""
    shots = s.get("shots") or []
    for p in ([os.path.join(_out(film), "anchor_%s.png" % shots[0]["id"])] if shots else []) + \
            [os.path.join(_out(film), "ref_%s.png" % (s.get("place") or {}).get("id", ""))]:
        u = _url(p)
        if u:
            return u
    return None


def listing():
    out = []
    for film in _films():
        s = _load(film) or {}
        has = {}
        for st, pats in STAGE_WRITES.items():
            has[st] = sum(len(glob.glob(os.path.join(_out(film), p))) for p in pats)
        sd = os.path.join(SPECS, film)
        out.append({"film": film, "title": s.get("title") or film, "cast": list((s.get("cast") or {}).keys()),
                    "place": (s.get("place") or {}).get("id"), "shots": [x.get("id") for x in s.get("shots", [])],
                    "logline": s.get("logline", ""), "poster": _poster(film, s),
                    "has": has, "specs": len([f for f in os.listdir(sd) if f.endswith(".md")]) if os.path.isdir(sd) else 0})
    archived = []
    if os.path.isdir(ARCHIVE):
        for f in sorted(os.listdir(ARCHIVE)):
            if f.endswith(".json"):
                a = _json(os.path.join(ARCHIVE, f), {})
                archived.append({"film": f[:-5], "title": a.get("title") or f[:-5], "shots": len(a.get("shots") or [])})
    return {"films": out, "archived": archived, "running": status()}, 200


def script(film):
    if not FILM_RE.match(film or ""):
        return {"error": "bad film"}, 400
    s = _load(film)
    if s is None:
        return {"error": "no script %s" % film}, 404
    return {"film": film, "script": s}, 200


def tree(film):
    if not FILM_RE.match(film or ""):
        return {"error": "bad film"}, 400
    out = _out(film)
    stages = {}
    for st, pats in STAGE_WRITES.items():
        fs = []
        for p in pats:
            fs += glob.glob(os.path.join(out, p))
        stages[st] = [{"name": os.path.relpath(f, out), "url": _url(f)} for f in sorted(set(fs)) if os.path.isfile(f)]
    return {"film": film, "stages": stages, "running": status()}, 200


# a line fight.py / previz_shot.py prints when one picture or take is finished (or skipped, or failed)
MADE_RE = re.compile(r"^\s+(?:shot|h3|pv|pvb|sd|anchor|ref)_\S+.*(?:\d+s\b|already there|FAILED)", re.M)


def status():
    log = _tail(_JOB["log"], 400) if _JOB["log"] else ""
    lines = [x.strip() for x in log.splitlines() if x.strip() and not x.startswith("$ ")]
    return {"running": _running(), "film": _JOB["film"], "op": _JOB["op"], "shots": _JOB["shots"],
            "started": _JOB["started"], "returncode": _JOB["rc"], "cmd": _JOB["cmd"], "id": _JOB.get("id"),
            # how far it has got: pictures and takes finished of those asked for, and what it said last
            "total": _JOB.get("total"), "done": len(MADE_RE.findall(log)) if _JOB.get("total") else None,
            "now": (lines[-1][:140] if lines else ""),
            "queue": [{"id": q["id"], "film": q["film"], "op": q["op"], "shots": q["shots"], "total": q["total"],
                       "at": q["at"]} for q in list(_QUEUE)],
            "last": getattr(_STATE, "LAST", None),
            "log": "".join(log.splitlines(True)[-80:])}


# ------------------------------------------------------------------------------ writes
def save(data):
    film = str(data.get("film") or "")
    s = data.get("script")
    if isinstance(s, str):
        try:
            s = json.loads(s)
        except ValueError as e:
            return {"error": "the script is not valid JSON: %s" % str(e)[:120]}, 400
    if not isinstance(s, dict):
        return {"error": "script must be an object"}, 400
    s["film"] = s.get("film") or film
    err = _check(s)
    if err:
        return {"error": err}, 400
    if FILM_RE.match(film) and s["film"] != film:
        return {"error": "the script's film (%s) does not match %s" % (s["film"], film)}, 400
    # a locked shot keeps its place in the cut: it cannot be deleted, and its trim cannot move
    old = _load(s["film"]) or {}
    new_shots = {x["id"]: x for x in s["shots"]}
    for x in old.get("shots", []):
        if not _spec(s["film"], x["id"])["locked"]:
            continue
        if x["id"] not in new_shots:
            return {"error": "shot %s is locked on its spec sheet - unlock it before deleting it" % x["id"]}, 409
        if (x.get("trim") or None) != (new_shots[x["id"]].get("trim") or None):
            return {"error": "shot %s is locked on its spec sheet - unlock it to change its trim" % x["id"]}, 409
    _write(s["film"], s)
    return {"ok": True, "film": s["film"]}, 200


def new(data):
    """A new shot script: a skeleton (with the look of another film, if asked), or a copy of one -
    its words, cast, place and shots, and if asked its cast and place pictures too, so a variation
    starts with the same people. A copy never brings takes, picks or trims: those belong to the
    original's renders."""
    film = str(data.get("film") or "").strip().lower()
    if not FILM_RE.match(film):
        return {"error": "name the film with a short slug: lowercase letters, digits, dashes"}, 400
    if _load(film) is not None:
        return {"error": "%s exists" % film}, 409
    if os.path.exists(os.path.join(ARCHIVE, film + ".json")):
        return {"error": "%s is an archived film - restore it, or pick another name" % film}, 409
    if os.path.isdir(os.path.join(STUDIO, "films", film)):
        # the spec sheets of both kinds of film live in shotspecs/<name>: one name, one film
        return {"error": "the film editor already has a film called %s - pick another name" % film}, 409
    src = str(data.get("from") or "")
    if src and FILM_RE.match(src) and _load(src):
        s = _load(src)
        s.pop("_comment", None)
        for x in s.get("shots", []):
            x.pop("trim", None)
    else:
        src = ""
        s = json.loads(json.dumps(SKELETON))
        look = str(data.get("look_from") or "")
        if look and FILM_RE.match(look) and _load(look):
            L = _load(look)
            for k in ("grade", "avoid", "realism", "score_tags", "score_tags_b"):
                if L.get(k):
                    s[k] = L[k]
    s["film"] = film
    s["title"] = str(data.get("title") or "").strip()[:80] or film.replace("-", " ").upper()
    if data.get("logline") is not None and str(data.get("logline")).strip():
        s["logline"] = str(data.get("logline")).strip()[:300]
    _write(film, s)
    out = _out(film)
    os.makedirs(out, exist_ok=True)
    copied = []
    if src and data.get("copy_refs"):
        import shutil
        so = _out(src)
        rec, keep = _json(os.path.join(so, "refs.json"), {}), {}
        wanted = set(s.get("cast") or {}) | {(s.get("place") or {}).get("id")}
        for f in sorted(os.listdir(so)) if os.path.isdir(so) else []:
            m = re.match(r"^ref_(.+)\.png$", f)
            if m and m.group(1) in wanted:
                shutil.copy(os.path.join(so, f), os.path.join(out, f))
                copied.append(m.group(1))
                if m.group(1) in rec:
                    keep[m.group(1)] = rec[m.group(1)]
        if keep:
            json.dump(keep, open(os.path.join(out, "refs.json"), "w"), indent=1)
    return {"ok": True, "film": film, "copied_refs": copied}, 200


def archive(data):
    """Put a film away: its script moves to shotscripts/_archive/, out of every list. Its renders
    and spec sheets stay where they are, so restoring it brings everything back."""
    film = str(data.get("film") or "")
    if not FILM_RE.match(film) or _load(film) is None:
        return {"error": "no film %s" % film}, 404
    if _running() and _JOB["film"] == film:
        return {"error": "a job is running on %s - let it finish or stop it first" % film}, 409
    os.makedirs(ARCHIVE, exist_ok=True)
    os.replace(os.path.join(SEQ_DIR, film + ".json"), os.path.join(ARCHIVE, film + ".json"))
    return {"ok": True, "film": film}, 200


def restore(data):
    film = str(data.get("film") or "")
    p = os.path.join(ARCHIVE, film + ".json")
    if not FILM_RE.match(film) or not os.path.exists(p):
        return {"error": "no archived film %s" % film}, 404
    if _load(film) is not None:
        return {"error": "a film called %s exists - archive or rename it first" % film}, 409
    os.replace(p, os.path.join(SEQ_DIR, film + ".json"))
    return {"ok": True, "film": film}, 200


def pick(data):
    film, sid, tok = str(data.get("film") or ""), str(data.get("shot") or ""), str(data.get("token") or "")
    if not (FILM_RE.match(film) and SHOT_RE.match(sid) and PICK_RE.match(tok)):
        return {"error": "pick needs film, shot and a take token like 202 or h3:11"}, 400
    if not os.path.exists(_take_file(film, tok, sid)):
        return {"error": "no such take"}, 404
    sp = _spec(film, sid)
    if sp["locked"] and tok != sp["locked_take"]:
        return {"error": "shot %s is locked to take %s on its spec sheet - unlock it there to change the take"
                         % (sid, sp["locked_take"] or "(none)")}, 409
    s = _load(film)
    order = [x["id"] for x in s["shots"]]
    picks = _picks(film)
    picks[sid] = tok
    line = _write_picks(film, picks, order)
    ranked = _json(os.path.join(_out(film), "ranked.json"), {})
    op = os.path.join(_out(film), "picks_overrides.json")
    ov = _json(op, {})
    # every reason a take was picked for is kept, so picking it again brings its reason back
    hp = os.path.join(_out(film), "picks_reasons.json")
    hist = _json(hp, {})
    prev = ov.get(sid) or {}
    if prev.get("pick") and prev.get("why"):
        hist.setdefault(sid, {})[prev["pick"]] = prev["why"]
    rp = (ranked.get(sid) or {}).get("pick")
    why = str(data.get("why") or "").strip()[:300]
    if why:
        hist.setdefault(sid, {})[tok] = why
    if rp and rp != tok:
        ov[sid] = {"pick": tok, "ranker": rp, "why": why or hist.get(sid, {}).get(tok) or "picked in the editor"}
    else:
        ov.pop(sid, None)
    json.dump(ov, open(op, "w"), indent=1)
    json.dump(hist, open(hp, "w"), indent=1)
    return {"ok": True, "picks": line}, 200


def anchor(data):
    film, sid, name = str(data.get("film") or ""), str(data.get("shot") or ""), str(data.get("candidate") or "")
    if not (FILM_RE.match(film) and SHOT_RE.match(sid) and re.match(r"^[a-z0-9_]{1,40}$", name)):
        return {"error": "anchor needs film, shot and a candidate name"}, 400
    no = _refuse_locked(film, [sid], "change its start frame")
    if no:
        return no
    out = _out(film)
    src = os.path.join(out, "anchor_%s_%s.png" % (sid, name))
    if not os.path.exists(src):
        return {"error": "no candidate %s" % name}, 404
    import shutil
    shutil.copy(src, os.path.join(out, "anchor_%s.png" % sid))
    ap = os.path.join(out, "anchors.json")
    rec = _json(ap, {})
    r = rec.setdefault(sid, {"candidates": {}})
    r.setdefault("candidates", {}).setdefault(name, {"file": os.path.basename(src), "faces": None, "mean": None})
    r["chosen"], r["why"] = name, "chosen in the editor"
    json.dump(rec, open(ap, "w"), indent=1)
    return {"ok": True}, 200


def seedance_save(data):
    film, sid = str(data.get("film") or ""), str(data.get("shot") or "")
    s = _load(film) if FILM_RE.match(film) else None
    if s is None or not SHOT_RE.match(sid):
        return {"error": "no such film or shot"}, 404
    sh = next((x for x in s["shots"] if x["id"] == sid), None)
    if sh is None:
        return {"error": "no shot %s" % sid}, 404
    prompt = str(data.get("prompt") or "").strip()
    if not prompt:
        sh.pop("seedance", None)
    else:
        try:
            secs = max(3, min(15, int(data.get("secs") or sh.get("secs") or 5)))
        except (TypeError, ValueError):
            secs = 5
        sh["seedance"] = {"secs": secs, "why": str(data.get("why") or "flagged in the editor")[:600],
                          "prompt": prompt[:4000]}
    _write(film, s)
    return {"ok": True}, 200


def upload(data):
    """Your own picture as a reference (a character or the place) or as a shot's start frame."""
    film, kind, ident = str(data.get("film") or ""), str(data.get("kind") or ""), str(data.get("id") or "")
    s = _load(film) if FILM_RE.match(film) else None
    if s is None:
        return {"error": "no such film"}, 404
    m = re.match(r"^data:image/(png|jpeg|jpg|webp);base64,(.+)$", str(data.get("dataurl") or ""), re.S)
    if not m:
        return {"error": "send a PNG, JPEG or WebP as a data URL"}, 400
    raw = base64.b64decode(m.group(2))
    if len(raw) > 25 * 1024 * 1024:
        return {"error": "that picture is over 25 MB"}, 400
    from PIL import Image
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    out = _out(film)
    os.makedirs(out, exist_ok=True)

    def cover(im, size):
        r = max(size[0] / im.width, size[1] / im.height)
        im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
        l, t = (im.width - size[0]) // 2, (im.height - size[1]) // 2
        return im.crop((l, t, l + size[0], t + size[1]))
    if kind == "ref":
        place = s["place"]["id"]
        if ident != place and ident not in s["cast"]:
            return {"error": "no reference %s in this film" % ident}, 404
        size = (1280, 720) if ident == place else (768, 1344)
        cover(im, size).save(os.path.join(out, "ref_%s.png" % ident))
        rp = os.path.join(out, "refs.json")
        rec = _json(rp, {})
        rec[ident] = {"engine": "upload", "seed": None, "prompt": None, "at": int(time.time())}
        json.dump(rec, open(rp, "w"), indent=1)
        return {"ok": True}, 200
    if kind == "anchor":
        if not SHOT_RE.match(ident):
            return {"error": "a start frame belongs to a shot id"}, 400
        no = _refuse_locked(film, [ident], "change its start frame")
        if no:
            return no
        cover(im, (1280, 720)).save(os.path.join(out, "anchor_%s_upload.png" % ident))
        return anchor({"film": film, "shot": ident, "candidate": "upload"})
    return {"error": "kind is ref or anchor"}, 400


# ------------------------------------------------------------------------------ jobs
def _seeds(raw, default=("11", "202", "3003")):
    if raw in (None, "", []):
        return list(default), None
    if isinstance(raw, list):
        raw = " ".join(str(x) for x in raw)
    parts = [p for p in re.split(r"[,\s]+", str(raw).strip()) if p]
    if not parts or not all(SEED_RE.match(p) for p in parts) or len(parts) > 8:
        return None, "seeds: up to eight whole numbers, like 11 202 3003"
    return parts, None


def _shot_list(data, s):
    ids = data.get("shots") or []
    if isinstance(ids, str):
        ids = [x for x in re.split(r"[,\s]+", ids) if x]
    have = {x["id"] for x in s["shots"]}
    bad = [i for i in ids if i not in have]
    if bad:
        return None, "no shot %s" % ", ".join(bad)
    return ids, None


def _start(film, op, shots, cmds, total=None):
    """Run it now, or - with a job running, or others already waiting - queue it behind them.
    Called with _LOCK held."""
    item = {"id": "%d%03d" % (time.time(), len(_QUEUE)), "film": film, "op": op, "shots": shots, "cmds": cmds,
            "total": total, "at": int(time.time())}
    if _running() or _QUEUE:
        _QUEUE.append(item)
        if not _running():
            _launch(_QUEUE.pop(0))
        return {"ok": True, "film": film, "op": op, "queued": len(_QUEUE),
                "cmd": " && ".join(" ".join(shlex.quote(c) for c in cmd) for cmd in cmds)}, 200
    return _launch(item)


def _launch(item):
    film, op, shots, cmds, total = item["film"], item["op"], item["shots"], item["cmds"], item["total"]
    out = _out(film)
    os.makedirs(out, exist_ok=True)
    log = os.path.join(out, "_app_%s.log" % op)
    lf = open(log, "w", encoding="utf-8")
    _JOB.update({"proc": None, "film": film, "op": op, "shots": shots, "started": int(time.time()), "log": log,
                 "cmd": " && ".join(" ".join(shlex.quote(c) for c in cmd) for cmd in cmds), "abort": False,
                 "done": False, "rc": None, "total": total or None, "id": item["id"]})
    env = dict(os.environ, PYTHONUNBUFFERED="1", FIGHT_SEQUENCE=film)

    def work():
        rc = 0
        for cmd in cmds:
            if _JOB["abort"]:
                rc = -15
                break
            lf.write("\n$ %s\n" % " ".join(shlex.quote(c) for c in cmd))
            lf.flush()
            try:
                p = subprocess.Popen(cmd, cwd=ROOT, stdout=lf, stderr=subprocess.STDOUT, env=env)
            except OSError as e:
                lf.write("could not start: %s\n" % e)
                rc = 1
                break
            _JOB["proc"] = p
            rc = p.wait()
            if rc != 0:
                lf.write("\n[step exited %s - stopping]\n" % rc)
                break
        lf.write("\n[exit %s]\n" % rc)
        lf.close()
        with _LOCK:
            _JOB.update({"done": True, "rc": rc, "proc": None})
            # the page reads this to say how the job ended even when the next one starts at once
            _STATE.LAST = {"id": item["id"], "op": op, "film": film, "shots": shots, "rc": rc, "at": int(time.time())}
            if _QUEUE:                          # the next one waiting starts now
                _launch(_QUEUE.pop(0))
    threading.Thread(target=work, daemon=True).start()
    return {"ok": True, "film": film, "op": op, "cmd": _JOB["cmd"]}, 200


def plan(film, seeds=None, anchor_seeds=None):
    """What 'make everything missing' would make: the cast and place pictures not drawn yet, the start
    frames not drawn yet, and a first round of takes for every shot with none - skipping locked
    shots - with a count for the progress bar and a rough time from what the demo films measured
    (a Qwen start frame ~14 s, an LTX-2.5 take ~6 s + 4 s per second of film, an H3 take ~45 s)."""
    s = _load(film)
    if s is None:
        return None
    out = _out(film)
    files = set(os.listdir(out)) if os.path.isdir(out) else set()
    seeds = list(seeds or ["11", "202", "3003"])
    aseeds = list(anchor_seeds or ["11", "202"])
    cast = [r for r in list(s["cast"]) + [s["place"]["id"]] if "ref_%s.png" % r not in files]
    anchors, takes, locked, skipped = [], [], [], []
    for x in s["shots"]:
        sid, eng = x["id"], x.get("engine", "ltx")
        if _spec(film, sid)["locked"]:
            locked.append(sid)
            continue
        if eng != "previz" and "anchor_%s.png" % sid not in files:
            anchors.append({"id": sid, "plate": x.get("anchor") is None})
        if not any(re.match(TAKE_RE % sid, f) for f in files):
            if eng == "previz" and not x.get("previz"):
                skipped.append({"id": sid, "why": "a physics shot with no scene chosen"})
                continue
            takes.append({"id": sid, "engine": eng, "secs": float(x.get("secs") or 4)})
    est = 20 * len(cast) + sum(1 if a["plate"] else 17 * len(aseeds) for a in anchors)
    for t in takes:
        per = {"ltx": 6 + 4 * t["secs"], "h3": 45, "both": 51 + 4 * t["secs"], "previz": 45}.get(t["engine"], 30)
        est += (per + 10) * len(seeds) + (90 if t["engine"] == "previz" else 0)
    total = len(cast) + sum(0 if a["plate"] else len(aseeds) for a in anchors) + \
        sum(len(seeds) * (2 if t["engine"] == "both" else 1) for t in takes)
    return {"film": film, "cast": cast, "anchors": anchors, "takes": takes, "locked": locked, "skipped": skipped,
            "seeds": seeds, "anchor_seeds": aseeds, "estimate": int(est), "total": total}


def run(data):
    with _LOCK:
        # with a job running, this one is queued behind it (_start) rather than refused
        film = str(data.get("film") or "")
        s = _load(film) if FILM_RE.match(film) else None
        if s is None:
            return {"error": "no script %r" % film}, 404
        err = _check(s)
        if err:
            return {"error": "the script will not run: " + err}, 400
        op = str(data.get("op") or data.get("stage") or "")
        py = ["python3", FIGHT, "--sequence", film]
        pyv = [PYVENV, FIGHT, "--sequence", film]
        rank = [PYVENV, os.path.join(TOOLS, "take_rank.py"), "--sequence", film]
        shots, err = _shot_list(data, s)
        if err:
            return {"error": err}, 400
        if op in ("anchors", "takes", "seedance"):
            # a locked shot is "not to be rebuilt": its spec sheet says so, and the page greys it
            no = _refuse_locked(film, shots, "make new start frames or takes for it")
            if no:
                return no
        if op == "cast":
            only = str(data.get("only") or "").strip()
            engine = str(data.get("engine") or "flux2")
            if engine not in [m["id"] for m in MODELS["cast"]]:
                return {"error": "cast model is flux2, krea2 or qwen21"}, 400
            cmd = py + ["--cast", "--cast-engine", engine]
            if only:
                if only not in s["cast"] and only != s["place"]["id"]:
                    return {"error": "no reference %s" % only}, 400
                seed = str(data.get("seed") or "4242")
                if not SEED_RE.match(seed):
                    return {"error": "seed: a whole number"}, 400
                cmd += ["--only", only, "--force", "--seed", seed]
            return _start(film, "cast", [], [cmd], total=1 if only else len(s["cast"]) + 1)
        if op == "anchors":
            if not shots:
                return {"error": "name the shots to draw start frames for"}, 400
            comp = str(data.get("compositor") or "qwen21")
            if comp not in ("qwen21", "flux2", "best"):
                return {"error": "compositor is qwen21, flux2 or best"}, 400
            seeds, err = _seeds(data.get("seeds"), ("11", "202"))
            if err:
                return {"error": err}, 400
            cmd = py + ["--anchors", "--only-shots", ",".join(shots), "--compositor", comp, "--redraw",
                        "--qseeds"] + seeds
            if data.get("force"):
                cmd.append("--force")
            drawn = sum((len(seeds) if comp in ("qwen21", "best") else 0) + (1 if comp in ("flux2", "best") else 0)
                        for x in s["shots"] if x["id"] in shots and x.get("anchor") is not None
                        and x.get("engine") != "previz")
            return _start(film, "anchors", shots, [cmd], total=drawn)
        if op == "takes":
            if not shots:
                return {"error": "name the shots to render"}, 400
            engine = str(data.get("engine") or "ltx")
            seeds, err = _seeds(data.get("seeds"))
            if err:
                return {"error": err}, 400
            missing = [i for i in shots if not os.path.exists(os.path.join(_out(film), "anchor_%s.png" % i))
                       and engine != "previz"]
            if missing:
                return {"error": "draw a start frame first for shot %s" % ", ".join(missing)}, 400
            # replace: render these seeds again (the words changed); otherwise a seed already rendered
            # is kept and only new seeds cost time
            force = ["--force"] if data.get("force") else []
            cmds = []
            if engine in ("ltx", "both"):
                cmds.append(py + ["--shots", "--only-shots", ",".join(shots), "--seeds"] + seeds + force)
            if engine in ("h3", "both"):
                cmds.append(py + ["--h3", ",".join(shots), "--seeds"] + seeds + force)
            if engine == "previz":
                for i in shots:
                    sh = next(x for x in s["shots"] if x["id"] == i)
                    if not sh.get("previz"):
                        return {"error": "shot %s has no previz scene - choose one in the inspector" % i}, 400
                    cmds.append(["python3", os.path.join(TOOLS, "previz_shot.py"), "--sequence", film, "--shot", i,
                                 "--seeds"] + seeds + ["--bypass-seeds"] + force)
            if not cmds:
                return {"error": "engine is ltx, h3, both or previz"}, 400
            cmds.append(py + ["--score"])
            cmds.append(rank + ["--only-shots", ",".join(shots)])
            per = {"ltx": 1, "h3": 1, "both": 2, "previz": 1}.get(engine, 1)
            return _start(film, "takes", shots, cmds, total=len(seeds) * per * len(shots))
        if op == "rank":
            cmds = [py + ["--score"], rank + (["--only-shots", ",".join(shots)] if shots else [])]
            return _start(film, "rank", shots, cmds)
        if op == "missing":
            # one job, in order: pictures, start frames, takes, then measure and rank what was made
            seeds, err = _seeds(data.get("seeds"))
            if err:
                return {"error": err}, 400
            aseeds, err = _seeds(data.get("anchor_seeds"), ("11", "202"))
            if err:
                return {"error": err}, 400
            p = plan(film, seeds, aseeds)
            cmds = []
            if p["cast"]:
                engine = str(data.get("cast_engine") or "flux2")
                if engine not in [m["id"] for m in MODELS["cast"]]:
                    return {"error": "cast model is flux2, krea2 or qwen21"}, 400
                cmds.append(py + ["--cast", "--cast-engine", engine])      # draws only the ones missing
            if p["anchors"]:
                cmds.append(py + ["--anchors", "--only-shots", ",".join(a["id"] for a in p["anchors"]),
                                  "--compositor", "qwen21", "--qseeds"] + aseeds)
            ltx = [t["id"] for t in p["takes"] if t["engine"] in ("ltx", "both")]
            h3 = [t["id"] for t in p["takes"] if t["engine"] in ("h3", "both")]
            pv = [t["id"] for t in p["takes"] if t["engine"] == "previz"]
            if ltx:
                cmds.append(py + ["--shots", "--only-shots", ",".join(ltx), "--seeds"] + seeds)
            if h3:
                cmds.append(py + ["--h3", ",".join(h3), "--seeds"] + seeds)
            for i in pv:
                cmds.append(["python3", os.path.join(TOOLS, "previz_shot.py"), "--sequence", film, "--shot", i,
                             "--seeds"] + seeds + ["--bypass-seeds"])
            made = [t["id"] for t in p["takes"]]
            if made:
                cmds.append(py + ["--score"])
                cmds.append(rank + ["--only-shots", ",".join(made)])
            if not cmds:
                return {"error": "nothing is missing - every shot has its pictures, its start frame and takes"}, 400
            touched = [x["id"] for x in s["shots"] if x["id"] in {a["id"] for a in p["anchors"]} | set(made)]
            return _start(film, "missing", touched, cmds, total=p["total"])
        if op == "music":
            # as long as the cut really is - the picked takes, trimmed - not the script's planned seconds
            payload, _ = editor(film)
            secs = "%.1f" % (float(payload.get("runtime") or 0) + 3.0)
            return _start(film, "music", [], [py + ["--music", "--force", "--music-secs", secs]])
        if op == "assemble":
            picks = _picks(film)
            order = [x["id"] for x in s["shots"]]
            missing = [i for i in order if i not in picks or not os.path.exists(_take_file(film, picks[i], i))]
            if missing:
                return {"error": "no take is picked for shot %s" % ", ".join(missing)}, 400
            line = ",".join("%s=%s" % (i, picks[i]) for i in order)
            fin = (pyv if data.get("master") else py) + ["--finish", "--picks", line]
            if data.get("master"):
                fin.append("--master")
            cmds = [fin, ["python3", os.path.join(TOOLS, "film_cards.py"), "--sequence", film, "--picks", line]]
            return _start(film, "assemble", [], cmds)
        if op == "seedance":
            # the paid door: the page asks the person to confirm the price first, and it only works
            # with somebody signed in to a Comfy account in the ComfyUI frontend
            if not data.get("confirm_paid") or len(shots) != 1:
                return {"error": "the paid engine runs one shot at a time and needs confirm_paid"}, 400
            res = str(data.get("resolution") or "1080p")
            if res not in ("480p", "720p", "1080p"):
                return {"error": "resolution is 480p, 720p or 1080p"}, 400
            return _start(film, "seedance", shots, [py + ["--seedance", shots[0], "--resolution", res, "--force"]])
        if op in ("stage",) or data.get("stage"):
            return _old_stage(film, s, data)
        return {"error": "unknown op %r" % op}, 400


def _old_stage(film, s, data):
    """The first /shots page's whole-film stage buttons, kept so its links still work."""
    stage = str(data.get("stage") or "")
    flags = {"cast": ["--cast"], "anchors": ["--anchors"], "shots": ["--shots"], "score": ["--score"],
             "sheets": ["--sheets"], "music": ["--music"], "finish": ["--finish"]}.get(stage)
    if not flags:
        return {"error": "unknown stage %r" % stage}, 400
    cmd = ["python3", FIGHT, "--sequence", film] + flags
    if stage == "shots":
        seeds, err = _seeds(data.get("seeds"))
        if err:
            return {"error": err}, 400
        cmd += ["--seeds"] + seeds
    if stage == "finish":
        picks = str(data.get("picks") or "").replace(" ", "")
        if not PICKS_RE.match(picks):
            return {"error": "picks look like 010=202,020=11,030=h3:3003"}, 400
        cmd += ["--picks", picks]
    return _start(film, stage, [], [cmd])


def stop(data=None):
    """Stop the running job ({}), take one waiting job off the queue ({queue_id}), or clear the queue
    and stop the running job ({all: true}). The queue moves on after a stop."""
    data = data or {}
    with _LOCK:
        if data.get("queue_id"):
            before = len(_QUEUE)
            _QUEUE[:] = [q for q in _QUEUE if q["id"] != str(data["queue_id"])]
            return ({"ok": True, "removed": before - len(_QUEUE)}, 200) if before != len(_QUEUE) else \
                ({"error": "that job is not waiting any more"}, 404)
        if data.get("all"):
            _QUEUE.clear()
    if not _running():
        return {"ok": True, "note": "nothing was running"}, 200
    _JOB["abort"] = True
    p = _JOB["proc"]
    if p is not None and p.poll() is None:
        p.terminate()
        for _ in range(20):
            if p.poll() is not None:
                break
            time.sleep(0.25)
        if p.poll() is None:
            p.kill()
    return {"ok": True, "stopped": _JOB["op"], "film": _JOB["film"]}, 200


# ------------------------------------------------------------------------------ dispatch
def get(path, query):
    """serve.py hands the path after /api/shots and the parsed query."""
    q = {k: (v[0] if isinstance(v, list) else v) for k, v in (query or {}).items()}
    rest = path.strip("/")
    if rest == "editor":
        return editor(q.get("film"))
    if rest in ("", "list"):
        return listing()
    if rest == "script":
        return script(q.get("film"))
    if rest == "tree":
        return tree(q.get("film"))
    if rest == "status":
        return status(), 200
    if rest == "plan":
        film = q.get("film") or ""
        if not FILM_RE.match(film):
            return {"error": "bad film"}, 400
        seeds, err = _seeds(q.get("seeds"))
        aseeds, err2 = _seeds(q.get("anchor_seeds"), ("11", "202"))
        if err or err2:
            return {"error": err or err2}, 400
        p = plan(film, seeds, aseeds)
        return (p, 200) if p else ({"error": "no script %s" % film}, 404)
    return {"error": "unknown shots route"}, 404


def post(path, data):
    rest = path.strip("/")
    fn = {"save": save, "new": new, "run": run, "stop": stop, "pick": pick, "anchor": anchor,
          "seedance": seedance_save, "upload": upload, "archive": archive, "restore": restore}.get(rest)
    if not fn:
        return {"error": "unknown shots route"}, 404
    return fn(data or {})
