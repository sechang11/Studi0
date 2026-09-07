# The Method

@title | The Method | How one computer makes films that hold together — one picture at a time, and knowing, not hoping, that they do. | book/hero_cover.jpg

@toc

@chapter | 0 | Look what one computer made | Five shots, one night market, a character who stays herself. Everything in this book is how this was done. | book/hero_01.jpg

Before a single rule, look at these pictures. They are frames from a short film called *Lantern Night*, and every one of them was made on the computer this book is about — a single desktop machine with one graphics card, no studio, no crew, no subscriptions. The film has a place, a person, a spoken line, sound, and music. The person is the same person in every shot she appears in. The place is the same place. That last sentence is the whole reason this book exists.

@row book/hero_01.jpg | book/hero_02.jpg | book/hero_03.jpg | *Lantern Night*, shots one to three. The market, empty and glowing. Terra arrives under the lanterns. She lifts one and looks into its light.

@row book/hero_04.jpg | book/hero_05.jpg | Shots four and five. A close smile, eyes closing. A single lantern in the dark, the camera drifting in.

Here is what you should notice, because it is the hard part. Between shot two and shot four the camera moves from a wide view to a close one — and it is still Terra. Her hair, her face, her red-and-gold clothes. The stalls behind her are the stalls from shot one. If you have ever asked an AI tool to make a picture twice and got two different people, you already know why this is not obvious. Video tools forget everything the moment they finish. Getting them to *remember* is the craft.

@box term | Words we will use from here on
- **A shot** is a few seconds of moving picture, made in one go.
- **A scene** is a group of shots in one place, in one kind of light.
- **A take** is one attempt at a shot. You make several and pick one, exactly like a film set.
- **The engine** is the program that turns a picture and a paragraph into a moving shot.
- **The studio** is the app this book describes — the buttons a person presses. The engine lives underneath it.
@end

### How *Lantern Night* was made, in one breath

A character called Terra already existed as a **pack** — about twenty pictures of her from every side. A place called the night market already existed as a **plate** — a clean wide picture of the stalls with nobody in them. The studio put Terra *into* the plate and made one start picture per shot. A person wrote one plain sentence for each shot about what happens, one about the camera, and one about the sound. The engine made each shot from its start picture and its sentences — except the two shots with nobody in them, where the engine kept inventing people and the studio moved its own camera slowly over the start picture instead. The studio measured every result — is that still her face? did the camera do what was asked? is there sound? — and kept only the takes that passed. Then it joined them, put one colour treatment over the whole thing, doubled the resolution, laid a music bed underneath, and checked that not one frame had gone missing.

@figure book/hero_strip.jpg | The whole film, one frame per second. Read it left to right like a comic strip: the market, the arrival, the lantern, the smile, the flame.

That is the method. The rest of this book walks through each of those steps slowly, shows you what goes wrong when you skip one, and gives you an exercise for each so that by the end you can make your own.

@box note | How to read this book
Chapter 1 explains what the machine really does — five minutes that make everything else make sense. Chapter 2 is the argument: other ways people try this, and why we do it this way. Chapters 3 to 8 are the method itself, one step per chapter, each with an exercise. Chapter 9 is about money. Chapter 10 is about time. Chapter 11 is your final project. The appendices hold the one-page rulebook and the words. If you only read one chapter, read 1. If you only keep one page, keep Appendix A.
@end

@chapter | 1 | What the machine actually does | One picture and one paragraph go in. A few seconds of moving picture come out. Nothing else is remembered. | book/plate_nightmarket_night_wide.jpg

Imagine a flipbook — the little paper kind, where you flick the pages and a drawing moves. Now imagine a very fast artist who can draw you a flipbook from two things: the **first page**, which you hand them already drawn, and a **short note** about what should happen over the next pages. The artist draws the rest. They are astonishingly good at it. But they have one strange limitation: when they finish a flipbook, they forget it completely. Hand them a new first page and a new note and they start from nothing. They do not remember the person in the last book. They do not remember the room. They do not remember what you told them yesterday.

That artist is the engine. Everything in this book follows from that one limitation.

@wrap right | book/hero_anchor_03.jpg | A first page, handed to the artist. This is the start picture for shot three of *Lantern Night*: Terra, already placed at the stall, already in lantern light. The engine will draw the next five seconds from here.

So the craft is in exactly two places. **Getting the first page right** — because the engine cannot invent a face it has never seen and get it the same twice; it can only keep drawing the face you hand it. And **writing the note so there is nothing left to guess** — who moves and how, where the camera is and what it does, what the scene sounds like. If the note does not say the camera stays still, the artist will move it. If the note does not mention sound, the flipbook is silent. If the note describes a face that is *also* in the picture, the artist now has two faces to please and draws a third.

@box why | Why "one picture and one paragraph" is the right way to think
People new to this imagine the tool as a director you brief once. It is not. It is a flipbook artist you brief per shot, with no memory. Once you hold that picture in your head, every rule in this book stops being a rule and becomes obvious: of course the people have to be *in* the first page; of course you cut between shots instead of asking one shot to do four things; of course you write down the sound.
@end

### Two engines, and when each is used

The studio has two of these artists, and it chooses between them for you most of the time. The main one is called **LTX-2.5**. It can draw up to thirty seconds in one go, it makes the sound along with the picture — footsteps, wind, a voice — and if a person on screen speaks, their mouth moves with the words. Nearly every shot in this book was made by it.

The second is called **H3**, and it is used for one special job: when you have *two* exact pictures — how the shot should start and how it should end — and want the movement in between. A person crouching down. Someone turning to look. H3 is very good at that kind of movement, the kind that stays in one place. It is not good at walking: given a start and an end picture of someone crossing a room, it ignores the pictures and draws its own walk. That was tested twice, and it is why the studio only hands H3 the in-place movements.

@box term | Words to know
- **Engine** — the flipbook artist. LTX-2.5 for almost everything; H3 for movement between two exact pictures.
- **Start frame** (also called the **anchor**) — the first page you hand the artist. The most important picture in the whole method.
- **Prompt** — the note. In this studio you never write it as one blob; you fill in a few boxes and the studio writes the note for you, in the wording the engine listens to.
- **Render** — the artist drawing. "Rendering the shot" means the engine is working. Count a few minutes.
@end

@chapter | 2 | Other ways, and why not | Five ways people try to make the same person appear twice. Four of them were measured here. One of them is this book. | book/ref2va_photoreal.jpg

There are, broadly, five ways to make a film where the people and places stay the same. We tried four of them on this machine and measured what happened. This chapter is that argument, with the evidence, because a method you follow without knowing why is a superstition, and superstitions break the first time something changes.

### Way one: describe everything, every time

The obvious first idea. Write a long, careful description of your character — "a young woman with long teal hair, green eyes, a red and gold dress, a jewelled headpiece" — and paste it into every shot. The engine is good at drawing *a* woman like that. It is not good at drawing *the same* woman twice, because a description is a category and a face is a particular. Look at the first row of pictures below: three shots written from words alone, three different women in the same clothes.

@row book/identity_prose_1.jpg | book/identity_prose_2.jpg | book/identity_prose_3.jpg | The same character described in words alone, in three shots: three strangers wearing her clothes.
@row book/identity_ref_1.jpg | book/identity_ref_2.jpg | book/identity_ref_3.jpg | The same three shots with her portrait handed to the engine as the start picture: one person. Nothing about the words changed.

There is a second problem with describing everything, and it is sneakier. If the start picture *already* shows her face, and the words *also* describe her face, the engine has two instructions that do not quite agree and it resolves them by drawing someone in between. This is why the first rule of the method is **never describe in words what a picture is already showing.** The picture carries the person. The words carry what happens.

### Way two: chain the shots

The second idea is clever and almost works. Take the last frame of shot one and use it as the first page of shot two. The person carries over! And they do — for one shot. Then the small changes the engine makes each time pile up: the face drifts a little, the room drifts a little, and by shot four you are somewhere else with someone else. We measured this in the early days of the studio and called it *the chaining era*. The method keeps one small piece of it: when a shot should continue exactly from the previous one — a push-in that ends where a close-up begins — the studio can start from the last frame. But it never chains more than once, and it never chains a face that has already started to slip.

### Way three: teach the engine everyone and everything

The third idea comes from image tools: *teach* the engine a face by training a small add-on on many pictures of it — the technical name is a **LoRA**, and this book calls it a **trained face**. It works, sometimes spectacularly, and the studio uses it — Chapter 3 shows you how. But three things stop it being the whole answer. It is expensive to check: a trained face that scores brilliantly on one render and badly on the next is a lottery ticket, so the studio only keeps one after three separate renders agree, and only two of the eight it trained passed that test. It does not stack: teach the engine a face *and* a costume *and* a crown and the third one breaks the picture. And for places it is exactly wrong: a trained "classroom" gives you *a* classroom each time, never *the* classroom — the desks move. A plain photograph of the room, handed to the engine as the start picture, gives you the room.

@row book/ladder_identity_off.jpg | book/ladder_identity_on.jpg | A trained face at work, same seed and same words: on the left the engine's own idea of "a woman in a market"; on the right, with her trained face switched on. This is the kind of thing a trained face buys — when it passes its test.

### Way four: hand the engine reference pictures

The fourth idea is what the best commercial tools do, and it is what the most impressive AI films you have seen are made with. You upload a picture of each character and a picture of the place, give each one a tag — *Picture 1*, *Picture 2* — and write "Picture 1 stands in Picture 2 and looks up." The engine reads the pictures as *who* and *where*, and the words as *what*. It is elegant, and on the paid engines it works.

Our machine has an engine with this very feature — the H3 engine has a reference mode called *ref2va* — and we tested it exactly that way: Terra's portrait as Picture 1, the plate as Picture 2, no start picture at all. Three renders, a drawn character and a photographic one. Every time the engine obeyed the *words* perfectly and ignored the *pictures*: a coherent shot of a woman looking up, in a market — and not Terra, and not our market. The reference route exists here and, as it is wired today, does not carry a face or a place. That may change; Chapter 10 explains how we keep checking. For now it is a fact, not a hope.

@row book/ref2va_terra.jpg | book/ref2va_photoreal.jpg | The reference route, tested. Left: Terra's portrait and the shrine plate handed in as Picture 1 and Picture 2 — a generic shrine, no Terra. Right: a photographic character and a café — the framing and the head-turn exactly as asked, and the wrong man in the wrong room. The words were obeyed; the pictures were not.

### Way five: this book

Put the person *into* the place in a still picture first — one composed start frame per shot, made from the character's pack and the place's plate — and only then hand it to the engine with words that describe action, camera and sound and nothing else. Keep each shot to one beat where a face matters, and cut between shots afterwards, the way every film ever made was cut. Measure every take. Keep what passes.

@box why | Why this is the one we chose
Because it is the only one of the five that we can **measure passing** on this machine. The composed start frame holds the face the engine is handed (the studio scores it: 0.68, 0.67 and 0.76 out of 1 at the start of Terra's three shots in *Lantern Night*, all "same person"). Cutting at assembly means no shot has to carry a face through a change of framing, which is where faces are lost. And it costs nothing per attempt, so you can try again — with different *words* — as often as you like. Describing everything fails on faces. Chaining drifts. Trained faces are a bonus for two characters in eight, not a foundation. The reference route is not there yet. This is what is left, and it works.
@end

### What this gets you

A film whose characters look like themselves in every shot and whose rooms stay put. A way of working that a person with no knowledge of AI can follow, because every decision is a box to fill in and every result comes back with a plain-language report card. And numbers instead of luck: you will know *why* a take was kept, and when one is wrong, the studio tells you which of three things to do about it.

@chapter | 3 | The library: a character and a place | Nothing about a person or a room is ever described to the engine. It is shown. So first, we make the things to show. | book/pack_pres_wide.jpg

Before any shot, the studio needs two kinds of thing in its library: **characters**, each as a pack of pictures, and **places**, each as a plate. Think of the pack as a passport with twenty photographs instead of one, and the plate as the empty stage before the actors walk on.

### A character is a pack

Go to **Characters → new character** and build one in the foundry. You describe them once — the studio turns your description into the wording the engine wants — and it generates the pack: a portrait, a full-body view, a turnaround (front, three-quarter, side, back), the face from three angles, six expressions, and a small "presentation set" of a hero shot, a low angle and a wide. About twenty pictures of the same person, all from one seed so they agree with one another.

@row book/pack_base_portrait.jpg | book/pack_turn_front.jpg | book/pack_turn_side.jpg | book/pack_turn_back.jpg | Terra's pack, four of twenty: portrait, front, side, back. The engine will be handed these — never a description of them.

@row book/pack_expr_joy.jpg | book/pack_expr_sorrow.jpg | book/pack_expr_anger.jpg | Three of her six expressions. A pack with expressions lets the studio start a shot from the right feeling instead of hoping the engine finds it.

The roster shows how complete a pack is with a level. **Level 1 means complete and ready to cast** — that is the floor, and it is all a character needs. Level 0 means views are still missing; finish it before you use them. Level 2 means the pack *also* has a trained face (below) — a bonus most packs never get and none of them requires.

@box why | Why twenty pictures and not one
Because the engine will need to start shots from many angles and moods, and it can only keep drawing a face it has been *shown* from that angle. One portrait gets you one framing. The turnaround gets you the back of her head in the walking-away shot. The expressions get you the smile in shot four without asking the engine to invent it. The pack is the whole set of first pages you will ever hand the artist.
@end

### A place is a plate

Go to **Places** and make one: a clean, wide picture of the location with nobody in it, in a particular light. Then make the same place in its other lights — dawn, day, dusk, night — because light is part of where you are. The studio also makes a *detail* and a *reverse* angle of each, so a scene can cut around the room without leaving it.

@row book/plate_nightmarket_night_wide.jpg | book/plate_nightmarket_dawn_wide.jpg | The night market at night and at dawn. Same stalls, same lanterns, a different film. Each is a plate: the stage before the actors.

**The plate is the place.** When Terra appears in the market in shots two, three and four, she is standing in *this* picture. The stalls do not move between shots because they are not being re-imagined — they are being re-used.

### A trained face, for some characters

For drawn characters the studio can go one step further and *teach* the engine a face from the pack itself. Press the training button on the roster and about a quarter of an hour later the studio has trained a small add-on, rendered a close-up of the character through it, rendered the same close-up the ordinary way, scored both against the pack's portrait — and done that three times on three different seeds. It keeps the trained face only if it wins by more than half of how much its own score wandered across those three renders. That wandering is called the **spread**, and it is the whole reason for the rule: a face that scores 0.74 once and 0.51 the next time is not a face you can promise anyone.

@row book/ladder_costume_off.jpg | book/ladder_costume_040.jpg | book/ladder_costume_100.jpg | Not all trained things behave alike. A trained *costume* at strength 0, 0.4 and 1.0: nothing, nothing, everything — a switch, not a dial. A trained *face* fades in gradually. The studio measured both before writing this caption.

Two of the eight characters we trained passed. On the roster they show a green **trained face**, and from then on every shot of them is made through it — you do not do anything. Characters whose training was tried and lost show *face training tried*, so nobody spends the quarter-hour again on the same result.

@box note | Photographic characters
Drawn characters get trained faces from the roster. Photographic ("photoreal") characters do not — yet. It is not that their faces cannot be trained; they can, and have been, on a model called RealVisXL. It is that the engine which draws photoreal start frames here is a different one, called Qwen, and a face trained for RealVisXL cannot be plugged into Qwen. Until the studio has a photoreal route that can use it, photoreal characters rely on the pack alone — which holds *the same actor*, if not the same photograph. Appendix D keeps the honest list of things like this.
@end

@box try | Exercise 3 — build your library
1. Make one character in the foundry. Wait until the roster says **level 1**. Open the pack and look at all twenty pictures: is the back of the head the same person as the front? If a view is drawn out of proportion, the roster will say so — fix it before you go on.
2. Make one place with two plates in two lights. Look at them side by side: could you tell someone which stall is where in both?
3. If your character is drawn, press train. Read the result the roster reports — the two scores and the spread — and write one sentence about whether the face was kept and why.
@end

@chapter | 4 | Scenes and shots | One place, one light, one thing happening at a time. The seven boxes you fill in for every shot. | book/hero_anchor_02.jpg

Open **Film editor** and start a film. Before shots, make **scenes**. A scene is one place, in one light, with the characters who are in it. *Lantern Night* has one scene: the night market, at night, Terra present. A longer film has many, and the rule holds for each: change the place or the light, and it is a new scene.

@box why | Why one light per scene
Because the engine draws whatever light the start picture has, and the start picture comes from the plate. If your scene wanders from dusk into night, the studio would have to hand the engine plates from two different lights and every cut would jump. One plate per scene, one light per plate, and the cuts are invisible.
@end

### One beat per shot

The most important habit in this chapter: **a shot does one thing.** Terra looks up at the lanterns — that is a shot. Terra lifts a lantern and speaks — that is a shot. She smiles — a shot. It is tempting to write "she looks up, lifts a lantern, says a line, smiles and walks off" as one ten-second shot, and the engine will try. But every time the framing changes *inside* a shot — wide to close, say — the engine re-draws the face from scratch, and it does not come back the same. We measured this: an internal cut holds the face only when the face is already in the start picture and stays there. So faces get one beat per shot, and the cuts between beats happen afterwards, in the editor, the way films are actually made.

@wrap left | book/shrine_anchor_060.jpg | A one-beat shot begins here: Terra at the foot of the shrine steps, from an earlier film. The beat is "she raises her eyes to the gate." Nothing else.

There is a length to plan for too. The engine can draw up to thirty seconds in one go — but a face is only held for so long before it wanders. Across 142 takes the studio measured the face clock by what the person is *doing*: a person standing still holds for about **4.3 seconds**, a person walking for about **4.0**, and a person crouching cannot be followed at all (both crouch takes lost the face within a second). In the studio's shorthand: still 4.3 s, walk 4.0 s, crouch not followable. So a still or walking beat of four to five seconds is the sweet spot, and anything that must run longer is two shots.

### The seven boxes

Every shot is filled in from the same seven boxes, in this order. The editor's fields are these boxes.

| box | what you write | *Lantern Night*, shot three |
|---|---|---|
| **1 · Start frame** | Where the first picture comes from. Usually the studio composes it for you from the plate and the pack. | Terra at the stall, composed by the studio |
| **2 · Who and what** | The character's name, and one action. **One mover per beat.** | TERRA — lifts a paper lantern in both hands and turns it slowly |
| **3 · Framing and camera** | One framing (wide, medium, close) and one camera move (static, slow push in, handheld...). Give the camera a job or the engine gives it one. | medium · static |
| **4 · Beats** | How many things happen. One, if a face is in it. | one |
| **5 · Sound** | What it sounds like — name the sources. A spoken line, if any. | paper rustling, the market softer, *no music* · "I remember this place." |
| **6 · Look** | The film's style and colour, set once for the whole film, not per shot. | anime, filmic |
| **7 · Check** | Read the take before you keep it (Chapter 6). | identity 0.67 → 0.68, same person; place held 0.94 |

Two details in box 2 are worth their own sentence. **One mover per beat**: a whole person walking is safe; a person standing still while an arm swings fast comes out with two arms — the engine draws the fast limb twice. And **never describe a garment the picture already shows**; the start frame carries the dress.

### Length: what the engine can hold

Longer shots cost resolution, and the trade is a table the studio enforces, not a slider:

| resolution | longest shot |
|---|---|
| 720p | 30 s |
| 1.2 MP (about 1472×832) | 20 s |
| ~1080p (1.5 MP) | 12 s |
| full (2.0 MP, 1920×1088) | 8 s |

Past these the engine's process is simply killed. The editor shortens or steps down for you and says so. Notice what is *not* in the table: how long each moment lasts inside a shot. We tested writing "0–2 s ... 2–4 s ..." into the words the way some guides suggest, on two seeds and four ways, and the engine ignored the numbers every time — it paced the beats its own way. What *did* work was the word **cut**: write it, and the engine makes a hard cut; leave it out, and it dissolves. Pacing, then, is decided when you cut shots together, not inside one.

@box try | Exercise 4 — plan a scene
Write a three-shot scene on paper before touching the editor: one place, one light, one character. For each shot fill the seven boxes in three lines: *who does what* · *framing and move* · *sound*. Check each shot against three questions: Does exactly one thing happen? Does the framing agree with the action (a close-up cannot hold someone who walks away)? Is the sound written? Then build the scene in the editor and compare your three lines with what the studio wrote in the boxes.
@end

@chapter | 5 | The start frame | The first page you hand the artist. Everything the engine will hold, it holds from here. | book/hero_anchor_04.jpg

When you make a shot, the studio composes its start frame before the engine sees anything: it takes the scene's plate, puts the character from their pack into it at the size and position the framing asks for — wide, medium, or close — in the plate's light, and checks the result. That picture is the shot's **anchor**. For a scene of five shots, five anchors, all from the same plate and the same pack, which is why they agree with one another.

@row book/hero_anchor_02.jpg | book/hero_anchor_03.jpg | book/hero_anchor_04.jpg | *Lantern Night*'s three composed start frames: Terra wide, medium, and close, all placed into the same night-market plate. The engine never saw a description of her; it saw these.

After composing, the studio **reads the words against the picture**. It looks at the anchor with a vision model and lists what the words mention that the picture does not contain. "Not in the anchor: crowd" is a warning that the shot may drift toward inventing one. When we made *Lantern Night* that warning fired on the empty establishing shot, and the word came out of the sentence before the shot was rendered.

### What the start frame fixes

Two things the start frame decides that you cannot argue with afterwards. **Where the shot begins.** In an earlier film we wrote "Terra walks in from the left and stops at the steps" — and the anchor already stood her at the steps. She never walked in; there was nowhere to walk from. The action changed to "stands at the steps and raises her eyes," which is what the picture allowed. **Who is in it.** A face not in the start frame is a face the engine invents; a face in it is a face the engine keeps.

@wrap right | book/sharpen_control.jpg | The start frame of a shot, sharpened through the studio's own upscaler. It looks better. The take made from it scored worse — three shots out of three.

And one thing it does *not* need: **detail**. We tried improving a shot by sharpening its start frame first — more texture, crisper edges — and rendered the same shot from both frames at the same seed, three times on three shots. Every time, the sharpened frame produced a face that scored *lower* (−0.038, −0.070, −0.029). The engine reads synthesised detail as noise. What a *better* start frame would change is composition and likeness, not sharpness — which matters for Chapter 9.

@box try | Exercise 5 — read a start frame
Open a shot in the editor and look at its anchor before you make it. Answer three questions: Is the character in it? Is the framing the one you asked for? Is there anything in your action sentence that the picture does not contain? If the answer to the last is yes, change the sentence, not the picture.
@end

@chapter | 6 | Make it, then read it | Press the button. Then read what came back like a referee, not a fan. | book/hero_03.jpg

Fill the boxes, press **Make this shot**. The studio composes the start frame, writes the engine's paragraph from your boxes, renders, and then — before it shows you anything — measures the result. Count three to five minutes a shot. **Make every missing shot, then assemble** does the whole film in order while you do something else.

Each render is a **take**, and takes are never overwritten. A shot collects them; you **pick** one. Drafts are cheap. The studio will even retry once on its own if the first take has a fault.

### The take's report card

Under every take the studio writes what it measured, in plain words:

- **identity** — how much the face at the start and at the end of the take is your character's, scored against the portrait in their pack. *Same person* at both ends is what you want. *Uncertain* usually means they turned to profile. *A different face* is a fault.
- **QC** — anything that went wrong: a limb doubled, the audio silent, the scene drifted, people appeared in an empty shot, the person ends up pressed against the frame edge.
- **camera** — what the camera actually did against what you asked for. "Push in 46%" under a shot that asked for a *slow* push-in is the studio telling you it overshot.
- **the strip** — one frame per second of the take. Look at it. The numbers say where to look; the strip is what you are judging.

@figure book/hero_take_strip_02.jpg | The strip for *Lantern Night* shot two: Terra under the lanterns, one frame a second. Read the face across it — does it stay hers? Read the background — does it stay put?

### The one rule for picking

**A take is picked if nothing counts against it.** The studio applies exactly this rule itself: when a take has a fault it renders once more on a new seed, ranks the two by how many faults they have, then by how truthful the camera was, then by how much of the scene drifted — and picks the winner only if its faults are zero. Notes never block a pick (the camera did as asked; the sound was borrowed from a sibling take; the person ends up closer than they began). Faults always do. When nothing is pickable the studio says why, and leaves the takes for you.

@box warn | Never pick a take with a fault the QC named
However good it looks. The fault is the thing everyone will see. If the face is wrong, the note under the take now tells you which of three things is true: **this character has no trained face and could have one** (Chapter 3); **this character's trained face was already in the render, so what missed is the shot, not the likeness** — try a closer framing, a shorter take, or another seed; or **a trained face was tried for this character and lost**, so asking again reaches the same place.
@end

### Retry by changing words, not luck

When a take is wrong, the instinct is to press Make again. Sometimes that is right — the studio does it once for you. But the measured truth is that seeds do not move a composition: four seeds of a cropped shot all stayed cropped, and one sentence asking for a farther framing fixed it. So read the report card, and change the *words* it points at. The camera overshot? Ask for "barely perceptible" instead of "slow". The background froze? Name it: "the crowd moves behind her". A garment opened mid-shot? Say it stays closed, or shorten the take.

### What *Lantern Night* got wrong the first time

The film at the front of this book did not come out of the machine in one pass, and it would be dishonest to let you think it did. Here is its first report card, shot by shot, and what changed.

@row book/hero_fault_040_a.jpg | book/hero_fault_040_b.jpg | Shot four, first take. Left: second one — Terra, a close-up, exactly as asked. Right: second four of the same take — the engine has cut to a street full of people. The words said "the crowd far away"; the picture had no crowd; the engine went and found one. The report card said *scene drift: the last frame has lost 78% of the start picture*.

@row book/hero_fault_010_a.jpg | book/hero_fault_010_b.jpg | book/hero_fault_030_a.jpg | book/hero_fault_030_b.jpg | Left pair: shot one, first take, its first and last seconds — a "static" camera that ended deep inside the stalls. Right pair: shot three, first take, seconds one and four — a stranger walks through the foreground while Terra speaks her line.

- **The market pushed in 278%.** Shot one asked for a static wide of the empty stalls; the engine dollied deep into them. Two more takes with "slow push in" written instead each grew a passer-by walking down the lane. The studio's rule for an empty shot the engine keeps filling is to move its own camera over the start picture instead — arithmetic, nothing invented — and that is what shot one became.
- **"Stands and looks up" walked at the lens.** Shot two ends with Terra much closer than she began, in both takes, whatever the words said. A whole body travelling is the one motion the engine does willingly; the report card notes it and the take was kept, because nothing in it is wrong — it is simply not what was written. The honest fix is to write the walk.
- **A stranger crossed her line.** Shot three's first take had a man walk through the foreground while she spoke. "The lane is empty, no one else in the frame" and a negative that named passers-by did not stop the second take from seating people at the stalls behind her — the engine draws the market it knows. The second take is the one kept: she is unobstructed, her face scores the same at both ends, the place held at 0.94.
- **The close-up cut away.** Six takes of shot four held her face for about a second and a half and then pulled back to the street — with a lantern named in the sentence and without, at four seconds and at three, with the engine's prompt-enhancer on and off. A face standing still is a shot this engine will not hold for long; it goes looking for the scene. The remedy the studio owns outright is arithmetic on the file: the sixth take was cut at 1.5 seconds, where the camera left her face — eyes closing, the smile — and the cut was measured like any fresh render: the same person at both ends (0.76), the place held at 0.95. One number disagreed. The caption-based drift score read 67% lost, two points over its limit, because a face with its eyes shut is captioned differently from one with them open. That was a scorer built for scenes being applied to a face; on a close-up it now counts only when the place score agrees, and the report card carries it as a note.
- **An empty street filled twice.** Shot five, a candle flame in a lantern, was first asked of the wide plate and came back with a family walking through it; then of a start frame showing one lantern in the dark, and the engine zoomed out to a market crowd anyway. It, too, became the start picture moved by the studio's camera.

Three of those failures were the studio's, not the engine's, and were fixed the same afternoon: the camera-over-the-plate fallback crashed on a variable it never set; a quiet take borrowed its soundtrack from a sibling that carried the engine's own version of Terra's spoken line; and the drift scorer faulted a close-up for closing its eyes. All three are in the report cards as they happened. Every rule in this chapter was applied to this film by the people writing it, and it took three passes and a cut.

@box try | Exercise 6 — read three takes
Make one shot three times with three different action sentences (not three seeds). For each take, write down the identity numbers, the QC line, and one sentence about the strip. Then pick — and write why, in the report card's own words. If you found yourself wanting to pick a take the QC faulted because it *looked* nice, you have found the exact habit this chapter exists to break.
@end

@chapter | 7 | Sound | The engine makes sound with the picture — but only the sound you wrote down. | book/hero_05.jpg

The LTX engine makes sound as it draws: footsteps on stone, wind, a lantern string creaking, a voice. This is one of the best things about it and one of the easiest to lose, because it only makes the sound that is *written*. When we let the studio propose five shots for the night market and forgot to give them sound, two came back with an audio track that was flat silence, measured. "A quiet room" as a description produces literal silence; "a quiet room — a clock, a fridge hum, rain on the window" produces a quiet room.

@wrap left | book/hero_04.jpg | Shot four: a close smile. Its sound line named the lantern strings overhead and the market far away; the engine's render came back silent anyway, and the studio lent it the soundtrack of shot two — the report card says so.

**Write the sound for every shot.** Name the sources. If a character speaks, put the line in the dialogue box; the engine moves their mouth with it, and the studio voices the line through the character's own voice pack so it sounds like them every time. A voice needs a mouth on screen — narration over an empty room comes back as nothing. And write *no music* when you will add the score yourself, so the engine does not improvise one.

Music comes at the finish (Chapter 8): the scene carries a music tag — "soft koto and wind chimes, a night market, gentle" — and a music engine called ACE-Step writes a bed for it, mixed quietly under the whole scene.

@box note | When a shot comes back quiet anyway
It happens; *Lantern Night*'s own close-up rendered silent, twice. The studio notices, borrows the soundtrack of a sibling take from the same scene so the cut does not go dead, and says so on the take. The sibling must not be a shot with a spoken line — the engine's own render of shot three carried its version of Terra's words, and until that rule was written it was lent to an empty market. It is a patch, not a fix — the honest fix, building the scene's ambient sound from its own description for a silent shot, is on the studio's to-do list.
@end

@box try | Exercise 7 — the sound pass
Take your three-shot scene from Exercise 4. For each shot, write a sound line naming at least two sources, and mark *no music* if you plan a score. Give one character one spoken line in one shot — and make sure their face is on screen in that shot. Make the scene. Open each take's QC and confirm none says *silent*.
@end

@chapter | 8 | The finish | Half the film happens after the shots are made. One look, a master, and a count. | book/hero_04.jpg

When every shot has a picked take, press **assemble film**. Next to the *music* switch you will find two more choices: **look** and **2× master**. Between them and the music bed, this is the half of filmmaking that turns a set of good shots into a film.

### One look, after the cuts

A film needs one colour treatment over every shot, or the cuts flicker. The studio applies the look to the *whole assembled film* after the shots are joined, so every take gets the identical treatment. Four looks are offered, in words:

- **filmic** — the default. Opens the shadows and warms the mid-tones. Measured on frames from two delivered films: about 11% more colour, 20% more brightness, and very few blown-out pixels.
- **punchy** — stronger: 17% more colour, 27% brighter. Good for daylight and drawn films; can push skin toward orange.
- **soft** — the old gentle base, barely visible.
- **none** — exactly what the engines made.

@row book/grade_none.jpg | book/grade_filmic.jpg | The same frame with no look, and with *filmic*, the default: the shadows open and the mid-tones warm. A stronger candidate was left out of the list on purpose: it added 49% colour by blowing ten times as many highlights and turning every yellow to poster paint. A look that wins by clipping has not won.

### The 2× master

Switch on **2× master** and every take is passed through an upscaler before the film is joined, so a 1920×1088 film is delivered at 3840×2176. About a minute a shot. There were two ways to do it and we measured both; the faster one, which halves the frame and lets the model draw it back at four times the size, turned out cleaner as well as six times quicker — the slower path invented texture on flat surfaces.

@row book/upscale_bicubic.jpg | book/upscale_fast.jpg | book/upscale_fine.jpg | The same detail at 1:1 three ways: a plain player zoom; the fast master; the slow master. The slow one is sharper *and* has invented a mottled texture on the wall that is not in the shot.

### The count

The finished film has exactly as many frames as its takes. The studio checks this, because it once did not: the sound of each take ran a fraction longer than its picture, and the old assembly held the last frame of every shot for three frames while the sound finished — a tiny hitch at every cut that nobody had seen and the numbers caught. Cuts now land on the frame.

@box try | Exercise 8 — finish twice
Assemble your scene with **look: none** and again with **look: filmic**. Step through both at the same moment and describe the difference in one sentence. Then assemble once with **2× master** on and compare a small detail at full zoom. Finally, check the delivered film's frame count against the sum of your takes — the studio prints it — and confirm they match.
@end

@chapter | 9 | Money | Everything in this book is free to run. Here is the one place you might spend, and the rule for it. | book/hero_02.jpg

Every render in this book cost nothing. The engines live on the computer; you can try a shot ten times for the price of the electricity. The films you may have seen that look better than *Lantern Night* were mostly made on **paid engines** — you send your pictures and words to a company's computer and pay per second of video they send back. Their engines are bigger; they were trained on more; and some of them take reference pictures the way Chapter 2 described and make it work.

@box term | What a "token" is
Paid engines charge in **tokens** — small units of work. An image costs a few; a second of video costs many. A useful rule of thumb: a frontier *picture* costs a small fraction of a frontier *second of video*. That asymmetry is the whole strategy below.
@end

### The rule, if you ever spend

The studio spends nothing by default and should keep it that way until a measurement says otherwise. If money is spent, it is spent in this order, and each step is gated by the studio's own numbers on the same shot — not by how the bought thing looks on its own.

1. **Start frames, for one scene — never video.** Our whole method starts from a picture; a better picture improves every shot made from it, and pictures are cheap. Buy a handful for one scene, render each shot from our composed frame and from the bought one at the same seed, and adopt only if the face scores higher or the QC is cleaner. The studio has a tool for exactly this comparison.
2. **By scene, never by shot.** Two engines in one room show — the grain, the colour, the way things move. The finish's single look hides some of it, not all.
3. **Never buy a likeness you can make.** A trained face beat the ordinary route on two of our eight characters; the ordinary route holds *the same actor*. A bought clip must beat our own face score on the same shot, measured by the same tool, or it is decoration.
4. **Whole-scene video from a paid engine, last** — for the one thing the local engines measurably cannot do, a fight's physics say — scored with our detectors, cut in at assembly, graded with the rest.

@box why | Why start frames and not video
Because we measured what a start frame does. Sharpening one did *not* help (Chapter 5) — the engine wants likeness and composition from its first page, not detail. Likeness and composition are exactly what a bigger image model sells, and they cost a fraction of what its video costs. And because everything downstream — the engine, the measuring, the finish — stays ours and free.
@end

@box try | Exercise 9 — the decision, on paper
Pick the one shot in your project that you like least. Write down its identity numbers and QC line. Then answer: is the problem the *words* (Chapter 6), the *start frame* (Chapter 5), or the *engine*? Only the third is a reason to spend anything, and only after the first two have been tried. Most students never reach the third.
@end

@chapter | 10 | The clock | Engines change faster than books. This one carries a date, and a rule for when to check. | book/plate_forestshrine_dawn.jpg

Everything in this book was true on the day at the top of the studio's playbook. That is not a modest disclaimer; it is a working part of the method. In the single week this chapter was written, the studio found twenty gigabytes of a reference-to-video engine on its own disk that nobody had ever connected, a video super-resolution model its finish had never used, and learned that the paid engine the best films were made on had just released a new version.

So the studio's playbook — the engineering book behind this one — opens with a **clock**: the date it was last checked, and a cadence of fourteen days. When the date is past due, the studio checks before it makes anything: new engines and weights, new features in the software underneath, models sitting on disk that nothing uses, what the paid engines now cost and can do — and anything new runs the same battery of tests this book's rules came from before it is allowed into the method. Then the date is stamped. A tool prints whether the check is due and lists the unused models, and the studio's own instructions make it the first thing done in any session that will generate.

@box why | Why fourteen days and not "when we remember"
Because "when we remember" is how the reference engine sat unnoticed. A cadence is a floor, not a schedule — anyone can check early — but it guarantees that nothing in this book is more than two weeks out of date without someone knowing it is.
@end

@box try | Exercise 10 — read the date
Open the studio's playbook and read the date at the top. Run the review tool. Read the list of unused models. Pick one and find out, in ten minutes of reading, what it is for — and write a sentence about whether the method should test it. That sentence is exactly how new capabilities enter this book.
@end

@chapter | 11 | Your final project | One scene, three to five shots, a line spoken, a finish. Everything in this book, once, by you. | book/shrine_frame_wide.jpg

You now know the method. The project is to use it once, start to finish, and hand in a film and a page.

### The brief

Make a **one-scene film of three to five shots**, with one character who is in at least three of them, one spoken line, written sound in every shot, and a finished master with a look and a music bed. Total length between twelve and twenty-five seconds. Any subject; invent your character and your place — the method wants nothing real and nothing borrowed.

### The steps, as a checklist

1. **Library.** One character at level 1; one place with the plate in the light your story needs. (Chapter 3)
2. **Scene.** One place, one light, the character present, an ambience line, a music tag. (Chapter 4)
3. **Shots.** Three to five, one beat each, the seven boxes filled, sound written, the line in one shot with the face on screen. Framing agrees with action. (Chapters 4, 7)
4. **Start frames.** Look at every anchor before making. Fix the words, not the picture. (Chapter 5)
5. **Make and read.** Make every shot. For each, read identity, QC, camera and the strip. Retry by words. Pick nothing with a named fault. (Chapter 6)
6. **Finish.** Assemble with a look, the master on, music on. Confirm the frame count. (Chapter 8)
7. **The page.** One page: for each shot, the seven boxes and the report card of the take you kept; one paragraph on what went wrong and what you changed; the clock's date.

### How it is judged

Not on beauty first. On these, in order: Is it the same person in every shot she is in? Is it the same place? Does every kept take have a clean report card? Is the sound present and the line spoken through a mouth on screen? Does the finished frame count equal the takes? Then, and only then: is it beautiful? A student who hands in a plain film with a perfect page has understood this book. A student who hands in a gorgeous film with a faulted take has not.

@quote The generation is the shoot. The edit is the movie. | a rule this studio borrowed, and measured true

@chapter | A | The rulebook on one page | Keep this open while you work. Every line has a measurement behind it. | book/shrine_anchor_070.jpg

1. **Show, don't describe.** A pack and a plate carry the person and the room; the words carry action, camera and sound only.
2. **One identity route per face.** Reference by default; a trained face only where it measured better on three renders by more than half its spread; never both at once.
3. **One scene, one place, one light.** Every start frame in a scene comes from the same plate and the same pack.
4. **One beat per face.** Cuts between faces happen at assembly.
5. **Length from the table, pacing from the edit.** 720p→30 s, 1.2 MP→20 s, 1.5 MP→12 s, 2 MP→8 s. Timecodes in the words do nothing here.
6. **The word *cut* makes the cut.** Without it, a dissolve.
7. **One mover per beat; a whole body, not a fast limb.**
8. **Give the camera a job.** Handheld float for photoreal; a locked camera reads synthetic.
9. **Write the sound.** Name the sources; a line needs a mouth; *no music* when you own the score.
10. **The start frame fixes where a shot begins.** Framing and action must agree.
11. **The negative grows.** Copy every QC fault into it in its own words.
12. **The plate is the place.** Trained things are for what cannot be photographed in advance.
13. **The finish is half the film.** One look, after the cuts; the master; the count.
14. **Nothing is kept on one render.** Read the numbers; look at the strip; pick only what has no faults.

@chapter | B | The pipeline on one page | The order the studio works in, and where each chapter fits. | book/hero_anchor_03.jpg

**Look** → **Library** (a level-1 pack; a trained-face attempt for drawn characters; a plate per light) → **Scenes** (one place, one light, ambience, music tag) → **Seven boxes per shot** (one beat where a face is) → **Start frames** (composed; read the words against the picture) → **Make** (LTX-2.5 by default; H3 for movement between two pictures; one retry) → **Read the takes** (identity, QC, camera, strip; pick iff no faults; retry by words) → **Sound** (written; the line voiced; the bed at the finish) → **Finish** (one look after the cuts; the 2× master; the frame count) → **Money**, only by the rule in Chapter 9 → **The clock**, every fourteen days.

The engineering version of this page, with each step's tool, measured reason and cost in minutes, is §96 of the studio's playbook. Its rules with their measurements are §95. This book changes when they do.

@chapter | C | Words to know | Every term in this book, in one sentence each. | book/pack_expr_joy.jpg

- **Anchor / start frame** — the first picture the engine is handed for a shot; composed by the studio from the plate and the pack.
- **Assemble** — joining the picked takes into a film, with the look, the master and the music.
- **Beat** — one thing happening. A shot with a face in it has one.
- **Cut** — where one shot ends and the next begins. Written into the words, it makes a hard cut inside a shot; otherwise cuts happen at assembly.
- **Engine** — the program that draws the moving picture. LTX-2.5 and H3 here.
- **Face clock** — how long the engine holds a face: about 4.3 s standing, 4.0 s walking, not at all crouching.
- **Identity** — the studio's score for "is this still the character", 0 to 1, against the pack portrait.
- **Level** — how complete a pack is. 1 is complete and castable; 2 also has a trained face.
- **Look** — the film's single colour treatment: filmic, punchy, soft or none.
- **Master** — the film at double resolution.
- **Negative** — the list of things the engine must not draw; it grows with every fault you meet.
- **Pack** — a character's twenty pictures.
- **Pick** — the take you keep for a shot.
- **Plate** — a place's clean wide picture in one light.
- **QC** — the plain-language list of what went wrong in a take.
- **Report card** — identity, QC, camera and the strip under a take.
- **Scene** — shots in one place in one light.
- **Seed** — the engine's random starting point. Changing it changes small things, not composition.
- **Spread** — how much a trained face's score wanders across renders; the gate it must clear.
- **Strip** — one frame per second of a take, for looking.
- **Take** — one render of a shot.
- **Trained face** — a small add-on that teaches the engine a character's face from the pack; kept only when measured better.

@chapter | D | What this studio cannot do yet | So you do not spend an evening trying. Honest as of the date on the playbook. | book/ref2va_terra.jpg

- **Carry several tagged reference pictures into one shot on the reference route.** The H3 engine's *ref2va* mode takes up to nine tagged pictures, and as wired today it carried neither a face nor a place in three measured renders. Put everyone in the start frame instead.
- **Pace beats inside one shot by the clock.** Cut at assembly.
- **Give a photoreal character a trained face from the roster.** Photoreal faces train fine on RealVisXL; the photoreal start-frame engine here is Qwen, which cannot use them. The missing piece is a photoreal render route, not a trainer.
- **Stack more than two trained things on one shot.** The third breaks the render.
- **Improve a shot by sharpening its start frame.** Three of three got worse.
- **Hold a close-up on a still face for more than about a second and a half.** Six takes of *Lantern Night*'s close-up pulled back to the street after 1.5 s, whatever the words said. Keep the beat short, give the face something to do, or cut where the camera leaves it.
- **Keep an empty street empty.** Asked for a market with nobody in it, the engine added people in six takes out of seven, and pushed the camera 278% into the seventh. For a shot with no one in it, the studio moves its own camera over the plate instead.

The full engineering account of where this studio stands against the paid tools, row by row, is the companion document *Where We Stand*.

@quote Every rule in this book was measured on one machine before it was written down. When a measurement changes, the book changes with it. | the studio's only real rule
