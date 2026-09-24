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
| Multi-reference conditioning (`@CHARAC1 @CHARAC2 @PLACE` as separate tagged images) | native | LTX-2.5 i2v: **1** image (start frame). flf2v and H3 first-last: **2**. **H3 ref2va: up to 9 tagged `<Picture i>` references + video/audio refs, native** (`MiniMaxH3ReferenceToVideo`; weights on disk since the collector; wired 2026-09-07 as workflow 63) | **present; carries identity and wardrobe once correctly wired (2026-09-17) and doubled the person in 2 of 4 - see §6** (the 2026-09-07 "neither identity nor place" measured the prompt alone) → §2 |
| Raw fidelity and motion realism | frontier-scale training | LTX-2.5 (22 B, open weights) for motion; **Qwen-Image / Qwen-Edit** for photoreal keyframes, **SDXL (animagine-xl-4.0)** for anime keyframes | **scale gap** → §3 |

Both video engines are local weights (`UNETLoader` / `VAELoader` / `SamplerCustomAdvanced`
in `60_minimax_h3_i2v.json`; the LTX graphs likewise). The studio spends nothing per render today.

So "they have better models" is true for the fidelity row, false for the first four, and the
multi-reference row - written as an architectural gap on 2026-09-07 - was wrong: the box has had
a native reference-to-video route since the collector pulled `minimax_h3_ref2va` "in case words
are not enough", and nobody wired it. The first measurement is in §6. Three of the rows we do not
lose on are things nobody has to pay for.

## 2. The architectural gap: references resolved inside the model

Their system uploads one full-body image per character and one establishing image of the
arena, tags them, and never describes a character in the prompt — the tags carry identity
across every shot and across the internal cuts of a 15-second generation.

We independently arrived at the same law (never describe what a reference carries; `film_routes`
forces the reference weight to 0 when a trained face is present; `caption_wear.py` captions
garments only so the face welds onto the trigger). On the LTX route we cannot *feed* N references,
because that interface takes one frame - and we have already measured the consequence; it is a
warning the compiler emits, verbatim:

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
| inside the video model, at generation | `@refs` | H3 `ref2va` (`<Picture i>` tags) - present; carries identity once correctly wired, doubled the person in 2 of 4 (§6, 2026-09-17) |
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
4. **One mover per beat; effects only at the instant of impact.** Their rules 3 and 4.
   **Measured 2026-09-24 (playbook §98.3-98.4).** One mover per beat was already ours. Effects at
   the instant of impact is *not obtainable by prompt on LTX-2.5*: two arms three seeds, the
   effect accumulates monotonically either way (clear_back 0.02 vs 0.03, difference −0.01 against a
   spread of 0.03). H3 plateaus on the same anchor and words (0.10, and ~40% less occluded at the
   end), so an effects beat belongs on H3 - or on the paid engine, which is the one place in this
   sequence where buying *video* rather than a frame is defensible.

Not worth taking: *codenames not names* exists to dodge IP filters while recreating a copyrighted
fight — we use invented characters, and our own measurement (wide framings) says leading with
the name helps. Their demo is a shot-for-shot recreation of Naruto; fine to study, not a thing
for this studio to output.

## 5. The post stage (built 2026-09-07)

`studio/_tools/post.py`, wired into assembly. Two jobs, both deterministic:

**One grade line on every shot.** Applied to the whole assembled film in its final encode — which
already re-encodes, so it costs nothing — and *after* the cuts, so every take gets the identical
treatment and nothing can drift between shots. Chosen in words in the editor, beside the music
switch, and remembered on the film:

| look | what it does | measured against no grade (10 frames, 2 films) |
|---|---|---|
| **filmic** (default) | opens the shadows, warms the mids | sat +11%, brightness +20%, blown pixels +0.03 |
| punchy | brighter and more saturated; daylight and anime | sat +17%, brightness +27%, blown +0.05 |
| soft | the old gentle base | sat +7%, brightness −1% — barely visible |
| none | exactly as the engines made it | — |

The strongest candidate by the numbers, `vibrance` (+49% saturation), is deliberately not offered:
it blew ten times the highlights of the ungraded frame and turned every yellow to poster paint on
the contact sheet. `vibrancy.py`'s own rule — a grade that wins by clipping has not won. A note in
that file records `filmic_warm` measuring *below* the old base on one earlier clip frame; on ten
frames from two delivered films it measures above it. Grades behave differently per film, which
is why the choice is per film and the default is the one that did no harm on either.

**The canvas follows the takes.** Found while building this: assembly fitted every take onto a fixed
1472×832 canvas — right when takes were rendered at that size, and a silent quarter-resolution
downgrade now that LTX takes on the 2.0 MP tier come out at 1920×1088. The canvas is now the largest
picked take (even-rounded, capped at 4K); a 1920×1088 film delivers at 1920×1088 with no AI
involved. A free win hiding under the free win.

**2x master.** RealESRGAN x4 on every frame through `spandrel` in the ComfyUI venv, delivered at 2×
the takes' size with each take's own audio re-muxed; run per take before normalisation. Two things
the first attempt forgot, both measured:

- *The card is shared.* ComfyUI keeps LTX-2.5 resident after a render — 27.8 GB of 31.4 — and every
  frame of the first finish failed with 500 MB free, silently, falling back to render size. The
  upscaler now asks ComfyUI to release its models (`/free`, honoured between prompts, never
  mid-render) and waits for the memory to actually appear before loading anything. The next render
  re-stages the model in under a minute.
- *The model is the cost.* Frames stream raw through ffmpeg pipes (a PNG per frame was the first
  minutes), and the frame is tiled with OOM-halving like ComfyUI's own node. Then the benchmark, one
  1920×1088 frame on this card:

  | path | per frame |
  |---|---|
  | fp32, tiled 768 | 4.08 s |
  | fp16, tiled 768 (what the finish ran) | 2.15 s |
  | fp16, whole frame | 1.35 s |
  | **fp16, halve the frame then x4 — which *is* 2×** | **0.35 s** |

  Six times faster for the same output size — Real-ESRGAN's own `outscale=2` path — at the cost of
  re-synthesising rather than carrying detail below the half-resolution grid. Looked at 1:1 on three
  crops of the same frame (`upscale_ab.py`, `samples/hybrid/upscale_fast_vs_fine.jpg`): **fast is at
  least as good as fine, and cleaner.** Both resolve beard, roof edge and jacket seam far past bicubic;
  the fine path additionally *invents* a mottled, painterly texture on a stone wall and softens a roof
  edge — hallucinated detail on soft generative input, the same synthesised texture the start-frame
  measurement in §6 found the video model dislikes. Fast is the default; `--fine` remains for a film
  someone wants to compare on.

If a take cannot be mastered the log says so and that film delivers at the takes' own size rather
than silently scaling a soft shot up.

**Exercised end to end** on `angles-and-mass`, 17 shots, filmic + 2× master: delivered
**3840×2176 at 24 fps, QC clean, 21 minutes wall** including every `/free` wait. Then the numbers
caught two things the eye had not, one new and one old:

- *The master dropped frames.* A single mastered take had 93 frames of the 97 the network produced;
  the mux's `-shortest` trimmed each take to whichever of its streams ended first. The video is now
  the master, the audio is padded or cut to exactly its length, and the upscaler refuses to return a
  file with fewer frames than it was given. Verified: 97 in, 97 out; and on the full film, every
  take's frame count survives master and normalise — `take == master == normalised` on all 17.
- *The old assembly held the last frame at every cut.* Auditing why the finished film was "shorter"
  than its takes: a raw LTX take's audio runs ~135 ms past its video (take 010: 4.875 s of picture,
  5.010 s of sound), and the old normaliser kept that tail, so at each cut the previous shot's last
  frame was held for about three frames while its audio finished. The film's longer duration *was*
  that hold. The finish fits audio to picture (4.875 / 4.885) and cuts now land on the frame.

The delivered film has **1977 frames, and the seventeen picked takes have 1977 frames** — thirteen of
117, three of 121, one of 93. Frame-exact end to end, through master, normalise, scene join and final
encode. (I briefly believed four were missing at the scene joins; that was my addition, not the
film's. Forcing constant frame rate on the final encode would have *added* six duplicates to fill
AAC priming gaps — the shipped path is the correct one, and the check that settles it is
`ffprobe -count_frames` on every stage, never a container duration.)

Still missing from the finish, in order of value: sound design beyond the scene music bed
(`film_audio.py` exists for one film and is not general), and a per-scene grade override for a
scene that wants to read differently from the film.

## 6. Measured results

**H3 ref2va — reference-to-video, first wiring and first measurement (2026-09-07).** (The first
attempt killed ComfyUI by loading the 20 GB model on top of resident LTX; `ref2va_test.py` now asks
for the memory back and waits before it submits.)

| render | character | framing | sampler | identity first → last | verdict |
|---|---|---|---|---|---|
| ref2va | Terra (drawn) | wide | fl2v turbo LoRA, 4 steps | 0.228 → 0.248 | a different face |
| ref2va | Terra (drawn) | wide | no LoRA, 30 steps | 0.247 → 0.250 | a different face |
| ref2va | tomas-reyl (photoreal) | medium | fl2v turbo LoRA, 4 steps | 0.225 → 0.191 | a different face |
| i2v, composited start frame | Terra | wide | LTX-2.5 | 0.65 | same person |

Each render gave the engine the character's portrait as `<Picture 1>` and the place plate as
`<Picture 2>`, the node's own tags in the prompt, and no start frame. The LoRA, the step count and
the domain are each ruled out as the cause. The two drawn renders also show a generic photoreal
shrine rather than the dawn cedar-forest plate — the place reference was not carried either. The
photoreal render is the most telling: a coherent medium shot of a man in a lamplit interior who
turns his head exactly as asked — framing and action honoured to the letter — and he is not the
referenced man, and the room is not the referenced café. The *words* were obeyed; the *pictures*
were not.

**The reference route exists on the box and, as wired today, supplies neither identity nor
place.** The collector's note from the day the weights were pulled held: it *"reinforces an
identity the prompt is already asking for; it does not supply one."* Whether it reinforces a
*described* face is untested, because the method says never to describe what a reference carries.
One wiring, three renders, `_tools/ref2va_test.py`; a wiring error would look exactly like a weak
model, and the node's docstring was followed to the letter — so this is a strong result about the
route as shipped, not a law about the weights. The multi-reference row therefore stays a gap in
practice, but it is a **route** gap, not an architectural one, and the test that would close or
confirm it is on the shelf.

**H3 ref2va — the measurement above was of the prompt alone (2026-09-17).** The wiring error this
entry warned "would look exactly like a weak model" was there. `MiniMaxH3ReferenceToVideo`'s
`ref_images` is an Autogrow input that ComfyUI reads only as flat, dotted, 0-indexed ids
(`ref_images.ref_image_0`); workflow 63 passed a nested dict, so the node received no pictures and
rendered from the words. ComfyUI's own `video_minimax_h3_r2v` template shows the right form. Fixed,
and the same test run again with only the wiring changed:

| render | character | framing | sampler | identity first → last | looked at |
|---|---|---|---|---|---|
| ref2va, wired | Terra (drawn), portrait + plate | wide | fl2v turbo LoRA, 4 steps, seed 4200 | 0.676 → 0.724 | Terra, drawn - and a second Terra behind her |
| ref2va, wired | tomas-reyl, three views | medium | fl2v turbo LoRA, 4 steps, seed 4200 | 0.536 → 0.471 | him, yellow jacket and all |
| ref2va, wired | tomas-reyl, three views | medium | seed 11 | 0.396 → 0.406 | two of him |
| ref2va, wired | tomas-reyl, three views | medium | seed 202 | 0.626 → 0.615 | him, once |

**The reference route supplies identity - face, hair, wardrobe, even the drawing style - and in 2 of
4 renders it put the person in the frame twice.** Place from a plate: one render, the motifs and not
the layout. So the multi-reference row is no longer a gap in kind; it is a route that needs a people
count in QC and more measurement before a film leans on it, and the composited start frame remains
the method's route. Detail and the queue: `studio/LTX_PLAYBOOK.md` §97.3-97.4.

**Timecoded beats — run 1** (12 s, three beats, asked cuts at 2 s and 8 s, seeds 1234 and 77):

| prompt form | seed 1234 | seed 77 |
|---|---|---|
| ordinal `Shot 1 / Shot 2 / Shot 3` (the studio today) | no spike | no spike |
| timecoded `0–2s / 2–8s: CUT to / 8–12s: CUT to` | hard cut at **8.0** | clusters at ~3.5 and ~8.4 |

Looking at one-frame-a-second strips changed what that means. The ordinal clip contains all three
beats, in order, at nearly the *same times* as the timecoded one (deck to ~2.5 s, wheel to ~7.5 s,
sky after) — it **dissolved** between them instead of cutting, and a dissolve is a plateau the spike
detector does not see. So run 1 cannot say whether the numbers moved the pacing; it can say the
timecoded prompt produced a hard cut where the ordinal produced a dissolve, and the word `CUT` is as
likely a cause as the numbers. Run 1 also had a design flaw: 8 s of 12 sits exactly on the thirds
grid, so a model dividing the clip evenly and a model reading the ask both land there.

**Run 2** — four variants, same beats, same key, asked boundaries at 3 s and 9 s (a second off the
thirds grid at both positions), a dissolve detector (a plateau of raised frame difference) alongside
the cut detector (a spike), and a one-frame-a-second strip of every clip, looked at:

| prompt form | seed 1234 | seed 77 |
|---|---|---|
| A ordinal, no CUT — the studio's `Shot 1 / Shot 2 / Shot 3` | dissolve @ 8.0 | no detectable boundary |
| B timecodes + `CUT to` | dissolve @ 8.8 | **cuts** @ 3.4–3.8, 8.2–8.9 |
| C timecodes, no CUT | dissolve @ 8.1 | dissolves @ 4.8, 5.6, 8.7 |
| D ordinal + `CUT to` | **cuts** @ 4.2, 8.5 | **cuts** @ 3.5–3.9, 5.1–5.8, 8.2 |

The strips show every variant containing the same three beats in the same order at nearly the same
times — deck until ~3–4 s, wheel until ~8–9 s, sky after — **including A, which was given no times at
all.** The model's own pacing for three beats is roughly thirds, and the timecodes did not move it:
B's boundaries on seed 77 (3.4, 8.2) are D's boundaries (3.5, 8.2) to within a tenth, and D has no
numbers in it. What the timecodes were asked for — 3 and 9 — never arrived; the second boundary sat
at 8–8.9 in all eight clips.

What *did* change is the transition. Every prompt without the word `CUT` produced dissolves or nothing
the detector could see; every prompt with it produced hard cuts, on both seeds. **On LTX-2.5 the word
makes the cut and the numbers set nothing.** The breakdown's `0–2s / 2–4s` structure is decoration on
our engine.

Two consequences. Our compiler already writes *"A hard cut transitions to …"*, so production shots
get hard cuts today — no change needed there, and it is now measured rather than assumed. And pacing
inside one generation is **not available** on this engine by prompt: a beat that must run eight of
fifteen seconds is two generations and a cut at assembly, which is what §18 said for a different
reason. D's extra cluster at 5.1–5.8 on seed 77 is a flash on the wheel, not a beat — visible in the
strip, and the reason a detector is read beside its frames.

**Does a better start frame make a better take?** — `hybrid_frame_test.py`, first measurement.
The harness renders a shot twice at one seed — from its own anchor, then from a candidate frame
swapped in as `file:` — and reports the delta on the numbers the studio trusts. Until a frontier
frame exists, `--sharpen` tests the cheapest honest version: the shot's own anchor through the 2×
master and back, the same frame with more detail.

Three photoreal shots of the same character (tomas-reyl, LTX, ~4 s), two films, seed 4242:

| shot | identity, first frame | identity, last frame | QC faults |
|---|---|---|---|
| encyclopedia-check 160 | 0.699 → 0.661 (**−0.038**) | 0.626 → 0.593 (−0.033) | 4 → 5 |
| encyclopedia-check 190 | 0.708 → 0.638 (**−0.070**) | 0.624 → 0.615 (−0.009) | 4 → 4 |
| builder-test 310 | 0.672 → 0.643 (**−0.029**) | 0.650 → 0.654 (+0.004) | 3 → 2 |

**Worse at the first frame, three times out of three; nothing reliable after it.** The first-frame
identity is the one number the start frame controls directly, and a sharper frame lowered it every
time. Three shots and one seed, so a strong hint rather than a law — but it says the thing the hybrid
argument needs said before money moves: the video model does not reward *detail* in its start frame.
Synthesised texture from an upscaler reads to it as noise, and it re-derives the face from its own
prior either way. What a frontier frame would change is *composition and identity fidelity*, which
this stand-in cannot test; that is what `--frame` is for, and the numbers to beat are on the table.

## 7. The MiniMax H3 acceleration stack, measured (2026-09-20)

A workflow posted online stacks four things on H3 — TeaCache, SageAttention KJ, Spectrum and the
"V4 ema600" turbo LoRA — and the question was whether any of it belongs here. Each piece was put
on the same three start frames at one seed, against LTX-2.5 doing the same shot with the same
words. `studio/_tools/h3_stack_ab.py` is the harness; the clips and strips are in
`studio/samples/h3stack/`.

**What each piece turned out to be.**

| piece | verdict |
|---|---|
| **V4 ema600 turbo LoRA** | real, and now ours. `minimax_h3_turbo_v4_step600_ema_pruned_comfyui.safetensors`, 620 MB, the ComfyUI conversion of larryvrh's v4 step-600 EMA checkpoint. Its card asks for 8 steps / euler / beta / shift 12, which is a different recipe from the v1.0 4-step graph we already ran — so it got its own graphs, `64` (i2v) and `65` (first-last), rather than a silent edit of `60`/`62`. |
| **SageAttention** | real, and free. ComfyUI has `--use-sage-attention` natively and H3's attention goes through `optimized_attention`, so the KJ wrapper node is not needed. Only the Triton build (1.0.6) installs here — the 2.x CUDA kernels want nvcc, which this box does not have. Measured on the card: attention alone 1.6–1.8x faster at ~1.4% relative error; end to end on a clip, 50 s against 58 s on the same two warm clips, **1.15x**. |
| **Spectrum** | not installed. It forecasts denoiser outputs with Chebyshev ridge regression to skip evaluations, and its own README says it changes composition and motion "noticeably" when stacked on a turbo LoRA. Our H3 path is 4 steps; there is nothing to skip. It earns its install only if the 20-step non-turbo path turns out to be worth running, which is not measured yet. |
| **TeaCache** | rejected on merit, not for want of trying. No H3 implementation exists in the node registry, caching contradicts a 4-step schedule (nothing left to cache), and Spectrum's README warns against running a cache on the same branch. |

**The recipe that shipped.** v4 at **4 steps**, not the card's 8. On all three start frames 4
steps held the approved frame as well or better than 8 (drift 0.275 vs 0.308 on the close-up,
0.743 vs 0.793 on the market, 0.138 vs 0.156 on the lantern) for roughly half the time.
The card's reason for 8 is audio-sync stability, which this test did not measure; the 8-step
renders did come back 2-4 dB louder. `studio/film.py` now compiles H3 onto `64` (`H3_GRAPH`).

**The finding that matters more than the speed.** H3 keeps the picture it is given and LTX
re-derives it. SSIM of frame 0 against the start frame, same anchors:

| | H3 (any arm) | LTX-2.5 |
|---|---|---|
| close-up | 0.962 | 0.289 |
| empty market | 0.952 | 0.284 |
| figure with a prop | 0.953 | 0.300 |

LTX's low *drift* number (0.16–0.23) is not the compliment it looks like: drift is `hold_f0 −
hold_last`, so an engine that never held the approved frame cannot drift away from it. For a
method whose central claim is that the start frame decides the shot, this is the difference
between an engine that obeys the claim and one that treats it as a suggestion.

**The second difference: sound on a held close-up.** LTX returned -55.7 dB on the close-up
with the enhancer off and -52.7 dB with it on — silence, the same failure *Lantern Night* hit
twice. H3 returned -27.4 dB with its own ambience.

**What did NOT survive the test.** The two shots H3 was brought in for — a still close-up and an
empty market — were listed in the guide as things this studio could not do, on the evidence of
seven *Lantern Night* takes. Handed plain words that name only what the picture holds, **LTX-2.5
did both correctly**, at 1.0 MP with the prompt enhancer on or off. The production failures were
this studio writing a contradiction into its own prompt: every shot in that film carried a
`crowd` ambient from the coverage generator, and the compiler rendered it as "people move through
the background continuously" — including on the two shots marked `no_people` and on the close-up
whose own sentence said "nothing else". Proved by adding that one clause back to a prompt that
was working: same picture, same seed, H3 filled the empty lane with walking figures; without it
the lane stayed empty. `studio/film.py` now drops a people-bearing ambient on a shot that says
there are none, and warns instead of doing it silently. Both guide entries were removed.

**Where H3 is now the right call**: a shot that must keep the composed start frame exactly, and a
held close-up that needs its own sound. Everything else stays on LTX-2.5, which is faster
(36 s against 60 s a clip here) and carries dialogue.

### 7.1  The rest of the stack, after the review (2026-09-20, same day)

The review that this question triggered found the thing the stack was really a proxy for:
**ComfyUI was 221 commits behind**, and PR #16072 (merged 2026-09-06) had put kijai's block
sparse attention into *core*. We were on 0.33.1 from 13 August; the box is now on **v0.37.0**.
Every one of the 149 node classes our workflows use was checked against upstream before pulling
and all of them survived; both engines were smoke-tested after.

| acceleration | measured here | verdict |
|---|---|---|
| **BlockSparseAttention** (core, `sol-attn`, tau 1.3) | 39.2 s against 47.3 s on the close-up and 39.2 against 48.2 on the market - **1.22x** - with hold_f0 identical to three decimals, drift within 0.01, and the strips indistinguishable | **Adopted.** `workflows/67_minimax_h3_i2v_sparse.json`. The 4x figures in circulation are against stock PyTorch attention on long sequences and a weaker card; on our 107-frame 4-step clips the honest number is 1.22x on top of Sage. |
| **SageAttention** (`--use-sage-attention`) | H3 1.15x, LTX-2.5 1.10x, hold_f0 unchanged on both, strips indistinguishable | **Adopted as the default flag.** Triton build only (1.0.6); the 2.x CUDA kernels want nvcc. |
| **Spectrum** (`xmarre/ComfyUI-Spectrum-MiniMax-H3`) | works - the step log alternates 7.1 s real evaluations with 1.0 s forecasts - and cut the 20-step run from 180.6 s to 84.2 s, **2.1x**. Then it killed the ComfyUI process at step 18 of 20, leaking multiprocessing semaphores on the way out | **Installed, measured, disabled.** Kept on disk as `...H3.disabled`. |

**Why Spectrum is disabled even though it works.** It only accelerates a path we should not be
running. The 20-step non-turbo H3 render scored hold_f0 0.963 and drift 0.258 on the close-up
against the 4-step turbo's 0.961 and 0.302 - a 0.04 improvement in drift for **180.6 s against
47.3 s**, nearly four times the cost. Spectrum's 2.1x brings that to 84.2 s, which is still
slower than the turbo path it is competing with. A tool that halves the price of the wrong
answer is not a saving, and this one crashes a server two sessions share.

**Where the H3 clip time went today**: about 60 s on 0.33.1 with no flags, 48 s on 0.37.0 with
Sage, 39 s with sparse attention on top. Roughly **1.5x**, none of it costing a measurable
change in the picture.

---
*Companion to `studio/LTX_PLAYBOOK.md` §18 (cuts re-derive faces), §56 (character LoRA),
§57 (wardrobe in the weights). Update this file when a row changes; a comparison that lives
only in a chat log is a comparison that is wrong within a month.*
