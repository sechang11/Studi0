#!/usr/bin/env python3
"""studio/_tools/build_method_book.py - typeset docs/METHOD.md as a book.

The PDF has no content of its own: it IS docs/METHOD.md.  The markdown carries a few layout
directives on their own lines, all beginning with @, which the studio's web renderer hides and
this generator typesets:

    @title    | The Method | a subtitle | book/hero_cover.jpg      the cover
    @toc                                                          a table of contents
    @chapter  | 3 | The library | a subtitle | book/plate.jpg      full-bleed chapter opener
    @figure   path | caption | 70%                                a figure, width optional
    @wrap     left|right | path | caption                         picture with the next paragraph wrapped around it
    @row      path | path | path | caption                        two to four pictures side by side
    @box      why|try|term|note|warn | Title                      a shaded box, until @end
    @end
    @quote    text | attribution                                  a pull quote
    @pagebreak

Everything else is ordinary markdown: #, ##, ### headings, paragraphs, *italic*, **bold**, `code`,
- lists, 1. lists, | tables |.  Set in Caladea and Montserrat from the box's own fonts, 6 x 9 inch,
cream page.  Run after any edit to METHOD.md:

    ~/.pdfvenv/bin/python studio/_tools/build_method_book.py
"""
import html
import os
import re
import subprocess
import sys

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, HRFlowable, Image, KeepTogether,
                                ListFlowable, ListItem, NextPageTemplate, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.doctemplate import ActionFlowable
from reportlab.platypus.flowables import Flowable, ParagraphAndImage
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs", "METHOD.md")
OUTDIR = os.path.join(ROOT, "studio", "samples", "docs")
OUT = os.path.join(OUTDIR, "METHOD.pdf")
IMGROOT = OUTDIR                      # image paths in the markdown are relative to samples/docs

# ---- page ---------------------------------------------------------------------------------
PAGE_W, PAGE_H = 6 * inch, 9 * inch
M_OUT, M_IN, M_TOP, M_BOT = 0.58 * inch, 0.66 * inch, 0.72 * inch, 0.64 * inch
FRAME_W = PAGE_W - M_OUT - M_IN

PAPER = colors.HexColor("#FBF7EF")
INK = colors.HexColor("#1F1B17")
INK2 = colors.HexColor("#5C554D")
MUTED = colors.HexColor("#8A827A")
AMBER = colors.HexColor("#C8791B")
CEDAR = colors.HexColor("#3A5A40")
RULE = colors.HexColor("#D8D0C2")
BOX = {"why": (colors.HexColor("#F6E9D3"), AMBER, "Why this way?"),
       "try": (colors.HexColor("#E4ECDF"), CEDAR, "Exercise"),
       "term": (colors.HexColor("#EDE9E1"), MUTED, "Words to know"),
       "note": (colors.HexColor("#F3EFE6"), INK2, "Note"),
       "warn": (colors.HexColor("#F4E1DC"), colors.HexColor("#A64B35"), "Careful")}

# ---- fonts --------------------------------------------------------------------------------
def _font_path(name):
    out = subprocess.run(["fc-list"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        p = line.split(":")[0]
        if p.rsplit("/", 1)[-1].lower() in (name.lower() + ".ttf", name.lower() + ".otf"):
            return p
    return None


def _try(name, path):
    """register a TrueType font; OpenType-CFF files (Montserrat here) are refused by reportlab"""
    try:
        pdfmetrics.registerFont(TTFont(name, path))
        return True
    except Exception:
        return False


def _family(fam, candidates):
    """candidates: list of (regular, bold, italic, bolditalic) file stems, first that loads wins"""
    for r, b, i, bi in candidates:
        paths = [_font_path(n) for n in (r, b, i, bi)]
        if not all(paths):
            continue
        if not _try(fam, paths[0]):
            continue
        _try(fam + "-Bold", paths[1]); _try(fam + "-Italic", paths[2]); _try(fam + "-BoldItalic", paths[3])
        pdfmetrics.registerFontFamily(fam, normal=fam, bold=fam + "-Bold", italic=fam + "-Italic",
                                      boldItalic=fam + "-BoldItalic")
        return True
    return False


def _single(name, candidates):
    for c in candidates:
        p = _font_path(c)
        if p and _try(name, p):
            return name
    return None


# Body: Caladea, the open twin of Cambria. Display: Carlito, the open twin of Calibri, designed to
# sit beside it; Montserrat is on the box but as OpenType-CFF, which reportlab cannot embed.
HAVE_BODY = _family("Body", [("Caladea-Regular", "Caladea-Bold", "Caladea-Italic", "Caladea-BoldItalic"),
                             ("LiberationSerif-Regular", "LiberationSerif-Bold", "LiberationSerif-Italic",
                              "LiberationSerif-BoldItalic")])
HAVE_DISP = _family("Disp", [("Carlito-Regular", "Carlito-Bold", "Carlito-Italic", "Carlito-BoldItalic"),
                             ("LiberationSans-Regular", "LiberationSans-Bold", "LiberationSans-Italic",
                              "LiberationSans-BoldItalic")])
HAVE_FONTS = HAVE_BODY and HAVE_DISP
BODY = "Body" if HAVE_BODY else "Times-Roman"
BODY_B = "Body-Bold" if HAVE_BODY else "Times-Bold"
BODY_I = "Body-Italic" if HAVE_BODY else "Times-Italic"
DISP = "Disp" if HAVE_DISP else "Helvetica"
DISP_B = "Disp-Bold" if HAVE_DISP else "Helvetica-Bold"
DISP_BLACK = _single("DispBlack", ["Cantarell-ExtraBold", "Cantarell-Bold", "Montserrat-Black",
                                   "Carlito-Bold"]) or DISP_B
DISP_SB = DISP_B
MONO = _single("Mono", ["LiberationMono-Regular", "DejaVuSansMono"]) or "Courier"

S = {
    "body": ParagraphStyle("body", fontName=BODY, fontSize=10.2, leading=14.6, textColor=INK,
                           spaceAfter=7, alignment=TA_LEFT),
    "lead": ParagraphStyle("lead", fontName=BODY_I, fontSize=11.6, leading=16.5, textColor=INK2,
                           spaceAfter=10),
    "h1": ParagraphStyle("h1", fontName=DISP_B, fontSize=17, leading=21, textColor=INK, spaceBefore=14,
                         spaceAfter=8),
    "h1toc": ParagraphStyle("h1toc", fontName=DISP_B, fontSize=17, leading=21, textColor=INK,
                            spaceBefore=14, spaceAfter=10),
    "h2": ParagraphStyle("h2", fontName=DISP_SB, fontSize=12.2, leading=15.5, textColor=CEDAR,
                         spaceBefore=12, spaceAfter=5),
    "h3": ParagraphStyle("h3", fontName=DISP_SB, fontSize=10, leading=13, textColor=INK, spaceBefore=8,
                         spaceAfter=3),
    "cap": ParagraphStyle("cap", fontName=DISP, fontSize=7.9, leading=10.4, textColor=INK2, spaceAfter=8),
    "capc": ParagraphStyle("capc", fontName=DISP, fontSize=7.9, leading=10.4, textColor=INK2,
                           alignment=TA_CENTER, spaceAfter=8),
    "li": ParagraphStyle("li", fontName=BODY, fontSize=10, leading=14, textColor=INK),
    "quote": ParagraphStyle("quote", fontName=BODY_I, fontSize=12.4, leading=17, textColor=INK,
                            alignment=TA_CENTER, leftIndent=18, rightIndent=18),
    "quoteby": ParagraphStyle("quoteby", fontName=DISP, fontSize=7.8, leading=10, textColor=MUTED,
                              alignment=TA_CENTER, spaceAfter=6),
    "boxtitle": ParagraphStyle("boxtitle", fontName=DISP_B, fontSize=8.2, leading=11, textColor=INK,
                               spaceAfter=3),
    "boxbody": ParagraphStyle("boxbody", fontName=BODY, fontSize=9.4, leading=13.2, textColor=INK,
                              spaceAfter=4),
    "boxli": ParagraphStyle("boxli", fontName=BODY, fontSize=9.2, leading=12.8, textColor=INK),
    "cell": ParagraphStyle("cell", fontName=BODY, fontSize=8.4, leading=11, textColor=INK),
    "cellh": ParagraphStyle("cellh", fontName=DISP_SB, fontSize=7.6, leading=10, textColor=INK),
    "toc1": ParagraphStyle("toc1", fontName=DISP_SB, fontSize=10, leading=15, textColor=INK),
    "toc2": ParagraphStyle("toc2", fontName=BODY, fontSize=9.4, leading=13, textColor=INK2, leftIndent=14),
    "small": ParagraphStyle("small", fontName=DISP, fontSize=7.4, leading=10, textColor=MUTED),
}


def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r'<font face="%s" size="8.6" backColor="#EFE9DD">\1</font>' % MONO, t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)      # non-greedy: bold may hold an *italic* word
    t = re.sub(r"(?<![*\w])\*([^*]+)\*(?![*\w])", r"<i>\1</i>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" color="#C8791B"><u>\1</u></a>', t)
    return t


def img_path(p):
    p = p.strip()
    if p.startswith("/samples/docs/"):
        p = p[len("/samples/docs/"):]
    return p if os.path.isabs(p) else os.path.join(IMGROOT, p)


def fit_image(path, width, maxh=None):
    w, h = PILImage.open(path).size
    dw = width
    dh = dw * h / float(w)
    if maxh and dh > maxh:
        dh = maxh
        dw = dh * w / float(h)
    return Image(path, width=dw, height=dh)


# ---- special flowables -------------------------------------------------------------------
class Opener(Flowable):
    """a full-bleed chapter opener: picture, dark veil, number, title, subtitle"""

    def __init__(self, num, title, sub, image):
        Flowable.__init__(self)
        self.num, self.title, self.sub, self.image = num, title, sub, image

    def wrap(self, aw, ah):
        return (aw, ah)

    def draw(self):
        c = self.canv
        c.saveState()
        # absolute page coordinates: the frame starts at (M_IN, M_BOT) on the body template,
        # but the opener template gives us the whole page; draw from the page origin
        c.translate(-self._frame._x1 if hasattr(self, "_frame") else 0, 0)
        c.restoreState()


def opener_page(num, title, sub, image):
    """draw the opener directly on the canvas via a page callback; returns (onPage, flowables)"""
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#14110E"))
        canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
        if image and os.path.exists(image):
            w, h = PILImage.open(image).size
            # cover the page
            scale = max(PAGE_W / w, PAGE_H / h)
            dw, dh = w * scale, h * scale
            canvas.drawImage(image, (PAGE_W - dw) / 2, (PAGE_H - dh) / 2, dw, dh, mask=None)
        # a veil from the bottom so the type reads
        canvas.setFillColor(colors.HexColor("#0E0C0A"))
        canvas.setFillAlpha(0.55)
        canvas.rect(0, 0, PAGE_W, PAGE_H * 0.46, stroke=0, fill=1)
        canvas.setFillAlpha(0.25)
        canvas.rect(0, PAGE_H * 0.46, PAGE_W, PAGE_H * 0.54, stroke=0, fill=1)
        canvas.setFillAlpha(1)
        x = M_IN
        if num:
            canvas.setFont(DISP_BLACK, 66)
            canvas.setFillColor(AMBER)
            canvas.drawString(x - 2, 1.95 * inch, str(num))
        canvas.setFont(DISP_B, 22 if len(title) < 26 else 18)
        canvas.setFillColor(colors.HexColor("#FBF7EF"))
        canvas.drawString(x, 1.45 * inch, title)
        if sub:
            canvas.setFont(BODY_I, 11)
            canvas.setFillColor(colors.HexColor("#E7DFD0"))
            # wrap the subtitle by hand at ~60 chars
            words, lines, cur = sub.split(), [], ""
            for wd in words:
                if len(cur) + len(wd) + 1 > 58:
                    lines.append(cur); cur = wd
                else:
                    cur = (cur + " " + wd).strip()
            if cur:
                lines.append(cur)
            y = 1.15 * inch
            for ln in lines[:4]:
                canvas.drawString(x, y, ln); y -= 14
        canvas.restoreState()
    return on_page


def title_page(title, sub, image):
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#14110E"))
        canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
        if image and os.path.exists(image):
            w, h = PILImage.open(image).size
            scale = max(PAGE_W / w, PAGE_H / h)
            dw, dh = w * scale, h * scale
            canvas.drawImage(image, (PAGE_W - dw) / 2, (PAGE_H - dh) / 2, dw, dh)
        canvas.setFillColor(colors.HexColor("#0E0C0A"))
        canvas.setFillAlpha(0.62)
        canvas.rect(0, 0, PAGE_W, 3.1 * inch, stroke=0, fill=1)
        canvas.setFillAlpha(1)
        canvas.setFont(DISP, 9)
        canvas.setFillColor(AMBER)
        canvas.drawString(M_IN, 2.62 * inch, "C O M F Y - S T U D I O")
        canvas.setFont(DISP_BLACK, 34)
        canvas.setFillColor(colors.HexColor("#FBF7EF"))
        canvas.drawString(M_IN - 2, 2.05 * inch, title)
        canvas.setFont(BODY_I, 12.5)
        canvas.setFillColor(colors.HexColor("#E7DFD0"))
        words, lines, cur = sub.split(), [], ""
        for wd in words:
            if len(cur) + len(wd) + 1 > 52:
                lines.append(cur); cur = wd
            else:
                cur = (cur + " " + wd).strip()
        if cur:
            lines.append(cur)
        y = 1.62 * inch
        for ln in lines[:4]:
            canvas.drawString(M_IN, y, ln); y -= 16
        canvas.setFont(DISP, 7.6)
        canvas.setFillColor(colors.HexColor("#B8AE9E"))
        canvas.drawString(M_IN, 0.55 * inch, "Every rule in this book was measured on one machine before it was written down.")
        canvas.restoreState()
    return on_page


def drop_cap(text, style):
    """a real drop cap: big letter in a left cell, the rest of the paragraph beside it"""
    text = text.strip()
    if not text:
        return Paragraph("", style)
    # mark up first, then lift the first LETTER out - a paragraph that opens in bold
    # must not hand its asterisk to the drop cap
    marked = inline(text)
    m = re.match(r"^((?:<[^>]+>)*)(\w)", marked)
    if not m:
        return Paragraph(marked, style)
    first = m.group(2)
    rest = marked[:m.start(2)] + marked[m.end(2):]
    cap = Paragraph('<font face="%s" size="34" color="#C8791B">%s</font>' % (DISP_BLACK, first),
                    ParagraphStyle("dc", fontName=DISP_BLACK, fontSize=34, leading=34))
    body = Paragraph(rest, style)
    t = Table([[cap, body]], colWidths=[0.42 * inch, FRAME_W - 0.42 * inch], hAlign="LEFT")
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (0, 0), 4), ("RIGHTPADDING", (1, 0), (1, 0), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return t


def box(kind, title, flow):
    bg, accent, default_title = BOX.get(kind, BOX["note"])
    head = Paragraph('<font color="%s">%s</font>%s' % (
        accent.hexval().replace("0x", "#"), html.escape((title or default_title).upper()), ""), S["boxtitle"])
    inner = [head] + flow
    t = Table([[inner]], colWidths=[FRAME_W], hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg),
                           ("LINEBEFORE", (0, 0), (0, -1), 2.2, accent),
                           ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return KeepTogether([Spacer(1, 4), t, Spacer(1, 8)])


def caption_img(path, width, caption, maxh=None):
    im = fit_image(path, width, maxh)
    cells = [[im]]
    if caption:
        cells.append([Paragraph(inline(caption), S["cap"])])
    t = Table(cells, colWidths=[im.drawWidth], hAlign="LEFT")
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def row_images(paths, caption):
    n = len(paths)
    gap = 6
    w = (FRAME_W - gap * (n - 1)) / n
    ims = []
    hmax = 0
    for p in paths:
        im = fit_image(p, w)
        ims.append(im); hmax = max(hmax, im.drawHeight)
    # equalise heights by cropping visually? keep aspect; align top
    t = Table([ims], colWidths=[w] * n, hAlign="LEFT")
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    out = [t]
    if caption:
        out.append(Spacer(1, 3)); out.append(Paragraph(inline(caption), S["cap"]))
    return KeepTogether(out)


def md_table(rows):
    head, body = rows[0], rows[1:]
    ncol = len(head)
    data = [[Paragraph(inline(c), S["cellh"]) for c in head]]
    data += [[Paragraph(inline(c), S["cell"]) for c in (r + [""] * ncol)[:ncol]] for r in body]
    first = FRAME_W * (0.3 if ncol > 2 else 0.4)
    widths = [first] + [(FRAME_W - first) / (ncol - 1)] * (ncol - 1) if ncol > 1 else [FRAME_W]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    st = [("LINEBELOW", (0, 0), (-1, 0), 0.9, AMBER), ("LINEBELOW", (0, 1), (-1, -1), 0.3, RULE),
          ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3.5),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5), ("LEFTPADDING", (0, 0), (-1, -1), 3),
          ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    for i in range(1, len(data)):
        if i % 2 == 0:
            st.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F4EFE6")))
    t.setStyle(TableStyle(st))
    return KeepTogether([t, Spacer(1, 8)])


# ---- the document ---------------------------------------------------------------------
def _full_frame(fid):
    return Frame(0, 0, PAGE_W, PAGE_H, id=fid, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)


class Book(BaseDocTemplate):
    """The cover template comes first, so page 1 is the cover.  Every chapter opener is its own
    page template whose onPage paints the full-bleed page - no state is handed from one page to
    the next, so nothing can leak onto the wrong page.  The running head is set by an action
    flowable (applied the moment it is reached, never pushed to the next page) and reset at the
    start of every build pass, because the table of contents needs two passes."""

    def __init__(self, path, **kw):
        BaseDocTemplate.__init__(self, path, pagesize=(PAGE_W, PAGE_H), **kw)
        self.chapter = ""
        self.title_fn = None
        body = Frame(M_IN, M_BOT, FRAME_W, PAGE_H - M_TOP - M_BOT, id="body",
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id="cover", frames=[_full_frame("cover")], onPage=self._cover_page),
                               PageTemplate(id="body", frames=[body], onPage=self._body_page)])

    def add_opener(self, tid, label, fn):
        """a page template that paints one chapter opener and files its table-of-contents line"""
        def on_page(canvas, doc, fn=fn, label=label):
            fn(canvas, doc)
            doc.notify("TOCEntry", (0, label, doc.page))
        self.addPageTemplates(PageTemplate(id=tid, frames=[_full_frame("f_" + tid)], onPage=on_page))

    def handle_documentBegin(self):
        self.chapter = ""
        BaseDocTemplate.handle_documentBegin(self)

    def _body_page(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(PAPER)
        canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
        canvas.setFont(DISP, 7.3)
        canvas.setFillColor(MUTED)
        if self.chapter:
            canvas.drawString(M_IN, PAGE_H - 0.45 * inch, self.chapter.upper()[:70])
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.4)
        canvas.line(M_IN, PAGE_H - 0.52 * inch, PAGE_W - M_OUT, PAGE_H - 0.52 * inch)
        canvas.drawCentredString(PAGE_W / 2, 0.38 * inch, str(doc.page))
        canvas.restoreState()

    def _cover_page(self, canvas, doc):
        if self.title_fn:
            self.title_fn(canvas, doc)
        else:
            canvas.saveState()
            canvas.setFillColor(colors.HexColor("#14110E"))
            canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
            canvas.restoreState()

    def afterFlowable(self, flowable):
        # chapter lines come from the openers; section headings inside a chapter come from here
        if isinstance(flowable, Paragraph) and flowable.style.name == "h2":
            txt = re.sub(r"<[^>]+>", "", flowable.getPlainText())
            self.notify("TOCEntry", (1, txt, self.page))


class _SetChapter(ActionFlowable):
    """set the running head; an action is applied where it stands, never carried to the next page"""

    def __init__(self, name):
        ActionFlowable.__init__(self); self.name = name

    def apply(self, doc):
        doc.chapter = self.name


def build(md):
    doc = Book(OUT, title="The Method", author="comfy-studio")
    story = []
    lines = md.splitlines()
    i = 0
    para, lst, tbl, boxst = [], None, [], None
    pending_wrap = None
    first_after_opener = False
    n_ch = 0

    def target():
        return boxst["flow"] if boxst else story

    def pstyle():
        return S["boxbody"] if boxst else S["body"]

    def flush_para():
        nonlocal para, pending_wrap, first_after_opener
        if not para:
            return
        text = " ".join(para).strip()
        para = []
        if pending_wrap:
            side, path, cap = pending_wrap
            pending_wrap = None
            width = FRAME_W * 0.44
            im = caption_img(path, width, cap, maxh=3.2 * inch)
            target().append(ParagraphAndImage(Paragraph(inline(text), pstyle()), im, xpad=14, ypad=2,
                                              side=side))
            target().append(Spacer(1, 4))
            return
        if first_after_opener and not boxst:
            first_after_opener = False
            target().append(drop_cap(text, S["body"]))
            return
        target().append(Paragraph(inline(text), pstyle()))

    def flush_list():
        nonlocal lst, first_after_opener
        if not lst:
            return
        first_after_opener = False      # a chapter that opens with a list gets no drop cap later
        kind, items = lst
        lst = None
        st = S["boxli"] if boxst else S["li"]
        target().append(ListFlowable([ListItem(Paragraph(inline(t), st), leftIndent=12) for t in items],
                                     bulletType="1" if kind == "ol" else "bullet",
                                     start="1" if kind == "ol" else None, bulletFontSize=8,
                                     bulletColor=AMBER, leftIndent=14))
        target().append(Spacer(1, 4))

    def flush_table():
        nonlocal tbl, first_after_opener
        if not tbl:
            return
        first_after_opener = False
        rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in tbl
                if not re.match(r"^\s*\|?\s*:?-{2,}", r)]
        tbl = []
        if rows:
            target().append(md_table(rows))

    def flush_all():
        flush_para(); flush_list(); flush_table()

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("|"):
            flush_para(); flush_list(); tbl.append(line); continue
        else:
            flush_table()
        if line.startswith("@"):
            flush_all()
            parts = [p.strip() for p in line[1:].split("|")]
            cmd = parts[0].split()[0].lower() if parts[0] else ""
            arg0 = parts[0][len(cmd):].strip()
            if cmd != "chapter":
                first_after_opener = False  # a figure, row, wrap or box came first: no drop cap
            if cmd == "title":
                # page 1 is the cover template; the story moves straight on to a body page
                title, sub, image = (parts[1:] + ["", "", ""])[:3]
                doc.title_fn = title_page(title, sub, img_path(image) if image else "")
                story.append(NextPageTemplate("body"))
                story.append(PageBreak())
            elif cmd == "toc":
                toc = TableOfContents()
                toc.levelStyles = [S["toc1"], S["toc2"]]
                toc.dotsMinLevel = 0
                story.append(Paragraph("Contents", S["h1toc"]))
                story.append(toc)
            elif cmd == "chapter":
                # the opener page carries the number, title and subtitle; the text then begins
                # on the next page under the running head, with a drop cap - no repeated heading
                num, title, sub, image = (parts[1:] + ["", "", "", ""])[:4]
                n_ch += 1
                tid = "ch%d" % n_ch
                doc.add_opener(tid, ("%s %s" % (num, title)) if num else title,
                               opener_page(num, title, sub, img_path(image) if image else ""))
                story.append(_SetChapter(("%s · %s" % (num, title)) if num else title))
                story.append(NextPageTemplate(tid))
                story.append(PageBreak())
                story.append(NextPageTemplate("body"))
                story.append(PageBreak())
                first_after_opener = True
            elif cmd == "figure":
                path, cap, width = (parts[0][len("figure"):].strip(), (parts[1] if len(parts) > 1 else ""),
                                    (parts[2] if len(parts) > 2 else "100%"))
                try:
                    frac = float(width.strip("%")) / 100.0
                except ValueError:
                    frac = 1.0
                p = img_path(path)
                if os.path.exists(p):
                    target().append(KeepTogether([caption_img(p, FRAME_W * frac, cap, maxh=5.6 * inch), Spacer(1, 6)]))
            elif cmd == "wrap":
                side, path, cap = (parts[0][len("wrap"):].strip() or "right", parts[1] if len(parts) > 1 else "",
                                   parts[2] if len(parts) > 2 else "")
                p = img_path(path)
                if os.path.exists(p):
                    pending_wrap = (side if side in ("left", "right") else "right", p, cap)
            elif cmd == "row":
                paths = [img_path(x) for x in parts[0][len("row"):].strip().split("||")] if "||" in parts[0] else None
                # form: @row a | b | c | caption  -> all but the last that is not a file are images
                items = [parts[0][len("row"):].strip()] + parts[1:]
                imgs = [img_path(x) for x in items if os.path.exists(img_path(x))]
                cap = items[-1] if items and not os.path.exists(img_path(items[-1])) else ""
                if imgs:
                    target().append(row_images(imgs, cap))
            elif cmd == "box":
                kind = parts[0][len("box"):].strip() or "note"
                boxst = {"kind": kind, "title": parts[1] if len(parts) > 1 else "", "flow": []}
            elif cmd == "end":
                if boxst:
                    b = boxst; boxst = None
                    story.append(box(b["kind"], b["title"], b["flow"]))
            elif cmd == "quote":
                text = parts[0][len("quote"):].strip()
                by = parts[1] if len(parts) > 1 else ""
                target().append(KeepTogether([
                    HRFlowable(width="40%", thickness=0.8, color=AMBER, spaceBefore=6, spaceAfter=6, hAlign="CENTER"),
                    Paragraph(inline(text), S["quote"]),
                    Paragraph(inline(by), S["quoteby"]) if by else Spacer(1, 2),
                    HRFlowable(width="40%", thickness=0.8, color=AMBER, spaceBefore=4, spaceAfter=10, hAlign="CENTER")]))
            elif cmd == "pagebreak":
                story.append(PageBreak())
            continue
        if not line.strip():
            flush_para(); flush_list(); continue
        m = re.match(r"^(#{1,3})\s+(.*)", line)
        if m:
            flush_all()
            lvl, text = len(m.group(1)), m.group(2)
            if lvl == 1:
                continue        # the book title is the cover; a stray # is ignored
            target().append(Paragraph(inline(text), S["h2"] if lvl == 2 else S["h3"]))
            continue
        if re.match(r"^-{3,}$", line.strip()):
            flush_all()
            target().append(HRFlowable(width="100%", thickness=0.5, color=RULE, spaceBefore=6, spaceAfter=8))
            continue
        m = re.match(r"^\s*[-*]\s+(.*)", line)
        if m:
            flush_para()
            if lst and lst[0] != "ul":
                flush_list()
            lst = lst or ("ul", []); lst[1].append(m.group(1)); continue
        m = re.match(r"^\s*\d+\.\s+(.*)", line)
        if m:
            flush_para()
            if lst and lst[0] != "ol":
                flush_list()
            lst = lst or ("ol", []); lst[1].append(m.group(1)); continue
        if lst and line.startswith("   "):
            lst[1][-1] += " " + line.strip(); continue
        if line.startswith(">"):
            flush_all()
            target().append(Paragraph(inline(line.lstrip("> ")), S["lead"])); continue
        para.append(line.strip())
    flush_all()
    if boxst:
        story.append(box(boxst["kind"], boxst["title"], boxst["flow"]))
    doc.multiBuild(story)
    return doc


def main():
    md = open(DOC, encoding="utf-8").read()
    os.makedirs(OUTDIR, exist_ok=True)
    doc = build(md)
    print("wrote %s" % OUT)
    print("  %d bytes, fonts %s" % (os.path.getsize(OUT), "Caladea/Montserrat" if HAVE_FONTS else "core"))


if __name__ == "__main__":
    main()
