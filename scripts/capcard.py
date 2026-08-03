#!/usr/bin/env python3
"""
capcard.py - render a folder's CAPABILITY.json into a self-explaining info card.

The problem: a folder of PNGs does not carry its own claim. Looking at
`flux2_beekeeper_00001_.png` you see a photograph, not a capability - you cannot tell
what model made it, when that model arrived, what it is good and bad at, what else
you could have used, or what the practical ceiling is on this GPU.

So each folder declares all of that in CAPABILITY.json and this renders
`_capability_card.png`: claim and "look at this" up top, labelled panels in the
middle, and a six-block info grid underneath covering model provenance, real limits
on this box, alternatives, strengths, weaknesses and next steps. Leading underscore
sorts it first in any listing.

    ~/ComfyUI/venv/bin/python scripts/capcard.py                     # all declared folders
    ~/ComfyUI/venv/bin/python scripts/capcard.py 24-outpaint-removal
    ~/ComfyUI/venv/bin/python scripts/capcard.py --list              # coverage audit

Schema - only `title` is required; every block is omitted if absent:

    {
      "title":    "...",                       "claim": "...",
      "look_at":  "...",                       "verdict": "works|mixed|failed|planned",
      "status":   "verified|installed-untested|not-installed",
      "updated":  "2026-07-31",                 // stamped into the header
      "model":    "Qwen-Image 2512",            "released": "2025-12-31",
      "vram":     "29.6 GB",                    "cost": "4.5 s",
      "workflow": "01_qwen_t2i_turbo.json",
      "limits":   ["...", "..."],               // practical ceilings on THIS gpu
      "strong":   ["...'],  "weak": ["..."],
      "alternatives": ["..."],                  // prefix with + installed, - not installed
      "next_steps":   ["..."],                  // for unexplored folders
      "panels": [ {"file": "x.png", "label": "...", "note": "...",
                   "crop": [cx, cy, frac],      // 1:1 crop - for upscalers
                   "frames": 6} ]               // video strip - for motion
    }

`file` may be `../other-folder/x.png`, or `-` for an empty slot.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap

ROOT = os.path.expanduser("~/ComfyUI/output/claude-generated")
CARD = "_capability_card.png"

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("PIL not found. Run with ~/ComfyUI/venv/bin/python")

FONT_DIRS = ["/usr/share/fonts/liberation-sans-fonts",
             "/usr/share/fonts/google-droid-sans-fonts",
             "/usr/share/fonts/abattis-cantarell-fonts"]
VERDICT = {"works": ((34, 120, 62), "WORKS"),
           "mixed": ((150, 105, 20), "PARTIAL"),
           "failed": ((150, 45, 45), "FAILED - kept on purpose"),
           "planned": ((60, 70, 95), "NOT YET EXPLORED")}

PANEL_H, PANEL_W, PAD = 560, 620, 22
BG, FG, DIM, ACC = (18, 18, 20), (238, 236, 232), (150, 150, 156), (126, 176, 255)


def font(size, bold=False):
    for d in FONT_DIRS:
        for n in (["LiberationSans-Bold.ttf", "DroidSans-Bold.ttf", "Cantarell-Bold.otf"]
                  if bold else
                  ["LiberationSans-Regular.ttf", "DroidSans.ttf", "Cantarell-Regular.otf"]):
            p = os.path.join(d, n)
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except OSError:
                    pass
    return ImageFont.load_default()


def crop_region(im, spec):
    """spec = [cx, cy, frac] as fractions. Same WORLD region from every panel, so an
    upscale yields proportionally more pixels and that becomes visible detail."""
    cx, cy, frac = (list(spec) + [0.5, 0.5, 0.25])[:3]
    w, h = max(8, int(im.width * frac)), max(8, int(im.height * frac))
    x0 = max(0, min(im.width - w, int(im.width * cx - w / 2)))
    y0 = max(0, min(im.height - h, int(im.height * cy - h / 2)))
    return im.crop((x0, y0, x0 + w, y0 + h))


def video_strip(path, n, h):
    """Tile n evenly-spaced frames. Motion cannot be shown in a still; a strip at
    least proves the frames are distinct content rather than duplicates."""
    if not os.path.exists(path):
        return None
    d = tempfile.mkdtemp(prefix="capstrip_")
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vf",
                        f"thumbnail,fps=1/1,scale=-1:{h}", "-frames:v", str(n),
                        os.path.join(d, "f_%02d.png")], check=True, timeout=120)
        fs = sorted(f for f in os.listdir(d) if f.endswith(".png"))[:n]
        if not fs:
            return None
        ims = [Image.open(os.path.join(d, f)).convert("RGB") for f in fs]
        gap = 4
        strip = Image.new("RGB", (sum(i.width for i in ims) + gap * (len(ims) - 1),
                                  max(i.height for i in ims)), BG)
        x = 0
        for i in ims:
            strip.paste(i, (x, 0)); x += i.width + gap
        return strip
    except Exception as e:
        print(f"    ! strip {os.path.basename(path)}: {e}", file=sys.stderr)
        return None
    finally:
        shutil.rmtree(d, ignore_errors=True)


def fit(path, h, max_w, crop=None):
    """Scale to EXACTLY h tall, natural width. Equal height not equal box: a wider
    output must look wider or the layout contradicts the claim."""
    blank = Image.new("RGB", (int(h * 1.4), h), (40, 40, 46))
    if not path or not os.path.exists(path):
        return blank
    try:
        im = Image.open(path)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            im = Image.alpha_composite(Image.new("RGBA", im.size, (128,) * 3 + (255,)), im)
        im = im.convert("RGB")
    except Exception as e:
        print(f"    ! {os.path.basename(path)}: {e}", file=sys.stderr)
        return blank
    if crop:
        im = crop_region(im, crop)
    w = max(1, round(im.width * h / im.height))
    if w > max_w:
        h = max(1, round(h * max_w / w)); w = max_w
    return im.resize((w, h), Image.LANCZOS)


def wrap(draw, text, f, width):
    out = []
    for para in str(text).split("\n"):
        line = ""
        for word in para.split():
            t = (line + " " + word).strip()
            if draw.textlength(t, font=f) <= width:
                line = t
            else:
                if line:
                    out.append(line)
                line = word
        out.append(line)
    return out


def block_lines(draw, heading, items, f_h, f_b, w):
    """Measure one info block: heading + bulleted items. Returns list of (text, font, colour)."""
    if not items:
        return []
    rows = [(heading, f_h, DIM)]
    for it in items:
        col = FG
        s = str(it)
        if s.startswith("+ "):
            col, s = (120, 200, 140), s[2:]
        elif s.startswith("- "):
            col, s = (170, 130, 130), s[2:]
        for j, ln in enumerate(wrap(draw, s, f_b, w - 16)):
            rows.append((("• " if j == 0 else "   ") + ln, f_b, col))
    rows.append(("", f_b, FG))
    return rows


def build(folder):
    spec = json.load(open(os.path.join(folder, "CAPABILITY.json"), encoding="utf-8"))
    panels = (spec.get("panels") or [])[:4]

    imgs = []
    for p in panels:
        src = p.get("file")
        if p.get("frames") and src not in (None, "-"):
            imgs.append(video_strip(os.path.join(folder, src), int(p["frames"]),
                                    PANEL_H // 2) or fit(None, PANEL_H, PANEL_W))
        else:
            imgs.append(fit(None if src in (None, "-") else os.path.join(folder, src),
                            PANEL_H, PANEL_W * 2, crop=p.get("crop")))

    f_t, f_c, f_m, f_l = font(34, True), font(22), font(19), font(19, True)
    f_bh, f_bb = font(16, True), font(17)

    width = max(PAD + sum(im.width + PAD for im in imgs), 1500) if imgs else 1500
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    # reserve the top-right corner so the verdict badge and updated-stamp never
    # collide with wrapped claim text
    tw = width - 2 * PAD - 300

    claim = wrap(probe, spec.get("claim", ""), f_c, tw) if spec.get("claim") else []
    look = wrap(probe, "Look at:  " + spec["look_at"], f_m, tw) if spec.get("look_at") else []
    # panel row is only as tall as the tallest panel - a short video strip should not
    # reserve full-image height and leave a dead gap
    row_h = max((im.height for im in imgs), default=0)

    # six info blocks in three columns
    colw = (width - 4 * PAD) // 3
    mdl = []
    if spec.get("model"):
        mdl.append(spec["model"])
    if spec.get("released"):
        mdl.append("released " + spec["released"])
    if spec.get("vram"):
        mdl.append(spec["vram"] + " VRAM needed")
    if spec.get("cost"):
        mdl.append(spec["cost"])
    if spec.get("workflow"):
        mdl.append(spec["workflow"])
    blocks = [("THE MODEL", mdl), ("REAL LIMITS ON THIS 5090", spec.get("limits")),
              ("ALTERNATIVES", spec.get("alternatives")), ("STRONG AT", spec.get("strong")),
              ("WEAK AT", spec.get("weak")), ("NEXT STEPS", spec.get("next_steps"))]
    rendered = [block_lines(probe, h, it, f_bh, f_bb, colw) for h, it in blocks]
    rowh = [max((len(rendered[i]) for i in (r * 3, r * 3 + 1, r * 3 + 2)), default=0) * 21
            for r in (0, 1)]

    head = PAD + 42 + 6 + len(claim) * 30 + (8 + len(look) * 26 if look else 0) + 14
    label_h = (8 + 22 * (2 if any(p.get("note") for p in panels) else 1)) if panels else 0
    panel_h = row_h if panels else 0
    info_h = (sum(rowh) + PAD) if any(rowh) else 0
    height = head + panel_h + label_h + info_h + PAD

    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)

    y = PAD
    d.text((PAD, y), spec.get("title", os.path.basename(folder)), font=f_t, fill=FG)
    y += 42 + 6
    for ln in claim:
        d.text((PAD, y), ln, font=f_c, fill=(206, 204, 200)); y += 30
    if look:
        y += 8
        for ln in look:
            d.text((PAD, y), ln, font=f_m, fill=ACC); y += 26

    # verdict badge + updated stamp, top right
    v = spec.get("verdict")
    if v in VERDICT:
        col, lab = VERDICT[v]
        w0 = d.textlength(lab, font=f_l)
        x0 = width - PAD - w0 - 24
        d.rounded_rectangle([x0, PAD + 2, width - PAD, PAD + 36], 8, fill=col)
        d.text((x0 + 12, PAD + 9), lab, font=f_l, fill=(255, 255, 255))
        if spec.get("updated"):
            s = "updated " + spec["updated"]
            d.text((width - PAD - d.textlength(s, font=f_bb), PAD + 44), s,
                   font=f_bb, fill=DIM)

    py = head
    x = PAD
    for p, pim in zip(panels, imgs):
        top = py + (row_h - pim.height) // 2
        img.paste(pim, (x, top))
        d.rectangle([x, top, x + pim.width - 1, top + pim.height - 1], outline=(70, 70, 76))
        lines = textwrap.wrap(p.get("label", ""), max(18, pim.width // 11))[:1]
        if p.get("note"):
            lines += textwrap.wrap(p["note"], max(18, pim.width // 10))[:1]
        for j, ln in enumerate(lines):
            d.text((x, py + row_h + 8 + j * 22), ln, font=f_l if j == 0 else f_m,
                   fill=FG if j == 0 else DIM)
        x += pim.width + PAD

    iy = head + panel_h + label_h + (PAD if any(rowh) else 0)
    for r in (0, 1):
        for c in range(3):
            rows = rendered[r * 3 + c]
            yy = iy
            for text, fnt, col in rows:
                d.text((PAD + c * (colw + PAD), yy), text, font=fnt, fill=col)
                yy += 21
        iy += rowh[r]

    out = os.path.join(folder, CARD)
    img.save(out, "PNG", optimize=True)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("folders", nargs="*")
    p.add_argument("--root", default=ROOT)
    p.add_argument("--list", action="store_true")
    a = p.parse_args()
    root = os.path.expanduser(a.root)

    if a.list:
        for n in sorted(os.listdir(root)):
            d = os.path.join(root, n)
            if not os.path.isdir(d):
                continue
            sp = os.path.join(d, "CAPABILITY.json")
            if os.path.exists(sp):
                try:
                    s = json.load(open(sp, encoding="utf-8"))
                    print(f"  ok   {n:<28} {s.get('status','?'):<20} updated {s.get('updated','?')}")
                except ValueError:
                    print(f"  BAD  {n}")
            else:
                print(f"  --   {n}")
        return

    made = 0
    for n in (a.folders or sorted(os.listdir(root))):
        d = os.path.join(root, n)
        if not os.path.isdir(d) or not os.path.exists(os.path.join(d, "CAPABILITY.json")):
            continue
        try:
            if build(d):
                made += 1
                print(f"  {n}/{CARD}")
        except Exception as e:
            print(f"  ! {n}: {e}", file=sys.stderr)
    print(f"\n{made} card(s) written", file=sys.stderr)


if __name__ == "__main__":
    main()
