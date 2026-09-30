# A move continued across several generations (`cont-move-across-cuts`)

| family | status | last tested | best result |
|---|---|---|---|
| continuity | proven | 2026-09-30 | cyber-alchemist 103-110, 112, 210, 310, grade A- |

**Also called:** continuous move, chained shots, last frame to first frame, continuing a shot, seamless continuation
**Not the same as:**
- [`trans-match-cut`](../transitions/match-cut.md) - a cut between two DIFFERENT shots that rhyme; here one move split over generations
- [`cont-place`](place.md) - the room staying the room across cuts

## Recipe (v1, 2026-09-30)

Start each next generation on the picked take's LAST frame, not on its start frame; draw long moves from the frame you trust; trim the duplicated frame at each join.

1. `"end:<take>.mp4"` as a first frame (`studio/_tools/flf_shots.py` `frame()`, `studio/_tools/previz_chain.py`), fitted to 1280x704.
2. For a chain over many hops, pull each start frame toward the first's colour (`--match 0.6`) and draw in two halves from the master (see [`cam-orbit-360`](../camera/orbit-360.md)).
3. To land on a known frame, draw backwards from it and reverse, or pin the last frame.
4. Trim the first frame of each continuing take.

## Checks before picking

- Measure each join (Lab mean, mean pixel difference).
- Watch the joins at full speed.

## Progression

### 2026-07-29 · EDITING §6, §10 · chaining takes (`from_prev`) · grade B
- **Did:** each link continuing from the previous take's last frame.
- **Got:** about 15 s plus up to 6 s per link; an 83 ms hiccup from `-sseof -0.08`; drift beyond 241 frames.
- **Learned:** chain at most two deep; restate the camera in each link.

### 2026-09-06 · §59 · continuing from the wrong last frame · grade C
- **Did:** shot 050 anchored on shot 040's last frame (`prev_last`).
- **Got:** 040 had been rebuilt, and 050 still opened on the old frame. `ffmpeg -sseof -0.2 ... -frames:v 1` took the FIRST frame of the tail (24.9 per channel off). `-sseof -0.5 -i src -update 1 dest` is byte-identical to a reverse pass (`flf_shots.py`'s `frame()` uses this form, without `-frames:v 1`).
- **Learned:** a rebuilt shot silently invalidates the next shot's start; lay the two frames side by side.

### 2026-09-07 · §71, §75, §84 · joins measured · grade A-
- **Did:** takes pinned to one plate joined on their darkest frame; one number per cut.
- **Got:** safe joins by construction; a hardcoded path later opened a shot on a retired take.
- **Learned:** "Anything that reads another shot asks the film which take is PICKED. Never a filename."

### 2026-09-30 · cyber-alchemist 112, 210 · tilts that continue from the shot before · grade A-
- **Did:** first frame = `end:shot_111_s11.mp4` and `end:shot_209_s11.mp4`.
- **Got:** no jump back at the cut.
- **Learned:** a start frame is where the shot BEGAN; the take ended elsewhere.

### 2026-09-30 · cyber-alchemist 102 → 103 · the static master into the orbit · grade B+
- **Did:** the orbit's first piece started from the master frame, not the 102 take's end.
- **Got:** a small jump at the cut (her breath and pose); 102 was trimmed to 2.5 s.
- **Learned:** a static take still drifts; continue from its end frame.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a jump back in time at the cut | continuing from the start frame | `end:<take>` | caught before rendering |
| a duplicated frame at each join | the take's first frame repeats the join | trim 1/24 s | orbit pieces |
| exposure drifts over hops | each hop continues a darker frame | `--match 0.6` | orbit seeds 11, 303 |

## Evidence

- `studio/_tools/flf_shots.py`, `studio/_tools/previz_chain.py`; the trims in `studio/shotscripts/cyber-alchemist.json`.

## Open questions

- None open.
