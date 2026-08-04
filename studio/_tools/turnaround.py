#!/usr/bin/env python3
"""One picture of a person becomes many consistent views of that same person.

    python3 studio/_tools/turnaround.py VIRO                    # from their sheet
    python3 studio/_tools/turnaround.py VIRO --views 12
    python3 studio/_tools/turnaround.py --image some.png --out /tmp/set
    python3 studio/_tools/turnaround.py TERRA --captions-only   # recaption, no GPU

WHY THIS IS THE KEYSTONE

Everything about character consistency in this project has been a workaround for not
having one. Tags describe someone; they do not make the same face twice. IPAdapter
refines a face from a single reference - and a measured weight sweep found the character
was "already recognisable at ZERO", i.e. the single sheet was carrying much less than
assumed. A character that is a PROMPT can never be reliably the same person.

The multiple-angles LoRA re-poses the SAME person rather than generating a new one that
matches the description. That gives two things at once:

  a real reference sheet   many views instead of one, which is a far stronger identity
                           lock for the paths that use a reference
  a training set           20-40 consistent views of one person is exactly what a
                           character LoRA needs, and producing that by hand is the reason
                           character training normally never happens

Views are authored rather than random. A training set wants ANGLES and EXPRESSIONS of a
neutral subject - not costumes, not scenes, not lighting. Anything the set varies that is
not the person is something the LoRA will learn as part of the person.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, COMFY, HOST   # noqa: E402

WF = "32_qwen_turnaround.json"
CAST = os.path.join(STUDIO, "characters")
OUT = os.path.join(STUDIO, "samples", "cast")

# EVERY PROMPT STATES ITS FRAMING, and all but the last two state the same one.
#
# The first version left framing to the model and it drifted: "side view ... full profile"
# was read as FULL BODY, so those two views zoomed out and lost the costume entirely -
# green tunic instead of the teal jersey - while the head-and-shoulders views held
# identity perfectly. Two things varied at once and only one was intended.
#
# That matters more here than in a comparison panel. A LoRA learns whatever the set holds
# CONSTANT as "the character" and whatever it varies as "not the character". A set that is
# half close-up and half full-body teaches a muddle, and the costume changing across the
# set teaches that the costume is optional.
#
# So: framing is written into every line. The two deliberate framing changes are named as
# such and come last, where they are a small minority of the set.
FRAME = "head and shoulders, waist up"
VIEWS = [
    ("front",        f"front view of the same person, facing the camera directly, neutral expression, {FRAME}"),
    ("three_quarter",f"three-quarter view of the same person, head turned slightly to their left, {FRAME}"),
    ("side_left",    f"the same person's head turned to face left, profile of the face, {FRAME}"),
    ("side_right",   f"the same person's head turned to face right, profile of the face, {FRAME}"),
    ("back",         f"the same person seen from behind, back of the head, head turned slightly, {FRAME}"),
    ("looking_up",   f"the same person looking upward, chin raised, neutral expression, {FRAME}"),
    ("looking_down", f"the same person looking downward, chin lowered, eyes cast down, {FRAME}"),
    ("low_angle",    f"the same person seen from a low camera angle looking up at them, neutral expression, {FRAME}"),
    ("high_angle",   f"the same person seen from a high camera angle looking down at them, neutral expression, {FRAME}"),
    ("smiling",      f"the same person smiling, front view, {FRAME}"),
    ("angry",        f"the same person with a hard angry expression, brows drawn down, front view, {FRAME}"),
    ("surprised",    f"the same person surprised, eyes wide, mouth slightly open, front view, {FRAME}"),
    ("shouting",     f"the same person shouting, mouth open wide, front view, {FRAME}"),
    ("eyes_closed",  f"the same person with eyes closed, calm, front view, {FRAME}"),
    # the only two that change framing on purpose, kept to a minority of the set
    ("close",        "an extreme close-up of the same person's face only, front view, neutral expression"),
    ("full_body",    "the same person standing, full body visible head to feet, front view, plain background"),
]

# The turnaround renders every view against the same flat neutral backdrop. That is
# correct for a training set - see the note on captions below for why it must then be
# NAMED in the caption rather than left implicit.
BACKDROP = "plain flat grey background"


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def stage(path):
    """ComfyUI can only LoadImage from its own input dir."""
    dst = os.path.join(COMFY, "input", "turnaround_src.png")
    if os.path.abspath(path) != os.path.abspath(dst):
        sh("cp", path, dst)
    return "turnaround_src.png"


def wardrobe_for(card, costume_id=None):
    """The garment nouns actually worn in the rendered set, at damage level 0.

    Level 0 because a turnaround is always the undamaged outfit. Returns "" when there is
    no card (a bare --image run), which falls the caption back to its old trigger-only
    form - wrong, but no more wrong than it was, and there is nothing better to say.
    """
    if not card:
        return ""
    costumes = card.get("costumes") or {}
    src = None
    if costume_id and costume_id in costumes:
        src = costumes[costume_id].get("wear_tags")
    elif costumes.get("default"):
        src = costumes["default"].get("wear_tags")
    if not src:
        src = card.get("wear_tags")
    return (src or [""])[0]


def caption(trigger, view, wardrobe):
    """A CAPTION IS A SUBTRACTION, NOT A DESCRIPTION.

    This is the single most consequential line in the character pipeline and the first
    version of it was backwards, so the reasoning is written out in full.

    During training every image is paired with its caption. Whatever the caption NAMES is
    explained by that word and is learned as an independent, re-usable thing. Whatever is
    present in every image and named NOWHERE has to be accounted for by the only token
    that is always there - the trigger. So the trigger silently absorbs it, permanently,
    as part of what the character IS.

    Therefore: caption exactly what you want to be able to CHANGE later, and omit exactly
    what you want welded on.

    The first version of this function wrote "terra, front" and nothing else, reasoning
    that "describing hair or clothing here would teach the model that those are separate
    from the character rather than part of it - the opposite of what is wanted." The
    mechanism was right and the conclusion was applied to the wrong nouns. Separable
    clothing is precisely what is wanted; only the face and the hair should be welded on.
    Because the garments were never named, "terra" came to mean *the woman AND the gold
    dress*, and every later costume change had to fight the weights that make her her.

    MEASURED, studio/samples/cast/terra_costume_fix/. The same failure had a second
    symptom nobody had connected to it: the flat grey turnaround backdrop was also in
    every image and also named nowhere, so the trigger absorbed that too. That is why
    raising the LoRA to 0.85 "destroys the setting" - a sunlit field going grey and a snow
    forest collapsing to flat beige is the memorised backdrop bleeding through, and beige
    is the literal colour of the turnaround wall. One uncaptioned constant, two bugs.

    So the caption names the trigger, the view, the wardrobe, and the backdrop. What it
    still does NOT name is hair, eyes, face or build - those are the character, and they
    stay welded to the trigger where they belong.
    """
    parts = [trigger, view]
    if wardrobe:
        parts.append(wardrobe)
    parts.append(BACKDROP)
    return ", ".join(parts)


def write_captions(out_dir, views, trigger, wardrobe):
    """LoadImageTextDataSetFromFolder pairs <name>.png with <name>.txt."""
    n = 0
    for i, (vid, _) in enumerate(views):
        img = os.path.join(out_dir, "%02d_%s.png" % (i, vid))
        if not os.path.exists(img):
            continue
        with open(img[:-4] + ".txt", "w", encoding="utf-8") as f:
            f.write(caption(trigger, vid.replace("_", " "), wardrobe) + "\n")
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("character", nargs="?", help="a character id from studio/characters/")
    ap.add_argument("--image", help="use this image instead of the character's sheet")
    ap.add_argument("--out", help="write here instead of samples/cast/<id>/")
    ap.add_argument("--views", type=int, default=len(VIEWS))
    ap.add_argument("--strength", type=float, help="override the angles LoRA strength")
    ap.add_argument("--costume", help="render the set in this costume from the card's "
                                      "costumes map, and caption it as such. A dataset "
                                      "built across TWO costumes leaves no garment "
                                      "present in every image.")
    ap.add_argument("--captions-only", action="store_true",
                    help="rewrite the .txt captions for an existing set and restage it. "
                         "No GPU, no re-render.")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    card = None
    if a.image:
        src, name = a.image, os.path.splitext(os.path.basename(a.image))[0]
        if a.character:
            p = os.path.join(CAST, a.character + ".json")
            if os.path.exists(p):
                card = json.load(open(p, encoding="utf-8"))
                name = a.character
    elif a.character:
        p = os.path.join(CAST, a.character + ".json")
        if not os.path.exists(p):
            have = sorted(f[:-5] for f in os.listdir(CAST) if f.endswith(".json"))
            raise SystemExit(f"unknown character {a.character!r}\n  have: {', '.join(have)}")
        card = json.load(open(p, encoding="utf-8"))
        if not card.get("sheet"):
            raise SystemExit(f"{a.character} has no `sheet` to turn around.\n"
                             f"  Generate one first, or pass --image.")
        src = os.path.join(COMFY, "input", card["sheet"])
        name = a.character
    else:
        raise SystemExit("give a character id or --image")

    if a.costume:
        cos = (card or {}).get("costumes") or {}
        if a.costume not in cos:
            raise SystemExit("%s has no costume %r\n  have: %s"
                             % (name, a.costume, ", ".join(sorted(cos)) or "none"))

    trigger = name.lower()
    wardrobe = wardrobe_for(card, a.costume)
    if not wardrobe:
        print("! no wardrobe found for %s - captions will not name the garments, so the\n"
              "  trigger will absorb whatever is worn. See caption() for why that hurts."
              % name)

    # a second costume gets its own filenames so both sets can live in one training dir
    tag = ("%s_%s" % (name, a.costume)) if a.costume else name
    out = a.out or os.path.join(OUT, tag)
    views = VIEWS[:max(1, a.views)]

    if a.captions_only:
        if not os.path.isdir(out):
            raise SystemExit("nothing at %s to recaption" % out)
        n = write_captions(out, views, trigger, wardrobe)
        print("recaptioned %d in %s" % (n, out))
        print("  %s" % caption(trigger, "front", wardrobe))
        n = restage(out, name, a.costume)
        print("restaged %d files" % n)
        print("\nnext:  python3 studio/_tools/train_character.py %s" % name)
        return

    os.makedirs(out, exist_ok=True)
    staged = stage(src)
    print("turning around %s from %s" % (name, os.path.basename(src)))
    if a.costume:
        print("  costume %s: %s" % (a.costume, wardrobe))
    print("  %d views -> %s" % (len(views), out))

    made = skipped = failed = 0
    for i, (vid, prompt) in enumerate(views):
        dst = os.path.join(out, "%02d_%s.png" % (i, vid))
        if os.path.exists(dst) and not a.force:
            skipped += 1
            continue
        # A costume run re-dresses the subject in the edit prompt. It comes last and is
        # stated as a change of clothes, because the source sheet is wearing the default
        # and the edit has to be told to override what it can see.
        p = prompt
        if a.costume and wardrobe:
            p = "%s. change her clothes to: %s" % (prompt, wardrobe)
        wf = load_wf(WF)
        set_path(wf, "7.inputs.image", staged)
        set_path(wf, "10.inputs.prompt", p)
        set_path(wf, "15.inputs.seed", 1100 + i)
        if a.strength is not None:
            set_path(wf, "40.inputs.strength_model", float(a.strength))
        set_path(wf, "17.inputs.filename_prefix",
                 "claude-generated/studio_cast/%s_%02d_%s" % (tag, i, vid))
        try:
            _, outs = run(HOST, wf, quiet=True)
        except Exception as e:
            print("  %-14s FAILED %s" % (vid, str(e)[:90]))
            failed += 1
            continue
        if not outs:
            failed += 1
            continue
        if not ensure_local(outs[0], dst, required=False):
            failed += 1
            continue
        made += 1
        print("  %-14s %6.0f KB" % (vid, os.path.getsize(dst) / 1024), flush=True)

    if made or skipped:
        write_captions(out, views, trigger, wardrobe)

    n = restage(out, name, a.costume)
    print("\n%d rendered, %d already there, %d failed" % (made, skipped, failed))
    print("browsable at  %s" % out)
    print("trainable at  %s  (%d files)" % (dataset_dir(name), n))
    print("\nnext:  python3 studio/_tools/train_character.py %s" % name)


def dataset_dir(name):
    # LoadImageTextDataSetFromFolder offers a dropdown of directories under ComfyUI/input,
    # so a dataset anywhere else is invisible to it no matter how well formed.
    return os.path.join(COMFY, "input", name.lower() + "_train")


def restage(out, name, costume=None):
    """Copy the set where the trainer can actually see it.

    A costume run keeps its own filename prefix, so a mixed-wardrobe dataset accumulates
    in one directory instead of overwriting itself.

    ONLY CAPTIONED PAIRS TRAVEL. The browsable sample directory is a place other tools
    drop things - a photographic sheet, a face reference, a contact sheet - and an earlier
    version of this copied every .png it found. That silently put an uncaptioned photoreal
    portrait into an anime training set, where it would have been trained on with an empty
    caption and blamed on something else entirely. An image with no .txt beside it is not
    part of the set.
    """
    train = dataset_dir(name)
    os.makedirs(train, exist_ok=True)
    n = 0
    for fn in sorted(os.listdir(out)):
        if not fn.endswith(".png"):
            continue
        txt = fn[:-4] + ".txt"
        if not os.path.exists(os.path.join(out, txt)):
            print("  not part of the set, skipping: %s (no caption beside it)" % fn)
            continue
        for f in (fn, txt):
            dst = ("%s_%s" % (costume, f)) if costume else f
            sh("cp", os.path.join(out, f), os.path.join(train, dst))
            n += 1
    return n


if __name__ == "__main__":
    main()
