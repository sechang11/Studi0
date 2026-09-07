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
work. You do not choose; the editor picks the engine from what the shot asks for.

## B · Before any shot: a character and a place

Nothing about a person or a room should ever be *described* to the engine. It should be *shown*.
That is the first rule and the one everything else depends on.

**A character is a pack.** Go to **Characters → new character** and build one in the foundry. A
finished pack has a portrait, a body turnaround, a face turnaround, six expressions and a
presentation set — about twenty pictures of the same person from every side. The roster shows how
complete a pack is and whether it can be cast. A character below level 2 will not hold together
across shots; finish the pack first.

**A place is a plate.** Go to **Places** and make one: a clean wide picture of the location with
no one in it, in the light your scene wants. That picture is the room. Every shot in that room
starts from it, so the desks are in the same place and the window is on the same wall in every
shot — something no amount of describing achieves.

**Some characters have a trained face.** On the roster you may see *trained face* in green: the
studio trained a small model on that character's own pack and measured, on three separate
renders, that it holds the likeness better than showing the engine a portrait does. Two of eight
tested did. If a character has one, shots of them are made through it automatically; you do not
do anything. If it says *face training tried*, it was measured and lost — do not ask for it again.

## C · Build the story: scenes first

Open **Film editor** and start a film. Before shots, make **scenes**. A scene is:

- **one place** (a plate),
- **one light** (morning, dusk, lamplight — pick it once),
- **one anchor**: a single picture the studio composes of your character *in* that place *in*
  that light, wearing what they wear in this scene.

Every shot in the scene starts from that anchor unless you tell it to continue from the end of the
previous shot. This is what keeps a person's face, their clothes and the room the same from shot
to shot: the shots share a starting picture, not a description.

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

**4 · Beats** — up to four things that happen in sequence inside one shot, joined by a *hard cut*
or a dissolve. Two rules the studio measured:
- The word **cut** is what makes a hard cut. Writing times like "0–2s, 2–4s" does nothing here —
  the engine paces its beats its own way regardless. If a beat must run long, make it its own shot.
- A cut *inside* a shot re-draws faces from scratch **unless the character is already in the start
  frame**. So cuts between two faces belong between shots, not inside one.

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
  For photoreal a single 4-second take typically holds the face for about four seconds; longer than
  that and the studio will tell you where it stopped being recognisable.
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
| 720p | 30 s |
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
scene anchor already holds her (B, C); the line in shot 2 through a mouth that is on screen (D5);
shot 3 continuing from shot 2's last frame so the push-in's end is the close-up's start (D1); every
sound named (D5); *no music* because the bed comes at the finish (I). Then *filmic*, 2× master,
assemble.

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

## Z · What this studio cannot do yet — so you do not spend an evening trying

- Feed several tagged reference pictures into one shot. The engine takes one start frame (two, for
  a shot pinned between a first and last frame). Put everyone in the anchor instead.
- Pace beats inside one shot by the clock. Cut at assembly.
- Train a photoreal face. The trainer's base model is the anime one; photoreal packs use the
  reference path (a photoreal trainer is being built).
- Stack more than two trained models on a shot. The third breaks the render.
- Improve a shot by sharpening its start frame. Measured three times: the face got worse each time.

*Companion documents: `docs/WHERE-WE-STAND.md` (where this studio stands against the commercial
stack and why), `studio/LTX_PLAYBOOK.md` §95 (these rules with their measurements), `/CLAUDE.md`
(the same rules as instructions to the studio's own agent).*
