# Capabilities

`/capabilities` — and `studio/capabilities.json`, which is the file behind it

## What this page is for

Everything the ComfyUI install on this box can do, whether or not the studio app exposes
it. The studio is a film-making front end built on top of a much larger toolkit, and most
of that toolkit has no button.

The source is a curriculum that was rendered and then forgotten:
`~/ComfyUI/output/claude-generated/`. 92 numbered folders live there. **34 of them are
capability demonstrations** — each with a card, a workflow, and rendered output. The
other 58 are production runs.

The catalogue is built by `python3 studio/_tools/capability_scan.py` and written to
`studio/capabilities.json`.

## What to do first

Look at the **ready and invisible** list. Thirteen capabilities are verified, rendered,
and have a runnable workflow today, and none of them are reachable from any page in the
app:

`03-controlnet` · `04-upscaling` · `07-frame-interpolation` ·
`12-segmentation-matting` · `14-ltx-two-stage-upscale` · `15-product-composite` ·
`18-audio-to-video` · `19-llm-lyrics-song` · `22-flux2` · `23-control-maps` ·
`24-outpaint-removal` · `25-music-remix` · `26-vision-caption`

If you are wondering "can this box do X", that list is where to look before assuming no.

## The three things that will confuse you

**1. "Capability" here means demonstrated, not installed.**

Each entry carries a state. Eight of the 34 — folders 27 through 34 — hold only a
capability card and a JSON declaration, with **no rendered sample at all**. They are
documented plans: lora-training, vace-video-editing, hunyuanvideo, camera-control,
character-identity, seedvr2-upscale, zimage-turbo, flf2v-transitions. Several are
described as zero-download builds on weights already present.

**2. Some declarations are out of date, and the catalogue flags them.**

Seven entries carry `declaration_stale`. The clearest case is `27-lora-training`, which
declares itself *"not explored"*, its workflow *"not built yet"*, and calls itself *"the
largest untouched capability here"*. All three are false: the workflow exists, two tools
build and run it, 22 LoRAs are on disk, and TERRA carries a trained rank-16 character
LoRA. Read the flag before you trust the card.

`10-voice` is stale in a more interesting way. It names zero-shot cloning as the unwired
fix for a one-voice problem. That problem is already solved by a newer engine the
declaration does not know about — 17 named Higgs v3 voices are on disk now.

**3. The archive documents the half of the studio the app uses least.**

Everything numbered in it is the **qwen** side. The app's entire illustration engine —
`animagine-xl-4.0` plus IPAdapter, reached from `compose.py`, `short.py`, `gallery_gen.py`
and `tag_examples.py` — has **no capability folder at all**. So do
`21_sdxl_anime_restyle.json` and `32_qwen_turnaround.json`.

If a capability seems missing from the catalogue, check whether it is anime-side before
concluding the box cannot do it.

## A worked example of reading these honestly

Folder `03-controlnet` claims its output matches the control map *"to the pixel"*. It
does not. The control map is a slender lighthouse on jagged sea rock; the output is a
squat concrete bunker on a dry grassy dune. The composition rhymes, the structure does
not — control strength was loose. The entry is flagged.

Folders `02` and `24` corroborate each other instead: `02` removes a lighthouse from a
scene successfully, `24` fails twice to remove a watch from a product shot. That is
exactly the rule folder 24 states — removal works on a small object in a contextful
scene and fails on the subject of a product shot.

## What good output looks like here

- Each entry names a **sample you can open**, a **card**, and a **workflow that resolves
  on disk**.
- The representative sample was picked **by looking**, not by filename. Folder 06's own
  declaration nominates a near-black rainy roof; the catalogue overrides it with a clip
  that is legible at tile size.
- Audio picks are marked **NOT AUDITIONED** rather than dressed up as verified. Five
  entries carry that flag and should be read as unproven.

## If `/capabilities` does not load

The page is being built in a parallel wave. `studio/capabilities.json` exists either way
and is readable directly. If the route 404s, the catalogue has landed but the page has
not yet.
