# The shot encyclopedia

One file per **kind of shot**: an orbit, a whip-tilt, a glass shatter, a helmet POV. Each file holds
the recipe to follow today, the checks a take must pass before it is picked, and the **progression**:
every time we made that kind of shot, dated and graded, with what went wrong and what fixed it.

The playbook (`studio/LTX_PLAYBOOK.md`) stays the measurement record, in the order things were
learned. The builder's catalog (`studio/shot_catalog.json`) stays the /film builder's shelf of
templates. `/recipes` stays the list of processes. The `/encyclopedia` page stays the reference for
what the box can run: capabilities, workflows and models. This book is the lookup: **you are about
to make this kind of shot - what do we know?** The entries cite the playbook's sections rather than
copying them.

The lookup table is [INDEX.md](INDEX.md), generated from the entries.

## How to use it

1. **Before writing a shot**, find its kind: `python3 studio/_tools/shotbook.py --find orbit`, or
   the "Look up by name" table in [INDEX.md](INDEX.md). A shot is usually several kinds at once - a
   camera move, a framing, an effect. Read each.
2. **If two entries look alike**, read both "Not the same as" lines. They say how the recipes differ.
3. **Follow the recipe.** If you do something else, you are running an experiment. Say so in the
   shot's notes, and give it its own progression step afterwards.
4. **After the takes are picked**, add a progression step to every entry the shot touched: the date,
   the film and shot id, what was done, what came out, the grade, the lesson. If the recipe changed,
   bump its version and say why in the step.
5. **Run `python3 studio/_tools/shotbook.py`.** It checks every entry and rewrites INDEX.md. It exits
   1 when something is wrong. Commit the entries and the index together.

## Two pipelines, one book

The studio makes films two ways, and they move the camera differently. When a recipe is split into
**/film builder:** and **Shot-script pipeline:**, follow the half for the pipeline you are in. A
result measured in one does not carry to the other.

| pipeline | driven by | the camera move |
|---|---|---|
| the /film builder | the /film editor on `studio/film.py`: one shot of layered inputs, rendered as takes on LTX-2.5, H3 and Wan | arithmetic on the finished take (`studio/_tools/postmove.py`): stabilise, then push, pull, pan, tilt, whip, crash zoom. The measured move equals the asked one, within the zoom's travel |
| the shot-script pipeline | `studio/_tools/fight.py` running a `studio/shotscripts/*.json` script: cast, anchors, shots, H3, score, finish, music | built before the take: a Blender previz painted by LTX-2.3's IC-LoRA (`studio/_tools/previz_shot.py`, `studio/_tools/previz_chain.py`), or first-last frames (`studio/_tools/flf_shots.py`) |

## Laws that recur

The same few causes sit under most of the failure tables. Each entry named here shows it.

1. **A camera move asked for in words is faked.** The engine arcs a little, pushes or cross-fades.
   Build the move: [`cam-orbit-360`](camera/orbit-360.md), [`cam-dolly-zoom`](camera/dolly-zoom.md),
   [`pipe-previz`](pipeline/previz.md), [`pipe-first-last`](pipeline/first-last.md).
2. **Asked to hold still, the engine pushes in.** Hold the frame by arithmetic, a pin or a short take:
   [`cam-locked-off`](camera/locked-off.md).
3. **Physical contact goes to H3.** LTX turns it into something else, or ignores it:
   [`fx-glass-shatter`](fx/glass-shatter.md), [`pov-vault-action`](pov/vault-action.md),
   [`fx-steam-on-glass`](fx/steam-on-glass.md), [`frame-hands-two-people`](framing/hands-two-people.md).
4. **Qwen-Image-2.1 keeps identity; Flux 2 keeps framing.** Draw every start frame on both and pick
   by eye: [`pipe-start-frame`](pipeline/start-frame.md), [`cont-face-identity`](continuity/face-identity.md).
5. **Asymmetric features flip or double.** Fix the side in the reference before anything is drawn:
   [`cont-asymmetric-mark`](continuity/asymmetric-mark.md).
6. **Light that makes no sense makes a figure look pasted on:**
   [`frame-silhouette-backlit`](framing/silhouette-backlit.md).
7. **Small things vanish at delivery size.** Judge at 1280x704, not on a zoomed frame:
   [`fx-dust-motes`](fx/dust-motes.md).
8. **A style asked for in words drifts to the engines' default look:**
   [`style-stop-motion`](style/stop-motion.md).
9. **The scorers block bad takes; they do not choose good ones.** Look at every take before the
   pick: [`pipe-take-pick`](pipeline/take-pick.md).

## The rules the checker holds the book to

- **One kind per entry.** The test for "is this its own kind?" is whether the recipe or the failure
  differs. A slow tilt and a whip-tilt are two entries: the slow one can sometimes be asked for in
  words; the fast one is built between two frames. A glass shatter, a puddle splash and spray off a
  wet surface are three entries: each failed differently. When one entry's recipe starts to say "but
  if it is X, do Y instead", X is a new entry.
- **A name answers to one entry.** Every alias ("360", "vertigo", "whip") belongs to exactly one
  entry, so a lookup never lands on two recipes and two kinds cannot quietly merge under one name.
- **Neighbours are named both ways.** Each entry lists the kinds it is most easily confused with, and
  says in one line how they differ. If A names B, B must name A. The index lists every such pair.
- **Every attempt is dated and graded**, including the ones that failed. A failed attempt is the most
  expensive information in the repo, and the easiest to lose.
- **Numbers, not adjectives.** Seeds, frame counts, scores, seconds, the take's file name.
- **Tools named are tools that exist.** Every `studio/_tools/*.py` or `workflows/*.json` an entry
  names must be on disk. Renders are out of git, so paths to takes are listed but not checked.

## Status

| status | meaning |
|---|---|
| proven | the recipe worked on the films it names, checks and all |
| works-with-caveats | works; the caveats are in the entry and in its failure modes |
| partial | part of what is asked comes out; the entry says which part |
| fails | nothing on this box delivers it yet; the entry says what was tried |
| untested | known only from the builder's catalog or from prose; no film has used it |
| retired | kept for its history; the entry names what replaced it |

## Grades

Graded by looking at the take, never by the face scorer alone.

| grade | meaning |
|---|---|
| A | what was asked is on screen, and a viewer would not notice a flaw |
| B | what was asked is on screen, with a flaw a careful viewer would see |
| C | part of what was asked is on screen |
| D | something else came out: usable only as a different shot |
| F | unusable |
| n/a | a measurement or a tool change, not a take |

`+` and `-` refine a grade.

**Where the grades came from.** The steps from the five challenge films of 2026-09-30 were graded
from the takes themselves; [the review](reviews/2026-09-30-challenge-films.md) grades the films.
Every other step was rebuilt from the written record: the playbook, the craft docs and the films'
notes. Where the text gave no date, the step carries the date of the commit that first added that
text, so the work may be a little older than its date. Those grades come from what the record says
came out; the takes were not watched again.

## The families (folders)

| folder | ids start | holds |
|---|---|---|
| `camera/` | `cam-` | the camera travels, turns or zooms |
| `framing/` | `frame-` | where the camera stands and how much it sees |
| `pov/` | `pov-` | the camera is a character's eyes |
| `fx/` | `fx-` | liquids, glass, light, weather, particles, flame |
| `cloth/` | `cloth-`, `hair-` | fabric and hair under force |
| `motion/` | `move-` | what the body does |
| `continuity/` | `cont-` | what must stay the same from shot to shot |
| `text/` | `text-` | letters and interface in the picture |
| `dialogue/` | `dia-` | a line spoken on screen |
| `style/` | `style-`, `master-` | the look of the whole film, and its master |
| `transitions/` | `trans-` | how one shot hands over to the next |
| `pipeline/` | `pipe-` | not shots: the steps every shot passes through |

## The template

Copy this for a new entry. The file is `craft/shots/<family>/<id without its prefix>.md`.

```markdown
# Title (`family-prefix-name`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | partial | 2026-09-30 | film shot-id, grade B |

**Also called:** every name a director might use, comma separated
**Not the same as:**
- [`other-id`](../family/name.md) - how the two differ, in one line

## Recipe (v1, YYYY-MM-DD)

One line saying what to do - the index quotes it.

1. The start frame: compositor, references, the framing words.
2. The engine and why.
3. The prompt, with a pattern to copy.
4. Seeds, length, trims.

## Checks before picking

- What to look at in every take before it is picked.

## Progression

### YYYY-MM-DD · film shot-id · what was tried · grade X
- **Did:** ...
- **Got:** ...
- **Learned:** ...

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|

## Evidence

- takes and boards (box-local), playbook sections, craft docs

## Open questions

- what nobody has measured yet
```
