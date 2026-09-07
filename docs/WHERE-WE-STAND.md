# Where we stand

*What this studio does as well as the commercial stack, where it is genuinely behind, and
what to do about each. Written 2026-09-07 after reading two paid breakdowns of a Seedance 2.0
live-action fight sequence; every row below was checked against this repo, not remembered.*

The question that prompted it: *"Are we able to build a REF system like this? Is it just that
they have better models? Can we build most of a film with our free tools and spend tokens only
where we need them? Or build our own Seedance?"*

## 1. The comparison, row by row

| capability | commercial stack (Seedance 2.0 + a frontier image model) | this studio (all local, RTX 5090) | verdict |
|---|---|---|---|
| Shot duration in one generation | 15 s | **30 s at 720p, 20 s at 1080p-ish (1.2 MP), 12 s at 1.5 MP, 8 s at 2.0 MP** — the measured `LTX_SAFE` envelope in `studio/film.py` | **ahead** |
| Native audio and lip-sync | yes | yes — LTX-2.5 joint audio, dialogue lip-synced through an on-screen mouth (measured, playbook) | **match** |
| Several shots / hard cuts inside one generation | yes | yes — LTX-2.5 multishot, measured with `_tools/multishot.py` (cut detector: frame-difference spikes above the clip's own median + k·MAD) | **match** |
| Post: upscale, grade, sound design | their Rule 10: *"post is half the film"* | per-take FILM-net interpolation to 48 fps, loudness levelling, scene music under at 0.5. **No grade, no upscale** on the film path | **free win, not yet taken** → §4 |
| Multi-reference conditioning (`@CHARAC1 @CHARAC2 @PLACE` as separate tagged images) | native | LTX-2.5 i2v: **1** image (start frame). flf2v and H3 first-last: **2** (first + last). Nothing takes N tagged identities | **architectural gap** → §2 |
| Raw fidelity and motion realism | frontier-scale training | LTX-2.5 (22 B, open weights) for motion; **Qwen-Image / Qwen-Edit** for photoreal keyframes, **SDXL (animagine-xl-4.0)** for anime keyframes | **scale gap** → §3 |

Both video engines are local weights (`UNETLoader` / `VAELoader` / `SamplerCustomAdvanced`
in `60_minimax_h3_i2v.json`; the LTX graphs likewise). The studio spends nothing per render today.

So "they have better models" is true for the last two rows and false for the first four.
Three of the four rows we do not lose on are things nobody has to pay for.

## 2. The architectural gap: references resolved inside the model

Their system uploads one full-body image per character and one establishing image of the
arena, tags them, and never describes a character in the prompt — the tags carry identity
across every shot and across the internal cuts of a 15-second generation.

We independently arrived at the same law (never describe what a reference carries; `film_routes`
forces the reference weight to 0 when a trained face is present; `caption_wear.py` captions
garments only so the face welds onto the trigger). What we cannot do is *feed* N references,
because the model interface takes one frame. And we have already measured the consequence —
it is a warning the compiler emits, verbatim:

> identity: an internal cut re-derives faces from the scene prior — the start frame's face does
> not survive it. Either compose the anchor so the character is IN the start frame (the cut then
> holds — measured), or use ONE-beat shots from identity keyframes and cut at assembly

Copy their flagship prompt (four timecoded beats, hard cuts, 15 s) onto our engine and the
character changes at each internal cut — **unless the character is composited into the start
frame, in which case the cut holds.** That nuance is ours and it is measured.

Playbook §57 states the general form:

> The commercial multi-shot models get it two ways — conditioning generation on a reference IMAGE
> rather than words, or generating the shots together in one pass so they share context … A LoRA
> is the same idea moved into the weights: stop asking a generator to draw the same object twice.

So the studio *has* a reference system. It resolves references at a different time:

| where identity is resolved | theirs | ours |
|---|---|---|
| inside the video model, at generation | `@refs` | — |
| before generation, composited into the start frame | — | anchors, plates, `compose_close` |
| inside the weights | — | character / costume LoRAs (2 of 8 anime packs survived a three-seed gate; §57's costume-LoRA + face-transplant recipe for photoreal) |
| in the edit | — | one-beat shots from identity keyframes, cut at assembly |

Our *library* half is ahead of theirs: a character pack is 19–20 images (body turnaround, face
turnaround, six expressions, presentation set, mesh) against their one neutral full-body image;
a place carries plates against their one establishing shot.

## 3. The scale gap, and the two questions it raises

**Can we build our own Seedance 2 / Nano Banana 2?** No. A frontier video model is thousands of
GPU-years and a licensed corpus at a scale that does not exist outside a large lab. This is not a
resource problem that grinds out on one card, and it is not worth exploring.

Where local training *does* compete is specialisation, not scale — which is exactly the LoRA
work: we cannot make a better general model, we can make *our* characters render better than a
general model renders them. Their `@CHARAC1` is one image re-uploaded every time; ours is in the
weights. And the other thing this repo has that the breakdowns conspicuously do not is
**measurement** — identity scoring, cut detection, angle measurement, survival curves, a
three-seed adoption gate. Their iteration advice is "re-roll and tighten the AVOID list."
Measurement does not close a fidelity gap, but it means our shots are chosen rather than lucky,
and it compounds.

**Can we build most of a film locally and spend tokens only where needed?** Yes — and the
right place to spend is not the obvious one.

**Do not buy video. Buy start frames.** Our whole video path is image-to-video: one start
frame decides composition, character, wardrobe, light and grade before any motion is generated,
and a frontier *image* costs a small fraction of a frontier *video* second. A frontier image
model with multi-image reference is also exactly how `@CHARAC1 + @CHARAC2 + @PLACE` gets
composited into one frame — the multi-reference resolved *before* generation, which is the
substitute §57 already reasoned its way to, done with a much better compositor.

The plumbing exists: a shot whose `anchor` is `file:<path>` uses that file as its start frame
(`film.keyframe_plan`, `film_routes._resolve_anchor_file`). Drop a frame in, render locally,
score it with the same identity and QC passes as any other take.

Two rules for the hybrid:

- **Spend by scene, not by shot.** Adjacent shots of the same character in the same room, one
  from a commercial engine and one from LTX, differ visibly in grain, colour response and motion
  character. Their Rule 8 (one grade line on every prompt) and Rule 10 (grade in DaVinci) exist
  partly to hide this.
- **Measure the delta before committing.** Render the same shot from our own keyframe and from
  the bought one; if identity, framing and QC do not move, the money did nothing.

## 4. What is worth taking from the breakdowns

Engine-independent ideas, in the order worth testing:

1. **Timecoded beats.** Our compiler writes *"A hard cut transitions to …"* — ordinal, untimed —
   so the model chooses the pacing. Theirs writes `0–2s / 2–4s / 4–12s / 12–15s` and spends eight
   of fifteen seconds on one beat. We cannot currently express pacing at all. Test:
   `_tools/timecode_test.py` renders the same three beats ordinal and timecoded, same seed, with
   the asked cuts deliberately uneven (2 s and 8 s of 12) so "honoured the timecodes" and
   "divided into thirds" predict different places. Judge: `multishot.cuts()`. **Result: see §6.**
2. **The AVOID list that learns.** *"Ban what usually breaks, then add whatever broke on your
   last roll."* We have QC detectors that measure failures and a negative prompt that never hears
   about them. Auto-populating a shot's negative from measured faults on its earlier takes is the
   "detection needs a consumer" rule again.
3. **Post as a stage, not an afterthought.** Their Rule 10. We have the pieces (RealESRGAN x4,
   FILM-net interpolation, loudness levelling, ACE-Step music) and no grade or upscale on the
   delivered film. **Built: see §5.**
4. **One mover per beat; effects only at the instant of impact.** Their rules 3 and 4. A different
   cut of our measured `h3-ghosts-a-fast-limb`; both testable, neither in our rulebook yet.

Not worth taking: *codenames not names* exists to dodge IP filters while recreating a copyrighted
fight — we use invented characters, and our own measurement (wide framings) says leading with
the name helps. Their demo is a shot-for-shot recreation of Naruto; fine to study, not a thing
for this studio to output.

## 5. The post stage (built 2026-09-07)

*Filled in below as the work lands.*

## 6. Measured results

*Filled in below as the tests land.*

---
*Companion to `studio/LTX_PLAYBOOK.md` §18 (cuts re-derive faces), §56 (character LoRA),
§57 (wardrobe in the weights). Update this file when a row changes; a comparison that lives
only in a chat log is a comparison that is wrong within a month.*
