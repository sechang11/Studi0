# Prompting these specific models

Generic "prompt engineering" advice mostly doesn't transfer between architectures. This
is what matters for the three models you actually have.

---

## Qwen-Image 2512 (text→image)

Its text encoder is **Qwen2.5-VL-7B** — a real vision-language model, not CLIP. Practical
consequences:

**Write sentences, not tag soup.** CLIP-era prompting (`masterpiece, best quality, 8k,
ultra detailed, trending on artstation`) does close to nothing here and wastes context.
Describe the scene the way you'd describe it to a person.

- Bad: `lighthouse, storm, dramatic, cinematic, 8k, masterpiece, hyperdetailed`
- Good: `A lone lighthouse on a black basalt sea stack at dusk, storm clouds shot through
  with copper light, spray freezing mid-air, long exposure, anamorphic lens, deep teal
  and amber palette`

**Spatial language works.** "in the foreground", "behind and to the left", "occupying the
lower third" are all understood. This is the model's real advantage over SDXL-era models.

**Text is the headline feature.** Put the literal string in quotes:

> `a vintage enamel shop sign, the sign reads "NORTHWIND SUPPLY CO." in cream serif
> lettering on deep green`

It renders correctly at 20 steps and usually at 4. Specify the typeface character
(serif/sans, condensed, hand-painted, neon tube) rather than naming a font. For long text
or multiple text elements, use the 20-step path — the 4-step LoRA is where letterforms
first degrade.

**Photographic vocabulary lands.** `85mm`, `shallow depth of field`, `long exposure`,
`large format`, `anamorphic`, `golden hour`, `overcast diffuse light`. Focal length and
lighting are the two highest-leverage words in most prompts.

**Negative prompts do very little at cfg 1.0.** With the Lightning LoRA the negative is
nearly ignored — that's inherent to CFG-distilled models, not a bug. If you truly need
negative steering, drop the LoRA and run 20 steps at cfg 2.5–4.0.

**Structure that works consistently:**

> [subject and what it's doing] + [setting and time of day] + [lighting] + [camera/lens] +
> [colour palette] + [medium/finish]

**Knobs, not words.** When a prompt isn't landing, reach for these before adding adjectives:

| Symptom | Fix |
|---|---|
| Composition ignores the prompt | raise `ModelSamplingAuraFlow.shift` 3.1 → 4.5 |
| Too literal / stiff | lower shift to 2.5 |
| Mushy detail at 4 steps | go to 20 steps, cfg 2.5 |
| Same image every time | seed is fixed — vary `13.inputs.seed` |

---

## Qwen-Image-Edit 2509 (instruction editing)

This model takes **instructions**, not descriptions. The difference is load-bearing.

- Bad: `a lighthouse in winter with snow` ← it will regenerate, losing your image
- Good: `Change the scene to deep winter: the rocks and lighthouse are coated in thick
  snow and ice, the sea is slate grey with drifting ice floes. Keep the lighthouse
  architecture, camera angle and composition exactly the same.`

**Always state what to preserve.** The single most useful trailing clause is some form of
`keeping everything else unchanged` / `preserve the composition, camera angle and
lighting`. Without it the model drifts far more than you want.

**One edit per pass.** Chained single edits beat one compound instruction. Relight, then
change season, then swap the object — three 48 s passes, each controllable.

**What it's genuinely excellent at:**

- Relighting (golden hour → overcast, add a rim light, change light direction)
- Season / weather / time-of-day changes
- Material replacement (`make the table marble instead of wood`)
- Object insertion and removal
- Style transfer while preserving layout
- Text replacement inside the image

**Multi-image.** `TextEncodeQwenImageEditPlus` takes `image1`, `image2`, `image3`. Use it
for "put the product from image 2 into the scene from image 1" and for character
consistency across shots. Refer to them in the prompt as "the first image", "the second
image".

**`FluxKontextImageScale` is not optional.** It snaps the input to a resolution the edit
model was trained on. Bypassing it degrades output noticeably.

---

## Wan 2.2 I2V (image→video)

Your image already fixes subject, style and composition. **The prompt's job is motion**,
and almost nothing else. Restating the scene in detail wastes the conditioning.

**Describe three things, in this order:**

1. **Camera** — `slow push in`, `handheld drift`, `crane up`, `locked off`, `orbit left`,
   `rack focus to the foreground`
2. **Subject motion** — what moves, and how fast
3. **Ambient motion** — cloth, hair, water, smoke, dust, foliage, light

> `Slow cinematic push-in toward the lighthouse. Storm clouds drift and churn overhead,
> the beacon sweeps a beam of warm light through falling rain, waves surge and break
> against the black rocks throwing spray into the air. Handheld camera, subtle drift,
> film grain.`

**The negative prompt matters here, unlike in the image model.** Keep
`static, still image, frozen` in it — I2V's characteristic failure is producing an
almost-still image with a slight Ken Burns drift, and those tokens push against it.
Add `morphing, warping, distorted` to fight identity drift on faces and text.

**Physics beats adjectives.** `waves surge and break, throwing spray` produces better
motion than `dramatic dynamic ocean`. The model has a real motion prior — describe
mechanics and it follows them.

**Length and pacing.** 81 frames at 16 fps is 5.1 s. That is one beat: a single camera
move or a single action. Don't ask for a sequence of events in one clip — you'll get
morphing. Generate separate shots and cut them.

**Don't fight the start frame.** Asking for motion the frame can't support (`the person
turns around` when you only see their back, `the camera flies through the door` when the
door is closed) produces the warping artefacts people blame on the model.

**Knobs:**

| Symptom | Fix |
|---|---|
| Barely moves | shift 8 → 10; strengthen motion verbs; check negative includes `static` |
| Warping / morphing | shift 8 → 5; simplify to one action; shorten to 61 frames |
| Detail crawls or boils | this is 4-step distillation — try 6 steps (split 3/3) |
| Colour shift vs the start frame | wrong VAE — must be `wan_2.1_vae`, not `wan2.2_vae` |

---

## Cross-model: prompt once, use everywhere

The pattern that works for a sequence:

1. Write the **shot description** (subject/setting/light/lens) → feeds the image model.
2. Write the **motion description** (camera/subject/ambient) → feeds the video model.
3. Keep them in separate fields. `scripts/pipeline.py` takes exactly these two as
   `prompt` and `--motion`.

A `shots.txt` line then looks like:

```
wide establishing shot of the harbour at dawn, mist on the water, fishing boats at anchor, cool blue light, 35mm|slow crane up, mist drifting, gulls crossing frame, water rippling
```

and the whole sequence renders unattended.
