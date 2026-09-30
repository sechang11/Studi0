# Steam fogging glass (`fx-steam-on-glass`)

| family | status | last tested | best result |
|---|---|---|---|
| fx | proven | 2026-09-30 | system-error 060, grade A |

**Also called:** fogging glasses, steamed-up glasses, condensation on lenses, misting glass
**Not the same as:**
- [`fx-smoke-steam-drift`](smoke-steam-drift.md) - steam drifting through the air; here it condenses on a surface and changes it

## Recipe (v1, 2026-09-30)

H3. LTX ignores the fogging.

1. Start frame: a close-up of the face over the steam source, the lenses "starting to" fog (system-error 060's start frame).
2. H3.
3. Prompt (system-error 060): "Steam rises from the bowl into her face and her round lenses mist over from the bottom up, until only the glow of her cyan eyes shows through the fog. She blinks slowly. Static camera, close."

## Checks before picking

- The lenses actually turn white by the end of the take.

## Progression

### 2026-09-30 · system-error 060 · the detective's glasses fog over the noodles · grade A
- **Did:** LTX and H3.
- **Got:** H3 seed 202 misted the lenses to white (in the cut). LTX pushed in and left them clear.
- **Learned:** H3 for an effect that changes a surface.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the glasses stay clear | LTX does not change a surface | H3 | system-error 060 LTX |

## Evidence

- `studio/samples/fight/system-error/h3_060_s202.mp4`.

## Open questions

- Fog clearing again afterwards.
