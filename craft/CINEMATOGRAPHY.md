# Cinematography — the image, and how to make Qwen give you the one you asked for

Written after auditing all 109 rendered keyframes of CHRONO TRIGGER against their prompts,
plus the 23 of THE HOLLOW CHOIR and 18 of THE LAST GOOD YEAR as controls. Every claim below
cites a real shot id you can go and look at:

```
Z:/ComfyUI/output/claude-generated/11-short-film/<slug>/keyframes/<shot_id>_00001_.png
# or, when the share lags:
http://192.168.1.46:8188/view?filename=<shot_id>_00001_.png&subfolder=claude-generated/11-short-film/<slug>/keyframes&type=output
```

Sibling docs: `STORY.md` (what the film says), `EDITING.md` (how it cuts). This one is the
frame.

---

## 0. Review method — do this before you animate anything

A bad keyframe costs 4.5 s as a still and ~16 s as a clip. A bad keyframe you *didn't
notice* costs the film. Contact-sheet everything, and look at it at a size where you can
actually see a face.

```bash
# 1. downscale + label (ffmpeg here has no -pattern_type glob; sequential names only,
#    and a gap in the numbering silently truncates the sequence)
i=0; for f in $(ls *.png | sort); do i=$((i+1)); n=$(printf "%03d" $i)
  ffmpeg -y -loglevel error -i "$f" -vf \
    "scale=700:-1,drawtext=fontfile='C\:/Windows/Fonts/arialbd.ttf':text='$n ${f%_00001_.png}':x=6:y=6:fontsize=30:fontcolor=yellow:box=1:boxcolor=black@0.8:boxborderw=6" \
    lab/$n.png </dev/null
done
# 2. tile in small batches
ffmpeg -y -i lab/%03d.png -vf tile=3x3:padding=6:color=white -frames:v 1 sheet.png
```

**3x3 at 700 px per tile is the sweet spot.** 4x3 at 560 is too small to judge a face,
which is exactly the thing that drifts. 109 shots is 19 sheets of 6 or 13 sheets of 9 —
half an hour of looking, and it is the highest-leverage half hour in the whole production.

Then build **per-character strips** — every appearance of one character tiled together.
Costume drift is invisible shot-by-shot and screams when nine appearances sit side by side.
This is how `250_dungeon` (no blue gi at all) and `540_magus_fight` (two katanas) were found.

---

## 1. Writing a Qwen keyframe prompt that lands

`PROMPTING.md` covers the model's basics: write sentences, spatial language works,
photographic vocabulary lands, negatives are near-dead at cfg 1.0. This section is the
failure modes that only show up when you write a hundred prompts in one film.

### 1.1 The single biggest lever is not words — it's steps

`epic.py` renders **every** keyframe with `13_qwen_t2i_styled.json`: 4 steps, cfg 1.0,
shift 3.1. Four steps has *very* little prompt adherence, and `FILMMAKING.md` already
records this from PUDDLE ("4 steps has far too little prompt adherence to resist a strong
style block"). CHRONO paid the same bill: roughly **30 of 109 shots** missed something the
prompt explicitly asked for.

`cartoon.py` has the escape hatch — `"quality": true` per shot swaps in the 20-step path.
**`epic.py` does not.** Adding it is the most valuable change you can make to this pipeline.

**Do not do it by loading `02_qwen_t2i_quality.json`** the way `cartoon.py` does — that
workflow has no style LoRA, so your 20-step shots would come back in a visibly different
style from the other hundred. Instead, drive the 20-step path *through* `13_qwen_t2i_styled`
by switching off the Lightning LoRA in place (node 4) and raising steps and cfg on the
sampler (node 13):

```python
# scripts/epic.py, in keyframes(), after the style-LoRA block
if s.get("quality"):
    set_path(wf, "4.inputs.strength_model", 0.0)   # bypass Lightning
    set_path(wf, "13.inputs.steps", 20)
    set_path(wf, "13.inputs.cfg", 2.5)
```

Two useful side effects: at cfg 2.5 the **negative prompt comes back to life**, so
`NEG_IMG`'s `photorealistic, photograph, 3d render` starts working and you can add per-shot
negatives for the PUDDLE-style "not the default pose" problem; and prompt adherence to
staged action jumps, which is the whole point.

Budget it: 20 steps costs 30 s instead of 4.5 s. Flagging **25 shots** in a 109-shot film
as `quality: true` costs ~11 extra minutes of GPU. That is nothing, and it buys back most of
the off-brief rate.

The middle option, when a shot is only mildly off: `PROMPTING.md`'s knob for "composition
ignores the prompt" is `ModelSamplingAuraFlow.shift` **3.1 → 4.5** (node 5). Costs nothing,
stays at 4 steps, and is worth trying first on the palette-and-scale misses.

**Which shots need it.** Not the establishing wides — `660_zeal`, `700_descent`,
`460_forest`, `920_lanterns` all landed perfectly at 4 steps because a landscape has no
staging to get wrong. The ones that need 20 steps are shots with a **specific staged
physical relationship**: someone seizing someone, a door coming off its hinges, a sword
broken in two pieces, a body dissolving, a machine tearing an arm off. Every one of CHRONO's
worst misses is of that kind.

### 1.2 The seed is deterministic per shot index — you cannot re-roll by deleting

`epic.py` uses `seed = seed0 + i * 7`. Delete a keyframe, re-run `--stage keyframes`, and
you get **byte-identical output**. The only ways to change a shot are to change its prompt
text, to shift `--seed` (which moves every missing shot), or to add per-shot seed support:

```python
set_path(wf, "13.inputs.seed", int(s.get("seed", seed0 + i * 7)))
```

Add it. Until you do, "re-roll shot 45" is not an operation that exists, and every fix has
to be a rewrite — which is fine, because most of them should be rewrites anyway.

### 1.3 Never use a simile the model can render literally

`720_rising` asked for "tiny figures scattered **like insects** before it". The floor of the
finished frame is covered in **actual beetles**. Twenty of them, drawn with legs.

Qwen2.5-VL is a language model reading a description of a picture. It does not know which
of your nouns are the subject and which are rhetoric. Every figurative noun is a candidate
object.

| Don't write | Write |
|---|---|
| figures scattered like insects | seven human figures, each no taller than one of its claws |
| a sky the texture of old paper | a flat, grainy, colourless overcast sky |
| bones of the city | roofless concrete shells |
| a wave of guards drops to one knee | guards kneeling in a curve around her |

Same class of error, different mechanism: `360_burning` asked for "a continent burning from
above" and got a recognisable **map of Europe and North Africa**. If your world isn't Earth,
say "an unnamed continent" or describe the coastline you want.

### 1.4 Attribute bleed: in a two-character prompt, props migrate

`040_collide` reads:

> Medium two-shot in a sunlit fairground lane as {CRONO} and {MARLE} collide and she falls,
> **her blue teardrop pendant swinging bright at her throat**

In the rendered frame the pendant is **around Crono's neck.** Zoom in and it's unambiguous.

Both character blocks were substituted into one sentence, so the encoder saw two people and
one pendant and attached it to the nearer, larger, more strongly described subject. This is
the general case: **in a multi-character prompt, any attribute not welded to a name drifts to
the dominant character.**

Three defences, in order of effect:

1. **One sentence per character.** Full stop between them. `{CRONO} does X. {MARLE} does Y.`
2. **Repeat the name inside the attribute clause** — "Marle's own pendant, at Marle's
   throat" is ugly prose and correct prompting.
3. **Give each character a distinct spatial anchor** — "on the left of frame", "in the lower
   right". Qwen's spatial language is genuinely good; use it to fence characters off from
   each other.

### 1.5 State the negative space positively

At cfg 1.0 the negative prompt is nearly inert, and `epic.py`'s `NEG_IMG` is global anyway.
So "no green anywhere" and "not a single bird or cloud shape" have to be *positive*
descriptions of what IS there, or they do nothing at all:

- `290_era2300` asked for "cracked concrete plains … **no green anywhere**" → delivered a
  ruined city carpeted in trees and shrubs under a blue sky with white clouds.
- `300_deadsky` asked for "a colourless overcast sky … **not a single bird or cloud shape**"
  → delivered a blue sky full of white clouds. The narration over it is *"The sky is dead."*

Rewrite as presence, not absence: "every surface bare grey concrete and rust, dry dust
drifted into the corners, the sky one flat unbroken sheet of pale grey with no visible sun
and no cloud edges." That the model can draw.

### 1.6 Worked before/after, from this film

**`290_era2300` — the apocalypse that came back sunny.**

> Before: `Devastating wide establishing shot of a ruined future city under a dead grey sky,
> snapped skyscrapers, collapsed elevated roads, cracked concrete plains to the horizon,
> rusted geodesic domes, no green anywhere`
>
> After: `Wide establishing shot of a dead city, every building a roofless grey concrete
> shell snapped off partway up, an elevated roadway collapsed into the street below, the
> ground bare cracked concrete and drifted grey dust to the horizon, two rusted geodesic
> domes in the middle distance. The sky is one flat unbroken sheet of pale ash grey, no sun,
> no cloud edges, no blue. Everything is grey, brown and rust. Nothing is growing. 35mm,
> desaturated, high haze, low contrast.`

Three changes doing the work: absences converted to presences; the palette named three times
in different words; "flat unbroken sheet" replacing the metaphor.

**`720_rising` — the beetles.**

> Before: `… its enormous spined shell filling the whole chamber, red core blazing, tiny
> figures scattered like insects before it`
>
> After: `… its enormous spined shell filling the frame from edge to edge, red core blazing
> at its centre. In the lower third, seven human figures thrown backwards across a shattered
> marble floor, each one no taller than a single one of the creature's claws. Water pouring
> in through cracks in the ceiling, blue-green light from above.`

**`580_ayla` — the woman who came back a bodybuilder.** See §2.5.

**`830_party` — the hero line-up nobody in it is in.** The prompt re-described all seven
characters in generic terms ("a red haired swordsman, a blonde girl with a crossbow, an
inventor girl with glasses…") instead of using `{CRONO}` `{MARLE}` `{LUCCA}` `{FROG}`
`{ROBO}` `{AYLA}` `{MAGUS}`. It got seven generic characters — a brown-haired ranger, a
plate-armour knight, a silver mech. **If a shot contains a recurring character, it must use
the placeholder.** No exceptions, no paraphrases, ever. The one place paraphrase is correct
is a wide where the character should be a speck — and there you omit the description
entirely (`FILMMAKING.md` on PUDDLE).

### 1.7 Prompt-shape rules that held up across 109 shots

- **Lead with camera and staging, put the character block last.** Confirmed again here: the
  shots where `{CRONO}` lands early (`030_crono`, `070_teleport`) came back as him standing
  in a hero pose regardless of what the sentence asked him to be doing. `FILMMAKING.md` found
  this on PUDDLE; it generalises.
- **Name the shot scale in the first three words and mean it.** `450_planting` opened "Wide
  melancholy shot of {ROBO} alone on a vast barren hillside" and delivered a *medium* — Robo
  fills half the frame. The character description outweighed the word "wide". If you want
  small, say how small: "Robo no more than one tenth of the frame height, on the horizon".
- **One sky per prompt, stated explicitly.** Every shot that didn't specify its sky got the
  LoRA's default (see §4). `670_machine` is set inside an undersea palace and has an orange
  sunset visible through its arches.
- **Don't ask for a state the frame can't hold.** "Dissolving into streaks of energy"
  (`070_teleport`) and "becoming translucent, dissolving into motes" (`150_fading`) both came
  back as solid, opaque, combat-ready characters. Qwen renders *people*; partial
  dematerialisation is a lighting/compositing idea. Stage it instead: shoot the character
  already half-gone, from the waist up only, with the lower half of the frame already just
  drifting light — describe the *picture*, not the *process*.
- **Photographic vocabulary is still your cheapest lever.** The shots with an explicit lens
  or light direction all landed: `700_descent` ("shafts of filtered light"),
  `740_death` ("everything else blasted to pure white light"), `920_lanterns`. The shots
  without one drifted to the model's default three-quarter mid-shot.

---

## 2. Character consistency — the playbook

### 2.1 The old trick, and why it works

THE HOLLOW CHOIR cast a **helmeted knight** and THE LAST GOOD YEAR a child shot mostly from
behind in a **red scarf**. Both hold across every single shot. Neither is a trick about
faces — it's a trick about **silhouette**.

A face is ~200 px of high-frequency detail that the model re-invents from scratch every
generation. A helmet, a hood, a hat brim, a pair of round glasses, a ponytail shape, an
optic band, a green frog head — these are **low-frequency shape** and they survive. Qwen
reproduces silhouette far more reliably than it reproduces identity.

So the helmet trick generalises into a rule:

> **Every recurring character needs one unmistakable identifier above the shoulders and one
> below, both describable as shape and colour rather than as a face.**

### 2.2 What that predicts, and what CHRONO measured

CHRONO has seven recurring named humans across 109 shots and cannot helmet any of them.
Ranked by how well each actually held, the correlation with §2.1 is almost perfect:

| Character | Holds? | Why |
|---|---|---|
| FROG | **Excellent** | Non-human head. Cannot drift into a different human. `470_frog` / `510_masamune` / `905_frog` are the same character. |
| ROBO | **Excellent within its run** | Armour is pure silhouette. `430_robo` / `440_robo_torn` / `450_planting` match exactly. |
| LUCCA | **Good** | Three hard silhouette features stacked: wide brown cap + round glasses + green tunic. Consistent across `060`–`380`. |
| MARLE | **Good on costume, poor on hair value** | Orange hood + white dress + high ponytail is a strong silhouette; the *colour* swings (see 2.4). |
| CRONO | **Head yes, body no** | Spiky crimson hair reads in 100 % of appearances. Everything below the neck has four different interpretations (2.3). |
| MAGUS | **Poor** | Reads female in `540`, `550`, and as a girl in `695_janus`. |
| AYLA | **Failed** | Reads as a muscular man in both appearances (`580`, `600`). |

The lesson is not "avoid humans". It's: **the identifier does the work, and a description
that leads with body type or personality instead of shape will fail.** ROBO's "one glowing
amber optic band across its face" is the ideal form of the rule — and note it *still* came
back as two separate glowing eyes, because a band across a face is unusual enough that the
model substituted the common case. Describe the *silhouette*, and describe it as a shape the
model has seen a thousand times.

### 2.3 CRONO — the layering ambiguity

Current wording:

> `a lean teenage swordsman with wild spiky crimson red hair, a white tunic under a short dark blue gi, an orange sash, a long katana across his back`

Two concrete failures.

**(a) "a white tunic under a short dark blue gi" is unparseable.** It was rendered as: a
blue coat over white sleeves (`030_crono`, `040_collide`); a blue sleeveless vest over a
white shirt (`070_teleport`, `910_two_shot`); an open blue haori over a bare chest
(`230_arrest`); and **no blue garment at all** — a plain white robe — in `250_dungeon`,
`540_magus_fight`, `600_tyrano`, `730_crono_steps`. Four of nine sampled appearances lose
the blue entirely, and the blue is half his colour identity.

**(b) "a long katana across his back" duplicates the sword.** In `540_magus_fight`,
`600_tyrano` and `730_crono_steps` he swings a katana **while a second identical katana is
still sheathed on his back**. The character block asserts a worn prop; the shot asserts a
held prop; the model renders both. Any prop that a shot might put in a character's hand
must not be described as worn in the character block.

Also: he is barefoot in five of nine sampled shots, and his apparent age swings from about
14 (`820_revived`) to about 22 with a bared chest (`230_arrest`).

**Replacement:**

```
"CRONO": "a slim 16-year-old boy, wild spiky crimson red hair standing straight up in
long points, a sleeveless dark navy blue wrap tunic worn open over a plain white shirt
with loose sleeves rolled to the elbow, a wide bright orange cloth sash knotted at his
waist, loose dark navy trousers, plain sandals, boyish round face"
```

What changed and why: age fixed numerically; "sleeveless … worn open over" removes the
layering ambiguity and forces both garments into frame; "wrap tunic" instead of "gi" stops
the slide into a bathrobe; footwear specified so he stops being barefoot; "boyish round
face" pushes back on the adult jaw; **the katana is removed entirely** — put it in the shot
prompt when he's carrying it ("a long katana slung across his back") and only when he isn't
using it.

Reference frames to match: `040_collide` and `910_two_shot`.

### 2.4 MARLE — "pale blonde" is being read as a value, not a hue

Current:

> `a girl with long pale blonde hair in a high ponytail, a white and orange hooded tunic dress, a light crossbow, a glowing blue teardrop pendant at her throat`

Her hair is **saturated yellow-gold** in `040_collide` and `910_two_shot` and **near-white
platinum** in `080_pendant`, `150_fading`, `220_princess`, `370_watching`, `380_resolve`.
"Pale" is doing this: half the time it's read as low saturation, half as high value. In a
film that cross-cuts between these shots it reads as two different girls.

The costume is the film's best-held design — don't touch the orange hood.

**Replacement:**

```
"MARLE": "a 16-year-old girl with long bright golden yellow hair, deep saturated blonde
not white or platinum, gathered high on the back of her head in one long ponytail, a
white knee-length tunic dress with a bright orange hood and orange trim, a small wooden
hand crossbow, a single teardrop-shaped blue gem pendant hanging at her own throat"
```

`her own throat` is the anti-bleed clause from §1.4. Also note the pendant prop itself drifts
— `100_dropped` renders it as a large round cabochon on a heavy chain rather than a small
teardrop; if it's a hero prop, describe it identically in every shot prompt too, not only in
the character block.

### 2.5 AYLA — the word order lost her gender

Current:

> `a powerfully built prehistoric woman with wild blonde hair, fur wraps and bone jewellery, barefoot, fierce grin`

In `580_ayla` and `600_tyrano` she is unmistakably a **man**: flat pectorals, defined abs, a
masculine jaw, a He-Man physique. "Powerfully built" arrives before "woman", and in the
model's prior "powerfully built + furs + prehistoric" is overwhelmingly male. This is the
worst character failure in the film — it is her introduction, and the narration calls her
"who leads her people".

**Replacement:**

```
"AYLA": "a young woman, athletic and strong but unmistakably female with a clearly
feminine face and figure, long wild sun-bleached blonde hair, a brief tan hide wrap top
and skirt, bone and tooth necklaces, leather cords around her wrists, barefoot, wide
fierce grin"
```

Gender first, twice, before any physique word; "athletic and strong" replaces "powerfully
built"; the garment is named as a top-and-skirt so it stops reading as a loincloth.

### 2.6 MAGUS — "sorcerer" plus "long blue white hair" equals anime sorceress

Current:

> `a tall sorcerer in a black hooded cloak with a high collar, long blue white hair, pale skin, a curved scythe, glowing red eyes`

`540_magus_fight` and `550_spell_runs` both render a slender young **woman** with silver-blue
hair and red eyes. `695_janus` (young Magus) renders a **girl**. The high collar never
appears in any shot. "Tall" never lands either — he's the same height as everyone else.

**Replacement:**

```
"MAGUS": "a tall gaunt adult man with a hard angular face, sharp jaw and narrow eyes
glowing red, straight waist-length pale blue-white hair, chalk-pale skin, a floor-length
black cloak whose collar rises in two stiff points higher than the top of his head, a
long curved black scythe"
```

`a tall gaunt adult man` front-loaded; the collar described geometrically ("two stiff points
higher than the top of his head") because "high collar" is too abstract to render;
"hard angular face, sharp jaw" as the anti-feminine steer. For `695_janus`, the child version
needs the same treatment inline: "a small boy, clearly male, short for his age".

### 2.7 The other four

```
"LUCCA": "a 15-year-old girl with a short reddish brown bob, a wide-brimmed soft brown
cap pulled low, large round wire-rimmed spectacles, a plain green long-sleeved tunic over
a short skirt, a broad brown leather tool belt with a small brass revolver holstered at
her hip"
```
Adds a fixed age (she is drawn as a small child in `270_escape` and a teenager in
`260_rescue`), keeps the three silhouette features that are already working, and says "tunic
over a short skirt" because `370_watching` and `380_resolve` slid her into a full-length
green kimono.

```
"FROG": "a tall upright anthropomorphic green frog standing on two legs like a man, broad
shouldered, wearing a brown hooded cloak and a long brown cape, a brown leather breastplate
and boots, carrying a broadsword with an ornate golden crossguard hilt"
```
Adds "standing on two legs like a man" and boots because `470_frog` renders splayed bare
frog feet and a comic amphibian stance where the brief said noble bearing. Everything else
stays — this description is working.

```
"ROBO": "a large heavy humanoid robot with a rounded barrel-shaped cream-white torso and
dull blue-steel limbs, a single wide horizontal amber light bar glowing across the front of
its smooth faceless head, no eyes and no mouth, oversized three-fingered claw hands, dented
scratched plating"
```
`no eyes and no mouth` is the load-bearing addition: "one glowing amber optic band" alone
produced two glowing eyes in every appearance. Negating the common case *inside the positive
prompt* is the only way to do it here, because the negative prompt is inert at cfg 1.0. Also
note `420_factory` renders a completely different thin skeletal android for deactivated-Robo
— when a character appears powered-down, use the same `{ROBO}` block plus "slumped,
unlit, dark", never a fresh description.

```
"LAVOS": "an immense armoured creature like a barnacle or limpet shell, a low domed shell
of overlapping grey-brown plates bristling with long dark spines, a single glowing red core
at the centre of the shell, many long segmented clawed legs splayed out beneath it, no face,
no eyes, utterly alien"
```
`no face, no eyes` again: `350_eruption`, `720_rising` and `840_assault` all rendered a
single enormous cyclops eye where the core should be, while `620_falling` and `640_burrow`
rendered the core correctly. Three of five appearances are a different creature. For a
monster that appears in eight shots, that matters as much as any human's face.

### 2.8 When you can't helmet anybody: the fallback ladder

In order of how much they buy you:

1. **Silhouette identifiers, per §2.1.** Cheapest and biggest.
2. **Shoot away from the face.** THE LAST GOOD YEAR's child is shot from behind, in profile,
   or tiny, in most of her shots, and never drifts. In CHRONO, `390_leaving`, `210_return`,
   `810_summit` and `920_lanterns` all use figures as silhouettes and none of them have a
   consistency problem. Budget a third of your character shots as backs, silhouettes and
   over-shoulders. It reads as coverage, not as evasion.
3. **`quality: true` on every shot where the party is recognisably in frame.** 20 steps holds
   a described costume much better than 4.
4. **Pick your hero frame and never re-describe.** Choose the one keyframe per character that
   is exactly right (`040_collide` for Crono, `910_two_shot` for Marle, `260_rescue` for
   Lucca, `430_robo` for Robo) and treat its costume as the spec. If a later shot disagrees,
   the later shot is wrong.
5. **Use Qwen-Image-Edit's multi-image path for the money shots only.**
   `TextEncodeQwenImageEditPlus` takes `image1`/`image2`/`image3`, and `PROMPTING.md` calls
   this out for character consistency. At 48 s a pass it is far too slow for 109 shots, but
   the hero line-up (`830_party`), the resurrection (`820_revived`) and the final battle
   (`870_final_battle`) are three shots — 2.5 minutes of GPU to fix the three frames the
   audience will actually remember. Do that.
6. **Cast non-humans and machines wherever the story lets you.** Frog and Robo cost nothing
   to hold. This is why the earlier films did it, and it is still the right answer when the
   story is negotiable.

### 2.9 The one thing that always breaks: crowds of named characters

Every shot in CHRONO with 4+ named characters in frame lost all of them: `830_party` (7),
`820_revived` (5), `870_final_battle` (7), `780_empty_seat` (4), `836_queen_last` (7).
Every shot with 1–3 held reasonably. **Three named characters per frame is the ceiling.**
Above that, either shoot them as silhouettes (`810_summit` does this and works), or shoot
partial coverage — two of them, then two others — and let the cut assert that all seven are
there.

---

## 3. Shot scale and composition rhythm

`EDITING.md` §5 classifies the film by the scale word in each *prompt* and finds runs of 4,
4 and 5. Classifying by what actually **rendered** is worse, because Qwen quietly promotes
wides to mediums when a character block is present. Delivered scale across 109:

| | XW | W | M | C | XCU | Macro |
|---|---|---|---|---|---|---|
| shots | 15 | 42 | 40 | 9 | **0** | 3 |

**There is not one extreme close-up in a ten-minute film, and only three macro inserts**
(`100_dropped`, `415_gatekey`, `805_eggname`). Both earlier films — 23 and 18 shots — had
more inserts than that in absolute terms. THE LAST GOOD YEAR builds an entire recurring
motif out of macro shots of one pocket watch (`03_watch`, `05_reply`, `09_fail`,
`17_watch_stop`), and those four shots are also the film's best character continuity,
because a watch face does not drift.

Two things follow:

- **A macro insert is the cheapest shot you can make.** No character, no face, no
  consistency risk, near-perfect prompt adherence (all three of CHRONO's macros landed
  exactly), 4.5 s of GPU, and it resets the eye. Write more of them.
- **Inserts are where continuity gets asserted for free.** A close-up of the pendant, the
  katana hilt, the gate key, Robo's optic band — each one re-establishes a design without
  risking a face.

### The runs worth fixing, by delivered scale

| Run | Shots | Problem | Fix |
|---|---|---|---|
| **Climax, worst in the film** | `834_black_omen` → `875_spawn` — that's `834`, `836`, `840`, `850`, `860`, `870`, `875` | **Seven consecutive wides.** The entire final battle has no close-up: no face, no hand on a hilt, no eye. The film's biggest emotional moment is played entirely in long shot. | Insert an XCU between `840_assault` and `850_inside` (a gloved hand white-knuckled on a control yoke), and a close single between `870_final_battle` and `875_spawn` (Crono's face lit red, half a second before the core breaks). |
| Future act opening | `290`, `300`, `310`, `320`, `330` | Five consecutive W/XW establishing shots — a slideshow, and the act where the audience most needs a person to identify with. | Make `300_deadsky` an **XCU**: the dead grey sky reflected in a single shard of broken window glass. Add a macro between `320_survivors` and `330_dome_interior`: an empty ration tin, scraped clean. |
| Zeal act opening | `650`, `655`, `660` | Three consecutive vista wides, all "look at this". | Insert a close between `655_ice_village` and `660_zeal`: a child's frost-cracked hands, or one face on the ice looking up. |
| Ocean Palace | `700`, `710`, `720` | Three wides, and `710`/`720` are both "large glowing red thing in a stone chamber" — nearly the same image twice. | `710_full_power` becomes a **close** on Queen Zeal's face lit from below by the machine. Keeps the wide for `720_rising`, where the scale is the point. |
| Epilogue | `880`, `885`, `890` | Three wides before the film finally closes in. | `EDITING.md` is right that the ending should resolve wide-to-close. `890_fair_again` can be a medium at crowd level; `900_never_know` already is. |
| Back-to-back staging repeat | `370_watching` / `380_resolve` | Not just the same scale — the **same shot**: three characters in a row, facing camera, in front of a monitor. `380` was specified as a close-up with the other two out of focus and delivered as a flat three-shot. | `380_resolve` must be a genuine close single. This is the film's turning point and it is currently staged as a class photo. |

### Rules worth keeping

1. **Never three consecutive delivered-wides.** Check the sheet, not the prompt.
2. **One insert per act minimum**, and make it an object, not a person.
3. **Every act's emotional peak gets the tightest shot in that act.** In CHRONO the peaks
   (`380_resolve`, `740_death`, `820_revived`, `870_final_battle`) are variously a three-shot,
   a wide, a medium and a wide. Only `740_death` works, and it works because the frame
   collapses to a silhouette and pure white.
4. **Symmetry is a tool, not a default.** `140_throne`, `170_nuns`, `240_trial`, `530_ritual`,
   `700_descent`, `834_black_omen` are all dead-centre one-point-perspective compositions and
   they are all strong — but there are eleven of them in the film and after the fourth it
   starts to read as a house style rather than as emphasis. Reserve it for the formal beats
   (throne, trial, ritual) and break it elsewhere.

---

## 4. Style LoRA strength — the evidence

`qwen_image_2512_storybook_anime_lora.safetensors` at `style_strength: 0.9`, on top of the
4-step Lightning LoRA, across all 109 shots.

### It does not hold consistently. It holds where there's a big anime character to anchor it.

**Full storybook-anime cel look, clean bold outlines, flat saturated fills:**
`070_teleport`, `080_pendant`, `150_fading`, `220_princess`, `260_rescue`, `270_escape`,
`370_watching`, `380_resolve`, `820_revived`, `910_two_shot`. All of them are one to three
large characters in saturated light.

**Style substantially absent — painterly / near-photoreal illustration:**
`320_survivors` (realistic gaunt adult faces, muted palette), `665_gurus` (Western realist
portrait heads), `790_egg` (an almost photographic old man), `900_never_know` (painterly
crowd), `800_deathpeak`, `860_harvest`, and most conspicuously **`920_lanterns`** — the final
shot of the film is a photoreal matte painting with no cel shading anywhere in it.

The pattern is consistent: the LoRA holds when there is a **large stylised character face**
in frame, and drops out on landscapes, architecture, crowds of small figures, and realistic
adult faces. That's not a strength problem — it's a *conditioning* problem, and `NEG_IMG`
already contains `photorealistic, photograph, 3d render, live action` and cannot help,
because at cfg 1.0 the negative is inert.

### It also hijacks the palette, which is worse

The LoRA has a very strong prior for **blue skies with white clouds** and **golden-hour
orange**. Every shot that asked for grey, colourless or dead got one of those two instead:

| Shot | Asked for | Got |
|---|---|---|
| `290_era2300` | dead grey sky, no green anywhere | blue sky, white clouds, trees everywhere |
| `300_deadsky` | colourless overcast, no cloud shapes | blue sky, white clouds |
| `310_domes` | grey wasteland, dead sky | warm orange sunset |
| `330_dome_interior` | dark facility, thick dust | blue sky through the ceiling |
| `390_leaving` | grey ruined wasteland, dead sky | golden sunset |
| `760_washed_up` | colourless sea, grey shoreline | bright blue sunlit sea |
| `800_deathpeak` | screaming grey storm | orange sunset behind the peak |
| `130_war` | grey dusk, heavy clouds | pretty golden sunset |
| `250_dungeon` | one pale bar of light across the dark | evenly, warmly lit cell |
| `670_machine`, `710_full_power` | interior / undersea | orange sunset through the arches |

And the LoRA is only half the culprit. CHRONO's global `style` string, appended verbatim to
all 109 prompts, is:

> `storybook anime illustration, classic 16-bit JRPG cover art, cel shaded characters with
> clean bold outlines, warm hand painted background, vivid saturated colour, dramatic sky,
> crisp readable shapes, epic widescreen composition`

**`warm hand painted background`, `vivid saturated colour` and `dramatic sky` are being
asserted on the dead-grey-sky shots too**, in the same prompt that asks for a colourless
overcast. The style string is the *last* thing in the encoded text and it wins. Strip those
three phrases out of the global style block and move them into the individual bright shots,
or keep two style strings and select per act:

```json
"style":      "storybook anime illustration, classic 16-bit JRPG cover art, cel shaded characters with clean bold outlines, crisp readable shapes, epic widescreen composition",
"style_warm": "…the above… , warm hand painted background, vivid saturated colour, dramatic sky",
"style_cold": "…the above… , desaturated grey-brown palette, flat overcast light, low contrast, bleak"
```

Compare THE HOLLOW CHOIR, rendered with **no style LoRA**: 23 of 23 shots are dark,
high-contrast, candle-lit and tonally identical, and the base Qwen model had no trouble at
all producing them. **The inability to make a dead grey sky is caused by the LoRA, not by
the model.** That's a clean A/B.

### Where it goes too twee for the content

- `750_zeal_falls` — a civilisation being annihilated, rendered as a pristine golden city on
  a floating island above decorative Hokusai wave curls. Nothing is toppling; nothing is even
  cracked. The prompt asked for spires toppling through cloud.
- `450_planting` — "wide melancholy … vast barren hillside, pale overcast sky" came back as
  a cheerful robot under fluffy white clouds on a blue-sky day.
- `630_impact` — an extinction event with untouched lush green jungle either side of the
  crater and a blue sky above it.
- `550_spell_runs` — the sorcerer whose life's work has just betrayed him, kneeling calmly
  and smiling gently at camera in a pretty sunset ruin.

### Verdict

**0.9 is wrong in two directions at once: too strong on palette, unreliably applied on
line.** Do this, in order:

1. **Add per-shot `style_strength` to `epic.py`** — one line, alongside the per-shot `quality`
   and `seed` from §1.1/§1.2:
   ```python
   set_path(wf, "7.inputs.strength_model",
            float(s.get("style_strength", film.get("style_strength", 0.9))))
   ```
2. **Global default 0.75.** Enough to keep the cel look on the character shots (which are the
   ones that carry it anyway), materially less palette hijack. Note the shipped workflow
   default in `13_qwen_t2i_styled.json` is 0.8, which is closer to right than the film JSON's
   0.9.
3. **0.50–0.55 for the dark acts:** everything in 2300 (`290`–`390`), the Ocean Palace
   (`700`–`760`), the Lavos interior (`850`, `870`, `875`), `800_deathpeak`, `480_cyrus`,
   `250_dungeon`. At 0.5 you keep enough line quality to sit next to the rest of the film and
   you get your grey sky back.
4. **0.85–0.9 for the fair, Zeal and epilogue acts** — `010`–`110`, `650`–`695`, `880`–`920`.
   These are where the storybook look is doing real work; `660_zeal` and `570_prehistoric` are
   genuinely beautiful because of it.
5. **Whatever the strength, name the palette positively in the prompt** (§1.5). Strength
   alone will not give you a grey sky if the words don't ask for one.

If you refuse to touch the code: **0.75 global**, and rewrite the palette language in the
~14 dark shots. That gets most of it.

---

## 5. Writing LTX `motion` prompts that don't morph

`PROMPTING.md` has the model-level advice (camera → subject → ambient; physics beats
adjectives; don't fight the start frame). `FILMMAKING.md` has the rule: **one camera move,
one action.** CHRONO's 109 motion fields violate it about **45 times**, and the violations
sort into nine recognisable shapes. Each one is a checkable rule.

### The nine failure shapes

**1. Sequential beats — "X, then Y".** The commonest by far. LTX has one motion prior per
clip; asking for two events in series produces a smear between them.
> `100_dropped`: *"A hand comes down slowly, **hesitates**, then closes around it and lifts it
> out of frame."* Three beats.
> Also `040_collide`, `090_gate`, `530_ritual`→no, `540_magus_fight`, `775_epoch_wings`
> (four beats), `905_frog`, `690_schala`, `695_janus`, `730_crono_steps`.

**2. Multiple actors with separate actions.** Each additional independent mover roughly
doubles the morph risk.
> `525_generals`: *"the fat one laughing silently, the masked one tilting its head, the
> swordsman turning a blade over in his hand."* Three characters, three actions.
> Also `050_fairmontage`, `060_telepod`, `180_fight`, `190_yakra`, `600_tyrano`,
> `765_dalton`, `830_party` (seven), `870_final_battle` (seven), `836_queen_last`.

**3. Motion that contradicts the keyframe.** The single most avoidable category — you have
the keyframe in front of you.
> `260_rescue`: motion says *"The door blows inward off its hinges … Lucca steps through the
> gap."* The keyframe shows the door **intact and shut**, with Lucca already outside it in the
> corridor.
> `230_arrest`: *"His sword is kicked away across the flagstones"* — the sword is on his back.
> `030_crono`: *"He runs away from camera … camera tracks fast behind him"* — he is standing
> still. `080_pendant`: *"Her hand closes around it"* — her hand is already open and extended.
> `410_gaspar`, `470_frog`, `510_masamune`, `380_resolve`, `220_princess`, `430_robo`,
> `910_two_shot` all do a version of this.
> **Always read the motion field with the keyframe open beside it.** This is a five-minute
> pass over the whole film and it catches ten shots.

**4. Subjects entering or leaving frame.** LTX has nothing to fill the hole with.
> `110_step_through` (*"the light swallows him whole"*), `210_return` (three figures walk
> into a portal one after another), `280_cornered` (*"leap sideways into it"*),
> `100_dropped` (*"lifts it out of frame"*), `725_schala` (*"the light swallows her
> completely"*).
> Exception that proves the rule: `740_death` asks the *light* to expand until it consumes the
> frame while the figure dissolves inside it. That works, because the end state is a flat
> white field — trivially easy to synthesise. **If you need something to vanish, vanish it
> into an even field of colour.**

**5. Dematerialisation and structural destruction of the subject.**
> `150_fading` (a body breaking into motes), `440_robo_torn` (*"an arm tears free"*),
> `750_zeal_falls` (*"the continent cracks apart"*), `070_teleport` (*"dissolves into
> streaking energy, reappearing an instant later on the far pad"* — a teleport is two
> positions, LTX has one).
> Stage the *after* as a separate keyframe and cut. Two shots always beat one impossible one,
> and per `CAPABILITIES.md` the second clip is nearly free.

**6. Hand-to-hand prop exchanges.** Two pairs of hands interacting is the hardest thing in
the i2v repertoire.
> `790_egg`: *"He places the egg into her hands **and closes her fingers around it** … He nods
> once."* Four hands, a small object between them, plus a head beat.
> Replace with a single continuous pressure: *"Both pairs of hands stay still. The egg's glow
> slowly brightens."*

**7. Screen and display content changes.**
> `340_recording`: *"Static bands crawl up the screen **and it resolves into an image**."* LTX
> will morph the screen's contents into mush. If the screen must change, cut to a second
> keyframe of the new image.

**8. Time-lapse.**
> `250_dungeon`: *"The pale bar of light creeps slowly across the floor and up the wall **as
> hours pass**."* In four seconds, at 24 fps. It will either do nothing or slide the whole wall.

**9. Split-screen / multi-panel frames.** The worst motion prompt in the film:
> `832_split`: *"Each vignette moves independently … All four settle at once."* LTX has no
> concept of a panel border. It will bleed motion across the divisions and warp the gutters.
> A 4-up montage frame should be animated as a **still with a slow push**, or not generated as
> one frame at all.

**Bonus category: micro-face actions.** `820_revived` (*"His eyes open and he takes a
breath"*), `915_mother` (*"She laughs"*), `690_schala` (*"glances back over her shoulder,
then down"*). The model has seen this face for exactly one frame; asking it to re-animate
eyelids and mouths is asking it to invent identity 96 times. Keep faces still and let the
hair, cloth and light move.

### Motion prompts from this film worth copying verbatim

These are the shape to aim for — one process, stated as physics, that the keyframe can
obviously support:

> `490_broken_sword`: *"Candlelight moves slowly across the broken faces of the blade. Dust
> settles into the fracture. A faint blue glow pulses once deep inside the metal and fades."*

> `780_empty_seat`: *"Streaks of light rush past the canopy. The crew sit quietly, none of
> them speaking. The katana on the empty seat shifts slightly with the motion. Nobody looks
> at it."*

> `920_lanterns`: *"Hundreds of lanterns drift steadily upward across the whole frame and
> their reflections move on the river. The two tiny silhouettes stay still. Very slow crane
> up and back."*

> `860_harvest`: *"The camera drifts slowly past the row of scarred dead planets. The spined
> shape moves steadily away toward the distant blue world. Stars turn slowly."*

All four: one camera idea, one subject idea, ambient underneath, nothing contradicting the
frame, nothing entering or leaving, no faces performing.

### The motion checklist

Run this over every `motion` field with the keyframe open:

- [ ] Is there exactly **one** camera move? (Or none — locked-off is a legitimate choice and
      `920_lanterns` proves it.)
- [ ] Is there exactly **one** subject action, and does it belong to **one** actor?
- [ ] Does the keyframe already show that action **completed**? If so, delete it.
- [ ] Does anything **enter or leave** frame? If yes, either remove it or make its
      destination a flat field of light.
- [ ] Does any subject **change shape, break, dissolve or teleport**? Split into two shots.
- [ ] Do any **hands touch other hands or exchange an object**? Rewrite as pressure or glow.
- [ ] Does any **screen, display or written surface change content**? Cut instead.
- [ ] Is there any word implying **elapsed time** ("as hours pass", "one after another",
      "then", "and then", "repeatedly")? Delete it.
- [ ] Are any **faces performing** (blink, laugh, gasp, eyes opening)? Move the motion to
      hair, cloth, smoke or light.
- [ ] Everything else in the field should be **ambient**: cloth, hair, water, smoke, dust,
      embers, foliage, light. You can have three or four of these safely — `010_kingdom` runs
      banners + clouds + birds + mist and is fine, because none of them is a subject.

Also: `epic.py` runs `expand(s["motion"], chars)`, so a `{CRONO}` in a motion field injects
the entire character description into the LTX prompt and drowns the motion words. CHRONO
never does this. Don't start.

---

## 6. The off-brief rate, and how to budget for it

The earlier two films drifted off-brief on roughly **20 %** of keyframes. CHRONO, with a
strong style LoRA stacked on top of the 4-step path, ran at about **28 %** — 30 of 109 shots
missed something the prompt explicitly asked for, of which about 10 are bad enough to hurt
the story. **A style LoRA raises your off-brief rate.** That is the price of the look, and
you should plan for it rather than discover it.

### The budget

| | |
|---|---|
| Keyframes at 4 steps, 1664x928 | 4.5 s each |
| Keyframes at 20 steps | 30 s each |
| LTX clip, 1280x704, any length up to 241 f | ~16 s each |
| **So: plan 1.3 keyframes per finished shot** | a 109-shot film is ~145 keyframe renders |
| Extra cost of that at 4 steps | ~3 minutes |
| Extra cost if the 36 re-rolls are at 20 steps | ~18 minutes |

Eighteen minutes to fix a quarter of your film. Do not skip it, and do not animate before
you've done it — a bad keyframe animated is 16 s wasted plus the review time plus the
temptation to keep it because it's already a clip.

### The workflow that follows from those numbers

1. **Render all keyframes at 4 steps.** Cheap, ~8 minutes for 109.
2. **Contact-sheet and review all of them** (§0). Half an hour of looking.
3. **Triage into three buckets:**
   - *Fine* — ship it. Roughly 70 %.
   - *Wrong staging / missing element* — rewrite the prompt per §1 **and** set
     `quality: true`. Roughly 20 %.
   - *Right idea, wrong palette or wrong scale* — often fixable by a `style_strength` drop
     and explicit palette words alone, still at 4 steps. Roughly 10 %.
4. **Re-render just those**, review again.
5. **Only then** run `--stage clips`.
6. **Read every motion field with its keyframe open** (§5 checklist) before clips, not after.

### What to check for specifically, ranked by how often it went wrong in CHRONO

1. **The sky.** Ten shots got the wrong sky. It's the largest area of most frames and the
   model has strong defaults. Name it every time.
2. **Did the stated action actually happen?** Standing where the prompt said running
   (`030_crono`), intact where the prompt said blasted (`260_rescue`), whole where the prompt
   said broken in two (`490_broken_sword`), undamaged where the prompt said torn apart
   (`440_robo_torn`).
3. **Is the named character actually that character?** Not "is there a girl with a crossbow" —
   is it *Marle*. `830_party`, `820_revived`, `870_final_battle`, `790_egg`, `780_empty_seat`
   and `832_split` all pass the first test and fail the second.
4. **Count the things you asked for.** Two silhouettes where the prompt said three
   (`340_recording`); one guard where it said two (`230_arrest`); three attackers where it
   said four (`440_robo_torn`); two women where it said one (`915_mother`); two whole swords
   where it said one broken one (`490_broken_sword`).
5. **Recurring locations and props.** The white castle in `010_kingdom` becomes a squat keep
   behind a windmill in `890_fair_again`. The Epoch is a red car (`770_epoch`), then a Gundam
   with feathered wings (`775_epoch_wings`), then a red jet (`840_assault`). Vehicles and
   buildings need character-block treatment exactly like people do — **put your hero props in
   the `characters` block** and reference them with a placeholder.
6. **Accidental resemblance to something famous.** `520_keep` is Hogwarts. `850_inside` is a
   Xenomorph — in a shot whose narration is *"it is not a monster"*. `775_epoch_wings` is a
   Gundam. Qwen reaches for the nearest famous instance of any archetype; if you don't want
   that, describe the silhouette specifically enough to exclude it.

### And the meta-lesson

The failures are not random. They cluster on **specific staged physical relationships** —
one thing doing a particular thing to another thing — and they almost never happen on
landscape, architecture, weather, scale or atmosphere. Qwen at 4 steps is a superb
*production designer* and a mediocre *stage director*.

Write to that. Put your ambition into places, light, weather and scale, where the model is
excellent and free. Buy prompt adherence with 20 steps only where the story genuinely needs
a specific action to be legible. And when a shot needs two things to happen, make it two
shots — clips are 16 seconds each and the cut was always going to be better anyway.

---

# 8. Reference-locked characters — the actual solution (added 2026-07-30)

Everything in section 2 above is damage limitation: careful wording so text-to-image
re-invents the character *similarly* each time. It re-invents it every time regardless.

The real fix is to stop describing the character and start **showing** it.

## The method

1. Render **one canonical character sheet** per character: full upper body, facing camera,
   neutral expression, flat frontal light, plain dark background, face unobstructed. Pay
   for it — 20 steps, no Lightning LoRA. Every other shot inherits from this one frame, so
   it is the highest-leverage image in the film.
2. Copy the sheet into `ComfyUI/input/`.
3. Generate every subsequent keyframe with **`workflows/14_qwen_edit_ref.json`** —
   Qwen-Image-Edit 2511 + its 4-step Lightning LoRA — passing the sheet as `image1` on
   `TextEncodeQwenImageEditPlus`, and phrase the prompt as *"the same man from the reference
   image, <doing something somewhere else>"*.

## The one setting that matters

`TextEncodeQwenImageEditPlus` carries the reference either way, but **what you feed
KSampler as `latent_image` decides whether you get a film or a square**:

| `latent_image` | denoise | Face held | Output size | Verdict |
|---|---|---|---|---|
| **empty latent at target res** | 1.0 | yes | **1664×928 as requested** | **use this** |
| VAEEncode(reference) | 1.0 | yes | 1328×1328 — the *reference's* aspect | unusable for widescreen |
| VAEEncode(reference) | 0.85 | yes | 1328×1328 | unusable for widescreen |

Measured on a wide battlefield shot and an extreme close-up of the same character: the face
held in all three modes, so the reference conditioning is doing the work, not the canvas.
Canvas mode only costs you aspect control. **Empty latent, denoise 1.0.**

## Cost

**7.6 s per keyframe** (vs ~5 s for plain 4-step t2i). Character consistency is now
essentially free — before the 2511 Lightning LoRA existed it was 48 s a frame, which is why
earlier films worked around the problem instead of solving it.

## Still true, and still worth doing

The reference does not repeal section 2. Keep the `characters` block wording disciplined —
gender before physique, no weapon in the block, spell out absences — because the block is
what generates the **sheet**, and every error in the sheet propagates to every shot in the
film. Get the sheet right and look at it closely before you build on it.

Up to 3 references per encode. Use `image2` for a second character in a two-hander, and
`image3` for a location plate when a place recurs.

## Video stage

`ltx-2.3-id-lora-talkvid-3k.safetensors` is an identity LoRA for LTX and holds a face
through the *clip*, not just the keyframe. i2v from a locked keyframe already holds well
within a shot; add the ID LoRA when a shot is long, chained, or close on a face.

## 5b. Never assert stillness in a motion prompt (added 2026-07-30)

LTX takes "nothing else moves" literally and hands back a genuinely static frame. On a
15-minute film, one such prompt produced a **1.54 s freeze** that `freezedetect` caught at
761 s — an actual still image in a film whose whole brief was that it contain none.

The rule: **the subject may be still; the frame may not.** If a shot needs a motionless
character, put the movement somewhere else in the frame and always add a slow camera move:

| Instead of | Write |
|---|---|
| "Nothing else moves." | "Dust turns in the shaft of light. Slow push in." |
| "He stands absolutely still." | "His cloak stirs. Smoke drifts past him. Slow drift in." |
| "The figure does not react." | "His shoulders rise and fall shallowly but continuously." |

Reliable ambient movers that never fight the composition: falling snow or ash, dust in a
light shaft, drifting smoke, firelight flicker, a shaft of light creeping as the sun moves,
breath, water dripping, cloth in a draught.

**Verify, don't assume.** One line finds it across a whole film:

```
ffmpeg -i film.mp4 -vf "freezedetect=n=-60dB:d=0.7" -map 0:v -f null -
```

And grep every `motion` field for asserted stillness before you render, not after — the
phrases to catch are "nothing else", "no movement", "does not move at all", "absolutely
still", "utterly still", "completely still".

### 5b-i. Audit EVERY motion field, not just `motion`

The first pass of this rule was applied only to `motion` and missed a freeze entirely. The
one that actually shipped was in **`motion3` of a chained shot** — a 3-link rescue whose
last link ended "both stop dead in the doorway". Told to stop, the model stops, and the
freeze lands at the tail of the take.

Two corrections to the method:

1. **Grep `motion2`, `motion3`, `motion4`, `motion5` as well.** A chained shot has most of
   its screen time in the links, not the opener, and its final link is the most likely
   place to write an ending beat like "they stop" or "he comes to rest".
2. **The grep is a pre-flight, not the verdict.** Of 8 shots flagged in one film, only 1
   actually froze — the rest assert stillness for the *subject* while smoke, crows or a
   crawling horizon keep the frame alive, which is correct and should not be "fixed".
   `freezedetect` is the authority. Grep to find candidates, measure to decide.

A chained link that has to end on a stop should end on a *slowing*, with the camera still
moving and something ambient still running:

> "…and slow to a walk, torchlight swinging across the walls as the torch lowers, smoke
> rolling past them, both still breathing hard. Slow continuous push forward."
