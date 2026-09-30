# Stop-motion (`style-stop-motion`)

| family | status | last tested | best result |
|---|---|---|---|
| style | partial | 2026-09-30 | smallest-gear, grade C+ |

**Also called:** stop-motion, Laika style, claymation, puppet animation, miniature set, handcrafted puppets
**Not the same as:**
- [`style-2d-anime`](2d-anime.md) - flat drawn animation
- [`style-photoreal`](photoreal.md) - live action

## Recipe (v1, 2026-09-30)

Not solved. Asking for the style in words ("Stop-motion animation, handcrafted puppets, miniature set" in every prompt) gave polished CG. What remains to try: references whose SURFACES are puppet-like (porcelain, felt, visible seams), and the cadence in post (on twos, 12 fps, which the film's alternate version has).

## Checks before picking

- By eye: do the faces look carved and painted, or rendered?

## Progression

### 2026-09-30 · smallest-gear · a clockmaker and an apprentice · grade C+
- **Did:** Qwen-Image-2.1 references and start frames; the style words in every prompt; LTX and H3; an on-twos version.
- **Got:** Pixar-like CG faces; the knit and the workshop are good; the on-twos cadence helps.
- **Learned:** the look is in the materials, not the words.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| CG instead of puppets | the engines' default look wins over the style words | puppet-surface references (untested) | smallest-gear |

## Evidence

- `challenge-films-2026-09-30/smallest-gear_final_on_twos.mp4` (local deliverables).

## Open questions

- Everything above.
