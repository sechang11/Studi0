# A line spoken on camera (`dia-line-on-camera`)

| family | status | last tested | best result |
|---|---|---|---|
| dialogue | proven | 2026-09-24 | native LTX-2.5, verbatim on 6 of 6 takes (§98.6), grade A- |

**Also called:** dialogue, a line, speaks to camera, lip sync, talking
**Not the same as:**
- [`dia-line-close`](line-close.md) - the line in a close-up, where the face fills the frame
- [`dia-walk-and-talk`](walk-and-talk.md) - the line while walking
- [`dia-narration`](narration.md) - a voice with no mouth on screen
- [`dia-vocal-effort`](vocal-effort.md) - sounds, not words

## Recipe (v2, 2026-09-24)

The line in quotes in the prompt, the mouth on screen, native LTX-2.5 speech; then a peak check (the takes come back clipped). Drawn (anime) mouths do not move: there the line is voice-over.

## Checks before picking

- The words heard (`take_rank.py` line check: under 60% of the words is a fault).
- Peaks (the 2026-09-24 takes clipped at 0.0 dBFS).

## Progression

### 2026-09-04 · §33, §37-§38, §43-§45 · native speech, then a voice pass · grade C
- **Did:** THE LAST BOAT's lines through the on-screen mouths; a speech-peak check; director review.
- **Got:** the mouths opened, but the director: "Most voices were wrong - incorrect speech or no speech". The peak check measured loudness, not words. Every line then got a voice-pack pass with the native track ducked to 0.12 (`ltx+vo`); the mouth no longer matches those words.
- **Learned:** measure the words, not the loudness.

### 2026-09-24 · §98.6 · "Get up. You are not finished." on LTX-2.5 · grade A-
- **Did:** native speech, six takes, checked by a speech model.
- **Got:** verbatim on 6 of 6 (content-word recall 100%); every take clipped (max 0.0 dB).
- **Learned:** native dialogue is "simply reliable, as long as the mouth is on screen"; add a peak check.

### 2026-09-27 · ACTION_SEQUENCE · a line nearly silent · grade C
- **Did:** DEAD STOCK's shot 110.
- **Got:** -56 dB: nearly silent.
- **Learned:** check the level of every line.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| wrong or no words | (2026-09-04, engine settings of the time) | native LTX-2.5 with the line in quotes | §43 → §98.6 |
| clipped audio | the engine's level | a peak check and limiter | §98.6 |
| drawn mouths do not move | anime | voice-over, two-shots, off-angles | §20 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §20, §33, §37-§38, §43-§45, §98.6; `studio/_tools/take_rank.py`.

## Open questions

- None of the 2026-09-30 films had dialogue.
