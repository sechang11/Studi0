# Rack focus (`cam-rack-focus`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | fails | 2026-08-08 | none |

**Also called:** rack focus, pull focus, focus shift, shifting focus
**Not the same as:**
- [`cam-push-in`](push-in.md) - the camera moves; in a rack focus only the focus moves

## Recipe (v0, 2026-08-08)

None. `craft/VIDEO_RULES.md` PICTURE-04: `roll.py`'s *rack_focus* came back byte-identical to a static render; it needs a depth pass. Next to try: a depth map of the take (the previz depth, or MoGe) driving a variable blur in post.

## Checks before picking

- The focal plane visibly moves from one subject to the other.

## Progression

### 2026-08-08 · VIDEO_RULES PICTURE-04 · rack focus in roll.py · grade F
- **Did:** the preset.
- **Got:** a mean absolute pixel difference of exactly 0.00 against a static render.
- **Learned:** the preset does nothing until a depth pass exists.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| no change at all | no depth pass | a depth-driven blur (untested) | PICTURE-04 |

## Evidence

- `craft/VIDEO_RULES.md` (PICTURE-04), `studio/_tools/roll.py`.

## Open questions

- Everything.
