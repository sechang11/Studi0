# Droplets in zero gravity (`fx-zero-g-droplets`)

| family | status | last tested | best result |
|---|---|---|---|
| fx | works-with-caveats | 2026-09-30 | cyber-alchemist 203, grade B+ |

**Also called:** zero-g droplets, floating mercury, liquid rising, weightless drops, rising droplets
**Not the same as:**
- [`fx-glass-shatter`](glass-shatter.md) - the violent moment of breaking; zero-g is the slow aftermath
- [`fx-floating-objects`](floating-objects.md) - solid things (books, flasks) floating; droplets are liquid that splits and wobbles
- [`fx-dust-motes`](dust-motes.md) - dust drifting in light under normal gravity

## Recipe (v1, 2026-09-30)

A start frame that already shows the droplets rising, on LTX, with a slow camera rise.

1. Start frame: droplets and shards already in the air above the floor (Qwen-Image-2.1 with the place).
2. LTX gave the more cinematic take: it craned up with the droplets toward the vault. H3 drew bubbles.
3. Prompt: "The mercury rises upward off the floor in zero gravity, splitting into trembling silver droplets that hang and turn in the air ... Slow motion, the camera drifting slowly upward with them."

## Checks before picking

- The droplets read as the right liquid (mercury: silver and heavy, not clear water).
- They rise; they do not fall back.

## Progression

### 2026-09-30 · cyber-alchemist 203 · rising mercury, LTX and H3 · grade B+
- **Did:** the recipe above, both engines, two seeds.
- **Got:** LTX seed 11 rose with the droplets to the vaulted ceiling (in the cut). H3 drew round bubbles. In both, the droplets read more like water or glass than mercury.
- **Learned:** the camera rise sells zero-g; the liquid's look has to be in the start frame at a size that reads.

### 2026-09-30 · quantum-courier 304-306 · dust rising as gravity reverses · grade A-
- **Did:** dust particles float upward around her as she rises (304 on H3 seed 202).
- **Got:** it reads.
- **Learned:** rising particles around a rising figure sell reversed gravity.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| mercury reads as water | small clear droplets in the start frame | bigger, silver, fewer droplets in the start frame | 203 |
| bubbles instead of droplets | H3's reading of "droplets hang" | LTX for this one | 203 H3 |

## Evidence

- `studio/samples/fight/cyber-alchemist/shot_203_s11.mp4`; `studio/samples/fight/quantum-courier/h3_304_s202.mp4`.

## Open questions

- Mercury that looks like mercury (a reference image of it).
