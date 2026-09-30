#!/usr/bin/env python3
"""studio/_tools/shots_routes.py - the shot-script pipeline as an app page: /shots, /api/shots/*.

The method that studio/_tools/fight.py runs from the shell (playbook §98, craft/ACTION_SEQUENCE.md)
- refs, then start frames, then shots, then read the takes, then finish - has nine stages and a
dozen flags. This puts the same stages on one page in order, each with what it writes, what to
look at, and one button. It runs the SAME tool with the SAME flags; nothing here can do what the
shell cannot, and the log the page shows is the tool's own stdout.

    GET  /shots                      the page (studio/shots.html)
    GET  /api/shots/list             every shot script, with which stages have output on disk
    GET  /api/shots/script?film=X    one script
    GET  /api/shots/tree?film=X      the outputs per stage as /samples URLs, measured.json, the log
    GET  /api/shots/status           the running job, if any, and its log tail
    POST /api/shots/save  {film, script}          write studio/shotscripts/<film>.json (schema-checked)
    POST /api/shots/new   {film}                  a new script from the skeleton
    POST /api/shots/run   {film, stage, seeds, shot, picks, master, force, only, seed}
    POST /api/shots/stop

One job at a time, on purpose: every stage holds the GPU, and two fight.py runs on one film
would race each other's files. Kept out of serve.py because it owns a child process.
"""
import glob
import json
import os
import re
import shlex
import subprocess
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
SEED_RE = re.compile(r"^\d{1,9}$")
PICKS_RE = re.compile(r"^\d{3}=(h3:)?\d{1,9}(,\d{3}=(h3:)?\d{1,9})*$")

# The stages, in the order the method runs them. `writes` is what the page looks for on disk to
# call a stage done; `look` is what a person should check before pressing the next button.
STAGES = [
    {"id": "cast", "title": "1 · Cast and place references", "flags": ["--cast"],
     "writes": ["ref_*.png"], "tool": "fight",
     "what": "One full-length picture per character on a plain grey backdrop, and one plate of the place, "
             "from the descriptions in the script (Flux 2, workflow 40). These are the pictures every later step "
             "refers to; a character is never described again.",
     "look": "Is each person who the script meant? Re-roll one with a new seed rather than editing the "
             "words - the face is what will be carried, so it has to be one you accept."},
    {"id": "sheet", "title": "2 · Reference sheet", "flags": [], "writes": ["sheet_*.png"], "tool": "refsheet",
     "what": "The cast faces, figures and the plate on one black board with no text: the Ingredients "
             "adapter (workflow 82) reads it to keep the same people and room inside a whole clip.",
     "look": "Faces should be the biggest panels. Nothing else is needed from you."},
    {"id": "anchors", "title": "3 · Start frames", "flags": ["--anchors"], "writes": ["anchor_*.png"],
     "tool": "fight",
     "what": "One composed frame per shot from the shot's references (Qwen-Image-2.1 by default since 2026-09-29, up to sixteen references; Flux 2 on request): "
             "the place, who is in it, where they stand. The start frame fixes where a shot BEGINS.",
     "look": "Right people, right room, right framing. A wrong start frame cannot be fixed by the video."},
    {"id": "shots", "title": "4 · Shots", "flags": ["--shots"], "writes": ["shot_*_s*.mp4"], "tool": "fight",
     "args": ["seeds"],
     "what": "Every shot rendered from its start frame on LTX-2.5 with sound, once per seed. Each take "
             "gets a strip of eight frames beside it.",
     "look": "Watch the strips first: a face that changes, people who appear, a camera that runs away. "
             "Three seeds is the floor for a pick."},
    {"id": "h3", "title": "5 · An effects or in-place beat on H3 (optional)", "flags": ["--h3"],
     "writes": ["h3_*_s*.mp4"], "tool": "fight", "args": ["shot", "seeds"],
     "what": "The same shot on MiniMax H3, which keeps the start frame exactly and clears an effect where "
             "LTX lets it accumulate (§98.3-98.4). Name the shot.",
     "look": "Compare its strip with the LTX takes of the same shot; pick by fewest faults, not by look."},
    {"id": "score", "title": "6 · Score the takes", "flags": ["--score"], "writes": ["measured.json"],
     "tool": "fight",
     "what": "Camera against the ask (push, pan, tilt, per take) and frame counts, into measured.json.",
     "look": "A take whose camera did something the shot did not ask for is a fault."},
    {"id": "sheets", "title": "7 · Contact boards", "flags": ["--sheets"], "writes": ["picks/*.jpg"],
     "tool": "fight",
     "what": "One board per shot with every take's strip and its measured camera, for choosing.",
     "look": "Choose one take per shot here. Write the choices as 010=202,020=11 for the finish."},
    {"id": "music", "title": "8 · Music bed", "flags": ["--music"], "writes": ["score.mp3"], "tool": "fight",
     "what": "The scene's bed from ACE-Step, from the score tags in the script, at the film's length.",
     "look": "Nothing to check yet; it is mixed under the takes at the finish."},
    {"id": "finish", "title": "9 · Finish", "flags": ["--finish"], "writes": ["*_filmic.mp4"], "tool": "fight",
     "args": ["picks", "master"],
     "what": "The picked takes conformed and cut in order, one grade over the whole film, the bed under "
             "at half level, loudness to -16 LUFS, the frame count checked against the takes, and "
             "optionally the 2x master.",
     "look": "Play it. The frame count line in the log must match the takes' total."},
]

SKELETON = {
    "_comment": "A shot script: the story as data. Edit on /shots or by hand; studio/_tools/fight.py runs it.",
    "film": "", "grade": ("Cinematic film, cool blue-green base, one warm practical, filmic contrast, "
                          "deep blacks with detail, fine grain, anamorphic."),
    "avoid": ("lowres, blurry, deformed limbs, fused fingers, extra limbs, doubled figure, two of the same "
              "person, melting face, morphing, warping, text, watermark, nsfw"),
    "score_tags": "sparse solo piano, room tone, slow, patient, instrumental, no percussion, no vocals",
    "realism": ("Unretouched photograph, available light, visible skin texture and pores, fine film grain, "
                "shallow depth of field, no retouching, no gloss."),
    "place": {"id": "room", "prompt": "Wide photograph of an empty place, nobody in it: ... "},
    "cast": {"someone": {"role": "the lead", "prompt": ("Full-length reference photograph of a person "
                                                        "against a plain mid-grey backdrop, even soft light, "
                                                        "standing still, facing the camera: ...")}},
    "shots": [
        {"id": "010", "title": "the place", "secs": 4, "refs": ["room"], "anchor": None,
         "avoid_extra": "people, a person, a figure, a crowd, hands",
         "prompt": "Nothing moves but the light. Static camera. Room tone; no music."},
        {"id": "020", "title": "the look", "secs": 5, "refs": ["someone", "someone", "room"],
         "anchor": "A still frame from a live-action film, a MEDIUM SHOT, the person of reference one in the "
                   "place of reference three, facing the camera.",
         "prompt": "They look up slowly and say, quietly: \"...\". Static camera. Room tone, their voice; no music."},
    ],
}

_JOB = {"proc": None, "film": None, "stage": None, "started": None, "log": None, "rc": None, "cmd": None}
_LOCK = threading.Lock()


# ------------------------------------------------------------------------------ helpers
def _out(film):
    return os.path.join(STUDIO, "samples", "fight", film)


def _url(path):
    rel = os.path.relpath(path, STUDIO).replace(os.sep, "/")
    return "/samples/" + rel[len("samples/"):] if rel.startswith("samples/") else None


def _films():
    if not os.path.isdir(SEQ_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(SEQ_DIR) if f.endswith(".json"))


def _load(film):
    p = os.path.join(SEQ_DIR, film + ".json")
    if not os.path.exists(p):
        return None
    return json.load(open(p, encoding="utf-8"))


def _check(script):
    for k in ("film", "cast", "place", "shots"):
        if k not in script:
            return "the script needs a %r" % k
    if not FILM_RE.match(str(script["film"])):
        return "film must be a short slug: lowercase letters, digits, dashes"
    if not isinstance(script["cast"], dict) or not script["cast"]:
        return "cast must name at least one character"
    for who, c in script["cast"].items():
        if not FILM_RE.match(who):
            return "character id %r must be a slug" % who
        if not (isinstance(c, dict) and c.get("prompt")):
            return "character %r needs a prompt" % who
    if not (isinstance(script["place"], dict) and script["place"].get("prompt")):
        return "place needs a prompt"
    ids = set()
    known = set(script["cast"]) | {script["place"].get("id", "court")}
    for s in script["shots"]:
        if not re.match(r"^\d{3}$", str(s.get("id", ""))):
            return "shot ids are three digits (010, 020...)"
        if s["id"] in ids:
            return "shot %s appears twice" % s["id"]
        ids.add(s["id"])
        if not s.get("prompt"):
            return "shot %s needs a prompt (what happens)" % s["id"]
        try:
            if not (1 <= float(s.get("secs", 0)) <= 30):
                return "shot %s: secs must be 1-30" % s["id"]
        except (TypeError, ValueError):
            return "shot %s: secs must be a number" % s["id"]
        for r in s.get("refs", []):
            if r not in known:
                return "shot %s refers to %r, which is not in the cast or the place" % (s["id"], r)
    for k in ("grade", "avoid", "score_tags"):
        if k not in script:
            return "the script needs %r (a string; the skeleton has one)" % k
    return None


def _stage_files(film, st):
    out = _out(film)
    files = []
    for pat in st["writes"]:
        files += glob.glob(os.path.join(out, pat))
    files = sorted(set(files))
    return [{"name": os.path.relpath(f, out), "url": _url(f), "mtime": int(os.path.getmtime(f)),
             "size": os.path.getsize(f)} for f in files if os.path.isfile(f)]


def _tail(path, n=60):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-n:])
    except Exception:
        return ""


def _running():
    p = _JOB["proc"]
    return p is not None and p.poll() is None


# ------------------------------------------------------------------------------ GET
def listing():
    out = []
    for film in _films():
        s = _load(film) or {}
        has = {st["id"]: len(_stage_files(film, st)) for st in STAGES}
        out.append({"film": film, "cast": list((s.get("cast") or {}).keys()),
                    "place": (s.get("place") or {}).get("id"), "shots": [x.get("id") for x in s.get("shots", [])],
                    "has": has, "title": s.get("title") or film})
    return {"films": out, "stages": [{k: v for k, v in st.items() if k != "flags"} for st in STAGES],
            "running": status()}, 200


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
    stages = {st["id"]: _stage_files(film, st) for st in STAGES}
    # strips beside the takes, so the page can show a strip without decoding video
    strips = {os.path.basename(p)[:-len("_strip.jpg")]: _url(p)
              for p in glob.glob(os.path.join(out, "*_strip.jpg"))}
    measured = {}
    mp = os.path.join(out, "measured.json")
    if os.path.exists(mp):
        try:
            measured = json.load(open(mp))
        except Exception:
            measured = {}
    logs = sorted(glob.glob(os.path.join(out, "_app_*.log")), key=os.path.getmtime)
    return {"film": film, "stages": stages, "strips": strips, "measured": measured,
            "log": _tail(logs[-1]) if logs else "", "log_name": os.path.basename(logs[-1]) if logs else None,
            "running": status()}, 200


def status():
    running = _running()
    rc = _JOB["proc"].returncode if (_JOB["proc"] is not None and not running) else None
    return {"running": running, "film": _JOB["film"], "stage": _JOB["stage"], "started": _JOB["started"],
            "returncode": rc, "cmd": _JOB["cmd"],
            "log": _tail(_JOB["log"]) if _JOB["log"] else ""}


# ------------------------------------------------------------------------------ POST
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
    if s["film"] != film and FILM_RE.match(film):
        return {"error": "the script's film (%s) does not match %s" % (s["film"], film)}, 400
    if _running() and _JOB["film"] == s["film"]:
        return {"error": "a stage is running on %s - wait for it, or stop it" % s["film"]}, 409
    os.makedirs(SEQ_DIR, exist_ok=True)
    p = os.path.join(SEQ_DIR, s["film"] + ".json")
    json.dump(s, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return {"ok": True, "film": s["film"], "path": os.path.relpath(p, ROOT)}, 200


def new(data):
    film = str(data.get("film") or "").strip().lower()
    if not FILM_RE.match(film):
        return {"error": "name the film with a short slug: lowercase letters, digits, dashes"}, 400
    if _load(film) is not None:
        return {"error": "%s exists" % film}, 409
    s = json.loads(json.dumps(SKELETON))
    s["film"] = film
    src = data.get("from")
    if src and _load(src):
        s = _load(src)
        s["film"] = film
    os.makedirs(SEQ_DIR, exist_ok=True)
    json.dump(s, open(os.path.join(SEQ_DIR, film + ".json"), "w", encoding="utf-8"), indent=1,
              ensure_ascii=False)
    return {"ok": True, "film": film, "script": s}, 200


def _seeds(data):
    raw = data.get("seeds")
    if raw in (None, ""):
        return ["11", "202", "3003"], None
    if isinstance(raw, list):
        raw = " ".join(str(x) for x in raw)
    parts = re.split(r"[,\s]+", str(raw).strip())
    parts = [p for p in parts if p]
    if not parts or not all(SEED_RE.match(p) for p in parts) or len(parts) > 8:
        return None, "seeds: up to eight whole numbers, like 11 202 3003"
    return parts, None


def run(data):
    with _LOCK:
        if _running():
            return {"error": "a stage is already running (%s on %s) - one at a time" % (
                _JOB["stage"], _JOB["film"])}, 409
        film = str(data.get("film") or "")
        stage = str(data.get("stage") or "")
        st = next((x for x in STAGES if x["id"] == stage), None)
        if not FILM_RE.match(film) or _load(film) is None:
            return {"error": "no script %r" % film}, 404
        if not st:
            return {"error": "unknown stage %r" % stage}, 400
        s = _load(film)
        err = _check(s)
        if err:
            return {"error": "the script will not run: " + err}, 400
        out = _out(film)
        os.makedirs(out, exist_ok=True)
        if st["tool"] == "refsheet":
            refs = [os.path.join(out, "ref_%s.png" % who) for who in s["cast"]]
            plate = os.path.join(out, "ref_%s.png" % s["place"].get("id", "court"))
            missing = [os.path.basename(p) for p in refs + [plate] if not os.path.exists(p)]
            if missing:
                return {"error": "run the cast stage first - missing %s" % ", ".join(missing)}, 400
            cmd = [PYVENV, REFSHEET, "--out", os.path.join(out, "sheet_%s.png" % film)]
            for r in refs:
                cmd += ["--char", r]
            cmd += ["--place", plate]
        else:
            cmd = ["python3", FIGHT, "--sequence", film] + list(st["flags"])
            if stage == "h3":
                shot = str(data.get("shot") or "")
                if not re.match(r"^\d{3}$", shot):
                    return {"error": "the H3 stage needs a shot id (three digits)"}, 400
                cmd += [shot]
            if "seeds" in st.get("args", []):
                seeds, err = _seeds(data)
                if err:
                    return {"error": err}, 400
                cmd += ["--seeds"] + seeds
            if stage == "finish":
                picks = str(data.get("picks") or "").replace(" ", "")
                if not PICKS_RE.match(picks):
                    return {"error": "picks look like 010=202,020=11,030=h3:3003 - one per shot"}, 400
                cmd += ["--picks", picks]
                if data.get("master"):
                    cmd += ["--master"]
            if stage == "cast":
                only = str(data.get("only") or "").strip()
                if only:
                    if not FILM_RE.match(only):
                        return {"error": "only: a cast or place id"}, 400
                    cmd += ["--only", only, "--force"]
                    seed = str(data.get("seed") or "").strip()
                    if seed:
                        if not SEED_RE.match(seed):
                            return {"error": "seed: a whole number"}, 400
                        cmd += ["--seed", seed]
            if data.get("force") and stage != "cast":
                cmd += ["--force"]
        log = os.path.join(out, "_app_%s.log" % stage)
        lf = open(log, "w", encoding="utf-8")
        lf.write("$ %s\n" % " ".join(shlex.quote(c) for c in cmd))
        lf.flush()
        env = dict(os.environ, PYTHONUNBUFFERED="1", FIGHT_SEQUENCE=film)
        try:
            proc = subprocess.Popen(cmd, cwd=ROOT, stdout=lf, stderr=subprocess.STDOUT, env=env)
        except OSError as e:
            return {"error": "could not start: %s" % e}, 500
        _JOB.update({"proc": proc, "film": film, "stage": stage, "started": int(time.time()), "log": log,
                     "cmd": " ".join(cmd)})

        def _watch():
            proc.wait()
            lf.write("\n[exit %s]\n" % proc.returncode)
            lf.close()
        threading.Thread(target=_watch, daemon=True).start()
        return {"ok": True, "film": film, "stage": stage, "cmd": _JOB["cmd"]}, 200


def stop(data=None):
    if not _running():
        return {"ok": True, "note": "nothing was running"}, 200
    _JOB["proc"].terminate()
    for _ in range(20):
        if not _running():
            break
        time.sleep(0.25)
    if _running():
        _JOB["proc"].kill()
    return {"ok": True, "stopped": _JOB["stage"], "film": _JOB["film"]}, 200


# ------------------------------------------------------------------------------ dispatch
def get(path, query):
    """serve.py hands the path after /api/shots and the parsed query."""
    q = {k: (v[0] if isinstance(v, list) else v) for k, v in (query or {}).items()}
    rest = path.strip("/")
    if rest in ("", "list"):
        return listing()
    if rest == "script":
        return script(q.get("film"))
    if rest == "tree":
        return tree(q.get("film"))
    if rest == "status":
        return status(), 200
    return {"error": "unknown shots route"}, 404


def post(path, data):
    rest = path.strip("/")
    fn = {"save": save, "new": new, "run": run, "stop": stop}.get(rest)
    if not fn:
        return {"error": "unknown shots route"}, 404
    return fn(data or {})
