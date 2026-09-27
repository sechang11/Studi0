#!/usr/bin/env python3
"""studio/_tools/refsheet.py - a REFERENCE SHEET from a cast and a place, for the Ingredients adapter.

The LTX IC-LoRA "Ingredients" adapter (workflow 82) is conditioned on one composite picture: a
clean panel per visual element - a character's face, the same character's whole figure, a prop,
the place - on a black background with no text. Its model card's one rule about layout is that
the more of the sheet an element takes up, the more faithfully it carries into the video; so
faces get the biggest panels and the place gets the whole bottom row.

    python3 studio/_tools/refsheet.py --out sheet.png \
        --char ref_vesper.png --char ref_koval.png --place ref_court.png [--prop x.png]
        [--canvas 1280x704] [--margin 12]

Layout, top to bottom: one row of character panels (face crop, then whole figure, per character),
then one row holding the place plate(s) and any props. The face crop is found with headbox.py's
head box (the same instrument identity.py scores with), widened by 40% so hair and jaw are in.
Writes the sheet and a sidecar JSON naming each panel's box, so a prompt can be written from the
same numbers ("top row, first two panels: Character A").
"""
import argparse
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _face_crop(path, pad=0.4):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    try:
        import headbox
        box = headbox.head_box(path)          # fractional x0,y0,x1,y1
    except Exception:
        box = None
    if not box:
        box = [0.3, 0.02, 0.7, 0.3]           # a portrait's head, roughly, when the finder fails
    x0, y0, x1, y1 = box
    bw, bh = (x1 - x0), (y1 - y0)
    side = max(bw * w, bh * h) * (1 + pad)
    cx, cy = (x0 + x1) / 2 * w, (y0 + y1) / 2 * h
    left, top = max(0, cx - side / 2), max(0, cy - side / 2)
    right, bottom = min(w, left + side), min(h, top + side)
    return im.crop((int(left), int(top), int(right), int(bottom))), box


def _fit(im, cw, ch):
    """Contain `im` in cw x ch, returning the pasted-size image and its offset."""
    r = min(cw / im.width, ch / im.height)
    nw, nh = max(1, int(im.width * r)), max(1, int(im.height * r))
    return im.resize((nw, nh), Image.LANCZOS), ((cw - nw) // 2, (ch - nh) // 2)


def build(chars, places, props, out, canvas=(1280, 704), margin=12, bg=(238, 238, 238), detail=True):
    """bg: the gutter colour. The model card says black; Lightricks' own example sheet (the
    template's german_shepherd_news_anchor_ref.png) uses white gutters and grey studio panels,
    and on 2026-09-27 a black-gutter sheet turned the whole generated room black while the
    people carried perfectly - so the default is the example's light grey. `detail` adds a
    centre crop of the plate as a second location panel, so the place fills its row."""
    W, H = canvas
    sheet = Image.new("RGB", (W, H), bg)
    panels = []
    top_h = int(H * 0.5) if (places or props) else H
    # top row: for each character, a face panel and a figure panel
    cells = []
    for i, p in enumerate(chars):
        face, box = _face_crop(p)
        cells.append(("face", chr(65 + i), face, {"source": p, "head_box": box}))
        cells.append(("figure", chr(65 + i), Image.open(p).convert("RGB"), {"source": p}))
    if cells:
        cw = (W - margin * (len(cells) + 1)) // len(cells)
        ch = top_h - 2 * margin
        for j, (kind, who, im, meta) in enumerate(cells):
            x = margin + j * (cw + margin)
            fitted, (ox, oy) = _fit(im, cw, ch)
            sheet.paste(fitted, (x + ox, margin + oy))
            panels.append({"row": "top", "index": j, "kind": kind, "character": who,
                           "box": [x + ox, margin + oy, x + ox + fitted.width, margin + oy + fitted.height],
                           **meta})
    # bottom row: places (each with a centre-detail companion so the place fills the row), then props
    bottom = []
    for p in places:
        im = Image.open(p).convert("RGB")
        bottom.append(("place", p, im))
        if detail:
            w, h = im.size
            bottom.append(("place_detail", p, im.crop((w // 4, h // 6, w - w // 4, h - h // 6))))
    for p in props:
        bottom.append(("prop", p, Image.open(p).convert("RGB")))
    if bottom:
        y0 = top_h
        ch = H - y0 - margin
        cw = (W - margin * (len(bottom) + 1)) // len(bottom)
        for j, (kind, p, im) in enumerate(bottom):
            x = margin + j * (cw + margin)
            fitted, (ox, oy) = _fit(im, cw, ch)
            sheet.paste(fitted, (x + ox, y0 + oy))
            panels.append({"row": "bottom", "index": j, "kind": kind, "source": p,
                           "box": [x + ox, y0 + oy, x + ox + fitted.width, y0 + oy + fitted.height]})
    sheet.save(out)
    json.dump({"canvas": [W, H], "panels": panels}, open(os.path.splitext(out)[0] + ".json", "w"),
              indent=1)
    return panels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--char", action="append", default=[], help="a character's full-length reference")
    ap.add_argument("--place", action="append", default=[], help="a place plate")
    ap.add_argument("--prop", action="append", default=[])
    ap.add_argument("--canvas", default="1280x704")
    ap.add_argument("--margin", type=int, default=12)
    ap.add_argument("--bg", default="grey", choices=["grey", "black", "white"],
                    help="gutter colour; grey is the example sheet's, black is the model card's")
    ap.add_argument("--no-detail", action="store_true", help="no centre-crop companion for the plate")
    a = ap.parse_args()
    W, H = (int(x) for x in a.canvas.lower().split("x"))
    bg = {"grey": (238, 238, 238), "black": (0, 0, 0), "white": (255, 255, 255)}[a.bg]
    panels = build(a.char, a.place, a.prop, a.out, (W, H), a.margin, bg=bg, detail=not a.no_detail)
    for p in panels:
        print("%-6s %-7s %s %s" % (p["row"], p["kind"], p.get("character", ""), p["box"]))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
