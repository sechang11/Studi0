#!/usr/bin/env python3
"""Crop the pictures the book uses, from renders and sheets already on the box.

The book shows single frames and single cells, never a whole contact sheet: a reader looks at one
thing at a time.  Every crop here is cut from a sheet whose geometry this repository wrote, or is
a whole asset (a pack view, a plate, a composed start frame) that needs no cutting.  Output goes
to studio/samples/docs/book/ with stable names the book text refers to.

    ~/.pdfvenv/bin/python studio/_tools/build_book_figures.py          # everything but the hero
    ~/.pdfvenv/bin/python studio/_tools/build_book_figures.py --hero   # frames from the opening film
"""
import argparse
import glob
import json
import os
import subprocess

from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STUDIO = os.path.join(ROOT, "studio")
OUT = os.path.join(STUDIO, "samples", "docs", "book")
S = os.path.join(STUDIO, "samples")
F = os.path.join(STUDIO, "foundry")


def save(im, name, q=88, maxw=1400):
    im = im.convert("RGB")
    if im.size[0] > maxw:
        im = im.resize((maxw, int(im.size[1] * maxw / im.size[0])), Image.LANCZOS)
    im.save(os.path.join(OUT, name), quality=q)
    print("  %-34s %dx%d" % (name, *im.size))


def cover(im, ratio):
    """crop to an aspect ratio (w/h), centred"""
    w, h = im.size
    if w / h > ratio:
        nw = int(h * ratio); x = (w - nw) // 2
        return im.crop((x, 0, x + nw, h))
    nh = int(w / ratio); y = (h - nh) // 2
    return im.crop((0, y, w, y + nh))


# ---- sheet geometries this repo wrote ------------------------------------------------------
def ladder_cell(path, col, row, cw=384, ch=494, pad=4, head=42):
    im = Image.open(path)
    x = pad + col * (cw + pad); y = head + pad + row * (ch + pad)
    return im.crop((x, y, x + cw, y + ch))


def strip_frame(path, i, fw, head=0):
    im = Image.open(path)
    return im.crop((i * fw, head, (i + 1) * fw, im.size[1]))


def frame_at(video, t):
    """one frame from a video at t seconds, as a temporary png; None if it cannot be read"""
    dest = "/tmp/_bookframe_%d.png" % int(t * 100)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "%.2f" % t, "-i", video, "-frames:v", "1", dest],
                   capture_output=True)
    return dest if os.path.exists(dest) else None


def upscale_ab_cell(path, row, col, cw=640, ch=400, gap=8, head=22):
    im = Image.open(path)
    x = col * (cw + gap); y = row * (ch + head) + head
    return im.crop((x, y, x + cw, y + ch))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hero", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    if not a.hero:
        # the library: a pack and a plate
        for v in ("base_portrait", "turn_front", "turn_side", "turn_back", "expr_joy", "expr_sorrow",
                  "expr_anger", "pres_wide"):
            p = os.path.join(F, "characters", "terra", v + ".png")
            if os.path.exists(p):
                save(Image.open(p), "pack_%s.jpg" % v, maxw=700)
        for pl in ("night_wide", "night_detail", "dawn_wide"):
            p = os.path.join(F, "places", "night-market", pl + ".png")
            if os.path.exists(p):
                save(Image.open(p), "plate_nightmarket_%s.jpg" % pl)
        p = os.path.join(F, "places", "forest-shrine", "dawn_wide.png")
        if os.path.exists(p):
            save(Image.open(p), "plate_forestshrine_dawn.jpg")

        # the shrine example: composed start frames and the finished strip, frame by frame
        ex = os.path.join(STUDIO, "films", "the-method---worked-example", "assets")
        for sid in ("060", "070", "080"):
            p = os.path.join(ex, "anchor_shot_%s.png" % sid)
            if os.path.exists(p):
                save(Image.open(p), "shrine_anchor_%s.jpg" % sid)
        # frames from the finished shrine film at full resolution, not from its 256-px strip
        shrine_mp4 = os.path.join(STUDIO, "films", "the-method---worked-example", "assets", "film.mp4")
        if os.path.exists(shrine_mp4):
            for t, name in ((2.5, "shrine_frame_wide"), (8.5, "shrine_frame_medium"), (13.0, "shrine_frame_close")):
                p = frame_at(shrine_mp4, t)
                if p:
                    save(Image.open(p), "%s.jpg" % name, maxw=1200); os.remove(p)

        # the trained face: strength ladder cells - off vs on, same seed
        lad = os.path.join(S, "loras", "lenga-identity-fb__ladder.jpg")
        if os.path.exists(lad):
            save(ladder_cell(lad, 0, 1), "ladder_identity_off.jpg", maxw=600)
            save(ladder_cell(lad, 3, 1), "ladder_identity_on.jpg", maxw=600)
        lad = os.path.join(S, "loras", "lenga-costume-lb3__ladder.jpg")
        if os.path.exists(lad):
            save(ladder_cell(lad, 0, 0), "ladder_costume_off.jpg", maxw=600)
            save(ladder_cell(lad, 1, 0), "ladder_costume_040.jpg", maxw=600)
            save(ladder_cell(lad, 2, 0), "ladder_costume_100.jpg", maxw=600)
        lad = os.path.join(S, "loras", "crown-leblanc__ladder.jpg")
        if os.path.exists(lad):
            save(ladder_cell(lad, 0, 0), "ladder_crown_off.jpg", maxw=600)
            save(ladder_cell(lad, 2, 0), "ladder_crown_on.jpg", maxw=600)
            save(ladder_cell(lad, 2, 1), "ladder_crown_wide_on.jpg", maxw=600)

        # timecodes: the same beat, ordinal vs with the word cut - frames either side of each boundary,
        # from the clips themselves
        tc = os.path.join(S, "timecode")
        for name, fn in (("tc_ordinal", "A_ordinal_3_9_1234.mp4"), ("tc_cut", "D_ordinal+CUT_3_9_1234.mp4")):
            p = os.path.join(tc, fn)
            if os.path.exists(p):
                for t in (2, 3, 8, 9):
                    fr = frame_at(p, t + 0.5)
                    if fr:
                        save(Image.open(fr), "%s_t%d.jpg" % (name, t), maxw=800); os.remove(fr)

        # the finish: fast vs fine vs bicubic at 1:1
        ab = os.path.join(S, "hybrid", "upscale_fast_vs_fine.jpg")
        if os.path.exists(ab):
            save(upscale_ab_cell(ab, 0, 1), "upscale_bicubic.jpg", maxw=640)
            save(upscale_ab_cell(ab, 1, 1), "upscale_fast.jpg", maxw=640)
            save(upscale_ab_cell(ab, 2, 1), "upscale_fine.jpg", maxw=640)

        # the sharpened start frame that made the take worse
        for name, fn in (("sharpen_control", "encyclopedia-check_160_sharpened.png"),):
            p = os.path.join(S, "hybrid", fn)
            if os.path.exists(p):
                save(Image.open(p), "%s.jpg" % name, maxw=900)

        # ref2va: the reference route that carried nothing - one full-resolution frame each
        rv = os.path.join(S, "ref2va")
        for name, fn in (("ref2va_terra", "ref_turbo_s4_4200.mp4"),
                         ("ref2va_photoreal", "ref_tomas-reyl_medium_turbo_s4_4200.mp4")):
            p = os.path.join(rv, fn)
            if os.path.exists(p):
                fr = frame_at(p, 2.5)
                if fr:
                    save(Image.open(fr), "%s.jpg" % name, maxw=1200); os.remove(fr)

        # the other session's composed figures, kept whole for the web page
        for fn in ("fig_identity.jpg", "fig_grades.jpg", "fig_cameras.jpg", "fig_photoreal_lora.jpg", "fig_pack.jpg"):
            p = os.path.join(S, "docs", "figures", fn)
            if os.path.exists(p):
                save(Image.open(p), fn)
        # ...and cut cell by cell for the book, which shows one picture at a time. The identity
        # figure is 1030x1648: three 330-px columns; the woman's row of the "described in words"
        # block starts at y=133 and her row of the "shown a reference" block at y=933 (measured
        # from the dark gutters of the sheet).
        fi = os.path.join(S, "docs", "figures", "fig_identity.jpg")
        if os.path.exists(fi):
            im = Image.open(fi)
            if im.size == (1030, 1648):
                for tag, y0 in (("prose", 133), ("ref", 933)):
                    for k, x0 in enumerate((16, 350, 685)):
                        save(im.crop((x0, y0, x0 + 329, y0 + 329)), "identity_%s_%d.jpg" % (tag, k + 1), maxw=600)
        # the four looks, one panel each - measured on the book's 1400x252 copy saved just above
        # (343-px panels under a 46-px header), so cut from that copy, not the wider source
        fg = os.path.join(OUT, "fig_grades.jpg")
        if os.path.exists(fg):
            im = Image.open(fg)
            if im.size == (1400, 252):
                for name, x0 in (("none", 6), ("soft", 354), ("filmic", 703), ("punchy", 1051)):
                    save(im.crop((x0, 46, x0 + 343, 241)), "grade_%s.jpg" % name, maxw=700)
        return

    # ---- the hero film ------------------------------------------------------------------
    rep = json.load(open(os.path.join(OUT, "hero.json"), encoding="utf-8"))
    fid = rep["film"]
    fdir = os.path.join(STUDIO, "films", fid)
    final = os.path.join(fdir, "assets", "film.mp4")
    if os.path.exists(final):
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                    "csv=p=0", final], capture_output=True, text=True).stdout.strip() or 0)
        # one frame from the middle of each shot, from the finished master
        t = 0.0
        for i, sh in enumerate(rep["shots"]):
            d = float(sh.get("duration") or 5)
            mid = t + d * 0.55
            dest = os.path.join(OUT, "hero_%02d.png" % (i + 1))
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "%.2f" % min(mid, max(dur - 0.1, 0)),
                            "-i", final, "-frames:v", "1", dest], capture_output=True)
            if os.path.exists(dest):
                im = Image.open(dest)
                save(im, "hero_%02d.jpg" % (i + 1), maxw=1600)
                if i == 2:      # the lantern shot carries the cover: portrait crop, 2:3
                    save(cover(im, 2 / 3.0), "hero_cover.jpg", q=90, maxw=1200)
                os.remove(dest)
            t += d
        # a one-frame-a-second strip of the whole film, for the "how it was made" spread
        d = "/tmp/hero_strip"
        subprocess.run(["rm", "-rf", d]); os.makedirs(d)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", final, "-vf", "fps=1,scale=320:-2",
                        os.path.join(d, "f%03d.png")], capture_output=True)
        fs = sorted(os.listdir(d))
        ims = [Image.open(os.path.join(d, f)).convert("RGB") for f in fs]
        if ims:
            w, h = ims[0].size
            cols = 6
            rows = (len(ims) + cols - 1) // cols
            sheet = Image.new("RGB", (w * cols, h * rows), (20, 18, 16))
            for i, im in enumerate(ims):
                sheet.paste(im, ((i % cols) * w, (i // cols) * h))
            save(sheet, "hero_strip.jpg", q=86, maxw=1600)
    # each shot's composed start frame and picked strip
    f = json.load(open(os.path.join(fdir, "film.json"), encoding="utf-8"))
    for i, sh in enumerate(rep["shots"]):
        sid = sh["shot"]
        shot = f["shots"].get(sid) or {}
        anc = (shot.get("anchor") or "")
        anc = anc[5:] if anc.startswith("file:") else os.path.join(fdir, "assets", "anchor_shot_%s.png" % sid)
        if os.path.exists(anc):
            save(Image.open(anc), "hero_anchor_%02d.jpg" % (i + 1), maxw=1200)
        tk = next((t for t in shot.get("takes") or [] if t["id"] == shot.get("picked")), None)
        if tk and tk.get("strip") and os.path.exists(os.path.join(fdir, tk["strip"])):
            save(Image.open(os.path.join(fdir, tk["strip"])), "hero_take_strip_%02d.jpg" % (i + 1), maxw=1400)

    # the takes that were NOT kept, frame by frame - the book teaches from them.  The strip is
    # six frames across a take, so strip index i is the moment (i + 0.5) / 6 of the way through;
    # the frame is cut from the take's video at full size, not from the 200-px strip.  The first
    # take whose QC names the fault is the one shown.
    def take_frames(tk, idxs, name):
        p = os.path.join(fdir, tk.get("file") or "")
        if not os.path.exists(p):
            return
        dur = float(tk.get("duration") or 0) or 4.0
        for k, i in enumerate(idxs):
            fr = frame_at(p, min((i + 0.5) * dur / 6.0, dur - 0.05))
            if fr:
                save(Image.open(fr), "%s_%s.jpg" % (name, "abcdef"[k]), maxw=800); os.remove(fr)

    def first_take_with(sid, needle):
        for t in (f["shots"].get(sid) or {}).get("takes") or []:
            if any(needle in q for q in (t.get("qc") or [])) and t.get("file"):
                return t
        return None

    for sid, needle, idxs, name in (("040", "scene drift", (1, 4), "hero_fault_040"),
                                    ("050", "people appeared", (0, 4), "hero_fault_050"),
                                    ("010", "push in 2", (0, 5), "hero_fault_010"),
                                    ("020", "ends closer", (0, 5), "hero_fault_020")):
        tk = first_take_with(sid, needle)
        if tk:
            take_frames(tk, idxs, name)
    # shot three's first take: a stranger walks through the foreground - no QC line names it,
    # so it is simply the earliest take
    t030 = ((f["shots"].get("030") or {}).get("takes") or [{}])[0]
    if t030.get("file"):
        take_frames(t030, (0, 3), "hero_fault_030")


if __name__ == "__main__":
    main()
