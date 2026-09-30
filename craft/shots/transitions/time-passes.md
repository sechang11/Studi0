# Time passes (`trans-time-passes`)

| family | status | last tested | best result |
|---|---|---|---|
| transitions | proven | 2026-09-05 | platefade push 1.056 for 1.06 (§51), grade A- |

**Also called:** time passes, time-lapse, day to night, the light changes, passage of time
**Not the same as:**
- [`trans-dissolve`](dissolve.md) - between two different shots

## Recipe (v1, 2026-09-05)

Nothing generated: the place's plates for several times of day (made from one description, so they agree on geometry) dissolved in order with a slow push (`platefade`, the camera rig).

## Checks before picking

- The two plates agree on geometry (boats, chairs), or the dissolve reads as a soft cut.

## Progression

### 2026-08-03 · CINEMATOGRAPHY §5 #8 · "as hours pass" in a motion prompt · grade D
- **Did:** time passing asked of one generation.
- **Got:** it failed.
- **Learned:** time passes between plates, not inside a take.

### 2026-09-05 · §51, §53 · platefade · grade A-
- **Did:** a night-to-late-night dissolve with a 1.06 push.
- **Got:** 1.056 measured, nothing else moved; the boats sit differently in the two plates.
- **Learned:** deterministic, and only as good as the plates' agreement.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| things jump between the plates | the plates disagree | plates made together | §51 |

## Evidence

- `studio/shot_catalog.json` (`time_passes`).

## Open questions

- None open.
