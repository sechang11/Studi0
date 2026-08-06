# TERRA, GEOMETRY: WHICH MESH AND WHY

Written by `studio/_tools/terra_mesh.py`'s operator after opening every sheet in
`mesh/views/`. Numbers come from `studio/_tools/mesh_doctor.py`; renders come from
terra_mesh's own point-splat rasteriser. Nothing here is asserted from a workflow note.

Labels: **MEASURED** = measured on this box in this run, with the measurement quoted.
**RULE OF THUMB** = general practice, not measured here. **JUDGED** = I opened the
pixels and formed a view.

---

## 1. THE WINNER

**`I_s512_thr045.glb`**, repaired to `I_thr045_fix900.glb`, shipped as
`mesh/print/TERRA_WINNER_150mm_resin.stl` / `.3mf`, and `TERRA_WINNER_200mm_fdm.stl`.

The runner-up `D_s512` (threshold 0.60) is shipped alongside as `ALT_D_thr060_*` so the
threshold trade-off in section 2 can be re-checked without regenerating anything.

Recipe, end to end:

| stage | setting |
|---|---|
| source image | `source/G_out_dark_s1_rgba.png`, alpha-cropped, composited on **white**, padded **square**, 1024x1024 |
| conditioning | `Hunyuan3Dv2Conditioning` (single view) — **not** the MultiView node |
| latent | `EmptyLatentHunyuan3Dv2` resolution **4096** |
| sampler | euler / normal, 30 steps, cfg 5.0, seed 777 |
| decode | `VAEDecodeHunyuan3D` octree_resolution **512** |
| extract | `VoxelToMesh` algorithm **surface net**, threshold **0.45** |
| repair | `mesh_doctor repair --method voxel --voxel-res 900` |
| export | `mesh_doctor export --height 150 --up y` |

Generation cost **MEASURED**: 53.7 s wall, 10,498 MiB peak VRAM. Repair 40 s, ~11 GB host RAM.

Final state **MEASURED**: 2,673,708 faces, 0 boundary edges, 0 non-manifold edges,
1 island, winding consistent, normals outward, `is_volume` true, `blocking: []`.
At 150 mm: 82.9 x 49.3 x 150.0 mm, zmin exactly 0, 55.5 cm3 solid.

---

## 2. WHY IT WON, AGAINST WHAT

Seventeen Hunyuan3D candidates and two TripoSplat runs. Three dials moved the result;
one dial destroyed it.

### Octree resolution is the dial that matters, and it fixes topology, not just detail

**MEASURED**, single view, everything else identical:

| octree | faces | non-manifold edges | as % of edges | islands | wall |
|---|---|---|---|---|---|
| 256 (`B_square`) | 250,058 | 43,703 | 12.56% | 1 | 16.3 s |
| 384 (`C_s384`) | 524,816 | 46,540 | 6.12% | 4 | 29.4 s |
| 512 (`D_s512`) | 886,708 | 25,263 | **1.92%** | 5 | 46.2 s |

This is the surprise. Octree resolution was documented as a detail dial; it is also a
**topology** dial. Raising it 256 -> 512 cut the non-manifold fraction by 6.5x. For
context the other agent measured 28.1% on the owl at octree 256 — so this is the same
defect, and it is largely a resolution artefact of the surface-net extractor, not an
inherent property of Hunyuan3D output. **Use 512.** It costs 2.8x the wall clock and
only 900 MiB more VRAM.

### VoxelToMesh threshold is the printability dial

**MEASURED**, both repaired at voxel-res 900, both evaluated at 150 mm:

| threshold | surface under 1.0 mm | p10 thickness | verdict |
|---|---|---|---|
| 0.45 (`I`) | **1.66%** | 1.68 mm | passes the 5% convention |
| 0.60 (`D`, the workflow default) | 6.93% | 1.19 mm | fails it |
| 0.70 (`K`) | worst of the three | — | fails |

Lowering the iso-surface from 0.60 to 0.45 moves the surface outward and takes the
sub-millimetre fraction from 6.93% to 1.66% — a **4x** printability gain. Workflow 24's
note says to lower the threshold "if the mesh comes out with holes or missing thin
parts". That is true but undersells it: on a figurine it is the single cheapest thing
you can do to make the model printable.

**JUDGED**: the cost is close to nothing. I opened `I_thr045_fix900_head.jpg` against
`D_s512_fix900_head.jpg` at 480 px. Both hold lidded almond eyes, a nose, a mouth,
earrings and the hair ribbon. I's features are a touch shallower and its hair locks
slightly fuller. That is a fair trade for 4x.

### Seed variance is real and large

**MEASURED / JUDGED**: `J_s512_seed` (seed 12345, everything else identical to D) came
back with visibly different leg thickness, a shorter skirt and a different hair fall.
Do not attribute a difference between two settings to the settings without holding the
seed, and do not read one seed as the model's ceiling.

### Two things made it worse

- **`L_s512_basic`** — `VoxelToMesh` algorithm `basic` instead of `surface net`.
  **JUDGED**: a fuzzy, sugar-coated blob; the silhouette dissolves. Confirms the
  workflow note. Not close.
- **`H_s384_l8192`** — latent resolution doubled to 8192. **JUDGED**: the face got
  *mushier* and the hair became a mass of tangled sausages. Latent tokens are not a
  substitute for octree resolution; 512/4096 beat 384/8192 clearly.

---

## 3. THE MULTI-VIEW RESULT: IT DOES NOT WORK HERE, AND THE REASON IS THE CHECKPOINT

This was the most likely big win in the brief. It is a clean, total failure, and it is
worth recording precisely so nobody spends another seven hours on it.

**MEASURED.** `Hunyuan3Dv2ConditioningMultiView` fed the four normalised cardinals
produced a **cloud of disconnected specks in a 0.11-unit-thick slab** — 12,108 faces,
134 vertex islands, 26.01% non-manifold. Not a worse figure. Noise.

The diagnostic ladder isolates the cause. All four cells, octree 256, same seed:

| cell | what it feeds the MultiView node | result |
|---|---|---|
| `MV1_single_img` | **one** slot, holding the exact image `B_square` used | **specks** |
| `MV1_mv_img` | one slot, the qwen front render | specks |
| `MV2_front_back` | two slots | a hollow inside-out box, 117k faces |
| `E_mv256` / `MV4_lrswap` | four slots, and four with L/R exchanged | specks, identical failure |

`MV1_single_img` is the decisive one. **The same pixels that produce an excellent figure
through `Hunyuan3Dv2Conditioning` produce noise through
`Hunyuan3Dv2ConditioningMultiView`.** The view count is not the variable. The images are
not the variable. The node is.

Mechanism, read out of `comfy_extras/nodes_hunyuan3d.py` lines 77-90: the MultiView node
adds a 1-D sincos view embedding to each view's CLIP tokens and concatenates the
sequences. That conditioning format belongs to the **Hunyuan3D-2mv** checkpoint.
`ls ~/ComfyUI/models/checkpoints/` shows only `hunyuan_3d_v2.1.safetensors` — the
single-view model. It has never seen an additive view embedding, so even one view
through that node is out of distribution.

**To actually get multi-view on this box you must download a `hunyuan3d-2mv`
checkpoint.** No amount of image preparation will help, and the source stage's excellent
four-cardinal turnaround is not at fault — it is a good set with nothing to eat it.

**The tiling workaround also fails.** `N_grid2x2` put the four cardinals into one square
image down the ordinary single-view path: 1.16M faces of floating slabs and fragments.
**JUDGED** from the contact sheet. CLIP-vision conditioning does not decompose a
contact sheet into viewpoints.

---

## 4. THE CENTRE CROP: SMALLER THAN FEARED, REAL ANYWAY

I predicted `CLIPVisionEncode` with `crop: center` would cut her head and feet off a
1664x2432 portrait. **I tested it instead of asserting it** by running
`comfy.clip_model.clip_preprocess` directly and saving what the model actually receives
(`mesh/views/EVIDENCE_clip_preprocess.jpg`, reproduced by `mesh/_work/clipprep_probe.py` under the ComfyUI venv).

**MEASURED**: the crop keeps the middle 1664 of 2432 rows — it removes **15.8% off the
top and 15.8% off the bottom**. In practice that takes the top of her hair ribbon and
the tips of her boots, not her whole head.

The mesh survives but is degraded. **MEASURED**, `A_portrait_crop` vs `B_square`, same
seed and settings, only framing changed: 13.86% non-manifold vs 12.56%, **11 islands vs
1**. **JUDGED**: A comes back stockier, surface-noisier, and reads the wrap skirt as a
long fringed cloth to the ankles.

Two fixes, either works: pad the source square yourself (what `prep` does), or set
`crop: none`, which letterboxes rather than squashing — also verified in the same image.

---

## 5. REPAIR AT THE DEFAULT RESOLUTION DESTROYS HER FACE

This is the finding I would most want carried forward, and it closes the other agent's
own open question ("I can assert it is watertight; I cannot assert it still looks like
an owl").

**MEASURED / JUDGED.** `mesh_doctor repair` at its default `--voxel-res 320`:

| voxel-res | one voxel at 150 mm | face | cost |
|---|---|---|---|
| 320 (default) | 0.47 mm | **destroyed** — a terraced Minecraft mass, no eyes, no nose, no ribbon | 5 s |
| 640 | 0.23 mm | partial — eye sockets return, nose and mouth still terraced | 17 s, 5.4 GB |
| **900** | 0.167 mm | **good** — lidded eyes, nose, mouth, ears, ribbon all legible | 37 s, 10.7 GB |

Open `views/D_s512_fixed_head.jpg` next to `views/D_s512_fix900_head.jpg`. The body
silhouette survives at 320 and looks fine at contact-sheet scale; that is exactly what
makes it dangerous. The damage is only visible when you zoom to the head.

**Why 320 is not enough here and was enough for the owl:** the dial is voxels along the
*longest axis*, and Terra is a slender standing figure whose longest axis is her height.
An anime eyelid crease is roughly 0.5 mm at a 150 mm print; at 0.47 mm per voxel it is
one voxel and cannot survive. **RULE OF THUMB from this measurement: for a humanoid
figure, use voxel-res >= 6x the octree resolution you decoded at, or put another way,
aim for at least 0.2 mm per voxel at your intended print height.**

Cost is bounded: res 900 on a 900k-face mesh took 37 s and 10.7 GB of host RAM, and
produced a 2.65M-face mesh.

---

## 6. PRINTABILITY OF THE WINNER

All **MEASURED** on `I_thr045_fix900.glb`.

**Watertight**: yes. 0 boundary edges, 0 non-manifold edges, 1 island, consistent
winding, outward normals, `is_volume` true, `blocking: []`. It re-loads from the written
STL still watertight.

**Genus ~329.** The solid carries a few hundred small tunnels. Reconstruction noise;
harmless to a slicer, which only needs inside/outside.

**Thickness** at 150 mm, 1.0 mm minimum (FDM, 0.4 mm nozzle):

| height | surface under 1.0 mm | p10 |
|---|---|---|
| 150 mm | 6.96%* | 1.19 mm |
| **200 mm** | **1.61%** | 1.58 mm |
| 250 mm | 1.18% | 1.99 mm |
| 300 mm | 0.89% | 2.36 mm |

\* the 150 mm row is `D`; the winner `I` reads **1.66%** at 150 mm. Both are quoted
because the ladder was run on D.

At the resin floor of 0.3 mm the winner reads **0.54% under** at 150 mm.

**So: 150 mm is a resin print. FDM wants 200 mm or a thickening pass.**

**Where the thin material is — and it is NOT where the brief predicted.** The
by-height-decile histogram puts it in deciles 2 and 3 (z 30-60 mm), at **32% thin in
each**. Decile 9, the top of her hair, is **1.9%**. Deciles 0-1, the boots and shins,
are 0.0% and 5.7%.

The brief predicted her hair would be the thin-shell problem. **It is not.** Hunyuan3D
reconstructs her hair as fat, fused sausage locks — visible in every head render — which
are among the *thickest* material in the model. The thin thing is the **skirt fringe** at
thigh-to-knee height, exactly as the source stage warned. Do not go looking for the
problem at the top of the model.

**Overhangs**: 7.79% of surface area past 45 degrees, 3.22% near-horizontal ceilings.
Modest. The outstretched arms and the hair flare are the offenders.

**A BASE IS REQUIRED. MEASURED, and it confirms the source stage's prediction**: bed
contact is **200.9 mm2**, giving bed-contact / height^2 = 0.0089 against the project's
0.015 flag. Her boots are pointed with a raised heel, so she stands on two small
triangles. She will not stay on the plate. Add a disc or plinth before slicing — this is
not optional.

**Material RULE OF THUMB** at 150 mm: 55.5 cm3 solid, so roughly 65 g resin, or roughly
14 g PLA at 2 walls / 15% infill.

---

## 7. TRIPOSPLAT: BETTER LOOKING, NOT PRINTABLE, AND NOT WORTH CONVERTING

**MEASURED**: 262,144 gaussians, 16.1 s, 8,454 MiB peak. Half density (131,072) ran in
6.0 s at 5,303 MiB. Outputs a `.spz` and a 90-frame orbit mp4.

**JUDGED** from the orbit strip: it is comfortably the best-looking result of the whole
job. Full colour, the correct gold bodice and fringed wrap skirt and red boots, a clean
silhouette, stable through a full 360. The mesh candidates are grey untextured geometry
by comparison — Hunyuan3D's GLB carries POSITION and nothing else, no colour, no normals,
no UVs.

**It is not printable and converting it is not worth it.** A gaussian splat is a cloud of
oriented translucent ellipsoids with opacity — it has no surface, no inside and no
outside, so there is nothing for a slicer to fill. Turning one into a printable solid
means either (a) rendering it from many viewpoints and running photogrammetry /
TSDF fusion, or (b) thresholding opacity into a density field and marching-cubes-ing
that. Both throw away the thing that makes the splat good (view-dependent colour) and
both land you back at a noisy iso-surface that needs the same repair Hunyuan3D's output
needs — only starting from worse geometry. Workflow 25's own note says its `SplatToMesh`
convenience output is "noticeably worse than Hunyuan3D's".

**Use TripoSplat for the turntable you show someone. Use Hunyuan3D for the thing you
print.** They are not competitors here.

---

## 7b. TWO THINGS THAT EXERCISED mesh_doctor's UNTESTED PATHS

The other agent flagged island-dropping and repair-failure as code paths the owl never
triggered. Terra triggered both. **MEASURED.**

- **`repair` can fail and say so honestly.** `C_s384` came out of `repair` with
  `fixed_watertight = False` at default settings — the only candidate that did. The tool
  reported it rather than shipping a broken solid. Raising `--voxel-res` is the fix, the
  same dial as section 5.
- **Island dropping works but cannot save a noise mesh.** `E_mv256` had **134** vertex
  islands raw; after repair with the default 1% drop threshold it still had **119**. When
  the input is a speck cloud there is no dominant shell for the threshold to keep. The
  path runs correctly; the mesh was simply unsalvageable.
- **Terra's raw meshes carry real floating debris**, unlike the owl's single island:
  1 island for `B_square` but 4-11 for the others. Every good candidate repaired down to
  exactly **1**.

---

## 8. WHAT I WOULD DO NEXT

1. **Add the base.** Nothing else can be trusted on the plate. A 3-4 mm disc under the
   boots, unioned into the solid.
2. **Get a `hunyuan3d-2mv` checkpoint** if multi-view is still wanted. The four-cardinal
   source set is good and is sitting there unused.
3. **If FDM at 150 mm is a hard requirement**, do not fight it with settings — thicken
   the skirt fringe deliberately, or split the fringe off and print it flat.
4. **Re-run the octree ladder on the owl** to check whether the 28.1% non-manifold figure
   was really an octree-256 artefact. If it was, `craft/PRINTING.md`'s provenance section
   should say so.

---

## 9. HONEST LIMITS OF THIS REPORT

- **No slicer opened any of these files.** None is installed on the box. Watertightness
  is verified by trimesh on reload; that it slices cleanly in PrusaSlicer/Cura/Bambu is
  **not** verified. STL is the safer of the two written formats.
- **No printer.** Every feature-size floor here (FDM 0.8-1.2 mm, resin 0.3 mm, the 45
  degree overhang rule, the material weights) is a rule of thumb, not a machine
  measurement.
- **The renders are my own rasteriser**, not a production renderer. It is orthographic
  point-splatting with a painter's depth sort. Silhouette, surface form and feature
  legibility are trustworthy; it has no shadows, no ambient occlusion and no perspective,
  so it will flatter a shape slightly.
- **`F_mv384`, `G_mv512`, `H_s384_l8192`, `L_s512_basic`, `N_grid2x2` and the MV
  diagnostics were judged from renders only** — they were not put through the full
  repair/thickness/overhang pass, because they had already lost on looks. Their rows in
  `REPORT.json` carry generation numbers and nulls, not failures.
- **One seed per cell**, except the deliberate `J` pair. The octree and threshold
  conclusions rest on one seed each and a large visible effect; the seed-variance finding
  is the caveat on all of them.
- **The 5% under-minimum convention and the 0.015 bed-contact flag are this project's
  own thresholds**, chosen by the previous agent, not industry standards. Treat a failure
  as "stop and look".
- **ComfyUI died once mid-grid** and I could not reproduce it. Host RAM was down to 7 GB
  free at that moment on a shared box; `C_s384` ran fine on retry and every octree
  setting including 512 has since run repeatedly. **It was an environment event, not a
  setting limit** — do not record "octree 384 crashes the server".
