# Current public practice, surveyed 2026-08-05

What the best public work is actually doing right now, what of it transfers to the
engines on this box, and where it contradicts what we measured ourselves.

Scope: Civitai, OpenArt, PromptHero listings, the official model cards and prompt
handbooks from Black Forest Labs, Alibaba/Tongyi, Tencent and Krea, plus three
independent hands-on comparisons. Every claim below carries the URL it came from.
Claims I could not verify are marked **unverified**.

**Content boundary:** several Civitai and blog listings that surfaced in these searches
were NSFW-oriented LoRAs and checkpoints (anatomy LoRAs, "best NSFW Flux LoRA"
round-ups, and the NSFW example prompts in one otherwise-good Japanese tag-order
guide). All skipped, none fetched, none proposed. Nothing on the download shortlist is
NSFW-adjacent and nothing clones a real person.

---

## 1. The one-paragraph version

The centre of gravity moved off SDXL and off FLUX.1 entirely. Public output volume in
mid-2026 is dominated by **Krea 2** (12B DiT, 8-step distilled, open weights since June
2026) with **Qwen-Image 2512** and **Z-Image Turbo** behind it, and **FLUX.2** used
where prompt adherence, in-image typography and structured control matter more than
speed. Three of those four are already on this box. The prompt conventions have
converged hard: **prose, subject-first, no negative prompt, low or no CFG**. The
tag-and-negative-prompt style survives in exactly one place, anime SDXL, and there it is
still correct. This is the single most important thing to carry into the app: the two
prompt dialects are not a stylistic preference, they are a property of the text encoder,
and the app currently has no concept of the split.

---

## 2. Where the installed models sit against public practice

| On disk | Public standing right now | Are we using it? |
|---|---|---|
| Qwen-Image 2512 fp8 (20 GB) | "What I overwhelmingly use locally" — Civitai 2026 scene guide. Best-in-class legible text. Weakness: low seed variability. | Yes, the `qwen` engine |
| animagine-xl-4.0 (6.9 GB) | Respectable but the anime scene has largely moved to Illustrious-derived bases | Yes, the `anime` engine |
| **Z-Image Turbo bf16 (12.3 GB)** | Rated **better skin detail than FLUX.1, Qwen-Image, HiDream or FLUX.2 dev** by an independent hands-on comparison. 8 steps, ~2.3 s/image on a 4090. | **No. Installed 2026-07-31, never wired in.** |
| **Illustrious-XL-v2.0 (6.9 GB)** | The base that essentially the whole current anime LoRA ecosystem attaches to | **No. Installed 2026-08-03, never rendered.** |
| **FLUX.2 dev fp8 (34 GB) + Turbo LoRA** | Top-tier prompt adherence; the only engine here that takes JSON prompts and hex colours | **No.** One workflow, one image on disk |
| **HunyuanVideo 1.5 720p t2v/i2v + 1080p SR** | Tencent ships a 30-page prompt handbook with ~48 worked example prompts | **No** |
| Wan 2.1 VACE 14B, FLUX.1 Fill OneReward, Qwen ControlNet Union, RealESRGAN | Standard parts of current pipelines | **No** |

Sources: [Civitai — Guide to the General AI scene in 2026](https://civitai.com/articles/30487/guide-to-the-general-ai-scene-in-2026),
[Diffusion Doodles — Model Rundown: Z-Image Turbo, Qwen Image-2512, Flux.2 Dev](https://medium.com/diffusion-doodles/model-rundown-z-image-turbo-qwen-image-2512-edit-2511-flux-2-dev-fc787f5e87ad),
[Thunder Compute — Best Open-Source Image Generation Models (2026)](https://www.thundercompute.com/blog/best-open-source-image-generation-models).

**The headline for this survey: the two best-reviewed models we could be shipping today
need zero downloads.** Z-Image Turbo is the current public favourite for photographic
skin, and it is sitting on the disk unused. Illustrious-XL-v2.0 is the anime base the
LoRA ecosystem is built on, also unused.

---

## 3. Prompt conventions, per engine

### 3.1 FLUX.2 dev — prose, subject-first, no negatives, guidance 4

Black Forest Labs' own guide gives the formula **Subject + Action + Style + Context**,
and says explicitly that word order is load-bearing: "FLUX.2 pays more attention to what
comes first." Priority order is main subject → key action → critical style → essential
context.
([docs.bfl.ai](https://docs.bfl.ai/guides/prompting_guide_flux2))

Four things FLUX.2 does that nothing else here does:

1. **No negative prompt at all.** BFL: "FLUX.2 does not support negative prompts. Focus
   on describing what you want, not what you don't want."
2. **Quoted text renders as typography.** Put the literal string in quotes.
3. **`#RRGGBB` hex colours are honoured** in the prompt.
4. **Structured JSON prompts.** BFL publish a schema:

```json
{
  "scene": "overall scene description",
  "subjects": [{"description": "...", "position": "where in frame", "action": "..."}],
  "style": "artistic style",
  "color_palette": ["#hex1", "#hex2", "#hex3"],
  "lighting": "...", "mood": "...", "background": "...", "composition": "...",
  "camera": {"angle": "...", "lens": "...", "depth_of_field": "..."}
}
```

This is a real capability gap in our authoring layer. We have spent a lot of effort
trying to make adjective-shaped variables (look / wear / mood) land on a model that
renders nouns. FLUX.2's JSON schema has `mood`, `lighting`, `composition` and `camera`
as *first-class typed fields*, which is exactly the shape `compose.py` already resolves
into. The layer stack maps onto this format almost one-to-one.

**FLUX.1 prompt habits do not transfer.** FLUX.2 dropped the CLIP+T5 dual encoder for a
Mistral-3 VLM. Our box has `mistral_3_small_flux2_fp8.safetensors` (18 GB), which is why
the CLIPLoader in `workflows/26_flux2_t2i.json` is `type: flux2`.

Settings that are already proven on this box (read out of
`~/shared/comfy-studio/workflows/26_flux2_t2i.json`, which has rendered):

```
UNETLoader        flux2_dev_fp8mixed.safetensors
CLIPLoader        mistral_3_small_flux2_fp8.safetensors, type=flux2
LoraLoaderModelOnly Flux2TurboComfyv2.safetensors @ 1.0
FluxGuidance      4.0
Flux2Scheduler    steps 8, 1024x1024
KSamplerSelect    euler
```

Public guidance corroborates guidance 4.0: "For relatively short prompts and
requirements, setting the guidance to 4 may be a good choice… if your prompt is longer
or you want more creative content, setting the guidance between 1.0 and 1.5 might be
better."
([ComfyUI Wiki, FluxGuidance](https://comfyui-wiki.com/en/comfyui-nodes/advanced/conditioning/flux/flux-guidance))

Cost warning from an independent test: FLUX.2 dev without the distill LoRA took **over
20 minutes for a base generation at 20 steps** on the reviewer's hardware, and its
photorealism, particularly skin, was judged "oddly weak."
([Diffusion Doodles](https://medium.com/diffusion-doodles/model-rundown-z-image-turbo-qwen-image-2512-edit-2511-flux-2-dev-fc787f5e87ad))
Use it for adherence, typography and structured control, not for faces. Always keep the
Turbo LoRA on.

### 3.2 Qwen-Image 2512 — structured prose, 1–3 sentences, quote your text

The best-regarded community guidance is *structure over narrative*: labelled lines
rather than flowing prose.

```
Subject: young woman, professional model
Pose: walking forward, confident stride
Clothing: flowing white dress
Camera: medium shot, eye level
Environment: dense forest, autumn colors
Lighting: golden hour, backlit
Mood: serene, ethereal
```

Claimed effects, from the same two guides: labelled structure ≈ +30% precision over
narrative; 1–3 sentences is the sweet spot and cuts tokens ~60%; **wrapping literal text
in double quotes lifts text-render accuracy from ~65% to 85–96%**. The quoted-text rule
is consistent across every Qwen source I read and is worth adopting outright.
([Civitai — Qwen-Image-2512 Prompt Guide & Best Practices](https://civitai.com/articles/30826/qwen-image-2512-prompt-guide-and-best-practices),
[apiyi — Qwen-Image-2512 Prompt Practical Guide, 23 test cases](https://help.apiyi.com/en/qwen-image-2512-prompt-guide-test-cases-en.html))

Public CFG/steps table (full-step regime, **not** the Lightning regime):

| Use case | CFG | Steps |
|---|---|---|
| Creative | 3.0–4.0 | 40–50 |
| General photography | 4.0–5.0 | 50 |
| Precise reproduction | 5.0–7.0 | 50 |
| Product / text-heavy | 7.0–10.0 | 50+ |

Default recommendation: **CFG 4.5 + 50 steps**. And an explicit warning that matches our
own finding: "The Lightning LoRA setting (CFG 1.0, 4 steps) is a different inference
regime, and mixing it with standard settings degrades quality significantly."

### 3.3 SDXL anime (animagine 4.0, Illustrious-XL 2.0) — tags, order matters, negatives are real

This is the one dialect where the old rules still hold, and both model cards are
explicit about ordering.

**animagine-xl-4.0**, official template:
`1girl/1boy/1other, character name, from which series, rating, everything else in any order and end with quality enhancement`
Quality tail: `masterpiece, high score, great score, absurdres`.
Negative: `lowres, bad anatomy, bad hands, text, error, missing finger, extra digits, fewer digits, cropped, worst quality, low quality, low score, bad score, average score, signature, watermark, username, blurry`
CFG 4–7 (5 recommended), steps 25–28 (28), Euler a, 1024×1024 / 1216×832 / 832×1216.
([HF model card](https://huggingface.co/cagliostrolab/animagine-xl-4.0))

**Illustrious-XL-v2.0**: quality tags go **in front**: `masterpiece, best quality, highres, absurdres, newest`, artist tags after quality tags or at the end. CFG 4.5–7.5 (5.5), steps 24, Euler a, **trained at 1536×1536** — a materially higher native resolution than animagine's 1024.
Short negative: `lowres, worst quality, bad quality, bad, sketch, jpeg artifacts, signature, watermark, artist name, old, oldest`
([SeaArt — The Ultimate Guide, Illustrious XL 2.0](https://www.seaart.ai/articleDetail/cvdosb5e878c73c7ipig))

That 1536 training resolution is directly relevant to our measured face-pixel problem. At
832×1216 full-body on animagine, a face is ~90 px and looks bad at any weighting. On
Illustrious the native box is 1536×1536, so the same framing buys roughly 1.5–1.8× more
face pixels before any reframing. **Unverified** on this box — nobody has rendered
Illustrious here yet — but it is the cheapest available shot at the face problem and it
needs no download.

Ordering, per a tag-order guide that compared the two side by side
([note.com/kazumu](https://note.com/kazumu/n/n6390a899bdce?hl=en)):

- Illustrious: `[subject], [character], [rating], [appearance/hair], [costume/composition], [quality/score], [era tag]`
- Animagine: `[subject], [character], [series], [rating], [appearance/hair/face], [costume/composition/background], [quality/score/era]` — stricter about order, and it *requires* the rating tag.

### 3.4 Z-Image Turbo — installed, unused, and the current photoreal favourite

Prompt scaffold from the community guide:
`[Shot & subject] + [Age & appearance] + [Clothing] + [Environment] + [Lighting] + [Mood] + [Style/medium] + [Technical notes] + [constraints]`

- **Steps 8–12**, native **1024×1024**, sampler **euler**.
- **guidance_scale = 0.0** for best quality; the official pipeline uses 0. Other write-ups say start 1.5–2.0 and that CFG 4+ renders worse.
- **Negative prompt is ignored entirely.** The official pipeline drops it. Constraints go in the positive prompt as literal phrases: "no text, no watermark, no logos".
- Prompt length sweet spot 80–250 words.

([Z-Image-Turbo Prompting Guide gist](https://gist.github.com/illuminatianon/c42f8e57f1e3ebf037dd58043da9de32),
[Tongyi-MAI/Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo))

Note the shape: Z-Image and Qwen-Image are both Alibaba, both prose, both negative-inert,
and Z-Image is 12.3 GB against Qwen's 20.4 GB and runs in 8 steps instead of 50. If it
really has better skin than Qwen it is a straight upgrade for the photographic engine.
That is a one-afternoon A/B, not a download.

### 3.5 HunyuanVideo 1.5 — the formula, from Tencent's own handbook

T2V: `Subject + Motion + Scene + [Shot Type] + [Camera Movement] + [Lighting] + [Style] + [Atmosphere]`
I2V: `Subject Motion Dynamics + Scene Motion Dynamics + [Camera Movement]`
Action logic: `Scene Setting + Sequential Action Decomposition + Key Details`

The handbook's own advice is the opposite of image prompting: **write longer**. It also
prescribes temporal conjunctions — "First… then… next… meanwhile… finally…" — spatial
vocabulary (left/right of frame, foreground/background), and explicit per-character
attribution when there are two subjects ("The black cat hands the bomb to the gray cat;
the gray cat takes the bomb and turns to run toward the right side of the frame").
Quoted strings render as on-screen text, in English or Chinese.
([HunyuanVideo_1_5_Prompt_Handbook_EN.md](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5/blob/main/assets/HunyuanVideo_1_5_Prompt_Handbook_EN.md))

This maps almost exactly onto our `craft/CINEMATOGRAPHY.md` and the MOTIONS card library,
and the handbook ships ~48 worked example prompts. If we turn HunyuanVideo on, that
handbook is the spec for the motion layer's prompt emitter.

### 3.6 Krea 2 — not installed; see the shortlist

8 steps, native 1K–2K, prompt-enhancement on by default, and a **style-reference LoRA**
that takes an image and transfers aesthetic direction.
([docs.comfy.org Krea-2 tutorial](https://docs.comfy.org/tutorials/image/krea/krea-2))

---

## 4. Where public practice contradicts what we measured

### 4.1 Negative prompts on Qwen — public advice is split, and the popular half is wrong

This is the big one and it is worth being blunt about.

- **The most-linked Civitai guide for Qwen-Image-2512** lists as one of its five core
  rules: "Include negative prompts for consistent ~15% satisfaction improvement", with a
  recommended template `blurry, low quality, pixelated, distorted, watermark, text
  overlay, oversaturated, plastic-looking, artificial`, and claims adding hand
  exclusions lifts portrait quality "from 60% to 85%".
  ([civitai.com/articles/30826](https://civitai.com/articles/30826/qwen-image-2512-prompt-guide-and-best-practices))
  The apiyi guide says the same thing with the same template.
  ([help.apiyi.com](https://help.apiyi.com/en/qwen-image-2512-prompt-guide-test-cases-en.html))

- **An independent test says that is false.** PromptMaster swept CFG 1.0 → 7.0 and found
  "zero effect across all CFG values" — negatives ignored even at CFG 7.0. Their
  explanation: Qwen-Image conditions on a Qwen2.5-VL vision-language encoder rather than
  CLIP, and "was never trained to push away from negative prompt content"; the parameter
  survives only because the diffusers pipeline requires it and "omitting it entirely
  breaks the generation."
  ([blog.promptmaster.pro](https://blog.promptmaster.pro/posts/qwen-image-negative-prompts/))

- **We measured the same thing, but narrower.** Our finding is "qwen at cfg 1.0 with the
  Lightning LoRA ignores the negative prompt entirely." We only tested the Lightning
  regime, so we could not distinguish "CFG 1.0 disables CFG, therefore no negative
  branch" — the trivial explanation — from "the encoder never learned negation."

  PromptMaster's sweep says it is the second. **If that holds, our rule is stronger than
  we thought and applies at every CFG, not just 1.0** — which means the full-step
  quality path (CFG 4.5, 50 steps) also gets nothing from a negative prompt, and any
  negative field we expose on the qwen engine is decoration.

  This is a 20-minute experiment we have not run: same seed, same prompt, CFG 4.5, 50
  steps, no Lightning LoRA, with and without a heavy negative. It is worth running,
  because the two published guides with the most traffic tell users to do the opposite
  and a lot of our users will have read them.

Same pattern, independently, on the other three engines: BFL says FLUX.2 "does not
support negative prompts"; the Z-Image pipeline discards `negative_prompt` outright.
**The convergent rule for 2026: on every prose-conditioned model, negation belongs in the
positive prompt as a stated fact ("fully clothed", "plain white background", "no text").
Negative prompts are an SDXL-era artefact that only still works on SDXL.**

### 4.2 "Structure over narrative" vs. our nouns-not-adjectives rule

Public Qwen practice pushes labelled key–value prompts (`Lighting: golden hour,
backlit`). We measured that adjective-shaped qualities (look / wear / mood) fail as
prompt content and had to be moved to deterministic stages.

These are not the same claim and they are not in conflict, but the difference is
instructive. The public template's fields that reliably work are the ones whose values
are nouns or noun phrases — *Subject*, *Clothing*, *Environment*, *Camera*. The field
whose value is an adjective — *Mood: serene, ethereal* — is exactly the one we measured
as inert. **The label does not rescue an adjective.** So: adopt the labelled-block prompt
format for qwen, but keep every value a noun phrase, and keep mood on the deterministic
side. FLUX.2's JSON schema has the same trap in the same place (`"mood"`).

### 4.3 Two-engine model vs. the four-dialect reality

Our standing model is "two engines today: tags for anime, prose for photographic." The
survey says the real split is by **text encoder**, and there are four dialects live on
this box right now:

| Encoder | Models here | Dialect |
|---|---|---|
| CLIP (SDXL) | animagine 4.0, Illustrious-XL 2.0 | danbooru tags, ordered, negatives real, CFG 5–5.5 |
| Qwen2.5-VL | Qwen-Image 2512, Qwen-Edit 2509/2511 | labelled prose, negatives inert, CFG 4.5 or 1.0-with-Lightning |
| Qwen3-4B | Z-Image Turbo | prose + inline constraints, negatives discarded, guidance 0 |
| Mistral-3 VLM | FLUX.2 dev | prose or JSON, hex colours, quoted typography, no negatives, guidance 4 |

`compose.py` needs the dialect as an explicit property of the engine, not an implicit
consequence of which of two engines was picked.

### 4.4 A methodology note: Civitai image metadata is no longer harvestable

I tried to pull top-rated prompts straight from `civitai.com/api/v1/images` sorted by
Most Reactions. **Every entry now returns `"meta": null` without authentication** —
prompt, cfgScale, steps and sampler are all withheld. Verified against a live call on
2026-08-05. Any older tooling or doc of ours that assumes that endpoint yields prompts is
stale. The prompts in `reference_prompts.json` therefore come from official model cards,
published prompt handbooks and named guide articles, which is a better provenance
anyway.

---

## 5. Download shortlist — proposals only, nothing fetched

Bar applied: *does this do something the installed models measurably cannot?* Four
candidates pass, two of them conditionally. Everything on the "already have it" list in
§2 should be tested first, because it costs zero GB.

### Tier 0 — no download required, do these first

1. **Wire up Z-Image Turbo.** `z_image_turbo_bf16.safetensors`, 12.3 GB, already on disk
   since 2026-07-31. Needs `qwen_3_4b.safetensors` (8.0 GB, already on disk). Public
   claim to test: better skin detail than Qwen-Image at 8 steps instead of 50.
2. **Render Illustrious-XL-v2.0.** 6.9 GB, on disk since 2026-08-03, never used. Native
   1536×1536 vs animagine's 1024 is a direct shot at the face-pixel problem.

### Tier 1 — worth downloading

**1. Krea 2 Turbo** — the current volume leader, and it brings a capability we have none of.

| | |
|---|---|
| Model | `krea2_turbo_fp8_scaled.safetensors` |
| URL | https://huggingface.co/Comfy-Org/Krea-2/resolve/main/diffusion_models/krea2_turbo_fp8_scaled.safetensors |
| Size | 13.1 GB (**unverified** — from a search snippet, not read off the repo) |
| Base | standalone 12B dense DiT; **not** a FLUX or Qwen derivative, so no existing LoRA fits it |
| Licence | `krea-2-community-license` (stated on the HF repo). Commercial terms **unverified** — Krea's own page says "community and enterprise licensing paths" without naming the split. **Read the licence before rendering anything intended for distribution.** |
| Also needs | `text_encoders/qwen3vl_4b_fp8_scaled.safetensors` — **5.24 GB**, verified from the repo listing. Qwen3-**VL**-4B is not the same file as our `qwen_3_4b.safetensors`. |
| VAE | `qwen_image_vae.safetensors` — already on disk (253 MB) |
| Total incremental | **~18.4 GB** |

Why it clears the bar: 8-step generation at **native 2K** (set megapixels to 2.0), and
`loras/krea2_style_reference.safetensors` does **image-driven style transfer for a
text-to-image base**. We have IP-Adapter for SDXL only (`22_anime_kf_ipadapter.json`);
there is no equivalent for Qwen or FLUX.2. Given how much of this project is a *styles
library*, an engine where a style can be supplied as a reference image rather than as
words is a structural fit.
([docs.comfy.org](https://docs.comfy.org/tutorials/image/krea/krea-2),
[Comfy-Org/Krea-2](https://huggingface.co/Comfy-Org/Krea-2),
[VentureBeat launch coverage](https://venturebeat.com/technology/enterprise-grade-ai-image-generation-in-2-seconds-is-here-krea-2-raw-and-turbo-available-as-open-weights-under-custom-license))

**2. Krea 2 style LoRAs (optional add-on, same repo, same licence).** Nine named styles
with trigger words: `darkbrush, dotmatrix, kidsdrawing, neondrip, rainywindow,
retroanime, softwatercolor, sunsetblur, vintagetarot`. Sizes **unverified**. Relevant
because our own measurement was that *a style named after an object gets the object
drawn* — these are trained styles with triggers, which is the deterministic form of the
thing we could not get from prompt words.

### Tier 2 — defensible, but argue it first

**3. FLUX.2 klein 9B.** ~13 GB, **Apache 2.0**, released Jan 2026. It is not more capable
than the flux2 dev we have; it is faster and, unlike dev's non-commercial FLUX licence,
it is permissively licensed. Buy it only if licence terms start mattering, or if dev's
34 GB residency is squeezing the video models out of VRAM. Size and date from
[Thunder Compute](https://www.thundercompute.com/blog/best-open-source-image-generation-models) — **unverified** against the HF repo.

**4. `[Qwen-Image-2512] Smartphone Snapshot Photo Reality [STYLE]`** — a Qwen-2512 LoRA
that pushes output toward casual phone photography. https://civitai.com/models/2384460
Attaches to Qwen-Image 2512 (fits our installed checkpoint). Size and licence
**unverified — not fetched, Civitai per-model licence flags must be read on the page
before download.** It clears the bar only on one specific claim: base Qwen-2512 has a
recognisable glossy look, and we measured that *Qwen cannot be steered off photography by
prompt at any cfg, but a LoRA can*. This is the same lever applied one level in — steering
it off *studio* photography. Test the base model at CFG 3.0 first; if that gets there, skip it.

### Explicitly rejected

- **Any anime SDXL finetune.** We already have two SDXL anime bases, one of them never
  rendered. Downloading a third before testing the second is not scepticism, it is
  shopping. Also: the highest-rated Illustrious derivatives are trained on full booru
  dumps and fail the content boundary, so this lane needs care regardless.
- **Everything NSFW-oriented.** Several of the most-downloaded checkpoints and LoRAs in
  the current Civitai top-10 are explicitly NSFW. Skipped, per the boundary.
- **Cloud API nodes** (Nano Banana Pro, GPT Image 2, Seedream 5, Ideogram 4). Note that
  many of the best public *prompts* are written for these — see §6.
- **NVIDIA Cosmos3-Super-Text2Image**, currently top of the open-weight Text-to-Image
  Arena at 1,219 Elo per [Artificial Analysis](https://artificialanalysis.ai/articles/recent-open-weights-model-launches).
  Flagged for the record, **not proposed**: I could not verify size, VRAM footprint,
  licence or whether ComfyUI supports it. All **unverified**. Worth one search next wave.

---

## 6. About the prompts in `studio/reference_prompts.json`

77 prompts, tagged `flux2` / `qwen` / `sdxl`, each with a `source_url`, the model it was
**authored** for, a `verbatim` flag, and a `demonstrates` string.

Three things to know before rendering them:

1. **Roughly half the prose prompts were authored for closed models** — OpenArt's
   50-prompt set targets Nano Banana Pro, GPT Image 2, Seedream 5.0 Lite and Flux 2 Max.
   I kept them because they are the best-written public prose prompts I found and the
   dialect transfers cleanly to FLUX.2 dev and Qwen; each carries `source_model` so the
   provenance is visible. Expect the *composition* to transfer and the *rendering* not to
   match the marketing images.
2. **The sdxl set is thinner on verbatim material** (12 of 19 counting the prose halves
   of the matched pairs; only 9 are verbatim *tag* prompts), because Civitai now hides
   image metadata (§4.4). The other 10 are marked `"verbatim": false` and carry
   `convention_source` — the model card or guide whose documented tag order they follow.
   They are not invented aesthetics, they are the documented convention instantiated.
3. **There are three matched pairs** (`pair_id`: `neon-anime-portrait`,
   `shonen-hero-fullbody`, `ghibli-countryside`): the same subject written as prose for a
   prose engine and as ordered tags for SDXL. Render both. They are the cheapest possible
   demonstration of why the app has to know which dialect it is speaking, and if the prose
   version wins on SDXL our whole engine-routing story needs revisiting.

---

## 7. Sources

Official model cards and handbooks
- https://docs.bfl.ai/guides/prompting_guide_flux2
- https://huggingface.co/cagliostrolab/animagine-xl-4.0
- https://huggingface.co/Tongyi-MAI/Z-Image-Turbo
- https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5/blob/main/assets/HunyuanVideo_1_5_Prompt_Handbook_EN.md
- https://huggingface.co/Comfy-Org/Krea-2
- https://docs.comfy.org/tutorials/image/krea/krea-2
- https://docs.comfy.org/tutorials/flux/flux-2-dev

Guides and community practice
- https://civitai.com/articles/30487/guide-to-the-general-ai-scene-in-2026
- https://civitai.com/articles/30826/qwen-image-2512-prompt-guide-and-best-practices
- https://civitai.com/articles/21885/the-civitai-prompting-compass
- https://help.apiyi.com/en/qwen-image-2512-prompt-guide-test-cases-en.html
- https://blog.promptmaster.pro/posts/qwen-image-negative-prompts/
- https://gist.github.com/illuminatianon/c42f8e57f1e3ebf037dd58043da9de32
- https://www.seaart.ai/articleDetail/cvdosb5e878c73c7ipig
- https://www.seaart.ai/articleDetail/csmspt99c71s73dqk2mg
- https://note.com/kazumu/n/n6390a899bdce?hl=en
- https://openart.ai/blog/best-ai-image-generator-prompts/
- https://comfyui-wiki.com/en/comfyui-nodes/advanced/conditioning/flux/flux-guidance

Comparisons and market state
- https://medium.com/diffusion-doodles/model-rundown-z-image-turbo-qwen-image-2512-edit-2511-flux-2-dev-fc787f5e87ad
- https://www.thundercompute.com/blog/best-open-source-image-generation-models
- https://artificialanalysis.ai/articles/recent-open-weights-model-launches
- https://venturebeat.com/technology/enterprise-grade-ai-image-generation-in-2-seconds-is-here-krea-2-raw-and-turbo-available-as-open-weights-under-custom-license
- https://prompthero.com/ai-models/illustrious-xl-v2-0-stable-download

Read off this box, not the web
- `~/shared/comfy-studio/workflows/26_flux2_t2i.json` — the working FLUX.2 settings in §3.1
- `~/ComfyUI/models/{checkpoints,diffusion_models,loras,text_encoders,vae,controlnet}` — the inventory in §2
