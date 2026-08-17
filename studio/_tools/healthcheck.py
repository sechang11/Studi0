#!/usr/bin/env python3
"""studio/_tools/healthcheck.py - is everything actually working?

    python3 studio/_tools/healthcheck.py              # everything, human readable
    python3 studio/_tools/healthcheck.py --json       # machine readable
    python3 studio/_tools/healthcheck.py routes tools # just those sections
    python3 studio/_tools/healthcheck.py --host 127.0.0.1:8777

SECTIONS: routes  tools  cards  workflows  movies  spine  defects

WHY THIS EXISTS. Nothing in this project answered the question "is the app working".
check_refs.py checks card cross-references, lora_scan.py checks the LoRA library, and
between them is every route, every API payload, every tool, every workflow graph and
every compiled film - unchecked. A 200 that carries a traceback in its body, a tool that
crashes on import, a workflow whose node 7 was renumbered out from under the code that
writes node 7: all of those were invisible.

THE ONE RULE THIS TOOL FOLLOWS, and it is written from an injury:

    NEVER EXECUTE A TOOL TO TEST IT.

Seventeen of the sixty tools in studio/_tools/ ignore --help and run their whole job
instead. Auditing this directory by running `--help` on each file overwrote ten style
cards with stale verdicts, rewrote two workflow JSONs, regenerated fifteen sample images,
created a directory literally named `--help` holding sixty-six style cards, and put real
jobs on the GPU. That happened. So tools are inspected by PARSING them - ast.parse plus
a scan for the specific shapes that make a tool dangerous to invoke - and this tool
imports nothing from _tools and runs nothing in it.

The two exceptions are check_refs.py and lora_scan.py, which are read-only by
construction and are the project's existing library checks, so they are shelled out to
and their exit status is reported. Nothing else in _tools is executed, ever.
"""
import argparse, ast, json, os, re, subprocess, sys, time
import urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))          # studio/_tools
STUDIO = os.path.dirname(HERE)                             # studio
ROOT = os.path.dirname(STUDIO)                             # repo root
HOST = os.environ.get("STUDIO_HOST", "127.0.0.1:8777")

SECTIONS = ["routes", "tools", "cards", "workflows", "movies", "spine", "defects"]

# ── every page and every API the server routes, read off serve.py's do_GET/do_POST ──
PAGES = ["/", "/wizard", "/styles", "/places", "/cast", "/character", "/character/TERRA",
         "/loras", "/video", "/gallery", "/make", "/tags", "/verify", "/changelog",
         # Landed after this list was first written. /guide/<slug> is
         # listed as well as /guide because they are different branches
         # in do_GET and only the index was ever reachable by accident.
         "/capabilities", "/guide", "/guide/getting-started"]
APIS = ["/api/cast", "/api/styles", "/api/places", "/api/loras", "/api/tags", "/api/video",
        "/api/effects", "/api/gallery", "/api/templates", "/api/library", "/api/cards",
        "/api/variables", "/api/movies", "/api/domains", "/api/changelog",
        "/api/verify/queue", "/api/character", "/api/character/TERRA",
        "/api/render/status?name=my-scene",
        "/api/capabilities", "/api/guides", "/api/guide/mental-model"]
POSTS = ["/api/save", "/api/render", "/api/make", "/api/workflow", "/api/verify",
         "/api/tag/reroll", "/api/compose"]

# A page that answers 200 with almost nothing in it is broken in the way that matters.
MIN_PAGE_BYTES = 2000
# Words that mean the body is an error even though the status line said otherwise.
BODY_ROT = ("Traceback (most recent call last)", "<title>Error", "Internal Server Error",
            "NameError", "AttributeError:", "KeyError:", "TypeError:")

R = []          # findings: (severity, section, message)
SEV = {"BROKEN": 0, "WRONG": 1, "GAP": 2, "NOTE": 3}


def say(sev, section, msg):
    R.append((sev, section, msg))


# ────────────────────────────────────────────────────────────────── 1. routes
def http(path, method="GET", body=None, timeout=45):
    url = f"http://{HOST}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read(), time.time() - t0
    except Exception as e:                                          # noqa: BLE001
        return 0, repr(e).encode(), time.time() - t0


def check_routes():
    out = {}
    for p in PAGES:
        code, body, ms = http(p)
        rec = {"status": code, "bytes": len(body), "secs": round(ms, 2)}
        txt = body[:200000].decode("utf-8", "replace")
        if code != 200:
            say("BROKEN", "routes", f"{p} answered {code}")
        elif len(body) < MIN_PAGE_BYTES:
            say("BROKEN", "routes", f"{p} answered 200 with only {len(body)} bytes")
        for w in BODY_ROT:
            if w in txt:
                say("BROKEN", "routes", f"{p} answered 200 but its body contains {w!r}")
                rec["rot"] = w
                break
        # HEAD must agree with GET. It did not for the whole life of this app: the
        # default do_HEAD resolved against the process cwd instead of the route table,
        # so every route 404'd to HEAD while GET returned 200.
        hcode, _, _ = http(p, method="HEAD")
        rec["head"] = hcode
        if hcode != code:
            say("WRONG", "routes", f"{p}: GET {code} but HEAD {hcode}")
        out[p] = rec

    for p in APIS:
        code, body, ms = http(p)
        rec = {"status": code, "bytes": len(body), "secs": round(ms, 2)}
        if code != 200:
            say("BROKEN" if code >= 500 else "GAP", "routes",
                f"{p} answered {code}: {body[:180].decode('utf-8','replace')}")
            out[p] = rec
            continue
        try:
            payload = json.loads(body)
        except Exception as e:                                      # noqa: BLE001
            say("BROKEN", "routes", f"{p} answered 200 with unparseable JSON: {e}")
            out[p] = rec
            continue
        rec["kind"] = type(payload).__name__
        rec["n"] = len(payload)
        # An error object served with a 200 is the exact failure this project keeps
        # finding: the page renders "nothing here yet" and the cause is a broken import.
        if isinstance(payload, dict) and payload.get("error"):
            say("BROKEN", "routes", f"{p} answered 200 carrying an error: {payload['error']}")
        if isinstance(payload, dict) and payload.get("trace"):
            say("BROKEN", "routes", f"{p} answered 200 carrying a traceback")
        if not payload:
            say("GAP", "routes", f"{p} answered 200 with an empty payload")
        out[p] = rec

    # POST endpoints: prove they are ROUTED without asking them to do anything. Four of
    # these seven start a render, write a verdict or reroll a card, so they are probed
    # with an EMPTY body and judged on the refusal.
    #
    # A 4xx that names the missing argument ("name required", "unknown domain: ") is the
    # handler answering, which is exactly the proof wanted - the route is live and it
    # validates before it acts. The only real failure here is the router's own
    # `{"error": "not found"}`, which means the path fell off the tuple in do_POST, or a
    # 5xx, which means the handler fell over before it validated anything.
    for p in POSTS:
        code, body, _ = http(p, method="POST", body={})
        b = body[:160].decode("utf-8", "replace")
        out[p] = {"status": code, "reply": b}
        if code >= 500:
            say("BROKEN", "routes", f"POST {p} answered {code} to an empty body: {b}")
        elif code == 404 and '"error": "not found"' in b:
            say("BROKEN", "routes", f"POST {p} is not routed - do_POST does not list it")
        elif code == 0:
            say("BROKEN", "routes", f"POST {p} did not answer at all: {b}")
        elif code not in (200, 400, 404, 422):
            say("WRONG", "routes", f"POST {p} answered {code} to an empty body: {b}")

    # EVERY PICTURE THE APP PROMISES, fetched. A card that names an image the server
    # will not serve renders as an empty box, and an empty box on a page that says
    # "rendered and looked at" is the worst failure mode this project has - it looks
    # like an absence of work rather than a broken path. There is no way to know from
    # the JSON alone; the URL has to be asked for.
    media = re.compile(r'/samples/[A-Za-z0-9_./+-]+\.(?:webp|png|jpg|jpeg|mp4|mp3|wav)')
    for api in ("/api/styles", "/api/places", "/api/cast", "/api/loras",
                "/api/templates", "/api/character/TERRA", "/api/tags"):
        code, body, _ = http(api)
        if code != 200:
            continue
        paths = sorted(set(media.findall(body.decode("utf-8", "replace"))))
        bad = []
        for mp in paths:
            c, _, _ = http(mp, method="HEAD", timeout=25)
            if c != 200:
                bad.append((c, mp))
        out.setdefault("_media", {})[api] = {"n": len(paths), "bad": len(bad)}
        if bad:
            say("BROKEN", "routes",
                f"{api} advertises {len(bad)} of {len(paths)} media file(s) the server "
                f"will not serve - those render as empty boxes: "
                + "; ".join(f"{c} {p}" for c, p in bad[:5]))
    return out


# ────────────────────────────────────────────────────────────────── 2. tools
# The shapes that decide whether a tool can be safely invoked, all read statically.
WRITE_CALLS = {"write_text", "savefig", "imwrite", "makedirs", "copyfile", "rename",
               "unlink", "remove", "rmtree"}
GPU_HINTS = ("run(", "queue_prompt", "comfy.run", "post_prompt")


class ToolFacts(ast.NodeVisitor):
    def __init__(self):
        self.argparse = False
        self.argv = False
        self.main_guard = False
        self.top_level_work = False
        self.opens_write = False
        self.gpu = False
        self.hardcoded_default = []     # (arg, default) that names one character
        self.abs_paths = []

    def visit_Call(self, n):
        f = n.func
        name = getattr(f, "attr", None) or getattr(f, "id", None)
        if name == "ArgumentParser":
            self.argparse = True
        if name in WRITE_CALLS:
            self.opens_write = True
        if name == "open":
            for a in list(n.args[1:]) + [k.value for k in n.keywords if k.arg == "mode"]:
                if isinstance(a, ast.Constant) and isinstance(a.value, str) \
                        and any(c in a.value for c in "wax"):
                    self.opens_write = True
        self.generic_visit(n)

    def visit_Attribute(self, n):
        if n.attr == "argv":
            self.argv = True
        self.generic_visit(n)


def looks_like_a_person(s):
    return bool(re.fullmatch(r"[A-Z][A-Z0-9_]{2,15}", s or ""))


def third_party_imports(tree):
    """Top-level import statements only - the ones that decide whether the file can be
    executed at all. An import inside a function fails later and only on that path, which
    is a different and less severe fact, so they are counted separately."""
    top, deep = set(), set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            top |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            top.add(node.module.split(".")[0])
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            deep |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            deep.add(node.module.split(".")[0])
    return top, deep - top


def resolvable(mod, extra_paths):
    import importlib.util
    saved = list(sys.path)
    sys.path[:0] = extra_paths
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:                                               # noqa: BLE001
        return False
    finally:
        sys.path[:] = saved


def check_tools():
    out = {}
    # Tools add these to sys.path themselves before importing their siblings, so a
    # dependency check that does not do the same manufactures false failures.
    sibling = [HERE, os.path.join(ROOT, "scripts"), STUDIO, ROOT]
    missing = {}
    files = sorted(f for f in os.listdir(HERE)
                   if f.endswith(".py") and not f.startswith("__"))
    for fn in files:
        p = os.path.join(HERE, fn)
        rec = {"file": fn}
        try:
            src = open(p, encoding="utf-8").read()
        except Exception as e:                                      # noqa: BLE001
            say("BROKEN", "tools", f"{fn} cannot be read: {e}")
            out[fn] = {"file": fn, "error": str(e)}
            continue
        try:
            tree = ast.parse(src, fn)
        except SyntaxError as e:
            say("BROKEN", "tools", f"{fn} does not parse: line {e.lineno}: {e.msg}")
            out[fn] = {"file": fn, "syntax_error": f"{e.lineno}: {e.msg}"}
            continue

        fx = ToolFacts()
        fx.visit(tree)
        # Work that runs at import time, outside any def/class and outside a
        # `if __name__ == "__main__"` guard. This is what makes `--help` run a render.
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                 ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign,
                                 ast.Expr, ast.Try)):
                if isinstance(node, ast.Expr) and not isinstance(node.value, ast.Constant):
                    fx.top_level_work = True
                continue
            if isinstance(node, ast.If):
                t = node.test
                if isinstance(t, ast.Compare) and getattr(t.left, "id", "") == "__name__":
                    fx.main_guard = True
                    continue
            fx.top_level_work = True

        rec["argparse"] = fx.argparse
        rec["reads_argv"] = fx.argv
        rec["main_guard"] = fx.main_guard
        rec["writes_files"] = fx.opens_write
        rec["work_at_import"] = fx.top_level_work

        # THE DANGEROUS SHAPE: no argparse, and the body runs on import. Such a tool
        # treats every argument - including --help - as either an input or as nothing,
        # and does its whole job the moment you name it on a command line.
        if not fx.argparse and (fx.top_level_work or not fx.main_guard) and fx.opens_write:
            rec["unsafe_to_probe"] = True
            say("WRONG", "tools",
                f"{fn} has no argparse and writes files at module level - running it "
                f"with any argument, INCLUDING --help, does its whole job")
        elif not fx.argparse:
            rec["unsafe_to_probe"] = True
            say("NOTE", "tools", f"{fn} has no argparse - it cannot be probed safely")

        # CAN IT EVEN IMPORT? Resolved with find_spec, never by importing the tool -
        # importing it would run it. Split by where the import sits, because the two
        # facts are different: a top-level import that does not resolve means the file
        # cannot be started at all, while one inside a function means it dies partway
        # through, on one code path, after possibly doing work.
        top, deep = third_party_imports(tree)
        bad_top = sorted(m for m in top if not resolvable(m, sibling))
        bad_deep = sorted(m for m in deep if not resolvable(m, sibling))
        if bad_top:
            rec["cannot_import"] = bad_top
            say("BROKEN", "tools",
                f"{fn} cannot start under this interpreter - missing at module level: "
                + ", ".join(bad_top))
            for m in bad_top:
                missing.setdefault(m, []).append(fn)
        if bad_deep:
            rec["dies_partway"] = bad_deep
            for m in bad_deep:
                missing.setdefault(m, []).append(fn)

        # Hardcoded to one character or one path.
        hard = []
        if fn == os.path.basename(__file__):
            pass                       # this file's own detector literals are not paths
        else:
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    v = node.value
                    if v.startswith(("/home/", "/Users/", "C:\\")):
                        hard.append(("absolute path", v))
        names = [] if fn == os.path.basename(__file__) else re.findall(r"\bTERRA\b", src)
        if names:
            # A default of TERRA on an argparse flag is fine; TERRA welded into a
            # prompt, a path or a card lookup is not.
            flagged = re.findall(r'default\s*=\s*"(TERRA)"', src)
            rec["terra_mentions"] = len(names)
            rec["terra_is_only_a_default"] = bool(flagged) and len(names) <= len(flagged) + 2
        if hard:
            rec["hardcoded"] = hard[:4]
            say("GAP", "tools", f"{fn} contains {len(hard)} absolute path literal(s)")
        out[fn] = rec

    # Which tools are welded to TERRA and cannot be pointed at anyone else? Decided by
    # whether the character is reachable as an argument at all.
    welded = [fn for fn, r in out.items()
              if r.get("terra_mentions", 0) >= 3 and not r.get("terra_is_only_a_default")
              and not r.get("argparse")]
    partly = [fn for fn, r in out.items()
              if r.get("terra_mentions", 0) >= 3 and r.get("argparse")
              and not r.get("terra_is_only_a_default")]
    if welded:
        say("GAP", "tools", "welded to TERRA with no way to pass another character: "
                            + ", ".join(sorted(welded)))
    if partly:
        say("NOTE", "tools", "takes a character argument but still names TERRA in its "
                             "body: " + ", ".join(sorted(partly)))

    # One line per missing dependency rather than one per tool - the fix is per module.
    out["_missing_modules"] = {m: sorted(set(v)) for m, v in missing.items()}
    for m, fs in sorted(missing.items()):
        say("GAP", "tools",
            f"module {m!r} is not installed for {os.path.basename(sys.executable)} and "
            f"{len(set(fs))} tool(s) want it: " + ", ".join(sorted(set(fs))[:8]))

    # The two read-only library checks are the exception: run them and report.
    for t, args in (("check_refs.py", []), ("lora_scan.py", [])):
        fp = os.path.join(HERE, t)
        if not os.path.exists(fp):
            say("BROKEN", "tools", f"{t} is missing")
            continue
        r = subprocess.run([sys.executable, fp] + args, capture_output=True, text=True,
                           cwd=ROOT, timeout=900)
        tail = (r.stdout + r.stderr).strip().splitlines()
        out[t] = {"file": t, "exit": r.returncode, "last": tail[-1] if tail else ""}
        if r.returncode != 0:
            say("BROKEN", "tools", f"{t} exited {r.returncode}: {tail[-1] if tail else ''}")
    return out


# ────────────────────────────────────────────────────── 3. card libraries
# id is required everywhere. The rest is what the app actually reads off each card,
# so a missing one is a hole in a page, not a style preference.
REQUIRED = {
    "styles":     ["id", "name", "engine", "status"],
    "places":     ["id", "name", "family", "status"],
    "characters": ["id", "name", "tags"],
    "motions":    ["id", "status"],
    "looks":      ["id", "grade"],
    "emotions":   ["id"],
    "cameras":    ["id", "status"],
    "loras":      ["id", "base_model", "kind", "status"],
    "voices":     ["id"],
    "templates":  ["id", "name"],
    "transitions": ["id"],
    "lighting":   ["id"],
    "weather":    ["id"],
    "shots":      ["id"],
    "cues":       ["id"],
    "tags":       ["id"],
    # A capability card is keyed by the VARIABLE it demonstrates, not by an id, and it
    # is only worth anything if it carries the panels that were actually rendered.
    "cards":      ["variable", "claim", "panels"],
}
# Directories whose filename stem is not the card's id by design.
NO_STEM_ID = {"cards"}


def check_cards():
    out = {}
    for d in sorted(os.listdir(STUDIO)):
        dp = os.path.join(STUDIO, d)
        if not os.path.isdir(dp) or d.startswith(("_", ".")) or d in ("samples", "gallery",
                                                                     "movies", "prompts"):
            continue
        files = [f for f in sorted(os.listdir(dp)) if f.endswith(".json")]
        if not files:
            continue
        rec = {"n": len(files), "unparseable": [], "missing_fields": [],
               "id_mismatch": [], "no_status": 0}
        req = REQUIRED.get(d, ["id"])
        for f in files:
            fp = os.path.join(dp, f)
            try:
                card = json.load(open(fp, encoding="utf-8"))
            except Exception as e:                                  # noqa: BLE001
                rec["unparseable"].append(f"{f}: {e}")
                say("BROKEN", "cards", f"studio/{d}/{f} does not parse: {e}")
                continue
            if not isinstance(card, dict):
                continue
            if f.startswith("_"):
                continue
            # A card may DECLARE why a required field is empty, and a declaration
            # satisfies the requirement. 72 craft cards have no `panels` because they
            # carry `not_visual` explaining that one frame cannot show the variable -
            # that is the library being complete, not incomplete, and counting it as a
            # gap is how a checker teaches you to ignore it.
            EXCUSED = {"panels": "not_visual"}
            miss = [k for k in req
                    if not card.get(k) and not card.get(EXCUSED.get(k, "\0"))]
            if miss:
                rec["missing_fields"].append(f"{f}: {','.join(miss)}")
            stem = os.path.splitext(f)[0]
            if d not in NO_STEM_ID and card.get("id") and card["id"] != stem:
                rec["id_mismatch"].append(f"{f}: id={card['id']}")
            if not card.get("status"):
                rec["no_status"] += 1
        if rec["missing_fields"]:
            say("GAP", "cards", f"studio/{d}: {len(rec['missing_fields'])} card(s) missing "
                                f"a required field ({req}): "
                                + "; ".join(rec["missing_fields"][:6]))
        if rec["id_mismatch"]:
            say("WRONG", "cards", f"studio/{d}: {len(rec['id_mismatch'])} card(s) whose id "
                                  f"does not match the filename - the resolver looks up by "
                                  f"filename stem: " + "; ".join(rec["id_mismatch"][:6]))
        out[d] = rec

    # The library's own claim vs what the loader serves.
    for d, api in (("styles", "/api/styles"), ("places", "/api/places"),
                   ("loras", "/api/loras"), ("templates", "/api/templates")):
        code, body, _ = http(api)
        if code != 200:
            continue
        try:
            payload = json.loads(body)
        except Exception:                                           # noqa: BLE001
            continue
        served = payload.get(d) if isinstance(payload, dict) else payload
        if not isinstance(served, list):
            continue
        disk = out.get(d, {}).get("n", 0)
        # A leading-underscore file is a control card and is meant to be withheld.
        control = len([f for f in os.listdir(os.path.join(STUDIO, d))
                       if f.startswith("_") and f.endswith(".json")]) if os.path.isdir(
            os.path.join(STUDIO, d)) else 0
        if len(served) + control != disk and disk:
            say("WRONG", "cards", f"studio/{d} holds {disk} json files ({control} control) "
                                  f"but {api} serves {len(served)}")
    return out


# ────────────────────────────────────────────────── 4. workflows vs the code
DRIVERS = ["scripts/short.py", "scripts/film.py", "scripts/epic.py", "scripts/pipeline.py",
           "scripts/cartoon.py", "scripts/make_audio_library.py"]
_GRAPHS = {}
_BINDINGS = {}


def load_graphs():
    """Every workflow JSON, parsed once. Cached, because two sections need them."""
    if _GRAPHS:
        return _GRAPHS
    wfdir = os.path.join(ROOT, "workflows")
    for f in sorted(os.listdir(wfdir)):
        if not f.endswith(".json"):
            continue
        try:
            _GRAPHS[f] = json.load(open(os.path.join(wfdir, f), encoding="utf-8"))
        except Exception as e:                                      # noqa: BLE001
            say("BROKEN", "workflows", f"workflows/{f} does not parse: {e}")
    return _GRAPHS


def negative_node(g):
    """The node id feeding a sampler's `negative` input.

    Asked of the graph, never assumed. Node numbering is not a convention in this repo -
    the negative is node 6 in one workflow and node 11 in three others - so any check
    that hardcodes a number is testing its own memory rather than the file."""
    for node in g.values():
        if not isinstance(node, dict):
            continue
        v = (node.get("inputs") or {}).get("negative")
        if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str):
            return v[0]
    return None


def driver_bindings(drv):
    """[(workflow, "node.inputs.field", lineno)] for one driver script.

    SCOPED PER FUNCTION and BOUND TO THE NEAREST PRECEDING load_wf, and both halves of
    that were learned by getting it wrong. Carrying "the last workflow seen" across a
    `def` reports short.py's style_lora_slot() - which writes node 7 of the QWEN graphs -
    as writing node 7 of the ANIME graph, where node 7 is an EmptyLatentImage. Checking
    every write in a function against every graph the function loads invents six more,
    because one function here loads workflow 14 in one branch and 13 in the next and
    writes different node ids to each.
    """
    if drv in _BINDINGS:
        return _BINDINGS[drv]
    graphs = load_graphs()
    dp = os.path.join(ROOT, drv)
    out = []
    if not os.path.exists(dp):
        _BINDINGS[drv] = out
        return out
    try:
        tree = ast.parse(open(dp, encoding="utf-8").read(), drv)
    except SyntaxError as e:
        say("BROKEN", "workflows", f"{drv} does not parse: {e}")
        _BINDINGS[drv] = out
        return out

    loads, calls, seq = {}, {}, {}
    for fdef in [n for n in ast.walk(tree)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        events = []
        for n in ast.walk(fdef):
            if not isinstance(n, ast.Call):
                continue
            fname = getattr(n.func, "id", None) or getattr(n.func, "attr", None)
            if fname == "load_wf" and n.args:
                a = n.args[0]
                names = ([a.value] if isinstance(a, ast.Constant) else
                         [c.value for c in ast.walk(a) if isinstance(c, ast.Constant)
                          and str(c.value).endswith(".json")])
                loads.setdefault(fdef.name, set()).update(names)
                events.append((n.lineno, "load", names))
            elif fname == "set_path" and len(n.args) >= 2:
                a = n.args[1]
                v = a.value if isinstance(a, ast.Constant) and isinstance(
                    a.value, str) else None
                events.append((n.lineno, "write", v))
            elif fname in ("set_negative", "_set_neg"):
                # engine.set_negative writes whichever node the graph routes as
                # `negative`; the concrete path is resolved per target graph below.
                events.append((n.lineno, "write", "<negative>"))
            elif fname:
                calls.setdefault(fdef.name, set()).add(fname)
        seq[fdef.name] = sorted(events)

    def graphs_for(fn, seen=None):
        """A helper with no load_wf of its own takes its graph from its CALLERS."""
        seen = seen or set()
        if fn in seen:
            return set()
        seen.add(fn)
        if loads.get(fn):
            return set(loads[fn])
        got = set()
        for caller, callees in calls.items():
            if fn in callees:
                got |= graphs_for(caller, seen)
        return got

    for fn in sorted(seq):
        inherited = None if loads.get(fn) else graphs_for(fn)
        active = None
        for lineno, kind, val in seq[fn]:
            if kind == "load":
                active = set(val)
                for wf in sorted(active):
                    if wf not in graphs:
                        say("BROKEN", "workflows",
                            f"{drv}:{fn} loads workflows/{wf} which does not exist")
                continue
            targets = active if active is not None else (inherited or set())
            if val == "<negative>":
                # one binding per target graph, each at THAT graph's negative node
                for g in sorted(targets):
                    nid = negative_node(graphs.get(g) or {})
                    if not nid:
                        continue
                    ins = (graphs.get(g) or {}).get(nid, {}).get("inputs") or {}
                    key = "text" if "text" in ins else "prompt" if "prompt" in ins \
                        else None
                    if key is None:
                        # mirrors engine.set_negative: a negative node with no text
                        # input (ACE-Step's tag encoder as its own negative) has no
                        # negative prompt to reach, and the writer writes nothing.
                        continue
                    out.append(([g], f"{nid}.inputs.{key}", lineno, fn))
                continue
            out.append((sorted(targets), val, lineno, fn))
    _BINDINGS[drv] = [(t, p, l, f) for t, p, l, f in out]
    return _BINDINGS[drv]


def check_workflows():
    out = {"files": {}, "drivers": {}}
    graphs = load_graphs()
    for f, g in graphs.items():
        rec = {"parses": True, "nodes": len(g), "dangling": []}
        # Every input that names another node must name a node that exists.
        for nid, node in g.items():
            if not isinstance(node, dict):
                continue
            for k, v in (node.get("inputs") or {}).items():
                if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str):
                    if v[0] not in g:
                        rec["dangling"].append(f"{nid}.{k} -> node {v[0]}")
        if rec["dangling"]:
            say("BROKEN", "workflows",
                f"workflows/{f} has {len(rec['dangling'])} input(s) wired to a node that "
                f"does not exist: " + "; ".join(rec["dangling"][:4]))
        out["files"][f] = rec

    # Now the half nobody checks: the node ids the CODE writes must still exist in the
    # graph it writes them into. Renumbering a workflow by hand is silent otherwise -
    # set_path creates the key and ComfyUI ignores an orphan node.
    #
    for drv in DRIVERS:
        problems, dynamic, seen_graphs = [], 0, set()
        for targets, path, lineno, fn in driver_bindings(drv):
            seen_graphs |= set(targets)
            if path is None:
                dynamic += 1
                continue
            nid, field = path.split(".")[0], path.split(".")[-1]
            # A write is only a defect if it fits NO graph the function can be holding.
            # `load_wf(a if cond else b)` makes two candidates and the writes that follow
            # are guarded by the same condition, so a write that fits one of them is
            # correct code. Requiring it to fail everywhere is what stops this check
            # crying wolf - and a check that cries wolf on a healthy repo is worse than
            # no check, because the next person stops reading it.
            fits, fails = False, []
            for wf in targets:
                g = graphs.get(wf)
                if g is None:
                    continue
                if nid not in g:
                    fails.append(f"workflows/{wf} has no node {nid}")
                elif path.split(".")[1:2] == ["inputs"] and field not in (
                        g[nid].get("inputs") or {}):
                    fails.append(f"node {nid} of workflows/{wf} is a "
                                 f"{g[nid].get('class_type')} with no input {field!r}")
                else:
                    fits = True
            if fails and not fits:
                problems.append(f"{fn} (line {lineno}) writes {path!r} and "
                                + "; ".join(fails))
        if not seen_graphs and not problems and not dynamic:
            continue
        out["drivers"][drv] = {"problems": problems, "dynamic_writes": dynamic,
                               "graphs": sorted(seen_graphs)}
        for p in problems:
            say("BROKEN", "workflows", f"{drv} -> {p}")
        if dynamic:
            say("NOTE", "workflows",
                f"{drv} writes {dynamic} node path(s) built at runtime - not checkable here")

    # A workflow nothing drives is not a defect, but it is worth knowing which of the
    # 41 graphs in this repo are reachable from the code and which are hand-run only.
    driven = {w for d in DRIVERS for t, _, _, _ in driver_bindings(d) for w in t}
    out["undriven"] = sorted(set(graphs) - driven)
    return out


# ────────────────────────────────────────────────────────────── 5. movies
def check_movies():
    out = {}
    mdir = os.path.join(STUDIO, "movies")
    for f in sorted(os.listdir(mdir)):
        if not f.endswith(".movie"):
            continue
        fp = os.path.join(mdir, f)
        r = subprocess.run([sys.executable, os.path.join(STUDIO, "compile.py"), fp],
                           capture_output=True, text=True, cwd=ROOT, timeout=300)
        text = (r.stdout or "") + (r.stderr or "")
        warns = [l.strip(" !") for l in text.splitlines() if l.strip().startswith("!")]
        # Three grades of warning, and they are not equally serious.
        #   fyi:  the compiler explaining a decision it made correctly
        #   hold: the beat will not move - the single most common real defect
        #   real: something the author asked for that will not happen
        fyi = [w for w in warns if w.startswith("fyi:")]
        hold = [w for w in warns if "nothing moves in this shot" in w]
        real = [w for w in warns if w not in fyi and w not in hold]
        rec = {"exit": r.returncode, "warnings": len(warns),
               "fyi": len(fyi), "hold": len(hold), "real": len(real),
               "real_warnings": real[:20]}
        m = re.search(r"(\d+) chapters, (\d+) scenes, (\d+) beats", text)
        if m:
            rec["beats"] = int(m.group(3))
        m = re.search(r"motion:\s*(.*)", text)
        if m:
            rec["motion"] = m.group(1).strip()
            h = re.search(r"(\d+) holding still", m.group(1))
            if h:
                rec["holding"] = int(h.group(1))
        if r.returncode != 0:
            say("BROKEN", "movies", f"{f} does not compile (exit {r.returncode}): "
                                    + text.strip()[-300:])
        # Only the REAL holds count - the compiler already grades them. A `fyi:` hold is
        # correct (an ffmpeg camera does the moving; asking LTX to hold is right); a
        # "nothing moves in this shot" hold is a beat with no mover named. The summary
        # line's "holding still" total mixes both and was what this used to report.
        rec["real_holds"] = len(hold)
        if rec.get("beats") and hold:
            frac = len(hold) / rec["beats"]
            if frac >= 0.5:
                say("WRONG", "movies",
                    f"{f}: {len(hold)} of {rec['beats']} beats name no mover and resolve "
                    f"to a hold - every frame of those beats is the keyframe")
            elif len(hold) >= 2:
                say("NOTE", "movies",
                    f"{f}: {len(hold)} beat(s) name no mover and hold - name one with "
                    f"@motion or an action")
        for w in real:
            say("GAP", "movies", f"{f}: {w[:200]}")
        out[f] = rec
    return out


# ───────────────────────────────────────────── 6. the known open defects
def check_spine():
    """Import every script that renders a film.

    This section exists because short.py was unimportable for a whole session and all six
    other sections passed - none of them import a film script, so the failure only
    surfaced when a render was attempted. --help runs the import block and argparse and
    exits; it costs about a second each and never reaches the GPU.
    """
    import subprocess
    rec = {"checked": 0, "broken": []}
    for rel in ("scripts/short.py", "scripts/epic.py", "scripts/cartoon.py",
                "studio/compile.py"):
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        rec["checked"] += 1
        try:
            r = subprocess.run([sys.executable, p, "--help"], capture_output=True,
                               text=True, cwd=ROOT, timeout=180)
        except Exception as e:                                      # noqa: BLE001
            say("BROKEN", "spine", f"{rel} could not be run at all: {e}")
            rec["broken"].append(rel)
            continue
        if r.returncode != 0:
            tail = [l for l in (r.stderr or "").strip().splitlines() if l.strip()]
            why = tail[-1] if tail else f"exit {r.returncode}"
            say("BROKEN", "spine", f"{rel} cannot be imported: {why[:170]}")
            rec["broken"].append(rel)
    if not rec["broken"]:
        say("NOTE", "spine", f"{rec['checked']} render scripts import cleanly")
    return rec


def check_defects():
    """Each of these was reported before. Verify it is STILL real, by measurement."""
    out = {}

    # (a) three camera moves that render nothing.
    short = os.path.join(ROOT, "scripts", "short.py")
    src = open(short, encoding="utf-8").read() if os.path.exists(short) else ""
    dead = []
    # A camera is alive if short.py can RENDER it: either fx_chain has a branch, or it
    # is a make_cut post step (FX_CAMERAS_DEPTH - the depth cameras, task 22, which
    # cannot be a flat filter and never will be). Anything in FX_CAMERAS_UNBUILT is dead
    # by short.py's own declaration.
    import re as _re
    def _set(name):
        m = _re.search(name + r"\s*=\s*\{([^}]*)\}", src, _re.S)
        return set(_re.findall(r'"([a-z_]+)"', m.group(1))) if m else set()
    alive = _set("FX_CAMERAS") | _set("FX_CAMERAS_DEPTH")
    unbuilt = set(_re.findall(r'^\s+"([a-z_]+)":\s+"', src.split("FX_CAMERAS_UNBUILT", 1)[-1]
                              .split("\n}", 1)[0], _re.M)) if "FX_CAMERAS_UNBUILT" in src else set()
    for cam in ("dolly_zoom", "orbit", "rack_focus"):
        if cam in unbuilt or cam not in alive:
            dead.append(cam)
    out["dead_cameras"] = dead
    if dead:
        say("BROKEN", "defects",
            f"STILL REAL - short.py cannot render {', '.join(dead)}, so a clip asking "
            f"for one is byte-identical to static")
    cards_claiming = []
    cdir = os.path.join(STUDIO, "cameras")
    for f in sorted(os.listdir(cdir)):
        c = json.load(open(os.path.join(cdir, f), encoding="utf-8"))
        if c.get("id") in dead and c.get("status") not in ("unavailable", "weak"):
            cards_claiming.append(c["id"])
    if cards_claiming:
        say("WRONG", "defects", f"camera card(s) {cards_claiming} do not say they are dead")

    # (b) the night grade. Measure the transfer curve rather than quoting a number.
    grade = None
    lp = os.path.join(STUDIO, "looks", "night.json")
    if os.path.exists(lp):
        grade = json.load(open(lp, encoding="utf-8")).get("grade")
    if grade:
        curve, black_at = [], None
        for lum in (16, 32, 48, 64, 80, 96, 128, 170, 200):
            y = _grade_luma(grade, lum)
            curve.append((lum, y))
            if y <= 1 and (black_at is None or lum > black_at):
                black_at = lum
        out["night_curve"] = curve
        out["night_black_below"] = black_at
        if black_at:
            say("BROKEN", "defects",
                f"STILL REAL - the night grade crushes every input luma at or below "
                f"{black_at} to pure black (measured: "
                + ", ".join(f"{a}->{b:.0f}" for a, b in curve[:5]) + "). A dark insert "
                f"does not go dark, it goes to nothing.")

    # (c) negatives, asked of the GRAPH rather than of a remembered node number.
    #
    # The negative node is whichever node feeds a sampler's `negative` input. Finding it
    # that way rather than hardcoding "node 11" is the difference between a check and a
    # second copy of the same assumption - and the first version of this check, which
    # grepped the whole file for `set_path(wf, "11.`, reported all four graphs healthy
    # because short.py writes node 11 of a DIFFERENT workflow (a SaveImage prefix) and
    # node 11 of a THIRD one (an audio duration). It found the string and missed the fact.
    #
    # PER DRIVER, not per graph. short.py is the renderer the app and the wizard reach;
    # epic.py is the older hand-run one. They do NOT agree - epic.py writes a negative
    # into the qwen graphs and short.py does not - and collapsing them into one answer
    # per workflow reports the defect as fixed on the exact path where it is live.
    negs = {}
    load_graphs()
    for drv in ("scripts/short.py", "scripts/epic.py"):
        for targets, path, _ln, _fn in driver_bindings(drv):
            for graph in targets:
                nid = negative_node(_GRAPHS.get(graph) or {})
                nins = (_GRAPHS.get(graph) or {}).get(nid or "", {}).get("inputs") or {}
                if nid and not ("text" in nins or "prompt" in nins):
                    nid = None          # no negative TEXT to reach - not a defect
                rec = negs.setdefault((drv, graph), {"written": False,
                                                     "negative_node": nid})
                if nid and path and path.startswith(f"{nid}.inputs.") \
                        and path.split(".")[-1] in ("text", "prompt"):
                    rec["written"] = True
    out["negative_written"] = {f"{d} -> {g}": v for (d, g), v in negs.items()}
    for drv in ("scripts/short.py", "scripts/epic.py"):
        un = sorted(g for (d, g), v in negs.items()
                    if d == drv and v["negative_node"] and not v["written"])
        wr = sorted(g for (d, g), v in negs.items() if d == drv and v["written"])
        if un:
            say("WRONG", "defects",
                f"STILL REAL - {drv} writes a positive prompt into {len(un)} graph(s) and "
                f"never touches the node feeding the sampler's `negative` input, so the "
                f"negative is whatever text is committed in the JSON and no card, "
                f"character or film can reach it: "
                + "; ".join(f"{g} (node {negs[(drv, g)]['negative_node']})" for g in un))
        if wr:
            say("NOTE", "defects", f"{drv} DOES write a negative on: " + ", ".join(wr))

    # (d) TERRA's headpiece.
    tp = os.path.join(STUDIO, "characters", "TERRA.json")
    if os.path.exists(tp):
        t = json.load(open(tp, encoding="utf-8"))
        tags = (t.get("tags") or "").lower()
        note = json.dumps(t).lower()
        if "red hair ribbon" in tags and "pink-and-gold ornament" in note \
                and t.get("headpiece"):
            # Understood and fenced: prose corrected, tags held for the LoRA contract
            # (captions absorbed the ornament into the trigger). Not a defect any more.
            out["terra_headpiece"] = "resolved: prose fixed, tags held (LoRA contract)"
            say("NOTE", "defects",
                "TERRA tags still say 'red hair ribbon' BY DESIGN - the LoRA absorbed the "
                "real ornament into its trigger and the tag is inert on the anime engine; "
                "prose (qwen/flux2) now describes the ornament. See TERRA.json headpiece.")
        elif "red hair ribbon" in tags and "pink-and-gold ornament" in note:
            out["terra_headpiece"] = "still real"
            say("WRONG", "defects",
                "STILL REAL - TERRA.json tags say 'red hair ribbon'; the card's own "
                "identity_note records that all 160 view renders draw a pink-and-gold "
                "ornament instead, and it is trained into the LoRA. The tags are the "
                "prompt, so every future render inherits the mismatch.")
    return out


def _grade_luma(vf, lum):
    """Push a flat grey plate of a known luma through an ffmpeg filter chain and read
    the mean luma back. This is how a grade gets checked - by measuring it, not by
    reading the filter string and reasoning about it."""
    src = f"color=c=0x{lum:02x}{lum:02x}{lum:02x}:s=160x90:d=0.1"
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", src, "-vf", vf,
           "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    try:
        b = subprocess.run(cmd, capture_output=True, timeout=60).stdout
    except Exception:                                               # noqa: BLE001
        return float("nan")
    return sum(b) / max(len(b), 1)


# ──────────────────────────────────────────────────────────────────── main
def main():
    global HOST
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sections", nargs="*", choices=SECTIONS, default=SECTIONS)
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    HOST = a.host
    want = a.sections or SECTIONS

    result = {}
    runners = {"routes": check_routes, "tools": check_tools, "cards": check_cards,
               "workflows": check_workflows, "movies": check_movies,
               "spine": check_spine, "defects": check_defects}
    for s in SECTIONS:
        if s not in want:
            continue
        if not a.json:
            print(f"\n=== {s} ", "─" * (56 - len(s)), sep="")
        try:
            result[s] = runners[s]()
        except Exception as e:                                      # noqa: BLE001
            import traceback
            say("BROKEN", s, f"the {s} check itself crashed: {type(e).__name__}: {e}")
            result[s] = {"crashed": traceback.format_exc()[-800:]}
        if not a.json:
            for sev, sec, msg in [r for r in R if r[1] == s]:
                print(f"  {sev:<7} {msg}")
            if not [r for r in R if r[1] == s]:
                print("  clean")

    counts = {}
    for sev, _, _ in R:
        counts[sev] = counts.get(sev, 0) + 1

    if a.json:
        print(json.dumps({"findings": [{"severity": s, "section": c, "message": m}
                                       for s, c, m in R],
                          "counts": counts, "detail": result}, indent=1))
        # Same exit status as the human run. A --json invocation is the one most likely
        # to be wired into something that checks it.
        return 1 if counts.get("BROKEN") else 0
    print("\n" + "=" * 64)
    print("  " + "  ".join(f"{k} {v}" for k, v in
                           sorted(counts.items(), key=lambda x: SEV.get(x[0], 9)))
          or "  nothing found")
    print("  BROKEN = does not work.  WRONG = works and tells you something untrue.")
    print("  GAP = missing, and the app does not claim otherwise.  NOTE = worth knowing.")
    return 1 if counts.get("BROKEN") else 0


if __name__ == "__main__":
    sys.exit(main())
