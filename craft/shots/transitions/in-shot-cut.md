# A cut inside one generation (`trans-in-shot-cut`)

| family | status | last tested | best result |
|---|---|---|---|
| transitions | works-with-caveats | 2026-09-24 | the word *cut* made a cut on 3 of 3 takes (§98.5), grade B+ |

**Also called:** internal cut, multishot, cut inside the take, two shots in one render
**Not the same as:**
- [`trans-match-cut`](match-cut.md) - a cut made at assembly between two takes
- [`cont-relay`](../continuity/relay.md) - one moment broken into separate shots, cut at assembly

## Recipe (v1, 2026-09-24)

The word *cut* in the prompt makes the cut on LTX-2.5; timecodes set nothing. It holds a face only when the character is in the start frame; otherwise cut at assembly.

## Checks before picking

- The cut happened; the face after it is the same person.

## Progression

### 2026-08-30 · §24 · a transition inside one generation · grade A-
- **Did:** a medium then a close-up in one take, on a composite start frame and on a plate-only one.
- **Got:** composite: the same face after the transition; plate-only: a different woman.
- **Learned:** in-shot cuts need the character in the start frame.

### 2026-09-24 · §95 S4, §98.5 · asking for cuts · grade B+
- **Did:** timecodes in the prompt; then the word *cut*.
- **Got:** timecodes paced nothing (beats at thirds regardless); with no cut asked, none appeared on 3 of 3; with *cut*, 3 of 3 cut. The cut detector reported 2, 7 and 5 spikes from body motion.
- **Learned:** the word makes the cut; the detector cannot be trusted inside an action beat.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a different face after the cut | a plate-only start frame | the character in the start frame | §24 |
| a cut nobody asked for is reported | the detector reads body motion | look at the take | §98.5 |

## Evidence

- `studio/LTX_PLAYBOOK.md` §24, §95, §98.5.

## Open questions

- None open.
