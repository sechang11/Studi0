# Hovering and flying (`move-hover-flight`)

| family | status | last tested | best result |
|---|---|---|---|
| motion | works-with-caveats | 2026-09-30 | quantum-courier 304-310; cyber-alchemist 307-308, grade B+ |

**Also called:** flying, hovering, floating upward, levitation, flight between buildings, superhero flight
**Not the same as:**
- [`move-fall`](fall.md) - out of control, downward

## Recipe (v1, 2026-09-30)

Start frames that already show the pose in the air (body stretched out for speed; upright for a hover); H3 for flight at speed; the flight's cause visible (jets) or stated (gravity reversed).

## Checks before picking

- Her pose reads as flight, not as standing in the air.

## Progression

### 2026-09-30 · quantum-courier 304-310 · reversed gravity, then flight between towers · grade B+
- **Did:** 304 floating up (H3 seed 202); 306 rising (LTX); 307 flying fast (H3 seed 202); 309-310 glint and face in flight (LTX).
- **Got:** the float and the rise read well; the fast flight reads as her flying past; the circling camera asked for did not happen (see [`cam-arc`](../camera/arc.md)).
- **Learned:** flight poses come from the start frame.

### 2026-09-30 · cyber-alchemist 301 anchors, 307-308 · diving and hovering on jets · grade B+
- **Did:** Qwen and Flux 2 start frames.
- **Got:** Qwen drew her upright, "standing" in the air, for the free fall; Flux 2 drew the dive. The hover on jets (307, 308) read.
- **Learned:** Flux 2 for dynamic flight poses.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| standing in mid-air instead of diving | the compositor's pose | Flux 2 start frame | cyber-alchemist 301 Qwen |

## Evidence

- `studio/samples/fight/quantum-courier/h3_304_s202.mp4`, `h3_307_s202.mp4`; `studio/samples/fight/cyber-alchemist/anchor_301_flux2.png`.

## Open questions

- A take-off (from standing to flying) in one shot.
