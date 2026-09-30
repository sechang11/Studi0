# A feature on one side only (`cont-asymmetric-mark`)

| family | status | last tested | best result |
|---|---|---|---|
| continuity | works-with-caveats | 2026-09-30 | quantum-courier (38 shots), grade A-; cyber-alchemist, grade B+ |

**Also called:** left eye iris, one glowing eye, nostril ring side, left sleeve circuit, asymmetric hair, which side, mirrored feature
**Not the same as:**
- [`cont-face-identity`](face-identity.md) - whether it is the same face; here whether a mark is on the right SIDE and appears once
- [`pipe-edit-fix`](../pipeline/edit-fix.md) - the repair tool; this entry says when to use it and what to check
- [`cont-wardrobe`](wardrobe.md) - the whole costume, not one detail

## Recipe (v2, 2026-09-30)

Fix the feature in the reference before anything is drawn, write its side in every prompt as the picture's side, and check every close-up for a flipped or doubled copy.

1. Draw the reference; zoom on the feature: side (her LEFT = the picture's RIGHT when she faces the camera) and count.
2. If wrong, fix the reference with the edit model (`studio/sheets.py` `edit()`, no angles LoRA), naming both sides in picture terms: "on the right side of the picture (her left arm) ...". Three seeds; pick by eye.
3. Every start frame's words: the feature, its side, and "only".
4. Every close-up start frame: check both eyes/arms. The Qwen compositor spread a one-eye feature to both eyes; fix with an edit ("Her right eye (on the left side of the picture) has a natural dark brown iris ... left eye keeps its glowing silver iris"), saved as a candidate `anchor_<id>_eyefix_s<seed>.png` and chosen with `fight.py --anchor-picks`.
5. Keep ONE design of the feature: the macro of the eye must show the same iris as the close-ups.

## Checks before picking

- Side and count in every take's first, middle and last frames, including during fast moves (a whip-tilt flashed it on the wrong eye).
- In a reflection the side flips: that is correct there.

## Progression

### 2026-09-07 · §70.1 · naming an asymmetric hip drape (SDXL costume LoRA) · grade D
- **Did:** the drape among six corrections written into the prompt.
- **Got:** the costume got worse (lost the strapping, gained a skirt).
- **Learned:** in the SDXL route, what is in the weights must not be asked for.

### 2026-09-30 · quantum-courier · the amber circuit on her LEFT sleeve · grade A-
- **Did:** her first Flux 2 reference put the circuit on the right forearm; the nose ring (left nostril, correct) ruled out mirroring the picture. Edited with Qwen-Image-Edit-2511, three seeds; seed 21 moved it. The old sheet and every start frame were redrawn from the fixed reference.
- **Got:** the circuit on the left sleeve in all 38 shots.
- **Learned:** fix it in the reference; everything downstream inherits it.

### 2026-09-30 · cyber-alchemist · a silver iris in her LEFT eye · grade B+
- **Did:** the first Flux 2 reference drew a metal eyepiece plate. Edit round 1 ("a glowing silver cybernetic iris made of fine concentric mechanical rings") drew lens discs over the eye; round 2 ("a normal open human eye ... only the iris ... shining metallic silver") seed 32 gave her own eye with a silver iris.
- **Got:** the Qwen compositor then gave her TWO silver eyes in the close-ups (114, 206, 311); an edit per close-up put the right eye back to brown (and scored higher on identity: 114 0.525 → 0.566). The Flux 2 macro of the eye (111) drew mechanical rings: a second design of the same iris. In some whip-tilt takes the silver iris flashed on the wrong side for about 0.2 s.
- **Learned:** words like "cybernetic", "mechanical rings" make the edit model add hardware; ask for the plain thing. Check every close-up for doubling. One design per feature, including in macros.

### 2026-09-30 · system-error · the detective's glowing cyan eyes · grade C
- **Did:** "her glowing cyan eyes behind" her glasses in the start frames.
- **Got:** the eyes read as ordinary in the medium shot; only a red glint in the glasses in 090.
- **Learned:** a signature feature must be big enough in the frame to show, or given its own close-up.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the feature on the wrong side | the reference drew it there | fix the reference with an edit before drawing | quantum-courier circuit |
| hardware drawn over the eye | "cybernetic / mechanical" words in the edit | ask for the plain feature | cyber-alchemist eye edit round 1 |
| both eyes silver | the compositor spreads a one-eye feature | per-close-up edit, picked as a candidate | cyber-alchemist 114, 206, 311 |
| two designs of one feature | Flux 2 macro redrew it | one design in the words; check macros | cyber-alchemist 111 |
| a flash on the wrong side mid-move | a fast move re-draws the face | pick the take without it | cyber-alchemist 112 takes |
| the feature does not read | too small in frame | its own close-up | system-error 030 |

## Evidence

- `studio/samples/fight/quantum-courier/ref_maya.png` (after the fix); `maya_fix_board.jpg`.
- `studio/samples/fight/cyber-alchemist/_alch_eye2_s32.png`, `anchor_114_eyefix_s41.png`, `anchor_206_eyefix_s42.png`, `anchor_311_eyefix_s42.png`.
- `studio/sheets.py` (`edit`), `studio/_tools/fight.py` (`--anchor-picks`).

## Open questions

- An automatic check (detect eyes, compare the two irises) before a take is picked.
