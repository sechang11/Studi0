#!/usr/bin/env python3
"""studio/_tools/build_site.py - the three feeds as a static site.

Reads what agency.py made (a hero portrait and ten posts each, plus the identity scores if
--score has run) and writes a self-contained folder: index.html, one page per person, the
images copied in at web size. No build step, no CDN, no fonts fetched - it opens from the
filesystem.

    python3 studio/_tools/build_site.py --out ~/agency_site
"""
import argparse
import importlib.util
import json
import os
import shutil

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "studio", "samples", "agency")


def load_people():
    spec = importlib.util.spec_from_file_location(
        "agency", os.path.join(ROOT, "studio", "_tools", "agency.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.PEOPLE


CSS = """
:root{
  --paper:#f6f4f0; --ink:#171614; --ink2:#575350; --muted:#8e8984;
  --line:#e0dcd5; --accent:#8a5a3b; --card:#fffefc;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --paper:#141312; --ink:#f2efe9; --ink2:#b5afa7; --muted:#837d76;
    --line:#2a2825; --accent:#d3a07a; --card:#1b1a18;
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font:16px/1.65 "Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  -webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
.wrap{max-width:1140px;margin:0 auto;padding:0 28px}
header.top{padding:54px 0 30px;border-bottom:1px solid var(--line);margin-bottom:54px}
.mark{font:600 12px/1 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  letter-spacing:.22em;text-transform:uppercase;color:var(--accent)}
h1{font-size:clamp(34px,6vw,58px);line-height:1.04;margin:16px 0 14px;letter-spacing:-.02em;
  font-weight:500;text-wrap:balance}
.sub{color:var(--ink2);max-width:60ch;margin:0;font-size:17px}
.roster{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:34px;
  padding-bottom:70px}
.card{background:var(--card);border:1px solid var(--line);overflow:hidden;
  transition:transform .35s cubic-bezier(.2,.7,.3,1), box-shadow .35s}
.card:hover{transform:translateY(-4px);box-shadow:0 18px 40px -22px rgba(0,0,0,.45)}
.card img{width:100%;aspect-ratio:4/5;object-fit:cover;display:block;filter:saturate(.98)}
.card .meta{padding:20px 22px 24px}
.card h2{margin:0 0 4px;font-size:21px;font-weight:500;letter-spacing:-.01em}
.handle{font:500 12px/1 ui-sans-serif,system-ui,sans-serif;letter-spacing:.1em;
  color:var(--accent);text-transform:lowercase}
.card p{margin:10px 0 0;color:var(--ink2);font-size:14.5px;line-height:1.55}
.profile{display:flex;gap:30px;align-items:flex-end;padding-bottom:40px;flex-wrap:wrap}
.profile img{width:148px;height:148px;border-radius:50%;object-fit:cover;flex:none;
  border:1px solid var(--line)}
.profile .who h1{margin:0 0 6px;font-size:clamp(28px,5vw,44px)}
.stats{display:flex;gap:26px;margin-top:14px;
  font:500 13px/1 ui-sans-serif,system-ui,sans-serif;color:var(--ink2)}
.stats b{display:block;font-size:17px;color:var(--ink);margin-bottom:3px;
  font-variant-numeric:tabular-nums}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:4px;
  padding-bottom:16px}
.tile{position:relative;display:block;background:var(--line)}
.tile img{width:100%;aspect-ratio:4/5;object-fit:cover;display:block}
.tile figcaption{position:absolute;inset:auto 0 0 0;padding:34px 14px 13px;color:#fff;
  font:400 13.5px/1.45 ui-sans-serif,system-ui,sans-serif;opacity:0;transition:opacity .3s;
  background:linear-gradient(transparent,rgba(0,0,0,.74))}
.tile:hover figcaption{opacity:1}
.back{display:inline-block;margin-bottom:26px;font:500 12px/1 ui-sans-serif,system-ui,sans-serif;
  letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.back:hover{color:var(--accent)}
footer{border-top:1px solid var(--line);margin-top:60px;padding:30px 0 70px;color:var(--muted);
  font:400 13px/1.6 ui-sans-serif,system-ui,sans-serif}
footer b{color:var(--ink2);font-weight:600}
@media (max-width:620px){.grid{grid-template-columns:repeat(2,1fr)}.wrap{padding:0 16px}}
"""


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def page(title, body):
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>%s</title><style>%s</style></head><body>%s</body></html>"
            % (esc(title), CSS, body))


def web_copy(src, dest, w):
    im = Image.open(src).convert("RGB")
    if im.size[0] > w:
        im = im.resize((w, round(im.size[1] * w / im.size[0])), Image.LANCZOS)
    im.save(dest, quality=90, subsampling=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.expanduser("~/agency_site"))
    a = ap.parse_args()
    people = load_people()
    img_dir = os.path.join(a.out, "img")
    os.makedirs(img_dir, exist_ok=True)

    ident = {}
    ip = os.path.join(SRC, "identity.json")
    if os.path.exists(ip):
        for r in json.load(open(ip)):
            ident[(r["who"], r["post"])] = r["identity"]

    cards = []
    for slug, p in people.items():
        d = os.path.join(SRC, slug)
        hero = os.path.join(d, "hero.png")
        if not os.path.exists(hero):
            continue
        web_copy(hero, os.path.join(img_dir, "%s_hero.jpg" % slug), 860)
        posts = sorted(f for f in os.listdir(d) if f.startswith("post_") and f.endswith(".png"))
        caps = {k: c for k, c, _ in p["posts"]}

        tiles = []
        for f in posts:
            key = f[8:-4]
            out = "%s_%s.jpg" % (slug, key)
            web_copy(os.path.join(d, f), os.path.join(img_dir, out), 900)
            cap = caps.get(key, "")
            tiles.append('<figure class="tile"><img src="img/%s" alt="%s" loading="lazy">'
                         '<figcaption>%s</figcaption></figure>'
                         % (out, esc(p["name"]), esc(cap)))

        scores = [ident[(slug, f)] for f in posts if (slug, f) in ident]
        held = ("%.2f" % (sum(scores) / len(scores))) if scores else "&mdash;"
        body = (
            '<div class="wrap"><a class="back" href="index.html">&larr; roster</a>'
            '<section class="profile"><img src="img/%s_hero.jpg" alt="%s">'
            '<div class="who"><h1>%s</h1><span class="handle">@%s</span>'
            '<p class="sub">%s</p>'
            '<div class="stats"><div><b>%d</b>posts</div><div><b>%s</b>face held</div>'
            '<div><b>1</b>reference portrait</div></div></div></section>'
            '<div class="grid">%s</div>%s</div>'
            % (slug, esc(p["name"]), esc(p["name"]), esc(p["handle"]), esc(p["bio"]),
               len(posts), held, "".join(tiles), FOOT))
        open(os.path.join(a.out, "%s.html" % slug), "w", encoding="utf-8").write(
            page("%s (@%s)" % (p["name"], p["handle"]), body))

        cards.append('<a class="card" href="%s.html"><img src="img/%s_hero.jpg" alt="%s">'
                     '<div class="meta"><h2>%s</h2><span class="handle">@%s</span>'
                     '<p>%s</p></div></a>'
                     % (slug, slug, esc(p["name"]), esc(p["name"]), esc(p["handle"]),
                        esc(p["bio"])))

    idx = ('<div class="wrap"><header class="top"><div class="mark">Agency</div>'
           '<h1>Three people who do not exist.</h1>'
           '<p class="sub">Each face was generated once, then carried into every photograph '
           'that follows by handing the engine that portrait rather than a description of it. '
           'One reference picture per person; thirty photographs; no retouching pass.</p>'
           '<p class="sub" style="margin-top:18px"><a href="casting.html" style="border-bottom:1px solid var(--accent);color:var(--accent)">See the casting call &rarr;</a> &mdash; twenty more faces, six frames each, one of them gets the account. <a href="faces.html" style="border-bottom:1px solid var(--accent);color:var(--accent)">Or browse the face library &rarr;</a></p>'
           '</header><section class="roster">%s</section>%s</div>' % ("".join(cards), FOOT))
    open(os.path.join(a.out, "index.html"), "w", encoding="utf-8").write(page("Agency", idx))
    n = len(os.listdir(img_dir))
    print("site -> %s  (%d pages, %d images)" % (a.out, len(cards) + 1, n))


FOOT = ('<footer><div class="wrap" style="padding:0">'
        '<b>These people are synthetic.</b> Rhea, Naia and Elin are invented characters '
        'generated on one desktop machine. They are not real people, no real person was used '
        'as a reference, and nothing here is a photograph of anyone. Made with comfy-studio: '
        'Flux&nbsp;2 for the portraits, the same model&rsquo;s reference conditioning to carry '
        'each face from one picture into the next.</div></footer>')

if __name__ == "__main__":
    main()
