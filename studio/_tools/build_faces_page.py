#!/usr/bin/env python3
"""studio/_tools/build_faces_page.py - the face library as a filterable picker.

Reads studio/foundry/faces/faces.json and writes faces.html into the site: every portrait as a
tile, with the attributes that made it as filter chips along the top. Filtering is done in the
page against data- attributes, so there is no server, no build step and no dependency; it opens
from the filesystem.

Clicking a face shows the command that casts it, because the useful end of a picker is getting
the chosen face into the pipeline rather than admiring it.

    python3 studio/_tools/build_faces_page.py --out ~/agency_delivery/site
"""
import argparse
import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "studio", "foundry", "faces")

FACETS = [("tier", "Tier"), ("heritage", "Heritage"), ("tone", "Skin"),
          ("hair_colour", "Hair"), ("hair_texture", "Texture"),
          ("hair_length", "Length"), ("age", "Age"), ("feature", "Feature")]

EXTRA = """
.bar{position:sticky;top:0;z-index:5;background:var(--paper);border-bottom:1px solid var(--line);
  padding:14px 0 12px;margin-bottom:20px}
.facet{display:flex;gap:7px;align-items:baseline;flex-wrap:wrap;margin-bottom:7px}
.facet>b{font:600 10px/1.6 ui-sans-serif,system-ui,sans-serif;letter-spacing:.16em;
  text-transform:uppercase;color:var(--muted);width:74px;flex:none}
.chip{font:500 12px/1 ui-sans-serif,system-ui,sans-serif;padding:5px 9px;border:1px solid var(--line);
  cursor:pointer;color:var(--ink2);background:none;border-radius:2px}
.chip:hover{border-color:var(--accent);color:var(--accent)}
.chip.on{background:var(--accent);border-color:var(--accent);color:#fff}
.count{font:500 12px/1 ui-sans-serif,system-ui,sans-serif;color:var(--muted);margin-left:auto}
.fgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));gap:6px;
  padding-bottom:40px}
.f{position:relative;cursor:pointer;background:var(--line)}
.f img{width:100%;aspect-ratio:4/5;object-fit:cover;display:block}
.f span{position:absolute;left:0;right:0;bottom:0;padding:20px 7px 5px;color:#fff;
  font:500 10px/1.3 ui-sans-serif,system-ui,sans-serif;
  background:linear-gradient(transparent,rgba(0,0,0,.72));opacity:0;transition:opacity .2s}
.f:hover span{opacity:1}
.f.hide{display:none}
#pick{position:fixed;inset:auto 0 0 0;background:var(--card);border-top:1px solid var(--accent);
  padding:16px 28px;display:none;z-index:9}
#pick code{font:500 12.5px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--ink);
  background:var(--paper);padding:3px 7px;display:inline-block}
#pick b{font-size:15px}
#pick .x{float:right;cursor:pointer;color:var(--muted);font-size:20px;line-height:1}
"""

JS = """
const chips=[...document.querySelectorAll('.chip')],tiles=[...document.querySelectorAll('.f')];
const on={};
function apply(){
  let n=0;
  tiles.forEach(t=>{
    const ok=Object.entries(on).every(([k,v])=>!v.size||v.has(t.dataset[k]));
    t.classList.toggle('hide',!ok); if(ok)n++;
  });
  document.getElementById('count').textContent=n+' of '+tiles.length;
}
chips.forEach(c=>c.onclick=()=>{
  const k=c.dataset.k,v=c.dataset.v;
  on[k]=on[k]||new Set();
  on[k].has(v)?on[k].delete(v):on[k].add(v);
  c.classList.toggle('on'); apply();
});
tiles.forEach(t=>t.onclick=()=>{
  const p=document.getElementById('pick');
  p.style.display='block';
  p.innerHTML='<span class="x" onclick="document.getElementById(\\'pick\\').style.display=\\'none\\'">&times;</span>'+
    '<b>'+t.dataset.id+'</b> &mdash; '+t.dataset.summary+'<br><br>cast it:<br>'+
    '<code>python3 studio/_tools/faces.py --cast '+t.dataset.id+' --name "NAME" --slug slug</code>'+
    '<br><br><code>python3 studio/_tools/agency.py --posts --who slug</code>';
});
const t=chips.find(c=>c.dataset.k==='tier'&&c.dataset.v==='beauty');
if(t)t.click(); else apply();
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.expanduser("~/agency_delivery/site"))
    a = ap.parse_args()
    site_mod = importlib.util.spec_from_file_location(
        "build_site", os.path.join(ROOT, "studio", "_tools", "build_site.py"))
    site = importlib.util.module_from_spec(site_mod)
    site_mod.loader.exec_module(site)

    idx = os.path.join(SRC, "faces.json")
    rows = json.load(open(idx)) if os.path.exists(idx) else []
    img_dir = os.path.join(a.out, "img", "faces")
    os.makedirs(img_dir, exist_ok=True)

    tiles, vals = [], {k: set() for k, _ in FACETS}
    for r in rows:
        src = os.path.join(SRC, r["id"], "portrait.png")
        if not os.path.exists(src):
            continue
        out = "%s.jpg" % r["id"]
        site.web_copy(src, os.path.join(img_dir, out), 420)
        r.setdefault("tier", "casting")
        for k, _ in FACETS:
            vals[k].add(r.get(k, ""))
        summary = ", ".join(str(r.get(k, "")).replace("-", " ") for k, _ in FACETS)
        data = " ".join('data-%s="%s"' % (k.replace("_", "-"), site.esc(r.get(k, "")))
                        for k, _ in FACETS)
        # dataset keys are camelCased from data-hair-colour -> hairColour; the JS uses those
        tiles.append('<figure class="f" %s data-id="%s" data-summary="%s">'
                     '<img src="img/faces/%s" alt="%s" loading="lazy">'
                     '<span>%s &middot; %s</span></figure>'
                     % (data, r["id"], site.esc(summary), out, r["id"],
                        r["id"], site.esc(str(r.get("feature", "")).replace("-", " "))))

    bar = []
    for k, label in FACETS:
        chips = "".join('<button class="chip" data-k="%s" data-v="%s">%s</button>'
                        % (_camel(k), site.esc(v), site.esc(str(v).replace("-", " ")))
                        for v in sorted(x for x in vals[k] if x))
        bar.append('<div class="facet"><b>%s</b>%s</div>' % (label, chips))

    body = ('<div class="wrap"><a class="back" href="index.html">&larr; roster</a>'
            '<header class="top"><div class="mark">Face library</div>'
            '<h1>Pick a face.</h1>'
            '<p class="sub">%d invented faces, each shot as the same neutral card in the same '
            'window light so they compare fairly. Two tiers: <b>beauty</b> is lit and styled the way a beauty campaign is, <b>casting</b> is the flat neutral card you judge a face on. None is a real person and none is a '
            'downloaded likeness: every one was grown here from typed attributes, which is also '
            'what the filters above are. Click one to cast it.</p></header>'
            '<div class="bar">%s<div class="facet"><b></b><span class="count" id="count"></span>'
            '</div></div><div class="fgrid">%s</div><div id="pick"></div>%s</div>'
            '<script>%s</script>'
            % (len(tiles), "".join(bar), "".join(tiles), site.FOOT, JS))
    html = site.page("Face library", body).replace("</style>", EXTRA + "</style>")
    open(os.path.join(a.out, "faces.html"), "w", encoding="utf-8").write(html)
    print("faces.html -> %s  (%d faces, %d facets)" % (a.out, len(tiles), len(FACETS)))


def _camel(k):
    bits = k.split("_")
    return bits[0] + "".join(b.capitalize() for b in bits[1:])


if __name__ == "__main__":
    main()
