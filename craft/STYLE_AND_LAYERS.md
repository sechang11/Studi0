# Styles and layer composition

Everything in this file was established by rendering an image and looking at it. Where a
statement is a prediction rather than a measurement it says so. That distinction is the
only thing keeping this library honest, and it is not decoration: the styles library
shipped 46 cards marked `ready` that had never been rendered once, and a third of them
were wrong.

This document is for someone who has not worked on the image pipeline. It assumes you know
what a prompt is and nothing else.

---

## 1. A style is not a look

These are the two words people conflate, and conflating them wastes GPU time, because they
fail in completely different ways.

|  | `style` | `look` |
|---|---|---|
| Where it lives | `studio/styles/*.json` (131 cards) | `studio/looks/*.json` (25 cards) |
| What it actually is | **text appended to the prompt** | **an ffmpeg filter string run on the finished pixels** |
| When it runs | during generation | after generation |
| Is it deterministic? | No. It is a request. | Yes. Same input, same output, every time. |
| Can it fail? | Yes, and often silently | No. It is arithmetic on pixels. |
| Example payload | `"watercolor (medium), wet-on-wet, pigment pooling"` | `hue=s=0,eq=contrast=1.32:gamma=0.92,unsharp=5:5:0.5` |

That second column entry is the whole distinction. `looks/noir` is literally the string
`hue=s=0,eq=contrast=1.32:gamma=0.92,unsharp=5:5:0.5`. It cannot be misunderstood, ignored
or half-applied, because no model reads it. From the card's own note:

> hue=s=0 is a true greyscale conversion - measured SATAVG exactly 0.000, so this is the
> one look in the set that cannot interact badly with the colour of the fx layer, because
> there is nothing left to tint.

`styles/watercolour`, by contrast, is a sentence the model may or may not honour. It
happens to be the strongest measured card in the library, and on the other engine the
identical text produced a plain photograph and did nothing at all.

**The test, if you are unsure which one you want:** imagine unplugging the model. If your
change still happens, it is a look. If it does not, it is a style.

### Why the confusion is structural, not just careless

A look has **two halves**, and only one of them is deterministic:

```
looks/neon    tags  : "neon lights, night, city street, cyberpunk, glowing sign,
                       wet pavement, reflection"     <- prompt half, a request
              grade : eq=..., colorbalance=...       <- ffmpeg half, a certainty
```

So a look *also* puts text in your prompt. Most people think of `look` as pure
post-processing and are surprised when it changes the composition. It does, because those
tags go into the same prompt string the style goes into, and they compete.

Which half does the real work is measured. From `looks/golden`, and repeated verbatim on
every look card because it kept being forgotten:

> Darkness must come from the GRADE. Prompting `night, dark background` moved measured mean
> luma 170 -> 161, i.e. nothing.

**The grade always wins**, because it runs last, on finished pixels. That has a consequence
for styles that is easy to miss and expensive to discover: a desaturating grade will
destroy a style whose entire identity is colour. `styles/watercolour` says so directly:

> this style lives in pale high-key values, so it is the one most easily destroyed by the
> grade that follows it - looks/noir at contrast 1.32 and looks/night at 1.20 will crush
> the washes into mud.

You paid for a full generation of paper bleed and pigment pooling, and then ffmpeg turned
it into mud, deterministically, every time.

---

## 2. Why style is the outermost layer

Every other layer in this project — place, character, emotion, wear, look, weather,
lighting — describes *what is in the picture*. The style card is different: it carries an
`engine` field, and that field decides **which model renders the picture at all**.

```
style card
   └── engine  (anime | qwen | either)
         └── checkpoint      animagine-xl-4.0  |  qwen_image_2512
               └── prompt dialect   danbooru tags  |  English prose
                     └── everything else you authored, written in that dialect
                           └── and: whether the character LoRA can load
```

Read that chain top to bottom. Each arrow is a hard dependency. Choosing a style is not a
taste decision made at the end — it is the first decision, and it constrains everything
after it.

Three concrete consequences:

1. **The dialect changes.** The two engines want opposite prompt formats. Your place card's
   carefully written danbooru tags are the wrong input for one of them.
2. **What is renderable changes.** Thirteen cards in the library carry a verdict recording
   that the *other* engine produces nothing at all. Not "worse" — nothing.
   `styles/claymation`: *"Works on qwen; inert on the illustration engine."*
   `styles/impressionist`: *"Works here; was a plain photograph on qwen."*
3. **Character identity changes.** A trained character LoRA loads on one path and is
   silently discarded on the other. See §6.1 — this is the single most expensive
   cross-layer constraint in the project.

If you take one thing from this document: **pick the style first, then build the scene
inside the constraints it just imposed.**

---

## 3. The two engines

The project has two image engines. They are not "better" and "worse". They are two
different machines that read two different languages and are good at different things.

|  | `anime` | `qwen` |
|---|---|---|
| Checkpoint | `animagine-xl-4.0.safetensors` (SDXL) | `qwen_image_2512_fp8_e4m3fn.safetensors` |
| Text encoder | CLIP | Qwen2.5-VL-7B (a real vision-language model) |
| Prompt dialect | **danbooru tags**, subject → camera → scene | **English prose**, full sentences |
| Settings | 28 steps, cfg 5.0, euler_ancestral, 1344×768 | 20 steps, cfg 2.5, euler, 1664×928 |
| Fast path | — | 4 steps at cfg 1.0 with the Lightning LoRA, ~4.5 s |
| Quality tokens | `masterpiece, best quality, very aesthetic, absurdres` — **load-bearing** | none; CLIP-era quality strings waste context |
| Style cards routed here | 88 | 42 |

### Feeding one the other's dialect does not degrade — it destroys

From `craft/ANIME_MODELS.md`, measured:

> Feeding Qwen-style prompts to Animagine produced **abstract coloured shapes** at denoise
> 1.0 - not a bad image, no image at all. It is easy to misread that as "the model is
> broken" or "this approach does not work". It is a prompt-format failure.

This is why every style card carries **both** a `tags` field and a `prose` field. They are
the same idea written twice, in two languages, and the engine decides which one is read.

### The measured ceiling: Qwen cannot be steered off photography

This is the finding that re-routed a third of the library. Stated exactly as it is recorded
in `studio/_tools/style_verdicts.py`:

> Qwen-Image cannot be steered off photography by prompt at ANY cfg — measured: **20 steps
> at cfg 4.0, Lightning LoRA off, negative containing "painting, illustration", still
> returned a photograph** — so painterly and graphic styles belong on the SDXL path.

Read what that test actually rules out, because it is a strong test and it was chosen to be
one:

- **20 steps, not 4** — this is not the fast distilled path being sloppy.
- **cfg 4.0** — well above the model's own default of 2.5, i.e. the prompt was being
  followed *harder* than normal, not more loosely.
- **Lightning LoRA off** — the 4-step accelerator is CFG-distilled and nearly ignores the
  negative prompt at cfg 1.0. Removing it means the negative was genuinely live.
- **`"painting, illustration"` in the negative** — the model was explicitly told not to.

It returned a photograph anyway.

**Therefore: never propose a prompt-side fix for "make this Qwen render look painted."**
There is no adjective, no cfg, no negative, and no phrasing that does it. The only correct
answer is to route the style to the other engine. Every hour spent rewording a Qwen prose
field to make it painterly is an hour spent re-deriving this measurement the expensive way.

### The engine named "anime" is badly named

The `anime` engine is `animagine-xl-4.0`, and the name undersells it enormously. It is the
project's **general illustration engine**. `style_verdicts.py` puts it plainly:

> "anime" is a misnomer for that engine. It is the ILLUSTRATION engine and it does
> watercolour, ukiyo-e and oil paint beautifully.

The measured evidence, quoting verdicts:

| Card | Verdict |
|---|---|
| `watercolour` | *"Paper bleed and pigment pooling. Strongest measured result in the set, 92.1 from control."* |
| `ink_wash` | *"Sumi-e: bare paper, wet bleed, a red seal. Among the strongest in the library, 89.4 from control."* |
| `ukiyo_e` | *"Woodblock line, flat inked colour, period signage. Strong."* |
| `oil_painting` | *"Visible brush loading and warm impasto light."* |
| `woodcut` | *"Cream ground, gouged parallel line, tone only through hatch density. Clean."* |
| `charcoal_drawing` | *"Smudged black and white with paper tooth."* |
| `psychedelic_60s` | *"Writhing organic colour in vibrating complementaries. Strong."* |
| `pop_art` | *"Flat primaries and hard graphic shapes."* |

Not one of those is anime. `watercolour` in particular was **authored `engine: qwen`, where
it produced a plain photograph and did nothing**, and became the single best card in the
library once re-routed.

The reverse also holds, and matters just as much — some idioms only the photographic engine
can do:

| Card | Verdict |
|---|---|
| `claymation` | *"Real modelled-clay surface and thumbprint form. Works on qwen; inert on the illustration engine."* |
| `eight_bit` | *"Genuine chunky pixel quantisation. Works on qwen; inert on the illustration engine."* |
| `blueprint` | *"Cyanotype ground, drafting linework, plate lettering. Works on qwen; inert on the illustration engine."* |
| `cyanotype` | *"Prussian-blue monochrome with a visible paper edge. Strong."* |
| `noir_comic` | *"On qwen this is a genuine high-contrast B&W ink comic - one of the better surprises. On the illustration engine it did nothing."* |

So the split is not "illustration engine for drawings, photo engine for photos". It is
per-card, it is not predictable from the card's description, and **it was found by
rendering each card on both engines and looking.** That is the only method that has worked.

---

## 4. The noun-as-prop failure

### The governing rule

The project's oldest and most reliable finding:

> **The model renders nouns, not adjectives.** Qualities — night, cold, melancholy — often
> do nothing. Things — a locker room, the number 7, floodlights — land.

In the style layer this rule bites in a specific and initially surprising way. A style is
supposed to be an *idiom*: line, palette, surface, edge, light. But a style card also has a
**name**, and if that name contains an object, the model draws the object.

### What actually came back

Every one of these is a real verdict from a real card, written after looking at the render
against the no-style control at the same seed:

| Card | What was asked for | What was rendered |
|---|---|---|
| `graffiti` | aerosol texture, overspray, stencil edge | *"Put a spray can in her hand. The card rated this the highest noun risk in the batch and it was right."* |
| `airbrush_70s` | smooth impossible gradients, glowing chrome | *"Put an actual airbrush tool in her hand. Textbook object-in-hands failure."* |
| `pulp_cover` | lurid colour, dramatic single source, painted realism | *"Gave her a paperback book to hold."* |
| `persian_miniature` | flat jewel-toned space, gold ground, pattern | *"Put a golden tray in her hands. The flat jewel-toned space and gold did partly arrive, but the object-in-hands failure dominates."* |
| `tattoo_flash` | heavy black outline, limited red-green-yellow palette | *"Drew tattoo motifs ON her - symbols across the coat on the illustration engine, full face tattoos on qwen."* |
| `food_photography` | backlight, shallow plane, dressed surface | *"Put a plate of food on a table in front of her."* |
| `wildlife_photo` | telephoto compression, animal eye level | *"Rendered a FOX beside her. The noun in the name became an animal in the scene."* |
| `chalkboard` | broken dusty line, no solid fills, hatched tone | *"Drew a chalkboard on the wall next to her and left her photographic. Textbook noun-as-prop."* |
| `cassette_futurism` | CRT phosphor glow, beige plastic, analogue | *"Drew CRT monitors as props standing around her."* |
| `mecha_anime` | hard panel line, mechanical rendering | *"Rendered a giant robot into the frame. That is a subject, not a style."* |

### The shape of the failure

Wave two of the library was authored specifically to test this, and it found the failure has
a very consistent form. From `studio/_tools/style_verdicts2.py`:

> THE OBJECT ENDS UP IN THE SUBJECT'S HANDS. graffiti gave her a spray can. airbrush_70s
> gave her an airbrush. pulp_cover gave her a paperback. persian_miniature gave her a
> golden tray. cassette_futurism surrounded her with CRT monitors. tattoo_flash drew
> tattoos on her face.
>
> That is a usable authoring rule: if the style's name is a thing a person could hold, the
> model will hand it to them.

### The controlled experiment

`pulp_cover` deserves attention because it was designed as a test rather than as a style.
`retro_scifi_paperback` had already failed by drawing a starship and a gas giant, and the
natural hypothesis was that the *description* was too full of genre furniture. So
`pulp_cover` was written to name **no** genre furniture at all — only the painting quality.
Its verdict:

> Gave her a paperback book to hold. The card deliberately named no genre furniture in
> order to test whether that was what broke retro_scifi_paperback - it was not.
> **The noun in the NAME is enough.**

That is the finding. Cleaning up the description does not save the card. The card's own
identifier is in the prompt path and it is sufficient on its own.

### THE AUTHORING RULE

> **If the style's name is a thing a person could hold, do not write that card.**

No amount of careful `means`/`tags`/`prose` writing rescues it. Write the idiom under a
name that is not an object, or do not write it.

### Where the boundary actually is

Not every noun injects. The rule is sharper than "avoid nouns", and the difference was
measured too. A noun that has somewhere legitimate to **attach** — a garment, a wall, a
building — attaches there and composes fine. A noun that is *portable* gets handed to the
subject.

| Card | Verdict | Why it survived |
|---|---|---|
| `steampunk` | *"Brass and oxidised copper, gaslight, riveted plate - and the goggles landed on her belt as costume rather than as a floating prop, which is the distinction that separates a wearable noun from an injected one."* | goggles are **wearable** |
| `y2k_chrome` | *"Iridescent holographic coat and blue-white flare. The chrome landed on the GARMENT, which keeps it composable."* | chrome is a **surface** |
| `dark_academia` | *"It did add a lantern, but as scenery rather than in her hands."* | a lantern belongs to the **room** |
| `eldritch` | *"Red tendril forms and light falling wrong, with no creature drawn - the card deliberately named none and that worked."* | the card **named no creature** |

`eldritch` is the positive control for the whole rule: it is a genre that is *usually*
defined by its monsters, the card deliberately refused to name one, and it came back as an
idiom rather than as a subject.

### The second failure hiding inside `injects`: shot-property impostors

Some cards marked `injects` do not draw a prop at all — they seize a slot that belongs to a
different layer. These are worse than prop injectors in one way: they look like they are
working.

| Card | Verdict |
|---|---|
| `drone_aerial` | *"Did NOT move the camera up. Still eye level, just a longer street. An aerial is a camera position - a shot property, not a style."* |
| `tilt_shift` | *"Produced blur bands top and bottom but also broke the framing, squeezing the subject into a letterboxed strip. The viewpoint never moved - the same failure as drone_aerial, because viewpoint is a shot property."* |
| `american_comic` | *"Heavy varied ink and saturated primaries - but it rewrote her pose into a dynamic action stance."* |
| `chibi` | *"Head-to-body proportion collapses to roughly 1:2. Note it also forces a wider framing - a chibi cannot be a mid-shot."* |

**Rule:** if the request is about *where the camera is*, *how the frame is cropped*, or
*what the subject's body is doing*, it is not a style. It belongs in the shot template, the
camera field, or the shot description. A style that quietly rewrites your blocking has
broken continuity across every shot in the film and you will not find out until the cut.

### And a third: the overlay

A handful of qwen cards render the style *on top of* an untouched photograph rather than
rendering the photograph in that style:

- `papercut_collage` — *"Drew torn-paper layers as a FRAME around an unmodified photograph."*
- `technical_diagram` — *"Drew a floating exploded-view diagram beside an untouched photo."*
- `thermal_imaging` — *"Recoloured her coat and scarf into a rainbow gradient and left the street a normal photograph. It painted the ramp onto an object instead of remapping the image."*
- `screenprint_poster` — *"Produced garbled poster lettering over a photo. Neither engine screenprints, and both hallucinate text."*

This is the noun rule again at one remove: the model understands "papercut collage" as a
*thing that can be in a picture*, not as *how a picture is made*.

---

## 5. The `compose` taxonomy

`compose` is the field that answers: **what happens to my other layers when I stack this
style on top of them?** It was assigned per card, from pixels, after rendering. It is not
derived from the family or the description, and it must be trusted over any heuristic —
`art_deco`'s verdict explicitly records that it did *not* build an enclosing frame the way
`art_nouveau` did, "so it composes", even though the two are neighbours in every other
respect.

Distribution across the 131 cards (130 styles plus `_control`, which has no `compose`):

| `compose` | count | `ready` | `weak` | `unavailable` |
|---|---|---|---|---|
| `safe` | 86 | 74 | 12 | 0 |
| `replaces` | 16 | **16** | 0 | 0 |
| `injects` | 20 | 2 | 8 | 10 |
| `inert` | 8 | 0 | 5 | 3 |

Note the second row. **Every `replaces` card is `ready`.** That is what makes them
dangerous — they are good cards, and they will quietly delete work you did in another layer.

### `safe` — 86 cards

Re-renders the same scene in a new idiom. Your place, your character, your look and your
wear all survive. This is what a style is supposed to do, and two thirds of the library
does it.

> `cel_anime_90s`: *"Heavier uneven line, duller warm palette, hard flat shadow. Reads
> unmistakably as a 90s OVA cel beside the control."*
>
> `expressionism`: *"Harsh angular line, crushed value, skewed space. Distinct from
> gothic_illustration."*

Stack freely. The only remaining constraint is the grade (§1) and the engine (§3).

### `replaces` — 16 cards

Re-renders the scene **and overrides the setting**. The style is strong enough that it
brings its own world with it, and your `place` card loses.

> `shojo_soft`: *"Sparkle, pastel, glazed eyes - and it replaced the street with a field of
> flowers. Very strong at 81.4, but it overwrites any place you choose."*
>
> `ghibli_pastoral`: *"Painted skies and warm village architecture, but it REPLACED the
> city street with a village lane. Do not stack on a place card."*
>
> `solarpunk`: *"Greenery, planters and bright clean daylight took over the street. Strong,
> but it rebuilds the setting."*
>
> `wasteland`: *"Ruined overgrown structures and dust haze. Convincing, but it rebuilds the
> location."*
>
> `brutalist`: *"Massive raw concrete under flat grey light. As the card predicted, it is
> an architecture card and it rebuilds the location."*
>
> `wuxia`: *"Flowing silk, jade, Chinese architecture. Strong, and it replaces the setting."*

**This is not a defect.** Two of them say so in as many words:

> `byzantine_icon`: *"Flat gold ground, halo, hieratic frontality. The gold ground deletes
> the setting by design, so compose=replaces is correct behaviour here rather than a
> fault."*
>
> `monogatari_geometric`: *"Replaced the background with flat geometric colour fields. That
> is the card working as designed, not failing."*

**How to use them:** pick a `replaces` style **or** pick a place, not both. If a tool warns
you here, the right wording is *"this style owns the background"*, never *"this style is
broken"*.

There is a sub-case worth naming separately. Two cards do not replace the setting with
another setting — they replace it with **decoration**:

> `art_nouveau`: *"Mucha ornament, gold line, flat decorative ground - it replaced the
> street with an ornamental arch. Beautiful, but it is a frame, not a lens."*
>
> `illuminated_manuscript`: *"Gold leaf and vermilion - drawn as an ornamental ring
> enclosing the figure."*

And two more shatter it rather than replace it, which is fatal to any establishing shot:

> `shonen_action`: *"Hard black line and speed fragments; it shattered the background into
> abstract shards. Style and setting cannot both survive this one."*
>
> `trigger_kinetic`: *"Thick tapering line, extreme perspective, red motion ribbons - and it
> broke up the background."*

### `injects` — 20 cards

The noun in the style's **name** becomes an object in the frame instead of an idiom applied
to it. Fully covered in §4. These **corrupt any scene they touch**: the prop is not in your
shot description, so it appears in one shot and not the next, and continuity is gone.

Only 2 of the 20 are `ready`, and both come with a caveat:

> `arcane_magitech`: *"Teal rune-glow and crystal - the idiom lands, but it also spawned
> floating crystals as props. Usable if you want them; disruptive if you do not."*
>
> `american_comic`: *"...but it rewrote her pose into a dynamic action stance."*

The other 18 are `weak` or `unavailable`. Treat `injects` as a warning label, not a feature.

### `inert` — 8 cards

No visible change from the control. **Not one of the eight is `ready`.**

> `comic_halftone`: *"On qwen a plain photo; on the illustration engine ordinary anime with
> no dot screen. Use manga_screentone, which actually produces tone."*
>
> `stop_motion_felt`: *"No felt fibre, no armature, no stop-motion staging on either engine.
> Ordinary anime."*
>
> `risograph`: *"On qwen it drew a riso-coloured rectangle over the photo; on the
> illustration engine, nothing. Misregistration and spot ink are print artifacts neither
> model has."*
>
> `unreal_render`: *"An ordinary photograph on qwen and ordinary clean anime on the
> illustration engine. The 'unreal engine' token acted as a generic quality booster rather
> than a style, which is precisely the risk the card flagged."*
>
> `constructivist`: *"Muted, with a diagonal scarf and nothing else. No red-black agitprop
> palette, no heroic angle."*
>
> `atompunk`: *"Came back as generic neon city, indistinguishable from cyberpunk_neon. The
> turquoise landed, the 1950s did not."*

The library exists to make these findable *before* you spend the render. This project's
standing doctrine is that a knob which quietly does nothing is worse than no knob, and
`inert` is the purest instance of it.

**One `inert` card is repairable and should not be blanket-rejected:**

> `matte_painting`: *"Came back broken: horizontal banding and a doubled figure. This is
> the above-2MP composition-duplication failure the qwen checkpoint card documents,
> triggered by the style's own wide-vista prose."*

That is a resolution problem, not a style problem. Generate at 1–2 MP and upscale. See §6.5.

### Two fields, easily confused

`compose` and `status` answer different questions, and so do `status` and `strength`:

- **`compose`** — how it behaves *stacked with other layers*. safe / replaces / injects / inert.
- **`status`** — how well it works *at all*, judged from the render. ready (93) / weak (25) / unavailable (13).
- **`strength`** — how *loud* the idiom is by design. strong (33) / moderate (83) / weak (14) / n/a (1).

`status: weak` means "we rendered it and it barely did anything". `strength: weak` means
"this idiom is subtle on purpose". The two sets overlap and neither contains the other.
Any tool that warns on one of them and calls it the other is warning about the wrong thing.

---

## 6. Cross-layer constraints

### 6.1 A character LoRA does nothing on the qwen path

**This is the most expensive constraint in the project.**

A LoRA (Low-Rank Adaptation) is a small set of correction matrices *added to a frozen base
model's weights at load time*. From `LORAS.md`:

> Because it is *added* to the base, a LoRA is welded to the base model it was trained on:
> **a Qwen-Image LoRA does nothing on Flux, SDXL, or Wan.** Not "worse" — nothing, or
> noise. Check the base model before you download, always.

The cast's trained LoRAs are deltas on **animagine** weights. `VIRO` carries
`character_viro_00001_.safetensors` — rank 16, 1000 steps, 16 images, trained 2026-08-03.
There is no arrangement under which that file means anything to Qwen-Image. It is not a
compatibility bug to be fixed; it is what a LoRA is.

`studio/_tools/character_demo.py` already encodes it and says so out loud:

```python
lora = None if (a.no_lora or a.engine == "qwen") else card.get("lora")
if a.engine == "qwen" and card.get("lora"):
    print("note: the LoRA is NOT applied on the qwen path - it is a delta on "
          "animagine weights. This pass tests the written description alone.")
```

**What this means when you pick a style.** Choosing a qwen-routed style — `brutalist`,
`cyanotype`, `noir_comic`, `western_frontier`, any of the 42 — discards your character
LoRA. Identity then falls back to reference sheets driven through Qwen-Edit, which the
compiler itself describes as *a weaker lock: expect more drift between shots*. Your
character will look approximately like themselves rather than exactly like themselves, and
the difference accumulates across a film.

The trap is that **nothing fails**. No crash, no error, no missing file. You get a complete
film in which the person is subtly a different person in each shot.

> **Rule.** If the film has a LoRA-bearing character whose face must hold across shots, the
> style must route to `anime`. That is a style decision taken for a character reason — the
> clearest possible demonstration of why style is the outermost layer.

And the worse case: a character with a LoRA **and no reference sheet** on the qwen path has
*no identity mechanism at all*. `MANAGER` currently has `"sheet": ""`. On the anime path a
missing sheet degrades gracefully (the IPAdapter weight drops to 0.0 and you get a generic
face). On the qwen path there is nothing to degrade to.

### 6.2 The grade runs last and always wins

Covered in §1. Restated as a constraint:

- A **desaturating** look destroys a style whose identity is colour. `looks/noir` sets
  saturation to exactly 0.000. `byzantine_icon`'s whole point is a gold ground;
  `cyberpunk_neon`'s is saturated signage; `illuminated_manuscript`'s is gold leaf and
  vermilion. Under `noir` all three become grey.
- A **saturation-boosting** look is a silent no-op on a monochrome style. `manga_inked`,
  `charcoal_drawing`, `cyanotype`, `woodcut`, `street_bw` have no chroma to boost. You
  believe you applied a warm look; nothing happened.
- A **high-contrast** look crushes a high-key style. `watercolour` says it explicitly:
  noir at contrast 1.32 and night at 1.20 turn the washes to mud.

Each style card carries a `suits_looks` array naming the looks it was checked against. It
is an endorsement list, not a whitelist — cards average about three entries out of
twenty-five looks, so "not listed" means "nobody checked", not "known bad". Do not treat
absence as a failure.

### 6.3 Looks carry prompt tags, and some of those tags name places

This one is easy to miss and it silently overwrites work. Eight of the 25 looks put a
**place noun** into the prompt:

```
neon         "neon lights, night, city street, cyberpunk, glowing sign, wet pavement, ..."
sodium       "night, street light, lamppost, orange glow, city street, dark"
hospital     "hospital, white room, sterile, clean, bright lighting, indoors"
fluorescent  "fluorescent lighting, ceiling light, indoors, harsh lighting, pale skin, office"
underwater   "underwater, submerged, bubbles, light rays, water, blue"
firelight    "campfire, fire, warm lighting, orange glow, dark background, ..."
day_for_night "night, floodlights"
blockbuster  "cinematic lighting, backlighting, dramatic shadow, lens flare, orange sky"
```

So `look: neon` is not only a colour grade — it also asks for a wet city street. Combine it
with `place: locker_room` and two layers are claiming the background.

**The tag order decides who wins, and at the time of writing it decides wrong.** The tag
stack in `studio/compile.py` currently assembles as:

```python
bits += [v["tags"], look["tags"], v["mood"], v["place"], v["time"], Q]
```

`look["tags"]` sits **before** `v["place"]`. In this project, earlier and more specific
wins — that ordering fact is itself measured, and painfully:

> With the jersey described as pristine in `tags` and the damage appended afterwards as
> "torn bloodied uniform", `wear: 4` rendered a **completely clean uniform** — the model
> resolves the contradiction in favour of the earlier, more specific description.
> (`studio/characters/VIRO.json`, verified 2026-08-03)

So `look: neon` + `place: locker_room` gets you a wet neon street. This is live, and it is
being worked on in `compile.py` in parallel with this document — **re-grep the assembly
line before relying on the order above.** The principle does not change: place should
precede look, so the deterministic grade owns the colour and the prompt half is only a
nudge.

### 6.4 `negative_add` reaches nothing on the render path

Every style card carries a `negative_add` field — `graffiti`'s is
`"clean, smooth, delicate, painterly"`. As of this writing the **only** consumer of that
field in the whole repository is `studio/_tools/style_examples.py`, the tool that rendered
the sample images you browse in the library.

`scripts/short.py` never sets a negative prompt on either keyframe path.

The consequence is uncomfortable and worth stating plainly: **every sample image in the
styles library was rendered with the style's negative applied, and every actual film
renders without it.** The library's own evidence is not quite what the pipeline produces.
`propaganda_poster`'s verdict measures the size of the gap:

> Red and black with a hard diagonal, but mostly ordinary anime underneath. **The text
> negative did at least prevent the garbled lettering** that killed screenprint_poster.

That protection is absent in a real render. Wiring the negative chain is outstanding work.

### 6.5 Qwen-specific ceilings

From `studio/checkpoints/qwen_image_2512.json`:

- **Negatives are nearly ignored on the fast path.** *"with the 4-step Lightning LoRA it
  runs at cfg 1.0 in ~4.5s, and AT THAT SETTING THE NEGATIVE PROMPT IS NEARLY IGNORED -
  inherent to CFG-distilled models. Negatives only bite if you drop the LoRA and run 20
  steps at cfg 2.5-4.0."* The cost of switching is roughly 4.5 s → 20 s+ per keyframe.
- **Composition duplicates above ~2 MP.** *"past about 2 MP it duplicates composition (two
  horizons, repeated subjects), so generate at 1-2 MP and upscale 4x."* The defaults are
  both under (anime 1344×768 = 1.03 MP, qwen 1664×928 = 1.54 MP), so this only fires on an
  override — but it is exactly what killed `matte_painting`.

### 6.6 Video: a style that survives as a still can boil in motion

A keyframe is not a clip. Fine, high-frequency texture is the failure class: the i2v pass
resamples every frame and there is nothing holding the texture in place, so it crawls.

Cards flagged **not viable** for video in their `works_for` text include `cubism` (*"the
fracture pattern will reshuffle every frame"*), `double_exposure` (*"the two layers will
drift independently"*), `pointillism` (*"a dot field is the worst case for temporal
stability"*), `risograph` (*"the doubled edges will strobe"*), and `stop_motion_felt`.
`pixel_art` is the worst of all: *"LTX-2.3 resamples every frame, a pixel grid is the
highest-frequency structure you can hand it... expect the grid to shimmer apart within a
second."*

Safest in motion: flat, hard-edged, low-frequency idioms — `webtoon_flat`, `chibi`,
`flat_vector`, `noir_comic`, `voxel` (*"hard-edged blocks are stable"*), `iyashikei`
(*"calm and static, very stable"*).

**Read the honesty marker.** Most of these `works_for` strings contain the literal words
**"INFERRED, not measured"**. No LTX sweep has been run across the style library. This is
the project's working prior, not a finding, and any tool surfacing these warnings must
carry that word through — it is the difference between this section and §3, and the whole
epistemics of this repo rest on it.

The reason to care is cost. Wall clock derived from the delivered 216-beat render's file
mtimes: keyframes **4.1 s/beat**, clips **32.1 s/beat** at `clip_secs=6`. Catching a style
that boils at keyframe time is about eight times cheaper than catching it at clip time.

---

## 7. What we got wrong

This section exists because the errors were systematic, not careless, and the same shape of
error is easy to repeat.

### 7.1 We shipped confidence as if it were measurement

The first wave of the styles library was 64 cards. **46 of them shipped marked `ready`
without a single render ever having been made.** Every `status`, `strength` and `engine`
value on them was a considered prediction written from documented model behaviour by
someone who knew the material well.

`style_examples.py` — the tool built to fix this — states the problem in its own docstring:

> THE WHOLE LIBRARY SHIPPED `untested`. 64 cards were authored without a single render, and
> every strength rating on them is a prediction from documented behaviour. This is the tool
> that turns them into findings. **Until it has run on a card, that card is someone's
> opinion.**

The project's own standard, written on the Illustrious checkpoint card before any of this
happened, is one sentence: **a recommendation is not a measurement.** It was written down
and then not followed.

### 7.2 Twenty-seven of sixty-four were routed to the wrong engine

When the renders were finally made — every card on **both** engines, against a no-style
control at the same seed with the same subject — **27 of the 64 first-wave cards had their
`engine` field rewritten from the pixels.**

That is 42% of the library pointing at a model that could not render it. The single most
damaging case is the one that turned out to be the best card in the set:

> `watercolour`: *"Paper bleed and pigment pooling. Strongest measured result in the set,
> 92.1 from control. **This card was authored engine=qwen, where it produced a plain
> photograph and did nothing.**"*

The root cause was a reasonable-sounding assumption — that a photographic model with a
strong text encoder could be talked into painting. §3 records the test that killed it.

### 7.3 Four specific predictions were refuted by rendering

Wave two wrote its predictions into the cards *before* rendering, which is why we can score
them. From `style_verdicts2.py`:

**`pixel_art` — called impossible without a post-process. It works directly.**

The card argued at length that this was a resolution problem no prompt could fix, and
specified an ffmpeg nearest-neighbour quantise pass as "the piece of work this card is
really asking for". Then:

> Convincing pixel grid and clamped palette. **The authoring agent concluded neither engine
> could produce a pixel grid and that the card needed a post-process instead - that was
> wrong, animagine does it directly.**

**`cubism` — called weak because models will not abstract a face. The background fractures.**

> The card's note: *"Both models resist abstracting faces. Predicted to produce a lightly
> angular portrait rather than genuine cubism."*
>
> The verdict: *"The **BACKGROUND** fractured into genuine faceted planes while the face
> stayed intact. Marked weak before rendering; that was too pessimistic and is corrected
> here."*

The premise was correct — the face *did* stay intact — and the conclusion drawn from it was
wrong, because the prediction only considered the face.

**`iyashikei` — called weak because "peaceful" is a quality. It lands.**

> The card's note: *"Honest expectation: WEAK. 'Peaceful' is a quality, not a thing, and
> this project has repeatedly measured that qualities do not render. The palette clause is
> the only part likely to land."*
>
> The verdict: *"Quiet wide composition, soft muted greens, nothing tense. Marked weak
> before rendering on the grounds that 'peaceful' is a quality - **the palette clause
> carried it further than expected.** Prediction corrected."*

This one is instructive because the reasoning invoked the project's own governing rule —
correctly — and still landed wrong. The rule says qualities do not render. It does not say
a card built mostly of concrete clauses fails because one of its clauses is a quality.

**`voxel` — guessed onto qwen. It needs the illustration engine.**

> A full cube-built construction on the illustration engine. Guessed onto qwen, where it
> produced only a small pixelated patch on one cheek - re-routed on the evidence.

### 7.4 In fairness: prediction is not worthless

The same wave got a lot right, and said so in advance:

> **right** — graffiti, tattoo_flash, cassette_futurism and space_opera all injected props
> exactly as their notes predicted
> **right** — surrealism and constructivist came back thin, as flagged

`graffiti`'s note before rendering read *"PREDICTED NOUN RISK: high"* and its verdict reads
*"The card rated this the highest noun risk in the batch and it was right."* `tattoo_flash`
predicted tattoos would be drawn on the subject; they were, on both engines.

The lesson is not "stop predicting". Prediction is how you decide **what to render first**.
The lesson is narrower and it is about a field name: **`status` must mean "rendered and
looked at", and never "authored confidently".** Wave two encoded that by shipping every
card as `untested` regardless of how sure the author was.

### 7.5 The method that finally worked

Recorded because it is not obvious and it was arrived at after a much worse first attempt:

- **One subject, one seed, one setting, for every card. Only the style changes.** From
  `style_examples.py`: *"That is the entire discipline here and this project has broken it
  repeatedly — 133 of 134 capability cards varied the subject alongside the variable and so
  demonstrated nothing. A grid where each cell has a different person in a different place
  cannot tell you what a style does."*
- **A control panel.** `styles/_control.json` is the same subject and seed with no style
  applied. Its note: *"If a style example is indistinguishable from this one, the style did
  nothing and its card is wrong."* That is the definition of `compose: inert`.
- **A subject chosen to expose style rather than flatter it** — a face (where idiom shows
  first), a garment with folds (where line and shading show), and a receding street (where
  depth and palette show). *"A landscape would hide all three."*
- **Both engines, every card**, because engine was the field most often wrong.
- **A human looks.** Every `verdict` in the library ends with
  `verified_by: "Looked at, against the no-style control at the same seed with the same
  subject, on both engines."`

Some verdicts carry a number — `watercolour` 92.1, `ink_wash` 89.4, `shojo_soft` 81.4,
`seinen_grounded` 20.6, `photorealistic` 21.0. That is mean pixel difference from the
control, and it is a useful sanity check but not the verdict itself: `photorealistic` sits
close to the control *"because qwen's baseline IS photographic — that is agreement, not
failure"*, and `cyberpunk_neon` scores a low 17.3 on the illustration engine while being
correct on the other one. The number tells you *whether something changed*, never *whether
it was the right thing*. Only looking does that. (`studio/_tools/panel_diff.py` implements
the same metric for capability cards, with 8.0 as "same picture" and 6.0 as "inert
variable"; the style-library figures were computed ad hoc and there is no re-runnable tool
that reproduces them.)

---

## 8. Writing a new style card

Checklist, derived from everything above.

1. **Is the name an object a person could hold?** If yes, stop. Rename it to the idiom or
   do not write it. (§4)
2. **Is it actually a shot property?** Camera position, crop, pose, motion — those belong to
   the shot, the camera field or the shot description. Not here. (§4)
3. **Describe line, palette, surface, edge and light.** Not subject matter, not genre
   furniture. `eldritch` is the model: name the treatment, name no creature.
4. **Write both dialects.** `tags` in danbooru for the illustration engine, `prose` in
   sentences for qwen. They are the same idea in two languages.
5. **Set `engine` as a hypothesis and say so in the note.** It will be rewritten from the
   pixels. Historically 42% of guesses were wrong.
6. **Ship it `status: untested`.** However sure you are. This is the rule the first wave
   broke.
7. **Render it on both engines** against `_control` at the same seed with the same subject:
   `python3 studio/_tools/style_examples.py <id> --all-engines`
8. **Look at it.** Then write `compose`, `status` and `verdict` describing *what you saw*,
   not what you hoped. Quote the failure if it failed — the verdicts that name their own
   refuted predictions are the most useful text in the library.

Fields on a style card: `id, name, family, engine, means, tags, prose, negative_add,
suits_looks, strength, works_for, status, note, examples, compose, verdict, verified_by`.

---

## 9. Quick reference

**Decide in this order.** Style → engine → everything else.

**Before you render, check:**

| Question | Where to look | If bad |
|---|---|---|
| Does the style route to the engine I want? | `engine` | The engine is not negotiable by prompt. Change the style. (§3) |
| Has it actually been rendered? | `status` = ready / weak / unavailable | `unavailable` means the engine cannot do this. Read the `verdict` for why. (§5) |
| Will it survive my other layers? | `compose` | `replaces` deletes your place. `injects` corrupts the frame. `inert` does nothing. (§5) |
| Does my character have a LoRA? | `character.lora` | Then the style must be `engine: anime`. (§6.1) |
| Will my look's grade kill it? | `looks/<id>.grade` | A desaturating grade beats any colour style, always. (§6.2) |
| Does my look's *tags* half claim my place? | `looks/<id>.tags` | Eight looks name a place noun. (§6.3) |
| Am I cutting this into video? | `works_for` | Fine texture boils. Mostly INFERRED, not measured. (§6.6) |

**Things that are true and stay true:**

- The model renders nouns, not adjectives.
- Qwen cannot be steered off photography by prompt at any cfg.
- The engine named "anime" is the general illustration engine.
- A LoRA is welded to the base it was trained on.
- The grade runs last, so the grade wins.
- Earlier and more specific wins in the tag stack.
- A recommendation is not a measurement.
