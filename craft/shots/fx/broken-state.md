# Something shown broken or dissolving (`fx-broken-state`)

| family | status | last tested | best result |
|---|---|---|---|
| fx | partial | 2026-08-03 | CHRONO keyframes: asked-for broken things came back whole, grade D |

**Also called:** broken sword, destroyed object, ruins, dematerialise, fading away, shattered remains, aftermath
**Not the same as:**
- [`fx-glass-shatter`](glass-shatter.md) - the moment of breaking; here the state after it

## Recipe (v1, 2026-08-03)

Do not ask a keyframe or a motion prompt to make something broken or vanish. Stage the "after" as its own start frame (drawn broken from the start) and cut to it.

## Checks before picking

- The object is in the state the shot needs in its FIRST frame.

## Progression

### 2026-08-03 · CINEMATOGRAPHY §1.7, §5 #5, §6 · broken and dematerialising things in CHRONO · grade D
- **Did:** keyframes and motion prompts asking for things to dematerialise (070, 150) or to be broken (260, 490 the broken sword, 440).
- **Got:** 070 and 150 came back solid; 260, 490 and 440 came back intact.
- **Learned:** the model draws the whole object; the "after" has to be its own keyframe, then cut.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the object is whole | a broken state asked in words | draw the after-state as the start frame | CHRONO 490 |

## Evidence

- `craft/CINEMATOGRAPHY.md` §1.7, §5, §6.

## Open questions

- An edit (Qwen) that breaks a drawn object, then the video from it.
