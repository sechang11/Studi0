# Tracking alongside (`cam-track-alongside`)

| family | status | last tested | best result |
|---|---|---|---|
| camera | works-with-caveats | 2026-09-30 | quantum-courier 202; cyber-alchemist 302, grade B+ |

**Also called:** tracking shot, side tracking, trucking, tracks alongside, travelling shot, follow alongside
**Not the same as:**
- [`cam-fpv-chase`](fpv-chase.md) - behind her, following her path
- [`cam-pan`](pan.md) - turns without travelling
- [`cam-lead-dolly`](lead-dolly.md) - in front of her, backing away
- [`cam-follow-behind`](follow-behind.md) - behind her rather than beside her

## Recipe (v1, 2026-09-30)

A start frame that is already the side-on view at speed (her side view from her sheet); the move in words; H3 for a fall, LTX for a run. "Tracking" alone is not a camera instruction.

## Checks before picking

- The background streams past while she holds her place in the frame.

## Progression

### 2026-09-05 · §52 · "tracking" as a camera word on LTX · grade D
- **Did:** the phrase *tracking* at seed 4242.
- **Got:** an 18% pull back.
- **Learned:** the word does not track.

### 2026-09-30 · storm-sonata 040 · "The camera tracks fast alongside the hands" · grade C
- **Did:** an extreme close-up of the keyboard; LTX and H3.
- **Got:** the take in the cut (H3 seed 11) holds still.
- **Learned:** a track along a close subject needs a start frame and a scene that let the camera move.

### 2026-09-30 · quantum-courier 202; cyber-alchemist 302 · alongside a runner; alongside a falling figure · grade B+
- **Did:** 202: `maya_side` from her sheet, "the camera tracks alongside her in profile, fast" (LTX seed 202). 302: a Flux 2 start frame of the horizontal fall, "The camera falls alongside her" (H3 seed 11).
- **Got:** both track: the corridor's stripes of light pass; the neon streams by.
- **Learned:** the side view from her sheet makes the track hers.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| no track at all | the word alone, or a close static subject | a side-on start frame at speed | §52; storm-sonata 040 |

## Evidence

- `studio/samples/fight/quantum-courier/shot_202_s202.mp4`; `studio/samples/fight/cyber-alchemist/h3_302_s11.mp4`; `studio/LTX_PLAYBOOK.md` §52.

## Open questions

- None open.
