#!/usr/bin/env python3
"""studio/_tools/make_flux2_styles.py - give FLUX.2 a way in, and render the proof.

    python3 studio/_tools/make_flux2_styles.py            author cards + render one each
    python3 studio/_tools/make_flux2_styles.py --cards-only

THE PROBLEM THIS FIXES. FLUX.2 is installed, works, is measured (7-19 s a frame on turbo),
and render_job.py has had a `flux2` branch all along. And **zero of 132 style cards route
to it**, so nothing in the app could ever reach it. The engine is a property of the style,
resolved by compose.resolve - so an engine with no style card is an engine that does not
exist. This is the same shape as the wizard offering three dead cameras, in the other
direction: a live capability nobody can select.

WHAT THESE CARDS ARE FOR, AND WHY THEY ARE NOT MORE PHOTOREALISM. Qwen already owns
photography here and cannot be steered off it. Animagine owns illustration. Duplicating
either would add cards without adding reach. FLUX.2's measured strength is **typography
and physical media** - a printed page, a painted sign, an instant photo with a white
border. Those are exactly what the other two do badly: an image model that cannot spell
cannot make a book page, and both of the others produce lettering as texture.

So every card below is an OBJECT WITH WRITING ON IT, or a physical print artifact. That is
the niche, and it is the reason to add an engine rather than a preset.

NO REAL BRANDS. Every name, logo and imprint invented. A model that renders legible text
is a model that can forge a label, so nothing here names a real company or person.
"""
import argparse, json, os, sys, time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

OUT = os.path.join(STUDIO, "samples", "styles")

# Written as complete sentences: FLUX.2 is a prose engine, and the measured sweep used
# full descriptive paragraphs, not tag lists.
CARDS = [
    {
        "id": "letterpress_page",
        "words": 'the drop capital opening the word "CHAPTER" and a running head reading "THE SALT ROAD"',
        "name": "Letterpress page",
        "family": "physical media",
        "prose": ("A photograph of a single page from an old letterpress-printed book, "
                  "lying flat and filling the frame. The paper is cream laid stock with a "
                  "visible deckle edge and a faint foxing stain in one corner. The type is "
                  "a serif face pressed hard enough to leave a bite in the paper, with a "
                  "drop capital opening the first paragraph and a small engraved vignette "
                  "beneath the last line. Even diffuse light from directly above, no "
                  "shadow, shot straight down on medium format at f8, natural colour."),
        "means": "A printed page as an object. The text is the subject, not decoration.",
    },
    {
        "id": "enamel_shop_sign",
        "words": 'lettering reading exactly "NIGHT PORTER" on the first line and "RING TWICE" below',
        "name": "Enamel shop sign",
        "family": "physical media",
        "prose": ("A photograph of a vitreous enamel shop sign screwed to a brick wall. "
                  "The sign is deep blue with cream lettering in a bold grotesque face, "
                  "chipped along the bottom edge where the steel shows rust through the "
                  "enamel, and it has a soft specular sheen. Raking afternoon light from "
                  "the left, the brick out of focus behind. Shot on 85mm at f2.8, natural "
                  "colour, fine grain."),
        "means": "Painted metal signage. Chips, rust and a curved specular are what sell it.",
    },
    {
        "id": "instant_film",
        "words": 'the handwritten date on the lower margin reading "MARCH 1987"',
        "name": "Instant film snapshot",
        "family": "physical media",
        "prose": ("A photograph of a developed instant film print held flat against a plain "
                  "surface. The print has the format's thick white border, wider at the "
                  "bottom, a handwritten date in ballpoint on that lower margin, and one "
                  "soft thumbprint on the emulsion. The image inside is slightly milky with "
                  "crushed shadows, a warm colour cast and low contrast, the way instant "
                  "film actually renders. Even light, shot straight down, natural colour."),
        "means": "An instant photo as a physical object, border and handwriting included.",
    },
    {
        "id": "drafting_blueprint",
        "words": 'the title block reading "SECTION B-B" with a drawing number "DWG 114"',
        "name": "Drafting blueprint",
        "family": "technical",
        "prose": ("A photograph of a large cyanotype blueprint unrolled on a table, corners "
                  "weighted down. White line work on deep Prussian blue: an orthographic "
                  "elevation with dimension lines, leader arrows, hatched section fill and "
                  "a title block in the lower right holding a drawing number and a date. "
                  "The paper is creased where it was folded and slightly cockled. Even "
                  "overhead light, shot straight down at f8, natural colour."),
        "means": "Technical drawing with real annotation furniture, not a blue texture.",
    },
    {
        "id": "museum_label",
        "words": 'the label reading "SALT MEASURE" in bold with "cast bronze, undated" in italic beneath',
        "name": "Museum object and label",
        "family": "physical media",
        "prose": ("A photograph of a small artefact resting on a neutral grey plinth in a "
                  "museum vitrine, with a printed white label card angled beside it. The "
                  "label carries a title line in bold, a smaller italic subtitle, and three "
                  "lines of catalogue text in a clean serif. Soft directional museum "
                  "lighting from above and slightly left, a faint reflection in the glass, "
                  "shallow depth so the label is sharp and the background falls away. "
                  "Shot on 100mm macro at f5.6, natural colour."),
        "means": "Object plus printed caption. Reads as a record rather than a picture.",
    },
    {
        "id": "newsprint_halftone",
        "words": 'the headline reading exactly "THE RIVER RETURNS" across two columns',
        "name": "Newsprint halftone",
        "family": "physical media",
        "prose": ("A close photograph of a folded newspaper page. A headline in a heavy "
                  "condensed serif runs across two columns above a photograph reproduced in "
                  "a coarse halftone dot screen, the dots plainly visible, with body text in "
                  "narrow justified columns beneath. The paper is grey-brown and slightly "
                  "translucent, with ink showing through from the reverse and a soft fold "
                  "crease across the middle. Flat even light, shot straight down, natural "
                  "colour, no vignette."),
        "means": "Print reproduction as the subject: dot screen, show-through, cheap paper.",
    },
    {
        "id": "botanical_plate",
        "words": 'the italic name beneath reading "Salvia obscura" and a plate number "PLATE XIV"',
        "name": "Botanical plate",
        "family": "illustration",
        "prose": ("A photograph of a hand-coloured engraved botanical plate on heavy rag "
                  "paper. A single specimen is drawn with fine stipple and line engraving, "
                  "watercolour washed over the print in muted greens and a dusty rose, with "
                  "a dissected detail of the flower parts inset at lower left. Beneath the "
                  "drawing sits an italic binomial name and a smaller line of plate "
                  "numbering. Wide clean margins, a faint plate impression pressed into the "
                  "paper. Even overhead light, shot straight down, natural colour."),
        "means": ("Scientific illustration with its caption. The plate mark and the wash "
                  "over engraved line are the tells."),
    },
    {
        "id": "neon_night_shopfront",
        "words": 'the neon spelling exactly "OPEN LATE" in warm pink tubing with "COFFEE" in cool blue script beneath',
        "name": "Neon shopfront at night",
        "family": "photographic",
        "prose": ("A night photograph of a small shopfront, seen straight on from across a "
                  "wet street. A neon sign in the window spells a short word in warm pink "
                  "tubing with a visible transformer flicker and a soft bloom, and a second "
                  "line of smaller cool blue tube script sits under it. The glass reflects "
                  "the street. Wet asphalt carries long colour smears of the sign. Shot on "
                  "35mm at f2, slight motion in the background, natural colour, fine grain."),
        "means": ("Lit lettering at night. Bloom, reflection and wet-road smear rather than "
                  "a flat glow."),
    },
    {
        "id": "hand_lettered_menu",
        "words": 'the board headed "TODAY" with the words "SOUP", "BREAD" and "PIE" listed beneath',
        "name": "Hand-lettered chalk menu",
        "family": "physical media",
        "prose": ("A photograph of a chalkboard menu leaning against a wall. The lettering "
                  "is hand-drawn in white and pale yellow chalk with a mixture of a bold "
                  "brush script and small neat capitals, ruled guide lines still faintly "
                  "visible, a smudged correction where one line was rubbed out and "
                  "rewritten, and a simple chalk border. The board is matt black and dusty. "
                  "Soft window light from the right at a grazing angle. Shot on 50mm at "
                  "f2.8, natural colour."),
        "means": "Handwriting rather than typesetting, with the smudges that prove the hand.",
    },
    {
        "id": "worn_paperback",
        "words": 'the cover title reading exactly "THE LONG WINTER" with a smaller author line "E. HALLOWAY"',
        "name": "Worn paperback cover",
        "family": "physical media",
        "prose": ("A photograph of a battered mass-market paperback lying on a wooden table, "
                  "seen from slightly above. The cover is a painted illustration in "
                  "saturated mid-century colour under a title set in a heavy display face, "
                  "with a smaller author line beneath and a price corner box. The spine is "
                  "creased white, the corners are soft and rounded from use, and the paper "
                  "edges have yellowed. Warm side light from a window, shot on 50mm at f4, "
                  "natural colour, fine grain."),
        "means": "A book as a used object: creased spine, rounded corners, yellowed edges.",
    },
]

NEG = ("blurry text, unreadable lettering, gibberish characters, misspelled words, "
       "watermark, signature, logo, lowres, jpeg artifacts, oversaturated, "
       "3d render, cgi, plastic")


def write_cards():
    d = os.path.join(STUDIO, "styles")
    for c in CARDS:
        card = {
            "id": c["id"], "name": c["name"],
            "engine": "flux2",
            "status": "ready", "compose": "safe", "family": c["family"],
            # THE WORDS ARE QUOTED IN THE PROMPT. This is the whole finding of
            # flux2_text_sweep.py: FLUX.2 spells correctly when the exact string is given
            # and produces word-shaped noise when it is not. The first ten proofs read
            # "VITREQUS SHOP", "Bagike Menu", "KNACK ENMETHLES" - beautiful media carrying
            # gibberish - because every prompt described lettering without saying what it
            # should say. Quoted, it is right even at 4 steps.
            "prose": c["prose"] + " The lettering shows " + c["words"] + ".",
            "words": c["words"],
            "text_rule": ("Replace `words` with the string you want and keep it QUOTED in "
                          "the prompt. Unquoted lettering comes back as gibberish."),
            "negative_add": NEG,
            "means": c["means"],
            "note": ("Routed to FLUX.2 deliberately. Before these cards, 132 style cards "
                     "existed and none named flux2, so an installed and measured engine "
                     "was unreachable from the app - the engine is a property of the "
                     "style, so a style card is the only door. Written as prose because "
                     "FLUX.2 is a sentence engine, and chosen for typography and physical "
                     "media because that is where it beats Qwen and animagine rather than "
                     "duplicating them."),
            "provenance": "invented - no real brand, imprint or person is named",
            "verdict": "unverified until the sample below is looked at.",
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        with open(os.path.join(d, "%s.json" % c["id"]), "w", encoding="utf-8") as f:
            json.dump(card, f, indent=1, ensure_ascii=False)
            f.write("\n")
    return len(CARDS)


def render_all(seed=5150):
    from comfy import run, set_path                                  # noqa: E402
    from epic import load_wf, ensure_local, HOST                     # noqa: E402
    os.makedirs(OUT, exist_ok=True)
    ok = 0
    for i, c in enumerate(CARDS):
        wf = load_wf("40_flux2_t2i.json")
        for nid, n in wf.items():
            if not isinstance(n, dict):
                continue
            ct = n.get("class_type", "")
            ins = n.get("inputs") or {}
            if ("CLIPTextEncode" in ct or "TextEncode" in ct) and "text" in ins:
                ins["text"] = c["prose"] + " The lettering shows " + c["words"] + "."
            for k in ("noise_seed", "seed"):
                if k in ins:
                    ins[k] = seed + i
            if "width" in ins and "height" in ins:
                ins["width"], ins["height"] = 1024, 1024
            if ct == "SaveImage":
                ins["filename_prefix"] = "claude-generated/styles/%s__flux2" % c["id"]
        t = time.time()
        try:
            _, outs = run(HOST, wf, quiet=True)
        except Exception as e:
            print("  %-22s FAILED %s" % (c["id"], str(e)[:70]))
            continue
        if not outs:
            print("  %-22s no output" % c["id"])
            continue
        dst = os.path.join(OUT, "%s__flux2.webp" % c["id"])
        got = ensure_local(outs[0], dst.replace(".webp", ".png"), required=False)
        print("  %-22s %5.1fs  %s" % (c["id"], time.time() - t,
                                      os.path.basename(got or "?")))
        ok += 1
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards-only", action="store_true")
    a = ap.parse_args()
    print("  wrote %d flux2 style cards" % write_cards())
    if a.cards_only:
        return 0
    print("  rendering one proof each:")
    n = render_all()
    print("\n  %d/%d rendered. LOOK AT THEM before trusting the cards - the whole point "
          "is legible lettering, and only pixels can say." % (n, len(CARDS)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
