#!/usr/bin/env python3
"""
gallery.py - build a browsable contact sheet of everything generated.

Walks ~/ComfyUI/output/claude-generated/ and writes gallery.html into that same
folder, so every "open full size" link is a simple relative path that works from
Windows over the Z: share with no server and no path rewriting.

    python3 scripts/gallery.py                     # rebuild
    python3 scripts/gallery.py --max-per-folder 40
    python3 scripts/gallery.py --thumb 520

Thumbnails are JPEG, base64-inlined, so the single .html file is portable - mail
it, copy it to a stick, it still renders. Full-resolution originals and video and
audio files stay as relative links, because inlining those would be absurd.

Video thumbnails need ffmpeg on PATH; without it videos still appear as links.
Requires PIL, so run it with ComfyUI's interpreter:

    ~/ComfyUI/venv/bin/python scripts/gallery.py
"""
import argparse
import base64
import html
import io
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.expanduser("~/ComfyUI/output/claude-generated")
IMG = {".png", ".jpg", ".jpeg", ".webp"}
VID = {".mp4", ".webm", ".mkv"}
AUD = {".mp3", ".wav", ".flac", ".ogg"}
SKIP_DIRS = {"_work"}

try:
    from PIL import Image
except ImportError:
    sys.exit("PIL not found. Run with ~/ComfyUI/venv/bin/python")


def thumb_b64(path, width):
    """Downscale to `width` and return a base64 JPEG, or None."""
    try:
        im = Image.open(path)
        if im.mode in ("RGBA", "LA", "P"):
            # flatten onto mid grey so alpha cutouts read as cutouts
            im = im.convert("RGBA")
            bg = Image.new("RGBA", im.size, (128, 128, 128, 255))
            im = Image.alpha_composite(bg, im)
        im = im.convert("RGB")
        if im.width > width:
            im = im.resize((width, max(1, round(im.height * width / im.width))),
                           Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=80, optimize=True)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        print(f"  ! thumb failed {os.path.basename(path)}: {e}", file=sys.stderr)
        return None


def video_thumb_b64(path, width):
    if not shutil_which("ffmpeg"):
        return None
    tmp = os.path.join(tempfile.gettempdir(), "_gal_frame.jpg")
    try:
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", "1", "-i", path,
             "-frames:v", "1", tmp],
            check=True, timeout=60,
        )
        return thumb_b64(tmp, width)
    except Exception:
        return None
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def shutil_which(name):
    from shutil import which
    return which(name)


def sidecar(path):
    txt = os.path.splitext(path)[0] + ".txt"
    if not os.path.exists(txt):
        return None
    try:
        with open(txt, encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return None


CARD = "_capability_card.png"


def capability(folder):
    """Read CAPABILITY.json - the folder's own statement of what it demonstrates.

    This is what makes the gallery self-explaining rather than a wall of pictures:
    a sample only demonstrates something if the claim travels with it.
    """
    p = os.path.join(folder, "CAPABILITY.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        print(f"  ! bad CAPABILITY.json in {folder}: {e}", file=sys.stderr)
        return None


def folder_blurb(folder):
    """Title + first prose paragraph from the folder's README.md."""
    rd = os.path.join(folder, "README.md")
    if not os.path.exists(rd):
        return None, None
    title = desc = None
    try:
        with open(rd, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return None, None
    for ln in lines:
        s = ln.strip()
        if not title and s.startswith("# "):
            title = s[2:].strip()
            continue
        if title and s and not s.startswith(("#", "|", "-", ">", "*", "`", "[")):
            desc = s
            break
    return title, desc


def pretty(name):
    s = re.sub(r"_\d{5}_?$", "", os.path.splitext(name)[0])
    s = re.sub(r"^\d+_", "", s)
    return s.replace("_", " ").replace("-", " ").strip() or name


def collect(root, max_per_folder):
    groups = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        rel = os.path.relpath(dirpath, root)
        if rel == ".":
            continue
        media = []
        for fn in sorted(filenames):
            ext = os.path.splitext(fn)[1].lower()
            kind = ("image" if ext in IMG else
                    "video" if ext in VID else
                    "audio" if ext in AUD else None)
            if kind:
                media.append((kind, fn))
        if not media:
            continue
        shown, dropped = media[:max_per_folder], max(0, len(media) - max_per_folder)
        groups.append({
            "rel": rel.replace(os.sep, "/"),
            "dir": dirpath,
            "media": shown,
            "dropped": dropped,
            "total": len(media),
        })
    groups.sort(key=lambda g: g["rel"])
    return groups


CSS = """
*{box-sizing:border-box}
:root{--bg:#faf9f7;--fg:#1a1a19;--dim:#6b6b68;--card:#fff;--line:#e3e1dd;--accent:#7a5cff}
@media (prefers-color-scheme:dark){:root{--bg:#131314;--fg:#eceae6;--dim:#9a9a96;--card:#1c1c1e;--line:#2e2e31;--accent:#a693ff}}
:root[data-theme=dark]{--bg:#131314;--fg:#eceae6;--dim:#9a9a96;--card:#1c1c1e;--line:#2e2e31;--accent:#a693ff}
:root[data-theme=light]{--bg:#faf9f7;--fg:#1a1a19;--dim:#6b6b68;--card:#fff;--line:#e3e1dd;--accent:#7a5cff}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1500px;margin:0 auto;padding:32px 20px 80px}
h1{font-size:1.7rem;margin:0 0 4px;letter-spacing:-.02em}
.sub{color:var(--dim);margin:0 0 26px}
nav{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:34px;
 padding-bottom:22px;border-bottom:1px solid var(--line)}
nav a{font-size:.82rem;text-decoration:none;color:var(--fg);background:var(--card);
 border:1px solid var(--line);border-radius:99px;padding:5px 12px}
nav a:hover{border-color:var(--accent);color:var(--accent)}
section{margin:0 0 52px;scroll-margin-top:16px}
h2{font-size:1.12rem;margin:0 0 3px;letter-spacing:-.01em}
h2 .n{color:var(--dim);font-weight:400;font-size:.85rem;margin-left:8px}
.blurb{color:var(--dim);font-size:.9rem;margin:0 0 16px;max-width:78ch}
.claim{font-size:1rem;margin:6px 0 8px;max-width:92ch;line-height:1.5}
.lookat{font-size:.9rem;margin:0 0 8px;max-width:92ch;color:var(--accent)}
.meta{font-size:.78rem;color:var(--dim);margin:0 0 14px;font-family:ui-monospace,monospace}
.verdict{display:inline-block;font-size:.68rem;font-weight:700;letter-spacing:.06em;
 border-radius:5px;padding:2px 8px;color:#fff;margin-bottom:8px}
.verdict.works{background:#22783e}.verdict.mixed{background:#966914}.verdict.failed{background:#963232}
img.card{width:100%;display:block;border:1px solid var(--line);border-radius:11px;
 margin:0 0 20px;cursor:zoom-in}
.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(290px,1fr))}
figure{margin:0;background:var(--card);border:1px solid var(--line);border-radius:11px;
 overflow:hidden;display:flex;flex-direction:column}
figure img{width:100%;display:block;background:#808080;cursor:zoom-in}
figcaption{padding:9px 11px;font-size:.78rem;border-top:1px solid var(--line)}
.nm{font-weight:600;word-break:break-word}
.badge{display:inline-block;font-size:.66rem;text-transform:uppercase;letter-spacing:.05em;
 color:var(--dim);border:1px solid var(--line);border-radius:4px;padding:1px 5px;margin-left:6px}
audio{width:100%;margin-top:7px}
details{margin-top:7px}
summary{cursor:pointer;color:var(--accent);font-size:.75rem}
pre{white-space:pre-wrap;word-break:break-word;font-size:.72rem;color:var(--dim);
 margin:6px 0 0;max-height:190px;overflow:auto}
a.dl{color:var(--dim);text-decoration:none;font-size:.72rem}
a.dl:hover{color:var(--accent)}
.more{color:var(--dim);font-size:.82rem;margin-top:12px}
#lb{position:fixed;inset:0;background:rgba(0,0,0,.93);display:none;
 align-items:center;justify-content:center;z-index:99;cursor:zoom-out;padding:22px}
#lb.on{display:flex}
#lb img{max-width:100%;max-height:100%;object-fit:contain}
.toggle{position:fixed;top:12px;right:14px;z-index:100;background:var(--card);
 color:var(--fg);border:1px solid var(--line);border-radius:99px;
 padding:6px 13px;font-size:.78rem;cursor:pointer}
"""

JS = """
var lb=document.getElementById('lb'),lbi=lb.querySelector('img');
document.addEventListener('click',function(e){
  var t=e.target;
  if(t.tagName==='IMG'&&t.dataset.full){lbi.src=t.dataset.full;lb.classList.add('on');}
  else if(lb.classList.contains('on')){lb.classList.remove('on');lbi.src='';}
});
document.addEventListener('keydown',function(e){
  if(e.key==='Escape'){lb.classList.remove('on');lbi.src='';}
});
document.querySelector('.toggle').addEventListener('click',function(){
  var r=document.documentElement;
  var cur=r.dataset.theme||(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light');
  r.dataset.theme=cur==='dark'?'light':'dark';
});
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=ROOT)
    p.add_argument("--out", default=None, help="default: <root>/gallery.html")
    p.add_argument("--thumb", type=int, default=460, help="thumbnail width px")
    p.add_argument("--max-per-folder", type=int, default=30)
    a = p.parse_args()

    root = os.path.expanduser(a.root)
    out = a.out or os.path.join(root, "gallery.html")
    if not os.path.isdir(root):
        sys.exit(f"no such folder: {root}")

    groups = collect(root, a.max_per_folder)
    if not groups:
        sys.exit(f"no media found under {root}")

    n_media = sum(len(g["media"]) for g in groups)
    print(f"{len(groups)} folder(s), {n_media} item(s) to thumbnail", file=sys.stderr)

    parts = [
        '<title>Comfy Studio — sample gallery</title>',
        f"<style>{CSS}</style>",
        '<button class="toggle">light / dark</button>',
        '<div id="lb"><img alt=""></div>',
        '<div class="wrap">',
        "<h1>Comfy Studio — sample gallery</h1>",
        f'<p class="sub">Everything generated on the RTX 5090, {len(groups)} categories. '
        "Click any image for full size. Prompts are under “details”.</p>",
        "<nav>",
    ]
    for g in groups:
        title, _ = folder_blurb(g["dir"])
        parts.append(f'<a href="#{html.escape(g["rel"])}">'
                     f'{html.escape(title or g["rel"])}</a>')
    parts.append("</nav>")

    for g in groups:
        title, desc = folder_blurb(g["dir"])
        cap = capability(g["dir"])
        parts.append(f'<section id="{html.escape(g["rel"])}">')
        parts.append(f'<h2>{html.escape((cap or {}).get("title") or title or g["rel"])}'
                     f'<span class="n">{g["total"]} files · {html.escape(g["rel"])}</span></h2>')

        if cap:
            v = cap.get("verdict")
            if v in ("works", "mixed", "failed"):
                lbl = {"works": "WORKS", "mixed": "PARTIAL", "failed": "FAILED — kept on purpose"}[v]
                parts.append(f'<span class="verdict {html.escape(v)}">{lbl}</span>')
            if cap.get("claim"):
                parts.append(f'<p class="claim">{html.escape(cap["claim"])}</p>')
            if cap.get("look_at"):
                parts.append(f'<p class="lookat"><b>Look at:</b> {html.escape(cap["look_at"])}</p>')
            meta = " · ".join(x for x in [cap.get("model"), cap.get("cost"),
                                          cap.get("workflow")] if x)
            if meta:
                parts.append(f'<p class="meta">{html.escape(meta)}</p>')
            # the card IS the demonstration - show it full width, before the file grid
            card = os.path.join(g["dir"], CARD)
            if os.path.exists(card):
                b = thumb_b64(card, 1400)
                if b:
                    href = html.escape(f'{g["rel"]}/{CARD}')
                    parts.append(f'<img class="card" alt="capability card" '
                                 f'data-full="{href}" src="data:image/jpeg;base64,{b}">')
        elif desc:
            parts.append(f'<p class="blurb">{html.escape(desc)}</p>')

        parts.append('<div class="grid">')

        for kind, fn in g["media"]:
            if fn == CARD:
                continue  # already shown above at full width
            full = os.path.join(g["dir"], fn)
            href = html.escape(f'{g["rel"]}/{fn}')
            label = html.escape(pretty(fn))
            parts.append("<figure>")

            if kind == "image":
                b = thumb_b64(full, a.thumb)
                if b:
                    parts.append(f'<img loading="lazy" alt="{label}" '
                                 f'data-full="{href}" src="data:image/jpeg;base64,{b}">')
            elif kind == "video":
                b = video_thumb_b64(full, a.thumb)
                if b:
                    parts.append(f'<a href="{href}"><img loading="lazy" alt="{label}" '
                                 f'src="data:image/jpeg;base64,{b}"></a>')

            parts.append(f'<figcaption><div class="nm">{label}'
                         f'<span class="badge">{kind}</span></div>')
            if kind == "audio":
                parts.append(f'<audio controls preload="none" src="{href}"></audio>')
            parts.append(f'<div><a class="dl" href="{href}">open original ↗</a></div>')

            sc = sidecar(full)
            if sc:
                parts.append("<details><summary>prompt / settings</summary>"
                             f"<pre>{html.escape(sc)}</pre></details>")
            parts.append("</figcaption></figure>")

        parts.append("</div>")
        if g["dropped"]:
            parts.append(f'<p class="more">+ {g["dropped"]} more file(s) in this folder — '
                         f'raise --max-per-folder to include them.</p>')
        parts.append("</section>")

    parts.append("</div>")
    parts.append(f"<script>{JS}</script>")

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))

    size = os.path.getsize(out) / 2 ** 20
    print(f"wrote {out} ({size:.1f} MB)", file=sys.stderr)


if __name__ == "__main__":
    main()
