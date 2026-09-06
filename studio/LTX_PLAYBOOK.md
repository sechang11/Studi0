# The LTX-2.5 playbook

Everything the 21 August overnight run established, in the order you need it.
Written so none of it has to be found twice.

---

## 1. What to reach for

| You want | Use | Why |
|---|---|---|
| A shot up to 30s, with sound, that holds its scene | **LTX-2.5** (`70_ltx25_i2v.json` via `studio/_tools/ltx_film.py`) | One sampling pass. No chain, so nothing can drift. |
| Real cuts inside one shot | **LTX-2.5 multishot** | Several framings, one generation, character held across them. |
| Spoken dialogue, photoreal | **LTX-2.5** | Lip-synced, through a mouth that is on screen. |
| Spoken dialogue, anime | **LTX-2.5, cut away from the face** | It generates the voice but leaves the drawn mouth shut. |
| One violent physical event, one unbroken take | **H3** (`60`/`62`) | Still hits harder than LTX. Its "one big committed motion" rule was built for this. |
| A locked location for 30s, audio not needed | **Wan context windows** (`61`) | The most rigid continuity available, but silent and 832×480. |
| Music, a score, a crescendo | **ACE-Step** (`06_acestep_music.json`) | LTX makes wind when asked for an orchestra. ACE-Step writes 46 s of real score in 6 s — but fades to silence past about 45 s, so cut the film to the music. MiniMax Music 3 is downloaded and still untested. |

The chaining **workarounds** are obsolete. H3 itself is not.

---

## 2. The measured envelope

Past it the ComfyUI **process is killed** — no exception, the socket closes mid-run, and
every remaining item in a batch fails with `Connection refused`.

| Base | Output | Max length | Result |
|---|---|---|---|
| 0.9 MP | 1280×704 | 30 s | ran |
| 1.2 MP | 1472×832 | 20 s | ran |
| 1.5 MP | 1664×896 | 12 s | ran |
| 2.0 MP | 1920×1088 | 8 s | ran |
| 1.5 MP | — | 20 s | **killed** |
| 1.8 MP | — | 15 s | **killed** |
| 2.5 MP | — | 8 s | **killed** |

**No single formula predicts this.** `(4 × MP) × frames` scores 2596 for 0.9 MP/30 s, which
runs, and 2599 for 1.8 MP/15 s, which dies. Higher base resolution costs more than
linearly. `ltx_film.py` enforces the table and restarts a dead ComfyUI between scenes.

Speed: 5 s → 37 s · 10 s → 47 s · 20 s → 94 s · 30 s → 165 s.

**Interpolation has a much tighter envelope than generation.** Polish scenes, never the
assembled film: an 83 s cut is ~4000 output frames and kills the process. Capped at 25 s.

---

## 3. Writing a multishot prompt

It must be **one chronological paragraph**. Shot slugs (`Shot 1 … CUT TO Shot 2 …`) produce
**no cuts at all** — fifteen seconds of one take.

At every cut:

1. **Name the transition in prose** — "A hard cut transitions to…"
2. **Re-establish framing** — "…a medium side-on shot of…"
3. **Re-identify the subject** — "…the same cook in the black shirt…"
4. **State audio continuity** — "…continue unbroken across both cuts."

Two to four cuts per generation, each with one clear job. `beats()` in `ltx_film.py` builds
this shape so it cannot drift back into slug lines.

> **The rule underneath all of it:** each cut is a fresh shot description. *Anything not
> restated at the cut gets re-derived* — the character, the wardrobe, the style, the audio,
> and the absence of people.

---

## 4. Keeping people out of frame

Harder than it sounds, and it escalates. Try in this order:

1. **Restate the absence at every cut.** "No people in frame" in the opening plus
   `person, hands, face` in the negative is **not enough** — two of six product spots still
   grew a person after the first cut.
2. **Give the action a non-human cause.** A door that "swings open on its own" still
   summons someone; name the draught.
3. **Reframe so there is no space for a figure.** A dim corridor with a door opening *is*
   "someone arrives" in the training data, and no sentence beat it. Shooting the threshold
   from the floor did.
4. **Let only light, wind and water move.** Removing the person only changes who fills the
   agency slot: reframed to macro, an espresso grew a *whisk*, oats grew a *scoop*, and a
   forest trail grew a **cat**. Something has to act, unless the motion belongs to a force
   already in frame.

---

## 5. Dialogue

- Put the line in **quotation marks** and name the accent.
- **The speaker must be on screen.** Narration over an empty landscape produced no voice at
  all, just wind. LTX speaks through a visible mouth, never over a plate.
- One short sentence per shot. A paragraph does not land.
- Re-identify the speaker after every cut, like any other character.
- **Verify it, don't assume it:** a spectrogram of a speaking close-up shows a voiced
  harmonic stack with syllable gaps; ambience and effects show a broadband wash with none.
- **Lip sync is photoreal only.** In flat cel anime the voice is generated but the drawn
  mouth stays shut — the mouth region changes 0.43x as much as the whole frame, against
  1.01x for a photoreal talking head. Cut anime dialogue the way anime actually is: play
  the line over an over-shoulder, a back-of-head, or the listener's reaction.

---

## 6. Identity

- **Cross-scene identity is prompt-only.** A three-scene short came back with a different
  cook in every scene. **Anchor every scene to the same keyframe image** (`"image"` in the
  spec) and person, wardrobe, location and lighting all lock together. Faces still drift a
  little; costume and place carry the continuity.
- **One IPAdapter reference is applied to every face in the frame.** Two characters need
  `45_anime_two_char_ipadapter.json` — one adapter each, separated by attention masks, and
  the prompt must say who is on which side.
- **PLUS FACE biases composition, not just identity.** At weight 0.6 a reference sheet
  turned a wide shot of a bridge at night into a close portrait on a blank background. Keep
  **0.6 for portraits, ~0.3 for anything wide** (`ipa` per scene).
- Setting the weight to **0** is worse than either: it was holding the *style* too, and
  without it one background collapsed into noise.

---

## 7. Tooling

| File | Does |
|---|---|
| `scripts/ui2api.py` | Flattens any shipped ComfyUI template — subgraphs and all — into an API graph. This is what made LTX-2.5 reachable. |
| `studio/_tools/ltx_film.py` | Renders a film spec. Enforces the envelope, restarts ComfyUI, builds multishot prompts from structured beats. |
| `studio/_tools/polish.py` | 24 → 48 fps via FILM interpolation, **re-muxing the audio** (the interpolation workflow silently drops it). |
| `studio/specs_*.py` | One file per film. Prose lives here; mechanics live in the tools. |

### Two traps in `ui2api.py` worth remembering
- A dropdown is `["COMBO", {…}]`, not a bare list. `widgets_values` is **positional**, so a
  missed dropdown shifts every later widget by one.
- Mode 4 is a real **bypass** — drop the node and bridge its links, or it becomes mandatory.

### Reels
`scripts/make_reel.sh` cuts a showreel to an ACE-Step bed, keeping each clip's own location
sound quiet underneath so the wok still roars and the blade still rings.

### And one in the runner
`-s` used to leave `"false"` as a **string**, which is truthy. Every boolean switch silently
stayed on for a whole night. If a flag appears to do nothing, check the coercion before
suspecting the workflow.

---

# Part two: the shot doctrine and the /film editor

The first half of this playbook is the engine manual. This half is the FILM manual - how
shots are actually built here, and the editor that builds them. Most movie shots are under
six seconds; the unit of work is therefore ONE SHOT, meticulously specified, rendered as
competing takes, picked, and assembled. The editor at **/film** is these rules as software
- `studio/film.py` owns the model and the compilers, `studio/_tools/film_routes.py` owns
the render jobs, and nothing in the UI can forget a rule the compiler enforces.

## 8. The layer model - what one shot is made of

A shot is not a prompt. It is a stack of layers, each its own input, compiled into each
engine's dialect at render time:

| Layer | What it holds | Who consumes it |
|---|---|---|
| **framing** | one of the closed ANGLES list (wide establishing … extreme macro) | every engine's first noun |
| **camera move** | static, push in, pull back, pan, follow, circle, handheld, tilt | LTX phrases it; H3/Wan bake it into the sentence |
| **subject** | a CAST id (expanded to the appearance clause) or free text | all |
| **action** | the one committed event of the beat | all |
| **background action** | named, or it freezes - H3 animates only what the clause names | all |
| **dialogue** | char + line + delivery; quoted, with the character's voice description | LTX (photoreal lip sync); off-screen over cutaways in anime |
| **sfx** | named noises - an absence returns literal silence | LTX, H3 |
| **ambience** | the scene's continuous bed, "running under the whole shot and never stopping" | LTX |
| **music** | ACE-Step tags at SCENE level, mixed under at assembly | assembly |
| **transition in** | between beats, inside one LTX generation: hard cut, dissolve | LTX only |
| **transition out** | between shots, at assembly: cut, fade, dissolve, dip to black | ffmpeg |
| **duration / aspect** | clamped per engine envelope; portrait flips canvas + IPA weight | all |

A shot holds up to **4 beats**. On LTX the beats are real cuts inside one generation; on
H3 and Wan only beat 1 renders - which is exactly what makes the takes grid a fair fight:
same layers, three engines, pick the read you want.

## 9. The context system - film → scene → shot

Three levels, nearest wins, and every resolved value remembers which level supplied it
(`Film.resolved()`); the editor's **Context tab** is that table plus the compiled prompt
per engine, so clicking any point on the timeline answers "what is in force here, and what
will actually be sent."

- **FILM** carries what must survive the whole movie: the cast (appearance clause, short
  re-identification form, sheet, voice pack, voice description), the look and its style
  clause, the grade, the global negative.
- **SCENE** is a sub-context: location, time of day, weather, palette, who is present, the
  AMBIENCE bed, the music tags - and the **scene anchor**, one image every shot in the
  scene starts from by default. One keyframe holding person, wardrobe, place and light
  together is what kept CLOSING TIME and THE LAST REQUEST coherent; the anchor makes that
  the default rather than a discipline.
- **SHOT** owns its beats and layers, and can override `no_people`, the anchor mode
  (scene | prev_last | generate | file), and the enhancer.

## 10. Consistency, mechanised

- **Re-identification is automatic.** The first mention of a cast id compiles to the full
  appearance clause; every later mention in the same prompt compiles to "the same
  <short>". A character can no longer be lost at a cut by forgetting to re-name them.
- **Absence is automatic.** `no_people` injects the empty-frame clause into EVERY beat and
  extends the negative - and the compiler lints agent nouns, because a named hand grows a
  whole person and a starved agency slot once produced a cat.
- **Voices are per-character, twice over.** The `voice_desc` rides inside every spoken
  line ("says in a level, unhurried American accent"), which steadies LTX's native voice
  - and the **VO button** synthesizes the line through the character's assigned voice pack
  (ready packs only; the blocked real-person packs are excluded at the listing) and ducks
  it over the take, which is the strong form of consistency across a whole film.
- **Anchors bound drift.** scene → the scene anchor; prev_last → the previous shot's
  picked take, last frame; generate → a shot-specific keyframe through the right identity
  path with the IPAdapter weight chosen by framing (0.6 portrait, 0.3 wide - PLUS FACE
  hijacks composition at 0.6, and 0.0 loses the style anchor with the identity).

## 11. Takes - the picker is the point

"Generate takes" fans a shot out across LTX / H3 / Wan with seed variation. Every take
lands immutable with poster, filmstrip, its compile warnings, and a QC verdict measured on
the bytes (streams present, audio not flat, nothing frozen, no dead black) - because this
project's worst failures are files that exist, run the right length, and are wrong. The
first clean take auto-picks so assembly always has something; the grid exists so you
overrule it.

Engine character, one line each: **LTX** cuts, talks, and holds a scene - the default.
**H3** hits harder on one violent committed event and makes real pitch - the action
specialist. **Wan** reads motion differently and is silent - the second opinion.

## 12. Auto-next and assembly

**Auto next shot** drafts the following shot: anchor = previous picked take's last frame,
framing advanced one step along wide → medium → close and back, and with two cast present
the subject alternates - plain shot-reverse-shot. It is a draft to be edited, not an
oracle.

**Assemble** normalizes every picked take (1472×832, 24fps), joins shots per their
transition_out (xfade for anything that is not a cut), generates each scene's ACE-Step bed
(≤46s - it fades to silence past that - mixed under at 0.5), concatenates the scenes, and
QCs the result. The film lands at `studio/films/<id>/assets/film.mp4`.

## 13. What the editor will not save you from

The compiler lints, it does not direct. It cannot know that a beat is boring, that a cut
is in the wrong place, or that the line lands better unsaid. The takes grid is where taste
happens; everything else here just makes sure taste is the only thing left to supply.

## 14. The quality ladder - draft, pick, master

A take is a DRAFT until it is picked; a pick is a draft until it is mastered. The ladder,
each rung cheap enough to climb often:

1. **Draft** - one LTX take per shot, compiler defaults. "Draft all missing takes" on the
   Review tab walks the whole film in one job, so a complete rough cut of a new film is
   one click and a coffee.
2. **Pick** - the grid. Regenerate with a nudged seed (click a take's seed to reuse it) or
   different engines until one reads right.
3. **Master** - the picked take goes through FILM interpolation to 48fps with its audio
   re-muxed, landing as a new take that supersedes the pick. The 25s interpolation
   ceiling applies per shot, which is why mastering happens here and never on an assembly.
4. **Assemble** - runs at 48fps automatically once every pick is mastered, and at 24
   otherwise; a mix would stutter, so it is all or nothing by design.

## 15. Identity - portraits are the anchor of the anchor

Costume and place hold a film together, but photoreal FACES drift shot to shot unless
something pins them. The pin is the **portrait**: each cast member renders one from their
appearance clause (film tab), and from then on every photoreal scene anchor and every
generated per-shot keyframe goes through the two-reference edit with the portraits in -
the identity route this project measured, now applied automatically wherever cast are
present. Regenerate a scene's anchor after adding portraits and re-shoot its takes; takes
are immutable, so the old ones remain as history rather than being lost.

Anime identity still rides the character sheet through IPAdapter, weight by framing.

## 16. The sound of an assembled film

Three fixes that turned assemblies from "clips in a row" into one soundtrack:

- **Fades at every cut.** Each take generates its own ambience TEXTURE, and two rains are
  never the same rain - a 0.1s audio fade either side of every cut stops the texture
  jumping while the picture cuts hard.
- **Loudness is levelled at delivery.** Dialogue shots, music beds and raw ambience land
  at wildly different levels; the final pass runs single-pass loudnorm to -16 LUFS with a
  limiter behind it. Remember the older lesson: normalisation promotes the median - level
  the FILM, never an individual hit.
- **VO lands on its beat.** A synthesized line is delayed to the start of the beat that
  carries it (beats divide an LTX shot evenly), nudged 0.4s so the cut lands first and
  the voice follows - not stacked at the head of the shot.

## 17. Review before you believe

The Review tab is the discipline made visible: every scene as a row of picked posters,
the total picked runtime, and a blocking list - shots with no takes, takes unpicked,
picked takes with QC issues, cast without portraits. The rule it encodes is the oldest
one in this project: a render that completed is not a shot until something has LOOKED at
it, and the cheapest looking is a grid.

## 18. Photoreal identity, the whole truth

Measured across seven re-shoots of the same film, so it does not have to be relearned:

- **A portrait pins a keyframe.** Anchors and generated keyframes through the
  two-reference edit carry the portrait's exact face. Proven repeatedly.
- **Two references need SIDES.** "On the left stands the woman from the first reference
  image with her exact same face unchanged, …" held both faces; naming refs abstractly or
  photo-language lost one. And even sides is a **seed lottery** - so anchors render three
  candidates and the Scene tab makes picking one a click. A lottery is what a picker is
  for.
- **An internal LTX cut re-derives faces from the scene prior.** The start frame's face
  does not survive a hard cut inside the generation, and facial traits written into the
  clause do not overpower a strong scene prior either. The compiler warns when a
  multi-beat photoreal shot carries portrait cast.
- **The grammar that works: cut in the EDIT, not in the generation.** Identity-critical
  moments are ONE-beat shots from identity keyframes (the beat's subject leads the
  keyframe; close framings use that person's portrait alone), joined by assembly cuts.
  Wide multi-beat shots are geography - identity there is clause-level, and that is fine
  because nobody reads a face at forty pixels.

Anime is different: costume and hair silhouette carry identity through cuts, which is why
FIRST LIGHT never had this problem.

## §19  The foundry: build by selecting

Freestyle prompt-writing is the hardest interface we ship. The untrained eye
cannot describe what it wants in one pass with enough detail; it can only
*recognise* it. The foundry turns that recognition into the workflow: every
creative decision is a selector, every selector option carries a hidden prompt
fragment, and the compiled prompt rides along with the asset where nobody has
to read it.

**Main variables are entities; sub-variables are their selectors.**
`style`, `character`, `place`, `costume`, `prop`, `music` are main. Face
shape, hair colour, time of day, closure, aura, tempo are sub. A main
variable owns files on disk (`studio/foundry/<type>s/<id>/`); a sub variable
only ever contributes a fragment to its main's compile. Voice is a sub of
character — offered dynamically from the ready voice packs, never from the
dictionary file (blocked packs must not appear).

**The dictionary is the single source of truth** (`studio/foundry/dictionary.json`,
6 mains / 35 subs / 254 options). The UI renders its forms *generically* from
it: adding an option (or a whole sub) is a data edit, not a UI edit. Each
style in the spectrum (photoreal → cinematic → noir → watercolour → anime →
cartoon → claymation → pixel) carries its own `look_clause`, negative, and
keyframe engine (`qwen` for photographic styles, `animagine` for drawn ones).

**Compile rules learned the hard way:**
- The prose clause and the danbooru tag stack are compiled SEPARATELY and
  consumed by different engines (clause → LTX prose; tags → animagine
  keyframes). Anything appended to only one of them silently fails on the
  other — free-text notes must join BOTH.
- Age and facial hair must be explicit tags. Silver hair alone reads as a
  young bishounen to animagine, never as an elder; "old man, elderly,
  wrinkles, beard" lands what "grey hair, 70s" cannot.
- `beast → "creature"` draws emblems and heraldry, not animals. Use
  "no humans, animal focus, full body" plus the species in notes.
- Grammar assembly matters: fragments join as "a short, slightly built
  woman", article first — naive joins produce "short slightly built a woman"
  and the model draws the confusion.

**Seed packs are the point.** Creating an asset stores selections; *seeding*
it renders the reference images every later render hangs on: characters get
portrait + full body + three turnarounds (drawn styles turn through their own
IPAdapter self-reference at 0.55, photographic styles through the
multiple-angles LoRA of wf32); places get wide/reverse/detail × every
selected time of day; costumes get a garment card; props get hero + macro.
Assets are film-independent. `send_to_film` COPIES files into the film so
films stay self-contained — the same library place can dress two films, the
demo being the night-market serving scene 1 (night) and scene 5 (dawn) of the
same film as two different scenes.

**Costume × character is a render, not a caption.** `apply` re-renders the
character full-body wearing the costume (drawn styles: self-ref chain + wear
tags; photo styles: wf14 two-reference edit). The applied image becomes the
identity sheet the film anchors on, so a cast swap mid-film ("Jin changes
into festival silks between scenes 4 and 5") is one more `send` with a
different costume id.

**ensure_local() is download-if-missing.** Any pipeline that re-renders into
an existing path must delete the file first or the GPU burns and the stale
file survives, which looks *identical* to "the render worked". Detection
without a consumer, file edition.

## §20  Directing from selectors: what the 3-minute film proved

THE LANTERN THIEF (~3 min, anime, 5 scenes / 11 shots) was made end-to-end
from foundry assets: zero free-written look prompts — every character, place,
costume, prop and music bed came from selector choices, and the shot list
only wrote *actions* (what happens), never *appearances* (what things look
like). The division of labour is the doctrine:

- **Appearance lives in assets.** The compiler splices each cast member's
  full compiled clause (including their costume's wear text) into every beat
  that names them — re-identification at every cut for free, from data.
- **Action lives in beats.** A beat is framing + move + subject + action +
  background + optional dialogue. Beats stay short; the compiled paragraph
  gets long. That is correct — length from data, not from typing.
- **Sound lives twice**: the place's ambience bed (from the base + weather
  selectors) runs under every shot in the scene; the shot's own sfx line
  adds the named noises. Both restated as continuing unbroken across cuts.
- **Music is a selector too** (mood × tempo × instruments → ACE tags), sent
  per-scene, mixed at assembly under the location sound.
- **Anime dialogue is VO, not lip-sync** — drawn mouths do not move. Keep
  lines short, prefer two-shots/off-angles for spoken beats, let delivery
  descriptors ("a wry whisper") do the acting.

## §21  The compositor: putting a built character in a built place

Words always combined — every asset compiles to a clause and clauses
concatenate. **Images did not.** A shot was one image plus words: either the
scene anchor won and the character was re-derived from text, or IPAdapter won
and the place was. `studio/_tools/compose.py` makes the two composable.

**Handing both images to qwen-image-edit and asking for one inside the other
makes a good picture of a DIFFERENT place.** Measured: the left margin of a
"relit" composite sat **0.187** from the original plate, against **0.211** for
that same market at a different time of day. The model does not edit locally, it
regenerates. So anything you care about has to be kept out of its reach:

    1 paste     the character's cutout onto the plate at a stated scale
    2 relight   through qwen-image-edit, which fixes the light and wrecks the plate
    3 re-cut    take ONLY the relit character back out
    4 shadow    ground her geometrically
    5 paste     onto the PRISTINE plate, which was never model-touched

Plate fidelity after step 5 is **0.000–0.007** on full framings. The place in the
shot *is* the asset, not a picture of something like it.

**The relight runs on its own canvas, never at the final framing.** Two bugs
proved why: `qwen_edit` had its output size hardcoded to a different aspect than
the plates, so every relight squashed its input (shortened legs); and pasting at
the final framing put the feet past the bottom edge, so `_trim()` returned a
legless figure that was then scaled to full height as if whole.

**The guard is PROPORTION, not edges.** The relight also *recomposes* — a
standing figure came back as a bust from the hips up, touching no edge at all,
and was placed with its hips on the ground as if they were feet. A cutout of the
same person keeps its aspect ratio however it is lit, so a silhouette that
changes shape by more than a quarter is refused and falls back to the source
cutout tinted to the plate: flat light, but a body with legs, and it says which
it used.

**A bigger figure on the relight canvas drifts LESS.** The intuition is
backwards and cost two runs:

| relight canvas | shape drift |
|---|---|
| figure at 0.66, bottom-anchored | 16 % |
| figure at 0.52, centred | 30–37 % |

More empty background gives the model more room to decide the shot is a
different shot. A figure that dominates the canvas is the one it leaves alone.

**The shadow is geometric, not prompted** — the same reason `bobble.py` cuts
heads off meshes. A contact pool at the feet plus a sheared silhouette cast. The
first numbers were invisible (mean diff 26/255 against warm pavement, which
looks exactly like no shadow), so the pool is wider than the figure and nearly
opaque.

## §22  Ground placement comes from depth, not from a table

`--stand` is one dial: 0 at the camera, 1 at the horizon. **Where the feet land
AND how tall she is both follow from it**, because on flat ground an upright
figure's apparent height is proportional to how far below the horizon the feet
are. Measured on one plate: `stand=0.28` → 476 px, `stand=0.72` → 186 px, from
one number. A figure can no longer be far away and gigantic at once.

**The horizon is where the ground stops receding, not where depth is greatest.**
The first detector took the farthest row, which in any frame with sky *is* the
sky — so two plates silently returned the clamp, the detector having found
nothing and reported its floor as an answer. Read bottom-up, depth climbs as the
ground recedes and turns over at the horizon:

    harbour-dawn   96%:0.04  80%:0.09  64%:0.21  56%:0.28  48%:0.29  40%:0.25
    rain-street    96%:0.02  80%:0.09  64%:0.21  56%:0.19

Walking up until it turns over gives 53 % and 69 %, which match a hand-read of
the same images.

**Depth does not know what is standable.** Water and a road are identical to it;
`--cx` stays a human choice. Depth only guarantees the figure is on the ground
plane at a consistent scale.

Two engine traps re-confirmed here: `DA3Render.output` is a dynamic combo whose
chosen option carries its own namespaced required inputs
(`output.normalization`, `output.apply_sky_clip`), and the H3 node hardcodes
768×1344 and renders portrait **in silence** unless width and height are passed.

## §23  Motion: requested is advisory, pinned is real

**Prose cannot direct action on LTX.** Verified by a person watching four clips:
she never crouched; she never turned; rain fell only in one streetlight's cone;
and the clip whose camera was selected *static* zoomed in. Three suspects were
isolated one at a time and **all three were wrong**:

| suspect | test | result |
|---|---|---|
| the enhancer rewrites the prompt | turned off | no change |
| `static` maps to `("static", "")` — nothing says the camera holds | added an explicit locked-off-tripod clause | no change |
| the action sits ~50 words deep | moved it first, in capitals | no change |

And the anchor is not at fault: frame 0 measures 0.081 from the composite, which
is only LTX resampling. **It is an engine prior.** LTX-2.5 i2v has its own idea
of a person in a street and follows it.

So every camera option carries `enforced`. **Only `pinned` is true.**

**Pinning both ends makes motion deterministic.** H3's `fl2va` takes a first and
a last frame, so the action stops being a request and becomes the interpolation
between two states you choose. Same crouch, pinned: she lowers across all 192
frames and the framing holds. The end state costs one still and no new asset —
it is an *edit of the start frame*, so the person, place, camera and light are
already right and only the pose changes.

**A pin needs enough change PER SECOND, not enough change.** Two nearly identical
frames leave the model seconds to fill with no motion, and it fills them by
inventing — a second copy of the subject, fire on the water:

| change | subject distance | seconds | per second | result |
|---|---|---|---|---|
| standing → crouched | 0.103 | 8.00 | 0.0129 | good |
| forward → head turned | 0.043 | 8.00 | **0.0054** | invented |
| forward → head turned | 0.043 | 3.75 | 0.0115 | good |

`pin_shot` refuses below **0.009/s** and says the longest duration that pair can
carry. Three points is not a calibration; the floor sits where the evidence is.

Pinned is **near**-locked, not locked: a slight handheld drift, no dolly or zoom.

## §24  The one-beat rule was measuring the anchor

§18 says an internal cut re-derives faces, so identity moments must be one-beat
shots cut at assembly. That cost THE LANTERN THIEF nineteen renders where five
or six would have done — **and it was established when anchors were scene
plates.**

Same two beats, same prompt, differing only in the first frame:

- **composite anchor** — the same woman throughout. Medium, then close-up, and
  it is her in both: same face, same braid, same freckles.
- **plate anchor** — the first half is an empty street with one distant figure,
  and the close-up after the transition is a **different woman entirely**.

A plate anchor does not put the character in the frame at all, let alone hold
her through a cut. **So the rule holds for plate anchors and does not apply to
composited ones**, and multi-beat shots are safe when the character is in the
start frame.

Not established: whether LTX rendered an actual hard cut. A frame-delta detector
scores this clip 3.3× against 1.7× for a multishot previously accepted as having
real cuts — a known-good clip scoring lower means the metric is wrong, so it
cannot separate a cut from a fast push. The identity conclusion does not rest on
it: the post-transition face is either the same person or not, and that is
directly visible.

## §25  Resolution is a trade, and triage says which side you are on

The film's resolution used to be derived and silent: LTX took the largest
megapixel count the shot's length permitted, so an 8s shot came out near 1080p
and a 30s shot at 720p, and nothing told the director that shortening the shot
would sharpen it.

A film now carries a **resolution target**, chosen when it is created or
changed in the Film tab:

| target | MP  | longest shot it permits |
|--------|-----|-------------------------|
| auto   | -   | the biggest the length allows (old behaviour) |
| 720p   | 0.9 | 30s |
| 1080p  | 1.5 | 12s |
| max    | 2.0 | 8s  |

The envelope (`LTX_SAFE`) is measured and does not bend. A 20s shot in a 1080p
film still renders - at 1.2 MP - and its compile carries a warning that says
exactly what to do: *cut this shot to 12s or less*. A 6s shot in that film
renders at 1.5 MP, not 2.0, because the target is a target: a film wants one
resolution across its cuts more than it wants one shot sharper than the rest.

**Triage** answers the question "what do we make here and what needs API
help", per shot, from the same envelope, in words:

- **local** - inside every measured limit.
- **trade-off** - it renders here, but something asked for will not be honoured
  as written: resolution below target; a camera move on LTX (advisory - the
  engine keeps its prior); a multi-beat character shot without a composed anchor
  (the face will not survive the cut); anime dialogue (voice yes, lip sync no).
- **api** - beyond this box: one shot over 30s; more than two identities that
  must hold in one frame; native 4K.

The Review tab shows the counts and, for every non-local shot, the reasons.
They are instructions, not grades. `deliver` (an upscale at master time) exists
on the film but is withheld from the UI until an upscaler is wired; the
LTX latent upsampler in workflow 17 is the candidate, untested on 2.5 latents.

## §26  Pin preview, and why the end frame must sit on the pristine plate

A pin costs one qwen-edit (seconds) and one H3 interpolation (minutes), and the
result could not be judged until the minutes were spent. **Preview end** stops
after the edit: the end frame is shown beside its verdict - enough change for
these seconds, or too alike, with the longest span the pair could carry. The
pin then reuses that exact file, so what was approved is what is interpolated.

Looking at the frame found the real defect. qwen-edit **regenerates**, however
firmly it is told to keep the background: the crouch came back correct and the
car had moved from the centre of the street to the right, the lamp post had
shifted, the signage had changed. H3 interpolated the sliding car as faithfully
as the crouch. That is the "slightly handheld" drift in the pinned shots, and
the shifted ground plane is the likeliest reason her feet started inside it.

The fix is the compositor's own three steps applied to the end frame: cut the
figure out of the regeneration and put it back on the **pristine plate** with
its shadow. Both ends of the pin then share one background, pixel for pixel,
and H3 has nothing to invent behind her. Requires a composed anchor, because
that is the only case where the plate is known; `anchor_source` now records it.

**The floor had to move.** `MIN_PIN_RATE = 0.009` was calibrated on end frames
with regenerated backgrounds. The same verified crouch measures 0.0123/s that
way and 0.0052/s against the pristine plate - more than half the "change" the
old floor was seeing was the car. Plate-composited ends use
`MIN_PIN_RATE_PLATE = 0.0026`, half the one verified interpolation. That is one
data point and the code says so; the three-measurement calibration behind the
old floor should be repeated on the new footing. The verdict is advice: the pin
route takes `force`, and the editor shows **pin anyway** when the preview says
too alike, because the director has looked at both frames and the number has
not.

General lesson, worth carrying to any change metric: **a distance that includes
the background measures the regeneration, not the subject.** Mask to what is
meant to change, or hold everything else fixed first.

## §27  Props are layers

A prop pack's `hero` view is a cutout waiting to happen. The compositor now
takes `props=[{id, stand, cx}]`, cuts each one, sizes it from the same depth
pass that sizes the character - scaled by what it is, in metres, from the
dictionary category (`PROP_M`: lantern 0.4, sword 1.0, staff 1.7 ... default
0.5; an asset can override with `size_m`) - and pastes all layers far to near,
each with its own contact shadow. So a lantern at her feet is lantern-sized
next to her and a lantern near the camera is big, and whichever is closer
overlaps whichever is behind.

Verified: bai-liwen in night-market with paper-lantern at stand 0.28 - a small
lantern on the ground in front of her, with a shadow, plate fidelity R=0.0037
(the lantern is the only change on that side). Props sit on the ground line;
a hanging prop wants a height-above-ground offset that does not exist yet.

## §28  Motion and ambient on every beat

Two measured facts shape the beat selectors. LTX animates what the prose
**names** and freezes what it does not, so **ambient** (rain, lanterns,
traffic, crowd, water, steam ...) is not decoration: its frags join the beat's
background clause and are the difference between a living street and a still
one. And LTX does not take direction on the subject's action from prose, so
**motion** is labelled advisory there and its real job is the pin: each action
in the dictionary now has an `end` phrasing ("lowers into a crouch" is what
happens; "has lowered into a deep crouch, knees bent, weight low" is what the
end frame shows), and picking a motion prefills the pin's sentence with it.
Both compile into H3 prompts too; on H3 an unnamed background still freezes,
and the warning now says to pick ambient motion.

## §29  The end figure is constrained, not requested - and the prose must describe the anchor

THE HARBOUR LETTER was made entirely through the API the Shot tab exposes:
eight shots, two scenes, composed anchors, three pins, ambient selectors,
scene music, assembly. Its contact sheets found three faults, all of the same
species: the engine did exactly what it was given.

**The end figure drifts in scale.** qwen-edit was told "same camera position,
same framing, only the pose changes". It returned the crouch with the woman a
quarter nearer the camera (head 76 px against 61 in the start frame). Pasted
where the regeneration put her, the end frame said "walked forward, then
crouched", and H3 interpolated that: she grows for three seconds before she
bends. Asked for "walked closer", it returned a medium shot - four times the
head width, thirty metres in eight seconds - and H3 bridged the gap by
inventing willow trees that slid past her.

An edit model regenerates composition as well as content; nothing in the
sentence anchors scale. So the end figure is now **constrained** from the
anchor recipe (`anchor_source`: stand, cx, plate) instead of asked for:

- **In-place motions** (crouch, rise, turn, look, reach, gesture, nod): the
  end figure's bottom goes on the start figure's ground line from the depth
  pass, centred on the same x, and it is scaled so its **head is as wide as the
  start figure's head**. Head width is the one measure of a person that a
  change of pose leaves alone; height, width and bounding box all move with the
  pose. The start silhouette is recovered as the difference between the start
  frame and the pristine plate.
- **Moving motions** (walk_to, walk_away, run): the change of scale is clamped
  to 0.6-1.6x by head width, and the feet go where the plate's own depth puts a
  figure of that height - the inverse of `place_by_depth` - so a larger figure
  is lower in the frame by exactly the amount the plate implies.
- `hold_feet` chooses between them. The editor's **feet planted** box follows
  the motion selector (off for walk_to / walk_away / run). Left unset, the
  change sentence decides (walk, closer, further, run ...).

Verified on shot B re-pinned: she bends in place across eight seconds, same
feet, same size, the cars and the lamp post fixed behind her, and H3 drew the
envelope she reaches for from the pin prompt. Measured: held in place the
crouch is 0.0028-0.0032/s; the plate floor is 0.002.

**Prose that contradicts the anchor rewrites it.** The "harbour" place pack is
a stone arch bridge over slow water in fog (base: bridge). The prose said
boats, moorings, a quay. By the fourth second LTX had turned the bridge into a
marina with a dozen boats. This is "unnamed backgrounds freeze" seen from the
other side: words that name things the anchor lacks are instructions to leave
the anchor. The Shot tab now has **check prose against anchor** - one vision
call captions the anchor, and every content word in the beats and the scene
location that the caption does not contain is listed on the shot. Change the
words or change the plate; the engine will not split the difference.

**Two things the compositor still does not know.** A ground line from depth
does not know water from stone: at stand 0.40 on the bridge plate, Doran stands
on the river. And a turn on a small distant figure measures below any floor
(0.0013/s) - the frame-wide rate shrinks with distance. A subject-region change
is now logged beside it for calibration; until it gates, the preview's "pin
anyway" is the director's override.

**Amendment, measured twice the same night: H3 fl2va holds the pinned frames for
in-place motion only.** Shot F was pinned twice - first with the oversized end
figure, then with the clamped one on the pristine plate - and both times the
result showed willow trees and a grass path from **frame 0**, when the start
frame is a small figure in a river under a stone arch with no tree in it. For
a walk toward the camera, H3's own prior (a tracking shot down a path) took
over and regenerated the scene; the two conditioning frames were advice.
Shot B, a crouch in place, honoured both frames exactly. So: **pin in-place
motions on H3; do not pin walks.** A walk wants LTX i2v from the composed
anchor (LTX holds the plate, see shots C and G) with the motion as prose - and
prose is advisory there, so the honest expectation for a walk on this box is a
push-in on a standing figure, or a cut. The end-figure geometry for moving
motions stays, because a correct end frame is still the precondition for the
day the interpolator honours it.

## §30  The library grows only through its own QC

Fifteen assets in twelve minutes (four characters, five places, six props - all
invented) is the good news. The sheet showed two failures the packs had already
detected and shipped anyway:

- **A cropped base poisons the pack.** Ines Varga's `base_fullbody` came back
  knees-up; every turnaround view is derived from it, so all five turns were
  knees-up and she would have composited with no legs - the defect the director
  has flagged twice. The full-length prompt was there; the photographic model
  declined it for a long coat with hands in pockets. Four seeds in a row gave
  gap=0.000 (the figure touching the bottom edge) - **a seed does not move a
  composition prior; words do.** The seeds job now checks the base with
  `pack_qc._truncated` and re-rolls: two seeds on the prompt as written, then
  two with a far framing sentence (small in frame, empty space above the head,
  the floor under both shoes).
- **A prop hero must be one whole object.** The red umbrella came back as a
  sliver at the frame edge, the oil lantern and the iron key as pairs - useless
  as cutouts. The hero render is checked on the segmenter's mask (no edge
  contact, one contiguous horizontal run) and re-rolls, saying "exactly one
  single ... nothing else in the picture" on the later tries. Umbrella: whole on
  seed 43. Lantern: single on the third try.

The pattern is the one from §16 again - detection without a consumer ships the
defect. Every detector the packs already run (truncation, expression, prop
wholeness) should gate the render it judges, with a bounded retry and a log
line that says which attempt won.

**Naming assets for what they are.** The place called "harbour-dawn" is a stone
arch bridge over slow water in fog (base: bridge). The compiled description
says so; the name did not, and a shot list written from the name put boats on
it. Name places by their base and condition, or read the description before
writing the prose - and run the anchor check either way.

## §31  A second character is a layer; props are set dressing; the night in numbers

**Two-shots from packs.** A character view is a cutout like a prop with a known
height, so a compose layer may now name a character instead of a prop
(`{"character": id, "view": "turn_side", "stand", "cx"}`). The second figure is
tinted to the plate rather than relit - relight regenerates, and two
regenerations in one frame are two chances to lose a face - grounded with its
own shadow and pasted far to near with everything else. Mara and Doran under
the bridge, one compose, one LTX take: both identities hold for six seconds and
she turns her head to him. Triage still calls three identities an API shot;
two is now a deterministic composite, not a graph.

**Props are set dressing, hands are identity.** Shot F of THE FERRYMAN'S BOOK
put the red umbrella on the ground beside Renji and wrote "rain running off the
umbrella" as if he held it. LTX kept the words: the umbrella vanished under
the push-in and he held a book instead. A prop that must be *held* has to be
in the character's pack (say it in the notes and it renders into every view);
the compositor's props are things that stand, sit or hang in the scene at a
distance from the subject. The anchor check said so before the render - "book"
was in the prose and not in the picture - and was ignored. Read it.

**The second film, as workflow.** Six shots, two scenes, 44s, anime, from the
night's new library, with the first film's lessons as procedure: every anchor
captioned and checked before anything rendered; only in-place motions pinned
(the crouch at the shrine, the Ferryman's raised pole - both held in place at
0.0063/s and 0.0022/s); ambient named on every beat; scene music from tags.
Two pins, four LTX takes, one assembly, no retakes needed for continuity - the
retake was for meaning (the umbrella), and the tool that would have prevented it
already existed.

**Numbers.** Two films made entirely through the API the Shot tab exposes
(56s photoreal, 44s anime, both mastered to 48 fps at 1472x832). Fifteen new
level-1 assets in twelve minutes plus two re-seeds for QC. Compose 16-20s;
pin preview 15-25s; H3 pin 96-144s for 6-8s; LTX take 78-112s for 6-8s at
2.0 MP; master ~40-60s a shot; ACE-Step scene music 6-9s a bed. Ten commits.
Seven playbook sections (§25-31).

**Open, honestly.** A delivery upscale at master time (the field exists; the
LTX latent upsampler in workflow 17 is the candidate, untested on 2.5 latents).
A ground line that knows water from stone (three characters stood in rivers
tonight). Character levels 2-5 executing. The subject-region change floor with
more than one calibration point. And H3 fl2va for walks - which today means:
do not.

## §32  Coverage: the scene starts with its standard shots

A director does not begin a scene by inventing shots. They begin with
coverage - the wide, the two-shot, the singles, the insert - and then decide what
happens in each. The Scene tab now does that in one click from selectors:

- **place** and **plate** (from the foundry), one or two **cast** members with
  their **packs**, an optional **prop**;
- the wide, empty, on the plate itself; the wide with the cast (a two-shot when
  there are two, the second as a compositor layer, the prop as set dressing);
  a medium on each; an insert on the plate's `_detail` sibling;
- every character shot gets a **composed anchor**, every anchor is **checked
  against its prose**, every beat gets **ambient** from the scene's weather and
  the place's base (rain/storm -> rain, cloth; boat/beach/bridge -> water;
  market/station/cityscape with a crowd -> crowd), and the actions are left as
  the director's blanks - "describe the beat".

Measured: Ines and Tomas on the harbour boat, five shots, three composed
anchors, all checked, 72 seconds. The cast entry remembers its pack
(`foundry`) so the next coverage needs no asking. From there the Review tab's
"draft every missing shot" renders takes for the lot.

**The anchor check, as it settled.** Six passes in one night, each removing a
class of false positive: the captioner had to be asked about the scene and not
the person; verbs and adverbs went; then adjectives and participles (moored,
swaying, weathered); then a small literal synonym map (shrine~temple,
cedar~tree, quay~dock, tarmac~asphalt, hull~boat); then body parts, pose verbs
and light words (face, hand, points, sodium, streaks); then cast names and
coverage's placeholders. What remains is what a picture can lack: the letter
that is not in the anchor, the footbridge the plate is not, the book in the
prose and not in the frame. It is advice on the shot and a trade-off in triage,
and it was right every time the director was wrong tonight.

## §33  Coverage, then dialogue: THE LAST BOAT

The fourth film of the night is the workflow the whole app was reaching for.
One click of coverage on a scene (Ines and Tomas, the harbour boat, the oil
lantern) made five shots with composed, checked anchors in 72 seconds. The
director's entire remaining work was three sentences:

    TOMAS  Last boat's not coming back tonight, Ines.
    INES   Then we wait with the light on.
    TOMAS  Aye. We wait.

put on the two-shot and the two singles as dialogue beats, with a delivery note
each and the speaker named. "Draft every missing shot", assemble. LTX speaks
through the on-screen mouth (§6): the dialogue takes peak at -6.5 and -7.4 dB
against -19.7 for the empty wide, and the sheet shows both mouths open
mid-line. Thirty-two seconds, QC clean, ~8 minutes of GPU, no retakes.

Voices are described, not cloned: the cast entry carries a synthetic voice pack
name and a description ("a warm, gravelly older man's voice"), and the
description is what reaches the prose. The four cloned packs in studio/voices
stay blocked.

The verify page carries the three questions that matter and that only a person
can answer: is it *her* voice, is the mouth moving *with* the words, and in the
two-shot is it *Tomas* speaking and not Ines.

**The night, closed.** Four films through the API (56s, 44s, 40s, 32s), 22 new
level-1 assets, coverage on the Scene tab, fifteen commits, playbook §25-33.
The director's work in the last film was three sentences. That is the ratio the
studio exists for.

## §34  Delivery upscale, measured: possible overnight, not as a master step

The `deliver` field (native / 1080p / 4k) has waited all night for an upscaler.
The box has the nodes for one with no downloads: core `LoadVideo` ->
`GetVideoComponents` -> `UpscaleModelLoader` (RealESRGAN_x4plus, the only
upscale model on disk) -> `ImageUpscaleWithModel` -> `ImageScaleBy` 0.5 ->
`CreateVideo` -> `SaveVideo`, run in chunks so the float batch fits in RAM
(12 frames of 1920x1088 at x4 is a 4.4 GB tensor; the box has 60 GB with
about 18 free while the studio is up).

Measured on a 6s dialogue take: **40 seconds per 12-frame chunk** - x4 on
1920x1088 is 7680x4352 per frame, roughly 3.3 s a frame on the 5090 before the
lanczos halving - so **~80x realtime**. A 56-second film is about 75 minutes;
the 3:08 LANTERN THIEF would be four hours. The third chunk then stalled in
ComfyUI with the GPU at 1% (the CPU-side halving or the encode; not
investigated further at 04:25). Interrupted; nothing left in the queue.

Verdict: a frame-wise RealESRGAN pass is a *deliverable*, not a master step -
something to start and walk away from, chunked and resumable, if it is wanted
at all. Two cheaper paths remain: a 2x ESRGAN model would cut the work about
fourfold (none is on disk; downloading one is the director's call), and the LTX
latent upsampler already inside the 2.5 pipeline is the only route that adds
detail the model meant rather than texture an upscaler guessed - untested on its
own past the pipeline's second pass. `deliver` stays in the film's data and out
of the UI until one of those is measured.

**Third pass (04:50).** With the end figure held in place, the same turn that
measured 0.0013/s at the old placement measured 0.0023/s - above the plate
floor - and pinned: Doran turns from side-on to camera in place, background
fixed. H3 also invented gulls in the fog and a dark smudge at his feet that
neither frame contains; the turn itself is real. The walk went to LTX from the
composed anchor: she stays put, the fog thickens and thins, the scene holds.
Both takes are on the verify page for the director's verdict; the film in the
repo carries the third pass.

## §35  The second block: nobody in the river, one button, and a take that checks itself

Two invariants for this block: a person with no knowledge of AI must be able to
use it, and what comes out must be right. Four things followed.

**Footing.** The ground line comes from depth and depth does not know water from
stone; three characters stood in rivers. Before a figure (or a prop, or a second
character) is placed, the plate is asked - one vision call with a red marker at
the intended feet: "what surface is under the marker?" Water moves the search
along the ground line (+-0.12, +-0.24, +-0.34), then a step nearer, then a step
farther, until the answer is solid. The river plate answered water four times
and stone at the left bank, in eleven seconds; the street plate kept its spot in
two. The adjusted stand and cx go into the recipe and into `anchor_source`, so
the pin's held geometry uses where she actually stands.

**The second character is relit.** It was tinted to the plate's mean colour -
flat next to the relit first figure. It now goes through the same rough paste,
relight and re-cut on its own before it is placed, with the same 25% proportion
guard and the tint as fallback. Twelve more seconds a two-shot.

**Make this shot.** One button on the Shot tab. It does what the measured laws
say, in order, and says so in plain words: puts the named character into the
scene's place (the scene now carries a foundry place and plate, set on the
Scene tab or by coverage); checks the words against the picture and lists what
the picture lacks; animates an in-place motion as a pose change (end pose first,
then the interpolation; rendering instead if the change is too small) or renders
the shot; picks the result. The expert controls fold under "Advanced" with
plain labels - distance and position instead of stand and cx, "put them in the
scene" instead of compose, "pose change" instead of pin, "start picture" instead
of anchor. Tested on a fresh shot: MARA crouching for a coin on the rain street -
placed, checked ("coin, road" not in the picture), end pose previewed, pinned,
132 seconds, correct.

**A take checks itself for drift.** LTX rewrites the scene mid-shot and nothing
measured it. Every rendered take now has its last frame captioned and compared
with the start picture's caption; the nouns the start has and the last frame
lost are the drift. Calibrated on the night's takes: the take that turned the
bridge into a marina lost 72%; takes that held their scene lost 9-29%; one
uncertain take 50%. The limit is 60%. Over it, "scene drift" is a QC issue on
the take (it is not auto-picked) and Make renders once more on a new seed and
keeps the take with fewer issues. Two vision calls a take, about seven seconds.
One lesson in passing: `_render_take` has two render paths (camera rig, and
LTX/H3) with a QC line each - the first version of the check landed on the
wrong one and reported nothing for three renders. When a consumer reports
nothing, check that it is on the path.

## §36  Start here; make every missing shot; pins that describe their scene

**Start here.** A page, first in the nav, for a person who has never used an AI
tool: three steps - choose your people, choose your places, make a film - in
plain words, with what to expect (a shot takes one to three minutes; the Review
tab says what will differ from what you asked and why) and a short table of
what the studio does well and what it does not do yet. No term of art on it.
The Foundry page's buttons followed: "make the pictures" for the seed pack,
"how complete" for the level, "dress them in this" for a costume.

**Make every missing shot, then assemble.** The Review tab's one button runs
Make on every shot without a picked take, in order, and assembles with the
scene music. With coverage this is the whole flow for a non-expert: a scene
with a place, coverage, one sentence per shot (and a spoken line where wanted),
one button, wait. Measured on THE STATION MASTER (five shots, two lines) -
see below.

**Pins describe their own scene.** The H3 prompt used to be the change plus
"the camera does not move", and H3 filled the fog with gulls it was never asked
for. The prompt now also states what the scene is - the place's compiled
description - and that it stays exactly as it is. On shot E of THE HARBOUR
LETTER the turn is unchanged and the gulls and the smudge are gone. One sample,
consistent with the rule that has held all night: give the prior something
true to hold, because it will not hold an absence.

## §37  A film starts with a form; a take carries its own verdicts

**New film, the way a person starts one.** Title, look, size - and where the
first scene happens and who is in it, all on the new-film form. The studio
makes the cast from the packs (a cast id from the NAME: RENJI, INES, KEEPER -
the first version took it from the appearance clause and produced a cast member
called BLACK), the first scene with its place and the place's own weather and
ambience, and lays out the coverage. The first thing a new user sees is a
timeline with shots in it and people in the pictures. Nothing to fill in but
what happens.

**Verdicts ride on the take.** THE STATION MASTER, made by coverage and one
button, came out right in four shots of five. The fifth asked for "wind moving
a scrap of paper along the platform"; the picture had no paper; the anchor
check said so; the render grew a sheet the size of a bench flapping across the
frame. The check was right and nothing consumed it. Now a rendered take carries
three verdicts as QC notes, so the Review tab shows them and the auto-pick
prefers a clean take: **scene drift** (last frame vs start picture, limit 60%),
**the line may not have been spoken** (a dialogue take whose audio peaks below
-14 dB; lines measured -3.8 to -7.4 dB, an empty street -19.7), and **words not
in the picture** (the anchor check's list). Make renders once more on a new
seed when the first two fire.

**Small things that were not small.** The jobs list showed the twelve most
recent jobs; a long make-all spawned enough sub-jobs to push itself off the list
while running, so the editor stopped following it and a polling script waited
forever. Running jobs are now always listed. And `_render_take` has two render
paths with a QC line each; the drift check first landed on the camera-rig one
and reported nothing for three renders. When a consumer reports nothing, check
that it is on the path that runs.

## §38  Two films from the form, and what their faults taught

THE STATION MASTER and NIGHT DINER were made the way a new user would make
them: the new-film form (title, look, size, where the first scene happens, who
is in it), one sentence per shot, a spoken line or two, "Make every missing
shot, then assemble". Thirty seconds each, about twelve minutes of waiting.

What was right: every person kept their face; the pose changes (look up, laugh)
happened in place; the lines were spoken and measured (peaks -3.8 to -8.8 dB);
nobody stood on water; the scene held in eight shots of ten.

What was not, and what each fault changed:

- **The insert grew things the picture never had** - a giant sheet of paper on
  the platform, coffee cups on the diner counter - because the sentence named
  them. The anchor check had said so and nothing consumed it. Now the check's
  words ride on the take as a QC note and the auto-pick prefers a clean take.
  The rule for the person: describe what is in the picture; to add a thing,
  add it as a prop or put it in the character's pack.
- **The scene description flagged every shot.** Coverage writes the scene's
  location from the place's compiled description, and the check compared it
  too, so "surfaces, roadside" was reported on shots whose words never said
  them. The check now reads only the shot's own words.
- **A cast member called BLACK.** Quickstart took the cast id from the
  appearance clause. Ids come from names now: INES, RENJI, and for role names
  all the words - STATION_MASTER, OLD_SHRINE_KEEPER.
- **One take flagged for drift held its scene** (61% of nouns lost by the
  caption's reckoning; the diner was still the diner). The limit moved to 65%;
  the marina, the one known failure, measured 72%. The verify page carries the
  clip so the director's eye can move it again.
- **LTX pushes in on every take**, so a figure that starts close ends cropped.
  Coverage now stands people a little farther back (0.40 wide, 0.22 medium).

The honest shape of "flawless" today: nothing wrong ships silently. Every fault
the machine can see is on the take, in words a person can act on.

## §39  Housekeeping for humans

Small things a person without a terminal needs, added in the last hour of the
second block:

- **What to fix.** The Review tab lists, under the triage, every shot whose
  picked take carries a note, with the note in the words it was written -
  "words not in the picture: coffee, steam", "scene drift: the last frame has
  lost 61% of the start picture", "the line may not have been spoken". Assembly
  writes the same list into its log. Nothing wrong ships silently.
- **Ends closer than it started.** LTX pushes in on nearly every take; when the
  person fills the frame edge at the end (mask flush along more than a quarter
  of the bottom, or a third of a side), the take says so. Information for the
  director, not a re-roll: the push-in is the engine's prior, and a second seed
  pushes in too. Measured on the coin shot: a wide became a medium close-up.
- **Delete a film, softly.** A button on the Film tab, with a confirm. The
  folder moves to `studio/films/_trash/<id>-<stamp>`; nothing is destroyed;
  the trash stays out of git.
- **The jobs list keeps running jobs.** A long make-all no longer falls off the
  list it is being followed on.

The rule underneath all four: the machine's judgement goes where the person is
looking, in the person's words, and the person keeps the last word.

## §40  The anime run, and the empty shot that filled itself

SCHOOL MORNING went through the form-to-film path in anime: Renji and the kite
seller, the school place, two lines, a pinned look-up and a pinned laugh. The
pins held in place and the faces held. Three things did not, and each got its
consumer.

- **People appeared in an empty shot.** The insert - a courtyard plate with
  nobody in it, the shot marked empty - came back with a man in a suit and a
  woman walking through. The drift check already captions the last frame; when
  a shot is meant to be empty and that caption names a person, the take now
  says "people appeared in an empty shot" and Make renders once more. Measured
  on the re-render: the caption said "man, person" again - LTX's prior for a
  school courtyard contains students, as its prior for a mountain contains a
  hiker (§8). The consumer catches it; the cure is still the one from the
  agency slot: give the motion a non-human cause and no room for a figure.
- **Silence where a sound bed should be.** Quickstart took the scene's
  ambience from the place's compiled ambience, and this place had none; a
  scene with no named sound gets literal silence (4s of it inside a 6s take,
  caught by the film QC). Quickstart now writes a default bed by the place's
  base when the compiled one is empty - corridors get distant voices and a
  bell, boats get water against the hull, diners get the coffee machine.
- **A two-shot on opposite shores.** Footing walked each figure outward from
  its own spot, so on the river plate Mara took the left bank and Doran the
  right. A second character now looks beside the first before walking outward.
  On that plate the left bank fits one person, so Doran still crossed the river;
  on a plate with room, they stand together.

Also seen: the "school-morning" pack's wide plate is a corridor, not the
courtyard the name suggests - name places by what their plates show, or read
the description before writing the shot (§30 again).

## §41  When the empty shot will not stay empty, stop generating the picture

The school courtyard grew a man and a woman; told to be empty, it grew a man
and a person; with the negative naming students, pedestrians, couples, men and
women, it grew a man. Three renders, three visitors. The negative has never
held an absence (§8, §9), and the empty-shot consumer now proves it per take.

So Make changes tools rather than seeds. After the one retry, if the take
still reports people in a shot marked empty, the shot becomes **the plate
itself on the camera rig** - `still_push`, arithmetic, no model - with the
rendered LTX take's audio muxed under it. Nobody can appear in arithmetic;
the ambience the scene asked for is kept from the render that failed the
picture. The take carries "the plate itself, moving slowly - generation kept
adding people" so the director knows why the insert is a push and not a live
plate.

One trap on the way: the rig's default window (2600 x 1464 at 1920, 1080) is
sized for a 4K plate. On our 1216 x 832 plates the window covered the whole
image and the push showed nothing - "almost no motion (0.00) - frozen?" said
the QC, correctly. The fallback sizes the window to the plate, centred, and
pushes 12% over the shot's own length; the QC is clean and the push is plain
on the sheet.

The general rule this adds to the doctrine: **when a generator keeps
producing the thing you asked it not to, the fix is a different instrument,
not a stronger prohibition.** Pins for motion prose cannot direct (§23); the
compositor for identity the scene prior swallows (§21); the rig for emptiness
the negative cannot hold.

## §42  The fourth run, and the block in numbers

AUTUMN PARK, the fourth form-to-film run of the morning: Ines and the station
master on a park path, two pins in place (she turns her head, he nods over the
watch), a line each, the pins and the faces right. Two notes on the takes:

- **A silent establishing shot.** "Wind in the trees, birds, distant traffic"
  returned rms 0.0013. The film QC already said "audio is effectively SILENT";
  Make now retries a silent take like a drifted one. The ambience rule from the
  QC chapter still holds - name sources; and even named ones sometimes return
  nothing, which is what the retry is for.
- **Bunting in the trees.** The insert's ambient words were "leaves, cloth". The
  cloth frag says "hanging cloth and banners lift in the wind"; in a park that
  drew bunting. An ambient word is a noun the model will draw. Choose them for
  what the place has.

**The block, 08:00-12:00, in numbers.** 31 commits. Four films from the form
(THE STATION MASTER, NIGHT DINER, SCHOOL MORNING, AUTUMN PARK), 30 seconds
each, about twelve minutes of waiting each, the director's work one sentence per
shot and a line or two. Five take-level consumers (drift, quiet line, people in
an empty shot, words not in the picture, ends closer than it started), one
instrument change (the rig for empty shots), one button for a shot and one for
a film, a form that starts a film with people already in the pictures, a Start
page, footing so nobody stands in water, a relit second character, a Review
tab that says what to fix, a soft delete, a jobs list that keeps running jobs.
Twenty-six clips on the verify page for the director's eye. Playbook §35-42.

The two invariants, honestly: a person with no knowledge of AI can now make a
short film from a form and a few sentences, and every fault the machine can see
is written on the take in that person's words. Faults the machine cannot see -
the taste of a shot, whether a laugh is a laugh - still want the eye, which is
what the verify page is for.

## §43  The director's verdicts, and what each one changed

Twenty-six clips were judged on the verify page. Yes: the crouches and turns
that were pinned from whole figures, the two-shot, the ambient street, the
empty shots that the checks had flagged (the director confirmed the paper, the
people, the bunting). Partly: the crouches whose start figure was cut at the
knee. No: nearly every spoken line, and every small pose change that had been
forced below the floor.

**"Most voices were wrong - incorrect speech or no speech."** LTX's own speech
is not reliable enough to ship. A shot with a line now gets the VO pass after
it is made: the line synthesised through the character's voice pack (a READY
synthetic pack, never a blocked one; a cast member without one is given one by
archetype, deterministically, and keeps it), laid on the beat, with the native
track ducked to 0.12 so the engine's murmur does not compete. The speech-peak
check measured loudness; it could not hear that the words were wrong. Only a
person could, and did.

**"Most crouching started with characters cropped below the knees."** The packs'
compositing views were cut at the shin on several characters - Mara and Tomas in
every view. The compositor now checks each candidate view with the truncation
detector (cached beside the pack) and uses the first whole one, or refuses with
the fix named. A repair route rebuilds a character's cropped views with the
detector-and-retry on every full-length render, not only the base; anime
turnarounds re-roll the same way. And when four seeds and the far framing still
crop - Mara's photographic prior is a three-quarter portrait, whatever the
sentence - the render is extended downward: the canvas padded by a third and
qwen-edit asked to continue the legs and shoes onto a plain floor, with
everything above untouched. Legs are not identity, which is why this is allowed
for a compositing view and was refused for meshes.

**The small pose changes that read as "no"** were the pins forced below the
floor (0.0012-0.0019/s: look up, look off, nod, laugh). Forced pins produce
invention, exactly as the floor said they would. Make no longer forces: a pose
change clears the plate floor or the shot renders on LTX with the motion as
prose, and the log says why.

**A reason with each verdict.** Yes/partly/no cannot tell "wrong words" from "no
words". The verify page now takes a few words with each verdict and keeps them
with it.

**The shot builder.** The director's brief for the product: choose the
character, the setting, the camera, the motion and whatever else, and have the
studio build the shot and many variants of it, holding the invariants the way
the spec sheet does. `/build` is that: pickers for who (with faces), where (with
plates), how (framings, camera, motion, ambient, length) and what happens (a
sentence, a line), and how many variants may differ in what. For each framing
it composes the anchor (footing, whole views), writes the shot's SPEC - the
selections as promises the checker can run - then renders the variants, which
differ only in the seed (and the camera sentence, if allowed). The bar is
regrouped as a product: make a film, library, more.

## §44  The builder's first film, measured

The shot builder was given the brief the director gave: Tomas, the night
harbour, wide and medium, a still camera, water and light moving, six seconds,
the line "Last boat's not coming back tonight", two variants that may differ
only in the seed. It made the film `builder-test` unattended.

**What it did, in order.** A film and a scene from the picks; Tomas's cast entry
from his pack; for each framing a shot with a composed anchor (footing checked,
a whole compositing view - the packs had just been repaired); a SPEC in the
spec sheet's own markdown with four promises and their CHECK lines (the people,
the place, the camera, the length) and three things left free (seed, engine,
take); then variant one through Make (anchor check, render, the take QC, the
line through the voice pack) and variant two on a new seed; then the cleanest
take picked. The checker's verdict on both shots: **all invariants hold**. The
camera promise is prose-only, so it is written but not machine-checked, and the
sheet says so.

**What the picks are.** Both picked takes are the voiced ones (`ltx+vo`), both
with clean QC. The medium shot's first take came back quiet (peak below -14 dB)
and Make re-rendered it before voicing, as designed. The wide shot's people
check saw nobody who should not be there. The two shots are on the verify page
with the question the director cares about: are the words right, is it the same
man's voice.

**The pack repairs.** Tomas and Mara (and Ines, still running) had every
compositing view cut at the shin, which is why the director saw awkward
crouches. Tomas's views re-rendered whole with the detector-and-retry. Mara's
did not: four seeds, then the far framing, all three-quarter portraits - her
photographic prior is a portrait whatever the sentence says. The downward
extension took over: canvas padded by a third, qwen-edit asked to continue the
legs and shoes onto a plain floor with everything above untouched. The result is
a whole figure in all three views (base, front, side): the trousers continue,
brown boots, a flat floor band where the grass ends. The band does not matter -
these are compositing views, the background is cut away - and the face, hands
and clothes above the pad are pixel-identical to the render. Legs are not
identity; that is the whole reason this repair is allowed for a view and was
refused for meshes.

**Numbers.** Build to picked takes: about nine minutes for two framings times
two variants including two VO passes. `/build` lists 18 people, 21 places, 15
motions, 11 ambient chips, 26 films. Verify page: 28 clips (26 judged, 2 new).

**What the builder still cannot promise.** The camera (prose-only on LTX; the
engine pushes in on most takes); the words (the voice pack says them, the mouth
does not move to them - lip sync is the encoder's, not the pack's); and a walk
(H3 pins hold in place only; a walking subject renders on LTX as prose and the
scene may drift). Each of these is written on the sheet under CAN CHANGE rather
than promised, so the sheet does not lie.

## §45  One product, not many builds

The director's other sentence: "we have many builds all over the place in
this app; we're looking to combine them into usable finished product
software." The afternoon's second half was that: not new engines, but the
seams between the pages, so that one path runs from a blank page to a picked
take without a person knowing which tool made which part.

**The pages point at each other.** A built shot's results link to *its
promises* (the spec sheet opens on that film and that shot: `/specs?film=&shot=`)
and to *in the editor* (the film editor opens on the shot too). The Start page
names the builder as the single-shot path before it explains films. The
builder remembers its last build and shows it when you come back, or shows any
film's builder shots from `/build?film=`, so a build that ran while you were
away is waiting for your eye, not gone.

**The spec sheet makes more.** The sheet was already the closest thing to an
editor: the shot's markdown, its promises, the reel. It now has a control that
makes N more variants of the open shot through Make - the same anchor, the same
promises, new seeds - and reports the job's own words while it runs. The
builder starts a shot; the sheet keeps it going; the editor fixes it. Three
pages, one shot.

**The voiced take carries its picture's notes.** A voiced take is the same
picture with a new soundtrack, but it was created with a fresh QC list, so a
picked take said *no faults reported* while its picture had ended closer than
it started and lacked the rail the sentence named. Now the voiced copy inherits
the picture's notes and drops only the speech ones the voice pass fixed. The
automatic pick was corrected with it: for a shot with a line only voiced takes
are eligible when any exist (a clean unvoiced seed must not beat the take that
says the words), and *ends closer than it started* is information, not a
fault, so it no longer decides between takes.

**Films, not experiments.** Nine test films from the day's engineering
(coverage-test, make-test, motion-test, two-shot-test and their kin) were in
every film picker beside the real ones. They went to the trash folder - the
soft delete, recoverable - and the pickers list 17 films instead of 26.

**What a person sees now.** Start here explains three steps and names the
builder. Build a shot asks who, where, how, what, and shows variants with
picks. The film editor holds scenes, shots, Make, what-to-fix. The spec sheet
holds promises and makes more. Verify judges. Everything else is under *more*.

## §46  A close-up is composed, not zoomed

The builder's third framing was tested and was wrong. "Close" placed the whole
figure at a near stand on the whole plate, which is a medium-wide with a large
person in it; LTX then spent the whole five seconds pushing in to reach a face,
and the first take lost 71% of its picture on the way (drift; retried). The
picture a close-up starts from has to *be* a close-up.

**How it is composed now.** The depth pass says where a person at medium
distance would stand; a window of the plate is taken there - 42% of its height
- and scaled up to the frame. It comes out soft, which is what a background
behind a face looks like. The pack's portrait view (the face at its native
resolution, every pack has one) is cut out and placed so that head and
shoulders fill the frame, a little head room above, the chest cut by the frame
edge so the render's own bottom is never seen. It is relit by qwen-edit with a
prompt that holds the framing hard, re-cut, checked by proportion (6% shape
drift; the floor is 25%) and laid on the untouched window. No footing - the
feet are out of frame; no shadow; no pin - the pristine-plate end frame is a
full-figure idea and a close-up renders on LTX with its motion as prose.
`anchor_source.framing` remembers which kind of anchor a shot has.

**The result.** Mara's face large and sharp from frame one, the bandstand soft
behind her, the same face at the end; the camera pushes in a little, as it does.
Composited in eighteen seconds.

**And it was silent.** Both LTX takes of the close-up came back with no sound
at all (rms 0.0009), although the prompt named birdsong, leaves and a far-off
dog. This is the speech law again: LTX makes sound from what it sees, and a
face filling the frame shows nothing that makes a noise. Re-rolling is the
wrong answer - the second seed was as silent as the first. The right answer is
the scene's own sound from a sibling take: the wide shot of the same place has
the park under it. Loudness decides, measured: the harbour takes sit at -20 dB,
the park two-shot at -35 to -45, the close-ups at -48 to -60, and the rms
"silent" test caught only the last. A take whose mean volume is under -40 dB
borrows the soundtrack of the loudest unvoiced take in its scene, else in a
scene of the same place (the first borrow reached across the film and put the
harbour's water under the park - a wrong bed is a fault, quiet is not), that is
itself above -40, looped to length and normalised to -26 LUFS on the way in; the note says so: *sound borrowed from take X of shot Y - the
render was too quiet (mean -52 dB)*. Make no longer spends a render on it.

**Two people from the repaired packs.** The two-person medium build worked
end to end: Mara and Tomas on the path, both whole (Tomas's three-quarter view
re-rendered whole that morning), both lit like the park, footing checked for
both. The prose asked them to stand and talk; they walked toward the camera -
the LTX law, not the picture. The camera variant differed from the seed
variant in its move alone, as promised.

## §47  Built by clicking: the afternoon's second half, measured

**From the page, not the API.** The builder was driven the way a person drives
it - a browser clicking: Tomas, the night harbour, the close framing, one
sentence ("listens to the water, then turns his head toward the sound"), the
line, one variant, into the builder's film. 456 seconds later the page showed
two takes, the voiced one picked, its promises one click away, the shot one
click away in the editor. No API call was written. That is the product the
director asked for, on one shot.

**What the take taught.** The close-up anchor is right - Tomas's face large,
the lamp and rigging soft behind him, head room held by the new geometry rule.
Then the sentence did exactly what it said: at one second he turns his head
toward the sound, and for the remaining four the camera has the back of his
head, the harbour beyond. The voice pack says the line to his collar. A
close-up whose subject is asked to turn away is an authoring choice, not a
pipeline fault; the lesson for the Start page is that in a close-up "turns
toward" means the model turns the whole head, and the face is gone. Keep the
face in a close-up: "glances", "looks up", "listens" - not "turns".

**Coverage in numbers.** Seven shots for a two-person scene: the empty wide,
the two-shot, a medium on each, a close-up on each, the insert. Composing the
anchors took 1350 s: the two-shot alone about six minutes (two footing
readings, two relights, two re-cuts, two shadows), each single about two, each
close-up about twenty seconds, and then the anchor check about a minute per
shot - the vision caption is the slow part. The close-ups were the fastest and
the cleanest of the seven.

**The sound rule, in numbers.** Mean volume by shot kind on this box: harbour
takes -18 to -21 dB (water, engines - LTX hears what it sees); the park
two-shot -34 to -45 dB; the park close-ups -48 to -60 dB (a face shows nothing
that makes a noise). The rms "silent" test caught only the last. The line is
now -40 dB, measured on every take; a take under it borrows from the loudest
take above it in its own scene, else in a scene of the same place, normalised
to -26 LUFS. The first version borrowed across the film and put the harbour
under the park; wrong sound is a fault, quiet is not, so a borrow never crosses
places. The re-made park close-up: -31 dB, the park's own leaves and distant
voices under Mara's face.

**Where the anchor check stands.** Two more classes of false positive fell
today: words that name the picture itself (place, scene, frame, background) and
words of hearing and attention (sound, voice, listening, watching). What
remains flagged is what a picture can lack: a rail, a path, people. On a
close-up "path" is a true absence, and the note is right to say the shot may
drift toward it.

**The block so far.** From noon: 24 commits on main, all mine; the shot
builder, its film of five builder shots and a coverage scene, three playbook
sections, thirty-one clips on the verify page (five new, awaiting the
director), the report published three times.

## §48  The builder's film, made and assembled

The last test of the block was the film editor's one button on the builder's
own film: *Make every missing shot, then assemble*. The coverage scene's seven
shots had anchors and no takes; the builder's five shots had their picks.

**What happened, unattended.** Seventy minutes for seven shots, retries
included: the empty wide held (89% of its picture in the last frame); the
two-shot and the mediums pushed in as LTX does; Tomas's medium drifted 67% and
72% on both seeds and kept the lesser; Mara's close-up came back too quiet
(-44 dB) and borrowed the park from Tomas's medium; the insert kept growing
people and fell to the camera rig with borrowed sound under it. Every shot
picked. Then the assembly: twelve shots across five scenes, 70.5 s at
1472x832, 24 fps, mastered to -17.9 dB mean, -0.8 dB peak. The contact sheet
reads as one film: the harbour with the line, the park close-up, the two-shot,
the coverage in order, the close-up built by clicking.

**Two things it exposed, fixed the same hour.** Coverage writes a placeholder
sentence - *describe the beat* - into the shots it lays out, and make-all
rendered the placeholder literally: the engine was asked, in so many words, to
describe. A shot nobody has written now gets a neutral sentence by framing
before it renders (*looks off, then back, a slow breath; the face held in the
frame* for a close-up; *stands in the scene, looking out at it, a slow breath*
for a single; *stand together, talking quietly* for a two-shot; *the place as
it is, alive* for an empty one), written into the shot so the editor and the
sheet tell the truth, with a log line asking for the real one. Measured at
once on Tomas's medium: with the neutral sentence the first seed still lost
72% of its picture - the same as with the placeholder - and the second seed
held; so the drift on that plate is the push-in law and the seed, not the
sentence; the fix is for honesty, not for drift. And a borrowed soundtrack no longer counts as a fault when takes are
compared or when Make decides to re-roll.

**Where the day leaves the product.** A person can: start on the Start page;
build a shot from pickers and get variants with promises; open the promises on
the sheet and make more; make a film from a form, lay out a scene's coverage
with real close-ups, press one button, and get an assembled film with every
take's verdicts in plain words and a what-to-fix list. What still needs a
person: the sentences (the neutral ones are placeholders that render), the
picks when the eye disagrees, and the verify page's verdicts, which are how
the next rules get written.

**Information is not a fault, anywhere a person reads it.** The same hour's
last fix ran through every surface: the film tree counts faults in
`picked_qc` and information separately; the editor's take badge shows faults
in red and information dim; what-to-fix lists faults first and marks the rest
*(information)*; the builder's results do the same; and the spec checker's
*qc is clean* fails on faults alone - a take that ended closer than it started,
borrowed its soundtrack, or was warned before rendering that a word is not in
its picture has kept every promise the picture makes. The builder's film, with
twelve picked takes and their honest notes: *all invariants hold*.

## §49  The afternoon block in numbers

Noon to a quarter past four, unattended, on main: 39 commits, all this
session's. Six playbook sections (§43-§48). The report republished a dozen
times as it grew.

**The builder's film.** `builder-test`: 14 shots across 7 scenes, 35 takes, 14
picked, 7 spec sheets; the spec checker: *all invariants hold*. Five shots from
`/build` (two by a browser clicking, not by API), seven from coverage, two
close-ups composed as close-ups, three voiced lines, one film assembled: 70.5 s,
1472x832, 24 fps, -17.9 dB mean.

**The verify page.** 33 clips, 26 judged this morning, 7 new and first in the
list: the two voiced harbour shots, the composed close-up, the two-shot with a
camera variant, the close-up built by clicking, the two-person medium built
from the page, the drawn close-up.

**Times a person can plan around, measured today.** A builder variant: three to
four minutes, plus a minute for a spoken line. A close-up composite: 18-20 s.
A two-shot composite: about six minutes (two footings, two relights, two
re-cuts, two shadows). Coverage anchors for a two-person scene: 22 minutes, the
anchor check about a minute a shot. Make-all on seven shots: 70 minutes with
retries. A build from the page to a voiced pick: 456 s; a two-person medium
with two variants and a retry: 336 s.

**Loudness by shot kind on this box.** Harbour -18 to -21 dB; park two-shot
-34 to -45; close-ups -48 to -60. The line is -40; a take under it borrows the
loudest take above it in its own scene, else a same-place scene, normalised to
-26 LUFS. Never across places.

**The rules that changed today, in one line each.** Lines go through voice
packs. Make never forces a pin. Only whole views are placed; cropped packs are
repaired, then extended downward. A close-up is composed, not zoomed. A silent
take borrows its place's sound. A shot nobody has written gets a neutral
sentence, never the placeholder. Information is not a fault, anywhere a person
reads it. Words that name the picture, hearing, attention or arrangement are
not things a picture can lack. The pages point at each other: builder, sheet,
editor, start.

**Still open.** LTX pushes in on most takes and speaks unreliably; H3 pins hold
in place only; the delivery upscale is a deliverable, not a master step; a
walk regenerates the scene; some drift is the seed's and no sentence fixes it.
The five new verify clips await the director's verdicts, which is how the next
rules get written.

**Late addendum: the drawn close-up.** The same close-up path on an anime
character - Bai Liwen in the back alley at night, the storybook LoRA on for
the relight: shape drift 1.3%, the relit figure moved back 10,-9 px to its
composed spot, the look held through the take (she looks up, a small smile,
the alley's lanterns soft behind), one take, no faults. Four close-ups today
across two engines' looks, all from the portrait view; the photographic ones
needed a borrowed soundtrack, the drawn one did not (-38 dB, just above the
line). Composed in 18 s, built in 104 s.

**Late addendum: the camera does not listen.** One more measurement before
six: shot 010's sentence was given "The camera is locked off on a tripod; the
framing never changes, nothing gets closer" and re-made on two seeds. Three of
three new takes ended closer than they started, exactly like the three before.
The push-in is not a wording problem; it is the engine's prior, and the only
things that hold a frame are a pin (in place) or the camera rig (no
generation). The camera promise on a spec sheet stays "prose only" for that
reason, and the anchor check learned not to count camera words and negations
as things a picture can lack.

## §50  The camera, measured and done by us

The night block's first question was the director's: maybe the engine has
keywords for camera moves, and what can we do to assist it? The honest answer
needed a measurement, so the first thing built was a ruler.

**The ruler.** `cammeasure` follows ORB features from frame to frame through a
similarity transform (scale, rotation, translation), on the border band of the
frame where the background lives, and accumulates the result into a zoom
factor, a pan and a tilt as fractions of the frame, and a roll in degrees.
Validated against things whose motion was already known: the `still_push` rig
at zoom 1.12 measured 1.117; two LTX takes that "ended closer" measured 2.98x
and 1.8x; an empty wide on a static prompt measured 1.09-1.16 (the engine's own
drift); a genuinely still take measured 0.999. A face that fills the frame
defeats it - the features follow the head, not the camera - so close-ups are
marked low confidence and say so.

**The vocabulary, observed.** Every take on disk, 625 of them across every film
and both sessions' work, was measured and grouped by engine and the beat's
camera word. LTX asked for *static* (180 takes): median zoom 1.02, but 45%
pushed in more than 6%, 10% pulled back, 21% panned. H3 asked for *static*
(71): median 1.06, 46% pushed in, 32% panned. LTX asked to *push in* (10):
median 1.39, and only half pushed in. H3 *pinned* (20): 1.000, 5% pushed. The
camera rig (14): 1.000, nothing moved that was not asked to. So: a camera word
is a coin flip on every generative engine measured here; a pin holds the
frame; arithmetic holds it exactly. The dictionary's camera moves now carry
those numbers in their notes, and `camera_vocab.json` states the law.

**Done by us.** `postmove` applies a move to a take the engine already made:
push, pull, pan, tilt, an orbit stand-in, handheld shake, and *stabilise* - the
compensating crop that turns a measured drift into a still frame. The engine is
asked to hold still; the move is arithmetic with the camrig's easing. Measured:
a post push of 1.15 on a take that had drifted 1.16 came out at 1.31 (the two
compound, as arithmetic must); a pan of 0.12 measured 0.119; stabilise took a
1.163 drift to 0.986. The price of stabilise is the end frame's crop
everywhere, about 14% of the picture for a typical drift.

**Wired in.** Every take now carries `cam_measured` and an information note
("camera: push in 12%"). A shot's `cam.post` names a move the studio performs
after the render and before QC. The builder's camera picker maps onto post
moves - *static* means stabilise - and the spec sheet's camera promise gained a
CHECK the checker runs on the measured take: `camera is static`, `camera pushes
in`, `camera pulls back`, `camera pans left/right`, `camera tilts up/down`. The
camera promise is no longer prose-only. Camera variants in a build are
different post moves, not different sentences.

**Identity, calibrated.** For the consistency question a second ruler: the
box has no face detector, but it has CLIP-ViT-H under ComfyUI's own loader,
which runs on CPU in 1.2 s per crop once the cpu flag is set before import.
Across 14 packs, a portrait against its own front view's head crop scores a
median 0.77 (min 0.40 with a crude crop); against another character's portrait
a median 0.31 (max 0.78 for two drawn characters who share a face by design).
The reading: 0.62 and above is the same person, 0.50-0.62 uncertain, under
0.50 a different face. `identity` measures a take's first and last frames
against the pack portrait, the head box coming from the compose geometry.

## §51  The encyclopedia of shots, and what each entry is allowed to promise

The director asked for templates for every kind of shot. A template here is a
recipe the builder can run, not a paragraph of prose: the framing, how many
people and where they stand, the camera (a post move the studio performs, or a
rig, or a pin - never a sentence the engine is asked for), the motion beat,
the length, a starting sentence, and the two lists that make it honest: what
the shot *keeps* and what it *cannot promise*, with what was measured.

**Thirty-two entries in seven families.** Coverage (establishing wide, wide
with the people, insert). People (medium, close-up, two-shot, over the
shoulder, low angle). Camera moves (push, pull, pan, tilt, orbit, handheld,
locked off, Dutch tilt). Place (the place at night, point of view, time
passes). Dialogue (a line on camera, a line in close-up, reaction, walk and
talk). Motion beats (turn in place, crouch, look up, walk toward camera).
Reveals (by pulling back, by tilting up, cutaway, whip pan, montage). Each is
also a shot template the film editor can add from its own menu, and the
catalog rides in `/api/film/libraries`, so the builder's shelf and the editor
read the same file.

**Two new kinds of shot that generate nothing.** *Time passes*: a place in the
foundry has plates for several times of day made from one description, so they
agree on geometry and disagree in light - which is a time-lapse. `platefade`
dissolves them in order with a slow push; twelve places have two or more wide
plates. Measured: push 1.06 asked, 1.056 measured, nothing else moved. *Over
the shoulder*: the second person's back view (`turn_back_three_quarter`) as a
near layer at stand 0.06, the speaker facing us behind - the template carries
the layer and the builder honours it. The first build of it taught a law: the
layer went through the usual relight, and qwen-edit, asked to relight a back
view "without changing the face", gave it one - Tomas came back facing us,
smiling, at a normal stand, because footing had also walked him onto the deck.
The compositor now has an over-the-shoulder mode for a layer: the exact back
view, no footing (its feet are below the frame by design), no relight - tinted
to the plate instead - and the figure allowed to run off the bottom.

**The compounding law, and its fix.** The first camera build through the new
pass asked for a push of 1.14 and measured 1.47: the engine had drifted 1.29
on its own and the studio's push multiplied it. Arithmetic does what it says,
including to a moving target. The fix is in the order of operations: a post
move now stabilises the engine's drift first (when it is above 3% and measured
with confidence), then applies the move, so 1.14 asked is 1.14 got. Stabilise
itself learned to hold pan and tilt as well as zoom, and to average the border
band's zoom with the whole frame's: an empty wide that drifted 1.163 came out
at 1.016, pan 0.000, tilt 0.001 - a still frame. Beyond about 1.35 the
accumulated error over-corrects (a 1.6x push came back 0.86 with a roll), so a
take the engine has pushed that far keeps its move and says so; it is a push
now, and a promise of stillness on it is broken honestly. The whip
pan taught a second law of the same kind: a pan's travel is capped by the room
the zoom gives ((1 - 1/z)/2 per side), so asking for 0.25 at zoom 1.16 returns
0.16; the whip runs at 1.25 now.

**What a person sees.** The builder opens with the shelf. Pick a shot type and
the pickers fill in; the info line says what it keeps, what it cannot promise,
and what was measured; the camera picker names only moves the studio can do
exactly, plus the pin. The spec sheet's camera promise carries a CHECK the
checker runs on the measured take. The Start page says so in one paragraph.

**Over the shoulder, third time.** The second build kept the back view but
left Tomas at Ines's distance: the depth pass places a figure on the ground it
can see, and the ground behind the camera's shoulder is not in the plate. So
an over-the-shoulder layer is not placed by depth at all; it is sized to 1.8
times the frame with the head in the upper sixth and the feet far below, and
tinted lightly (the plate's blue had bled into his hair at the usual strength).
The third build is the shot: his back and shoulder large in the near left, her
face and the harbour beyond. Three builds, three laws - relight invents a face
for a back, depth cannot see behind the shoulder, tint has a strength.

## §52  The keyword bench: does the engine have camera words?

The director's question deserved a direct experiment, not only the
observational table. One anchor (Tomas, wide, the night harbour), one seed
(4242), one engine at a time, one camera phrase per take, the camera measured
afterwards. Eight phrases on LTX; twelve on H3, six of them in the bracketed
form its documentation favours ([Push in], [Pan left], [Static shot],
[Zoom out]).

**LTX (8 phrases).** *static*: zoom 1.005 - still, and so the baseline is a
still frame. *push in*: 1.007 with a 9% tilt - no push. *pull back*: a 39%
tilt up - no pull. *pan left*: a push of 86% - the opposite axis. *pan right*:
pan right 42% (with an 18% push) - obeyed. *tilt up* and *dolly in*: the same
86% push as *pan left*, to three decimals - three different phrases, three
different files, one camera; the seed decided the motion and the phrase did
not change it, so *dolly in* "scores" only because the seed happened to push.
*tracking*: a pull back of 18%. Honest score: one phrase of seven (pan right)
moved the camera as it said over and above the seed's own motion.

**H3 (12 phrases).** Everything pushes: *static* pushed 20% and panned right
12%, and that is the baseline the others sit on. Against that baseline, three
phrases moved the camera as they said: [Push in] (36%, sixteen points over
the drift), *pull back* (28% pull, a reversal) and [Zoom out] (41% pull, the
strongest response in the bench). *push in*, *dolly in*, *pan right* and *tilt
up* had the asked motion underneath the drift, by five to nine points - not
distinguishable from luck. *pan left* and [Pan left]: pushes of 39% and 41%,
no pan - the engine does not turn left on this anchor. [Static shot]: zoom 1.05
but a 16% pan right - not still. The brackets are not magic: [Zoom out] worked,
[Pan left] and [Static shot] did not.

**So: what can we do to assist it?** Stop asking, in the frame. The phrase
that reliably moves a camera on either engine does not exist here at a single
seed; what moves it reliably is arithmetic after the render (a post move on a
stabilised take), a pin (both frames chosen) or the rig (no generation). The
one exception worth keeping is H3's pull back / zoom out, which it obeys and
which arithmetic cannot do without a wider render - so the encyclopedia's
*pull back* entry offers it as an engine move on H3 and a post move on LTX.
The words stay in the dictionary with their measured odds, for the person who
wants to gamble a seed on them.

**Exact, proven.** After the bench, one more build through the pass with the
camera set to *push in*, two variants: the first take measured 1.127 for 1.14
asked (the engine's 9% drift stabilised first, then the push); the second
take's engine ran away 65% - too far to stabilise - and kept its move, and the
pick, now judged by faults, then camera closeness, then the face, chose the
first. That is the shape of every camera promise from here: asked, done,
measured, and the measurement chooses.

## §53  The encyclopedia, checked: every entry once, unattended

An encyclopedia of shots is a set of promises; a promise is worth what a test
says. From 02:10 every entry was built once through the builder into a film of
its own - `encyclopedia-check` - with Tomas, Ines as the second when two were
needed, the autumn park by day and the harbour by night, one variant each, and
the take that came back was measured: the camera, the face, the place, the
notes. The results ride on the catalog (`checked` per entry) and on the shelf,
so a person picking a shot type sees what happened the last time it was built.

**What held.** The camera moves the studio performs came back as asked: push
in 13% for 14, pull back 12% for 12, the insert's push 15%, the two statics
stabilised to still. The place held on every two-shot and single measured so
far (0.87-0.93 first frame to last). Where a person walked toward the camera
the ruler that follows the background said "still" and the ruler that follows
the face said "a different face" - and it was: the engine redrew him on the
way in, confirmed by eye against the portrait.

**What the check taught.** The head of a person in a wide or medium framing is
a few dozen pixels; the same person scores 0.56-0.72 against the portrait
there, and 0.74-0.78 in a close-up, so the identity bands now depend on the
framing. A face that fills the frame is what the camera ruler follows, so on a
close-up the face keeps its box instead of being carried through a "camera"
that is really the head. The matrix driver read a job's result rather than
the shot itself and lost one entry to a reload that landed as the job finished;
the shot had its two takes all along.

**The numbers.** Thirty-two entries, 261 minutes, unattended: 31 built (the one
recorded as not built was the matrix driver's own loss - its shot has two takes);
25 picks with no fault; the faults on the other six are the honest kind: a face
the engine redrew on a walk toward the camera (walk to camera, low angle, the
tilt reveal, the over-the-shoulder where the near figure occludes at the start),
people who appeared in an empty pan, and three seconds of silence inside the
walk-and-talk's voiced take. Every studio camera move measured within two points
of what was asked: push 13-18%, pull 12-22%, pan 14%, tilt 10-12%, roll 7.9
degrees, whip 25%, and every static stabilised to still where the drift allowed
it. The place held (0.86-0.93 first frame to last) on every shot that did not
have a person walking through it.

| entry | built | s | camera measured | face | faults |
|---|---|---|---|---|---|
| establishing_wide | yes | 144 | static |  |  |
| wide_with_people | yes | 712 | static | uncertain |  |
| medium_single | NO | 600 |  |  |  |
| close_up | yes | 336 | tilt down 72% (a face fills the frame; the camera is hard to tell from the head) | unmeasured |  |
| two_shot_medium | yes | 512 | static | uncertain |  |
| insert_detail | yes | 392 | push in 15% |  |  |
| push_in | yes | 584 | push in 13% | uncertain |  |
| pull_back | yes | 352 | pull back 12% | uncertain |  |
| pan | yes | 616 | pan right 14% |  | people appeared in an empty shot (people) |
| tilt | yes | 512 | tilt down 12% | same person |  |
| orbit | yes | 496 | pan right 11% | uncertain |  |
| handheld | yes | 496 | static | uncertain |  |
| locked_off | yes | 192 | static | same person |  |
| line_on_camera | yes | 736 | static | same person |  |
| line_close | yes | 568 | static (a face fills the frame; the camera is hard to tell from the head) | same person |  |
| reaction | yes | 464 | tilt down 70% (a face fills the frame; the camera is hard to tell from the head) | same person |  |
| turn_in_place | yes | 520 | static | same person |  |
| crouch | yes | 488 |  |  |  |
| look_up | yes | 472 | push in 17% (a face fills the frame; the camera is hard to tell from the head) | same person |  |
| walk_to_camera | yes | 768 | static | a different face | the face is a different one by the end (identity 0.66 -> 0.29); place  |
| reveal_by_pull | yes | 536 | pull back 22% | same person |  |
| reveal_by_tilt | yes | 736 | tilt up 10% | a different face | the face is a different one by the end (identity 0.50 -> 0.39); place  |
| cutaway_detail | yes | 248 | push in 18% |  |  |
| empty_night | yes | 536 | static |  |  |
| time_passes | yes | 144 | static |  |  |
| dutch_tilt | yes | 488 | roll -7.9 deg | uncertain |  |
| whip_pan | yes | 248 | pan right 25% |  |  |
| over_the_shoulder | yes | 800 | tilt up 19% | a different face | the face is a different one by the end (identity 0.63 -> 0.33); place  |
| pov_drift | yes | 256 | static |  |  |
| walk_and_talk | yes | 728 | pull back 15% | uncertain | 3s of silence inside the film (at 3s, 4s, 5s) |
| montage_details | yes | 232 | push in 18% |  |  |
| low_angle_wide | yes | 744 | tilt up 11% | a different face | the face is a different one by the end (identity 0.54 -> 0.45); place  |

**The H3 exception, withdrawn.** The bench had H3 obeying *pull back* on one
anchor at one seed (28% and 41%), and for an hour the builder asked H3 for a
pull back in prose. The first build to use it, on the builder's own anchor at
another seed, pushed in 4.2x. One anchor and one seed is a measurement, not a
law; the exception is withdrawn, and H3 gets the same treatment as LTX - the
engine is asked to hold still, the move is arithmetic, and when the engine runs
away past what stabilise can undo, the take says so and the camera promise
fails honestly.

**Correction, an hour later.** The entry recorded as not built was lost a
second time when it was re-run: my own patch watcher fires in the gap after a
build finishes and before the driver reads the result, and the reload it
triggers empties the job list. The record was rebuilt from the film itself,
which had the takes all along: 32 of 32 built, 26 clean picks. A driver should
read the film, not the job list - the film is what happened.

**The seed dance, proven on the walk.** The walk toward the camera cost the face
on one seed (0.66 to 0.29). Built again with three variants, the same anchor:
0.58 same person, 0.47 uncertain, 0.57 same person - two of three kept the face
- and the pick, judged by faults, then camera, then the face, took the 0.58.
That is what "seed dance" means here: not hoping a seed behaves, but rendering
several, measuring each, and letting the measurement choose. The walk entries
ask for three variants by default now.

## §54  The block in numbers, and the last correction

Twelve hours from 23:38 to 11:38, one branch, 46 commits. Four films made for
measurement: `builder-test` (24 shots, 50 takes: the exact push, the
stabilised static, two time passes, three over-the-shoulder builds, the push
proven at 1.127 for 1.14, the H3 build), `cam-vocab` (20 shots, the keyword
bench), `encyclopedia-check` (39 shots, 71 takes: the matrix, the medium
re-run, the seed dance) and `shot-builds-09-04`. Six playbook sections (§50 to
§55 counted with this one), 44 verify clips waiting for a verdict, five new
tools that load fresh per job (cammeasure, postmove, platefade, identity, and
the OTS mode of compose), a 32-entry catalog with recipes and a `checked`
block on every entry, a camera grammar in the spec, and a camera picker on the
builder, the editor and the start page.

**The seed dance on the five faulted entries.** Each faulted entry of the
matrix was built again with three to five variants, unattended, 05:50 to
09:15: reveal by tilt (4 takes, 1300 s), low angle wide (2 takes, 2400 s -
the queue was shared), over the shoulder (4 takes, 1530 s), pan (3 takes,
750 s), walk and talk (5 takes, 1340 s). The pan came back clean on all three
(the people who had appeared in the empty pan appeared on one of three; the
pick took another). The other four picks still read "uncertain" or "a
different face" when the dance finished - and two of those readings were
wrong, which is the correction.

**The correction: the ruler was reading the wrong pixels.** A studio move
crops the first frame - a tilt at zoom 1.12 shows a window of the anchor, not
the anchor - and the identity ruler had been placing the anchor's head box on
the cropped frame. On a tilt up the box landed on the chest. postmove now
reports the first-frame window (zoom, centre) and identity carries the head
box into it before it crops; 31 picked takes were re-scored on CPU without
a render, and 22 start scores moved. Reveal by tilt went from 0.42 to 0.64 at
the start and 0.46 to 0.60 at the end - the same person; low angle wide from
0.47 to 0.66 and 0.49 to 0.57 - the same person. The dance had found good
takes an hour earlier; the ruler could not see them. Rule: any measurement
taken on a frame the studio has transformed must be taken in the transformed
frame's coordinates - the same law as the camera curve, now applied to the
face.

**What still fails, honestly.** Three picks end on a different face after the
re-score: the over-the-shoulder pair (his back covers her face at the start
by design; the end reading follows the near figure's tint, and the note says
"may cover"), the walk-and-talk (five seeds, every one redrew the face on the
walk toward camera: 0.57 to 0.34, 0.61 to 0.33, 0.54 to 0.32 - on this
anchor the dance did not rescue the walk the way it did on shot 340, so the
entry says three variants help and do not guarantee), and the medium walk in
shot 200. The final matrix: 32 of 32 built, 27 clean picks, 16 same person,
4 uncertain, 3 a different face, 9 with no face to judge (empty frames,
inserts, time passes).

**For the next block.** A face detector would replace the compose-geometry
head box and the framing-dependent bands with one band. The walk toward
camera wants a pin on the end frame (in place, so the H3 rule holds) or a cut
at the point the face is redrawn. A driver should read the film, not the
job list. And the window0 lesson generalises: every ruler that runs after a
studio transform (identity, people, the edge check) should be handed the
transform.

**Addendum, 09:55: the other two rulers.** The same bias sat under the
scene-drift and frame-edge checks: the camera pass replaced the take in place,
so both read the studio's crop and a 1.15 push could be reported as "scene
drift" - a fault that re-rolls. The pass now keeps the raw render beside the
moved take (`<take>_raw.mp4`) and those two rulers read it when it exists;
the identity ruler reads the moved frame through its window. Proven on one
build in `builder-test` (shot 250): push asked 1.15, measured 1.147, the face
0.73 to 0.68 (same person), the place 0.91, no drift and no edge note. The
rule stands: a ruler judges either the engine's picture or the studio's, and
the code has to say which.

**Checked by eye, 10:00.** The three picks the re-scored ruler still calls a
different face (shots 200, 370, 390 of `encyclopedia-check`) were looked at,
first frame against last: in all three the man who arrives at the camera has a
fuller, whiter beard and a rounder face than the man who set off - a redraw,
not a lighting change - and in all three the walk ended in a medium or close
framing the shot never asked for. The ruler is right three of three where it
disagrees with the wish. A walk toward the camera is the one entry the
studio cannot yet promise the face on; the shelf says so.

**A reading to distrust, for the next block.** The shelf's checked line on
*Crouch (pinned)* says "face: a different face". The identity box is carried
through the measured camera, not through the subject's own motion: in a crouch
the head drops a third of the frame and the box stays where the head was, so
the ruler reads the chest. Until the box follows the figure (a face detector,
or the pin's end frame geometry, which the studio already has for pinned
shots), an in-place motion that moves the head - crouch, sit, bow, lie down -
should carry its end box from the pin's end frame, and the reading on those
entries is not to be trusted. The walk entries and the rest of the shelf
read correctly; this one is the ruler's blind spot, named.

**Closing numbers, 10:10.** The blind spot above is now named in the code:
for a motion that moves the head (crouch, kneel, sit, bow, lie, stand up)
the end reading is information, never a fault, and the rescore applies the
same rule to the check table. The crouch reads "unmeasured (the crouch moves
the head; 0.25 not judged)" instead of "a different face", and Make no longer
re-rolls a good pin for it. Final matrix after every correction: 32 of 32
built, 28 clean picks, 16 same person, 4 uncertain, 2 a different face (the
walk toward the camera and the over-the-shoulder, both explained above), 1
unmeasured by rule, 9 with no face to judge. 55 commits in the block.

## §55  Precision: the face has a clock, the camera has a place, and the move has mass

The block before this one gave the studio rulers. This one used them to find three things
the studio had been getting wrong quietly, and built the three things it was missing.

**The face does not fail at the end. It decays through the clip.** The identity ruler read
the first frame and the last, which answers "did it survive" and not "how long did it
survive". Reading nine points instead - with the head box carried through the camera as
measured AT THAT MOMENT, not at the end - turns the verdict into a clock. Over 51 picked
takes the median face holds 1.000 of its own starting score at the top, 0.977 at a quarter,
0.962 at half, 0.911 at three quarters and 0.886 at the end: a slow decay with most of the
loss in the last quarter. On a walk toward the camera the crossing is sharp and has a time -
3.7 s, 4.5 s and 4.5 s of six second takes. So a six second walk is a good four second shot
with two seconds of a stranger on the end, and the remedy is not a better seed, it is a cut.
The studio now reports where the face went, prefers the take whose face lasts longest, and
will cut the take there when the shot asks (`cam.trim_face`, never below two seconds).

**A repair must not win the pick.** The first build with the cut on came back with one take
that ran the full six seconds and kept the face, and one that lost the face at three seconds
and was cut to three - and the cut one won, because a cut take is faultless and its camera
happened to measure a hair closer to the static that was asked. Three seconds of the right
shot is not better than six. What a take DELIVERS against what the shot asked now sorts
above how exactly the camera matched.

**Where the camera is, measured.** cammeasure says what the camera did; anglemeasure says
where it stands. A camera tilted up makes the world's verticals converge toward the top of
the frame, so: Canny, Hough, keep the near-vertical segments, find the point most of them
agree on, and read the pitch off where that point sits. RANSAC, not least squares - least
squares was the first attempt and it failed on the answer that matters most, calling a
picture of parallel verticals a steep angle because a few outliers pulled the fit. Against
synthetic keystones of a known pitch the ruler reads to a median error of 0.008 and a worst
of 0.045, on seven of eight plates. The eighth is a harbour reverse of masts and rigging
which has no vertical family; there the ruler says so and the studio promises nothing.

**Where the camera is, performed.** A low angle is two things at once and doing only one of
them looks wrong. The camera DROPS - near things fall in the frame further than far things,
which is parallax and comes free from the depth map - and the camera TILTS UP - verticals
converge, and the view rises. The first version had only the convergence: it measured
correctly and looked like a lens fault, because what a viewer names as a low angle is mostly
"we are looking higher than before". The framing move runs inside a zoom, the way postmove
does a tilt, so no pixel outside the plate is ever invented. Delivered against asked: exact
to 0.02 on every place the ruler can read. The angled view is kept beside its plate with a
depth map warped the same way, so compose, the footing check, the identity head box and the
spec all treat it as what it is - the same place, from a different camera.

**The person from below is harder than the place, and it is not shipped.** The packs' own
`pres_low` is cropped at the knees in every pack on the box - correct for a presentation
card, useless for compositing, which needs feet to stand a figure on ground. Made whole
through the pack's own must-be-whole renderer, four came back whole and three of them were
not low angles at all, and one was crouching. The cause is the renderer's fallback: when a
figure runs off the bottom of the frame it adds a FAR FRAMING sentence, and standing well
back moves the camera to eye level. The detector was satisfied every time because the
detector measures wholeness and nothing else. **A retry sentence must restate what the shot
must not lose.** The retry now names the framing AND the angle AND the pose, and when it is
still cropped it extends the picture downward instead of surrendering the angle. Two packs
of four then passed both gates. And the composite still reads wrong: a foreshortened view
scaled to a 1.7 m person by total height puts all of the foreshortening in the head, and the
result is a big head on a short body. So the place angle ships and the figure angle sits
behind a flag. What the compositor is missing is a way to scale a figure by head width
against the pack's own eye-level view rather than by total height.

**The move has mass.** Every post move was eased with a smoothstep: symmetric, arriving
exactly on its mark with zero velocity, with no physics in it. Real camera moves are made by
a person pushing a heavy thing. The ease is now a choice, and one choice is a real
second-order system - x'' + 2 zeta omega x' + omega^2 (x - target) = 0, integrated over the
clip, with `settle` saying what fraction of the clip the drive takes so the rest is the
ring-out. Measured back off the rendered file against the analytic curve the solver produced:
worst step error 0.026 across a smoothstep, a light spring, a critically damped move and a
crash zoom. The crash zoom asked for 1.34 and peaked at 1.393 asked against 1.364 measured
before settling. Four of them are in the picker: dolly in, crash zoom, snap pan, whip with
a bounce.

**The identity LoRA, tested and rejected.** The box carries `ltx-2.3-id-lora-talkvid-3k`, and
all 864 of its targets match the 2.5 int8 model by name - same 48 blocks, same width. It
loads and it changes the picture: the same anchor at the same seed rendered a 13% push where
the control was static. It does not hold the face. Lost at 4.53 s against the control's
4.47, ending 0.30 against 0.30, with a slight mid-clip gain of about 0.05 that the last
quarter erases. Kept as `workflows/70_ltx25_i2v_lora.json` for the next LoRA to be tried
through, not adopted.

**And a rule about rulers, twice over.** A measurement taken on a frame the studio has
transformed must be taken in the transformed frame's coordinates. Last block that fixed the
first frame; this block the post move reports where its window sits at nine moments through
the clip and the face box follows it exactly, which is both cheaper and more accurate than
reading it back off the pixels. The corollary bit twice more: the head box is computed for
an upright figure at eye level, so a crouch and a foreshortened low view both put the head
where the box does not look, and on those the reading is information and never a fault.

**Addendum: the angle survives the engine, and the sweep found two holes.** Eleven shots
built into `angles-and-mass`, one per entry added today, each measured twice - the plate the
studio made against what was asked, and the take the engine returned against that plate.

  asked -> plate    median error 0.041, worst 0.073
  plate -> take     median drift 0.118, within 0.20 on 8 of 11
  by sign           the take reads the angle it was asked for, 6 of 6

That is the whole thesis in three lines. A camera word is a coin flip; a camera move is
arithmetic the engine cannot argue with; and an angle put into the PLATE is copied, because
a plate is what the engine copies. Confirmed separately over 56 takes measured at both ends:
on the six built from angled plates the median drift through the clip is +0.010 and only one
moved toward eye level.

**Hole one: a shot with nobody in it was losing its angle entirely.** The builder resolves
the plate to a path before it makes the angled version, and a people-free shot uses that path
directly as its anchor - so worm's eye and bird's eye were rendered on the pristine plate
while the log said the angle had been made. Shots with a person were fine, because those pass
the plate KEY and the compositor resolves the name after the angle exists. Two of the first
eight shots measured at eye level having asked for the two most extreme angles in the catalog.
Re-run after the fix: +0.56 and -0.51.

**Hole two: a camera that ran away carried no fault.** The camera pass stabilises an engine's
drift only to 1.35x, and past that it logs "the take keeps its move" - a note beginning
"camera:", and every note beginning "camera:" is information. Right for a measurement, wrong
for a failure: the sweep returned a take that pushed 204% on a shot that asked the camera to
hold still, with no fault at all, eligible to be picked and to satisfy a spec that reads
faults. A runaway is now a fault by name and Make rolls it again.

**Also worth knowing where it breaks.** Two of eleven shots ran away, both at the night diner,
both pushing past 140%. A place can make this engine bolt; the fault now catches it, but the
place is worth remembering.

**A crane: the angle travels.** The angle lives in the plate, and a plate does not move, so
every angle so far held for a whole take. A crane is the same keystone applied per frame with
a pitch that ramps, inside a zoom that gives the swinging frame room. Built through the
studio on the same alley: up asked +0.45 and delivered +0.31 of change, down asked -0.45 and
delivered -0.46, first frame against last. What it cannot do is the parallax - the depth map
belongs to the plate and a rendered take has no depth per frame - so it is a boom on a locked
head and the entry says so. Note also that the similarity-transform ruler reads a keystone as
a roll, because a keystone is not a similarity transform; the two rulers disagree honestly.

**The words were wrong, and the population said so.** The ruler was calibrated against
synthetic keystones, which checks that it measures what it claims and says nothing about what
the numbers should be CALLED. The first names came from theory - past 0.12 a low angle, past
0.55 a steep one - and over 102 readings of every plate and picked take on the box that made
two thirds of ordinary pictures "a steep low angle". Real photographs are not shot dead level
at the middle of their subject: the population's quartiles are 0.00 and +0.80 with a median
of +0.39, skewed upward because a camera at chest height in a street has converging verticals
whether or not anyone asked. The words now come from that distribution, and, because an
ordinary plate is not at zero, the PROMISE is relative: the builder records what the source
plate measured and the spec compares the take against that. Score against the baseline, never
against the ideal - the third time this project has had to learn it.

**Packs: a view can be drawn out of proportion.** Every composite sizes a cutout so its total
height is what a 1.7 m person subtends where it stands, which only holds if every view of one
person shares proportions. They do not. On the well-behaved packs the head varies 13% to 33%
between views of the same character; eight packs of eighteen have at least one view more than
a third from their own median - a hat brim, a raised arm, a failed cutout, a figure that is
not standing - and those views are in active use. `_tools/pack_views_check.py` names them and
the repair job now removes them along with the cropped ones. Scaling by the head instead was
tried and withdrawn inside the hour: it did not reach the path that composes the subject, and
a head measured in a finished composite is not the same measurement as one measured in a clean
cutout. A uniform scale cannot repair a ratio anyway.

**And the box killed ComfyUI three times.** Staging a 20 GB video model while another session
holds the card ends the process outright - no exception, no traceback, the socket simply
closes, the signature already written down for oversized renders. The studio knew how to bring
it back and was not calling that where it mattered: a submission into a closed socket raised
straight out of the take and the variant was lost. Six submission sites now restart ComfyUI
and try once more. Once, not forever. Separately: a hundred segmenter calls back to back will
do the same thing, so the pack check is paced.

**The clock, closed.** The whole chain in one build. The face was measured over time; the
measurement said a walk toward the camera keeps its face about four seconds; the catalog
entry was changed to ask for four rather than six; and the entry was built again with three
seeds to see whether the change was worth making.

  six seconds, three seeds (earlier)   0 of 3 kept the face; best held 4.5 s of 6.0
  four seconds, three seeds            2 of 3 kept the face for the whole shot
                                       the third lost it at 3.0 s and was cut to 2.5 s
                                       the pick took a full-length take that held

Nothing about the engine changed. The shot was made shorter than the failure, and the
failure stopped happening. That is what a ruler is for: not to grade a take after the fact
but to change what gets asked for.

**The clock advises, from 101 takes.** The hold curve was backfilled onto every take the
studio had already made - CPU only, no renders - and gathered by what the shot asks the
person to do:

  still   98 takes, 68 held the face throughout, 25 lost it; three quarters held 4.8 s
  walk    17 takes, 10 held, 7 lost;                         three quarters held 4.0 s
  crouch   2 takes, neither followable (the head leaves the box the geometry predicts)

The number the builder speaks from is a survival statistic, not the worst take that ever
happened. The first version used the earliest moment a face had ever been lost, which let one
unlucky still shot at 1.9 s cap every still shot in the studio at three seconds. A margin
keeps it quiet on an ordinary five second shot against a 4.8 s survival, because a warning
that fires on everything is a warning nobody reads. The builder says it in the job log, writes
it into the spec, and the length field says it live as the director types.

Worth noticing what the two numbers mean together: a still shot's face survives 4.8 s and a
walking one's 4.0 s, so the walk is not uniquely cursed - LTX loses faces at about five
seconds in general, and a walk toward the camera simply gives it more reason to.

**Where the block ends: 45 entries, all built, all measured.** Thirteen were added today -
five angles, three moves with mass, two cranes, and three that compose them - and all
thirteen have now been built once through the builder and measured. Twelve came back clean.
The one that did not is the runaway-camera fault added this afternoon doing its job: the
matched-angles entry asked the camera to hold still and the engine pushed 39%, which before
today would have been an information note on a faultless take.

**Who loses the face, from 119 clocked takes.**

  by framing        close 17 of 19 (89%)   wide 33 of 50 (66%)   full 1 of 6 (17%)
  by the place      held 42 of 52 (81%)    drifted 20 of 37 (54%)   changed 0 of 5 (0%)
  by the first frame  0.65+ 45 of 62 (73%)   0.55-0.65 31 of 40 (78%)   under 0.55 4 of 17 (24%)

The place and the face fail together and completely: on the five takes whose place changed
between the first frame and the last, not one kept the face. An engine that rewrites the scene
rewrites the person in it, so the remedy there is the plate or the length and never another
seed - and the fault now says so. A bigger head survives: the framing warns before the build
from its own record.

The third row looked like the best find of all, because an anchor is a still picture that
exists before any card time is spent. It does not transfer. On 65 shots with both, the anchor
reads 0.069 below the take's first frame at the median with a spread of 0.103 - one is a
plate-sized composite, the other the engine's rendering of it at the film's resolution - and
across that offset the anchor separates 67% from 79%. Real, and smaller than the noise it
would be read through. identity.py can score a still, the compositor records what the anchor
scored, and nothing is gated on it. A 67-against-79 predictor would throw away good anchors
and keep bad ones while looking rigorous, which is the failure mode this whole project is
built to avoid.

**And the last measurement of the block explains the first.** The framing table said a
close-up keeps the face on 17 of 19 takes and a full-length framing on 1 of 6, which invited
the obvious guess: head pixels. It could not be tested from the takes already made, because
the builder derives the standing distance from the framing and never varies it - every wide
shot on the box stands in the same place. So the builder was given the dial and the same wide
shot of the same person was rendered at two distances, three seeds each:

  stand 0.22   head 135 px in the delivered frame   the composed face scores 0.655, 0.66, 0.675
  stand 0.62   head  65 px                          the same face scores 0.27, 0.30, 0.30, 0.32

Not a degraded face - an unreadable one. And the ruler had been calling it a different face,
which is a fault, which sends Make to render it again on another seed. A seed cannot make a
head bigger. Below a hundred pixels of head the ruler now declines to judge, and the studio
stops re-rolling shots for a failure that is geometry rather than luck.

That is the shape of the whole block in one finding: a ruler that reports confidently outside
the range it can actually read does more harm than no ruler at all, and the only way to know
the range is to render the two cases and look at the numbers.

**And it generalises past the walk.** The four-second result was proven on a walk toward the
camera, which is the motion that fails hardest, so the advice the studio now gives on every
motion rested on a survival number rather than a trial. The takes already on the box could
not check it: almost none of them are under four and a half seconds, because four second
shots are a thing the studio only started asking for this afternoon. So the same still
medium shot - same place, same person, same words - was built at two lengths, four seeds each:

  four seconds    3 of 4 kept the face
  seven seconds   1 of 4 kept it

Same engine, same anchor, same everything but the number in the length field. The one failure
at four seconds started from a composed face of 0.45 where its siblings started near 0.67,
which is the other law showing through: a shot that begins badly does not recover.

So the rule stands for any motion, not only the ones that move toward the camera. This engine
holds a face for about five seconds and the honest thing to do with that is to ask for less.

**Watched, not only measured.** Two features shipped today were checked the way this project
is supposed to check things - by looking at the render.

The face cut: the six second walk that lost its face at three seconds, cut there, ends on the
man mid-stride with his own face still on him. It is a shot, not a truncation - a walk cut
while the person is still walking is how walks are normally cut. The full-length sibling that
kept its face runs to the end and arrives close; both are usable and the pick correctly took
the longer one.

The crane: on the alley, up runs +0.09 to +0.20 to +0.40 across first frame, halfway and last,
and down runs +0.06 to -0.19 to -0.40. The walls converge and splay with it and the midpoint
sits between the ends, so the ramp is doing what the solver says. The effect is modest rather
than dramatic, which is exactly what a boom on a locked head should look like and what the
entry promises.

## §56  Putting a REAL person in a costume, and keeping them there

The problem this section solves: a director hands over a folder of a real person's
photographs and wants that person — their face and their build, recognisably — wearing a
specific costume, in shot after shot, without the face or the wardrobe drifting between
shots. Every part of this was measured on the LENGA films; nothing here is inferred.

### 56.1  The five stages

    photodump  ->  sort  ->  train  ->  render  ->  dress
                    |         |          |           |
              photosort   lora_train  the LoRA   dress_keep_face
                          _sdxl.py    is the     (costume + face
                                      identity    restored)

1. **Sort** (`studio/_tools/photosort.py`). A face LoRA and a body LoRA want different
   pictures and a folder of both trains neither. One vision call per image answers
   three fixed lines (FACE / BODY / NOTE); a photo showing both is copied into BOTH.
2. **Crop** — inside `lora_photoreal.py`, and it is not optional. See 56.3.
3. **Train** (`studio/_tools/lora_train_sdxl.py`). See 56.4 for the three bugs.
4. **Render** the person freely with the LoRA. This is where the likeness lives.
5. **Dress** (`studio/_tools/dress_keep_face.py`). See 56.5 and 56.6.

### 56.2  What is actually on this box, and what is not

| Want | Use | Not |
|---|---|---|
| Photoreal person LoRA | `lora_train_sdxl.py` on RealVisXL | ComfyUI's `TrainLoraNode` — it CANNOT bind a concept to a token |
| Anime character LoRA | `train_character.py` (animagine) | — |
| Face location | SAM 3.1, text prompt `the person's face` | OpenCV — the build here is headless, no `CascadeClassifier` |
| Costume on a rendered person | `dress_keep_face.py` | asking the LoRA for the costume in prose — it pulls to its training data's clothes |

**The test that condemns a trainer, in one render pair:** same seed, LoRA loaded both
times, trigger word present in one prompt and absent in the other. If the two faces are
IDENTICAL the trigger is doing nothing and the adapter is only an unconditional shift.
ComfyUI's node failed this four times across 11, 6, 49 and 46 images. No quantity of
data fixes it.

### 56.3  A face too small to see is a face too small to learn

Phone screenshots put a face in perhaps a tenth of the frame. Resized to 1024 for
training that is ~150 px of face, and SDXL trains in an 8x-downsampled latent, so the
identity being shown is about a 19x19 patch. 49 uncropped screenshots at 1800 steps
produced a clean, coherent, *different* woman on every seed. The same 49, face-cropped
first, produced her. `lora_photoreal.py --kind face` crops through SAM3 automatically
(0.75x margin for hair and jaw); `--nocrop` exists and is almost always wrong.

This is the same arithmetic `face_quality.py` already wrote down for RENDERING: no LoRA
can add detail to a face the sampler never had room to draw. It applies equally to
training.

### 56.4  The three bugs a from-scratch SDXL trainer will hit

1. **Export throws away the run.** `convert_state_dict_to_kohya` raised "Original type
   None is not supported" AFTER 1600 finished steps. Write the raw peft adapter FIRST,
   then map to kohya explicitly: `lora_unet_<module path, dots to underscores>` with
   `.lora_down.weight` / `.lora_up.weight` / `.alpha`, and `lora_te1_` / `lora_te2_`
   for the text encoders.
2. **fp16 with no GradScaler** gives an adapter with no usable strength band — inert
   below 0.3, image destroyed above 0.5. Use **bf16**: fp32 range, no scaler needed.
3. **Noising with the INFERENCE scheduler.** RealVisXL ships EulerDiscrete, which works
   in sigma space and expects its own timestep indices; feeding it random ints in
   0..1000 noises by the wrong law. The loss still falls — it is fitting something —
   and the renders are PURE STATIC. Training must use
   `DDPMScheduler.from_config(pipe.scheduler.config)`.

### 56.5  Text encoders are what make it a PERSON

UNet-only training gave the right ethnicity and the right face *type* and not her.
Adding LoRA to both CLIP text encoders (`--train-te`, targets `k_proj q_proj v_proj
out_proj`, text-encoder LR at half the UNet's) produced a real likeness. Trainable
parameters go 12M -> 59M. **When training the encoders you cannot pre-cache text
embeddings** — they change every step; cache token ids and encode inside the loop.

Settings that worked, 97 images (49 face crops + 48 body shots, one trigger):
rank 32, UNet LR 1e-4, TE LR 4e-5, 3600 steps, bf16, aspect-bucketed. Final loss 0.10.

**Strength is not a percentage of likeness.** It scales the trained weight change; 1.0
is "as trained" and beyond that is extrapolation. This LoRA is stable and recognisably
her from 0.85 to 1.3. If likeness is short, the answer is a better LoRA, never a higher
number.

**Train face AND body under one trigger.** A face-only LoRA has no idea what the
person's build is, and a 5'2" woman renders at whatever height the base model likes.

### 56.6  The costume is applied to the render, and the face is put back

Asking the LoRA for the costume in prose FAILS: it drags everything toward the clothes
and places in its training photos (casual tops, bedrooms, stone corridors, generic
tiaras). Asking qwen-image-edit to change only the clothing also fails, but differently
— **it changes the face too**, because qwen REGENERATES rather than editing locally.
That is §21's compositor law applied to a face, and the cure is the same: keep what you
care about out of the model's reach and put it back afterwards.

    1 dress    qwen puts the costume on the LoRA render (and rewrites the face)
    2 locate   SAM3 finds the face box in BOTH the render and the dressed version
    3 restore  the ORIGINAL face is scaled, colour-matched and blended back

**Four artifacts, each with a fix, all of them visible to a director immediately:**

| Symptom | Cause | Fix |
|---|---|---|
| Bright halo around the head | patch pad too generous, dragged the original's wall in | mask the FACE, not its surroundings |
| Face sits off the head | the two face boxes aligned by their CORNERS | align CENTRES; scale on the mean of width and height |
| Restored face glows | no exposure match to a darker plate | masked per-channel mean/std transfer |
| **"Two faces, one transparent"** | a FEATHERED mask over two different faces is a double exposure | solid core, thin rim: blur then `clip(a*2.6-0.8)` |
| **"On the edge of the face is another face"** | the patch MATCHED the dressed face, so its jaw and hairline showed around it | oversize the patch ~1.14x so her face COVERS the other one; the rim then lands on hair and background |

### 56.7  Wardrobe consistency is measured, not hoped for

Two rules, both learned the hard way:

- **The costume reference must be the FINISHED LOOK, not the source art.** Pointing
  `--ref` at the original splash painting made qwen re-invent the headpiece every time
  (horned circlets, tiaras, spikes). Pointing it at the film's own approved LeNga
  reproduced the exact three-point circlet with the loop-blade. A film's reference is
  its own first good frame.
- **The costume render is stochastic, so dress several times and pick.** The
  tool's `--variants N` dresses each render on N seeds, extracts the **crown band** - the
  region above the brow, normalised by the face box so scale and framing cancel - and
  keeps the variant whose band best correlates with the reference's.

**HOW FAR THAT METRIC ACTUALLY GOES, measured on five approved renders and not further:**
it ranks variants of ONE source image usefully - on the first close-up the two
loop-blade crowns scored 0.611 and 0.609 against 0.560 and 0.547 for the spiked ones,
and it chose correctly. It does NOT compare across images: absolute scores ran 0.078 to
0.664 on the same wardrobe, because a full-body render gives a small face box and
therefore a small, noisy band. And it is not reliable even within one image - on the
second close-up the winning variant (0.658) came back with a SPIKE, while a full-body
render that scored 0.137 had the correct loop-blade. Read the scores as a weak prior and
LOOK at the crowns; do not ship on the number alone.

**The honest cure, when a headpiece must be identical shot to shot, is a different
instrument** - §41's rule again. Cut the crown out of the approved frame and composite
it onto each render aligned to the head, the way the compositor already places props
and shadows, rather than asking a generator to draw the same object twice. Prose and
scoring narrow the field; only arithmetic makes it the same crown.

This is the takes-grid doctrine (§11) applied to wardrobe: generate competing takes,
score them on the bytes, auto-pick the best, and let the director overrule.

### 56.8  The replicable recipe

    # 1  sort the dump (face/ and body/, collages split first)
    python3 studio/_tools/photosort.py --src ~/dump --out ~/sets

    # 2  caption the body set (faces are captioned during training prep)
    python3 studio/_tools/lora_photoreal.py --src ~/sets/body --name NAMEbody \
        --kind body --dry

    # 3  combine face crops + body shots under ONE trigger, then train
    python3 studio/_tools/lora_train_sdxl.py --src ~/ComfyUI/input/NAME_train \
        --name NAME --steps 3600 --rank 32 --train-te --lr 1e-4 --te-lr 4e-5

    # 4  render the person; keep the ones that look like them
    #    (a numbered contact sheet per framing - the director names numbers)

    # 5  dress the picks against the film's OWN approved look
    python3 studio/_tools/dress_keep_face.py --src '~/picks/*.png' \
        --ref lb_canon_look.png --variants 4 --out ~/dressed

Stop ComfyUI before training (it holds ~29 GB) and restart it with
`scripts/restart-comfy.sh` afterwards. **Never inline `pkill -f 'main.py'` in an ssh
command string** — the pattern matches the ssh command itself and kills the session;
kill by PID. ComfyUI also restarts itself whenever a render is attempted, so train with
nothing queued.


## §57  Wardrobe consistency: put the costume in the weights, not in the prompt

§56 got a real person into a costume once. Getting the SAME costume in every shot is a
different problem, and four approaches were measured before one held.

| Approach | Result |
|---|---|
| Ask the identity LoRA for the costume in prose | drags to its training data's clothes - casual tops, bedrooms, generic tiaras |
| Have qwen dress each render | re-rolls the wardrobe on every image; the crown drifts shot to shot |
| Dress N times and score the crown band | a weak prior only - it ranked one image's variants correctly and then picked a spike over a loop-blade on the next |
| **Train a LoRA on her IN the costume** | **the crown is identical across every seed and framing** |

**Why the fourth works, and what it teaches.** Consistency is not a prompting problem.
The commercial multi-shot models get it two ways - conditioning generation on a
reference IMAGE rather than words, or generating the shots together in one pass so they
share context. This project already found the second one independently: §18's rule that
an internal cut re-derives faces, and that identity-critical cuts belong in the EDIT,
exists because one generation holds what two generations cannot. A LoRA is the same
idea moved into the weights: stop asking a generator to draw the same object twice.

**CAPTIONS ARE SUBTRACTION, USED DELIBERATELY IN REVERSE.** train_character.py warns
that whatever a caption omits is absorbed into the trigger forever - that is how TERRA's
trigger swallowed her gold dress and her grey wall. To bake a costume in, that is
exactly what you want: caption the POSE and the ROOM, and never name the crown, the
cape or the colour. The trigger takes the wardrobe on purpose.

The set: 15 frames already wearing the approved costume, each contributing the whole
frame AND an upper-body crop so the headpiece is learned large as well as small - 30
images. rank 32, LR 8e-5, TE LR 3e-5, 2400 steps, text encoders trained. Verified by
rendering three framings x four seeds with NO costume word in any prompt: every render
wore the same three-point circlet with the loop-blade.

**THE COST, measured: a costume LoRA trained on generated frames softens the face.**
Those 15 sources are themselves renders, so the wardrobe LoRA is a copy of a copy and
carries a generic face along with the costume. Used alone it dresses her perfectly and
makes her someone else.

**Stacking the two LoRAs does not resolve it.** Chaining costume + identity loaders
keeps the wardrobe at every identity weight up to 1.0 - the costume LoRA simply owns
the clothes - but the face stays generic, because the wardrobe LoRA's own face competes.
Pushing identity past 1.0 destroys both: at 1.4 the costume is gone and the render
returns to her casual snapshots, at 1.8 it is a phone-mirror selfie with artifacts.

### 57.1  The recipe that holds

    1  costume LoRA renders the shot     wardrobe identical across seeds, from weights
    2  identity LoRA renders her face    the likeness, from her real photographs
    3  transplant the face               dress_keep_face.restore_face()

Step 3 needs no matching pose - only the face moves, aligned by its own detected box -
so one approved portrait of her can supply the face for every shot in a film. Run at
identity 0.55 / costume 1.0 in the stack so the body reads as hers before the face is
even replaced.

### 57.2  A worn object needs the CONTACT in the training crop

First costume LoRA: the wardrobe was identical across seeds, and the director's note was
"some of the crowns are behind the head, it should be sitting on the head." The training
set explains it. At full-figure scale the tall gold shapes flaring above the hair are
hundreds of pixels and the band where the headpiece actually MEETS her forehead is a
handful, so the model learned the salient thing - gold above and behind a head - and not
the thing that makes it worn.

The fix is §56.3 again in a new place: a relationship too small to see is a relationship
too small to learn. Every source now also contributes a TIGHT HEAD crop, framed from
just above the crown to the chin, where that contact fills the frame. Those crops carry
the only placement words in the whole set - "the headpiece worn on her brow" - so the
statement sits exactly where the evidence is. 30 images became 44; the crown then read
as seated on the brow, gem on the forehead, across every seed.

The general form, for any worn or held prop: **train a crop in which the contact point
is the subject.** A staff needs the hand, a necklace needs the collarbone, a crown needs
the brow. Whole-figure frames teach what a thing looks like; only the close crop teaches
where it belongs.

This is §21's compositor law arriving for the third time, and it is worth stating
plainly as a law of this box: **anything that must be identical shot to shot is either
in the weights or composited in - never asked for.** Places are composited (§21),
emptiness is arithmetic (§41), a pinned motion is two chosen frames (§23), and a
costume is a LoRA. Prose is for what is allowed to vary.


## §58  A face that moves: identity per frame, not per shot

§56 put a real person in a costume and §57 kept the costume on her, and both were solved
in STILLS. The film then failed on the one thing a still cannot test. The director's
notes, in order, were "faces definitely don't hold up", then "this is like a face sticker
on a video", then "still no good". Three attempts, and only the third works.

### §58.1  Both failures were the same trade-off

H3 re-renders every frame from the start picture, so a face drifts across a take even
when the anchor is perfect. Two repairs were tried.

**face_lock.py** transplanted one approved still onto every frame. Identity was perfect
and the shot was dead: a still cannot turn its head, blink, or catch a moving light, so
it floats on top of the picture. Rejected on sight, and correctly.

**face_detail.py** ran each frame's OWN face crop through img2img at 0.40 denoise with
her identity LoRA. Motion, expression, motion blur and lighting all survived, because the
pass starts from the frame's real pixels. But the identity barely moved - at a denoise
low enough to keep the performance, SDXL only nudges the face it is given.

These are not two problems. They are the two ends of ONE axis, and there is no setting
between them, because **neither tool knows where the face is pointing.** A paste ignores
pose entirely; a low-denoise pass sees pose but has no mechanism to impose an identity on
it. Any further tuning of either was going to fail the same way, and it did.

### §58.2  What the third tool does differently

inswapper does not work in the frame. It works in the ALIGNED FACE SPACE: five landmarks
give a similarity transform onto the arcface template, identity is applied to that
canonical crop, and the result is warped back through the inverse. The pose, the
expression and the blink belong to the frame; only the identity is replaced. That is the
capability the other two lacked, and it is the whole reason this works.

The install is deliberately fenced off. `insightface` + `onnxruntime-gpu` live in
`~/shared/faceswap-venv`, NOT in ComfyUI's environment. onnxruntime-gpu links CUDA 13,
whose libraries already exist inside ComfyUI's venv, so `face_swap.py` points
`LD_LIBRARY_PATH` at them and re-executes itself once - the linker reads that variable at
process start, so setting it from inside a running process is too late. Nothing is
installed into or changed in ComfyUI. Weights: `buffalo_l` (detector + arcface, fetched
by insightface) and `inswapper_128.onnx`, whose sha256 is
`e4a3f08c753cb72d04e10aa0f7dbe3deebbf39567d4ead6dce08e98aa49e16af` - three independent
mirrors served a byte-identical file, which is the check worth doing on a model this box
will keep.

### §58.3  Identity is an average, not a photograph

`--source` takes a FOLDER, not a file. Every usable reference contributes a 512-d arcface
embedding and the mean is re-normalised. One photograph carries its own lighting, angle
and expression into every frame of the film; forty photographs cancel those out and leave
only what is consistently her.

This is the single biggest quality lever in the tool, and it is what the `sorted/face`
set from §56 was actually for. The photo sorter earns its keep here more than it did in
training.

### §58.4  Jitter is a landmark problem, and smoothing it naively costs you the motion

The detector re-finds the face from scratch every frame, so the five points shimmer by a
pixel or two even on a still head, and the swapped face wobbles inside the real one.

The obvious fix - average the landmarks over a short window - trades the wobble for LAG.
In shot 030 she walks at the camera; a lagging landmark set slides the face off the head,
which is worse than the shimmer.

So split the landmark set in two. The CENTRE passes through exactly as detected, so
translation tracks perfectly. Only the offsets from that centre - scale, roll, the small
internal geometry, which is where the shimmer actually lives - are averaged over five
frames, and only across an unbroken run of detections. Wobble goes, motion stays.

The same split is worth remembering for any per-frame tracked effect: **smooth the shape,
never the position.**

### §58.5  Do not stack the detailer after the swap. This was measured

The tempting move is to run `face_detail.py` after the swap to add skin texture. It
undoes the swap, because the detailer REGENERATES the face from SDXL - exactly what the
swap just overwrote.

Cosine to her averaged identity, across shot 010:

| pass | mean | worst frame |
|---|---|---|
| swap only | 0.870 | 0.822 |
| swap, then detail at 0.25 denoise | 0.694 | 0.478 |

That number is somewhat circular - it is the quantity inswapper optimises - so it is a
check that the swap APPLIED, not proof of likeness; the eye still decides that, with her
real photographs in the same picture at the same size. But circular or not, it detects a
pass that takes identity away, and it did.

**The swap is the identity. Anything after it can only give some of her back.**

### §58.6  The paste-back, and where the softness comes from

inswapper outputs 128x128 against a face two hundred pixels wide, so the swapped face is
softer than the frame around it. insightface's own paste-back upsamples with bilinear,
which is where most of that softness is added rather than inherited.

`paste()` reimplements their mask recipe unchanged - warp a white square through the
inverse transform, erode it well inside the face, blur the edge - and changes only two
things: LANCZOS4 for the warp, and a mild unsharp on the warped face alone. Measured on
shot 010 this RAISED identity from 0.870 to 0.884, because a sharper face registers
better. Free improvement, no artifact.

Do not be tempted to widen or feather that mask. A feathered mask over two faces is a
double exposure, the director caught it twice in §56.6, and the erode-then-blur keeps the
blend well inside the jaw where there is nothing to double.

The residual softness is a real limit of a 128px model and the honest fix is a face
restorer (GFPGAN/CodeFormer as ONNX, same venv, same session). It is not installed here.

### §58.65  Coverage is the failure mode, and the close-up will not show it to you

The first full pass looked finished. Shot 010 measured 0.87 to her averaged identity,
shot 030 measured 0.88, and the review still on the close-up was convincing. The last
shot was not her at all - it measured -0.02, which is to say the swap had never run on
it.

**A frame with no detection gets no swap, so it silently keeps the engine's face.** The
tool reported success because it had swapped every frame it found, and in the WIDE shots
it found almost nothing: shot 050 came back with 17 of 48 sampled frames, shot 040 with
one. She is small there, and motion blur on a fast pass costs the rest. Nothing errored.

Two changes fix it, and the second is the important one:

1. `det_size` 640 -> 1024 and `det_thresh` 0.5 -> 0.4. Worth a little, not much - on shot
   050 this alone moved 17/48 to about 21/48. **Raising detection resolution is not the
   fix, and stopping there would have been a wrong conclusion drawn from a real
   measurement.**
2. `bridge()` - interpolate the landmarks across SHORT detection gaps. A head cannot
   teleport in a fifth of a second, so a gap of a few frames between two solid detections
   can be filled. Guarded twice: only gaps up to `--gap` frames, and only when the face
   has not JUMPED across the gap, because a jump means two different faces or a genuine
   exit. Shot 050 went to 60/60.

The frames that stay unswapped after that are the ones that SHOULD - behind the orb,
before she lands, off the end of the shot.

The general lesson is about how this was nearly missed. An intermittent swap is worse
than no swap, because it flickers between two people, and it is invisible in exactly the
place you are most tempted to review: the close-up, where detection never fails. **Check
per-shot coverage on the WIDE shots, and measure identity on the assembled film rather
than on the shot you tuned.** `idsheet.py` sampling the finished cut is what caught this;
the close-up comparison that came before it was, by construction, incapable of catching
anything.

### §58.7  The recipe

    master take (48fps, pre-effects)
      -> face_swap.py --source sorted/face --sharp 0.45
      -> POV effect
      -> assemble

The order is §55's rule again and it still holds: swap the MASTERED take, never the
finished one. Swapping a finished take drops a clean face into frames the blink has
already blurred and darkened, and it stands out. Swap first and the blur, the darkening
and the knockback all land on her face too, because by then it is part of the picture.

### §58.8  The law this adds

§57 ended on: anything that must be identical shot to shot is either in the weights or
composited in, never asked for. A face in motion is the case where BOTH of those fail -
weights drift frame to frame, and a composite cannot turn its head.

So there is a third mechanism, and it is worth naming: **anything that must be identical
AND must move is neither trained nor pasted - it is re-derived per frame in a space where
the motion has been factored out.** inswapper factors out pose with five landmarks. That
is the whole trick, and it generalises: find the space where the thing that varies has
been normalised away, do the work there, and warp back.


## §59  `prev_last` is a snapshot, and the frame it took was the wrong one

The director's note was four words - "shot 5 should use the last frame of shot 4" - and
shot 050's anchor already said `prev_last`. The data was correct and the cut was wrong,
which is the interesting part: two separate faults, one hiding behind the other.

### §59.1  An anchor is resolved once, at render time

`prev_last` is not a live link. It is read when the take is rendered and never again.
Shot 050's master had been rendered against a version of shot 040 that no longer existed
- 040 has since been re-pinned, head-trimmed, sped 2.9x and face-swapped, and every one
of those moved its final frame. 050 still opened on the old one: she sat smaller and
higher, cape flared instead of hanging, the mist and the chains in different places.

Nothing in the film would ever say so. The anchor field still reads `prev_last`, the spec
check still passes, and the QC still reports clean, because every one of those inspects
the DECLARATION and not the pixels.

**Rebuilding a shot silently invalidates the start of the shot that follows it.** When a
shot changes, re-render its successor, or at minimum lay its last frame beside the
successor's first and look. `assets/cut45.png` in this film is that check; it took one
ffmpeg call and it is the only thing that would have caught this.

### §59.2  `-frames:v 1` after `-sseof` takes the FIRST frame of the tail, not the last

Re-rendering fixed the staleness and the cut still jumped, less. The anchor the studio
had extracted was not 040's last frame at all:

    ffmpeg -sseof -0.2 -i src -update 1 -frames:v 1 dest

`-sseof -0.2` seeks to 0.2 s before the end and `-frames:v 1` then takes the FIRST frame
it finds there. That frame is up to 0.2 s early. On a shot that drifts, nobody notices.
Shot 040 is sped 2.9x, so 0.2 s of it is ten delivered frames of her settling out of the
landing - and the next shot began from a pose the audience never sees.

Measured against the true final frame, the extracted one differed by a mean of 24.9 per
channel. Not subtle; simply never checked.

The fix is smaller than the bug. Drop `-frames:v 1` and let `-update` overwrite its way
through the window, so the file is left holding the last frame written:

    ffmpeg -sseof -0.5 -i src -update 1 dest

Verified byte-identical to a full `-vf reverse` pass, without reading the clip into
memory. Fixed at source in `film_routes.py`, in BOTH places that did it: the anchor
resolver, and `_last_frame()` behind the scene-drift QC - which means every drift score
this box has ever reported was computed against a frame that was not the last one.

### §59.3  The habit worth taking

Both faults share a shape. `prev_last` claims to mean "the frame the audience last saw"
and `_last_frame` claims it in its name, and neither delivered it - one because it was
answered too early, one because it was answered from the wrong end. The declaration was
right in both cases, so nothing that reads declarations could catch either.

**When a joint between two shots matters, look at the two frames.** Not the anchor field,
not the QC line, not the take id - the pixels either side of the cut, side by side. That
comparison is four lines of ffmpeg and it is the only instrument here that measures the
thing the audience actually experiences.


## §60  A live plate is only worth having when the plate is still

"The stairs changed on shot 5" - and they did: across shot 050 the staircase narrows,
the arches shift and the torches walk, while the shot's own prompt says the camera is
locked off on a tripod, no zoom, and the hall stays exactly as it is. §21 again: an
element that is only DESCRIBED is re-invented every step.

### §60.1  The tool that fixed the same fault before, and why it failed here

§v10 cured shot 030's drifting background with pov_fx `comp`: mask the character against
a static empty plate, lay her over a LIVE empty plate, and the room never comes from the
character take at all. Shot 050 is the same fault, so it got the same treatment - a new
plate made from its own first frame, since a plate is framing-specific and the 030 plate
differed from this framing by a mean of 72 per channel.

It came out worse. Measuring the live plate against its own first frame says why:

| plate frame | 10 | 40 | 100 | 140 |
|---|---|---|---|---|
| drift | 17.6 | 36.6 | 50.3 | 56.1 |

There is no stable window. Shot 030's plate held for about three seconds because its
chains were small and far back; shot 050's framing puts two enormous chains across the
near foreground, and H3 starts swinging them inside the first fifth of a second. The
composite delivered a still staircase behind swimming, doubled chains.

**Measure the plate before trusting it.** Its stability is a property of the FRAMING, not
of the technique, and the number takes one pass to get. A plate that drifts is not a
weaker version of a good plate - it is a second drifting layer fighting the first.

### §60.2  What holds a room still is a pin at each end

§23's first+last pin is what made shot 040 immune, and it is the right instrument here:
H3 must ARRIVE at a frame we chose, so the geometry is nailed at both ends and only
interpolated between. After pinning, the staircase, arches, torches and chains hold for
the whole shot.

The whole difficulty moves into the end frame, and it took two goes.

**Attempt one: ask qwen to grow the orb.** It obeyed the wrong half - the orb got bigger
and stayed welded to her staff. The pinned take then charged up and never fired, because
an end frame that is just a bigger start frame guarantees nothing can travel. The stairs
were fixed and the payoff was gone, which is not a fix.

**Attempt two: take one thing from each source.** The old drifting take always had a good
orb - a real rendered sphere racing at the lens; only its hall was wrong. The start frame
has the right hall and no orb. `orb_end.py` finds the orb by brightness (nothing else in
a torch-lit hall is above 200), lifts it on a feathered radial mask, drops it on the
start frame, and adds the light it should be throwing past its own edge. The end pin then
carries a huge close orb AND the room the shot opens in.

### §60.3  The rule

**A pinned end frame must differ from the start in exactly the thing that is supposed to
move, and in nothing else.** Change too much and the pin drags the room with it; change
too little - or the wrong axis of the same object - and the shot has nowhere to go.

When no single generator will produce that frame, build it. The end frame here is a
composite of two takes and was made with numpy in a few lines; it never had to be a
render at all. This is §21's law reaching the pins themselves: what must be exact is
constructed, not requested.


## §61  A prompt will hold two of three: the room, the costume, or the scale

"Shot 5 has a different background than shot 4." True, and the cause was not in shot 5.

### §61.1  The fault was in shot 040's own pins

Shot 040's start pin and end pin were TWO DIFFERENT ROOMS, differing by a mean of 64.3
per channel. The start pin is the wide bright cathedral shot 030 ends in - flat floor,
chains crossing low, the far staircase small under a stained-glass window. The end pin
was a dark narrow hall with a big staircase close to camera and the chains crossing high.

So 040 was never drifting. It was doing exactly as instructed: changing rooms, smoothly,
over three seconds. And because 050 pins off 040's last frame (§59), it inherited the
second room permanently. **One bad end pin does not spoil one shot; it spoils every shot
downstream of it.** That is the expensive way to break §60's rule, and it is why an end
pin deserves the same scrutiny as an anchor.

### §61.2  Three attempts, and what each one traded away

The end pin has to satisfy three things at once: the same room as the start pin, her real
costume, and a size the audience can read. Each attempt bought one by selling another,
and the numbers say so plainly.

| attempt | pin diff vs room | costume | her scale |
|---|---|---|---|
| original | 64.3 | right | good |
| qwen, "keep everything, add her" | 43.5 | plain gown | speck - face found in 3 of 145 frames |
| qwen, "closer, costume from image 3" | 62.9 | right | good, but the room re-framed |
| **composited** | **4.6** | right | good - face found in 77 of 145 |

The second row is the one worth staring at. All three qwen slots held the same image, so
nothing in the call carried wardrobe, and §57 applied on schedule - with no costume in
the reference, qwen invents one. The third row fixed that and lost the room instead:
asking for her CLOSER is an instruction about framing, and framing is the room.

There is no prompt that holds all three, because all three are the same generator's free
choice, and a generator asked for three exact things will always trade.

### §61.3  So none of them is asked for

`studio/_tools/figure_paste.py`. The room is a file. The costumed figure is a file. It
mattes her out with SAM 3.1, scales her to a stated height at a stated place, and matches
her exposure to the region of the room she will land in - only PART way, because a figure
lit exactly like the wall behind her disappears into it.

**The occlusion is what stops it reading as a sticker.** The room's golden chains hang in
the extreme near foreground; a figure pasted over them is instantly wrong. So the chains
are matted out of the ROOM by the same text-prompted segmentation, and after she is
pasted those chain pixels go back on top. She ends up standing behind them, which is
where a person halfway down the hall actually is.

Pin diff fell from 64.3 to 4.6 - the residue is her, the smoke and the orb light, which
are the only things that should differ.

### §61.4  The law, in its most general form yet

§21 said places are composited. §57 said costumes go in the weights. §60 said a pinned end
frame must differ from the start in exactly one thing. All three are the same statement,
and this is it stated once:

**Every requirement you hand a generator is one it may trade against the others. Hand it
one, and construct the rest.**

The corollary is practical: when a render keeps failing in a different way each time, stop
rewording. Count the exact things being asked for. If it is more than one, the prompt is
not the tool.

## §62  Two beats, two pins - and a sound the engine makes rather than reads

### §62.1  A shot with two beats needs two pin pairs

The finale was asked to do two things: she DISPLACES closer to the camera, and then the
orb fills the screen and fires into the lens. §60 already recorded what happens when one
pinned render is asked for two things through prose - the orb stayed welded to her staff
and the shot charged up without ever firing.

So each beat gets its own pin pair, and the join is the frame between them:

    A  displacement   start = 040's last frame     end = her, closer, in the SAME room
    B  the firing     start = A's last frame       end = the full-screen orb

Both end frames are constructed rather than requested (§61). Her closer position is
`figure_paste` at a larger height into the same room file, so the hall cannot move while
she does. The full-screen orb needed nothing built at all: the OLD drifting take had
already rendered a frame where the orb covers the whole lens, and by then the hall is
invisible behind it - so that take's drift, which was the fault being fixed, costs
exactly nothing in the one frame where none of the room is visible.

**A discarded take is still an asset.** It failed at holding a room; it never failed at
making an orb.

### §62.2  `zap`: what a fade cannot say

`fx_boom` ends on a knockback and a fade to black, which reads as being hit by a LIGHT.
The brief was to be electrified, so `fx_zap` keeps the knockback and adds three things:

- a violet flash that spikes at contact and decays at exp(-2.2t),
- forked arcs drawn as random walks with a decaying step, redrawn every second frame,
- a chromatic shear that pulls R and B apart by 14 px and settles.

The arcs are drawn FROM THE CENTRE OUTWARD. Bolts that start at the frame edge read as
weather; bolts that start where the orb is read as the thing discharging into us. That is
the whole difference between an effect that lands and one that decorates.

### §62.3  The sound: stop asking a voice to read a grunt

Three attempts had failed and two of them were the same attempt. StableAudio kiais came
out as small dogs barking; IndexTTS-2 was given words ("Hee-yah") and then wordless
grunts, and both are a VOICE MODEL PERFORMING A TEXT. There is no text for the noise a
person makes when they land, which is why every version sounded like someone SAYING a
grunt.

The director's question - "can h3 make cute feminine noises?" - is the right one, because
H3 is a different mechanism, not a different voice. It does not read text; it scores the
SHOT, given the picture and the action, so the sound arrives already attached to a body
doing something. `v18_h3voice.py` renders 39-frame landings (17n+5, the shortest render
that still contains an impact) and keeps only the audio.

Two practical notes:

- H3 hands back a whole SCENE's audio, not an isolated vocal. Dropping 1.6 s of it into
  the mix drags the chain creak and the floor thud along too. `cut_vocal()` band-passes
  to 300-3400 Hz, finds the loudest moment of that envelope, and takes a short window
  around it - the vocal is cut by measurement, not by ear.
- Picking between candidates has a usable proxy when nobody can listen yet: the ratio of
  voice-band energy to sub-250 Hz rumble. Across ten clips it ranged 0.75 to 2.46, and it
  ranks exactly what matters in a mix that already contains a whoomp and a music bed -
  how much of the clip is VOICE rather than room. It is a tiebreaker, not a verdict; the
  director's ear still decides.

## §63  The recipe encyclopedia, and why a card must be checked

The studio already knew what its MODELS could do - `capabilities.json`, 35 entries, one
per thing the box can be asked for. It had no record of what WE could do: the end-to-end
processes built on top of those models, which is where every hard-won thing in this
document actually lives. `/recipes` is that record, and it is built on one rule.

### §63.1  A card that is not checked is worse than no card

`studio/_tools/recipes.py` resolves every script, workflow, model and toolbox id a card
names against the filesystem BEFORE the card is served, and reports what it cannot find
rather than hiding it. This is `capability_scan.py`'s discipline applied to prose: a card
claiming a tool that no longer exists sends someone looking, which costs more than the
card ever saved.

It earned that on the first run, twice. One card named `17_higgs_v3.json`, and the file
is `17_higgs_v3_voice.json`. Another named `24_qwen_edit_2511_triple.json` - the
three-reference qwen variant this whole project depends on - and found it only in
`leblanc-night/`, never installed into the kit's `workflows/`, where every other tool
looks. It had been used for weeks from one script's hardcoded path. It is installed now.

Neither would have been found by reading. Both were found by a check that runs every
time the page is opened.

### §63.2  A card leads with a picture

ComfyUI's template gallery leads with an image and ours led with a paragraph, which is
the wrong way round for a page whose job is "show me what this box can do".
`recipe_thumbs.py` builds one per card from a small spec language - `img:`, `vid:#frame`,
`pair:a||b`, `grid:dir#n` - naming files that already exist in the film and asset
folders. Nothing is pasted in, so the gallery rebuilds from scratch anywhere the work
exists, and a card whose source was deleted reports a miss instead of showing something
stale.

Two details that mattered more than expected. **Before/after belongs on any card that is
about a CHANGE** - the figure-paste and face-swap cards say more as two frames than as
two paragraphs. And **crop portraits from the top**: centre-cropping a portrait into a
landscape card cut a close-up down to a shoulder and a torch, because the face is always
the highest thing in the frame.

### §63.3  What the cards carry that a model card cannot

Each one has the usual - what it does, what it costs, what to run. It also has three
fields a capability listing has no room for, and they are the reason the page is worth
maintaining:

    use it when          the case it is actually for
    not this if          the case it is NOT for, naming the recipe that is
    what it cost         every gotcha, measured, with the number that settled it

Seventy of those across twenty-four cards. Three cards are marked `superseded` or
`rejected` ON PURPOSE and kept: the face-sticker approach is on the page as a card,
because "we tried that and here is exactly how it failed" is the most expensive
information in this repo and the easiest to lose.

### §63.4  The trap the page exposed on day one

`lora_real` in the toolbox described itself as "the only route here that puts an actual
person into a render". It runs ComfyUI's `TrainLoraNode`, which §56 had already proved
cannot bind a concept to its token. The working trainer had existed for a day and was
not in the app at all.

**A tool's blurb is a claim, and claims rot.** Writing the recipe forced the comparison
that a scattered set of scripts never does - which is most of the argument for having
the page.

## §56  Finding the head, and a LoRA that is worth its minutes

Two blocks of work rested on a head box that was a guess. The compose geometry knows where a
figure was told to stand and how tall a person is there, and from that a head box was derived
and then carried through the measured camera to find the head at the end of a take. That is
exact for an upright figure at eye level in a shot where only the camera moved. It is wrong
every time the person does anything, and the studio has been recording those wrongs as
failures of the engine.

**There is no face detector on this box, and there did not need to be.** BiRefNet cuts a
person out of a picture cleanly enough to build every composite in the studio, and the top of
a silhouette is a head whatever the body is doing. Matte the frame, keep the region the
geometry says the subject is in, and read the head off its top. Painted onto the frames the
difference is not subtle: on a pinned crouch the guessed box floats in empty air a third of a
frame above his head.

**Largest-region was the obvious rule and it is wrong in the one place the studio deliberately
puts two people in a frame.** An over-the-shoulder foreground is sized past the frame on
purpose, so it wins any size contest, and the ruler scored the back of the listener's head
against the speaker's portrait: 0.24 where the guess had said 0.62. So the two signals do what
each is good at. The geometry knows roughly where the SUBJECT was put, which is what it was
written down for. The matte knows exactly where a head is. Given the hint, the region whose
head is nearest it wins.

**Two of the five recorded face failures were the ruler.** Same takes, same encoder, same
portrait, only the box moved:

  a pinned crouch        0.65 -> 0.25 a different face     0.67 -> 0.56 uncertain
  walk and talk          0.57 -> 0.34 a different face     0.65 -> 0.63 SAME PERSON
  over the shoulder      0.62 -> 0.36 a different face     0.67 -> 0.45 a different face
  a walk to the camera   0.66 -> 0.30 a different face     0.68 -> 0.43 a different face
  an ordinary wide       0.57 -> 0.66 same person          0.59 -> 0.62 same person

Re-scored across every picked take the studio has: same person 36 to 42, a different face 12
to 10, unmeasured 6 to 3.

**And the face clock was systematically pessimistic.** The hold curve read nine moments and
placed the box at each of them by carrying the first one through the camera, which is wrong
for exactly the shots the clock is most used on. Three mattes instead of two - start, middle,
end - and the box between them read as a line, because a head does not teleport. The crouch
went from "lost at 1.11 s of 4.5" to holding the whole way; a walk from 3.72 s to 5.21; a
walk-and-talk from a loss at 5.26 to holding throughout. The survival numbers the builder
advises from are built out of those readings, so they were too low: the studio has been
telling directors to shorten shots on the strength of a ruler looking at the wrong pixels.

**The exemption for head-moving motions is withdrawn** wherever the matte found a head. It was
correct while the box was a guess and it is not needed when the box is found in the frame it
is judging. It still applies where the matte finds nothing, because there the fallback is the
same guess that made it necessary.

**A character LoRA, and whether it is worth its minutes.** The question was put directly, so
it was answered directly. A foundry pack already holds what a character LoRA wants: a
turnaround, a face turnaround, expressions and a full body, all one person from one
description. What it lacks is captions, and captions are the whole game - whatever a caption
does not name is welded onto the trigger. This pack never specified clothing, so there were no
words for it; the studio's own vision model was asked a narrow question, the garments and the
ground behind them and nothing about face, hair or build, and those answers became the
captions.

1200 steps, rank 16, on the checkpoint the drawn packs were made with. Four routes to the same
close-up, same seed, same words, scored against the pack portrait on a head found by the matte:

  prompt only          not her at all - a generic figure with the wrong hair
  IPAdapter at 0.6     0.685    what the studio does now
  the LoRA             0.749
  both                 0.768

It generalises rather than memorising. Four asks the training set never contained - a
lantern-lit alley, a red winter coat in snow, running along a riverbank, sitting at a desk
with a book - at three strengths: she scores 0.592 to 0.755 and every scene is the scene that
was asked for. Strength 0.85 is best at a mean of 0.701, and that is the strength the studio
now uses. The LoRA is recorded on the pack, so nothing has to be told about it twice.

**A note on checking.** The first pass at "did the asked-for scene appear" used the studio's
character-reference caption, which is written to describe a person and explicitly not their
surroundings, and it reported 3 of 12. Looking at the pictures, it is 12 of 12. A check is
only as good as the question it asks, and a check that reports a failure it was never able to
see is worse than no check at all.


**A correction to §55, owed immediately.** The face clock's numbers, and the advice the
builder gives from them, were measured with the carried box. Re-measured with the found head
across every take on the box:

  still   121 takes   80 held -> 71 held    three quarters hold 4.3 s -> 4.5 s
  walk     17 takes   10 held -> 14 held    three quarters hold 4.0 s (unchanged)
  crouch    2 takes    0 held ->  2 held    both hold the whole way

The walk line is the one that matters. §55 says that a six second walk toward the camera kept
its face on none of three seeds and a four second one on two of three, and concludes that the
shot was made shorter than the failure and the failure stopped happening. Under the corrected
ruler most six second walks DO hold: of the seventeen walk takes on the box, fourteen keep the
face, and the six second takes from the seed dance that were recorded as losses now read as
holds. The engine was doing better than the studio said, and the studio was telling directors
to shorten shots on the strength of a box that had drifted off the head.

What survives that correction, and what does not:

  survives     the face decays through a clip - that was measured as a fraction of each
               take's own start, so a box that drifts equally at both ends does not create it
  survives     head pixels: 135 px scores 0.66 and 65 px scores 0.30 for the same person,
               measured on first frames where the box was right
  weakened     the four-against-six walk result, whose two arms were both measured with the
               carried box, and which the corrected clock does not support
  unmeasured   the four-against-seven still result, which has not been re-run yet

The rule for the next block is the rule this block keeps proving: when a ruler changes, every
claim it produced has to be re-read, and the ones that do not survive have to be said out loud
rather than left standing because they were convenient.

**And the correction above is itself withdrawn.** Written an hour ago, on numbers produced by
reading the face clock between three found heads, and that method does not survive being
checked the way the endpoint change was. On a medium shot in a cafe the nine sampled scores
wander from 0.20 to 0.63 and back inside two seconds while the first and last frames of the
same take score 0.66 and 0.46. A face does not do that. Dropping anchors that claim the head
teleported helped and did not fix it: three anchors are not enough to interpolate through, and
on a medium framing the per-frame matte is not reliable enough to carry the guess.

So the studio keeps the half that was verified and reverts the half that was not. The first
and last frames use the found head - checked by eye on six takes and by score on every take
the studio has, and it turned two recorded failures into ruler errors. The curve goes back to
carrying the first box through the measured camera, which is approximate for a moving subject
and is at least stable, and is the basis every number the builder advises from was calibrated
on. §55's walk result stands as originally measured. The question it raised stays open.

What would settle it: a head found in every sampled frame rather than three, which is nine
segmenter calls a take instead of three, or a tracker that follows a head between frames
rather than re-finding it each time. Either is a block's work.

Two withdrawals and one correction-of-a-correction in one block is not a bad night. The
alternative was three confident numbers, two of which were wrong, sitting in the record where
the next block would have built on them.

## §64  The identity LoRA does not make her face. The swap does, and it does it alone

A bench, not an impression. Twenty ordinary situations she had never been rendered in -
a café, a subway car, snow, a strict profile, a plain studio portrait - varied on the
three things that break a likeness: DISTANCE, ANGLE and LIGHT. Four LoRA strengths
including **zero as a control**, two seeds each, 160 images. Every one then face-swapped,
and both versions scored by arcface cosine against the mean embedding of her 49 real
photographs.

| LoRA strength | cosine, LoRA only | cosine, after swap | n |
|---|---|---|---|
| 0.00 | 0.004 | 0.867 | 39 |
| 0.65 | 0.151 | 0.869 | 39 |
| 0.80 | 0.180 | 0.877 | 38 |
| 0.95 | 0.181 | 0.870 | 35 |

### §64.1  What the control arm bought

Everything. Without a zero-strength row the table reads as "the LoRA helps a little" and
the obvious next move is more steps and more data. With it, the answer is unmistakable:
**the swapped column does not move.** 0.867 with no LoRA loaded at all, 0.870 at 0.95.
Whatever the LoRA contributes to the face, the swap overwrites completely.

And the LoRA column never gets near recognition. Its best single image was 0.451 - a
tight elevator close-up, the friendliest frame in the set - against a swapped floor of
0.74 and a swapped mean of 0.87. Looking at the sheet says the same thing faster than
the numbers do: **every LoRA-only render is a different woman, and every swapped one is
her.**

This is the measurement §56 and §57 never made. Four training runs, a text-encoder
discovery, a trainer written from scratch, and the thing was never benched against the
alternative on a task it had not been tuned for.

### §64.2  So what is the identity LoRA still for

Not the face. Two honest remaining uses:

- **The body.** Across the sheets the LoRA arm is consistently closer to her build -
  slimmer, her proportions - and arcface measures none of that, because it is a FACE
  model. The swap cannot change a body. So judge an identity LoRA on the body and stop
  crediting it for the face.
- **When there is no swap model.** The whole result is conditional on inswapper being
  installed. Without it the LoRA is all there is.

The COSTUME LoRA is untouched by this. It solves wardrobe consistency, which no face
model addresses, and §57 stands exactly as written.

### §64.3  The swap is not a close-up trick

The worry with any face method is that it only works when the face is big. Scored by
size: faces at 90px and over swapped to 0.873; faces under 90px still swapped to 0.808.
It degrades gracefully, and it degrades from a height the LoRA never reached at any size.

### §64.4  The law

**A pipeline you have never benched against its own absence is a pipeline you do not
know the value of.** The control arm cost one extra strength setting - forty renders, a
tenth of the night - and it overturned a conclusion four training runs had been built
on. Put the null case in the grid. It is the cheapest row in any experiment and it is
the only one that can tell you to stop.

**Where the clock ended up.** One basis, stated plainly so the next block does not have to
guess which of three it is looking at: the head is FOUND in the first frame and then CARRIED
through the measured camera for the other eight samples. That is strictly better than what
§55's numbers were built on, which was a guessed box carried the same way, and it is stable in
a way that reading between three found heads was not. Rebuilt across all 129 clocked takes:

  still   121 takes   77 recognisable, 28 lost   three quarters hold 4.3 s
  walk     17 takes   11 recognisable,  5 lost   three quarters hold 4.0 s
  crouch    2 takes    0 recognisable             the carried box cannot follow a crouch

The last line is the honest cost of the revert. The END verdict on a crouch is now right,
because that uses the found head; the CURVE on a crouch is still wrong, because a carried box
leaves the head a third of a frame behind. So a crouch's `holds_until` is not to be trusted and
its verdict is. Both facts are on the take.

**A second pack, and a correction to the adoption.** One pack is an anecdote. The same
pipeline was run on a second drawn pack - dataset from its own views, captions from the narrow
vision ask, 1200 steps at rank 16 - and the two disagree about exactly one thing:

                       bai-liwen   renji
    prompt only          not her    0.345
    IPAdapter at 0.6       0.685    0.538
    the LoRA               0.749    0.709
    both                   0.768    0.436

The LoRA alone wins on both, and comfortably. The COMBINATION is a coin flip: best of the four
on one pack, worst on the other, where the reference image dragged the pose and the props
across from the portrait while the face drifted younger and rounder. The score caught what the
eye then confirmed. Two routes to one identity fighting each other is not a thing to ship on
the strength of one lucky pack, so where a LoRA exists the reference weight goes to zero and
the LoRA answers for the character alone.

Also worth recording because it cost half an hour: the trained file lands in
ComfyUI/output/loras and the loader only looks in ComfyUI/models/loras. The studio's older
trainer moves it and names it to avoid collisions; driving the workflow directly skips that,
and a LoRA that silently is not there looks exactly like a LoRA that does nothing.

**A third pack, and the gate earning its place.** The whole thing is one command now -
`_tools/pack_lora.py <pack>` builds the dataset from the pack's views, captions it with the
narrow vision ask, trains, runs the four-route comparison and adopts only if the LoRA beats
what the studio already does. Run on a third drawn pack, the Ferryman:

    reference path 0.611    the LoRA 0.555    NOT ADOPTED

Which is the first time it has lost, and it is not mysterious. The Ferryman's own tags read
"no humans, solo, spirit, translucent, white hair, faintly glowing eyes" - a translucent
figure with no garments to name and, arguably, no face for the encoder to compare. A method
that works on two people and not on a spirit is a method with a domain, and the gate found the
edge of it without being told where to look.

So the count so far is two adopted, one declined, and the declining is the part worth having.
A pipeline that adopts whatever it produces would have put a worse identity route into the
studio for that character and nobody would have noticed until a film looked wrong.
