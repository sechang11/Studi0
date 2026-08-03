# Lip sync

Characters currently speak with mouths that do not match the dialogue. In close-ups — which
is most of a dialogue scene — this is the most obvious remaining artificiality.

## Why it is blocked

Keyframes are generated before the audio exists, and LTX image-to-video has no phoneme
conditioning.

## Paths

1. **Post-hoc mouth driving** (LatentSync, MuseTalk, SadTalker). Take the rendered clip and
   the voice wav, drive the mouth. Best fit for our pipeline: it is a post pass, so nothing
   upstream changes. Risk: these are trained on photoreal faces and may fight anime
   proportions.
2. Generate mouth shapes as separate keyframes per phoneme and cut between them. This is
   what limited animation actually does, and it is stylistically authentic — anime uses
   three mouth positions, not lip sync. Cheap and possibly BETTER than real sync.
3. Avoid the problem: more shots where the speaker is off-screen, back to camera, or in a
   wide. This is legitimate direction, not a workaround, and it is free.

Try 2 and 3 before 1.

## Falls back to

Current behaviour, plus a compiler hint suggesting off-screen coverage for long lines.
