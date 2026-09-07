#!/usr/bin/env python3
"""Render pages of the book PDF to contact sheets, so the layout can be LOOKED at.

The in-app browser downloads PDFs rather than showing them, and there is no poppler on the box;
pypdfium2 in the PDF venv rasterises.  Six pages to a sheet, page numbers on each.

    ~/.pdfvenv/bin/python studio/_tools/book_preview.py                 # first 18 pages, 3 sheets
    ~/.pdfvenv/bin/python studio/_tools/book_preview.py 1 2 3 8 12 20   # these pages, one sheet
    ~/.pdfvenv/bin/python studio/_tools/book_preview.py --all           # every page, many sheets
"""
import os
import sys

import pypdfium2 as pdfium
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PDF = os.path.join(ROOT, "studio", "samples", "docs", "METHOD.pdf")
OUT = "/tmp/bookprev"


def sheet(pdf, pages, out, cols=3, scale=1.3):
    n = len(pdf)
    ims = []
    for p in pages:
        if 1 <= p <= n:
            ims.append((p, pdf[p - 1].render(scale=scale).to_pil().convert("RGB")))
    if not ims:
        return None
    w, h = ims[0][1].size
    rows = (len(ims) + cols - 1) // cols
    S = Image.new("RGB", (w * cols + (cols + 1) * 10, (h + 22) * rows + 10), (40, 38, 36))
    d = ImageDraw.Draw(S)
    for i, (p, im) in enumerate(ims):
        x = 10 + (i % cols) * (w + 10)
        y = 10 + (i // cols) * (h + 22)
        S.paste(im, (x, y + 18))
        d.text((x + 4, y + 2), "page %d" % p, fill=(230, 225, 215))
    S.save(out, quality=82)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    pdf = pdfium.PdfDocument(PDF)
    n = len(pdf)
    print("pages", n)
    args = [a for a in sys.argv[1:]]
    if args and args[0] == "--all":
        pages = list(range(1, n + 1))
    elif args:
        pages = [int(a) for a in args]
    else:
        pages = list(range(1, min(n, 18) + 1))
    k = 0
    for i in range(0, len(pages), 6):
        k += 1
        out = os.path.join(OUT, "sheet%d.jpg" % k)
        if sheet(pdf, pages[i:i + 6], out):
            print("->", out, pages[i:i + 6])


if __name__ == "__main__":
    main()
