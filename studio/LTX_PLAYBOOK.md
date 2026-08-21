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
