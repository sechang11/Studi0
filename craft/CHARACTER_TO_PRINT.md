# A CHARACTER, END TO END, TO A THING YOU CAN PRINT

This is the recipe. It was found the expensive way on TERRA — seventeen mesh candidates,
two splat runs, four source sweeps and about seven hours — and it exists so the next one
is an hour.

Read the result of following it at **`/model3d`** in the studio app. Read the evidence
behind every number at `studio/samples/terra_3d/mesh/VERDICT.md` and
`studio/samples/terra_3d/source/RECOMMENDATION.json`. Read the mesh vocabulary — what
manifold means, why thickness is a shape diameter function — at `craft/PRINTING.md`.

Labels used throughout, the same three `PRINTING.md` and `VERDICT.md` use:

- **MEASURED** — measured on this box, on our own output, with the measurement quoted.
- **RULE OF THUMB** — general hobby-printing practice. Not measured here. No printer was
  ever identified for this project.
- **HARD** — a property of a file format or a piece of software, not a preference.

---

## 0. THE SHORT VERSION

```
source image   1600+ px on the long edge, arms OUT, no cast shadow,
               plate colour chosen to contrast with SKIN, matted to RGBA
prep           alpha-crop, composite on white, pad SQUARE, 1024x1024
conditioning   Hunyuan3Dv2Conditioning        <- single view. NOT the MultiView node.
latent         EmptyLatentHunyuan3Dv2         resolution 4096
sample         euler / normal, 30 steps, cfg 5.0
decode         VAEDecodeHunyuan3D             octree_resolution 512
extract        VoxelToMesh  surface net       threshold 0.45
repair         mesh_doctor repair --method voxel --voxel-res 900
verify         mesh_doctor diagnose <the repaired file>     <- do not skip
scale+export   mesh_doctor export --height 150 --up y --out x.stl --out x.3mf
then           add a base. Nothing is trustworthy on the plate until you do.
```

Cost **MEASURED** on the 5090: 54 s to generate, 40 s to repair (10.7 GB host RAM),
about 3 minutes end to end once the source image exists. The source image is the part
that takes an afternoon.

---

## 1. THE SOURCE IMAGE IS MOST OF THE JOB

Single-image-to-3D means the image *is* the prompt. There is no text conditioning in
either graph — **MEASURED**, read out of `workflows/24_hunyuan3d_mesh.json`. Everything
the mesh will be is decided here.

### Six requirements, in the order they bite

**1. ARMS CLEAR OF THE TORSO, with air on both sides for their whole length.**
Anything touching the body gets fused into one lump of geometry, and no repair separates
it afterwards.

**MEASURED, and this one is counter-intuitive.** Five pose vocabularies were swept at two
LoRA strengths. Only **`outstretched arms`** opens the arms. The danbooru tag
**`spread arms` — the tag that literally means a T-pose — does not**: it returns arms
near the hips at both strengths tested. Evidence:
`studio/samples/terra_3d/source/evidence/sheet_pose.jpg`, 10 cells.

The natural hypothesis was that the character LoRA had memorised arms-down, because all
16 of TERRA's training views have arms down. **That is wrong.** Sweeping strength
alongside the pose words shows the pose opens at full trained strength. Keep the
character card's measured LoRA strength. Dropping it is not a free win — one cell at half
strength drifted off the anime engine entirely and returned a smooth 3D-render doll.

**2. LEGS AND BOOTS SEPARATE**, both feet complete, nothing bridging them.

**3. NO CAST SHADOW.** A shadow pool at the feet mattes as part of the figure and becomes
geometry welded to the soles.

**MEASURED:** `no cast shadow` in the POSITIVE prompt **still draws the shadow**. A
negation does not render — the model draws the nouns it is given, and `shadow` is one of
them. Put `shadow, drop shadow, floor, ground, reflection` in the NEGATIVE prompt.
Evidence: `source/evidence/sheet_light_out.jpg`.

**4. THE WHOLE FIGURE IN FRAME**, roughly 90% of frame height, nothing touching an edge.

**5. RENDER LARGE.** 1600+ px on the long edge. Geometry detail follows source detail,
and a full-body render at 832x1216 gives a head about 90 px across — there is no face in
that to reconstruct.

**6. CLEAN COSTUME.** The wear ladder does not render above rung 1 on this project's
engines anyway, and a clean costume is the right choice for a figurine.

### The plate colour is a matting variable, not decoration

**MEASURED, and this is the finding most likely to bite a new character.** On the
project's usual grey plate, BiRefNet **severed a bare pale forearm** — the hand survived
as a floating island of 1.33% of the figure area. Same seed, same pose, only the plate
changed to dark blue: stray area **0.04%**, forearm continuous, confirmed at 1:1 against
magenta. Evidence: `source/evidence/sheet_matte.jpg`.

Pale skin on pale grey is not enough contrast for the matter. **Choose the plate to
contrast with the SKIN, not just with the costume.** (n=2, attributed cleanly but not
swept — check it for your character rather than assuming dark blue.)

### Then look at the alpha

Every stray island in the matte is a floating shell in the mesh downstream. Composite the
RGBA over magenta at 1:1 and look at the hands, the hair edge and the gap between the
legs. Do not trust an `edge_softness_px` number that divides soft pixels by the *bounding
box* perimeter — a figure with spread arms and a fringed skirt has a silhouette perimeter
several times longer than its bbox, so that figure overstates. The real hair edge here
was a crisp ~2 px antialias band.

### Do NOT feed the character's existing turnaround

**MEASURED**, four independent disqualifications of `studio/samples/cast/TERRA/`:

1. **Three of the six usable views are cropped by the frame.** A cropped view cannot be
   scale-matched to a complete one, so the set has no common scale at all.
2. **The costume disagrees.** The cape is smooth and short in two views and floor-length,
   shredded and stained in the others. Those are two different garments.
3. **The arms are against the body in all sixteen** — it is the pose the LoRA trained on.
4. **The mattes are dirty**: 17 detached fragments on the front view, 11 on side-left.

And a trap: the figure-height column reads 95–100% across those views, which *looks* like
scale agreement and is the opposite of it. A figure whose legs left the frame measures
100% of frame height **because** it is cut off.

---

## 2. PREP: PAD SQUARE, AND WHY THAT IS NOT COSMETIC

Alpha-crop to the figure, composite onto a **white** plate, pad to a **square**, resize to
1024x1024.

**MEASURED.** `CLIPVisionEncode` with `crop: center` — the default — squares a portrait by
throwing away the ends. On a 1664x2432 source it keeps the middle 1664 of 2432 rows:
**15.8% off the top and 15.8% off the bottom**. In practice that removes the top of the
hair ribbon and the tips of the boots. Verified by running
`comfy.clip_model.clip_preprocess` directly and saving what the model actually receives —
`studio/samples/terra_3d/mesh/views/EVIDENCE_clip_preprocess.jpg`.

The mesh survives and is degraded. Same seed, same settings, only the framing changed:
**11 floating islands against 1**, 13.86% non-manifold against 12.56%, and the wrap skirt
read as a long fringed cloth to the ankles.

Two fixes, either works: **pad square yourself**, or set `crop: none`, which letterboxes
rather than squashing. Both verified.

---

## 3. CONDITIONING: SINGLE VIEW. THE MULTIVIEW NODE DOES NOT WORK HERE.

Use `Hunyuan3Dv2Conditioning`.

**Do not use `Hunyuan3Dv2ConditioningMultiView` on this box.** **MEASURED**: fed four
normalised cardinals it returns **a cloud of disconnected specks in a slab 0.11 units
thick** — 12,108 faces, 134 vertex islands, 26% non-manifold. Not a worse figure. Noise.
Look at it on `/model3d`; it is unmistakable.

The decisive diagnostic: **one slot of the MultiView node, holding the exact image that
makes an excellent figure through the single-view node, also returns specks.** View count
is not the variable. Image provenance is not the variable (the qwen front render fails
identically). Handedness is not the variable (L/R swapped fails identically).

Mechanism, read out of `comfy_extras/nodes_hunyuan3d.py` lines 77–90: the node adds a 1-D
sincos view embedding per view and concatenates the token sequences. That is the
**Hunyuan3D-2mv** conditioning format. Only `hunyuan_3d_v2.1.safetensors` — the
single-view checkpoint — is installed, and it has never seen an additive view embedding,
so even one view through that node is out of distribution.

**To get multi-view you must download a `hunyuan3d-2mv` checkpoint.** No amount of image
preparation helps. Tiling four views into one square image down the single-view path also
fails (1.16M faces of floating slabs) — CLIP-vision conditioning does not decompose a
contact sheet into viewpoints.

**UNVERIFIED**: the 2mv explanation was never confirmed against a working 2mv checkpoint,
because none exists on the box. It is read from the node source and is consistent with
every cell of the ladder.

Building a good multi-view source set is still worth it *if* you get the checkpoint. The
recipe that produced a costume-consistent set: render the six views **image-conditioned**
from the single-view winner (workflow 32 plus `qwen-image-edit-2511-multiple-angles-lora`),
not text-conditioned. A text-conditioned turnaround fixed framing and still came back with
a gold bodice in one view and red in the other five — each view is an independent sample
of a bistable costume and no prompt work fixes that. Use the four cardinals, not all six;
the nominal 45-degree three-quarters came back close to profile.

---

## 4. GENERATE: TWO DIALS THAT MATTER

### octree_resolution — a TOPOLOGY dial, not just a detail dial

**MEASURED**, single view, everything else identical:

| octree | faces | non-manifold edges | as % of edges | wall | VRAM peak |
|---|---|---|---|---|---|
| 256 | 250,058 | 43,703 | 12.56% | 16.3 s | 9,582 MiB |
| 384 | 524,816 | 46,540 | 6.12% | 29.4 s | 9,422 MiB |
| **512** | 886,708 | 25,263 | **1.92%** | 46.2 s | 9,730 MiB |

Raising 256 → 512 cut the non-manifold **fraction** 6.5x. This was documented as a detail
dial and it is also a topology dial. **Use 512.** It costs 2.8x the wall clock and about
900 MiB more VRAM, which on a 32 GB card is nothing — VRAM was never the constraint at any
setting tested.

Corollary worth carrying: the 28.1% non-manifold measured on an earlier test object at
octree 256 was largely a **resolution artefact of the surface-net extractor**, not an
inherent property of Hunyuan3D output.

### VoxelToMesh threshold — the printability dial, worth 4x

**MEASURED**, both repaired at voxel-res 900, both evaluated at a 150 mm print:

| threshold | surface under 1.0 mm | p10 thickness | verdict |
|---|---|---|---|
| **0.45** | **1.66%** | 1.68 mm | passes the project's 5% convention |
| 0.60 (workflow default) | 6.93% | 1.19 mm | fails it |
| 0.70 | worse still | — | fails |

Lowering the iso-surface moves the surface outward. **JUDGED**, opening both head sheets
at 480 px: 0.45 keeps lidded almond eyes, nose, mouth, earrings and hair ribbon, only
slightly shallower than 0.60, with slightly fuller hair locks. That is a fair trade for
4x. On a figurine this is the single cheapest thing you can do to make the model
printable.

### Two things that do not help

- **Latent resolution is not a substitute for octree resolution.** Doubling
  `EmptyLatentHunyuan3Dv2` to 8192 at octree 384 came back with a *mushier* face and hair
  degenerated into tangled sausages. 512/4096 beats 384/8192 clearly. Spend on octree.
- **`VoxelToMesh` algorithm `basic`** produces a fuzzy, sugar-coated blob whose silhouette
  dissolves. `surface net` is correct despite being the source of the non-manifold edges.

### Seed variance is large

**MEASURED / JUDGED**: the same settings at a second seed came back with visibly different
leg thickness, a shorter skirt and a different hair fall, and 10 raw islands against 5. Do
not attribute a difference between two settings to the settings without holding the seed,
and do not read one seed as the model's ceiling. Every conclusion above rests on one seed
and an effect much larger than this — but that is the caveat on all of them.

---

## 5. REPAIR: THE ONLY THING THAT MAKES IT WATERTIGHT, AND THE DIAL THAT DESTROYS FACES

### Why hole-filling cannot work

**MEASURED** on the earlier test object: 160 open edges — essentially hole-free — but
**190,005 of 675,541 edges shared by three or four faces (28.1%)**. The surface is pinched
against itself and carries interior membranes. `fill_holes` moved the Euler number by
exactly zero. Surface-local repair cannot remove a membrane welded to the outer skin along
a shared edge.

**Only voxel remesh fixes it**: rasterise, flood-fill the interior, re-extract with
marching cubes. Measured: boundary edges 160 → 0, non-manifold 190,005 → 0, watertight
False → True, winding False → True, volume +4.5%.

Use `--voxel-fill orthographic` (the tool's default). **MEASURED**: `base` fill leaves
3.6% less interior filled because a leaky surface lets the simpler fills escape, and the
unfilled interior is then mistaken for thin walls — 2.5 mm median thickness against
7.0 mm on the same object.

### --voxel-res is the dial that decides whether the face survives

**MEASURED / JUDGED**, on a slender standing figure at a 150 mm intended print:

| voxel-res | one voxel | the face | cost |
|---|---|---|---|
| 320 (tool default) | 0.47 mm | **destroyed** — a terraced mass, no eyes, no nose, no ribbon | 5 s |
| 640 | 0.23 mm | partial — eye sockets return, nose and mouth still terraced | 17 s, 5.4 GB |
| **900** | 0.167 mm | **good** — lidded eyes, nose, mouth, ears, ribbon legible | 37 s, 10.7 GB |

**This is the most dangerous failure in the whole pipeline**, because at res 320 the
full-body silhouette still reads correctly at contact-sheet scale. The damage is only
visible when you zoom to the head. Both sheets are side by side on `/model3d`.

The dial counts voxels along the **longest axis**, so a slender standing figure is
penalised where a squat object is not.

**RULE OF THUMB from this measurement: voxel-res ≥ 6x the octree resolution you decoded
at, or equivalently at most 0.2 mm per voxel at your intended print height.** Memory grows
fast — 900 already takes 10.7 GB of host RAM.

**UNVERIFIED**: three points on one figure. The actual threshold between 640 and 900 was
not found, nothing above 900 was tested, and the rule was not checked on a
differently-proportioned subject.

### Repair can fail, and it says so

One candidate came back `fixed_watertight: false` at default settings. The tool reported
it rather than shipping a broken solid. Raising `--voxel-res` is the fix — same dial.

Island dropping works but cannot rescue a noise mesh: a candidate with 134 vertex islands
still had 119 after repair, because there is no dominant shell for the 1% threshold to
keep. Every *good* candidate repaired down to exactly 1 island.

### Then diagnose the file you wrote — do not skip this

```
python3 studio/_tools/mesh_doctor.py diagnose out/fixed.glb
```

Repair reports its own success. Re-verifying from the written file is what catches an
exporter that quietly degraded the mesh.

---

## 6. THICKNESS, AND THE TRAP IN MEASURING IT

**Thickness measured on an unrepaired mesh is a lie.** **MEASURED**: a raw mesh read a
0.71 mm median wall and condemned 59% of its surface as unprintable; the same object after
repair read 6.9 mm median and 0.35% below 1 mm. The raw reading is the ray stopping on
interior membranes, not on the far wall. `mesh_doctor` now refuses to present thickness
numbers without a loud UNTRUSTWORTHY banner when the input is not a closed solid. Believe
the banner.

**Where the thin material actually is — and the brief predicted the opposite.** By-height
decile on the delivered figure at 150 mm:

| band | surface under 1 mm |
|---|---|
| z 0–15 mm, the boots | 0.0% |
| z 30–45 mm | **32.2%** |
| z 45–60 mm | **32.3%** |
| z 135–150 mm, the top of the hair | 1.9% |

Everyone expects the hair to be the thin-shell problem. **It is not.** Hunyuan3D
reconstructs hair as fat, fused sausage locks, which are among the *thickest* material in
the model. The thin thing is the **skirt fringe at thigh-to-knee height** — many separate
hanging strands, every one of them sub-millimetre at figurine scale.

**Print height is the cheapest fix, and it is not linear.** Measured ladder:

| height | surface under 1.0 mm |
|---|---|
| 150 mm | 6.96% |
| 200 mm | 1.61% |
| 250 mm | 1.18% |
| 300 mm | 0.89% |

The jump between 150 and 200 is steep because a cluster of fringe features sits right at
about 1 mm at 150 mm scale.

**So: 150 mm is a resin print (0.54% under the 0.3 mm resin floor). FDM wants 200 mm** —
or a deliberate thickening pass, the way commercial statuettes turn a fringe into a slab.

Feature floors, all **RULE OF THUMB**: FDM with a 0.4 mm nozzle, 0.8–1.2 mm (two to three
extrusion widths); resin/SLA, ~0.3 mm.

---

## 7. THE PRINT SPEC

```
python3 studio/_tools/mesh_doctor.py scale     fixed.glb --height 150 --up y
python3 studio/_tools/mesh_doctor.py thickness fixed.glb --height 150 --min-mm 1.0
python3 studio/_tools/mesh_doctor.py overhang  fixed.glb --height 150
python3 studio/_tools/mesh_doctor.py export    fixed.glb --height 150 --up y \
        --out FIG_150mm.stl --out FIG_150mm.3mf
```

**`--up y` is required, not optional. HARD:** glTF/GLB is Y-up by specification; STL and
every slicer are Z-up. STL carries no units, so the export must already be in millimetres.
3MF does carry units, which is why both are written.

**Overhangs.** 45 degrees from vertical is the **RULE OF THUMB** threshold. Beware a naive
overhang count: faces resting on the build plate point straight down and get counted as
overhangs unless you exclude bed contact. On one test object that mistake read 27.06%
against a true 4.25%. `mesh_doctor` excludes bed contact.

**A BASE IS ALMOST CERTAINLY REQUIRED, and this was predicted from the source render
before any mesh existed.** A character in pointed boots with a raised heel stands on two
small triangles. **MEASURED** on the delivered figure: bed contact **200.9 mm²**, giving
bed-contact / height² = 0.0089 against the project's 0.015 flag. **She will not stay on
the plate.** Union in a disc or plinth before slicing.

**This has not been done.** It is the top of the next agent's list.

**Splitting** is the fix when a part cannot be supported: split and rejoin with a 3–4 mm
registration peg at 0.15–0.2 mm clearance (**RULE OF THUMB**).

---

## 8. GAUSSIAN SPLATS: FOR SHOWING, NOT FOR PRINTING

Run TripoSplat as well — it takes 16 s — but know what it is for.

**MEASURED**: 262,144 gaussians in 16.1 s at 8,454 MiB peak; 131,072 in 6.0 s at 5,303
MiB. **JUDGED**: the orbit strip is comfortably the best-looking output of the whole job —
full colour, the correct costume, stable through a full 360 — against Hunyuan3D's grey
untextured geometry (its GLB carries POSITION and nothing else: no colour, no normals, no
UVs).

**It is not printable and converting it is not worth it.** A splat is a cloud of oriented
translucent ellipsoids with opacity — no surface, no inside, no outside, nothing for a
slicer to fill. Converting means either multi-view render plus photogrammetry/TSDF fusion,
or opacity-thresholded marching cubes. Both discard the view-dependent colour that makes
it good, and both land back at a noisy iso-surface needing the same repair — from worse
geometry.

**Use the splat for the turntable you show someone. Use Hunyuan3D for the thing you
print.** They are not competitors.

---

## 9. RUNNING IT FOR THE NEXT CHARACTER

### What is already generic

`studio/_tools/mesh_doctor.py` takes any mesh path. Nothing in it is TERRA-specific.
`studio/_tools/model3d_index.py` and the `/model3d` page discover a character by looking
for `studio/samples/<id.lower()>_3d/` — put NIKA's pipeline at `studio/samples/nika_3d/`
in the same layout and both find her with no edit.

### What is not, and what to change

Both generation tools hardcode TERRA. **Honest cost: about four constants each.**

`studio/_tools/terra_3d_source.py`
- `OUT` (~line 54) — `studio/samples/terra_3d/source`
- `CAST` (~line 56) — `studio/samples/cast/TERRA`
- the character card path (~line 130) — `studio/characters/TERRA.json`
- `POSES` and the prompt constants carry TERRA's costume nouns and her required identity
  token

`studio/_tools/terra_mesh.py`
- `SRC` / `OUT` (~lines 49–50) — `studio/samples/terra_3d/{source,mesh}`

Either parameterise those with a `--character` argument, or copy the two files. Copying is
honest for a one-off; parameterising is right if a third character is coming.

### The identity token

**MEASURED on TERRA and true of every LoRA-backed character on this project:** the
character's danbooru identity token must stay in every prompt. Without it the LoRA alone
returns a generic figure. Read the token and the measured strength off
`studio/characters/<ID>.json` — do not retype them.

### Run order

```
# source
python3 studio/_tools/<char>_3d_source.py --stage pose      # sweep the pose words, LOOK
python3 studio/_tools/<char>_3d_source.py --stage light     # shadow into the negative
python3 studio/_tools/<char>_3d_source.py --stage final
python3 studio/_tools/<char>_3d_source.py --stage matte --dir final
python3 studio/_tools/<char>_3d_source.py --stage publish

# mesh
python3 studio/_tools/<char>_mesh.py prep
python3 studio/_tools/<char>_mesh.py gen
python3 studio/_tools/<char>_mesh.py splat
python3 studio/_tools/<char>_mesh.py diagnose
python3 studio/_tools/<char>_mesh.py render --fixed --mp4 90
python3 studio/_tools/<char>_mesh.py contact
python3 studio/_tools/<char>_mesh.py report

# check the app sees it
python3 studio/_tools/model3d_index.py --character NIKA --check
```

Each source stage reads what the earlier ones left in `samples/<char>_3d/_work/`.

### Two things that will waste your time if nobody tells you

**A cached failure is not a result.** If a grid runner's skip test is `name in runs`, one
server death poisons the whole grid and the retry silently does nothing. Skip only records
that actually produced a mesh.

**ComfyUI died once mid-grid** with no traceback, right as an octree-384 job was queued,
which looked exactly like a memory limit. It was not reproducible — host RAM was down to
7 GB free on a shared box at that moment. **Do not record "octree 384 crashes the
server."** Restart and retry once.

---

## 10. WHAT IS NOT PROVEN, EVERY TIME

Carry these forward on every character. They do not get better by being repeated.

- **NO SLICER HAS EVER OPENED ONE OF THESE FILES.** None is installed on the box.
  Watertightness is verified by re-loading the written STL through trimesh; that
  PrusaSlicer, Cura or Bambu Studio ingest it cleanly is **not** verified. STL is the safer
  of the two written formats. **This is the single largest gap between "qualified" and
  "proven printable."**
- **NO PRINTER.** Every feature-size floor, the 45-degree rule, the peg clearances and the
  material weights are rules of thumb from general practice, not machine measurements. No
  printer was ever identified for this project. If you have a specific machine, check them
  against it.
- **The 5% under-minimum fail threshold and the 0.015 bed-contact flag are this project's
  own conventions**, not standards. Treat a failure as "stop and look", not as physics.
- **The delivered solid carries genus ~329** — a few hundred small tunnels from
  reconstruction noise. A slicer only needs inside and outside, so this should not matter;
  it was not sliced and it was not sectioned to confirm.
- **The renders on `/model3d` are `terra_mesh.py`'s own orthographic point-splat
  rasteriser** — no shadows, no ambient occlusion, no perspective. Silhouette, surface form
  and feature legibility are what it can be trusted for, and it flatters a shape slightly.
  Nothing has been viewed in Blender or any production 3D viewer.
- **A 133 MB STL at 2.67M faces is far more than a print needs.** Decimating to a few
  hundred thousand faces would almost certainly be fine; how far it can be reduced before
  the face degrades was not tested.

---

## 11. INSTALLED FOR THIS, WITH NO ROOT

`python3 -m pip install --user trimesh numpy scipy networkx rtree shapely manifold3d
embreex scikit-image`

Two of those are not optional and are easy to miss:

- **scikit-image** — without it trimesh's `marching_cubes` raises `ModuleNotFoundError`
  and the voxel repair path, the only thing that makes this output watertight, simply does
  not run.
- **embreex** — without it trimesh silently falls back to a pure-python ray intersector.
  With it, a thickness pass over 576k faces takes about a second.

**Note against an older brief:** system `python3` (3.14.6) on this box already has numpy
and PIL. If a tool fails on `import numpy`, that is not the reason today — read the
traceback before pip installing anything.
