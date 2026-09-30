# Wide shot with a person (`frame-wide-with-figure`)

| family | status | last tested | best result |
|---|---|---|---|
| framing | proven | 2026-09-30 | storm-sonata 020, 090; cyber-alchemist 312, grade A- |

**Also called:** wide shot, full shot, long shot, figure in the landscape, wide with the character, wide with people
**Not the same as:**
- [`frame-establishing-empty`](establishing-empty.md) - the place alone
- [`frame-medium`](medium.md) - closer: the figure from the waist or knees up
- [`frame-silhouette-backlit`](silhouette-backlit.md) - a wide where the figure is only a dark shape against the light
- [`move-fight`](../motion/fight.md) - action does not survive at this size

## Recipe (v1, 2026-09-30)

Compose with Qwen-Image-2.1 from [place, character]; LTX; one simple action.

1. Start frame: "a WIDE SHOT of the woman of reference two standing in the middle of the wet street of reference one".
2. LTX.
3. One action (she walks away; he stands beside the piano).

## Checks before picking

- The figure keeps her size and place in the frame; a second person does not appear.

## Progression

### 2026-07-29 · EDITING §5 · runs of wides · grade C
- **Did:** 49 of 109 prompts were wides, in runs of 4, 4 and 5.
- **Got:** about 26-30 s of wides at a time.
- **Learned:** never three wides in a row; break a run with an insert.

### 2026-08-03 · CINEMATOGRAPHY §1.7 · "Wide" asked, medium delivered · grade C
- **Did:** 450_planting asked for a wide.
- **Got:** a medium came back; a character description promotes wides to mediums.
- **Learned:** name the scale in the first three words and give a size ("one tenth of frame height").

### 2026-09-05 · §53, §55 · faces at wide sizes · grade B
- **Did:** the same wide at two distances, three seeds each; the face clock over 119 takes.
- **Got:** a head of 135 px scored 0.66; of 65 px, 0.27-0.32 (unreadable, not degraded). Wides kept the face 66% of the time, full-length shots 17%.
- **Learned:** "a bigger head survives".

### 2026-09-24 · §98.2 · a fight in a wide · grade D
- **Did:** both fighters whole in a wide, 6 s.
- **Got:** a 50% push-in; the combo never happened.
- **Learned:** "a wide swallows a fight"; stage action close.

### 2026-09-30 · storm-sonata 020, 090; cyber-alchemist 312 · the figure small in the place · grade A-
- **Did:** the recipe above.
- **Got:** all held; cyber-alchemist 312 walks away into the haze.
- **Learned:** wides are the safest shots; identity at this size is not tested.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| (none recorded in these films) | | | |

## Evidence

- `studio/samples/fight/storm-sonata/shot_090_s11.mp4`; `studio/samples/fight/cyber-alchemist/shot_312_s11.mp4`.

## Open questions

- None open.
