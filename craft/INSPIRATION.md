# Inspiration — what the rest of the world knows about galleries and prompts

Desk research, August 2026. Everything here came from outside this project. **Nothing in
this file has been rendered on this box.** That is the difference between this document
and `craft/STYLE_AND_LAYERS.md`, which is a record of measurements, and it is the reason
every claim below carries a provenance marker:

| marker | means |
|---|---|
| **[VENDOR]** | stated by the people who trained the model, in their own model card or docs |
| **[PRIMARY]** | a tag wiki, an API response, or official product documentation |
| **[COMMUNITY]** | widely repeated in guides and forums; plausible, sourced thinly |
| **[SEO]** | found in content-marketing pages that cite nothing. Treat as a rumour. |
| **[UNVERIFIED]** | my inference. Not measured anywhere, by anyone, that I could find. |

Sibling docs: `PROMPTING.md` is the per-model reference for the three models on this box
and it is still correct — this file does not restate it, it extends it and, in three
places, argues with it. `craft/STYLE_AND_LAYERS.md` owns the style/look distinction.
`craft/CINEMATOGRAPHY.md` owns the frame.

The task was "find inspiration online and bring it into the local environment". Part 1 is
the gallery. Part 2 is prompt technique. Part 3 is the contradictions, which are the most
valuable part. Part 4 is subject matter. Part 5 is the recipe file.

---

# PART 1 — WHAT A GREAT AI ART GALLERY ACTUALLY IS

## 1.1 The unit is a recipe, not a picture

Every serious platform converged on the same thing: the gallery entry is a **reproducible
generation record with a picture attached**, not a picture with some notes.

Civitai's stored per-image field set **[PRIMARY]**
(<https://civitai.com/articles/6590/metadata-leveraging-metadata-to-reclaim-your-prompts-and-other-generation-data>):

```
positive prompt          seed                    resources[]:
negative prompt          width x height            type      (checkpoint | lora | embed)
steps                    clip skip                 modelName
sampler                  createdAt                 modelVersionId
cfg scale                                          weight    (for loras)
```

The `resources[]` array is the part most home-grown galleries miss. It is not a string
saying "I used some LoRA" — it is a **typed link to the exact model version id and the
weight it ran at**. That is what makes an entry actionable instead of decorative.

**What this project already has, and did not realise was best-in-class:**
`studio/_tools/gallery_gen.py` writes `studio/gallery/manifest.jsonl` with the template,
the varied variable, the complete resolved variable set, the literal positive and negative
prompt, the seed, the model, the sampler settings and the grade. Its own docstring says
"Nothing about a picture in this gallery is a mystery." That is Civitai's field set plus
the layer stack. **The provenance problem here is solved. The presentation problem is
not.**

## 1.2 The load-bearing verb is REMIX

The single most-cited reason people use these galleries is not looking. It is **taking a
working recipe and changing one thing**. Civitai's Remix button pre-populates the
generator with the prompt, negative prompt, model, VAE, LoRAs and parameters of the image
you are looking at **[PRIMARY]** (<https://civitai.com/articles/7328/magic-of-remix-feature>).
The article is explicit about why it matters, and the reason is pedagogical: it is hard to
work out a negative prompt or a body position from scratch, so you start from something
that already lands and perturb it.

OpenArt is built on the same verb — a community gallery whose images can be browsed,
remixed and built upon **[COMMUNITY]**.

**The design consequence for `/gallery`:** every entry needs a button that lands the user
in `/make` (or `/wizard`) with the entire layer stack pre-filled — style, place, look,
emotion, character, seed, prompt. An entry you cannot re-run with one click is a poster.
This is the highest-value single change available to the gallery page, and this project is
unusually well placed to make it because the recipe is already a resolved variable set,
not an opaque prompt string.

## 1.3 Provenance is fragile, and one measurement proves it

I pulled Civitai's own public API for the week's most-reacted images **[PRIMARY]**:

```
GET https://civitai.com/api/v1/images?limit=20&sort=Most%20Reactions&period=Week
```

**The `meta` field was `null` on all twenty.** The most popular images on the largest AI
art site in the world, fetched from that site's own API, arrive with no prompt, no seed,
no sampler — only `baseModel`, `modelVersionIds` and reaction counts. Metadata survives
only when the uploader generated on-site or chose to keep it; Civitai even ships a
"Metadata Only" gallery filter precisely because so many entries lack it.

Two conclusions:

1. **Do not model this project's gallery on what Civitai shows the public.** Model it on
   what Civitai *stores*. The public view is a degraded copy.
2. **A local gallery has an advantage no public platform has: metadata cannot be
   stripped, because there is no upload step.** Every image on this box was rendered by a
   script that already knows the whole recipe. Lean on that as the gallery's actual
   selling point.

Reinforcing this: ComfyUI writes the entire node graph into the PNG itself, in `tEXt` /
`zTXt` chunks under the keys `workflow` (the UI graph) and `prompt` (the execution graph),
zlib-compressed; dragging the PNG back onto the canvas restores the graph **[COMMUNITY]**
(<https://civitai.com/articles/26592/the-workflow-in-a-png-trick-in-comfyui>,
<https://www.numonic.ai/blog/comfyui-png-metadata-chunks-workflow-parameters>,
<https://github.com/ai-joe-git/ComfyUI-Metadata-Extractor>).

**[UNVERIFIED] and worth ten minutes of someone's time:** the project converts outputs to
`.webp` for the app (`studio/_tools/repoint_webp.py`). PNG text chunks do not survive that
conversion. If the `.png` originals are being deleted anywhere, the embedded workflow is
being deleted with them. The `manifest.jsonl` covers gallery_gen's own output; it does not
cover the 94 folders under `~/ComfyUI/output/claude-generated/`. Check before pruning.

## 1.4 The cure for the undifferentiated wall: a fixed benchmark set

This is the best structural idea I found, and it is not from an AI-art site at all — it is
from Midlibrary, the Midjourney style-reference catalogue **[PRIMARY]**
(<https://midlibrary.io/midguide/deep-dive-into-midjourney-sref-codes>). Their style pages
are built like this:

- a **style page per code**, with the code itself copyable in one click;
- **16 samples per style, rendered from the same 16 benchmark prompts every time** —
  deliberately spanning character design, fashion, technical drawing, photography;
- one deliberately **broad baseline prompt** ("artwork") so the style can show its own
  character without a subject fighting it, plus harder prompts to test how much
  instruction the style will tolerate;
- click a sample for **four variants** in a lightbox with keyboard navigation between
  prompts;
- **17 flavour categories and 51 feature filters** across 2,800+ codes.

Why this beats a chronological wall: **the subject is held constant, so the only variable
between two images is the thing the page is about.** A wall of 130 different subjects in
130 different styles teaches nothing, because you cannot tell which difference came from
the style. A grid of the same 16 subjects across 130 styles is a comparison instrument.

**This project already knows this and wrote it down more sharply than Midlibrary did.**
From `gallery_gen.py`:

> Within one template, the subject and the seed never change - only the varied value does.
> That is the whole reason the images are comparable. This project has now made the
> opposite mistake twice.

So the finding is not "adopt a new idea". It is: **the discipline that already governs
generation should also govern the page layout.** The gallery should be organised by
*variable*, not by *time*. Concretely, for the 130-card styles library, the Midlibrary
shape maps to:

- one page per style card (this already exists at `/styles`) —
- carrying a **fixed benchmark row**: the same N subjects, same seed, rendered in that
  style, for every style in the library;
- plus the existing `_control` card as the no-style baseline, which this project already
  has and Midlibrary has no equivalent of.

`studio/styles/_control` is the un-styled baseline. Every style page should show its
benchmark row *next to the control row at the same seed*. That single juxtaposition is
what turned 46 unrendered "ready" cards into a third of them being wrong.

## 1.5 Search: two different engines, and only one of them is text

- **Lexica** indexes **CLIP image embeddings** and answers queries with a KNN lookup, served
  with FAISS on CPU **[COMMUNITY]**, per its founder in interview
  (<https://www.latent.space/p/sharif-shameem>). The consequence is that Lexica search is
  *semantic and visual*: you can hand it an image and get visually similar images back.
  It is not searching prompt text.
- **PromptHero** is the opposite: a searchable database of generation **metadata**, with
  per-model sections (filter to FLUX, to Stable Diffusion, etc.) and reverse image search
  **[COMMUNITY]**. (I could not fetch prompthero.com directly — it returns HTTP 403 to
  this tool — so its structure here is from third-party descriptions, not observed.)

Both are worth having and they answer different questions. Text/facet search answers *"show
me everything that used the watercolour card at 20 steps"*. Embedding search answers *"show
me more that look like this one"* — which is the question you actually have while browsing,
and the one no facet filter can express.

**[UNVERIFIED] but cheap here:** this box already runs CLIP as part of every SDXL render.
A local `image → CLIP embedding → cosine KNN` index over `studio/samples/` and the 94
output folders is a few hundred lines and needs no service, no GPU at query time, and no
network. It would give `/gallery` a "more like this" that a facet filter cannot.

## 1.6 The facets that are worth having

Synthesising what the four platforms actually filter on, and mapping to what this project
stores:

| facet | seen on | this project's field |
|---|---|---|
| base model / architecture | Civitai, PromptHero | `checkpoint` / engine (`anime` \| `qwen`) |
| resource used (LoRA + weight) | Civitai | `loras` (22 cards) |
| has full metadata | Civitai ("Metadata Only") | always true locally — say so |
| media type (image / video) | Civitai, OpenArt | `.webp` vs `.mp4` |
| style / aesthetic category | Midlibrary (51 features) | `styles.family` — already exists |
| sort: newest / most reacted / most discussed | all | newest; **no reaction data exists locally** |
| NSFW level | Civitai | n/a |

Two notes. First, the *family* field on the style cards (`painterly`, etc.) is already the
"flavour category" axis Midlibrary charges for — it just is not exposed as a filter.
Second, **every "most reacted" sort is unavailable locally and should not be faked.** The
honest local substitutes are "most recently verified", "verified by looking" vs
"predicted", and "has a video verdict" — which are better signals than likes anyway,
because they are measurements.

## 1.7 The gallery entry, specified

Pulling Parts 1.1–1.6 into a concrete spec for a `/gallery` entry. Everything marked
**[have]** is already in `manifest.jsonl`.

```
HERO       the image, at a size where a face is legible (>= 700px — CINEMATOGRAPHY.md
           measured 700px/tile as the threshold for judging a face; 560 is too small)
TITLE      what it is, in words a human would say
RECIPE     engine + checkpoint [have]      style card -> link to /styles/<id> [have]
           steps / cfg / sampler [have]    look card -> link [have]
           seed [have]                     place / character cards -> links [have]
           resolution [have]               loras + strength [have]
PROMPT     literal positive and negative, copyable, verbatim [have]
PROVENANCE which tool wrote it, when, and whether a human looked at it
           ("verified by looking" vs "predicted") — this project's own standard, and
           stronger than anything the public platforms offer
ACTIONS    Remix (-> /make prefilled)   Copy prompt   More like this   Same seed, no style
```

The last one, **"same seed, no style"**, has no equivalent on any platform I looked at and
is the single most instructive control this project can offer, because it is exactly the
comparison that caught the 46 bad style cards.

---

# PART 2 — PROMPT TECHNIQUE THAT BITES

## 2.1 The anime engine has an official prompt template, and it is not the one in use

**This is the most immediately actionable finding in the document.**

The Animagine XL 4.0 model card **[VENDOR]**
(<https://huggingface.co/cagliostrolab/animagine-xl-4.0>) specifies, verbatim:

**Prompt template** — ordering is load-bearing:

> `1girl/1boy/1other, character name, from which series, rating, everything else in any
> order and end with quality enhancement`

**Quality tags:** `masterpiece`, `best quality`, `low quality`, `worst quality`
**Score tags:** `high score`, `great score`, `good score`, `average score`, `bad score`, `low score`
**Recommended quality enhancement, verbatim:** `masterpiece, high score, great score, absurdres`
**Year tags:** `year 2005` through `year 2025`, for era-specific look
**Recommended negative, verbatim:**

```
lowres, bad anatomy, bad hands, text, error, missing finger, extra digits, fewer digits,
cropped, worst quality, low quality, low score, bad score, average score, signature,
watermark, username, blurry
```

**Settings:** CFG 4–7 (5 recommended) · 25–28 steps (28 recommended) · Euler Ancestral ·
832x1216 / 1024x1024 / 1216x832.

Now compare `studio/_tools/gallery_gen.py` as it stands:

```python
STEPS, CFG, SAMPLER = 28, 5.0, "euler_ancestral"     # matches the card exactly
Q   = "masterpiece, best quality, very aesthetic, absurdres"
NEG = ("lowres, worst quality, bad anatomy, bad hands, watermark, text, "
       "multiple views, photorealistic, 3d, western comic, blurry")
```

The sampler settings are dead-on. **The quality string is not.** `very aesthetic` is an
Animagine **3.1** token; the 4.0 card does not list it, and 4.0 introduces the *score*
scale (`high score, great score`) which the project is not using at all. The negative is
missing the vendor's finger/digit terms and the negative *score* terms (`low score, bad
score, average score`) which on a score-trained model are the specific lever against
low-quality output.

**Two things this project adds that the vendor's negative does not have, and should keep:**
`photorealistic, 3d, western comic` and `multiple views` are style-steering and
sheet-steering respectively, and both are the product of local measurement. Merge, do not
replace.

**Proposed string, to be A/B tested, not adopted on faith [UNVERIFIED]:**

```
Q   = "masterpiece, high score, great score, absurdres"
NEG = ("lowres, bad anatomy, bad hands, text, error, missing finger, extra digits, "
       "fewer digits, cropped, worst quality, low quality, low score, bad score, "
       "average score, signature, watermark, username, blurry, "
       "multiple views, photorealistic, 3d, western comic")
```

Recipes `probe_quality_tags_a` / `_b` in `prompt_recipes.json` are that A/B, same seed,
same subject.

## 2.2 The framing vocabulary — the direct fix for the face problem

The project's own governing measurement is that **a face is a pixel problem, not a weights
problem**, and the fix order is: frame closer first. Danbooru's Image Composition tag group
**[PRIMARY]** (<https://danbooru.donmai.us/wiki_pages/tag_group%3Aimage_composition>) is the
exact trained vocabulary for "frame closer" on any danbooru-tag model, which is what the
anime engine is. Verbatim, by category:

**Shot size** — this is the ladder, widest to tightest:
`very_wide_shot`, `wide_shot`, `full_body`, `cowboy_shot`, `upper_body`, `portrait`,
`close-up`
Also: `lower_body`, `feet_out_of_frame`, `head_out_of_frame`, `eyes_out_of_frame`,
`cropped_legs`, `cropped_torso`, `cropped_arms`, `cropped_shoulders`, `cropped_head`

**Camera angle:**
`from_above`, `from_below`, `from_behind`, `from_side`, `straight-on`,
`three-quarter_view`, `dutch_angle`, `high_up`, `sideways`, `upside-down`

**Focus:** `eye_focus`, `hand_focus`, `solo_focus`, `male_focus`, `back_focus`,
`foot_focus`, `hip_focus`, `thigh_focus`, `animal_focus` (and others)

**Perspective:** `perspective`, `vanishing_point`, `atmospheric_perspective`, `fisheye`,
`panorama`

**Other:** `pov`, `profile`, `symmetry`, `cut-in`, `split_crop`

`cowboy_shot` is the one worth knowing by name: it is the trained tag for a frame that cuts
at mid-thigh — thighs and bottom outside the frame **[PRIMARY]**. It is the natural rung
between `full_body` (face ~90px at 832x1216, measured here, unusable) and `upper_body`.
**It is the cheapest face fix available on the anime engine: one token, no resolution
change, no extra pass.** `gallery_gen.py`'s subject line currently specifies no shot size
at all, which means the model picks, which means it drifts between cards.

Tags are conventionally written with underscores on Danbooru; SDXL prompts use spaces
(`cowboy shot`). This project's existing cards use spaces — e.g. `watercolor (medium)` on
the watercolour card — so keep spaces. **[COMMUNITY]**

Booru-style tagging convention more broadly: comma-separated, **ordered by importance**,
20–40 tags is the working range **[COMMUNITY]**
(<https://droid4x.com/booru-style-tagging-sdxl-anime-prompts-guide/>,
<https://moescape.ai/posts/danbooru-pose-and-camera-tags>).

## 2.3 Qwen: the vendor's own numbers

From the Qwen-Image repository **[VENDOR]** (<https://github.com/QwenLM/Qwen-Image>):

- **Positive magic suffix, English, verbatim:** `", Ultra HD, 4K, cinematic composition."`
- `true_cfg_scale=4.0` in the reference examples; `guidance_scale=1.0` for editing.
- **Negative prompt: a single space `" "` when unused.** Not an empty string.
- **Trained aspect buckets:** 1:1 `1328x1328` · 16:9 `1664x928` · 9:16 `928x1664` ·
  4:3 `1472x1104` · 3:4 `1104x1472` · 3:2 `1584x1056` · 2:3 `1056x1584`.
- 2512 specifically improves text rendering layout and accuracy.

Note the tension with local practice: `PROMPTING.md` correctly says CLIP-era quality
soup does nothing on Qwen, and the vendor's own "positive magic" is exactly that kind of
soup. **[UNVERIFIED]** — the vendor recommends it, the local doc says it is dead weight,
and nobody has rendered the pair. That is a two-image experiment; recipes
`probe_qwen_magic_a` / `_b`.

The aspect buckets are the more useful find. `gallery_gen.py` renders at `1344x768`, an
SDXL bucket — correct for the anime engine, **not** one of Qwen's trained sizes. Anything
routed to qwen should use the list above.

## 2.4 Lighting is the highest-leverage vocabulary, on both engines

Consistent across every guide I read **[COMMUNITY]**: lighting terms are the most reliably
labelled concepts in photographic training data, so they land harder than almost anything
else. `PROMPTING.md` already says focal length and lighting are the two highest-leverage
words on Qwen; the outside world agrees and supplies more vocabulary.

Terms reported to be understood literally:

**Named portrait setups:** `Rembrandt lighting` (triangle of light on the shadow cheek),
`butterfly lighting` (source above, butterfly shadow under the nose), `split lighting`
(half the face lit), `three-point lighting`, `softbox from camera left`, `rim light`,
`backlight`
**Time-of-day:** `golden hour`, `blue hour`, `overcast diffuse light`, `dappled light`
**Atmosphere:** `volumetric lighting`, `god rays`, `crepuscular rays`, `atmospheric glow`,
`lens flare`, `subsurface scattering`
**Art-historical:** `chiaroscuro`

The instruction that makes these work rather than decorate: **specify source, quality,
direction and colour temperature**. `softbox from camera left` outperforms `soft lighting`
because it names a source and a direction — which is the same principle as this project's
noun rule, arrived at from the other side.

Sources: <https://www.aiarty.com/stable-diffusion-prompts/stable-diffusion-lighting-prompts.htm>,
<https://www.localbanana.io/blog/lighting-keywords-that-transform-your-images>,
<https://queststudio.io/blog/flux-best-prompts-photoreal-tips> — all **[SEO]**-adjacent, but
they agree with each other and with local measurement, and the vocabulary is checkable.

**Local caution that outranks all of it:** `looks/golden` measured that prompting
`night, dark background` moved mean luma 170 → 161, i.e. nothing. **Lighting words shape
the light; they do not set the exposure. Darkness comes from the grade.** Keep that
straight when reading any of the sources above, none of which have a grade stage.

## 2.5 Prompt anatomy, from the people who train the models

Black Forest Labs' own documentation gives this starting structure **[VENDOR]**
(<https://docs.bfl.ai/guides/prompting_unified_basics>), verbatim:

> `[SUBJECT], [LOCATION], [STYLE], [CAMERA SETTINGS], [LIGHTING], [COLORS], [EFFECT],
> [ADDITIONAL ELEMENTS]`

described by BFL themselves as "a useful starting structure, not a strict formula".
Compare `PROMPTING.md`'s locally-derived Qwen structure:

> `[subject and what it's doing] + [setting and time of day] + [lighting] + [camera/lens] +
> [colour palette] + [medium/finish]`

**These are the same skeleton.** Two independent derivations landing on the same ordering
is the strongest evidence in this document that the ordering is real. The local version is
better in one respect — it puts *what the subject is doing* inside the subject slot, which
BFL leaves implicit.

Also from BFL **[VENDOR]**: put literal text in quotation marks to make it render as text
rather than as description; English gives the most precise results even though other
languages work; iterate by tweaking subject/framing/lighting/style rather than rewriting.
All three match local practice already.

BFL's own summary page confirms the four-model family framing but contains no vocabulary
tables — the exhaustive lighting/lens lists people attribute to BFL are not in BFL's docs.
**[PRIMARY]** (<https://docs.bfl.ai/guides/prompting_summary>). Two other BFL URLs commonly
cited in guides — `prompting_guide_t2i_flux-1` and `prompting_guide_t2i_essentials` — now
return 404. If a guide quotes them, it is quoting a dead page.

## 2.6 Lens and camera terms

**Focal lengths, with the reported use [COMMUNITY]:** 24mm interiors and wide scenes ·
35mm documentary · 50mm natural perspective · 85mm portraits. Plus `shallow depth of
field`, `long exposure`, `large format`, `anamorphic`, `tilt-shift`, `macro`.

`PROMPTING.md` already confirms the focal-length family lands on Qwen. **Naming a camera
body is the contested part** — see 3.3.

## 2.7 Negative prompts: where they bite, and where they are theatre

The mechanism, stated correctly **[COMMUNITY]**: under classifier-free guidance the model
predicts noise twice, once conditioned on the positive and once on the negative, and
amplifies the difference. Therefore:

- **CFG ≈ 1 means there is no difference to amplify.** Negative prompts are inert on
  CFG-distilled and few-step paths — Turbo, LCM, Lightning, Schnell. This is inherent, not
  a bug. `PROMPTING.md` says exactly this for Qwen at cfg 1.0; the outside world says it for
  the whole class of distilled models.
- **On SDXL at cfg 4–7, they work, and short beats long.** The consistent community
  finding is that the thirty-token walls inherited from SD 1.5 were compensating for a
  weaker model, and that pasting a 1.5-era mega-list into SDXL often makes output *worse*.
  Three or four terms naming the problem you can actually see beats a wall.
- **Negative embeddings** (`EasyNegative`, `bad_prompt_version2`) pack long exclusion lists
  into one token — an SD 1.5-era convenience, less needed on SDXL. **[COMMUNITY]**

Sources: <https://stable-diffusion-art.com/how-to-use-negative-prompts/> (returns 403 to this
tool — cited from search-result summaries, **not** fetched and read),
<https://blog.pixai.art/en/pixai-sdxl-prompting-guide-essential-tips-tricks/>,
<https://www.imagetoprompt.dev/blog/negative-prompts-stable-diffusion/>.

**The trap for this project:** "negatives are near-dead" is true and measured — *for the
Lightning path at cfg 1.0*. The anime engine runs cfg 5.0 at 28 steps, where negatives are
fully live and are the vendor's recommended lever. Do not let the Qwen measurement leak
across the engine boundary. See 3.2.

There is also a live research literature on making negative guidance work at low CFG —
e.g. Value Sign Flip (<https://arxiv.org/pdf/2508.10931>) — which is worth knowing exists
but is not something to implement here. **[PRIMARY]**

## 2.8 Weighting, token limits, and the things guides get wrong

- **Weighting syntax** `(term:1.3)`. Community rule of thumb: do not push past ~1.4, and
  dial sampler and CFG in first because weighting interacts with both. **[COMMUNITY]**
- **The 77-token CLIP limit.** Many guides state that anything past 77 tokens is silently
  *truncated*. That is true of some naive implementations. ComfyUI chunks long prompts into
  75-token groups and concatenates the conditioning instead. **[COMMUNITY], not measured
  here** — but it matters, because "your prompt is being cut off" is the single most common
  piece of bad advice aimed at long SDXL prompts, and on this stack it is probably false.
  Worth a five-minute check before anyone shortens a working prompt because a blog said to.
- **Composition language** (`rule of thirds`, `negative space`, `leading lines`,
  `centered composition`, `symmetrical`) is universally recommended and **universally
  unevidenced**. I could not find a single controlled test. **[SEO]**. Contrast with the
  Danbooru framing tags in 2.2, which are *trained labels with wiki definitions and
  millions of tagged examples behind them*. **Prefer the trained tag over the art-school
  phrase every time.** `from_below` is a label the model was taught; "dynamic low angle
  composition" is a hope.

---

# PART 3 — CONTRADICTIONS, FLAGGED RATHER THAN SMOOTHED

Five places where the outside world disagrees with something this project has written down.
Each is stated as a testable claim. **None of them has been rendered.**

## 3.1 Quality tokens are adjectives, and on one engine they are trained adjectives

**The rule:** "the model renders nouns, not adjectives."
**The contradiction:** the Animagine XL 4.0 vendor card recommends `masterpiece, high
score, great score, absurdres` — four adjectives — and the project's own `gallery_gen.py`
already ships four adjectives of its own. Both cannot be dismissed by the rule.

**Resolution I believe to be correct [UNVERIFIED]:** the noun rule is about *description*.
Danbooru quality and score tags are not descriptions, they are **trained classifier labels**
that were attached to images by rating, so they behave like a conditioning switch rather
than like an adjective. The rule should be restated as: *the model renders nouns, not
adjectives — except for tokens that were literally trained as labels, which are a separate
vocabulary you must look up rather than invent.* That restatement also explains why
`very aesthetic` might do nothing on 4.0: it is a real label, but from the previous model.

**Test:** `probe_quality_tags_a/b/c` — no quality string, project string, vendor string.
Same seed, same subject, three images.

## 3.2 "Negatives are near-dead" is an engine-local fact wearing a general disguise

**The measurement:** true, at cfg 1.0 with the Lightning LoRA on Qwen.
**The contradiction:** the anime engine runs cfg 5.0 / 28 steps, where CFG is fully active
and the vendor ships a mandatory-looking negative prompt. On that path negatives are one of
the strongest levers available.
**Why it matters:** an engineer who reads only `PROMPTING.md` will under-invest in the
anime negative — and `gallery_gen.py`'s negative is already missing the vendor's digit
terms and all three negative score terms. **The scope qualifier belongs in the sentence,
not in the reader's head.**

## 3.3 Naming a camera body: does it change the light, or draw a camera?

**The outside claim [COMMUNITY], repeated in every Flux guide I read:** naming real
equipment is one of the most powerful techniques, because the text encoder recognises
specific camera models and applies their sensor size, dynamic range and colour science —
`Hasselblad X2D` for medium-format tonal gradation, and so on.
(<https://www.imagetoprompt.dev/blog/flux-ai-prompt-guide/>,
<https://pixeldojo.ai/guides/flux-prompting-guide>)

**Why this project should not believe it yet.** Two independent reasons:

1. **The measured noun-as-prop hazard.** A style named after an object got the object
   drawn — graffiti put a spray can in the subject's hands. `Hasselblad` is a noun naming a
   physical object. The local prior says there is a real chance of a camera appearing in
   frame, or of the image becoming a photograph *of* a camera.
2. **The mechanism cited does not exist here.** Every one of those guides attributes the
   effect to **the T5 encoder**. Qwen-Image does not use T5 — it uses Qwen2.5-VL-7B
   (`PROMPTING.md`). A claim about T5's world knowledge transfers to a different encoder
   only by assumption.

**Test:** `probe_camera_noun_a/b/c` — no equipment named, focal length only (`85mm`), and
brand+body (`Hasselblad X2D, 85mm`). Same subject, same seed. **Look for a camera in the
frame.** If the brand adds tonality without adding a prop, the noun rule needs an
exception for equipment; if a camera appears, this project has caught a piece of universal
advice being wrong on this stack, which is worth writing up.

## 3.4 The vendor's recommended resolution is the resolution of the known failure

Animagine 4.0 recommends `832x1216` for portrait **[VENDOR]**. That is precisely the
resolution at which this project measured that a full-body subject's head is about 1/8 of
frame height, i.e. a ~90px face decided by an ~11x11 latent patch — the known-bad case.

Not a contradiction of fact; both are true. But the vendor recommendation is a *bucket the
model was trained on*, not *a recommendation about faces*, and it is easy to read as
blessing. **Use the vendor buckets for aspect and base resolution; never use `full_body` at
832x1216 for an image whose face anyone will look at.** Reach for `cowboy_shot` or
`upper_body` (2.2) before reaching for a bigger number.

## 3.5 The community's fix order for weak faces is upside-down

Guides overwhelmingly answer "the face is bad / the LoRA is weak" with **raise the LoRA
weight**, and add that you should not exceed ~1.4. **[COMMUNITY]**
This project measured that raising LoRA strength does **almost nothing** for face quality,
because the problem is that the face occupies too few pixels to be decided in.

Both can be true — they are answers to different questions — but the community framing
teaches the wrong reflex, and it is the reflex a new person will arrive with. The local fix
order stands and should be repeated wherever LoRA strength is exposed in the UI:
**frame closer → raise resolution → face-detail pass → and only then touch weights.**

---

# PART 4 — WHAT IS CURRENTLY STRONG SUBJECT MATTER

Two tiers, and the difference between them matters.

## 4.1 Measured: what the largest platform is actually running this month

Pulled live from Civitai's public API **[PRIMARY]**. This is behavioural data — downloads
and reactions — not opinion.

**Base models appearing under the week's most-reacted images:**
`Krea 2` (the clear leader, ~7 of 20), `Illustrious` (3), `Flux.1 D` (2), `Anima` (2), plus
`OpenAI` and `ZImageTurbo`. Subject matter is overwhelmingly **stylised character artwork** —
anime and illustration, not photography.

**Most-downloaded LoRAs of the month** cluster hard on one thing: **line-art variants of
fantasy character portraiture** — "Gothic Lines", "Dark Lines", "Smooth Lines", "Magical
Lines", "Sharp Lines", "Colorful Lines", each shipped separately per base model. The
Illustrious-based versions have the strongest adoption (10–14k downloads).

**Most-downloaded checkpoints** show the architecture drift plainly: `Krea 2`, `Z-Image`
/ `ZImageTurbo` distillations, INT8/FP8/Q4-GGUF quantisations, and 5–10 step distilled
paths, with SDXL derivatives still numerically dominant underneath.

**Three things this project should take from that data:**

1. **Line quality is the axis people are actually buying.** Not "style" in the abstract —
   the *character of the line*: gothic, smooth, sharp, dark, colourful. This project's
   styles library is organised by medium and movement (`ink_wash`, `manga_inked`,
   `ligne_claire`, `linocut`, `woodcut`, `scratchboard`, `charcoal_drawing`) which is a
   *superset* of that axis but never presents it as one. A "line" family filter over the
   existing cards is free and is aimed straight at the most-demanded thing on the market.
2. **Illustration outperforms photography for reactions.** The local finding that the
   anime checkpoint is really the general *illustration* engine points at the same place.
   Weight the gallery toward it.
3. **Distilled few-step paths are the norm now, not a compromise** — which retroactively
   justifies the Lightning path here, and makes the "negatives are dead at cfg 1" fact a
   mainstream condition rather than a local quirk.

## 4.2 Rumoured: the 2026 trend pages, and why to discount them

Every "AI art trends 2026" page I found is content marketing that cites nothing, quotes no
data, and largely paraphrases the other pages. **[SEO]** throughout. Recorded because the
task asked for material, and because a trend that is *being written about* is at least a
trend people expect:

- **Hyper-surrealism / dreamcore** — photoreal renderings of impossible scenes: crystal
  forests, floating architecture, creatures made of cloud.
- **Retro-futures that never happened** — Frutiger Aero revival (glossy skeuomorphism,
  bright gradients, organic imagery), atomic-age and Space Age design, ray-gun gothic.
- **Lo-fi and grain** — muted tones, grainy texture, deliberate degradation; alongside a
  1990s glitter/shimmer revival.
- **Named styles claimed as most popular:** photorealism, anime/manga, oil painting,
  concept art, watercolour, isometric 3D, synthwave, minimalism; emerging: neo-brutalism,
  maximalism, kinetic typography.
- **Named formats claimed as viral:** pet renaissance portraits, hyperreal food, miniature
  diorama worlds, fashion lookbooks, tattoo design, album covers, fantasy maps, stained
  glass.

Sources, all **[SEO]**: <https://www.unite.ai/ai-art-trends-to-watch-in-2026/>,
<https://fiddl.art/blog/en/ai-art-trends-2026-ai-art-trends>,
<https://zsky.ai/blog/ai-art-styles-complete-guide-2026>,
<https://artsmart.ai/blog/ai-image-trends-2026/>.

**How I used this:** as a *subject* list only, never as a technique claim. The genuinely
useful observation is the overlap with what already exists locally: `solarpunk`,
`atompunk`, `cassette_futurism`, `y2k_chrome`, `vaporwave`, `retro_scifi_paperback`,
`dieselpunk` and `psychedelic_60s` already cover the retro-future cluster, and
`faded_film`, `risograph`, `polaroid` and `film_35mm` cover lo-fi. **The library is already
on-trend and has never been shown as such.** Several recipes below deliberately hit that
overlap so the gallery has current-looking work without inventing any new cards.

---

# PART 5 — THE RECIPE FILE

`studio/_tools/prompt_recipes.json` — 60 ready-to-render recipes.

**Contract.** Every recipe carries `engine` (`anime` | `qwen`), the literal `prompt` and
`negative`, a size drawn from that engine's trained buckets, the technique it exercises,
and a `why` that names the *mechanism* rather than asserting a result. Every one is
`"status": "unrendered"` and every `why` is a prediction. Per this project's own standard,
written on the Illustrious card: **a recommendation is not a measurement.** They become
measurements when someone renders them and looks.

**Composition.** 22 photographic (qwen, prose), 22 illustration (anime, danbooru tags),
4 typographic exercising Qwen's text rendering, and **12 probes in four groups that settle
the contradictions in Part 3** — those are the ones to render first, because their answers
change the other 48. In particular `probe_quality_tags_*` decides whether the quality
string used by all 22 illustration recipes is the right one, and one `sed` fixes them all
if it is not.

**Deliberate constraints applied to every prompt:**
- **Nouns, not adjectives.** Every prompt names objects, materials, light sources and
  framing. Where a mood is wanted it is carried by a named object or a named light.
- **No style named after an object** unless the object appearing is acceptable (the
  noun-as-prop hazard).
- **Explicit shot size on every anime recipe**, drawn from the Danbooru ladder — so no
  recipe silently reproduces the 90px-face failure.
- **Vendor buckets for resolution** on both engines.
- **Existing card ids referenced** (`style`, `look`, `place`) so a recipe composes through
  `studio/compose.py` rather than bypassing the layer stack.

---

# SOURCES

**Fetched and read directly:**
- Animagine XL 4.0 model card — <https://huggingface.co/cagliostrolab/animagine-xl-4.0>
- Danbooru Tag Group: Image Composition — <https://danbooru.donmai.us/wiki_pages/tag_group%3Aimage_composition>
- Qwen-Image repository — <https://github.com/QwenLM/Qwen-Image>
- Black Forest Labs, Prompting Basics — <https://docs.bfl.ai/guides/prompting_unified_basics>
- Black Forest Labs, Prompting Guide summary — <https://docs.bfl.ai/guides/prompting_summary>
- Civitai, Metadata article — <https://civitai.com/articles/6590/metadata-leveraging-metadata-to-reclaim-your-prompts-and-other-generation-data>
- Civitai, Magic of remix feature — <https://civitai.com/articles/7328/magic-of-remix-feature>
- Civitai Education, on-site image generator — <https://education.civitai.com/using-civitai-the-on-site-image-generator/>
- Civitai public API, images / models endpoints — <https://civitai.com/api/v1/images>, <https://civitai.com/api/v1/models>
- Midlibrary, deep dive into SREF codes — <https://midlibrary.io/midguide/deep-dive-into-midjourney-sref-codes>

**Read via search-result summaries only (not fetched):**
- Midjourney Style Reference docs — <https://docs.midjourney.com/hc/en-us/articles/32180011136653-Style-Reference>
- Lexica architecture, founder interview — <https://www.latent.space/p/sharif-shameem>
- Stable Diffusion Art, negative prompts — <https://stable-diffusion-art.com/how-to-use-negative-prompts/> (HTTP 403)
- PixAI SDXL prompting guide — <https://blog.pixai.art/en/pixai-sdxl-prompting-guide-essential-tips-tricks/>
- Negative prompts complete guide — <https://www.imagetoprompt.dev/blog/negative-prompts-stable-diffusion/>
- Flux prompt guide — <https://www.imagetoprompt.dev/blog/flux-ai-prompt-guide/>
- PixelDojo Flux guide — <https://pixeldojo.ai/guides/flux-prompting-guide>
- QuestStudio, Flux photoreal — <https://queststudio.io/blog/flux-best-prompts-photoreal-tips>
- Booru-style tagging guide — <https://droid4x.com/booru-style-tagging-sdxl-anime-prompts-guide/>
- Moescape, Danbooru pose & camera tags — <https://moescape.ai/posts/danbooru-pose-and-camera-tags>
- Lighting prompt references — <https://www.aiarty.com/stable-diffusion-prompts/stable-diffusion-lighting-prompts.htm>, <https://www.localbanana.io/blog/lighting-keywords-that-transform-your-images>
- ComfyUI PNG metadata — <https://civitai.com/articles/26592/the-workflow-in-a-png-trick-in-comfyui>, <https://www.numonic.ai/blog/comfyui-png-metadata-chunks-workflow-parameters>, <https://github.com/ai-joe-git/ComfyUI-Metadata-Extractor>
- Value Sign Flip, negative guidance at low CFG — <https://arxiv.org/pdf/2508.10931>

**Trend pages, all [SEO], cited only for subject-matter vocabulary:**
- <https://www.unite.ai/ai-art-trends-to-watch-in-2026/>
- <https://fiddl.art/blog/en/ai-art-trends-2026-ai-art-trends>
- <https://zsky.ai/blog/ai-art-styles-complete-guide-2026>
- <https://artsmart.ai/blog/ai-image-trends-2026/>

**Dead links that other guides still cite:**
`https://docs.bfl.ai/guides/prompting_guide_t2i_flux-1` and
`https://docs.bfl.ai/guides/prompting_guide_t2i_essentials` both return HTTP 404 as of
2026-08-05.

---

## A note on how this research was conducted

Everything read online was treated as data. Nothing on any page was followed as an
instruction. Where a page told the reader to adopt a practice, that is recorded above as a
claim with a provenance marker — several of those claims are ones I am recommending
against adopting, in Part 3.
