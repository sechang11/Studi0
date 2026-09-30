# A fight beat (`move-fight`)

| family | status | last tested | best result |
|---|---|---|---|
| motion | works-with-caveats | 2026-09-24 | ash-court: punches read on 3 of 3 seeds once restaged close (§98.2), grade B+ |

**Also called:** fight, punch, strike, combo, brawl, action beat, martial arts
**Not the same as:**
- [`fx-impact-burst`](../fx/impact-burst.md) - the dust or ash at the moment of a strike
- [`frame-wide-with-figure`](../framing/wide-with-figure.md) - the framing that swallows a fight

## Recipe (v1, 2026-09-24)

Stage each fight beat close and low (a medium from a low angle, both bodies large), one beat per shot, 4 s, one mover per beat; the strike's effects on H3.

1. Start frame: both fighters composed from their references and the place (Flux 2 ref3, `workflows/75_flux2_ref3.json`, or Qwen-Image-2.1).
2. One mover per beat: never a fast limb against a still torso.
3. Strike beats with a burst of debris: H3 (see [`fx-impact-burst`](../fx/impact-burst.md)).

## Checks before picking

- The blows land (count them); both faces against their shot's own start frame.

## Progression

### 2026-07-29 · EDITING §5, §12 · the length of a blow · grade B
- **Did:** fight beats in the cut.
- **Got:** silent action beats all came out 4.04 s; blows should be 2.0-2.5 s; a 174-shot fast cut felt "random" and was rejected.
- **Learned:** trim blows short; cut on action, not on a clock.

### 2026-09-24 · §98.2 · a combo in a wide, then restaged · grade B+
- **Did:** both fighters whole in a wide of the court, 6 s; then a medium from a low angle, both bodies large, 4 s, one beat - same engine, words and cast.
- **Got:** the wide measured a 50% push-in and ended with the two standing still: "the combo never happened". Restaged, the punches read on all three seeds.
- **Learned:** "a wide swallows a fight"; staging close "is not style, it is what makes the action survive".

### 2026-09-24 · §98.5b · identity across the fight sequence · grade A-
- **Did:** faces scored against each shot's own start frame.
- **Got:** 0.894-0.925 for a 3.8 s H3 take; 0.75 across the cut; against the neutral cast reference only 0.22-0.33.
- **Learned:** score against the shot's own start frame; the neutral reference is a conditioner, not a yardstick.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the blows never happen | a wide framing | a close low medium, one beat | §98.2 |
| a fast limb ghosts | H3 on a fast limb | one mover per beat | §98 intro |

## Evidence

- `studio/LTX_PLAYBOOK.md` §98; `craft/ACTION_SEQUENCE.md`; `studio/_tools/fight.py`.

## Open questions

- Paid engines for strike beats (§98.7) - not used; the user does not pay for them.
