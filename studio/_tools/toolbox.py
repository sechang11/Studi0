"""Run the project's tools from a button instead of a terminal.

A CURATED ALLOWLIST, NEVER A GENERIC RUNNER, and that is a safety decision rather than a
stylistic one. There are 99 scripts in studio/_tools and a large minority have no argparse
at all: they run their entire job on ANY argument, including --help, and several write
files at import time. A page that shells whatever it is handed would eventually be handed
one of those. So every entry below was checked by reading its interface, and nothing runs
that is not in this table.

Each tool declares its arguments with a type, and the runner builds argv from that table -
the page cannot invent a flag, and neither can a crafted POST.
"""
import json, os, random, re, subprocess, sys, threading, time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)

JOBS = {}
_LOCK = threading.Lock()

PY = sys.executable


def _characters():
    d = os.path.join(STUDIO, "characters")
    return sorted(f[:-5] for f in os.listdir(d)
                  if f.endswith(".json") and not f.startswith("_")) if os.path.isdir(d) else []


def _films():
    d = os.path.join(ROOT, "films")
    return sorted(f for f in os.listdir(d) if f.endswith(".json")) if os.path.isdir(d) else []


def _stories():
    d = os.path.join(ROOT, "stories")
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


# name, arg spec. kind: choice | text | int | flag. Every one of these interfaces was read
# before it was listed.
TOOLBOX = [
    {"id": "turnaround", "group": "Cast", "script": "studio/_tools/turnaround.py",
     "title": "Turnaround",
     "blurb": "One picture of a person becomes many consistent views of the same person. "
              "This is the identity set: angles and expressions, one outfit, one light. "
              "Anything it varies that is not the person is something a LoRA would learn "
              "as the person.",
     "cost": "about 16 renders",
     "args": [{"n": "character", "kind": "choice", "src": "characters", "pos": True},
              {"n": "--views", "kind": "int", "default": 16}]},

    {"id": "suite_identity", "group": "Cast", "script": "studio/_tools/character_suite.py",
     "title": "Picture suite - identity",
     "blurb": "Turnaround, collected into the cast folder with a contact sheet.",
     "cost": "about 16 renders",
     "args": [{"n": "character", "kind": "choice", "src": "characters", "pos": True},
              {"n": "--identity", "kind": "flag", "always": True},
              {"n": "--views", "kind": "int", "default": 16}]},

    {"id": "suite_presentation", "group": "Cast",
     "script": "studio/_tools/character_suite.py",
     "title": "Picture suite - presentation",
     "blurb": "Wardrobe x style grid on top of the locked sheet. Built AFTER identity, "
              "because a grid made before identity is locked is people who merely "
              "resemble each other.",
     "cost": "roughly 5s per cell",
     "args": [{"n": "character", "kind": "choice", "src": "characters", "pos": True},
              {"n": "--presentation", "kind": "flag", "always": True},
              {"n": "--wear", "kind": "text", "default": "default,travelling,armour,ruined"},
              {"n": "--styles", "kind": "text", "default": "house,ink,oil"}]},

    {"id": "audition", "group": "Voice", "script": "studio/_tools/voice_audition.py",
     "title": "Voice audition",
     "blurb": "Speak one line in every castable voice and build a single file to judge "
              "them back to back.",
     "cost": "a few seconds per voice",
     "args": [{"n": "--line", "kind": "text", "default": ""}]},

    {"id": "roll_explain", "group": "Library", "script": "studio/_tools/roll.py",
     "title": "What the libraries can draw",
     "blurb": "Counts the drawable space from the cards on disk and names every exclusion "
              "with its reason. Renders nothing.",
     "cost": "instant",
     "args": [{"n": "--explain", "kind": "flag", "always": True}]},

    {"id": "rules", "group": "Library", "script": "studio/_tools/filmrules.py",
     "title": "Check a film against the rules",
     "blurb": "Runs craft/VIDEO_RULES.md against a film and fails on a violation.",
     "cost": "instant",
     "args": [{"n": "--check", "kind": "choice", "src": "films", "prefix": "films/"}]},

    {"id": "rules_list", "group": "Library", "script": "studio/_tools/filmrules.py",
     "title": "List the rules",
     "blurb": "Every rule, its status and how it is enforced.",
     "cost": "instant",
     "args": [{"n": "--list", "kind": "flag", "always": True}]},

    {"id": "story_plan", "group": "Story", "script": "studio/_tools/story_tool.py",
     "title": "What is stale",
     "blurb": "Which scenes have no take, which takes no longer match their inputs, and "
              "which are locked and would be skipped. Spends nothing.",
     "cost": "instant",
     "args": [{"n": "plan", "kind": "flag", "always": True, "pos": True},
              {"n": "story", "kind": "choice", "src": "stories", "pos": True}]},

    {"id": "story_export", "group": "Story", "script": "studio/_tools/story_tool.py",
     "title": "Export a story",
     "blurb": "Assemble the selected takes into a timestamped manifest of exactly which "
              "takes went in.",
     "cost": "instant",
     "args": [{"n": "export", "kind": "flag", "always": True, "pos": True},
              {"n": "story", "kind": "choice", "src": "stories", "pos": True}]},

    {"id": "docs", "group": "Maintenance", "script": "studio/_tools/docs.py",
     "title": "Reindex the documentation",
     "blurb": "Walks the repo and rebuilds the /docs index from the files themselves.",
     "cost": "instant",
     "args": [{"n": "--print", "kind": "flag", "always": True}]},

    {"id": "changelog", "group": "Maintenance", "script": "studio/_tools/changelog.py",
     "title": "Rebuild the changelog",
     "blurb": "Regenerates /changelog from the git log.",
     "cost": "instant", "args": []},
]

SRC = {"characters": _characters, "films": _films, "stories": _stories}


def catalogue():
    out = []
    for t in TOOLBOX:
        d = dict(t)
        d["args"] = []
        for a in t["args"]:
            a2 = dict(a)
            if a.get("kind") == "choice" and a.get("src"):
                a2["options"] = SRC[a["src"]]()
            d["args"].append(a2)
        out.append(d)
    groups = []
    for g in ("Cast", "Voice", "Story", "Library", "Maintenance"):
        items = [t for t in out if t["group"] == g]
        if items:
            groups.append({"group": g, "tools": items})
    return {"groups": groups}, 200


SAFE = re.compile(r"^[A-Za-z0-9 ,._/'-]{0,400}$")


def _argv(tool, vals):
    argv = [PY, os.path.join(ROOT, tool["script"])]
    for a in tool["args"]:
        n, kind = a["n"], a.get("kind")
        if kind == "flag":
            if a.get("always") or vals.get(n):
                argv.append(n if not a.get("pos") else n.lstrip("-"))
            continue
        v = vals.get(n, a.get("default"))
        if v in (None, ""):
            continue
        v = str(v)
        if not SAFE.match(v):
            raise ValueError("%s has characters that are not allowed" % n)
        if kind == "choice" and a.get("options") is None and a.get("src"):
            if v not in SRC[a["src"]]():
                raise ValueError("%s is not one of the available %s" % (v, a["src"]))
        if kind == "int":
            v = str(int(float(v)))
        if a.get("prefix"):
            v = a["prefix"] + v
        if a.get("pos"):
            argv.append(v)
        else:
            argv += [n, v]
    return argv


def _run(job, argv):
    try:
        r = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=3600)
        with _LOCK:
            JOBS[job]["out"] = (r.stdout or "")[-6000:]
            JOBS[job]["err"] = (r.stderr or "")[-2000:]
            JOBS[job]["code"] = r.returncode
    except subprocess.TimeoutExpired:
        with _LOCK:
            JOBS[job]["err"] = "timed out after an hour"
            JOBS[job]["code"] = -1
    except Exception as e:
        with _LOCK:
            JOBS[job]["err"] = str(e)[:400]
            JOBS[job]["code"] = -1
    with _LOCK:
        JOBS[job]["state"] = "done"
        JOBS[job]["seconds"] = round(time.time() - JOBS[job]["t0"], 1)


def run_tool(data):
    tid = str(data.get("id") or "")
    tool = next((t for t in TOOLBOX if t["id"] == tid), None)
    if not tool:
        return {"error": "unknown tool"}, 404
    try:
        argv = _argv(tool, data.get("values") or {})
    except ValueError as e:
        return {"error": str(e)}, 400
    job = "t%d" % (len(JOBS) + 1)
    with _LOCK:
        JOBS[job] = {"state": "running", "tool": tid, "t0": time.time(),
                     "cmd": " ".join(argv[1:]), "out": "", "err": "", "code": None}
    threading.Thread(target=_run, daemon=True, args=(job, argv)).start()
    return {"ok": True, "job": job, "cmd": " ".join(os.path.basename(a) if i == 0 else a
                                                    for i, a in enumerate(argv[1:]))}, 200


def job_status(job):
    with _LOCK:
        j = JOBS.get(job)
    return (j or {"error": "no such job"}), (200 if j else 404)


# ── randomisers ──────────────────────────────────────────────────────────────────────
# A blank field is a worse starting point than a wrong one: it invites nothing. These give
# something to react to, which is how most authoring actually starts.

ON = ["ba", "ka", "mar", "sel", "vor", "thal", "eli", "dra", "kes", "bran", "ith", "cor",
      "nym", "hal", "ver", "sun", "gar", "lyr", "oskr", "ren", "tam", "vess", "wyn", "zad"]
OFF = ["a", "en", "is", "or", "eth", "ia", "un", "ek", "ra", "il", "ov", "ash", "wen",
       "dar", "ick", "os", "ine", "ul"]


def random_name(rng=None):
    rng = rng or random
    n = rng.choice(ON).capitalize() + rng.choice(OFF)
    if rng.random() < 0.35:
        n += rng.choice(["", "", " " + rng.choice(ON).capitalize() + rng.choice(OFF)])
    return n.strip()


def randomize(data):
    """A name, and a style drawn from the measured card library rather than invented."""
    what = data.get("what") or "all"
    out = {}
    if what in ("all", "name"):
        out["name"] = random_name()
    if what in ("all", "style"):
        sys.path.insert(0, TOOLS)
        try:
            import roll as R
            libs = R.load_libs()
            drawable = R.drawable_styles(libs)
            if drawable:
                sid = random.choice(drawable)
                c = libs["styles"][sid]
                # Prefer the card's own prose; it is what was measured to work.
                txt = (c.get("prose") or c.get("prompt") or c.get("text")
                       or c.get("qwen") or c.get("tags") or sid)
                out["style"] = str(txt)[:400]
                out["style_id"] = sid
        except Exception as e:
            out["style_error"] = str(e)[:160]
    return out, 200


def styles():
    """The drawable style cards, for a picker."""
    sys.path.insert(0, TOOLS)
    import roll as R
    libs = R.load_libs()
    out = []
    for sid in R.drawable_styles(libs):
        c = libs["styles"][sid]
        txt = (c.get("prose") or c.get("prompt") or c.get("text") or c.get("qwen")
               or c.get("tags") or "")
        out.append({"id": sid, "text": str(txt)[:400]})
    return {"styles": out}, 200
