# Sheets: one picture in, every angle out

`/sheets` turns a picture of a **character**, an **item** (a weapon, a piece of clothing, any object)
or a **place** into a labelled model sheet: every angle, a face or detail close-up, expressions or
times of day, lifted to HD, laid out as one picture, and each view kept as its own file. A sheet can
be sent to a shot-script film as a reference picture, or saved to the Foundry as an asset.

| file | what it is |
|---|---|
| `studio/sheets.py` | the engine and a command line; no web code |
| `studio/_tools/sheets_routes.py` | the page's API, the job queue, the bridges to films and the Foundry |
| `studio/sheets.html` | the page |
| `studio/sheets/<id>/` | one sheet: `sheet.json` is the record; the pictures are git-ignored |
| `studio/samples/sheets_lab/` | the contact sheets every claim below rests on |

Labels, as elsewhere in `craft/`: **MEASURED** = measured on this box, the number quoted;
**JUDGED** = I opened the pixels and formed a view.

## Using it

The page: **+ New sheet**, say what it is, drop in up to three pictures (the first is turned; a
close-up of the face or of a detail is used for the close-ups; a third is shown on the sheet), name
it, tick what to include, **Make the sheet**. It shows each view as it lands. Any view can be made
again on a new seed (**redo**); the automatic check flags some bad ones (below). Deleting is undone
from the message, not confirmed. **Send to a film…** makes a view the reference picture of a new or
existing cast member (or the place) of a shot-script film; the picture it replaces is kept and
**undo** puts it back.

The command line makes the same sheets:

    python3 studio/sheets.py new character PICTURE --name "Doran Vey" [--closeup FACE.png]
    python3 studio/sheets.py new item PICTURE --name "Winged sword" --subject sword --item-type weapon
    python3 studio/sheets.py new place PICTURE --name "Harbour" --times midday,golden,night,rain
    python3 studio/sheets.py make SHEET_ID [--redo turn_back,face_right]
    python3 studio/sheets.py list

One process makes a sheet at a time (`_work/making.lock`); the page follows a sheet the command line
is making and refuses to start a second maker on it.

## What each kind gets

| kind | views | time with HD ×2 (MEASURED) |
|---|---|---|
| character | 8 turnaround angles on grey; 4 face angles; 5 expressions (joy, anger, fear, sorrow, surprise) | 196 s for 17 views |
| item | front, 3/4, both sides, back, back 3/4, from above; the most detailed part close up; your close-up restored. Weapon: stood upright first, no "from above". Clothing: worn (front, back) and a flat lay | 102-128 s |
| place | from the left, from the right, reverse, reverse 3/4, raised left, raised right, aerial; times of day (dawn, midday, golden hour, night, rain, snow, fog) | 116 s for 7 angles + 3 times |

## What turns the camera

**Qwen-Image-Edit-2511 + its 4-step Lightning LoRA + the multiple-angles LoRA at 0.85** (workflow 32),
asked in the LoRA's **own camera words**: `<sks> {azimuth} {elevation} {distance}` - azimuth one of
front / front-right quarter / right side / back-right quarter / back / back-left quarter / left side /
front-left quarter view; elevation low-angle / eye-level / elevated / high-angle shot; distance
close-up / medium shot / wide shot. About 6 s a view on the 5090, ~1 MP out (1248×832, 880×1184).

- **MEASURED - plain English does not turn a place; the LoRA's words do.** "The same place seen from
  the opposite direction" handed the harbour back as the same deck view, and "the same temple seen
  from behind" handed back the front (`01`, `02`). `<sks> back view eye-level shot wide shot` turned
  the harbour right round - the boat seen from the water ahead of it (`03`); side views and the
  raised three-quarters are real new cameras (`03`, `05`).
- **JUDGED - weak on places, so not offered:** `low-angle shot` and `close-up` came back nearly
  unchanged on both places (`03`, `04`); `back-left quarter view elevated shot` rolled the temple onto
  its side (`04`). A temple's "back" is drawn as a second front - plausible, not known.
- **MEASURED - a figure turns cleanly once it stands on flat grey.** BiRefNet (workflow 14) cuts it
  out, it is centred on grey at 86% of the frame, and the 8 azimuths hold the man, his coat and his
  boots all the way round (`06`). The Foundry's anime turnaround - animagine re-drawing each view with
  the full body as its IPAdapter reference - gave Jin a "back" view facing the camera and changed
  Hoshi's species (`07`); the same Jin on grey turned cleanly through the LoRA (`08`).
- A picture that stops at the shoulders is **finished first**: the edit model, without the angles
  LoRA, "the same person standing, full body visible from head to feet", then cut out again (`12`).

## What does not turn the camera

The same edit model **without** the angles LoRA, in plain sentences: expressions, time of day
(`17`: midday, golden hour, night and rain keep every boat, rope and lamp where it was), a garment
worn by a person and laid flat (`16`), a weapon stood upright (`13`), and "an extreme close-up of
the most detailed part of the same sword" - which found the winged crossguard, and the radio's dial,
by itself (`14`).

## Faces are cropped, not asked for

terra_views.py measured framing words in an edit prompt coming back full length 23 times in 24, so
a face close-up is **cut** from the figure on grey (the head found from the cut-out's alpha), made
sharp by **SeedVR2 ×4** - a 271 px crop became a 1084 px face with the scar on his forehead still
there - and turned from that (`10`, `11`). A close-up you supply is used instead of the crop.

## HD

**MEASURED:** SeedVR2 3B (int8, core ComfyUI nodes) restores and doubles a view in 4.5-6 s; RealESRGAN
×4 takes 3 s. **JUDGED** on the same face (`18`): SeedVR2 adds real skin and wool detail;
ESRGAN paints it smooth - the plastic look. SeedVR2 is the default; ESRGAN is the fallback if the
SeedVR2 graph is ever refused. ×2 gives about 2.5K (1760×2368 for a standing figure), ×4 about 5K.
The detail is **re-synthesised** by the restorer, not recovered.

## The check, and what it cannot do

Every view is measured against what it was turned from, and one retry is made on a new seed when
either trips:

- **colours** - the subject's colour histogram against the source's, background excluded (characters
  and items). MEASURED: a character's own views scored 0.71-0.93, two different characters 0.00-0.01,
  so under **0.55** is flagged. An item's back can honestly be another colour - a radio's plain green
  back scored 0.52 against its chrome front - so an item is flagged only under **0.40**.
- **unchanged** - mean pixel difference under **3.0** (of 255) on a view meant to move the camera.
  MEASURED: a real back view of a man in a dark coat scored 5.3; a "from above" that did nothing, 2.4.
  A 32×32 structure correlation was tried first and does not work: a man's back view scored 0.97
  against his front (the same silhouette).

Neither judges a face, and a view can be wrong in ways neither sees. The page says so; **redo** is
one click.

## Limits worth knowing

- The back of anything, the side of a building, the rest of a street: **invented**, plausibly, from
  one picture. Lettering on an invented surface is gibberish.
- A prop the figure is not clearly holding is **background** to the cut-out: the ferryman's pole
  went with the lanterns. Make the prop its own item sheet.
- A figure cut by the frame or by water gets feet the model draws.
- The 3D buttons (a TripoSplat 360° turntable, a Hunyuan3D 2.1 mesh) start from the clean front view;
  they are for a single figure or object, not a place.

## The Foundry changes that came with it (2026-09-30)

- **Anime turnaround**: the full body is cut out onto grey (`_work/turn_base.png` in the asset) and
  turned by the LoRA in its own words, instead of the IPAdapter chain (`07` before, `09` after, a
  Foundry anime pack made from a description with the change in).
- **From an image**: the uploaded picture is made into a sheet and the pack IS that sheet - base,
  portrait, 5 turns, 3 face angles, 6 expressions - where it used to be redrawn from a caption of the
  picture, which made a lookalike. The caption still writes the asset's words. A later "make the
  pack" keeps those pictures and fills only the gaps, by editing the picture, never from words.
- **Save to the Foundry** from a sheet makes the same kind of asset: a character, a prop (hero +
  macro) or a costume (card).
