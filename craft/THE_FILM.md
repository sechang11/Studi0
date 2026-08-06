# THE COAT — the writing, and why

`studio/movies/terra_field_coat.movie` → `studio/movies/terra_field_coat.json`
20 beats, 18 scenes, 4 chapters, **66.7 s** of finished picture, one character, two spoken lines.

    python3 studio/compile.py studio/movies/terra_field_coat.movie --timeline
    python3 scripts/short.py studio/movies/terra_field_coat.json

Nothing has been rendered. This document is the argument for spending the GPU time, and
the list of the three things that must be fixed before it is spent.

---

## 1. The film in a paragraph

A young woman is buckled into armour by hands that are not hers, is sent somewhere with a
blank face, and comes back to a hall where it is decided in her presence what she is —
without her being asked. She walks out of it and keeps walking until the clothes she
happened to be wearing that day are rags. At the lowest point somebody's money ends up in
her hand and she closes her fingers on it. In a border town she asks the price of a brown
coat on a hook, puts her own arm into the sleeve, and walks toward the camera for the
first time in the film. The last shot is the moor she crossed in rags, at golden hour, and
the only thing moving in the frame is the coat.

**The spine, in five sentences** (STORY.md §8 wants this written before the shot list, and
every beat below is auditable against it):

1. She is dressed by other people.
2. She is decided about by other people.
3. She is moved by the world until there is nothing left of what she was wearing.
4. She takes something, and then she chooses something.
5. She is in the same place as before, in a garment she picked, and she is still.

**The turn** is beat 15 — her fingers closing over a purse — and it is *expressed* at beat
18, her arm going into a sleeve. The film separates the two on purpose: the moment she
takes is ugly and unlit and lasts 2.6 s; the moment she chooses is quiet and dawn-lit and
has the score cut out from under it.

**Why the last image means something different because of what preceded it.** The final
shot is the same moorland as beat 11, at the same shot size, with the same person in it.
In beat 11 she is crossing it in someone else's clothes, handheld, leaving frame to the
right. In beat 20 she is standing still in a coat she bought, the camera is locked off,
and the only motion in the frame belongs to the garment. STORY.md §5 identifies "the same
subject in two states" as the cheapest and strongest thing this pipeline can produce and
recommends it as an *opening*. Used as an ending it costs the same two keyframes and pays
the whole film off.

---

## 2. Why this is a wordless film with two lines in it

TERRA's card says: *"Moves like she is waiting to be told she is allowed."* A character
written that way cannot be given dialogue to carry her arc, because the arc is precisely
that nobody addresses her. So:

* **She is the only person on screen for all 66 seconds.** Nobody else has a face, a name,
  or a line. The people who dress her are two hands and a gauntlet. The people who decide
  about her are an empty hall. The person who gives her the money is an open hand. This is
  not a cast limitation — it is the character's own brief rendered as coverage.
* **Two lines, five words and five words.** "Nobody will say which half." is a fragment of
  her own measured audition line (`voice_lines.dialogue`), spoken to an empty room.
  "How much for the brown one." is the first sentence in the film in which she asks for
  anything. The distance between those two sentences is the entire story.
* **No narration.** STORY.md §1 puts a wordless short at 45–70 s. This lands at 66.7 s.
  The narrated long-form shape would have halved the cutting rate and needed ~130 words of
  voice-over, and there is nothing here a narrator could say that the wardrobe does not.

---

## 3. The style: `cel_anime_90s`, and the four it beat

One style, `status: ready`, `compose: safe`, `engine: anime`.

**Why it, positively.** It is the only candidate that is simultaneously (a) on TERRA's own
`style_verdict` shortlist of styles that are *strong and holding at both seeds* with her,
(b) carrying a rendered `video_verdict` of `holds: yes` **measured over 8.04 s** — detail
octiles flat 1.01 → 0.976, boil 0.173 — and (c) `compose: safe`, meaning it has never been
recorded pushing a subject back in the frame. That third property is not cosmetic. Her
`style_verdict` records the finding that *the composition hijack and the identity failure
are one failure*: where a style wins the framing and shrinks her, her hair comes back red.
A film pinned this close needs a style that does not fight for the frame.

**What it beat, and why each lost.**

| candidate | on her shortlist | why not |
|---|---|---|
| `watercolour` | yes, and the strongest measured result in the whole set (92.1 from control) | its own `video_verdict` says *"avoid tight facial close-ups over long shots"* — the face goes muddy mid-clip. This film is eleven close and medium-close-ups. Disqualified by the one property it fails on. |
| `art_nouveau` | yes | her `style_verdict` names it as a style that **builds frames**. Rule 7 territory: it would put her inside an ornamental arch. |
| `oil_painting` | yes | its own card says *"Do not run this on the anime checkpoint"* — animagine returns cel shading with a blur. And its video behaviour is `INFERRED, not measured`. |
| `kyoani_soft`, `golden_age_illustration` | yes | both `works_for: video` are one-line assertions with no rendered clip behind them. `cel_anime_90s` has a measured 8-second clip. On a film whose longest beat is 7.4 s, that is the deciding difference. |
| `ova_80s` | yes | `works_for` says *"middling … INFERRED. Prefer it on held or slow cuts"*, and it collides with `cel_anime_90s` on the shared `retro artstyle` tail. Between two neighbours, take the measured one. |

**One thing it costs, stated.** `cel_anime_90s` carries `negative_add: 3d, modern anime
style, clean digital coloring, glossy, crisp lineart`, and the compiler warns that no
renderer has a negative input wired (rule 9). The library's own sample image had those
words and this film will not, so expect it slightly less clean than the card's example.
Nothing can be done about that from a `.movie` file.

---

## 4. The camera is the argument

Three moves, used 20 times between them, and the pattern is the film's thesis.

* **`push` appears exactly three times**, always at medium close-up, always on a pair of
  hands doing something at her body: the gauntlet closing the buckle at her throat (beat 2),
  her own fist closing on the table edge (beat 10), her own arm going into the sleeve
  (beat 18). Same size, same move, three different owners of the hands. Zero agency, then
  one gesture of refusal, then the choice. If a viewer notices nothing else, the film has
  still told them this.
* **`handheld` is the whole of act three and appears nowhere else.** The act where the
  world moves her is the only act where the camera is unstable.
* **`static` is everything in act four except the one push.** The camera stops moving at
  exactly the point she starts. `pull` is used once, on the empty hall, because CINEMATOGRAPHY
  reads a pull as isolation and that is what an empty room deciding about you is.
* **She leaves frame twice and enters it once.** Beat 4 she walks out to the left, beat 11
  out to the right, beat 19 forward toward the lens. The one entrance is the last act.

**Three dead cameras were never considered.** `dolly_zoom`, `orbit` and `rack_focus` are
byte-identical to static (rule 5) and `compose._live_camera()` would have silently
downgraded them anyway.

---

## 5. Beat by beat

`W` = damage rung. `mot` = what the video model is actually asked for, copied out of the
compiled JSON. Every line was read back from `terra_field_coat.json`, not predicted.

### I — ISSUED. costume `armour`, look `cold`, cue `unease`

| # | beat | size | W | why |
|---|---|---|---|---|
| 1 | `dressed_00` insert, 1.8 s | close | 0 | **The film's thesis as its first frame.** `mot: Two hands pull a breastplate strap tight across her ribs.` A mover, a verb, a path — and the mover is not her. 1.8 s, hard, straight out of a fade from black. We do not see her face yet, because she is being handled, not looked at. |
| 2 | `dressed_01` react `@push`, 2.6 s | medium close-up | 0 | `mot: A steel gauntlet pushes the throat buckle closed under her jaw. Nothing else in the frame moves.` The hold clause is doing real work: she is the only thing in the frame that could move and she does not. Push #1 of 3. |
| 3 | `dressed_02` establish, 4.2 s | wide, no humans | – | `mot: Banners lift on their poles above the courtyard wall.` **The establish is third, not first.** We see what she is being dressed *for* only after we have watched her being dressed. One of only two wides in the film, and it has nobody in it, so rule 2 is not violated. |
| 4 | `sent_00` master, 3.6 s | medium | 2 | `mot: She walks out of frame to the left.` Rung 2 of the plate ladder — *"scratched across the front, one pauldron dented"*. The armour ladder is only trusted to rungs 0–2 with the danbooru name in the prompt (her `costume_verdict`), so the film never asks it for more. The whole campaign is one shot of her leaving. |
| 5 | `the_gauntlet_00` insert, 1.8 s | close, no humans | – | `mot: A steel gauntlet drops through the frame into deep snow.` The aftermath insert, and EDITING §1 says an aftermath insert is **cut** to, never dissolved to. |

### II — DECIDED. costume `court`, look `golden`, cue `tense_strings`

| # | beat | size | W | why |
|---|---|---|---|---|
| 6 | `the_hall_00` establish `@pull`, 4.2 s | wide, no humans | – | `mot: An iron chandelier swings above a long timber table.` The second and last wide. A room built for a great many people, with none in it. |
| 7 | `decided_00` hold_silent `@hold_frame` `@8s`, 5.5 s | medium | 1 | **A deliberate hold, and the only one in the film that is not derived from an action.** `mot: Nothing in the frame moves.` `hold_frame` is the library's single `status: ready` stillness card and it names no occupant, which is why it was authored (its own card records `hold_nobody` drawing a person into a shot written "no humans"). `silence: true`, so the score drops out for 5.5 s — the compiled cue timeline shows `tense_strings` splitting into two runs around it. This is the shot where the decision is made, and the shot contains no decision, no room, and no other person. |
| 8 | `she_says_it_00` speak, 3.2 s | medium close-up | 2 | *"Nobody will say which half."* A spoken beat has no shot line to derive from — the failure demo_cast diagnosed — so it gets a named ready card, `@hand_to_face_only`: `mot: She raises her right hand to her face. Nothing else in the frame moves.` A hand going to the face while saying that is the gesture of someone who has stopped expecting an answer. `mood` carries the staging (the empty table running away behind her) because a descless beat's whole prompt would otherwise be identity + look + place. |
| 9 | `the_glove_00` insert, 1.8 s | close, no humans | – | `mot: A white glove drops through the frame onto the flagstones.` **The damage ladder as an event.** Court rung 3 reads *"both gloves gone"*; instead of arriving as a state at the next shot, one of them is shown leaving. |
| 10 | `her_fist_00` react `@push`, 2.6 s | medium close-up | 2 | `mot: Her fist closes on the edge of the table. Nothing else in the frame moves.` Push #2. The first thing in the film she does that nobody asked her to. It is three inches of movement and it is the act's whole button. |

### III — THE ROAD. costume `default`, looks `overcast`→`storm`, cue `desolate`, camera `handheld`

The traveller costume is the one that **lands at all five rungs in every arm at both
seeds** (her `costume_verdict`), so it is the only one the film is allowed to ruin, and it
is ruined all the way to 4.

| # | beat | size | W | why |
|---|---|---|---|---|
| 11 | `the_road_00` master, 3.6 s | medium | 2 | `mot: She walks out of frame to the right.` Rhymes with beat 4 and reverses it. Handheld. |
| 12 | `the_sash_00` insert, 1.8 s | close, no humans | – | `mot: A torn red sash blows across the frame.` **Continuity, not decoration.** Rung 2 says the sash is loose; rung 3 says the sash is *"used as a bandage on the forearm"*. The garment that blows out of frame here is the bandage in the next shot. The ladder is being used as a chain of events across a cut. |
| 13 | `the_ford_00` build, 3.1 s | medium | 3 | `mot: She stumbles forward through shallow water over stones.` `build` is in `MOTION_BUSY_TEMPLATES`, so the hold clause is correctly *not* appended — this is the one beat that should not be told to keep still. It is also the only three-cut beat in the film, which is where the pulse comes from. |
| 14 | `the_purse_00` insert, 1.8 s | close, no humans | – | `mot: A leather purse drops into an open hand.` A **cut**, because EDITING §1 says a reveal is cut to. We never see whose hand held it out and the film never explains it. "Money that was not hers" is one insert long. |
| 15 | `what_it_cost_00` react, 2.6 s | medium close-up | 4 | `mot: Her fingers close over a leather purse at her chest. Nothing else in the frame moves.` Rung 4: *"gold dress in rags, bare forearms wrapped in cloth, blood dried at the temple."* **This is the turn.** It is deliberately the ugliest shot in the film and it is over in 2.6 s. |

### IV — CHOSEN. costume `field`, looks `dawn`→`golden`, cues `quiet_dawn`→`hopeful_rising`, `pace: slow`

`pace: slow` multiplies every shot in this act by 1.35. The act is 22.5 s of a 66.7 s film
— a third of the runtime for a fifth of the beats. EDITING §11: *the single longest hold
in the piece belongs at the very end.*

| # | beat | size | W | why |
|---|---|---|---|---|
| 16 | `the_rail_00` insert, 2.4 s | close, no humans | – | `mot: A heavy brown coat swings on a hook above the cobbles.` **The act opens on the object, not on the place.** STORY.md §4: a title drop lands where the object is *given*, not where it is used. There is no establishing shot of the town at all; the town is established at beat 19, by her walking through it. |
| 17 | `she_asks_00` speak, 4.3 s | medium close-up | 1 | *"How much for the brown one."* `@hand_reach` — `status: weak`, and the compiler says so. Used anyway, and **staged to its own verdict**: the card lands as a reach *only where the hand is already large in frame* (0.904 at `close`, 2.231 at `anchor`), so the `mood` line puts the sleeve at her hand and the shot at medium close-up. This is the demo_cast `cup_lift` lesson applied: the precondition is not *a thing in frame*, it is *a thing within reach*. |
| 18 | `the_sleeve_00` react `@push`, 3.5 s | medium close-up | 1 | `mot: Her arm pushes through the sleeve of a brown coat. Nothing else in the frame moves.` **Push #3, and the film's answer to beat 2** — same size, same move, same buckling-in gesture, opposite hands. `silence: true`: the compiled cue timeline shows a 1.3 s hole in `quiet_dawn` sitting exactly under this shot. STORY.md §8: *check the biggest beat in the film has silence in it.* |
| 19 | `she_walks_00` master `@8s`, 4.9 s | medium | 1 | `mot: She walks forward toward the camera between the stalls.` **The only shot in the film where she moves toward the lens**, and it is not a coincidence that it is at `market_street`: her own `motion_verdict` measured `walk_in` at `market_street` holding her frontal and stable for the full 8.04 s — *the clean confirmation that identity survives 8 s at strength 0.5*. It is the one place in the entire library where this shot is known to survive its own length, and it is also the border town where the coat was bought. The clip is generated at 8 s and cut at 4.9, so the face never gets near the drift ceiling. Camera `static`: she does the moving now. |
| 20 | `the_moor_again_00` hold_silent `@8s`, 7.4 s | medium | 2 | `mot: A heavy brown coat blows across her legs. Nothing else in the frame moves.` The longest beat in the film, last. She is still and the coat is not. Rung 2 of the field ladder — *"torn at the pocket, satchel strap knotted where it broke, boots caked"* — which is the **first damage in the film that is hers**: every previous rung was wear on something she was issued or handed. The coat has started to earn its own. |

**Why not rung 4 of the field coat.** Field rung 4 is *"no coat, gold dress in rags"*. The
ladder's top rung deletes the object the film is named after. The act stops at 2.

---

## 6. The cut

18 scene boundaries: **11 cut (61%), 4 dissolve (22%), 3 fade_black (17%)**. EDITING §8
expects roughly cut ~50%, dissolve ~25%, fade exactly 3. Three fades, spaced at the film's
real structural hinges rather than by the clock: the opening, the courtyard→hall act break,
and the river→market act break. The one act break that is *not* a fade is II→III, which is
a `dissolve`, because she is not cut away from that hall — she leaves it, and time passes.

Every `dissolve` in the film is at a boundary crossing **two axes at once** (new place
*and* new time): courtyard→snowfield, hall→moor, moor→river, market→moor. Every `cut` is
inside one axis, or is a consequence, an aftermath insert, or a reveal — the four things
EDITING §1 says must never be dissolved through.

`match_cut` was wanted for beat 18 and **not used**: its card is `status:
needs_authoring`, compile.py would have silently downgraded it to a cut and warned. The
rhyme is carried by identical framing and identical camera instead, which is free and
which works today.

**The rhythm.** Six beats at or under 2.6 s against a 7.4 s close. The shortest and longest
shots in the film are 1.8 s and 7.4 s, a 4:1 spread — EDITING §5's complaint about CHRONO
is that 81% of it sat inside a single 4-second band. Nothing here runs more than four
consecutive beats without one under 2.6 s, and no three consecutive beats share a shot
size.

**The score.** Resolved off the real timeline by the compiler, never hand-written: seven
cues, overlaps of ~2 s at each junction, no gaps, and the last cue ends 1.6 s past the
final frame where the master fade eats it. Two deliberate holes in it, at beats 7 and 18.

---

## 7. THE ONE THING THAT IS NOT WIRED

**`costume:` does not reach the renderer, and until it does this film renders in the wrong
clothes from end to end.**

The resolver already has the whole feature. `compose.resolve()` reads `sel["costume"]` at
`studio/compose.py:2366`, looks it up in the character's `costumes` map at `:2427`, warns
by name if it is unknown, and falls back to the default. `studio/_tools/turnaround.py`
already passes one. The gap is entirely in the compiler: `costume` is not in `compile.py`'s
`VARS` table, and it is not in the dict handed to `compose.resolve()` at `compile.py:688`.
An unknown lowercase key in a `.movie` file is stored on the scene and read by nothing, so
this fails **silently** — no warning, no error, a clean compile.

Read out of the compiled JSON, beat 18, the turn of the film:

    terra branford (final fantasy vi), 1girl, solo, long wavy green hair, ...,
    red cape, gold dress, red sash, red boots, travel dust on the hem,
    her arm pushing through the sleeve of a brown coat, medium close-up, ...

`_assemble_anime()`'s own docstring says **earlier and more specific wins**, and it says so
citing the exact failure this is: a garment named early beat a damage state named late, and
the model resolved the contradiction in favour of the earlier claim. Here the traveller
gold dress sits at slot 5 and the brown coat sits at slot 6 as part of the shot line. The
coat loses. The final shot of a film called THE COAT renders a red cape.

**The fix is two lines**, and this `.movie` file is already written in the resolver's own
spelling so that the fix turns the film on without touching it:

```python
# studio/compile.py, in VARS, next to wear at line 142
("costume",     ("any",     "",   "studio/characters/<ID>.json costumes map - WHICH "
                                  "outfit. wear is the damage rung within it")),

# studio/compile.py:688, in the dict passed to compose.resolve()
"character": who, "emotion": emo, "wear": wear, "costume": v.get("costume", ""),
```

`resolve()` in compile.py already inherits any key down movie → chapter → scene by
override, so a chapter-level `costume:` propagates with no further work, which is exactly
how the four movements are written.

**Two related things worth doing at the same time, neither of which blocks the render:**

1. **compile.py should warn on an unrecognised variable name.** This whole class of bug —
   a knob typed into a `.movie` file that is stored and then read by nobody — is the exact
   failure the format's own header says it exists to prevent (*"NOTHING SILENTLY DOES
   NOTHING"*). The parser has `VARS` in hand at the point it writes `target["vars"][k]`
   and could say so in one line.
2. **`compose.py` strips a place card's `scenery, no humans` when a character is in the
   shot, and has no equivalent for a place card that names its own weather.**
   `studio/places/moorland.json` ends in `grey overcast sky, distant rain`; place is
   assembled before look; earlier wins; so `look: golden` on that card renders grey. This
   film's final shot works around it by writing the moor as free text with the sky clause
   removed — checked in the compiled prompt, not assumed. The mechanism for the mirror-image
   problem already exists as `LOOK_PLACE_NOUNS` (a look that names a place gets stripped
   when a place card is present). A `PLACE_SKY_NOUNS` doing the same in the other direction
   is the same shape of fix.

---

## 8. Every warning the compiler printed, and what was done about it

The first compile raised one that mattered. The rest are project-level and are recorded
here so nobody has to re-derive them.

| warning | what was done |
|---|---|
| `place_vs_shot` — *"your place and your shot ask for different pictures: 'scenery' against 'close-up'"* | **Fixed.** Five close inserts were pulled into their own scenes with a free-text close place (`deep wind-crusted snow filling the frame, no horizon visible`, etc). A place card is a location; an insert is a surface; the card's scenery nouns beat the two words at the end of the shot line. This is demo_cast's `the_coins` lesson, and it is why the film has 18 scenes for 20 beats. Gone on recompile. |
| moorland's own sky beating `look: golden` on the final shot | **Fixed**, by writing that one place as free text minus the sky clause. Not a warning the compiler raises — found by reading the compiled prompt. See §7.2. |
| *"90s cel anime is expected to be unstable once it moves"* followed by its own `video_verdict` saying `CONFIRMED to hold` | **Ignored, deliberately.** The warning quotes the data that contradicts it. This is the open bug "Fix the style card warning that says the opposite of its own data". The style is measured to hold for 8.04 s and the film's longest clip is 8 s. |
| *"90s cel anime asks for extra words in the negative prompt … the renderer has no negative input wired"* | **Nothing to do** (rule 9). Recorded in §3 as a stated cost. |
| *"the motion 'hand_reach' is marked weak"* | **Accepted and staged to the card's own verdict.** See beat 17. |
| *"the posture from `<emotion>` was dropped because the damage level is N"* × 11 | **Intended.** The emotion cards' `body` tags are whole-figure postures and her `emotion_verdict` records four cards losing the face entirely to them. Only beat 1 sits at wear 0, and it has no character in it. Every beat that shows her runs at wear ≥ 1, so the posture tag is suppressed on all of them — including `tender`, whose body tag is *"reaching toward face, open palm"* and would have fought the reach at beat 17. |
| *"`<place>` is written as an empty location … those words were removed"* × 3 | **Intended.** snowfield, moorland and riverbank all carry `scenery, no humans`; the resolver strips it on the shots that have her in them and leaves it on the inserts that do not. |
| *"emotion `<x>` renders as face tags, but its voice_style is not routed to TTS yet"* × 12 | **Nothing to do.** Known, documented on her card at `voice_emotion_routing`. It costs this film nothing: the two spoken lines are small and flat and want the neutral read anyway, which is what an all-zero vector gives. |

---

## 9. The decisions that are unmeasured, stated plainly

* **`face_weight: 0.6`** is the house default and nothing on TERRA's card measures an
  IPAdapter weight for her. Her `realism_verdict` recommends IPAdapter 0.0 for *painterly*
  styles on the illustration engine; `cel_anime_90s` is cel, which is the LoRA's native
  medium, so 0.6 is kept. If the first keyframes come back with the style suppressed,
  this is the knob.
* **The danbooru name is kept in every prompt**, per rule 3 and her `identity_correction`.
  Her `costume_verdict` says every costume improves with the name *stripped*, and that
  those two facts are in tension is a property of the character, not of this film. Once
  `costume:` is wired, the four movements are the natural place to test it: the same film,
  name kept and name stripped, is a controlled A/B across four wardrobes.
* **The emotion arc is `neutral` for three movements and then `tender` → `resolve` →
  `determined`.** Only cards her `emotion_verdict` names as working were used, and `rage`,
  `despair`, `relief`, `shame` and `awe` were avoided entirely. Her face is deliberately
  doing nothing until her hands start doing something.
* **Nothing has been watched.** There are no eyes on this box. Every claim above about how
  a beat will behave comes from a card that was rendered and looked at by somebody else, or
  from the compiled JSON. The one number that would change the plan if it is wrong is
  `walk_in` at `market_street` holding 8.04 s, and that one *was* measured on this
  character at this LoRA strength.

## 10. Order of operations

1. Apply the two-line `costume` patch in §7, recompile, and diff the prompts. Beat 18
   should say `heavy brown travelling coat buttoned to the collar, leather satchel across
   the body` where it currently says `red cape, gold dress`.
2. Render **keyframes only** and look at all 20. The style warning is right about one
   thing: the clip stage costs about eight times the keyframe stage.
3. Check three frames specifically — beat 3 and beat 6 for whether the two wides read as
   deliberate rather than as the film losing her; beat 19 for whether the market crowd
   fights `1girl, solo`.
4. Then clips.

---

## 10. GROUND TRUTH: what the delivered film actually shows

Written after watching the delivered `studio/samples/the_film/final/THE_COAT.mp4` as 55 frames
at 1fps plus the four per-shot watch sheets, and after auditing the compiled JSON rather than
the reports. Everything below is read off pixels or off the JSON.

### 10.1 The nine measured rules were all followed

Audited on `studio/samples/the_film/terra_field_coat.json`, the film that was actually rendered.

| Rule | Result |
|---|---|
| 1. actions not compositions | 20 of 20 beats carry a motion string; 17 derived from the shot line, 3 from cards. Zero accidental holds. |
| 2. closer than full body | 11 close-ups, 6 mediums, 2 wides. No beat asks for full body. Both wides are character-free. |
| 3. danbooru name in every prompt | Present in all 12 beats that carry a character ref. Zero misses. |
| 4. no `look: night` | No beat carries it and the string `night` appears in no prompt. |
| 5. no dead cameras | static 11, handheld 5, push 3, pull 1. `dolly_zoom` / `orbit` / `rack_focus` appear zero times. |
| 6. LTX budget by the action | Every shipped slice ends at or before 6.0s of its clip. |
| 7. style hijack | cel_anime_90s is compose:safe and never pushed her back in frame. |
| 8. LTX audio, no SR | LTX throughout, SR stage off. |
| 9. no negatives relied on | Nothing in the film depends on a negative prompt. |

The rules are clean. What follows are things the rules do not yet cover.

### 10.2 THE WEAR LADDER DOES NOT REACH THE PIXELS, and the costume arc is thinner than reported

This is the substantive finding of the ground-truth pass and it corrects a headline claim.
The costume text in the prompts is correct, specific and well written. It is not rendered.

Asked for, against what is on screen:

- `i_issued_sent_00` asks **"steel breastplate scratched across the front, one pauldron dented,
  mail torn at the left sleeve"**. On screen: a strapless teal bodice with bare shoulders and one
  long red glove. No breastplate, no pauldron, no mail. This is the shot that closes act one's
  dressing sequence and the armour is simply absent from it.
- `ii_decided_her_fist_00` asks **"green gown with a torn hem, one glove off and held in the
  hand"**. On screen: bare shoulders, no gown, no glove anywhere in frame - two shots after the
  same gown rendered correctly at rung 1 in `ii_decided_decided_00`.
- `iii_the_road_what_it_cost_00` asks **"gold dress in rags, bare forearms wrapped in cloth,
  blood dried at the temple"**. On screen: bare shoulders and an unclothed-looking chest, hands
  clasped over a gold object, no visible wraps, no blood.

The pattern: **rung 0 and rung 1 render; rungs 2 and above collapse to Terra's canonical
strapless silhouette.** The danbooru name is load-bearing for identity (rule 3) and it is also
pulling the wardrobe back to the character's shipped design, and damage tags lose that fight.
The two are the same tag doing both jobs, so this is not tunable by weight alone.

Consequence for the film: the costume arc that reads on screen is three states, not four times
five. Armour is legible only in `dressed_01` (the gorget at her jaw); the court gown is legible
in two shots; the coat is legible in five and is the one that fully lands. Everything between
those reads as the same bare-shouldered dress. The film still works, because the coat - the
thing it is named after - is the state that renders. But the five-rung ladder is currently an
authoring fiction on this engine at this framing.

Worth measuring next: whether the ladder survives with the danbooru name at reduced weight and
the LoRA raised to compensate, or whether damage has to be carried by props and place rather
than by garment tags.

### 10.3 What act three costs the film

`iii_the_road_what_it_cost_00` is act three's closing emotional beat and, because the rags did
not render, it reads as a bare-chested close-up rather than as a woman in ruined clothes. In a
wordless film about what she is wearing, that is the wrong accident to have in the wrong place.
It is not fixable at the cut - it is the only close-up carrying that moment - but it should not
be presented as the ladder working.

### 10.4 Act four is a different continent

Acts one to three are European: a stone courtyard, a snow field, a green gothic hall, a moor.
Act four renders as a Japanese festival street - paper lanterns, triangular bunting, and shop
signage in kana on two shots. It is a good-looking street and the coat lands in it, but the
border town where she buys the coat does not appear to be in the same world as the hall where
she was decided about. `market_street` was chosen because it is the one place with a measured
8s identity hold, and that measurement was about her face, not about the set.

### 10.5 Shot 14 does not read

`the_sleeve`, the film's turn, is a hunched brown mass filling the right of frame with a hand at
a cuff and a street receding behind it at a broken scale. Knowing what it is meant to be, it is
an arm going into a sleeve. Not knowing, it is unreadable. Moving the line onto shot 13 was the
right call and it rescues the moment, but the insert itself is the weakest frame in the film and
it carries more story weight than any other weak frame.

### 10.6 `ipadapter_weight` in the film JSON said 0.6 and every frame was rendered at 0.0

`reroll.py` forced the weight to 0.0 at runtime while the compiled film on disk still declared
the 0.6 house default, so the file did not reproduce its own render. Corrected in
`studio/samples/the_film/terra_field_coat.json` with the measurement written into the file.

### 10.7 What is good, said plainly

Three sequences are genuinely good and would survive being shown to somebody who does not know
how they were made: the gloved hands pulling the strap tight across a crimson torso while we
never see whose hands they are; her walking away across a snow field until she is a speck; and
3.9 continuous seconds of her going down in the ford and pushing back up off one hand. The white
glove on the flagstones is the best insert. The empty green hall is the best composition. The
cut is disciplined - two dropped beats that did not read, one reorder that buys the gauntlet and
the glove as a rhyme, and no shot outstaying its material.
