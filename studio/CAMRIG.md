# The camrig playbook

**Camera moves as reusable, parameterised shot templates.** A fourth engine, `cam`,
alongside LTX / H3 / Wan.

---

## 1. The gap this closes

Three engines make a picture out of a *prompt*. None of them makes a picture out of a
*camera*. Every attempt to ask LTX or H3 for a specific camera move came back as a drift —
the playbook already records that LTX "will quietly substitute a camera drift for any body
action you ask it for," and the reverse is just as true: it substitutes its own drift for
any camera move you ask it for.

The moves that finally worked were written by hand, frame by frame, in a throwaway script
— and would have died with the film. `camrig` makes them **assets**: named rigs, declared
parameters with ranges and docs, saved presets, and a numeric report you can read *before*
spending a render.

A rig takes a **still** and produces a **shot**. Its plate is the shot's anchor image, so a
cam shot is specified exactly like any other shot in `/film`. The only difference is that
its motion is arithmetic, which means:

- **the same parameters always give the same pixels** — no seed lottery
- **re-rendering is free**, so taste iterations cost minutes, not GPU hours
- **text never garbles and faces never drift**, because nothing is generated

---

## 2. Using it

```
camrig.py list                                     # every rig and its presets
camrig.py doc drive_by_brake                       # parameters, ranges, what each does
camrig.py verdict drive_by_brake --preset big      # the shape test, as numbers
camrig.py report drive_by_brake --preset big       # velocity over time
camrig.py render drive_by_brake plate.png out.mp4 --preset big --grip 3.4
```

In the film editor, a shot carries a `cam` block and renders with engine `cam`:

```json
"cam": {
  "rig": "drive_by_brake",
  "preset": "sour_pickle",
  "params": {"grip": 3.4},
  "audio": "/path/to/anything.mp4"
}
```

`params` override the preset, which overrides the defaults. **An unknown parameter is an
error, not a typo that silently does nothing** — that failure mode is most of what this
module exists to prevent.

`audio` is optional: arithmetic has no sound, so a cam take gets whatever file you name
muxed under it, or a silent track if you name nothing.

---

## 3. The three rigs

### `drive_by_brake`
A camera held out of a car window, square to a facade, stopped by a hard brake.

**The camera never rotates.** A pan rotates about the camera, so the perspective of
everything in frame stays fixed; driving past changes your *viewing angle* on a building.
Sliding a window across one photograph can only ever produce a pan — **unless that
photograph is fronto-parallel**, shot square-on from across the road with both buildings
already square-on in it. Then a pure horizontal translation is geometrically correct and
the shot reads as travel. *Choosing the right plate is most of this rig.*

> The check that no rotation is left in a take: **vertical edges stay vertical.** Piers,
> doorframes, downpipes. If they lean, the camera is turning.

**The brake is a body, not a wobble.** The car decelerates; the operator does not, because
inertia. They pitch forward — and with the camera pointed 90° left, forward is the frame's
**right**. So all three phases come from one damped spring driven by the car's own
deceleration:

| phase | what happens | what you see |
|---|---|---|
| **1 cruise** | operator upright | framing moves steadily |
| **2 brake** | car slows, body doesn't | **framing accelerates** while the car slows |
| **3 release** | body at max lean, restoring force at its largest | the **fastest** move in the shot, back to rest |

### `still_push`
A slow push into a still. The honest answer whenever a shot must stay pixel-faithful:
readable signage, a real person's face, a plate of food that must not morph.

Written because LTX grew hands around a plate of lettuce on *every* seed tried — the
empty-frame clause and a negative did not stop it, because something has to act in a
generated shot and a plate of food starves the agency slot. A push on the real photograph
has no such problem.

### `zoom_punch`
A fast shove into frame that overshoots and rings out. An impact, a slam, a title landing.
The hit is a step and everything after it is one damped spring, so the recovery can never
look unrelated to the blow — which is the usual tell of a hand-keyframed shake.

---

## 4. Read the verdict before you render

`camrig.py verdict` turns "does this feel right" into something testable. For
`drive_by_brake` the two rules are:

```
phase 2 must SUSTAIN a framing velocity above the cruise
phase 3 must EXCEED phase 2
```

A setting that fails the second rule **reads as a car accident**: the surge collapses
before the brake has finished and the shot jumps straight to the snap-back. That is not a
subjective note — it is visible in the numbers, and it is exactly the failure that cost
several rounds of renders before the test existed.

```
sour_pickle  framing 761->1251  lean 332px  body out 1001 back -1193  PASS
gentle       framing 761-> 940  lean 157px  body out  502 back  -615  PASS
```

**Measure the body, not the framing.** Through the brake the framing velocity still carries
the car's residual speed, so a framing-based comparison can never show phase 3 winning even
when the operator is unmistakably snapping back harder than they lurched. The verdict
reports both, and tests the body.

The compiler surfaces a failing verdict as a **warning in the editor**, before the render.

---

## 5. Two traps, both paid for

**Motion blur averages several crops, so they must be identical sizes.** Clamping the crop
*box* to the image bounds silently changes its dimensions and `Image.blend` throws
`images do not match`. Clamp the crop **origin** and keep width and height fixed.

**Anything expressed per-pixel is not scale-invariant.** `roll` was originally degrees per
pixel of lean; upscaling the plate ×4 then rolled the camera four times as hard for the
same move, and put 7° of tilt into a shot that wanted one. Roll is now declared in
**degrees at a lean of 5% of `win_w`**, so a rig behaves identically at any plate
resolution. Positions stay in plate pixels — upscale the plate and scale those numbers with
it.

---

## 6. Where it lives

| | |
|---|---|
| `studio/_tools/camrig.py` | the motion, the compositor, the verdict, the CLI |
| `studio/camrigs/*.json` | one file per rig: params, ranges, docs, presets |
| `studio/film.py` | `_compile_cam` — surfaces the rig and its verdict to the Context tab |
| `studio/_tools/film_routes.py` | the `cam` render branch |
| `studio/film_editor.html` | the Cam checkbox in the takes grid |

Adding a rig is: write the motion function, add it to `RIGS`, drop a JSON beside it. The
`doc` and `list` commands read the JSON, so a new rig documents itself.

Adding a **preset** is a data edit — no code at all. That is the intended way to keep a
look: shoot it once, tune it against the verdict, save the numbers with a note about what
it is for.
