# Editing — transition grammar, shot rhythm, assembly

Cutting practice for `scripts/epic.py` (long narrated) and `scripts/cartoon.py` (short
dialogue). Every number here was measured on this box against real render output, not
estimated. Written by the editor, 2026-07-29, after auditing all 108 boundaries of
`films/chrono.json` (109 shots, 10 m 17 s).

---

## 1. The transition grammar

Five transitions, set per shot with `"in"` (the transition **into** that shot). This is
`TRANSITIONS` in `epic.py`. Do not add a sixth without a reason you can state in one line.

| `in` | xfade | dur | Means |
|---|---|---|---|
| `cut` | — (concat) | 0.00 | Neutral. Inside a scene, and at every impact. |
| `soft` | `fade` | 0.28 | Two shots that are **one beat**. Barely perceptible. |
| `dissolve` | `fade` | 0.70 | Scene change **within** a time/place. "Elsewhere, later." |
| `flash` | `fadewhite` | 0.50 | Reserved for the film's one recurring motif. |
| `fade` | `fadeblack` | 1.00 | Act break. Three per film, maximum. |

Per-shot `"in_dur"` overrides the duration. It works and nobody uses it — it is the right
lever when a boundary needs the *same* grammar with more weight (see §2).

### The rules that actually matter

**A cut is the default and should win roughly half the boundaries.** CHRONO ran 57 cuts /
108 boundaries (53%) and that is the right ballpark. The failure mode this grammar exists
to prevent is `hollow-choir.json` — 23 shots, one 0.35 s dissolve everywhere, and the whole
film reads as a single mushy slideshow. If you find yourself typing `dissolve` a fourth
time in a row, you have stopped editing and started defaulting.

**Never dissolve through violence, impact, or a reveal.** A dissolve says "time passed";
an impact happens *now*. Every one of these wants a cut:

- consequence shots (the shell cracks → cut from the blow that cracked it)
- the aftermath insert (a broken sword, a dropped pendant, an empty seat)
- an interruption (a battle is interrupted by the sky changing → cut, not dissolve)
- penetration (something flies *into* something else → cut, or better, a continuation)

The test: **if the second shot is caused by the first, cut. If it merely follows it,
dissolve.**

**A cut needs air when the content jumps two axes at once.** One axis (new angle, or new
subject, same room) cuts fine. Two — new location *and* new time, or new era *and* new
tone — reads as a mistake. Exterior→interior of the *same building* is one axis and cuts
beautifully; interior chamber→exterior forest at dusk is two and needs 0.70 s.

**Flashbacks and memories are always entered on a dissolve, never a cut.** No exceptions
found yet.

**Reserve one transition for one motif, and let nothing else use it.** In CHRONO `flash`
means *time-gate jump between eras* and only that. The motif is the reason the grammar
works; the moment a `flash` appears at a boundary that is not a gate crossing, every other
flash in the film loses a little meaning. Two corollaries learned the hard way:

- **Travel by vehicle is not a gate.** CHRONO's Epoch crosses time without a gate, so
  Epoch travel gets a `dissolve`. That is not a fudge — it is the distinction the motif is
  *for*, and honouring it makes the flashes read louder.
- **Motif density beats motif purity.** Three `flash` boundaries inside 17 seconds — even
  when all three are genuine era jumps — stop reading as a motif and start reading as a
  slideshow preset. In an epilogue, where the job is release, one flash for the payoff and
  dissolves after it. Budget the motif like a limited resource: roughly one per 45 s of
  film, never two adjacent.

**Three act breaks, spread by story shape, not by clock.** `fade` is the only transition
the audience consciously notices. Two of them 27 seconds apart is not two act breaks, it
is one act break and one glitch. Space them at the film's real structural hinges — for a
five-act recap that landed at ~36%, ~74%, and the coda. If a story beat *feels* like an
act-out but you already have three fades, the answer is a `cut` into silence, which is
often stronger anyway.

**`soft` is systematically underused.** CHRONO used it 4 times in 108. It is the right
answer far more often than that: two shots of the same subject at different scale, a
sibling pair, a wide and its crowd-level counterpart, a montage inside a scene. Reach for
`soft` before `dissolve` whenever the two shots are the same *thought*.

---

## 2. xfade gotchas, measured

These are the ones that cost real time. All measured with `signalstats` / `astats` on
actual segments from `11-short-film/the-hollow-choir/_work/`.

### `fadeblack` and `fadewhite` are asymmetric — extreme at ~25%, not 50%

`fadeblack:duration=1.0`, sampled per frame at 24 fps:

| t into transition | 0.00 | 0.08 | 0.17 | **0.21** | 0.33 | 0.50 | 0.75 | 1.00 |
|---|---|---|---|---|---|---|---|---|
| Y average | 68 | 39 | 5 | **1.4** | 4 | 15 | 37 | 53 |

`fadewhite:duration=0.5`: peak Y = **243 at 0.125 s** (25% in), then 0.375 s to recover.

So the shape is a **fast snap to the extreme, then a slow reveal at 3× the length**. It
never reaches true black (1.4/255) or true white (243/255), and **it never holds**.

Consequences:

- A 1.00 s `fade` act break is a **0.21 s blink**, not a breath. If you want an act break
  the audience registers as one, set `"in_dur": 1.6` — that puts the black bottom at
  0.4 s and the reveal at 1.2 s. Nothing shorter than ~1.4 s reads as an act break.
- The 0.50 s `flash` is *correct as-is*: a 0.125 s blow-out and a 0.375 s recover is
  exactly what a flash should feel like. Do not lengthen it.
- A `fadeblack` **into the film's final image** is a blink before the last shot, and then
  the master out-fade blacks it again 4 s later. If the last shot is meant to bloom, use
  `dissolve`. If it is meant to be an act-out, use `fade` with `in_dur >= 1.6`.
- **You cannot hold on black with xfade.** If a film genuinely needs a beat of black
  between acts, insert a real black segment; xfade will not do it.

### `acrossfade` does not dip when the picture does

`epic.py:470` pairs every video transition with `acrossfade`. At a `fadeblack`/`fadewhite`
boundary the picture goes to the extreme and **the audio sails straight through**. Measured
across a 1.0 s `fadeblack`: audio RMS was −27.6 dB immediately before the transition and
−27.6 dB at the exact frame the picture hit black. Full level, no dip.

A picture that snaps to black while the sound continues unchanged reads as a *dropped
frame*, not an act break. If you want a real act break, the audio has to dip with the
picture: `afade=t=out` on A, `afade=t=in` on B, and mix — not `acrossfade`.

### `acrossfade` attenuates the first words of the incoming narration

`acrossfade=d=D` ramps the incoming stream from silence to unity over D seconds. Narration
is delayed by `LEAD = 0.30 s` inside its segment. So at a boundary:

| boundary | D | narration starts at | acrossfade gain there |
|---|---|---|---|
| `soft` | 0.28 | 0.30 s | unity (just clears) |
| `dissolve` | 0.70 | 0.30 s | **0.43 (−7.4 dB)**, unity only at 0.70 s |
| `fade` | 1.00 | 0.30 s | **0.30 (−10.5 dB)**, unity only at 1.00 s |

Every dissolve in the film ducks the first word of the next line by ~7 dB, and every act
break by ~10 dB. **Rule: `LEAD` must be ≥ the incoming transition duration.** Either raise
`LEAD` to 0.75 s (costs 0.45 s per shot, ~50 s over 109 shots) or — better architecture —
crossfade only the ambience/SFX bed and lay narration on its own continuous track at
absolute timecodes over the finished picture, the way the music step already does.

### Transitions eat picture from both ends

Each non-cut boundary consumes `d` seconds from the outgoing shot's tail *and* `d` from the
incoming shot's head. On CHRONO: 51 non-cut boundaries × their durations = **32.3 s removed
from 649.5 s of picture**, a 5.2% shrink. Two things follow:

- Shot lengths sized as `LEAD + narration + tail` are **short by `d_in + d_out`**. With
  `tail = 1.15` and a 0.70 s dissolve following, the outgoing line's clean air drops to
  0.45 s; before a 1.00 s `fade` it drops to **0.15 s** — the last syllable lands on the
  dip. Size shots as `d_in + LEAD + narration + tail + d_out`.
- `tail` is film-global in `epic.py` (`shot_frames`, and again in `edit()`), so you cannot
  give the shot before an act break more air. Make it `s.get("tail", film.get("tail"))`.

### Compute xfade offsets from the **video** stream, not the container

`ffprobe -show_entries format=duration` returns `max(video, audio)`. AAC's tail padding
makes audio 0–19 ms longer than video per segment; on a finished 78.25 s master the
container reported **78.469 s — a 219 ms lie**. `_xfade_group` accumulates
`off += format_dur[i-1] - d`, so offsets drift late by up to ~20 ms per boundary. Inside a
10-item chunk that is ~180 ms; at a 0.28 s `soft` boundary the fade can then extend past
the outgoing stream's end and xfade freezes or blacks. Use
`ffprobe -select_streams v:0 -show_entries stream=duration`.

Same applies to any duration used for a filter time: derive the master's out-fade and the
score's `-t` from `ffprobe` on the actual joined file, never from arithmetic. Arithmetic
that is 200 ms long puts `fade=t=out:st=total-1.5` past the end and **the film has no
fade-out at all** — with no error.

---

## 3. `concat -c copy` — what it can and cannot be trusted with

Verified on six real segments (73+73+121+97+73+97 = 534 frames):

**Trustworthy for A/V sync.** Output video was 534 frames / 22.250 s — frame-exact.
Audio came out 22.2697 s, i.e. **+20 ms total, not +20 ms per junction**; ffmpeg trims AAC
priming at each junction (1056 encoded frames in, 1052 out). Concatenating 50+ separately
encoded segments does **not** accumulate drift. Cuts are free and lossless — keep doing it.

**Two silent-corruption modes, both exit 0.** `sh()` in `epic.py` only checks the return
code, so both pass as success:

1. **Missing input file.** ffmpeg prints `Impossible to open …` / `Error during demuxing`
   to stderr, **exits 0**, and writes a file containing only the segments before the
   missing one. Measured: 2-file list, 1 missing → 73-frame output, exit 0.
2. **Resolution mismatch.** A 768×512 segment concatenated between two 1280×704 segments
   produced a 267-frame file (all frames present) whose header declares 1280×704.
   **Exit 0.** The middle third is garbage on playback.

Mode 2 is a live hazard because segments in `_work/` are cached by filename with no record
of what resolution they were built at. The documented workflow is "preview at 480p, then
commit to HD" — do that with `epic.py --sd` and then re-run `--stage edit` without `--sd`
and you get a silently corrupt film. **Always `rm -rf _work/` when changing resolution**,
and prefer a pre-flight probe that asserts every segment shares width/height/fps/pix_fmt.

Also: scan ffmpeg's stderr for `Error during demuxing` even on exit 0.

---

## 4. Cache invalidation — the thing that will waste your afternoon

`epic.py`'s edit stage caches three tiers by filename with `if not os.path.exists(...)`:

| File | Depends on |
|---|---|
| `_work/<shot_id>.mp4` | clip, voice, sfx, `titles` — **not** transitions. Safe to keep. |
| `_work/reel_NNN.mp4` | **the transition layout.** Reel *N* is "the run of cuts starting at boundary *N*". |
| `_work/_joined_gNN.mp4` | the reel layout, i.e. the transition layout again. |

Change one `"in"` value and re-run `--stage edit`, and the reel numbering shifts while the
old `reel_*.mp4` files are all still on disk and still get reused. **The film is silently
assembled from the previous grammar.** After any transition edit:

```bash
rm -f _work/reel_*.mp4 _work/_joined*.mp4
```

Keep `_work/<shot_id>.mp4` — those are the expensive part and they are still valid. Delete
only the shot segments whose `titles` you changed.

Related latent bug: `join_mixed` names its group files `f"{out[:-4]}_gNN.mp4"` and recurses
with the **same** `out`, so a film needing three levels of chunking (>100 reels, i.e. >100
non-cut boundaries) collides level 2 against level 1 and — because of the existence check —
silently reuses the wrong files. Include the recursion depth in the name.

---

## 5. Shot rhythm

Shot length in `epic.py` is **derived, not authored**: `LEAD + measured_narration + tail`,
quantised up to LTX's 8n+1 frames, capped at `FRAME_CAP = 241` (10.0 s @ 24 fps). This is
correct — it is the only way a ten-minute narrated film never freezes a frame — but it
means **the narrator writes the cutting rhythm**, and prose rhythm is flatter than film
rhythm. You have to fight it back.

### The metronome check

Run the film's derived durations and look for stretches with no short shot. On CHRONO:

| Stretch | Shots | Range |
|---|---|---|
| `010_kingdom` → `380_resolve` | **38** | 4.04–8.04 s |
| `440_robo_torn` → `600_tyrano` | 19 | 4.04–8.04 s |
| `620_falling` → `700_descent` | 12 | **5.38**–8.04 s |

The first shot under 4 s arrived **219 seconds in**. That is 3½ minutes without a single
punctuation mark. A film's pulse comes from the *contrast* between a 7 s shot and a 2.5 s
one; a run of shots all between 4 and 8 s has no pulse at all, only a duration.

The whole distribution, for calibration — CHRONO's 109 shots by derived frame count:

| ≤3.4 s | 3.7–4.4 s | 4.7–6.4 s | 6.7–8.0 s | ≥8.4 s |
|---|---|---|---|---|
| 6 shots | 19 | 45 | 36 | 3 |

**81% of the film sat inside a single 4-second band.** A healthy narrated cut wants
something closer to 15 / 25 / 35 / 20 / 5 — noticeably more weight at the short end.

### 8n+1 quantisation is coarser than you think

At 24 fps the legal lengths are 4.04, 4.38, 4.71, 5.04 … — steps of **0.333 s**. Anything
needing between 3.71 and 4.04 s of screen time becomes *exactly* 97 frames. On CHRONO that
collapsed **twelve shots to a byte-identical 4.0417 s**, nine of them inside the first
third: `030_crono`, `050_fairmontage`, `070_teleport`, `090_gate`, `110_step_through`,
`180_fight`, `210_return`, `230_arrest`, `270_escape`, `320_survivors`, `350_eruption`,
`600_tyrano`. Twelve identical shot lengths *is* the metronome. Check the frame-count
histogram, not the requested seconds — the quantiser hides collisions.

Practical floor: with `LEAD 0.30 + tail 1.15`, a narrated shot can never be shorter than
1.45 s + speech. To get a genuinely short narrated shot you need a line under ~2.0 s of
speech (four or five words).

**Rule of thumb: no more than six consecutive shots without one under 3.5 s.** One short
shot every ~25 s is enough. Get them by writing shorter narration lines for the beats you
want fast — a three-word line ("It works.", "Lavos answers.", "They break it anyway.")
buys a 2.5–3.0 s shot for free, and those turned out to be CHRONO's three best-cut moments.

### The silent-shot trap

Shots with no `say` fall through to `film["seconds"]` — so on CHRONO **all nine silent
shots came out at exactly 4.04 s.** The shots where you have complete freedom over length
were the only ones with no variation at all, and they are all the action beats. Always set
per-shot `"seconds"` on silent shots, and set them *against* the neighbours:

| Kind of silent shot | `seconds` |
|---|---|
| pure action / an exchange of blows | 2.0–2.5 |
| a run or chase | 2.5–3.0 |
| a montage (needs room to read) | 5.0–5.5 |
| an overwhelming event that must dominate | 5.0–6.0 |
| a transitional walk-into-frame | 3.0–3.5 |

### Scale

`FILMMAKING.md` already says vary the scale. What the audit adds is *how to find the
violations*: classify every shot's prompt by its opening scale word and look for runs.
CHRONO's prompts were **49 wides out of 109**, including runs of 4, 4, and 5 consecutive
wide shots (~26–30 s each). A run of wides is the exact thing that makes generated footage
read as a moodboard, because a wide gives the eye nowhere to land and every wide is
composed by the same model with the same instincts.

**Rule: never three consecutive shots at the same scale. Break a wide run with an insert,
not with another wide from a different angle.** An extreme close-up of an object costs the
same 13.5 s of LTX as a wide and does ten times more for the cut. CHRONO's best boundaries
are all scale changes into a macro insert (`100_dropped` — the pendant on the boards;
`490_broken_sword`; `805_eggname`).

The epilogue deserves its own note: four consecutive wides is wrong *everywhere*, but it is
worst at the end, where the film should be closing in on faces. Resolve wide-to-close, not
wide-to-wide.

### Length is nearly free, shots are not

LTX charges **13.7 s for 193 frames vs 13.5 s for 97** — length is free, each additional
*shot* costs a keyframe plus a clip. So the economics push toward long shots, and the
craft pushes back. Resolve it by making the long shots genuinely long (7–10 s of real
camera movement) and the short ones genuinely short (2–3 s), rather than letting everything
converge on 5.

---

## 6. Continuous takes (`from_prev`)

`"from_prev": true` extracts the last frame of the previous clip, hands it to LTX as the
start frame, and the boundary between them becomes invisible. Pair it with `"in": "cut"` —
a transition would defeat the point.

**Where it beats a cut:** when two shots are **one continuous event that will not fit in
one clip**. Not "the same location" — the same *moment*.

Good uses, in order of value:
1. **A cause and its consequence** — the blade swings / the thing breaks; the machine
   floods with power / the creature rises through the floor.
2. **A death, a transformation, or anything the audience must not be given an escape
   from.** A cut is a blink and a blink is relief. If the point is that there is no relief,
   chain it.
3. **Penetration or entry** — flying into something, descending into something.
4. **Exceeding `FRAME_CAP`.** Two chained shots instead of one impossible 15 s clip.

**Where it does not help:** anything crossing location, era, or tone. The chained start
frame will fight the new prompt and you get morph rather than continuity.

### Costs and caveats

- Continuations are **serial** — `continuations()` runs after the main batch, one at a
  time, because each needs its predecessor finished. Budget ~15 s of render plus up to 6 s
  of poll latency each. Four extra continuations is about a minute. Cheap; use them.
- **The chained frame is 1280×704, not 1664×928.** A continuation starts from video, not
  from a Qwen keyframe, so it is measurably softer than its neighbours. Do not chain more
  than two shots deep or the softness compounds visibly.
- `epic.py:330` grabs the frame with `-sseof -0.08 -frames:v 1`, which at 24 fps lands
  **~2 frames before the true last frame**. Those two frames play before the chained clip
  starts, so there is an 83 ms hiccup at a boundary that is supposed to be invisible. Use
  `-sseof -1 -update 1 -frames:v 100` (keeps overwriting, ends on the real last frame).
  The `-q:v 2` on that command is a JPEG flag and does nothing for a `.png` output.
- `epic.py:340` gives **every** continuation the same `noise_seed = seed0 + 977`. With two
  it does not matter; with six their motion and artefacts correlate. Add `i * 13`.
- No guard for `from_prev` on the first shot — `ids[-1]` wraps to the last shot of the film.

---

## 7. Score cues on a derived timeline

`music` cues anchor to `at_shot`, which is right — hand-written timecodes drift the moment
a narration line is re-rolled. But nothing checks that the cues **sequence**, and the shot
starts they resolve to are not obvious from reading the JSON.

CHRONO's 17 cues, resolved: `m01_theme` (46 s) starts at 0.0 s and `m02_fair` starts at
**6.0 s** — the main theme is buried under the fair tune for 40 seconds, both at level ~0.2,
which is where the narration lives. Six other pairs overlapped by 30–55 s. `m17_finale` was
84 s long starting at 576 s of a 617 s film: 43 s of it never plays, so its own 3.5 s
out-fade never happens and the cue is chopped by the master fade.

**Always resolve the cue timeline before rendering music** — it is arithmetic, no GPU:

```python
# starts[shot_id] accounting for per-boundary transition overlap
t = 0.0
for i, s in enumerate(shots):
    starts[s["id"]] = t
    t += segdur[i] - (trans_dur(shots[i+1]) if i+1 < len(shots) else 0.0)
```

Then set each cue's `seconds` to `next_cue_start - this_cue_start + 4.0` (the +4 covers the
2.5 s in-fade / 3.5 s out-fade so consecutive cues overlap by a few seconds instead of
stacking or gapping). Cap the last cue at `film_total - its_start + 2`.

One more mix note: `loudnorm=I=-16:TP=-1.5:LRA=11` is applied **single-pass** over the whole
film (`epic.py:646`). Single-pass loudnorm is adaptive and will ride the gain over ten
minutes of alternating quiet narration and loud SFX, pumping the narration level. For
anything over ~2 minutes, measure first and apply with `linear=true`.

---

## 8. Pre-flight checklist before `--stage edit`

Cheap, no GPU, catches everything above:

1. `rm -f _work/reel_*.mp4 _work/_joined*.mp4` if any `"in"` changed.
2. `rm -rf _work/` entirely if the resolution changed.
3. Probe every `_work/*.mp4` for identical `width,height,r_frame_rate,pix_fmt`.
4. Resolve derived shot durations and list every stretch of >6 shots with none under 3.5 s.
5. Classify prompts by scale word; list every run of ≥3 at the same scale.
6. Count transitions. Expect roughly: `cut` ~50%, `dissolve` ~25%, `soft` ~10%,
   motif transition ~1 per 45 s, `fade` exactly 3.
7. Resolve the music cue timeline and check for overlaps > 8 s, gaps > 2 s, and any cue
   extending past the end of the film.
8. Assert no `"in": "flash"` (or whatever your motif transition is) at a boundary that is
   not an instance of the motif.

## 9. Legacy films

`trans_of` reads only `shot["in"]` and `film["default_transition"]`. The old top-level
`"transition": 0.35` float (used by `hollow-choir.json`, and absent entirely from
`last-good-year.json`) is **silently ignored** — re-running `--stage edit` on either film
today produces a version with zero dissolves and no warning. Either map a legacy
`transition` float onto `{"in": "dissolve", "in_dur": value}` for every shot, or refuse to
edit a film that has neither `in` nor `default_transition` on any shot.

---

# 10. Long continuous takes by chaining (added 2026-07-30)

A single LTX clip drifts past roughly 241 frames (10 s at 24 fps). That is a hard ceiling on
one *generation*, not on one *shot*.

## The primitive

`"chain": N` on a shot renders N clips. Clip 1 starts from the keyframe; every later clip
starts from the **previous clip's final frame**. Concatenated with a hard cut, the motion
runs straight through and the joins are invisible — one continuous take.

```json
{ "id": "300_bazuso", "chain": 4, "seconds": 32,
  "motion":  "Guts charges the giant, sword dragging sparks off the stone",
  "motion2": "The giant's axe comes down; Guts turns it aside and keeps moving",
  "motion3": "Guts is thrown back through a market stall, rolls, comes up",
  "motion4": "He drives up under the guard and the giant goes down" }
```

`seconds` is the length of the **whole scene**; `chain` decides how many clips it is split
across. Optional `motion2`, `motion3`, … direct each successive clip, which is how you
choreograph a fight instead of describing an average of one.

## Why this is the right way to do action

- **It's cheap.** LTX cost is nearly flat in clip length, so 4×8 s costs about what 4×4 s
  would. A 32-second continuous take is roughly the price of four ordinary shots.
- **It beats cutting.** Two independently generated keyframes of "the same" fight never
  match; chained frames match exactly, because each one *is* the previous frame.
- **It permits choreography.** One clip can hold one action. Four chained clips hold a
  charge, a parry, a reversal and a kill — which is a fight rather than a shot of fighting.

## Limits, measured

- Chained frames come from **1280×704 video**, not the 1664×928 keyframe, so each generation
  is a little softer than the last. Beyond about **4 links** it is visible. Reset with a new
  keyframe rather than chaining 8 deep.
- Motion accumulates: if link 1 is a fast push, link 4 will still be pushing. State the
  camera afresh in each `motionN`, or say "camera settles".
- Add `id_lora` (`ltx-2.3-id-lora-talkvid-3k`) when the chain holds a face — that is exactly
  where identity drift would otherwise show.

## Related, same mechanism

`"from_prev": true` chains a shot off the **previous shot** instead of off itself. Use it
when one event spans a boundary you want invisible — an eruption then the sky burning, a
fall then the impact. Combine with `"in": "cut"`.

## 11. Arcs: where the fast parts go

A cut rhythm is not a constant. Measuring a 52-second vertical short at a tight scene
threshold gave 182 shots, median 0.10s, 87% of them under half a second - but the density
was nowhere near uniform:

    cuts per 5s block:  9  10  6 | 25 | 14 | 27  26  22 |  8 | 33 |  2
                        build       BURST  rest  ASSAULT   rest FINAL resolve

That shape is the craft, not the average. A piece cut at a flat 0.10s throughout is
exhausting and reads as noise; the 33-cut block only lands as violent because an 8-cut
block came right before it. The breathers are load-bearing.

Three rules fall out of it:

  * **Density comes from beat COUNT, not from shortening shots.** `clash` at intensity 1.0
    is already 0.19s per shot, which IS burst density. Pushing intensity past ~1.3 makes
    shots too short to register as images at all - the viewer sees flicker, not cutting.
    If a block needs more cuts, add beats to it.

  * **Spend the runtime unevenly.** Roughly: 30% building, 45% assault, 15% breathing,
    10% resolving. The single longest hold in the piece belongs at the very end.

  * **Tease before you start.** The reference plants a blurred flash-forward of the fight
    inside its opening block, several seconds before the fight begins.

`SPORTS_CLASH_50S` in `scripts/scene_templates.py` encodes exactly this, and
`arc_summary()` prints the block histogram next to the reference's so a re-time can be
checked before any GPU time is spent. To re-time a film, edit the arc - not the film.

## 12. Fast cutting needs recognition, or words

A reference short cut at a 0.10s median and read perfectly. Ours copied the rhythm exactly
- 174 shots, matching density curve, higher motion energy - and the verdict was "no
substance, they feel random, there's no context."

The rhythm was never the thing that made the reference legible. It cut over subjects the
viewer ALREADY KNEW: real footballers, a famous anime character. Recognition is free
there, so a tenth of a second is enough to land a shot. With invented characters there is
no recognition to borrow, and a 0.2s shot is gone before it means anything.

Two ways to pay for speed. Use at least one:

  * **Recognition.** Reuse setups. Return to the same angle, the same face, the same
    location, so by the fourth time the viewer reads it instantly. Using each generated
    clip exactly once - which is what "generate few, cut many" tempts you into - means
    every single shot is brand new and none of them accumulate.

  * **Words.** A caption per beat. The images then illustrate a story instead of being
    asked to imply one. THE DERBY had dialogue on 5 of 35 beats - 86% of the film said
    nothing, and the plot existed only in the prompt file where no viewer could reach it.

Also give the piece a CLOCK. "89th minute... fifty seconds... twenty... five... now"
converts a pile of disconnected images into one event with a deadline, and gives every
cut a reason to be where it is. It costs nothing - it is text - and it is the single
cheapest structural fix available.

Measure it: count the fraction of beats that say anything. Under about half, and a fast
edit will read as noise however good the individual frames are.

## 13. Transitions and camera moves — the actual literature

Reading worth doing, in order of usefulness here:

  * **Walter Murch, *In the Blink of an Eye*.** The one to read first. His **Rule of Six**
    ranks what a cut must serve, and the weights are the surprising part:
    emotion 51%, story 23%, rhythm 10%, eye-trace 7%, two-dimensional plane of screen 5%,
    three-dimensional space of action 4%. Spatial continuity — the thing amateurs agonise
    over — is worth 4%. If a cut serves emotion, it survives breaking every other rule.
  * **Karel Reisz & Gavin Millar, *The Technique of Film Editing*.** The systematic one.
  * **Steven Katz, *Film Directing Shot by Shot*.** Coverage and camera-move vocabulary.
  * **Bordwell & Thompson, *Film Art*.** The grammar, formally.
  * For anime specifically: the Kanada school and Ozu's pillow shots are the two traditions
    worth stealing from, and they pull in opposite directions.

### The transition vocabulary

    CUT            default. ~95% of an edit. Needs no justification.
    MATCH CUT      shape/motion/idea rhymes across the cut. The strongest device available.
    L-CUT          audio of the NEXT scene starts under the current picture.
    J-CUT          audio of the current scene continues over the next picture.
                   L and J cuts are what make dialogue scenes feel professional. Cutting
                   picture and sound at the same frame is the single loudest tell of an
                   amateur edit.
    DISSOLVE       passage of time. Expensive - use rarely or it means nothing.
    FADE TO BLACK  act break. Full stop, not a comma.
    WIPE / IRIS    stylised, era-specific. Deliberate or not at all.
    SMASH CUT      loud to quiet, or quiet to loud. Contrast is the whole effect.

### The camera-move vocabulary

Every move must be a CHOICE, and "static" is a legitimate and frequently correct one.
Anime holds still far more than western live action; a locked frame with a good drawing
is not a failure.

    static      no move. The default for reaction shots and pillow shots.
    push        slow in. Growing interest, intimacy, dawning realisation.
    pull        slow out. Isolation, abandonment, endings.
    pan L/R     lateral reveal, or following action.
    tilt U/D    up = power/scale; down = defeat/diminishment.
    handheld    unease. Very subtle or it reads as a mistake.

**The bug this section exists because of:** `punch` was the only implemented move, and four
of the seven episode templates called it, so nearly every shot in an 8-minute episode
panned left identically. One hardcoded move applied everywhere reads as a rendering
artefact, not a style.
