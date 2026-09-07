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

---
*Companion to `studio/LTX_PLAYBOOK.md` §18 (cuts re-derive faces), §56 (character LoRA),
§57 (wardrobe in the weights). Update this file when a row changes; a comparison that lives
only in a chat log is a comparison that is wrong within a month.*
