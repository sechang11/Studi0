#!/usr/bin/env python3
"""FLUX.2 gallery - a body of work that shows what this engine does that nothing else here can.

WHAT THIS IS FOR. FLUX.2 was wired up this week. The checkpoint card measured it against
Qwen-Image on seven prompts and routed it to "shot description is the work" - camera angle,
layout, count, hex colour, readable type. This tool goes after the lane that A/B got WRONG,
and a second lane it got right.

  PHYSICAL MEDIA. The card says, from one rendered pair: "Watercolour is Qwen's, and not
  close ... Anything hand-media stays off FLUX.2." That test was run through the TURBO
  distill LoRA, and the same card says two paragraphs earlier that Turbo degrades "fine
  repeating structure" specifically. Paper tooth IS fine repeating structure. So is a
  halftone rosette, a gouge mark, a knitted stitch, a lead came and a woven weft. This
  tool re-runs that question with the Turbo LoRA OFF - see --mode calibrate, which renders
  the same medium at the same seed both ways so the decision is made from pixels.

  TYPOGRAPHY. Quoted strings land letter-perfect and hex codes land within a few percent
  per channel. Every entry in the typo lane carries the exact strings it asked for and
  every entry in the hex lane carries the code it asked for AND the code sampled back off
  the PNG. That is the difference between a gallery that decorates and one that teaches.

THE ONE CRAFT RULE. This box learned it the expensive way on comfy-studio and it is the
whole reason the physical-media lane works: THE MODEL RENDERS NOUNS, NOT ADJECTIVES.
"in a plasticine style" is an adjective and produces a clean digital picture that is
slightly waxy. What produces plasticine is naming what a lump of plasticine HAS -
thumbprints, the seam where two colours were pressed together, dust and one hair stuck to
the surface, armature wire at the ankle. Every medium below is authored as
lead + tell + finish, where `tell` is a list of the substrate's own physical defects.

FLUX.2 HAS NO NEGATIVE PROMPT AND NONE CAN BE ADDED. BasicGuider takes one conditioning.
Every suppression in this corpus is written as a positive fact.

    python3 studio/_tools/flux2_gallery.py --mode calibrate      # turbo vs no-turbo, 8 media
    python3 studio/_tools/flux2_gallery.py --mode media --wave 1 # the physical-media lane
    python3 studio/_tools/flux2_gallery.py --mode typo
    python3 studio/_tools/flux2_gallery.py --mode hex            # renders AND samples back
    python3 studio/_tools/flux2_gallery.py --mode ab             # flux2 vs qwen vs animagine
    python3 studio/_tools/flux2_gallery.py --mode sheets         # contact sheets, per medium
    python3 studio/_tools/flux2_gallery.py --mode drop --slugs a,b,c   # record a rejection
    python3 studio/_tools/flux2_gallery.py --mode index          # the browsable gallery

EVERY IMAGE CARRIES ITS FULL RECIPE. Each PNG gets a sidecar <slug>.json next to it with
engine, checkpoint file, full prompt text, seed, steps, guidance, size, sampler, scheduler
and LoRA. Every render also appends a row to _ledger.json. Nothing in this gallery is
claimed that is not written next to the pixels.

IT YIELDS. This box is shared and there is a film rendering on it. Work is submitted in
small chunks; between chunks the tool looks at the ComfyUI queue for prompt ids it did not
submit, and if it finds any it stops submitting and waits. Worst case another agent waits
one chunk. --chunk sets the size.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.expanduser("~/shared/comfy-studio")
COMFY_OUT = os.path.expanduser("~/ComfyUI/output")
GAL = os.path.join(ROOT, "studio", "samples", "flux2_gallery")
LEDGER = os.path.join(GAL, "_ledger.json")
DROPPED = os.path.join(GAL, "_dropped.json")
HOST = os.environ.get("COMFY_HOST", "127.0.0.1:8188")

WF_FLUX = os.path.join(ROOT, "workflows", "40_flux2_t2i.json")
WF_QWEN = os.path.join(ROOT, "workflows", "02_qwen_t2i_quality.json")

# The gallery's shipping settings, and why.
#   steps 20 / turbo off - the Turbo distill is a speed path that eats fine repeating
#     structure, which is exactly what every medium in this corpus is made of. Settled by
#     --mode calibrate, not assumed.
#   guidance 4.0 - the template value. 2.5 goes soft and loses small prompt detail; 6.0
#     starts to plasticise. Swept on this box already, in studio/samples/flux2/settings.
#   euler / flux2 scheduler - the only sampler wired into 40_flux2_t2i.json.
STEPS = 20
GUIDANCE = 4.0
TURBO = False
SEED = 20250805
QWEN_NEG = "blurry, low quality, watermark, deformed text, misspelled, jpeg artifacts"


# -*- coding: utf-8 -*-
"""Corpus part A: the physical-media vocabulary.

ONE CRAFT RULE BUILT INTO EVERY ENTRY HERE, and it is this box's own rule, learned the
expensive way on comfy-studio: THE MODEL RENDERS NOUNS, NOT ADJECTIVES. "in a plasticine
style" is an adjective and it produces a clean digital picture that is slightly waxy.
What produces plasticine is naming the things a lump of plasticine actually HAS -
thumbprints, the seam where two colours were pressed together, dust and cat hair stuck to
the surface, armature wire showing at the ankle.

So each medium is authored as three parts:
  lead   - what the artefact PHYSICALLY IS. Usually "a photograph of <object>", because the
           strongest way to get a medium is to make the picture a photograph of a thing
           that is made of it, rather than a picture rendered in it.
  tell   - the substrate's own defects. This is the load-bearing clause. It is written as
           a list of concrete nouns, never as a quality word.
  finish - light, camera and film, so the photograph is a photograph.

FLUX.2 has NO NEGATIVE PROMPT, so every suppression is written as a positive fact.
"""

MEDIA = {
 # ------------------------------------------------------------------ modelling / objects
 "plasticine": dict(
  name="Plasticine",
  blurb="Oil-based modelling clay, photographed as a physical model on a tabletop set.",
  lead="A macro photograph of a handmade plasticine model standing on a tabletop set, "
       "photographed as a real object.",
  tell="The clay carries thumbprints and fingernail scrapes across every surface, a visible "
       "seam where two colours of clay were pressed together, small crumbs of clay on the "
       "table, and specks of dust and one short hair stuck to the sticky surface. The "
       "colours are the flat chalky colours of a clay block. Edges are slightly slumped "
       "under their own weight.",
  finish="Macro lens at f8, soft diffused tent lighting from above with one warmer lamp from "
         "the left, shallow depth of field falling off behind the model, natural colour.",
  size="1536x1152"),

 "stopmotion": dict(
  name="Stop-motion puppet",
  blurb="Silicone and fabric armature puppet on a built miniature set.",
  lead="A photograph of a stop-motion animation puppet standing on a built miniature set, "
       "photographed on the animation stage between frames.",
  tell="The puppet has a silicone skin with a faint mould seam down one side of the face, "
       "real woven fabric clothing whose weave is far too coarse for the scale, hand-painted "
       "eyes with a wet gloss varnish, and a brass tie-down bolt visible where one foot "
       "meets the drilled set floor. Fine dust sits in the folds. The miniature set is built "
       "from painted card and real moss.",
  finish="Shot on a long lens at f11 with deep focus, hard key light from a small fresnel "
         "camera-left and a cold fill from the right, black stage darkness beyond the set.",
  size="1536x1152"),

 "needlefelt": dict(
  name="Needle-felted wool",
  blurb="Barbed-needle sculpted wool roving.",
  lead="A photograph of a needle-felted wool sculpture sitting on a pale linen cloth, "
       "photographed as a real handmade object.",
  tell="The surface is matted wool fibre with a soft halo of loose fibres catching the light "
       "at every silhouette edge, thousands of tiny needle punctures dimpling the wool, "
       "colours blended by carding so the joins are gradual and fuzzy, and two black glass "
       "bead eyes with a hard specular highlight that the wool does not have.",
  finish="Macro lens at f5.6, large soft window light from the left, warm shadow under the "
         "object, natural colour, fine grain.",
  size="1536x1152"),

 "brick": dict(
  name="Interlocking plastic bricks",
  blurb="A built model in moulded ABS bricks, everything stepped to the grid.",
  lead="A photograph of a model built entirely from small interlocking plastic bricks, "
       "photographed as a real built object on a white table.",
  tell="Every form is stepped to the brick grid with no curve smaller than one brick, the "
       "studs on the top surfaces cast their own small shadows, each brick has a glossy "
       "injection-moulded finish with a faint mould seam and a sprue mark, a few bricks are "
       "scuffed and one is a slightly different shade of the same colour, and the joints "
       "between bricks are visible as thin dark lines.",
  finish="Shot on a 100mm macro at f11, bright even studio light from a large softbox above, "
         "a soft shadow on the white table, natural colour.",
  size="1536x1152"),

 "origami": dict(
  name="Folded paper",
  blurb="Single-sheet origami, every plane a fold.",
  lead="A photograph of an origami figure folded from a single square of paper, standing on "
       "a dark grey table.",
  tell="Every surface is a flat plane meeting another at a crisp fold line, the paper carries "
       "visible fibre grain and one different colour on its reverse side that shows in the "
       "reversed folds, there are faint ghost creases from folds that were made and undone, "
       "and one corner has softened from handling.",
  finish="Shot on an 85mm at f8, a single hard light from high camera-right throwing a long "
         "sharp shadow across the table, natural colour.",
  size="1536x1152"),

 "ceramic": dict(
  name="Glazed ceramic",
  blurb="Kiln-fired earthenware under a running glaze.",
  lead="A photograph of a glazed ceramic piece on a wooden shelf, photographed as a real "
       "fired object.",
  tell="The glaze has run and pooled thick and dark in every recess and pulled thin and pale "
       "over every raised edge, a fine web of crazing runs through the glaze surface, the "
       "unglazed foot ring shows raw grogged clay, there is one kiln kiss where the piece "
       "touched a shelf, and three small pinholes where the glaze bubbled.",
  finish="Shot on a 100mm macro at f8, soft light from a north window camera-left, the wet "
         "specular sheen of the glaze reading against the matte raw clay, natural colour.",
  size="1536x1152"),

 "sand": dict(
  name="Carved sand",
  blurb="Compacted damp sand, carved and crumbling.",
  lead="A photograph of a sculpture carved from compacted damp sand on a beach, photographed "
       "as a real object.",
  tell="The whole form is one colour of wet sand, tool marks from a flat trowel run across "
       "the broad planes, fine dry sand has crumbled away from the undercuts and lies in "
       "little cones at the base, individual grains catch the light along every edge, and "
       "one thin detail has already collapsed.",
  finish="Shot on a 50mm at f8 in low raking evening sunlight from the left that makes the "
         "grain texture read across the whole surface, wet sand and sky behind, natural colour.",
  size="1536x1024"),

 "wax": dict(
  name="Sculpted wax",
  blurb="Modelling wax, translucent at the thin edges.",
  lead="A photograph of a figure modelled in dark red sculpting wax on a turntable in a "
       "workshop, photographed as a real object.",
  tell="The wax carries the marks of a heated loop tool in long scraped ribbons, thin edges "
       "glow translucent orange where light passes through them while the thick masses stay "
       "opaque, fingerprints are pressed into the softer areas, and shavings of wax lie on "
       "the turntable.",
  finish="Shot on an 85mm at f4, one bare warm bulb behind and to the right so the "
         "translucency reads, a dim workshop behind, natural colour, fine grain.",
  size="1152x1536"),

 # ------------------------------------------------------------------ print / ink
 "benday": dict(
  name="Ben-Day dots",
  blurb="Four-colour comic printing on newsprint, off-register.",
  lead="A photograph of a page from a cheap 1960s comic book lying flat, shot straight down "
       "from above so the page fills the frame.",
  tell="The colour is made entirely of coarse halftone dots in cyan, magenta and yellow, each "
       "dot individually visible and large enough to count, arranged in screens at different "
       "angles so a rosette pattern appears in the overlaps. The black key line is printed "
       "slightly out of register so a thin fringe of magenta shows along one side of every "
       "outline. The dots have gained and bled into the absorbent newsprint. The paper has "
       "yellowed to a tan and the print from the reverse side shows faintly through it. There "
       "is a crease across one corner.",
  finish="Shot straight down on a 60mm macro at f8 under flat even light, the paper fibre and "
         "the dot structure both resolved, natural colour.",
  size="1536x1536"),

 "risograph": dict(
  name="Risograph",
  blurb="Two soy-ink spot colours, misregistered, on rough stock.",
  lead="A photograph of a risograph-printed poster taped to a wall, shot square on so the "
       "sheet fills the frame.",
  tell="The image is built from exactly two spot inks laid one over the other, a fluorescent "
       "pink and a deep blue, with a third colour existing only where the two overlap. The "
       "two passes are misregistered by two or three millimetres so a white gap opens along "
       "one side of every shape and the inks double along the other. Both inks are laid as "
       "coarse open dither dots. Roller streaks run down the sheet, one thumbprint of pink "
       "ink sits in the margin, and the paper is a rough flecked oatmeal stock.",
  finish="Shot square on with a 50mm at f5.6 under flat soft daylight, the paper texture "
         "resolved, natural colour.",
  size="1152x1536"),

 "woodcut": dict(
  name="Woodcut",
  blurb="Relief block cut with gouges, hand-burnished.",
  lead="A photograph of a woodcut print on damp handmade paper, shot flat from directly above.",
  tell="Every tone is made of carved lines and nothing else - parallel gouge cuts for the "
       "mid-tones, cross-hatching where it goes darker, and bare white paper where the block "
       "was cut away entirely. The gouge marks have the chatter and the widening taper of a "
       "hand-pushed V-tool, and the wood grain of the block itself has printed as a faint "
       "striping through the solid black areas. The ink is thick and slightly uneven with a "
       "few pale flecks where it did not take. The paper has a deckle edge and visible fibres.",
  finish="Shot straight down on a 60mm macro at f8, soft raking light so the paper texture and "
         "the ink relief both read, black ink on cream paper.",
  size="1152x1536"),

 "linocut": dict(
  name="Linocut, two blocks",
  blurb="Bold reduction lino, black key over one flat colour.",
  lead="A photograph of a two-colour linocut print pinned to a studio wall, shot square on.",
  tell="One flat block of solid colour is printed first and a black key block over it, with "
       "the black slightly off register so the colour shows as a bright sliver along one edge "
       "of every shape. The cuts are broad and blunt with the rounded ends of a U-gouge and "
       "small slips where the tool skidded. The black is a heavy opaque slab with pinholes "
       "where the ink was thin. Areas of the lino that were meant to be cleared still hold a "
       "faint grey scumble of ink. Heavy cotton rag paper with a plate impression.",
  finish="Shot square on with an 85mm at f5.6 under soft even light, natural colour.",
  size="1152x1536"),

 "letterpress": dict(
  name="Letterpress",
  blurb="Metal type and cuts bitten into damp cotton rag.",
  lead="A photograph of a letterpress-printed sheet lying on a compositor's stone, shot at a "
       "slight angle so the surface relief catches the light.",
  tell="Every printed mark is physically pressed down into the thick soft cotton paper so it "
       "sits in a shallow debossed valley you can see the shadow of, with a faint halo of ink "
       "squeezed out around the edge of each stroke. The ink is uneven across large solids, "
       "showing the texture of the paper through it. One letter has printed lighter than its "
       "neighbours. The paper is thick, soft, cream, with a deckle on one edge.",
  finish="Shot at fifteen degrees off square on a 100mm macro at f8 with hard raking light "
         "from the left so every deboss throws a shadow, natural colour.",
  size="1536x1152"),

 "etching": dict(
  name="Drypoint etching",
  blurb="Intaglio, burr and plate tone on damp paper.",
  lead="A photograph of a drypoint etching on damp handmade paper, shot flat from above.",
  tell="The lines are velvety and soft-edged where the burr thrown up by the needle has held "
       "extra ink, and thin and scratchy where it has not. A film of grey plate tone lies "
       "across the whole image from ink that was not fully wiped, heavier at the edges. The "
       "steel plate has left a hard embossed plate mark rectangle pressed into the paper with "
       "clean white margins beyond it. There are a few stray scratches and one thumbprint in "
       "the margin.",
  finish="Shot straight down on a 60mm macro at f8 in soft raking light so the plate mark "
         "emboss reads, warm black ink on cream paper.",
  size="1152x1536"),

 "cyanotype": dict(
  name="Cyanotype",
  blurb="Iron-salt contact print, Prussian blue on brushed paper.",
  lead="A photograph of a cyanotype print lying on a wooden table, shot from directly above.",
  tell="The whole image is a single Prussian blue, from a deep saturated blue in the shadows "
       "to bare white paper in the highlights, with no other colour anywhere. The "
       "light-sensitive solution was brushed on by hand, so the blue stops at a ragged brush "
       "edge with visible bristle streaks and the paper outside it is untouched white. The "
       "image is soft and slightly low in contrast. The paper is heavy watercolour stock with "
       "visible fibre and it has cockled where it dried.",
  finish="Shot straight down on a 50mm at f8 in flat soft daylight, the paper cockle throwing "
         "faint shadows, natural colour.",
  size="1536x1152"),

 "blueprint": dict(
  name="Blueprint",
  blurb="White line on Prussian blue, folded and stained.",
  lead="A photograph of an old blueprint drawing unrolled and weighted flat on a drawing "
       "board, shot from above.",
  tell="The whole sheet is a deep Prussian blue and every line, dimension and letter on it is "
       "bare white, the reverse of ink on paper. The drawing is orthographic - a plan and two "
       "elevations laid out on the sheet with dimension lines, arrowheads, hatched section "
       "cuts and a ruled title block in the bottom right corner. Hard fold creases cross the "
       "sheet in a grid and the blue has worn to white along them. There is a brown coffee "
       "ring near one edge and a torn corner.",
  finish="Shot straight down on a 35mm at f8 under flat even light, the paper curl casting "
         "soft shadows, natural colour.",
  size="1536x1024"),

 "chalkboard": dict(
  name="Chalk on slate",
  blurb="Soft chalk on a wiped blackboard.",
  lead="A photograph of a drawing made in chalk on a large slate blackboard, shot square on.",
  tell="Every mark is soft powdery chalk sitting on top of the board rather than in it, "
       "breaking up over the board texture so the black shows through the strokes. Broad "
       "areas were laid with the side of the stick and blended with a fingertip, leaving "
       "smears. Ghosts of earlier drawings remain where the board was wiped with a dry cloth "
       "in wide arcs. Chalk dust has collected in the wooden tray at the bottom edge and a "
       "worn stub of white chalk lies in it.",
  finish="Shot square on with a 50mm at f5.6 in soft raking light from the left so the chalk "
         "dust and the wipe smears both read, near-monochrome with one colour of chalk.",
  size="1536x1024"),

 "scratchboard": dict(
  name="Scratchboard",
  blurb="White lines scratched out of a black clay-coated board.",
  lead="A photograph of a scratchboard engraving, shot flat from above.",
  tell="The board is solid matte black and every light in the image has been scratched out of "
       "it with a knife point, so all the tone is white lines on black and there is no grey "
       "except where the lines get closer together. The scratches have the slight wobble and "
       "the tapering ends of a hand-held blade, they burr up a tiny ridge of white clay at "
       "their edges, and a fine dust of scraped clay lies in the deeper cuts. One slip of the "
       "blade runs off across the background.",
  finish="Shot straight down on a 100mm macro at f8 in hard raking light from the right so "
         "the scratched relief reads, black and white only.",
  size="1152x1536"),

 "screenprint": dict(
  name="Screenprint",
  blurb="Flat opaque spot inks, four pulls, hand-registered.",
  lead="A photograph of a screenprinted poster pinned flat to a wall, shot square on.",
  tell="The image is built from four flat opaque spot colours pulled one at a time, each one a "
       "solid area of ink with no gradient inside it and a slightly ragged edge where the "
       "emulsion stencil was. The ink sits on top of the paper with a physical thickness you "
       "can see at the edges. Two of the colours are misregistered by a millimetre. There is "
       "one pinhole of colour in a solid area where the screen had a gap, and a faint mesh "
       "texture inside the largest solid. The paper is heavy uncoated stock.",
  finish="Shot square on with an 85mm at f5.6 under soft even light, raking slightly so the "
         "ink thickness catches, natural colour.",
  size="1152x1536"),

 # ------------------------------------------------------------------ paint
 "watercolour": dict(
  name="Watercolour",
  blurb="Pigment in water on cold-press rag - the one FLUX.2 was said to lose.",
  lead="A photograph of a watercolour painting on cold-pressed rag paper, shot flat from "
       "above so the paper fills the frame.",
  tell="The pigment has settled into the pits of the rough paper tooth and skipped the peaks, "
       "so every wash is granular rather than even. Where a wash dried undisturbed it has "
       "left a hard dark line at its own edge. Where clean water hit damp paint a pale "
       "cauliflower bloom has pushed the pigment outward in a ragged ring. Two colours have "
       "run into each other while wet and bled a soft fringe. The white of the paper is left "
       "bare for every highlight and there is no white paint anywhere. A few pencil "
       "underdrawing lines still show. The paper has cockled into low ridges where it dried.",
  finish="Shot straight down on a 60mm macro at f8 in soft raking daylight so the paper tooth "
         "and the cockle both read, natural colour.",
  size="1536x1152"),

 "impasto": dict(
  name="Oil impasto",
  blurb="Palette-knife oil, standing in ridges off the canvas.",
  lead="A photograph of an oil painting on stretched linen, shot at a slight angle so the "
       "paint relief catches the light.",
  tell="The paint stands up off the canvas in thick ridges laid with a palette knife, each "
       "stroke holding the sharp edge and the trailing tail the blade left, and the ridges "
       "cast real shadows across the surface. Colours are dragged wet into wet so they streak "
       "into each other without mixing. The weave of the linen shows through in the thin "
       "passages at the edges. A single bristle is stuck in the paint. The varnish is uneven "
       "so parts of the surface are glossy and parts are matte.",
  finish="Shot twenty degrees off square on an 85mm at f5.6 with hard light from the left so "
         "every ridge throws a shadow, natural colour.",
  size="1536x1152"),

 "gouache": dict(
  name="Gouache",
  blurb="Opaque matte body colour, flat and chalky.",
  lead="A photograph of a gouache painting on grey-toned board, shot flat from above.",
  tell="Every colour is completely opaque and completely matte with no shine anywhere, laid in "
       "flat shapes with visible brush chatter at the edges where the loaded brush ran dry. "
       "Light colours are painted straight over dark ones and sit on top of them. The paint "
       "has dried a shade paler than it went on and has a chalky bloom. Two areas were "
       "overworked so the layer beneath has lifted and streaked. The grey board shows in a "
       "few unpainted gaps.",
  finish="Shot straight down on a 60mm at f8 in flat soft light with no specular highlight "
         "anywhere on the surface, natural colour.",
  size="1536x1152"),

 "fresco": dict(
  name="Buon fresco",
  blurb="Pigment into wet lime plaster, cracked and lost.",
  lead="A photograph of a section of a wall painting in lime plaster, shot square on to the "
       "wall.",
  tell="The colour is soaked into the plaster rather than sitting on it, in a limited earth "
       "palette of ochre, red iron oxide, black and lime white. The plaster is divided into "
       "day sections whose joins run as faint seams across the picture. A network of fine "
       "cracks runs through the whole surface and in three places the plaster has fallen away "
       "entirely to bare rough render beneath. Salt bloom has whitened one lower corner. The "
       "surface is chalky and completely matte.",
  finish="Shot square on with a 50mm at f8 in soft raking daylight so the losses and the "
         "plaster relief read, natural colour.",
  size="1536x1024"),

 # ------------------------------------------------------------------ thread / glass / stone
 "embroidery": dict(
  name="Hand embroidery",
  blurb="Cotton floss on linen, still in the hoop.",
  lead="A photograph of a piece of hand embroidery still stretched in its wooden hoop, shot "
       "from directly above.",
  tell="Every filled shape is made of parallel satin stitches whose direction changes shape to "
       "shape and which catch the light differently depending on which way they run. The "
       "outlines are stem stitch, a rope of small overlapping stitches. The floss has a soft "
       "sheen the linen does not. Individual threads are visible and one has frayed. The "
       "linen weave is open enough to count and it has puckered slightly under the densest "
       "stitching. A threaded needle is parked at the edge and the hoop screw is at the top.",
  finish="Shot straight down on a 100mm macro at f8 in soft directional light from the left "
         "so the stitch direction reads, natural colour.",
  size="1536x1536"),

 "tapestry": dict(
  name="Woven tapestry",
  blurb="Wool weft on linen warp, everything stepped to the weave.",
  lead="A photograph of a woven wool tapestry hanging on a stone wall, shot square on.",
  tell="The whole image is built from horizontal rows of wool weft packed down over a vertical "
       "linen warp, so every diagonal edge is stepped into small rectangles and no line is "
       "truly smooth. Colour changes leave visible slits where two wefts turn back on "
       "themselves. The wool is slightly hairy and the dyes are uneven from batch to batch so "
       "large areas band subtly. The bottom edge is a fringe of cut warp threads and the "
       "whole thing hangs with a slight sag.",
  finish="Shot square on with an 85mm at f8 in soft light from the left, the weave resolved "
         "across the whole frame, natural colour.",
  size="1536x1152"),

 "stainedglass": dict(
  name="Stained glass",
  blurb="Coloured glass in lead came, lit from behind.",
  lead="A photograph of a stained glass window photographed from inside a dark building with "
       "daylight coming through it.",
  tell="Every colour is a separate piece of coloured glass held in a dark lead came whose "
       "H-section throws a thick black line around every single shape, and there are no "
       "gradients within a piece except the streaks and bubbles frozen in the glass itself. "
       "Faces, folds and shading are painted onto the glass in brown-black vitreous enamel and "
       "fired, applied as fine hatched lines and stippled shadow. Horizontal iron saddle bars "
       "cross the window in front of the glass. Some panes are cracked and mended with a lead "
       "strip. The stonework around it is in darkness.",
  finish="Shot from a dark interior on a 50mm at f5.6 exposed for the glass so the surrounding "
         "stone goes almost black, saturated transmitted colour.",
  size="1152x1536"),

 "mosaic": dict(
  name="Mosaic",
  blurb="Cut stone and smalti tesserae in uneven grout.",
  lead="A photograph of a floor mosaic, shot from above at a slight angle.",
  tell="The whole image is made of small cut squares of stone and glass, each one individually "
       "visible with chipped edges and its own slightly different shade, set at slightly "
       "different angles so they catch the light unevenly. The rows of tesserae follow the "
       "contours of the forms they describe and fan out into straight courses in the "
       "background. Grey grout fills the uneven gaps between them. Several tesserae are "
       "missing and show bare mortar beneath, and a crack runs across one corner.",
  finish="Shot from above on a 35mm at f8 in raking sunlight so the uneven tessera surfaces "
         "sparkle, natural colour.",
  size="1536x1024"),

 "marquetry": dict(
  name="Marquetry",
  blurb="Inlaid wood veneer, grain doing the shading.",
  lead="A photograph of a marquetry panel in inlaid wood veneers, shot flat from above.",
  tell="Every shape in the picture is a separate piece of wood veneer chosen for its own grain "
       "and colour, cut to fit and butted against its neighbours along a fine dark glue line. "
       "The shading is done entirely by the direction and figure of the grain and by scorching "
       "the edges of pieces in hot sand, which leaves a brown gradient at their borders. There "
       "is walnut, pale sycamore, and one piece of burr. The whole panel is under a shellac "
       "polish with a few fine scratches in it and one small lifted corner.",
  finish="Shot straight down on a 60mm macro at f8 in soft light angled to bring out the grain "
         "and the polish sheen, natural colour.",
  size="1536x1152"),

 "enamel": dict(
  name="Cloisonné enamel",
  blurb="Glass enamel pooled inside soldered wire cells.",
  lead="A macro photograph of a cloisonné enamel pin lying on black velvet, photographed as a "
       "real metal object.",
  tell="Every colour is a pool of glossy glass enamel held inside a cell walled by a thin "
       "polished gold wire, and every wire reads as a bright metal line around every shape. "
       "The enamel surfaces are slightly concave where they sank in the kiln and hold a wet "
       "reflection of the light. There are two tiny bubble pits in one colour. The metal has "
       "fine polishing swirls in it. The design is simplified into flat colour areas because "
       "no shape can exist without a wire around it.",
  finish="Macro lens at f11 focus-stacked, one large soft light above and a bright reflector "
         "below so the gold wires catch, black velvet background, natural colour.",
  size="1536x1152"),

 # ------------------------------------------------------------------ screens / light
 "ps1": dict(
  name="PlayStation 1 real-time",
  blurb="Flat-shaded low-poly triangles, affine texture swim, 320x240, no filtering.",
  lead="A frame captured directly out of the framebuffer of a 1997 PlayStation 1 game "
       "running on original hardware, 320 by 240 pixels, scaled up so that every single "
       "pixel is a visible hard-edged square block.",
  tell="Everything in the frame is built from a few hundred large flat-shaded triangles with "
       "hard visible edges and no smoothing at all, so every curve is a chain of straight "
       "facets and every silhouette is a polygon outline you can trace. The textures are 64 "
       "by 64 bitmaps stretched across those triangles with affine mapping, so they visibly "
       "warp and slide across the polygon seams and the perspective inside each triangle is "
       "wrong. There is no texture filtering anywhere, so every texel is a hard square block "
       "of flat colour with no blending into its neighbour. The polygon vertices snap to "
       "whole pixels so the edges wobble and crawl. Every gradient is replaced by a coarse "
       "checkerboard dither of two colours. Distant geometry is cut off abruptly into a wall "
       "of one flat fog colour. The characters have mitten hands with no separate fingers "
       "and their faces are a texture painted flat onto the front of the head.",
  finish="No anti-aliasing anywhere: every polygon edge is a hard aliased staircase. Flat "
         "per-vertex lighting, no shadows, no reflections, no specular highlights.",
  size="1536x1152"),

 "crtpixel": dict(
  name="Pixel art on a CRT",
  blurb="Hand-placed pixels, sixteen colours, dithered gradients. Photographed off the glass "
        "- but see the note: naming the phosphor structure gets the phosphor structure DRAWN.",
  lead="A close photograph of a 1992 pixel-art game frame displayed on a Trinitron CRT "
       "monitor, filling the frame.",
  # THE CLAUSE THAT WAS HERE IS GONE ON PURPOSE. Wave 1 said "the pixels are split by the
  # vertical stripes of the aperture grille into red, green and blue phosphor bars" and
  # FLUX.2 DREW THAT - full-strength RGB stripes painted across the whole picture, two of
  # four cells destroyed (they are in _dropped/ with the reason). This is the checkpoint
  # card's known literalism failure in its purest form: name a display technology as a
  # noun and you get the technology as an object, not as an effect. The replacement asks
  # for the CONSEQUENCES of a CRT - glow, softening, curvature - and never names the part.
  tell="The image is made of large hand-placed square pixels from a palette of sixteen "
       "colours and nothing else, with dithered checkerboard patterns standing in for every "
       "gradient and hard single-pixel black outlines around every object. Every diagonal is "
       "a visible staircase. Bright areas glow outward and soften into the dark ones. The "
       "whole picture bows very slightly outward at the centre of the curved glass, and a "
       "dim reflection of the dark room lies across one corner of it.",
  finish="Shot with a macro lens at f8 square on to the glass with the room lights off, "
         "natural colour, the screen the only light source.",
  size="1536x1152"),

 "neon": dict(
  name="Neon glass",
  blurb="Bent glass tube, real electrodes, real wall glow.",
  lead="A night photograph of a neon sign mounted on a brick wall, photographed as a real "
       "glass object.",
  tell="Every line in the sign is one continuous bent glass tube of even thickness that never "
       "branches, so the drawing is a single unbroken path with the returns and the dark "
       "painted-out sections that a real tube bender would need. The tubes are supported on "
       "spot-welded metal standoffs, black electrode housings sit at the ends, and there are "
       "visible cables and a transformer box. The lit tube has a hot white core with the "
       "colour blooming outward from it, and it throws a real coloured wash onto the brick "
       "behind and a reflection into the wet pavement below. One section has failed and sits "
       "dark grey.",
  finish="Shot at night on a 35mm at f2.8, long exposure, the wall lit only by the sign, "
         "natural colour.",
  size="1536x1024"),

 "airbrush": dict(
  name="Airbrushed metal",
  blurb="Candy coat and masked edges on a real panel.",
  lead="A photograph of an airbrushed mural painted on the metal side panel of a 1979 van, "
       "shot square on to the panel.",
  tell="The paint is sprayed in soft graded fades with no brush marks anywhere, over a base "
       "coat whose metallic flake sparkles under the light. The hard edges were made with "
       "frisket masks so they are absolutely crisp against the soft gradients, and one mask "
       "has lifted and let a thin spray of overspray through. Fine white highlight lines were "
       "sprayed last through a stencil. The whole thing is under a thick clearcoat that "
       "reflects the sky and the street, and there are swirl marks in the polish and one "
       "stone chip through to primer.",
  finish="Shot square on with a 35mm at f8 on an overcast day so the clearcoat reflects a flat "
         "grey sky, natural colour.",
  size="1536x1024"),

 "shadowpuppet": dict(
  name="Shadow puppet",
  blurb="Pierced hide against a lit cotton screen.",
  lead="A photograph of a shadow puppet performance seen from the audience side of the lit "
       "cotton screen.",
  tell="The figures are flat silhouettes of pierced and cut hide pressed against the back of "
       "the screen, so all their interior detail exists only as small punched holes and thin "
       "cut slots that let light through. Where a puppet touches the cloth its edge is razor "
       "sharp and where it lifts away the shadow goes soft and doubles. The thin control rods "
       "read as hard vertical lines. The cotton screen has a visible weave, a seam across it, "
       "and the oil lamp behind falls off into darkness at the corners of the frame.",
  finish="Shot on an 85mm at f2.8 from the dark audience side, exposed for the lit screen, "
         "warm lamplight, natural colour, fine grain.",
  size="1536x1024"),

 "papercut": dict(
  name="Layered papercut",
  blurb="Cut card in stacked planes, real cast shadows.",
  lead="A photograph of a layered papercut diorama inside a shallow wooden box, shot straight "
       "on into the box.",
  tell="The scene is built from six separate sheets of cut card standing at different depths, "
       "each one a flat silhouette with no shading of its own, and each one throws a real soft "
       "shadow onto the sheet behind it so the depth is made entirely of shadow. Every edge "
       "shows the white core of the card and the slight fuzz of cut fibre, with one or two "
       "places where the craft knife overran a corner. The layers are held apart on small "
       "foam pads that are just visible at the edges.",
  finish="Shot straight on with a 50mm at f11 for deep focus, one warm light raking in from "
         "the top left so the inter-layer shadows are long, natural colour.",
  size="1536x1152"),
}


# -*- coding: utf-8 -*-
"""Corpus part B: subjects.

A gallery, not a test sheet. Every medium gets subjects that would have been CHOSEN for
it by someone who works in it - stained glass gets a saint and a shipwreck, PS1 gets a
car park and a hotel lobby, needle-felt gets a hare - and no subject is used twice.

Each entry is (medium, slug, subject_passage, size_override_or_None). The subject passage
carries WHAT IS DEPICTED and WHAT IT IS DOING. The medium card carries the substrate and
the light. Prompt = lead + subject + tell + finish.
"""

# wave 1: four per medium, the spread that decides whether the medium lives.
WAVE1 = [
 # ---- plasticine
 ("plasticine", "badger_bus", "The model shows a badger in a bus conductor's uniform and peaked cap standing on the open platform of a red double-decker bus, one paw on the pole, punching a ticket with the other. The bus is modelled too, cut off at the rear axle.", None),
 ("plasticine", "diver_octopus", "The model shows a deep-sea diver in a copper helmet and canvas suit shaking hands with an octopus on a seabed of modelled clay rocks and weed. Bubbles rise from the helmet valve as small clear beads.", None),
 ("plasticine", "kitchen_disaster", "The model shows a small kitchen where a pressure cooker has just blown its lid. A woman in an apron is flat against the wall with her arms up, the lid is in the air, and modelled soup hangs in mid-flight in strings. Every pot and tile is modelled.", None),
 ("plasticine", "moon_picnic", "The model shows two astronauts sitting on a folded picnic blanket on the surface of the moon with a hamper open between them, their helmets set down beside them, a small modelled Earth hanging in a black sky.", None),

 # ---- stopmotion
 ("stopmotion", "fox_tailor", "A fox puppet in a three-piece tweed suit stands at a tailor's cutting table with a tape measure round its neck, chalking a line on a bolt of cloth. Behind it the miniature shop is walled with tiny bolts of fabric and a brass till.", None),
 ("stopmotion", "witch_kitchen", "A hunched witch puppet in layered felt robes stirs an iron pot over a fire in a miniature cottage kitchen, her free hand holding a jar up to the light. Bundled herbs hang from the beam above her.", None),
 ("stopmotion", "boy_telescope", "A boy puppet in a knitted jumper kneels on a miniature attic floor with his eye to a brass telescope pushed through a gap in the roof tiles, one hand steadying it. Boxes and a rocking horse fill the space behind him.", None),
 ("stopmotion", "skeleton_rowing", "A skeleton puppet with articulated brass joints rows a small wooden boat across a miniature sea of painted glass and cotton wool, leaning back into the stroke, a lantern hooked on the prow.", None),

 # ---- needlefelt
 ("needlefelt", "hare_boxing", "The sculpture is a brown hare sitting up on its haunches with both forepaws raised, ears back, mid-box. Its fur is felted in shifting browns and its belly is cream.", None),
 ("needlefelt", "kingfisher", "The sculpture is a kingfisher perched on a felted reed, body turned, beak down toward the water. Its back is felted in three blues and its breast in burnt orange.", None),
 ("needlefelt", "sheep_farmer", "The sculpture is a small figure of a shepherd in a felted wax jacket and flat cap with a crook under one arm, a felted collie sitting pressed against his leg looking up at him.", None),
 ("needlefelt", "hedgehog_teacup", "The sculpture is a hedgehog curled asleep inside a real china teacup that is part of the photograph, its spines felted in stiff dark grey fibre against soft cream underfur.", None),

 # ---- brick
 ("brick", "lighthouse_storm", "The model is a lighthouse on a stack of grey rocks with a wave built from clear and white bricks curling up against it, a keeper figure with a printed face standing in the doorway.", None),
 ("brick", "space_station", "The model is a rotating space station with a central hub and four spokes, a small shuttle docked at one port, built in white, grey and trans-blue bricks against a black background.", None),
 ("brick", "diner_corner", "The model is a corner diner with a curved chrome facade, red booth seats visible through the windows, a counter with three stools, and a minifigure cook behind it holding a spatula.", None),
 ("brick", "t_rex_skeleton", "The model is a museum tyrannosaurus skeleton mounted in a striding pose on a base, built entirely in white and tan bricks, with a railing and two visitor figures for scale.", None),

 # ---- origami
 ("origami", "crane_flock", "Five paper cranes at different sizes stand in a loose arc, the largest in front with its wings pulled open, the smallest behind. The paper is red on one face and cream on the other.", None),
 ("origami", "elephant", "A folded elephant stands with its trunk raised, the reversed folds of the ears showing the pale reverse of the sheet against the deep blue front.", None),
 ("origami", "samurai_helmet", "A folded samurai helmet sits on the table with its wide swept horns forward, folded from a large sheet of gold paper with a black reverse.", None),
 ("origami", "koi_pair", "Two folded koi lie overlapping as if swimming past each other, one folded from orange paper and one from white with a grey reverse, their scales suggested by a pleated fold across the body.", None),

 # ---- ceramic
 ("ceramic", "moon_jar", "The piece is a large round white moon jar with a visible join around its middle where two thrown halves were luted together, standing alone.", None),
 ("ceramic", "tea_bowl", "The piece is a hand-thrown tea bowl with a heavily faceted side, glazed in a thick iron glaze that has broken to rust at the rim and pooled black in the well.", None),
 ("ceramic", "owl_jug", "The piece is a jug modelled as an owl with the handle as its folded wing and the spout as its beak, glazed in a running honey glaze over a white slip.", None),
 ("ceramic", "tiles_fish", "The piece is a set of four square tiles laid together making one leaping fish across all four, tin-glazed white with cobalt blue painted brushwork.", None),

 # ---- sand
 ("sand", "castle_collapse", "The sculpture is a tall castle keep with carved windows and a spiral stair cut into its side, and one whole corner turret has already slumped into a heap at its foot.", None),
 ("sand", "sleeping_giant", "The sculpture is the head and one shoulder of a giant lying asleep in the beach, carved so it appears half sunk in the sand, its eye closed and its hair carved as long ridges.", None),
 ("sand", "wave_carved", "The sculpture is a breaking wave carved from a single mound, its lip curled over into a tube, the whole impossible thing standing in still sand.", None),
 ("sand", "dragon_coil", "The sculpture is a dragon coiled twice around a carved column, its head at the top, individual scales cut with a knife point down the length of its back.", None),

 # ---- wax
 ("wax", "anatomical_hand", "The figure is a study of a human hand, life-size, held open with the fingers slightly curled, the tendons and knuckles modelled carefully and the wrist left as a rough cut mass.", None),
 ("wax", "horse_rearing", "The figure is a small horse rearing on its hind legs with its mane thrown back, a twisted wire armature showing through the wax at one raised foreleg.", None),
 ("wax", "portrait_bust", "The figure is a portrait bust of an old woman with her hair pinned up, one side of the face finished and smoothed and the other still in rough blocked planes.", None),
 ("wax", "hive_form", "The figure is a beehive-shaped abstract form with a spiral scraped into its surface, standing on a small turned wooden base.", None),

 # ---- benday
 ("benday", "romance_panel", "The page shows a single large comic panel: a woman in the foreground turns away from a man in a doorway, one hand at her mouth, tears drawn as three hard teardrop shapes. A yellow caption box in the top left corner reads exactly MEANWHILE, IN QUEENS. A speech balloon from the man reads exactly DONT GO.", None),
 ("benday", "war_panel", "The page shows a comic panel of a fighter pilot in a leather helmet and goggles pulling back on the stick, the cockpit canopy framing him, another plane trailing smoke behind. A jagged burst shape in the top right corner reads exactly BRAKKA BRAKKA.", None),
 ("benday", "monster_panel", "The page shows a comic panel of an enormous crab rising out of a harbour with tiny fishing boats beneath it, people on the quay pointing up. A caption box along the bottom reads exactly IT CAME FROM THE HARBOUR MOUTH.", None),
 ("benday", "advert_page", "The page is a full-page back-cover comic advertisement for a mail-order sea monkey kit, with a cartoon family of grinning sea creatures, a coupon with a dotted cut line in the bottom corner, and a headline that reads exactly OWN A BOWLFUL OF HAPPINESS.", None),

 # ---- risograph
 ("risograph", "cyclist", "The poster shows a cyclist seen from the side climbing out of the saddle on a steep road, hills stacked behind in flat shapes.", None),
 ("risograph", "concert_bill", "The poster is a gig bill: a drum kit seen head on, sticks crossed above it, with a band name in heavy condensed capitals across the top that reads exactly THE LONG SLOW EMERGENCY and a date line at the bottom that reads exactly FRI 14 NOV - THE MARINE HALL.", None),
 ("risograph", "swimmers", "The poster shows six swimmers seen from directly above in a lido, each in their own lane, their arms mid-stroke, the water a flat field of the blue ink.", None),
 ("risograph", "greenhouse", "The poster shows the interior of a botanical greenhouse with enormous leaves in the foreground and the iron ribs of the roof arching overhead.", None),

 # ---- woodcut
 ("woodcut", "wave_boat", "The print shows a small open boat with four rowers being lifted on the face of a huge breaking wave, the foam of the crest cut as clawing fingers, a mountain small and calm in the distance.", None),
 ("woodcut", "wolf_forest", "The print shows a wolf standing among close-set pine trunks looking straight out of the picture, the forest floor cut in short dashes and the canopy in dense black.", None),
 ("woodcut", "harvest", "The print shows three figures cutting corn with sickles in a field, bent at the waist, the stooks behind them and a cart at the top edge of the picture.", None),
 ("woodcut", "skeleton_dance", "The print shows a line of skeletons dancing hand in hand with a bishop, a soldier and a merchant, in the manner of a dance of death, a fiddle-playing skeleton leading them.", None),

 # ---- linocut
 ("linocut", "puffin_cliff", "The print shows a puffin standing on a cliff edge in profile with a beakful of sand eels, the sea and a second cliff behind it. The flat colour block is a burnt orange.", None),
 ("linocut", "tractor_field", "The print shows a tractor ploughing, seen from behind and slightly above, gulls following the furrow in a scattered flock. The flat colour block is a chalk blue.", None),
 ("linocut", "cat_window", "The print shows a cat sitting in a window frame with its back to the room, looking out at rooftops and chimney pots. The flat colour block is a warm yellow.", None),
 ("linocut", "runners_start", "The print shows five runners at the moment a race starts, bunched and leaning forward, legs overlapping. The flat colour block is a deep red.", None),

 # ---- letterpress
 ("letterpress", "seed_packet", "The sheet is a seed packet design, with a wood-engraved beetroot in the centre, and type above it that reads exactly DETROIT GLOBE BEETROOT and below it in small capitals exactly SOW APRIL TO JUNE - THIN TO SIX INCHES.", None),
 ("letterpress", "auction_bill", "The sheet is a farm auction bill in six sizes of wood type stacked full width, the largest line reading exactly SALE OF LIVE AND DEAD STOCK, a smaller line reading exactly TUESDAY THE 14TH AT ELEVEN, and a rule between every section.", None),
 ("letterpress", "concert_ticket", "The sheet is a small concert ticket with a hairline border, a numbered stub with a perforation down one side, and type that reads exactly ADMIT ONE - GALLERY and beneath it exactly NO 0447.", None),
 ("letterpress", "specimen_page", "The sheet is a type specimen page showing one alphabet in a heavy slab serif at large size, the full lowercase beneath it, and a line of numerals at the foot, with a small ornament in the top corner.", None),

 # ---- etching
 ("etching", "rooftops_rain", "The print shows a run of city rooftops and chimney stacks in rain, seen from a high window, with washing lines strung between two of them.", None),
 ("etching", "old_man_hands", "The print shows an old man seated with his hands folded in his lap, his face half in shadow, in the manner of a seventeenth century portrait etching.", None),
 ("etching", "heron_reeds", "The print shows a heron standing in reeds, its neck folded back, the water surface indicated by a few horizontal lines and left mostly bare.", None),
 ("etching", "ruined_abbey", "The print shows the ruined nave of an abbey with grass growing on the wall heads and two tiny figures for scale under the west arch.", None),

 # ---- cyanotype
 ("cyanotype", "fern_specimen", "The print is a contact print of pressed ferns and grasses laid directly on the paper, five fronds arranged across the sheet, their stems overlapping, every leaflet recorded as a white silhouette.", None),
 ("cyanotype", "pier_legs", "The print shows the underside of a seaside pier, the forest of iron legs receding, the sea between them.", None),
 ("cyanotype", "hands_wheat", "The print shows a pair of hands holding a bundle of wheat ears, cropped at the wrists.", None),
 ("cyanotype", "jellyfish", "The print shows three moon jellyfish suspended at different depths, their trailing tentacles fine and pale.", None),

 # ---- blueprint
 ("blueprint", "steam_locomotive", "The drawing is a general arrangement of a steam locomotive: a side elevation with the boiler and driving wheels, a plan below it, and a front end view to the right, with leader lines to numbered parts and a title block that reads exactly CLASS 4F 0-6-0 - GENERAL ARRANGEMENT.", None),
 ("blueprint", "lighthouse_section", "The drawing is a vertical section through a lighthouse showing the stair spiralling up the tower, the store rooms, the keepers quarters and the lantern room with its lens, hatched to show the masonry.", None),
 ("blueprint", "diving_bell", "The drawing is a sectional drawing of a diving bell with its air hose, ballast weights, viewing ports and bench, with dimension lines to the outside and a scale bar at the bottom.", None),
 ("blueprint", "bridge_truss", "The drawing is an elevation of a wrought iron railway truss bridge across three spans, with an enlarged detail of one riveted joint circled and drawn separately at larger scale.", None),

 # ---- chalkboard
 ("chalkboard", "cafe_menu", "The drawing is a cafe menu board with a curling banner across the top that reads exactly TODAYS SOUP, a drawn bowl with steam beneath it, and a hand-lettered line at the bottom that reads exactly LEEK AND POTATO - 4.50.", None),
 ("chalkboard", "orrery_lesson", "The drawing is a schoolroom diagram of the solar system with the sun at the left, six planets on their arcs, the moon shown orbiting one of them, and each body labelled in a schoolmaster's cursive.", None),
 ("chalkboard", "rugby_moves", "The drawing is a coach's board covered in a rugby lineout plan, players as circles and crosses, arrows curving between them, a scrawled line at the side that reads exactly HOLD THE SHAPE.", None),
 ("chalkboard", "anatomy_heart", "The drawing is a lecture diagram of a human heart in section, chambers labelled with arrows for the direction of blood flow, drawn in white with one colour of chalk used for the arteries.", None),

 # ---- scratchboard
 ("scratchboard", "owl_flight", "The engraving shows a barn owl flying straight at the viewer at night, wings spread wide, every feather scratched out as a separate white line, the darkness behind it left solid.", None),
 ("scratchboard", "trawler_night", "The engraving shows a fishing trawler working at night, its deck lights blazing, the net coming up over the stern, the sea a mass of short scratched strokes.", None),
 ("scratchboard", "wolfhound", "The engraving shows the head and chest of a wolfhound in three-quarter view, its rough coat built from thousands of short scratched hairs.", None),
 ("scratchboard", "chapel_window", "The engraving shows the interior of a small chapel with a single shaft of light coming through a high window and striking the floor, the beam scratched as fine parallel lines through the dark.", None),

 # ---- screenprint
 ("screenprint", "surf_van", "The poster shows a boxy camper van parked side on with two surfboards on the roof and a low sun behind it, everything reduced to four flat colours.", None),
 ("screenprint", "boxer_portrait", "The poster shows a boxer's head and shoulders, gloves up by his chin, reduced to four flat colours with the darkest doing all the drawing.", None),
 ("screenprint", "mountain_range", "The poster shows a range of mountains in receding planes, each ridge a separate flat colour, a lake in the foreground holding a flat reflection.", None),
 ("screenprint", "record_sleeve", "The poster is a record sleeve design showing a rotary telephone with its cord trailing off the bottom edge, with a title line in the top right that reads exactly HOLD MUSIC FOR THE END OF THE WORLD.", None),

 # ---- watercolour
 ("watercolour", "hare_field", "The painting shows a hare sitting in long grass, alert, its ears up, the grass around it done in wet-in-wet strokes that bleed into the background and the far field left as bare paper.", None),
 ("watercolour", "harbour_boats", "The painting shows three fishing boats leaning over on the mud at low tide in a small harbour, the wet mud reflecting them in soft downward washes, a stone quay behind.", None),
 ("watercolour", "peonies", "The painting shows a bunch of blown peonies in a glass jar on a windowsill, the petals painted as single loaded strokes each dropping a darker edge as it dried.", None),
 ("watercolour", "rain_street", "The painting shows a wet city street at dusk with two umbrellas and the lit windows of a shop, the reflections in the road pulled downward in vertical wet strokes.", None),

 # ---- impasto
 ("impasto", "sunflowers_late", "The painting shows a jug of sunflowers past their best, heads dropping, painted so thickly that each petal is a single raised ridge of yellow.", None),
 ("impasto", "north_sea", "The painting shows a heavy grey sea under a low sky, no land, the swell built from knife-laid slabs of grey green and the foam scraped on last in white.", None),
 ("impasto", "man_in_cap", "The painting shows the head and shoulders of a man in a flat cap seen three-quarter on, his face built from broad separate planes of colour laid side by side without blending.", None),
 ("impasto", "orchard_snow", "The painting shows bare apple trees in snow, the trunks laid in dark knife strokes and the snow built up in thick white ridges that hold real shadow.", None),

 # ---- gouache
 ("gouache", "bus_station", "The painting shows a 1950s bus station at night, three buses under a concrete canopy, a lit timetable board and two waiting figures, in a flat limited palette.", None),
 ("gouache", "arctic_camp", "The painting shows a small expedition camp on ice, two orange tents, a sledge and a figure bent over a stove, under a pale flat sky.", None),
 ("gouache", "diner_interior", "The painting shows the inside of a roadside diner seen from a corner booth, the counter running away to the right, a waitress at the far end, flat shapes and hard edges.", None),
 ("gouache", "botanical_thistle", "The painting is a botanical study of a thistle with a dissected floret and a seed head placed separately on the same sheet, painted opaquely with fine dry-brush detail.", None),

 # ---- fresco
 ("fresco", "fishermen", "The painting shows three fishermen hauling a net full of fish into a boat, their bodies simplified and outlined, a band of stylised waves beneath them.", None),
 ("fresco", "banquet", "The painting shows a banquet with figures reclining along a table in a row, each holding a cup, a servant with a jug at the left end, and a border of stylised vine above.", None),
 ("fresco", "horse_and_boy", "The painting shows a boy leading a horse by a rope halter, both in profile, on a plain ground with a single tree behind them.", None),
 ("fresco", "saints_procession", "The painting shows a procession of four haloed figures walking left to right, each carrying a different object, their robes falling in simple repeated folds.", None),

 # ---- embroidery
 ("embroidery", "beetle_specimen", "The embroidery shows a large stag beetle worked life-size seen from directly above, its wing cases in shifting greens and its mandibles outlined in black.", None),
 ("embroidery", "cottage_sampler", "The embroidery is a sampler with a cottage and two trees in the middle, an alphabet worked in cross stitch above it, and a line beneath that reads exactly MARY ANNE COLE AGED 11.", None),
 ("embroidery", "wave_japanese", "The embroidery shows a single stylised breaking wave with its foam worked in raised white satin stitch and the water in six graded blues.", None),
 ("embroidery", "fox_head", "The embroidery shows the head of a fox in three-quarter view, the fur worked in long and short stitch so the direction of the thread follows the direction of the fur.", None),

 # ---- tapestry
 ("tapestry", "unicorn_garden", "The tapestry shows a unicorn standing in a fenced garden of small flowers, its head turned, a pomegranate tree behind it, the ground covered in scattered plants with no perspective.", None),
 ("tapestry", "hunting_party", "The tapestry shows a hunting party of four riders and three hounds moving left to right through a wood, the trees flattened into a decorative screen behind them.", None),
 ("tapestry", "ship_and_whale", "The tapestry shows a single-masted ship on a stylised sea with a whale surfacing beside it and a compass rose in the upper corner.", None),
 ("tapestry", "harvest_months", "The tapestry shows three panels of labour side by side: a man scything, a woman binding a sheaf, and an ox cart, divided by woven columns.", None),

 # ---- stainedglass
 ("stainedglass", "saint_fisher", "The window shows a saint holding a fish in one hand and a staff in the other, standing under a canopy, with a band of Latin text on a scroll at his feet.", None),
 ("stainedglass", "shipwreck", "The window shows a ship breaking up on rocks with figures in the water reaching upward and a lifeboat coming in from the right, in a memorial window with a dedication band at the bottom.", None),
 ("stainedglass", "tree_of_life", "The window shows a tree filling the whole light, its branches spreading into the tracery, birds among them and roots spreading at the base.", None),
 ("stainedglass", "rose_window", "The window is a rose window seen head on, twelve radiating petals each containing a single figure, with a central roundel of a lamb.", "1536x1536"),

 # ---- mosaic
 ("mosaic", "octopus_floor", "The mosaic shows an octopus with its arms curling out to fill a circular panel, surrounded by fish and a border of interlocking wave pattern.", None),
 ("mosaic", "chariot_race", "The mosaic shows a four-horse chariot at full gallop with the driver leaning back, a row of columns behind, in a long horizontal panel.", None),
 ("mosaic", "guard_dog", "The mosaic shows a chained black dog with bared teeth on a white ground, with a line of lettering beneath it that reads exactly CAVE CANEM.", None),
 ("mosaic", "vine_border", "The mosaic shows a peacock standing on a fountain rim drinking, surrounded by a wide border of vine scroll and grapes.", None),

 # ---- marquetry
 ("marquetry", "compass_rose", "The panel shows a sixteen-point compass rose, each point cut from a different veneer so the alternating points read light and dark, inside a double stringing line border.", None),
 ("marquetry", "stag_forest", "The panel shows a stag standing among birch trunks, the birch bark suggested by choosing a pale striped veneer for the trunks and a dark burr for the canopy.", None),
 ("marquetry", "urn_and_swags", "The panel shows a classical urn with swags of husk falling from either handle, in the manner of an eighteenth century cabinet door.", None),
 ("marquetry", "sailing_ship", "The panel shows a three-masted ship under full sail, the sails cut from a pale straight-grained veneer and the sea from a rippling figured one running horizontally.", None),

 # ---- enamel
 ("enamel", "hummingbird_pin", "The pin is a hummingbird in flight with its beak in a trumpet flower, its throat in three enamels of graded red and its wings blurred into two solid shapes.", None),
 ("enamel", "lighthouse_pin", "The pin is a lighthouse with a red and white banded tower, a beam of pale yellow enamel cast out to one side, standing on a rock over a small band of blue.", None),
 ("enamel", "koi_pin", "The pin is a koi curled into a circle to bite its own tail, its scales made by a spiral of gold wire and filled with orange, white and black enamel.", None),
 ("enamel", "moth_pin", "The pin is a luna moth with its wings open and its long tails trailing, the wings in two greens with a small eyespot of amber on each.", None),

 # ---- ps1
 ("ps1", "hotel_lobby", "The screenshot shows a hotel lobby at night with a reception desk, a potted palm, and a lift with its doors open casting a rectangle of light. A player character in a blue jacket stands with their back to the camera in the middle of the floor. A small text box at the bottom of the screen reads exactly THE LIFT IS WAITING.", None),
 ("ps1", "car_park", "The screenshot shows an underground car park with square concrete pillars receding into fog, three low-polygon cars, and a strip light overhead. A yellow arrow floats above one of the cars.", None),
 ("ps1", "castle_courtyard", "The screenshot shows a castle courtyard with a well in the centre, a wooden cart, and battlement walls on three sides. An armoured player character stands mid-stride with a sword drawn. A health bar and a magic bar sit in the top left corner.", None),
 ("ps1", "boss_arena", "The screenshot shows a boss fight in a circular stone arena: an enormous four-legged stone golem standing over a small player character, the floor cracked, a boss health bar stretched along the bottom of the screen.", None),

 # ---- crtpixel
 ("crtpixel", "sidescroll_forest", "The frame shows a side-scrolling platform level in a forest: a running character mid-jump between two mossy platforms, a treasure chest below, three parallax layers of trees behind, and a score line across the top that reads exactly SCORE 004250.", None),
 ("crtpixel", "rpg_town", "The frame shows a top-down role playing game town in three-quarter view, with a well, a shop with a hanging sign, four townspeople, and a dialogue box at the bottom that reads exactly THE ROAD NORTH IS CLOSED.", None),
 ("crtpixel", "shmup_boss", "The frame shows a vertical shooting game: a small player ship at the bottom firing upward at a large mechanical boss that fills the top half of the screen, bullets in dense patterns between them.", None),
 ("crtpixel", "point_click", "The frame shows a point-and-click adventure scene in a cluttered pawn shop, with a player character standing at the counter, a row of verb commands along the bottom of the screen reading exactly LOOK  TALK  USE  TAKE.", None),

 # ---- neon
 ("neon", "diving_lady", "The sign is a diving woman in a swimsuit built in three sequential positions so she appears to dive when they flash, with a curve of tube beneath her spelling exactly PLUNGE POOL.", None),
 ("neon", "motel_vacancy", "The sign is a tall motel sign with an arrow of chasing bulbs down one side, the word MOTEL stacked vertically in orange tube, and a smaller panel below reading exactly NO VACANCY with the NO section dark and unlit.", "1152x1536"),
 ("neon", "oyster_bar", "The sign is an open oyster shell in white and blue tube with a pearl of warm white at its centre, and script tube beneath it reading exactly OYSTER BAR.", None),
 ("neon", "laundrette", "The sign is a washing machine drum drawn in blue tube with three tumbling shirts inside it, above pink script tube reading exactly WASH & FOLD.", None),

 # ---- airbrush
 ("airbrush", "wizard_wolves", "The mural shows a bearded wizard raising a staff on a rocky outcrop with two wolves beside him and a full moon behind, in the manner of a 1979 custom van.", None),
 ("airbrush", "eagle_flag", "The mural shows an eagle coming in with talons out over a mountain lake at sunset, its wings running the length of the panel.", None),
 ("airbrush", "sea_serpent", "The mural shows a sea serpent coiling out of a stormy sea around a small galleon, lightning behind, sprayed in blues and greens.", None),
 ("airbrush", "chrome_skull", "The mural shows a chrome skull wearing a winged helmet over crossed pistons, with flames sprayed behind it and fine white highlight lines on every chrome edge.", None),

 # ---- shadowpuppet
 ("shadowpuppet", "monkey_king", "The performance shows a horned warrior figure with a staff raised over his head facing a bearded demon with a curved sword, both in profile, mid-fight.", None),
 ("shadowpuppet", "elephant_procession", "The performance shows an elephant with a howdah on its back and a driver on its neck, walking left to right, three smaller attendant figures following.", None),
 ("shadowpuppet", "boat_crossing", "The performance shows a boat with a standing poleman carrying two seated passengers, a cut band of stylised water running across the bottom of the screen.", None),
 ("shadowpuppet", "bird_and_snake", "The performance shows a great bird with pierced wings stooping on a coiled snake that rears up to meet it, the two filling the screen.", None),

 # ---- papercut
 ("papercut", "forest_deer", "The diorama shows a deer standing in a forest, with layers of tree silhouettes stepping back behind it and a layer of ferns in front, the furthest layer a plain moon.", None),
 ("papercut", "city_skyline", "The diorama shows a city skyline at three depths with a bridge in the front layer, a river of cut blue card, and a small ferry silhouette between the layers.", None),
 ("papercut", "whale_dive", "The diorama shows a whale diving with its tail up, cut waves stepping forward in four layers, and a small rowing boat in the front layer.", None),
 ("papercut", "reading_window", "The diorama shows the silhouette of a person reading in an armchair by a tall window, with the window frame as the front layer and a garden receding behind it.", None),
]


# -*- coding: utf-8 -*-
"""Wave 2: authored after wave 1 was looked at, so it can spend its budget on the media
that survived. Run with --only <surviving media>, which is why entries exist here for
media that may never be rendered - the filter is applied at the command line, not by
deleting authored work."""

WAVE2 = [
 # ---- plasticine
 ("plasticine", "band_rehearsal", "The model shows a four-piece band crammed into a garage: a drummer behind a modelled kit, a bass player, a guitarist on one knee, and a singer standing on an upturned crate. Cables snake across the floor.", None),
 ("plasticine", "dentist", "The model shows a dentist leaning over a patient in a chair with a mirror and a probe, the patient's mouth wide open and both hands gripping the armrests. A tray of modelled instruments sits beside them.", None),
 ("plasticine", "cheese_heist", "The model shows two mice in striped jumpers lowering themselves on a string toward a wedge of cheese on a kitchen counter, a sleeping cat modelled below them.", None),
 ("plasticine", "penguin_orchestra", "The model shows five penguins in bow ties playing a cello, a trumpet, a triangle, a double bass and a set of cymbals on a modelled stage with a red curtain behind.", None),
 ("plasticine", "lighthouse_tea", "The model shows a lighthouse keeper in a jumper pouring tea in a cramped round room at the top of a tower, the lamp mechanism modelled behind him and rain modelled as streaks on the window.", None),
 ("plasticine", "farmyard_escape", "The model shows a pig halfway through a gap in a fence with a farmer diving after it, three chickens scattering, and a modelled tractor in the background.", None),

 # ---- stopmotion
 ("stopmotion", "mole_library", "A mole puppet in a knitted waistcoat and round spectacles stands on a stepladder in a miniature underground library, pulling a book from a shelf of tiny bound volumes.", None),
 ("stopmotion", "diver_workshop", "A puppet in a canvas diving suit sits on a stool in a miniature workshop with its helmet on the bench beside it, polishing the faceplate with a rag.", None),
 ("stopmotion", "crow_postman", "A crow puppet in a postman's cap and satchel stands at a miniature front door pushing a letter through the flap, a picket fence and a felt hedge behind it.", None),
 ("stopmotion", "chef_lobster", "A chef puppet in whites and a tall hat backs away from a lobster puppet that has climbed onto the miniature kitchen counter with its claws up.", None),
 ("stopmotion", "girl_in_snow", "A girl puppet in a red felt coat and rubber boots stands in a miniature snowy street looking up, snowflakes hung around her on invisible wires.", None),
 ("stopmotion", "inventor_workshop", "An old inventor puppet with wild wire hair leans over a miniature workbench covered in tiny brass cogs, a half-built clockwork bird held in a vice in front of him.", None),

 # ---- needlefelt
 ("needlefelt", "badger_reading", "The sculpture is a badger sitting in a tiny felted armchair with a felted book open on its lap and small round spectacles of bent wire on its nose.", None),
 ("needlefelt", "wren_nest", "The sculpture is a wren standing on the rim of a woven nest with three pale felted eggs in it, its tail cocked up.", None),
 ("needlefelt", "highland_cow", "The sculpture is a highland cow with a long fringe of felted hair hanging over its eyes and curved horns built over wire.", None),
 ("needlefelt", "octopus_jar", "The sculpture is a small octopus draped over the lip of a glass jar with two arms hanging down the outside, every sucker punched separately.", None),
 ("needlefelt", "sleeping_dormouse", "The sculpture is a dormouse curled asleep in a felted cup of leaves with its tail wrapped over its nose.", None),
 ("needlefelt", "arctic_fox", "The sculpture is an arctic fox in winter coat mid-pounce, front paws together and hind legs stretched out behind, mounted on a felted snowdrift.", None),

 # ---- brick
 ("brick", "windmill", "The model is a Dutch windmill with four sails, a stepped gable house at its foot, and a canal of translucent blue plates with a small boat on it.", None),
 ("brick", "submarine_cutaway", "The model is a submarine built with one side left open as a cutaway, showing a bridge, bunks, a torpedo room and four minifigures at their stations.", None),
 ("brick", "pirate_ship", "The model is a pirate ship under sail with cloth sails, three masts, a row of cannon along the side and a minifigure in the crow's nest.", None),
 ("brick", "fire_station", "The model is a two-storey fire station with the doors open and an engine half out, a pole running down from the upper floor, and three minifigure firefighters.", None),
 ("brick", "moon_rover", "The model is a six-wheeled lunar rover on a grey plate landscape with craters built as rings, an astronaut minifigure planting a flag beside it.", None),
 ("brick", "greengrocer_shop", "The model is a narrow three-storey shop with a green awning, crates of studded fruit on the pavement, a bicycle leaning on the wall and a cat on the window ledge.", None),

 # ---- origami
 ("origami", "dragon", "A folded dragon with a long pleated neck, folded wings held open and a tail of narrow reverse folds, standing on its hind legs.", None),
 ("origami", "rose", "A folded rose with layered spiral petals, folded from a single square of red paper, standing on a folded stem and leaf.", None),
 ("origami", "owl_branch", "A folded owl sitting on a folded branch, its ear tufts made by two sharp reversed folds and its face by a single crimped fold.", None),
 ("origami", "sailing_boat", "A folded boat with a triangular sail and a hull that opens into a flat base, folded from paper printed with a fine blue grid on one face.", None),
 ("origami", "stag_beetle", "A folded stag beetle with segmented legs and two long folded mandibles, folded from one square of dark brown paper.", None),
 ("origami", "crab", "A folded crab with eight folded legs and two raised claws, its shell made from a single pleated surface, sitting on a dark table.", None),

 # ---- ceramic
 ("ceramic", "celadon_vase", "The piece is a tall narrow vase under a pale green celadon glaze, the glaze pooling darker in an incised line pattern cut into the body.", None),
 ("ceramic", "salt_pig", "The piece is a salt pig with a wide mouth, thumb-pressed decoration around the shoulder, and a thick cream glaze that has run and stopped short of the foot.", None),
 ("ceramic", "raku_bowl", "The piece is a raku-fired bowl with a crackled white glaze stained grey in every crack and a rim gone matte black from the reduction.", None),
 ("ceramic", "hare_lidded_jar", "The piece is a lidded jar with a modelled hare crouched as the knob of the lid, glazed in a speckled iron glaze with the hare left in bare white porcelain.", None),
 ("ceramic", "delft_plate", "The piece is a flat plate with a windmill and two figures painted in cobalt blue on a tin white glaze, a border of stylised flowers, and one chipped edge.", None),
 ("ceramic", "teapot_dragon", "The piece is a small teapot whose handle is a modelled dragon and whose tail forms the spout, glazed in a running oxblood red over a stoneware body.", None),

 # ---- sand
 ("sand", "cathedral_front", "The sculpture is the west front of a cathedral with three carved arched doorways, a rose window cut right through the sand, and two towers of unequal height.", None),
 ("sand", "hand_from_beach", "The sculpture is an enormous hand rising out of the beach as if the rest of the body were buried, the fingers curled, sand crumbling from the fingertips.", None),
 ("sand", "turtle", "The sculpture is a sea turtle mid-stroke with its flippers extended, the plates of the shell carved as separate raised panels.", None),
 ("sand", "chess_king", "The sculpture is a chess king a metre tall on a carved plinth, the cross of its crown carved thin and already cracking.", None),
 ("sand", "diver_helmet", "The sculpture is an oversized old diving helmet with three carved portholes, standing alone on wet sand.", None),
 ("sand", "coiled_rope", "The sculpture is a coil of ship's rope and an anchor carved together as one mass, the rope fibres cut in with a knife point.", None),

 # ---- wax
 ("wax", "hare_leaping", "The figure is a hare stretched out in mid-leap, supported only by a wire under its belly, the wax scraped thin along the back.", None),
 ("wax", "hands_clasped", "The figure is a pair of clasped hands modelled life-size on a wooden block, the knuckles smoothed and the wrists left rough.", None),
 ("wax", "dancer_turning", "The figure is a small dancer caught mid-turn with one arm above her head, her skirt modelled as a thin translucent sheet of wax.", None),
 ("wax", "bull_charging", "The figure is a bull with its head lowered and one foreleg forward, modelled in heavy masses with loop tool marks left across the shoulder.", None),
 ("wax", "skull_study", "The figure is an anatomical skull modelled in wax over a plaster core, the white core showing through a thin patch on the temple.", None),
 ("wax", "seated_figure", "The figure is a seated woman with her elbows on her knees and her chin on her hands, blocked out in planes with almost no surface finishing.", None),

 # ---- benday
 ("benday", "space_panel", "The page shows a comic panel of an astronaut floating outside a capsule with a tether behind him and a planet filling the background. A caption box in the top left reads exactly THE TETHER WAS FRAYING.", None),
 ("benday", "western_panel", "The page shows a comic panel of a gunfighter turning in a dusty street with his hand at his hip, a saloon and a water trough behind him. A jagged burst shape in the corner reads exactly BLAM.", None),
 ("benday", "detective_panel", "The page shows a comic panel of a detective in a trench coat and hat lighting a cigarette under a streetlight in the rain. A caption box along the bottom reads exactly SHE HAD LIED ABOUT THE TRAIN.", None),
 ("benday", "jungle_panel", "The page shows a comic panel of a woman in a pith helmet cutting through vines with a machete, a snake coiled on a branch above her that she has not seen. A caption box reads exactly SOMETHING WAS WATCHING.", None),
 ("benday", "kitchen_ad", "The page is a full-page comic advertisement for a kitchen gadget, a smiling woman holding it up beside a cutaway diagram with numbered call-outs, and a headline that reads exactly NEVER PEEL A POTATO AGAIN.", None),
 ("benday", "superhero_panel", "The page shows a comic panel of a caped figure landing in a crouch on a rooftop with the city lights behind, one fist on the gravel. A caption box reads exactly THE ROOF GAVE A LITTLE.", None),

 # ---- risograph
 ("risograph", "library_poster", "The poster shows a person asleep at a library desk under a green lamp with a tower of books beside them, and a line of type at the foot that reads exactly OPEN UNTIL MIDNIGHT.", None),
 ("risograph", "birdwatchers", "The poster shows two birdwatchers lying flat in long grass with binoculars up, and a single enormous bird standing in front of them looking down at them.", None),
 ("risograph", "night_bus", "The poster shows a bus interior at night seen down the aisle, four passengers in silhouette and the driver's mirror at the far end.", None),
 ("risograph", "mountain_hut", "The poster shows a small hut on a mountain ridge with a figure at the door and a line of footprints coming up the snow toward it.", None),
 ("risograph", "record_shop", "The poster shows a person flipping through a crate of records seen from above, their hands and the record sleeves filling the frame.", None),
 ("risograph", "market_stall", "The poster shows a fruit stall with an awning, a stallholder with a paper bag in one hand, and pyramids of stacked fruit.", None),

 # ---- woodcut
 ("woodcut", "whale_hunt", "The print shows a whale surfacing under a small boat and lifting it clear of the water, three figures thrown into the air, the sea cut as rolling scale-like curves.", None),
 ("woodcut", "printing_shop", "The print shows a sixteenth century printing shop with a man at the press pulling the bar, a compositor at a case of type, and drying sheets hung on a line above.", None),
 ("woodcut", "eclipse_crowd", "The print shows a crowd in a market square all looking up at an eclipsed sun, some shielding their eyes, one figure kneeling.", None),
 ("woodcut", "mountain_pilgrims", "The print shows a line of pilgrims with staffs climbing a steep zigzag path up a mountain, cloud cut as flat bands across the slope.", None),
 ("woodcut", "owl_and_mice", "The print shows an owl on a bare branch at night with three mice in the grass below, the night sky cut as solid black with a white crescent moon.", None),
 ("woodcut", "storm_at_sea", "The print shows a sailing ship heeled over under a black sky with lightning cut as white jagged lines and the crew clinging to the rigging.", None),

 # ---- linocut
 ("linocut", "swimmer_lake", "The print shows a swimmer's head and shoulders in open water seen from the side, ripples spreading in concentric cut lines. The flat colour block is a deep teal.", None),
 ("linocut", "kestrel_hover", "The print shows a kestrel hovering with its wings held high and its tail fanned, a hedgerow and a field far below. The flat colour block is a pale ochre.", None),
 ("linocut", "brass_band", "The print shows a brass band marching toward the viewer, a bass drum in front and a row of bells behind it. The flat colour block is a bright red.", None),
 ("linocut", "allotment", "The print shows an allotment with a shed, a water butt, bean poles in a row and a figure bent over a bed. The flat colour block is a leaf green.", None),
 ("linocut", "lighthouse_gull", "The print shows a lighthouse from below with a gull crossing in front of it, the tower cut in bold vertical strokes. The flat colour block is a slate blue.", None),
 ("linocut", "fox_bins", "The print shows an urban fox standing among knocked-over bins in an alley at night, looking back over its shoulder. The flat colour block is a sodium orange.", None),

 # ---- letterpress
 ("letterpress", "railway_notice", "The sheet is a railway notice inside a heavy rule border. The main line reads exactly PASSENGERS MUST NOT CROSS THE LINE. Below it in smaller type exactly BY ORDER OF THE COMPANY and at the foot exactly PENALTY FORTY SHILLINGS.", None),
 ("letterpress", "wedding_invitation", "The sheet is a wedding invitation set centred in a fine old style face. The lines read exactly TOGETHER WITH THEIR FAMILIES, then exactly RUTH AND ISOBEL, then exactly THE TWELFTH OF SEPTEMBER, then exactly THE OLD CUSTOM HOUSE.", None),
 ("letterpress", "circus_bill", "The sheet is a circus bill in five sizes of wood type with a wood-engraved elephant in the middle. The largest line reads exactly ONE NIGHT ONLY and below the cut exactly MARVELS OF THE ORIENT.", None),
 ("letterpress", "apothecary_wrapper", "The sheet is a printed powder wrapper with a small mortar and pestle cut, reading exactly TAKE ONE POWDER IN WATER on the first line and exactly THRICE DAILY AFTER FOOD on the second.", None),
 ("letterpress", "poem_broadside", "The sheet is a broadside of a short poem set in one column with generous leading, an ornamental initial at the start, and a colophon at the foot that reads exactly SET BY HAND AND PRINTED IN AN EDITION OF NINETY.", None),
 ("letterpress", "warning_label", "The sheet is a printed warning label inside a thick black border. The lines read exactly THIS SIDE UP, then exactly GLASS - WITH CARE, then exactly DO NOT STOW IN THE HOLD.", None),

 # ---- etching
 ("etching", "windmill_flat", "The print shows a windmill on a flat horizon with a cart track running toward it, the sky left almost entirely bare paper.", None),
 ("etching", "beggars", "The print shows two beggars at a doorway, one seated with a stick, the line concentrated in the faces and the rest of the plate left open.", None),
 ("etching", "canal_bridge", "The print shows a low brick bridge over a canal with a barge passing under it and a man on the towpath leading a horse.", None),
 ("etching", "self_portrait", "The print is a self portrait of the artist at the plate, seen close, with wild hair and one eye lost in deep burr shadow.", None),
 ("etching", "tree_alone", "The print shows a single wind-shaped tree on a bank with its roots exposed, the ground indicated by a few drypoint flicks.", None),
 ("etching", "market_crowd", "The print shows a crowded market with figures pressed together under awnings, the foreground fully worked and the back of the crowd only suggested.", None),

 # ---- cyanotype
 ("cyanotype", "seaweed_specimens", "The print is a contact print of four kinds of seaweed laid out across the sheet with a small pencil note under each, every frond recorded in fine white detail.", None),
 ("cyanotype", "shipyard_cranes", "The print shows a row of shipyard cranes against a blank sky, their lattice arms crossing each other.", None),
 ("cyanotype", "swimmer_underwater", "The print shows a swimmer underwater seen from below with arms out, the surface above broken into pale shapes.", None),
 ("cyanotype", "birch_wood", "The print shows a stand of birch trunks receding, the trunks pale and the gaps between them deep blue.", None),
 ("cyanotype", "feathers", "The print is a contact print of seven feathers of different sizes arranged in a fan across the sheet, every barb recorded.", None),
 ("cyanotype", "bicycle_leaning", "The print shows a bicycle leaning against a wall, its spokes and frame recorded as pale lines against a deep blue ground.", None),

 # ---- blueprint
 ("blueprint", "airship_frame", "The drawing is a side elevation and two cross sections of a rigid airship showing the ring frames, the gas cells, the keel walkway and the gondolas, with a scale bar and a title block that reads exactly RIGID AIRSHIP - FRAME ARRANGEMENT.", None),
 ("blueprint", "clock_movement", "The drawing is an exploded assembly of a mechanical clock movement with the plates, the going train, the escapement and the fusee drawn separately and joined by dashed centre lines, each part numbered.", None),
 ("blueprint", "harbour_plan", "The drawing is a harbour plan seen from above with two breakwaters, soundings marked as small numbers across the water, a lighthouse symbol and a north arrow.", None),
 ("blueprint", "tenement_section", "The drawing is a section through a four-storey tenement showing every floor, the stair well, the chimney flues and the basement, with room names lettered in each space.", None),
 ("blueprint", "engine_piston", "The drawing is a detail sheet of a piston and connecting rod at large scale with a sectional view, an end view, four dimensioned details and a materials note.", None),
 ("blueprint", "glider_wing", "The drawing is a plan of a glider wing showing the spar, the ribs at stations numbered one to fourteen, the aileron hinge line, and a rib profile drawn separately at larger scale.", None),

 # ---- chalkboard
 ("chalkboard", "pub_specials", "The drawing is a pub board with a drawn pint glass and a curling ribbon that reads exactly TONIGHT, below it exactly QUIZ AT EIGHT, and at the foot exactly LOSERS BUY THE CRISPS.", None),
 ("chalkboard", "sailing_knots", "The drawing is an instructional board showing six knots drawn and labelled, each with an arrow marking the working end, under a heading that reads exactly KNOTS YOU WILL ACTUALLY USE.", None),
 ("chalkboard", "physics_lecture", "The drawing is a university lecture board covered in a force diagram with a block on an inclined plane, arrows for the forces, and three lines of working beneath it, half of an earlier diagram still ghosted behind.", None),
 ("chalkboard", "bird_migration", "The drawing is a natural history board showing a map with curving arrows for migration routes and three birds drawn in the margin at different scales.", None),
 ("chalkboard", "bakery_board", "The drawing is a bakery board with a drawn cottage loaf in the middle and a heading that reads exactly OUT OF THE OVEN AT, with times chalked beside three bread names.", None),
 ("chalkboard", "theatre_call", "The drawing is a backstage call board inside a hand-drawn border, reading exactly HALF HOUR CALL at the top and exactly ACT ONE BEGINNERS TO THE STAGE beneath it.", None),

 # ---- scratchboard
 ("scratchboard", "stag_night", "The engraving shows a stag standing in mist at night, its breath scratched as fine white plumes, the antlers cut hard against solid black.", None),
 ("scratchboard", "lighthouse_beam", "The engraving shows a lighthouse at night with its beam cut as a widening wedge of scratched lines across the dark and waves breaking at the base.", None),
 ("scratchboard", "old_hands_rope", "The engraving shows a pair of old hands splicing a rope, every strand and every wrinkle scratched separately.", None),
 ("scratchboard", "steam_engine", "The engraving shows a steam locomotive coming out of a tunnel at night, the steam scratched into a great white mass above the boiler.", None),
 ("scratchboard", "kingfisher_dive", "The engraving shows a kingfisher entering the water with its wings folded back, the splash cut as radiating white lines.", None),
 ("scratchboard", "cathedral_vault", "The engraving shows the vaulted ceiling of a cathedral seen looking straight up, every rib and boss scratched in white line against black.", None),

 # ---- screenprint
 ("screenprint", "swimmer_pool", "The poster shows a swimmer at the moment of a racing dive, body arched over the water, reduced to four flat colours.", None),
 ("screenprint", "coffee_pot", "The poster shows a stovetop coffee pot on a flame seen square on with steam rising, reduced to three flat colours and a black.", None),
 ("screenprint", "gig_poster_bird", "The poster shows a heron standing in flat water, with a line at the foot that reads exactly TWO NIGHTS AT THE ALBERT.", None),
 ("screenprint", "motorcycle", "The poster shows a motorcycle leaning hard into a corner seen head on with the rider's knee down, reduced to five flat colours.", None),
 ("screenprint", "desert_road", "The poster shows a straight road running to a vanishing point between mesas, the sky in three bands of flat colour.", None),
 ("screenprint", "tiger_face", "The poster shows a tiger's face filling the frame with the stripes doing all the drawing, in four flat colours.", None),

 # ---- watercolour
 ("watercolour", "market_flowers", "The painting shows a flower stall with buckets of blooms on the pavement and a seller wrapping a bunch in paper, the crowd behind suggested only by wet blots.", None),
 ("watercolour", "sheep_in_mist", "The painting shows four sheep on a hillside in mist, the nearest fully painted and the furthest only a pale wash, the hill vanishing into bare paper.", None),
 ("watercolour", "venice_backwater", "The painting shows a narrow canal between two leaning buildings with washing strung across it and a moored boat, the water done in broken horizontal strokes.", None),
 ("watercolour", "kitchen_window", "The painting shows a kitchen windowsill with a jug, two lemons and a pair of glasses, the light through the window bleaching the top of everything to bare paper.", None),
 ("watercolour", "estuary_birds", "The painting shows a wide estuary at low tide with a scatter of wading birds, the whole picture built from three long horizontal washes.", None),
 ("watercolour", "boy_and_dog", "The painting shows a boy sitting on a step with a dog leaning against him, painted loosely with the faces left almost blank.", None),

 # ---- impasto
 ("impasto", "cafe_night", "The painting shows a cafe terrace at night under a yellow awning with a few figures at tables, the lamplight built up in thick swirled ridges.", None),
 ("impasto", "ploughed_field", "The painting shows a ploughed field running to a low horizon, every furrow a separate knife stroke, a strip of pale sky above.", None),
 ("impasto", "woman_at_window", "The painting shows a woman standing at a window with her back to the room, the light on her shoulder scraped on thickly in one stroke.", None),
 ("impasto", "harbour_masts", "The painting shows a forest of masts in a harbour, each mast a single vertical drag of the knife, the water below broken into short horizontal slabs.", None),
 ("impasto", "still_life_fish", "The painting shows two mackerel on a white cloth with a lemon and a knife, the fish scales laid on in short curved strokes of grey green and silver.", None),
 ("impasto", "storm_trees", "The painting shows a row of poplars bending in wind under a heavy sky, the trees laid in with a loaded knife in long upward strokes.", None),

 # ---- gouache
 ("gouache", "cable_car", "The painting shows a cable car halfway up a valley on its wire, the mountain behind flattened into three bands of colour.", None),
 ("gouache", "swimming_pool_noon", "The painting shows an empty outdoor swimming pool at noon with hard shadows and one figure on a diving board, everything reduced to flat shapes.", None),
 ("gouache", "petrol_station", "The painting shows a petrol station at dusk with two pumps under a lit canopy and a single car, the sky a flat graded band.", None),
 ("gouache", "botanical_iris", "The painting is a botanical study of a bearded iris with a bud and a cross-section of the flower placed separately on the same sheet.", None),
 ("gouache", "ferry_deck", "The painting shows the deck of a ferry with rows of empty seats, a life ring on the rail and a flat grey sea beyond.", None),
 ("gouache", "office_night", "The painting shows an office block at night with most windows dark and four lit, seen from the street opposite, in a flat limited palette.", None),

 # ---- fresco
 ("fresco", "olive_harvest", "The painting shows two figures beating an olive tree with poles and a third holding a basket, the tree flattened into a decorative shape.", None),
 ("fresco", "swimmer_diving", "The painting shows a single figure diving from a rock into stylised water, the body simplified to a long outlined curve.", None),
 ("fresco", "musicians", "The painting shows three musicians in profile playing a double pipe, a lyre and a drum, standing in a row on a plain ground.", None),
 ("fresco", "bull_leaping", "The painting shows a figure vaulting over the back of a charging bull with an attendant at either end, in a long horizontal panel with a spiral border.", None),
 ("fresco", "garden_birds", "The painting shows a garden wall with birds among pomegranate branches, the whole surface filled with foliage and no sky at all.", None),
 ("fresco", "shipwreck_votive", "The painting shows a small ship on stylised waves with a figure praying on the shore, and a band of lettering along the bottom edge.", None),

 # ---- embroidery
 ("embroidery", "moth_specimen", "The embroidery shows a large moth with its wings spread, the wing patterns worked in long and short stitch in eight browns and one flash of pink.", None),
 ("embroidery", "map_of_island", "The embroidery is a map of a small island with a compass rose, a stitched coastline, three tiny buildings, and a line of text along the bottom that reads exactly HERE IS WHERE WE LIVED.", None),
 ("embroidery", "hare_and_moon", "The embroidery shows a hare running beneath a full moon, the moon worked in raised padded satin stitch so it stands proud of the linen.", None),
 ("embroidery", "thistle_study", "The embroidery shows a thistle with its head worked as a dense mass of straight stitches in three purples and its leaves in split stitch.", None),
 ("embroidery", "trout", "The embroidery shows a brown trout in profile, each scale a separate tiny stitch and the fins worked in fine open stitching over bare linen.", None),
 ("embroidery", "house_martins", "The embroidery shows three house martins over a stitched roofline with their nests under the eaves, the birds worked in navy and white.", None),

 # ---- tapestry
 ("tapestry", "falconer", "The tapestry shows a falconer on horseback with a hooded bird on his gloved fist and a hound running alongside, against a field of small flowers.", None),
 ("tapestry", "wildwood_boar", "The tapestry shows a boar at bay among trees with three hounds around it and a spearman entering from the right edge.", None),
 ("tapestry", "lady_and_lion", "The tapestry shows a woman standing between a lion and a unicorn holding a banner, on a red ground scattered with flowers and small animals.", None),
 ("tapestry", "vineyard_labour", "The tapestry shows figures picking grapes and treading them in a vat, arranged in two registers one above the other.", None),
 ("tapestry", "sea_monsters", "The tapestry shows a stylised sea filled with fantastical fish and a serpent, with a small ship at the top edge and a wind head blowing from the corner.", None),
 ("tapestry", "castle_siege", "The tapestry shows a castle under siege with a trebuchet at the left, ladders against the wall and defenders on the battlements, all flattened into one plane.", None),

 # ---- stainedglass
 ("stainedglass", "annunciation", "The window shows two figures facing each other across a lily in a pot, one of them winged, under two carved canopies, with a scroll of text between them.", None),
 ("stainedglass", "st_george", "The window shows an armoured figure on a white horse driving a spear into a green dragon coiled at the horse's feet.", None),
 ("stainedglass", "harvest_window", "The window shows a figure with a sheaf of corn under one arm and a sickle in the other hand, standing in a field of stylised wheat.", None),
 ("stainedglass", "miners_memorial", "The window shows three miners with lamps standing shoulder to shoulder at a pit head, with a dedication band of lettering across the bottom of the light.", None),
 ("stainedglass", "creation_roundel", "The window is a single circular roundel showing the sun, the moon and the stars arranged around a central hand, set into plain quarry glazing.", "1536x1536"),
 ("stainedglass", "fishermen_window", "The window shows two figures hauling a net full of fish into a boat on a blue sea, with a shoal of separately leaded fish below them.", None),

 # ---- mosaic
 ("mosaic", "neptune_head", "The mosaic shows the head of a bearded sea god with seaweed in his hair and two dolphins curling out of his beard, in a circular panel.", None),
 ("mosaic", "hunting_dogs", "The mosaic shows two hunting dogs bringing down a stag, arranged in a long panel with a guilloche border.", None),
 ("mosaic", "bathhouse_fish", "The mosaic shows nine kinds of fish and an octopus scattered across a white ground with no border, as a bathhouse floor.", None),
 ("mosaic", "labyrinth_panel", "The mosaic shows a square labyrinth in black on white with a small figure at the centre and a crenellated wall border around it.", None),
 ("mosaic", "vine_and_birds", "The mosaic shows a vine growing out of a two-handled vase with birds perched among the leaves, spreading symmetrically to fill a square panel.", None),
 ("mosaic", "chariot_horses", "The mosaic shows the heads of four horses in a row wearing harness, each one named in small lettering above it.", None),

 # ---- marquetry
 ("marquetry", "songbird_branch", "The panel shows a songbird on a flowering branch, the petals cut from pale holly and the bird's body from a piece of figured maple.", None),
 ("marquetry", "harbour_scene", "The panel shows a harbour with two boats and a row of houses, the roofs cut from a dark straight-grained veneer and the sky from one broad sheet of pale sycamore.", None),
 ("marquetry", "chessboard_border", "The panel is a chessboard with a wide border of interlaced strapwork, the squares alternating ebony and boxwood.", None),
 ("marquetry", "beetle_panel", "The panel shows a stag beetle seen from above at large scale, its wing cases cut from one piece of rippled walnut split down the middle so the figure mirrors.", None),
 ("marquetry", "lighthouse_panel", "The panel shows a lighthouse on a headland with the sea below, the sea cut from a wide piece of wavy-grained veneer running horizontally.", None),
 ("marquetry", "musical_trophy", "The panel shows a trophy of musical instruments - a lute, a horn and a sheet of music - tied with a ribbon, in the manner of an eighteenth century inlay.", None),

 # ---- enamel
 ("enamel", "beetle_pin", "The pin is a jewel beetle seen from above, its wing cases filled with two greens and a gold, its legs picked out in fine wire.", None),
 ("enamel", "wave_pin", "The pin is a breaking wave curled over on itself, the foam in white enamel and the body of the wave in three blues, each cell wired separately.", None),
 ("enamel", "fox_pin", "The pin is a fox curled asleep with its tail over its nose, in three oranges with a white tail tip and a black nose.", None),
 ("enamel", "balloon_pin", "The pin is a hot air balloon with a striped envelope in four enamel colours and a tiny wicker basket rendered in cross-hatched wire.", None),
 ("enamel", "peacock_feather", "The pin is a single peacock feather with the eye at the top filled in blue, green and gold enamel and the barbs suggested by fine radiating wires.", None),
 ("enamel", "compass_pin", "The pin is a compass rose with alternating enamel points in navy and cream, a gold needle across it and a fine wire ring around the edge.", None),

 # ---- ps1
 ("ps1", "train_station", "The screenshot shows a deserted railway platform at night with a bench, a vending machine and a clock, fog swallowing the far end of the platform. A save point icon spins above the bench.", None),
 ("ps1", "racing_game", "The screenshot shows a racing game from a chase camera: a blocky car mid-corner on a coastal road, three other cars ahead, a lap counter and a speedometer along the bottom of the screen.", None),
 ("ps1", "dungeon_corridor", "The screenshot shows a stone dungeon corridor with torches on the walls, a locked door at the end and a skeleton enemy walking toward the camera, an inventory strip along the bottom.", None),
 ("ps1", "village_market", "The screenshot shows a small fantasy village market with four stalls and six villagers, a fountain in the centre, and a text box that reads exactly THEY SAY THE BRIDGE IS OUT.", None),
 ("ps1", "aircraft_hangar", "The screenshot shows the inside of an aircraft hangar with two low-polygon jets, crates stacked along one wall and a strip of skylights overhead.", None),
 ("ps1", "beach_level", "The screenshot shows a bright beach level with palm trees, a jetty running out into flat blue water, and a player character standing on the sand with a rotating item box beside them.", None),

 # ---- crtpixel
 ("crtpixel", "isometric_base", "The frame shows an isometric strategy game: a small base of prefabricated buildings on a grid, four units, a resource counter along the top that reads exactly ORE 1240, and a minimap in the corner.", None),
 ("crtpixel", "fighting_game", "The frame shows a fighting game mid-round: two large sprite characters facing off on a temple stage, two health bars at the top, and a timer between them reading exactly 42.", None),
 ("crtpixel", "puzzle_game", "The frame shows a falling-block puzzle game, the well half full of coloured blocks, the next piece shown in a box at the side, and a line count that reads exactly LINES 087.", None),
 ("crtpixel", "underwater_level", "The frame shows an underwater platform level with a diving character, bubble trails, a treasure chest on the sea floor and an oxygen meter draining along the top.", None),
 ("crtpixel", "space_trading", "The frame shows a space trading game docked at a station, a wireframe planet on the viewscreen, and a menu list of goods with prices down the right side.", None),
 ("crtpixel", "haunted_house", "The frame shows a side-view haunted house level with a staircase, two candles, a ghost sprite and a player character holding a lantern, and a text box that reads exactly THE DOOR IS LOCKED.", None),

 # ---- neon
 ("neon", "bowling_pin", "The sign is a bowling pin and a ball drawn in white and red tube with three chasing arcs behind the ball, above script tube that reads exactly STRIKE LANES.", None),
 ("neon", "coffee_cup", "The sign is a coffee cup with three curls of steam in warm white tube, the steam built as three separate tubes that would flash in sequence, above capitals reading exactly ALL NITE.", None),
 ("neon", "fish_and_chips", "The sign is a fish drawn in a single continuous blue tube with a chip fork crossing it in yellow, above tube capitals reading exactly FRYER OPEN.", None),
 ("neon", "hotel_arrow", "The sign is a tall vertical hotel sign with an arrow of chasing bulbs pointing down into a doorway and the word ROOMS stacked vertically in green tube.", "1152x1536"),
 ("neon", "record_bar", "The sign is a record and a stylus arm drawn in pink and white tube, with script beneath reading exactly SPIN CITY and one letter dark where the tube has failed.", None),
 ("neon", "palm_motel", "The sign is two crossed palm trees in green tube over a pink sunset arc of three concentric tubes, above capitals reading exactly SEA BREEZE.", None),

 # ---- airbrush
 ("airbrush", "dragon_castle", "The mural shows a dragon circling a castle on a crag with a storm behind, sprayed in purples and greens with fine white lightning.", None),
 ("airbrush", "space_whale", "The mural shows a whale swimming through space past a ringed planet, the stars sprayed as fine speckle through a screen.", None),
 ("airbrush", "tiger_jungle", "The mural shows a tiger coming through jungle leaves toward the viewer, the leaves masked hard and the tiger sprayed soft.", None),
 ("airbrush", "biker_desert", "The mural shows a lone motorcyclist on a desert highway with mesas behind and a huge low sun, sprayed in oranges and browns.", None),
 ("airbrush", "mermaid_wreck", "The mural shows a mermaid sitting on the rail of a sunken ship with shafts of light coming down through green water.", None),
 ("airbrush", "phoenix_flames", "The mural shows a phoenix rising with its wings spread, the flames sprayed in four graded colours with hard-masked feather edges.", None),

 # ---- shadowpuppet
 ("shadowpuppet", "court_scene", "The performance shows a seated king figure on a raised throne with two attendants standing behind and a kneeling messenger in front, all in profile.", None),
 ("shadowpuppet", "tiger_hunt", "The performance shows a tiger crouched to spring at two hunters with spears, the tiger's stripes cut as long slots through the hide.", None),
 ("shadowpuppet", "wedding_procession", "The performance shows a wedding procession of six figures carrying umbrellas and offerings, moving right to left across the screen.", None),
 ("shadowpuppet", "storm_at_sea", "The performance shows a boat tipping on a cut band of waves with two figures clinging to the mast and a cloud figure blowing from the top corner.", None),
 ("shadowpuppet", "garuda_and_snake", "The performance shows a great winged figure with a beaked mask gripping a coiling serpent, filling the whole screen.", None),
 ("shadowpuppet", "farmer_and_buffalo", "The performance shows a farmer walking behind a water buffalo pulling a plough, with three cut rice stalks in the foreground.", None),

 # ---- papercut
 ("papercut", "mountain_train", "The diorama shows a train crossing a viaduct with mountain ridges stepping back behind it in five layers and a pine forest in the front layer.", None),
 ("papercut", "lighthouse_night", "The diorama shows a lighthouse on a headland with cut waves in three layers in front of it and a moon in the back layer.", None),
 ("papercut", "jungle_tiger", "The diorama shows a tiger between layers of cut leaves, half hidden by the front layer, with a shaft of light cut through the back layer.", None),
 ("papercut", "cathedral_nave", "The diorama shows the nave of a cathedral in six receding arch layers with a rose window cut in the furthest one.", None),
 ("papercut", "fox_and_moon", "The diorama shows a fox on a hilltop against a full moon, with layers of grass and a bare tree in front of it.", None),
 ("papercut", "harbour_boats", "The diorama shows a harbour with three boats at different depths, a quay wall in the front layer and a row of houses in the back layer.", None),
]


# -*- coding: utf-8 -*-
"""Corpus part C: the typography lane and the hex lane.

TYPO entries carry `strings`: the exact text that must appear, verbatim. That list is not
decoration - it is the pass/fail criterion, and it goes in the ledger and on the card so a
viewer can check the claim rather than take it.

HEX entries carry `asked`: {region: "#RRGGBB"}. After the render the tool samples the PNG
at that region and writes what it actually GOT next to what was asked. Nothing else on
this box takes a hex code at all, so this lane is the whole argument in one number.
"""

TYPO = [
 ("shop_ironmonger", "1536x1024",
  "A photograph of a hand-painted wooden shop fascia above an ironmonger's window on a wet "
  "street. The board is deep maroon and the lettering is cream with a fine gold shadow. The "
  "main line reads exactly HOLLIS & DAUGHTER. Beneath it a smaller line in capitals reads "
  "exactly IRONMONGERS - ESTABLISHED 1888. In the window below, a small enamel plate reads "
  "exactly KEYS CUT WHILE YOU WAIT. The paint is chipped along the bottom edge and the "
  "brickwork above is soot-blackened. Late afternoon light from the left, 50mm at f4, "
  "natural colour, fine grain.",
  ["HOLLIS & DAUGHTER", "IRONMONGERS - ESTABLISHED 1888", "KEYS CUT WHILE YOU WAIT"]),

 ("book_spines", "1024x1536",
  "A close photograph of five hardback books standing on a shelf, shot square on so only "
  "their spines show, filling the frame. From left to right the spines read exactly THE "
  "SALT ROADS, exactly A HISTORY OF RUST, exactly NIGHTJAR, exactly TWELVE BRIDGES, and "
  "exactly THE LONG FIELD. Each is a different cloth colour with the title stamped in gold "
  "or blind. The cloth is rubbed at the head and tail of each spine. Soft window light from "
  "the left, 85mm at f4, natural colour.",
  ["THE SALT ROADS", "A HISTORY OF RUST", "NIGHTJAR", "TWELVE BRIDGES", "THE LONG FIELD"]),

 ("enamel_platform", "1536x1024",
  "A photograph of a vitreous enamel railway station sign bolted to a brick wall on a "
  "platform. The sign is dark blue with white sans-serif capitals that read exactly "
  "WHITMORE HALT. A smaller enamel plate below it reads exactly ALIGHT HERE FOR THE FERRY. "
  "The enamel is chipped to black metal around two of the bolt holes and has rusted at the "
  "bottom edge. Overcast daylight, 50mm at f5.6, natural colour.",
  ["WHITMORE HALT", "ALIGHT HERE FOR THE FERRY"]),

 ("market_chalkboard", "1152x1536",
  "A photograph of a chalkboard propped outside a greengrocer's, shot square on. Written in "
  "white chalk in a confident signwriter's hand, the top line reads exactly BRAMLEY APPLES. "
  "Below it a larger line reads exactly 2 KILO FOR 3. At the bottom a smaller line reads "
  "exactly ASK ME ABOUT THE PLUMS. There is a drawn apple in one corner and chalk dust in "
  "the tray. Flat daylight, 50mm at f4, natural colour.",
  ["BRAMLEY APPLES", "2 KILO FOR 3", "ASK ME ABOUT THE PLUMS"]),

 ("jam_label", "1024x1536",
  "A close photograph of a glass jar of dark jam with a paper label gummed to the front, "
  "shot square on. The label has a printed border of small strawberries and hand-lettered "
  "text that reads exactly GREENGAGE & VANILLA on the first line and exactly MADE 14 "
  "AUGUST on the second. A small circle of gingham cloth is tied over the lid with string. "
  "Soft window light from the right, 100mm macro at f5.6, natural colour.",
  ["GREENGAGE & VANILLA", "MADE 14 AUGUST"]),

 ("boxing_poster", "1024x1536",
  "A photograph of a boxing bill pasted to a hoarding, shot square on. The type is stacked "
  "in six sizes of condensed wood letter. The top line reads exactly TWELVE ROUNDS. The "
  "largest line reads exactly KEANE v ABARA. Below that a line reads exactly THE DRILL "
  "HALL - SATURDAY 9PM, and at the foot in small capitals exactly DOORS SEVEN - NO "
  "ADMISSION AFTER THE THIRD. The paper is wrinkled where it was pasted and torn at one "
  "corner. Overcast daylight, 35mm at f5.6, natural colour.",
  ["TWELVE ROUNDS", "KEANE v ABARA", "THE DRILL HALL - SATURDAY 9PM",
   "DOORS SEVEN - NO ADMISSION AFTER THE THIRD"]),

 ("bus_blind", "1536x1024",
  "A close photograph of the destination blind in the front window of an old bus, shot "
  "square on and filling the frame. White capitals on black canvas read exactly 27 "
  "CASTLEGATE on the main line and beneath it in smaller capitals exactly VIA THE "
  "INFIRMARY. The canvas has a horizontal crease and the glass in front of it is dusty. "
  "Overcast daylight with a faint reflection of the street in the glass, 85mm at f4.",
  ["27 CASTLEGATE", "VIA THE INFIRMARY"]),

 ("seed_packets_three", "1536x1024",
  "A photograph of three paper seed packets laid side by side on a potting bench, shot "
  "straight down from above. Each has a small botanical illustration and a name. The left "
  "one reads exactly SCARLET RUNNER. The middle one reads exactly WINTER SAVORY. The right "
  "one reads exactly BLACK RADISH. Along the bottom of all three runs the same small line "
  "that reads exactly SOW THINLY. Soil and a pencil lie on the bench. Flat soft daylight, "
  "60mm at f8, natural colour.",
  ["SCARLET RUNNER", "WINTER SAVORY", "BLACK RADISH", "SOW THINLY"]),

 ("tattoo_flash", "1024x1536",
  "A photograph of a sheet of traditional tattoo flash pinned to a shop wall, shot square "
  "on. A swallow, an anchor and a dagger through a heart are drawn in heavy black outline "
  "with flat red and green fill. A banner across the anchor reads exactly HOLD FAST. A "
  "banner under the swallow reads exactly HOMEWARD. A banner across the dagger reads "
  "exactly NO REGRETS. The paper has yellowed and the drawing pins have rusted. Warm "
  "tungsten light, 50mm at f4, natural colour.",
  ["HOLD FAST", "HOMEWARD", "NO REGRETS"]),

 ("cinema_marquee", "1536x1024",
  "A night photograph of a cinema marquee with plastic changeable letters on three lit "
  "tracks. The top line reads exactly THE WEATHER HOUSE. The middle line reads exactly LAST "
  "TWO NIGHTS. The bottom line reads exactly SEATS FROM SIX. One letter on the middle line "
  "is slightly crooked and one bulb in the border has failed. Wet pavement below reflecting "
  "the light, 35mm at f2.8, natural colour.",
  ["THE WEATHER HOUSE", "LAST TWO NIGHTS", "SEATS FROM SIX"]),

 ("luggage_tag", "1536x1024",
  "A close photograph of a buff card luggage tag tied with string to the handle of a "
  "battered leather suitcase, shot from above. The tag is filled in by hand in fountain "
  "pen. The top line reads exactly M. OKONKWO. The next line reads exactly HOLD - NOT "
  "WANTED ON VOYAGE. A rubber stamp across the corner reads exactly LIVERPOOL. The card is "
  "scuffed and the ink has feathered slightly. Soft window light, 100mm macro at f5.6.",
  ["M. OKONKWO", "HOLD - NOT WANTED ON VOYAGE", "LIVERPOOL"]),

 ("scoreboard", "1536x1024",
  "A photograph of a hand-operated cricket scoreboard at a village ground, shot square on. "
  "White painted numbers hang on hooks. The panel labels are painted on the black board and "
  "read exactly TOTAL, exactly WICKETS, exactly LAST MAN and exactly OVERS, each with a "
  "number beside it. Along the top of the board a painted line reads exactly BRAMPTON C.C. "
  "The paint is flaking and the board is streaked with rain. Overcast daylight, 85mm at f4.",
  ["TOTAL", "WICKETS", "LAST MAN", "OVERS", "BRAMPTON C.C."]),

 ("wine_label", "1024x1536",
  "A close photograph of a wine bottle shot square on so the label fills the frame. The "
  "label is cream with a fine engraved line drawing of a hillside and black type. The top "
  "line reads exactly DOMAINE DE LA PIERRE FROIDE. Below it exactly VIEILLES VIGNES. At the "
  "foot in small capitals exactly MIS EN BOUTEILLE AU DOMAINE. The paper is slightly "
  "wrinkled from cellar damp. Soft light from the left, 100mm at f5.6, natural colour.",
  ["DOMAINE DE LA PIERRE FROIDE", "VIEILLES VIGNES", "MIS EN BOUTEILLE AU DOMAINE"]),

 ("fire_extinguisher_plate", "1024x1536",
  "A close photograph of the instruction plate on an old brass fire extinguisher mounted on "
  "a wall, shot square on. The engraved plate reads exactly IN CASE OF FIRE on the first "
  "line, exactly STRIKE KNOB SMARTLY on the second, and exactly DIRECT JET AT BASE OF FLAME "
  "on the third. The brass is polished bright in the middle and tarnished at the edges. "
  "Warm side light, 100mm macro at f8, natural colour.",
  ["IN CASE OF FIRE", "STRIKE KNOB SMARTLY", "DIRECT JET AT BASE OF FLAME"]),

 ("newspaper_front", "1152x1536",
  "A photograph of a newspaper lying folded on a kitchen table, shot from above so the top "
  "half of the front page fills the frame. The masthead reads exactly THE EVENING TIDE. The "
  "main headline in heavy capitals reads exactly BRIDGE OPENS AFTER NINE YEARS. A "
  "subheading beneath it reads exactly Traffic expected from Monday. A photograph sits "
  "below with a caption. The paper is creased along the fold and a coffee cup has left a "
  "ring on one corner. Flat morning light, 35mm at f5.6, natural colour.",
  ["THE EVENING TIDE", "BRIDGE OPENS AFTER NINE YEARS", "Traffic expected from Monday"]),

 ("matchbook", "1536x1024",
  "A close photograph of an open matchbook lying on a dark bar top, shot straight down. The "
  "inside of the cover is printed in two colours and reads exactly THE BLUE WHISTLE on the "
  "first line and exactly OPEN TILL LATE on the second, with a small drawing of a bird. "
  "Written across it in blue ballpoint in a rushed hand is exactly ASK FOR DANNY. Three "
  "matches have been torn out. Warm low light, 100mm macro at f4, natural colour.",
  ["THE BLUE WHISTLE", "OPEN TILL LATE", "ASK FOR DANNY"]),

 ("gravestone", "1024x1536",
  "A photograph of a weathered slate headstone in a churchyard, shot square on. The "
  "lettering is cut in a fine serif face and reads on successive lines exactly SACRED TO "
  "THE MEMORY OF, exactly ELIZABETH HARROW, exactly WHO DIED 3RD MARCH 1871, and at the "
  "foot exactly SHE KEPT THE LIGHT. Lichen has grown in the cut letters and the stone is "
  "streaked with rain. Soft overcast light raking from the left so the cut letters read, "
  "85mm at f5.6, natural colour.",
  ["SACRED TO THE MEMORY OF", "ELIZABETH HARROW", "WHO DIED 3RD MARCH 1871",
   "SHE KEPT THE LIGHT"]),

 ("arcade_cabinet", "1024x1536",
  "A photograph of the side art and control panel of an arcade cabinet in a dark arcade. "
  "The marquee above the screen is backlit and reads exactly ASTRO SALVAGE. A printed "
  "instruction strip on the control panel reads exactly 1 PLAYER START and exactly 2 PLAYER "
  "START beside two lit buttons, and a small warning below reads exactly INSERT COIN TO "
  "CONTINUE. The perspex is scratched and there are cigarette burns on the panel edge. Dark "
  "room lit by the screen, 35mm at f2.8, natural colour.",
  ["ASTRO SALVAGE", "1 PLAYER START", "2 PLAYER START", "INSERT COIN TO CONTINUE"]),

 ("apothecary_jars", "1536x1024",
  "A photograph of four glass apothecary jars on a shelf, shot square on, each with a gold "
  "and black glass label panel. From left to right the labels read exactly SAL AMMONIAC, "
  "exactly OIL OF CLOVES, exactly TINCT. MYRRH and exactly POT. NITRATE. The glass is "
  "uneven and the contents are different colours. Warm side light from the right, 85mm at "
  "f5.6, natural colour.",
  ["SAL AMMONIAC", "OIL OF CLOVES", "TINCT. MYRRH", "POT. NITRATE"]),

 ("protest_placard", "1024x1536",
  "A photograph of a hand-painted cardboard placard held up in a crowd, shot from below. "
  "The letters are painted in thick black emulsion by hand, getting smaller as they run out "
  "of room, and read exactly THE RIVER IS NOT A DRAIN on three lines. A smaller line "
  "underneath in a different hand reads exactly WE SWIM HERE. The card is bending under its "
  "own weight and the paint has run in two places. Bright overcast daylight, 35mm at f4.",
  ["THE RIVER IS NOT A DRAIN", "WE SWIM HERE"]),

 ("harbour_boat_name", "1536x1024",
  "A close photograph of the stern of a wooden fishing boat in a harbour, shot square on. "
  "The name is signwritten in white with a red shadow on the blue transom and reads exactly "
  "GANNET, with the port of registry beneath it in smaller letters reading exactly WK 114 "
  "WICK. The paint is blistered and there is weed along the waterline. Overcast daylight, "
  "50mm at f5.6, natural colour.",
  ["GANNET", "WK 114 WICK"]),

 ("typewriter_page", "1152x1536",
  "A close photograph of a sheet of paper in a manual typewriter, shot from above and "
  "slightly behind the carriage. Three typed lines are visible. The first reads exactly "
  "CHAPTER ONE. The second reads exactly The tide went out and did not come back. The third "
  "reads exactly For eleven days the harbour stood empty. The typing is uneven, some "
  "letters strike darker than others, and there is one struck-through word. Warm desk lamp "
  "light from the right, 50mm at f4, natural colour.",
  ["CHAPTER ONE", "The tide went out and did not come back",
   "For eleven days the harbour stood empty"]),

 ("van_livery", "1536x1024",
  "A photograph of the side of a cream 1960s delivery van parked at a kerb, shot square on. "
  "Signwritten in maroon with gold shading, the main line reads exactly DALE & SON. Beneath "
  "it in smaller script exactly FAMILY BAKERS SINCE 1931, and along the bottom edge in "
  "small capitals exactly TELEPHONE MARKET 2214. There is a small painted wheatsheaf "
  "between the lines. The paint has crazed and there is a dent below the door. Overcast "
  "daylight, 35mm at f5.6, natural colour.",
  ["DALE & SON", "FAMILY BAKERS SINCE 1931", "TELEPHONE MARKET 2214"]),

 ("museum_label", "1536x1024",
  "A close photograph of a printed museum object label on a plinth beside a small bronze, "
  "shot at a shallow angle. The label reads exactly BRONZE HARE on the first line, exactly "
  "Maker unknown, about 1780 on the second, and exactly Bequeathed by A. Sowerby, 1954 on "
  "the third, with an accession number at the foot reading exactly 1954.116. Museum "
  "spotlight from above, 100mm at f4, natural colour, dark background.",
  ["BRONZE HARE", "Maker unknown, about 1780", "Bequeathed by A. Sowerby, 1954", "1954.116"]),

 ("shipping_crate", "1536x1024",
  "A photograph of a wooden shipping crate on a dock, shot square on. Black stencilled "
  "letters are sprayed across the boards and read exactly PORT OF LEITH on the top line, "
  "exactly CASE 4 OF 9 on the second, and exactly THIS SIDE UP with a stencilled arrow on "
  "the third. The stencil edges have bled and one letter is half missing where the boards "
  "meet. Overcast daylight, 35mm at f5.6, natural colour.",
  ["PORT OF LEITH", "CASE 4 OF 9", "THIS SIDE UP"]),

 ("neon_typography", "1536x1024",
  "A night photograph of a neon sign on a wall made entirely of type. Three lines of bent "
  "glass tube spell out, on the top line in warm white script, exactly good morning, on the "
  "middle line in larger pink capitals exactly THE NIGHT IS OVER, and on the bottom line in "
  "small blue capitals exactly PLEASE COME IN. Every letter is one continuous tube with "
  "visible electrodes and standoffs, glowing onto the brick behind. 35mm at f2.8, long "
  "exposure, natural colour.",
  ["good morning", "THE NIGHT IS OVER", "PLEASE COME IN"]),

 ("recipe_card", "1152x1536",
  "A photograph of a stained handwritten recipe card on a kitchen counter, shot from above. "
  "In looping blue fountain pen the heading reads exactly Gran's Fruit Loaf. The ingredient "
  "lines beneath read exactly 8oz mixed fruit, exactly 6oz self raising flour and exactly a "
  "cup of cold tea. At the bottom in a different hand and a different pen it reads exactly "
  "do NOT skip the tea. There are butter stains on the card and one corner is torn. Soft "
  "window light, 50mm at f4, natural colour.",
  ["Gran's Fruit Loaf", "8oz mixed fruit", "6oz self raising flour", "a cup of cold tea",
   "do NOT skip the tea"]),

 ("lift_panel", "1024x1536",
  "A close photograph of the floor indicator and control panel inside an old lift, shot "
  "square on. Engraved brass plates beside the buttons read exactly LOWER GROUND, exactly "
  "GROUND, exactly MEZZANINE and exactly ROOF GARDEN. A separate plate below reads exactly "
  "MAXIMUM 8 PERSONS - 600 KG. The brass is worn bright around the most-used button. Warm "
  "interior light, 85mm at f4, natural colour.",
  ["LOWER GROUND", "GROUND", "MEZZANINE", "ROOF GARDEN", "MAXIMUM 8 PERSONS - 600 KG"]),

 ("bakery_window", "1536x1024",
  "A photograph of a bakery window with gold leaf lettering applied to the inside of the "
  "glass, shot from the street. The main arc of letters reads exactly PEMBERTON'S. Beneath "
  "it a straight line reads exactly BREAD - CAKES - PIES. On the door glass a smaller "
  "hand-lettered card reads exactly SORRY WE ARE CLOSED. Loaves are stacked on wooden "
  "shelves behind the glass and the street is faintly reflected in it. Morning light, 35mm "
  "at f4, natural colour.",
  ["PEMBERTON'S", "BREAD - CAKES - PIES", "SORRY WE ARE CLOSED"]),

 ("record_label", "1536x1536",
  "A close photograph of a seven inch vinyl record on a turntable, shot straight down so "
  "the paper centre label fills most of the frame. The label is orange with black type "
  "arranged in a circle and in the centre. The artist line reads exactly THE HARROW ROAD "
  "SET. The title line reads exactly Nothing Doing. Small type beneath reads exactly 45 RPM "
  "- SIDE A and exactly ORB 117. The label has a ring wear scuff and the vinyl grooves "
  "catch the light. Warm side light, 60mm macro at f5.6, natural colour.",
  ["THE HARROW ROAD SET", "Nothing Doing", "45 RPM - SIDE A", "ORB 117"]),
]


# --------------------------------------------------------------------------------- hex
# Two named hex codes per image, one for a large flat field and one for a shape at the
# centre, so both can be sampled off the PNG without ambiguity. No engine else on this box
# takes a hex code at all.
HEX = [
 ("hex_deepsea",   "#12303F", "#E8B04B", "a circle"),
 ("hex_moss",      "#2F4B26", "#F2E8CF", "a five-pointed star"),
 ("hex_oxblood",   "#6B2737", "#E0C9A6", "an equilateral triangle pointing up"),
 ("hex_slate",     "#3A4750", "#F26B38", "a square rotated forty-five degrees"),
 ("hex_ink",       "#151E3F", "#F5F5F5", "a crescent moon"),
 ("hex_terracotta","#B85042", "#E7E8D1", "a ring, an outlined circle with nothing inside it"),
 ("hex_pine",      "#1B3022", "#C6A15B", "a hexagon"),
 ("hex_plum",      "#4B2E39", "#9FD8CB", "a teardrop"),
 ("hex_sand",      "#D9C5A0", "#2B303A", "a solid black bar running horizontally"),
 ("hex_cobalt",    "#26547C", "#EF476F", "a heart"),
 ("hex_olive",     "#606C38", "#FEFAE0", "a semicircle, flat side down"),
 ("hex_charcoal",  "#22223B", "#F2E9E4", "a diamond"),
]



# =========================================================================== plumbing

def _api(path, payload=None, timeout=180):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request("http://%s%s" % (HOST, path), data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def load_wf(path):
    return {k: v for k, v in json.load(open(path)).items() if not k.startswith("_")}


def parse_size(s):
    w, _, h = s.lower().partition("x")
    return int(w), int(h)


def flux_wf(prompt, seed, steps, guidance, size, turbo):
    """40_flux2_t2i.json, patched.

    Flux2Scheduler and EmptyFlux2LatentImage MUST agree on size - the scheduler computes a
    resolution-dependent sigma schedule and a mismatch degrades the image silently with no
    error. Both are set from one place here for that reason.

    turbo=False rewires BasicGuider straight to the UNETLoader, so node 3 loses its only
    consumer and ComfyUI never executes the LoRA at all. It is a different graph, not a
    strength of zero.
    """
    wf = load_wf(WF_FLUX)
    w, h = size
    wf["6"]["inputs"]["text"] = prompt
    wf["7"]["inputs"]["guidance"] = float(guidance)
    wf["9"]["inputs"].update(steps=int(steps), width=w, height=h)
    wf["11"]["inputs"]["noise_seed"] = int(seed)
    wf["12"]["inputs"].update(width=w, height=h)
    wf["15"]["inputs"]["filename_prefix"] = "claude-generated/40-flux2/gallery"
    if not turbo:
        wf["8"]["inputs"]["model"] = ["1", 0]
    return wf


def qwen_wf(prompt, seed, size, steps=20, cfg=2.5):
    wf = load_wf(WF_QWEN)
    w, h = size
    wf["10"]["inputs"]["text"] = prompt
    wf["11"]["inputs"]["text"] = QWEN_NEG
    wf["12"]["inputs"].update(width=w, height=h)
    wf["13"]["inputs"].update(seed=int(seed), steps=int(steps), cfg=float(cfg))
    wf["15"]["inputs"]["filename_prefix"] = "claude-generated/40-flux2/gallery_qwen"
    return wf


def sdxl_wf(prompt, seed, size, ckpt="animagine-xl-4.0.safetensors"):
    """A plain SDXL text-to-image graph, built here rather than added to workflows/.

    There is no t2i workflow for the anime checkpoint in this repo - 21_sdxl_anime_restyle
    is image-to-image. The A/B needs one, and this tool does not own workflows/, so the
    graph is constructed in memory. It is the standard SDXL path at the card's settings.
    """
    w, h = size
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ckpt}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": prompt}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1],
              "text": "lowres, worst quality, jpeg artifacts, watermark, signature"}},
        "4": {"class_type": "EmptyLatentImage",
              "inputs": {"width": w, "height": h, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {
              "model": ["1", 0], "positive": ["5", 0], "negative": ["6", 0],
              "latent_image": ["4", 0], "seed": int(seed), "steps": 28, "cfg": 5.5,
              "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["1", 2]}},
        "15": {"class_type": "SaveImage", "inputs": {"images": ["8", 0],
               "filename_prefix": "claude-generated/40-flux2/gallery_sdxl"}},
    }


def ledger_append(rows):
    os.makedirs(GAL, exist_ok=True)
    have = []
    if os.path.exists(LEDGER):
        try:
            have = json.load(open(LEDGER))
        except ValueError:
            have = []
    have.extend(rows)
    with open(LEDGER, "w") as f:
        json.dump(have, f, indent=1)
        f.write("\n")


def build_prompt(medium, subject):
    m = MEDIA[medium]
    return " ".join(x.strip() for x in (m["lead"], subject, m["tell"], m["finish"]))


# ---------------------------------------------------------------- submit / yield / drain

def foreign_in_queue(ours):
    """prompt ids in the ComfyUI queue that this tool did not submit.

    The box is shared and a film is being rendered on it. Anything in the queue that is
    not ours is somebody else's job and we get out of its way.
    """
    try:
        q = _api("/queue", timeout=20)
    except Exception:
        return 0
    n = 0
    for key in ("queue_running", "queue_pending"):
        for item in q.get(key) or []:
            try:
                pid = item[1]
            except Exception:
                continue
            if pid not in ours:
                n += 1
    return n


def wait_for_others(ours, cap, note=""):
    """Wait for the queue to clear of other people's work, but not forever.

    MEASURED ON THIS BOX WHILE THE FILM WAS RENDERING: the film agent submits ONE job at a
    time and its jobs take 2.7-7.8 s (SDXL keyframes through IPAdapter, and IndexTTS
    lines). It is not batching, so the queue is never empty for long and an uncapped wait
    means this gallery renders nothing at all in eight hours.

    So: yield first, always, and yield hard - but after `cap` seconds take a turn. With a
    small --chunk the film never waits behind more than a couple of our frames, and it
    gets the box back immediately afterwards. Set --yield-cap 0 to defer completely.
    """
    n = foreign_in_queue(ours)
    if not n:
        return 0
    print("  YIELDING: %d foreign job(s) in the queue%s." % (n, note), flush=True)
    waited = 0
    while n:
        if cap and waited >= cap:
            print("  yield cap %ds reached, taking a turn (%d foreign job(s) still queued)."
                  % (cap, n), flush=True)
            return waited
        time.sleep(10)
        waited += 10
        n = foreign_in_queue(ours)
        if waited % 300 == 0:
            print("    still yielding after %ds, %d foreign job(s)" % (waited, n), flush=True)
    print("  queue clear after %ds, resuming." % waited, flush=True)
    return waited


def run_cells(cells, chunk=8, label="cells", yield_cap=240):
    """cells: dicts of wf/dest/slug/recipe. Submit in chunks, yield between them, drain.

    Chunked rather than all-up-front on purpose. All-up-front is cheapest (one model load)
    but it parks N of our jobs in front of anyone else's. Chunked costs nothing extra here
    - ComfyUI keeps the model resident between our chunks because nothing else evicted it -
    and it caps how long a foreign job can wait at one chunk.
    """
    if os.environ.get("GAL_NO_RESUME") != "1":
        # Skip anything already on disk. Two reasons this matters more than usual here:
        # a restart must not re-pay the 34 GB FLUX.2 load for work already done, and on a
        # SHARED box every avoidable render is a model eviction inflicted on someone else.
        before = len(cells)
        gone = _dropped_slugs()
        cells = [c for c in cells
                 if c["slug"] not in gone
                 and not os.path.exists(os.path.join(c["dest"], c["slug"] + ".png"))]
        if before != len(cells):
            print("  resume: %d of %d already rendered, %d to go"
                  % (before - len(cells), before, len(cells)), flush=True)
    ours, done, flushed = set(), [], []
    total, i = len(cells), 0
    t_start = time.time()
    if not total:
        return []
    while i < total:
        wait_for_others(ours, yield_cap, " before chunk %d" % (i // chunk + 1))
        batch, pending = cells[i:i + chunk], {}
        for c in batch:
            try:
                pid = _api("/prompt", {"prompt": c["wf"],
                                       "client_id": "flux2_gallery"})["prompt_id"]
            except Exception as e:
                print("  !! submit failed %s: %s" % (c["slug"], e), flush=True)
                continue
            ours.add(pid)
            pending[pid] = c
        i += chunk
        while pending:
            time.sleep(5)
            try:
                hist = _api("/history?max_items=400")
            except Exception:
                continue
            for pid in list(pending):
                e = hist.get(pid)
                if not e:
                    continue
                st = e.get("status", {})
                if not (st.get("completed") or st.get("status_str") == "error"):
                    continue
                c = pending.pop(pid)
                outs = ["%s/%s" % (f.get("subfolder", ""), f["filename"])
                        for o in e.get("outputs", {}).values() for f in o.get("images", [])]
                outs = [o.lstrip("/") for o in outs]
                local = None
                if outs:
                    src = os.path.join(COMFY_OUT, outs[0])
                    if os.path.exists(src):
                        os.makedirs(c["dest"], exist_ok=True)
                        local = os.path.join(c["dest"], c["slug"] + ".png")
                        shutil.copyfile(src, local)
                row = dict(c["recipe"])
                row["file"] = os.path.relpath(local, ROOT) if local else None
                t0 = t1 = None
                for m in st.get("messages", []):
                    if m[0] == "execution_start":
                        t0 = m[1].get("timestamp")
                    elif m[0] in ("execution_success", "execution_error"):
                        t1 = m[1].get("timestamp")
                if t0 and t1:
                    row["seconds"] = round((t1 - t0) / 1000.0, 1)
                if local:
                    with open(os.path.splitext(local)[0] + ".json", "w") as f:
                        json.dump(row, f, indent=1)
                        f.write("\n")
                else:
                    row["error"] = "no image output"
                    print("  !! no output: %s" % c["slug"], flush=True)
                done.append(row)
        # Flush the ledger every chunk, not at the end. A run of 140 cells on a shared box
        # can be killed and restarted; the per-image sidecars survive that, and the ledger
        # should too.
        ledger_append(done[len(flushed):])
        flushed = list(done)
        el = time.time() - t_start
        n = len(done)
        print("  [%5.0fs] %s %d/%d  (%.0fs/img)" % (el, label, n, total, el / max(n, 1)),
              flush=True)
    return done


# --------------------------------------------------------------------------- recipes

def recipe(slug, lane, prompt, size, engine="flux2", steps=None, guidance=None,
           turbo=None, seed=None, **extra):
    steps = STEPS if steps is None else steps
    guidance = GUIDANCE if guidance is None else guidance
    turbo = TURBO if turbo is None else turbo
    seed = SEED if seed is None else seed
    if engine == "flux2":
        r = dict(
            slug=slug, lane=lane, engine="flux2",
            checkpoint="flux2_dev_fp8mixed.safetensors",
            text_encoder="mistral_3_small_flux2_fp8.safetensors (CLIPLoader type=flux2)",
            vae="flux2-vae.safetensors",
            lora=("Flux2TurboComfyv2.safetensors @ 1.0" if turbo else "none"),
            turbo=turbo, workflow="workflows/40_flux2_t2i.json",
            prompt=prompt, negative_prompt=None,
            seed=seed, steps=steps, guidance=guidance,
            sampler="euler", scheduler="Flux2Scheduler", size=size)
    elif engine == "qwen":
        r = dict(
            slug=slug, lane=lane, engine="qwen",
            checkpoint="qwen_image_2512_fp8_e4m3fn.safetensors",
            lora="none", workflow="workflows/02_qwen_t2i_quality.json",
            prompt=prompt, negative_prompt=QWEN_NEG,
            seed=seed, steps=20, cfg=2.5, size=size)
    else:
        r = dict(
            slug=slug, lane=lane, engine="sdxl",
            checkpoint="animagine-xl-4.0.safetensors",
            lora="none", workflow="in-memory SDXL t2i (see sdxl_wf in this tool)",
            prompt=prompt,
            negative_prompt="lowres, worst quality, jpeg artifacts, watermark, signature",
            seed=seed, steps=28, cfg=5.5, sampler="dpmpp_2m", scheduler="karras", size=size)
    r.update(extra)
    return r


# =============================================================================== modes

CALIBRATE_MEDIA = ["watercolour", "benday", "woodcut", "embroidery",
                   "plasticine", "ps1", "impasto", "stainedglass"]


def _first_subjects():
    d = {}
    for (m, sl, s, z) in WAVE1:
        d.setdefault(m, (sl, s, z))
    return d


def mode_calibrate(a):
    """The one question the checkpoint card got wrong.

    The card concluded hand-media is a FLUX.2 weakness from a single rendered pair, run
    through the Turbo distill LoRA - and the same card says Turbo degrades fine repeating
    structure specifically. Paper tooth is fine repeating structure. Same prompt, same
    seed, both graphs, eight media. Decide from the pixels.
    """
    subj = _first_subjects()
    dest = os.path.join(GAL, "_calibrate")
    cells = []
    for m in CALIBRATE_MEDIA:
        sl, s, z = subj[m]
        p = build_prompt(m, s)
        size_s = z or MEDIA[m]["size"]
        for turbo, st, tag in ((True, 8, "turbo8"), (False, 20, "plain20")):
            slug = "%s__%s" % (m, tag)
            cells.append(dict(
                wf=flux_wf(p, a.seed, st, a.guidance, parse_size(size_s), turbo),
                dest=dest, slug=slug,
                recipe=recipe(slug, "calibrate", p, size_s, steps=st, guidance=a.guidance,
                              turbo=turbo, seed=a.seed, medium=m,
                              medium_name=MEDIA[m]["name"])))
    print("calibrate: %d cells (%d media x turbo/no-turbo)"
          % (len(cells), len(CALIBRATE_MEDIA)), flush=True)
    run_cells(cells, a.chunk, "calibrate", a.yield_cap)


def mode_media(a):
    items = WAVE1 if a.wave == 1 else WAVE2
    if a.only:
        keep = set(x.strip() for x in a.only.split(","))
        items = [i for i in items if i[0] in keep]
    cells = []
    for medium, slug, subject, size_over in items:
        size_s = size_over or MEDIA[medium]["size"]
        p = build_prompt(medium, subject)
        cells.append(dict(
            wf=flux_wf(p, a.seed, a.steps, a.guidance, parse_size(size_s), a.turbo),
            dest=os.path.join(GAL, medium), slug=slug,
            recipe=recipe(slug, "media", p, size_s, steps=a.steps, guidance=a.guidance,
                          turbo=a.turbo, seed=a.seed, medium=medium,
                          medium_name=MEDIA[medium]["name"],
                          medium_blurb=MEDIA[medium]["blurb"],
                          subject=subject, wave=a.wave)))
    print("media wave %d: %d cells across %d media"
          % (a.wave, len(cells), len(set(c["recipe"]["medium"] for c in cells))), flush=True)
    run_cells(cells, a.chunk, "media", a.yield_cap)


def mode_typo(a):
    dest = os.path.join(GAL, "typography")
    cells = []
    for slug, size_s, prompt, strings in TYPO:
        cells.append(dict(
            wf=flux_wf(prompt, a.seed, a.steps, a.guidance, parse_size(size_s), a.turbo),
            dest=dest, slug=slug,
            recipe=recipe(slug, "typography", prompt, size_s, steps=a.steps,
                          guidance=a.guidance, turbo=a.turbo, seed=a.seed,
                          strings_asked=strings)))
    print("typography: %d cells" % len(cells), flush=True)
    run_cells(cells, a.chunk, "typo", a.yield_cap)


HEX_PROMPT = (
    "A flat graphic design poster, shot straight on so the whole sheet fills the frame with "
    "nothing else visible. The background is one completely flat field of the colour %s, "
    "edge to edge, with no gradient, no texture and no vignette anywhere in it. Centred on "
    "that field is %s, filling about one third of the frame height, in one completely flat "
    "field of the colour %s. There is nothing else in the picture: no text, no border, no "
    "shadow, no highlight and no paper texture. Both colours are exact."
)


def sample_hex(path, asked=None):
    """Read the two flat colours back off the rendered PNG.

    THIS TOOL GOT THIS WRONG TWICE AND BOTH WRONG VERSIONS PRODUCED CONFIDENT NUMBERS.
    Written down because the numbers are the whole point of this lane:

      v1 sampled a patch at dead centre for the shape. Correct for a disc, nonsense for a
      crescent moon and a ring - both have BACKGROUND at their centre. It reported a
      239/255 error on the crescent, which was the tool measuring the background twice.

      v2 took the two largest colour clusters. Also wrong: the shape covers well under a
      tenth of the frame, so the second-largest cluster is a shading variant of the
      background, not the shape. It made nine of twelve readings worse.

      v3, below, assumes only what is actually guaranteed by the prompt: the background
      touches the border, and the shape is whatever is LEAST LIKE the background. Sample
      the border ring for the background, then take the median of the most
      background-unlike decile of pixels for the shape. Works for a ring, a crescent, a
      bar and a star alike, and does not need to know where the shape is.
    """
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im.thumbnail((400, 400))
    w, h = im.size
    px = im.load()

    def med(vals):
        out = []
        for i in range(3):
            v = sorted(c[i] for c in vals)
            out.append(v[len(v) // 2])
        return tuple(out)

    inset = max(3, min(w, h) // 60)
    ring = ([px[x, inset] for x in range(inset, w - inset)] +
            [px[x, h - inset - 1] for x in range(inset, w - inset)] +
            [px[inset, y] for y in range(inset, h - inset)] +
            [px[w - inset - 1, y] for y in range(inset, h - inset)])
    bg = med(ring)

    inner = [px[x, y] for y in range(4, h - 4, 2) for x in range(4, w - 4, 2)]
    dist = sorted(((sum((a - b) ** 2 for a, b in zip(c, bg)), c) for c in inner),
                  key=lambda t: -t[0])
    # THRESHOLD, NOT RANK. A fixed top-decile fails when the shape is small: the crescent
    # covers about three per cent of the frame, so a decile is nine parts background and
    # the median of it comes back as the background. Keying off the FARTHEST pixel instead
    # adapts to any shape size - keep only pixels more than half as far from the background
    # as the farthest one is, which on a clean two-colour poster is exactly the shape.
    dmax = dist[0][0]
    core = [c for d, c in dist if d > dmax * 0.5]
    # Drop the leading few - those are antialiased rim pixels, a blend of the two colours.
    core = core[len(core) // 10:] or [dist[0][1]]
    return bg, med(core)


def hexstr(t):
    return "#%02X%02X%02X" % t


def hexval(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def mode_hex(a):
    """Render the swatches and read the colours back.

    --suffix runs the same twelve asks into a separate folder, which is how the guidance
    sweep is done: guidance is the one knob the checkpoint card says "tightens adherence",
    so whether it tightens COLOUR adherence is a question the pixels can answer.
    """
    dest = os.path.join(GAL, "hex" + (a.suffix or ""))
    cells = []
    for slug, bg, fg, shape in HEX:
        p = HEX_PROMPT % (bg, shape, fg)
        cells.append(dict(
            wf=flux_wf(p, a.seed, a.steps, a.guidance, (1024, 1024), a.turbo),
            dest=dest, slug=slug,
            recipe=recipe(slug, "hex", p, "1024x1024", steps=a.steps, guidance=a.guidance,
                          turbo=a.turbo, seed=a.seed,
                          asked={"background": bg, "shape": fg}, shape=shape)))
    print("hex: %d cells" % len(cells), flush=True)
    rows = run_cells(cells, a.chunk, "hex", a.yield_cap)
    measure_hex(rows)


def measure_hex(rows):
    """Read the colours back off the PNGs and write the error down next to the ask."""
    out = []
    for r in rows:
        if not r.get("file"):
            continue
        p = os.path.join(ROOT, r["file"])
        try:
            bg, fg = sample_hex(p, r.get("asked"))
        except Exception as e:
            print("  !! sample failed %s: %s" % (r["slug"], e), flush=True)
            continue
        got = {"background": hexstr(bg), "shape": hexstr(fg)}
        err = {}
        for k in ("background", "shape"):
            want, have = hexval(r["asked"][k]), hexval(got[k])
            per = [abs(x - y) for x, y in zip(want, have)]
            err[k] = {"per_channel": per, "max_channel": max(per),
                      "pct_of_255": round(100.0 * max(per) / 255, 1)}
        r["got"], r["error"] = got, err
        with open(os.path.splitext(p)[0] + ".json", "w") as f:
            json.dump(r, f, indent=1)
            f.write("\n")
        out.append(r)
        print("  %-16s bg %s -> %s (max %2d)   shape %s -> %s (max %2d)"
              % (r["slug"], r["asked"]["background"], got["background"],
                 err["background"]["max_channel"], r["asked"]["shape"], got["shape"],
                 err["shape"]["max_channel"]), flush=True)
    mdir = os.path.dirname(os.path.join(ROOT, out[0]["file"])) if out else         os.path.join(GAL, "hex")
    with open(os.path.join(mdir, "_measured.json"), "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    if out:
        allmax = sorted(e["error"][k]["max_channel"]
                        for e in out for k in ("background", "shape"))
        print("\n  %d swatches, %d readings. max channel error: median %d/255, worst %d/255"
              % (len(out), len(allmax), allmax[len(allmax) // 2], allmax[-1]), flush=True)


AB_PICKS = ["watercolour", "benday", "ps1", "woodcut", "embroidery", "plasticine",
            "stainedglass", "letterpress"]


def mode_ab(a):
    """Same prompt, same seed, same frame, three engines.

    All FLUX cells first, then all Qwen, then all SDXL - deliberately, not by accident of
    loop order. 34 GB of DiT plus a 16.8 GB encoder does not co-reside with the others on
    a 32 GB card, and an interleaved order costs a 60-150 s model reload per switch.
    """
    subj = _first_subjects()
    dest = os.path.join(GAL, "_ab")
    for eng in ("flux2", "qwen", "sdxl"):
        cells = []
        for m in AB_PICKS:
            sl, subject, z = subj[m]
            size_s = z or MEDIA[m]["size"]
            size = parse_size(size_s)
            p = build_prompt(m, subject)
            slug = "%s__%s" % (m, eng)
            if eng == "flux2":
                wf = flux_wf(p, a.seed, a.steps, a.guidance, size, a.turbo)
            elif eng == "qwen":
                wf = qwen_wf(p, a.seed, size)
            else:
                wf = sdxl_wf(p, a.seed, size)
            cells.append(dict(wf=wf, dest=dest, slug=slug,
                              recipe=recipe(slug, "ab", p, size_s, engine=eng,
                                            steps=a.steps, guidance=a.guidance,
                                            turbo=a.turbo, seed=a.seed, medium=m,
                                            medium_name=MEDIA[m]["name"])))
        print("ab: %s, %d cells" % (eng, len(cells)), flush=True)
        run_cells(cells, a.chunk, "ab-" + eng, a.yield_cap)


# ------------------------------------------------------------------------ contact sheets

def _sheet(paths, out, cols, cell, label=True):
    if not paths:
        return False
    cmd = ["montage"]
    if label:
        cmd += ["-label", "%t"]
    cmd += paths + ["-tile", "%dx" % cols, "-geometry", "%dx%d+6+6" % (cell, cell),
                    "-background", "#141414", "-fill", "#dddddd", "-pointsize", "17",
                    "-quality", "88", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print("  montage failed: %s" % r.stderr[:300], flush=True)
        return False
    return True


def mode_sheets(a):
    os.makedirs(os.path.join(GAL, "_sheets"), exist_ok=True)
    made = 0
    dirs = sorted(d for d in os.listdir(GAL)
                  if os.path.isdir(os.path.join(GAL, d)) and d != "_sheets")
    if a.only:
        keep = set(x.strip() for x in a.only.split(","))
        dirs = [d for d in dirs if d in keep]
    for d in dirs:
        pngs = sorted(os.path.join(GAL, d, f) for f in os.listdir(os.path.join(GAL, d))
                      if f.endswith(".png"))
        if not pngs:
            continue
        cols = a.cols or (2 if len(pngs) <= 4 else (3 if len(pngs) <= 9 else 4))
        out = os.path.join(GAL, "_sheets", "%s.jpg" % d)
        if _sheet(pngs, out, cols, a.cell):
            made += 1
            print("  %-16s %2d cells -> %s (%d KB)"
                  % (d, len(pngs), out, os.path.getsize(out) // 1024), flush=True)
    print("\n%d sheets" % made, flush=True)


# ----------------------------------------------------------------------------- curation

def _dropped_slugs():
    if not os.path.exists(DROPPED):
        return set()
    try:
        return {d["slug"] for d in json.load(open(DROPPED))}
    except Exception:
        return set()


def mode_drop(a):
    """Record a rejection.

    Moves the PNG and its recipe into _dropped/ and writes down WHY. Dropping is part of
    the work, not an embarrassment - the kept-over-rendered ratio is the honest number
    this gallery reports, and it can only be honest if the rejects are written down with
    a reason instead of quietly deleted.
    """
    if not a.slugs:
        print("--slugs required", file=sys.stderr)
        return 2
    reason = a.reason or "did not read as the medium"
    dd = os.path.join(GAL, "_dropped")
    os.makedirs(dd, exist_ok=True)
    have = []
    if os.path.exists(DROPPED):
        try:
            have = json.load(open(DROPPED))
        except ValueError:
            have = []
    moved = 0
    for slug in [s.strip() for s in a.slugs.split(",") if s.strip()]:
        hit = None
        for d in sorted(os.listdir(GAL)):
            p = os.path.join(GAL, d, slug + ".png")
            if os.path.isfile(p):
                hit = p
                break
        if not hit:
            print("  not found: %s" % slug, flush=True)
            continue
        rec, side = {}, os.path.splitext(hit)[0] + ".json"
        if os.path.exists(side):
            rec = json.load(open(side))
            shutil.move(side, os.path.join(dd, slug + ".json"))
        shutil.move(hit, os.path.join(dd, slug + ".png"))
        have.append({"slug": slug, "lane": rec.get("lane"), "medium": rec.get("medium"),
                     "reason": reason})
        moved += 1
    with open(DROPPED, "w") as f:
        json.dump(have, f, indent=1)
        f.write("\n")
    print("dropped %d (%s)" % (moved, reason), flush=True)


def mode_stats(a):
    kept, by_lane, by_folder = 0, {}, {}
    for d in sorted(os.listdir(GAL)):
        p = os.path.join(GAL, d)
        if not os.path.isdir(p) or d in ("_sheets", "_dropped"):
            continue
        n = len([f for f in os.listdir(p) if f.endswith(".png")])
        kept += n
        if n:
            by_folder[d] = n
    drops = json.load(open(DROPPED)) if os.path.exists(DROPPED) else []
    ledger = json.load(open(LEDGER)) if os.path.exists(LEDGER) else []
    for r in ledger:
        k = r.get("lane", "?")
        by_lane[k] = by_lane.get(k, 0) + 1
    print("rendered (ledger rows): %d" % len(ledger))
    print("kept on disk:           %d" % kept)
    print("dropped:                %d" % len(drops))
    if ledger:
        print("keep rate:              %.0f%%" % (100.0 * kept / len(ledger)))
    print("\nby lane (rendered):")
    for k in sorted(by_lane):
        print("  %-12s %d" % (k, by_lane[k]))
    print("\nby folder (kept):")
    for k in sorted(by_folder):
        print("  %-16s %d" % (k, by_folder[k]))


# -------------------------------------------------------------------------------- index

INDEX_CSS = """
:root{--bg:#0d0d0f;--fg:#e8e6e3;--dim:#8b8880;--line:#26262b;--accent:#d9a441}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,sans-serif}
header{padding:48px 32px 28px;border-bottom:1px solid var(--line);max-width:1180px;margin:0 auto}
h1{margin:0 0 12px;font-size:30px;letter-spacing:-.01em}
header p{margin:0 0 10px;color:var(--dim);max-width:74ch}
header b{color:var(--fg)}
nav{max-width:1180px;margin:0 auto;padding:16px 32px;font-size:13px;color:var(--dim)}
nav a{color:var(--accent);text-decoration:none;margin-right:14px;white-space:nowrap}
main{max-width:1180px;margin:0 auto;padding:0 32px 80px}
section{padding:36px 0;border-bottom:1px solid var(--line)}
h2{font-size:21px;margin:0 0 4px}
h2 small{color:var(--accent);font-weight:400;font-size:13px;margin-left:10px}
.blurb{color:var(--dim);margin:0 0 20px;max-width:74ch}
.grid{display:grid;gap:18px;grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
figure{margin:0;background:#151518;border:1px solid var(--line);border-radius:6px;overflow:hidden}
figure img{width:100%;display:block;background:#000}
figcaption{padding:10px 12px;font-size:12px;color:var(--dim)}
figcaption b{color:var(--fg);font-weight:600}
details{margin-top:8px}
summary{cursor:pointer;color:var(--accent);font-size:11.5px;letter-spacing:.04em;
 text-transform:uppercase}
pre{white-space:pre-wrap;word-break:break-word;
 font:11.5px/1.5 ui-monospace,Menlo,Consolas,monospace;
 color:#b9b6b0;background:#0a0a0c;padding:10px;border-radius:4px;margin:8px 0 0;
 max-height:340px;overflow:auto}
.sw{display:inline-block;width:15px;height:15px;border-radius:3px;vertical-align:-3px;
 margin-right:6px;border:1px solid #3a3a40}
.ok{color:#7ec97e}.bad{color:#e07a5f}
"""


def mode_index(a):
    """One browsable page. Every picture carries its whole recipe in a fold-out."""
    lanes = {}
    for d in sorted(os.listdir(GAL)):
        p = os.path.join(GAL, d)
        if not os.path.isdir(p) or d == "_sheets":
            continue
        recs = []
        for f in sorted(os.listdir(p)):
            if not f.endswith(".json") or f.startswith("_"):
                continue
            if not os.path.exists(os.path.join(p, f[:-5] + ".png")):
                continue
            try:
                recs.append(json.load(open(os.path.join(p, f))))
            except ValueError:
                pass
        if recs:
            lanes[d] = recs

    def esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Two media shipped only partially and their authored blurb overclaims what actually
    # landed. Saying so here is cheaper than pretending, and it is the difference between
    # a gallery and an advert.
    OVERRIDE = {
        "ps1": "PARTIAL, AND THE ONLY MEDIUM IN THIS GALLERY THAT DID NOT LAND. Two "
               "rewrites both failed to produce flat-shaded low-polygon geometry: FLUX.2 "
               "renders the photographic memory of a 1997 game - hard texels, aliasing, "
               "correct HUD, letter-perfect text box - but not faceted triangles or "
               "affine texture swim. Two of four cells were dropped and the medium was "
               "cut from the second wave. Kept as the honest negative result.",
        "gouache": "PARTIAL. The substrate reads - opaque, matte, no specular anywhere, "
                   "grey board showing at the edges - but three of four cells collapsed "
                   "toward greyscale and the brush chatter that separates gouache from "
                   "acrylic is faint. One cell dropped, cut from the second wave.",
        "crtpixel": "Hand-placed pixels, sixteen colours, dithered gradients, on CRT "
                    "glass. THESE SIX ARE THE SECOND VERSION. The first named the "
                    "aperture grille and its phosphor bars, and FLUX.2 drew them - "
                    "full-strength RGB stripes across the picture. All four originals are "
                    "in the rejected section below. The fix was to ask for the "
                    "CONSEQUENCES of a CRT (glow, bow, reflection) and never name the part.",
    }
    reasons = {}
    if os.path.exists(DROPPED):
        try:
            reasons = {d["slug"]: d.get("reason", "") for d in json.load(open(DROPPED))}
        except Exception:
            reasons = {}

    def card(r, folder):
        rows = [("engine", r.get("engine")), ("checkpoint", r.get("checkpoint")),
                ("text encoder", r.get("text_encoder")), ("vae", r.get("vae")),
                ("LoRA", r.get("lora")), ("workflow", r.get("workflow")),
                ("seed", r.get("seed")), ("steps", r.get("steps")),
                ("guidance", r.get("guidance", r.get("cfg"))),
                ("sampler", r.get("sampler")), ("scheduler", r.get("scheduler")),
                ("size", r.get("size")),
                ("negative", r.get("negative_prompt")
                 or "none - FLUX.2 has no negative field")]
        meta = "\n".join("%-13s %s" % (k, v) for k, v in rows if v is not None)
        extra = ""
        if r.get("strings_asked"):
            extra = ('<br><span style="color:#b9b6b0">asked for, verbatim:</span> ' +
                     " &middot; ".join('&ldquo;%s&rdquo;' % esc(s)
                                       for s in r["strings_asked"]))
        if r.get("asked"):
            g, e, bits = r.get("got", {}), r.get("error", {}), []
            for k in ("background", "shape"):
                w, hgot = r["asked"][k], g.get(k, "?")
                m = e.get(k, {}).get("max_channel")
                cls = "ok" if (m is not None and m <= 12) else "bad"
                bits.append('<span class="sw" style="background:%s"></span>%s asked '
                            '&rarr; <span class="sw" style="background:%s"></span>%s got '
                            '<span class="%s">(%s/255)</span>' % (w, w, hgot, hgot, cls, m))
            extra = "<br>" + "<br>".join(bits)
        if r["slug"] in reasons:
            extra = ('<br><span style="color:#e07a5f">DROPPED:</span> ' +
                     esc(reasons[r["slug"]])) + extra
        return ('<figure><img loading="lazy" src="%s/%s.png" alt="%s">'
                '<figcaption><b>%s</b>%s'
                '<details><summary>recipe</summary><pre>%s\n\nPROMPT\n%s</pre></details>'
                '</figcaption></figure>'
                % (folder, r["slug"], esc(r["slug"]), esc(r["slug"]), extra,
                   esc(meta), esc(r.get("prompt", ""))))

    # These four are lanes, not media, and they must not inherit a medium_name off
    # whichever record happens to sort first (which is how the calibration section came
    # out titled "Ben-Day dots").
    SPECIAL = {
        "typography": ("Typography",
                       "Quoted strings, verbatim. Each card lists exactly what was asked "
                       "for so the claim can be checked rather than taken. Short "
                       "capitalised strings land; the failure mode is a repeated or split "
                       "line, never a misspelling."),
        "hex": ("Named hex colours, guidance 4.0",
                "The only engine on this box that takes a hex code at all. Each card shows "
                "the colour asked for and the colour sampled back off the rendered PNG, "
                "with the worst channel error. Shape adherence was 12 of 12."),
        "hex_g6": ("Named hex colours, guidance 6.0",
                   "The same twelve asks at guidance 6.0 instead of 4.0 - the one knob the "
                   "checkpoint card says tightens adherence. Same seed, same prompts."),
        "_ab": ("Three engines, one prompt",
                "Identical prompt, identical seed, identical frame, on FLUX.2, Qwen-Image "
                "and Animagine XL. All FLUX cells were rendered first and the others "
                "after, because a 34 GB transformer does not co-reside with them and an "
                "interleaved order costs a model reload per switch."),
        "_dropped": ("Rejected, and why",
                     "The failures, kept rather than deleted. A keep rate only means "
                     "something if the rejects are visible with the reason each one "
                     "failed. Two of these - the destroyed CRT frames - are the reason "
                     "the pixel-art medium was rewritten and re-rendered; compare them "
                     "with the section above."),
        "_calibrate": ("Turbo distill on and off",
                       "The question the checkpoint card answered from one pair and got "
                       "wrong. Same prompt, same seed, eight media, both graphs: Turbo at "
                       "8 steps against the undistilled path at 20. The 20-step column is "
                       "what the rest of this gallery is rendered at."),
    }
    order = ([k for k in lanes if k not in SPECIAL] +
             [k for k in SPECIAL if k in lanes])
    body, nav = [], []
    total = sum(len(v) for v in lanes.values())
    for d in order:
        recs = lanes[d]
        if d in SPECIAL:
            name, blurb = SPECIAL[d]
        else:
            name = recs[0].get("medium_name") or d.replace("_", " ").title()
            blurb = OVERRIDE.get(d) or recs[0].get("medium_blurb", "")
        nav.append('<a href="#%s">%s</a>' % (d, esc(name)))
        body.append('<section id="%s"><h2>%s<small>%d images</small></h2>'
                    '<p class="blurb">%s</p><div class="grid">%s</div></section>'
                    % (d, esc(name), len(recs), esc(blurb),
                       "".join(card(r, d) for r in recs)))
    drops = json.load(open(DROPPED)) if os.path.exists(DROPPED) else []
    ledger = json.load(open(LEDGER)) if os.path.exists(LEDGER) else []
    gal_total = sum(len(v) for k, v in lanes.items()
                    if k not in ("_calibrate", "_dropped"))
    head = (
        '<header><h1>FLUX.2 &mdash; physical media, and type</h1>'
        '<p><b>%d images kept</b> of %d rendered; %d dropped and listed in _dropped.json '
        'with the reason each one failed. (A further %d frames below are the '
        'Turbo calibration, which is a measurement rather than gallery work.) '
        'Every image carries its full recipe &mdash; engine, checkpoint, prompt, '
        'seed, steps, guidance, size, LoRA &mdash; in the fold-out under it. FLUX.2 dev '
        'fp8mixed on an RTX 5090, Mistral-3-Small text encoder, Turbo distill LoRA OFF at '
        '20 steps. There is no negative prompt anywhere in this gallery because FLUX.2 has '
        'nowhere to put one: BasicGuider takes a single conditioning.</p>'
        '<p>The corpus is written to one rule this box learned the expensive way: '
        '<b>the model renders nouns, not adjectives</b>. Nothing below says &ldquo;in a '
        'plasticine style&rdquo;. Each entry names what the substrate physically has &mdash; '
        'thumbprints, the seam where two colours were pressed together, dust and one hair '
        'stuck to the surface, armature wire showing at the ankle.</p></header>'
        % (gal_total, len(ledger), len(drops), len(lanes.get('_calibrate', []))))
    html = ("<!doctype html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>FLUX.2 gallery</title><style>%s</style></head><body>%s"
            "<nav>%s</nav><main>%s</main></body></html>"
            % (INDEX_CSS, head, " ".join(nav), "".join(body)))
    out = os.path.join(GAL, "index.html")
    with open(out, "w") as f:
        f.write(html)
    print("index: %d images across %d folders -> %s" % (total, len(order), out), flush=True)


def mode_remeasure(a):
    d = os.path.join(GAL, "hex" + (a.suffix or ""))
    rows = [json.load(open(os.path.join(d, f))) for f in sorted(os.listdir(d))
            if f.endswith(".json") and not f.startswith("_")]
    measure_hex(rows)


# ================================================================================= main

def main():
    p = argparse.ArgumentParser(
        description="FLUX.2 gallery: physical media and typography.")
    p.add_argument("--mode", required=True,
                   choices=["calibrate", "media", "typo", "hex", "ab", "sheets",
                            "drop", "stats", "index", "remeasure", "list"])
    p.add_argument("--wave", type=int, default=1)
    p.add_argument("--only", help="comma-separated media keys / folder names")
    p.add_argument("--slugs", help="drop mode: comma-separated slugs")
    p.add_argument("--reason", help="drop mode: why it was dropped")
    p.add_argument("--seed", type=int, default=SEED)
    p.add_argument("--steps", type=int, default=STEPS)
    p.add_argument("--guidance", type=float, default=GUIDANCE)
    p.add_argument("--turbo", action="store_true", default=TURBO)
    p.add_argument("--chunk", type=int, default=8)
    p.add_argument("--yield-cap", type=int, default=240, dest="yield_cap",
                   help="seconds to wait for a clear queue before taking a turn anyway; "
                        "0 defers to other agents completely")
    p.add_argument("--cols", type=int, default=0)
    p.add_argument("--cell", type=int, default=640)
    p.add_argument("--suffix", default="", help="hex mode: folder suffix, e.g. _g6")
    a = p.parse_args()

    if a.mode == "list":
        for k, v in MEDIA.items():
            n = len([1 for m, _s, _t, _z in WAVE1 if m == k])
            n2 = len([1 for m, _s, _t, _z in WAVE2 if m == k])
            print("%-16s %-28s w1=%d w2=%d" % (k, v["name"], n, n2))
        print("\n%d media | wave1 %d | wave2 %d | typo %d | hex %d | total %d"
              % (len(MEDIA), len(WAVE1), len(WAVE2), len(TYPO), len(HEX),
                 len(WAVE1) + len(WAVE2) + len(TYPO) + len(HEX)))
        return

    os.makedirs(GAL, exist_ok=True)
    fn = {"calibrate": mode_calibrate, "media": mode_media, "typo": mode_typo,
          "hex": mode_hex, "ab": mode_ab, "sheets": mode_sheets, "drop": mode_drop,
          "stats": mode_stats, "index": mode_index, "remeasure": mode_remeasure}[a.mode]
    sys.exit(fn(a) or 0)


if __name__ == "__main__":
    main()
