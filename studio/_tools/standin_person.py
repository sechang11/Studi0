#!/usr/bin/env python3
"""Build a SYNTHETIC STAND-IN: a photo set that behaves like real photographs of one
person who does not exist.

    --stage casting    6 candidate people, one prompt, six seeds. LOOK, then pick.
    --stage anchor     the chosen candidate re-rendered large: the reference plate
    --stage set        the snapshot set, reference-locked through the qwen edit path
    --stage control    the SAME framings with NO reference - the arm that makes the
                       reference-path number mean something
    --stage ideal      the A-pose sculpt-ready target, 1536+ long edge
    --stage matte      BiRefNet on the ideal, so the alpha is measured not assumed
    --stage faces      crop the face out of every image, by hand-set boxes, for measuring
    --stage measure    embed the crops and report WITHIN-person vs BETWEEN-person
    --stage publish    assemble standin/ and write MANIFEST.json

THIS TOOL HAS ARGPARSE AND DOES NOTHING AT IMPORT TIME. Seventeen of the sixty tools in
this directory run their whole job on any argument including --help; this one does not.

*** THE SUBJECT IS SYNTHETIC AND MUST STAY SYNTHETIC. ***
Every pixel here comes from Qwen-Image out of the prose in PERSON below. No photograph of
any real person is fetched, used or referenced, and no celebrity or public-figure token
appears in any prompt. The point of the stand-in is that the pipeline can be built and
measured before anyone's real photographs are involved.

WHY A CHECKLIST OF MARKS AND NOT JUST "A WOMAN".
Identity is testable only if there are things to test. A face that is merely "similar" can
be argued about forever. So this person carries five CONCRETE marks - round gold wire-frame
glasses, a mole on one cheek, dark brown hair just past the shoulders with a grown-out
fringe, small gold stud earrings, and a mustard corduroy jacket - and every downstream
stage of the wave can be scored on how many of the five survive. Two of them are
deliberately awkward for a mesher (thin wire glasses, fine hair), which is the point.

WHY THERE IS A CONTROL ARM, AND WHY THE CASTING REJECTS ARE KEPT.
A single "cosine similarity 0.82" is not a measurement, it is a number. Two controls make
it one:

  BETWEEN-PERSON FLOOR - stage siblings. The plan was to use the five REJECTED casting
  candidates as the floor, on the reasoning that six seeds of one prompt give six
  different people. THEY DO NOT. Measured here: at cfg 1.0 on the 4-step Lightning path,
  six seeds of the prose in FACE returned SIX RENDERS OF ONE WOMAN - the window moves, the
  hair falls a little differently, the face does not change. Qwen's identity is carried by
  the DESCRIPTION, and the seed only moves what the description left unsaid. So the
  rejects are worthless as a floor, and a floor has to be built on purpose: six SIBLINGS,
  each an ordinary woman in her thirties in the same jacket under the same window,
  differing only in the face and the marks. SIB6 is the hard case - same gold round
  glasses, same skin tone, same hair colour and length, a different face - and it is the
  one the measurement lives or dies on.

  NO-REFERENCE ARM - stage control. Four framings are also rendered from the prose alone,
  with no reference image. Given what casting showed about prose carrying identity, this
  is no longer a formality: it says how much of the set's consistency the edit path
  actually bought and how much the words were doing by themselves. That distinction
  matters downstream, because a real friend's photographs arrive with no prose at all.

WHY THE FACE BOXES ARE HAND-SET AND NOT DETECTED.
There is no face detector on this box that works: insightface, cv2, facexlib and mediapipe
are all absent from both pythons, LoadMediaPipeFaceLandmarker has no landmarker file in
models/detection (only sam3), and SDPoseFaceBBoxes needs a POSE_KEYPOINT from
SDPoseKeypointExtractor, which wants a whole diffusion MODEL and VAE. Rather than pretend,
the boxes in FACE_BOXES are normalised and were set BY LOOKING at each render, and
--stage faces writes a contact sheet of the crops so the crops themselves can be checked.
A crop that missed the face would poison the measurement silently; the sheet is what stops
that.
"""
import argparse
import json
import os
import urllib.request
import shutil
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, HOST          # noqa: E402

OUT = os.path.join(ROOT, "studio", "samples", "photo2anime", "standin")
WORK = os.path.join(OUT, "_work")
COMFY_IN = os.path.expanduser("~/ComfyUI/input")

# ---------------------------------------------------------------- the person

# THE FACE. Held byte-identical in every prompt, reference-path and control-path alike,
# so the control arm is a fair test of the words rather than of a different description.
FACE = (
    "a woman in her early thirties, ordinary looking rather than glamorous, an oval face "
    "with a slightly crooked nose and uneven eyebrows, warm light-olive skin with visible "
    "pores, faint under-eye shadows and a few small blemishes, no makeup, dark brown eyes, "
    "thin round gold wire-frame glasses, a small dark mole on her right cheek about an "
    "inch below the eye, dark brown hair falling just past her shoulders, parted on the "
    "left, with a grown-out fringe tucked behind one ear"
)

WEAR_A = "a mustard yellow corduroy jacket over a plain white t-shirt"
WEAR_B = "a grey marl ribbed wool sweater"
WEAR_C = "a navy and white horizontally striped long-sleeve cotton shirt"

# Real photographs are not clean. Naming the grain and the ordinary lens is what keeps
# Qwen off its default glamour render, which is the thing that would make the stand-in
# behave unlike a snapshot of a friend.
SNAP = ("a candid amateur photograph, taken on a phone, slight sensor noise, ordinary "
        "unretouched skin")

NEG = ("cartoon, anime, illustration, painting, drawing, 3d render, cgi, plastic skin, "
       "doll, mannequin, wig, glamour retouching, airbrushed, beauty filter, fashion "
       "model, studio glamour, oversaturated, watermark, text, signature, deformed, "
       "extra limbs, extra fingers, fused fingers, blurry, lowres")

CAST_PROMPT = (
    "A head and shoulders photograph of %s. She wears %s. Soft daylight from a window to "
    "camera-left, plain pale wall behind her, she is looking at the camera with a neutral "
    "expression. %s" % (FACE, WEAR_A, SNAP)
)
CAST_SEEDS = [10101, 20202, 30303, 40404, 50505, 60606]

# ---------------------------------------------------------------- the floor
# Six DIFFERENT people, built by hand because seeds do not make different people here.
# Everything outside the face is held identical to the stand-in's casting frame: same
# jacket, same window, same wall, same framing, same amateur-photo treatment. So any
# similarity these score against the stand-in is what two strangers get for free, and any
# gap above it is identity.
#
# They are ordered easy to hard. SIB6 shares the glasses, the skin tone, the hair colour
# and the hair length with the stand-in and differs only in the face itself. If the
# measurement cannot separate the stand-in from SIB6 it cannot separate anything.
SIBLINGS = [
    ("SIB1_far", 11001,
     "a woman in her early thirties, a round face with full cheeks, wide-set grey-green "
     "eyes, a snub nose, pale freckled skin, no glasses, short ash-blonde hair cut in a "
     "chin-length bob"),
    ("SIB2_far", 11002,
     "a woman in her early thirties, a long face with a strong square jaw, dark brown "
     "eyes, deep brown skin, heavy black rectangular acetate glasses, black hair pulled "
     "back tightly into a bun"),
    ("SIB3_mid", 11003,
     "a woman in her early thirties, a heart-shaped face with a pointed chin, hazel eyes, "
     "very pale skin heavily freckled across the nose and cheeks, no glasses, coppery "
     "red-brown wavy hair falling to the middle of her back"),
    ("SIB4_mid", 11004,
     "a woman in her early thirties, a broad square face, thin lips, narrow dark eyes, "
     "olive skin, thin silver rectangular glasses, dark hair cropped very short"),
    ("SIB5_near", 11005,
     "a woman in her early thirties, a soft round face, hooded brown eyes, light tan skin, "
     "round tortoiseshell glasses, straight dark hair cut to the chin with a blunt fringe "
     "across the forehead"),
    # THE HARD ONE. Same marks, different face.
    ("SIB6_hard", 11006,
     "a woman in her early thirties, a narrow face with high cheekbones and a long "
     "straight nose, dark brown eyes, warm light-olive skin, thin round gold wire-frame "
     "glasses, dark brown hair falling just past her shoulders"),
]

# ---------------------------------------------------------------- the set

# id, seed, wear, w, h, prose, intent
# intent: "good" = meant to be usable, "dud" = DELIBERATELY imperfect, "stress" = an
# identity stress test (a mark removed on purpose, to find out what the face alone carries)
SHOTS = [
    ("01_window_3q", 7001, WEAR_A, 1024, 1280,
     "a head and shoulders photograph, turned three-quarters to camera-left, soft daylight "
     "from a tall window, a plain pale grey wall behind her, neutral expression", "good"),
    ("02_front_flat", 7002, WEAR_A, 1024, 1280,
     "a head and shoulders photograph, straight on to the camera, flat even indoor "
     "lighting, a plain white wall behind her, neutral expression", "good"),
    ("03_profile", 7003, WEAR_B, 1024, 1280,
     "a head and shoulders photograph in full side profile facing camera-left, soft "
     "daylight, a plain pale wall behind her", "good"),
    ("04_3q_right", 7004, WEAR_B, 1024, 1280,
     "a head and shoulders photograph turned three-quarters to camera-right, looking at "
     "the camera, soft overcast daylight, plain background", "good"),
    ("05_kitchen_busy", 7005, WEAR_A, 1216, 928,
     "a candid waist-up photograph in a cluttered domestic kitchen, warm ceiling light, "
     "open shelves crowded with jars mugs and a plant behind her, she is mid-sentence "
     "looking slightly off camera", "dud"),
    ("06_outdoor_overcast", 7006, WEAR_A, 1024, 1280,
     "a waist-up photograph outdoors on a grey overcast day, flat soft light, a blurred "
     "hedge and pavement behind her, hands in her jacket pockets", "good"),
    # 07 and 08 CARRY THE SHOES LEVER. Their first pass asked for "a full length
    # photograph" and got two more waist-up frames, at 896x1344, with "cropped, out of
    # frame" sitting in the negative the whole time. Naming the shoes - an object that has
    # to be drawn - is what put the feet in the frame, and the taller latent gives them
    # somewhere to go. Same lesson as the A-pose, arrived at independently.
    ("07_outdoor_sun_full", 7007, WEAR_C, 1024, 1792,
     "a full length photograph outdoors in hard midday sunlight, strong shadow under the "
     "chin and nose, squinting slightly, a sunlit brick wall behind her, standing with "
     "her weight on one hip, her whole body down to her white canvas shoes in the frame "
     "and her shoes visible near the bottom edge with pavement below them", "dud"),
    ("08_fullbody_plain", 7008, WEAR_B, 1024, 1792,
     "a full length photograph standing against a plain pale grey wall indoors, soft even "
     "light, arms at her sides, her whole body down to her white canvas shoes in the "
     "frame, her shoes visible near the bottom edge and clear space above her head", "good"),
    ("09_seated_cafe", 7009, WEAR_C, 1216, 928,
     "a candid photograph of her seated at a small cafe table, one elbow on the table, a "
     "coffee cup in front of her, warm tungsten light from above mixed with cold daylight "
     "from a window behind, other tables out of focus behind her", "dud"),
    ("10_selfie_wide", 7010, WEAR_A, 1024, 1280,
     "a phone selfie held at arm's length, slight wide-angle lens distortion enlarging the "
     "nose, harsh overhead ceiling light, a hallway behind her, one shoulder raised toward "
     "the camera", "dud"),
    ("11_off_axis_dim", 7011, WEAR_B, 1024, 1280,
     "a slightly off-axis snapshot, the horizon tilted a few degrees, her head turned away "
     "and tipped, dim evening room light, a doorway behind her, mild motion blur", "dud"),
    ("12_mixed_light", 7012, WEAR_A, 1024, 1280,
     "a waist-up photograph in a living room at dusk, a warm orange table lamp lighting "
     "one side of her face and cold blue window light on the other, a sofa and bookshelf "
     "behind her", "dud"),
    ("13_over_shoulder", 7013, WEAR_C, 1024, 1280,
     "a photograph from behind and to the side, she has turned to look back over her right "
     "shoulder at the camera, soft daylight, a plain wall behind her", "good"),
    ("14_no_glasses", 7014, WEAR_B, 1024, 1280,
     "a head and shoulders photograph with her glasses removed and held in one hand, faint "
     "pressure marks on the bridge of her nose, soft window light, plain pale background", "stress"),
    ("15_hair_up", 7015, WEAR_C, 1024, 1280,
     "a head and shoulders photograph with her hair tied back in a low ponytail, loose "
     "strands at the temples, soft daylight, plain background", "stress"),
    ("16_laughing", 7016, WEAR_A, 1024, 1280,
     "a candid head and shoulders photograph caught mid-laugh, eyes creased shut, head "
     "tipped back slightly, soft daylight from a window, plain pale wall", "good"),
]

# The shots that need the standing-distance reference pair rather than the portrait one.
FULL_FIGURE = {"07_outdoor_sun_full", "08_fullbody_plain"}

# The four framings the no-reference arm repeats. Chosen to span the set: two easy
# portraits, one full body, one busy scene.
CONTROL_IDS = ["02_front_flat", "04_3q_right", "08_fullbody_plain", "05_kitchen_busy"]

# ---------------------------------------------------------------- the ideal one

IDEAL_W, IDEAL_H = 1536, 2304
IDEAL_PROSE = (
    "A full length photograph of the woman from image 1, standing squarely facing the "
    "camera in an A-pose: both arms held straight down and away from her body at about "
    "forty-five degrees, elbows straight, a clear gap of background visible between each "
    "arm and her torso, hands relaxed into loose closed fists, feet shoulder width apart, "
    "head level and facing the camera. She wears %s. Completely flat even shadowless "
    "lighting from the front, a plain uniform mid grey background with no floor line and "
    "no cast shadow anywhere. Her whole figure is in frame with clear space above her head "
    "and below her feet. Keep her face, her round gold wire-frame glasses, the mole on her "
    "right cheek, her earrings and her hair exactly as in image 1." % WEAR_A
)
# "no cast shadow" in a POSITIVE prompt is a negation and does not render - the word has to
# be in the NEGATIVE. Measured on terra_3d_source_v2, kept here rather than re-derived.
IDEAL_NEG = NEG + (", cast shadow, drop shadow, floor, ground, floor line, reflection, "
                   "gradient background, vignette, cropped, out of frame, close-up, "
                   "arms at sides, arms touching body, crossed arms, hands on hips, "
                   "splayed fingers, open hands, spread fingers, dynamic pose, from below")
IDEAL_SEEDS = [8801, 8802, 8803, 8804]

# ---------------------------------------------------------------- the A-pose probe
#
# IDEAL_PROSE ABOVE IS THE VERSION THAT FAILED, and it is kept verbatim as the probe's
# control arm so the comparison is honest. Rendered against the head-and-shoulders anchor
# at 1536x2304 it returned four images that were:
#   NOT FULL LENGTH  - every one cropped at mid-thigh, despite "her whole figure is in
#                      frame" in the positive and "cropped, out of frame" in the negative.
#   NOT AN A-POSE    - arms hanging straight down flat against the torso, no background
#                      visible between arm and waist. That is precisely the "touching arms
#                      fuse into a blob" failure a mesher cannot recover from.
#
# Both failures are the same mistake, and it is the one this project has already paid for
# twice: THE MODEL RENDERS NOUNS, NOT DESCRIPTIONS. "Her whole figure is in frame" and
# "arms away from her body at forty-five degrees" are both descriptions of a state. They
# name nothing to draw. And "no cast shadow" and "cropped" sitting in the negative cannot
# manufacture a body part that was never composed.
#
# So each arm of this probe replaces a description with a NOUN the model can put pixels on:
#   the frame   name the SHOES. Feet are the thing being cropped off, and a shoe is an
#               object; "whole figure" is not.
#   the pose    name the GAP. A triangle of visible background between arm and waist is an
#               object with a shape; "forty-five degrees" is a measurement.
# The mode axis asks the other half of the question - whether the head-and-shoulders
# reference plate is itself what is dragging the framing in, in which case the A-pose has
# to be built WITHOUT a reference and identity has to come from the prose. Casting showed
# the prose alone holds this face, so that is a real option rather than a fallback.

APOSE_W, APOSE_H = 1152, 2048
APOSE_ARMS = [
    ("A1_control", "both arms held straight down and away from her body at about "
                   "forty-five degrees, elbows straight, a clear gap of background "
                   "visible between each arm and her torso, hands relaxed into loose "
                   "closed fists"),
    ("A2_gap_noun", "her arms angled out from her sides so that a clear triangle of empty "
                    "grey background is visible between each arm and her waist, elbows "
                    "straight, both hands closed into loose fists"),
    ("A3_mannequin", "posed like a shop window mannequin, both arms lifted away from her "
                     "sides with empty grey background all around each arm, elbows "
                     "straight, hands closed into loose fists"),
]
APOSE_FRAME = ("Her whole body is in the photograph from the top of her hair down to her "
               "white canvas shoes, and her shoes are visible near the bottom edge of the "
               "frame with grey background below them. She is standing well back from the "
               "camera.")
APOSE_SEED = 8801

# ---------------------------------------------------------------- A-pose, round two
#
# WHAT ROUND ONE SETTLED, so nobody re-derives it:
#
#   THE SHOES LEVER WORKS, COMPLETELY. All six probe cells put the feet in frame, against
#   0 of 4 before. Naming an OBJECT that has to be visible is what moves a crop; "whole
#   figure in frame" in the positive and "cropped" in the negative did nothing across four
#   seeds. This is the noun rule again and it is now measured twice on this job.
#
#   THE NO-REFERENCE ARM IS DEAD FOR FULL BODY. All three noref cells came back with a
#   huge head on tiny legs - a wide-angle dwarf. Prose that describes a face in detail AND
#   asks for a full figure makes Qwen spend the frame on the face. The reference plate is
#   what supplies correct human proportion, so full-body work is reference-locked or it is
#   nothing. (Note this is the OPPOSITE of the casting finding: prose alone holds the
#   IDENTITY fine, it just cannot hold the CAMERA.)
#
#   GAP-AS-A-NOUN BACKFIRED ON THE REFERENCE PATH. "A clear triangle of empty grey
#   background between each arm and her waist" returned a severed body - floating torso,
#   no legs between the jacket hem and the shoes. Asking for background INSIDE the
#   silhouette got background, in the wrong place. Rejected.
#
#   AND THE ARMS ARE STILL NOT OPEN. Every surviving cell hangs the arms along the torso.
#   The reference plate is a head-and-shoulders frame with no arm information in it, and
#   what the model does with an unspecified limb is put it where it usually goes.
#
# SO ROUND TWO STOPS ARGUING WITH THE POSE IN WORDS AND HANDS IT A PICTURE. Qwen-Edit
# 2511's headline capability is multi-image composition, and workflow 23 already uses it
# to take a person from one image and a place from another. The same lever takes a POSE
# from one image and an IDENTITY from another: image1 is a throwaway A-pose plate of
# nobody in particular, image2 is the stand-in's face plate, and the prompt says which to
# take from which. Two other arms are kept as controls so the fusion has something to beat.

APOSE2_NEG = IDEAL_NEG + (", arms down, arms hanging straight down, arms along the sides, "
                          "arms touching the torso, arms against the body, hands in "
                          "pockets, elbows bent, arms folded, severed body, missing legs, "
                          "floating torso, disconnected limbs")

# The pose plate. Identity is irrelevant here - it is scaffolding and gets thrown away, so
# the prose says as little about the face as possible and everything about the pose.
# "photogrammetry body scan reference" is doing the real work: it is a NAMED CATEGORY of
# photograph that is always full length, always flat lit, always on a plain background and
# always in an open-limbed pose. One noun buys the entire brief.
PLATE_PROSE = (
    "A photogrammetry body scan reference photograph of a standing woman, full length, "
    "her whole body from the top of her head down to her white canvas shoes inside the "
    "frame. She stands in an A-pose: both arms held out and away from her sides so there "
    "is a wide open space between each arm and her body, elbows straight, hands closed "
    "into loose fists, feet shoulder width apart. She wears a plain grey t-shirt and plain "
    "grey leggings. Completely flat even shadowless studio lighting, a plain uniform mid "
    "grey background."
)
PLATE_SEEDS = [9101, 9102]

# ---------------------------------------------------------------- face boxes
# normalised x, y, w, h - SET BY LOOKING at each render. --stage faces writes a contact
# sheet of the crops so a box that missed can be seen rather than trusted.
def _b(src, x, y, w, h):
    return {"src": src, "x": x, "y": y, "w": w, "h": h}


# These are the SECOND pass. The first pass put every box too high: the proof sheet came
# back full of foreheads with the eyes on the bottom edge and no nose, mouth or chin in
# frame at all - and the siblings were the worst of them, which would have compared the
# floor's HAIRLINES against the stand-in's face. The numbers from that would have looked
# perfectly reasonable. This is exactly what the proof sheet exists to catch, and it is
# why nothing here is measured off boxes that have not been looked at.
FACE_BOXES = {}
for _k, _x, _y, _w, _h in [
    ("01_window_3q", 0.24, 0.12, 0.44, 0.42), ("02_front_flat", 0.28, 0.12, 0.44, 0.42),
    ("03_profile", 0.32, 0.10, 0.42, 0.40), ("04_3q_right", 0.30, 0.12, 0.44, 0.42),
    ("05_kitchen_busy", 0.36, 0.24, 0.24, 0.46), ("06_outdoor_overcast", 0.34, 0.16, 0.34, 0.32),
    ("07_outdoor_sun_full", 0.34, 0.04, 0.30, 0.20), ("08_fullbody_plain", 0.36, 0.24, 0.32, 0.24),
    ("09_seated_cafe", 0.36, 0.22, 0.22, 0.40), ("10_selfie_wide", 0.38, 0.24, 0.36, 0.34),
    ("11_off_axis_dim", 0.46, 0.22, 0.34, 0.32), ("12_mixed_light", 0.36, 0.24, 0.36, 0.34),
    ("13_over_shoulder", 0.24, 0.16, 0.38, 0.36), ("14_no_glasses", 0.32, 0.20, 0.40, 0.38),
    ("15_hair_up", 0.32, 0.16, 0.38, 0.36), ("16_laughing", 0.38, 0.18, 0.38, 0.36),
]:
    FACE_BOXES["SET_" + _k] = _b("set/%s.png" % _k, _x, _y, _w, _h)
for _k, _x, _y, _w, _h in [
    ("02_front_flat", 0.26, 0.16, 0.48, 0.44), ("04_3q_right", 0.26, 0.16, 0.50, 0.46),
    ("05_kitchen_busy", 0.38, 0.22, 0.22, 0.46), ("08_fullbody_plain", 0.34, 0.20, 0.36, 0.34),
]:
    FACE_BOXES["CTL_" + _k] = _b("control/%s.png" % _k, _x, _y, _w, _h)
for _s, _, _ in SIBLINGS:
    FACE_BOXES["SIB_" + _s] = _b("siblings/%s.png" % _s, 0.28, 0.12, 0.44, 0.48)
FACE_BOXES["REF_anchor"] = _b("anchor/anchor_face.png", 0.16, 0.16, 0.68, 0.52)
FACE_BOXES["IDL_apose"] = _b("final/IDEAL_1152x2048.png", 0.40, 0.045, 0.20, 0.115)


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def _prefix(sub, tag):
    return "claude-generated/standin/%s/%s" % (sub, tag)


def _fetch(outs, dest):
    if not outs:
        return None
    return ensure_local(outs[0], dest, required=False)


def t2i(prose, neg, seed, w, h, tag, sub):
    """Pure text to image on Qwen. Node 7 is the style-LoRA slot and stays at 0.0 - a
    style LoRA would pull this off photography, which is the whole point of the stand-in."""
    wf = load_wf("13_qwen_t2i_styled.json")
    set_path(wf, "10.inputs.text", prose)
    set_path(wf, "11.inputs.text", neg)
    set_path(wf, "12.inputs.width", w)
    set_path(wf, "12.inputs.height", h)
    set_path(wf, "13.inputs.seed", seed)
    set_path(wf, "7.inputs.strength_model", 0.0)
    set_path(wf, "15.inputs.filename_prefix", _prefix(sub, tag))
    _, outs = run(HOST, wf, quiet=True)
    return _fetch(outs, os.path.join(WORK, sub, tag + ".png"))


def ref2i(prose, neg, seed, w, h, tag, sub, ref_name, ref2_name=None, denoise=None):
    """REFERENCE mode on 14_qwen_edit_ref: image1 conditions a FRESH composition drawn
    into an empty latent (node 20), rather than being repainted as a canvas (node 12).
    That is what lets the framing, pose and background move while the face is held.

    IMAGE ORDER IS NOT COSMETIC. Measured on the A-pose work: with a pose plate as image1
    and the stand-in's face as image2, the OUTPUT WORE THE PLATE'S FACE and took only the
    glasses from image2. image1 is the dominant conditioning; image2 decorates it. So the
    picture you want the identity from goes FIRST, and everything else is image2.

    Passing `denoise` switches to EDIT mode: the latent starts from image1 as a canvas
    (node 12) instead of empty (node 20), so composition survives and only the requested
    amount is repainted. That is the lever for fixing a face without losing a pose."""
    wf = load_wf("14_qwen_edit_ref.json")
    set_path(wf, "8.inputs.image", ref_name)
    set_path(wf, "9.inputs.image", ref2_name or ref_name)
    if ref2_name:
        set_path(wf, "10.inputs.image2", ["9", 0])
        set_path(wf, "11.inputs.image2", ["9", 0])
    set_path(wf, "10.inputs.prompt", prose)
    set_path(wf, "11.inputs.prompt", neg)
    set_path(wf, "20.inputs.width", w)
    set_path(wf, "20.inputs.height", h)
    set_path(wf, "13.inputs.seed", seed)
    set_path(wf, "7.inputs.strength_model", 0.0)
    if denoise is not None:
        set_path(wf, "13.inputs.latent_image", ["12", 0])   # the canvas, not the void
        set_path(wf, "13.inputs.denoise", float(denoise))
    set_path(wf, "15.inputs.filename_prefix", _prefix(sub, tag))
    _, outs = run(HOST, wf, quiet=True)
    return _fetch(outs, os.path.join(WORK, sub, tag + ".png"))


def sheet(paths, labels, dst, cols, cw=480, ch=640):
    """Contact sheet, with the cell count ASSERTED from the output pixels.

    TWO TRAPS, both already paid for here.

    tile= IS A SINGLE-STREAM FILTER. It tiles the FRAMES of one input. Handing ffmpeg six
    separate -i files and one tile= consumes input 0 and silently emits a sheet with five
    black cells - which is exactly what the first run of this tool produced, and it looks
    like five failed renders rather than one wrong filtergraph. So the cells are written as
    a numbered SEQUENCE and read back through the image2 demuxer as one stream.

    tile= ALSO DROPS CELLS OF DIFFERING SIZE. Every cell is therefore scaled AND padded to
    exactly cw x ch before it goes near the tiler, and the grid is filled out to a whole
    rectangle with blanks so the last row cannot be short.

    Neither of those is visible in the output, so the sheet is measured afterwards: the
    finished image must be exactly the grid arithmetic, or this raises.
    """
    if not paths:
        return None
    tmp = os.path.join(WORK, "_sheet")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    n = 0
    for p, lab in zip(paths, labels):
        c = os.path.join(tmp, "cell_%03d.png" % n)
        r = sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
               "scale=%d:%d:force_original_aspect_ratio=decrease,"
               "pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=0x101010,"
               "drawtext=text='%s':fontcolor=yellow:fontsize=20:x=8:y=8:"
               "box=1:boxcolor=black@0.85:boxborderw=5"
               % (cw, ch, cw, ch, lab.replace(":", "\\:").replace("'", "")), c)
        if os.path.exists(c):
            n += 1
        else:
            print("  cell failed for %s: %s" % (p, r.stderr[-200:]))
    real = n
    rows = (n + cols - 1) // cols
    while n < rows * cols:
        sh("ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
           "color=c=0x101010:s=%dx%d" % (cw, ch), "-frames:v", "1",
           os.path.join(tmp, "cell_%03d.png" % n))
        n += 1
    m, pad = 8, 8
    r = sh("ffmpeg", "-y", "-v", "error", "-framerate", "1", "-start_number", "0",
           "-i", os.path.join(tmp, "cell_%03d.png"),
           "-vf", "tile=%dx%d:margin=%d:padding=%d:color=0x101010" % (cols, rows, m, pad),
           "-frames:v", "1", "-q:v", "3", dst)
    if not os.path.exists(dst):
        raise SystemExit("contact sheet failed: %s" % r.stderr[-400:])
    want_w = cols * cw + (cols - 1) * pad + 2 * m
    want_h = rows * ch + (rows - 1) * pad + 2 * m
    got = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height", "-of", "csv=p=0", dst).stdout.strip()
    if got != "%d,%d" % (want_w, want_h):
        raise SystemExit("sheet %s is %s but the %dx%d grid must be %d,%d - cells were "
                         "dropped" % (dst, got, cols, rows, want_w, want_h))
    print("  sheet %s  (%d real cells in a %dx%d grid, %s px - verified)"
          % (dst, real, cols, rows, got))
    return dst


# ---------------------------------------------------------------- stages

def stage_casting():
    os.makedirs(os.path.join(WORK, "casting"), exist_ok=True)
    paths, labels = [], []
    for i, s in enumerate(CAST_SEEDS):
        tag = "cand%d_s%d" % (i + 1, s)
        print("  casting %s" % tag, flush=True)
        p = t2i(CAST_PROMPT, NEG, s, 1152, 1408, tag, "casting")
        if p:
            paths.append(p)
            labels.append("%d  seed %d" % (i + 1, s))
    sheet(paths, labels, os.path.join(WORK, "casting_sheet.jpg"), 3, 520, 640)
    print("\nLOOK before picking. If these are six renders of ONE woman rather than six "
          "women, the seed is not moving identity and the floor must come from "
          "--stage siblings instead.")


def stage_siblings():
    """The between-person floor. See the module docstring: this exists because the casting
    seeds did not produce different people."""
    os.makedirs(os.path.join(WORK, "siblings"), exist_ok=True)
    paths, labels = [], []
    for sid, seed, face in SIBLINGS:
        prose = ("A head and shoulders photograph of %s. She wears %s. Soft daylight from "
                 "a window to camera-left, plain pale wall behind her, she is looking at "
                 "the camera with a neutral expression. %s" % (face, WEAR_A, SNAP))
        print("  sibling %s" % sid, flush=True)
        p = t2i(prose, NEG, seed, 1152, 1408, sid, "siblings")
        if p:
            paths.append(p)
            labels.append(sid)
    sheet(paths, labels, os.path.join(WORK, "siblings_sheet.jpg"), 3, 520, 640)
    print("\nSIB6_hard is the one that matters: same glasses, same skin, same hair, "
          "different face.")


def stage_anchor(pick):
    """The reference plate. A face is a pixel problem - this is rendered close and large
    so the plate itself has a face worth conditioning on."""
    os.makedirs(os.path.join(WORK, "anchor"), exist_ok=True)
    seed = CAST_SEEDS[pick - 1]
    close = ("A close head and shoulders photograph of %s. She wears %s and small gold "
             "stud earrings. Soft even daylight from a window to camera-left, a plain "
             "pale grey wall behind her, looking straight at the camera, neutral "
             "expression, the face fills most of the frame. %s"
             % (FACE, WEAR_A, SNAP))
    body = ("A waist-up photograph of %s. She wears %s and small gold stud earrings. "
            "Flat even indoor lighting, a plain pale grey wall behind her, standing "
            "squarely facing the camera, arms relaxed at her sides. %s"
            % (FACE, WEAR_A, SNAP))
    a = t2i(close, NEG, seed, 1216, 1600, "anchor_face", "anchor")
    b = t2i(body, NEG, seed, 1152, 1600, "anchor_body", "anchor")
    for p, n in ((a, "standin_anchor_face.png"), (b, "standin_anchor_body.png")):
        if p:
            shutil.copy(p, os.path.join(COMFY_IN, n))
            print("  -> %s (and into ComfyUI/input as %s)" % (p, n))
    sheet([x for x in (a, b) if x], ["anchor face", "anchor body"],
          os.path.join(WORK, "anchor_sheet.jpg"), 2, 560, 720)


def stage_set(only=None, ref2=True):
    """WHICH REFERENCE GOES IN SLOT 1 IS A FRAMING DECISION, not a bookkeeping one.

    The close head-and-shoulders anchor in slot 1 carries its CAMERA as well as its face.
    Every shot in this set that asked for a full figure came back at portrait distance:
    first cropped at the thigh, and then - once the shoes lever forced the feet into the
    frame - TILTED STEEPLY DOWNWARD, a look-at-my-own-shoes phone snap with a huge head on
    a foreshortened body. The model was holding the reference's camera distance and buying
    the feet by pitching down, which is the cheapest way to satisfy both.

    So full-figure shots get the pair the sculpt-ready render was settled on: the WAIST-UP
    anchor in slot 1, and the photogrammetry pose plate in slot 2 purely to supply standing
    distance and a level camera. The pose words still come from the shot line, so slot 2
    lends its camera without lending its A-pose."""
    os.makedirs(os.path.join(WORK, "set"), exist_ok=True)
    paths, labels = [], []
    for sid, seed, wear, w, h, prose, intent in SHOTS:
        if only and sid not in only:
            continue
        wide = sid in FULL_FIGURE
        print("  set %-22s %-6s %s" % (sid, intent, "wide-pair" if wide else "face-pair"),
              flush=True)
        # THE WIDE CLAUSE HAD TO BE FOUND, in three tries, and the winner is not the
        # obvious one:
        #   "the camera is level, several metres back"   -> waist-up, no feet. A camera
        #                                                   description, so: nothing.
        #   APOSE_FRAME alone (names the shoes)          -> waist-up, no feet. The shoes
        #                                                   noun alone beat a THIGH crop
        #                                                   earlier, but it cannot beat a
        #                                                   slot-1 portrait reference.
        #   "the same full length framing as image 2"    -> works.
        # The last one is the same trick the sculpt-ready render turned out to depend on:
        # slot 2 only lends its composition when the PROMPT NAMES IT. An unreferenced
        # image2 is decoration. So the wide pair and the phrase have to travel together -
        # either alone is worth nothing.
        cam = ((" She is photographed at the same distance and in the same full length "
                "framing as the person in image 2, standing well back from the camera. "
                + APOSE_FRAME) if wide else "")
        full = ("The woman in image 1. %s.%s She wears %s. %s Keep her face, her thin round "
                "gold wire-frame glasses, the small mole on her right cheek, her gold stud "
                "earrings and her hair exactly as in image 1."
                % (prose[0].upper() + prose[1:], cam, wear, SNAP))
        if wide:
            r1, r2 = "standin_anchor_body.png", "standin_pose_plate_1.png"
        else:
            r1, r2 = "standin_anchor_face.png", ("standin_anchor_body.png" if ref2 else None)
        p = ref2i(full, NEG, seed, w, h, sid, "set", r1, r2)
        if p:
            paths.append(p)
            labels.append("%s [%s]" % (sid, intent))
    sheet(paths, labels, os.path.join(WORK, "set_sheet.jpg"), 4, 440, 560)


def stage_control():
    """The same framings with NO reference image. This is what makes the set's number a
    measurement instead of an assertion."""
    os.makedirs(os.path.join(WORK, "control"), exist_ok=True)
    paths, labels = [], []
    for sid, seed, wear, w, h, prose, intent in SHOTS:
        if sid not in CONTROL_IDS:
            continue
        print("  control %s" % sid, flush=True)
        full = ("%s of %s. She wears %s and small gold stud earrings. %s"
                % (prose[0].upper() + prose[1:], FACE, wear, SNAP))
        p = t2i(full, NEG, seed, w, h, sid, "control")
        if p:
            paths.append(p)
            labels.append("noref %s" % sid)
    sheet(paths, labels, os.path.join(WORK, "control_sheet.jpg"), 4, 440, 560)


def stage_ideal():
    os.makedirs(os.path.join(WORK, "ideal"), exist_ok=True)
    paths, labels = [], []
    for s in IDEAL_SEEDS:
        tag = "apose_s%d" % s
        print("  ideal %s at %dx%d" % (tag, IDEAL_W, IDEAL_H), flush=True)
        p = ref2i(IDEAL_PROSE, IDEAL_NEG, s, IDEAL_W, IDEAL_H, tag, "ideal",
                  "standin_anchor_body.png", "standin_anchor_face.png")
        if p:
            paths.append(p)
            labels.append("A-pose seed %d" % s)
    sheet(paths, labels, os.path.join(WORK, "ideal_sheet.jpg"), 4, 420, 640)


def stage_apose():
    """arms treatment x reference-or-not. See the block above APOSE_ARMS for why."""
    os.makedirs(os.path.join(WORK, "apose"), exist_ok=True)
    paths, labels = [], []
    for aid, arms in APOSE_ARMS:
        for mode in ("noref", "ref"):
            tag = "%s_%s" % (aid, mode)
            print("  apose %s" % tag, flush=True)
            if mode == "ref":
                prose = ("A full length photograph of the woman in image 1, standing "
                         "squarely facing the camera, %s. She wears %s. %s Completely "
                         "flat even shadowless lighting from the front, a plain uniform "
                         "mid grey background. Keep her face, her round gold wire-frame "
                         "glasses, the mole on her cheek and her hair exactly as in "
                         "image 1." % (arms, WEAR_A, APOSE_FRAME))
                p = ref2i(prose, IDEAL_NEG, APOSE_SEED, APOSE_W, APOSE_H, tag, "apose",
                          "standin_anchor_body.png", "standin_anchor_face.png")
            else:
                prose = ("A full length photograph of %s. She wears %s. She is standing "
                         "squarely facing the camera, %s. %s Completely flat even "
                         "shadowless lighting from the front, a plain uniform mid grey "
                         "background. %s" % (FACE, WEAR_A, arms, APOSE_FRAME, SNAP))
                p = t2i(prose, IDEAL_NEG, APOSE_SEED, APOSE_W, APOSE_H, tag, "apose")
            if p:
                paths.append(p)
                labels.append(tag)
    sheet(paths, labels, os.path.join(WORK, "apose_sheet.jpg"), 6, 340, 604)
    print("\nRead the FEET first (is the shoe in frame at all), then the ARMPITS (is there "
          "background between arm and waist). A cell that fails either is not sculpt-ready "
          "however good the face is.")


def stage_apose2():
    """Pose from one picture, identity from another. See the block above PLATE_PROSE."""
    os.makedirs(os.path.join(WORK, "apose2"), exist_ok=True)
    paths, labels = [], []

    # 1. the throwaway pose plates
    plates = []
    for i, s in enumerate(PLATE_SEEDS):
        tag = "P%d_plate_s%d" % (i + 1, s)
        print("  plate %s" % tag, flush=True)
        p = t2i(PLATE_PROSE, APOSE2_NEG, s, APOSE_W, APOSE_H, tag, "apose2")
        if p:
            name = "standin_pose_plate_%d.png" % (i + 1)
            shutil.copy(p, os.path.join(COMFY_IN, name))
            plates.append(name)
            paths.append(p)
            labels.append(tag + " (scaffold)")

    # 2. two word-only controls on the reference path, so the fusion has to beat something
    for tag, arms in (("R_spread", "her arms spread out wide and away from her sides, well "
                                   "clear of her body, elbows straight, hands closed into "
                                   "loose fists"),
                      ("R_tpose", "both arms held out straight sideways from her shoulders "
                                  "like the arms of a letter T, elbows straight, hands "
                                  "closed into loose fists")):
        prose = ("A full length photograph of the woman in image 1, standing squarely "
                 "facing the camera with %s. She wears %s. %s Completely flat even "
                 "shadowless lighting, a plain uniform mid grey background. Keep her face, "
                 "her round gold wire-frame glasses and her hair exactly as in image 1."
                 % (arms, WEAR_A, APOSE_FRAME))
        print("  words  %s" % tag, flush=True)
        p = ref2i(prose, APOSE2_NEG, APOSE_SEED, APOSE_W, APOSE_H, tag, "apose2",
                  "standin_anchor_body.png", "standin_anchor_face.png")
        if p:
            paths.append(p)
            labels.append(tag + " (words only)")

    # 3. the fusion. image1 is the POSE, image2 is the PERSON, and the prompt says so
    #    literally - "image 1" / "image 2" is the phrasing TextEncodeQwenImageEditPlus
    #    responds to, per the note on workflow 23.
    for i, plate in enumerate(plates):
        for s in (9201, 9202):
            tag = "F_fuse_p%d_s%d" % (i + 1, s)
            prose = ("Redraw the photograph in image 1 so that the woman standing in it is "
                     "the woman from image 2. Keep the pose of image 1 exactly - the same "
                     "A-pose with both arms held out and away from her sides, the same "
                     "full length framing with her shoes near the bottom of the frame, the "
                     "same flat lighting and the same plain grey background. Take her face, "
                     "her round gold wire-frame glasses, her gold stud earrings and her "
                     "dark brown shoulder-length hair from image 2. Dress her in %s, dark "
                     "trousers and white canvas shoes." % WEAR_A)
            print("  fusion %s" % tag, flush=True)
            p = ref2i(prose, APOSE2_NEG, s, APOSE_W, APOSE_H, tag, "apose2",
                      plate, "standin_anchor_face.png")
            if p:
                paths.append(p)
                labels.append(tag + " (pose+face)")

    sheet(paths, labels, os.path.join(WORK, "apose2_sheet.jpg"), 4, 340, 604)
    print("\nThree things to read, in order: ARMPITS (background between arm and waist?), "
          "FEET (shoes in frame?), FACE (still her?). The plates are scaffolding and are "
          "not candidates.")


def stage_apose3():
    """Round three. Round two produced two half-answers and this stage tries to join them.

    WHAT ROUND TWO SETTLED:
      THE PLATE IS PERFECT. "A photogrammetry body scan reference photograph" returned, at
      both seeds, exactly the brief: full length, feet in frame, flat shadowless light,
      plain grey, and a true A-pose with open background between each arm and the torso.
      One named category of photograph bought what four rounds of adjectives could not.

      WORDS ALONE GIVE A T-POSE, NOT AN A-POSE. Both "arms spread out wide and away from
      her sides" and the explicit letter-T wording returned the SAME thing: arms straight
      out horizontally. Qwen appears to have one open-arm attractor and prose lands on it
      whatever angle is asked for. Identity survived - it is her - so this is a usable
      fallback, but the arms reach nearly to the frame edge and a T-pose deforms the
      shoulder for a mould.

      THE FUSION LOST THE FACE. Plate as image1 and her face as image2 gave a flawless
      A-pose worn by THE PLATE'S WOMAN, with the stand-in's glasses stuck on it. This is
      the tension the wave is about, arriving early and in a new place: it is not only
      style that a reference suppresses, it is the other reference.

    SO TWO REPAIRS ARE TRIED, and they attack opposite ends:
      ORDER SWAP - put her plate first and the pose plate second, and ask for the pose by
      description. If image1 really is the dominant slot, identity should now win.
      FACE RESTORE - keep the good fusion as a CANVAS in edit mode at partial denoise and
      repaint toward her face. Composition is what a canvas preserves, so the A-pose should
      survive the repair. Two denoise strengths, because this is the dial the whole repair
      turns on: too low and the wrong face stays, too high and the pose goes.
    """
    os.makedirs(os.path.join(WORK, "apose3"), exist_ok=True)
    paths, labels = [], []

    pose_words = ("She stands in the same A-pose as the person in image 2: both arms held "
                  "out and down and away from her sides at about forty-five degrees, "
                  "elbows straight, clear grey background visible between each arm and her "
                  "body, hands closed into loose fists, feet shoulder width apart.")

    # A. order swap - identity first, pose second
    for anchor, aid in (("standin_anchor_body.png", "body"),
                        ("standin_anchor_face.png", "face")):
        for s in (9301, 9302):
            tag = "S_%s_s%d" % (aid, s)
            prose = ("A full length photograph of the woman in image 1. %s She wears %s, "
                     "dark trousers and white canvas shoes. %s Completely flat even "
                     "shadowless lighting, a plain uniform mid grey background. Her face, "
                     "her round gold wire-frame glasses, her gold stud earrings and her "
                     "dark brown shoulder-length hair are exactly as in image 1."
                     % (pose_words, WEAR_A, APOSE_FRAME))
            print("  swap   %s" % tag, flush=True)
            p = ref2i(prose, APOSE2_NEG, s, APOSE_W, APOSE_H, tag, "apose3",
                      anchor, "standin_pose_plate_1.png")
            if p:
                paths.append(p)
                labels.append(tag + " (id first)")

    # B. face restore on the best round-two fusion, as a canvas
    src = os.path.join(WORK, "apose2", "F_fuse_p2_s9201.png")
    if os.path.exists(src):
        shutil.copy(src, os.path.join(COMFY_IN, "standin_fusion_canvas.png"))
        for dn in (0.40, 0.55, 0.70):
            tag = "E_restore_d%02d" % int(dn * 100)
            prose = ("Keep this photograph exactly as it is - the same A-pose with the "
                     "arms held out from the sides, the same full length framing, the same "
                     "flat lighting, the same plain grey background and the same clothes. "
                     "Change only her head: give her the face, the thin round gold "
                     "wire-frame glasses, the small mole on her cheek, the gold stud "
                     "earrings and the dark brown shoulder-length hair of the woman in "
                     "image 2.")
            print("  restore %s" % tag, flush=True)
            p = ref2i(prose, APOSE2_NEG, 9401, APOSE_W, APOSE_H, tag, "apose3",
                      "standin_fusion_canvas.png", "standin_anchor_face.png", denoise=dn)
            if p:
                paths.append(p)
                labels.append(tag + " (canvas)")
    else:
        print("  no round-two fusion at %s - run --stage apose2 first" % src)

    sheet(paths, labels, os.path.join(WORK, "apose3_sheet.jpg"), 4, 340, 604)
    print("\nA cell wins only if it takes ALL THREE: armpit gaps, shoes in frame, and a "
          "face that is hers. Two out of three is what round two already had.")


# ---------------------------------------------------------------- the winning recipe
#
# THE SCULPT-READY RECIPE, settled after three rounds. Every clause below is here because
# a version without it failed and was looked at:
#
#   image1 = her body anchor          identity lives in the FIRST reference slot
#   image2 = the photogrammetry plate the pose is a picture, not an adjective
#   "the same A-pose as image 2"      naming the other image is what transfers the pose
#   "...down to her white canvas shoes, near the bottom edge of the frame"
#                                     the shoes lever - the only thing that ever put feet
#                                     in the frame
#   APOSE2_NEG                        carries the arms-down and severed-body negations
#
# Round three ran this at two seeds against a face-restore alternative, and the head crops
# were compared against the anchor at magnification. Seed 9302 won on the marks: heaviest
# eyebrows, the cheek mole clearly present, both gold studs. The face-restore arm kept a
# trace of the scaffold woman in the eyebrows and was dropped.
IDEAL_PROSE_V2 = (
    "A full length photograph of the woman in image 1. She stands in the same A-pose as "
    "the person in image 2: both arms held out and down and away from her sides at about "
    "forty-five degrees, elbows straight, clear grey background visible between each arm "
    "and her body, hands closed into loose fists, feet shoulder width apart. She wears %s, "
    "dark trousers and white canvas shoes. %s Completely flat even shadowless lighting, a "
    "plain uniform mid grey background. Her face, her round gold wire-frame glasses, her "
    "gold stud earrings and her dark brown shoulder-length hair are exactly as in image 1."
    % (WEAR_A, APOSE_FRAME)
)
IDEAL_V2_SEED = 9302
# 1152x2048 already clears the 1536-long-edge intake rule. The larger size is rendered
# anyway and compared, because a mesher wants silhouette pixels and they are cheap here -
# but it is NOT assumed to be better: more pixels at a fixed step count is its own risk.
IDEAL_V2_SIZES = [(1152, 2048), (1408, 2496)]


def stage_final():
    """Render the settled recipe at both sizes so the size question is looked at too."""
    os.makedirs(os.path.join(WORK, "final"), exist_ok=True)
    paths, labels = [], []
    for w, h in IDEAL_V2_SIZES:
        tag = "IDEAL_%dx%d" % (w, h)
        print("  final %s" % tag, flush=True)
        p = ref2i(IDEAL_PROSE_V2, APOSE2_NEG, IDEAL_V2_SEED, w, h, tag, "final",
                  "standin_anchor_body.png", "standin_pose_plate_1.png")
        if p:
            paths.append(p)
            labels.append(tag)
    sheet(paths, labels, os.path.join(WORK, "final_sheet.jpg"), 2, 420, 744)


def stage_matte(src):
    os.makedirs(os.path.join(WORK, "ideal"), exist_ok=True)
    base = os.path.basename(src)
    shutil.copy(src, os.path.join(COMFY_IN, base))
    wf = load_wf("14_birefnet_matte.json")
    set_path(wf, "1.inputs.image", base)
    set_path(wf, "8.inputs.width", IDEAL_W)
    set_path(wf, "8.inputs.height", IDEAL_H)
    for n, pfx in (("10", "rgba"), ("11", "matte"), ("12", "proof")):
        set_path(wf, "%s.inputs.filename_prefix" % n, _prefix("ideal", "cut_" + pfx))
    _, outs = run(HOST, wf, quiet=True)
    got = []
    for o in outs:
        name = o.rsplit("/", 1)[-1]
        d = ensure_local(o, os.path.join(WORK, "ideal", name), required=False)
        if d:
            got.append(d)
            print("  %s" % d)
    return got


def stage_faces(boxes_json=None):
    """Crop the face out of every image with the hand-set boxes, and prove the crops."""
    boxes = json.load(open(boxes_json)) if boxes_json else FACE_BOXES
    fdir = os.path.join(WORK, "faces")
    shutil.rmtree(fdir, ignore_errors=True)
    os.makedirs(fdir)
    paths, labels = [], []
    for key, b in sorted(boxes.items()):
        src = os.path.join(WORK, b["src"])
        if not os.path.exists(src):
            print("  MISSING %s" % src)
            continue
        dst = os.path.join(fdir, key + ".png")
        r = sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vf",
               "crop=iw*%.4f:ih*%.4f:iw*%.4f:ih*%.4f,scale=448:448"
               % (b["w"], b["h"], b["x"], b["y"]), dst)
        if os.path.exists(dst):
            paths.append(dst)
            labels.append(key)
        else:
            print("  crop failed %s: %s" % (key, r.stderr[-160:]))
    sheet(paths, labels, os.path.join(WORK, "faces_sheet.jpg"), 6, 300, 300)
    print("\n%d crops. LOOK at faces_sheet.jpg before trusting any number that follows."
          % len(paths))


def stage_measure():
    """Embed every face crop and report WITHIN vs BETWEEN.

    Runs the embedding under the ComfyUI venv python, using ComfyUI's own
    comfy.clip_vision loader against the clip_vision weights already on the box. No
    download, no new package, and the same encoder ComfyUI itself would use.
    """
    script = os.path.join(WORK, "_embed.py")
    with open(script, "w") as f:
        f.write(EMBED_SRC)
    venv = os.path.expanduser("~/ComfyUI/venv/bin/python")
    env = dict(os.environ)
    # FREE THE SERVER FIRST, then measure on the GPU.
    #
    # Two CPU routes were tried and both failed, so neither is worth retrying:
    #   CUDA_VISIBLE_DEVICES=""  comfy.model_management calls torch.cuda.current_device()
    #                            at IMPORT time, so hiding the GPU stops the module loading
    #                            at all rather than making it fall back.
    #   sys.argv --cpu           does not reach comfy.cli_args from an embedded script; the
    #                            encoder still went to CUDA and still hit OOM.
    # What does work is asking the running server to drop its models: ComfyUI is resident
    # holding 27 of 32 GB, and a 142 MiB allocation for the vision tower could not be found
    # beside it. POST /free is non-destructive - the server reloads what it needs on the
    # next prompt - and it turns a hard OOM into a clean run.
    try:
        req = urllib.request.Request(
            "http://%s/free" % HOST,
            data=json.dumps({"unload_models": True, "free_memory": True}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=60).read()
        print("  asked ComfyUI to unload its models")
    except Exception as e:
        print("  /free failed (%s) - measuring anyway" % str(e)[:120])

    r = subprocess.run([venv, script, os.path.join(WORK, "faces")],
                       capture_output=True, text=True, env=env,
                       cwd=os.path.expanduser("~/ComfyUI"))
    print(r.stdout)
    if r.returncode:
        print(r.stderr[-2500:])


EMBED_SRC = r'''
import json, os, sys, torch
sys.path.insert(0, os.path.expanduser("~/ComfyUI"))
import comfy.clip_vision as cv
from PIL import Image
import numpy as np

FDIR = sys.argv[1]
MODELS = {
    "clipH": os.path.expanduser("~/ComfyUI/models/clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"),
    "dinov3": os.path.expanduser("~/ComfyUI/models/clip_vision/dino_v3_vit_h.safetensors"),
}
import comfy.clip_model
import comfy.model_management


def encode(m, img):
    """encode_image() cannot be used for DINOv3: it unconditionally does out[2].to(...)
    for image_embeds, and DINOv3 has no projection head, so out[2] is None and the call
    dies with "NoneType object has no attribute to". Calling the tower directly and
    falling back to the CLS TOKEN of the last hidden state gives a real DINOv3 embedding
    and leaves CLIP's behaviour byte-identical."""
    comfy.model_management.load_model_gpu(m.patcher)
    px = comfy.clip_model.clip_preprocess(img.to(m.load_device), size=m.image_size,
                                          mean=m.image_mean, std=m.image_std,
                                          crop=True).float()
    out = m.model(pixel_values=px, intermediate_output=-2)
    e = out[2] if out[2] is not None else out[0][:, 0]
    return e.detach().float().cpu()


names = sorted(n for n in os.listdir(FDIR) if n.endswith(".png"))
imgs = []
for n in names:
    a = np.array(Image.open(os.path.join(FDIR, n)).convert("RGB")).astype(np.float32) / 255.0
    imgs.append(torch.from_numpy(a)[None])
batch = torch.cat(imgs, 0)

def grp(n):
    return n.split("_")[0]


def report(mid, sim, names):
    idx = {n: i for i, n in enumerate(names)}
    anchor = idx.get("REF_anchor.png")
    sets = [n for n in names if n.startswith("SET_")]
    ctls = [n for n in names if n.startswith("CTL_")]
    sibs = [n for n in names if n.startswith("SIB_")]
    print("")
    print("=" * 66)
    print("%s   %d crops" % (mid, len(names)))
    print("=" * 66)

    def pairs(a, b, same=False):
        v = []
        for i, x in enumerate(a):
            for j, y in enumerate(b):
                if same and j <= i:
                    continue
                if x == y:
                    continue
                v.append(float(sim[idx[x]][idx[y]]))
        return v

    def line(lab, v):
        if not v:
            return
        v = sorted(v)
        n = len(v)
        print("  %-34s n=%-3d mean %.4f  min %.4f  max %.4f"
              % (lab, n, sum(v) / n, v[0], v[-1]))

    line("WITHIN set (set x set)", pairs(sets, sets, True))
    line("set x anchor", pairs(sets, ["REF_anchor.png"]))
    line("no-ref control x anchor", pairs(ctls, ["REF_anchor.png"]))
    line("no-ref control x set", pairs(ctls, sets))
    line("FLOOR siblings x anchor", pairs(sibs, ["REF_anchor.png"]))
    line("FLOOR siblings x set", pairs(sibs, sets))
    line("FLOOR siblings x siblings", pairs(sibs, sibs, True))
    if anchor is not None and "IDL_apose.png" in idx:
        print("  %-34s      %.4f" % ("sculpt-ready A-pose x anchor",
                                     sim[idx["IDL_apose.png"]][anchor]))
    hard = [n for n in sibs if "SIB6" in n]
    if hard and anchor is not None:
        print("  %-34s      %.4f  <- the near-miss stranger"
              % ("SIB6_hard x anchor", sim[idx[hard[0]]][anchor]))
    print("")
    print("  every image against the anchor, worst first:")
    rows = [(float(sim[idx[n]][anchor]), n) for n in names if n != "REF_anchor.png"]
    for v, n in sorted(rows):
        print("    %.4f  %s" % (v, n[:-4]))


out = {"files": names, "models": {}}
for mid, path in MODELS.items():
    try:
        m = cv.load(path)
        if m is None:
            print("%s: loader returned None" % mid); continue
        # no_grad AND detach: encode_image returns a tensor that still requires grad, and
        # .numpy() on it raises rather than silently doing the wrong thing.
        # Chunked, because the second encoder OOMed on a 28-image batch even with the
        # server unloaded - and a chunked encode is numerically identical.
        chunks = []
        with torch.no_grad():
            for k in range(0, batch.shape[0], 6):
                chunks.append(encode(m, batch[k:k + 6]))
        e = torch.cat(chunks, 0)
        e = e / e.norm(dim=-1, keepdim=True)
        sim = (e @ e.T).numpy()
        out["models"][mid] = sim.tolist()
        report(mid, sim, names)
    except Exception as ex:
        print("%s FAILED: %s" % (mid, str(ex)[:300]))
    finally:
        m = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
json.dump(out, open(os.path.join(FDIR, "..", "sim.json"), "w"))
print("\nwrote sim.json")
'''


# Which of the five marks each frame is EXPECTED to carry. A stress frame removes one on
# purpose, so scoring it out of five would count a success as a failure; the expected set
# is what makes "5 of 5" mean something.
MARKS = ["glasses", "cheek_mole", "hair", "earrings", "jacket"]
NOT_EXPECTED = {
    "14_no_glasses": ["glasses"],          # removed on purpose, held in her hand
    "15_hair_up": ["hair"],                # tied back on purpose
}
# The jacket is only in shot when she is wearing outfit A.
for _sid, _s, _wear, _w, _h, _p, _i in SHOTS:
    if _wear != WEAR_A:
        NOT_EXPECTED.setdefault(_sid, []).append("jacket")


def stage_publish():
    """Assemble the deliverable and write MANIFEST.json beside it."""
    for sub in ("set", "ideal", "reference", "floor", "control", "contact"):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)

    def cp(src, dst):
        s = os.path.join(WORK, src)
        if os.path.exists(s):
            shutil.copy(s, os.path.join(OUT, dst))
            return True
        print("  missing %s" % src)
        return False

    shots = []
    for sid, seed, wear, w, h, prose, intent in SHOTS:
        ok = cp("set/%s.png" % sid, "set/%s.png" % sid)
        shots.append({
            "id": sid, "file": "set/%s.png" % sid, "present": ok,
            "intent": intent, "wear": wear, "seed": seed, "size": [w, h],
            "reference_pair": (["anchor_body", "pose_plate"] if sid in FULL_FIGURE
                               else ["anchor_face", "anchor_body"]),
            "marks_expected": [m for m in MARKS if m not in NOT_EXPECTED.get(sid, [])],
            "prose": prose,
        })
    cp("final/IDEAL_1152x2048.png", "ideal/IDEAL_apose_1152x2048.png")
    cp("final/IDEAL_1408x2496.png", "ideal/IDEAL_apose_1408x2496_alt.png")
    for n in os.listdir(os.path.join(WORK, "ideal")) if os.path.isdir(
            os.path.join(WORK, "ideal")) else []:
        if n.startswith("cut_"):
            cp("ideal/%s" % n, "ideal/%s" % n)
    cp("anchor/anchor_face.png", "reference/anchor_face.png")
    cp("anchor/anchor_body.png", "reference/anchor_body.png")
    cp("apose2/P1_plate_s9101.png", "reference/pose_plate.png")
    for s, _, _ in SIBLINGS:
        cp("siblings/%s.png" % s, "floor/%s.png" % s)
    for c in CONTROL_IDS:
        cp("control/%s.png" % c, "control/noref_%s.png" % c)
    for sh_ in ("casting_sheet.jpg", "siblings_sheet.jpg", "anchor_sheet.jpg",
                "set_sheet.jpg", "control_sheet.jpg", "apose_sheet.jpg",
                "apose2_sheet.jpg", "apose3_sheet.jpg", "final_sheet.jpg",
                "faces_sheet.jpg"):
        cp(sh_, "contact/%s" % sh_)

    man = {
        "subject": "STANDIN-A",
        "synthetic": True,
        "provenance": ("Every image generated on this box from the prose in "
                       "studio/_tools/standin_person.py. No photograph of any real person "
                       "was used, fetched or referenced, and no celebrity or public-figure "
                       "token appears in any prompt."),
        "engine": "Qwen-Image 2512 (t2i) and Qwen-Image-Edit 2511 (reference), 4-step "
                  "Lightning, cfg 1.0, style LoRA off",
        "marks": MARKS,
        "face_prose": FACE,
        "wear": {"A": WEAR_A, "B": WEAR_B, "C": WEAR_C},
        "shots": shots,
        "ideal": {
            "file": "ideal/IDEAL_apose_1152x2048.png",
            "recipe": "image1=anchor_body, image2=pose_plate, seed %d" % IDEAL_V2_SEED,
            "meets": ["A-pose with background between each arm and the torso",
                      "hands closed into fists", "flat shadowless light",
                      "plain uniform grey background", "whole figure with margin",
                      "long edge 2048, clears the 1536 rule"],
        },
        "consistency": {
            "method": "CLIP-ViT-H and DINOv3 cosine over 28 hand-boxed face crops, with a "
                      "purpose-built between-person floor (6 siblings).",
            "verdict": "THE EMBEDDING METRIC FAILED ITS OWN CONTROL AND IS NOT REPORTED AS "
                       "EVIDENCE. SIB6 - a different woman wearing the same glasses, hair, "
                       "skin tone and jacket - scored 0.865 on CLIP-ViT-H (above 8 of the "
                       "16 genuine frames) and 0.967 on DINOv3, the highest score in the "
                       "whole matrix. Both encoders rank a stranger above the real thing, "
                       "so they are measuring photographic similarity, not identity. The "
                       "consistency claim rests on the MARKS instead, which are countable.",
            "floor_beats_signal": True,
        },
    }
    with open(os.path.join(OUT, "MANIFEST.json"), "w") as f:
        json.dump(man, f, indent=2)
    print("  wrote %s" % os.path.join(OUT, "MANIFEST.json"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["casting", "siblings", "anchor", "set", "control", "ideal",
                             "apose", "apose2", "apose3", "final", "matte", "publish", "faces", "measure"])
    ap.add_argument("--pick", type=int, default=1, help="casting candidate 1-6")
    ap.add_argument("--only", help="comma-separated shot ids for --stage set")
    ap.add_argument("--src", help="source image for --stage matte")
    ap.add_argument("--boxes", help="face box json for --stage faces")
    ap.add_argument("--no-ref2", action="store_true")
    a = ap.parse_args()
    os.makedirs(WORK, exist_ok=True)

    if a.stage == "casting":
        stage_casting()
    elif a.stage == "siblings":
        stage_siblings()
    elif a.stage == "anchor":
        stage_anchor(a.pick)
    elif a.stage == "set":
        stage_set(set(a.only.split(",")) if a.only else None, not a.no_ref2)
    elif a.stage == "control":
        stage_control()
    elif a.stage == "ideal":
        stage_ideal()
    elif a.stage == "apose":
        stage_apose()
    elif a.stage == "apose2":
        stage_apose2()
    elif a.stage == "apose3":
        stage_apose3()
    elif a.stage == "final":
        stage_final()
    elif a.stage == "publish":
        stage_publish()
    elif a.stage == "matte":
        stage_matte(a.src)
    elif a.stage == "faces":
        stage_faces(a.boxes)
    elif a.stage == "measure":
        stage_measure()


if __name__ == "__main__":
    main()
