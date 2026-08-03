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
import http.server, json, os, socket, socketserver, urllib.parse

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
          "weather", "emotions", "soundscapes", "pacing", "places", "characters", "cues"]


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
        if path == "/api/library":
            return self._send(library())
        if path == "/api/cards":
            return self._send(cards())
        if path == "/api/variables":
            return self._send(variables())
        if path == "/api/movies":
            return self._send(movies())
        return self._send({"error": "not found"}, 404)

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != "/api/save":
            return self._send({"error": "not found"}, 404)
        n = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            return self._send({"error": f"bad json: {e}"}, 400)
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
