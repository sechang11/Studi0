# comfy-studio — standing instructions for the agent

This repository is an offline AI film studio. Two invariants override everything: **it must be
usable by a person with no knowledge of AI, and the generations must be flawless.** Measure
rather than assert; look at the render before reporting; never adopt anything on one seed.

## First, the clock

At the start of any session that will generate or change how generation works, run
`python3 studio/_tools/review_clock.py`. If it says the review is due, walk playbook §0's list
before generating anything - new weights, new ComfyUI nodes, orphan models on disk, the paid
engines' price and capability, the standard battery on anything new - update WHERE-WE-STAND and
§96, run `method_check.py`, then `review_clock.py --checked`. The stamp means the list was walked.

## The pipeline (playbook §96) and the method (single source: `docs/METHOD.md`; measurements: §95)

**§96 is the go-to workflow** - look, then library, then scenes, then the seven blocks per shot,
render on LTX-2.5 by default, read the takes, finish; and the rule for when money is spent on a
paid engine (start frames first, by scene, measured with `hybrid_frame_test.py` before committing).
Build to §96; §95 says why each step is as it is.

Build every story and every shot by these. `docs/METHOD.md` is the source; §95 carries each
rule's measurement; this file is the summary. **Run `python3 studio/_tools/method_check.py`
before committing a change to any of the three** - it derives the numbers from the code and
fails when the copies disagree. The PDF is generated only by `studio/_tools/build_method_pdf.py`
(`~/.pdfvenv/bin/python`); never hand-build it.

**Story**
1. Refs before words: every character is a pack, every place a plate, before a shot is written.
   Never describe in a prompt what a reference already carries.
2. One identity route per character, recorded on the pack: reference path by default; a trained
   face only where it beat the reference on three seeds by more than max(0.02, spread/2)
   (`pack_lora.py`); never both at once. Roster levels: **1 = complete pack, the casting floor**;
   2 = also carries a trained face (a bonus, not a requirement).
3. A scene is one place, one light, one source for every start frame: each shot's anchor is
   composed from the scene's plate and the character's pack (`assets/anchor_shot_NNN.png`,
   `anchor: "file:..."`), or continues from `prev_last`. The anchor fixes where a shot BEGINS.
   Framing and action must agree - a close-up cannot hold a character who walks away.
4. One beat per shot when a face matters. Internal cuts only with the face in the start frame or
   no face at all; cuts between faces happen at assembly.
5. Length from `LTX_SAFE` (0.9 MP→30 s, 1.2 MP→20 s, 1.5 MP→12 s, 2.0 MP→8 s); pacing from
   the edit. Timecodes in a prompt set nothing on LTX-2.5; the word *cut* makes the hard cut.
   The face clock is by motion, not look: still ~4.3 s, walk ~4.0 s, a crouch not followable.
6. Sound is written: sources named, a line needs an on-screen mouth, *no music* when the edit
   owns the score, the scene bed from ACE-Step at the finish. Coverage shots inherit the scene's
   ambience as sfx; a shot with no written sound renders silence.
7. Continuity of place is the plate, not a LoRA. LoRAs do not stack past two.
8. The finish is half the film: one grade after the cuts, canvas from the takes, optional 2×
   master, loudness, and the film's frame count equals its takes' - checked.
9. Nothing is adopted on one render. A take is picked iff `_faults(take)` is empty - one rule
   for every path; notes never block a pick, faults always do, the log says which.

**Shot — seven blocks → compiler fields**
`anchor` · `subject/action/motion` · `framing/move` (+ `engine`: a field, default LTX; in-place
motions are pinned on H3 automatically; H3 pins hold in-place motion only) · `beats[]/
transition_in` · `dialogue/sfx/ambience` · film-level `look/grade/negative` · read
`identity/qc/angle_measured` before picking. One mover per beat; a whole body, never a fast limb
against a still torso.

**What the box cannot do yet, and what it can that the docs once denied**
- Pace beats inside one generation by the clock. Cut at assembly.
- Give a photoreal pack a trained face *from the roster*: photoreal faces DO train
  (`lora_train_sdxl.py` on RealVisXL, §56); the roster's trainer is wired to the anime workflow
  33, and the photoreal keyframe engine is Qwen, to which no SDXL LoRA attaches. The unlock is a
  photoreal SDXL render route, not a trainer.
- Stack more than two LoRAs; improve a take by sharpening its start frame (3 of 3 worse).
- **Multi-reference IS on the box**: `MiniMaxH3ReferenceToVideo` takes up to nine tagged
  `<Picture i>` references (+ video/audio refs); weights `minimax_h3_ref2va` on disk; workflow
  `63_minimax_h3_ref2va.json`, test `_tools/ref2va_test.py`. **Measured 2026-09-07: as wired
  it supplies neither identity nor place** (0.19-0.25 vs 0.65 for a composited start frame, 3/3,
  drawn and photoreal). A route gap, not an architectural one; do not plan a film on it yet.

## Operating rules that have cost time

- **Never overwrite a tracked file from a local copy without checking it is unchanged since you
  last read it** (`git status -- <file>` / mtime). Two sessions share this checkout; on
  2026-09-07 a `scp` erased another session's fifteen corrections. Merge, do not replace.
- Never edit `studio/_tools/film_routes.py` while a film job runs; use `~/bin/safe_patch2.sh`
  (waits for quiet, backs up, compiles, reloads or rolls back). `/tmp` is cleared overnight.
- Patches: Write → scp → run. Never inline nested-quote heredocs. Commit messages via `-F file`.
- ComfyUI holds the last video model (~20-28 GB) after a render: POST `/free` and WAIT for the
  memory (`post.make_room`) before any other GPU work or before loading a second big model -
  loading H3 ref2va on top of resident LTX killed the process silently. Never run ESRGAN and an
  LTX render together.
- A job "running" with an idle ComfyUI queue and no new log line for minutes is a dead thread:
  check `/tmp/comfy.log` for "Failed to validate prompt"; `comfy.run` now raises instead of
  exiting, and a reload of film_routes clears the zombie from JOBS.
- Stage explicit paths only (shared checkout); renders and film state stay out of git.
- Compare frame counts (`ffprobe -count_frames`), never container durations.
- Real people's voices in `studio/voices/` marked blocked stay blocked; no real people as
  subjects; consent gates any photo-derived character; `nsfw` in every negative.

When a rule here disagrees with a measurement you have just made, the measurement wins - and it
goes into the playbook with its number, the guide, and this file, in one commit, and
`method_check.py` passes before it lands.
