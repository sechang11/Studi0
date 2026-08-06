# PRINTING

The spec this project holds a mesh to before it is called printable, and the reasoning
behind every number in it.

A `.glb` that looks right in a viewer is not a print. A viewer draws triangles; a slicer
has to decide, for every horizontal plane, which side of the surface is plastic. Those
are different demands, and generated meshes routinely satisfy the first and fail the
second. Everything below exists to catch that gap before seven hours of GPU time turns
into an unsliceable file.

**Every threshold here is labelled.** MEASURED means it was measured on this box, on our
own output, and the measurement is quoted. RULE OF THUMB means it is standard practice in
the hobby-printing world, widely agreed but not measured here — treat it as a starting
value to be checked against your own printer. HARD means it is a property of the file
format or of slicer software, not a preference.

The tool that enforces all of this is `studio/_tools/mesh_doctor.py`.

---

## 0. The headline finding

**Hunyuan3D output is not watertight, and the failure is not holes.** MEASURED, on
`~/ComfyUI/output/claude-generated/21-3d-generation/hunyuan3d_mesh_00001_.glb` (the owl,
produced by `workflows/24_hunyuan3d_mesh.json`, VAE decode at octree resolution 256,
`VoxelToMesh` algorithm `surface net`, threshold 0.6):

| property | value |
|---|---|
| vertices / faces | 187,314 / 525,708 |
| unique vertex positions | 187,314 — already welded, nothing to merge |
| duplicate faces | 0 |
| degenerate faces | 0 |
| boundary (open) edges | **160** |
| non-manifold edges (3+ faces) | **190,005 of 675,541 — 28.1%** |
| islands (vertex-connected) | **1** — no floating debris |
| is_watertight | **False** |
| is_winding_consistent | **False** |
| normals point outward | True (signed volume positive) |

Read that table carefully, because the obvious reading is wrong. Only 160 edges are open.
The mesh is essentially hole-free. What is wrong is that **28% of its edges have three or
four faces on them** — the surface is pinched against itself and carries interior
membranes. Marching-cubes-family extractors do this when the field is noisy near the
isosurface.

Two consequences that shape the whole job:

1. **Hole-filling will not fix it.** `fill_holes` on the owl moved the Euler number by
   zero. There are no meaningful holes to fill. Surface-local repair cannot remove a
   membrane that is welded to the outer skin along a shared edge.
2. **Thickness measured on the raw mesh is a lie.** A thickness ray fired inward stops on
   the first surface it meets, and on this mesh that is usually an interior membrane. The
   raw owl measures a median wall thickness of 0.71 mm at a 150 mm print height, which
   would condemn 59% of its surface as unprintable. After repair the same measurement on
   the same object gives a median of 6.9 mm and 0.35% below 1 mm. The first number is
   measuring reconstruction junk. `mesh_doctor.py thickness` now refuses to present its
   numbers without a loud warning when the input is not a closed solid.

Also worth knowing before Terra is generated: trimesh reports **143,993 connected
components** for this mesh, and that number is an artefact, not debris. trimesh builds
face adjacency only across edges shared by exactly two faces; the 190,005 non-manifold
edges are excluded, which shatters the graph. Counted by vertex connectivity the mesh is
**one island**. `mesh_doctor.py diagnose` prints both and labels which is which. Do not
report the big number.

### What actually fixes it

Voxel remesh: rasterise the surface into a grid, flood-fill the interior, re-extract with
marching cubes. The fill absorbs interior membranes and self-intersections because they
are simply inside the solid. MEASURED on the owl at resolution 320 with orthographic fill:

| | before | after |
|---|---|---|
| boundary edges | 160 | **0** |
| non-manifold edges | 190,005 | **0** |
| watertight | False | **True** |
| winding consistent | False | **True** |
| is_volume | False | **True** |
| volume (model units) | 0.4206 | 0.4395 (+4.5%) |

Cost: detail below one voxel is gone. At resolution 320 on a 150 mm print that voxel is
**0.62 mm** — comfortably under the FDM feature floor, so for FDM the repair costs nothing
you could have printed anyway. For resin, where the floor is ~0.3 mm, raise the resolution.

The fill method matters. MEASURED on the owl, surface rasterises to 277,816 voxels, then:
`base` fills to 1,840,510; `holes` to 1,879,005; `orthographic` to **1,906,073**.
Orthographic fills 3.6% more interior than `base` and is the `mesh_doctor` default,
because a leaky surface lets the simpler fills escape.

Residual after repair: genus ~41 (MEASURED) — the solid carries around forty small tunnels
through it. Harmless for printing; they are reconstruction noise, not holes in the shell.

---

## 1. Watertight and manifold — non-negotiable

HARD. A printable mesh is a **closed orientable 2-manifold with consistent outward
normals**. Concretely, four conditions, all of which `diagnose` checks:

- **No boundary edges.** Every edge is shared by exactly two faces. An edge with one face
  is a hole, and the slicer has no way to know which side is solid.
- **No non-manifold edges.** No edge shared by three or more faces. This is the one that
  Hunyuan3D fails, at 28%.
- **Consistent winding.** All faces wound the same way round, so "outward" is well defined
  everywhere.
- **Outward normals.** Signed volume positive. A negative volume means the model is
  inside-out and the slicer will fill the room and hollow the owl.

Slicers vary in how much they will paper over. Modern Cura/PrusaSlicer/Bambu Studio run
their own mesh fixing and often produce *something* from a broken mesh. That something is
not predictable and is not what you modelled. Fix it upstream.

**Check:** `mesh_doctor.py diagnose <mesh>` — exits nonzero if anything is blocking.
**Fix:** `mesh_doctor.py repair <mesh> --out fixed.glb` (defaults to `--method auto`:
conservative surface repair first, voxel remesh only if that was not enough).

---

## 2. Minimum feature size

This is the number that decides whether Terra's hair prints.

| process | minimum printable feature | source |
|---|---|---|
| FDM, 0.4 mm nozzle | **0.8 – 1.2 mm** | RULE OF THUMB |
| FDM, 0.2 mm nozzle | ~0.5 mm | RULE OF THUMB |
| Resin / MSLA | **~0.3 mm** | RULE OF THUMB |

The FDM figure is two to three extrusion widths. A 0.4 mm nozzle lays a bead roughly
0.4–0.45 mm wide; a wall thinner than two beads has no interior and the slicer will either
drop it entirely or produce a single wandering bead with no strength. 0.8 mm is the
optimistic end (two perimeters, fragile); 1.2 mm (three) is what survives handling. **Use
1.0 mm as the project default and 1.2 mm for anything that will be touched.**

Resin has no bead width — the limit is pixel size and the green strength of a
part-cured feature during peel. ~0.3 mm is the common working figure for a feature that
survives washing and curing; finer detail resolves optically but snaps off.

### What this means for TERRA specifically

At a 150 mm figurine height, a head is roughly 20 mm. A hair strand rendered as a distinct
tapering lock is on the order of 1–3 mm at the root and goes to zero at the tip. **The tip
of every lock is below the FDM floor by construction, and the ribbon and cape edge will
be too.** This is not a defect to be fixed by a better generation; it is geometry that
cannot exist at this scale in this process. The options are, in order of preference:

1. **Print resin.** Drops the floor from ~1.0 mm to ~0.3 mm.
2. **Scale up.** Feature thickness scales linearly with model height. Doubling to 300 mm
   halves the fraction below threshold.
3. **Thicken deliberately.** Accept a chunkier, more stylised silhouette — which is what
   commercial figurines do anyway; look at any production statuette's hair and it is
   fused into slabs, not strands.
4. **Split and reorient** so the thin parts print flat rather than as unsupported spires.

**Check:** `mesh_doctor.py thickness <mesh> --height 150 --min-mm 1.0`

The measurement is the **Shape Diameter Function**: from ~40,000 points sampled uniformly
by area on the surface, fire a cone of nine rays inward around the surface normal and take
the median distance to the far wall, rejecting hits on walls that face the same way the
ray is travelling. That median is the local feature thickness. It is the same family of
measurement Meshmixer and Netfabb use for wall-thickness analysis. It costs about one
second on 576k faces with embree.

The report gives the full percentile distribution, the fraction below threshold, and a
by-height-decile breakdown so you can see *where* the thin material is — for a figure,
expect the answer to be "the top decile", which is the hair.

**Tolerance:** the tool exits nonzero above 5% of surface under the minimum. That 5% is a
project convention, not a physical constant. Treat it as "stop and look", not "fail".

---

## 3. Overhangs and supports

RULE OF THUMB, and the most universally cited number in FDM: **anything more than 45° from
vertical needs support.** The reasoning is geometric — at 45° each layer overlaps the one
below by half its width, which is enough for the bead to bond and not droop. Past that,
the overlap shrinks and the bead is extruded into air.

45° is conservative-to-typical. Well-tuned machines with good part cooling manage 55–60°
on short spans. Bridges (a downward face with anchored ends) are a separate case and can
span tens of millimetres unsupported.

Resin has an analogous but different constraint: the limit is not droop but **peel force**.
Large flat downward-facing areas suction to the FEP and tear off the plate. Resin prints
are therefore usually tilted 20–30° so that no layer presents a large flat cross-section,
and supports exist to take peel load rather than to hold up drooping plastic.

For a figure the offenders are predictable: **long hair, a cape, an outstretched arm, and
the underside of the chin and jaw.**

**Check:** `mesh_doctor.py overhang <mesh> --height 150`

Three things it reports that a naive angle count does not:

- **Bed contact is excluded.** Faces sitting on the build plate point straight down but
  are supported by the plate. MEASURED on the repaired owl: counting them gave 27.1%
  overhang; excluding them gives **4.25%**. A model with a flat base would otherwise
  report a quarter of its surface as overhanging on the base alone.
- **Overhangs with nothing beneath them** are found by casting a ray straight down. These
  are the expensive ones — support has to be built all the way from the plate, and it will
  leave marks on a visible surface.
- **A by-height histogram**, so you can tell a cape hem at z=40 from a fringe at z=140.

---

## 4. Scale, orientation and units

HARD. A generated mesh arrives in arbitrary units. The owl arrives with a longest extent
of 1.96 and trimesh reports its glTF units as "meters", which is a convention of the file
format and says nothing about intent.

- **glTF/GLB is Y-up.** HARD, it is in the specification.
- **STL and every slicer are Z-up.** HARD. The rotation is not optional; skip it and the
  figure loads lying on its face.
- **Drop to z = 0 and centre on X/Y.** Convention, and it means the file opens sitting on
  the plate instead of buried under it or floating.
- **STL carries no units.** HARD — the numbers in the file are bare floats and every
  slicer reads them as millimetres. So the export must already be in millimetres. **3MF
  does carry units** and is the better format for that reason; write both.

**Target height: 150 mm for a figurine.** Project convention, chosen because it sits in
the normal 100–200 mm range for a display figure, fits every common printer's build
volume including a 180 mm Mars-class resin machine, and gives a ~20 mm head, which is
enough for a face to read.

**Check / fix:** `mesh_doctor.py scale <mesh> --height 150 --up y --out scaled.glb`

It reports the scale factor, final bounding box in mm, surface area, solid volume, and a
material estimate. MEASURED on the repaired owl at 150 mm: 197.3 × 105.7 × 150.0 mm,
442.7 cm³ solid, ~110 g of PLA at two walls and 15% infill, ~509 g as solid resin. The
20%-of-solid figure behind the PLA estimate is a RULE OF THUMB.

---

## 5. A base

RULE OF THUMB, and a mechanical argument rather than a measurement. A tall figure standing
on two boot soles has a bed contact area of a few tens of mm² carrying 150 mm of leverage.
Every layer change nudges it; the first knock separates it from the plate and the print
becomes spaghetti. Resin is worse, not better — peel force pulls *up* on that same tiny
contact patch on every single layer.

So: a figurine gets a base. A disc or plinth, ideally 1.2–2 × the footprint of the feet,
2–4 mm thick, fused to the soles. It is also what makes the object display properly, so
this is not a compromise.

`mesh_doctor.py overhang` reports **bed contact area divided by height squared** and flags
`needs_base` below 0.015. That threshold is a project convention — it is the point where
contact area stops being large enough to resist the moment from a model that tall. MEASURED
on the repaired owl: 0.93, no base needed, because the owl has a large flat underside. A
standing Terra will be nowhere near it.

---

## 6. Floating and disconnected shells

Generated meshes often carry stray islands — a speck of geometry floating beside the
model. A slicer will happily print them as debris welded into the part.

The owl has **none**: MEASURED, one vertex-connected island. That is a genuinely good sign
for Hunyuan3D and one fewer thing to plan around for Terra.

`repair` drops islands below `--min-component-frac` (default 0.01, i.e. 1% of the largest
by face count), counted by **vertex** connectivity. Face-adjacency counting is unusable
here for the reason given in section 0.

---

## 7. When to split

A part gets split when no single orientation makes it printable:

- An overhang that cannot be supported without wrecking a visible surface — support scars
  on a face are unfixable.
- A feature thinner than the floor in every orientation, which needs to be printed flat
  and glued.
- A model taller than the build volume.
- Resin, where a large flat cross-section at any height means peel forces that will rip
  the part off.

Split on a plane, and add a **registration peg** — a 3–4 mm cylinder with 0.15–0.2 mm
clearance on the socket. RULE OF THUMB: below ~0.1 mm clearance the parts will not go
together after the print's own dimensional error; above ~0.3 mm the joint is sloppy and
the seam shows. Put the split where a seam is already expected — a belt line, a neckline,
the join between cape and body.

---

## 8. The order to run things in

```
mesh_doctor.py diagnose  mesh.glb                                   # what am I holding
mesh_doctor.py repair    mesh.glb --out fixed.glb                   # make it a solid
mesh_doctor.py diagnose  fixed.glb                                  # confirm it worked
mesh_doctor.py scale     fixed.glb --height 150 --up y --out f150.glb
mesh_doctor.py thickness f150.glb --in-mm --min-mm 1.0              # will the hair print
mesh_doctor.py overhang  f150.glb --up z                            # what needs support
mesh_doctor.py export    fixed.glb --height 150 --up y \
                         --out terra.stl --out terra.3mf
```

`diagnose` and `thickness` exit nonzero on failure, so this chains under `set -e`.
`export` refuses a non-watertight mesh unless given `--force`, and re-loads what it wrote
to prove the file on disk is still a closed solid. Every subcommand takes `--json`.

**Do not skip the second `diagnose`.** Repair reports its own success; verifying it from
the written file is what catches an exporter that quietly degraded the mesh.

---

## 9. Toolchain

Installed with `python3 -m pip install --user`, no root, on the Fedora box under system
Python 3.14.6:

| package | version | why |
|---|---|---|
| trimesh | 5.0.0 | mesh loading, topology, repair, voxelisation, export |
| numpy | 2.5.1 | required by trimesh |
| scipy | 1.18.0 | sparse connected-components for island counting |
| networkx | 3.6.1 | trimesh graph operations |
| rtree | 1.4.1 | spatial indexing |
| shapely | 2.1.2 | cross-section polygon area |
| manifold3d | 3.5.2 | boolean operations, available for splitting work |
| **embreex** | 4.4.0 | **fast raycasting — thickness and support checks are ~1 s instead of minutes** |
| **scikit-image** | 0.26.0 | **marching cubes; the voxel repair path does not work without it** |
| pillow | 12.3.0 | already present, texture handling |

The two in bold are not optional. Without `scikit-image` the voxel repair — the only thing
that makes Hunyuan3D output watertight — raises `ModuleNotFoundError` inside trimesh.
Without `embreex` trimesh silently falls back to a pure-Python ray intersector and the
thickness pass becomes unusable on a half-million-face mesh.

Note the ambient hazard: **numpy is not in the system Python by default on this box** — it
lives in the ComfyUI venv. The `--user` install above puts it in
`~/.local/lib/python3.14/site-packages`, so `mesh_doctor.py` runs under plain `python3`.
