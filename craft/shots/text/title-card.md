# Title card (`text-title-card`)

| family | status | last tested | best result |
|---|---|---|---|
| text | proven | 2026-09-30 | all five challenge films' cards (`film_cards.py`), grade A |

**Also called:** title card, main title, film title, subtitle card, opening card
**Not the same as:**
- [`text-legible-sign`](legible-sign.md) - text inside the picture; a title card is laid over or before it

## Recipe (v1, 2026-09-30)

Made after the finish, never generated: `studio/_tools/film_cards.py --sequence F --picks ...` writes the film with its card. Main titles about 0.075 of the frame height, subtitles about 0.034, one line each; above 0.15 is a bug.

## Checks before picking

- The whole title fits on one line.

## Progression

### 2026-08-08 · VIDEO_RULES PICTURE-01, PICTURE-02 · a title at scale 1.0 · grade D
- **Did:** a title drawn at `scale` 1.0.
- **Got:** only four letters fit the frame.
- **Learned:** titles ~0.075, subtitles ~0.034, single-line (`filmrules.py`).

### 2026-09-30 · five challenge films · cards by film_cards.py · grade A
- **Did:** the title and logline card on every film.
- **Got:** readable cards; the annotated cut labels each shot too.
- **Learned:** as above.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the title does not fit | scale 1.0 | ~0.075 | VIDEO_RULES PICTURE-01 |

## Evidence

- `craft/VIDEO_RULES.md` (PICTURE-01, 02); `studio/_tools/film_cards.py`.

## Open questions

- None open.
