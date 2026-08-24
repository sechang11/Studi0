# BOBBLEHEAD: two solids and a spring

The section that builds these is `/three`. The tool is `studio/_tools/bobble.py`. The print
spec everything here defers to is `craft/PRINTING.md`.

A bobblehead is not one model. It is a **body**, a **head**, and a **spring** that glues
into a socket in each. That makes the whole job mechanical rather than artistic: what has
to be true at the end is that two blind holes of a known diameter exist at a known place on
two flat faces, at the same size in millimetres, on parts that a slicer will accept.

Everything below is either **MEASURED** on this box with the measurement quoted,
**RULE OF THUMB** (general practice, not measured here), or **JUDGED** (somebody opened the
pixels and formed a view).

---

## 1. THE ASSEMBLY

```
        head.glb            printed at 95 mm
        ┌──────────┐
        │          │        socket: Ø8.4 mm × 14 mm deep, bored UP from
        │    ▲▲    │        the flat under the jaw, 1.2 mm chamfered mouth
        └───┬──┬───┘
            ││              spring: 8 mm OD compression spring,
            ││              ~20-25 mm free length, glued both ends
            ││
        ┌───┴──┴───┐
        │          │        socket: Ø8.4 mm × 12 mm deep, bored DOWN into
        │  body.glb│        the neck stump, 1.2 mm chamfered mouth
        └──────────┘        printed at 110 mm
```

**The 0.4 mm.** The socket is Ø8.4 mm for an 8.0 mm spring: 0.2 mm of radial clearance for
glue and for the printer's tendency to make holes undersize. **RULE OF THUMB** — not
measured on a print yet. If the spring rattles, drop `GEOM["socket_d"]` to 8.2; if it will
not seat, raise it. That constant is in one place in `bobble.py` and both parts read it.

**The chamfer** is a 1.2 mm cone at the mouth of each socket. It is there so the spring
finds the hole under thumb pressure instead of catching the rim. It also gives the glue
somewhere to go rather than being scraped off on the way in.

**Total height** is body + spring free length + head. **MEASURED**, `suit_male` +
`stand_in`: 110 + 22 + 95 = **227.0 mm** standing. The two heights are arguments
(`--height`); change either and the sockets stay the same size, because they are bored
after scaling.

```bash
python3 studio/_tools/assemble.py --body suit_male --head stand_in
```

writes a **preview** stack — the three parts at their real heights, with the spring drawn
as a swept helix — and prints whether the two sockets agree. It appears on `/three` under
*Assembled*. It is not a print file and must not become one: the parts print separately,
which is the entire point of the socket, and a printed PLA spring is a spring once. What
it is for is the check nothing else performs — that two parts sized and socketed
independently actually meet.

---

## 2. WHY THE HEAD IS CUT OFF INSTEAD OF NOT DRAWN

The first plan was to ask the image model for a headless body. Image models render nouns
and are poor at absence: you get a head anyway, or a stump drawn as a wound.

So the seed asks for a **complete figure**, which is the thing the model is good at, and the
head is removed from the **mesh** by a plane cut. A plane cut cannot misunderstand the
instruction. It also leaves a real neck cross-section to bore into, which a prompted stump
would not.

### Finding the neck, and the three versions it took

`bobble.neck_plane` measures the enclosed area of the horizontal cross-section at 240
heights and picks one. Getting that pick right took three attempts, and the two failures
are more useful than the success, so they are recorded here rather than deleted.

The whole story is visible in one column of `bobble.py report` — the **joint diameter**,
which is the equivalent diameter of the cross-section the cut actually landed on. A neck on
a 110 mm body is 14–28 mm. Anything far outside that is the finder telling on itself, and
that is the entire reason the number is printed.

**v1 — the global minimum with a head above it.** Take the narrowest section in
0.52–0.94 H, require some section above it to be ≥1.35× wider. **MEASURED across 24
bodies: three bad cuts.**

| body | joint | what it actually cut |
|---|---|---|
| astronaut | 50.2 mm | the chest of the suit |
| sundress | 34.7 mm | the shoulders |
| pilot | 30.5 mm | low, at the collar line |

A bulky costume has no waist narrower than its own chest, so the global minimum of the band
landed low — and the chest and helmet above it passed the 1.35× test easily. **The test was
true and the answer was wrong.**

**v2 — find the shoulders first, then the minimum above them.** True, and worse.
**MEASURED: six bodies came back with their heads still attached** — astronaut,
firefighter, knight, nurse_scrubs, pilot and wizard all cut at `f = 0.970`, the ceiling of
the band. Here is why, on the astronaut, reading the profile above the shoulder line:

```
f=0.743  2022        f=0.786  2168        f=0.858  1469
f=0.758  2012  <--   f=0.801  2151        f=0.915  1195
f=0.772  2097        f=0.829  1654        f=0.970   587
```

The neck **is** there at 0.758. But the head above it is only **1.078×** wider, because a
spacesuit's head is barely wider than its collar — so the 1.35× test rejected it, every
other section failed too, and the fallback took the narrowest section above the shoulders.
That is the crown. *A threshold tuned on a business suit does not survive a spacesuit.*

Raising the shoulder search floor to fix a related miss on the knight then let the pilot's
peaked cap and the nurse's hair become "the shoulders", after which there was nothing above
them and three bodies ran to the ceiling again. **Finding the shoulders is harder than
finding the neck**, so the shoulder line is now computed, reported, and *not obeyed*.

**v3 — prominence, and no threshold to tune.** For each candidate, take the smaller of the
two peaks flanking it — the widest section below it, and the widest above it within the
band — and divide by the candidate. Take the maximum.

A neck scores high because it has shoulders below **and** a head above. A crown scores ~1.0
because it has nothing above it. A shoulder scores ~1.0 because it *is* the peak. There is
no constant to pick.

Two hard bounds do the rest, and both are statements about human proportion rather than
tuning: **no neck below 0.66 of height** (that is a waist, however prominent) and **none
above 0.92** (that is a head, and the ceiling binds the fallback too, which is exactly what
v2 lacked).

**MEASURED, v3 across the same 24 bodies: 0 cuts above 0.90, 0 fallbacks**, and every body
v1 got right is cut at the identical height. The three v1 failures land at 0.751, 0.782 and
0.825 — the astronaut's collar, the sundress's neck, the pilot's collar.

The 240-row profile is stored in each item's record and drawn on its card in `/three`, with
the chosen height marked, so where the cut went is something you look at rather than a
number you trust.

**Where a wide joint is correct, not a fault.** The astronaut still reports 50 mm and the
pilot 44 mm. Those are right: a spacesuit and a peaked cap genuinely have no neck, the
narrowest real constriction is the collar, and a 50 mm flat is a perfectly good face to bore
an 8.4 mm socket into. The number to worry about is one that disagrees with the picture
beside it.

### Boring the socket

After the cut, the body is **rescaled so its own height is the target**, and only then is
the socket bored.

> *The first version had this backwards.* It scaled the whole figure to 110 mm and then
> removed the head, leaving a body 83.8 mm tall while the record still said 110 — and 110
> is the number a person reads off the library and slices to.

If the neck is narrower than the socket plus 2.4 mm of wall, the socket is **shrunk to
fit** and the record says `socket_reduced: true`. Silently boring a hole wider than the
neck is how a part arrives hollow.

**Debris is stripped after the boolean, not before.** The CSG produces small shells; an
earlier version cleaned the mesh immediately upstream of the operation that dirtied it and
still shipped a 128-face island. `mesh_doctor`'s own warning is the one that caught it:
*"stray shells slice as floating debris"*.

---

## 3. THE SEED IMAGE: FIGURINE GRAMMAR

Every body shares one prompt spine and one negative. Subject, costume and pose are the only
per-body fields. This is deliberate: a rule that lives in the catalogue can be forgotten
when a new body is added; a rule that lives in the grammar cannot.

| rule | where it came from |
|---|---|
| hair sculpted as **one closed mass with carved grooves** | `terra_3d_source_v2.py`: separated locks became stacked tubes and the mesh read as Medusa. A mould cannot release free strands and a printer cannot support them. |
| **arms held close to the body** | RULE OF THUMB, print: an outstretched arm is an overhang and a thin unsupported part. |
| **"cast shadow" in the NEGATIVE prompt** | `terra_3d_source_v2.py` MEASURED that asking for "no cast shadow" in the POSITIVE does not work. The word has to move to the negative to land. |
| **no held thin objects** — no sword, staff, cane | at 110 mm they are under the printable minimum, and the matte eats them anyway. |
| **complete figure with margin on all sides** | so the alpha crop has something to find. A cropped figure comes back stockier with more islands. |
| **flat plain background, even frontal light** | BiRefNet needs contrast at the silhouette; `terra_3d_source_v2` MEASURED it eating a bare forearm off a pale plate. |

The seed then goes: **BiRefNet → RGBA → alpha-crop → composite on white → pad square →
1024×1024**, which is the exact shape `VERDICT.md` §1 fed the winning mesh. Squaring here
rather than letting `CLIPVisionEncode` centre-crop is the point: on a 1664×2432 portrait the
node's centre crop removes 15.8% off the top **and** the bottom.

### A NEGATIVE CANNOT REMOVE WHAT THE SUBJECT NOUN PUTS THERE

The most useful thing the first 24 bodies taught, in three rounds on one card.

**Round 1.** The negative contained `flowing cape, billowing fabric`. The superheroine came
back **wearing a cape** — a thin sheet the size of the figure, and the one shape on the
whole list a printer cannot make unsupported. Reading it back: the model parses *"flowing
cape"* as *a cape that is flowing*, and cheerfully supplies one that is not.

**Round 2.** Negate the **noun**: `cape, cloak` added bare, plus `no cape and nothing
hanging from the shoulders` in the positive as well. **MEASURED: still a cape.**

**Round 3.** Take the noun out of the subject. `a superheroine` became `a woman in a
costumed hero suit`.

The same three rounds ran on `sundress`, whose long loose hair widened the neck band until
the cut hit the 0.66 floor: asking for *"shoulder-length hair sculpted as one closed mass"*
did nothing, and `a young woman with a short bob haircut ending at the jaw` did.

This is the same finding `terra_3d_source_v2.py` reached from the other direction — that
`terra branford` **means** very long wavy hair, and no amount of appending `ponytail, hair
behind back` argues it away. Its answer was tag surgery. So is this one:

> **The subject noun is a bundle of nouns.** A negative prompt filters what the sentence
> asks for; it does not reach inside what the subject *is*. If a costume keeps arriving,
> change what the figure is, and stop negotiating about what it wears.

The bare-noun fix from round 2 is kept in `FIGURINE_NEG` anyway — it costs nothing and it
does help on weaker priors. It is just not the lever.

---

## 4. THE MESH RECIPE, THE REPAIR, AND THE STAIRCASE

Generation is unchanged from the measured winner in `studio/samples/terra_3d/mesh/VERDICT.md`
§1–2: latent 4096, octree **512**, threshold **0.45**, surface net, 30 steps, cfg 5.0,
single-view conditioning.

Repair is where this section departs, and it took two attempts to get right.

### THE STAIRCASE IS THE REPAIR. NOT THE MODEL, AND NOT THE OCTREE.

**MEASURED**, by rendering the same shoulder crop off four meshes at 12 M splat samples:

| mesh | what the surface looks like |
|---|---|
| **raw**, Hunyuan3D output, no repair | **smooth.** No terracing at any magnification. |
| `repair --voxel-res 489` | a pronounced staircase, contour rings across the whole jacket |
| `repair --voxel-res 900` | the same staircase, finer |
| `repair --voxel-res 1200` | the same staircase, finer still |

Surface-net extraction places vertices at **sub-cell** positions, so a 512 octree does not
have to look like 512 steps — and it does not. `repair --method voxel` re-rasterises to a
**binary occupancy grid** and re-extracts, and that rasterisation is the staircase. Raising
the repair resolution only changes the step size; it never removes the steps.

> **This corrects an earlier claim in this file, and a bigger one in `docs/3D-QUALITY.md`.**
> An earlier version of this section compared repair at 500 and 900 and concluded that
> "voxel-res is a face dial, not a body dial" — that a suit hides the terracing a face
> cannot. That comparison was between two *terraced* meshes and never included the raw one,
> so it measured *how coarse* the staircase was and not *where it came from*.
>
> The bigger consequence: `docs/3D-QUALITY.md` had raising the octree as its top item, and
> that ceiling turned out to be blocked by system RAM. **Raising the octree would not have
> improved these surfaces at all.** A dial nobody could turn was being blamed for damage
> done two stages later by a dial that was free.

### THE FIX: A TAUBIN PASS, AFTER THE REPAIR, BEFORE THE CUT

Plain Laplacian smoothing contracts a closed solid on every pass — on a figurine that is
lost millimetres and lost silhouette. **Taubin** alternates a positive shrinking step
(`lamb`) with a negative inflating one (`nu`), which low-passes the surface instead of
shrinking it.

**MEASURED**, `suit_male`, 40 passes at `lamb=0.5, nu=0.53`:

| | |
|---|---|
| volume kept | **100.017%** |
| watertight after | still true — 0 boundary, 0 non-manifold, 1 shell |
| surface moved, mesh-to-mesh | **mean 0.024 mm, p99 0.085 mm, max 0.117 mm** |
| cost | **under a second** |

**JUDGED** at 560 px against the unsmoothed repair: the staircase is gone, and the clasped
hands, individual fingers, jacket vent, sleeve folds and pocket flaps are all still there.
0.117 mm of worst-case movement is **a quarter of one FDM extrusion width**.

It runs **after the repair and before the cut and the bore**, never after — smoothing a
bored socket would round its walls and dome the flat seating face, which is the one surface
on the part that has to stay flat.

40 rather than the 60 that was tested: a face has finer features than a jacket, and heads go
through the same call.

### THE REPAIR RESOLUTION, NOW THAT IT IS ONLY A FILE-SIZE DIAL

With the staircase handled by smoothing, repair resolution decides step size and triangle
count and nothing else. It is set from a target voxel size in millimetres, per part and per
process:

```
VOXEL_MM = {"fdm":   {"body": 0.30, "head": 0.15},
            "resin": {"body": 0.15, "head": 0.10}}
```

**RULE OF THUMB** for the millimetre figures, against the printers rather than against a
test print: a 0.4 mm nozzle cannot resolve below about 0.3 mm in XY, so a finer voxel than
that buys file size and nothing else; resin at 0.035 mm XY can still use 0.10.

The effect on what you download, `suit_male` at 110 mm on `fdm`:

| | faces | STL | 3MF |
|---|---|---|---|
| voxel-res 900 | 2,224,782 | 111 MB | 19.6 MB |
| voxel-res 489 + Taubin 40 | 660,740 | **33 MB** | 11.8 MB |

Both watertight, zero non-manifold edges. The second is the one a slicer will open without
complaint, and it is now also the smoother of the two.

**Quadric decimation was tried and rejected.** `fast_simplification` takes the 2.2 M mesh to
300 k in 1.7 s, but **MEASURED**: at every target from 800 k down the result loses
watertightness — at 300 k and below, boundary edges go to zero while the component count
jumps to 12, 31, 16, which is non-manifold edges being created. Controlling face count at
the repair stage costs nothing and keeps the solid a solid.

**A surface-preserving repair was tried and rejected too**, and it is worth recording why,
because it is the obvious idea. The raw mesh is 845,780 faces in **3,297 shells** — but the
largest holds **98.06%** of them and the rest are specks of 42, 12, 12 faces. Taken whole,
the mesh has only **14** boundary edges. So: keep the big shell, drop the debris, fill the
holes, done? **No.** The debris is welded to the body by the 8,307 non-manifold edges, so
splitting it off **opens 6,660 boundary edges**, and `fill_holes` closes none of them. Voxel
repair stays, and Taubin cleans up after it.

### THE MELTED-WAX PROBLEM, AND HOW FAR IT GOES AWAY

The first fix for the staircase — a heavy Taubin pass over a coarse grid — traded one
artefact for another. The surfaces stopped being terraced and started looking like melted
wax: cloth folds rounded off, hair strands merged into blobs, the whole figure softened.

**Both middle steps were lossy in the same direction, and that is the whole story.**
Rasterising to a 0.30 mm grid destroys every feature finer than 0.30 mm *permanently*.
Taubin then low-passes the result, which hides the staircase the first step created **and**
removes whatever fine relief survived it. Smoothing cannot recover detail rasterisation
already threw away — it can only blur the evidence.

#### Scoring a repair honestly

**RAW IS THE GROUND TRUTH FOR DETAIL.** Hunyuan3D's surface-net output is smooth *and*
detailed; its only fault is topological. So the right question for any repair is: how far
did the surface move away from raw, and did it become a solid?

`dev` below is the mean distance from a candidate's surface back to the raw surface, in mm,
on the figure at its 146.67 mm working height. **MEASURED**, all on `suit_male`:

| path | faces | dev mean | dev p99 | what it looks like |
|---|---|---|---|---|
| raw (the target) | 845,780 | 0 | 0 | smooth, hair strands crisp — but **not watertight** |
| **v489 + taubin60** — the old ship | 783,948 | **0.1500** | 0.3321 | melted wax |
| v900 + taubin25 | 2,644,212 | 0.0888 | 0.1972 | finer ripple, hair legible |
| **v1202 + taubin20 + dec 800k** — ships now | 800,000 | **0.0649** | 0.1569 | finest ripple, most hair kept |

**A finer grid with less smoothing is 2.3× closer to raw than a coarse grid with heavy
smoothing — at the same file size.** 12.5 MB of 3MF either way.

#### A metric that lied, and why the render is the arbiter

An obvious second metric is the fraction of edges with a dihedral angle over 30° — creases,
folds, cloth edges. **It does not work here, and it nearly cost a bad decision.**
`v900 + taubin10` scored 0.70% against raw's 0.68% — an apparently perfect match — and
rendered as an obvious staircase. The metric was counting *step edges* as creases. A
staircase inflates it and melted wax deflates it, so it can agree with the target from
either side for the wrong reason. **Every recipe change here was decided by rendering the
same crop at 30 M splat samples and looking.**

#### Decimation, which was written off once and should not have been

The high-resolution repair is 4.7 M faces. That is only affordable because decimation turns
out to be free: **MEASURED**, decimating 4,710,846 → 800,000 left `dev` at 0.0675 → 0.0675,
unchanged to four decimals. Face count and fidelity are independent once the geometry is
banked, so paying for a smaller file with a coarse grid was buying nothing.

It was rejected earlier because it broke watertightness at every target. Two things were
wrong with that test:

1. It ran on an **unsmoothed, coarse** mesh full of staircase and debris.
2. **Scale.** Quadric error is quadratic in the coordinates, so the same mesh and the same
   target decimates cleanly at 147 units across and comes back non-watertight at 2 units
   across — which is the size Hunyuan3D output arrives in. `stage_decimate` normalises to
   150 units, decimates, and scales back. That one line is the difference between the
   standalone test passing and the first pipeline wiring failing.

It is still **checked rather than trusted**: the result is tested for watertightness and
shell count, and the full-resolution mesh is kept when it fails. A smaller file is worth
having; it is not worth shipping a part a slicer will argue with.

#### Where the remaining ripple comes from, and what it would take to remove

**More smoothing does not help, and that is a finding rather than a limit of patience.**
**MEASURED** at v1200: taubin 20, 35 and 50 give `dev` 0.0675, 0.0675, 0.0672 and render
identically. The residual is no longer high-frequency noise that a low-pass filter can
catch — it is a lower-frequency contour pattern baked in by the rasterisation, and Taubin
cannot tell it from real shape.

**The only real fix is a repair that never rasterises. Three were tried and all three
failed:**

| attempt | result |
|---|---|
| `mesh_doctor repair --method surface` | returns the input unchanged — 8,307 non-manifold edges, still open |
| drop the 3,296 speck shells, then `fill_holes` | the specks are welded on by those non-manifold edges, so splitting **opens 6,660 boundary edges**; `fill_holes` closes none |
| `manifold3d` self-union | `Not all meshes are volumes!` — manifold3d requires manifold *input*; it cannot repair, only compose |

What would work is a repair that operates on the surface rather than on a grid. That was the
honest next step at the time of writing, and it is what the section below does — `pymeshlab`
turned out to have a Python 3.14 wheel, and screened Poisson closes the last 0.065 mm.
**Everything above this line is now history rather than the shipping recipe**, kept because
the three dead ends are worth not repeating.

### THE REPAIR THAT NEVER RASTERISES — AND IT IS 24× CLOSER

Everything above fought the same losing battle from inside the voxel path. The way out was
to leave it.

`mesh.voxelized().fill().marching_cubes` builds a **binary** grid, so the 0.5 crossing the
extractor solves for always lands exactly halfway between two cell centres. There is no
sub-voxel information left to place a vertex with. Detail finer than the pitch is gone
*before* marching cubes runs, which is why nothing downstream ever recovered it.

Two attempts to give the extractor something continuous, both **MEASURED**:

| field | dev mean | verdict |
|---|---|---|
| binary occupancy, res 900 | 0.0892 mm | the staircase |
| **Gaussian-blurred** occupancy, res 900 | 0.0882 mm | visibly smoother than binary — a real but small gain |
| **exact EDT** signed field, res 900 | 0.0888 mm | **no better than binary** |

The EDT result is the instructive one. An exact Euclidean distance transform *of a binary
grid* is still quantised at the boundary — values jump from −1 to +1 across it, so the zero
crossing lands at the midpoint again, exactly as before. A Gaussian is different because it
creates a genuine multi-voxel ramp for the crossing to slide along.

A hand-rolled in-place repair got closer than any field trick: isolate the largest shell
(98.06% of faces), fan every boundary loop to a centroid — **6,660 boundary edges to 0** —
then iteratively drop faces on over-subscribed edges and re-fan. It **stalled at 224
non-manifold faces** (0.027%) because closing a hole at a pinch point recreates the pinch.
`manifold3d` cannot rescue it either: it requires manifold *input*, so it composes solids
but never repairs them.

#### Screened Poisson

`pymeshlab` has a `cp314` wheel, so it installs on this box. Screened Poisson fits an
implicit surface to the raw mesh's **own oriented points** rather than sampling it onto a
grid, so its accuracy is set by the input rather than by a pitch.

**MEASURED**, `suit_male`, depth 12, against every path that came before:

| path | dev mean | dev p99 | watertight |
|---|---|---|---|
| voxel 489 + taubin 60 | 0.1500 | 0.3321 | yes |
| voxel 1202 + taubin 20 + decimate | 0.0644 | 0.1563 | yes |
| in-place stitch | — | — | **no** — 224 non-manifold faces |
| **screened Poisson depth 12 + decimate** | **0.0027** | **0.0117** | **yes** |

**24× closer to raw than the best voxel path**, and cheaper: the finish phase went from
197 s to 59 s, at the same file size (11.5 MB of 3MF).

**JUDGED** at 30 M splat samples, side by side with raw at two magnifications:
indistinguishable. Hair strands, lapel roll, waistcoat buttons, pocket flaps, tie, hands and
plinth all read exactly as they do before any repair.

#### Four things the rollout taught that the bench test did not

**Depth 10, not 12.** MEASURED: depth 10 gives dev 0.0028 mm and depth 12 gives 0.0026 —
no meaningful difference, and near-identical face counts (2.39 M vs 2.49 M). Depth 12 costs
**30–42 GB of RSS** and OOM-killed the batch on its fourth body. Depth 10 buys the same
surface for a fraction of the memory.

**ComfyUI has to be out of the way.** Calling `/free` is not enough — that releases model
weights, not the process. MEASURED twice: the Poisson solve peaks around 30–35 GB, ComfyUI
sits on ~20 GB it does not need during a CPU-only phase, and 60 GB does not hold both. The
kernel killed ComfyUI the first time and the batch the second. `rollout2.sh` stops ComfyUI
for the duration and `--from-raw` lets a head re-run its repair with no GPU at all.

**Three edges out of ten million can fail an item.** MEASURED on the astronaut:
`mesh_doctor scale` took a watertight Poisson solid and returned it with four two-face
shells and three boundary edges. `is_volume` then goes False, `trimesh.boolean` refuses with
*"Not all meshes are volumes!"*, and the socket bore fails — on a mesh that is 99.9999%
fine. `ensure_solid` runs after every step that rewrites geometry and costs three faces.

**A batch lock, because three ran at once.** Three `fill --phase finish` runs ended up alive
together, each launched after the previous appeared dead — a `pgrep` between two items
reports nothing. MEASURED consequence: 48 GB resident, swap completely full, and a 13 s
Poisson solve taking over twenty minutes. Nothing crashed and nothing logged an error; the
library just stopped progressing. A PID file with a liveness check turns that into a message.

#### What is left

**24 of 27 items decimate to target; three do not.** `astronaut`, `pilot` and `stand_in`
fail every decimation step on their Poisson meshes — not from debris, which the rescue
handles, but because what decimation leaves behind cannot be made watertight at any
reduction. They keep their full mesh: 2.2–4.2 M faces, **28–53 MB of 3MF** against a
median of 11.7 MB. Watertight, printable, and simply larger. Bambu Studio opens them; it is
a file-size wart rather than a defect, and the check is doing exactly what it should by
refusing to ship a smaller broken solid instead.

**The Taubin pass is now zero.** There is no staircase left to remove, so smoothing could
only cost detail. `stage_smooth` is skipped when the count is 0 and the dial stays only
because the voxel fallback still needs it — a box without `pymeshlab`, or the rare mesh
Poisson cannot close, still gets a printable part by the old route and the record says which
one ran.

#### How much does the residual matter on a print?

The steps are now **0.122 mm**, one voxel at the working scale.

- **FDM** (0.4 mm nozzle): **invisible.** The extrusion is more than three times wider than
  the ripple; the nozzle cannot lay it down. **RULE OF THUMB**, not measured on a print.
- **Resin** (0.035 mm XY): **marginal.** Resin resolves 0.122 mm, so it would show as a very
  fine contour texture — far less than the 0.295 mm it replaces.

Everything visible in the comparison renders on this page is magnified well past print
scale. The gain that matters is not the ripple; it is the **detail that came back** — hair
strands, cloth folds and pocket edges that the old path had melted away.

## 5. PRINTING THEM

Hand the slicer the **`.3mf`**, not the `.stl`. It carries units and orientation
explicitly, so the model arrives at the size you meant. The STL is written alongside for
any other slicer.

Both parts come out of `mesh_doctor export` Z-up and sitting on `z = 0`, so they are already
oriented for the plate.

**RULE OF THUMB** for the settings, not measured on a print from this library:

- **Body** — flat on its plinth, no supports needed for a pose with arms in. If a pose has
  arms away from the torso, that is where supports go, and it is worth checking
  `mesh_doctor overhang` before slicing.
- **Head** — flat face down. The socket is then a vertical blind hole printed upward,
  which is the orientation it prints cleanest in.
- **Do not hollow the head.** A bobblehead head wants to be light but it also has to hold a
  glued spring; 15–20% gyroid is the compromise, solid around the socket.
- **The socket is not a tolerance-critical fit.** It is a glue joint. Do not "fix" it in the
  slicer with a hole-compensation setting.

`mesh_doctor thickness` and `mesh_doctor overhang` will answer the two questions worth
asking before a long print. `printable: true` on a `/three` card means `mesh_doctor
diagnose` returned an empty `blocking` list — it does **not** mean anyone has printed it.
Nothing in this library has been printed yet. When one is, this section gets the numbers.

---

## 6. THE HEAD

A head takes a photograph rather than a generated seed, and there is one extra stage in
front: **the figurine pass**.

### A photograph is not a sculpt-ready image

`bobble.stage_stylize` runs the photo through `22_qwen_edit_2511` with one instruction that
does three separable jobs, because a photo is wrong for meshing in three separable ways:

- **Loose hair.** Every lesson `terra_3d_source_v2` learned about drawn hair applies harder
  to photographed hair. A strand becomes a tube; a flyaway becomes a spike.
- **Baked light.** *Hunyuan3D sculpts what it sees.* A hard shadow under a cheekbone is read
  as geometry, so a portrait shot with a key light comes back with the key light carved into
  it. This is the **delighting** stage a commercial pipeline runs, which
  `docs/3D-QUALITY.md` §3.4 lists as untested here — the head path is where it gets tested.
- **Shoulders and a room.** The mesh should be a head, not a bust in a room.

`--style raw` skips it. Both source images stay in the item folder side by side, so the pass
can be judged rather than assumed.

**JUDGED**, `stand_in`, a portrait with real directional window light: the pass returned the
same face — hairline, smile, jaw all recognisable — with the shading removed, the hair
closed into one grooved mass, the background flat, and the crop at the neck. The stubble is
gone, and that is a genuine loss of likeness; it is also what *sculpted resin* means.

### The flat and the socket, and the shoulders nobody asked for

**HUNYUAN3D INVENTS A BUST.** MEASURED on the `pickle` head, and it is worth being precise
about where the fault is *not*: the figurine pass did exactly what it was asked, and
`source_styled.png` is a head and the top of a neck on a flat plate, no shoulders anywhere.
The **mesh** came back a full bust with shoulders and an upper chest. A bust is a very
common 3D subject; given a floating head, the model supplies the body a head is usually
attached to.

The first cut rule took the lowest section reaching **55% of the widest section below the
mid-line**. On a bust the widest section below the mid-line *is the shoulders*, so 55% of
that is still down in the chest — and the part came out 95 mm of mostly shoulder with a
small head on top. Watertight, printable, and not a bobblehead.

The fix is the **same prominence test the body's neck finder uses**, for the same reason: a
neck is a constriction with something wider below and something wider above, and that holds
whether the wider thing below is a pair of shoulders or a whole body. No threshold tuned to
how much shoulder the model decided to add.

**MEASURED**, cutting the same two meshes both ways:

| head | old rule | prominence | new cut | what changed |
|---|---|---|---|---|
| `pickle` | 0.237 — through the chest | **5.78** | 0.321 | shoulders gone; the head now fills the 95 mm |
| `stand_in` | 0.175 | **1.12** | 0.175 | already close; unchanged |

If there is **no** prominent constriction — the model returned the head-on-a-stub that was
actually asked for — there is no neck to find and the old 55% rule is right, so it stays as
the fallback. The record says which one fired, in `cut_rule`.

The head is then rescaled so `--height` is the height of the **head**, not of the head plus
whatever was removed below it, and only then is the socket bored upward from the flat. Same
correction, same reason, as the body.

**MEASURED**, `stand_in` at 95 mm: watertight, one shell, zero non-manifold edges, seating
face 59.8 mm across, socket 8.4 × 14 mm, `printable: true`, 164 s end to end.

`mesh_doctor` warns `genus ~21 — the surface carries a lot of tunnels/handles, usually
reconstruction noise`. The tunnels are in the hair grooves. The solid is closed and slices,
so this is cosmetic rather than blocking, and it is the kind of thing a higher octree
(`docs/3D-QUALITY.md` §4.1) would be expected to reduce.

**Supersizing is just `--height`.** The head is scaled independently of the body, so a
95 mm head on a 110 mm body is a bobblehead and a 130 mm head on the same body is a
caricature. Nothing else changes.

### THE PREVIEW WAS LYING ABOUT THE SURFACE

The library's own renders had a speckled, sandpapered look that reads as surface texture on
every part. It is not in the mesh. It is the renderer.

`terra_mesh.render_one` is a **point splatter**: it samples a point cloud off the surface
once and rasterises it. Too few points over too many pixels and the gaps between splats read
as a fine, even grain. **MEASURED** on one head, same mesh, same crop, sample count the only
thing that moved:

| samples | what the surface looks like |
|---|---|
| **2.6 M** — render_one's default, and what the library used | a uniform speckle over everything |
| 10 M | largely clean; real hair strands legible as strands |
| 40 M | clean; eyelids, brows and forehead read as smooth surfaces |

Geometry cannot change with sample count, so all three are the same object — the first one
simply lies about it. **Every judgement anyone made about "surface quality" from a library
card was partly a judgement about this number**, including two of mine.

`stage_views` now renders at **9 M**. That is a cost decision, not a quality one: at size
420 / 6 frames, 2.6 M takes 6–12 s, 9 M takes 38 s, and 16 M takes 110–122 s. Two minutes an
item is not worth the last of the grain across a 24-item library.

**What is left after the noise is gone** is real, and worth knowing how to read:

- **Hair strand texture** — genuine. Hunyuan3D sculpts hair as grooved strands and it is
  visible in the **raw** mesh before anything of ours touches it. Intended.
- **A faint ripple on skin** — ours. It is the residue of the voxel staircase that the
  Taubin pass reduces but does not fully remove. The raw mesh is still smoother than
  anything we ship, and closing that gap needs a repair that does not rasterise — §4 records
  the attempt that failed.

### The close-up on a head is the scalp

`render_one` also writes a `_head.jpg` by slicing the top 26% of the mesh and giving it the
whole sample budget. On a **body** that is the head, which is exactly the point. On a
**head** it is the top of the scalp, and it was being shown on the library card beside the
orbit as though it meant something. `stage_views` now deletes it for heads.

### One trap in reading the renders

The orbit strips are drawn by `terra_mesh.render_one`, whose camera sits at **8° of
elevation** looking down. On a head — an object with no obvious horizon — that reads
convincingly as *the head is tipped back*, and it is not.

**MEASURED** before believing it: fitting a line through the centroids of 25 horizontal
cross-sections gives a 6.8° drift, but the centroids do not drift monotonically — they run
forward at the jaw, back at the crown, which is the shape of a head rather than a rotation.
The geometry sits square. *Check the camera before correcting the model.*

---

## 7. WHAT WOULD MAKE THESE BETTER

In `docs/3D-QUALITY.md`, with the honest version of where this stands against Meshy and
Tripo. The short answer for bodies specifically: **multi-view conditioning and more than one
seed**, in that order, and neither of them needs a better model.

---

## 8. FIGURES: ONE PHOTO OF A PERSON, CUT IN HALF

A **body** comes from a generated seed and its head is thrown away. A **head** comes from a
photo and its body never existed. A **figure** is the third thing: one photograph of a whole
person, meshed **once**, and cut into the two halves of a bobblehead that were always meant
to fit each other.

```bash
python3 studio/_tools/bobble.py figure --photo <photo> --id someone --body 110 --head 95
```

or drop a full-length photo into the **Figures** panel on `/three`.

**Meshing once rather than twice is the entire point.** Two separate generations of the same
person agree on nothing — not the neck width, not the shoulder line, not the style — so the
joint between them is a guess. One mesh cut in half has **one** neck cross-section, and both
sockets are bored to it.

### One diameter, decided once

Each half has its own limit: the body needs 2.4 mm of wall around the neck, the head needs
3.0 mm around its seating face. Clamping them independently is how you get a body bored at
8.4 and a head bored at 6.0, which no single spring fits. Both limits are computed, **the
smaller wins**, and both halves are bored to it.

### The head is meshed twice, and the body is not

**MEASURED on the first figure:** meshing a whole standing person at octree 448 produced
415k faces, and the head — about an eighth of the figure's height — came out of the cut with
**49,002 of them**. The dedicated head path gives a head 768k. The face was visibly soft,
and the face is the entire reason anyone wants their own bobblehead.

Resolution is spent per-mesh, not per-object. So the head is re-meshed from a **crop**, and
the crop comes from the mesh rather than from a guess about where heads are: `neck_plane`
already returned the neck as a fraction of figure height, and the matte's alpha box says
where the figure sits in the picture. Between them the neck line is a pixel row.

**MEASURED after:** 681,218 faces, **14× the resolution**, eyes, nose, lips and jawline all
reading. The body keeps the figure mesh, so the neck both sockets are sized from is still
measured once, on one mesh.

### A whole figure will not mesh at octree 512

**MEASURED, three times:** a full standing person takes ComfyUI down at octree 512 — available
memory fell from 34.7 GB to 841 MB inside one six-second sample — while 448, 384 and 320 all
completed in 20–37 s at 9.4 GB of VRAM, producing 415k, 307k and 213k faces. The spike is in
the `VoxelToMesh` extraction, not the decode, and it is not proportional: 448 is fine and 512
takes the machine down.

A headless bobblehead body is chunky and meshes at 512 without trouble; a tall slender person
with separated legs does not. `stage_mesh` therefore walks a ladder downward on failure
rather than the setting being lowered for everyone, and **figures start at 448** because 512
has never held and each attempt costs a ComfyUI restart. The record says which rung ran.

---

### THE FIGURINE FRAMING WAS EATING THE LIKENESS

The first version of this pass opened with *"Turn this into a full-length collectible vinyl
figurine"* and went on to ask for hair *"as one solid closed mass with carved grooves"* and
skin *"smoothed into continuous sculpted surfaces like painted resin"*.

**MEASURED**, reading the original photograph and the result at the same crop:

| | photograph | after the pass |
|---|---|---|
| hair colour | mid-brown, sun-lightened | **near black** |
| hair shape | wavy, voluminous, falling forward over both shoulders | straight, sleek, flat to the skull |
| face | narrow, defined cheekbones, nasolabial lines, small asymmetric mouth | rounder, fuller-cheeked, **every line removed** |

None of that is drift. **It is the prompt doing exactly what it was told.** "Turn this into
a figurine" means idealise the face. "One solid closed mass" means straighten and darken.
"Smooth like painted resin" means delete the lines that make a face *that person's* face.

#### Negation failed again — the third time in this file

The obvious fix is to pin what must not change. So: *"keep her hair the colour it already
is, do not darken it, do not lighten the ends, do not add highlights or an ombre."*

**MEASURED: it came back with a strong dark-root-to-blonde ombre.** The negation was
explicit, specific, and ignored — exactly like the superhero's cape in §3, and exactly like
`terra_3d_source_v2`'s hair tags before that.

> **A negative cannot remove what the framing puts there.** The answer is never another
> clause. It is to delete the instruction causing it.

#### What the pass actually needs to do

Two things, and only two, are genuinely required before a photograph can be meshed:

- **even lighting** — Hunyuan3D sculpts what it sees, so a hard shadow becomes a groove
- **no background**

The resin-smoothing had no justification at all. Hunyuan3D reconstructs a smooth surface
from any photograph, and the Poisson repair smooths it again; pre-smoothing the **image**
bought the mesh nothing and cost the likeness everything. The closed-hair clause had a real
job — free strands become spikes — but "connect the strands" and "make it one sleek dark
mass" are different instructions and only the first was ever needed. In practice the Poisson
repair handles loose hair well enough that the clause is not needed at all.

So `FIGURE_PRESERVE` asks for the lighting and the background, pins the person, and says
explicitly that **nothing else may change**. **MEASURED on the same photograph:** hair
colour, waves, parting, face shape and skin lines all survive, and the head mesh carries her
hair parting and her jawline instead of a generic one.

#### Two clauses that are now opt-in

Both were unconditional and both were invitations to redraw:

- **completion** is added only when `stage_detect_crop` says the photograph is cut off.
  Telling a *complete* photograph to "show the complete figure" invites a redraw, and a
  redraw is precisely what costs the likeness.
- **the plinth** likewise. Someone photographed standing on a pavement already has their
  feet on a plane.

**The general rule this arrived at, on the third attempt:** every clause in a preservation
prompt is a licence to change something. Ask for the fewest things that the next stage
genuinely cannot do without.

---

## 9. COMPLETION: THE PARTS THAT WERE NOT IN THE PHOTOGRAPH

**MEASURED:** handed the same photograph cropped at mid-thigh, the figurine pass returned a
**complete standing figure** — it invented the legs, the shoes and the plinth, and kept the
jacket, the face and the pose. Both halves came out watertight and printable.

That is the feature working. It is also a model inventing a third of a person and saying
nothing about it, so `stage_detect_crop` runs **first**, on the original, before any styling
— after the styling the evidence is gone. A subject whose matte occupies a real span of a
frame edge is cut off there:

```
cut off at: bottom (25% of that edge) - the figurine pass will invent what is missing
```

The card on `/three` carries that line, and the figure is tagged **completed**. It turns
"the legs look wrong" into "the legs were never in the photograph".

**JUDGED, and worth knowing:** the completion held the jacket, jeans and face, and **changed
the hairstyle** — long hair past the shoulders came back as a bob. Completion is not free of
identity drift, and the further the crop, the more the model is inventing.

---

## 10. POSES: MORE BODIES FOR THE SAME HEAD

```bash
python3 studio/_tools/bobble.py poses                       # the catalogue
python3 studio/_tools/bobble.py pose --figure someone --poses arms_crossed,hands_hips
```

**A pose changes the body. It does not change the head.** That is not a simplification — it
is what a bobblehead *is*: one head on a spring, and the head does not know what the body is
doing. So a figure builds its head once and then a body per pose. N poses cost N bodies, not
N figures.

**Every posed body is bored to the figure's diameter, not its own.** Each pose meshes
separately and so has its own neck cross-section; clamping each to its own neck would give a
library of bodies at 8.4, 8.1 and 7.6 mm that no single spring fits. The figure's diameter is
the contract, and a pose whose neck cannot take it is **reported**, not silently re-bored.

### Why there is no ControlNet here

The box has `sdpose_wholebody` and a `qwen_image_instantx_controlnet_union`, which is the
heavyweight route: detect a skeleton, edit it, regenerate conditioned on it. Three workflows
instead of one.

**MEASURED first, and it was not needed:** asking `22_qwen_edit_2511` for a different pose
*in words* held the identity on the first try. Face, hairstyle, jacket, jeans, shoes, plinth,
background and lighting all survived across arms-folded, fists-on-hips and a raised-arm wave,
in **6–12 s each**. The skeleton route is worth reaching for only if a pose the words cannot
express turns up.

### The catalogue carries a print verdict, because poses are where printability is decided

| pose | print |
|---|---|
| `arms_down` | safe — nothing projects |
| `arms_crossed` | safe — the arms rest on the torso |
| `hands_pockets` | safe — the arms rest against the body |
| `hands_hips` | the elbows enclose a gap each side; check overhang before slicing |
| `waving` | **risky** — a raised arm is an unsupported overhang and a thin section at 110 mm |
| `arms_out` | **risky** — both arms are unsupported overhangs |

The figurine grammar in §3 spends three of its rules keeping generated bodies out of trouble.
A pose is the user deliberately asking for the trouble, so the answer is not to refuse it but
to say plainly which ones need supports. The chips on `/three` mark the risky ones and the
verdict is in every pose record.
