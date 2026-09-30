#!/usr/bin/env python3
"""studio/_tools/walkthrough_pdf.py - the walkthrough of the three demo films (2026-09-29): what was used
for every shot, and why.

Built only from the films' own records, so every number in it is the measured one:
  studio/shotscripts/<film>.json         the story as data: cast, place, shots, prompts, Seedance notes
  studio/samples/fight/<film>/anchors.json    both compositors' start frames per shot, scored, the pick
  .../ranked.json                        every take: face against its start frame, line heard, level, pick
  .../measured.json                      camera per take (cammeasure)
  .../timeline.json                      where each shot sits in the finished film (film_cards.py)
  .../previz_070.json                    the physics shot (previz_shot.py)
  ~/logs/demo_*.log                      wall-clock per render, for the cost table

    ~/.pdfvenv/bin/python studio/_tools/walkthrough_pdf.py
-> studio/samples/docs/DEMO_FILMS_WALKTHROUGH.pdf
"""
import json
import os
import re
import subprocess

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
FIGHT = os.path.join(STUDIO, "samples", "fight")
OUTDIR = os.path.join(STUDIO, "samples", "docs")
OUT = os.path.join(OUTDIR, "DEMO_FILMS_WALKTHROUGH.pdf")
WORK = os.path.join(OUTDIR, "_walkthrough")
FILMS = ["dead-stock", "house-rules", "temper"]
LOGS = os.path.expanduser("~/logs")

F = "/usr/share/fonts"
for name, path in [
    ("Body", "%s/google-crosextra-caladea-fonts/Caladea-Regular.ttf" % F),
    ("Body-B", "%s/google-crosextra-caladea-fonts/Caladea-Bold.ttf" % F),
    ("Body-I", "%s/google-crosextra-caladea-fonts/Caladea-Italic.ttf" % F),
    ("Body-BI", "%s/google-crosextra-caladea-fonts/Caladea-BoldItalic.ttf" % F),
    ("Sans", "%s/liberation-sans-fonts/LiberationSans-Regular.ttf" % F),
    ("Sans-B", "%s/liberation-sans-fonts/LiberationSans-Bold.ttf" % F),
    ("Mono", "%s/liberation-mono-fonts/LiberationMono-Regular.ttf" % F),
]:
    pdfmetrics.registerFont(TTFont(name, path))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-B", italic="Body-I", boldItalic="Body-BI")

INK = colors.HexColor("#1b1b1b")
MUTED = colors.HexColor("#5e5e5e")
RULE = colors.HexColor("#cfc8b8")
ACCENT = colors.HexColor("#8a5a12")
AMBER = colors.HexColor("#b7791f")
AMBER_BG = colors.HexColor("#fbf3e4")
GOOD = colors.HexColor("#2f6b4f")

S = {
    "cover": ParagraphStyle("cover", fontName="Sans-B", fontSize=30, leading=35, textColor=INK, spaceAfter=6),
    "coversub": ParagraphStyle("coversub", fontName="Body-I", fontSize=13, leading=18, textColor=MUTED,
                               spaceAfter=14),
    "h1": ParagraphStyle("h1", fontName="Sans-B", fontSize=21, leading=26, textColor=INK, spaceAfter=4),
    "h2": ParagraphStyle("h2", fontName="Sans-B", fontSize=13, leading=17, textColor=ACCENT, spaceBefore=12,
                         spaceAfter=5),
    "h3": ParagraphStyle("h3", fontName="Sans-B", fontSize=10.5, leading=13.5, textColor=INK, spaceAfter=2),
    "lede": ParagraphStyle("lede", fontName="Body-I", fontSize=11, leading=15.5, textColor=MUTED, spaceAfter=10),
    "body": ParagraphStyle("body", fontName="Body", fontSize=10.2, leading=14.3, textColor=INK, spaceAfter=6,
                           alignment=TA_JUSTIFY),
    "small": ParagraphStyle("small", fontName="Body", fontSize=8.9, leading=12, textColor=INK, spaceAfter=2),
    "smallm": ParagraphStyle("smallm", fontName="Body-I", fontSize=8.4, leading=11.2, textColor=MUTED,
                             spaceAfter=2),
    "label": ParagraphStyle("label", fontName="Sans-B", fontSize=8.2, leading=10.5, textColor=MUTED),
    "cap": ParagraphStyle("cap", fontName="Body-I", fontSize=8.6, leading=11.5, textColor=MUTED, spaceBefore=2,
                          spaceAfter=8, alignment=TA_CENTER),
    "th": ParagraphStyle("th", fontName="Sans-B", fontSize=8.6, leading=11, textColor=INK),
    "td": ParagraphStyle("td", fontName="Body", fontSize=9.1, leading=11.8, textColor=INK),
    "mono": ParagraphStyle("mono", fontName="Mono", fontSize=7.9, leading=10.4, textColor=INK, spaceAfter=4),
    "amber": ParagraphStyle("amber", fontName="Body", fontSize=8.8, leading=11.8, textColor=colors.HexColor("#5a3c0c")),
}

PW, PH = A4
MARGIN = 17 * mm
CW = PW - 2 * MARGIN

ENGINE = {"shot": "LTX-2.5", "h3": "MiniMax H3", "pv": "Blender previz + LTX-2.3 depth control",
          "pvb": "Blender previz + LTX-2.3 depth control (no start frame)"}
COMPOSITOR = {"flux2": "Flux 2 (three references, workflow 75)",
              "qwen21": "Qwen-Image-2.1 (reference edit, workflow 80)"}
WHY_ENGINE = {
    "ltx": "LTX-2.5 is the default engine: one sampling pass holds the scene, sound is generated with the "
           "picture, and a written line is lip-synced through a mouth on screen (playbook §96.5).",
    "both": "Rendered on both engines and picked by measurement: H3 keeps the composed start frame almost "
            "exactly and returns louder close sound; LTX-2.5 moves more freely. The take that scored best "
            "against its own start frame went in.",
    "h3": "An effects beat: on LTX-2.5 dust accumulates whatever the words say; on H3 it plateaus and clears "
          "(measured, §98.3-98.4), so this shot was rendered on H3 only.",
    "previz": "A physical event with dozens of bodies in contact. The motion was simulated in Blender, and the "
              "video engine only painted over the simulation's depth, so every crate lands where the physics put it.",
}


def esc(t):
    return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def P(t, st="body"):
    return Paragraph(t, S[st])


def img(path, w=None, h=None):
    if not path or not os.path.exists(path):
        return P("<i>(missing: %s)</i>" % esc(os.path.basename(str(path))), "smallm")
    iw, ih = PILImage.open(path).size
    if w and not h:
        h = ih * w / iw
    elif h and not w:
        w = iw * h / ih
    im = Image(path, width=w, height=h)
    im.hAlign = "CENTER"
    return im


def thumb(src, dst, width=900):
    """A JPEG copy small enough that twenty of them do not make a 200 MB PDF."""
    if not os.path.exists(src):
        return None
    if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
        return dst
    im = PILImage.open(src).convert("RGB")
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), PILImage.LANCZOS)
    im.save(dst, quality=84)
    return dst


def frame(video, t, dst, width=1100):
    if not os.path.exists(video):
        return None
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % t, "-i", video, "-frames:v", "1",
                    "-vf", "scale=%d:-2" % width, dst], capture_output=True)
    return dst if os.path.exists(dst) else None


def load(film, name, default=None):
    p = os.path.join(FIGHT, film, name)
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
    return default if default is not None else {}


def take_file(film, token, sid):
    if not token:
        return None
    stem, _, seed = token.rpartition(":")
    stem = {"": "shot"}.get(stem, stem)
    return os.path.join(FIGHT, film, "%s_%s_s%s.mp4" % (stem, sid, seed)), stem, seed


def seconds_of_logs():
    """Wall-clock per render, per film and stage, from the logs the chains wrote."""
    cost = {f: {} for f in FILMS}
    pat_shot = re.compile(r"^\s+(shot|h3)_(\d{3})_s(\d+)\s+(\d+)s")
    pat_anchor = re.compile(r"^\s+anchor_(\d{3}) (flux2|qwen21)(?: s\d+)?\s+(\d+)s")
    pat_pv = re.compile(r"^\s+(pvb?)_(\d{3})_s\d+\.mp4\s+(\d+)s")
    pat_ref = re.compile(r"^\s+ref_\S+\s+(\d+)s")

    def add(f, k, v):
        cost[f][k] = cost[f].get(k, 0.0) + v
    # cast: one invocation per film, in order
    p = os.path.join(LOGS, "demo_cast.log")
    if os.path.exists(p):
        i = 0
        for ln in open(p, errors="replace"):
            m = pat_ref.match(ln)
            if m and i < len(FILMS):
                add(FILMS[i], "cast and plate", float(m.group(1)))
            if "FIGHT STAGE DONE" in ln:
                i += 1
    p = os.path.join(LOGS, "demo_anchors.log")
    if os.path.exists(p):
        i = -1                                # the diner re-roll comes first
        for ln in open(p, errors="replace"):
            m = pat_anchor.match(ln)
            if m and 0 <= i < len(FILMS):
                add(FILMS[i], "start frames (%s)" % ("Flux 2" if m.group(2) == "flux2" else "Qwen-2.1"),
                    float(m.group(3)))
            m = pat_ref.match(ln)
            if m and i == -1:
                add("house-rules", "cast and plate", float(m.group(1)))
            if "FIGHT STAGE DONE" in ln:
                i += 1
    p = os.path.join(LOGS, "demo_films.log")
    if os.path.exists(p):
        cur = "dead-stock"
        for ln in open(p, errors="replace"):
            m = re.match(r"^=== \d\d:\d\d (\S+):", ln)
            if m and m.group(1) in FILMS:
                cur = m.group(1)
            m = pat_shot.match(ln)
            if m:
                add(cur, "takes on %s" % ("LTX-2.5" if m.group(1) == "shot" else "H3"), float(m.group(4)))
            m = pat_pv.match(ln)
            if m:
                add("dead-stock", "physics shot (LTX-2.3)", float(m.group(3)))
    return cost


# ---------------------------------------------------------------------------------------- page chrome
def on_page(c, doc):
    c.saveState()
    c.setFont("Sans", 7.5)
    c.setFillColor(MUTED)
    c.drawString(MARGIN, 10 * mm, "comfy-studio  -  three demo films, one RTX 5090  -  2026-09-29")
    c.drawRightString(PW - MARGIN, 10 * mm, str(doc.page))
    c.restoreState()


def boxed(flow, bg=AMBER_BG, line=AMBER):
    t = Table([[flow]], colWidths=[CW])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("BOX", (0, 0), (-1, -1), 0.6, line),
                           ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t


def grid(rows, widths, head=True, size="td"):
    data = []
    for i, r in enumerate(rows):
        data.append([c if not isinstance(c, str) else P(c, "th" if (head and i == 0) else size) for c in r])
    t = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1 if head else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LEFTPADDING", (0, 0), (-1, -1), 3),
          ("RIGHTPADDING", (0, 0), (-1, -1), 3),
          ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#e7e2d6"))]
    if head:
        st.append(("LINEBELOW", (0, 0), (-1, 0), 0.9, RULE))
    t.setStyle(TableStyle(st))
    return t


# ------------------------------------------------------------------------------------------ sections
def cover(story, data):
    story.append(Spacer(1, 18 * mm))
    story.append(P("Three films, one RTX 5090", "cover"))
    story.append(P("A walkthrough of the comfy-studio pipeline: what was used for every shot, and why. "
                   "Every frame was made on one local graphics card with open-weight models; nothing was "
                   "paid for. The shots we would have sent to Seedance 2.5, and the exact prompts, are in "
                   "section 6.", "coversub"))
    cells, caps = [], []
    for f in FILMS:
        d = data[f]
        cells.append(img(d.get("poster"), w=CW / 3 - 4 * mm))
        caps.append(P("<b>%s</b><br/><font size='8'>%s</font>" % (esc(d["seq"].get("title", f)),
                                                                  esc(d["seq"].get("logline", ""))), "small"))
    t = Table([cells, caps], colWidths=[CW / 3] * 3)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 2),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 2)]))
    story.append(t)
    story.append(Spacer(1, 8 * mm))
    rows = [["film", "runtime", "shots", "takes rendered", "engines in the cut"]]
    for f in FILMS:
        d = data[f]
        eng = sorted({ENGINE.get(x[1], x[1]).split(" (")[0] for x in d["cut"]})
        rows.append(["<b>%s</b>" % esc(d["seq"].get("title", f)), "%.0f s" % d["runtime"],
                     str(len(d["cut"])), str(d["n_takes"]), esc(", ".join(eng))])
    story.append(grid(rows, [CW * 0.2, CW * 0.12, CW * 0.1, CW * 0.16, CW * 0.42]))
    story.append(Spacer(1, 6 * mm))
    story.append(P("<b>What is in this document.</b> 1 - the pipeline, stage by stage, and why each stage is "
                   "there. 2-4 - the three films, shot by shot: the start frame, the engine, the take that "
                   "went in and the numbers that put it there. 5 - the start-frame compositor contest, run "
                   "on every shot. 6 - H3 against LTX-2.5 on the same frames. 7 - the Seedance notation. 8 - what "
                   "was deliberately not used. 9 - what it cost in minutes. 10 - how to make them again.", "body"))
    story.append(P("<b>The films.</b> Each comes three ways: <i>_final_2x.mp4</i> (2560x1408, the master), "
                   "<i>_final.mp4</i> (1280x704) and <i>_annotated.mp4</i>, which captions every shot with the "
                   "engine that drew it, what its start frame was composed with, the take and why it was picked - "
                   "and marks in amber the shots we would have sent to Seedance. "
                   "<i>dead-stock_physics_side_by_side.mp4</i> shows the Blender simulation beside the shot it drove.",
                   "body"))
    story.append(PageBreak())


def pipeline(story):
    story.append(P("1  The pipeline", "h1"))
    story.append(P("The films were made the way the paid breakdowns make a sequence - pictures first, a "
                   "composed start frame per shot, one beat per shot, sound written in, a pick by "
                   "measurement, one grade at the finish - with the engine swapped for local weights and "
                   "every choice measured. It runs from one file per film (a <i>shot script</i>) through "
                   "<font face='Mono' size='8.5'>studio/_tools/fight.py</font>, which is also the "
                   "<font face='Mono' size='8.5'>/shots</font> page of the studio app.", "lede"))
    rows = [["stage", "what did it", "why"],
            ["<b>Shot script</b>", "one JSON per film: cast, place, shots, prompts, engine per shot, the "
             "line each take must say, the Seedance note",
             "The story as data: the same tool builds any film, and every decision below is recorded."],
            ["<b>Cast and plate</b>", "Flux 2 text-to-image (workflow 40): each person full-length on grey; "
             "the place wide and empty",
             "Refs before words: a character is described once, then every shot points at the picture."],
            ["<b>Start frames</b>", "BOTH Flux 2 with three chained references (75) and Qwen-Image-2.1 "
             "with its reference edit (80, two seeds); every face scored against the cast; best kept",
             "The start frame decides where a shot begins, who is in it and what it looks like. Qwen won "
             "the 09-27 A/B on one shot; tonight it ran on every shot (section 5)."],
            ["<b>Takes</b>", "LTX-2.5 (70) by default; MiniMax H3 (67) for effects and close sound; both "
             "where it was a toss-up; Blender previz + LTX-2.3 depth control (74) for the physical beat",
             "Each engine where it is measurably best (playbook §96.5, §98.3-98.4, review §0.2). Three "
             "seeds a shot is the floor for a pick."],
            ["<b>The pick</b>", "take_rank.py: each face on the last frame against the same face in the "
             "start frame; each line through a local speech model; level; camera against the ask",
             "One rule for every shot: a fault blocks a pick, a note never does; the highest score "
             "among the unfaulted takes goes in."],
            ["<b>Music</b>", "ACE-Step (06): two cues from the script's score tags, crossfaded",
             "ACE-Step fades out past about 45 s; two cues make an act break instead of a fade."],
            ["<b>Finish</b>", "audio conformed, cut, one film grade, the score under at half level, "
             "loudness to -16 LUFS, the frame count checked against the takes, a 2x master, title card",
             "The finish is half the film; the frame-count check is how a dropped or doubled frame is "
             "caught."]]
    story.append(grid(rows, [CW * 0.16, CW * 0.44, CW * 0.40]))
    story.append(PageBreak())


def film_section(story, n, f, d):
    seq = d["seq"]
    story.append(P("%d  %s" % (n, esc(seq.get("title", f))), "h1"))
    story.append(P(esc(seq.get("logline", "")), "lede"))
    story.append(P("<b>%.0f seconds, %d shots.</b> %s" % (d["runtime"], len(d["cut"]), esc(seq.get("_comment", ""))),
                   "body"))
    refs = [os.path.join(FIGHT, f, "ref_%s.png" % c) for c in seq["cast"]]
    plate = os.path.join(FIGHT, f, "ref_%s.png" % seq["place"]["id"])
    cells = [img(thumb(r, os.path.join(WORK, "%s_ref_%d.jpg" % (f, i)), 500), h=48 * mm) for i, r in enumerate(refs)]
    cells.append(img(thumb(plate, os.path.join(WORK, "%s_plate.jpg" % f), 900), h=48 * mm))
    t = Table([cells])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(t)
    names = ", ".join("%s (%s)" % (c, esc(v.get("role", ""))) for c, v in seq["cast"].items())
    story.append(P("The cast and the place, made first: %s; and the %s. Every later picture of them is drawn "
                   "from these." % (esc(names), esc(seq["place"]["id"])), "cap"))
    story.append(P("Look, negative and score", "h2"))
    story.append(P("<b>Grade</b> (appended to every start frame, applied once at the finish): %s" % esc(seq["grade"]),
                   "small"))
    story.append(P("<b>Score</b> - cue one: %s. Cue two: %s." % (esc(seq.get("score_tags", "")),
                                                               esc(seq.get("score_tags_b", ""))), "small"))
    story.append(P("Shot by shot", "h2"))
    anchors, ranked, measured = d["anchors"], d["ranked"], d["measured"]
    for s, stem, seed, path in d["cut"]:
        sid = s["id"]
        r = ranked.get(sid) or {}
        a = anchors.get(sid) or {}
        pick_row = next((x for x in r.get("takes", []) if x.get("take") == os.path.basename(path)), {})
        # the start frame line
        if s.get("engine") == "previz":
            start = "Qwen-Image-2.1 dressing the first frame of the Blender simulation (see the physics page)"
        elif s.get("anchor") is None:
            start = "the place's plate itself - nobody in the shot, nothing to compose"
        else:
            ch = a.get("chosen", "")
            cands = a.get("candidates", {})
            parts = []
            for k, v in sorted(cands.items()):
                parts.append("%s %s" % (k.replace("qwen21_", "Qwen s").replace("flux2", "Flux"),
                                        "%.2f" % v["mean"] if v.get("mean") is not None else "n/a"))
            start = "%s, %s. Faces against the cast: %s (%s)." % (
                COMPOSITOR.get(ch.split("_")[0], ch), ch.replace("qwen21_", "seed ").replace("flux2", "seed 4242"),
                "; ".join(parts) or "not scored", esc(a.get("why", "")))
        # the take line
        bits = []
        if pick_row.get("faces"):
            bits.append("face against its own start frame " + ", ".join(
                "%s %.2f" % (k, v) for k, v in pick_row["faces"].items()))
        if pick_row.get("line_hit") is not None:
            bits.append("line heard %d%% (\"%s\")" % (int(100 * pick_row["line_hit"]), esc(pick_row.get("heard", "")[:80])))
        cam = (measured.get(os.path.basename(path)) or {}).get("camera")
        if cam:
            bits.append("camera: %s" % esc(cam))
        if pick_row.get("mean_db") is not None:
            bits.append("level %.0f dB" % pick_row["mean_db"])
        alts = [x for x in r.get("takes", []) if x.get("take") != os.path.basename(path)]
        other = ""
        if s.get("engine") == "both":
            oe = [x for x in alts if x.get("engine") != stem]
            if oe:
                ob = sorted(oe, key=lambda x: (len(x.get("faults", [])), -x.get("score", 0)))[0]
                other = " The best take on the other engine (%s, %s) scored %.3f%s." % (
                    ENGINE.get(ob["engine"], ob["engine"]), ob["token"], ob.get("score", 0),
                    ("; faults: " + "; ".join(ob["faults"])) if ob.get("faults") else "")
        text = [P("<b>%s  %s</b>  -  %s s" % (sid, esc(s["title"]), s["secs"]), "h3"),
                P("<b>Engine:</b> %s, seed %s. %s" % (ENGINE.get(stem, stem), seed,
                                                      WHY_ENGINE.get(s.get("engine", "ltx"), "")), "small"),
                P("<b>Start frame:</b> %s" % start, "small"),
                P("<b>The take:</b> %s. Picked: %s (%d takes rendered).%s" % (
                    "; ".join(bits) or "no face or line to score in this shot",
                    esc(r.get("why", "by eye")), len(r.get("takes", [])), esc(other)), "small")]
        if s.get("line"):
            text.append(P("<b>The line:</b> \"%s\"" % esc(s["line"]), "small"))
        if s.get("note"):
            text.append(P("<b>Note:</b> %s" % esc(s["note"]), "small"))
        anchor_im = thumb(os.path.join(FIGHT, f, "anchor_%s.png" % sid), os.path.join(WORK, "%s_a%s.jpg" % (f, sid)), 700)
        row = Table([[img(anchor_im, w=58 * mm), text]], colWidths=[61 * mm, CW - 61 * mm])
        row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        block = [row]
        strip = path[:-4] + "_strip.jpg"
        if os.path.exists(strip):
            block.append(Spacer(1, 2))
            block.append(img(thumb(strip, os.path.join(WORK, "%s_s%s.jpg" % (f, sid)), 1600), w=CW))
        block.append(P("<b>Prompt:</b> %s" % esc(s["prompt"]), "smallm"))
        if s.get("seedance"):
            block.append(boxed(P("<b>Seedance candidate.</b> %s The prompt we did not send is in section 6."
                                 % esc(s["seedance"]["why"]), "amber")))
        block.append(Spacer(1, 7))
        story.append(CondPageBreak(95 * mm))
        story.append(KeepTogether(block))
    story.append(PageBreak())


def physics_page(story, data):
    f = "dead-stock"
    pv = load(f, "previz_070.json")
    if not pv:
        return
    story.append(P("The physics shot: choreograph, dress, draw", "h2"))
    story.append(P("DEAD STOCK's collapse is the one shot in these films whose motion was not written in "
                   "words. A tall stack of eighteen crates is pushed over across the aisle in Blender 5.2 "
                   "with rigid-body physics; the simulation says the top crate comes down at frame %s of %s. "
                   "Its first frame is then dressed as the film by Qwen-Image-2.1 (the simulation as the "
                   "canvas, the warehouse plate and the collector as further references), and LTX-2.3 with "
                   "the IC-LoRA union control reads the simulation's depth and paints the real scene over it. "
                   "The engine paints; the physics moves." % (pv.get("previz", {}).get("impact_frame", "?"),
                                                               pv.get("previz", {}).get("frames", "?")), "body"))
    out = os.path.join(FIGHT, f)
    pieces = [("the Blender simulation (proxy boxes, a proxy figure)", os.path.join(out, "previz_070_strip.jpg")),
              ("its first frame dressed by Qwen-Image-2.1", os.path.join(out, "anchor_070.png"))]
    cut = next((c for c in data[f]["cut"] if c[0]["id"] == "070"), None)
    if cut:
        pieces.append(("the take in the film (%s, seed %s)" % (ENGINE.get(cut[1], cut[1]), cut[2]),
                       cut[3][:-4] + "_strip.jpg"))
    for cap, p in pieces:
        if p.endswith(".png"):
            story.append(img(thumb(p, os.path.join(WORK, "pv_anchor.jpg"), 900), w=CW * 0.62))
        else:
            story.append(img(thumb(p, os.path.join(WORK, "pv_%d.jpg" % len(cap)), 1600), w=CW))
        story.append(P(cap, "cap"))
    sbs = os.path.join(out, "dead-stock_physics_side_by_side.mp4")
    if os.path.exists(sbs):
        fr = frame(sbs, 2.0, os.path.join(WORK, "pv_sbs.jpg"), 1400)
        if fr:
            im = PILImage.open(fr)
            box = im.crop((0, int(im.height * 0.255), im.width, int(im.height * 0.745)))
            box.save(os.path.join(WORK, "pv_sbs_crop.jpg"), quality=86)
            story.append(img(os.path.join(WORK, "pv_sbs_crop.jpg"), w=CW))
            story.append(P("Two seconds in, frame for frame: the simulation (left) and the take in the film (right). "
                           "The clip is dead-stock_physics_side_by_side.mp4.", "cap"))
    rows = [["take", "start frame", "motion agreement with the simulation (r)", "seconds"]]
    for t in pv.get("takes", []):
        rows.append([esc(t["take"]), "none (bypassed)" if t["take"].startswith("pvb") else "dressed frame",
                     str((t.get("motion") or {}).get("r")), str(t.get("secs"))])
    story.append(grid(rows, [CW * 0.28, CW * 0.2, CW * 0.36, CW * 0.16]))
    story.append(P("Motion agreement is the Pearson correlation between the simulation's frame-to-frame "
                   "motion energy and the render's, over the whole clip: 1.0 moves exactly when the "
                   "simulation moves.", "smallm"))
    rs = {True: [], False: []}
    for t in pv.get("takes", []):
        r = (t.get("motion") or {}).get("r")
        if r is not None:
            rs[t["take"].startswith("pvb")].append(r)
    if rs[True] and rs[False]:
        story.append(P("<b>What the two arms say.</b> Without a start frame the render follows the simulation "
                       "even more closely (r %s) - nothing competes with the depth guide - but it invents its "
                       "own room, lit its own way, and cannot be cut into the film. With the dressed start frame "
                       "(r %s) the warehouse is the film's warehouse and the collector is the collector. On "
                       "2026-09-27, with no start frame and a ball-and-crates previz, the same route measured "
                       "r 0.84 / 0.71." % (" / ".join("%.2f" % x for x in rs[True]),
                                           " / ".join("%.2f" % x for x in rs[False])), "body"))
    story.append(PageBreak())


def compositor_section(story, n, data):
    story.append(P("%d  The start-frame contest, on every shot" % n, "h1"))
    story.append(P("On 2026-09-27 Qwen-Image-2.1 beat Flux 2 as the start-frame compositor on one shot (a tie on "
                   "one face, +0.09 on the other) and the rule said: keep Flux 2 until it holds on a second "
                   "shot. Tonight every composed start frame was drawn by both - Flux 2 once, Qwen-2.1 on two "
                   "seeds - and every face scored against its character's reference. This is that second "
                   "shot, thirty times over.", "lede"))
    rows = [["film", "shot", "Flux 2", "Qwen s11", "Qwen s202", "kept", "why"]]
    wins = {"flux2": 0, "qwen21": 0}
    deltas = []
    for f in FILMS:
        for sid, v in sorted(data[f]["anchors"].items()):
            c = v.get("candidates", {})
            fx = (c.get("flux2") or {}).get("mean")
            q1 = (c.get("qwen21_s11") or {}).get("mean")
            q2 = (c.get("qwen21_s202") or {}).get("mean")
            ch = v.get("chosen", "")
            if fx is not None and (q1 is not None or q2 is not None):
                wins["qwen21" if ch.startswith("qwen21") else "flux2"] += 1
                deltas.append(max(x for x in (q1, q2) if x is not None) - fx)
            fm = lambda x: "%.2f" % x if x is not None else "-"
            rows.append([esc(data[f]["seq"].get("title", f)), sid, fm(fx), fm(q1), fm(q2),
                         ch.replace("qwen21_", "Qwen ").replace("flux2", "Flux 2"), esc(v.get("why", ""))])
    story.append(grid(rows, [CW * 0.16, CW * 0.07, CW * 0.1, CW * 0.11, CW * 0.12, CW * 0.12, CW * 0.32]))
    if deltas:
        mean = sum(deltas) / len(deltas)
        s11 = []
        for f in FILMS:
            for sid, v in data[f]["anchors"].items():
                c = v.get("candidates", {})
                fx, q1 = (c.get("flux2") or {}).get("mean"), (c.get("qwen21_s11") or {}).get("mean")
                if fx is not None and q1 is not None:
                    s11.append(q1 - fx)
        story.append(Spacer(1, 4))
        story.append(P("<b>Result.</b> Where faces could be scored, Qwen-Image-2.1's better seed beat Flux 2 on "
                       "%d of %d shots (mean %+.3f). Its FIRST seed alone beat Flux on %d of %d (%+.3f), so this "
                       "is not the extra seed talking. Qwen draws a start frame in about 13 seconds against "
                       "Flux 2's 33. Qwen-Image-2.1 is now the studio's default start-frame compositor "
                       "(playbook §0.3)." % (sum(1 for x in deltas if x > 0), len(deltas), mean,
                                             sum(1 for x in s11 if x > 0), len(s11), sum(s11) / max(1, len(s11))),
                       "body"))
        story.append(P("<b>What the scores cannot see.</b> Five start frames were overridden by eye: two between "
                       "Qwen seeds (a stranger's hair intruding at the frame edge; an arm raised for the action), "
                       "and three toward Flux 2 - every one for shot size. Asked for a close-up or an insert, Qwen "
                       "tended to draw a medium shot with the whole person in it; Flux 2 kept to the framing. "
                       "Qwen wins faces; Flux 2 still wins framing.", "body"))
    story.append(PageBreak())


def engines_section(story, n, data):
    story.append(P("%d  H3 against LTX-2.5, on the same frame and words" % n, "h1"))
    story.append(P("Nine shots were rendered on both engines from the same start frame with the same words, three "
                   "seeds each, and the take that went in was picked by measurement and by eye. The face numbers "
                   "are each engine's best take, scored against the shot's own start frame.", "lede"))
    rows = [["film", "shot", "H3 best face", "LTX best face", "in the cut", "what decided it"]]
    diffs, wins = [], 0
    for f in FILMS:
        seq = data[f]["seq"]
        cut = {c[0]["id"]: c for c in data[f]["cut"]}
        for s in seq["shots"]:
            if s.get("engine") != "both":
                continue
            takes = (data[f]["ranked"].get(s["id"]) or {}).get("takes", [])
            best = {}
            for t in takes:
                if t.get("faces"):
                    v = min(t["faces"].values())
                    best[t["engine"]] = max(best.get(t["engine"], -1), v)
            h, l = best.get("h3"), best.get("shot")
            c = cut.get(s["id"])
            went = ENGINE.get(c[1], c[1]) if c else "-"
            wins += bool(c and c[1] == "h3")
            if h is not None and l is not None:
                diffs.append(h - l)
            why = (data[f]["ranked"].get(s["id"]) or {}).get("why", "")
            rows.append([esc(seq.get("title", f)), "%s %s" % (s["id"], esc(s["title"])),
                         "%.2f" % h if h is not None else "no face", "%.2f" % l if l is not None else "no face",
                         esc(went), esc(why[:110])])
    story.append(grid(rows, [CW * 0.14, CW * 0.17, CW * 0.1, CW * 0.1, CW * 0.12, CW * 0.37]))
    if diffs:
        story.append(Spacer(1, 4))
        story.append(P("<b>Result.</b> The H3 take went in on %d of %d shots. Where there was a face to score, H3's "
                       "best take held it better than LTX-2.5's best by %+.2f on average, with a static camera "
                       "where the LTX takes pushed in on close-ups that asked for stillness. On the two effects "
                       "inserts in TEMPER the difference is visible without a number: the bellows gave two separate "
                       "flares on H3, each dying before the next, where every LTX take grew the fire and kept it; "
                       "the quench burst into steam that held low on H3, with the blade still visible, where every "
                       "LTX take whited out the frame. LTX-2.5 stays the default - it is the only engine here that "
                       "speaks a written line through a moving mouth, and it made every line in these films - but a "
                       "held close-up and an effect that must clear belong on H3." % (
                           wins, len(rows) - 1, sum(diffs) / len(diffs)), "body"))
    story.append(PageBreak())


def seedance_section(story, n, data):
    story.append(P("%d  The Seedance notation - what we would have sent, and did not" % n, "h1"))
    story.append(P("Every shot below was rendered locally. For each: why the paid engine would do it better, and "
                   "the exact prompt it would get, with [image 1] the shot's composed start frame, [image 2] "
                   "the character's reference and [image 3] the place's plate. It runs through workflow 76 "
                   "(Seedance 2.5, reference mode, 1080p) with one command once someone signs in to a Comfy "
                   "account; the same text is in studio/samples/fight/SEEDANCE_NOTATION.md.", "lede"))
    for f in FILMS:
        seq = data[f]["seq"]
        cands = [s for s in seq["shots"] if s.get("seedance")]
        story.append(P(esc(seq.get("title", f)), "h2"))
        if not cands and not seq.get("not_shot"):
            story.append(P("No shot in this film needs it.", "body"))
        for s in cands:
            sd = s["seedance"]
            story.append(KeepTogether([
                P("<b>%s %s</b> - %d s. %s" % (s["id"], esc(s["title"]), sd.get("secs", s["secs"]), esc(sd["why"])),
                  "small"),
                boxed(P(esc(sd["prompt"]), "mono"), bg=colors.HexColor("#f6f4ef"), line=RULE),
                P("fight.py --sequence %s --seedance %s --resolution 1080p" % (f, s["id"]), "mono"),
                Spacer(1, 4)]))
        for ns in seq.get("not_shot", []):
            story.append(KeepTogether([
                P("<b>Not shot: %s</b> - %d s. %s" % (esc(ns["title"]), ns.get("secs", 5), esc(ns["why"])), "small"),
                boxed(P(esc(ns["seedance"]), "mono"), bg=colors.HexColor("#f6f4ef"), line=RULE),
                Spacer(1, 4)]))
    story.append(P("<b>Price.</b> Seedance 2.5's rate was not verified tonight. At the last rate verified here "
                   "(Seedance 2.0 Fast, $0.09 a second) the whole notation is about $5 for one take of each, "
                   "$16 for three. The studio's rule for spending it (§96.4): start frames before video, by "
                   "scene not by shot, and a bought take must beat the local take on the same beat, scored by "
                   "the same tools.", "body"))
    story.append(PageBreak())


def not_used(story, n):
    story.append(P("%d  What was deliberately not used" % n, "h1"))
    rows = [["tool", "why not tonight"],
            ["Seedance 2.5 (paid video)", "No paid engines, by instruction. Section 6 is what it would have been "
             "handed."],
            ["Nano Banana 2 (paid start frames)", "The local compositor was measured instead (section 5); the "
             "paid one has never been scored against it. Wired as workflow 85, switched off."],
            ["Wan Animate 2 (motion transfer)", "It runs and transfers motion, but its identity through motion is "
             "unmeasured (the first wiring cropped the reference's head). Nothing enters a film on a look."],
            ["LTX Ingredients (reference sheet)", "It carries the cast into a clip with no start frame, but adding "
             "it to a start frame lowered identity against the start frame alone (§0.2). Not a route yet."],
            ["Krea 2 (look and style)", "A look tool, measured once; the cast stage stays on Flux 2 until the "
             "three-engine casting test (queue item 22)."],
            ["H3 reference-to-video", "Carries identity but doubled the person in 2 of 4 renders (§97.3)."],
            ["Timecodes in prompts", "Measured to do nothing on LTX-2.5; the word 'cut' makes the cut (§95)."]]
    story.append(grid(rows, [CW * 0.3, CW * 0.7]))
    story.append(PageBreak())


def cost_section(story, n, data):
    story.append(P("%d  What it cost, in minutes" % n, "h1"))
    story.append(P("Wall-clock seconds of GPU work per stage, from the render logs, on one RTX 5090 with "
                   "nothing paid for. The films were built between 02:00 and 09:00 on 2026-09-29.", "lede"))
    cost = data["_cost"]
    stages = sorted({k for f in FILMS for k in cost.get(f, {})})
    rows = [["stage"] + [esc(data[f]["seq"].get("title", f)) for f in FILMS] + ["all three"]]
    tot = {f: 0.0 for f in FILMS}
    for st in stages:
        vals = [cost.get(f, {}).get(st, 0.0) for f in FILMS]
        for f, v in zip(FILMS, vals):
            tot[f] += v
        rows.append([esc(st)] + ["%.1f min" % (v / 60) if v else "-" for v in vals] + ["%.1f min" % (sum(vals) / 60)])
    rows.append(["<b>total</b>"] + ["<b>%.0f min</b>" % (tot[f] / 60) for f in FILMS] +
                ["<b>%.0f min</b>" % (sum(tot.values()) / 60)])
    story.append(grid(rows, [CW * 0.32, CW * 0.17, CW * 0.17, CW * 0.17, CW * 0.17]))
    story.append(P("Not counted: measuring and ranking takes, the music, the finish and the 2x master - a few "
                   "minutes a film.", "smallm"))


def reproduce(story, n):
    story.append(P("%d  How to make them again" % n, "h2"))
    cmds = ["python3 studio/_tools/fight.py --sequence temper --cast",
            "python3 studio/_tools/fight.py --sequence temper --anchors --compositor best --qseeds 11 202",
            "python3 studio/_tools/fight.py --sequence temper --shots --seeds 11 202 3003",
            "python3 studio/_tools/fight.py --sequence temper --h3 all --seeds 11 202 3003",
            "python3 studio/_tools/previz_shot.py --sequence dead-stock --shot 070",
            "python3 studio/_tools/fight.py --sequence temper --score",
            "~/ComfyUI/venv/bin/python3 studio/_tools/take_rank.py --sequence temper",
            "python3 studio/_tools/fight.py --sequence temper --music",
            "python3 studio/_tools/fight.py --sequence temper --finish --master --picks \"$(cat .../picks.txt)\"",
            "python3 studio/_tools/film_cards.py --sequence temper",
            "python3 studio/_tools/seedance_notation.py"]
    story.append(boxed(P("<br/>".join(esc(c) for c in cmds), "mono"), bg=colors.HexColor("#f6f4ef"), line=RULE))
    story.append(P("Or open http://192.168.0.45:8777/shots and press the stages in order. The shot scripts are "
                   "studio/shotscripts/dead-stock.json, house-rules.json and temper.json.", "small"))


# ---------------------------------------------------------------------------------------------- main
def gather():
    data = {}
    for f in FILMS:
        seq = json.load(open(os.path.join(STUDIO, "shotscripts", f + ".json"), encoding="utf-8"))
        ranked = load(f, "ranked.json")
        picks_txt = os.path.join(FIGHT, f, "picks.txt")
        picks = {}
        if os.path.exists(picks_txt):
            picks = dict(kv.split("=", 1) for kv in open(picks_txt).read().strip().split(",") if "=" in kv)
        cut = []
        for s in seq["shots"]:
            tok = picks.get(s["id"]) or (ranked.get(s["id"]) or {}).get("pick")
            tf = take_file(f, tok, s["id"])
            if tf and os.path.exists(tf[0]):
                cut.append((s, tf[1], tf[2], tf[0]))
        timeline = load(f, "timeline.json", [])
        runtime = timeline[-1]["end"] if timeline else sum(float(s["secs"]) for s, *_ in cut)
        n_takes = len([x for x in os.listdir(os.path.join(FIGHT, f))
                       if re.match(r"^(shot|h3|pv|pvb)_\d{3}_s\d+\.mp4$", x)])
        poster_shot = {"dead-stock": "080", "house-rules": "040", "temper": "050"}[f]
        poster = None
        final = os.path.join(FIGHT, f, "%s_filmic.mp4" % f)
        span = next((x for x in timeline if x["shot"] == poster_shot), None)
        if span:
            poster = frame(final, span["start"] + 0.55 * (span["end"] - span["start"]),
                           os.path.join(WORK, "%s_poster.jpg" % f))
        elif cut:
            poster = frame(cut[len(cut) // 2][3], 1.5, os.path.join(WORK, "%s_poster.jpg" % f))
        for sid, o in load(f, "picks_overrides.json").items():
            ranked.setdefault(sid, {"takes": []})["why"] = "by eye over the ranker's %s - %s" % (
                (ranked.get(sid) or {}).get("pick", "pick"), o["why"])
        data[f] = {"seq": seq, "ranked": ranked, "anchors": load(f, "anchors.json"),
                   "measured": load(f, "measured.json"), "cut": cut, "runtime": runtime,
                   "n_takes": n_takes, "poster": poster}
    data["_cost"] = seconds_of_logs()
    return data


def main():
    os.makedirs(WORK, exist_ok=True)
    data = gather()
    doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN,
                          bottomMargin=18 * mm, title="Three films, one RTX 5090 - a walkthrough",
                          author="comfy-studio", subject="The demo films of 2026-09-29: what was used and why")
    fr = Frame(MARGIN, 18 * mm, CW, PH - MARGIN - 18 * mm, id="f", leftPadding=0, rightPadding=0,
               topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="p", frames=[fr], onPage=on_page)])
    story = []
    cover(story, data)
    pipeline(story)
    for i, f in enumerate(FILMS, 2):
        film_section(story, i, f, data[f])
        if f == "dead-stock":
            physics_page(story, data)
    compositor_section(story, 5, data)
    engines_section(story, 6, data)
    seedance_section(story, 7, data)
    not_used(story, 8)
    cost_section(story, 9, data)
    reproduce(story, 10)
    doc.build(story)
    print("wrote %s (%.1f MB)" % (OUT, os.path.getsize(OUT) / 1e6))


if __name__ == "__main__":
    main()
