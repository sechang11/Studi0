#!/usr/bin/env python3
"""Does a style LoRA rescue the styles the base model CANNOT do?

    python3 studio/_tools/lora_rescue.py --pilot
    python3 studio/_tools/lora_rescue.py --styles risograph,claymation
    python3 studio/_tools/lora_rescue.py --sheets-only

THE QUESTION. 13 style cards in studio/styles/ are status=unavailable and 25 are weak, and
their verdict fields say exactly how each failed. A large group failed the same way: the
base model has no concept of the MEDIUM, so it drew the medium as an object in the scene
instead (a chalkboard on the wall, a riso-coloured rectangle over a photo, a plate of food)
or simply ignored it. The one mechanism on this box measured to move Qwen off photography
is a LoRA - illustration-1.0-qwen-image did what no prompt at any cfg could. So: does that
LoRA, or either of the other two qwen style LoRAs, put the medium back?

ISOLATION, copied verbatim from studio/_tools/style_examples.py, which is how every verdict
in the styles library was measured. Same subject prose, same seed 5150, same 1024x1024, same
negative assembly, same workflow. The ONLY thing that moves between cells in a row is node 7
of workflows/13_qwen_t2i_styled.json - the LoRA name and its strength. A comparison against
a differently-seeded or differently-prompted control would demonstrate nothing, and this
project has made that mistake before.

EVERY ROW IS RENDERED ON QWEN, including the styles whose card routes them to `anime`. Five
of the candidates (risograph, comic_halftone, stop_motion_felt, scratchboard, pointillism)
carry engine=anime, but all three style LoRAs installed here are qwen-based and a LoRA is a
delta on specific weights - an animagine engine cannot load them at all. The relevant fact
for those cards is the qwen half of their verdict, which style_examples.py --all-engines
recorded.

THE PLAIN ROW (`_plain`, no style card at all) is the control that makes the rest mean
something. If the illustration LoRA turns the bare subject into a painting, then a painted
risograph cell is the LoRA painting everything, not the LoRA rescuing risograph. Read that
row first.
"""
import argparse, glob, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, HOST          # noqa: E402

STYLES = os.path.join(STUDIO, "styles")
OUT = os.path.join(STUDIO, "samples", "lora_rescue")
CELLS = os.path.join(OUT, "cells")
PNGDIR = "/tmp/lora_rescue_png"

SEED = 5150
SIZE = 1024
SUBJ_PROSE = ("a young woman in a wool coat and red scarf standing on a city street, "
              "buildings receding behind her, overcast daylight, facing the camera")
NEG_BASE = "lowres, worst quality, bad anatomy, bad hands, watermark, text, signature"

ILLUS = "illustration-1.0-qwen-image.safetensors"
MODERN = "qwen_image_modern_anime_lora.safetensors"
STORY = "qwen_image_2512_storybook_anime_lora.safetensors"

# key, sheet label, lora file, strength, trigger phrase appended to the prose
VARIANTS = [
    ("a_control",  "A  no LoRA (control)",        None,   0.0, ""),
    ("b_illus10",  "B  illustration @ 1.0",       ILLUS,  1.0, ""),
    ("c_illus15",  "C  illustration @ 1.5",       ILLUS,  1.5, ""),
    ("d_modern10", "D  modern_anime @ 1.0",       MODERN, 1.0, ""),
    ("e_modern15", "E  modern_anime @ 1.5",       MODERN, 1.5, ""),
    ("f_story10",  "F  storybook @ 1.0",          STORY,  1.0, ""),
    ("g_story10t", "G  storybook @ 1.0 + TRIGGER", STORY, 1.0, "storybook anime illustration"),
    # second pass, run only on the candidates that survived the first look
    ("h_illus06",  "H  illustration @ 0.6",       ILLUS,  0.6, ""),
    ("i_illus08",  "I  illustration @ 0.8",       ILLUS,  0.8, ""),
    ("j_illus12",  "J  illustration @ 1.2",       ILLUS,  1.2, ""),
]
VMAP = {v[0]: v for v in VARIANTS}

# The five the brief named, plus five more that failed the same way (the medium was drawn as
# an object, or never arrived), plus four that already WORK on qwen and are here as controls:
# if a LoRA damages those, that is a cost the rescue has to be weighed against.
CANDIDATES = ["risograph", "stop_motion_felt", "screenprint_poster", "comic_halftone",
              "thermal_imaging", "papercut_collage", "chalkboard", "technical_diagram",
              "scratchboard", "pointillism"]
CONTROLS = ["claymation", "eight_bit", "blueprint", "noir_comic"]
ROWS = ["_plain"] + CANDIDATES + CONTROLS
PILOT = ["_plain", "risograph", "comic_halftone", "claymation"]


# What was seen, written down next to the pixels rather than only in a chat message. The
# style cards carry the per-style verdicts; these are the findings that belong to the LAYER
# rather than to any one style, and they are the ones a reader of a style card would miss.
FINDINGS = [
    "THE ILLUSTRATION LoRA DOES NOT PAINT EVERYTHING, WHICH IS WHY A RESCUE MEANS "
    "SOMETHING. On the _plain row - the bare subject with no style card at all - "
    "illustration at 1.0 returns a PHOTOGRAPH. It only takes over the whole image "
    "unprompted at 1.5. So the felt puppet and the pointillist figure are the LoRA and the "
    "style prose acting together, not the LoRA imposing a house look.",

    "THE STORYBOOK LoRA'S TRIGGER PHRASE IS EVERYTHING, AND THAT SETTLES THE STANDING BUG. "
    "qwen_image_2512_storybook_anime at 1.0 with no trigger leaves a photograph "
    "(mean |delta| 18.1/255 against the control - a different photograph, same idiom). The "
    "same LoRA at the same strength with 'storybook anime illustration' appended returns a "
    "complete flat-colour anime illustration (41.7/255). Every qwen keyframe this project "
    "made before the slot was fixed carried this LoRA at 0.8 UNTRIGGERED - so it was "
    "shifting composition without ever contributing its idiom.",

    "qwen_image_modern_anime IS NOT A NO-OP, IT IS A NON-STYLE. Its card says it 'did "
    "nothing' at 1.0. Measured here it moves the pixels a lot - mean |delta| 15.9/255 on "
    "the plain row, 36% of pixels past 16/255 - but every single one of the 15 rows comes "
    "back photographic at 1.0 AND at 1.5. It changes the picture and never changes the "
    "medium. MAP 1 found no trigger phrase in the file, so the trigger half of the question "
    "is still open; the strength half is now closed - 1.5 does not help.",

    "EVERY LoRA COMPRESSES THE DIFFERENCES BETWEEN STYLES. Mean pairwise pixel distance "
    "across four different styles at the same setting: 45.4 with no LoRA, 40.7 at "
    "illustration 1.5, 35.7 at illustration 1.0, and 32-33 for all three of modern_anime "
    "and storybook. A style LoRA buys a missing medium at the price of the styles it "
    "flattens together.",

    "IT DAMAGES STYLES THAT ALREADY WORKED - the control rows are the bill. noir_comic is "
    "a clean high-contrast B&W ink comic without a LoRA; at illustration 1.0 colour leaks "
    "back into the coat and at 1.5 the whole frame returns to tan and brown, which is the "
    "one thing that style is defined by not having. claymation loses its thumbprint clay "
    "surface at illustration 1.5 and is pushed back toward PHOTOGRAPHY by modern_anime at "
    "1.0 and 1.5. eight_bit is the exception in the other direction: storybook at 1.0 gives "
    "it a more coherent pixel grid and a flat drawn background instead of a bokeh "
    "photograph. Do not set a style LoRA globally.",

    "THE FAILURE MODE SURVIVES THE LoRA BECAUSE IT IS SEMANTIC, NOT STYLISTIC. Every style "
    "whose failure was 'the medium got drawn as an object in the scene' - chalkboard, "
    "technical_diagram, papercut_collage, thermal_imaging, risograph, screenprint_poster - "
    "kept that failure under all six LoRA settings. illustration at 1.5 sometimes DELETES "
    "the object (the riso rectangle, the torn-paper frame) but replaces it with its own "
    "idiom rather than with the style. The two rescues, felt and pointillism, are both "
    "styles whose failure was 'the surface never arrived' - and a surface is what a LoRA "
    "changes.",
]

RESULTS = {
    "stop_motion_felt": "RESCUED at illustration 1.0. Needle-felted puppet with hand "
                        "stitching and macro depth of field; control is a photograph. "
                        "4 seeds, 5 strengths.",
    "pointillism":      "RESCUED at illustration 1.2. Genuine optical mixing on the "
                        "figure; the background never becomes divisionist. 4 seeds.",
    "comic_halftone":   "PARTIAL at illustration 1.0. Real ink comic and sometimes a "
                        "tonal flesh screen; the Ben-Day screen as a colour mechanism does "
                        "not arrive, and at 1.5 the dots become polka dots on the coat.",
    "risograph":        "NOT RESCUED. No misregistration, overprint or bare paper at any "
                        "setting; the spot ink colours arrive as paint.",
    "screenprint_poster": "NOT RESCUED. Garbled lettering at all seven settings.",
    "thermal_imaging":  "NOT RESCUED. The ramp stays painted on the garment, or is deleted "
                        "entirely. False colour is a global remap - a look, not a style.",
    "papercut_collage": "NOT RESCUED. The torn-paper frame survives six of seven.",
    "chalkboard":       "NOT RESCUED. The board stays a prop in all seven.",
    "technical_diagram": "NOT RESCUED. The diagram stays an overlay in all seven.",
    "scratchboard":     "NOT RESCUED. Never inverts to white line on black.",
    "claymation":       "CONTROL, damaged. illustration 1.5 removes the clay; "
                        "modern_anime pushes it back to photography.",
    "noir_comic":       "CONTROL, damaged. illustration reintroduces colour, which is the "
                        "one thing this style is defined by not having.",
    "eight_bit":        "CONTROL, improved by storybook 1.0 - a more coherent pixel grid "
                        "and a drawn background instead of a photographic one.",
    "blueprint":        "CONTROL, mixed. illustration 1.5 turns the whole frame into a "
                        "drafting sheet but keeps a coloured coat, which a cyanotype "
                        "cannot have.",
    "_plain":           "CONTROL ROW. illustration 1.0 is still a photograph; 1.5 is not.",
}


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def card(name):
    if name == "_plain":
        return {"id": "_plain", "name": "NO STYLE (bare subject)", "prose": "",
                "negative_add": "", "status": "n/a", "engine": "qwen", "verdict":
                "The control row. Whatever a LoRA does here it does to everything."}
    return json.load(open(os.path.join(STYLES, name + ".json"), encoding="utf-8"))


def tag(name, variant):
    """Filename stem. The default seed is unsuffixed so the first pass keeps its names;
    a seed-robustness pass writes alongside it rather than overwriting it."""
    return "%s__%s%s" % (name, variant, "" if SEED == 5150 else "__s%d" % SEED)


def build(st, variant):
    _, _, lora, strength, trigger = VMAP[variant]
    wf = load_wf("13_qwen_t2i_styled.json")
    prose = SUBJ_PROSE
    if st.get("prose"):
        prose = prose + ". " + st["prose"]
    if trigger:
        prose = prose + ". " + trigger
    neg = NEG_BASE
    if st.get("negative_add"):
        neg = neg + ", " + st["negative_add"]
    set_path(wf, "10.inputs.text", prose)
    set_path(wf, "11.inputs.text", neg)
    set_path(wf, "12.inputs.width", SIZE)
    set_path(wf, "12.inputs.height", SIZE)
    set_path(wf, "13.inputs.seed", SEED)
    # node 7 is the slot. When no LoRA is wanted the strength goes to 0.0 and ComfyUI's
    # LoraLoader short-circuits before it opens the file, so the name is inert.
    set_path(wf, "7.inputs.lora_name", lora or STORY)
    set_path(wf, "7.inputs.strength_model", strength)
    return wf, prose, neg


def render(name, variant, force=False):
    st = card(name)
    stem = tag(name, variant)
    png = os.path.join(PNGDIR, stem + ".png")
    webp = os.path.join(CELLS, stem + ".webp")
    if os.path.exists(png) and os.path.exists(webp) and not force:
        return png, "cached"
    wf, prose, neg = build(st, variant)
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/lora_rescue/" + stem)
    try:
        _, outs = run(HOST, wf, quiet=True)
    except Exception as e:
        return None, "FAILED %s" % str(e)[:70]
    if not outs:
        return None, "no output"
    os.makedirs(PNGDIR, exist_ok=True)
    os.makedirs(CELLS, exist_ok=True)
    loc = ensure_local(outs[0], png, required=False)
    if not loc:
        return None, "could not fetch"
    sh("ffmpeg", "-y", "-v", "error", "-i", png, "-quality", "92", webp)
    return png, "%.0f KB" % (os.path.getsize(png) / 1024)


# ---------------------------------------------------------------- contact sheets
def font(size):
    from PIL import ImageFont
    for p in ("/usr/share/fonts/liberation-sans/LiberationSans-Bold.ttf",
              "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf",
              "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/open-sans/OpenSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    hits = glob.glob("/usr/share/fonts/**/*Bold*.ttf", recursive=True)
    if hits:
        return ImageFont.truetype(hits[0], size)
    return ImageFont.load_default()


def wrap(draw, text, fnt, width):
    out, line = [], ""
    for w in text.split():
        t = (line + " " + w).strip()
        if draw.textlength(t, font=fnt) <= width:
            line = t
        else:
            out.append(line)
            line = w
    if line:
        out.append(line)
    return out


def sheet(name, variants, cell=480, cols=4):
    """One style, every LoRA variant, labelled. Read this with your eyes."""
    from PIL import Image, ImageDraw
    st = card(name)
    have = [(v, os.path.join(PNGDIR, tag(name, v) + ".png")) for v in variants]
    have = [(v, p) for v, p in have if os.path.exists(p)]
    if not have:
        return None
    rows = (len(have) + cols - 1) // cols
    lab, pad, head = 30, 8, 96
    W = cols * (cell + pad) + pad
    H = head + rows * (cell + lab + pad) + pad
    im = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(im)
    f_title, f_sub, f_lab = font(30), font(17), font(20)
    d.text((pad + 4, 10), "%s   [%s]   seed %d" % (st.get("id"), st.get("status"), SEED),
           font=f_title, fill=(255, 255, 255))
    sub = "was: " + (st.get("verdict") or "")
    for i, ln in enumerate(wrap(d, sub, f_sub, W - 2 * pad - 8)[:2]):
        d.text((pad + 4, 46 + i * 21), ln, font=f_sub, fill=(170, 170, 180))
    for i, (v, p) in enumerate(have):
        cx = pad + (i % cols) * (cell + pad)
        cy = head + (i // cols) * (cell + lab + pad)
        d.rectangle([cx, cy, cx + cell, cy + lab - 2], fill=(45, 45, 52))
        d.text((cx + 6, cy + 5), VMAP[v][1], font=f_lab, fill=(240, 240, 120))
        img = Image.open(p).convert("RGB").resize((cell, cell), Image.LANCZOS)
        im.paste(img, (cx, cy + lab))
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "sheet_%s%s.jpg"
                       % (name, "" if SEED == 5150 else "__s%d" % SEED))
    im.save(dst, quality=92)
    return dst


def column(variant, names, cell=380, cols=4):
    """One LoRA setting across every style, so a LoRA's own signature is visible."""
    from PIL import Image, ImageDraw
    have = [(n, os.path.join(PNGDIR, tag(n, variant) + ".png")) for n in names]
    have = [(n, p) for n, p in have if os.path.exists(p)]
    if not have:
        return None
    rows = (len(have) + cols - 1) // cols
    lab, pad, head = 28, 8, 52
    W = cols * (cell + pad) + pad
    H = head + rows * (cell + lab + pad) + pad
    im = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(im)
    d.text((pad + 4, 12), "ALL STYLES  --  %s" % VMAP[variant][1], font=font(28),
           fill=(255, 255, 255))
    f_lab = font(19)
    for i, (n, p) in enumerate(have):
        cx = pad + (i % cols) * (cell + pad)
        cy = head + (i // cols) * (cell + lab + pad)
        d.rectangle([cx, cy, cx + cell, cy + lab - 2], fill=(45, 45, 52))
        d.text((cx + 6, cy + 4), n, font=f_lab, fill=(120, 230, 240))
        im.paste(Image.open(p).convert("RGB").resize((cell, cell), Image.LANCZOS),
                 (cx, cy + lab))
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "column_%s.jpg" % variant)
    im.save(dst, quality=92)
    return dst


def main():
    global SEED
    ap = argparse.ArgumentParser()
    ap.add_argument("--styles", help="comma list, default every row")
    ap.add_argument("--variants", help="comma list, default all seven")
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--sheets-only", action="store_true")
    ap.add_argument("--columns", action="store_true")
    ap.add_argument("--seed", type=int, default=SEED,
                    help="a rescue seen at one seed is an anecdote; re-run the survivors "
                         "at other seeds before writing it onto a card")
    a = ap.parse_args()

    SEED = a.seed
    names = PILOT if a.pilot else ROWS
    if a.styles:
        names = [s.strip() for s in a.styles.split(",") if s.strip()]
    variants = [v[0] for v in VARIANTS]
    if a.variants:
        variants = [v.strip() for v in a.variants.split(",") if v.strip()]

    if not a.sheets_only:
        for n in names:
            for v in variants:
                png, msg = render(n, v, a.force)
                print("  %-20s %-12s %s" % (n, v, msg), flush=True)

    made = []
    for n in names:
        s = sheet(n, variants)
        if s:
            made.append(s)
    if a.columns:
        for v in variants:
            c = column(v, names)
            if c:
                made.append(c)
    for m in made:
        print("SHEET %s  %.0f KB" % (m, os.path.getsize(m) / 1024))

    man = {"seed": SEED, "size": SIZE, "subject": SUBJ_PROSE, "negative_base": NEG_BASE,
           "workflow": "13_qwen_t2i_styled.json", "slot": "node 7",
           "seeds_used": [5150, 7, 99999, 314159],
           "variants": [{"key": v[0], "label": v[1], "lora": v[2], "strength": v[3],
                         "trigger": v[4]} for v in VARIANTS],
           "rows": ROWS, "results": RESULTS, "findings": FINDINGS,
           "blocker": "stop_motion_felt, pointillism and comic_halftone all carry "
                      "engine=anime on their style card. Every style LoRA installed on this "
                      "box is qwen-based, so compose.resolve_style_lora() correctly refuses "
                      "the recommendation these cards now make until their engine field is "
                      "changed to qwen. The engine field was outside this task's ownership "
                      "and was NOT changed."}
    os.makedirs(OUT, exist_ok=True)
    json.dump(man, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"),
              indent=2)
    print("\nNOW LOOK AT THE SHEETS. Read the _plain row first: it separates 'the LoRA "
          "rescued this style' from 'the LoRA paints everything'.")


if __name__ == "__main__":
    main()
