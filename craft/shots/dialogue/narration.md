# Narration over picture (`dia-narration`)

| family | status | last tested | best result |
|---|---|---|---|
| dialogue | proven | 2026-08-08 | one continuous narration track (VIDEO_RULES SOUND-03), grade A- |

**Also called:** narration, voice-over, VO, narrator, interior monologue
**Not the same as:**
- [`dia-line-on-camera`](line-on-camera.md) - a line from an on-screen mouth

## Recipe (v1, 2026-08-08)

Lay narration as one continuous track over the finished picture, never baked into segments that dissolve; size the picture to the narration, slowing rather than freezing.

## Checks before picking

- The first word of each line is at full level.

## Progression

### 2026-07-29 · EDITING §2 · narration through transitions · grade C
- **Did:** narration inside segments joined by crossfades.
- **Got:** `acrossfade` ducked the first word by -7.4 dB on a dissolve and -10.5 dB on a fade.
- **Learned:** the line's lead must be at least the transition's length.

### 2026-08-08 · VIDEO_RULES SOUND-03, PICTURE-03 · narration as its own track · grade A-
- **Did:** narration laid over the finished picture; the picture sized to the narration.
- **Got:** no quiet first words; `tpad=stop_mode=clone` on long lines had frozen the picture for minutes, so the picture is slowed instead.
- **Learned:** one track, over the finished cut.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a quiet first word | narration inside a dissolving segment | one continuous track | SOUND-03 |
| a frozen picture | `tpad` clone on a long line | slow the picture | PICTURE-03 |

## Evidence

- `craft/EDITING.md` §2; `craft/VIDEO_RULES.md` (SOUND-03, PICTURE-03).

## Open questions

- None open.
