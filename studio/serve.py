#!/usr/bin/env python3
"""studio/serve.py - a local web UI for browsing the variable library and building scenes.

    python3 studio/serve.py            then open http://localhost:8777

No dependencies, no build step. The library is read from disk on every request, so editing
a preset file and refreshing the page shows the change immediately - the point is that the
JSON files stay the source of truth and this is only a window onto them.

Endpoints:
    /                 the app
    /api/library      every preset folder, expanded
    /api/variables    the 461-variable census
    /api/cards        capability cards - what each option value looks like
    /api/movies       .movie files found in studio/movies
    /api/save         POST {name, text} -> writes studio/movies/<name>.movie
"""
import http.server, json, os, re, socket, socketserver, subprocess, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("STUDIO_PORT", "8777"))
# Bind on all interfaces so the studio is usable from the machine you actually sit at,
# not only from a browser on the render box. Set STUDIO_BIND=127.0.0.1 to keep it local.
BIND = os.environ.get("STUDIO_BIND", "0.0.0.0")

# Serving a .webp as image/png happens to work in most browsers because they sniff the
# magic bytes, but it is wrong, it defeats caching heuristics, and it breaks anything
# that trusts the header. Be explicit.
MIME = {".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg", ".gif": "image/gif", ".mp4": "video/mp4",
        ".webm": "video/webm", ".mp3": "audio/mpeg", ".wav": "audio/wav",
        ".svg": "image/svg+xml"}

# folders that hold pickable presets, in the order the UI should show them
GROUPS = ["shots", "cameras", "transitions", "looks", "lighting", "layers",
          "weather", "emotions", "soundscapes", "pacing", "places", "characters", "cues",
          "prompts", "checkpoints", "voices", "sfx", "mesh"]


def library():
    out = {}
    for g in GROUPS:
        d = f"{HERE}/{g}"
        if not os.path.isdir(d):
            continue
        items = []
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json"):
                continue
            try:
                items.append(json.load(open(f"{d}/{fn}", encoding="utf-8")))
            except Exception as e:
                items.append({"id": fn[:-5], "desc": f"UNREADABLE: {e}", "status": "error"})
        for it in items:
            # .webp first: the panels were re-encoded from PNG (14.8x smaller) and a
            # stale .png beside a .webp should not win.
            for ext in (".webp", ".png", ".mp4"):
                if os.path.exists(f"{HERE}/samples/{g}/{it['id']}{ext}"):
                    it["sample"] = f"/samples/{g}/{it['id']}{ext}"
                    break
        if items:
            out[g] = items
    return out


ROOT = os.path.dirname(HERE)
COMFY_OUT = os.path.expanduser(
    os.environ.get("COMFY_ROOT", "~/ComfyUI")) + "/output/claude-generated/12-shorts"


def safe_name(s):
    """Names come off the network and are used to build paths and a shell command, so
    strip everything that is not plainly a filename. No dots, so `..` cannot form."""
    return "".join(c for c in str(s) if c.isalnum() or c in "-_")[:64]


def cast():
    """Characters, each with whatever identity assets actually exist for them.

    The card on disk is the source of truth for tags, voice and sheet; the turnaround
    views are discovered from samples/cast/<id>/ rather than recorded, so the page cannot
    claim views that were deleted. Same reason the LoRA is reported from the card only
    after training wrote it there.
    """
    d = f"{HERE}/characters"
    if not os.path.isdir(d):
        return []
    out = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            c = json.load(open(f"{d}/{fn}", encoding="utf-8"))
        except Exception as e:
            out.append({"id": fn[:-5], "name": fn[:-5], "desc": f"UNREADABLE: {e}"})
            continue
        vd = f"{HERE}/samples/cast/{c.get('id', fn[:-5])}"
        views = []
        if os.path.isdir(vd):
            for v in sorted(os.listdir(vd)):
                if v.endswith(".png"):
                    views.append({"name": v[:-4].split("_", 1)[-1],
                                  "file": f"/samples/cast/{c.get('id', fn[:-5])}/{v}"})
        c["views"] = views
        out.append(c)
    return out


def verify_queue():
    """Cards that have panels but no human verdict, plus the ones already done.

    This is the project's largest honest gap: 1026 rendered comparison panels that
    nobody has looked at. Both predictions ever checked against pixels turned out WRONG
    (extreme_close was predicted to fail and is the best panel in the set; extreme_wide
    was predicted to work and loses the figure entirely), so the claims cannot be trusted
    until someone looks. Predicting is worse than useless here.

    Unverified first, since that is the work. Cards with no panels are excluded - there
    is nothing to look at.
    """
    d = f"{HERE}/cards"
    if not os.path.isdir(d):
        return {"todo": [], "done": [], "total": 0}
    todo, done = [], []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            c = json.load(open(f"{d}/{fn}", encoding="utf-8"))
        except Exception:
            continue
        if c.get("not_visual") or not (c.get("panels") or c.get("sheet")):
            continue
        item = {
            "slug": fn[:-5],
            "variable": c.get("variable", fn[:-5]),
            "claim": c.get("claim", ""),
            "sheet": c.get("sheet"),
            # the clause is what the option ASKED FOR, in the model's own words. Showing
            # it means a reviewer does not need to know the term to judge the picture.
            "panels": [{"value": p.get("value"), "sample": p.get("sample"),
                        "control": bool(p.get("control")),
                        "clause": p.get("clause") or ""}
                       for p in (c.get("panels") or [])],
            "verdict": c.get("verdict"),
            "look_at": c.get("look_at"),
            "review": c.get("review") or [],
        }
        (done if c.get("verdict") else todo).append(item)
    return {"todo": todo, "done": done, "total": len(todo) + len(done)}


def domains():
    """The non-film makers: voice, music, sfx, image, mesh.

    Each is a descriptor naming its workflow, its node mapping and its fields. The page
    is generic - adding a sixth is a JSON file, not a feature.
    """
    d = f"{HERE}/domains"
    if not os.path.isdir(d):
        return []
    out = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            out.append(json.load(open(f"{d}/{fn}", encoding="utf-8")))
        except Exception as e:
            out.append({"id": fn[:-5], "name": fn[:-5], "desc": f"UNREADABLE: {e}"})
    return out


def gallery():
    """Every generation, newest first, with the full recipe that produced it.

    Read fresh from the append-only manifest on each request, so a run in progress shows
    up on refresh without restarting anything. A malformed line is skipped rather than
    taking the whole endpoint down - the writer appends while this reads, so a torn final
    line is normal rather than exceptional.
    """
    p = f"{HERE}/gallery/manifest.jsonl"
    if not os.path.exists(p):
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    out.reverse()
    return out


def templates():
    """Clickable scene templates - a bundle that sets many variables at once AND brings
    its own shots, so you start from something that works instead of a blank page.

    Each is shown with a rendered example and its full settings visible, the way a model
    page shows the prompt that made the picture. The settings are not hidden behind the
    thumbnail: seeing exactly which knobs produced it is the point, because that is what
    lets you change one of them on purpose.

    A template is expanded by the WIZARD into ordinary .movie text. Nothing downstream
    knows templates exist, so a film stays a readable text file you can hand-edit.
    """
    d = f"{HERE}/templates"
    if not os.path.isdir(d):
        return []
    out = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            t = json.load(open(f"{d}/{fn}", encoding="utf-8"))
        except Exception as e:
            out.append({"id": fn[:-5], "name": fn[:-5],
                        "desc": f"UNREADABLE: {e}", "status": "error"})
            continue
        for ext in (".webp", ".jpg", ".png", ".mp4"):
            p = f"{HERE}/samples/templates/{t.get('id', fn[:-5])}{ext}"
            if os.path.exists(p):
                t["sample"] = f"/samples/templates/{t.get('id', fn[:-5])}{ext}"
                break
        out.append(t)
    return out


def cards():
    d = f"{HERE}/cards"
    if not os.path.isdir(d):
        return []
    return [json.load(open(f"{d}/{f}", encoding="utf-8"))
            for f in sorted(os.listdir(d)) if f.endswith(".json")]


def variables():
    p = f"{HERE}/variables.json"
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []


def movies():
    d = f"{HERE}/movies"
    if not os.path.isdir(d):
        return []
    return [{"name": f[:-6], "text": open(f"{d}/{f}", encoding="utf-8").read()}
            for f in sorted(os.listdir(d)) if f.endswith(".movie")]


class H(http.server.SimpleHTTPRequestHandler):
    def _send(self, obj, code=200, ctype="application/json"):
        body = obj if isinstance(obj, bytes) else json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            p = f"{HERE}/app.html"
            if not os.path.exists(p):
                return self._send(b"app.html is missing", 500, "text/plain")
            return self._send(open(p, "rb").read(), 200, "text/html; charset=utf-8")
        if path.startswith("/samples/"):
            rel = os.path.normpath(path[1:]).replace("\\", "/")
            fp = os.path.join(HERE, rel)
            if not os.path.abspath(fp).startswith(HERE) or not os.path.isfile(fp):
                return self._send({"error": "no sample"}, 404)
            ct = MIME.get(os.path.splitext(fp)[1].lower(), "application/octet-stream")
            return self._send(open(fp, "rb").read(), 200, ct)
        if path in ("/wizard", "/wizard.html"):
            p = f"{HERE}/wizard.html"
            if not os.path.exists(p):
                return self._send(b"wizard.html is missing", 500, "text/plain")
            return self._send(open(p, "rb").read(), 200, "text/html; charset=utf-8")
        if path == "/api/effects":
            p = f"{HERE}/effects.json"
            if not os.path.exists(p):
                return self._send({"tiers": {}, "vars": {}})
            return self._send(json.load(open(p, encoding="utf-8")))
        if path in ("/gallery", "/gallery.html"):
            p = f"{HERE}/gallery.html"
            if not os.path.exists(p):
                return self._send(b"gallery.html is missing", 500, "text/plain")
            return self._send(open(p, "rb").read(), 200, "text/html; charset=utf-8")
        if path in ("/make", "/make.html"):
            p = f"{HERE}/make.html"
            if not os.path.exists(p):
                return self._send(b"make.html is missing", 500, "text/plain")
            return self._send(open(p, "rb").read(), 200, "text/html; charset=utf-8")
        if path in ("/cast", "/cast.html"):
            p = f"{HERE}/cast.html"
            if not os.path.exists(p):
                return self._send(b"cast.html is missing", 500, "text/plain")
            return self._send(open(p, "rb").read(), 200, "text/html; charset=utf-8")
        if path == "/api/cast":
            return self._send(cast())
        if path in ("/verify", "/verify.html"):
            p = f"{HERE}/verify.html"
            if not os.path.exists(p):
                return self._send(b"verify.html is missing", 500, "text/plain")
            return self._send(open(p, "rb").read(), 200, "text/html; charset=utf-8")
        if path == "/api/verify/queue":
            return self._send(verify_queue())
        if path in ("/tags", "/tags.html"):
            p = f"{HERE}/tags.html"
            if not os.path.exists(p):
                return self._send(b"tags.html is missing", 500, "text/plain")
            return self._send(open(p, "rb").read(), 200, "text/html; charset=utf-8")
        if path == "/api/tags":
            d = f"{HERE}/tags"
            if not os.path.isdir(d):
                return self._send([])
            out = []
            for fn in sorted(os.listdir(d)):
                if fn.endswith(".json"):
                    try:
                        out.append(json.load(open(f"{d}/{fn}", encoding="utf-8")))
                    except Exception:
                        pass
            return self._send(out)
        if path == "/api/domains":
            return self._send(domains())
        if path == "/api/render/status":
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            return self._render_status(q.get("name", [""])[0])
        if path.startswith("/render/") and path.endswith(".mp4"):
            # The finished film lives under ComfyUI's output tree, keyed by the film's
            # TITLE slug rather than the .movie name, so resolve it through the film json.
            name = safe_name(path[len("/render/"):-4])
            fj = f"{HERE}/movies/{name}.json"
            if not os.path.exists(fj):
                return self._send({"error": "unknown render"}, 404)
            try:
                slug = json.load(open(fj, encoding="utf-8"))["title"].lower().replace(" ", "-")
            except Exception:
                return self._send({"error": "unreadable film"}, 500)
            fp = f"{COMFY_OUT}/{slug}/{slug}.mp4"
            if not os.path.isfile(fp):
                return self._send({"error": "not rendered yet"}, 404)
            return self._send(open(fp, "rb").read(), 200, "video/mp4")
        if path == "/api/gallery":
            return self._send(gallery())
        if path == "/api/templates":
            return self._send(templates())
        if path == "/api/library":
            return self._send(library())
        if path == "/api/cards":
            return self._send(cards())
        if path == "/api/variables":
            return self._send(variables())
        if path == "/api/movies":
            return self._send(movies())
        return self._send({"error": "not found"}, 404)

    def _render_start(self, data):
        """Compile a .movie and launch the render, so a beginner never has to open a
        terminal to see their own scene.

        compile runs SYNCHRONOUSLY - it takes about a tenth of a second and its errors
        are the ones an author can actually act on (unknown character, unknown cue, a
        movie-level variable set on a scene). Those come straight back to the page.
        The render itself is minutes long, so it is detached and polled.
        """
        name = safe_name(data.get("name", ""))
        if not name:
            return self._send({"error": "name required"}, 400)
        movie = f"{HERE}/movies/{name}.movie"
        if not os.path.exists(movie):
            return self._send({"error": f"no such scene: {name}.movie"}, 404)

        r = subprocess.run([sys.executable, f"{HERE}/compile.py", movie],
                           capture_output=True, text=True, cwd=ROOT, timeout=120)
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode != 0:
            return self._send({"error": "compile failed", "detail": out.strip()[-1200:]}, 400)

        film = f"{HERE}/movies/{name}.json"
        if not os.path.exists(film):
            return self._send({"error": "compile produced no film", "detail": out[-600:]}, 500)

        log = f"/tmp/render-{name}.log"
        # setsid so it survives this request, and its own log so status can be polled
        subprocess.Popen(
            f"setsid nohup {sys.executable} {ROOT}/scripts/short.py {film} > {log} 2>&1 < /dev/null &",
            shell=True, cwd=ROOT)
        warns = [l.strip(" !") for l in out.splitlines() if l.strip().startswith("!")]
        return self._send({"ok": True, "name": name, "log": log,
                           "compile": out.strip()[-1200:], "warnings": warns})

    def _make(self, data):
        """Run one domain generation and return the artifact.

        These are SECONDS, not minutes - 3s for a voice line, 7.6s for a music cue, 4.5s
        for a still - so unlike a film render this is answered inline rather than polled.
        Values are passed as argv, never interpolated into a shell string.
        """
        dom = safe_name(data.get("domain", ""))
        if not dom or not os.path.exists(f"{HERE}/domains/{dom}.json"):
            return self._send({"error": f"unknown domain: {dom}"}, 404)
        cmd = [sys.executable, f"{HERE}/_tools/domain_gen.py", dom]
        for k, v in (data.get("set") or {}).items():
            k = "".join(c for c in str(k) if c.isalnum() or c == "_")[:40]
            if k and v not in (None, ""):
                cmd += ["--set", f"{k}={v}"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=420)
        except subprocess.TimeoutExpired:
            return self._send({"error": "generation timed out"}, 504)
        out = (r.stdout or "") + (r.stderr or "")
        # the runner appends to the manifest; the newest record for this domain is ours
        rec = None
        mp = f"{HERE}/gallery/manifest.jsonl"
        if os.path.exists(mp):
            for line in open(mp, encoding="utf-8"):
                try:
                    j = json.loads(line)
                except Exception:
                    continue
                if j.get("domain") == dom:
                    rec = j
        if rec and "1 generated" in out:
            return self._send({"ok": True, "record": rec})
        return self._send({"error": "generation failed",
                           "detail": out.strip()[-1500:]}, 500)

    def _verify(self, data):
        """Record a HUMAN verdict on a card, straight into the card's own JSON.

        Written back to studio/cards/<slug>.json rather than to a side file, so the
        verdict travels with the claim it judges and shows up in a git diff. `verified_by`
        marks it as observed rather than predicted - that distinction is the entire point,
        since every predicted verdict in this project that was later checked was wrong.
        """
        slug = safe_name(data.get("slug", ""))
        p = f"{HERE}/cards/{slug}.json"
        if not slug or not os.path.exists(p):
            return self._send({"error": f"unknown card: {slug}"}, 404)
        verdict = str(data.get("verdict", "")).strip()[:40]
        # "unsure" is a first-class answer, not a failure to answer. A reviewer who does
        # not know the term should be able to say so, and that is far more useful than a
        # guess - every predicted verdict here that was later checked was wrong.
        if verdict not in ("works", "mixed", "fails", "unsure", ""):
            return self._send({"error": "verdict must be works, mixed, fails, unsure "
                                        "or empty"}, 400)
        try:
            c = json.load(open(p, encoding="utf-8"))
        except Exception as e:
            return self._send({"error": f"unreadable card: {e}"}, 500)
        if verdict == "unsure":
            # record that a human looked and could not judge, WITHOUT claiming a verdict.
            # The card stays in the queue for someone who knows the term.
            c["seen_unsure"] = int(c.get("seen_unsure", 0)) + 1
            c.pop("verdict", None)
        elif verdict:
            c["verdict"] = verdict
            c["verified_by"] = "human"
            c["verified_at"] = __import__("time").strftime("%Y-%m-%dT%H:%M:%S")
        else:                       # clearing a verdict re-opens the card
            for k in ("verdict", "verified_by", "verified_at"):
                c.pop(k, None)
        look = str(data.get("look_at", "")).strip()[:600]
        if look:
            c["look_at"] = look
        broken = [str(x)[:60] for x in (data.get("broken_options") or [])][:40]
        if broken:
            c["broken_options"] = broken
        elif "broken_options" in c and data.get("broken_options") is not None:
            c.pop("broken_options")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(c, f, indent=2, ensure_ascii=False)
            f.write("\n")
        return self._send({"ok": True, "slug": slug, "verdict": c.get("verdict")})

    def _reroll(self, data):
        """Re-render a tag's with/without pair on a different seed.

        An example only earns its place if it DEMONSTRATES the tag. Sometimes the base
        image happens to hide the effect - the jacket is already flat, the background
        already blurred - and no amount of rewording fixes that. The fix is a different
        roll of the same comparison, not a different definition.

        Takes about 6s (two 3s renders), so it is answered inline.
        """
        tag = safe_name(data.get("tag", ""))
        if not tag or not os.path.exists(f"{HERE}/tags/{tag}.json"):
            return self._send({"error": f"unknown tag: {tag}"}, 404)
        try:
            seed = int(data.get("seed") or 0)
        except (TypeError, ValueError):
            seed = 0
        if not seed:
            # deterministic per-attempt, so a reroll is reproducible rather than random
            prev = json.load(open(f"{HERE}/tags/{tag}.json", encoding="utf-8")) \
                       .get("example_seed", 4242)
            seed = int(prev) + 1111
        # "slop" and "doesn't show the tag" are different failures. The first says the
        # comparison worked but the picture is not worth showing; recording it means a tag
        # that keeps producing weak images can be found later and given a better base,
        # rather than being rerolled forever.
        reason = str(data.get("reason", ""))[:20]
        if reason == "slop":
            try:
                tp = f"{HERE}/tags/{tag}.json"
                t = json.load(open(tp, encoding="utf-8"))
                t["slop_rerolls"] = int(t.get("slop_rerolls", 0)) + 1
                with open(tp, "w", encoding="utf-8") as f:
                    json.dump(t, f, indent=2, ensure_ascii=False)
                    f.write("\n")
            except Exception:
                pass
        cmd = [sys.executable, f"{HERE}/_tools/tag_examples.py", tag, "--seed", str(seed)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=300)
        except subprocess.TimeoutExpired:
            return self._send({"error": "reroll timed out"}, 504)
        out = (r.stdout or "") + (r.stderr or "")
        if "1 rendered" not in out:
            return self._send({"error": "reroll failed", "detail": out.strip()[-1200:]}, 500)
        return self._send({"ok": True, "tag": tag, "seed": seed,
                           "example": f"/samples/tags/{tag}.webp"})

    def _workflow(self, data):
        """The exact ComfyUI graph this would submit, without submitting it.

        Built by the same code path as a real run, so it cannot drift from what actually
        executes. Useful for three things: seeing which node a setting lands on, checking
        a prompt before spending GPU, and loading the graph into ComfyUI itself to tweak
        by hand (its Load-API-format menu takes this JSON directly).
        """
        dom = safe_name(data.get("domain", ""))
        if not dom or not os.path.exists(f"{HERE}/domains/{dom}.json"):
            return self._send({"error": f"unknown domain: {dom}"}, 404)
        cmd = [sys.executable, f"{HERE}/_tools/domain_gen.py", dom, "--show"]
        for k, v in (data.get("set") or {}).items():
            k = "".join(c for c in str(k) if c.isalnum() or c == "_")[:40]
            if k and v not in (None, ""):
                cmd += ["--set", f"{k}={v}"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=90)
        except subprocess.TimeoutExpired:
            return self._send({"error": "timed out building the workflow"}, 504)
        try:
            # the runner prints warnings before the JSON, so take from the first brace
            txt = r.stdout[r.stdout.index("{"):]
            return self._send(json.loads(txt))
        except Exception:
            return self._send({"error": "could not build the workflow",
                               "detail": ((r.stdout or "") + (r.stderr or ""))[-1200:]}, 500)

    def _render_status(self, name):
        name = safe_name(name)
        log = f"/tmp/render-{name}.log"
        if not os.path.exists(log):
            return self._send({"state": "none"})
        txt = open(log, encoding="utf-8", errors="replace").read()
        stage, done, total = "starting", 0, 0
        for line in txt.splitlines():
            s = line.strip()
            if s.startswith("=== "):
                stage = s.strip("= ").split(":")[0].lower()
            m = re.search(r"\((\d+)/(\d+)\)", s)
            if m:
                done, total = int(m.group(1)), int(m.group(2))
            m = re.search(r"clips (\d+)/(\d+)", s)
            if m:
                done, total = int(m.group(1)), int(m.group(2))
        final = None
        for line in txt.splitlines():
            if line.strip().startswith(">>>"):
                final = line.strip()[3:].strip()
        state = "done" if final else ("failed" if "Traceback" in txt else "running")
        return self._send({
            "state": state, "stage": stage, "done": done, "total": total,
            "final": final,
            # the video is under ComfyUI's output, not ours, so expose a play URL
            "play": f"/render/{name}.mp4" if final else None,
            "tail": "\n".join(txt.splitlines()[-24:]),
        })

    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        if p not in ("/api/save", "/api/render", "/api/make", "/api/workflow",
                     "/api/verify", "/api/tag/reroll"):
            return self._send({"error": "not found"}, 404)
        n = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            return self._send({"error": f"bad json: {e}"}, 400)
        if p == "/api/render":
            try:
                return self._render_start(data)
            except subprocess.TimeoutExpired:
                return self._send({"error": "compile timed out"}, 504)
        if p == "/api/make":
            return self._make(data)
        if p == "/api/workflow":
            return self._workflow(data)
        if p == "/api/verify":
            return self._verify(data)
        if p == "/api/tag/reroll":
            return self._reroll(data)
        name = "".join(c for c in str(data.get("name", "")) if c.isalnum() or c in "-_")
        if not name:
            return self._send({"error": "name required"}, 400)
        os.makedirs(f"{HERE}/movies", exist_ok=True)
        p = f"{HERE}/movies/{name}.movie"
        open(p, "w", encoding="utf-8").write(data.get("text", ""))
        return self._send({"ok": True, "path": p})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    lib = library()
    print(f"studio  http://localhost:{PORT}"
          + (f"   (also http://{socket.gethostbyname(socket.gethostname())}:{PORT})"
             if BIND == "0.0.0.0" else ""))
    print(f"  {sum(len(v) for v in lib.values())} presets in {len(lib)} groups, "
          f"{len(variables())} variables")
    # Refuse to start if something is already listening. On Windows SO_REUSEADDR lets a
    # SECOND process bind the same port instead of erroring, and the OS then round-robins
    # between them - so a stale server keeps serving old code and edits appear to do
    # nothing at random. Check first, and leave reuse off.
    probe = socket.socket()
    probe.settimeout(0.4)
    if probe.connect_ex(("127.0.0.1", PORT)) == 0:
        probe.close()
        raise SystemExit(
            f"something is already serving on {PORT}.\n"
            f"  stop it first, or run with a different port:  STUDIO_PORT=8778 python3 studio/serve.py")
    probe.close()
    # THREADED. The card page pulls one JSON plus dozens of panel images; on a
    # single-threaded TCPServer those serialise behind each other and the page appears
    # to hang.
    #
    # SO_REUSEADDR is platform-dependent and the difference matters here. On WINDOWS it
    # genuinely lets a second process bind a live port, which is the bug the probe above
    # was written for - three servers once bound 8777 at once and the OS round-robined
    # between them, so a stale one served old code at random. On LINUX it does no such
    # thing (that needs SO_REUSEPORT); it only permits rebinding a socket sitting in
    # TIME_WAIT, which is exactly what you want when restarting a dev server. Refusing it
    # on Linux just means every restart fails for ~60s. The probe is the real guard.
    class Studio(socketserver.ThreadingTCPServer):
        daemon_threads = True
        allow_reuse_address = (os.name == "posix")

    with Studio((BIND, PORT), H) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")
