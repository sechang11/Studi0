# Film craft → capability → model

*Six specialists audited one discipline each against the live box on 2026-07-29: story,
cinematography, editing, sound, character/continuity, colour. Every claim below was checked
against `/object_info` (821 nodes) or the filesystem.*

This is the **inverse** of [FILMMAKING.md](FILMMAKING.md). That document teaches the pipeline —
read it first, and read [craft/STORY.md](craft/STORY.md) for the narration clock and word budgets.
This one asks: *for each craft discipline, what can this box execute today, what is blocked, and
by exactly what?* It exists to decide what to build and what to buy.

---

## The one finding that matters

**Five capabilities are installed and unreachable from the kit.** `ltx-2.3-id-lora-talkvid-3k`,
`ltx-2.3-22b-ic-lora-union-control`, `sdpose_wholebody`, `depth_anything_3_mono_large` and
`moge_2_vitl_normal` are all on disk with all their nodes live — and no workflow or script
references any of them. Grepping `workflows/*.json` and `scripts/*.py` finds one mention of the
word "SDPose", inside a comment.

This is the **same failure mode** that [NEW-CAPABILITIES.md](NEW-CAPABILITIES.md) documented and
fixed for SAM 3.1 and BiRefNet, recurring within the same day. A model that is downloaded but
unwired is worth exactly nothing.

The consequence for planning: **the top-ranked action in five of six disciplines costs 0 GB.**
The bottleneck moved from acquisition to plumbing. Anyone reading the old
[AI-CONTENT-MAP.md](AI-CONTENT-MAP.md) §9 download list is being told to buy things that arrived
hours ago — those rows are corrected now.

---

## Two premises in the older docs are wrong

**1. "Shots are 4–5 seconds" is a Wan fact, not a rig fact.**

| Path | Frame quantum | Practical ceiling | Cost curve |
|---|---|---|---|
| Wan 2.2 i2v (`04`, via `film.py`) | `4n+1` @ 16 fps | 121 f = 7.6 s before drift | ~130 s/clip @720p — **linear and punishing** |
| LTX-2.3 i2v (`12`, via `cartoon.py`/`epic.py`) | `8n+1` @ 24 fps | `FRAME_CAP = 241` = **10.04 s** | 193 f costs 13.7 s vs 97 f at 13.5 s — **flat** |

On the LTX path a *long shot is nearly free* while an *extra shot costs a whole keyframe plus a
whole clip*. That inverts the usual economy: sizing shots to their content makes a film **cheaper
per minute**, not more expensive. Writing to a hard 5-second beat is writing to the wrong pipeline.

**2. `FILMMAKING.md`'s "`id` must sort alphabetically into cut order" is stale.** Nothing sorts —
all three scripts iterate `for s in film["shots"]` in JSON list order. `her-name.json` proves it
(`a01_harvest` … `01_village` … `b01_shrine`); ASCII-sorted, that film would be scrambled. The doc
is wrong in the safe direction, but it is wrong. *Left unedited here to avoid clobbering a
concurrent session — worth fixing in place when that settles.*

---

## Story & structure

**Structure is a render-order problem.** Reordering the `shots` array is free (`--stage edit`, zero
GPU). Duplicating an image is not (new `id` → new keyframe → new clip). Classify every structural
decision by that line. A payoff that reuses a framing at a different scale is cheap and reads
better than one needing a new image — same prompt, "closer", different seed.

**Setup/payoff is the only structure that survives short shots**, because it is the only one that
doesn't need continuity: two images 90 seconds apart do the job. `her-name.json`'s `_structure_note`
is the best worked example in the repo.

**Silence is a structural element, not a mood.** Narration costs `LEAD 0.30 + tail` per line —
`chrono.json` sets `tail: 1.15`, so **1.45 s of dead air before a word is spoken**. A silent shot
costs only its `seconds`. That makes silence the cheapest pacing tool on the box and the only way
to get a fast run inside a narrated film. Comedy and action timing on this rig *are* the `seconds`
field. Corollary: never plan comedy beats in a narrated film — setup/action/reaction at 2 s each
becomes 20 s and the joke dies.

Measured cutting rates: wordless ~25 shots/min, dialogue ~20, narrated **10.4**.

**Blocked, all by code and none by models:**

| Gap | Blocker |
|---|---|
| idea → `film.json` generator | Missing script. `idea.py` makes one image prompt. Every structure on this box was hand-authored, yet `TextGenerate` + `gemma_3_12B` + the `/history` read-back idiom are all present. |
| Sequence/act primitive in the schema | `parent` exists in `chrono.json` and **nothing reads it**. You cannot say "shots 12–17 are one scene". |
| Draft → critique → revise loop | `TextGenerate` has no system-prompt field and no multi-turn, and there is **no loop/iterator node in the 821-node install**. Must be orchestrated from Python. |
| Vision critique of your own footage | `TextGenerate` has optional `image` / `video` inputs and `qwen_2.5_vl_7b` is installed. **Completely unused.** A bad structure is currently discovered by watching the finished cut. |

---

## Cinematography

**Coverage is faked by scale contrast, not by matching.** No video model here has a persistent 3D
space, so you cannot cut from a wide to a matching close-up of the same room and have the room
agree. Build sequences where the CU is of a *thing* — hand, dial, water, eye — whose surroundings
are out of frame. Insert-heavy grammar isn't a style choice; it's what the constraint permits.

**Camera moves, by how reliably they land:**

| Move | Reliability |
|---|---|
| Locked-off / static | highest |
| Slow push-in / forward dolly | high — the official IC-LoRA prompt *opens* with "A slow forward dolly shot" |
| Handheld drift | high |
| Crane up / tilt | medium |
| Orbit / arc | low without control |
| Rack focus | **unverified** — `PROMPTING.md` lists it, nothing demonstrates it |
| Whip pan, dolly zoom, crash zoom | unavailable |

The pattern in every working prompt: **the camera clause comes first and names one move only.**

**Lens language lives in the still.** The video model inherits the lens from the frame it is given
— it does not re-lens. Anamorphic squeeze, 24 mm distortion, 85 mm compression and shallow DoF must
be baked into the keyframe. Asking an i2v model for shallow DoF over a deep-focus keyframe produces
nothing. Grain and halation are the exceptions, because they're texture, not geometry.

**Motivated light is the thing generated footage gets wrong, and it's fixable in the prompt:** name
the *source* in frame (bare bulb, sodium lamp, monitor glow), then the *effect*. If the source
moves, the shadows move, and the model's motion prior has something mechanical to follow. In-shot
lighting *changes* are effectively free with LTX — beacon sweeps, lightning, headlights raking. Use
light events as your motion when you don't want the camera to move.

**Screen direction and the 180° rule are your bookkeeping.** No model has any notion of either.
Write direction as geometry, not jargon: "seen from her left, she faces frame-right". "Reverse
angle" and "over the shoulder" are unreliable tokens.

Two format traps: **LTX snaps height to a multiple of 32** (ask 720, get 704 — visible in our own
1280×704 output) and **LTX is 24 fps while Wan is 16 fps**. Mixing engines in one film means one
gets retimed. Decide per film, not per shot.

**Blocked:** explicit parametric camera control. The **nodes are already installed** —
`WanCameraEmbedding` exposes `Static / Pan Up / Pan Down / Pan Left / Pan Right / Zoom In / Zoom
Out / ACW / CW` plus a `speed` float — and the template reuses your existing encoder, VAE and both
lightx2v LoRAs. Only the two Fun Camera DiTs are missing (~28 GB).

---

## Editing, transitions & continuity

**Three editors exist and they are not equivalent.** This is the most consequential finding in the
discipline.

| | `film.py` | `cartoon.py` | `epic.py` |
|---|---|---|---|
| Transition grammar | none — one global value at *every* boundary | none — `xfade=fade` hardcoded | **5-name grammar, per-shot `in:`** |
| Hard cuts possible | no | no | yes — lossless `concat -c copy` |
| Per-shot durations | **ignored** | via padding | yes, narration-derived |
| Titles | black cards | cards | **over moving footage** |

`epic.py` is the real editor. Its grammar — `cut` (0.00, default) / `soft` (0.28) / `dissolve`
(0.70) / `fade` → **`fadeblack`** (1.00, act break) / `flash` → `fadewhite` (0.50) — is the most
useful piece of story grammar in the kit, and **only `chrono.json` uses it.** The other seven films
set a flat global `transition` and therefore **dissolve every single boundary.** That is not a
capability gap; it is seven films that need re-cutting with a grammar that already works, at zero
GPU cost.

Three punctuation marks (`cut` / `dissolve` / `fadeblack`) is all a viewer needs to parse a
three-act shape out of 109 disconnected clips.

**A dissolve is also a repair tool** — it launders a look mismatch between independently generated
clips. That's why it spreads: a hard cut *exposes* the mismatch. Fix the mismatch upstream and the
cut does the work.

**First/last-frame conditioning is the headline, and it's zero-download.**
`video_wan2_2_14B_flf2v` needs **only weights already on disk** (leave the optional
`clip_vision_*` inputs unconnected — that folder is empty). Same model family as existing footage,
so a bridge clip look-matches. `templates-6-key-frames` chains five of them — a working long-take
rig, unused.

LTX FLF2V is **8× cheaper** (16.5 s vs 129 s) and comes with synced audio. Build it by cloning
`12_ltx23_i2v_audio.json`, replacing the `LTXVImgToVideoInplace` node with
`LTXVAddGuide(frame_idx=0, 0.7)` → `LTXVAddGuide(frame_idx=-1, 0.7)` → `LTXVCropGuides`. The one
gotcha: the template hardcodes `ltx-2.3-22b-distilled-fp8`, which we deliberately did **not**
download — repoint to `dev-fp8` + the distilled LoRA @ 0.5, exactly as workflows 11/12/17 do.
*That validates the 27.5 GB skip: it was a rewire, not a missing model.*

**Blocked by code, not weights:**

- **True match cuts and cut-on-action.** There is **no in-point** anywhere: `epic.py` has no `-ss`
  in segment assembly and no per-shot in/out fields. Every shot plays from frame 0. Tail trim
  exists; head trim does not. ~20 lines of script work unblocks the two highest-value techniques.
- **L/J cuts.** Audio is welded to picture — hard cuts stream-copy, soft boundaries use the *same*
  crossfade duration for audio and video. No offset parameter exists. Sound is the only element
  with genuine cross-shot continuity, so this is the cheapest large gain in perceived craft.
- **`film.py` reads only film-level `seconds`**, ignoring per-shot values, and re-encodes 16 fps Wan
  output at `-r 24` — 2-1-2-1 frame duplication, the exact judder the docs warn about, while
  `07_video_interpolate` sits unused.

---

## Sound & music

**Ambience does the most work for the least effort**, because it fixes what AI cuts fail at worst:
spatial discontinuity. Nine shots share no room. A continuous bed of room tone spanning the cut
asserts they do, and **the ear believes the room over the eye.** More true of ambience than of
music, because ambience is unpitched and never collides with an edit.

Layer priority: **ambience → score → foley → dialogue.** Dialogue is the weakest link and the
highest risk.

**Sound bridges cuts — your strongest continuity tool, and free.** *Overlap*: run the outgoing
ambience 0.3–0.6 s past the picture cut. *Pre-lap*: bring the incoming ambience up *before* the
picture cuts — the cheapest way to make a hard cut feel motivated.

**Three generators, three sample rates.** Measured on actual output:

| Source | Rate | Ch | Integrated |
|---|---|---|---|
| ACE-Step 1.5 | 48 000 | stereo | **−17.9 LUFS**, LRA 14.7 |
| Stable Audio 3 | **44 100** | stereo | ~−22 LUFS, LRA 7.5 |
| Chatterbox | **24 000** | **mono** | varies by `exaggeration` |

**Do the layering in ffmpeg, not ComfyUI.** `amix` resamples silently and correctly; ComfyUI's
`AudioMerge` has no resampler and no gain staging — its `add` clips and its `mean` halves your bed.

**Spotting:** ACE honours `duration` sample-exactly but has **no concept of a hit point.** Generate
longer than picture and trim in; for a cue that must land somewhere, butt-join two cues at the hit
with `acrossfade`. Or cut the picture to the music rather than the reverse.

**LTX in-pass audio vs. layering is not a choice — stack them.** LTX gives free physical
correlation (a footfall lands on the foot) but doesn't know what a brass ticket punch is, and you
cannot re-level it after the fact. Doctrine: **LTX audio lowest as an unstructured "reality" bed,
designed SFX above it, dialogue on top.**

**Blocked:**

| Gap | Blocker |
|---|---|
| Stem separation | Hard blocked — no node in 821, no `demucs` in the venv. An ACE-Step song is **atomic**: you cannot duck its vocal under dialogue. Demucs pins old torch, so it must live in its own venv, never ComfyUI's. |
| More than one convincing voice | `ChatterboxTTS.model_pack_name` has **exactly one option**. Current workaround is `rubberband` pitch-shift — a cartoon solution that won't survive a two-hander. **But `ChatterboxTTS` has an optional `audio_prompt: AUDIO` input for zero-shot cloning and nothing in the kit uses it.** The blocker is that `input/` holds no reference voice clips. A 10-second-per-character asset problem, not a model problem. |
| Loudness normalisation | **Not blocked — just not done.** ffmpeg 8.1.2 has `loudnorm`, `ebur128`, `alimiter`, `sidechaincompress`. Scripts use only `dynaudnorm`, a *dynamic* normaliser that fights the dynamics you just built, and `mixdown.sh` applies no loudness pass at all by default. |

---

## Character & continuity

**Identity drift is the tell.** An audience forgives soft 16 fps motion and flat grading; it does
not forgive a face that is 90% the same. Face recognition is the most over-trained visual system we
have, so a 5% shift in jaw width between shot 3 and shot 4 reads instantly as two different people.
Budget consistency effort **faces → wardrobe silhouette → props → place**, in that order, because
that is the order the eye checks.

**Pick features that survive resampling.** "Cropped white hair, black turtleneck, wire-rim glasses"
holds across shots. "A subtly asymmetric embroidered collar" will not. A model has no concept of
*the* mug, only *a* mug.

**Locking identity fights performance**, and this has no clean answer. Every mechanism that pins a
face also pins expression and gaze — push it up and you get a consistent character who cannot act.
Two working strategies: lock hard on wides where the face is small, release on the close-up where
performance matters; or train the LoRA on a *deliberately expressive* dataset so variation lives
inside the LoRA rather than being suppressed by it.

**Proven on this box:** two-image fusion at **12.0 s** (`23_qwen_edit_2511_fusion` — two separately
generated portraits composed into one photograph with both faces staying distinct), single-image
continuity edit at **8.3 s**, SAM 3.1 isolation, BiRefNet matting, pixel-locked prop compositing.

**The ID-LoRA is the most important unwired thing on the box.** All five required models verified
present. Be clear-eyed: `talkvid` means trained on *talking* video, driven by a reference identity
image plus reference audio and a structured prompt (`[VISUAL]: / [SPEECH]: / [SOUNDS]:`). So it is
identity lock for **dialogue coverage**, not for arbitrary wide shots. It slots directly into
`cartoon.py`, which already renders a per-character voice clip per line — those clips are exactly
the reference audio this graph wants.

**Blocked:** the whole **face-embedding family** — IPAdapter, PuLID, InstantID, PhotoMaker — is
absent. Nothing installed, zero matching nodes, and `clip_vision/`, `style_models/`, `photomaker/`
are all empty. That is the standard toolkit everyone else uses. On this box identity must come from
reference-image editing (2511), the LTX ID-LoRA, or a trained LoRA. Plan around it.

Also absent: `qwen-image-edit-2511-multiple-angles-lora` (~1 GB) — the cheapest remaining download,
because it manufactures the character bible everything else depends on.

---

## Colour & look

**Nothing in `scripts/` does any colour work at all.** `grep -nE "curves|colorbalance|lut3d|haldclut|vibrance|eq=" scripts/*.py scripts/*.sh`
returns **zero hits.** `FILMMAKING.md` lists grading as gap #5 and it is genuinely unimplemented.
That makes grading the **single largest cheap win in the entire audit** — pure CPU, no model, no GPU.

**A named palette is the only consistency mechanism that survives independent generation.** "Moody
blue" resolves differently every seed; `slate blue, bone white, dull ochre` is a hard constraint the
encoder can hit repeatably, because colour *nouns* ground far more tightly than colour adjectives.
Nine of the twelve clauses in `sweeps/styles.txt` carry an explicit named palette, and those are the
nine that read as a coherent look. Put it in the film JSON's `style` block — appended verbatim to
every shot — not in individual prompts. Same rule as the `characters` block: **identical wording,
never paraphrased.** Name the key direction there too (`hard low key from frame left, cool bounce
fill`), because a shot lit from frame left cut against one lit from frame right reads as two
different days.

**Bake vs. grade — the decision rule:**

| Bake into generation | Grade afterwards |
|---|---|
| The look is **pigment** — flat gouache values, riso duotone, cyanotype, woodblock keyline. No grade produces those; they change how form is *drawn*. | The look is a **transfer function** — lift/gamma/gain, split-tone, crushed blacks, grain, halation. |
| One-off images. | Sequences. Always sequences. |
| Cost: a full re-render per iteration. | Cost: ~0, no GPU, iterate 50× a minute. |

So: **generate flat and grade hard.**

**Author the look once, bake it to a CLUT, apply it everywhere.** ffmpeg can't write `.cube` but
doesn't need to — grade an identity Hald CLUT, save as PNG, then apply with one filter:

```bash
ffmpeg -f lavfi -i haldclutsrc=level=8 -vf "curves=master='0/0.03 0.25/0.20 0.75/0.82 1/0.97',colorbalance=rs=-0.06:bs=0.10:rh=0.08:bh=-0.05,vibrance=intensity=-0.15" -frames:v 1 look.png
ffmpeg -i shot.mp4 -i look.png -filter_complex "[0:v][1:v]haldclut=interp=tetrahedral" out.mp4
```

The CLUT is a **single versionable artefact** — diffable, hand-offable, and guaranteed identical
across 200 shots and across re-runs months later. Also ~40× cheaper per frame than re-evaluating the
chain. Lifting the black point to 0.03 is the main thing that stops generated footage looking
digital; negative `vibrance` pulls back the oversaturation distilled models produce.

**Sequence colour matching is NOT blocked** — I had assumed it was. **`ColorTransfer`** exists
(`image/filters`, three algorithms, `strength` 0–10) and is **batch-aware** via `source_stats`. Use
`uniform` (pool the sequence's stats, match the pool to a hero frame) — it preserves *relative*
differences between shots. `per_frame` flattens deliberate contrast and will destroy a day/night cut.
The measured alternative: `ffmpeg -vf signalstats,metadata=mode=print` reports `YAVG`/`UAVG`/`VAVG`/
`SATAVG` per frame, so you can drive `colorbalance` deltas from real numbers rather than your eye.

`deflicker=size=5:mode=am` fixes the temporal luminance crawl inside distilled video clips — a
specific fix for a specific generated-video tell.

**Two traps.** In-graph curves are **structurally dead**: `CurveEditor` outputs a `CURVE` and
*nothing in 821 nodes accepts one* except the Color Curves blueprint subgraph. Use ffmpeg. And
FLUX.2 (35.4 GB + an 18 GB text encoder) **cannot co-reside with Qwen** on 32 GB — batch by model,
never interleave shots.

**Blocked, and it is one missing LoRA:** `image_qwen_image_edit_2509_relight`,
`template_character_portrait_relighting` and `templates-product_scene_relight` are all **present and
fully wired**, and all fail on `Qwen-Image-Edit-2509-Relight.safetensors` alone. Same for
`templates-portrait_light_migration`, which needs `Qwen-Image-Edit-2509-Light-Migration` — the only
thing on this box that can move light *direction* off a reference image (`ColorTransfer` moves
colour statistics, not light). Both are small. Note the Light-Migration trigger is a **Chinese prompt
string** that must be preserved verbatim — it's trained, not decorative.

Also empty: `models/style_models/`, `models/clip_vision/`, `models/model_patches/` — so the whole
IP-Adapter / Redux / USO style-reference family is unavailable despite its nodes being installed.
Low priority: it would be a worse version of `ColorTransfer` + a CLUT.

---

## What to do, across all six disciplines

Ranked by value ÷ effort. Note that **eight of the top ten cost nothing to acquire.**

| # | Action | Cost | Discipline |
|---|---|---|---|
| 1 | **Add a grade stage to the edit** — author one Hald CLUT per film, apply with `haldclut` alongside the existing `xfade` | **0 bytes**, ~1 h, no GPU | Colour — closes the largest quality gap in the audit; a grep proves *no* script does any colour work. Bit-reproducible, and every future film inherits it |
| 2 | **Add in/out trim handles to `epic.py`** (`-ss`/`-t`, per-shot `in_point`/`out_point`) | ~20 lines | Editing — unblocks match cuts *and* cut-on-action. There is currently **no in-point anywhere** |
| 3 | **Put a named palette + named key direction in every film's `style` block** | 0 bytes, ~20 min | Colour — highest consistency-per-effort on the box; the mechanism already exists and is underused |
| 4 | **Port `epic.py`'s transition grammar into `cartoon.py` and `film.py`** | ~40 lines | Story/editing — act structure in the short films where it matters most |
| 5 | **Add audio lead/lag → real L/J cuts**; decouple `acrossfade` from `xfade` | ~15 lines | Sound — cheapest large gain in perceived craft |
| 6 | **Add a `loudnorm` finishing pass; swap `dynaudnorm` for `sidechaincompress`** | ffmpeg only | Sound — the difference between amateur and mastered. Measured material starts at −17.9 LUFS |
| 7 | **Build `24_ltx23_ic_control.json`** (control video → DA3/MoGe → `LTXVAddGuide` + IC-LoRA) | 0 GB | Cinematography — arbitrary camera control, today |
| 8 | **Build an ID-LoRA workflow** and wire `cartoon.py`'s voice clips into it | 0 GB | Character — unblocks multi-shot narrative |
| 9 | **Build `25_color_match.json`** — `LoadImageDataSetFromFolder` → `ColorTransfer` (`mkl_lab`, `source_stats=uniform`) | 0 GB | Colour — sequence matching, on no weights at all |
| 10 | **Wire `ChatterboxTTS.audio_prompt`** + record ~10 s per character | 0 GB | Sound — real casting instead of one pitch-shifted voice |
| 11 | **Build `26_ltx23_flf2v.json`** (clone `12`, swap in two `LTXVAddGuide` + `LTXVCropGuides`) | 0 GB | Editing — controlled transitions, 8× cheaper than Wan |
| 12 | **Re-cut the seven flat-dissolve films** with the `in:` grammar | 0 GB, edit stage | Editing — biggest visible jump per minute spent |
| 13 | **Write `story.py`**: logline → spine → beats → `films/<slug>.json` | 2–3 h | Story — removes the only fully manual stage |
| 14 | `Qwen-Image-Edit-2509-Relight` **+** `-Light-Migration` (+ the 2509 Lightning LoRA to run them fast) | ~2.5 GB | Colour — unblocks four present-and-wired templates. Light-Migration is the *only* way to move light direction off a reference |
| 15 | `qwen-image-edit-2511-multiple-angles-lora` | ~1 GB | Character — manufactures the character bible |
| 16 | Finish HunyuanVideo 1.5 support files (VAE, byt5, sigclip, upsampler) | ~3 GB | Turns 46.5 GB of downloaded DiTs from dead weight into a working third motion model |
| 17 | Real `.cube` film-emulation LUTs, driven by `lut3d=interp=tetrahedral` | a few MB | Colour — instant credible looks. Below #1 only because authoring your own is better craft |
| 18 | Wan 2.2 Fun Camera DiTs | ~28 GB | Cinematography — *parametric*, repeatable camera moves |
| 19 | Demucs in its own venv | ~300 MB | Sound — vocal ducking. **Never** into ComfyUI's venv |

**Where ffmpeg beats buying a model, stated plainly:** overall film look, black/white point,
split-toning, saturation policy, contrast, grain, halation, temporal flicker, shot-to-shot luminance
and chroma matching, and reproducibility across re-runs. All deterministic, zero-GPU, iterable in
seconds, versionable as one CLUT PNG. Models are worth paying for only where the pixel content
itself must change — **relighting** (#14) and **drawing style**. Everything else here is a transfer
function, and you already own the best tool for those.

**Do not buy:** the LTX-2.0 19B family (superseded by your 2.3 + IC-LoRA), Lotus depth, Wan
Fun-Control weights, `Qwen-Image-Edit-2509-Light-Migration` (pinned to the base you're superseding),
or SCAIL2 character replacement (a post technique for live plates you don't have). A fancy
transition library is also pointless — `xfade` already exposes 58 and you use one.
