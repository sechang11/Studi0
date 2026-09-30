# Grunts, kiais and breaths (`dia-vocal-effort`)

| family | status | last tested | best result |
|---|---|---|---|
| dialogue | works-with-caveats | 2026-09-06 | H3's own landing sounds, band-passed (§62.3), grade B+ |

**Also called:** kiai, grunt, effort sound, battle cry, exertion, breath sounds
**Not the same as:**
- [`dia-line-on-camera`](line-on-camera.md) - words

## Recipe (v1, 2026-09-06)

Let the video engine make the sound (H3 renders it with the action), then cut the voice band out of it. Text-to-speech says the word "grunt"; a sound model barks.

## Checks before picking

- It sounds like a person exerting, not a word.

## Progression

### 2026-09-06 · §62.3 · kiais from three sources · grade B+
- **Did:** StableAudio; IndexTTS-2 with words ("Hee-yah") and with grunts; H3 renders of landings.
- **Got:** small dogs barking, or someone SAYING a grunt; H3's landings (39 frames, 17n+5) carried a real effort sound, cut with a 300-3400 Hz band-pass around the loudest moment.
- **Learned:** the engine that renders the body renders its sounds.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a word instead of a grunt | text-to-speech | H3's own sound | §62.3 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §62.3.

## Open questions

- None open.
