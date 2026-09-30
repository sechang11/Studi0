# References: characters, places, props (`pipe-reference`)

| family | status | last tested | best result |
|---|---|---|---|
| pipeline | proven | 2026-09-30 | all five films, grade A- |

**Also called:** references, refs, character reference, place plate, cast, sheet views, made references
**Not the same as:**
- [`pipe-start-frame`](start-frame.md) - composing a shot's first frame FROM the references
- [`pipe-edit-fix`](edit-fix.md) - repairing a reference or a start frame

## Recipe (v1, 2026-09-30)

Characters full length on mid-grey; places empty and wide; props alone on grey; then the views a film needs, made from each character's own sheet. Check every reference at full size before anything is drawn from it.

1. `fight.py --sequence F --cast --cast-engine flux2|qwen21 --only X`: characters 768x1344, places 1280x720 (`workflows/40_flux2_t2i.json` photoreal; `workflows/79_qwen21_t2i.json` anime and puppets).
2. `studio/_tools/sheet_refs.py --sequence F`: `"sheet_view": [who, "turn_back" | "face_front_r" | "turn_right"]` (a full character sheet on /sheets, about 200 s), `"place": true` (a second place drawn wide), `"place_view": [place, "angle_aerial"]` (the plate turned by the angles LoRA).
3. For a camera move round her: her 3D shape from the sheet (Hunyuan3D, `workflows/24_hunyuan3d_mesh.json`, 34 s).
4. Zoom on every signature feature (side, count, design) and fix it with an edit BEFORE drawing anything.

## Checks before picking

- One-sided features on the right side; props able to do their job (a visor you can see a face through).

## Progression

### 2026-09-04 · §30, §43, §55 · character views cut at the knee · grade C
- **Did:** turnaround views of the packs.
- **Got:** views cut at the knee or shin; head size varied 13-33% between views of one character.
- **Learned:** re-roll with a far-framing sentence; extend the canvas downward; drop out-of-proportion views.

### 2026-09-07 · §72, §81 · Qwen is literal; art as a reference · grade B
- **Did:** viewpoints and designs described to Qwen; drawn art as an img2img source.
- **Got:** Qwen drew the camera it was told about; img2img from drawn art made nothing photographic below 0.5 denoise and broke the design above it.
- **Learned:** describe geometry; use art as a reference.

### 2026-09-30 · five films · references and made references · grade A-
- **Did:** the recipe above.
- **Got:** three references were fixed before use: Maya's circuit (wrong arm), the alchemist's eye (a plate instead of an iris), the helmet (a screen instead of a visor).
- **Learned:** every downstream shot inherits the reference; fix it first.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| a feature on the wrong side | the first draw | edit before use | quantum-courier |
| a prop that cannot do its job | the first draw's design | redraw on seeds | cyber-alchemist helmet |

## Evidence

- `studio/_tools/fight.py` (`stage_cast`), `studio/_tools/sheet_refs.py`, `studio/sheets.py`.

## Open questions

- None open.
