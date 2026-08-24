# RIVALLING MESHY AND TRIPO: WHAT IS ACTUALLY IN THE WAY

The question this document answers is the one that was asked: *is the only way through
Hunyuan3D or TRELLIS, and are those subpar to the paid options?*

The short version: **the model is not the bottleneck, and the gap is smaller than the
framing suggests — but it is real, and almost all of it is pipeline rather than weights.**

Labels, as everywhere in this project: **MEASURED** = measured on this box, with the
measurement quoted. **RULE OF THUMB** = general practice, not measured here.
**JUDGED** = somebody opened the pixels and formed a view. **UNVERIFIED** = stated from
outside knowledge and not checked on this box — treat as a lead, not a fact.

---

## 1. THE FRAMING IS SLIGHTLY WRONG, AND THE WAY IT IS WRONG MATTERS

"Hunyuan3D or TRELLIS vs. the paid options" compares two **models** against two
**products**. Meshy and Tripo are pipelines with a model somewhere inside them. What you
are buying is mostly the pipeline.

The single most useful data point: **TripoSG is Tripo's own open research release.** The
company whose product is the benchmark published a geometry model with open weights. That
does not make the product and the release equivalent — but it does mean "their model is
better than the open ones" is not the explanation, because one of the open ones is theirs.
*(UNVERIFIED as to current version and licence — check before relying on it.)*

The rest of the open field worth knowing about (**UNVERIFIED** — availability, licences and
ComfyUI support all move; this is a shopping list to check, not a ranking to trust):

| what | what it is for |
|---|---|
| **Hunyuan3D 2.x** | what this box runs. 2.1 is the fully-open PBR generation. There are `2mv` (multi-view) and `2mini` variants, and later 2.5 / 3.0 tiers that went API-first. |
| **TRELLIS** (Microsoft) | structured latents that decode to mesh *or* Gaussians *or* radiance field. Its reputation is multi-view consistency — the back of the object not being mush. |
| **TripoSG** | flow-based geometry, large curated training set. |
| **Step1X-3D**, **Direct3D-S2**, **Hi3DGen**, **CraftsMan3D** | the geometry-fidelity front. Direct3D-S2 pushes decode resolution; Hi3DGen goes image → high-res normal map → surface, which is a different and interesting lever. |
| **PartCrafter**, **HoloPart**, **P3-SAM**, **Hunyuan3D-Part** | part-aware generation and segmentation. Underrated for printing — see §4.6. |
| **MeshAnything**, **BPT** | artist-grade topology. Irrelevant here; see §2. |

---

## 2. HALF OF WHAT YOU ARE PAYING FOR DOES NOT APPLY TO THIS PROJECT

Before listing the gap, it is worth deleting the parts of it that are not gaps *for us*.

A commercial image-to-3D product sells roughly six things:

| what they sell | does it matter to a printed bobblehead? |
|---|---|
| **Geometry fidelity** | **Yes. This is the whole thing.** |
| **Printability** — watertight, manifold, thick enough | **Yes, and it is the half nobody advertises.** |
| PBR texture synthesis, 2K/4K maps, real UV unwrap | **No.** It prints in one colour and gets painted. |
| Quad topology, clean edge flow | **No.** A slicer wants triangles and does not care how they are arranged. |
| Auto-rigging, animation-ready output | **No.** |
| Turnaround, queue, UI, credits | **No** — we have a 5090 and a queue of one. |

So four of the six do not apply. That is not a rationalisation: it is the reason a plausible
plan exists at all. We are not trying to match a general-purpose 3D asset product. We are
trying to match it **on geometry and printability of a stylised human figure**, which is the
narrowest and most favourable slice of its job.

And on printability specifically, this box is already ahead of where a raw commercial export
lands, because `mesh_doctor` + `to_print.py` exist and a downloaded `.glb` from anywhere
does not arrive watertight, oriented, or in millimetres. **MEASURED**, `suit_male`: 660,128
faces, watertight, **0 boundary edges, 0 non-manifold edges, 1 shell**, 110.0 mm exactly,
`blocking: []`, in 110 s end to end.

---

## 3. WHERE THE REAL GAP IS

Three things, in the order they cost us quality.

### 3.1 They condition on multiple views. We condition on one.

This is the big one and it is not close.

A commercial pipeline runs **image → multi-view diffusion → 4-6 view-consistent images →
reconstruction**. The geometry model is being told what the back and sides look like. Ours
is shown one photograph of the front and asked to invent the other 270°.

Everything Hunyuan3D gets wrong on our seeds is downstream of that: the back of a jacket is
smoother than it should be, hair behind the head is a mass, a hand tucked behind the back is
a guess.

**MEASURED, and this is why it is not already fixed** (`terra_3d/mesh/VERDICT.md` §3):
`Hunyuan3Dv2ConditioningMultiView` on this box, fed four normalised cardinals, returned
**12,108 faces in 134 islands, 26% non-manifold** — noise, not a worse mesh. The decisive
cell was `MV1_single_img`: the *same pixels* that make an excellent figure through the
single-view node make specks through the multi-view node. The node adds a sincos view
embedding belonging to the **hunyuan3d-2mv** checkpoint, and this box has `hunyuan_3d_v2.1`,
which has never seen one. Tiling four views into one image fails too — 1.16 M faces of
floating slabs. CLIP-vision does not decompose a contact sheet into viewpoints.

So the blocker is **one missing checkpoint file**, not an architecture problem.

### 3.2 They decode at higher resolution than we do — and we cannot follow them.

**MEASURED** (`VERDICT.md` §2) — the surprise finding of the terra run:

| octree | faces | non-manifold edges | as % of edges |
|---|---|---|---|
| 256 | 250,058 | 43,703 | 12.56% |
| 384 | 524,816 | 46,540 | 6.12% |
| 512 | 886,708 | 25,263 | **1.92%** |

Octree resolution was documented as a *detail* dial. It is also a **topology** dial: 256 →
512 cut the non-manifold fraction 6.5×. The obvious next move is 640, 768, 1024.

**That sweep has now been run, and the answer is no. Twice, for two different reasons.**

`bobble.py sweep --id suit_male --values 512,640,768,1024`, seed and every other dial held.

**First wall — an interface limit, not a hardware one.** 640 was rejected before it
reached the GPU:

```
Value 640 bigger than max of 512 · octree_resolution
input_config: ["INT", {"default": 256, "min": 16, "max": 512}]
```

That ceiling is one integer in ComfyUI's own node definition,
`comfy_extras/nodes_hunyuan3d.py:105`. The **VAE beneath it has no such limit** —
`comfy/ldm/hunyuan3d/vae.py:437` simply builds a `linspace` grid of `(N+1)³` points and
decodes it. So the number this project has been living under is a validation range, and it
looked for a moment like the cheapest win on the whole list was one character.

**Second wall — and this one is real.** Raising that integer to 2048 and re-running:

| octree | grid points | result |
|---|---|---|
| 512 | 135 M | **845,780 faces, 0.657% non-manifold, 52.4 s, 10,387 MiB VRAM** |
| 640 | 263 M | **OOM-killed at 15% of volume decoding — 55.6 GB resident** |
| 768 | 455 M | died in the decoder |
| 1024 | 1.08 B | died in the decoder |

`Out of memory: Killed process (python) anon-rss:55568600kB` — on a 60 GB box, with the
**GPU sitting at 11.2 GiB of 32**. The bottleneck was never VRAM.

**And it is not a chunk-size problem either.** `num_chunks` is points-per-chunk in the
volume decoder, so lowering it makes chunks smaller and more numerous — the obvious lever
if peak memory were one chunk of activations. **MEASURED: octree 640 at `num_chunks=2000`
OOM-kills exactly the same way.** (1000 is the node's floor, so there is nowhere further to
go.) The memory is in the `(N+1)³` grid and the surface-net extraction over it, and those
scale with resolution no matter how the decode is fed.

So: **512 is this box's real ceiling**, the reason is system RAM, and the recommendation
that was top of this list is now closed. The node's cap was restored to 512 after the
experiment, because a limit that permits values which reliably kill the server is worse
than the limit.

**And then it turned out not to have been the problem anyway.** The rough surfaces that
motivated this whole section were coming from the *repair* stage, not the decode — see §4.0.
Octree 512 is a real ceiling and a real limitation on how much shape Hunyuan3D can resolve,
but it was not what made the jackets look terraced.

### 3.3 They give you candidates. We generate one and keep it.

**MEASURED** (`VERDICT.md` §2): seed variance is "real and large" — seed 12345 against seed
777, everything else identical, came back with visibly different leg thickness, a shorter
skirt and a different hair fall.

Meshy hands you four results and you pick. We generate one at 55 s and ship it. This is a
pure-arithmetic gap, not a capability gap: three seeds cost 165 s of a machine that is idle
anyway, and `mesh_doctor` can already score them.

### 3.4 Delighting — which we have now done, and it is the cheapest thing on this page

Commercial pipelines *delight* the input — strip baked shadows and speculars before
reconstruction — because a geometry model sculpts what it sees, and a shadow in the crease
of a sleeve becomes a groove in the mesh.

The figurine grammar already pushes `cast shadow` into the negative prompt, which kills the
shadow *on the floor*. It does nothing about form shading on the subject. So the head path
now runs an explicit delight-and-restyle pass — `bobble.stage_stylize`, one
`22_qwen_edit_2511` edit with a flat-albedo instruction — and **JUDGED** on `stand_in`, a
portrait shot with real directional window light, it returned the same face with the
shading removed, the hair closed into one grooved mass, the background flat and the crop at
the neck. 15 s on a 164 s pipeline.

**It is not applied to bodies yet**, because the body seeds are generated rather than
photographed and their grammar already asks for flat frontal light. Whether a second
explicit pass still helps there is the A/B nobody has run — see §4.4.

---

## 4. THE ORDERED LIST, MOST LEVERAGE FIRST

Written so each item says what it costs and how we would know it worked.

### 4.0 THE ONE THAT WAS NOT ON THIS LIST, AND WAS THE ACTUAL PROBLEM — DONE
**Cost: under a second per part. Nothing to download, nothing to buy.**

Every surface in the first library was visibly stair-stepped, and this document blamed the
octree ceiling for it. **That was wrong**, and the way it was wrong is the most useful thing
on this page.

**MEASURED**, same shoulder crop off four meshes at 12 M splat samples: Hunyuan3D's **raw**
output is *smooth*. Every `repair --method voxel` result is stepped — 489, 900 and 1200
differ only in how fine the staircase is, never in whether there is one. Surface-net
extraction places vertices at sub-cell positions; the voxel repair re-rasterises to binary
occupancy and re-extracts, and that rasterisation is the staircase.

**So raising the octree would not have improved these surfaces at all.** The dial nobody
could turn was being blamed for damage done two stages later by a dial that was free.

The fix is a **Taubin pass** after the repair, before the cut: volume kept to **100.017%**,
still watertight, surface moved by **mean 0.024 mm / max 0.117 mm**, and the hands, fingers,
jacket vent and pocket flaps all survive. `craft/BOBBLEHEAD.md` §4 has the full measurement.

**The lesson worth carrying:** the pipeline stage that hurt most was the one nobody was
looking at, three stages downstream of the one everybody was arguing about. Before buying
RAM or a checkpoint, check what your own post-processing is doing to the surface.

### 4.1 ~~Sweep the octree above 512~~ — DONE, and it is closed
**Result: 512 is the ceiling on this box, and the limit is system RAM.** See §3.2 for the
run. Two things follow, and they replace this item:

- **More RAM is a real upgrade path, and it is the only one on this list you can buy.**
  640 died at 55.6 GB of 60. A 128 GB box would clear it and probably 768 too, and §3.2
  says the reward is a lower non-manifold fraction and a sharper face — the thing Meshy's
  resolution advantage actually buys. Nothing else here is fixed by hardware.
- **Or move the decode out of ComfyUI's node.** The VAE has no resolution limit; the
  memory goes into materialising the whole `(N+1)³` grid at once. A decoder that swept the
  volume in slabs and streamed the surface out would not need it. That is real work, and
  it is the kind of engineering the paid tools have done and we have not.

Everything below is unchanged and 4.2 is now the top item.

### 4.2 Get a multi-view path working — the biggest single quality jump
**Cost:** one checkpoint download, then plumbing.
Two routes, and they compose:

- **(a) Fetch `hunyuan3d-2mv`.** This unblocks `Hunyuan3Dv2ConditioningMultiView`, which is
  already wired in `terra_mesh.graph_hunyuan` and currently produces noise for exactly one
  reason. Cheapest real win available.
- **(b) Generate the views we feed it.** *This box already has the parts.*
  `workflows/32_qwen_turnaround.json` is a multiple-angles LoRA that `foundry_routes.py`
  already drives: one image of a subject in, the same subject from a named angle out. That
  is the multi-view diffusion stage of a commercial pipeline, sitting on disk, being used for
  character sheets instead. Feed front/left/back/right into (a).

**Success:** the back of a jacket stops being smoother than the front, and hair behind the
head gains structure. Judge it by opening the 180° orbit frame against the 0°.

### 4.3 Generate three seeds and let mesh_doctor pick
**Cost:** 3× the mesh stage — 165 s instead of 55 s per body. No new code beyond a scorer.
Score on what is already in `diagnose`: island count, non-manifold fraction, and the
sub-millimetre surface fraction from `mesh_doctor thickness`. Keep all three on disk;
show the winner and let the page offer the others, the way `/model3d` already shows losing
candidates.
**Success:** the failure rate of "this body came out with a fused arm" drops, and the
library stops depending on a lucky seed.

### 4.4 Extend the delight pass from heads to bodies
**Cost:** one A/B. The pass already exists — `bobble.stage_stylize` — and heads already use
it (§3.4). The question is only whether a generated body seed, which was already asked for
flat frontal light, still has form shading worth removing.
**Success:** creases that were shading stop being geometry. Measure it as thickness
distribution: a sleeve crease sculpted from a shadow shows up as thin surface in
`mesh_doctor thickness`.
**This is the one on the list most likely to do nothing**, and it is now cheap enough to
find out that not finding out is the only mistake.

### 4.5 Add a second geometry model and make it a bake-off
**Cost:** an install and an evaluation harness. **UNVERIFIED** which of TRELLIS / TripoSG /
Step1X-3D installs cleanly against this ComfyUI; that is the first thing to find out.
The value is not "the other one is better" — it is that **different models fail differently**,
and with `mesh_doctor` as an automatic scorer a per-object bake-off picks the winner without
anybody opening a viewer. That is a thing a paid product cannot do for you, because it only
has its own model.
TRELLIS is the most interesting first pick for this project specifically: its stated strength
is multi-view consistency, which is §3.1, and it decodes to Gaussians as well as mesh — this
box already has a TripoSplat path in `terra_mesh.graph_triposplat` to compare against.

### 4.6 Part-aware splitting, for printing rather than for looks
**Cost:** real work. **UNVERIFIED** tooling.
A pose with arms away from the torso needs supports, and supports leave scars on the exact
surfaces a figurine is judged on. Part segmentation → print the arms separately → glue is
what a professional print service does. It also lets each part be oriented for its own best
surface finish.
This is the item that would let the catalogue stop avoiding poses, and the figurine grammar
currently spends three of its rules avoiding them.

### 4.7 Normal-bridged surface refinement
**Cost:** the most, and the most speculative. **UNVERIFIED.**
Hi3DGen's approach — predict a high-resolution normal map from the image, use it to refine
the surface — targets exactly what a latent-space model cannot hold: crisp cloth folds,
button edges, hair grooves. Worth reading before building, and worth doing only after 4.1
and 4.2 have found their ceiling.

---

## 5. SO: IS THE OPEN PATH SUBPAR?

**For a textured game asset:** yes, meaningfully. The texture, UV and topology stack is where
most of the commercial engineering has gone, and none of it is reproduced here.

**For a printed bobblehead body:** no, and the measurement says so. **MEASURED across the
whole first library — 24 bodies and one head, every one of them watertight, one shell, zero
non-manifold edges, dimensionally exact, `blocking: []`, at 85–165 s each** — and they went
through a print-preparation path that a commercial export does not include, so the file that
lands is closer to sliceable than a downloaded `.glb` would be.

The failures in that run were **not** geometric. Every one of them was the seed image or
the cut: a cape the negative prompt could not remove, a guitar neck sticking out of the
silhouette, a figure rendered back-on, and a neck-finder that cut three bodies through the
chest. Those are prompt and algorithm bugs, and all four are fixed. *Nothing failed because
Hunyuan3D was not good enough.*

**The honest caveat**, and it should not be buried: *nothing in this library has been
printed.* `printable: true` means `mesh_doctor diagnose` returned an empty `blocking` list.
That is the strongest claim available without a printer, and it is not the same claim as
"this came off the plate and looks right". The first print is the measurement that would
settle most of this document, and it costs an afternoon and a spool.

### Is it a RAM limitation?

Only for one item, and not the one that mattered. Setting the record straight, because this
document spent a whole revision pointing at the wrong thing:

| lever | blocked by | status |
|---|---|---|
| **Voxel-repair staircase** (§4.0) | *nothing* | **fixed** — a Taubin pass, under a second |
| Octree above 512 (§4.1) | **system RAM** | closed on this box; 128 GB would open it |
| Multi-view conditioning (§4.2) | one checkpoint download | **open, and now the top item** |
| Three seeds and pick (§4.3) | GPU minutes | **open** |
| Delight the body seeds (§4.4) | nothing | **open**, and already built for heads |
| Second model, bake-off (§4.5) | an install | **open** |
| Part-aware splitting (§4.6) | real work | open |
| Normal-bridged refinement (§4.7) | real work | open |

**One of eight is RAM-blocked.** The single biggest quality lever available — multi-view
conditioning — needs one checkpoint download, and its multi-view *generator*, normally the
hard half, is already on this disk being used for character sheets.

**And the thing worth doing first was never on the shopping list at all.** It was a
post-processing stage we had written ourselves.

**A note on how to read the UNVERIFIED table in §1.** Three of the four items on this page
that got measured came back *against* the plan: the octree ceiling was a validation range
hiding a memory wall, the delight pass turned out to matter more for heads than the place it
was proposed for, and the surface roughness everyone was attributing to the model was our
own repair stage. The model shopping list has not been checked at all. Check it before you
buy the argument.
