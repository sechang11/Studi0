# STORY.md — writing the films, not rendering them

Everything in `FILMMAKING.md` is about getting pixels out of the box. This file is about
whether anyone wants to watch them. Written by the story editor after auditing
`films/chrono.json` (109 shots, 10:28, narrated recap) against `films/hollow-choir.json`,
`films/last-good-year.json`, `films/carriage-seven.json` and `films/puddle.json`.

All numbers below are **measured off this box**, not estimated. Re-derive them any time
from a film's `narration.json` plus its shot list.

---

## 1. Pick the shape before you write a word

Three shapes work here. They are not interchangeable and they have different clocks.

| | Wordless short | Dialogue short | Narrated long-form |
|---|---|---|---|
| Example | `puddle.json` | `carriage-seven.json`, `hollow-choir.json` | `chrono.json` |
| Script | `cartoon.py` | `cartoon.py` | `epic.py` |
| Length | 45–70 s | 60–90 s | 5–15 min |
| **Shots per minute** | **25** | **~20** | **10.4** |
| **Words per minute** | 0 | 45–65 | **124** |
| Who carries the story | cutting rhythm + score | subtext in 6–12 word lines | the narrator |
| Fails as | a moodboard | a radio play with pictures | a Wikipedia article read aloud |

**The one number to internalise: narration halves your cutting rate.** Every narrated shot
costs `0.30 s lead + speech + 1.15 s tail` — 1.45 s of dead air per line before a single
word is spoken. You physically cannot cut every two seconds in a narrated film, so:

- **Never plan comedy timing, action beats or a chase in a narrated film.** Setup / action /
  reaction at 2 s each is a `cartoon.py` structure. In `epic.py` the same three beats take
  20 seconds and the joke dies.
- **Conversely, never try to carry 10 minutes of plot on dialogue.** 90 seconds of
  `carriage-seven.json` holds 71 words. A recap needs 1,300.
- If your idea needs both — a long story *and* fast physical comedy — it is two films.

### Which shape a given idea wants

- **Original story, one location, one turn** → wordless or dialogue short. This is where
  the box is strongest and where `STORIES.md`'s reasoning applies.
- **Somebody else's plot, retold** → narrated long-form. There is no other way to move
  through six eras in ten minutes.
- **Original story you want to run 10 minutes** → be honest: you probably have a 90-second
  story and 8 minutes of connective tissue. Narration is not a licence to be long.

---

## 2. The narration clock (measured)

From `chrono-trigger/narration.json` — 100 lines, Chatterbox, `NARRATOR` voice at
`pitch 0.88`, `rate 0.85`:

| Quantity | Measured |
|---|---|
| Words written | 1,301 |
| Speech audio generated | 446.6 s |
| **Spoken rate** | **2.89 words/sec** (median 2.90, range 1.60–3.63) |
| Raw Chatterbox rate before `rate: 0.85` | **~3.4 words/sec** |
| Air added per line (`LEAD` + film `tail`) | 1.45 s |
| Finished film | 627.6 s = **10:28** |
| **Words per second of screen time** | **2.07** |
| **Words per minute of finished film** | **124** |
| Median line | **14 words** (min 2, max 23) |

### Word budgets you can use directly

- **A 10-minute narrated film is ~1,250–1,300 words.** Not 1,800. Not 900.
- **One minute of film = ~124 words = ~9 lines = ~10 shots.**
- **A single line: 8–20 words.** 14 is the sweet spot. Below 8 the 1.45 s of air dominates
  and the shot feels like a stutter; above 20 you are asking one LTX shot to hold nearly
  10 seconds, which is `FRAME_CAP` (241 frames @ 24 fps = 10.04 s) and the practical drift
  ceiling. Nothing in `chrono.json` exceeds 23 words and that line is the worst-paced in
  the film.
- **Line → shot length:** `shot seconds ≈ words / 2.89 + 1.45`. A 14-word line is a 6.3 s
  shot. A 20-word line is an 8.4 s shot.
- **Silent shots cost `seconds`** (film-level default, 4 s in `chrono.json`). They are the
  cheapest tool you have for pace. Use more of them than feels natural — see §4.

### If you change the voice, re-derive

`rate` in the `voices` block is a rubberband tempo multiplier applied *after* generation,
so it scales the whole clock linearly. `rate: 0.85` bought a gravelly, unhurried narrator
and cost 15% more runtime for the same script. At `rate: 1.0` the same 1,301 words would
run ~9:00 instead of 10:28. **Decide the voice before you decide the word count**, and
always run `--stage narrate` first and read `narration.json` before rendering any picture:
it is 90 seconds of GPU that tells you exactly how long your film is.

### Long shots are nearly free — exploit it

LTX charges ~the same for 193 frames as for 97 (13.7 s vs 13.5 s measured), while each
extra shot costs a whole keyframe *and* a whole clip. So a narrated film sized to its
narration is **cheaper per minute** than short-shot cutting. Do not pad a script to fill
shots, and never split one idea across two shots to "keep it moving" — in `epic.py` that
is strictly more expensive and reads worse.

---

## 3. Narration must not describe the picture

This is the rule that separates a film from a slideshow with a voiceover. The picture
already tells the viewer *what is in frame*. The narrator's only job is to supply what the
frame cannot: **causality, interiority, time, scale, and consequence.**

Test every line: **cover the picture and read the line. Then mute the line and watch the
picture. If you learned the same thing twice, one of them is wasted.**

Worked examples from the audit:

| Shot | Written | Problem | Fixed |
|---|---|---|---|
| ruined city | *"The sky is dead. The cities are bones. Nothing grows."* | The frame is a dead sky over a bone city where nothing grows. Zero new information. | *"Nobody alive here remembers what a sky is supposed to look like."* |
| white flash, silhouette dissolving | *"It kills him where he stands."* | The audience just watched it happen. The narrator is explaining the most powerful image in the film. | **No line.** Let it be silent. |
| two characters watching lanterns rise | *"Marle finds him in the crowd, and they watch the lanterns go up together."* | A caption. | *"Neither of them says anything about it. They don't have to."* |
| dormant creature under rock strata | *"It has been down there ever since. Waiting. Growing."* | Good — the picture shows a thing underground; only the narrator can supply *sixty-five million years of it.* | keep |
| ordinary 1999 city street | *"The day of Lavos comes. And nothing happens."* | Best line in the film. The picture is deliberately boring; the line is what makes boring devastating. | keep |

Corollaries:

- **Where the picture is at its strongest, shut up.** The three most important images in a
  narrated film should be silent or nearly so. A narrator talking over your best shot is
  the single most common failure mode of this format.
- **Adjectives belong in the `prompt`, not the `say`.** "Devastating", "bleak", "beautiful"
  are art direction. If the narration has to tell the viewer the shot is sad, the shot
  isn't.
- **Never name what is on screen unless the name is new information.** "A boy named Crono"
  earns its words once. "Frog takes up the blade" does not need "the reforged legendary
  blue-white sword" — we are looking at it.
- **Filler adverbs are the tell.** *simply, suddenly, finally, meanwhile, of course.* Each
  is ~0.35 s of a 10-minute film spent on nothing. Delete on sight.
- **Dramatise, don't summarise, when a shot already exists for it.** *"He is arrested"* over
  a shot of him being arrested is a caption; *"The chancellor has been waiting for a reason"*
  over the same shot is a film.

---

## 4. Structuring a narrated recap

A recap has a structural advantage and a structural trap. The advantage: the audience
opted in — they *want* the plot, so you never have to earn attention with mystery. The
trap: a plot summary has no shape of its own, and 100 sequential facts is not a story.

### Give it a spine, then hang the facts on it

`chrono.json` works because underneath the six eras there is a five-beat spine:
**an ordinary afternoon → proof the world ends → a war fought across time → the cost
(a death) → the same ordinary afternoon, kept.** Every shot is auditable against that
spine. Write the spine in five sentences *before* the shot list, and cut anything that
does not serve it.

### The four ordering rules

Every ordering fault found in the audit was one of these:

1. **Never explain a thing before you have shown it.** Two shots in `chrono.json` mention
   "the machine" one shot *before* the machine appears. Swap them; it is free at
   `--stage edit`.
2. **Never put a beat between a blow and its reaction.** The biggest beat in the film is a
   character's death; a shot about a *different* character's fate sits immediately before
   it, so the death arrives on a divided audience. Nothing goes between the strike and the
   flinch.
3. **Exposition goes before the climax, never after.** "They break it anyway" is followed
   by 23 words explaining what the antagonist's plan had been. That is a footnote after a
   kill and it deflates the ending. If a fact matters, it matters *while the outcome is
   still in doubt*.
4. **A title drop lands where the object is given, not where it is used.** The line naming
   the film's title object is stranded mid-climb, two shots after the object changes hands.

### Signpost every departure from chronology

A recap teaches the viewer "this is what happened next" in its first minute. The moment
you break that — a character-backstory block, a flashback, a montage of side-stories —
the viewer reads it as chronology and gets lost. Either keep strict order or spend three
words on the signpost (*"Long before any of this…"*, *"They each had a reason."*).

### Connective clauses are the highest-value words in the film

The audit's biggest finding: `chrono.json`'s comprehension problems are all *missing
single clauses*, not missing shots. Four examples, each a ~6-word fix that would join
two things the film already shows: the old man at the void is the same scholar thrown
through time; the smith who reforges the sword is another of them; the pendant that opens
the first door came from the sky-kingdom; the impact that ended the dinosaurs is why the
next era is frozen.

**Budget explicitly for this.** In a narrated recap, spend ~5% of your word count on
clauses whose only job is to say *"the thing you saw an hour of film ago and the thing
you are seeing now are the same thing."* They cost nothing to render and they are the
difference between "a series of events" and "a story."

### Antecedent decay

Track the last time you named each character. A pronoun is unusable once ~60 seconds and
~8 shots have passed since its noun — `chrono.json` says "Her fortress" twelve shots
after the last mention of the woman in question. **Re-name any character the viewer has
not heard about for a minute.** It costs two words and it is never wrong to do.

### Denouement gets more room than you think

Long-form buys you an ending. `chrono.json` spends its last ~28 seconds on five quiet
shots with no plot in them and it is the strongest passage in the film. Don't stop on the
climax; the climax is not what the film is about.

### Every returning character needs a reason to have returned

If someone the heroes defeated is standing in the final line-up, say why in one clause.
Otherwise the frame contradicts the narration and the viewer stops trusting it.

---

## 5. The cold open

**Fifteen seconds.** Roughly three shots in a narrated film, four in a short.

The rule: **open on the stakes, not the status quo.** A recap viewer has already agreed to
watch; what they have not been given is a reason to believe the story is *big*. Opening on
a pretty establishing shot of the peaceful world spends your best 15 seconds telling the
audience nothing is wrong.

Proven openings on this box:

- `hollow-choir.json` — a match struck in total blackness (3 s), then a tilt up into a vault
  of hundreds of bells (3 s). Mystery, then scale, before a word. Two keyframes.
- `last-good-year.json` — a sunlit town square, then **the identical framing burnt to ash.**
  The entire premise, in two shots, wordless, for the price of two keyframes. This is the
  cheapest and strongest hook the pipeline can produce and it should be reached for first.
- `puddle.json` — the gag setup in shot one, because a comedy short's stakes *are* the gag.

The generalisable move: **find the two images in your film that are the same subject in
two states, and put them first.** Before/after, sleeping/waking, whole/ruined. A recap of a
story about a hidden threat should open on the threat, not on the town.

Practical note: **moving a shot is free, copying one is not.** `epic.py` builds one segment
per shot `id` in list order, so reordering costs a `--stage edit` re-run and no GPU. Adding
a duplicate shot needs a new `id` and therefore a new keyframe and clip. When you want an
image up front that also appears later, **move it and rewrite its old line** rather than
rendering it twice — and check the shot you are moving does not carry an era `titles` card.

---

## 6. Line-by-line checklist

Run this over every `say` before rendering anything. It costs an hour and saves a re-cut.

1. **Word count 8–20.** Outside that band, justify it.
2. **Does it duplicate the frame?** (§3) If yes: rewrite or delete the line, keep the shot.
3. **Does it duplicate the previous line?** *"Marle says this can be stopped."* / *"They
   decide to change it."* — the second is 5 words of nothing. Delete.
4. **Is it internally consistent?** *"rationing a food supply that ran out long ago"* — you
   cannot ration what is gone. Read every line as a hostile reader would.
5. **Are both halves earning?** *"losing a war against the Reptites, who are winning it
   easily"* says one thing twice. Halved clauses are the commonest padding.
6. **Would a first-time viewer know who "he", "she", "it", "them" is?** (§4)
7. **Is anything abstract that could be concrete?** *"a thing that lets time be given a
   second answer"* → *"one chance for time to answer differently."*
8. **Read it aloud at 2.9 words/sec.** Anything that trips your tongue trips Chatterbox
   worse. Numbers spoken as words ("twenty first of July, nineteen ninety nine") eat 3+
   seconds — use them only when the precision is the point.
9. **Could the shot carry it with no line at all?** If yes, that is usually the better film.

---

## 7. Adapting existing IP as commentary

A plot recap is commentary and it is a legitimate thing to make. The line to stay on the
right side of is **protected expression**, and it runs in three places.

**Names and facts — fine.** Character names, place names, era labels, the sequence of
events, the title of the work being discussed. A recap that cannot name the characters is
not a recap. Use the plain title as a plain title card; do not reproduce the original's
logo, typeface or key art.

**Narration — write it, never quote it.** The one hard rule: **no line of the source's
script appears in the film, in any form.** Not the famous ones, not paraphrased-but-
recognisable, not "the line everyone knows" as a knowing wink. `chrono.json` passes this
cleanly — 100 lines, zero borrowed dialogue, and it deliberately steps around the source's
most-quoted lines. Keep doing exactly that. If you find yourself reaching for a quotation
because it is *better* than what you wrote, write something better instead; that is the
whole job.

**Visual prompts — this is where it actually drifts, not in the prose.** Writing your own
sentence about a character does not make the *rendered image* original. Three habits keep
you on the right side:

- **Describe role and silhouette, not a costume inventory.** An itemised list of a
  character's exact garments, accessories and hair — *"white tunic under a short dark blue
  gi, an orange sash, a katana across his back"* — is a specification of the original
  design written out longhand, and the render will be a copy of it. *"a lean teenage
  swordsman with wild spiky crimson hair"* is evocation, and it is enough: the reason it
  works is that a silhouette plus one signature colour is all a viewer needs to track a
  character. This is the same constraint that makes character consistency work
  (`FILMMAKING.md`), so the safe choice is also the better-looking one.
- **One signature, then stop.** A red scarf. A glowing visor slot. A blue pendant. The
  `characters` block in `chrono.json` averages five specified items per character; two is
  plenty and reads stronger.
- **Never name the source's artist, publisher, or art style in a prompt.** Genre labels
  ("classic JRPG cover art", "storybook anime") are fine and generic. A named illustrator
  or "in the style of <work>" is asking the model for a reproduction. `chrono.json` is
  clean here — keep it that way.

**Things not to make at all:** a recap that reproduces the source's own footage, sprites,
screenshots or music; a "cover" of its soundtrack; anything presented as if it *is* the
original rather than about it. Score everything from ACE-Step against the *mood*, never
against the original cue.

**And the craft argument, which is stronger than the legal one:** `STORIES.md` already
makes it — an original story in a genre's lineage lands harder than a retelling of a story
the audience knows the ending of. Recaps are worth making for what they teach you about
structure and pace at length. They are not the thing this box is best at.

---

## 8. Pre-flight, in order

1. Write the five-sentence spine. Cut any planned shot that doesn't serve it.
2. Choose the shape (§1) and therefore the script and the shots-per-minute budget.
3. Write the word count to the budget: **124 words per minute of finished film.**
4. Set the voice, then run `--stage narrate` **only**. Read `narration.json`. Confirm the
   runtime. This is the cheapest decision point in the whole pipeline.
5. Run §6 over every line. Delete the lines that describe pictures.
6. Read the shot list in order as a stranger. Mark every place you'd ask "who?", "why is
   that person here?", "when is this?" Each mark is a missing clause, not a missing shot.
7. Check the first 15 seconds against §5.
8. Check the biggest beat in the film has silence in it.
9. Only then render keyframes.
