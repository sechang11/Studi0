# Legible text on a sign (`text-legible-sign`)

| family | status | last tested | best result |
|---|---|---|---|
| text | proven | 2026-09-30 | system-error 010, 070, 080, grade A |

**Also called:** readable text, neon sign text, hologram text, legible lettering, words on a billboard
**Not the same as:**
- [`text-hud-overlay`](hud-overlay.md) - interface graphics on a visor; its text is decoration
- [`text-title-card`](title-card.md) - text laid over the film, not in it

## Recipe (v1, 2026-09-30)

Draw the exact words into the start frame (Qwen-Image-2.1 renders text); the video engine carries them. Background signs you did not spell out come back as pseudo-script.

1. Start frame: 'its sharp glowing red letters reading "SYSTEM ERROR" filling the frame' - the words in quotes.
2. LTX or H3; a slow camera.
3. A glitch in words when wanted: "the words flicker, break into scanlines and snap back sharp and legible".

## Checks before picking

- The words spelled right in every frame, including after a glitch.

## Progression

### 2026-08-15 · PROMPTING · quoted text · grade A
- **Did:** text on FLUX.2 and Qwen keyframes, quoted and unquoted, at 4-30 steps.
- **Got:** quoted text spelled right at 4 steps on FLUX.2 and held at 20 on Qwen; unquoted text was gibberish at any step count.
- **Learned:** put the words in quotes.

### 2026-09-30 · system-error 010, 070, 080 · "SYSTEM ERROR" on a hologram in the rain · grade A
- **Did:** the recipe above; 010 LTX seed 11, 070 LTX seed 11 (the glitch), 080 H3 seed 11.
- **Got:** sharp through a push-in and a sideways drift; the glitch breaks it and snaps it back.
- **Learned:** text is a start-frame job; the engines keep it.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| gibberish on background signs | words not specified | spell out any sign that must read | all neon backgrounds |

## Evidence

- `studio/samples/fight/system-error/shot_070_s11.mp4`, `h3_080_s11.mp4`.

## Open questions

- Text that moves (a scrolling ticker).
