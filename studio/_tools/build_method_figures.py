#!/usr/bin/env python3
"""Build every figure the illustrated METHOD.pdf needs, from assets that exist on this box.

Nothing here invents a picture. Every figure is either a crop of an existing sample, a
contact sheet of files already in a pack, or - for the grade strip - one real frame run
through the EXACT ffmpeg filters studio/_tools/post.py ships.

    ~/.pdfvenv/bin/python build_figures.py
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
SAMPLES = os.path.join(STUDIO, "samples")
OUT = os.path.join(SAMPLES, "docs", "figures")
os.makedirs(OUT, exist_ok=True)

FONT_R = "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf"
FONT_B = "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf"


def font(sz, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT_R, sz)


def label_strip(paths, labels, cell_w=560, pad=8, title=None, cap_h=30):
    """A row of images with a caption bar over each."""
    ims = []
    for p in paths:
        im = Image.open(p).convert("RGB")
        h = int(im.height * cell_w / im.width)
        ims.append(im.resize((cell_w, h), Image.LANCZOS))
    row_h = max(i.height for i in ims)
    top = 34 if title else 0
    W = len(ims) * cell_w + (len(ims) + 1) * pad
    H = top + row_h + cap_h + 2 * pad
    canvas = Image.new("RGB", (W, H), (17, 17, 19))
    d = ImageDraw.Draw(canvas)
    if title:
        d.text((pad, 9), title, font=font(19, True), fill=(255, 214, 102))
    x = pad
    for im, lab in zip(ims, labels):
        canvas.paste(im, (x, top + cap_h))
        d.text((x + 4, top + 7), lab, font=font(16, True), fill=(235, 235, 235))
        x += cell_w + pad
    return canvas


def grid(paths, labels, cols, cell_w=300, pad=6, title=None, cap_h=22):
    ims = []
    for p in paths:
        im = Image.open(p).convert("RGB")
        h = int(im.height * cell_w / im.width)
        ims.append(im.resize((cell_w, h), Image.LANCZOS))
    cell_h = max(i.height for i in ims)
    rows = (len(ims) + cols - 1) // cols
    top = 34 if title else 0
    W = cols * cell_w + (cols + 1) * pad
    H = top + rows * (cell_h + cap_h + pad) + pad
    canvas = Image.new("RGB", (W, H), (17, 17, 19))
    d = ImageDraw.Draw(canvas)
    if title:
        d.text((pad, 9), title, font=font(19, True), fill=(255, 214, 102))
    for i, (im, lab) in enumerate(zip(ims, labels)):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = top + pad + r * (cell_h + cap_h + pad)
        canvas.paste(im, (x, y + cap_h))
        d.text((x + 3, y + 3), lab, font=font(14, True), fill=(215, 215, 215))
    return canvas


def save(im, name):
    p = os.path.join(OUT, name)
    im.save(p, quality=90)
    print("  %-34s %5d x %-5d" % (name, im.width, im.height))
    return p


def stack(items, width, title, pad=10, cap_h=30):
    """items: [(path, label)] stacked vertically, each scaled to `width`."""
    ims = []
    for p, lab in items:
        im = Image.open(p).convert("RGB")
        h = int(im.height * width / im.width)
        ims.append((im.resize((width, h), Image.LANCZOS), lab))
    top = 38
    H = top + sum(i.height + cap_h + pad for i, _ in ims) + pad
    canvas = Image.new("RGB", (width + 2 * pad, H), (17, 17, 19))
    d = ImageDraw.Draw(canvas)
    d.text((pad, 10), title, font=ImageFont.truetype(FONT_B, 21), fill=(255, 214, 102))
    y = top
    for im, lab in ims:
        d.text((pad + 3, y + 5), lab, font=ImageFont.truetype(FONT_B, 17), fill=(235, 235, 235))
        canvas.paste(im, (pad, y + cap_h))
        y += im.height + cap_h + pad
    return canvas



# ---------------------------------------------------------------- 1. the pack
def fig_pack():
    d = os.path.join(STUDIO, "foundry", "characters", "terra")
    order = [
        ("base_portrait.png", "portrait"),
        ("face_front.png", "face front"),
        ("face_three_quarter.png", "face 3/4"),
        ("face_side.png", "face side"),
        ("turn_front.png", "turn front"),
        ("turn_front_three_quarter.png", "turn 3/4"),
        ("turn_side.png", "turn side"),
        ("turn_back_three_quarter.png", "turn back 3/4"),
        ("turn_back.png", "turn back"),
        ("base_fullbody.png", "full body"),
        ("expr_neutral.png", "neutral"),
        ("expr_joy.png", "joy"),
        ("expr_anger.png", "anger"),
        ("expr_sorrow.png", "sorrow"),
        ("expr_fear.png", "fear"),
        ("expr_surprise.png", "surprise"),
        ("pres_hero.png", "hero"),
        ("pres_wide.png", "wide"),
        ("pres_low.png", "low"),
        ("seed_source.png", "seed source"),
    ]
    paths, labs = [], []
    for f, lab in order:
        p = os.path.join(d, f)
        if os.path.exists(p):
            paths.append(p)
            labs.append(lab)
    return save(grid(paths, labs, cols=5, cell_w=250,
                     title="A pack is twenty pictures of one person - Terra, complete"),
                "fig_pack.jpg")


# ------------------------------------------------------------ 2. plate + shots
def fig_plate():
    plate = os.path.join(STUDIO, "foundry", "places", "forest-shrine", "dawn_wide.png")
    fp = os.path.join(STUDIO, "films", "the-method---worked-example")
    film = json.load(open(os.path.join(fp, "film.json"), encoding="utf-8"))
    posters = []
    for sid in sorted(film["shots"]):
        s = film["shots"][sid]
        pick = s.get("picked")
        for t in s.get("takes") or []:
            if t.get("id") == pick and t.get("poster"):
                posters.append((sid, os.path.join(fp, t["poster"])))
                break
    paths = [plate] + [p for _, p in posters[:5]]
    labs = ["the plate - dawn_wide"] + ["shot %s" % s for s, _ in posters[:5]]
    return save(grid(paths, labs, cols=3, cell_w=430,
                     title="One plate, five shots - the room is the same because the picture is"),
                "fig_plate.jpg")


# ------------------------------------------------------------------ 3. grades
GRADES = [
    ("none", None),
    ("soft", "eq=contrast=1.06:saturation=1.12"),
    ("filmic  (default)",
     "curves=all='0/0.02 0.22/0.26 0.5/0.58 0.78/0.88 1/0.995',"
     "eq=saturation=1.22,colorbalance=gm=-0.05:rm=0.05:bh=0.03"),
    ("punchy",
     "curves=all='0/0.02 0.22/0.28 0.5/0.60 0.78/0.88 1/0.995',eq=saturation=1.42"),
]


def fig_grades(src):
    made = []
    for name, vf in GRADES:
        slug = name.split()[0]
        dst = os.path.join(OUT, "_grade_%s.png" % slug)
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", src]
        if vf:
            cmd += ["-vf", vf]
        cmd += ["-frames:v", "1", dst]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print("  ffmpeg failed for %s: %s" % (name, r.stderr[:200]))
            return None
        made.append((dst, name))
    return save(label_strip([p for p, _ in made], [n for _, n in made], cell_w=470,
                            title="The four looks, on one real frame - post.py's own filters"),
                "fig_grades.jpg")


# ------------------------------------------------------------ 4. worked example
def fig_example():
    fp = os.path.join(STUDIO, "films", "the-method---worked-example")
    film = json.load(open(os.path.join(fp, "film.json"), encoding="utf-8"))
    paths, labs = [], []
    for sid in sorted(film["shots"]):
        s = film["shots"][sid]
        pick = s.get("picked")
        for t in s.get("takes") or []:
            if t.get("id") == pick and t.get("poster"):
                paths.append(os.path.join(fp, t["poster"]))
                labs.append("%s  %s" % (sid, (s.get("title") or "")[:26]))
                break
    return save(grid(paths, labs, cols=4, cell_w=420,
                     title="The worked example as built - eight shots, one scene, one anchor"),
                "fig_example.jpg")


# ----------------------------------------------------------------- 5. cameras
def fig_cameras():
    d = os.path.join(SAMPLES, "cameras")
    want = [("push", "push in"), ("pull", "pull back"), ("orbit", "orbit"),
            ("handheld", "handheld"), ("pan_l", "pan left"), ("dolly_zoom", "dolly zoom")]
    paths, labs = [], []
    for f, lab in want:
        p = os.path.join(d, f + ".jpg")
        if os.path.exists(p):
            paths.append(p)
            labs.append(lab)
    return save(grid(paths, labs, cols=3, cell_w=430,
                     title="Give the camera a job - the studio performs these, measured after"),
                "fig_cameras.jpg")


def fig_identity_and_timecode():
    qc = os.path.join(SAMPLES, "qwen_character", "_sheets")
    save(stack([(os.path.join(qc, "X_A_control.jpg"),
                 "described in words only - three places, one description: three different faces"),
                (os.path.join(qc, "X_B2_photo_sheet.jpg"),
                 "shown a reference sheet - same three places: one person")],
               width=1010,
               title="Show, don't describe - the same two people, both ways"),
         "fig_identity.jpg")

    tc = os.path.join(SAMPLES, "timecode")
    save(stack([(os.path.join(tc, "C_time_noCUT_3_9_1234_strip.jpg"),
                 'timecodes in the prompt, the word "cut" absent - the beats dissolve into each other'),
                (os.path.join(tc, "D_ordinal+CUT_3_9_1234_strip.jpg"),
                 'the word "cut" present - t=3s is hull, t=4s is wheel: a hard cut')],
               width=1900,
               title="The word cut makes the cut - same seed, same beats, one word apart"),
         "fig_timecode.jpg")


def fig_photoreal_lora():
    """The LENGA identity strength ladder, as it was rendered - it carries its own labels."""
    src = os.path.join(SAMPLES, "loras", "lenga-identity-te__ladder.jpg")
    if not os.path.exists(src):
        print("  !! %s is gone; section Z loses its figure" % src)
        return None
    return save(Image.open(src).convert("RGB"), "fig_photoreal_lora.jpg")


if __name__ == "__main__":
    print("figures ->", OUT)
    fig_pack()
    fig_plate()
    fig_example()
    fig_cameras()
    fig_identity_and_timecode()
    fig_photoreal_lora()
    # a real frame from the worked example for the grade strip
    fp = os.path.join(STUDIO, "films", "the-method---worked-example")
    film = json.load(open(os.path.join(fp, "film.json"), encoding="utf-8"))
    src = None
    for sid in sorted(film["shots"]):
        s = film["shots"][sid]
        for t in s.get("takes") or []:
            if t.get("id") == s.get("picked") and t.get("poster"):
                src = os.path.join(fp, t["poster"])
                break
        if src:
            break
    if src:
        fig_grades(src)
    print("done")
