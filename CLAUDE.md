# comfy-studio — standing instructions for the agent

This repository is an offline AI film studio. Two invariants override everything: **it must be
usable by a person with no knowledge of AI, and the generations must be flawless.** Measure
rather than assert; look at the render before reporting; never adopt anything on one seed.

## The method (playbook §95, human version `docs/METHOD.md`)

Build every story and every shot by these. Each is measured; the measurement is cited in §95.

**Story**
1. Refs before words: every character is a pack, every place a plate, before a shot is written.
   Never describe in a prompt what a reference already carries.
2. One identity route per character, recorded on the pack: reference path by default; a trained
   face only where it beat the reference on three seeds above its own spread; never both at once.
3. A scene is one place, one light, one anchor. Shots start from the scene anchor or `prev_last`.
4. One beat per shot when a face matters. Internal cuts only with the face in the start frame or
   no face at all; cuts between faces happen at assembly.
5. Length from `LTX_SAFE` (0.9 MP→30 s, 1.5 MP→12 s, 2.0 MP→8 s); pacing from the edit.
   Timecodes in a prompt set nothing on LTX-2.5; the word *cut* makes the hard cut.
6. Sound is written: sources named, a line needs an on-screen mouth, *no music* when the edit
   owns the score, the scene bed from ACE-Step at the finish.
7. Continuity of place is the plate, not a LoRA. LoRAs do not stack past two.
8. The finish is half the film: one grade after the cuts, canvas from the takes, optional 2×
   master, loudness, and the film's frame count equals its takes' — checked.
9. Nothing is adopted on one render.

**Shot — seven blocks → compiler fields**
`anchor` · `subject/action/motion` · `framing/move` · `beats[]/transition_in` ·
`dialogue/sfx/ambience` · film-level `look/grade/negative` · read `identity/qc/angle_measured`
before picking. One mover per beat; a whole body, never a fast limb against a still torso.

## Operating rules that have cost time

- Never edit `studio/_tools/film_routes.py` while a film job runs; use `~/bin/safe_patch2.sh`
  (waits for quiet, backs up, compiles, reloads or rolls back). `/tmp` is cleared overnight.
- Patches: Write → scp → run. Never inline nested-quote heredocs. Commit messages via `-F file`.
- ComfyUI holds LTX (~28 GB) after a render: POST `/free` and wait for the memory before any
  other GPU work; never run ESRGAN and an LTX render together.
- Stage explicit paths only (shared checkout); renders and film state stay out of git.
- Compare frame counts (`ffprobe -count_frames`), never container durations.
- Real people's voices in `studio/voices/` marked blocked stay blocked; no real people as
  subjects; consent gates any photo-derived character; `nsfw` in every negative.

When a rule here disagrees with a measurement you have just made, the measurement wins — and it
goes into the playbook with its number, and this file gets corrected.
