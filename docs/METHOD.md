# The Method — building a story and a shot in this studio, A to Z

*This is the studio's own guide, written for someone who has never touched an AI tool. Every rule
in it was measured on this machine before it was written down; where a rule comes from a
measurement, the measurement is named so you can go and look. Read it once from A to Z, then keep
the one-page rulebook (section K) open while you work. Printable copy:
[METHOD.pdf](/samples/docs/METHOD.pdf). The engineering version is playbook §95.*

---

## A · What you are making, and what the machine actually does

You are making a film out of shots. A shot is a few seconds of moving picture with sound, made by
a video engine from **one starting picture and one paragraph of words**. That sentence is the
whole method: the engine does not see your character sheet, your location, your previous shot or
your intentions. It sees one frame and one paragraph, and it invents everything else.

So the craft is in two places only: **getting the right starting picture**, and **writing the
paragraph so the engine has nothing left to guess about** — who moves, how the camera moves,
what it sounds like. Everything in this guide is one of those two things.

Two engines live here. **LTX-2.5** is the one you will use for nearly everything: up to 30 seconds
in one go, with sound and speech, and it can hold several framings in one shot. **H3** is for a
shot pinned between two exact pictures — a character standing still while the camera does the
work. The engine is a field on the shot and it defaults to **LTX-2.5**; you reach for H3 only
when you have two exact pictures to pin a movement between. H3 honours both pins for motion
that stays in one place and ignores them for a walk — measured twice — so pin stillness, not
travel.

## B · Before any shot: a character and a place

Nothing about a person or a room should ever be *described* to the engine. It should be *shown*.
That is the first rule and the one everything else depends on.

@figure figures/fig_identity.jpg | Two people, two ways. Above: described in words alone, the
same description in three places — three different faces each time, the accessories pinned and
the face free. Below: the same three places with a reference sheet supplied — one woman, one
man. The reference is doing the work, not the adjectives.

**A character is a pack.** Go to **Characters → new character** and build one in the foundry. A
finished pack has a portrait, a body turnaround, a face turnaround, six expressions and a
presentation set — twenty pictures of the same person from every side. The roster shows how
complete a pack is and whether it can be cast. **Level 1 is the casting floor**: a complete
pack, ready to use. Level 0 means views are still missing — finish it before you cast. Level 2
means the pack *also* carries a trained face, which most packs never get and none of them
needs; it is a bonus rung, not a requirement.

@figure figures/fig_pack.jpg | A finished pack: Terra, twenty views. Portrait, a face
turnaround, a body turnaround, six expressions and a presentation set. This is what the engine
is shown instead of a sentence.

**A place is a plate.** Go to **Places** and make one: a clean wide picture of the location with
no one in it, in the light your scene wants. That picture is the room. Every shot in that room
starts from it, so the desks are in the same place and the window is on the same wall in every
shot — something no amount of describing achieves.

**Some characters have a trained face.** On the roster you may see *trained face* in green: the
studio trained a small model on that character's own pack and measured, on three separate
renders, that it holds the likeness better than showing the engine a portrait does - and by more
than half of how much its own score wandered between those renders (the *spread*), because a face
that scores well on one render and badly on the next is a lottery ticket, not a likeness. Two of
eight tested did. If a character has one, shots of them are made through it automatically; you do not
do anything. If it says *face training tried*, it was measured and lost — do not ask for it again.

The roster's trainer builds on the **anime** checkpoint, so this badge is reachable today only
for drawn packs. Photoreal packs are not short of a trainer — see section Z, which says what
is actually in the way.

## C · Build the story: scenes first

Open **Film editor** and start a film. Before shots, make **scenes**. A scene is:

- **one place** (a plate),
- **one light** (morning, dusk, lamplight — pick it once),
- **one source for every start frame**: the studio composes each shot's starting picture from
  that plate and your character's pack — the person *in* that place *in* that light, wearing what
  they wear in this scene, framed as the shot asks (wide, medium, close).

Every shot in the scene starts from a picture built from the same plate and the same pack, unless
you tell it to continue from the end of the previous shot. This is what keeps a person's face,
their clothes and the room the same from shot to shot: the shots share their starting picture's
*sources*, not a description. One consequence worth knowing early: the start frame fixes where a
shot *begins*. A character the anchor already places at the steps cannot "walk in from the left".

@figure figures/fig_plate.jpg | One plate, five shots. The shrine, the lanterns and the path
are in the same places in every shot because every shot started from the same picture — not
because any of it was described.

Write the film-level things once, in the **film** tab: the **look** (photoreal or anime), the
**grade** note, and the **negative** — a list of things that must never appear. The negative is
your insurance policy; section H tells you how it grows.

## D · Build a shot: the seven blocks

Each shot is filled in from the same seven blocks, in this order. The editor's fields map to them
exactly.

**1 · Start frame** — *anchor*. Where the picture the engine starts from comes from: the scene
anchor (normal), the last frame of the previous shot (to continue an action), a fresh one made for
this shot, or a file you supply. Whatever this frame shows, **do not describe it in words as well.**
Describing a face the frame already carries makes the engine draw a second, competing face.

**2 · Who and what** — *subject, action, motion*. Name the character by their studio name; the
editor supplies the rest. Then one action. **One mover per beat**: a person walking is safe; a
person standing still while their arm swings fast renders the arm twice. Name a garment only if no
picture is carrying it.

**3 · Framing and camera** — *framing, move*. One framing (wide, medium, close) and one camera move
(static, push in, orbit, handheld…). Give the camera a job; if you do not, the engine gives it one,
badly. For photoreal, a faint handheld float reads as real; a locked-off camera reads as synthetic.

@figure figures/fig_cameras.jpg | Give the camera a job. Each of these was asked for by name
and then measured on the render; the studio reports what the camera actually did next to what
you asked for.

**4 · Beats** — up to four things that happen in sequence inside one shot, joined by a *hard cut*
or a dissolve. Two rules the studio measured:
- The word **cut** is what makes a hard cut. Writing times like "0–2s, 2–4s" does nothing here —
  the engine paces its beats its own way regardless. If a beat must run long, make it its own shot.
- A cut *inside* a shot re-draws faces from scratch **unless the character is already in the start
  frame**. So cuts between two faces belong between shots, not inside one.

@figure figures/fig_timecode.jpg | The same shot, the same seed, the same three beats. Above,
the prompt carries timecodes and no "cut": the beats blur into each other. Below, the word
*cut* is present: t=3s is still the hull, t=4s is the wheel. Both paced their beats at the
same places — the numbers set nothing, the word set everything.

**5 · Sound** — *dialogue, sfx, ambience*. Write what it sounds like. Name the sources: "rain on a
tin roof, a kettle" — asking for "a quiet room" produces literal silence. A spoken line goes in
quotes and only works through a mouth that is on screen; narration over an empty room gives
nothing. Write *no music* when you will add the score yourself at the finish.

**6 · Look** — set once for the whole film (section C). Do not restate it per shot.

**7 · Check** — read the take before you pick it (section F).

## E · Make it

Fill in the shot, press **Make this shot**. The studio composes the start frame, writes the
paragraph from your blocks, renders, and then *measures* the result before it shows it to you. Count
five to ten minutes a shot, retries included. **Make every missing shot, then assemble** does the
whole film in order while you do something else.

Each render is a **take**. Nothing about a take is ever overwritten; a shot collects takes and you
**pick** one. Drafts are cheap; keep making them until one is right.

## F · Pick a take by reading it, not by liking it

Under every take the studio writes what it measured:

- **identity** — how much the face at the start and end of the take is the character's, scored
  against their portrait. *Same person* at both ends is what you want. *Different face* is a fault.
  How long a face survives depends on what you asked the person to **do**, not on the look.
  Measured across 142 takes: **still 4.3 s**, **a walk 4.0 s**, and a **crouch is not
  followable at all** — both crouch takes lost the face, median hold 0.56 s. Ask for longer
  than the motion can carry and the length field tells you so as you type.
- **QC** — the plain-language list of things that went wrong: a limb doubled, the camera moved when
  it was told not to, the wardrobe opened, the frame was cropped.
- **camera** — what the camera actually did against what you asked.

**Never pick a take with a fault the QC named**, however good it looks — the fault will be the
thing everyone sees. If the face is wrong, the note under it now tells you which of three things is
true: this character has no trained face and could have one; this character's trained face was
already in the render, so the fix is the shot (closer framing, a shorter take, another seed), not the
likeness; or a trained face was tried for this character and lost, so asking again reaches the same
place.

## G · Length: what the engine can hold

Longer shots cost resolution, and the trade is a table, not a slider:

| resolution | longest shot |
|---|---|
| 720p (0.9 MP) | 30 s |
| 1.2 MP | 20 s |
| ~1080p (1.5 MP) | 12 s |
| full (2.0 MP) | 8 s |

The editor enforces this and tells you when a shot has been shortened or a resolution stepped down.
Pacing — how long each moment lasts — is decided **when you cut**, at assembly, not inside a shot.

## H · When it looks wrong

The QC line is written in the same words you would use. Copy them into the film's **negative**.
"Ghosting on the moving arm" becomes *ghosting, doubled limb* in the negative, and the next take is
told not to do it. The negative should grow with every fault you meet; that is what it is for.

Three things that look like the engine's fault and are not:

- **The composition is cropped or too close.** Seeds do not fix this — four seeds stayed cropped;
  one sentence about a farther framing fixed it. Change the words, not the seed.
- **The background froze.** The engine animates only what is named. Name it: "the crowd moves
  behind her", "leaves drift".
- **The wardrobe opened mid-shot.** A start picture fixes a garment's starting state, not its
  behaviour. Name the garment closed in the action, or shorten the take.

## I · Finish: half the film

When every shot has a picked take, **assemble film**. Next to the *music* switch you will find
**look** and **2× master**.

- **look** applies one colour treatment to the *whole film, after the cuts*, so nothing drifts
  between shots. *filmic* (the default) opens the shadows and warms the mid-tones; it was measured
  on frames from two delivered films to add saturation and brightness without blowing highlights.
  *punchy* is stronger, for daylight and anime. *soft* is barely visible. *none* is the engines'
  raw output.
- **2× master** delivers at double resolution. It takes about a minute a shot.

@figure figures/fig_grades.jpg | The four looks on one real frame, through the studio's own
filters. *none* is the engine's output; *soft* is barely a change; *filmic* opens the shadows
and warms the mids; *punchy* pushes both further and will turn skin orange if you let it.
- The scene **music** bed is generated at this step and mixed under the picture; the whole film is
  then levelled to broadcast loudness.

The studio checks that the finished film has exactly as many frames as its takes. It used to hold
the last frame of every shot for a fraction of a second because the takes' sound ran past their
picture; it does not any more.

## J · A worked example — three shots, one scene

*Terra* (an anime character with a trained face) at the *forest shrine*, at dawn. One scene, one
anchor, three shots, cut at assembly.

**Scene:** place *forest-shrine*, plate *dawn_wide*, cast *terra*. Film look *anime*. Negative:
*lowres, bad anatomy, extra limbs, text, watermark, nsfw*.

**Shot 1 · the arrival** — anchor: *scene*. Subject *terra*. Action: *walks in from the left along
the stone path and stops at the foot of the shrine steps*. Framing *wide*, move *static*. Sound:
*wind in the cedars, gravel underfoot, a single bell far off; no music*. 6 s.

**Shot 2 · the look up** — anchor: *scene*. Subject *terra*. Action: *looks up at the shrine gate,
her hand resting on the rope rail*. Framing *medium*, move *slow push in*. Dialogue: *"So this is
where he left it."* Sound: *the same wind, closer; the bell again*. 5 s.

**Shot 3 · the decision** — anchor: *prev_last* (continues from shot 2's last frame). Subject
*terra*. Action: *closes her eyes for a breath, opens them, and starts up the steps*. Framing
*close*, move *handheld, a faint float*. Sound: *her breath, the wind dropping away*. 4 s.

Why it is built this way: three shots because each has her face in it and a cut between faces
belongs at assembly (D4); a wide first because a wide anchor swallows a named character unless the
start frame already holds her (B, C); the line in shot 2 through a mouth that is on screen (D5);
every sound named (D5); *no music* because the bed comes at the finish (I). Then *filmic*, 2×
master, assemble.

### What happened when it was actually run

This example was built through the editor's own routes and rendered, because a template whose
example was never run is a belief with a diagram. The **first pass** taught four things, each now
a rule above:

- Shot 1 as first written said *"walks in from the left and stops at the steps"*. She never walked
  in — the start frame already stood her at the steps. **The start frame fixes where a shot begins**
  (C). The action became *"stands at the foot of the steps and slowly raises her eyes to the gate."*
- In the last two seconds of that wide the engine added a burst of sparkles nobody asked for. The
  negative grew by their name — *magic sparkles, glowing particles, light burst* — and the retake
  was clean (H).
- Shot 3 as first written said *"starts up the steps"* in a close-up. The engine followed the action
  and abandoned the framing; the last frame was the back of her head and the identity score fell
  to 0.37 — the scorer was right, the shot was wrong. **Framing and action must agree** (D3). It
  also continued from shot 2's last frame, inheriting a face that had already drifted to profile;
  a close-up wants its own start frame (D1). The action became *"closes her eyes for a breath,
  opens them, and lifts her chin toward the gate"*, from the close frame the studio had composed.
- The studio then **picked that failed take anyway** — a defect in "make every shot", fixed the same
  hour: a take whose QC names a face fault is now left unpicked for a person to read (F).

The **corrected pass**, as delivered — 15 s, 3840×2176, every one of the takes' 363 frames:

| shot | what the studio measured |
|---|---|
| 1 · the arrival (6 s, wide, static) | camera static as asked · same person at the start (0.65) · recognisable for 4.5 s of 6 · place held 0.92 · sound present |
| 2 · the look up (5 s, medium, push in) | the push-in overshot (46 %) · same person → uncertain by the end (0.65 → 0.55, she turns to profile) · place held 0.91 · the line voiced through her voice pack |
| 3 · the decision (4 s, close-up, handheld) | camera static · same person at the start (0.66), the end unmeasured (the head left the tracked box) · place held 0.88 · her own sound rendered too quiet, so the studio carried shot 1's under it |

Shot 3's take was picked by a person on those notes — none is a fault — which is exactly the flow
section F describes. Shot 2 is the honest weak point: a *slow* push-in that lands at 46 % and a
turn to profile. The next thing to try, by the method, is the words (*"barely perceptible push
in"*) and not the seed.

![one frame a second of the finished example](/samples/docs/method_example_strip.jpg)

@figure figures/fig_example.jpg | The example as it was actually built and rendered on this
box — eight shots off one scene, every one of them picked from its takes. The three shots
described above are the spine of it; the rest are the same moves at other framings.

## K · The rulebook — one page to keep open

1. **Show, don't describe.** A pack and a plate carry the person and the room; the words carry
   action, camera and sound only.
2. **One identity route per face.** Reference by default; a trained face only where it measured
   better on three renders; never both.
3. **One scene, one place, one light, one anchor.**
4. **One beat per face.** Cuts between faces happen at assembly.
5. **Length from the table, pacing from the edit.** Timecodes in a prompt do nothing here.
6. **The word *cut* makes the cut.**
7. **One mover per beat; a whole body, not a fast limb.**
8. **Give the camera a job.** Handheld float for photoreal.
9. **Write the sound.** Name the sources; a line needs a mouth; *no music* when you own the score.
10. **The negative grows.** Copy every QC fault into it in its own words.
11. **The plate is the place.** Weights are for what cannot be photographed in advance.
12. **Finish is half the film.** One look, after the cuts; master; levelled; frame count checked.
13. **Nothing is kept on one render.** Read the numbers; look at the strip; pick, don't hope.

## L · The pipeline on one page, and the clock that keeps it honest

Everything above, as the order the studio actually works in: **look → library → scenes → seven
blocks per shot → start frames → render (LTX-2.5 by default, H3 for a pinned in-place movement)
→ read the takes → sound → finish.** The engineering version, with each step's tool, measured
reason and cost in minutes, is playbook **§96**; it is the go-to template, and it changes only when
a measurement changes it.

**When to spend money.** The studio spends nothing by default. If it ever does, the order is fixed:
start frames for one scene first (a better picture improves every local render downstream), never
mixing engines inside a scene, never buying a likeness the studio can make, and whole-scene video
from a paid engine only as a last resort — each step gated by our own identity and QC numbers on the
same beat, not by how the bought thing looks on its own (§96.4).

**The clock.** Models, nodes and paid engines change faster than a guide. The playbook's first
section is a review clock: the date the studio last checked for new weights, new ComfyUI nodes,
models sitting unused on disk and the paid engines' prices, and a fourteen-day cadence. When the
date is past due, the studio checks before it generates and stamps the date when it has. The
date at the top of `studio/LTX_PLAYBOOK.md` tells you how current this guide is.

## Z · What this studio cannot do yet — so you do not spend an evening trying

- Feed several tagged reference pictures into one shot **on the LTX route**: it takes one start
  frame (two, for a shot pinned between a first and last frame). Put everyone in the anchor. The
  H3 engine, however, has a reference-to-video mode (`ref2va`) that takes up to nine pictures you
  name in the words as *Picture 1*, *Picture 2*... - a character portrait and a place plate, for
  instance - with no start frame at all. It was wired and measured on 2026-09-07: three renders, a
  drawn character and a photoreal one, and it carried **neither the face nor the place** — the
  scores read a stranger every time where the start-frame route reads the same person. So it
  exists, and today it does not do the job. Put everyone in the anchor. See
  `docs/WHERE-WE-STAND.md` §6.
- Pace beats inside one shot by the clock. Cut at assembly.
- Give a **photoreal pack a trained face from the roster**. Not because photoreal faces cannot
  be trained — they can, and have been: `lora_train_sdxl.py` trains on RealVisXL and produced a
  real likeness on the LENGA films (playbook §56). Two other things are in the way. First, the
  roster's own trainer is wired to the anime checkpoint. Second, and the harder one: the
  photoreal *keyframe* engine here is Qwen, and **no SDXL LoRA can attach to it at all** —
  anime or photoreal alike, every key is rejected when a Qwen model loads. So a photoreal
  trained face has nowhere to be spent until there is a photoreal SDXL render route to spend
  it on. Until then photoreal packs use the reference path, which holds *the same actor*,
  not the same photograph.
@figure figures/fig_photoreal_lora.jpg | A photoreal trained face, working. The same seed and
the same two prompts at four strengths of the LENGA identity LoRA: at 0.00 the engine draws
strangers, and from 0.70 up it draws her. This is `lora_train_sdxl.py` on RealVisXL — proof
that the missing piece is a route from the roster to this trainer and a photoreal engine to
spend the result on, not the training itself.

- Stack more than two trained models on a shot. The third breaks the render.
- Improve a shot by sharpening its start frame. Measured three times: the face got worse each time.

*Companion documents: `docs/WHERE-WE-STAND.md` (where this studio stands against the commercial
stack and why), `studio/LTX_PLAYBOOK.md` §95 (these rules with their measurements), `/CLAUDE.md`
(the same rules as instructions to the studio's own agent).*
