# Blocking (where characters stand, and the line between them)

Who is on the left, who is on the right, and who crosses. Blocking is how a scene shows a
power shift without a word — the antagonist entering frame behind the protagonist, two
people who never share a frame until they do.

## Why it is blocked

Composition comes from tags. "from below, two boys" gets a low angle with two figures, but
not *which* figure is where, nor consistency between consecutive shots. This is also why
the multi-character clash shots failed: 8 of 35 beats had merged bodies and distorted limbs.

## Paths

1. **The 180-degree rule via tags.** Cheapest by far: `facing left` / `facing right` per
   character per scene, held consistent. Costs nothing and fixes the most jarring errors.
2. **Pose control.** SDPose and ControlNet are installed. Author blocking as a stick figure
   or pick from a pose library, condition on it. Real control, real work.
3. Two single-character generations composited into one frame. Fiddly, but it sidesteps the
   multi-character failure entirely.

Start with 1 — it is a compiler feature, not a model feature.

## Falls back to

Prompt text only, plus a warning when a scene has 3+ characters, which is where the model
reliably falls apart.
