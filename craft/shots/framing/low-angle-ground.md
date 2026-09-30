# Ground-level shot (`frame-low-angle-ground`)

| family | status | last tested | best result |
|---|---|---|---|
| framing | proven | 2026-09-30 | cyber-alchemist 309; quantum-courier 106, grade A |

**Also called:** ground level, puddle level, boots shot, feet at floor level, worm's-eye close, low close shot, worms eye, worm's eye
**Not the same as:**
- [`frame-low-angle`](low-angle.md) - looking up at the figure from below; here the lens is on the ground framing the feet

## Recipe (v1, 2026-09-30)

Flux 2 for the start frame (Qwen drew full figures), "at ground level" and "the boots" named; H3 when the feet strike water.

## Checks before picking

- Only the feet and lower legs; the ground fills the lower frame.

## Progression

### 2026-09-07 · §71, §72 · a worm's-eye step-over · grade B+
- **Did:** twelve SDXL renders across three prompt shapes; then H3 with both ends pinned to the same empty ceiling plate; floor viewpoints described to Qwen.
- **Got:** every SDXL render reverted to eye level; the H3 pin got it first time (boots on one seed, the cape blacking out the lens on another). "The camera is lying on the stone floor" put a DSLR on the flagstones; "we are lying flat on our back" rendered a man lying on the floor.
- **Learned:** "a prompt cannot outvote weights on framing"; describe the viewpoint as geometry, never the camera or the observer.

### 2026-09-30 · cyber-alchemist 309; quantum-courier 106 · boots landing; boots striding through a puddle · grade A
- **Did:** 309: Flux 2 start frame, H3 seed 11. 106: "a LOW CLOSE SHOT at ground level ... the heavy-soled black combat boots ... splashing through a neon puddle", H3 seed 11.
- **Got:** both clean. Qwen's 309 candidates were full figures standing.
- **Learned:** Flux 2 for ground level.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a full figure instead of feet | Qwen ignores the framing | Flux 2 | cyber-alchemist 309 |
| the camera or an observer drawn in the picture | naming the apparatus | describe geometry only | §72 |

## Evidence

- `studio/samples/fight/cyber-alchemist/anchor_309_flux2.png`, `h3_309_s11.mp4`; `studio/samples/fight/quantum-courier/h3_106_s11.mp4`.

## Open questions

- None open.
