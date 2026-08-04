#!/usr/bin/env python3
"""Freeze a live studio page into one standalone HTML file that renders anywhere.

    python3 studio/_tools/page_snapshot.py /            -> /tmp/snap_home.html
    python3 studio/_tools/page_snapshot.py /styles --out /tmp/s.html
    python3 studio/_tools/page_snapshot.py /wizard --extra /api/movies

WHY THIS EXISTS. Nobody on this project has ever LOOKED at most of these pages. Four
separate agents tried and failed: this box has no Xvfb and Firefox headless dies with
"RenderCompositorSWGL failed mapping default framebuffer", so --screenshot produces
nothing. Meanwhile a page opened straight from disk is blank, because every page draws
itself from fetch("/api/...") and a file:// origin has no server to answer.

So: fetch the page, fetch the API responses it depends on, and inline them as a fetch
STUB injected into <head>. The page's own code is not modified at all - it still calls
fetch("/api/styles") and still runs its real render path - it just gets served from a
frozen dictionary instead of the network. The result is a single file that shows the real
layout with real data and can be opened anywhere, including a browser pane that has no
route to the box.

WHAT THIS DOES AND DOES NOT PROVE. It proves the page's markup, CSS and render logic
produce what you see - layout, spacing, colour, whether a filter row wraps, whether a
status flag is legible. It does NOT prove anything that needs a live server: POSTs,
rendering, the wizard's compose round-trip, or any interaction that mutates state. Those
still need a real browser against the running app. The snapshot says so in its own banner
so a screenshot of it is never mistaken for a working app.

Images: the page's <img src="/samples/..."> paths are rewritten to absolute URLs against
the live server, so a snapshot opened on a machine that CAN reach the box shows real
pictures, and one opened elsewhere shows the layout with broken thumbnails rather than
failing to load at all.
"""
import argparse, json, os, re, sys, urllib.request

DEFAULT_HOST = os.environ.get("STUDIO_HOST", "127.0.0.1:8777")

# Which API calls each page makes. A page that asks for something not listed here simply
# gets a 404 from the stub, which is the same thing it would get from a server missing
# that route - so the snapshot degrades exactly like the real page does.
PAGE_APIS = {
    "/":        ["/api/styles", "/api/loras", "/api/cast", "/api/library",
                 "/api/gallery", "/api/domains", "/api/video", "/api/verify/queue"],
    "/styles":  ["/api/styles", "/api/library"],
    "/loras":   ["/api/loras", "/api/styles"],
    "/cast":    ["/api/cast", "/api/library"],
    "/gallery": ["/api/gallery", "/api/domains"],
    "/make":    ["/api/domains", "/api/library", "/api/variables"],
    "/tags":    ["/api/tags", "/api/library"],
    "/verify":  ["/api/verify/queue", "/api/library"],
    "/video":   ["/api/video", "/api/library"],
    "/wizard":  ["/api/library", "/api/styles", "/api/loras", "/api/cast",
                 "/api/templates", "/api/movies", "/api/domains"],
}

BANNER = """<div style="position:fixed;left:0;right:0;bottom:0;z-index:99999;
 background:#e0b252;color:#1a1205;font:600 11.5px/1.5 ui-monospace,Menlo,monospace;
 padding:6px 12px;text-align:center;letter-spacing:.04em">
 FROZEN SNAPSHOT &mdash; %s from %s. Layout and data are real; nothing here is live.
 Buttons that would POST, render or save do nothing.</div>"""


def get(host, path, timeout=25):
    url = "http://%s%s" % (host, path)
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace"), r.status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("page", nargs="?", default="/")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--out")
    ap.add_argument("--extra", action="append", default=[],
                    help="additional /api/... path to freeze")
    ap.add_argument("--trim", type=int, default=400,
                    help="cap list responses at N items so the file stays openable")
    a = ap.parse_args()

    page = a.page if a.page.startswith("/") else "/" + a.page
    html, status = get(a.host, page)
    if status != 200:
        raise SystemExit("page %s returned HTTP %s" % (page, status))

    apis = list(dict.fromkeys(PAGE_APIS.get(page, []) + a.extra))
    frozen, notes = {}, []
    for p in apis:
        try:
            body, st = get(a.host, p)
            if st != 200:
                notes.append("%s -> HTTP %s (stub will 404, as the live page sees)" % (p, st))
                continue
            data = json.loads(body)
        except Exception as e:
            notes.append("%s -> %s (stub will 404)" % (p, str(e)[:60]))
            continue
        # Trim long lists. The point is to see the layout, and a 1828-entry gallery makes
        # a file too large to open while showing nothing the first 400 do not.
        if isinstance(data, list) and len(data) > a.trim:
            notes.append("%s trimmed %d -> %d" % (p, len(data), a.trim))
            data = data[:a.trim]
        elif isinstance(data, dict):
            for k, v in list(data.items()):
                if isinstance(v, list) and len(v) > a.trim:
                    notes.append("%s.%s trimmed %d -> %d" % (p, k, len(v), a.trim))
                    data[k] = v[:a.trim]
        frozen[p] = data
        notes.append("%s frozen" % p)

    stub = """<script>
/* Injected by page_snapshot.py. The page's own code is untouched; it still calls
   fetch("/api/..."), but the network is replaced by this frozen dictionary. Anything not
   frozen returns 404, which is exactly what the live page would get from a missing route. */
(function(){
  var SNAP = %s;
  var origin = "http://%s";
  window.fetch = function(u, opts){
    var k = String(u && u.url ? u.url : u).replace(origin, "");
    if ((opts && opts.method && opts.method.toUpperCase() !== "GET")) {
      return Promise.resolve({ok:false, status:405, json:function(){return Promise.resolve(
        {error:"frozen snapshot - no live server"});}, text:function(){return Promise.resolve("");}});
    }
    if (Object.prototype.hasOwnProperty.call(SNAP, k)) {
      return Promise.resolve({ok:true, status:200,
        json:function(){ return Promise.resolve(JSON.parse(JSON.stringify(SNAP[k]))); },
        text:function(){ return Promise.resolve(JSON.stringify(SNAP[k])); }});
    }
    return Promise.resolve({ok:false, status:404,
      json:function(){ return Promise.reject(new Error("404 " + k)); },
      text:function(){ return Promise.resolve(""); }});
  };
})();
</script>""" % (json.dumps(frozen), a.host)

    if "</head>" in html:
        html = html.replace("</head>", stub + "\n</head>", 1)
    else:
        html = stub + html

    # Point relative asset paths at the live server so thumbnails resolve for anyone who
    # can reach it. Only src/href starting with a single slash, and never /api (the stub
    # owns those) and never a page route.
    html = re.sub(r'(\s(?:src|href)=")(/(?!/)(?:samples|static|assets|thumbs)[^"]*)"',
                  lambda m: '%shttp://%s%s"' % (m.group(1), a.host, m.group(2)), html)

    html = html.replace("</body>", (BANNER % (page, a.host)) + "\n</body>", 1)

    out = a.out or ("/tmp/snap_%s.html" % (page.strip("/").replace("/", "_") or "home"))
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    print("%s  (%.0f KB)" % (out, os.path.getsize(out) / 1024.0))
    for n in notes:
        print("  %s" % n)
    if not frozen:
        print("  ! nothing was frozen - the page will render as if every API were down")


if __name__ == "__main__":
    main()
