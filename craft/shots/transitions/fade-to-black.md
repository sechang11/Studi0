# Fade to black (`trans-fade-to-black`)

| family | status | last tested | best result |
|---|---|---|---|
| transitions | proven | 2026-07-29 | `in_dur` 1.6 s with an audio fade (EDITING), grade A- |

**Also called:** fade to black, fade out, act break, fade in from black
**Not the same as:**
- [`trans-dissolve`](dissolve.md) - one picture into another
- [`trans-flash`](flash.md) - a burst of white

## Recipe (v1, 2026-07-29)

At least 1.4 s (1.6 s used) to read as an act break, and fade the audio with it (`afade`): the picture's fade leaves the sound running.

## Checks before picking

- The picture reaches black; the sound goes down with it.

## Progression

### 2026-07-29 · EDITING · fades between acts · grade A-
- **Did:** measured the fade's curve and the audio under it.
- **Got:** fadeblack bottoms at Y 1.4 at 0.21 s; under about 1.4 s it does not read as an act break; the audio stays at -27.6 dB through it.
- **Learned:** `in_dur` 1.6; add `afade`.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| sound runs through the black | the picture fade only | `afade` | EDITING |

## Evidence

- `craft/EDITING.md`.

## Open questions

- None open.
