# L-cuts and J-cuts (audio/picture offset)

**The single highest-value missing feature.** We currently cut picture and sound on the
same frame at every transition, which is the loudest tell of an amateur edit. Real dialogue
scenes overlap: you hear the next scene before you see it, or the last line lingers over the
new picture.

    J-CUT   audio of the CURRENT scene continues over the NEXT picture
    L-CUT   audio of the NEXT scene starts under the CURRENT picture

## Why it is blocked

`cut()` in `scripts/short.py` builds one picture track by concatenating micro-shots, then
lays dialogue and music over the finished timeline. Voice cues are positioned from the beat
they belong to (`cues.append((line_start, ...))`), so audio is welded to its own picture.
Nothing models "this audio belongs to a shot other than the one it plays under."

## Cheapest path

1. Give each cue an `offset` field (negative = start early, positive = linger).
2. In the beat loop, add `b.get("audio_lead", 0)` to `line_start`.
3. Expose it as `transition: l_cut` / `j_cut`, which is sugar for an offset of ±0.6s on the
   boundary cue.

Roughly 20 lines. The risk is cues colliding once they can move, so the compiler must
detect overlapping voice cues and warn — an earlier film had 13 of 16 music pairs
overlapping by 20-40s and nobody noticed until it was measured.

## Test

Two dialogue scenes, one with L-cuts and one without, cut identically otherwise. If the
difference is not obvious on a blind listen, the offset is too small.
