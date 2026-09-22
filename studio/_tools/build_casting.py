#!/usr/bin/env python3
"""studio/_tools/build_casting.py - the casting call as a page in the same site.

One row per character: the six comp-card frames, the name and city, the one-line hook, and a
link to the 4K card. Reuses build_site.py's stylesheet so the section does not look bolted on.

    python3 studio/_tools/build_casting.py --out ~/agency_delivery/site
"""
import argparse
import importlib.util
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "studio", "samples", "casting")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


EXTRA = """
.cast{border-top:1px solid var(--line);padding:30px 0 34px}
.cast:first-of-type{border-top:none}
.cast .hd{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin-bottom:14px}
.cast h2{margin:0;font-size:23px;font-weight:500;letter-spacing:-.01em}
.cast .city{font:500 11px/1 ui-sans-serif,system-ui,sans-serif;letter-spacing:.16em;
  text-transform:uppercase;color:var(--accent)}
.cast .hook{color:var(--ink2);font-style:italic;font-size:15px}
.cast .k4{margin-left:auto;font:500 11px/1 ui-sans-serif,system-ui,sans-serif;
  letter-spacing:.12em;text-transform:uppercase;color:var(--muted);
  border:1px solid var(--line);padding:7px 11px}
.cast .k4:hover{color:var(--accent);border-color:var(--accent)}
.strip{display:grid;grid-template-columns:repeat(6,1fr);gap:4px}
.strip img{width:100%;aspect-ratio:4/5;object-fit:cover;display:block;background:var(--line)}
.strip figure{margin:0;position:relative}
.strip figcaption{position:absolute;left:0;bottom:0;right:0;padding:16px 8px 6px;color:#fff;
  font:500 10px/1 ui-sans-serif,system-ui,sans-serif;letter-spacing:.1em;text-transform:uppercase;
  background:linear-gradient(transparent,rgba(0,0,0,.66));opacity:0;transition:opacity .25s}
.strip figure:hover figcaption{opacity:1}
@media (max-width:900px){.strip{grid-template-columns:repeat(3,1fr)}}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.expanduser("~/agency_delivery/site"))
    a = ap.parse_args()
    site = load("build_site", os.path.join(ROOT, "studio", "_tools", "build_site.py"))
    cast = load("casting", os.path.join(ROOT, "studio", "_tools", "casting.py"))
    img_dir = os.path.join(a.out, "img")
    os.makedirs(img_dir, exist_ok=True)

    order = [k for k, _, _ in cast.SHOTS] if False else [s[0] for s in cast.SHOTS]
    rows, n_img, n_4k = [], 0, 0
    for i, (slug, name, city, hook, _look) in enumerate(cast.PEOPLE):
        d = os.path.join(SRC, slug)
        if not os.path.isdir(d):
            continue
        tiles = []
        for j, key in enumerate(order):
            src = os.path.join(d, "%d_%s.png" % (j + 1, key))
            if not os.path.exists(src):
                continue
            out = "cast_%s_%s.jpg" % (slug, key)
            site.web_copy(src, os.path.join(img_dir, out), 760)
            n_img += 1
            tiles.append('<figure><img src="img/%s" alt="%s" loading="lazy">'
                         '<figcaption>%s</figcaption></figure>'
                         % (out, site.esc(name), site.esc(key)))
        if not tiles:
            continue
        k4 = os.path.join(d, "1_card_4k.png")
        link = ""
        if os.path.exists(k4):
            out4 = "cast_%s_4k.jpg" % slug
            im = Image.open(k4).convert("RGB")
            im.save(os.path.join(img_dir, out4), quality=92, subsampling=1)
            n_4k += 1
            link = ('<a class="k4" href="img/%s">4K card &middot; %d&times;%d</a>'
                    % (out4, im.size[0], im.size[1]))
        rows.append('<section class="cast"><div class="hd"><h2>%02d. %s</h2>'
                    '<span class="city">%s</span><span class="hook">%s</span>%s</div>'
                    '<div class="strip">%s</div></section>'
                    % (i + 1, site.esc(name), site.esc(city), site.esc(hook), link,
                       "".join(tiles)))

    body = ('<div class="wrap"><a class="back" href="index.html">&larr; roster</a>'
            '<header class="top"><div class="mark">Casting call</div>'
            '<h1>Twenty faces, six frames each.</h1>'
            '<p class="sub">Open submissions for the next signing. Every card is a neutral '
            'headshot in window light, shot the way a casting director asks for it, then five '
            'more frames carried from that one picture. One of the twenty gets the account.</p>'
            '</header>%s%s</div>' % ("".join(rows), site.FOOT))
    open(os.path.join(a.out, "casting.html"), "w", encoding="utf-8").write(
        site.page("Casting call", body).replace("</style>", EXTRA + "</style>"))
    print("casting.html -> %s  (%d characters, %d frames, %d at 4K)"
          % (a.out, len(rows), n_img, n_4k))


if __name__ == "__main__":
    main()
