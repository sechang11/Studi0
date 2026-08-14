#!/usr/bin/env python3
"""Audit the repo for the bug CLASSES this project actually keeps producing.

    python3 studio/_tools/audit.py               # everything
    python3 studio/_tools/audit.py --only cards
    python3 studio/_tools/audit.py --strict      # exit 1 on any finding

WHY THESE CHECKS AND NOT OTHERS. Every check below exists because that exact mistake was
made here and cost something. This is not a generic linter; it is a list of scars.

  SILENT SUCCESS      the work happens, the report lies. A job table wiped by a
                      per-request reload; a scoreboard that read two lines of output as
                      one and called five successes failures; ffmpeg told to be quiet and
                      then asked to report. The worst class, because nothing looks wrong.
  SCHEMA DRIFT        a field that is a list in one card and a string in another. Crashed
                      a dossier read, and "fixing" it flattened five wardrobe rungs into
                      one string across nine cards.
  GRAPH ROT           a workflow node nobody reads, or a reference to a node that is not
                      there. A LoRA hung off the wrong node renders exactly as if it were
                      not there at all.
  IMPOSED DEFAULTS    an unmetered cue given 140 bpm; an unkeyed cue given D minor. The
                      value is invented and then treated as measured.
  UNREACHABLE         a capability that exists and cannot be selected. FLUX.2 works and no
                      style card routes to it.
  DANGEROUS TOOLING   scripts that run their whole job on any argument, including --help.
"""
import argparse, ast, glob, json, os, re, subprocess, sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)

FINDINGS = []


def add(sev, group, what, where="", fix=""):
    FINDINGS.append({"sev": sev, "group": group, "what": what, "where": where, "fix": fix})


# ── workflows ────────────────────────────────────────────────────────────────────────

def audit_workflows():
    for f in sorted(glob.glob(os.path.join(ROOT, "workflows", "*.json"))):
        name = os.path.basename(f)
        try:
            w = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            add("error", "graph", "will not parse: %s" % str(e)[:80], name)
            continue
        nodes = {k: v for k, v in w.items() if isinstance(v, dict) and v.get("class_type")}

        # A reference to a node that is not in the graph. ComfyUI rejects the whole prompt.
        for nid, node in nodes.items():
            for k, v in (node.get("inputs") or {}).items():
                if (isinstance(v, list) and len(v) == 2 and isinstance(v[0], str)
                        and v[0] not in w):
                    add("error", "graph", "%s.%s points at missing node %s"
                        % (nid, k, v[0]), name, "the graph will be refused wholesale")

        # Nodes nothing reads and that produce nothing. ComfyUI will still execute them.
        consumed = set()
        for node in nodes.values():
            for v in (node.get("inputs") or {}).values():
                if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str):
                    consumed.add(v[0])
        terminal = {n for n, d in nodes.items()
                    if re.search(r"Save|Preview|Output", str(d.get("class_type")))}
        # A workflow file is a TEMPLATE, not a finished graph. Callers wire slots at
        # runtime - epic.py attaches a second and third LoadImage to the text encoders
        # only when the shot names that many references. So an unread LOADER is usually a
        # slot waiting for a caller, and reporting it as a fault means reporting most
        # templates as faulty, which is how an audit becomes noise.
        #
        # An unread node that COMPUTES is different: it is submitted, it runs, and its
        # result is discarded.
        SLOT = r"Load|Empty|Checkpoint|Loader|Text|Note|Primitive"
        for nid in nodes:
            if nid in consumed or nid in terminal:
                continue
            ct = str(nodes[nid]["class_type"])
            if re.search(SLOT, ct):
                add("info", "graph", "node %s (%s) is unwired in the file" % (nid, ct),
                    name, "fine if a caller wires it; dead weight if none does")
            else:
                add("warn", "graph", "node %s (%s) computes and nothing reads it"
                    % (nid, ct), name,
                    "it is submitted, it runs, and the result is thrown away")

        # Audio latent rate against video rate. A 4% drift is a second lost per half minute.
        vid = None
        for d in nodes.values():
            if d.get("class_type") == "LTXVConditioning":
                vid = d["inputs"].get("frame_rate")
        if vid:
            for nid, d in nodes.items():
                if "EmptyLatentAudio" in str(d.get("class_type")):
                    a = d["inputs"].get("frame_rate")
                    if a and float(a) != float(vid):
                        add("error", "graph", "audio latent %sfps against %sfps video"
                            % (a, vid), "%s node %s" % (name, nid), "drift")

        # A LoadImage naming a file that is not in ComfyUI's input dir.
        comfy_in = os.path.expanduser("~/ComfyUI/input")
        for nid, d in nodes.items():
            if d.get("class_type") == "LoadImage":
                img = d["inputs"].get("image")
                if isinstance(img, str) and img and not os.path.exists(
                        os.path.join(comfy_in, img)):
                    add("info", "graph", "LoadImage default %r is not on disk" % img,
                        "%s node %s" % (name, nid),
                        "harmless if every caller sets it; a crash if one forgets")


# ── cards ────────────────────────────────────────────────────────────────────────────

def audit_cards():
    for lib in ("characters", "styles", "places", "looks", "voices", "cameras",
                "motions", "emotions", "cues", "sfx"):
        d = os.path.join(STUDIO, lib)
        if not os.path.isdir(d):
            continue
        cards, types = {}, {}
        for f in sorted(glob.glob(os.path.join(d, "*.json"))):
            cid = os.path.basename(f)[:-5]
            if cid.startswith("_"):
                continue
            try:
                c = json.load(open(f, encoding="utf-8"))
            except Exception as e:
                add("error", "cards", "will not parse: %s" % str(e)[:70],
                    "%s/%s" % (lib, cid))
                continue
            cards[cid] = c
            for k, v in c.items():
                types.setdefault(k, {}).setdefault(type(v).__name__, []).append(cid)

        # A field that is a list here and a string there. This crashed a dossier read.
        for k, kinds in types.items():
            kinds = {t: ids for t, ids in kinds.items() if t != "NoneType"}
            if len(kinds) > 1 and len(cards) > 1:
                desc = "; ".join("%s on %s" % (t, ", ".join(sorted(ids)[:4]))
                                 for t, ids in sorted(kinds.items()))
                add("warn", "cards", "field %r has mixed types - %s" % (k, desc), lib,
                    "one consumer will join it and the other will index it")

        # Referenced files that are not there.
        for cid, c in cards.items():
            for key, base in (("sheet", os.path.expanduser("~/ComfyUI/input")),
                              ("file", os.path.join(
                                  os.path.expanduser("~/ComfyUI"), "custom_nodes",
                                  "TTS-Audio-Suite"))):
                v = c.get(key)
                if isinstance(v, str) and v and not os.path.exists(os.path.join(base, v)):
                    add("warn", "cards", "%s names %s %r which is not on disk"
                        % (cid, key, v), lib, "shows as unheld rather than as an error")
            lora = c.get("lora")
            if isinstance(lora, str) and lora:
                # A lora field may be a bare .safetensors name OR the id of a card in
                # studio/loras/, whose `file` names the real weights. Resolve before
                # accusing: the indirection is deliberate and the card carries the
                # base-model and strength findings that make the reference safe.
                weights = os.path.expanduser("~/ComfyUI/models/loras")
                card = os.path.join(STUDIO, "loras", lora + ".json")
                resolved = None
                if os.path.exists(os.path.join(weights, lora)):
                    resolved = lora
                elif os.path.isfile(card):
                    try:
                        f2 = json.load(open(card, encoding="utf-8")).get("file")
                    except Exception:
                        f2 = None
                    if f2 and os.path.exists(os.path.join(weights, f2)):
                        resolved = f2
                    elif f2:
                        add("error", "cards",
                            "%s -> lora card %r -> %r which is not on disk"
                            % (cid, lora, f2), lib,
                            "passed through, quietly never read")
                    else:
                        add("error", "cards",
                            "%s -> lora card %r has no file field" % (cid, lora), lib)
                    continue
                if not resolved:
                    add("error", "cards",
                        "%s names a LoRA that is neither a file nor a card: %s"
                        % (cid, lora), lib,
                        "it is passed through, quietly never read, and nothing warns you")


# ── unreachable capability ───────────────────────────────────────────────────────────

def audit_reachable():
    sys.path.insert(0, STUDIO)
    sys.path.insert(0, TOOLS)
    try:
        import roll as R
        import compose
        libs = R.load_libs()
    except Exception as e:
        add("info", "reach", "could not load the libraries: %s" % str(e)[:80])
        return
    engines = {}
    for sid in libs.get("styles", {}):
        if sid.startswith("_"):
            continue
        try:
            e = compose.resolve(libs, {"style": sid}).get("engine")
        except Exception:
            continue
        engines.setdefault(e, []).append(sid)
    known = {"anime", "qwen", "flux2"}
    for e in sorted(known - set(engines)):
        add("warn", "reach", "engine %r is installed but NO style card routes to it" % e,
            "studio/styles", "the capability exists and cannot be chosen")
    for e, ids in sorted(engines.items()):
        ready = [s for s in ids if libs["styles"][s].get("status") == "ready"]
        if ids and not ready:
            add("warn", "reach", "engine %r has %d cards and none are ready"
                % (e, len(ids)), "studio/styles")


def audit_workflow_files():
    """Referenced-vs-exists for workflow files, both directions, loads kept apart from
    mentions.

    The first scan of this problem counted ANY "NN_name.json" string in a .py file as a
    reference and reported six missing workflows. Five of the six were prose inside
    _write_caps.py - "Build workflows/32_..." - plans, not loads. A reachability check that
    cannot tell a load from a mention would cry wolf forever, so this one separates them:

      error  a literal passed to load_wf()/wf_of() that is not on disk - that path crashes
      error  a domain card whose `workflow` field is not on disk - the same crash one
             indirection later, because render_job loads card["workflow"] verbatim
      info   a mention that is neither loaded nor on disk - a plan or a stale note
      info   a file on disk that nothing mentions - dead weight, not danger
    """
    wf_dir = os.path.join(os.path.dirname(STUDIO), "workflows")
    if not os.path.isdir(wf_dir):
        add("error", "reach", "workflows/ directory is missing", wf_dir)
        return
    on_disk = {f for f in os.listdir(wf_dir) if f.endswith(".json")}

    load_re = re.compile(r'(?:load_wf|wf_of)\(\s*["\']([^"\']+\.json)')
    name_re = re.compile(r'["\']([0-9]{2}_[a-z0-9_]+\.json)["\']')
    loaded, mentioned = {}, {}
    srcs = (glob.glob(os.path.join(TOOLS, "*.py"))
            + glob.glob(os.path.join(STUDIO, "*.py"))
            + glob.glob(os.path.join(os.path.dirname(STUDIO), "scripts", "*.py")))
    for f in srcs:
        try:
            src = open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        name = os.path.relpath(f, os.path.dirname(STUDIO)).replace("\\", "/")
        for m in load_re.finditer(src):
            loaded.setdefault(m.group(1), name)
        for m in name_re.finditer(src):
            mentioned.setdefault(m.group(1), name)

    for wf, where in sorted(loaded.items()):
        if wf not in on_disk:
            add("error", "reach", "load_wf(%r) but the file is not in workflows/" % wf,
                where, "that code path crashes the moment it runs")
    for f in sorted(glob.glob(os.path.join(STUDIO, "domains", "*.json"))):
        try:
            card = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        w = card.get("workflow")
        if w and w not in on_disk:
            add("error", "reach",
                "domain card names workflow %r which is not on disk" % w,
                "domains/" + os.path.basename(f),
                "render_job loads card['workflow'] verbatim - this crashes")
    for wf, where in sorted(mentioned.items()):
        if wf not in on_disk and wf not in loaded:
            add("info", "reach",
                "%r is mentioned but not on disk and not loaded - a plan or a stale note"
                % wf, where)
    for wf in sorted(on_disk - set(mentioned)):
        add("info", "reach", "workflow %r exists on disk and nothing mentions it" % wf,
            "workflows/" + wf, "dead weight, not danger")


def audit_card_schema():
    """Every card against its kind's declared schema (studio/cards.py).

    This differs from audit_cards, which detects INTERNAL inconsistency (a field whose
    type varies across a kind) without knowing what the kind should look like. The schema
    check knows: required fields, types, enums, per-kind statuses, and the semantic rules
    the library has paid for - a character must carry a usable dialect, a wear ladder must
    be a list. One measures agreement; the other measures conformance to a declaration.
    """
    sys.path.insert(0, STUDIO)
    try:
        import cards as C
    except Exception as e:
        add("error", "schema", "studio/cards.py failed to import: %s" % str(e)[:100])
        return
    for sev, kind, cid, msg in C.validate_all():
        add("error" if sev == "error" else "warn", "schema", msg,
            "%s/%s" % (kind, cid))


# ── silent-failure patterns in our own code ──────────────────────────────────────────

SILENT = [
    (r"subprocess\.run\([^)]*check\s*=\s*False", "check=False - a failure is swallowed"),
    (r"except\s*:\s*\n\s*pass", "bare except: pass - hides every error"),
    (r"except Exception:\s*\n\s*pass", "except Exception: pass - hides every error"),
    # ONLY filters that report on STDERR. -v error is correct and normal for:
    #   ffprobe -show_entries      prints to stdout
    #   metadata=print:file=X      writes to a file
    #   -f md5 -                   prints to stdout
    # The real bug is silencedetect / volumedetect / a bare metadata=print, which report at
    # info level on stderr and vanish when ffmpeg is quieted. Flagging the stdout cases too
    # produced eight false alarms and would have buried the one real hit.
    (r'"-v",\s*"error"(?:(?!metadata=print:[^"]*file=)[^\n])*?'
     r'(silencedetect|volumedetect|metadata=print(?!:[^"]*file=))',
     "ffmpeg quieted with -v error while being asked to REPORT ON STDERR - the "
     "measurement is suppressed and reads as zero"),
]


def audit_code():
    for f in sorted(glob.glob(os.path.join(STUDIO, "_tools", "*.py"))
                    + glob.glob(os.path.join(ROOT, "scripts", "*.py"))
                    + [os.path.join(STUDIO, "serve.py"),
                       os.path.join(STUDIO, "story.py")]):
        name = os.path.relpath(f, ROOT)
        try:
            src = open(f, encoding="utf-8").read()
        except Exception:
            continue
        try:
            ast.parse(src)
        except SyntaxError as e:
            add("error", "code", "syntax error line %s: %s" % (e.lineno, e.msg), name)
            continue
        for pat, why in SILENT:
            for m in re.finditer(pat, src, re.S):
                line = src[:m.start()].count("\n") + 1
                add("info", "code", why, "%s:%d" % (name, line))

        # A *_routes.py module is imported by serve.py and never run from a shell, so the
        # no-argparse hazard cannot fire on it. Reported at info so the inventory stays
        # complete, but kept off the warn list, which is only useful if every line on it is
        # worth acting on. A route module that ALSO has a __main__ block is a script and
        # falls through to the real check below.
        _is_route = (name.endswith("_routes.py")
                     and not re.search(r'if __name__ == .__main__.', src))
        if _is_route and "argparse" not in src:
            add("info", "code",
                "route module imported by serve.py - no argparse needed, never run "
                "from a shell", name)

        # The known hazard: a tool with no argparse runs its whole job on ANY argument.
        if ("/_tools/" in f.replace("\\", "/") and "argparse" not in src
                and not _is_route):
            if re.search(r'if __name__ == .__main__.', src) or "\ndef main" not in src:
                writes = bool(re.search(r"^\s*(open\(|json\.dump|os\.makedirs)", src, re.M))
                if writes:
                    add("warn", "code",
                        "no argparse and writes at import or module level - runs its whole "
                        "job on any argument, including --help", name,
                        "read it before running it")


# ── live app ─────────────────────────────────────────────────────────────────────────

def audit_routes():
    import urllib.request
    import urllib.error
    base = "http://127.0.0.1:8777"
    pages = ["/", "/cast", "/voices", "/story", "/generate", "/tools", "/docs",
             "/character/new", "/gallery", "/wizard", "/styles", "/places",
             "/capabilities", "/changelog"]
    apis = ["/api/story", "/api/voice", "/api/tool", "/api/character/sources",
            "/api/tool/styles", "/api/story/libraries"]
    for p in pages + apis:
        try:
            r = urllib.request.urlopen(base + p, timeout=15)
            if r.status >= 500:
                add("error", "routes", "HTTP %d" % r.status, p)
        except urllib.error.HTTPError as e:
            sev = "error" if e.code >= 500 else "info"
            add(sev, "routes", "HTTP %d" % e.code, p)
        except Exception as e:
            add("error", "routes", str(e)[:70], p,
                "is the studio running on 8777?")


CHECKS = {"workflows": audit_workflows, "wf_files": audit_workflow_files,
          "schema": audit_card_schema,
          "cards": audit_cards,
          "reach": audit_reachable, "code": audit_code, "routes": audit_routes}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=sorted(CHECKS))
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--sev", choices=["error", "warn", "info"], default="info")
    a = ap.parse_args()

    for name, fn in CHECKS.items():
        if a.only and name != a.only:
            continue
        try:
            fn()
        except Exception as e:
            add("error", name, "the check itself failed: %s" % str(e)[:120])

    order = {"error": 0, "warn": 1, "info": 2}
    keep = [f for f in FINDINGS if order[f["sev"]] <= order[a.sev]]
    keep.sort(key=lambda f: (order[f["sev"]], f["group"], f["where"]))

    n = {"error": 0, "warn": 0, "info": 0}
    last = None
    for f in keep:
        n[f["sev"]] += 1
        if f["group"] != last:
            print("\n%s" % f["group"].upper())
            last = f["group"]
        print("  %-5s %-34s %s" % (f["sev"], f["where"][:34], f["what"]))
        if f["fix"]:
            print("        -> %s" % f["fix"])
    print("\n%d error, %d warn, %d info" % (n["error"], n["warn"], n["info"]))
    return 1 if (n["error"] or (a.strict and n["warn"])) else 0


if __name__ == "__main__":
    sys.exit(main())
