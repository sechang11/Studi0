#!/usr/bin/env python3
"""Render docs/METHOD.md to studio/samples/docs/METHOD.pdf, figures and all.

The PDF has no content of its own: it IS docs/METHOD.md, so the two cannot drift. Figures are
placed by a `@figure <path> | <caption>` line in the markdown and are built by
`studio/samples/docs/figures/` (see build_figures.py). Run this after any edit to METHOD.md.

    ~/.pdfvenv/bin/python studio/_tools/build_method_pdf.py
"""
import os
import re
import sys

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

ROOT = os.path.expanduser("~/shared/comfy-studio")
DOC = os.path.join(ROOT, "docs", "METHOD.md")
OUTDIR = os.path.join(ROOT, "studio", "samples", "docs")
OUT = os.path.join(OUTDIR, "METHOD.pdf")

F = "/usr/share/fonts"
for name, path in [
    ("Serif", "%s/liberation-serif-fonts/LiberationSerif-Regular.ttf" % F),
    ("Serif-B", "%s/liberation-serif-fonts/LiberationSerif-Bold.ttf" % F),
    ("Serif-I", "%s/liberation-serif-fonts/LiberationSerif-Italic.ttf" % F),
    ("Serif-BI", "%s/liberation-serif-fonts/LiberationSerif-BoldItalic.ttf" % F),
    ("Sans-B", "%s/liberation-sans-fonts/LiberationSans-Bold.ttf" % F),
    ("Sans", "%s/liberation-sans-fonts/LiberationSans-Regular.ttf" % F),
    ("Mono", "%s/liberation-mono-fonts/LiberationMono-Regular.ttf" % F),
]:
    pdfmetrics.registerFont(TTFont(name, path))
pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="Serif-B",
                              italic="Serif-I", boldItalic="Serif-BI")

INK = colors.HexColor("#1a1a1a")
MUTED = colors.HexColor("#5a5a5a")
RULE = colors.HexColor("#c8c2b4")
ACCENT = colors.HexColor("#7a5c1e")

S = {
    "title": ParagraphStyle("title", fontName="Sans-B", fontSize=23, leading=28,
                            textColor=INK, spaceAfter=4),
    "lede": ParagraphStyle("lede", fontName="Serif-I", fontSize=10, leading=14.5,
                           textColor=MUTED, spaceAfter=10),
    "h2": ParagraphStyle("h2", fontName="Sans-B", fontSize=13.5, leading=17,
                         textColor=ACCENT, spaceBefore=15, spaceAfter=6),
    "body": ParagraphStyle("body", fontName="Serif", fontSize=10.2, leading=14.6,
                           textColor=INK, spaceAfter=7, alignment=TA_JUSTIFY),
    "li": ParagraphStyle("li", fontName="Serif", fontSize=10.2, leading=14.3,
                         textColor=INK, spaceAfter=4, leftIndent=13, bulletIndent=3),
    "cap": ParagraphStyle("cap", fontName="Serif-I", fontSize=8.7, leading=11.8,
                          textColor=MUTED, spaceBefore=3, spaceAfter=11),
    "th": ParagraphStyle("th", fontName="Sans-B", fontSize=9.2, leading=12, textColor=INK),
    "td": ParagraphStyle("td", fontName="Serif", fontSize=9.7, leading=12.5, textColor=INK),
}

PW, PH = A4
MARGIN = 19 * mm
BOTTOM = 21 * mm
CW = PW - 2 * MARGIN
FRAME_H = PH - MARGIN - BOTTOM
MAX_FIG_H = FRAME_H * 0.70


def inline(t):
    """markdown inline -> reportlab markup"""
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"`([^`]+)`", r'<font face="Mono" size="9">\1</font>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", t)
    return t.replace("--", "–")


def figure(spec):
    """`<path> | <caption>` -> [Image, caption]"""
    path, _, cap = spec.partition("|")
    p = os.path.join(ROOT, "studio", "samples", "docs", path.strip())
    if not os.path.exists(p):
        print("  !! missing figure %s" % p)
        return []
    iw, ih = PILImage.open(p).size
    w = CW
    h = ih * w / iw
    # A figure never takes more than this, so its caption always fits on the same page and a
    # paragraph or two of text can still share the page with it.
    if h > MAX_FIG_H:
        h = MAX_FIG_H
        w = iw * h / ih
    im = Image(p, width=w, height=h)
    im.hAlign = "CENTER"
    out = [im]
    if cap.strip():
        out.append(Paragraph(inline(cap.strip()), S["cap"]))
    return [KeepTogether(out)]


def table(rows):
    head = [Paragraph(inline(c), S["th"]) for c in rows[0]]
    body = [[Paragraph(inline(c), S["td"]) for c in r] for r in rows[1:]]
    t = Table([head] + body, colWidths=[CW * 0.42, CW * 0.28], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.9, RULE),
        ("LINEBELOW", (0, 1), (-1, -2), 0.35, colors.HexColor("#e6e2d8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
    ]))
    return [t, Spacer(1, 9)]


def parse(md):
    story = []
    lines = md.split("\n")
    i = 0
    para = []

    def flush():
        if para:
            story.append(Paragraph(inline(" ".join(para).strip()), S["body"]))
            para.clear()

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()

        if not s:
            flush()
            i += 1
            continue

        if s.startswith("@figure "):
            flush()
            # a caption may wrap over as many lines as it likes; it ends at the blank line
            spec = [s[8:]]
            i += 1
            while i < len(lines) and lines[i].strip():
                spec.append(lines[i].strip())
                i += 1
            story.extend(figure(" ".join(spec)))
            continue

        if s.startswith("# "):
            flush()
            story.append(Paragraph(inline(s[2:]), S["title"]))
            i += 1
            continue

        if s.startswith("## "):
            flush()
            story.append(Paragraph(inline(s[3:]), S["h2"]))
            i += 1
            continue

        if s == "---":
            flush()
            story.append(Spacer(1, 5))
            i += 1
            continue

        if s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") for c in cells):
                    rows.append(cells)
                i += 1
            story.extend(table(rows))
            continue

        m = re.match(r"^(\d+)\.\s+(.*)", s)
        if m or s.startswith("- "):
            flush()
            # gather one item, including its continuation lines
            if m:
                bullet, text = m.group(1) + ".", m.group(2)
            else:
                bullet, text = "•", s[2:]
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if not nxt.strip() or nxt.strip().startswith(("- ", "|", "#", "@")) \
                        or re.match(r"^\d+\.\s", nxt.strip()) or not nxt.startswith(" "):
                    break
                text += " " + nxt.strip()
                i += 1
            story.append(Paragraph(inline(text), S["li"], bulletText=bullet))
            continue

        para.append(s)
        i += 1

    flush()
    return story


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Sans", 7.6)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 11 * mm, "The Method · comfy-studio")
    canvas.drawRightString(PW - MARGIN, 11 * mm, "page %d" % doc.page)
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, 14.5 * mm, PW - MARGIN, 14.5 * mm)
    canvas.restoreState()


def main():
    md = open(DOC, encoding="utf-8").read()
    doc = BaseDocTemplate(OUT, pagesize=A4, title="The Method - comfy-studio",
                          author="comfy-studio", subject="building a story and a shot",
                          leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=MARGIN, bottomMargin=BOTTOM)
    frame = Frame(MARGIN, BOTTOM, CW, FRAME_H, id="f",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=footer)])
    story = parse(md)
    n = len(story)
    doc.build(story)
    print("wrote %s" % OUT)
    print("  %d bytes, %d flowables, %d figures"
          % (os.path.getsize(OUT), n, md.count("@figure ")))


if __name__ == "__main__":
    sys.exit(main())
