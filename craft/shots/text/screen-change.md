# A screen whose content changes (`text-screen-change`)

| family | status | last tested | best result |
|---|---|---|---|
| text | fails | 2026-08-03 | CHRONO 340: the content morphed into mush, grade D |

**Also called:** changing screen, monitor content, a recording plays, display updates, TV screen
**Not the same as:**
- [`text-hud-overlay`](hud-overlay.md) - a fixed interface on glass; here the content itself changes

## Recipe (v1, 2026-08-03)

Do not animate a change of screen content inside one generation. Cut to a second start frame showing the new content.

## Checks before picking

- The screen's content is readable in every frame of the take.

## Progression

### 2026-08-03 · CINEMATOGRAPHY §5 #7 · a recording playing on a screen · grade D
- **Did:** 340_recording, the content changing during the shot.
- **Got:** the screen morphed into mush.
- **Learned:** cut to a second keyframe instead.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the screen turns to mush | content asked to change mid-shot | two keyframes and a cut | CHRONO 340 |

## Evidence

- `craft/CINEMATOGRAPHY.md` §5.

## Open questions

- A composited screen (the content as its own video, keyed onto the screen).
