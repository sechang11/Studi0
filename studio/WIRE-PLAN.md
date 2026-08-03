# WIRE-PLAN — compile.py -> short.py

**Status: the gap is CLOSED. This document is now a verification and residual-work spec, not an implementation plan.**

## 0. Provenance, and why this document changed shape

This plan was commissioned to specify a patch closing a reported break: `studio/compile.py`
emitted 9 top-level keys, `scripts/short.py` needed 14, and the first spoken line raised
`KeyError: 'voice'`. Five agents mapped both ends; two contracts were adversarially verified.

**While that analysis was being written, the patch was implemented.** Verified directly:

| file | at analysis time | now | evidence |
|---|---|---|---|
| `studio/compile.py` | 244 lines, 9 film keys | **418 lines, 14 film keys** | `md5 38b04e7e7bf865a4201eebd5c23c9297` |
| `scripts/short.py` | 630 lines | **645 lines** | `md5 ac0cd03dbca1675734fb34383940ceba` |
| `studio/characters/` | empty | **3 cards** (VIRO, RASK, MANAGER) | `ls` |
| `studio/cues/` | empty | **8 cards** | `ls` |

`short.py` moved through three revisions in ~15 minutes (630 -> 634 -> 645). **Every line
number below is stamped to the md5 above. Re-grep by symbol before trusting one**, e.g.
`grep -n 'narrator_voice' scripts/short.py`.

The reported break is real but **historically located**: in the current `compile.py` it cannot
occur. All line citations in the source material are off by roughly +4 after line ~246 — the
crash the material cites as `short.py:364` is now `short.py:368`.

### Verified end-to-end, read-only

`compile_movie("studio/movies/derby-ep1.movie")` imported in memory (no file written):

```
TOP KEYS: title fps canvas engine keyframe_engine anime_ckpt ipadapter_weight style
          anime_sheets sheets characters voices music beats          <- 14/14
beats: 12 | with ref: 8 | with line: 6
CONTRACT FAILURES: NONE
```

Every beat has `id`/`tags`/`motion`; every `line.who` resolves in `voices`; every `template`
survives `scene_templates.expand`. **A smoke render is in flight as this is written**
(PID 68290, `short.py studio/movies/derby-ep1.json`, log `/tmp/derby-smoke.log`, reached
`=== KEYFRAMES: 12 ===`). Its result supersedes this document's predictions.

---

## 1. The key table

`short.py` performs no validation: `film = json.load(...)` at **short.py:632** is the entire
input check. Keys are therefore discovered mid-render, not at load.

Only **two** keys are unconditionally hard — `title` (short.py:633) and `beats` (short.py:413).
Everything else the material marked "hard" is *optional container / hard child*: the container
is fetched with `.get`, then a child is subscripted bare. That distinction is what makes the
fix order obvious.

| key | failure if absent | how screenplay.py builds it | how compile.py builds it NOW |
|---|---|---|---|
| `voices` | **THE BREAK.** `.get` at short.py:349 survives; `vo.get(who,{})` at :359 returns `{}`; `cfg["voice"]` at **:368** raises `KeyError: 'voice'`. Fires before `run()`, so zero GPU cost. | screenplay.py:234-236 — splits one `voice: <engine> <path>` string from each CHARACTER block | **compile.py:378-380**, from `studio/characters/*.json`. Plus a *compile-time* assertion at **compile.py:289-292** naming the exact renderer line it prevents |
| `anime_sheets` | No crash. `refs[0] in sheets` at short.py:251 fails -> IPAdapter weight **0.0** at :255. Renders a complete film with no character likeness. | screenplay.py:231 | **compile.py:365, 375** |
| `sheets` | Dead on this path — short.py:274 `continue`s before the Qwen branch. Both compilers hardcode `keyframe_engine="anime"`. | screenplay.py:232 (same dict, twice) | **compile.py:376** (same dict, twice) |
| `characters` | `.get` -> `{}`; `expand()` no-ops, so `{NAME}` placeholders survive literally into `motion` (short.py:335). Never applied to `tags`. | screenplay.py:233 (identity map) | **compile.py:377** (identity map) |
| `music` | `.get` -> `[]`; silent film, still masters and delivers. Each cue that *is* present hard-requires `prefix`/`tags`/`seconds` (short.py:388, :392-393). | screenplay.py:237 — from hand-written `MUSIC ep_cold @0 95s` offsets | **compile.py:341-349**, from `studio/cues/*.json` placed on the **measured** timeline via `beat_seconds` (compile.py:120-129) |
| `beat["ref"]` | `.get` -> `[]` -> IPAdapter 0.0. Not emitted at all previously, so *all* beats were characterless. | screenplay.py:202-203 | **compile.py:301** |
| character tags in `beat["tags"]` | Not a crash — a quality hole nobody flagged. Old `tags` were scenery+mood only, identical for every beat in a scene. Even with sheets and refs there was nothing for a likeness to attach to. | screenplay.py:196-200 | **compile.py:302-308** — card tags + `MALE` + `WEAR[wear]`, consuming the `wear` that was previously computed and discarded |

### Still absent, by design — none is a crash

| key | read at | consequence | verdict |
|---|---|---|---|
| `hook` | short.py:472 | no title overlay | unreachable from both formats; screenplay.py:106 parses `HOOK:` and drops it |
| `hud` | short.py:498 | no scoreboard | if ever added, `before`/`after` are bare subscripts |
| `beat["caption"]` | short.py:450 | no story caption band | `captions` VAR declared, never written |
| `beat["grade"]`, `beat["transition"]` | **nowhere** | emitted, read by nobody; grade is hardcoded in `make_cut` | dead payload |
| `fps` | **nowhere** | `FPS = 24` is a module constant (short.py:68) | `fps: 30` silently renders at 24 |

---

## 2. The patch

### 2a. Already written — review these, do not rewrite

In dependency order, all in `studio/compile.py`:

| # | function / block | derived from | contract |
|---|---|---|---|
| 1 | `liblist(kind) -> {id: card}` **:107** | new; generalises `lib()` **:98** | loads a whole preset dir. Enables cast/cue lookup without a call per name |
| 2 | `beat_seconds(beat) -> float` **:120** | screenplay.py:250 `--timeline` | expands the template and sums cut lengths. **Also a free pre-flight validator** — an unknown `template` now `SystemExit`s at compile time instead of at the `cut` stage after all GPU spend (`scene_templates.py:145-147`) |
| 3 | cast resolution **:229, :253-264, :285-297** | screenplay.py:194 + parse | `characters:` -> upper-cased list, each validated against `studio/characters/`. Speaker resolution prefers the line's `who`; otherwise the scene's first declared character, unless `template in NO_PERSON` (**:222** = pillow/insert/establish) |
| 4 | speaker assertion **:289-292** | *fixes a hole screenplay.py still has* | screenplay.py:211 writes the raw token while :236 filters the registry by `if v.get("voice")` — so the working reference is one typo from the identical `KeyError`. compile.py now refuses at compile time |
| 5 | `ref` + tag splice **:301-308** | screenplay.py:196-203 | `WEAR` ladder (**:60**) overridable per card via `wear_tags` — better than screenplay.py's global constant |
| 6 | registries **:365-382** | screenplay.py:231-237 | the five keys |
| 7 | music timeline **:316-349** | *supersedes* screenplay.py:117-123 | merges consecutive scenes on the same cue, honours `silence:`, generates +2 s long and trims in the mix |

### 2b. Still to write

| # | signature | why | size |
|---|---|---|---|
| 1 | `validate_film(film) -> list[str]` | compile.py validates its own output *implicitly*. Nothing validates an arbitrary `film.json` — a hand-edited one still discovers faults mid-render. Re-assert: `title`, `beats`, per-beat `id`/`tags`/`motion`, `line.who in voices`, unique `id`. Call from `main()`; add `--check` to short.py. | ~25 lines |
| 2 | `warn_dead_vars(movie, chapters) -> list[str]` | Six VARS remain parsed-then-dropped: `logline`, `negative`, `fx`, `type`, `captions`, `blocking` (verified: zero reads after compile.py:225). The file's own doctrine at **compile.py:39-43** is "NOTHING SILENTLY DOES NOTHING". | ~15 lines |
| 3 | `beat_caption(v, b) -> str \| None` | wires `captions` -> `beat["caption"]` (short.py:450), the only one of the six that needs no renderer change | ~10 lines |

`negative`, `fx` and `blocking` need **renderer** work, not compiler work — `short.py` has no
film-level negative key in its read set at all. Do not fake them in compile.py.

---

## 3. Preset -> variable resolver

Ten preset categories, 87 files. `compile.py` calls `lib()`/`liblist()` for **five**:
looks, transitions, cameras, characters, cues.

| category | field | maps to | status |
|---|---|---|---|
| looks | `tags` | folded into `beat["tags"]` (compile.py:307) | **wired** |
| looks | `grade` | `beat["grade"]` | **dead** — no reader; grade hardcoded in `make_cut` |
| cameras | `id` | `beat["camera"]` (compile.py:276) | **wired** — the 8 `ready` ids are exactly short.py's 8 recognised moves; the 3 roadmap ids degrade to `static` with a warning |
| transitions | `id` | `beat["transition"]` | **dead** — no reader |
| characters | `tags`, `sheet`, `voice`, `wear_tags` | `beat["tags"]`, `anime_sheets`, `voices` | **wired** |
| cues | `tags`, `bpm`, `key`, `level` | `film["music"][i]` | **wired** |
| shots | `id` | `beat["template"]` | validated indirectly via `beat_seconds`; `approx_seconds` **unread** (`clip_secs` hardcoded 6 at compile.py:275) |
| pacing | `scale` | `beat["intensity"]` | **partial** — `PACE` at compile.py:95 hardcodes 3 of 7; `brisk`/`contemplative`/`decelerating`/`frantic` silently resolve to 1.0. `rhythm`, `hold_bias` unread |
| lighting, layers, weather, soundscapes | all | — | **no landing point** in short.py |

### Genuinely ambiguous — do not guess

| field | candidate target | why ambiguous |
|---|---|---|
| `emotions/*.json` `voice_style`, `voice_rate` | short.py:364-366 IndexTTS2 axes | The renderer exposes 8 fixed axes (Happy, Angry, Sad, Surprised, Afraid, Disgusted, Calm, Melancholic). The 9 emotion cards are angry/cold/determined/exhausted/fear/grief/joy/neutral/resolve. Only `angry`, `joy->Happy`, `fear->Afraid` are unarguable. `cold`, `determined`, `resolve`, `exhausted` have **no axis**. A guess here silently mis-performs a line. |
| `weather/*.json` `wind` (float 0.4) | census `world.wind_speed` (enum still\|breeze\|...\|gale) | float vs enum, no stated quantisation |
| `weather/*.json` `ground` (`"wet"`) | census `world.ground_state` | `"wet"` is **not a member** of that enum (`wet_reflective` is) |
| `soundscapes/*.json` `duck`, `reverb`, `bed_level` | — | short.py has no ambience bed and no sfx stage at all |

**The 461-variable census (`studio/variables.json`) maps to nothing.** Zero of its dotted
names appear as a literal in any renderer or compiler source. Its `status: ready` on 280
entries describes intent, not wiring. Do not treat it as a contract.

---

## 4. Decisions the author must make

| # | question | recommendation |
|---|---|---|
| 1 | `MANAGER` has no reference sheet -> IPAdapter 0.0 on his shots (warned, compile.py:355-359). Ship or generate? | **Ship.** He is a supporting voice; one drifting face is a smaller defect than delaying the first end-to-end render. Generate later with `make_sheets.py`. |
| 2 | Auto-generated reaction beats — port them? screenplay.py:213-221 produces 59 of episode01's 216 beats. | **No.** The reactor heuristic hardcodes the literal string `"MANAGER"` (screenplay.py:214) and assumes a two-hander. Porting it imports a bug. Add an explicit `react: NAME` beat key when needed. |
| 3 | `ref` for non-dialogue beats: a scene lists everyone, `ref` wants one. | **Keep the current rule** (first declared character, suppressed for `NO_PERSON` templates, compile.py:296-297). It is defensible and legible. |
| 4 | `MALE` constant (compile.py:54) is injected into every character beat — this film cannot render a woman. | **Move it into the card** as an optional `base_tags`, defaulting to empty. One-line change; do it before a second film exists. |
| 5 | `grade` / `transition` are computed and dropped. | **Keep emitting, add a warning.** Wiring them means threading per-beat grade into `make_cut` — a renderer change, out of scope for "one film renders". |
| 6 | `clip_secs` fixed at 6 vs `shots/*.json approx_seconds`. | **Leave at 6** for now. It is the main cost knob (below); vary it only once the pipeline is proven. |
| 7 | `--stage` accepts one value; there is no "everything except music". | Not worth fixing. Run stages individually. |

**Resolved already, no action:** the slug collision (title is now `DERBY STUDIO TEST` ->
`derby-studio-test`, so the delivered 526 s master at `.../the-derby-ep1/` is safe) and the
`COMFY_ROOT` landmine (short.py:58-59 now defaults to `~/ComfyUI` and `127.0.0.1:8188`).

---

## 5. The smoke test

Run from `~/shared/comfy-studio` on the box. No env exports needed.

```bash
# 1. compile (writes studio/movies/derby-ep1.json)          ~0.1 s
python3 studio/compile.py studio/movies/derby-ep1.movie --timeline

# 2. ZERO-GPU proof: voices used to be the crash. Run it FIRST.
#    Stage order is keyframes -> clips -> voices (short.py:622), so a plain
#    run would burn ~7 min of GPU before reaching the old fault.
python3 scripts/short.py studio/movies/derby-ep1.json --stage voices    # ~16 s, 6 lines

# 3. generation, cheapest first
python3 scripts/short.py studio/movies/derby-ep1.json --stage keyframes # ~50 s
python3 scripts/short.py studio/movies/derby-ep1.json --stage clips     # ~6.5 min
python3 scripts/short.py studio/movies/derby-ep1.json --stage music     # ~1 min

# 4. cut. Requires clips to exist — with none it dies on an IndexError,
#    and it wipes {out}/_work as its first act (short.py:408).
python3 scripts/short.py studio/movies/derby-ep1.json --stage cut       # ~2-3 min
```

Wall clock derived from the delivered 216-beat render's file mtimes: keyframes **4.1 s/beat**,
clips **32.1 s/beat** at `clip_secs=6`, voices **2.6 s/line**, music **18.7 s/cue**.
This film is 12 beats / 6 lines / 3 cues -> **~10-11 min total**.

### Cheapest first proof

1. `compile.py:275` `clip_secs=6` -> `2`. LTX drops 145 -> 49 frames (short.py quantises to
   `8n+1`), roughly 3x faster clips. **-> ~4 min.**
2. Copy the `.movie` and delete everything after `CHAPTER cold_open`: 3 beats, 1 line, still
   exercising keyframe + clip + voice + cut. **-> ~60 s + cut.**

Do **not** lower `canvas` expecting a speed-up. Generation size is fixed at `KF = (1664,928)`
and `VID = (1280,704)` (short.py:65-66); `canvas` is read only at short.py:470 for the final
composite.

**Success:** `cut` prints `>>> <out>/derby-studio-test.mp4` plus a duration/shot-count/LUFS
line. Audio duration must match video duration. All four generation stages are resumable —
each skips a beat whose output already exists — so a failure costs only the failing stage.

---

## 6. What this does NOT fix

The goal was **one film rendering**. It is not a general authoring layer.

- **461 census variables still drive nothing.** Zero are read by any renderer. `studio/variables.json` remains documentation.
- **58 of 87 presets still have no consumer** — lighting, layers, weather, soundscapes, and 4 of 7 pacing values. All are `status: partial`; their rich fields (`wind`, `ground`, `duck`, `reverb`, `temp`, `ratio`) reach nothing.
- **206 cards remain a display artefact.** Their ~900 `panels[].clause` strings are the only enum-value-to-prompt-text mapping on disk and no compiler reads them. `app.html:263-264` still interpolates `look_at` (absent on 198/206) and `method`/`model` (absent on 72/206) unguarded, printing `undefined`.
- **Six VARS still silently do nothing:** `logline`, `negative`, `fx`, `type`, `captions`, `blocking`.
- **Three of four text-overlay features stay unreachable:** `hook`, `hud`, `caption`.
- **`fps` is still ignored** — `FPS = 24` (short.py:68). The `--vars` help calls it "LOCKED"; the renderer never reads it.
- **Stable seeds cover keyframes only.** `stable_seed` (compile.py:132-141) feeds `beat["seed"]`, read only on the keyframe path. Clips (short.py:340, `seed0 + i*13`) and voices (short.py:369, `seed0 + i*17`) are still positional, and the voices index enumerates the *filtered* line list — inserting one line re-rolls every later voice.
- **No sfx stage, no lipsync, no per-shot durations** (`hold` is inert), **no reaction beats.**
- **Cosmetic:** short.py:508 emits a `SyntaxWarning` for invalid `\:` escapes three times on every import, and hardcodes a football clock (`89:%{eif...}`) into the HUD overlay.

One more, unrelated to this patch: `beat["id"]` also names a file in the **shared**
`{COMFY}/input/` directory (staged i2v source frames). That namespace is global across every
film ever rendered and is never cleaned up — two films sharing a beat id race each other.
