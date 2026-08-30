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
