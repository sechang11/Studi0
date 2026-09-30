# Making a sequence — the runbook

*The Alter Anime Studio breakdown's method, rebuilt on this box's weights and measured. Every
number here comes from `studio/LTX_PLAYBOOK.md` §98; this page is how to run it. Worked examples:
`ash-court` (five shots, 31 s, a fight) and `the-letter` (two shots, a quiet interior), both in
`studio/samples/fight/<film>/`.*

Their pipeline and ours are the same five boxes. Only the fourth differs.

    refs  ->  start frame  ->  a prompt of action, camera and sound  ->  engine  ->  post

| box | theirs | ours |
|---|---|---|
| refs | one full-body image per character, one arena wide | the same — `40_flux2_t2i` |
| start frame | characters composited into the place | **`75_flux2_ref3`** — two characters + the plate, chained references |
| prompt | seven blocks, timecoded beats | seven blocks; **the word *cut*, never timecodes** |
| engine | Seedance 2.0/2.5 (paid, 15 s) | LTX-2.5 (30 s at 0.9 MP); H3 for strikes |
| post | Topaz + DaVinci + CapCut | the finish: one grade, ACE-Step bed, −16 LUFS, 2× master |

---

## 0 · Before you start

    ssh k4shix@192.168.0.45
    free -g                                   # you want 25 GB+ available
    curl -s localhost:8188/queue              # ComfyUI answering, and nobody else queued

The box is shared. Another project's solver takes 11–22 GB of the 60 GB host, and when memory runs
out the kernel kills ComfyUI, not the solver. Two consequences, both already handled:

- **every stage skips what is already on disk**, so a killed run resumes by re-running the command;
- **`fight.py` restarts ComfyUI itself** on a closed socket and retries twice.

If you are about to run H3 or Flux 2 while the solver is mid-solve, wait for it. Nothing else.

## 1 · Write the shot script

One file per film: `studio/shotscripts/<film>.json`. Copy `ash-court.json` and change the words.
This is the only file you edit to tell a different story.

| field | what it is | the rule |
|---|---|---|
| `film` | the id; names the output folder | lowercase, hyphens |
| `realism` | the clause every character prompt ends with | pores, grain, available light — drop it and you get an airbrushed poster |
| `grade` | one colour line | written into every anchor, and the *real* grade happens once at the finish |
| `avoid` | the film's negative | ban what usually breaks, then add whatever broke on the last roll |
| `score_tags` | the bed, for ACE-Step | instrumental; the shots are rendered with "No music" |
| `place.id` / `place.prompt` | the plate | **nobody in it**, one wide, in the light the scene wants |
| `cast.<id>.role` | a role label | "the striker", never a name, never a description |
| `cast.<id>.prompt` | the reference picture | full length, plain mid-grey backdrop, even light, facing camera |
| `shots[].id` | sort order | `005`, `010`, `020` — leave gaps so a beat can be inserted |
| `shots[].secs` | length | see the envelope below |
| `shots[].refs` | which cast + place go into the anchor | up to three; `[place]` alone means an empty shot |
| `shots[].anchor` | how to compose the start frame | prose; `null` means "use the plate as the start frame" |
| `shots[].avoid_extra` | a per-shot negative | for an empty room, ban people — they arrive otherwise |
| `shots[].prompt` | what the engine is told | action, camera, sound. **Never who anybody is** |

**Length comes from two tables, not from taste.**

| resolution | longest shot | | motion | how long a face survives |
|---|---|---|---|---|
| 0.9 MP (1280×704) | 30 s | | still | 4.3 s |
| 1.2 MP | 20 s | | a walk | 4.0 s |
| 1.5 MP | 12 s | | a crouch | unmeasured — pin it on H3 |
| 2.0 MP | 8 s | | | |

An action beat wants **4 s**. A beat that must run longer is two shots.

**Writing the shot prompt.** Say the action, then give the camera a job, then write the sound, then
`No music`. A spoken line goes in double quotes and needs a mouth on screen. To cut inside a shot,
write *a hard cut to…* — and only when both people are already in the start frame.

## 2 · Cast and place

    python3 studio/_tools/fight.py --sequence <film> --cast

Produces `ref_<name>.png` (768×1344) per character and `ref_<place>.png` (1280×720). About 15 s
each. **Look at them.** Re-roll one without touching the others:

    python3 studio/_tools/fight.py --sequence <film> --cast --only vesper --force --seed 8801

The failure to watch for: the brief loses to realism. "A wiry woman in her late twenties" came back
gaunt and fifty. Ask for youth and build as **anatomy** — "a young face with high cheekbones and
smooth taut skin… broad deltoids, defined forearms" — and keep every realism anchor.

## 3 · Anchors — the start frames

    python3 studio/_tools/fight.py --sequence <film> --anchors

Chains the references through Flux 2 (`75_flux2_ref3`) into one 1280×720 frame per shot, ~40 s
each. A shot whose `anchor` is `null` just copies the plate.

**Check two things.** Is the framing close enough — both bodies large, low, in a medium? A fight
staged wide dissipates: measured, the camera pushed in 50% by itself and the take ended with both
fighters standing. And is it the same room in every anchor? It will be: the plate handed in as a
reference returns the same lamps and floor cracks (border-band difference 11–19 between anchors,
against 73 for an unrelated room).

## 4 · Shots

    python3 studio/_tools/fight.py --sequence <film> --shots --seeds 11 202 3003

One take per shot per seed, into `studio/samples/fight/<film>/`. Three seeds is the floor — none of
the breakdown's own shots was a first roll either.

**Which engine for which beat:**

| the beat | engine | why |
|---|---|---|
| establishing, nobody in it | LTX-2.5 (default) | give it `avoid_extra` against people |
| a strike with dust, ash, debris | **H3** — `--h3 <shot>` | LTX accumulates an effect monotonically whatever the prompt says; H3 plateaus after ~1 s and ends ~40% less occluded |
| a flurry with an internal cut | LTX-2.5 | it holds the cut when both are in the start frame |
| a held close-up with a line | LTX-2.5 | lip-synced through an on-screen mouth |
| a move between two exact frames | H3 `fl2va` (`62`) | pins hold in-place motion, and are ignored for a walk |

    python3 studio/_tools/fight.py --sequence <film> --h3 010 --seeds 11 202 3003

H3 needs every dimension a multiple of 32 (the tool crops to 1280×704) and a length of 17n+5
frames (it picks the closest under your `secs`).

## 5 · Read the takes

    python3 studio/_tools/fight.py --sequence <film> --score     # strips, camera, durations, frames
    python3 studio/_tools/fight.py --sequence <film> --sheets    # one contact board per shot

`--sheets` writes `picks/<shot>.jpg`: every take stacked, labelled with engine, seed and the camera
that was measured, with the take currently in the cut marked. This is where you pick.

**What to check, and what the numbers mean:**

| check | how | the line |
|---|---|---|
| camera | `--score` prints what it measured against what you asked | "push in 48%" on a shot you asked to be static is a fault |
| identity | score a frame against **the shot's own anchor**, never the cast reference | ≥ 0.62 same person · 0.50–0.62 uncertain · < 0.50 a different face |
| the words | Granite transcribes the take | six of six takes said the line verbatim, so a miss is a real defect |
| sound | `ffmpeg -i take.mp4 -af volumedetect` | every LTX take arrives at `max_volume 0.0 dB` — clipped |
| people | your eyes, on the board | an empty room grows people; a reference route can double a person |

**Then pick by rule, not by liking it:** fewest faults first, then the truest camera, then the
least drift — and never a take with a fault you can name, however good it looks.

## 6 · The bed

    python3 studio/_tools/fight.py --sequence <film> --music

ACE-Step, ~15 s, written as long as the film plus three seconds. The shots were all rendered with
"No music" on purpose so the edit owns the score.

## 7 · Finish

    python3 studio/_tools/fight.py --sequence <film> \
        --finish --picks 005=11,010=h3:3003,020=7,025=202,030=202 --master

`--picks` names one take per shot; prefix with `h3:` to take the H3 take. In order, the finish:

1. **conforms** the audio — H3 writes 32 kHz and LTX 48 kHz, and the concat demuxer wants them
   identical. Video is copied, so no frame can move;
2. **cuts** the takes together;
3. applies **one grade after the cuts** (`filmic`), not per shot;
4. mixes the **bed under at 0.5** and levels the whole thing to **−16 LUFS**;
5. **checks the frame count**: the film's frames must equal the sum of its takes';
6. writes the **2× master** with `--master` (2560×1408, ~0.35 s a frame).

One counting caveat: anything through the concat re-encode *decodes* to one frame more than its
packets, so the master reads +1 against the cut. Nothing is lost or duplicated in the picture —
two counters disagree about one file.

## 8 · If something breaks

| symptom | cause | what to do |
|---|---|---|
| `Connection refused` mid-run | the kernel OOM-killed ComfyUI | nothing — the tool restarts it and retries; re-run to resume |
| a stage does nothing | the output is already on disk | `--force`, or delete the file |
| H3 dies in `patchify_video` | a dimension is not a multiple of 32 | the tool crops; check any hand-made frame |
| people in an empty room | no per-shot negative | add `avoid_extra` |
| the whole sequence feels wrong though each take passed | a missing beat | watch the **cut**, not the takes — see rule 9 |

---

## The rules that survived contact

**1. Show the character, never describe them.** A description competes with the picture and you get
a second face. Identity holds across a cut: her face in shot 010 scores 0.75 against her face in
020, and 0.89 against her own start frame at the end of a four-second beat. **Score against the
start frame, never against the cast reference** — the reference is lit flat on grey and the shot is
not, so the same face reads 0.3 there and 0.75 here.

**2. Name the references by role, not appearance.** "the woman of reference one".

**3. The plate is a reference, and the room stops drifting.** 11–19 between anchors against 73 for
an unrelated room.

**4. Stage a fight close.** Wide, it dissipates. Medium, low, four seconds, one beat.

**5. Ask for youth and athleticism as bone structure**, keeping the realism anchors.

**6. One mover per beat.** Freeze the defender — it halves the artefacts and reads as dominance.

**7. The word *cut* works inside a shot if both people are in the start frame.** Two caveats: a cut
inside violent motion cannot be told from the motion by any detector, and if the frame is full of
an effect at the cut point the engine hides the cut inside it — which looks better than the cut you
asked for.

**8. Write the sound, say *no music*.** A spoken line lands: six takes, six verbatim readings. The
engine's own audio arrives clipped; the finish rescales but cannot un-clip.

**9. Watch the cut, not the takes.** Every take here passed its own reading and the sequence still
did not work: one shot ended with the guard thrown down, the next opened with the striker face
down, and nothing turned the fight around in between. Each shot was fine; the film was a continuity
error. The fix was a fifth shot. No per-take measurement will tell you a beat is missing.

## The two that did not survive

**Timecoded beats do nothing.** Measured twice. Pace at assembly.

**"One burst per strike" is not available by prompt on LTX-2.5.** Two arms, three seeds, one
sentence apart: the effect accumulated monotonically either way and never cleared in any of six
takes. The wording changed only how *much*. Use H3 for the beat, keep it short, composite the burst
in post — or buy that beat.

---

## Where money would go, if it ever does

`76_seedance25_ref.json` is Seedance 2.5 — the breakdown's own engine — through ComfyUI's API node:
up to 30 s, 1080p, up to 30 reference images, native audio, spoken lines in double quotes.
`fight.py --seedance <shot>` would hand it the same composed anchor as reference one and the
character references after it. **It is wired and switched off.** API nodes need a Comfy account
token that the front end supplies after sign-in, and this box has none, so the command fails
harmlessly until somebody signs in at `http://192.168.0.45:8188`. It charges per call.

If it is ever turned on, the rule from §96.4 still holds — **buy start frames, not video** — with
one exception this sequence found: the **strike beats**, because holding an effect to its instant
is the one thing our engines measurably cannot do. Everything else in `ash-court` is already as
good as the shots deserve, so there is nothing else here worth paying for.

## What it costs, on this card

| step | time |
|---|---|
| a character reference or a plate | 11–31 s |
| a three-reference anchor | 36–55 s |
| LTX-2.5, 4 s / 97 frames | 20–44 s |
| LTX-2.5, 10 s / 241 frames | 51–55 s |
| H3, 3.8 s / 90 frames | 45–50 s |
| the bed | ~15 s |
| the 2× master, 742 frames | ~110 s |
| **a whole five-shot sequence from nothing, three seeds a shot** | **about 50 minutes** |


## 2026-09-27: the page, the sheet, the compositor

- **The page.** Every stage above is one button on http://192.168.0.45:8777/shots, in order, with
  what it writes, what to look at before the next, the log, and the script editable in a form
  (`studio/_tools/shots_routes.py`, `studio/shots.html`). It runs the same `fight.py` with the same
  flags; nothing the page does is more than the shell does. One stage at a time, on purpose.
- **Stage 2 (new, optional): the reference sheet.** `refsheet.py` lays the cast faces, figures and
  the plate on one board for the Ingredients adapter (workflow `82`), which carries the people into
  a clip with no start frame at all. Measured on 2026-09-27 (playbook §0.2): the people carry, the
  camera angle is the model's own, and it is not yet a route - use it to see the cast move before
  a start frame exists, not to make the shot.
- **The compositor is now a measured choice.** `compositor_ab.py --film X --shot NNN` renders one
  shot's anchor with Flux 2 ref3 (`75`) and Qwen-Image-2.1 (`80`) on the same seeds and scores both
  by the studio's identity and room instruments. On ash-court 010: a tie on one face, +0.09 on the
  other for Qwen, 15 s against 42. `75` stays the default until the A/B holds on a second shot.
- **A look from one picture.** Krea 2's style reference (`78`) turns a plate, a painting or a frame
  grab into the look of a new picture - a way to "decide the look once" (§96.1) with a picture
  instead of an adjective.
- **A physics beat.** `previz_blender.py` simulates it (rigid bodies, a proxy figure, a camera arc),
  and `74` draws the real scene over its depth. The measured first run is in §0.2.


## 2026-09-29: three demo films, and what the pipeline gained making them

Three one-minute films - DEAD STOCK, HOUSE RULES, TEMPER - built on this runbook overnight; the
walkthrough is `studio/samples/docs/DEMO_FILMS_WALKTHROUGH.pdf`. What changed in the runbook:

- **Start frames: Qwen-Image-2.1 by default** (`--anchors` now means `--compositor qwen21`, two seeds,
  scored). `--compositor best` also draws Flux 2 and keeps whichever face scores higher; use it, or override
  with `--anchor-picks 090=flux2`, for inserts and true close-ups, where Flux 2 obeys shot size better.
- **Engine per shot** in the script: `"engine": "ltx" | "h3" | "both" | "previz"`. `--h3 all` renders every
  h3/both shot. On the nine `both` shots of these films the H3 take won every time.
- **The pick, measured**: `~/ComfyUI/venv/bin/python3 studio/_tools/take_rank.py --sequence FILM` after
  `--score` - each face on the last frame against its own start frame, each line through the local speech
  model, level, camera - writes `ranked.json` and `picks.txt`. Look at the boards anyway: it cannot see an
  intruding stranger, a shot size, or an effect that should have cleared.
- **A physics beat**: `"engine": "previz"` with `"previz": {"scene": ..., "seconds": ...}`, then
  `python3 studio/_tools/previz_shot.py --sequence FILM --shot NNN` - Blender, the dressed first frame,
  LTX-2.3 depth control; the takes are `pv_NNN_sSEED.mp4`, picked as `NNN=pv:SEED`.
- **Music past 45 s**: `--music` writes two ACE-Step cues (the script's `score_tags`, then `score_tags_b`)
  crossfaded over four seconds.
- **Delivery**: `--finish --master` (the upscale runs under the venv), then `film_cards.py --sequence FILM`
  for the title card, the 2x final and the annotated cut; `seedance_notation.py` for the prompts the paid
  engine would have been sent.
