# THE STAND-IN - print card

*Anime-first arm (B_anime). The photo-direct control is measured at `_work/CONTROL_photo_150mm_audit.json`; see `../mesh/VERDICT.json` for why this one shipped.*

**File to load: `STANDIN_150mm.stl`**

One closed solid. Millimetres, Z-up, standing on its own plinth, bottom face
already on z = 0. Drop it in the slicer and it lands the right way up at the
right size - no scaling, no rotating, no repair step.

Every number below is labelled. **MEASURED** was measured on this exact file.
**ESTIMATE** is arithmetic from measured quantities. **RULE OF THUMB** is
general hobby practice and was not tested on a printer - no printer was ever
identified for this project.

## The file

| | |
|---|---|
| Size | **91.3 x 78.0 x 150.0 mm** (w x d x h) MEASURED |
| Solid volume | **93.8 cm3** MEASURED |
| Surface area | 278 cm2 MEASURED |
| Triangles | 2,991,008 MEASURED |
| Watertight | **yes** - 0 open edges, 0 non-manifold edges, 1 body MEASURED |
| Sits at | z = 0, centred on X/Y MEASURED |

## Recommended settings

| | Resin (MSLA) - **preferred** | FDM (0.4 mm nozzle) |
|---|---|---|
| Layer height | 0.03 - 0.05 mm | 0.12 - 0.16 mm |
| Supports | **yes**, auto, medium | **yes**, tree/organic |
| Orientation | as supplied, or tilted 15-20 deg | as supplied, plinth down |
| Material | ~103 g resin (~122 g with supports) ESTIMATE | ~42 g PLA, ~14.1 m of 1.75 mm ESTIMATE |
| Layers | 3,000 at 0.05 mm | 750 at 0.2 mm |
| Time | ~2.5 - 3.5 h RULE OF THUMB (MSLA time follows height, not volume) | ~14 - 22 h RULE OF THUMB |

FDM material assumes 0.84 mm shell (2 perimeters), 15% infill, PLA 1.24 g/cm3, 1.75 mm filament.
Add roughly 15-25% for support material. RULE OF THUMB - your slicer's own
estimate supersedes all of this.

**Why resin is preferred:** the minimum feature enforced here is 1.0 mm, which
clears a 0.4 mm nozzle, so FDM will physically print. But her face is ~20 mm
tall and her eyes and mouth are sub-millimetre relief; a 0.4 mm nozzle cannot
resolve them. FDM gives you the silhouette and the costume, not the face.

## Will it print - the honest answer

| | |
|---|---|
| Surface thinner than 0.80 mm | **0.01%** MEASURED |
| Surface thinner than 0.30 mm | **0.00%** MEASURED |
| Thinnest 1% of surface | 2.55 mm MEASURED |
| Median wall thickness | 10.8 mm MEASURED |
| Overhanging past 45 deg | **2.0%** of surface MEASURED |
| Of that, nothing beneath it | 10% - support from the plate MEASURED |
| Near-horizontal ceilings | 0.6% of surface MEASURED |
| Bed contact | 4787 mm2 MEASURED |

Where the remaining thin material is (share of all sub-0.80 mm surface):

- **head and face** - holds 50% of it; 0.1% of that region's surface is thin
- **boots and ankles** - holds 25% of it; 0.0% of that region's surface is thin
- **hair crown and ribbon** - holds 25% of it; 0.0% of that region's surface is thin
- **plinth** - holds 0% of it; 0.0% of that region's surface is thin

Where the supports go (share of all overhanging surface):

- **hips, wrap skirt, hair fall** - 40% of it
- **head and face** - 21% of it
- **outstretched arms** - 11% of it
- **boots and ankles** - 7% of it

## Do you need to split it?

**No.** MEASURED reasoning, not a preference:

- It is 91 x 78 x 150 mm. That fits the build volume of every consumer
  FDM printer and every consumer MSLA machine except the smallest.
- Only **2.0%** of the surface overhangs past 45 deg, and only **10%** of
  that has nothing beneath it. That is an ordinary support job, not a
  split-and-peg job.
- The hardest case is the **outstretched arms**: they are near-horizontal
  cantilevers, and they carry the densest overhang of any band (4% of that
  band's own surface, against 2% for the torso). A waist or neck cut would
  not help them at all - they hang off the torso, so the only cut that reaches
  them is at the shoulder, through a ~5 mm arm. That puts a visible seam and a
  peg on a bare shoulder, to save supports you were going to print anyway.

If you want to split it regardless, cut at the waist under the wrap skirt where
the seam hides in an existing costume line, and use a 4 mm peg with 0.15-0.2 mm
clearance. RULE OF THUMB - not done here, and not needed.

## The plinth

78.0 mm diameter, 6.0 mm thick, 1.5 mm chamfer on the top edge, flat
underside for bed adhesion. The figure is sunk 1.2 mm into it, so it is one
fused solid, not two parts touching. MEASURED

It is not decoration. Her boots are pointed with a raised heel, so bare she
stands on two small triangles - the previous stage measured 201 mm2 of bed
contact, against **4787 mm2** with the plinth. Her centre of mass also sits
**3.2 mm behind her feet** (the hair mass), which is 8% of the plinth
radius - comfortably inside it, so she balances. MEASURED

## What was done to the mesh, and what it cost

| | Before | After |
|---|---|---|
| Open (boundary) edges | 116 | **0** |
| Non-manifold edges | 11,417 | **0** |
| Disconnected shells | 1 | **1** |
| Winding consistent | False | **True** |
| Sliceable solid | False | **True** |

MEASURED. The repair is a voxel remesh at 0.15 mm, not a hole fill - a
Hunyuan3D surface is pinched against itself and no surface-local repair can
open that. Detail below 0.15 mm is gone; at this size that is under the FDM
nozzle floor anyway.

## Known compromises

- **Her hair is one fused mass, not separate strands.** Hunyuan3D already reconstructed it as fat fused sausage locks rather than hair, and the crevice closing merged the near-touching ones further. This is what a commercial statuette does on purpose, and it is why the hair is not the thin-feature problem you would expect - it is among the THICKEST material in the model.
- **The skirt fringe the source render showed as many separate hanging strands is gone**, absorbed into the skirt panel. Nothing that fine can exist at 150 mm in any process.
- **The face is soft.** It is legible - lidded eyes, nose, mouth, ribbon, earrings - but it is a ~20 mm head reconstructed from a single image, not a sculpted one. Resin will show what is there; FDM will not.
- **Untextured.** Hunyuan3D's output carries geometry only, no colour. If you want to see her in colour, look at the TripoSplat orbit the mesh stage rendered - but a splat cannot be printed.
- **The solid carries a few dozen small tunnels** through it (genus ~43), left over from reconstruction noise. A slicer only needs inside vs outside, so this should not matter, and none was visible in the turntable or head renders. Not proven harmless by actually slicing it.
- **No slicer has opened this file.** None is installed on the box. Watertightness is verified by re-reading the written file and re-measuring it, which is a strong check, but it is not the same as PrusaSlicer/Cura/Bambu/Lychee ingesting it. This is the single largest remaining gap.
- **No printer, so every feature-size floor here is a rule of thumb.** FDM 0.8-1.2 mm, resin ~0.3 mm and the 45 degree overhang rule are general practice, not measured on a machine.

## Files

| File | Size | Verified on reload |
|---|---|---|
| `STANDIN_150mm.stl` | 150 MB | watertight, 2,991,008 faces, 91.35 x 78.00 x 150.00 mm |
| `STANDIN_150mm.3mf` | 26 MB | watertight, 2,991,008 faces, 91.35 x 78.00 x 150.00 mm |
| `STANDIN_150mm.glb` | 54 MB | watertight, 2,991,008 faces, 91.35 x 78.00 x 150.00 mm |

Every file above was written, re-read from disk and re-measured. MEASURED

### Alternates in `alt/`

Only take one of these if the primary gives you trouble. All three are
watertight single solids at 150.0 mm, verified the same way.

| File | Why you would use it |
|---|---|
| `TERRA_150mm_lighter-file.stl` | Half the triangles (1.8M, 91 MB) if your slicer struggles with the primary. Built on a 0.20 mm grid instead of 0.15 mm. Printability is the same; the **face is visibly softer** - shallower eyes, flatter nose. That is why it is not the primary. |
| `TERRA_150mm_resin-detail.stl` | Lighter intervention: 0.60 mm minimum feature instead of 1.00 mm, gentler crevice closing. Slightly crisper detail, but 0.67% of surface under 0.80 mm against the primary's 0.21%. Resin only. |
| `TERRA_150mm_minimal-edit.stl` | Repaired and based, but **no** thickening and **no** closing. Closest to what Hunyuan3D produced. 1.23% of surface under 0.80 mm and 0.52% under 0.30 mm - expect fine detail to fail. For comparison, or for a high-resolution resin machine. |

