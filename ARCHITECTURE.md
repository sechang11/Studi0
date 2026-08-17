# ARCHITECTURE — the one path

Written after ~45 commits of feature work landed in quick succession, against a measured
inventory: 24 pages, 119 tools, 25 scripts, 10 distinct generation entry points, 609 cards
across 20 sibling directories, a 2,335-line server, 21 root markdown files, 16 GB of
samples. Supersedes REFACTOR.md, which it absorbs.

The diagnosis in one sentence: **the vision arrived incrementally, and each arrival grew a
new path beside the last one instead of deepening it** — so the app now has several roads
to most destinations, each partly finished, and the cost is paid every time a fix lands on
one road and not its siblings.

This document names the destinations, picks one road to each, and sequences the merge.

---

## 1. What this app is

Assembled from the vision statements across this project's life:

**Primary: top-tier video, made locally on the 5090.** Films built scene by scene from
layered, reusable inputs — style, place, character, emotion, light, motion, camera — with
voice, score and effects; consistent characters across shots and angles; and a growing
encyclopedia of craft (transitions, shot grammar, cut rhythm, the things a director knows)
that is *executable*, not just written down.

**Secondary: 3D printing.** Meshify the cast; print gadgets and props.

**Standing constraints:** open-source models first — the 5090 was bought instead of API
credits, and iteration must stay free. Every capability must be reachable from the app.
Every claim must be measured or labelled unverified.

## 2. The rules already paid for

These were each bought with a real failure. They are the constitution of the consolidated
app; anything that violates one is a bug even if it works.

1. **The model renders nouns.** Adjectives, moods and framings lose to any noun in the
   prompt. Subject is decided first; competing nouns are removed, not outweighed.
2. **The engine is a property of the style**, and **a card is written in a dialect**
   (tags vs prose). Crossing engines silently deletes the card — a LoRA is a delta on
   weights, a card is a delta on a prompt language. Wave 4 lost 82 frames to this.
3. **Evidence lives beside the artifact.** A recipe next to every file; a verdict on every
   card. If a number disagrees with the pixels, the record is stale — regenerate it,
   never edit it.
4. **Discovery over registration.** The gallery manifest held 1,828 of 3,612 real items.
   Walk the disk; a writer that must remember to register will eventually forget.
5. **Coverage is distinct-counts, never totals.** Twenty frames of one close-up is one
   frame twenty times.
6. **Moved, never deleted.** Rejected frames, replaced files, normalised audio — keep the
   original beside the change or in `_rejected/`. A change you cannot undo is a change you
   cannot check.
7. **Every loop has a deadline; every checker gets validated against a known answer before
   its verdict is believed.** The motion checker failed 7/7 until the instrument itself was
   tested and found sign-flipped.
8. **One checker per property.** Two checkers that can disagree are worse than one that is
   wrong. mesh_doctor for meshes, filmrules for films, motion_check for movement.
9. **A capability without a reachable door does not exist.** FLUX.2 sat installed and
   unusable because zero style cards named it; 16 pages were unreachable from home.
10. **Refactor and behaviour change never share a commit.** Outputs must stay comparable.

## 3. The overlap map

Each row is one intent that currently has several implementations. **Bold** survives.

| Intent | Paths today | Resolution |
|---|---|---|
| *See what we made* | `/gallery` (manifest), **`/library`** (disk discovery), `/video`, per-kind pages (styles, places, loras, tags…) each with its own payload assembler | Library is canonical. Kind pages become library views; `/video` becomes the `domain=video` view (its measurement extras move into recipes); the manifest retires. |
| *Make something* | `bin/generate.sh` (roll), `isolation_run` (isolate/grow), `sequence_render` (beats), `gallery_gen` / `gallery_fill` / `make_samples` / `flux2_gallery`, `/api/library/grow`, wizard, `/make`, `/generate`, story takes, `epic` / `short` / `cartoon` | **One generator core** with modes — `roll · isolate · grow · beats · scene` — one CLI, one API route. Pages stay as fronts but all call the core. Films are the assembly layer consuming the same scene renders. |
| *Is it real / any good?* | `audit`, `package_check`, `motion_check`, `filmrules`, `lora_check`, `test_*`, `/verify`, panel verification, reject reasons | **One evidence system**: every checker writes a dated verdict (MEASURED / JUDGED / UNVERIFIED + method) onto the card or recipe it judged. `/verify` becomes the reading surface for verdicts plus the manual-judgement input, sharing the reject-reason taxonomy — the user already spotted these are the same act. |
| *Who is in it?* | `/newchar`, `/cast`, `character_new`, `character_suite`, `make_wave4` / `make_wuxia_*`, turnarounds, LoRA training, dossier | **One character pipeline** expressed as staged package: card → sheet → 18-slot set → turnaround → dataset → LoRA → voice → *(mesh)*. Every authoring path ends by registering the same card shape with dialect declared. `package_check` measures the stages. |
| *Engine knowledge* | `compose.resolve` (routing), `roll` (drawable, subject rules), `render_job` (graph branches), `isolation_run` (NEUTRAL, dialect guard, self-contained exclusion), `sequence_render` (subject modes) | **`studio/engine/`** owning: routing, dialect legality (card × style × engine), graph builders per engine/domain, dial application by input key. Everything imports it; local copies die. |
| *3D* | `/model3d` (character meshes), `/make3d` (image→mesh), `to_print`, `bambu`, `mesh_doctor` | One **Print** section. `make3d` is the door; `model3d` becomes the character-mesh view; the character package gains an optional `mesh` stage. mesh_doctor stays the sole checker. |
| *Craft knowledge* | `VIDEO_RULES.md` (enforced), `PROMPTING.md` (measured), 21 root MDs, card notes, `sequences/` | The **encyclopedia is the card library**: transitions, shots, sequences, motions, cameras, pacing — each card carrying (claim, consumer, evidence). Docs collapse to README + this file + `craft/` (machine-read rules) + `docs/`. |
| *Models & workflows* | 96 checkpoints, 44 workflow files, 50 references in code — **6 referenced workflows do not exist on disk**, 0 unused | **Models become a card kind** (big cards, earned by content: dialect, measured speed, VRAM, strengths, a frame strip). Workflows get a reachability table — reachable / installed-but-unreachable / referenced-but-missing — linked from model cards. The 6 missing references are Phase-0 bugs. |

Why this happened is worth stating without blame: vision statements arrived one at a time
("make a gallery", later "organize the library", later "sets", later "packages"), and each
was built as a new thing because rebuilding the old thing mid-request felt slower. The
consolidation below is the debt repayment, sequenced so the primary goal is never frozen.

## 4. The target: six layers and a side path

```
CARDS      one schema per kind, one loader; dialect, provenance, package, verdict
  ↓
ENGINE     routing + dialect legality + graph builders (the only place graphs are wired)
  ↓
GENERATOR  one core, five modes: roll · isolate · grow · beats · scene
  ↓                                   (every artifact + recipe beside it)
EVIDENCE   one verdict format, many instruments; /verify to read and judge
  ↓
LIBRARY    the single browsing surface: frames, sets, kinds, models, stars, rejects
  ↓
ASSEMBLY   story → scenes → takes → cut (one cutter + sound department) → grade → film
           consistency kit: master-frame, first→last chaining, reference conditioning

SIDE: PRINT   make3d → mesh_doctor → to_print → bambu; characters gain a mesh stage
```

## 5. The plan

Each phase is small enough to gate, and refactor never shares a commit with behaviour.

**Phase 0 — Truth first.** Fix or stub the 6 referenced-but-missing workflows; add the
reachability check to `audit`; record `wear` in recipes (one field — it unlocks the outfit
axis of the character package, which is currently unmeasurable); keep shrinking the CLI
contract baseline. *Gate: audit 0 errors; reachability table clean.*

**Phase 1 — Cards.** One loader + per-kind schema: `id, name, status, dialect(s),
provenance, verdict, package`. Dialect required on characters and styles. Blocked-voice
enforcement moves into the loader (one place instead of every picker). No folder moves —
ids and paths stay; the schema is the substance, relocation is cosmetics for Phase 7.
*Gate: every card validates; a wave-4-class dialect crossing is refused at load.*

**Phase 2 — Engine.** Extract routing, legality and graph builders into `studio/engine/`;
migrate `render_job`, `epic`, `short`, `terra_mesh`, `isolation_run`, `sequence_render`
onto it; delete the local copies. *Gate: same seed, same settings → byte-comparable
outputs before and after.*

**Phase 3 — One generator.** `generate.py` with the five modes; `generate.sh` becomes a
thin wrapper; `/api/library/grow` and the `/generate` page call it; `gallery_gen`,
`gallery_fill`, `make_samples`, `flux2_gallery` retire once any unique behaviour is
absorbed. *Gate: all pages render; recipe shape unchanged.*

**Phase 4 — Evidence.** Shared verdict writer; every checker stamps what it judged;
`/verify` reads verdicts and takes manual judgements with the reject taxonomy. Motion
triage: sweep every clip with `motion_check`, retire or regenerate the failing motion
cards (currently ~2 of 19 sampled pass), finish the 976-panel verification. *Gate: every
`ready` card carries a dated verdict or is relabelled UNVERIFIED.*

**Phase 5 — Library absorbs.** Models as a kind with the big cards; `/video`, `/gallery`
and kind pages become views; manifest retired. *Gate: nothing reachable only through a
retired page.*

**Phase 6 — The film spine** (primary goal; new build allowed). One cutter for
`short`/`epic` with the sound department (#46 done, #47, #49); the **master-frame
consistency kit** — one hero still per scene, crops and outpaints derived per beat,
first→last chaining between shots (28_flux_outpaint + 50_ltx_first_last +
14_qwen_edit_ref already exist; the derive tool does not — this is the single biggest
missing piece for consistency-in-angles); story editor consumes sequence cards; the
transition filters get their consumer (#24). *Gate: one short film rendered end-to-end
through the consolidated path, watched, filmrules passing.*

**Phase 7 — Shell.** One page shell + stylesheet + nav route table; `serve.py` split into
route modules (the `*_routes.py` pattern already exists); docs merged; optional card-folder
unification. Cosmetic, last, safe.

## 6. New build the vision still requires

Not consolidation — things that do not exist yet, in value order:

1. **Master-frame kit** (Phase 6) — the local answer to multi-shot consistency.
2. **Motion regeneration after triage** — the encyclopedia's motion shelf is mostly
   unverified or failing its own claims.
3. **Transition consumer** — 12 cards, 6 real filters, nothing applies them.
4. **Model cards + reachability table** — makes the 96 checkpoints legible.
5. **Character mesh stage** — connects the cast to the printer.
6. **Authoring pages for simple kinds** — the library's "+" tile currently lands on
   `/generate` for places and styles because no authoring page exists.

## 7. Kill list

The manifest gallery path and its writers; `gallery_gen` / `gallery_fill` /
`make_samples` / `flux2_gallery` (after absorption); the `_v2` tool pairs; per-page CSS
copies; the NEUTRAL style list (becomes engine data); overlapping doc pairs
(FILMCRAFT/FILMMAKING, CAPABILITIES/NEW-CAPABILITIES, GENERATED/GENERATING).

## 8. What must not move

Card **ids** (referenced by stories, LoRA paths, inputs hashes). The **samples tree**
layout (discovered by path convention). The **recipe shape** (extend only — never rename a
field something already reads). And during every phase: outputs stay comparable, because
comparing an output to what it used to be is how every bug in this project has been found.


## 9. Phase log

| Phase | Commit | Gate result |
|---|---|---|
| 0 - Truth first | `13083d8` (plan) + session commits | 6 missing-workflow refs fixed; workflow-file audit added; CLI contract at 0 grandfathered |
| 1 - Cards | `36071ac` | one loader (proven byte-identical to `load_libs`), per-kind measured schema, dialect LAW in compose + roll reroll, blocked-voice enforcement at `cards.require_voice` |
| 2 - Engine | `4a4b980` | `studio/engine.py`; image graphs, submitted video wf, keyscale and style pools all byte-equal before/after; tail (20 `load_wf` sites) closed in `5d2519d` via `epic.load_wf` delegation, proven over all 44 workflows |
| 3 - One generator | `b2038f6` | `generate.py` roll/scene/grow/isolate/beats; wrapper + page + grow route all through it, live-tested (6 kept in a 2-min run, scoreboard parsed); 4 tools + a stale duplicate retired |
| 4 - Evidence | `2dc65f4` | every ready card carries dated evidence or honest UNVERIFIED (audit-enforced, 0 errors); 131 panel sheets judged by eye (69 works / 42 mixed / 20 fails); motion sweep 686 clips, `walk_in` demoted, camera demotions reverted with dual-path evidence |
| 5 - Library absorbs | `600957d` | 46 model cards (13 measured), big-card browse view; /gallery retired to a 302, /api/gallery reads disk discovery (4,899 vs the manifest's 1,828) |
| 6 - Film spine | `5d2519d` | sound_dept (levelled buses + ducking + sfx stage), transition consumer, master-frame kit (crop/outpaint/edit/chain/scene, demo watched); gate film deck-run: 13.5s, -9.74 LUFS / -0.90 dBTP, filmrules 0, frame strip watched |
| 7 - Shell | partial | docs collapsed to README + ARCHITECTURE + docs/ + craft/; REMAINING: one page shell + shared stylesheet, serve.py split into route modules, optional card-folder unification - deliberately left for a session with eyes on the UI, because blind cosmetic surgery on 22 pages is how a working app breaks overnight |

Remaining from section 6: depth pass (#22), motion regeneration for the demoted/weak
motion shelf, character mesh stage, authoring pages for simple kinds.

### 2026-08-15 afternoon (4h block)

| Commit | What | Gate |
|---|---|---|
| `6bca07c` | ComfyUI 0.28 -> 0.33.1 (tag `pre-0.33-snapshot`); negative prompt reaches every graph via `engine.set_negative`; healthcheck learns the helper; route modules guarded | all 7 domains re-rendered ok; healthcheck WRONG 10 -> 4 |
| `1c63d40` | `ui2api.py` (UI template -> API graph, server-validated); `51_ltx25_i2v.json`; `ltx25_probe.py`; fetch script + runbook. **Weights gated on HF - user step** | server validation: only gated-file errors remain; 2.3 baseline 28.9s / ssim 0.42 on record |
| `0587aa3` | photo-count experiment LoRAs get cards (kind `experiment`) | lora_scan clean; healthcheck BROKEN 2 -> 1 |
| `c5a2a9e` | depth pass (DA3 core nodes) + rack_focus/dolly_zoom as make_cut post steps; probe measures renderability | film re-cut with both; strips looked at; audit 0/0; BROKEN 1 = orbit (honest) |

Ecosystem check (evidence-based, not FOMO): LTX-2.5 (2026-08-12, native multi-shot) is
the one worth bringing in - same routed family, needs only the gated download. MiniMax H3
(110 GB new stack), Wan 2.5+ (not open weights), HunyuanVideo 1.5 (on disk, unrouted, needs
an A/B) are deferred and the reasons are in `docs/LTX25-RUNBOOK.md`.

### 2026-08-15 evening (second 4h block)

| Commit | What | Gate |
|---|---|---|
| `e795f73` | TERRA headpiece resolved (prose fixed, tags held for the LoRA contract, reason on the card); motion-hold probe grades holds like the compiler | healthcheck WRONG 4 -> 0 |
| `99807dd` | audio_sweep (17 voices measured; 20 sfx + 21 cues rendered+measured); look_check (10 of 25 looks crushed 42-70% to black - task 26 unswept - fixed with held-toe curves, colour intent kept, before/after looked at) | evidence debt 89 -> 16 ready-UNVERIFIED (shots+pacing, structural); audit 0/0 |
| `28114bb` | frame_check: Gemma-4 VLM on core nodes describes a frame; recipe nouns checked (synonyms grown from looked-at misses; --recheck free); library detail shows "What a VLM saw"; compose C22 measured verdict beats prose regex; check_refs @tokens | places 279/304 seen; C22 0 false warnings; 1947 refs 0 dangling |
| `a075454` | frame_check on characters (visual nouns from tags/prose; person gate separate from identity) finds 5 no-person wave-4 leftovers, rejected via the library path; "ask a VLM" button + /api/library/check | characters 133/138 seen |
| `9aefe06` | task 50: --wear flag (ladder was unreachable); wear_sweep sheet looked at: garment PRESENCE renders, damage ADJECTIVES lose to the LoRA; compile-time note | rungs 2-4 note fires, rung 1 quiet |

Instrument lessons this block, all paid for: ebur128's running `I:` line demoted 17
good voices before the Summary-only parse; ffmpeg signalstats read a PNG at a different
range than a lut pass and contradicted itself (PIL is the one instrument now); a VLM asked
YES/NO says NO to things it just described (never ask yes/no - ask for a description and
check the nouns); a checker's fail verdict and its printed number must come from the same
measurement or one of them is lying.

Still owed: LTX-2.5 weights (user's HF token), the one-page shell / serve.py split (eyes
on the UI), motion regeneration for the weak motion shelf, character mesh stage.

### 2026-08-15/16 overnight - LTX-2.5, and the first content slate

| Commit | What | Gate |
|---|---|---|
| `d848998` | LTX-2.5 lands. `clipmetrics.py` (hold/drift/motion, one instrument for every video comparison); `multishot.py` with robust cut detection. NATIVE MULTI-SHOT CONFIRMED: three viewpoints, one pass, identity across the cuts. Selectable as `video_engine: ltx25`; default unchanged | 2.5 drift -0.004 vs 2.3's 0.141; motion 1.54 vs 8.79 (static floor 0.001) |
| `33e4ad3` | Reverse-angle battery: 15 derived angles, 5 heroes | palette distance mean 0.0073; VLM names the subject in 14/15 |
| `fda238d` | Motion shelf on both engines - **and the over-claim rolled back**: liveness is not the card's claim | all 34 alive on 2.3; 26 statuses corrected back |
| `1a2c6b4` | 20 short-form films authored (8 supplement, 6 commercial, 6 hook) + deadline-bounded harness; LTX-2.5 in the capability gallery as folder 51 | pilot proven before the night; 35 capabilities |
| `86a0d64` | Cutter: captions cannot overlap each other or the story band | both collisions were visible in the first films |
| `37b3da8` | **ASR found the last spoken line truncated in EVERY film** - the master is cut at the picture length. Cutter now holds the final frame for the overhang | NORTHWIND recall 64% -> 76%, final line complete; 6 films re-cut |

The night's lesson, again and in three separate places: **an instrument that measures the
wrong thing is worse than no instrument.** SSIM-drift punished clips for animating.
Loudness and coverage both passed on films whose last words were missing. Liveness was
about to promote 34 cards on a test that never checked their claims. Each was caught by
asking what the number actually means - and in two cases the right instrument was already
written down in this repo from an earlier session.

New tools: `clipmetrics`, `multishot`, `motion_shelf`, `look_sheets`, `reverse_battery`,
`shorts_specs`, `overnight_shorts`, `shorts_deliver`, `shorts_asr`, `overnight_report`.

### 2026-08-16 - the slate, and three defects between "rendered" and "watchable"

The 20-film slate finished 20/20 with 0 failures. Every one of them was also wrong, in
three ways that every existing check passed:

| Commit | What | Evidence |
|---|---|---|
| `900d1ad` | **Voices were talking over each other in all 13 films then rendered.** The cutter measured the collision, printed `!! voice overlap`, and wrote the master anyway - its own comment says overlap "is not an L-cut, it is a mistake". The warning had no consumer. Lines are now scheduled sequentially | ATLAS voice stem: "atlas buy it once". ATLAS master, final 3.5s: "the trade and we are not going to pretend otherwise" - the WRONG line. The closing line was playing under the previous one |
| `900d1ad` | **More copy than picture**, which the collision had been hiding. The overflow went to a frozen final frame - a quarter of each film. Each beat's shots now stretch to cover its own read, from clip material already on disk and being discarded | ATLAS 10.3s picture under 14.5s of speech, 4.23s frozen; CREATINE 6.00s frozen, which HIT THE CAP. After: 0 freezes and 0 collisions across all 13 re-cuts |
| `b7a77b9` | **Every beat printed its sentence twice**, once as a spoken-line caption and once smaller as a story caption. Found by looking at a contact strip, not by measuring | 121 captions across the shorts, 56 suppressed as pure restatements; derby.json's 35 captions untouched |
| `642834e` | **LTX-2.5 was catalogued, verified, rendered - and invisible.** The gallery is the catalogue PLUS an authored teaching sentence, and 51 had no sentence, so the publisher skipped it silently. I had reported it as done | 34 published entries -> 35, 0 missing |
| `3ba7c8c` | Four LTX-2.5 model cards still said "gated download pending" and one said `unavailable` for a file that is on disk and loaded by a working workflow | 18.2 GB promoted to ready, stamped MEASURED |
| `c05fa2f` | **AAC adds ~1 dB of true peak, and nothing was measuring after the encode.** The limiter hit -1.2 dBFS exactly; the shipped MP4 was -0.2. Ceiling moved 0.87 -> 0.78, set for the file that ships. Adds `qc_slate.py`, which measures DELIVERED masters | pace -0.17 -> -1.33 dBTP, magnesium -0.13 -> -1.84, loudness unchanged |

**The slate, verified by ear rather than by counting.** ASR over all 20 finished masters:
mean recall **98%**, with 14 films at 100% recall and 100% tail. Before the cutter fixes
ATLAS was 91% recall on a 33% tail, hook-lift 60%, creatine 68%. Those low scores were
voices talking over each other - not the paraphrase I first blamed - and they came back
the moment the lines stopped colliding.

**The tail metric earned itself.** Overall ASR recall could not separate "the model
paraphrased" from "the line is missing" - Granite rewrites meaning, so a middling score
condemns good films. Recall of the LAST LINE ALONE does separate them, and it is what
found the ATLAS defect: recall 91%, tail 33%. A low tail with a healthy body is a real
defect; a low overall with a healthy tail is the model being chatty.

**And the correction that came with it.** An hour earlier I attributed those middling
recall scores to paraphrase. Paraphrase is real and documented, but it was not the main
cause: the scripts were being read over each other.

**Three wrong answers from the same typo class.** `find -iname "*spatial_upscaler*"`
returns nothing for a file named `...-spatial-upscaler-...`. Card ids use underscores,
filenames use hyphens. It produced a confident "not on disk" about a model that is on
disk. The fixer that followed asserts nothing - it resolves each file against the models
tree AND checks the workflow loads it, promotes only what passes both, and prints what it
left alone.

The through-line for the whole night, in one sentence: **every one of these defects was
already detected by something in this repo, and none of them had a consumer.** The
overlap warning printed. The held-frame cap silently truncated. The capability sat
verified in the catalogue. Detection without a consumer is not a check, it is a comment.

### 2026-08-17 overnight - music, and the render spine coming back from the dead

| Commit | What | Evidence |
|---|---|---|
| `d6c0c3d` | **ACE-Step 1.5 has taken a `lyrics` input the whole time.** Every cue in the library passed `lyrics=""`; the model had never been sent a word to sing. It sings | lyric take -> ASR "i counted in" from a written line; instrumental control -> the hallucinated "thank you" ASR always gives non-speech |
| `d6c0c3d` | **The house recipe, measured over six tag variants on one lyric and one seed.** Name the voice, then stop | no vocal words 10% · "clear female lead vocal" **90%** · sparse band 90% · + "mixed loud and up front, intelligible diction" **30%** · + "polished studio pop, crisp consonants" 40% |
| `ff039dc` | **short.py was unimportable for a whole session and every check passed.** `import voice_emotion` sat four lines before the path that makes it importable | three ad renders died before touching the GPU; healthcheck gains a `spine` section, proven by breaking it on purpose |
| `b064b33` | Ads rebuilt against the two complaints - daylight styles instead of STYLE_CINE's "rich shadows", and single-cut templates so shots ≈ clips | 10 shots from 9 clips, against ATLAS's 9 from 4. And the hook was running off both sides of frame: "eakfast that respects your ti" |
| `d1f699f` | Alternate takes attached to their parent card | 125 cards, 219 players |

**NAME THE NOUN. AGAIN.** The vocal recipe is the same law the image engines taught this
project in June and the sound library re-taught it in August: one noun phrase takes
intelligibility from 10% to 90%, and piling adjectives about the mix on top drops it back
to 30%. Wave 2's genres are written as INSTRUMENTS for the same reason - "nylon guitar,
cajon, hand claps" puts a flamenco in the room; "passionate Spanish feeling" does not.

**THE TESTS I SKIPPED ARE THE ONES THAT BROKE.** Twice in two sessions. The queue button
was never clicked because it costs GPU time, and it was broken. short.py was never run
end-to-end because the emotion vector had been proven another way, and it did not import
at all. Both were found by a later task tripping over them rather than by any check.
Hence the `spine` section: an import is the cheapest possible test and it catches the
whole class.

**Four bugs the music pipeline hit, all of them ordinary:** one bad card killed a 44-song
batch because `comfy.run` calls `sys.exit(1)`; `bpm 0` is below ACE-Step's floor of 10;
`"B flat major"` is not one of the 34 keyscale spellings the model accepts; and delivered
takes sat 12 dB apart until the audition copies were normalised.
