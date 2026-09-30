# 2D anime (`style-2d-anime`)

| family | status | last tested | best result |
|---|---|---|---|
| style | proven | 2026-09-30 | system-error, grade A- |

**Also called:** anime, 2D animation, cel shading, cyberpunk anime, cartoon
**Not the same as:**
- [`style-stop-motion`](stop-motion.md) - puppets and miniature sets

## Recipe (v1, 2026-09-30)

References and start frames on Qwen-Image-2.1 (`--cast-engine qwen21`, `--compositor qwen21`); "2D anime, cel shading, clean line art" in every video prompt; LTX holds the look, H3 too.

## Checks before picking

- By eye: the face scorer is blind to drawn faces.
- Lines stay clean; nothing drifts toward 3D.

## Progression

### 2026-08-03 · CINEMATOGRAPHY §4, §6 · a storybook style LoRA · grade B
- **Did:** the LoRA at 0.9 across CHRONO.
- **Got:** it held only on large faces and hijacked the palette; off-brief 28% with it against 20% without.
- **Learned:** 0.75 globally; 0.50-0.55 for dark acts.

### 2026-08-21 · §19, §95.4 · the foundry's anime route · grade n/a
- **Did:** animagine keyframes with IPAdapter self-reference; anime packs.
- **Got:** "old man, elderly, wrinkles, beard" works where "grey hair, 70s" does not; the anime engine added sparkles nobody asked for.
- **Learned:** state age as explicit tags; put unwanted effects in the negative.

### 2026-09-30 · system-error · a cyberpunk anime short · grade A-
- **Did:** the recipe above; half the shots on H3.
- **Got:** the look held in every shot, with legible text.
- **Learned:** LTX and H3 both hold 2D anime from a Qwen start frame.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| no identity score | the scorer does not see drawn faces | pick by eye | system-error |

## Evidence

- `studio/samples/fight/system-error/`; `studio/_tools/fight.py` (`--cast-engine`).

## Open questions

- None open.
