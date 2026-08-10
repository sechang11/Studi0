#!/usr/bin/env python3
"""Turn one image into a full character: description, reference sheet, and a card.

    python3 studio/_tools/character_new.py --image ref.png --name "MARGIT" \\
        --style "dark fantasy tabletop illustration, painted in gouache and ink"
    python3 studio/_tools/character_new.py --image ref.png --name X --caption-only
    python3 studio/_tools/character_new.py --list-sources          # what is browsable

WHAT THE SOURCE IMAGE IS, AND IS NOT. It is a STARTING POINT, not the identity. This
project measured the alternative and it does not work: an IPAdapter reference at any weight
transports hair mass, garment colour and the presence of eyewear but not a face - a costume,
not a person - and the usable band tops out around 0.60 before composition breaks. So the
source is used two ways that DO work, and never as a live identity reference:

  1. It is CAPTIONED into physical facts, which become the character's words. Words survive
     every engine; an image reference does not.
  2. It is REDRAWN into the project's own idiom with Qwen-Image-Edit 2511, which the
     photo-to-anime work found to be the route that actually holds a face. The redraw
     becomes the reference sheet.

Step 2 matters more than it looks. A reference sheet imports its STYLE AND ITS MEDIUM into
everything downstream, so a sheet that is still a photograph quietly turns the whole film
photographic. The sheet has to be in the idiom the film is in, which is why the redraw is
not optional and why --style defaults to the house style rather than to nothing.

CONSENT IS THE GATE FOR A REAL PERSON. If the source is a photograph of someone real, the
thing being created is a trained likeness of their face that lives on disk. That needs
their agreement, not just access to the picture. Pass --consent to confirm you have it;
without it the tool will still build a character from a drawing or a synthetic image, but
it refuses to pretend the question does not exist.
"""
import argparse, glob, json, os, re, shutil, subprocess, sys, time, urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, HOST, COMFY   # noqa: E402

HOUSE_STYLE = ("dark fantasy tabletop illustration, painted in gouache and ink, heavy "
               "shadow, painterly brushwork, muted earth palette, detailed face")

CAPTION_ASK = (
    "Describe the person in this image as a character reference. Physical facts only: "
    "apparent age, build, hair colour and style, eye colour, skin tone, any distinguishing "
    "marks, and the clothing. One dense paragraph. No story, no mood, no camera language, "
    "no guesses about who they are.")


def caption(src_name):
    """Ask the vision model what it sees, and get the answer back as a file.

    The shipped graph ends in PreviewAny, which renders text in the ComfyUI web UI and
    registers NOTHING in the history - so a caller reading outputs gets an empty list and no
    error. SaveText is appended so the answer lands somewhere a script can read it.
    """
    wf = load_wf("30_vision_caption.json")
    set_path(wf, "2.inputs.image", src_name)
    set_path(wf, "3.inputs.prompt", CAPTION_ASK)
    stamp = "cap_%d" % (time.time() % 100000)
    wf["90"] = {"class_type": "SaveText",
                "inputs": {"text": ["3", 0], "filename_prefix": stamp, "format": "txt"}}
    run(HOST, wf, quiet=True)
    hits = sorted(glob.glob(os.path.join(COMFY, "output", "**", stamp + "*"),
                            recursive=True))
    if not hits:
        return ""
    return open(hits[-1], encoding="utf-8", errors="replace").read().strip()


MEDIUM_ASK = (
    "What MEDIUM is this image? Answer with the drawing or photographic technique only, "
    "as a short phrase that could be used in an image prompt - for example 'a painted "
    "digital fantasy illustration with soft airbrushed shading', or 'a 35mm colour "
    "photograph with shallow depth of field'. Name the medium, the rendering technique and "
    "the palette. Do not describe the subject, the pose or the setting.")


def analyse_style(src_name):
    """Ask the vision model what medium the source is already in.

    This exists so a source that is ALREADY in the right idiom does not have to be
    converted into something it already is. Redrawing a good illustration into the house
    style is a lossy round trip for no gain.
    """
    wf = load_wf("30_vision_caption.json")
    set_path(wf, "2.inputs.image", src_name)
    set_path(wf, "3.inputs.prompt", MEDIUM_ASK)
    stamp = "med_%d" % (time.time() % 100000)
    wf["90"] = {"class_type": "SaveText",
                "inputs": {"text": ["3", 0], "filename_prefix": stamp, "format": "txt"}}
    run(HOST, wf, quiet=True)
    hits = sorted(glob.glob(os.path.join(COMFY, "output", "**", stamp + "*"),
                            recursive=True))
    if not hits:
        return ""
    return " ".join(open(hits[-1], encoding="utf-8", errors="replace")
                    .read().strip().split())[:300]


# Word-boundary matching, and hand-made media win outright. A bare substring test flagged
# "a digital painting with photorealistic rendering" as photographic, because "photo" sits
# inside "photorealistic" - and a photorealistic PAINTING is a painting. The warning only
# earns its place when the sheet is genuinely a photograph; a false positive teaches people
# to ignore it, which is worse than not warning at all.
import re as _re

PHOTOGRAPHIC = (r"photograph", r"photographic", r"35\s?mm", r"dslr", r"camera",
                r"lens", r"film still", r"snapshot", r"polaroid")
HANDMADE = (r"painting", r"painted", r"illustration", r"illustrated", r"drawing",
            r"drawn", r"sketch", r"render", r"anime", r"cartoon", r"comic", r"ink",
            r"watercolou?r", r"gouache", r"3d", r"cgi", r"engraving", r"woodcut")


def looks_photographic(medium):
    m = (medium or "").lower()
    if any(_re.search(r"\b" + w, m) for w in HANDMADE):
        return False          # a photorealistic painting is still a painting
    return any(_re.search(r"\b" + w, m) for w in PHOTOGRAPHIC)


def redraw(src_name, style, seed, prefix):
    """Redraw the source in the project's idiom. This becomes the reference sheet."""
    wf = load_wf("22_qwen_edit_2511.json")
    set_path(wf, "7.inputs.image", src_name)
    # The medium goes in the FIRST sentence. Measured on the photo-to-anime work: naming the
    # medium late leaves the model in whatever medium the source was in.
    set_path(wf, "10.inputs.prompt",
             "Redraw this as a %s. Keep the same person: same face, same hair, same build, "
             "same clothing. Bust portrait, plain dark backdrop, even light." % style)
    set_path(wf, "15.inputs.seed", seed)
    set_path(wf, "17.inputs.filename_prefix", prefix)
    _, outs = run(HOST, wf, quiet=True)
    return outs[0] if outs else None


def tags_from(text):
    """A rough danbooru-ish tag line for the anime engine, from the caption's own words.

    Deliberately crude and deliberately visible in the card: it is a starting point for
    someone to edit, not a claim to have understood the picture. The prose carries the
    real description.
    """
    t = text.lower()
    out = []
    for pat, tag in (
        (r"\b(woman|female|she|her)\b", "1girl"), (r"\b(man|male|he|his)\b", "1boy"),
        (r"\bblonde|blond\b", "blonde hair"), (r"\bred hair|ginger|auburn\b", "red hair"),
        (r"\bblack hair\b", "black hair"), (r"\bbrown hair\b", "brown hair"),
        (r"\bwhite hair|silver hair|grey hair|gray hair\b", "white hair"),
        (r"\bgreen hair\b", "green hair"), (r"\bblue eyes\b", "blue eyes"),
        (r"\bgreen eyes\b", "green eyes"), (r"\bbrown eyes\b", "brown eyes"),
        (r"\bgrey eyes|gray eyes\b", "grey eyes"), (r"\blong hair\b", "long hair"),
        (r"\bshort hair\b", "short hair"), (r"\bbraid\b", "braid"),
        (r"\bbeard\b", "beard"), (r"\bglasses|spectacles\b", "glasses"),
        (r"\barmou?r\b", "armor"), (r"\bcloak\b", "cloak"), (r"\bscar\b", "scar"),
    ):
        if re.search(pat, t) and tag not in out:
            out.append(tag)
    if "1girl" in out and "1boy" in out:
        out.remove("1boy")          # both matched on a pronoun; keep the stronger noun
    return ["solo"] + out


def build(args):
    src = os.path.abspath(args.image)
    if not os.path.isfile(src):
        raise SystemExit("no such image: %s" % src)
    cid = re.sub(r"[^A-Z0-9_]", "", args.name.upper().replace(" ", "_")) or "UNNAMED"
    card_path = os.path.join(STUDIO, "characters", cid + ".json")
    if os.path.exists(card_path) and not args.force:
        raise SystemExit("%s already exists - pass --force to replace it" % cid)

    staged = "charnew_%s.png" % cid.lower()
    shutil.copy(src, os.path.join(COMFY, "input", staged))

    print("  captioning ...")
    desc = caption(staged)
    print("    %s" % ((desc[:150] + " ...") if len(desc) > 150 else desc or "(no caption)"))
    if args.caption_only:
        return

    sheet_name = "sheet_%s.png" % cid.lower()
    sheet = os.path.join(COMFY, "input", sheet_name)
    style_used, medium = args.style, ""

    if str(args.style).strip().lower() in ("keep", "detect"):
        # KEEP THE SOURCE'S OWN LOOK. The redraw still happens, because a sheet has other
        # work to do besides medium - it needs the background stripped and the subject
        # framed as a bust, or the backdrop travels into every later render. So the medium
        # is detected and fed back in, which converts nothing and fixes the framing.
        print("  reading the medium ...")
        medium = analyse_style(staged)
        print("    %s" % (medium or "(could not tell)"))
        style_used = medium or HOUSE_STYLE
        if looks_photographic(medium):
            print("    NOTE: this source is photographic. A reference sheet imports its "
                  "medium into everything downstream, so keeping it will make the whole "
                  "film photographic. That is fine if it is what you want, and a real "
                  "problem if it is not.")

    if str(args.style).strip().lower() in ("none", "as-is", "asis"):
        # NO REDRAW AT ALL. The source becomes the sheet untouched. Right when the source
        # is already a clean bust portrait on a plain backdrop; wrong otherwise, because
        # whatever is behind the subject gets learned as part of them.
        print("  keeping the source as the sheet, unmodified")
        shutil.copy(src, sheet)
        rel, style_used = "as-is", "unchanged from the source"
        print("    %s" % sheet)
    else:
        print("  redrawing ...")
        rel = redraw(staged, style_used, args.seed,
                     "claude-generated/characters/%s" % cid.lower())
        if rel:
            ensure_local(rel, sheet, required=False)
            print("    %s" % sheet)
        else:
            print("    redraw FAILED - card will be written without a sheet")

    card = {
        "id": cid, "name": args.name,
        "status": "draft",
        "desc": desc or args.desc or "",
        "prose": desc or args.desc or "",
        "tags": tags_from(desc or args.desc or ""),
        "base_tags": tags_from(desc or args.desc or ""),
        "wear_tags": [],
        "sheet": sheet_name if rel else None,
        "sheet_style": style_used,
        "source_medium": medium or None,
        "voice": args.voice or None,
        # Provenance travels with the card. Six months from now the only way to know why a
        # face looks the way it does is to have written down where it started.
        "provenance": "from_image",
        "provenance_note": (
            "Built from %s. The source was captioned into the description above and "
            "redrawn into the project idiom with Qwen-Image-Edit 2511; the redraw is the "
            "reference sheet. The source image is NOT used as a live identity reference - "
            "measured, that transports a costume rather than a face."
            % os.path.basename(src)),
        "source_image": os.path.basename(src),
        "consent": bool(args.consent),
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "note": ("DRAFT. The tags are a crude first pass from the caption's own words and "
                 "are meant to be edited. Nothing here is measured yet: no turnaround, no "
                 "LoRA, no verdicts. Run the turnaround next if the sheet looks right."),
    }
    os.makedirs(os.path.dirname(card_path), exist_ok=True)
    with open(card_path, "w", encoding="utf-8") as f:
        json.dump(card, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("  %s" % card_path)
    print("  tags: %s" % ", ".join(card["tags"]))
    if not args.consent:
        print("  NOTE: --consent was not passed. If the source is a photograph of a real "
              "person, get their agreement before training a likeness of them.")


def list_sources():
    """Images already on the box that can be used as a starting point."""
    roots = [(os.path.join(COMFY, "input"), "comfy input"),
             (os.path.join(STUDIO, "samples", "rolled", "image"), "rolled gallery")]
    for d, label in roots:
        if not os.path.isdir(d):
            continue
        files = [f for f in sorted(os.listdir(d))
                 if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
        print("%s  (%d)" % (label, len(files)))
        for f in files[:25]:
            print("   ", f)
        if len(files) > 25:
            print("    ... and %d more" % (len(files) - 25))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image")
    ap.add_argument("--name")
    ap.add_argument("--style", default=HOUSE_STYLE,
                    help="a style to redraw into; 'keep' to detect the source's own "
                         "medium and stay in it; 'none' to use the source untouched")
    ap.add_argument("--desc", default="", help="used if the vision model returns nothing")
    ap.add_argument("--voice", default="")
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--consent", action="store_true",
                    help="confirm the subject agreed, if the source is a real person")
    ap.add_argument("--caption-only", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--list-sources", action="store_true")
    a = ap.parse_args()
    if a.list_sources:
        return list_sources()
    if not (a.image and a.name):
        ap.error("--image and --name are required")
    build(a)


if __name__ == "__main__":
    main()
