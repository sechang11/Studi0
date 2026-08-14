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
