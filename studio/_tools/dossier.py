#!/usr/bin/env python3
"""studio/_tools/dossier.py - assemble ONE CHARACTER'S DOSSIER from what is on disk.

    python3 studio/_tools/dossier.py TERRA          # what was found, section by section
    python3 studio/_tools/dossier.py TERRA --json   # the payload /api/character/<id> serves
    python3 studio/_tools/dossier.py --index        # every cast member, section by section

WHAT THIS IS. /character/<id> answers, for one character, everything a director asks before
writing her into a scene: who she is, what holds her face ON EACH ENGINE, what she looks
like from every angle and at every shot size, what she wears, how she is drawn, how she
moves, how she sounds, and - the section that makes the rest trustworthy - what is still
unknown. This module is the half that reads the disk. character.html is the half that
renders it and holds the prose.

THE SHAPE IS THE DELIVERABLE, NOT JUST TERRA. Eight sections, defined in SPEC below, each
with a state (measured / partial / missing) and, when it is missing, the exact command that
fills it. Terra is the worked example; every other cast member falls through the same
builders and comes back mostly `missing` with the command to run. Nothing here is special-
cased on the id apart from LOOKED_AT, which is a transcription and says so.

CONVENTIONS IT DISCOVERS BY, so a new character inherits the page for free:

    studio/characters/<ID>.json           the card
    studio/samples/cast/<ID>/             the turnaround - NN_name.png + NN_name.txt
    studio/samples/cast/<ID>_<costume>/   a second turnaround in another costume
    studio/samples/cast/<id>_views/       angles, elevation, framing ladder, expressions
    studio/samples/cast/<id>_styles/      the style sweep, with verdicts.json
    studio/samples/cast/<id>_wardrobe/    the costume x damage grids
    studio/samples/cast/<id>_motion/      clips, strips, head crops, results.json
    studio/samples/cast/<id>_voice/       audition, lines, emotion sweeps, measurements.json

EVERY CLAIM CARRIES ITS RENDER. That is this project's rule and it is enforced structurally
here: a verdict record without an `evidence` list of files that actually exist on disk is
dropped by _keep(), so the page cannot print a claim whose picture is gone. Where a number
came from a measurements.json the entry carries the number and the file it came from; where
a verdict came from a person opening the image, the entry says `looked_at` and names the
sheet they opened.

WHAT THIS MODULE DELIBERATELY DOES NOT DO. It does not render, it does not write into
studio/samples/, and it does not edit a character card. Several things it reports are
DISAGREEMENTS between a card and a later render - see contested() - and the fix for those
is an edit to a file this tool does not own, so it reports them rather than papering over
them.
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../studio
ROOT = os.path.dirname(HERE)
SAMPLES = f"{HERE}/samples"
CAST = f"{SAMPLES}/cast"
COMFY = os.path.expanduser(os.environ.get("COMFY_ROOT", "~/ComfyUI"))
IMG = (".png", ".webp", ".jpg", ".jpeg")
AUDIO = (".mp3", ".wav", ".flac")


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _url(path):
    """A path under studio/ as a URL this server can serve, or None.

    Everything the page shows has to live under studio/samples/, because that is the only
    tree serve.py's static handler will open. A file outside it is reported by ABSOLUTE
    PATH instead, so a reader can still find it on the box - see the motion clips, which
    live in ComfyUI's output tree and are streamed through their own route.
    """
    p = os.path.abspath(path)
    if p.startswith(SAMPLES + os.sep):
        return "/samples/" + os.path.relpath(p, SAMPLES).replace("\\", "/")
    return None


def _ls(d, exts=IMG):
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d) if f.lower().endswith(exts))


def _rel(path):
    """The path as a human would type it from the repo root."""
    p = os.path.abspath(path)
    return os.path.relpath(p, ROOT).replace("\\", "/") if p.startswith(ROOT) else p


def _img(path, label="", caption="", **extra):
    """One piece of evidence. Returns None when the file is not there, which is how a
    missing render removes the claim that rested on it instead of leaving a broken box."""
    if not os.path.isfile(path):
        return None
    e = {"url": _url(path), "label": label, "caption": caption,
         "path": _rel(path), "bytes": os.path.getsize(path)}
    e.update({k: v for k, v in extra.items() if v not in (None, "", [], {})})
    return e if e["url"] else None


def _pack(items):
    return [x for x in items if x]


def _pretty(name):
    return re.sub(r"^\d+[_-]", "", os.path.splitext(name)[0]).replace("_", " ")


def _stage_dir(cid, stage):
    """samples/cast/<id>_<stage>, matched case-insensitively - the tools name these
    lowercase (terra_views) while the card id is upper (TERRA)."""
    want = f"{str(cid).lower()}_{stage}"
    if not os.path.isdir(CAST):
        return None
    for d in sorted(os.listdir(CAST)):
        if d.lower() == want and os.path.isdir(f"{CAST}/{d}"):
            return f"{CAST}/{d}"
    return None


# ---------------------------------------------------------------------------
# THE SPEC - what a complete character dossier contains.
#
# This list IS the answer to "whatever completeness means for a character in this app".
# The page renders it as a checklist at the top, so an incomplete character reads as a
# named set of gaps with commands beside them rather than as a short page.
# ---------------------------------------------------------------------------
SPEC = [
    {"id": "who", "title": "who she is",
     "asks": "the concrete nouns that carry her, the prose, and where she came from",
     "tool": None, "args": "",
     "how": "author the card by hand: tags, base_tags, prose, photo_prose, provenance"},
    {"id": "holds", "title": "how she holds",
     "asks": "what fixes her face ON EACH ENGINE - they are different mechanisms",
     "tool": "studio/_tools/turnaround.py", "args": "<ID>",
     "then": "studio/_tools/train_character.py <ID>"},
    {"id": "looks", "title": "what she looks like",
     "asks": "the turnaround, the angle grid, the expression grid, the framing ladder",
     "tool": "studio/_tools/terra_views.py", "args": "all --character <ID>"},
    {"id": "wears", "title": "what she wears",
     "asks": "every costume, each with its five-rung damage ladder, rendered",
     "tool": "studio/_tools/terra_wardrobe.py", "args": "costumes places"},
    {"id": "drawn", "title": "how she is drawn",
     "asks": "which styles suit her, which repaint her, which hijack the frame",
     "tool": "studio/_tools/terra_styles.py", "args": "all"},
    {"id": "motion", "title": "in motion",
     "asks": "clips, and the measured seconds before her face stops being hers",
     "tool": "studio/_tools/terra_wardrobe.py",
     "args": "keyframes clips measure strips faces"},
    {"id": "sound", "title": "how she sounds",
     "asks": "the cast voice, why it beat the others, her ceilings, her rendered lines",
     "tool": "studio/_tools/cast_voice.py", "args": "audition lines emotion sweep measure"},
    {"id": "unknown", "title": "what is unknown",
     "asks": "the gaps, stated - a dossier that hides them is worse than one that admits",
     "tool": None, "args": "", "how": "computed from the sections above; nothing to run"},
]

_HARD = re.compile(r'^CHAR\s*=\s*["\']([A-Za-z0-9_]+)["\']', re.M)


def _how(spec, cid):
    """The command that fills a section, CHECKED AGAINST THE TOOL rather than remembered.

    This app has printed an impossible fix before - three pages told you to run
    scripts/make_sheets.py for a bare character card, which exits on argparse because it
    takes a FILM. So a command is only printed here if the file is on disk, and it is only
    printed FOR THIS CHARACTER if the tool can actually take a character.

    Four of the five sweep tools were written for Terra and hardcode `CHAR = "TERRA"` at
    module scope with no flag. For Terra they are the right command. For anybody else the
    honest answer is that the tool needs a --character flag first, so that is what gets
    said - it is also the most actionable item in that character's gaps.
    """
    rel = spec.get("tool")
    if not rel:
        return {"cmd": None, "blocked": None, "note": spec.get("how")}
    p = f"{ROOT}/{rel}"
    if not os.path.isfile(p):
        return {"cmd": None, "note": None,
                "blocked": "%s is not on disk. There is no tool for this section yet."
                           % rel}
    try:
        src = open(p, encoding="utf-8").read()
    except OSError:
        src = ""
    args = spec.get("args", "").replace("<ID>", cid)
    cmd = ("python3 %s %s" % (rel, args)).strip()
    if spec.get("then"):
        cmd += "\npython3 " + spec["then"].replace("<ID>", cid)
    if "--character" in src or "<ID>" in spec.get("args", ""):
        return {"cmd": cmd, "blocked": None, "note": None}
    m = _HARD.search(src)
    if m and m.group(1).upper() == str(cid).upper():
        return {"cmd": cmd, "blocked": None,
                "note": "%s is hardcoded to %s, which is this character." % (rel, m.group(1))}
    return {"cmd": cmd, "note": None,
            "blocked": "%s hardcodes CHAR = %r and takes no --character flag, so this "
                       "command would render %s, not %s. Generalising that tool the way "
                       "terra_views.py was generalised is the prerequisite for this "
                       "section on any other cast member."
                       % (rel, m.group(1) if m else "TERRA", m.group(1) if m else "TERRA", cid)}


# ---------------------------------------------------------------------------
# LOOKED_AT - verdicts that were established by a person OPENING THE IMAGE, and whose
# only machine-readable home is this file.
#
# READ THIS BEFORE TRUSTING ANY OF IT. Three different kinds of claim live in this
# project and they are not equally good:
#
#   1. a number in a measurements.json          - reproducible, and often measures the
#                                                 wrong thing (see the CLIP note below)
#   2. a verdict in a verdicts.json on disk     - somebody looked, and wrote it down
#                                                 where a program can read it
#   3. a verdict in a wave report               - somebody looked, and wrote it into prose
#
# The styles sweep produced (2). The views, wardrobe and motion sweeps produced (3) and
# nothing else: their measurements.json files hold numbers only. Rather than let the
# dossier show 400 pictures and no conclusions, those verdicts are transcribed here, each
# one naming the sheet that was opened. THE PAGE LABELS THEM AS SUCH. They belong on the
# character card or in a verdicts.json beside their renders, and moving them there is a
# real task for whoever owns those files - it is listed in the gaps.
#
# Every entry needs: what was seen, which files show it, and which tool made them. An
# entry whose evidence is not on disk is dropped by _keep().
# ---------------------------------------------------------------------------
_V = "verdicts.json"

LOOKED_AT = {"TERRA": [

    # ---- how she holds -------------------------------------------------------
    {"sec": "holds", "kind": "good", "tool": "studio/_tools/terra_wardrobe.py",
     "claim": "The LoRA carries her with the danbooru name removed from the prompt entirely.",
     "saw": "She is the same woman in the name-stripped and name-kept columns. That is what "
            "makes her a cast member rather than a prompt trick, and it is what makes the "
            "advice below affordable: stripping the tag costs nothing in identity.",
     "evidence": ["terra_wardrobe/costume_damage_v3_noname.jpg",
                  "terra_wardrobe/costume_damage_v3_name.jpg"]},
    {"sec": "holds", "kind": "bad",
     "tool": "studio/_tools/terra_wardrobe.py + terra_styles.py",
     "claim": "THE DANBOORU NAME IS THE DOMINANT VARIABLE, AND IT BEATS HER OWN CARD. "
              "Strip 'terra branford (final fantasy vi)' on any shot that is not her "
              "default costume.",
     "saw": "With the name in the prompt the base checkpoint drags Amano canon back: a "
            "feathered headdress that is on no card of hers, and the card's gold dress "
            "replaced by a bandeau and wrap. It beats the DEFAULT costume too, not only "
            "the alternatives. With the LoRA at v1 it is worse still - one outfit, the "
            "canonical polka-dot bodice and magenta sarong, in all 20 cells at both seeds.",
     "evidence": ["terra_wardrobe/costume_damage_v1_name.jpg",
                  "terra_wardrobe/costume_damage_v3_name.jpg",
                  "terra_styles/sheet_hair_02.jpg"]},
    {"sec": "holds", "kind": "good", "tool": "studio/_tools/terra_wardrobe.py",
     "claim": "The v3 retrain is real but smaller than 'v1 < v2 < v3' suggests: it is "
              "confined to the name-kept case and mostly to the court dress.",
     "saw": "Name KEPT: v1 gives one outfit in all 20 cells; v3 gives an actual "
            "floor-length green gown with gold embroidery and white gloves in all five "
            "court cells at both seeds. Name STRIPPED: v1 and v3 are hard to tell apart. "
            "The retrain did not fix armour and did not touch the field coat.",
     "evidence": ["terra_wardrobe/costume_damage_v1_noname.jpg",
                  "terra_wardrobe/costume_damage_v3_noname.jpg",
                  "terra_wardrobe/costume_damage_v1_name_s1337.jpg",
                  "terra_wardrobe/costume_damage_v3_name_s1337.jpg"]},
    {"sec": "holds", "kind": "note", "tool": "studio/_tools/terra_styles.py",
     "claim": "0.85 is available as a harder identity lock and it costs style strength. "
              "0.50 stays the default because every existing film was built against it.",
     "saw": "On all 11 styles that repainted her hair, 0.85 with no danbooru name restored "
            "both the hair and the costume - and the style visibly weakened: chiaroscuro "
            "flattened, glow dimmed, the ink wash thinned. There is no free option.",
     "evidence": ["terra_styles/sheet_hair_01.jpg", "terra_styles/sheet_hair_02.jpg",
                  "terra_styles/sheet_hair_03.jpg"]},

    # ---- what she looks like -------------------------------------------------
    {"sec": "looks", "kind": "bad", "tool": "studio/_tools/terra_views.py",
     "claim": "A TURNAROUND CANNOT BE ASKED FOR IN DEGREES, and the word 'rotate' is a trap.",
     "saw": "'rotate the camera N degrees clockwise around the same person': at 75, 90, 105, "
            "180, 195, 225, 255, 270 and 285 the WHOLE IMAGE is rolled 90 degrees - she "
            "lies horizontally, upright relative to nothing - and at six of those she is "
            "drawn twice, mirrored, with stray glyph artefacts. Not one of the 24 produced "
            "a rotated VIEW. The set is kept on disk rather than deleted.",
     "evidence": ["terra_views/sheet_yaw_rotate_failed.jpg"]},
    {"sec": "looks", "kind": "bad", "tool": "studio/_tools/terra_views.py",
     "claim": "The English steers and THE NUMBER IS INERT. 24 camera angles came back as "
              "the same near-three-quarter pose.",
     "saw": "The adopted orbit phrasing never rolls the frame, and across a full circle it "
            "produced zero front views, zero back views and zero profiles. Similarity to "
            "the 0-degree cell runs 0.931 to 0.980 with no trend, no cliff and no "
            "periodicity - a flat line with noise. The four-phrasing probe is the control: "
            "no phrasing distinguished 135 from 225.",
     "evidence": ["terra_views/sheet_yaw.jpg", "terra_views/sheet_yawprobe.jpg"]},
    {"sec": "looks", "kind": "good", "tool": "studio/_tools/terra_views.py",
     "claim": "NAMED VIEWS WORK. Eight English words produce a textbook turnaround where a "
              "protractor produced nothing.",
     "saw": "front 1.000, front_3q_l 0.930, profile_l 0.911, back_3q_l 0.876, back 0.836, "
            "back_3q_r 0.861, profile_r 0.927, front_3q_r 0.948 - a clean V bottoming at "
            "the back view. This is the reference an animator should be handed.",
     "evidence": ["terra_views/sheet_octants.jpg"]},
    {"sec": "looks", "kind": "warn", "tool": "studio/_tools/terra_views.py",
     "claim": "HANDEDNESS COLLAPSES AT FULL FIGURE: four distinct angles out of eight asked for.",
     "saw": "profile_l and profile_r both face screen-LEFT; back_3q_l and back_3q_r are both "
            "plain back views. Every turn goes the same way - the model never mirrors. The "
            "existing 16-view training set DOES separate them, and its phrasing is "
            "different: a HEAD-turn instruction at a close crop, not a body instruction at "
            "full figure. So handedness is obtainable and is one 8-cell run away.",
     "evidence": ["terra_views/sheet_octants.jpg"]},
    {"sec": "looks", "kind": "warn", "tool": "studio/_tools/terra_views.py",
     "claim": "THE ELEVATION AXIS HAS THREE STOPS, NOT FIVE. Do not write a worm's-eye or "
              "bird's-eye shot for the edit path expecting to get one.",
     "saw": "Low and high angles land with real foreshortening. 'extreme worm eye view, "
            "camera on the floor looking straight up' returned a normal EYE-LEVEL shot, and "
            "the bird's-eye returned an eye-level shot with the subject simply smaller and "
            "further away. The extremes are re-read as camera DISTANCE, which is also why "
            "those cells score lowest - that drop is distance, not identity.",
     "evidence": ["terra_views/sheet_elevation.jpg"]},
    {"sec": "looks", "kind": "bad", "tool": "studio/_tools/terra_views.py",
     "claim": "IDENTITY DIES AT ONE RUNG OF THE FRAMING LADDER. 5_wide is the honest "
              "cut-off for a shot that must read as Terra.",
     "saw": "The same face at extreme-close through wide. At 6_full she is a small figure "
            "at the end of a hall with no face at all and an INVENTED costume - a red bodice "
            "with a long train at one seed, a red-and-gold gown at another, neither hers. "
            "6_full is a silhouette shot: green hair and red-and-gold, nothing more.",
     "evidence": ["terra_views/sheet_frames.jpg"]},
    {"sec": "looks", "kind": "note", "tool": "studio/_tools/terra_views.py",
     "claim": "The most reproducible shot size is the COWBOY SHOT, and the extreme close-up "
              "is NOT the safest crop.",
     "saw": "Cross-seed similarity within a fixed framing: 4_medium 0.938, 3_medium_close "
            "0.910, 1_extreme_close 0.903, 2_close 0.903, 5_wide 0.891, 6_full 0.827. At "
            "extreme close the costume is out of frame and the seed is free to redesign the "
            "eye styling - one of the three cells comes back with a visibly different eye "
            "design, rounder iris and thinner brows.",
     "evidence": ["terra_views/sheet_frames.jpg"]},
    {"sec": "looks", "kind": "bad", "tool": "studio/_tools/terra_views.py",
     "claim": "HER WARDROBE COLOUR IS UNSTABLE ON THE PRODUCTION PATH, seed by seed and "
              "even cell by cell at the same seed.",
     "saw": "The card says 'sleeveless gold dress with red and blue pattern'. Across the "
            "framing ladder and the expression grid the bodice flips between GOLD-with-spots "
            "and RED-with-florals - angry has a red bodice and awe a gold one, both at seed "
            "4242. The costume work fixed which GARMENT arrives; this is the garment's "
            "COLOUR, a different bug, and it is live in every shot.",
     "evidence": ["terra_views/sheet_frames.jpg", "terra_views/sheet_emotions_s4242.jpg"]},
    {"sec": "looks", "kind": "good", "tool": "studio/_tools/terra_views.py",
     "claim": "TWENTY OF THE 27 EMOTION CARDS ARE DIRECTABLE on her.",
     "saw": "Both seeds read as the same woman doing twenty legibly different things: angry, "
            "cold, determined, doubt, embarrassed, exhausted, fear, grief, joy, longing, "
            "neutral, panic, pride, resignation, resolve, shock, smug, suspicion, tender, "
            "focus. Most repeatable across seeds: smug 0.964, tender 0.953, shock 0.948, "
            "focus 0.945. Furthest from neutral while still being her: joy 0.959 is the "
            "safest big move, then determined 0.948 and resolve 0.947.",
     "evidence": ["terra_views/sheet_emotions_s4242.jpg",
                  "terra_views/sheet_emotions_s7411.jpg"]},
    {"sec": "looks", "kind": "bad", "tool": "studio/_tools/terra_views.py",
     "claim": "FOUR EMOTION CARDS FAIL BY ONE MECHANISM - THE BODY TAG BEATS THE FRAMING - "
              "and they are the four a director most wants for a reaction shot.",
     "saw": "despair, relief, shame and awe carry `body` tags describing a WHOLE-FIGURE "
            "posture ('hunched, collapsed', 'head back', 'face turned away'). At wear 0 that "
            "tag goes into the prompt, overrides the pinned 'portrait, upper body', and the "
            "shot re-frames itself: despair came back as a full-figure kneeling shot at BOTH "
            "seeds with the face lost in hair, and awe threw the head back so far at 7411 "
            "that the FACE IS ENTIRELY OUT OF FRAME. Their numbers agree - shame 0.857, "
            "grief 0.869, relief 0.875, despair 0.889 are the four worst cross-seed scores.",
     "evidence": ["terra_views/sheet_emotions_s4242.jpg",
                  "terra_views/sheet_emotions_s7411.jpg"]},
    {"sec": "looks", "kind": "bad", "tool": "studio/_tools/terra_views.py",
     "claim": "RAGE REBUILDS HER FACE AT BOTH SEEDS. Use `angry`, never `rage`.",
     "saw": "vs-neutral 0.799, the lowest of all 27 by four points. Cropped against neutral: "
            "the eyes go from large soft green almonds with heavy lashes to SMALL ROUND "
            "PUPILS IN HUGE WHITE SCLERA - a different eye design, not a different "
            "expression; the skin goes from pale pink to flat mid-brown, the card's 'red "
            "face' tag repainting the whole head; a creased brow ridge appears and the jaw "
            "widens. Hair, headpiece and earrings are untouched, which is the general "
            "lesson: identity is carried by hair and jewellery, so a broken cell still reads "
            "as Terra in a contact sheet and only fails when someone looks at the face. "
            "angry does the same job and keeps her.",
     "evidence": ["terra_views/sheet_emotions_s4242.jpg",
                  "terra_views/sheet_emotions_s7411.jpg"]},
    {"sec": "looks", "kind": "warn", "tool": "studio/_tools/terra_views.py",
     "claim": "THE HEADPIECE IS NOT A RED RIBBON ANY MORE, on either engine - and the two "
              "halves of her dossier do not agree about her hair colour.",
     "saw": "Her identity vocabulary says 'red hair ribbon'. All 160 view renders draw a "
            "large pink/lilac-and-gold ornament with a red gem and two upswept gold prongs "
            "that read as HORNS. It is in the source sheet, so both paths inherit it, and it "
            "is now trained in. Her hair is a saturated teal-green on the edit path and a "
            "pale yellow-mint on the production path, consistently.",
     "evidence": ["terra_views/sheet_octants.jpg", "terra_views/sheet_frames.jpg"]},
    {"sec": "looks", "kind": "warn", "tool": "studio/_tools/terra_views.py",
     "claim": "THE FRAMING WORDS IN A QWEN-IMAGE-EDIT PROMPT ARE A SUGGESTION. If an "
              "edit-path set needs a crop, crop it afterwards.",
     "saw": "Every yaw and octant prompt pinned its shot size. 23 of the 24 yaw cells came "
            "back FULL BODY regardless, and only one cell in the whole edit-path corpus "
            "honoured 'waist up'. The shot size is being set by the SOURCE image, which is a "
            "full-figure sheet.",
     "evidence": ["terra_views/sheet_yaw.jpg", "terra_views/sheet_octants.jpg"]},

    # ---- what she wears ------------------------------------------------------
    {"sec": "wears", "kind": "bad", "tool": "studio/_tools/terra_wardrobe.py",
     "claim": "THE FIELD COAT IS NOT BROKEN - TWO OF ITS FIVE LINES OF TEXT ARE. It lands at "
              "damage 1 and 2 and fails at 0 and 3, identically in all four arms at both seeds.",
     "saw": "Levels 1 and 2 are the only rungs whose wear_tags do not name the gold dress. "
            "Level 0 reads 'heavy brown travelling coat OVER THE GOLD DRESS' and level 3 "
            "reads 'gold dress showing through the tear' - the model renders nouns, so it "
            "renders the gold dress and drops the coat. Level 4 correctly says 'no coat' and "
            "correctly has none. It failed in both no-LoRA controls too, so no retrain "
            "touches it: it is a two-line card edit.",
     "evidence": ["terra_wardrobe/costume_damage_v3_noname.jpg",
                  "terra_wardrobe/costume_damage_v3_name.jpg",
                  "terra_wardrobe/costume_damage_v3_noname_s1337.jpg"]},
    {"sec": "wears", "kind": "bad", "tool": "studio/_tools/terra_wardrobe.py",
     "claim": "DAMAGE IS NOT ORTHOGONAL TO WARDROBE. It is orthogonal for garments defined "
              "by CLOTH and destructive for garments defined by STRUCTURE.",
     "saw": "Imperial plate lands at damage 0-1 and collapses to a gown or a black bodysuit "
            "at 3-4 in every arm at both seeds, because its high rungs are written as "
            "REMOVALS - 'breastplate discarded', 'one pauldron gone' - and once the hard "
            "structural nouns are gone there is nothing left to render. The court dress, "
            "defined by a fabric silhouette that survives being torn, is the ONLY costume "
            "that lands at all five levels in all four arms at both seeds.",
     "evidence": ["terra_wardrobe/costume_damage_v3_noname.jpg",
                  "terra_wardrobe/costume_damage_v3_noname_s1337.jpg"]},
    {"sec": "wears", "kind": "warn", "tool": "studio/_tools/terra_wardrobe.py",
     "claim": "A ONE-SEED-PER-CELL LIBRARY SWEEP MANUFACTURES FALSE IDENTITY FAILURES AT "
              "ABOUT 1 IN 6. The place is innocent; the seed was not.",
     "saw": "floating_islands came back with CORAL hair - the kind of result that gets "
            "written onto a place card as a property of the place. Re-rendered at six seeds, "
            "green fraction in the located head crop was 11.9 / 79.0 / 52.7 / 35.9 / 64.8 / "
            "28.2 percent: five of six are green and only the sweep's own seed is coral.",
     "evidence": ["terra_wardrobe/recheck_floating_islands.jpg",
                  "terra_wardrobe/places_grid.jpg"]},

    # ---- how she is drawn ----------------------------------------------------
    {"sec": "drawn", "kind": "bad", "tool": "studio/_tools/terra_styles.py",
     "claim": "THE COMPOSITION HIJACK AND THE IDENTITY FAILURE ARE ONE FAILURE. A character "
              "LoRA holds identity in proportion to the pixels the character occupies.",
     "saw": "11 of 66 anime cells came back with her hair repainted RED at seed 3311; at "
            "seed 7788 roughly 40 did, and at 7788 almost every red-haired cell is also one "
            "where the style pulled the camera back and made her small. Where she is "
            "rendered large she stays green. So 'the style shrank her' and 'the style "
            "repainted her' are the same event - shot size is the load-bearing control.",
     "evidence": ["terra_styles/sheet_heads_a_01.jpg",
                  "terra_styles/sheet_heads_a_s7788_01.jpg"]},
    {"sec": "drawn", "kind": "warn", "tool": "studio/_tools/terra_styles.py",
     "claim": "PINNING THE SHOT SIZE IN THE PROMPT IS NOT SEED-ROBUST. Anything that depends "
              "on a character being large in frame needs the framing enforced by something "
              "stronger than a tag.",
     "saw": "'cowboy shot' placed first in the tag string stopped both known hijackers at "
            "seed 3311 and then failed across most of the library at 7788. ukiyo_e at 7788 "
            "is the clean demonstration: strongest style read in the sweep, a printed border "
            "built around the frame, her pushed deep into a receding courtyard, hair red.",
     "evidence": ["terra_styles/sheet_heads_a_s7788_01.jpg",
                  "terra_styles/sheet_a_tradition_s7788_01.jpg"]},
    {"sec": "drawn", "kind": "good", "tool": "studio/_tools/terra_styles.py",
     "claim": "THE QWEN EDIT-REF PATH DOES NOT HAVE THE IDENTITY PROBLEM AT ALL - 28 of 29 "
              "cells held her at the confirmation seed against roughly 26 of 66 on anime.",
     "saw": "Pixel conditioning beats a weight-space prior when something else is fighting "
            "for the frame. A style that changes how she is DRAWN lands completely; a style "
            "that needs to change what she IS cannot - pixar_3d's stylised proportion, "
            "stop_motion_felt's puppet and claymation's clay face all convert the SET and "
            "leave her a photographic human standing in it.",
     "evidence": ["terra_styles/sheet_heads_q_01.jpg",
                  "terra_styles/sheet_heads_q_s7788_01.jpg"]},
    {"sec": "drawn", "kind": "note", "tool": "studio/_tools/terra_styles.py",
     "claim": "THE PRIOR THAT A REFERENCE SHEET SUPPRESSES STYLE IS FALSE ON THE QWEN EDIT "
              "ROUTE. It is real on the anime IPAdapter path and does not transfer.",
     "saw": "With the medium declared first in the prompt, her PHOTOGRAPHIC sheet still "
            "produced a full hard-boiled ink comic and a genuine pixel sprite. The "
            "no-reference arm was measured and rejected: it buys style fidelity and returns "
            "a different woman.",
     "evidence": ["terra_styles/sheet_pilot_0q_01.jpg"]},
    {"sec": "drawn", "kind": "warn", "tool": "studio/_tools/terra_styles.py",
     "claim": "SEED-FRAGILITY IS THE REAL LIMIT ON EVERY PER-STYLE VERDICT IN THIS PROJECT. "
              "A one-seed pass/fail is a lower bound, not a verdict.",
     "saw": "gouache, grimdark and illuminated_manuscript all passed at 3311 and failed at "
            "7788. Fifteen anime styles are strong-and-holding at one seed only. The "
            "two-seed comparison cost 96 renders and about 11 minutes, and it changed the "
            "answer.",
     "evidence": ["terra_styles/sheet_seedcheck_01.jpg",
                  "terra_styles/sheet_heads_a_s7788_01.jpg"]},
    {"sec": "drawn", "kind": "warn", "tool": "studio/_tools/terra_styles.py",
     "claim": "THE STANDING ANIME NEGATIVE CONDEMNS THREE CARDS IN ITS OWN LIBRARY. This "
              "applies to every character sweep on this path, not only to her.",
     "saw": "The medium guard 'photorealistic, 3d, western comic' applied blindly fights "
            "american_comic, low_poly_3d and voxel - each style negated by the workflow that "
            "is meant to render it. neg_for_style() drops any guard clause the style's own "
            "text or family asks for; american_comic landed strongly only because of it.",
     "evidence": ["terra_styles/sheet_a_illustration_01.jpg"]},

    # ---- in motion -----------------------------------------------------------
    {"sec": "motion", "kind": "good", "tool": "studio/_tools/terra_wardrobe.py",
     "claim": "IDENTITY IS NOT BUDGETED BY TIME, IT IS BUDGETED BY WHETHER THE ACTION TURNS "
              "HER AWAY. walk_in holds her frontal and stable for the full 8.04 seconds.",
     "saw": "Same eyes, face, earrings and hair in all nine sampled frames of walk_in_long - "
            "the clean confirmation that identity survives 8s at strength 0.5. head_turn is "
            "frontal through 6.00s then breaks hard between 6 and 7 and is back-of-head by "
            "8s. turn_away loses the face at 4s and is fully backed by 5s. step_back "
            "OVER-DELIVERS: she recedes to a quarter of her starting height and the face is "
            "gone by 2.0s - it is a walk-away, not a step.",
     "evidence": ["terra_motion/strips/c5_walk_in_long.png",
                  "terra_motion/strips/c1_head_turn_long.png",
                  "terra_motion/strips/c3_turn_away_long.png",
                  "terra_motion/strips/c6_step_back.png"]},
    {"sec": "motion", "kind": "bad", "tool": "studio/_tools/terra_wardrobe.py",
     "claim": "A PLACE WITH A STRONG IMPLIED PROP CAN CAPTURE A GESTURE.",
     "saw": "hand_to_face in the library reading room did NOT complete: LTX put a RED BOOK "
            "in her hands and her hands went to the book instead of her face. Motion 0.452, "
            "the lowest of the nine clips. The motion card's own verdict says the gesture "
            "'COMPLETES at all four stagings' - it was measured across stagings, never "
            "across PLACES, and the place beat it here.",
     "evidence": ["terra_motion/strips/c2_hand_to_face.png"]},
    {"sec": "motion", "kind": "warn", "tool": "studio/_tools/terra_wardrobe.py",
     "claim": "STRUCTURAL DRIFT IS A POSE DETECTOR AS MUCH AS AN IDENTITY DETECTOR. Rank "
              "with it; never conclude with it.",
     "saw": "On walk_in_long the figure oscillates 16-40 with no trend because it is tracking "
            "her MOUTH opening and closing, while the face is visibly identical throughout. "
            "On head_turn_long it is non-monotonic - 62, 65, 59, 56 - because she turns "
            "partway and comes back. Also: LTX re-frames, so a head window measured on the "
            "keyframe creeps off the head (1.275 on head_turn_long) and the green-hair "
            "number then reads as her hair leaving frame when it has not.",
     "evidence": ["terra_motion/strips/c5_walk_in_long.png",
                  "terra_motion/faces/c4_hair_lifts.png"]},
]}


def _keep(cid, sec):
    """The LOOKED_AT entries for one section whose evidence is actually on disk."""
    out = []
    for f in LOOKED_AT.get(str(cid).upper(), []):
        if f.get("sec") != sec:
            continue
        ev = _pack(_img(f"{CAST}/{p}", os.path.basename(p)) for p in f.get("evidence", []))
        if not ev:
            continue                    # the picture is gone, so the claim goes with it
        out.append({"claim": f["claim"], "saw": f["saw"], "kind": f.get("kind", "note"),
                    "tool": f.get("tool", ""), "evidence": ev, "looked_at": True})
    return out


# ---------------------------------------------------------------------------
# the card, and the claims it makes about the filesystem
# ---------------------------------------------------------------------------
def card(cid):
    p = f"{HERE}/characters/{cid}.json"
    if not os.path.isfile(p):
        for fn in sorted(os.listdir(f"{HERE}/characters")):
            if fn.lower() == f"{str(cid).lower()}.json":
                p = f"{HERE}/characters/{fn}"
                break
    return _load(p), p


_BARE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _sheet(name):
    """A reference sheet named on a card, mirrored into samples/_refsheets/ so it can be
    shown.

    ComfyUI/input is the only directory LoadImage reads and the only place these live, and
    the static handler serves studio/ only. Rather than widen that handler into an
    arbitrary-path file server, the one file a card NAMES is copied into the same mirror
    directory serve.py's cast payload uses - re-copied whenever size or mtime move, so a
    sheet being re-rendered while the page is open appears on the next refresh.

    serve.py mirrors `sheet` and not `sheet_photo`, which is why the photographic sheet was
    invisible on this page until this did it too. Same directory, same rules.
    """
    if not name:
        return None
    base = os.path.basename(str(name))
    src = f"{COMFY}/input/{base}"
    e = {"name": base, "input_path": src, "exists": os.path.isfile(src), "url": None}
    if not e["exists"] or not _BARE.match(base) or not base.lower().endswith(IMG):
        return e
    dst = f"{SAMPLES}/_refsheets/{base}"
    try:
        st = os.stat(src)
        try:
            d = os.stat(dst)
            stale = d.st_size != st.st_size or d.st_mtime < st.st_mtime
        except OSError:
            stale = True
        if stale:
            os.makedirs(f"{SAMPLES}/_refsheets", exist_ok=True)
            with open(src, "rb") as a, open(dst + ".part", "wb") as b:
                b.write(a.read())
            os.replace(dst + ".part", dst)
            os.utime(dst, (st.st_atime, st.st_mtime))
        e["url"] = _url(dst)
    except OSError:
        pass                            # it is there, we just cannot show it
    return e


def _lora(name):
    if not name:
        return {"name": None, "exists": False}
    p = f"{COMFY}/models/loras/{name}"
    return {"name": name, "path": p, "exists": os.path.isfile(p),
            "bytes": os.path.getsize(p) if os.path.isfile(p) else None}


def _dataset(cid):
    d = f"{COMFY}/input/{str(cid).lower()}_train"
    if not os.path.isdir(d):
        return {"dir": d, "exists": False, "pairs": 0}
    imgs, caps = set(), set()
    for f in os.listdir(d):
        stem, ext = os.path.splitext(f)
        if ext.lower() in IMG:
            imgs.add(stem)
        elif ext.lower() == ".txt":
            caps.add(stem)
    return {"dir": d, "exists": True, "images": len(imgs), "captions": len(caps),
            "pairs": len(imgs & caps)}


def _resolver(cid):
    """What compose.resolve() says holds this face, per engine - the same call the renderer
    makes, so this page and the wizard cannot disagree about the same character."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    try:
        import compose
        libs = compose.load_libs()
    except Exception as e:                                          # noqa: BLE001
        return {"error": "%s: %s" % (type(e).__name__, e)}
    out = {}
    for eng in ("anime", "qwen"):
        try:
            r = compose.resolve(libs, {"character": cid, "engine": eng})
            out[eng] = {"prompt": r.get("prompt"), "negative": r.get("negative"),
                        "lora": r.get("lora"), "lora_active": bool(r.get("lora_active")),
                        "lora_reason": r.get("lora_reason"),
                        "layers": [x for x in (r.get("layers") or [])
                                   if x.get("layer") in ("character", "wear")],
                        "conflicts": [x for x in (r.get("conflicts") or [])
                                      if "character" in (x.get("layers") or [])]}
        except Exception as e:                                      # noqa: BLE001
            out[eng] = {"error": "%s: %s" % (type(e).__name__, e)}
    return out


# ---------------------------------------------------------------------------
# section builders. Each returns {"state": measured|partial|missing, ...}
# ---------------------------------------------------------------------------
def who(c, cid):
    return {"state": "measured" if c.get("tags") and c.get("prose") else "partial",
            "desc": c.get("desc", ""), "status": c.get("status"),
            "tags": c.get("tags", ""), "base_tags": c.get("base_tags", ""),
            "prose": c.get("prose", ""), "photo_prose": c.get("photo_prose", ""),
            "provenance": c.get("provenance"), "provenance_note": c.get("provenance_note"),
            "source": c.get("source"), "source_note": c.get("source_note"),
            "note": c.get("note"),
            "sheet_anime": _sheet(c.get("sheet")),
            "sheet_photo": _sheet(c.get("sheet_photo")),
            "sheet_photo_verdict": c.get("sheet_photo_verdict"),
            "face_reference": _img(f"{CAST}/{str(cid).lower()}_face_reference.png",
                                   "face reference",
                                   "kept separately from the photographic sheet - the "
                                   "better FACE, no costume"),
            "photo_probe": _img(f"{CAST}/{str(cid).lower()}_photo_probe.jpg",
                                "photographic sheet probe",
                                "four treatments at one seed; the cosplay failure and its fix"),
            "known_probe": _img(f"{CAST}/known_{str(cid).lower()}_probe.jpg",
                                "known-character probe",
                                "what the bare name, the danbooru form and the description "
                                "alone each return before any of this was built"),
            "findings": _keep(cid, "who")}


def holds(c, cid):
    lo = _lora(c.get("lora"))
    # lora_previous is prose that names the superseded weight files, and it names some of
    # them twice (the file and its .keep byte copy). Ordered, de-duplicated, current one
    # dropped - it is already the row above.
    seen, prev = set(), []
    for m in re.finditer(r"character_[a-z0-9_]+\.safetensors", str(c.get("lora_previous", ""))):
        f = m.group(0)
        if f not in seen and f != lo.get("name"):
            seen.add(f)
            prev.append(_lora(f))
    return {"state": "measured" if lo["exists"] else
            ("partial" if _sheet(c.get("sheet")) and _sheet(c.get("sheet"))["exists"]
             else "missing"),
            "resolver": _resolver(cid),
            "lora": lo, "lora_previous": prev,
            "lora_strength_measured": c.get("lora_strength_measured"),
            "lora_steps": c.get("lora_steps"), "lora_rank": c.get("lora_rank"),
            "lora_dataset": c.get("lora_dataset"),
            "lora_trained_at": c.get("lora_trained_at"),
            "lora_training_note": c.get("lora_training_note"),
            "lora_verdict": c.get("lora_verdict"),
            "lora_setting_verdict": c.get("lora_setting_verdict"),
            "dataset": _dataset(cid),
            "sheet_anime": _sheet(c.get("sheet")),
            "sheet_photo": _sheet(c.get("sheet_photo")),
            "lora_check": _img(f"{CAST}/{str(cid).lower()}_lora_check.jpg", "LoRA check",
                               "same seed, weights on and weights dropped"),
            "costume_fix": _pack(_img(f"{CAST}/{str(cid).lower()}_costume_fix/{f}",
                                      _pretty(f))
                                 for f in _ls(f"{CAST}/{str(cid).lower()}_costume_fix")),
            "findings": _keep(cid, "holds")}


def _turnaround(cid):
    """samples/cast/<ID>/ - the 16 views, each with the caption that trained on it.

    The caption is shown because captioning is the mechanism that decides what stays
    separable from the trigger, and it is invisible everywhere else in the app.
    """
    sets = []
    if not os.path.isdir(CAST):
        return sets
    up = str(cid).upper()
    for d in sorted(os.listdir(CAST)):
        if not os.path.isdir(f"{CAST}/{d}"):
            continue
        if d.upper() != up and not d.upper().startswith(up + "_"):
            continue
        # <id>_views, <id>_styles and the rest of the sweep directories match that prefix
        # too, so a turnaround is identified by its CONTENT: numbered NN_name.png files,
        # which is what turnaround.py writes and what train_character.py reads.
        names = [f for f in _ls(f"{CAST}/{d}") if re.match(r"^\d{1,2}[_-]", f)]
        if len(names) < 4:
            continue
        views = []
        for f in names:
            if f.startswith("_"):
                continue                          # deliberately not a turnaround view
            cap = ""
            txt = f"{CAST}/{d}/{os.path.splitext(f)[0]}.txt"
            if os.path.isfile(txt):
                try:
                    cap = open(txt, encoding="utf-8").read().strip()
                except OSError:
                    cap = ""
            e = _img(f"{CAST}/{d}/{f}", _pretty(f), cap, caption_is="training caption")
            if e:
                views.append(e)
        if views:
            sets.append({"dir": f"samples/cast/{d}",
                         "name": "the trained default" if d.upper() == up
                                 else d.split("_", 1)[-1],
                         "views": views})
    return sets


def looks(c, cid):
    vd = _stage_dir(cid, "views")
    m = _load(f"{vd}/measurements.json", {}) if vd else {}
    turn = _turnaround(cid)
    out = {"turnaround": turn,
           "turnaround_views": sum(len(t["views"]) for t in turn),
           "measurements": m, "dir": _rel(vd) if vd else None,
           "findings": _keep(cid, "looks")}

    def grid(sub, key, title, why, num=None, sheet=None):
        d = f"{vd}/{sub}" if vd else None
        cells = []
        for f in (_ls(d) if d else []):
            stem = os.path.splitext(f)[0]
            n = None
            if num:
                n = num.get(stem) or num.get(re.sub(r"^\d+_", "", stem))
            cells.append(_img(f"{d}/{f}", _pretty(f), "", score=n))
        return {"id": key, "title": title, "why": why,
                "sheet": _img(f"{vd}/{sheet}", title) if (vd and sheet) else None,
                "cells": _pack(cells), "numbers": num or {}}

    if vd:
        # The elevation cells are named fb_0worm_front on disk and fullbody_worm_front in
        # the numbers, so the scores are re-keyed to the filenames rather than the page
        # being handed two vocabularies for the same twenty cells.
        HGT = {"worm": "0worm", "low": "1low", "eye": "2eye", "high": "3high", "bird": "4bird"}
        elev = {}
        for k, v in (m.get("elevation_vs_eye_front") or {}).items():
            scale, height, yaw = k.split("_", 2)
            if height in HGT:
                elev["%s_%s_%s" % ("fb" if scale == "fullbody" else "wu",
                                   HGT[height], yaw)] = v
        out["grids"] = _pack([
            grid("octants", "octants", "the turnaround an animator would work from",
                 "Eight NAMED views at full figure. Named views work where degrees do not.",
                 m.get("octant_vs_front"), "sheet_octants.jpg"),
            grid("yaw", "yaw", "24 camera angles, 15 degrees apart",
                 "Asked for as numbers. Read the phrasing probe before reading this.",
                 {("yaw_" + k): v for k, v in (m.get("yaw_vs_front") or {}).items()},
                 "sheet_yaw.jpg"),
            grid("yawprobe", "yawprobe", "four phrasings, three angles - the control",
                 "This is what says the number in the yaw sweep is doing nothing.",
                 None, "sheet_yawprobe.jpg"),
            grid("yaw_rotate_failed", "yaw_failed", "the rolled sweep, kept as evidence",
                 "'rotate the camera N degrees' is read as an IMAGE TRANSFORM.",
                 None, "sheet_yaw_rotate_failed.jpg"),
            grid("elevation", "elevation", "five camera heights x three yaws",
                 "The extremes are re-read as camera DISTANCE, so there are three stops.",
                 elev, "sheet_elevation.jpg"),
            grid("frames", "frames", "the shot-size ladder, six sizes x three seeds",
                 "On the PRODUCTION path. Rows are sizes, columns are seeds, so identity "
                 "drift reads left to right.",
                 {k + "_s" + s: v for k, v in (m.get("frames_vs_medium_close") or {}).items()
                  for s in ("4242", "7411", "9090")}, "sheet_frames.jpg"),
        ])
        em = []
        for f in _ls(f"{vd}/emotions"):
            stem = os.path.splitext(f)[0]
            name, _, seed = stem.rpartition("_s")
            em.append(_img(f"{vd}/emotions/{f}", name or stem, "",
                           seed=seed,
                           vs_neutral=(m.get("emotion_vs_neutral") or {}).get(name),
                           cross_seed=(m.get("emotion_cross_seed") or {}).get(name)))
        out["emotions"] = {"cells": _pack(em),
                           "sheets": _pack([_img(f"{vd}/sheet_emotions_s4242.jpg", "seed 4242"),
                                            _img(f"{vd}/sheet_emotions_s7411.jpg", "seed 7411")]),
                           "vs_neutral": m.get("emotion_vs_neutral") or {},
                           "cross_seed": m.get("emotion_cross_seed") or {}}
        out["metric_note"] = m.get("_what", "")
        out["sheet_note"] = m.get("_sheets", {})
    else:
        out["grids"], out["emotions"] = [], {"cells": [], "sheets": []}
    out["state"] = ("measured" if (vd and out["grids"] and turn) else
                    "partial" if turn else "missing")
    return out


_GARMENT = re.compile(r"\b([a-z]+)\s+(dress|gown|coat|cape|cloak|tabard|robe|jacket|"
                      r"breastplate|plate|armour|armor|uniform|suit|gloves|sash)\b")


def _garments(text):
    """Garment phrases in a wear string, reduced to one adjective plus the noun - so
    'sleeveless gold dress' and 'the gold dress' both come out as 'gold dress'."""
    return {"%s %s" % m for m in _GARMENT.findall(str(text).lower())}


def _costume_text_conflicts(costumes, default_key="default"):
    """A costume whose own text names a garment belonging to the DEFAULT costume.

    The model renders nouns, so a rung that reads 'travelling coat over the gold dress'
    names the very garment it exists to replace, and what comes back is the gold dress with
    no coat. MEASURED on Terra's field coat, which fails at exactly the two damage levels
    this check flags and lands at the three it does not.

    A text check, not a render check - it costs nothing and runs before any image is made,
    so any character with a costumes map can be cleared before a GPU is booked.
    """
    if not isinstance(costumes, dict) or len(costumes) < 2:
        return []
    dk = default_key if default_key in costumes else sorted(costumes)[0]
    mine = set()
    for rung in costumes[dk].get("wear_tags") or []:
        mine |= _garments(rung)
    # a garment worn in every costume is a shared item, not one costume's signature
    for k, cc in costumes.items():
        if k == dk:
            continue
        if mine and mine <= set().union(*[_garments(r) for r in
                                          (cc.get("wear_tags") or [""])]):
            mine = set()
    out = []
    for k, cc in costumes.items():
        if k == dk:
            continue
        rungs = cc.get("wear_tags") or []
        for i, rung in enumerate(rungs):
            for g in sorted(_garments(rung) & mine):
                # The last rung of every ladder in this project is the costume DESTROYED,
                # so naming what is underneath is deliberate there and a real instruction
                # everywhere else. Flagged either way, ranked apart.
                out.append({"costume": k, "level": i, "garment": g,
                            "belongs_to": dk, "text": rung,
                            "terminal": i == len(rungs) - 1})
    return out


def wears(c, cid):
    wd = _stage_dir(cid, "wardrobe")
    costumes = c.get("costumes") or {}
    if not costumes and c.get("wear_tags"):
        costumes = {"default": {"name": "default", "desc": "the only costume on this card",
                                "wear_tags": c["wear_tags"]}}
    grids = []
    for f in _ls(wd or "", (".jpg", ".png", ".webp")):
        if not f.startswith("costume_"):
            continue
        stem = os.path.splitext(f)[0]
        lora_v = "v3" if "_v3" in stem else ("v1" if "_v1" in stem else "?")
        name = "kept" if "_name" in stem else "stripped"
        seed = stem.split("_s")[-1] if "_s" in stem else "4242"
        grids.append(_img(f"{wd}/{f}",
                          "LoRA %s, danbooru name %s, seed %s" % (lora_v, name, seed),
                          "rows are the four costumes, columns the five damage levels",
                          lora=lora_v, danbooru_name=name, seed=seed))
    # The two probes that turned _costume_text_conflicts() from a warning into a
    # measurement: the same rungs rendered with the shipped text and with it reworded.
    probes = []
    for f in _ls(wd or "", (".jpg",)):
        if f.startswith("field_fix_"):
            probes.append(_img(f"{wd}/{f}",
                               "naming the garment it replaces - %s"
                               % f[len("field_fix_"):-4].replace("_", ", "),
                               "top row shipped text, bottom row with the gold dress "
                               "taken out of levels 0 and 3"))
        elif f.startswith("damage_nouns_"):
            probes.append(_img(f"{wd}/{f}",
                               "damage as a removal - %s"
                               % f[len("damage_nouns_"):-4].replace("_", ", "),
                               "top row the shipped subtractive wording, bottom row the "
                               "same state written as objects that are present"))
    places = _pack([_img(f"{wd}/places_grid.jpg", "18 places, six families",
                         "one seed per place - a screening pass, not a verdict") if wd else None,
                    _img(f"{wd}/places_faces.jpg", "the same 18, cropped to the head",
                         "the head locator missed about five of eighteen") if wd else None,
                    _img(f"{wd}/recheck_floating_islands.jpg", "one odd cell, six seeds",
                         "the recheck that proved the place innocent") if wd else None])
    return {"state": "measured" if (grids and costumes) else
            ("partial" if costumes else "missing"),
            "costumes": costumes, "costume_note": c.get("costume_note"),
            "costume_verdict": c.get("costume_verdict"),
            "costume_text_rule": c.get("costume_text_rule"),
            "lora_costume_verdict": c.get("lora_costume_verdict"),
            "wear_tags": c.get("wear_tags") or [],
            "text_conflicts": _costume_text_conflicts(c.get("costumes") or {}),
            "grids": _pack(grids), "places": places, "text_probes": _pack(probes),
            "dir": _rel(wd) if wd else None,
            "findings": _keep(cid, "wears")}


def drawn(c, cid):
    sd = _stage_dir(cid, "styles")
    v = _load(f"{sd}/{_V}", {}) if sd else {}
    m = _load(f"{sd}/measurements.json", {}) if sd else {}
    lib = {}
    for fn in sorted(os.listdir(f"{HERE}/styles")) if os.path.isdir(f"{HERE}/styles") else []:
        if fn.endswith(".json"):
            s = _load(f"{HERE}/styles/{fn}")
            if isinstance(s, dict):
                lib[str(s.get("id") or fn[:-5])] = s
    rows = {"anime": [], "qwen": []}
    for eng, pre in (("anime", "a_"), ("qwen", "q_")):
        for sid, ver in sorted((v.get(eng) or {}).items()):
            mm = m.get(pre + sid) or {}
            m2 = m.get(pre + sid + "_s7788") or {}
            card_ = lib.get(sid) or {}
            hold = ver.get("id_3311"), ver.get("id_7788")
            rows[eng].append({
                "id": sid, "name": card_.get("name") or sid,
                "family": mm.get("family") or card_.get("family") or "",
                "style": ver.get("style"), "id_3311": hold[0], "id_7788": hold[1],
                "saw": ver.get("saw", ""),
                "shortlist": ver.get("style") == "strong" and hold == ("yes", "yes"),
                "conditional": ver.get("style") == "strong" and hold[0] == "yes"
                               and hold[1] != "yes",
                "compose": mm.get("lib_compose") or card_.get("compose") or "",
                "lib_verdict": mm.get("lib_verdict") or card_.get("verdict") or "",
                "metrics": mm.get("metrics") or {},
                "metrics_7788": m2.get("metrics") or {},
                "prompt": mm.get("prompt", ""), "negative": mm.get("negative", ""),
                "seed": mm.get("seed"),
                "cell": _img(f"{sd}/cells/{pre}{sid}.webp", sid,
                             "seed %s" % mm.get("seed", "")) if sd else None,
                "cell_7788": _img(f"{sd}/cells/{pre}{sid}_s7788.webp", sid,
                                  "seed 7788") if sd else None})
    sheets = _pack(_img(f"{sd}/{f}", _pretty(f)[6:] if f.startswith("sheet_") else _pretty(f))
                   for f in _ls(sd or "", (".jpg",)))
    control = _pack([_img(f"{sd}/cells/a__control.webp", "no style, anime, seed 3311"),
                     _img(f"{sd}/cells/q__control.webp", "no style, qwen, seed 3311")]) \
        if sd else []
    return {"state": "measured" if rows["anime"] or rows["qwen"] else "missing",
            "held_constant": v.get("held_constant") or {}, "key": v.get("key") or {},
            "verified_by": v.get("verified_by", ""), "intro": v.get("_", ""),
            "styles": rows, "sheets": sheets, "control": control,
            "dir": _rel(sd) if sd else None,
            "card_verdict": c.get("style_verdict"),
            "findings": _keep(cid, "drawn")}


def motion(c, cid):
    md = _stage_dir(cid, "motion")
    res = _load(f"{md}/results.json", []) if md else []
    man = _load(f"{md}/manifest.json", []) if md else []
    by = {r.get("id"): r for r in res if isinstance(r, dict)}
    clips = []
    for entry in (man or res):
        cid_ = entry.get("id")
        r = by.get(cid_, entry)
        secs = r.get("secs")
        idx = r.get("sample_idx") or []
        fps = round(r["frames"] / secs) if (r.get("frames") and secs) else 24
        clips.append({
            "id": cid_, "motion": r.get("motion_id"), "place": r.get("place"),
            "text": r.get("text"), "want": r.get("want"),
            "seconds": secs, "frames": r.get("frames"), "lora": r.get("lora"),
            "metrics": {k: r.get(k) for k in
                        ("motion", "churn", "frozen", "creep", "ssim_last_vs_f0")
                        if r.get(k) is not None},
            "samples": [{"t": round(i / fps, 2), "drift_struct": (r.get("drift_struct") or [None])[n]
                         if n < len(r.get("drift_struct") or []) else None,
                         "drift_hue": (r.get("drift_hue") or [None])[n]
                         if n < len(r.get("drift_hue") or []) else None,
                         "green_pct": (r.get("green_pct") or [None])[n]
                         if n < len(r.get("green_pct") or []) else None}
                        for n, i in enumerate(idx)],
            "strip": _img(f"{md}/strips/{cid_}.png", "nine sampled frames",
                          "read the strip, not the numbers"),
            "faces": _img(f"{md}/faces/{cid_}.png", "the same nine, cropped to the head"),
            "keyframe": _img(f"{md}/keyframes/{r.get('kf', cid_)}.png", "the still it grew from"),
            # The mp4 is in ComfyUI's output tree, which the static handler will not open.
            # serve.py streams it through /character/<id>/clip/<clip id>.mp4 instead.
            "clip_url": ("/character/%s/clip/%s.mp4" % (cid, cid_)
                         if r.get("file") and os.path.isfile(r["file"]) else None),
            "clip_path": r.get("file"),
            "error": r.get("error")})
    return {"state": "measured" if clips else "missing",
            "clips": clips, "dir": _rel(md) if md else None,
            "card_verdict": c.get("motion_verdict"),
            "findings": _keep(cid, "motion")}


def _voice_card(raw):
    if not raw:
        return None
    parts = str(raw).split()
    engine, wav = parts[0], parts[-1]
    base = os.path.basename(wav).lower()
    d = f"{HERE}/voices"
    best = None
    for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not fn.endswith(".json"):
            continue
        vc = _load(f"{d}/{fn}")
        if not isinstance(vc, dict):
            continue
        if vc.get("engine") == engine and str(vc.get("file", "")) == wav:
            return vc
        if os.path.basename(str(vc.get("file", ""))).lower() == base:
            best = best or vc
    return best


def sound(c, cid):
    sd = _stage_dir(cid, "voice")
    m = _load(f"{sd}/measurements.json", {}) if sd else {}
    vc = _voice_card(c.get("voice"))

    def clips(sub, numbers):
        out = []
        for f in _ls(f"{sd}/{sub}" if sd else "", AUDIO):
            stem = os.path.splitext(f)[0]
            n = (numbers or {}).get(stem) or {}
            out.append({"id": stem, "url": _url(f"{sd}/{sub}/{f}"),
                        "path": _rel(f"{sd}/{sub}/{f}"),
                        "n": {k: n.get(k) for k in
                              ("seconds", "peak_dbfs", "rms_dbfs", "pitch_median_hz",
                               "centroid_hz", "rolloff85_hz", "pitch_range_semitones",
                               "silence_frac", "onsets_per_sec_speech", "wer")
                              if n.get(k) is not None},
                        "text": n.get("expected_text", "")})
        return out

    lines = c.get("voice_lines") or {}
    spec = c.get("voice_spec") or {}
    # The spec's own keys ARE the card's field names with a rank prefix: 6_voice_lines
    # describes the card key voice_lines. So the checklist is checked against the card
    # rather than against a second list that could drift from it. Key 0_ is the essay
    # explaining why the list exists and is not a field.
    have = []
    for k in sorted(spec, key=lambda x: int(x.split("_", 1)[0])
                    if re.match(r"^\d+_", x) else 99):
        mm = re.match(r"^([1-9]\d*)_(.+)$", k)
        if not mm:
            continue
        field = mm.group(2)
        have.append({"n": int(mm.group(1)), "field": field, "asks": spec[k],
                     "present": bool(c.get(field)),
                     "required": str(spec[k]).startswith("REQUIRED")})
    return {"state": "measured" if (vc and sd and m) else
            ("partial" if c.get("voice") else "missing"),
            "voice": c.get("voice"), "voice_card": vc,
            "blocked": bool(vc and vc.get("status") == "blocked"),
            "verdict": c.get("voice_verdict"),
            "engine_verdict": c.get("voice_engine_verdict"),
            "direction": c.get("voice_direction"),
            "range_note": c.get("voice_range_note"),
            "library_verdict": c.get("voice_library_verdict"),
            "emotion_routing": c.get("voice_emotion_routing"),
            "note": c.get("voice_note"),
            "audition_meta": c.get("voice_audition") or {},
            "audition": clips("audition", m.get("audition")),
            "lines": clips("lines_indextts2", m.get("lines_indextts2")),
            "lines_meta": lines,
            "lines_higgs": clips("lines_higgs", m.get("lines_higgs")),
            "lines_unbounded": clips("lines_indextts2_unbounded",
                                     m.get("lines_indextts2_unbounded")),
            "emotion_sweep": clips("emotion_sweep", m.get("emotion_sweep")),
            "emotion_probe": clips("emotion_probe", m.get("emotion_probe")),
            "sheets": _pack(_img(f"{sd}/{f}", _pretty(f)) for f in _ls(sd or "", (".png",))),
            "spec": have, "spec_intro": spec.get("_", ""),
            "verification_standard": spec.get("verification_standard", ""),
            "spec_why": spec.get("0_why_this_list_exists", ""),
            "dir": _rel(sd) if sd else None,
            "findings": _keep(cid, "sound")}


# ---------------------------------------------------------------------------
# CONTESTED - where the card and a later render disagree.
#
# This is the section the project's own discipline demands and the one a normal profile
# page would never have. Three of these are known-and-unfixed because the file that needs
# editing is owned by somebody else; printing them beside the render that contradicts them
# is the honest alternative to silently preferring one.
# ---------------------------------------------------------------------------
CONTESTED = {"TERRA": [
    # FOUR ENTRIES WERE REMOVED HERE ON 2026-08-04 BECAUSE THEY WERE FIXED, not because
    # they stopped being true: costume_verdict blaming the weights alone, costume_verdict
    # and lora_costume_verdict both saying the field coat FAILS, costume_note claiming
    # damage is orthogonal to wardrobe, style_verdict recording a five-style probe, and a
    # status_note saying nothing had been rendered. All five now read what the renders
    # show, and costume_verdict keeps its own "THIS FIELD PREVIOUSLY SAID" paragraph so
    # the correction is legible on the card rather than only here. What is left below is
    # what a render still contradicts.
    {"field": "tags - 'red hair ribbon'",
     "says": "she wears a red hair ribbon.",
     "but": "Every one of 160 view renders draws a large pink/lilac-and-gold ornament with "
            "a red gem and two upswept gold prongs that read as horns. It is in the source "
            "sheet, so both engines inherit it, and it is now trained into the weights. "
            "DELIBERATELY NOT FIXED: editing the tag would move every render of her and "
            "would not change the sheet or the LoRA. Fixing it for real means a new sheet "
            "and a retrain. Written up on the card as identity_note.",
     "evidence": ["terra_views/sheet_octants.jpg"]},
    {"field": "tags - 'sleeveless gold dress with red and blue pattern'",
     "says": "one bodice, gold with a red and blue pattern.",
     "but": "On the anime production path the bodice flips between gold-with-spots and "
            "red-with-florals seed by seed, and cell by cell at the SAME seed - angry has "
            "a red bodice and awe a gold one, both at 4242. The costume work fixed which "
            "GARMENT arrives; this is the garment's COLOUR, a different bug, and it is "
            "live in every shot.",
     "evidence": ["terra_views/sheet_frames.jpg",
                  "terra_views/sheet_emotions_s4242.jpg"]},
]}


def contested(cid):
    out = []
    for x in CONTESTED.get(str(cid).upper(), []):
        ev = _pack(_img(f"{CAST}/{p}", os.path.basename(p)) for p in x.get("evidence", []))
        if ev:
            out.append(dict(x, evidence=ev))
    return out


# ---------------------------------------------------------------------------
# WHAT IS UNKNOWN. Half computed from the disk, half the standing caveats that each
# sweep recorded about its own method.
# ---------------------------------------------------------------------------
STANDING = {"TERRA": [
    ("sound", "NOTHING WAS HEARD. There are no ears on this box. Every voice judgement is "
              "measurement plus waveform and mel-spectrogram inspection plus ASR - and all "
              "33 renders scored word error rate 0.000, including the one that came back a "
              "shriek, so ASR eliminated nobody. Play the four line renders before this "
              "voice goes into a film, and listen for whether maya reads as CAREFUL, which "
              "is what she was cast for, or merely BLAND."),
    ("motion", "NOTHING WAS WATCHED AS VIDEO. Every motion verdict comes from nine sampled "
               "frames per clip. A flicker, a one-frame face swap or a smear that resolves "
               "between samples is unobserved. The clips are embedded above - play them."),
    ("sound", "SIX OF THE EIGHT EMOTION DIMENSIONS ARE UNSWEPT. Only Angry (max 0.4) and "
              "Afraid (saturates 0.8) have measured ceilings. Happy, Sad, Surprised, "
              "Disgusted, Calm and Melancholic have none. Sad 1.0 produced a 26.7-semitone "
              "range and 42% silence, which is either a beautiful broken delivery or a "
              "malfunction, and only listening will say which."),
    ("sound", "THE EMOTION LIBRARY IS NOT WIRED. voice_style on all 27 emotion cards is an "
              "ADJECTIVE and the engine takes eight NAMED FLOATS; voice_rate has nothing to "
              "map to, because this node pack exposes no rate input at all; and compile.py "
              "builds its voices map as engine+wav, so a finished mapping still has no "
              "channel - even though short.py already consumes cfg['emotion']. The consumer "
              "exists and the producer does not."),
    ("drawn", "THE 0.85 ESCALATION IS RECOMMENDED, NOT SWEPT. It restores hair and costume "
              "on all 11 failing styles at one seed and visibly weakens the style. The full "
              "66-style sweep was not re-run at 0.85, intermediate strengths were not tried, "
              "and 0.85 was not checked at the second seed."),
    ("drawn", "EVERY STYLE VERDICT RESTS ON ONE PLACE, ONE COSTUME AND ONE FRAMING - a "
              "walled daylight exterior with stone, sky and banners. Place is exactly the "
              "axis the composition-hijack finding says matters most."),
    ("drawn", "FIFTEEN ANIME STYLES ARE CONDITIONAL - strong and holding at seed 3311, "
              "failed at 7788. Until a third seed or the 0.85 escalation is measured on "
              "each, they are coin tosses, and they include four a director is most likely "
              "to reach for."),
    ("looks", "THE SIMILARITY NUMBER IS A WHOLE-FRAME CLIP COSINE, NOT A FACE ID SCORE. "
              "There is no face recogniser on this box. It is confounded by background, "
              "pose and subject size - the bird's-eye row scores low because she is SMALL. "
              "It was used only where the confound cancels, and every verdict was decided "
              "by looking."),
    ("looks", "EVERY QWEN-EDIT STAGE IS ONE SEED PER CELL. The handedness collapse, the "
              "three elevation stops and the four phrasings all rest on single samples. "
              "The yaw result is the exception: 24 cells at 24 seeds all saying the same "
              "thing."),
    ("looks", "THE SEVEN FAILING EMOTION CARDS WERE RENDERED EXACTLY AS AUTHORED. Whether "
              "moving 'hunched, collapsed' out of despair's `body` field fixes it is the "
              "obvious next experiment and has not been run."),
    ("wears", "THE COSTUME CONCLUSIONS REST ON ONE PLACE (a plain stone courtyard) AND ONE "
              "FRAMING (full body). A throne room or a battlefield could plausibly rescue "
              "the armour rows that collapse at high damage."),
    ("wears", "THE FIELD-COAT FIX IS UNTESTED. 'Remove the gold dress from the text and the "
              "coat will land' is an inference from the two rungs that already work, not a "
              "measurement - the wear_tags were not reworded and re-rendered."),
    ("wears", "THE PLACES SWEEP IS ONE SEED PER PLACE. One cell was rechecked because it "
              "looked wrong; a place that happened to look FINE at its one seed but usually "
              "breaks her would not have been caught."),
    ("motion", "ALL NINE CLIPS USE ONE VIDEO SEED AND ONE LoRA STRENGTH - and the character "
               "LoRA is not in the video graph at all, so nothing here says whether the "
               "raised 0.85 ceiling would change a clip."),
    ("holds", "THE 0.85 CEILING IS MEASURED IN TWO PLACES, NOT ACROSS THE 64-PLACE LIBRARY. "
              "lora_strength_measured stays 0.5 because every existing film was built "
              "against it."),
    ("holds", "v2 WAS NEVER RENDERED ON THE DAMAGE AXIS. 'monotone v1 < v2 < v3' is neither "
              "confirmed nor denied there; only v1 against v3 was compared."),
]}


def unknown(cid, secs, spec):
    """The honest gaps: what the disk says is missing, then the standing caveats."""
    gaps = []

    def add(kind, sec, what, how="", blocked=""):
        gaps.append({"kind": kind, "section": sec, "what": what, "how": how,
                     "blocked": blocked})

    for s in spec:
        st = s["state"]
        # A command that would render the WRONG CHARACTER is not a fix, so a blocked
        # section shows the obstacle and no command at all.
        cmd = "" if s.get("blocked") else (s.get("cmd") or s.get("note") or "")
        if st == "missing":
            add("absent", s["id"], "Nothing on disk for '%s' - %s." % (s["title"], s["asks"]),
                cmd, s.get("blocked") or "")
        elif st == "partial":
            add("partial", s["id"], "'%s' is only partly built." % s["title"],
                cmd, s.get("blocked") or "")

    snd = secs.get("sound") or {}
    for f in snd.get("spec", []):
        if f["required"] and not f["present"]:
            add("absent", "sound", "voice spec field %s (%s) is missing." % (f["n"], f["field"]))
        if not f["required"] and not f["present"]:
            add("optional", "sound",
                "voice spec field %s (%s) is unset on every card in the project." %
                (f["n"], f["field"]))

    for tc in (secs.get("wears") or {}).get("text_conflicts", []):
        if tc.get("terminal"):
            continue                # the last rung is the costume destroyed, by convention
        add("bug", "wears",
            "costume '%s' level %d names '%s', which belongs to '%s' - the model renders "
            "nouns, so that garment arrives and this costume's does not."
            % (tc["costume"], tc["level"], tc["garment"], tc["belongs_to"]))

    for sec, txt in STANDING.get(str(cid).upper(), []):
        add("caveat", sec, txt)
    return gaps


# ---------------------------------------------------------------------------
def build(cid):
    c, path = card(cid)
    if not isinstance(c, dict):
        return {"error": "no character card for %r" % cid, "id": cid}
    cid = str(c.get("id") or cid)
    secs = {"who": who(c, cid), "holds": holds(c, cid), "looks": looks(c, cid),
            "wears": wears(c, cid), "drawn": drawn(c, cid), "motion": motion(c, cid),
            "sound": sound(c, cid)}
    spec = []
    for s in SPEC:
        spec.append(dict(s, state=(secs.get(s["id"]) or {}).get("state", "missing"),
                         **_how(s, cid)))
    gaps = unknown(cid, secs, [x for x in spec if x["id"] != "unknown"])
    secs["unknown"] = {"state": "measured", "gaps": gaps, "contested": contested(cid)}
    for s in spec:
        if s["id"] == "unknown":
            s["state"] = "measured"
    return {"id": cid, "name": c.get("name") or cid, "desc": c.get("desc", ""),
            "status": c.get("status"), "card_path": _rel(path),
            "card": c, "spec": spec, "sections": secs,
            "generated_by": "studio/_tools/dossier.py"}


def index():
    """Every cast member with a state per section - the cast list this page can offer."""
    d = f"{HERE}/characters"
    out = []
    for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not fn.endswith(".json"):
            continue
        c = _load(f"{d}/{fn}")
        if not isinstance(c, dict):
            out.append({"id": fn[:-5], "name": fn[:-5], "unreadable": True, "spec": []})
            continue
        cid = str(c.get("id") or fn[:-5])
        states = {}
        for fn_, key in ((who, "who"), (holds, "holds"), (looks, "looks"), (wears, "wears"),
                         (drawn, "drawn"), (motion, "motion"), (sound, "sound")):
            try:
                states[key] = fn_(c, cid)["state"]
            except Exception:                                       # noqa: BLE001
                states[key] = "missing"
        states["unknown"] = "measured"
        out.append({"id": cid, "name": c.get("name") or cid, "desc": c.get("desc", ""),
                    "status": c.get("status"), "states": states,
                    "measured": sum(1 for v in states.values() if v == "measured"),
                    "portrait": ((_turnaround(cid) or [{}])[0].get("views") or [{}])[0]
                                .get("url")})
    out.sort(key=lambda x: (-x.get("measured", 0), x["id"]))
    return {"characters": out, "spec": SPEC}


def clip_path(cid, clip_id):
    """The absolute path of one motion clip, RESOLVED THROUGH THE MANIFEST.

    The mp4s live in ComfyUI's output tree, outside anything the static handler will open.
    Rather than widen that handler, serve.py asks here and gets back either a path that the
    manifest for THIS character vouches for, or None. The id never becomes part of a path.
    """
    md = _stage_dir(cid, "motion")
    if not md:
        return None
    for entry in (_load(f"{md}/manifest.json", []) or []) + (_load(f"{md}/results.json", []) or []):
        if isinstance(entry, dict) and entry.get("id") == clip_id:
            f = entry.get("file")
            if f and os.path.isfile(f) and f.lower().endswith(".mp4"):
                return f
    return None


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("character", nargs="?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--index", action="store_true")
    a = ap.parse_args()

    if a.index or not a.character:
        ix = index()
        if a.json:
            print(json.dumps(ix, indent=1))
            return
        keys = [s["id"] for s in SPEC]
        print("%-10s %s" % ("", "  ".join(k[:6].ljust(6) for k in keys)))
        for ch in ix["characters"]:
            print("%-10s %s" % (ch["id"], "  ".join(
                {"measured": "  ok  ", "partial": " part ", "missing": "  --  "}
                [ch["states"].get(k, "missing")] for k in keys)))
        return

    d = build(a.character)
    if d.get("error"):
        sys.exit(d["error"])
    if a.json:
        print(json.dumps(d, indent=1))
        return
    print("%s  (%s)  %s" % (d["name"], d["id"], d.get("status") or ""))
    print("card: %s" % d["card_path"])
    for s in d["spec"]:
        sec = d["sections"][s["id"]]
        extra = ""
        if s["id"] == "looks":
            extra = "%d turnaround views, %d grids, %d expression cells" % (
                sec.get("turnaround_views", 0), len(sec.get("grids") or []),
                len((sec.get("emotions") or {}).get("cells") or []))
        elif s["id"] == "drawn":
            extra = "%d anime + %d qwen styles" % (len(sec["styles"]["anime"]),
                                                   len(sec["styles"]["qwen"]))
        elif s["id"] == "wears":
            extra = "%d costumes, %d grids, %d text conflicts" % (
                len(sec.get("costumes") or {}), len(sec.get("grids") or []),
                len(sec.get("text_conflicts") or []))
        elif s["id"] == "motion":
            extra = "%d clips" % len(sec.get("clips") or [])
        elif s["id"] == "sound":
            extra = "%d audition + %d line renders" % (len(sec.get("audition") or []),
                                                       len(sec.get("lines") or []))
        elif s["id"] == "unknown":
            extra = "%d gaps, %d contested card fields" % (len(sec["gaps"]),
                                                           len(sec["contested"]))
        print("  %-8s %-9s %-8s %s" % (s["id"], s["state"],
                                       "", extra))
    n = sum(len((d["sections"][k] or {}).get("findings") or []) for k in d["sections"])
    print("  %d looked-at findings carried, each with its evidence on disk" % n)


if __name__ == "__main__":
    main()
