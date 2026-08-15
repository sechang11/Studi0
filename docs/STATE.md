# comfy-studio — authoritative state document

**Written** 2026-08-02 from six mined + adversarially verified transcript surveys.
**Source of truth** Claude Code session transcripts in `C:\Users\Kashix\.claude\projects\C--Users-Kashix-Documents-CS-Projects\`.
**The project files themselves are UNREACHABLE** — the SMB share `Z:` / `\\192.168.1.46\k4shix` is wedged. Every path below is from a transcript record, not from a live filesystem read. Last successful read of the share: **2026-08-02T23:51:54Z**, and that command timed out.

Status markers on every claim: `[EXISTS]` `[PARTIAL]` `[NOT BUILT]` `[BROKEN]` `[UNVERIFIED]` `[INFERRED]`.

---

## 1. Orientation

comfy-studio is a filmmaking system built on one RTX 5090 (`k4shix`, 192.168.1.46, Fedora 44, ComfyUI 0.28.0 at `/home/k4shix/ComfyUI`, Windows view `Z:\ComfyUI`). It has three layers. **Bottom:** a measured capability layer — ~202 GB of models, 38 API-format ComfyUI workflow graphs, and 33 self-documenting capability folders that record what each model can actually do and at what cost. **Middle:** two renderers — `scripts/epic.py` (long-form narrated films, `shots` schema) and `scripts/short.py` (the current one: generate few clips, cut them into many micro-shots, add energy in post, `beats` schema) — which have produced eight finished films including a 20-minute Berserk piece and an 8.8-minute anime episode. **Top:** an authoring layer built on 2026-07-31 in response to the user's demand for "a framework for making movies … a timeline that the user can edit for more control in each scene" — a MOVIE > CHAPTER > SCENE text format (`studio/compile.py`), a 461-variable census, an 87-preset category library, a local web app on port 8777, and 206 capability cards with 976 rendered comparison panels showing what each option value actually looks like. **The top layer does not connect to the middle layer.** `compile.py` emits render JSON but was never wired into `short.py`, so nothing authored in `studio/` has ever rendered a single frame of video. That gap was stated four times, escalating, and was never closed.

---

## 2. What exists and works

### 2.1 Renderers and authoring tools

| Path | Status | What it is |
|---|---|---|
| `Z:/shared/comfy-studio/scripts/short.py` (630 lines, 31,788 b, last edit 2026-07-31T11:22Z) | [EXISTS] | **Current renderer.** `beats` schema. Stages keyframes → clips → voices → music → cut. Has produced THE CLASH, THE DERBY, THE DERBY Ep.1. |
| `Z:/shared/comfy-studio/scripts/epic.py` (1069 lines, 51,457 b, last edit 2026-07-30T22:52Z) | [EXISTS] | **Long-form narrated renderer.** `shots` schema. Stages narrate → keyframes → clips → sfx → music → edit. Produced chrono, berserk, hound, her-name. Its master chain is [BROKEN] — see §4.4. |
| `Z:/shared/comfy-studio/scripts/scene_templates.py` (349 lines, 17,102 b) | [EXISTS] | 17 templates in two opposed grammars + `SPORTS_CLASH_50S` 35-entry arc table + `arc_summary()`. |
| `Z:/shared/comfy-studio/scripts/screenplay.py` (276 lines, 11,515 b, written 2026-07-31T11:21:51Z, never edited) | [EXISTS] | `.film` screenplay → render JSON. Compiled `episode01.film` → 17 scenes / 216 beats / 59 lines / 10.1 min. |
| `Z:/shared/comfy-studio/studio/compile.py` (11,977 b, written 12:33:55Z + one Edit 12:35:12Z) | [PARTIAL] | `.movie` (MOVIE>CHAPTER>SCENE) → render JSON. Implements only 25 flat variables. Not wired to any renderer. |
| `Z:/shared/comfy-studio/scripts/comfy.py` (5,423 b) | [EXISTS] | Minimal ComfyUI HTTP client. `api()`, `set_path(wf,'9.inputs.seed',42)`, `run()`, `submit()`/`wait_all()`. Keys starting `_` are stripped as documentation. |
| `Z:/shared/comfy-studio/scripts/restart-comfy.sh` (1,060 b, never edited) | [EXISTS] | The ONLY observed way ComfyUI gets started. `setsid nohup venv/bin/python main.py --listen 0.0.0.0 --port 8188 --reserve-vram 1.5`. |
| `Z:/shared/comfy-studio/scripts/cue_seconds.py` (3,347 b) | [EXISTS] | Derives music cue lengths from the real timeline. Run AFTER `--stage narrate`, BEFORE `--stage music`. |
| `Z:/shared/comfy-studio/scripts/analyze_shots.py` (5,186 b) | [EXISTS] | Per-shot motion/churn/frozen/DEAD scoring via ffmpeg signalstats. **`shots` schema only** — KeyErrors on any `beats` film. |
| `Z:/shared/comfy-studio/scripts/make_sheets.py` (3,470 b) | [EXISTS] | Character reference sheets → `{COMFY}/input/`. **Not the same file as `studio/make_sheets.py`.** |
| `Z:/shared/comfy-studio/scripts/make_audio_library.py` (14,084 b, last edit 2026-07-30T17:19:21Z) | [PARTIAL] | Reference SFX/music/voice/emotion library. Its own header docstring is STALE — see §4.5. |
| `Z:/shared/comfy-studio/scripts/capcard.py`, `_write_caps.py` (59,483 b) | [EXISTS] | Folder-level capability card declarations + renderer. |
| `Z:/shared/comfy-studio/scripts/gallery.py` | [EXISTS] | Last build 2026-07-31T17:16: 111 folders / 857 items / 19.0 MB `gallery.html`. |
| `Z:/shared/comfy-studio/studio/serve.py` | [EXISTS] | Local web app, port 8777. Endpoints `/`, `/api/library`, `/api/variables`, `/api/cards`, `/api/movies`, `/samples/*`, `POST /api/save`. |
| `Z:/shared/comfy-studio/studio/app.html` | [PARTIAL] | The UI. Last edited 2026-07-31T14:49:21Z — **before** the 198-card expansion. See §4.3. |
| `Z:/shared/comfy-studio/studio/gen_cards.py` | [EXISTS] | Renders every option of every renderable card. Produced 976 panels / 206 card JSONs. |

**Superseded but still on disk:** `cartoon.py` (25,110 b), `film.py` (8,893 b), `pipeline.py`, `mixdown.sh`. None is imported by `epic.py`/`short.py`/`screenplay.py`. [EXISTS]

**Deleted, do not look for them:** `studio/_ingest.py`, `studio/_doc.py`, `studio/_presets.py`, `studio/_finish.py`, `studio/_ingest_cards.py`, `studio/_enums.json`, `studio/_enums_slim.json`, `studio/_wf.js`, `workflows/07_video_upres.json`. [EXISTS as fact of deletion]
> **Consequence:** `studio/roadmap/FINISH-PARTIAL.md`, `studio/variables.json`, `studio/VARIABLES.md` and the 87 preset JSONs are **not regenerable** — every generator that produced them deleted itself in the same `&&` chain that ran it.

### 2.2 Finished films (all rendered, all watchable)

| File | Duration | Res | Shots | Notes |
|---|---|---|---|---|
| `11-short-film/the-hollow-choir_captioned.mp4` | 78.2 s | 1280×704 | **23** (not 25) | Clean A/B control: NO style LoRA, 23/23 correctly bleak |
| `11-short-film/the-last-good-year_captioned.mp4` | 70.4 s | — | **18** (not 20) | |
| `11-short-film/chrono-trigger_captioned.mp4` | 10 m 00.8 s | — | 109 | 96 narration lines, 17 cues. The film all four craft audits dissected |
| `11-short-film/the-hound_captioned.mp4` | 4 m 45.0 s | — | — | |
| `11-short-film/berserk-the-golden-age_captioned.mp4` | 20 m 34.6 s (1234.583333 s) | 1280×704 | 133 | 90 lines, 24 cues, **502,139,782 b**, −18.66 LUFS / −3.44 dBTP. Rendered 3× (15m29.7 → 16m13.2 → 20m34.6). **User rejected it.** |
| `12-shorts/the-clash.mp4` | 33.9 s | 1080×1920 | 73 | |
| `12-shorts/the-derby.mp4` | **62.9 s** (not 55 s) | 1080×1920 | 174 | median cut 0.21 s |
| `12-shorts/the-derby-ep1.mp4` | 526.1 s (8.8 min) | **1920×1080** | 219 | 59 spoken lines, −10.24 LUFS / −0.85 dBTP. No byte size recorded for the delivered 16:9 cut (175,501,381 b was the earlier 1080×1920 vertical). |

### 2.3 Authored film sources

| Path | Status | Note |
|---|---|---|
| `films/build_berserk.py` (52,705 b) + `_p2` + `_p3`, `build_hound.py`, `build_clash.py`, `build_derby.py`, `build_episode.py` | [EXISTS] | **Films are authored in PYTHON.** The `.json` is regenerated on every builder run — hand-edits to the JSON are destroyed. |
| `films/episode01.film` (17,441 b) | [EXISTS] | The human-editable screenplay. Compiles to 216 beats. |
| `films/episode01.json` (159,486 b) | [BROKEN as a reproduction source] | **Contains the 216-beat screenplay output, which OVERWROTE the 180-beat `build_episode.py` output at 2026-07-31T11:22:14Z.** The delivered Ep.1 video was cut from the 180-beat version. To reproduce the shipped film you must re-run `build_episode.py` first. The 216-beat file has **0 captions** and the identical hardcoded motion string in all 216 beats. |
| `studio/movies/derby-ep1.movie` | [PARTIAL] | An **11-beat skeleton** — 3 chapters, 5 scenes, 11 beats, 5 spoken lines. Not the episode. Compiles with two warnings every run. Never rendered. |
| `films/{chrono,berserk,hound,her-name,clash,derby}.json` + 6 cartoon.py-era shorts | [EXISTS] | |

### 2.4 The measured capability layer

- **33 capability folders** under `~/ComfyUI/output/claude-generated/`, declared by `scripts/_write_caps.py`, rendered to `_capability_card.png` by `scripts/capcard.py`. Audit at 2026-07-31T17:16:30: **25 `verified`, 7 `installed-untested` (28-vace, 29-hunyuanvideo, 30-camera-control, 31-character-identity, 32-seedvr2, 33-zimage, 34-flf2v), 1 `not-explored` (27-lora-training)**. [EXISTS]
- `Z:/shared/comfy-studio/CAPABILITIES.md` — the measured-throughput core. Every number wall-clocked on this box 2026-07-29. [EXISTS]
- `~/ComfyUI/output/claude-generated/gallery.html` — 19.0 MB, 111 folders, 857 items. [EXISTS]
- Craft docs: `FILMCRAFT.md` (14,344 b), `FILM-CRAFT-AUDIT.md` (372 lines — **a different document, see §4.7**), `FILMMAKING.md`, `craft/CINEMATOGRAPHY.md` (48,148 b), `craft/SOUND.md` (37,857 b), `craft/EDITING.md` (22,442 b), `craft/STORY.md` (18,373 b), `craft/VOICE.md`, `craft/ANIME_MODELS.md`, `craft/ANIME_EPISODE.md`, plus `PROMPTING.md`, `AUDIO.md`, `LORAS.md`, `NEW-CAPABILITIES.md`, `TEMPLATES.md`, `WORKFLOWS.md`, `MODEL-SHOPPING-LIST.md`, `AI-CONTENT-MAP.md`, `GENERATED.md`. [EXISTS]

### 2.5 Local recovery copies (survive the wedged share)

| Path | Contents |
|---|---|
| `C:\Users\Kashix\.claude\projects\C--Users-Kashix-Documents-CS-Projects\74b2253e-9c14-46fe-a4eb-8c8a9b16f130\tasks\w5qxwi28l.output` | 172,307 b. The **full 461-variable census**, `result.count == 461`. |
| `…\74b2253e-…\subagents\workflows\wf_95ebc01a-55d\journal.jsonl` | 567,271 b. **Second complete copy of the 461 dataset** + the raw per-department proposals the `.output` file lacks. 11 agent files alongside. |
| `…\74b2253e-…\tasks\wajus8avs.output` | 372,748 b. The 198 authored card specs. |
| `…\74b2253e-…\workflows\wf_002e1135-911.json` | The card-authoring run: 198 cards, 126 renderable, 976 panels, 107 review problems (with `variable`/`issue`/`fix`). |
| `…\74b2253e-…\workflows\wf_4fba04bc-2fe.json` | The dead verification run. `{"verdicts":[],"weak":[]}`. |
| `…\74b2253e-…\workflows\scripts\verify-variable-cards-wf_4fba04bc-2fe.js` | The verification workflow script, resumable. |

**If `Z:` never comes back, `variables.json` and `cards_spec.json` can be fully rebuilt from these.** [EXISTS]

---

## 3. What exists but is unverified

### 3.1 The 976 rendered card panels — the largest block of unverified work

- **1,026 PNGs** under `studio/samples/vars/` (976 new + 50 from the original 8 cards) and **206 card JSONs** in `studio/cards/`, confirmed by shell at 2026-07-31T18:05:09Z. [EXISTS]
- **ZERO of the 198 new cards carry a `look_at` or `verdict` field.** The authoring workflow was explicitly forbidden from writing them: *"DO NOT write a `look_at` or `verdict` field. Those are filled in AFTER looking at the actual renders — asserting them up front is how wrong claims ship."* [EXISTS]
- The verification pass that would have filled them from pixels — workflow `verify-variable-cards`, run `wf_4fba04bc-2fe`, 13 agents, launched 2026-07-31T18:05:41Z — **died completely**. All 13 agents returned `"You've hit your weekly limit · resets Aug 2, 7pm"`. `agents_done: 0`, `agents_error: 13`, result `{"verdicts":[],"weak":[]}`. [BROKEN]
- **11 of 13 agents (not 12)** did open panel PNGs before dying, but across all 13 only **109 PNGs of 976 (~11%)** were ever opened, and the observations exist only as unstructured thinking text inside `subagents/workflows/wf_4fba04bc-2fe/agent-*.jsonl`. Nothing was persisted to any card. [PARTIAL]
  - Per-agent PNG-read counts: a67b1fd6 16, aa7d7ab2 14, a970bffb 13, a52bd735 12, a1023298 10, a6d49650 10, a1176732 9, a03a8422 8, a9ef40f8 8, a1928d2c 5, a7ea13c2 4, **a254474a 0**, **a875bf6e 0**.
- **Only 2 cards in the entire system have a pixel-derived verdict**, both from the original 8:
  - `shot_size` → `"works, except extreme_wide"` — and **both predictions were wrong**: `extreme_close` works perfectly (predicted to fail); `extreme_wide` loses the figure from frame entirely (predicted to work).
  - `shot_angle` → `"mixed - high_angle reliable, low_angle and dutch understated"`.
  - The other 6 original cards carry a **predicted** `look_at` written before rendering, and no verdict. [PARTIAL]

**Bottom line: 976 comparison panels sit on disk as pixels nobody has looked at.** The whole point of the card system — knowing which enum values actually change the image — is unrealised.

### 3.2 Contact sheets — attempted, produced nothing observable

- `studio/make_sheets.py` was written 2026-08-02T23:37:02Z (ffmpeg montage, 300×169/panel, 4 cols if >6 panels, option value burned in with drawtext, then stamps `sheet: /samples/sheets/<slug>.png` onto the card JSON). [EXISTS]
- Launched 23:37:26Z as `py studio/make_sheets.py 2>&1 | tail -3 && ls studio/samples/sheets | wc -l`. Exceeded its 600 s timeout at 23:47:30Z and was backgrounded (`bzw4z7ex3`). Its task output file is **0 bytes**. A re-check at 23:51:54Z also timed out (`bx4yfin7c`), whose output file contains exactly `0\n`. A bare `ls` at 2026-08-03T00:14:27Z timed out at 120 s. **Transcript ends there.** [BROKEN / UNVERIFIED]
- **Careful reading:** the 0-byte output proves nothing — `tail` buffers until the process exits. And `ls … | wc -l` printing `0` is equally consistent with *the directory not existing* or *the share being unreachable* as with *the script producing nothing*; that same command then hung for 120 s, which points at the share. **Defensible conclusion: as of ~14 min in, no sheets were visible; no card was ever confirmed to gain a `sheet` key; the background job was never observed to terminate.** Whether sheets exist today is genuinely unknown. [UNVERIFIED]
- **`sheet` is NOT a field of the card schema.** No card JSON was ever confirmed to have one, and `app.html` contains no code that reads one. [NOT BUILT]

### 3.3 Other unverified items

| Item | Why unverified |
|---|---|
| `films/episode01.json` byte content | Its mtime (Jul 31 07:54 local ≈ 11:54Z) is ~32 min AFTER the recorded 11:22Z screenplay compile, with no matching transcript activity. Diff it against a fresh `screenplay.py` run. [UNVERIFIED] |
| 14 of the 38 workflow JSONs | No live `ls` of `workflows/` exists after 2026-07-30T02:12 (which showed 24). The other 14 rest on `Write` tool records alone — strong, but not a directory listing. [UNVERIFIED] |
| `models/latent_upscale_models/hunyuanvideo15_latent_upsampler_1080p.safetensors` | Appears only in a DOWNLOAD PLAN and in a "still missing" note. Never observed in any directory listing. Its manifest siblings did land. [UNVERIFIED / INFERRED] |
| Disk free space | The "450 GB used / 1.4 TB free" figure is from an **assistant thinking block**, not a `df`. The only real `df` (2026-07-29T16:12, pre-download) reads `/dev/nvme0n1p3 1.9T 142G 1.7T 8% /home`. [UNVERIFIED] |
| ComfyUI auto-start behaviour | **Nobody ever ran `systemctl`.** "No systemd unit" was never checked — it is speculation from two thinking blocks that contradict each other. [UNVERIFIED] |
| Machine B (`C:/Users/Kashix/Documents/ComfyUI`, "16 packs, 153 GB, older") | Self-reported in a table headed *"Captured 2026-07-28"* whose own column reads **"older, not audited"**. Never inspected. [UNVERIFIED] |
| Camera-move reliability ranking | The audit agent **explicitly disclaimed it**: *"There is no measured evidence on this box for which move phrasings land — the table in §1 is inferred from shipped prompts, not tested."* [INFERRED, not measured] |

---

## 4. What is authored but does not render

**This section is the reason the project is stuck. Read it before doing anything else.**

### 4.1 THE BIG ONE — `compile.py` never reaches `short.py` [NOT BUILT]

Nothing authored in `studio/` has ever rendered a single frame of video. Stated four times, escalating, never retracted, never fixed:

| Time | Quote |
|---|---|
| 2026-07-31T12:44:34Z | *"compile.py emits the render JSON but I haven't wired it into short.py yet, so the .movie file compiles but doesn't render — that's the next connection to make."* |
| 13:51:12Z | *"**Not yet done:** `compile.py` still only knows the original 25."* |
| 13:58:53Z | *"**Still not wired:** `compile.py` doesn't resolve presets yet … nothing from `studio/` renders yet."* |
| **18:06:02Z** | *"**`compile.py` still doesn't feed `short.py`**, so nothing authored in `studio/` renders a frame of video yet. The library, the cards and the web app are all real, but the wire from authoring to output is missing — and that's arguably worth more than finishing any individual partial."* |

**Size of the gap, concretely.** `compile.py`'s output film dict contains only: `title, fps, canvas, engine, keyframe_engine, anime_ckpt, ipadapter_weight, style, beats`. It emits **no `sheets`, no `anime_sheets`, no `voices`, no `music`**. Therefore a `.movie`-compiled JSON cannot be rendered end-to-end by `short.py` as written:
- `short.py voices()` does `cfg = vo.get(b["line"]["who"], {})` then `set_path(wf, "30.inputs.narrator_voice", cfg["voice"])` → **KeyError** on the first spoken line.
- `short.py anime_keyframe()` reads `film["anime_sheets"][refs[0]]` → falls to IPAdapter weight **0.0** on every beat, i.e. no face lock anywhere.
- No `music` key → no score.

**No render of `studio/movies/derby-ep1.json` appears anywhere in any transcript.** [INFERRED from code, high confidence]

### 4.2 `compile.py` knows 25 variables, not 461, and resolves no presets [PARTIAL]

- Its `VARS` OrderedDict has exactly 25 flat, un-namespaced entries: `title, fps, canvas, checkpoint, face_weight, seed_root, logline, look, mood, tags, negative, place, time, camera, fx, transition, cue, silence, wear, characters, pace, type, captions, lipsync, blocking`. These are a **different naming scheme** from the 461-variable census (`movie.fps`, `world.weather`, `shot.cam.angle`, …). Nothing maps between them.
- The only modification `compile.py` ever received after its initial write is a **dialogue-parser bugfix** at 2026-07-31T12:35:12Z (`k, _, v = line.partition(":")` → `raw_k, _, v = …`), which predates the census by an hour.
- **Correction to a widely-repeated claim:** the 13:51 prose says *"It reads `variables.json` for `--vars`"* — **this is false.** `compile.py --vars` prints from the in-file 25-entry `VARS` OrderedDict and never opens `variables.json`.
- **NOTHING IS ACTUALLY LOCKED.** The "movie level" strings are documentation printed by `--vars`. `resolve()` unconditionally does `for src in (movie["vars"], ch["vars"], sc["vars"]): out[k] = v` for every key including `fps` and `canvas`. The **only** `SystemExit` in the file is for an unknown library preset name. Setting `fps` on a scene raises no error — it is silently ignored, because film-level fps is read from `movie["vars"]` alone. [BROKEN — documented behaviour ≠ implemented behaviour]
- The schema text *"fps: LOCK, compile error if set at chapter/scene/shot"* plus a compile-time VRAM warning is a **design proposal produced at 12:30:48Z, three minutes BEFORE `compile.py` was written**, and was never implemented. [NOT BUILT]
- Only three warnings are ever emitted: `transition` with `status=="roadmap"`, `camera` with `status=="roadmap"`, and truthy `lipsync`. `blocking` and audio-picture-offset have roadmap files but produce **no warning at all**, violating the file's own stated principle *"NOTHING SILENTLY DOES NOTHING."* [PARTIAL]

### 4.3 The web app renders the new cards wrong [BROKEN]

`app.html`'s card tab (`drawCardTab()`, last edited **2026-07-31T14:49:21Z**) was written for the Gen-1 8-card shape and never updated for the 198 Gen-2 cards that landed at 17:11. It does:
```
<p class="lookat"><b>What to notice:</b> ${c.look_at}</p>
```
unconditionally. The 198 new cards **have no `look_at` key**, so the tab will print the literal string `undefined` for every one of them. It also has no branch for `not_visual`, `panels: []`, `control`, `review[]`, or `sheet`. The 72 non-visual cards will render an empty strip with no explanation. [BROKEN — code read, never visually verified: the browser check timed out because the Browser pane was hidden]

### 4.4 `epic.py`'s master chain ships a known-bad limiter [BROKEN]

The last edit `epic.py` ever received (2026-07-30T22:52:21Z, matching its final mtime) changed `alimiter=limit=0.891` → `limit=0.708`, with the comment *"alimiter caps SAMPLE peak, not TRUE peak … a 20-minute mix measured +0.48 dBTP with limit=0.891."*

**0.708 was ALSO measured insufficient** — the full film came back at **+1.03 dBTP**. The delivered Berserk master was **not** produced by `epic.py edit()` at all, but by a one-off heredoc: `loudnorm I=-17:TP=-3.0` + `aresample=192000` + `alimiter=limit=0.63` + `volume=-1.5dB` → −18.66 LUFS / −3.44 dBTP. **That 192 kHz oversampling exists only in `short.py`'s `slam()` and was never folded back into `epic.py`.** Anyone re-running `epic.py --stage edit` today gets the still-broken 0.708 chain.

### 4.5 Stale documentation that will actively mislead [BROKEN]

| Doc | Stale claim | Reality |
|---|---|---|
| `README.md` | *"Custom nodes: ComfyUI-Manager only — everything else is stock"* | Four packs: ComfyUI-Manager, ComfyUI-Chatterbox, TTS-Audio-Suite, ComfyUI_IPAdapter_plus (observed 2026-07-31T04:39) |
| `_write_caps.py` card `10-voice` | *"IndexTTS 2 — not installed"* | In production since 2026-07-30. `16_indextts2_voice.json` + `17_higgs_v3_voice.json` exist; `higgs_v3` is the default engine |
| `_write_caps.py` card `31-character-identity` | *"The whole face-embedding family (IPAdapter/PuLID/InstantID) is absent"* | IPAdapter installed 2026-07-31T04:33, **hours before that card was written at 17:11** |
| `make_audio_library.py` header docstring | *"ACE-Step v1 3.5B, 60 steps, cfg 5"* | `music()` was **REVERTED** at 2026-07-30T17:19:21Z to `06_acestep_music.json`, 20 steps, **cfg 1.0** — *"This is the ORIGINAL setting, and it beat every improvement I tried"*; cfg 1.0 is correct for a DISTILLED turbo model. The SFX half (100 steps / cfg 7 / dpmpp_3m_sde) does stand. |
| `CAPABILITIES.md` | LTX ambience "−35 dBFS" | Measured spread across 91 clips is **39 dB** (−51.2 to −12.2); only 16 of 91 are at or below −35 |
| `_doc.py` `ORDER` constant | includes `"weather"` | There is **no `weather.*` namespace**; it is a dead entry filtered out at render |

### 4.6 Camera vocabulary: written, never rendered [PARTIAL]

The "every clip pans left" bug was real — `punch` was the only implemented camera move, hardcoded to drift one direction, and 4 of 7 episode templates called it. The fix (2026-07-31T11:22:34Z) added `push/pull/pan_l/pan_r/tilt_u/tilt_d/handheld` to `fx_chain()` plus a per-beat `camera` override in `cut()` that strips template move-fx and substitutes the authored one.

**But no frame has ever been produced with it.** No `short.py` invocation exists after 11:22:34Z in any transcript. And the reported *"216/216 beats carry an explicit camera"* is misleading: **every one of those 216 cameras is `static`** — the `.film` round-trip could not recover camera intent from the old JSON and defaulted everything. `episode01.json` therefore has **no camera move at all**, not varied ones. [PARTIAL — mechanism wired, zero directing decisions made, zero verification]

### 4.7 Five installed capabilities that no code can reach [NOT BUILT]

From `Z:/shared/comfy-studio/FILM-CRAFT-AUDIT.md` (372 lines, written 2026-07-30T02:21:52Z — **a separate document from `FILMCRAFT.md`, indexed by nothing, easy to miss**). Its headline finding: **"Five capabilities are installed and unreachable from the kit"** — weights on disk, nodes live, and **no workflow or script references any of them**:

| Weight | On disk | Referenced by |
|---|---|---|
| `ltx-2.3-id-lora-talkvid-3k` | yes | nothing |
| `ltx-2.3-22b-ic-lora-union-control-ref0.5` | yes | nothing |
| `sdpose_wholebody_fp16` | yes | `27_control_maps.json` only |
| `depth_anything_3_mono_large` | yes | `27_control_maps.json` only |
| `moge_2_vitl_normal_fp16` | yes | `27_control_maps.json` only |

Its ranked #1 action item is **a grade stage** — *"grep proves no script does any colour work."* [NOT BUILT]

### 4.8 Everything else in this class

| Item | Status |
|---|---|
| L-cuts / J-cuts (audio-picture offset) | [NOT BUILT] — *"the loudest tell of an amateur edit, and we do it on every single transition."* Costed at **~20 lines**. |
| The 33 audio/dialogue/caption cards ("a different kind of card") | [NOT BUILT] — never designed. Note they are **not** all `audio.*`; the classifier bucketed by four prefixes (`audio` 18, `dialogue` 10, `caption` 5). |
| `shot.keyframe_mode` (`start_only`/`start_end`/`start_mid_end`) | [NOT BUILT] — no renderer has a first-last-frame or interpolation path. (Census status is `partial`, not `roadmap`; its card is `renderable: false` only because *a still cannot demonstrate it*.) |
| 155 partial variables + 41 partial presets | [NOT BUILT] — deferred twice, the second time flagged: *"this is the second time I've deferred it."* |
| Preset → census-variable resolver | [NOT BUILT] — preset field `wind` ≠ `world.wind_speed`; `bg_value` ≠ `layer.bg.value`. **No mapping table exists anywhere.** |
| `studio/places/`, `studio/characters/`, `studio/cues/` | [NOT BUILT] — directories created, left empty, so `/api/library` shows 10 groups not the 13 `serve.py` declares |
| `workflows/32_train_character_lora`, `33_ltx_ic_control`, `34_ltx_id_lora`, `35_seedvr2_upscale`, `36_zimage_turbo` | [NOT BUILT] — these are **explicit TODOs** in `_write_caps.py`'s `next_steps` blocks beside `"workflow": "not built yet"`. They are not files. |
| `24_color_match`, `25_flux2_t2i`, `24_wan22_flf2v`, `24_ltx23_ic_control`, `24_ltx_id_lora`, `25/26_ltx23_flf2v` | [NOT BUILT] — subagent *recommendations* in ranked tables, 2026-07-30. Only `26_flux2_t2i.json` shipped. |
| LoRA training, Wan 2.1 VACE, HunyuanVideo 1.5, SeedVR2, Z-Image Turbo, FLF2V | [NOT BUILT] — weights on disk, zero measured timings, zero workflows |

---

## 5. The variable model

### 5.1 Where it lives

| Path | Status |
|---|---|
| `Z:/shared/comfy-studio/studio/variables.json` | [EXISTS] **CANONICAL.** 461 records, `json.dumps(out, indent=1, ensure_ascii=False)`. Written 2026-07-31T13:49:47Z by `studio/_ingest.py`, which then deleted itself. **Never regenerated after 13:49.** |
| `Z:/shared/comfy-studio/studio/VARIABLES.md` | [EXISTS] Human-readable, generated by `studio/_doc.py` (self-deleted 13:50:48Z). Badges `OK` / `~` / `TODO`. |
| `Z:/shared/comfy-studio/studio/roadmap/VARIABLES-TODO.md` | [EXISTS] 26 roadmap entries with fallbacks, plus an index of the other roadmap docs. **This is the roadmap folder's own table of contents.** |
| `Z:/shared/comfy-studio/studio/roadmap/FINISH-PARTIAL.md` | [EXISTS] 155 partial variables + 41 partial presets. Generated by `studio/_finish.py` (self-deleted 14:25:05Z). **Not regenerable.** |
| `http://localhost:8777/api/variables` | [EXISTS] Serves all 461. Verified live 2026-07-31T14:29:49Z. |

### 5.2 Hierarchy and inheritance

```
MOVIE      one film. Locks fps, canvas, checkpoint (BY CONVENTION ONLY - see 4.2)
 +- CHAPTER   an act. Sets mood, look and score for everything inside it.
     +- SCENE   a unit of story in one place. Most work happens here.
         +- SHOT    a single image.
```

- `resolve()`: **scene <- chapter <- movie. Tags APPEND down the tree; everything else OVERRIDES.** The asymmetry is deliberate: *"If tags overrode, one scene tag would silently wipe the whole film's art direction - the classic inheritance footgun."* [EXISTS]
- `wear` uses `max(movie, ch, sc)` - damage continuity never decreases. [EXISTS]
- **`block` is a NAMESPACE (character blocking), not a level.** **`beat` is not a level either** - `story.beat` is a scene-level variable, and in `compile.py`'s parser `shot:` and `beat:` are interchangeable keys for a shot line inside a SCENE. Recognised block headers are only `MOVIE` / `CHAPTER` / `SCENE`. [EXISTS]

### 5.3 The five `level` values (461 total)

| level | count | meaning |
|---|---|---|
| `shot` | 180 | |
| `any` | 157 | settable at any level |
| `scene` | 69 | |
| `movie` | 41 | locked for the whole film (by convention only) |
| `chapter` | 14 | |

### 5.4 Per-variable metadata - exactly seven fields

`_ingest.py`: `out.append({k: v.get(k, "") for k in ("name","level","type","default","why","status","fallback")})`

| field | notes |
|---|---|
| `name` | dotted, e.g. `shot.cam.angle` |
| `level` | one of the five above |
| `type` | **free STRING, not structured.** Forms: `enum: a \| b \| c`, `list of enum: ...`, `enum or string: ...`, `number 0.0-1.0`, `number (seconds)`, `string (char.id)`, `list of tags`, `bool`, `list of [x, y]`. **233 of 461 contain the substring `enum`.** |
| `default` | |
| `why` | one sentence, the design rationale |
| `status` | **three-valued enum**: `ready` 280 / `partial` 155 / `roadmap` 26 |
| `fallback` | non-empty on **all 181** partial+roadmap variables; `""` on every ready one |

**There is NO `renderable` field on a variable.** `renderable` belongs to the capability-card spec. [EXISTS]

### 5.5 The 16 namespaces (not 13)

| ns | total | direct | sub-namespaces | partial |
|---|---|---|---|---|
| `shot` | 80 | 24 | cam 18, comp 14, lens 9, focus 7, fx 5, frame 3 | 34 |
| `anime` | 67 | 0 | anim 15, fx 11, draw 10, color 9, format 8, bg 7, perf 7 | 38 |
| `audio` | 52 | 0 | music 21, mix 12, sfx 10, amb 6, vo 3 | 13 |
| `char` | 39 | 34 | wear 5 | 8 |
| `world` | 27 | 27 | flat - **ALL weather lives here** | 5 |
| `dialogue` | 24 | 4 | line 16, voice 4 | 6 |
| `light` | 23 | 23 | flat | 8 |
| `grade` | 22 | 22 | flat | 5 |
| `story` | 21 | 21 | flat | 4 |
| `time` | 21 | 21 | flat | 7 |
| `render` | 18 | 18 | flat | 2 |
| `movie` | 17 | 17 | flat | 5 |
| `layer` | 17 | 6 | bg 5, fg 4, mid 2 | 8 |
| `caption` | 13 | 13 | flat | 3 |
| `edit` | 12 | 12 | flat | 3 |
| `block` | 8 | 8 | flat | 6 |
| | **461** | | | **155** |

**There is NO top-level `weather.*` namespace.** Weather is `world.weather`, `world.weather_intensity`, `world.wind_speed`, `world.wind_dir`, `world.cloud_cover`, `world.fog_density`, `world.precip_render`, `world.ground_state`, `world.sky_state`, `world.air_particles`. **There is NO `music.*` namespace** - it is `audio.music.*` (21 variables, the largest sub-namespace), including the user's explicitly-requested `audio.music.transition` and `audio.music.transition_at`. [EXISTS]

**NAME COLLISION [BROKEN]:** `shot.fx` is BOTH a leaf variable (`list of enum: punch | shake | aberr | glow | flash | hot | ramp | smea...`) AND a branch prefix (`shot.fx.bg_treatment`, `.emote_symbols`, `.impact_frame`, `.screentone`, `.speed_lines`). Separately `shot.fx_at_pct` and `shot.fx_intensity` use an underscore. **Any code doing prefix-based namespace grouping will mis-handle this.**

### 5.6 Movie-level variables (41 - locked for the whole film)

`movie.title` `movie.logline` `movie.fps` `movie.canvas` `movie.aspect` `movie.seed_root` `movie.tag_style` `movie.prompt_budget` `movie.language` `movie.rating` `movie.credits` `movie.lint` `movie.runtime_target_s` - `story.genre` `story.structure` `story.type` `story.theme_tags` - `time.max_shot_s` `time.min_shot_s` - `world.era` - `caption.font` `caption.style` `caption.size_pct` `caption.max_chars` `caption.max_lines` `caption.reading_speed` - `audio.mix.dynamics` `audio.mix.target_lufs` `audio.mix.true_peak_db` - `render.codec` `render.bitrate` `render.color_space` `render.order` `render.proxy_mode` `render.version_tag` `render.watermark` - `anime.format.episode_no` `anime.format.broadcast_safe` `anime.color.script` `anime.color.motif_map` - `shot.frame.caption_safe`

### 5.7 Chapter-level variables (14)

`story.chapter_role` `story.tonality_curve` `edit.chapter_transition` `time.chapter_s` `char.arc_stage` `audio.mix.fade_in_s` `audio.mix.fade_out_s` `anime.anim.motion_budget` `anime.format.sequence_role` `anime.format.op_style` `anime.format.ed_style` `anime.format.eyecatch` `anime.format.eyecatch_style` `anime.format.next_preview`

### 5.8 The preset layer (the answer to "there are too many variables")

User, 2026-07-31T13:55:41Z: *"there are too many variables. can we group them into categories, for example all variables involving weather goes into just weather, but it can be expanded for more detail."*

The fix is **two tiers, not a renaming**: `studio/<category>/<preset>.json`, each a named bundle expanding into detail fields, every individual field still overridable. *"So the 461 didn't go away - VARIABLES.md stays as the reference, and every preset is just a named bundle of those fields. Three depths available: pick a word, override one field, or set raw variables."*

**10 populated categories / 87 presets** (API-verified `/api/library`: `groups: 10  presets: 87`):

| folder | n | `.movie` key | status | samples |
|---|---|---|---|---|
| `shots/` | 9 | `shot` | ready | 9 PNG |
| `cameras/` | 11 | `camera` | 8 ready + dolly_zoom/rack_focus/orbit roadmap | 8 MP4 |
| `transitions/` | 12 | `transition` | 9 ready + match_cut needs_authoring + l_cut/j_cut roadmap | 9 MP4 |
| `looks/` | 7 | `look` | ready | 7 PNG |
| `lighting/` | 8 | `lighting` | **partial** | 0 |
| `layers/` | 7 | `layers` | **partial** | 0 |
| `weather/` | 9 | `weather` | **partial** | 0 |
| `emotions/` | 9 | `emotion` | **partial** | 0 |
| `soundscapes/` | 8 | `sound` | **partial** | 0 |
| `pacing/` | 7 | `pace` | ready | 7 MP4 |
| `places/` `characters/` `cues/` | 0 | `place` `characters` `cue` | EMPTY dirs, never appear in the API | - |

- **"12 categories, 97 presets" is an OVERCOUNT** from a shell loop that counted `studio/movies/` (2 files) and `studio/roadmap/` (8 files) as preset folders. [BROKEN claim]
- **40 of 40 ready presets have a sample.** Partial presets deliberately show `"unfinished - see roadmap/FINISH-PARTIAL.md"` instead of a thumbnail: *"a preset that looks finished but is not is worse than one plainly marked unfinished."* [EXISTS]
- **41 partial presets** = weather 9 + emotions 9 + soundscapes 8 + lighting 8 + layers 7. [INFERRED - count verified against the generator's own output, names not individually enumerated in any transcript]
- Example preset, `studio/weather/rain.json`:

```json
{ "id": "rain", "desc": "weather preset: rain", "status": "partial",
  "note": "tags and atmospherics render today; wind and per-particle motion are prompt-only.",
  "tags": "rain, wet ground, reflections", "intensity": 0.6, "wind": 0.4,
  "precip": "rain", "atmos": "mist", "visibility": 0.7, "ground": "wet" }
```

- Expansion field sets per category: weather `tags,intensity,wind,precip,atmos,visibility,ground` - emotions `face,eyes,mouth,body,voice_style,voice_rate` - soundscapes `desc,ambience,bed_level,music_level,duck,reverb` - layers `count,fg,fg_blur,fg_coverage,bg_blur,bg_value,character_plane` - lighting `key,ratio,direction,quality,temp,rim` - pacing `desc,scale,rhythm,hold_bias`.
- **PRESET FIELDS DO NOT MAP TO CENSUS VARIABLES [BROKEN].** `wind` != `world.wind_speed`. `ground` != `world.ground_state`. `bg_value` != `layer.bg.value`. **No resolver bridges them and no mapping table exists anywhere on disk.**

### 5.9 The count-disambiguation table (numbers that are easy to conflate)

| n | what it is | source |
|---|---|---|
| 461 | total variables in `variables.json` | 13:49:47Z |
| 16 | top-level namespaces | 13:49:47Z |
| 280 / 155 / 26 | ready / partial / roadmap | 13:49:47Z |
| 181 | variables with a non-empty `fallback` (= 155+26) | derived |
| **233** | variables whose `type` contains `enum` - **the TRUE number** | derived |
| ~~239~~ | *"enum variables total"* as PRINTED - **an ARTIFACT.** `len(enums)+len(done)` double-counts 6 names. Only 2 of the 8 "done" card labels (`shot.size`, `char.emotion`) exist as census variables | 16:53:49Z [BROKEN] |
| 8 | already-carded, the Gen-1 `CARDS_SPEC` entries | 14:50:46Z |
| 198 | visual enum variables needing a card | 16:53:49Z |
| 33 | enum vars bucketed by name prefix `audio`/`music`/`dialogue`/`caption` -> **audio 18, dialogue 10, caption 5**. NOT all `audio.*` | 16:53:49Z |
| 198 | cards AUTHORED | 17:11:24Z |
| 126 / 72 | renderable:true / renderable:false-with-skip_reason | 17:11:24Z |
| 976 | option panels implied by the 126 | 17:11:24Z |
| 107 / 91 | review problems / cards flagged | 17:11:55Z |
| 206 | card JSONs on disk (198 + 8, **zero slug collisions**) | 18:05:09Z |
| 1026 | PNGs on disk (976 + 50) | 18:05:09Z |
| 87 | presets in 10 populated categories (API) | 14:14:48Z |
| ~~97~~ | *"presets"* in *"12 categories"* - **OVERCOUNT** | 13:58:53Z [BROKEN] |
| 40 | ready presets, all 40 with a sample | 14:29:49Z |
| 155 / 41 | partial CENSUS VARIABLES / partial PRESET FILES - **two different populations, do not conflate** | 14:27:07Z |
| **25** | variables `compile.py` actually implements | 12:33:55Z |

### 5.10 The 26 roadmap variables

`layer.depth_map` `layer.parallax_strength` `layer.sky_plane` `layer.bg.motion` `layer.mode` - `shot.focus.behavior` `shot.focus.rack_at_pct` `shot.comp.axis_line` `shot.lens.distortion` `shot.lens.bokeh_shape` `shot.lens.vignette` `shot.lens.breathing` `shot.cam.shutter_angle` `shot.cam.motion_blur` `shot.cam.rolling_shutter` - `grade.match_ref` `grade.scope` - `time.beat_grid` `time.sync_to_music` - `anime.anim.partial` `anime.anim.smear_style` `anime.anim.smear_frames` `anime.anim.cg_mix` `anime.color.count` - `audio.music.key` `audio.music.build_s`

Each carries an explicit fallback, e.g. `layer.depth_map` -> *"Not generated; all depth effects fall back to tags."* [EXISTS]

---

## 6. The card model

### 6.1 Provenance

The variable-card idea was copied directly from the **folder-level `CAPABILITY.json` cards** in `Z:/ComfyUI/output/claude-generated/*` (v1 schema: `title, claim, look_at, model, cost, workflow, verdict, panels[{file,label,note}]`; v2 added `status, updated, released, vram, limits[], strong[], weak[], alternatives[], next_steps[]` and panel `crop`/`frames`). The user asked for the same treatment per-variable at 2026-07-31T14:42. [EXISTS]

### 6.2 Two generations, no collisions

| | Gen 1 (14:44-14:51) | Gen 2 (16:53-18:05) |
|---|---|---|
| Driver | `studio/make_cards.py`, hardcoded 8-entry `CARDS_SPEC` | workflow `author-variable-cards` run `wf_002e1135-911` (18 agents, 754,929 ms, 891,626 subagent tokens) -> `studio/cards_spec.json` -> `studio/gen_cards.py` |
| Cards | 8 | 198 |
| Panels | 50 | 976 |
| Shape | `{variable, claim, look_at, method, model, panels[{value, clause, sample}]}` | see 6.3 |
| Verdicts | 2 real, 6 predicted | **0** |

Gen-1 slugs: `char_emotion` 9 panels, `char_gaze` 5, `light_direction` 5, `shot_angle` 6, `shot_focus` 4, `shot_size` 7, `time_of_day` 6, `weather_type` 8. **198 + 8 = 206 exactly, zero slug overlap** - `gen_cards.py` did not overwrite the two verified Gen-1 cards. [EXISTS]

The authoring workflow had to be launched **three times**: run 1 (`wf_fa53c3ba-be9`, 16:54) failed with empty `args`; run 2 (`wf_bbd80fd5-93d`, 16:57) hit a half-patched script; run 3 (`wf_002e1135-911`, 16:58) succeeded. [EXISTS]

Authoring schema (workflow SCHEMA, required `variable, claim, renderable, options`):
`{variable: string, claim: string, renderable: boolean, skip_reason: string, options: [{value: string, clause: string}]}`
Field census over the 198 results: `variable` 198, `claim` 198, `renderable` 198, `options` 198, `skip_reason` 72. Over all 1,441 options: `value` 1441, `clause` 1441 - **options only ever have those two keys.** [EXISTS]

### 6.3 On-disk schema

Slug = variable name with `.` -> `_`. Path: `Z:/shared/comfy-studio/studio/cards/<slug>.json`.

**RENDERABLE card:**

```json
{
  "variable": "shot.cam.angle",
  "claim":    "<1-2 sentences: what it controls and why a director reaches for it>",
  "method":   "identical subject sentence and seed in every panel; only the option clause changes. panels marked control render the untouched subject, because SDXL cannot express absence.",
  "model":    "animagine-xl-4.0, 28 steps, cfg 5.0, euler_ancestral",
  "panels": [ {"value": "...", "clause": "...", "control": false, "sample": "/samples/vars/<slug>/<value>.png"} ],
  "review":  [ {"variable": "...", "issue": "...", "fix": "..."} ]
}
```

**NON-RENDERABLE card (72 of them)** - note `skip_reason` is RENAMED to `not_visual` at write time:

```json
{ "variable": "shot.priority", "claim": "...",
  "not_visual": "Pure scheduling and budget metadata. It changes render allocation and trim order, never a pixel of the image, so four identical panels is the honest result.",
  "options": ["filler","normal","important","critical"], "panels": [] }
```

**`look_at` and `verdict` are absent from all 198 by design. `sheet` does not exist on any card.** [EXISTS]

### 6.4 Full literal example

`Z:/shared/comfy-studio/studio/cards/shot_cam_angle.json` - reconstructed by replaying `gen_cards.py`'s writer over the authored spec; claim/clauses/review text verbatim from `wf_002e1135-911.json`:

```json
{
  "variable": "shot.cam.angle",
  "claim": "Angle is the classic dominance lever: the tilt of the lens relative to the subject. Low makes a figure monumental, high makes them small and observed, and dutch says the world itself is off its axis.",
  "method": "identical subject sentence and seed in every panel; only the option clause changes. panels marked control render the untouched subject, because SDXL cannot express absence.",
  "model": "animagine-xl-4.0, 28 steps, cfg 5.0, euler_ancestral",
  "panels": [
    {"value":"level","clause":"straight-on, eye level, level horizon","control":false,"sample":"/samples/vars/shot_cam_angle/level.png"},
    {"value":"low","clause":"from below, low angle","control":false,"sample":"/samples/vars/shot_cam_angle/low.png"},
    {"value":"high","clause":"from above, high angle","control":false,"sample":"/samples/vars/shot_cam_angle/high.png"},
    {"value":"birds_eye","clause":"bird's-eye view, from far above","control":false,"sample":"/samples/vars/shot_cam_angle/birds_eye.png"},
    {"value":"worms_eye","clause":"worm's-eye view, extreme low angle, from below","control":false,"sample":"/samples/vars/shot_cam_angle/worms_eye.png"},
    {"value":"top_down","clause":"top-down view, from directly above","control":false,"sample":"/samples/vars/shot_cam_angle/top_down.png"},
    {"value":"dutch","clause":"dutch angle, tilted horizon","control":false,"sample":"/samples/vars/shot_cam_angle/dutch.png"}
  ],
  "review": [{
    "variable": "shot.cam.angle",
    "issue": "birds_eye and top_down are the same instruction in two phrasings and will render as one picture; both also duplicate cam.height.overhead/aerial. worms_eye differs from low only by intensifiers the model largely ignores.",
    "fix": "Keep level / low / high / dutch as the load-bearing four plus one overhead extreme, and delete the twin. Assign overhead ownership to exactly one card (angle or height, not both)."
  }]
}
```

> One of the 11 agents that did open PNGs recorded the OPPOSITE of that reviewer claim - *"I initially thought birds_eye and top_down might be the same, but looking at the actual images, they're distinct"* - and that observation was never persisted anywhere. This is exactly what section 3.1 costs you.

Second literal example, one of the 58 negation-rule matches (`Z:/shared/comfy-studio/studio/cards/shot_lens_flare.json`): the `none` panel has `"clause": "no lens flare, clean image"` PRESERVED in the JSON for the record, `"control": true`, and `none.png` is the **untouched subject** because `gen_cards.py` sent an empty clause to the sampler.

### 6.5 Panel pipeline

```
studio/cards_spec.json   198 specs {variable, claim, renderable, skip_reason?, options[{value,clause}], review[]}
  |
  v   gen_cards.py::clean(card, opt)        <-- the ONLY place review fixes were applied
prompt = SUBJ [+ clause] + Q ;  NEG fixed
  |
  v   ComfyUI 192.168.1.46:8188   COMFY_ROOT=Z:/ComfyUI
      animagine-xl-4.0.safetensors | EmptyLatentImage 1344x768 | 28 steps | cfg 5.0
      euler_ancestral / normal | denoise 1.0 | SEED = 9001 FIXED for every panel of every card
  |
  v   SaveImage -> claude-generated/studio_cards/<slug>__<val>_00001_.png
      ensure_local() pulls it over the ComfyUI HTTP /view endpoint (never trust the SMB share)
      ffmpeg -vf scale=640:360 -> studio/samples/vars/<slug>/<val>.png
  |
  v   card JSON -> studio/cards/<slug>.json
```

- `val = re.sub(r"[^a-z0-9_]+", "_", str(opt["value"]).lower())`
- **Fixed subject sentence, identical in EVERY panel of EVERY card:**
  `1boy, solo, male focus, dark red hair, undercut, yellow eyes, black soccer jersey, number 9, soccer stadium, floodlights, crowd`
- `Q = "masterpiece, best quality, very aesthetic, absurdres"`
- `NEG = "1girl, female, lowres, worst quality, bad anatomy, bad hands, watermark, text, multiple views, photorealistic, 3d, western comic, blurry"`
- Render cost: 976 panels in ~52 min GPU. CLI: `gen_cards.py [--only <namespace>] [--dry]`; skips any panel whose PNG already exists. [EXISTS]

### 6.6 Known problem classes

**The systemic one - SDXL has no negation in a positive prompt.** A `none` option whose clause reads `"no lens flare"` **ADDS** lens flare; the model sees the tokens, not the "no". Fix in `gen_cards.py::clean()`:

```python
NULLS = {"none","off","no","false","disabled","flat","neutral","static","straight"}
if val in NULLS or re.match(r"^(no|without)[\s_]", clause.lower()):
    clause = ""          # renders the untouched subject as a labelled control
```

**The numbers, corrected.** The transcript reports *"58 of 976 panels become CONTROL renders"* - but that counter never checks whether the clause was already empty. True decomposition of the **77 panels** carrying `control: true` on disk:

| | n | effect |
|---|---|---|
| already had an empty clause from the authoring agents | 42 | **no change** (23 of these also have value-in-NULLS and are double-counted inside the reported 58) |
| value in `NULLS` **with** a non-empty clause -> blanked | 31 | real change |
| clause matched `^(no\|without)[\s_]` -> blanked | 4 | real change |
| **total `control: true` on disk** | **77** | of which only **35 panels actually had a clause removed** |

So `58 + 19 = 77` is arithmetic coincidence, not a decomposition. Examples of already-empty-clause `none` options: `anime.anim.smear_style`, `anime.fx.aura`, `world.precip_render`. [BROKEN as previously stated / corrected here]

**The negation regex over-fires [BROKEN].** `no humans` is a genuine danbooru tag. `shot.framing_type` options `insert_object` (`"no humans, object focus, close-up"`) and `empty_frame` (`"no humans, empty, scenery only"`) were blanked to control panels, so **those two panels render the ordinary boy instead of an empty frame.** They need re-rendering. [INFERRED from replaying the rule - verify the two PNGs on the box]

**Second fix - people-count cards.** `SUBJ_NOSOLO = SUBJ.replace("1boy, solo, ", "")` is substituted when `re.search(r"\d\s*boys|multiple|group|crowd|two_shot|three_shot|over_shoulder", val + " " + clause)` matches. (The trailing `.replace("male focus, ", "male focus, ")` in that line is a no-op.) [EXISTS]

**Everything else was NOT fixed.** `gen_cards.py`'s docstring lists exactly **TWO** "FIXES APPLIED TO THE AUTHORED SPECS, from the review pass" - negation, and clauses fighting the fixed subject. Writing a card for non-renderable variables was part of `gen_cards.py`'s design, not a review response. **No option clause was ever edited.** The remaining ~100 problems were attached as a `review[]` array and shipped as-is:

- options that would render identically (`birds_eye` vs `top_down`; `circular` vs `oval` anamorphic)
- prose / camera-department jargon instead of danbooru tags - `light.ratio`: *"The clauses are camera-department jargon rather than tags"*
- clauses contradicting the fixed subject - `block.*`: *"Every clause opens with \"2boys\" or \"multiple boys\", which directly contradicts \"1boy, solo, male focus\""*
- cross-card duplicate options (`fisheye` appears on three cards)
- **19 problems saying the `renderable` flag is wrong or a per-option skip is needed - NOT acted on**
- 4 enum values not matching the type string
- three byte-identical baselines inside one renderable card (`registration_jitter`, `telecine_wobble`, `gate_weave` all carry empty clauses)

> **Do not trust any finer-grained breakdown of the 107.** Only two of the six previously-circulated category counts reproduce (renderable-flag **19**, enum-mismatch **4**); the others vary by up to 40% depending on regex choice. Treat category counts as one analyst's soft classification. [UNVERIFIABLE]

**12 orphaned review problems** have compound `variable` strings (e.g. `"light.rim.none, light.fill.none, ..."`, `"light.motivation vs light.practicals"`) that matched no card. They are attached to nothing and are invisible in the app. 95 problems attached across 91 cards, all renderable. [PARTIAL]

**Namespace breakdown of the 126 renderable cards:** shot 30, anime 28, world 18, char 13, light 13, story 7, block 7, layer 4, grade 4, movie 2. **`render`, `edit` and `time` produced ZERO renderable cards** (all 20 non-visual). Authored totals were shot 45, anime 44, world 19, story 15, char 15, light 14, render 9, movie 7, layer 7, block 7, edit 6, time 5, grade 5. [EXISTS]

**Workflow sharding:** 13 namespace prefixes - `['shot','anime','world','story','char','light','render','movie','layer','block','edit','time','grade']`. No `weather` prefix, because `weather.type` was in the already-carded 8. [EXISTS]

### 6.7 The verification workflow (resumable, but a full re-run)

`.../74b2253e-.../workflows/scripts/verify-variable-cards-wf_4fba04bc-2fe.js` [EXISTS]

Intended output per card: `{slug, look_at, verdict, broken_options[]}`, sharded over 13 slug prefixes `['shot_cam','shot_lens','shot_comp','shot_','anime_','world_','char_','light_','story_','block_','layer_','grade_','movie_']`. Agent instruction: *"OPEN EVERY PNG in the directory and compare them. Use the Read tool on the image paths. ... Do not infer from the option names or the clauses. Two earlier predictions were both WRONG when checked against pixels. Predicting is worse than useless here."* It also correctly warns: *"A control panel looking like the plain subject is CORRECT, not a failure."*

**All 13 agents errored, so nothing replays from cache - resuming is a full re-run.** Given only 109 of 976 PNGs were opened before the limit hit, **contact sheets plus direct Reads is the cheaper path.** [PLANNED_NOT_BUILT]

---

## 7. The render pipeline

**There are TWO renderers and they consume DIFFERENT film JSON schemas.** `epic.py` reads a top-level `shots` array; `short.py` reads a top-level `beats` array. Nothing converts between them, and `analyze_shots.py` only understands `shots`.

### 7.1 PATH A - `short.py`, the current path

```
1. AUTHOR
   films/build_derby.py | films/build_episode.py          (python builder -> json.dump)
   scripts/screenplay.py <name>.film                      (.film -> .json)
   studio/compile.py <name>.movie                         (.movie -> .json)   <-- DEAD END, see 4.1
        -> films/<name>.json  with a top-level `beats` array

2. SHEETS   scripts/make_sheets.py films/<name>.json -> {COMFY}/input/sheet_*.png
            (the ANIME sheets were made by ad-hoc Bash heredocs; NO committed script regenerates them)

3. KEYFRAMES  short.py keyframes()
      if film.keyframe_engine == "anime":  anime_keyframe() -> 22_anime_kf_ipadapter.json
          node1 ckpt | node2 = film.anime_sheets[refs[0]] | node4 weight = film.ipadapter_weight
          (0.0 when the beat has no `ref`) | node5 = beat.tags | node8 seed
          node7 latent 1344x768 | node10 ImageScale -> KF 1664x928
      elif beat.ref:  14_qwen_edit_ref.json     (sheets on nodes 8/9/16 -> encoders 10, 11)
      else:           13_qwen_t2i_styled.json
      -> keyframes/<id>_00001_.png

4. CLIPS      short.py clips()
      secs   = float(b.get("clip_secs", 4))
      length = max(9, ceil(secs*FPS/8)*8 + 1)          # LTX 8n+1 rule
      12_ltx23_i2v_audio.json:  node8 image | node10 motion text
                                node20 w/h/length | node21 frames_number
                                node32 noise_seed | node43 filename_prefix
      ALL clips submit()ed as ONE batch, then wait_all()
      -> clips/<id>_00001_.mp4   (video with natively synced audio)

5. VOICES     17_higgs_v3_voice.json (default) or 16_indextts2_voice.json
              -> norm_to(raw, final, -18.0, tp=-3.0, pre=acompressor) -> voice/<id>.mp3
              os.makedirs({COMFY}/temp) FIRST - ComfyUI wipes it on every restart

6. MUSIC      06_acestep_music.json -> music/<prefix>_00001.mp3

7. CUT        short.py cut()
   a. scene_templates.expand(beat, clip_secs) -> [{at, len, fx}] + impact flag
   b. beat.camera OVERRIDES the template's move fx (strips punch/push/pull/pan_*/tilt_*/handheld)
   c. make_cut(): ffmpeg -ss/-t + base grade (+ day-for-night) + fx_chain,
                  re-encode libx264 crf16 veryfast yuv420p at FPS -> _work/NNNN_<id>_<ci>.mp4
   d. make_impact(): 2-frame abstract flash derived from the outgoing frame
   e. ffmpeg -f concat -safe 0 -i list.txt -c copy -> _work/_joined.mp4   (ALL hard cuts)
   f. composite to film.canvas + hook + HUD + story captions + dialogue captions -> _work/_vertical.mp4
   g. amix voices+music (duration=longest, apad) -> _mix_raw.wav -> slam() -> _mix_master.wav
   h. mux -c:v copy -c:a aac 256k -movflags +faststart
   -> {COMFY}/output/claude-generated/12-shorts/<slug>/<slug>.mp4
```

### 7.2 PATH B - `epic.py`, long-form narrated

```
1. AUTHOR    films/build_berserk*.py, build_hound.py -> films/<name>.json, `shots` array
2. NARRATE   epic.narrate() -> voice/<id>.mp3 + narration.json (measured durations, cached
             so later stages never re-probe the SMB share)
2b. CUES     scripts/cue_seconds.py films/<name>.json   (rewrites music[].seconds IN PLACE)
3. KEYFRAMES 14_qwen_edit_ref.json when the shot has `ref`, else 13_qwen_t2i_styled.json
4. CLIPS     part_frames() -> 8n+1 per part, capped at FRAME_CAP 241; i2v_wf() (optionally
             stacking film.id_lora); batch submit; then chain_stage() for `chain: N` and
             `from_prev` via last_frame()
5. SFX       10_stableaudio_sfx.json  -> sfx/<id>_00001.mp3
6. MUSIC     06_acestep_music.json    -> music/<prefix>_00001.mp3
7. EDIT      one ffmpeg segment per shot (setpts stretch, never a freeze, if a line overruns;
             ambience+sfx mixed in; drawtext titles over MOVING footage, no cards)
             -> concat_copy() for runs of `cut` (frame count VERIFIED)
                _xfade_group() for soft/dissolve/fade/flash, chunked into reels of CHUNK=10
             -> mix_layer() lays narration + score; sidechaincompress ducks score under
                the NARRATION-ONLY key stem
             -> two-pass linear loudnorm I=-16 TP=-1.5 LRA=11 + alimiter 0.708  [BROKEN, see 4.4]
             -> <slug>_nosubs.mp4, <slug>_scored.mp4, <slug>.srt, <slug>_captioned.mp4
```

### 7.3 Hard mechanical constraints (all measured on this box)

| Constraint | Value | Why |
|---|---|---|
| **LTX-2.3 frame count** | `length` must be **8n+1** | 97 = 4.04 s @24fps, 193 = 8.04 s, 241 = 10.04 s. `max(9, ceil(secs*fps/8)*8 + 1)`. |
| **LTX practical clip ceiling** | ~10 s (`FRAME_CAP = 241`) | *"LTX's practical ceiling before drift."* Past it, chain with `from_prev`. |
| **LTX cost is FLAT in length** | 193 f = 13.7 s vs 97 f = 13.5 s | Sizing shots to the narration is CHEAPER per minute, not more expensive - every extra shot costs a whole keyframe plus a whole clip. |
| **LTX resolution snap** | height snaps to a multiple of 32 | Ask 1280x720, get **1280x704**. |
| **LTX two-stage dims** | multiples of 32 at BOTH stages | 640x352 -> 1280x704 works; 768x432 does not. |
| **Wan 2.2 frame count** | `length` must be **4n+1** at 16 fps | 81 = 5.06 s, 121 = 7.6 s. Non-conforming values are silently rounded and can stutter on the last frames. |
| **Wan 2.2 clip ceiling** | ~5 s @720p; subject drifts past ~7 s | |
| **Wan negative prompt** | MUST contain `static, still image, frozen` | Or it may not move at all. |
| **FPS LOCK** | fps must not vary across a film | `ffmpeg -f concat -c copy` on mixed-fps segments fails or judders AFTER the whole render is spent. **Mixing engines is a trap: LTX is 24 fps, Wan is 16.** |
| **CANVAS LOCK** | same reason | Every micro-shot is re-encoded then stream-copied together. |
| **concat exits 0 on failure** | | A missing input or a mismatched resolution produces a truncated/garbled file **and a zero exit code**. `epic.py concat_copy()` verifies `sum(nframes(inputs)) == nframes(output)` and raises. **`short.py`'s concat path has NO such check** - every 219-shot render depends on `make_cut()` having already normalised codec/size/fps. |
| **Seeds - renderers** | positional | `short.py`/`epic.py`: keyframes `seed0 + i*7`, clips `+i*13`, voices `+i*17`, music `+i*41`. A per-beat `seed` field overrides. |
| **Seeds - compile.py** | content-hashed | `stable_seed(root, ch, sc, i) = int(sha256(f"{root}\|{ch}\|{sc}\|{i}").hexdigest()[:8], 16)`. *"The old scheme was `seed0 + index*7`. Inserting one scene at the top therefore re-rolled every keyframe after it and forced a full re-render."* **The renderers still use the positional scheme** - the fix only exists in the un-wired compiler. [PARTIAL] |
| **Card seed** | `SEED = 9001`, fixed for all 976 panels | |
| **IPAdapter weight** | 0.6 default, node 4 of `22_anime_kf_ipadapter.json` | Beats with no `ref` get 0.0 (passes the model through untouched - simpler than a second graph). A weight sweep at 0.0/0.4/0.7/1.0 found the character *"already recognisable at ZERO. IPAdapter refines the face; it is not what makes the character."* |
| **IPAdapter encoder** | `*_vit-h` needs the **ViT-H** encoder from h94's `models/image_encoder/` | The ViT-bigG one under `sdxl_models/` **loads silently and produces garbage**. |
| **`last_frame()` grab** | `-sseof -1 -update 1 -frames:v 100` | `-sseof -0.08` lands ~2 frames early at 24 fps, putting a visible hiccup at a join designed to be invisible. |
| **mix chunking** | 24 inputs per amix chunk | 100 narration lines through a single `amix` is slow and fragile. |
| **amix duration** | `duration=longest` + `apad` | The default `duration=first` silently truncated a 63 s short to 5.2 s of audio while every loudness check still passed. There is now a coverage guard comparing `dur(final)` with `adur(final)`. |
| **`{COMFY}/temp`** | must be created before every run | ComfyUI wipes it on restart; IndexTTS-2 writes a scratch wav there without creating it. |
| **SMB lag** | never read a just-written file off `Z:` | `ensure_local()` fetches it through ComfyUI's HTTP `/view` endpoint. One incident reported 10 files as "silent/n-a" purely because the share was checked instead. |
| **ComfyUI filename increment** | re-rendering writes `_00002_` while code reads `_00001_` | |
| **ffprobe duration** | `format=duration` is `max(video, audio)` | AAC padding pushed a final fade past the end so there was no fade-out. Probe `stream=duration` on `v:0`. |
| **ffmpeg build quirks** | no `-pattern_type glob`; a gap in a numbered sequence truncates silently; fontconfig is unconfigured on Windows and supplying a config **segfaulted** this build | |
| **Batch by model** | | ComfyUI runs its queue FIFO, so a batch stays contiguous and the model loads once. Interleaving model families costs a **25-90 s reload on every alternation**. |

### 7.4 The fx / camera vocabulary (`short.py fx_chain()`, applied per cut)

`push`/`punch` `zoompan z=1+0.10*on/n` - `pull` `zoompan 1.12-0.10*on/n` - `pan_l`/`pan_r`, `tilt_u`/`tilt_d` (scale 1.16x + time-ramped crop) - `handheld` (small sin/cos crop) - `shake` (`crop` with `sin(t*90)`/`cos(t*77)`) - `aberr` (`rgbashift rh=4:bh=-4:rv=-2:bv=2`) - `glow` (split + `gblur sigma 18` + screen blend 0.38) - `flash` (`eq brightness=0.55*max(0,1-t*8)`) - `ramp` (`setpts` slow-then-snap) - `smear` (`gblur sigma 6`) - `whiteout` - `hot` (`eq contrast 1.10 sat 1.18` + `vibrance 0.22`). [EXISTS]

### 7.5 The transition grammar (`epic.py TRANSITIONS`, per-shot `in` / `in_dur`)

| name | filter | duration | use |
|---|---|---|---|
| `cut` | (concat, no overlap) | 0.00 s | inside a scene, at every impact. **Should win roughly half the boundaries** (CHRONO ran 57/108 = 53%) |
| `soft` | `fade` | 0.28 s | two shots that are really one beat |
| `dissolve` | `fade` | 0.70 s | scene change within a time/place |
| `flash` | `fadewhite` | 0.50 s | the film's ONE recurring motif, ~1 per 45-55 s, never two adjacent |
| `fade` | `fadeblack` | 1.00 s (use **1.6**) | act break, three per film maximum |

**Measured xfade shape:** `fadeblack`/`fadewhite` are **asymmetric** - they snap to the extreme at ~25% of the duration then reveal over 3x that. `fadeblack:duration=1.0` Y-average by time: 0.00->68, 0.08->39, 0.17->5, **0.21->1.4**, 0.33->4, 0.50->15, 0.75->37, 1.00->53. So a "1.00 s fade act break" is a **0.21 s blink**; nothing under ~1.4 s reads as an act break. `fadewhite:duration=0.5` peaks Y=243 at 0.125 s then takes 0.375 s to recover - correct as-is. **You cannot hold on black with xfade.** [EXISTS]

**`short.py` uses NONE of this** - *"this format is ALL hard cuts, no dissolves anywhere."*

### 7.6 The templates (`scene_templates.py`, 17 total)

`expand(beat, clip_secs)`: an explicit `cuts` array on the beat **always wins**; otherwise `TEMPLATES[beat['template']](beat.get('intensity', 1.0))`, then `_scale` divides every `len` by intensity with a 0.06 s floor, then fractional `at` is multiplied by `clip_secs` and clamped so `at + len <= clip_secs`. Unknown template names raise `SystemExit` listing the valid ones.

**SHORT grammar** (one clip -> 6-10 micro-shots), at intensity 1.0:
`hook` 2 shots 2.50 s - `taunt` 2/1.85 - `clash` 6/1.13 +impact - `charge` 5/1.49 +impact - `impact` 3/1.04 +impact - `reveal` 3/1.56 +impact - `finisher` 3/2.32 - `aftermath` 1/1.40

**EPISODE grammar** (the opposite grammar, added 2026-07-31T06:12):
`establish` 4.20 s - `master` 3.60 - `speak` 3.20 - `react` 2.60 - `pillow` 3.00 - `insert` 1.80 - `build` 3 cuts / 3.10 - `sakuga` 5 cuts / 1.96 +impact - `hold_silent` 5.50

Docstrings that encode the craft: `speak` - *"Held for the line plus a beat of silence after it. The silence is the point. Cutting on the last syllable is the single most common way an AI edit betrays itself."* `react` - *"This is where an episode earns its emotion, and it is exactly what the rejected 20-minute film had none of."* `sakuga` - *"An episode gets one or two. If everything is sakuga, nothing is."* `hold_silent` - *"Silence immediately before an impact makes the impact twice as loud."* [EXISTS]

`SPORTS_CLASH_50S`: a 35-entry `(block, template, intensity)` arc table derived from a measured 52 s reference short (182 shots, median 0.10 s, 87% under 0.5 s, `REF_BLOCKS = [9,10,6,25,14,27,26,22,8,33,2]` cuts per 5 s block). `arc_summary()` prints ours-vs-reference **before any GPU is spent**. Its warning: *"Density comes from beat COUNT. Intensity above ~1.3 makes shots too short to read."* `build_derby.py` asserts `len(CONTENT) == len(SPORTS_CLASH_50S)` and refuses to run otherwise. [EXISTS]

### 7.7 Loudness

**`short.py slam()` - WORKS, and the dead ends are documented in the code so they are not retried.** [EXISTS]

Up to 6 iterations of measure-then-`volume=<delta>dB, aresample=192000, alimiter=limit=0.87:attack=1:release=60:level=disabled, aresample=48000` until within 0.3 LU of `TARGET_LUFS = -9.5`. That constant carries the comment: *"the reference short measures -9.43 LUFS. Feed-loud, not broadcast-safe. Do not round this to a nicer number - it is a measurement."*

Four attempts, each failing silently while reporting success:

| attempt | result |
|---|---|
| `loudnorm` inside a `filter_complex` | -16 LUFS (single-pass adaptive, never reaches target) |
| two-pass linear `loudnorm` | -13.9 (linear mode refuses gain that would breach TP, **and reports success**) |
| + `acompressor` in the gain loop | -18.3, LRA 0.50 - flatter than the reference it was imitating |
| **gain -> 192k-oversampled limiter, iterated** | **-9.84 LUFS / -0.58 dBTP** |

`alimiter` caps **SAMPLE** peak, not **TRUE** peak - hence the 192 kHz oversampling. **This fix was never back-ported to `epic.py`** (see 4.4).

Post-checks in `cut()`: warn if `abs(dur - adur) > 0.5` (*"the mix stopped early"*), if `abs(measured_LUFS - TARGET) > 1.5` (*"the master did not take"*), if `input_tp > -0.5` (*"raise the limiter's headroom"*). [EXISTS]

### 7.8 Grade, HUD, canvas

- **DAY-FOR-NIGHT is applied in the grade, not the prompt.** *"Animagine renders bright stadiums no matter what the prompt says - 'night, dark, dark background' plus a full daylight negative moved mean luma from 170 to 161, i.e. nothing. Grading is deterministic; prompting is not."* Final chain when `NIGHT`: `eq=brightness=-0.15:contrast=1.20:saturation=0.72, colorbalance=bs=0.05:rs=-0.03, eq=gamma=0.92`. A first, stronger version compounded with `hot`/`glow`/`aberr` into **solid magenta on a third of the film** and was toned down. [EXISTS]
- **Scoreboards and clocks are drawn in POST.** `film['hud'] = {before, after, goal_at}` plus a ticking 89:00->90:00 `drawtext eif` clock. *"These were first generated as scoreboard shots and came back as garbled digits ('8?.99.10'). Diffusion models cannot render specific text; asking them to is a waste of a beat."* [EXISTS]
- **Canvas:** `cw, ch = film.get("canvas") or CANVAS` (default 1080x1920). Widescreen (`cw >= ch`) uses `scale=...:force_original_aspect_ratio=increase` + `crop`. Vertical uses `crop=ih*1.38:ih, scale=cw:-2, pad=cw:ch:0:(ch-ih)/2` - cropped to **1.38:1 not 16:9** because the measured reference filled ~40% of the canvas against our 31%. [EXISTS]
- `short.py` constants: `KF=(1664,928)`, `VID=(1280,704)`, `CANVAS=(1080,1920)`, `FPS=24`, `NIGHT=True`, `TARGET_LUFS=-9.5`. [EXISTS]

### 7.9 Prompt duality

Every beat carries BOTH `prompt` (cinematic prose for the Qwen path) and `tags` (danbooru for the anime path), because *"the two model families want OPPOSITE prompt formats - Animagine returns abstract colour shapes when fed the cinematic prose Qwen wants."* [EXISTS]

**Known prompt-leak quirk in `build_episode.py` [BROKEN]:** for a `say` beat it builds `tags = f"{BASE[who]}, {MALE}, {WEAR[wear_seen]}, {text or 'close-up'}, {loc}, {Q}"` - **the spoken dialogue line is interpolated into the danbooru image prompt.** `screenplay.py` avoids this by using the shot's separate description line and defaulting dialogue shots to `"close-up"`.

### 7.10 Measured wall clock

| Render | Beats/shots | Finished | Wall clock |
|---|---|---|---|
| THE DERBY | 35 beats -> 174 shots | 62.9 s | 22 m 21 s |
| THE DERBY, full anime re-render | 35 | 62.9 s | 17 m 04 s |
| THE DERBY, final with fixes | 35 | 62.9 s | 17 m 12 s |
| THE DERBY Ep.1 | 180 beats -> 219 shots | 526.1 s | **1 h 55 m 49 s** |

**Rule of thumb: ~38.6 s wall clock per beat, or ~13 minutes of wall clock per finished minute of video.** [INFERRED from the four timings above]

---

## 8. Capability inventory

### 8.1 The box

| | |
|---|---|
| Host | `k4shix` @ 192.168.1.46, Fedora 44, 16 threads, 61,907 MB RAM, 1.9 TB NVMe |
| GPU | RTX 5090, 32,127 MB VRAM, Blackwell, 480 W. Under load: **479.5 W, 100% util, 63 C, no throttling** |
| Usable VRAM | ~30.5 GB (`--reserve-vram 1.5`). A GNOME session eats ~550 MB; headless frees ~2 GB more |
| ComfyUI | `/home/k4shix/ComfyUI`, **0.28.0** (`v0.28.0-49-gcd0eddaf`, released 2026-07-28), frontend 1.47.10, templates 0.11.17 |
| Python / torch | 3.14.6 in `$COMFY/venv` / **2.13.0+cu130**, plain pytorch attention (no xformers/sage/flash-attn) |
| Driver | 610.43.03 (CUDA 13.3) |
| Custom nodes | ComfyUI-Manager, ComfyUI-Chatterbox, TTS-Audio-Suite, ComfyUI_IPAdapter_plus |
| Startup | `scripts/restart-comfy.sh` only. **Auto-start behaviour UNKNOWN** - nobody ever ran `systemctl`. |
| Endpoints | `/manager/reboot` and `/api/refresh` are **404** on this build |

**NEVER inline `pkill -f 'main.py --listen'` in an ssh command string** - the pattern matches the ssh command's own `bash -c` process and kills your session. `restart-comfy.sh` matches on the full interpreter path instead.

### 8.2 Best-in-class per job

| Job | Model | Workflow | Cost | Notes |
|---|---|---|---|---|
| Text-to-image | Qwen-Image 2512 fp8 + Lightning 4-step, cfg 1.0 | `01_qwen_t2i_turbo` | **4.5 s** @1664x928 | 29.6 GB VRAM |
| T2I quality | Qwen-Image 2512, 20 steps cfg 2.5 | `02_qwen_t2i_quality` | 30-36 s | ~7x cost for the last 10-15% |
| T2I photoreal alt | FLUX.2 dev fp8 + Turbo LoRA, 8 steps | `26_flux2_t2i` | 24.6 s @1024^2 | 52.7 GB wanted -> **cannot co-reside with Qwen** |
| Anime keyframe | animagine-xl-4.0 + IPAdapter PLUS FACE | `22_anime_kf_ipadapter` | - | 1344x768, 28 steps, cfg 5.0, euler_ancestral |
| Image edit | Qwen-Image-Edit **2511** + 4-step Lightning | `22_qwen_edit_2511` | **8.3 s** | **5.8x faster** than 2509's 48 s on a better base |
| Two-image fusion | Qwen-Edit 2511 | `23_qwen_edit_2511_fusion` | 12.0 s | |
| Reference-locked keyframe | Qwen-Edit 2511 + style LoRA, up to 3 refs | `14_qwen_edit_ref` | - | The character-consistency workflow |
| T2V + audio | LTX-2.3 22B dev-fp8 + distilled LoRA, 8 steps | `11_ltx23_t2v_audio` | 13.5 s @768x512, **16.5 s @1280x704** | 44 GB wanted, offloads between stages |
| I2V + audio | LTX-2.3 | `12_ltx23_i2v_audio` | ~15 s | **ALL video generation in both renderers** |
| I2V holding the keyframe | Wan 2.2 I2V 14B + lightx2v 4-step | `04_wan22_i2v_turbo` | 36 s @480p / **129 s @720p** / 555 s @1080p | ~8x slower than LTX |
| Two-stage upscaled video | LTX-2.3 | `17_ltx23_t2v_upscaled` | 21.0 s @1280x704x97f | |
| Audio-driven video | LTX-2.3 ia2v | `20_ltx_audio_to_video` | 23.0 s | |
| Music | ACE-Step **1.5 Turbo**, 20 steps **cfg 1.0** | `06_acestep_music` | 7.6 s / 60 s | cfg 1.0 is CORRECT - it is a distilled model. Won a listening test against v1 3.5B |
| Music remix / extend | ACE-Step **1** v1 3.5B | `31_acestep_remix` | 6.0 s / 30 s | **The ONLY version that can do music-to-music**, 44.1 kHz |
| SFX | Stable Audio 3 Medium, 100 steps cfg 7 dpmpp_3m_sde | `10_stableaudio_sfx` | 1.7-3.0 s | **One sound per bed**, then normalise to -20 LUFS / -3 dBTP |
| Voice | Higgs Audio V3 (house engine) | `17_higgs_v3_voice` | - | via TTS-Audio-Suite |
| Voice, emotive | IndexTTS-2, 8 emotion dimensions | `16_indextts2_voice` | **~3 s/line** | |
| Still upscale | RealESRGAN x4plus | `09_image_upscale` | 4.5 s | 1664x928 -> 6656x3712 |
| Frame interpolation | FILM, 16->32 fps | `07_video_interpolate` | 7.5 s | |
| Segmentation | SAM 3.1 text-prompted + RGBA + magenta proof | `13_sam3_segment` | 18.1 s | |
| Matte | BiRefNet + magenta proof | `14_birefnet_matte` | 25.5 s | |
| Outpaint | FLUX.1 Fill + OneReward | `28_flux_outpaint` | 27.0 s | feather 24-48 px, FluxGuidance 30, `noise_mask FALSE` |
| Object removal | SAM 3.1 mask -> GrowMask -> FLUX Fill | `29_flux_object_removal` | 22.5 s | `noise_mask TRUE`. Verdict **mixed** |
| Control maps | DA3 depth + MoGe-2 normals + SDPose | `27_control_maps` | 1.5 s for all four | |
| ControlNet | Qwen 2512 + InstantX Union (Canny) | `05_qwen_controlnet` | 10.5 s | strength 0.6-0.9. **The only ControlNet on the box** |
| Vision caption | **Gemma-3-12B** via CLIPLoader type `ltxv` | `30_vision_caption` | 7.5 s | Qwen2.5-VL crashes - see below |
| Prompt writing | Qwen3.5-2B | `15_llm_prompt_studio` | 3.0 s | idea->prompt->image in one graph = 6.0 s warm |
| LTX prompt writing | Gemma-3-12B + abliterated LoRA | `18_ltx_prompt_enhancer` | 10.6 s | writes the soundscape clause too |
| Lyrics -> song | Qwen3.5-2B -> ACE-Step 1.5 | `21_llm_lyrics_to_song` | 12.0 s / 60 s | |
| 3D mesh | Hunyuan3D 2.1 | `24_hunyuan3d_mesh` | 19.5 s | **GEOMETRY ONLY** - POSITION attribute, no vertex colour/normals/UVs/texture; 525k tris |
| 3D splat | TripoSplat | `25_triposplat` | 19.5 s | + 90-frame 360 turntable @1024^2. No UVs or faces |
| Product composite | BiRefNet + Qwen backdrop + composite | `19_product_composite` | 31.7 s | |
| Anime restyle | animagine-xl-4.0 img2img | `21_sdxl_anime_restyle` | - | 1344x768, 28 steps, cfg 5.5, dpmpp_2m/karras |

**38 workflow JSONs total** (not 37), numbered 01-31 with **seven number collisions** because two concurrent Claude sessions numbered independently from 13 upward - e.g. both `13_sam3_segment.json` and `13_qwen_t2i_styled.json` coexist (confirmed by a live `ls -la` at 2026-07-30T02:12). [EXISTS]

**Not on the render path:** `08_chatterbox_tts.json` (removed from `epic.py` 2026-07-30T20:52:55Z and verified absent - *"chatterbox removed: True"*); `15_acestep_v1_full.json` (never referenced by either renderer; its only consumer, `make_audio_library.py`, reverted to `06_acestep_music.json`). [EXISTS]

### 8.3 Model inventory highlights

`diffusion_models/`: acestep_v1.5_turbo 4.79 GB, flux.1-fill-dev-OneReward-transformer_fp8 11.9, flux2_dev_fp8mixed 35.5, hunyuanvideo1.5_1080p_sr_distilled_fp16 16.7, hunyuanvideo1.5_720p_i2v_fp16 16.65, hunyuanvideo1.5_720p_t2v_fp16 16.65, qwen_image_2512_fp8_e4m3fn 20.4, qwen_image_edit_2509_fp8_e4m3fn 20.4, qwen_image_edit_2511_fp8mixed 20.5, seedvr2_3b_int8_convrot 3.46, triposplat_fp16 0.74, wan2.1_vace_14B_fp16 34.7, wan2.2_i2v_high/low_noise_14B_fp8_scaled 14.3 each, + z_image_turbo_bf16 11.46 (2026-07-31).

`checkpoints/`: ace_step_v1_3.5b 7.70, hunyuan_3d_v2.1 7.37, ltx-2.3-22b-dev-fp8 29.1, **sam3.1_multiplex_fp16 (SYMLINK to ../detection/)**, sdpose_wholebody_fp16 1.92, stable_audio_3_medium 9.22, animagine-xl-4.0.

> SAM 3.1 shipped into `models/detection/` where `CheckpointLoaderSimple` cannot see it. Fixed with a symlink, not a second copy: `ln -sf ../detection/sam3.1_multiplex_fp16.safetensors ~/ComfyUI/models/checkpoints/`.

`loras/` (12 as of 2026-07-30, + 6 small ones on 07-31): Flux2TurboComfyv2 2.76, Qwen-Image-2512-Lightning-4steps 1.70, Qwen-Image-Edit-2511-Lightning-4steps 0.85, Wan21_CausVid_14B_T2V_rank32 0.32, gemma-3-12b-it-abliterated_rank64 0.63, **ltx-2.3-22b-ic-lora-union-control-ref0.5 0.65**, **ltx-2.3-id-lora-talkvid-3k 1.16**, ltx_2.3_22b_distilled_1.1 2.74, qwen_image_2512_storybook_anime, qwen_image_modern_anime, wan2.2_i2v_lightx2v_4steps high+low. Later: Qwen-Edit-2509-Relight, -Light-Migration, 2511-multiple-angles, ltx2.3-transition, illustration-1.0-qwen-image, Qwen-Edit-2509-Lightning-4steps.

`models/ipadapter/ip-adapter-plus-face_sdxl_vit-h.safetensors` (847,517,512 b) + `models/clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` (2,528,373,448 b). **Note the paths - these are NOT under the custom node.** Installed by the USER on 2026-07-31 following instructions written to `Z:\shared\INSTALL-IPADAPTER.txt`.

**Empty dirs (placeholder file only):** `style_models`, `model_patches`, `photomaker`, `gligen`, `embeddings`, `hypernetworks`, `optical_flow`, `audio_encoders`, `unet`, `diffusers`, `vae_approx`, `clip`.

**Downloaded but not installed:** `Illustrious-XL-v2.0.safetensors` - the download **failed** on 2026-07-31T04:19. [BROKEN]

**Deliberately skipped (~68 GiB by plan sizes):** `mistral_3_small_flux2_bf16` (33.14), **`ltx-2.3-22b-distilled-fp8` (27.50)**, `hunyuan3d-dit-v2_fp16` (4.59), duplicate FLUX.2 turbo LoRA (2.57).

> **The skipped `ltx-2.3-22b-distilled-fp8` is a BLOCKER for two built-in templates.** `video_ltx2_3_ic_lora` (camera control) and the LTX FLF2V path both hardcode it. **Fix is a rewire to dev-fp8 + the distilled LoRA at 0.5** - as workflows 11/12/17 already do - **not a download.**

### 8.4 VRAM requirements (from ComfyUI's own `templates/index.json`; the `size` field IS the VRAM requirement, hence values >32 GB)

Qwen-Image 2512 29.6 | Qwen-Edit 2511 **47.8** | Qwen-Edit 2509 29.6 | FLUX.2 fp8 **52.7** | Z-Image Turbo 19.4 | LTX-2.3 t2v/i2v 44.0 | LTX-2.3 ia2v 40.0 | LTX ID-LoRA 40.5 | LTX IC-LoRA 38.1 | Wan 2.2 14B i2v 35.4 | Wan VACE 14B v2v **53.8** | HunyuanVideo 1.5 720p t2v 42.3 | ACE-Step 1.5 XL turbo 18.5 | ACE-Step 1 t2a 7.2 | Stable Audio 3 Medium 14.6 | FLUX.1 Fill OneReward 20.8 | Hunyuan3D 2.1 4.6 | TripoSplat 3.7 | SeedVR2 3B int8 3.7 | Depth Anything 3 1.2 | SAM3 1.6 | BiRefNet 0.4 | frame interpolation 0.1

### 8.5 Measured limits and traps

| | |
|---|---|
| **Image resolution ceiling is QUALITY, not VRAM** | Past ~2 MP Qwen duplicates composition (two horizons, repeated subjects). 2048x1152 is the practical edge. Correct workflow: 1-2 MP native then 4x upscale to 24.7 MP. Dimensions must be multiples of 16. |
| **Batching wins ~20%** | 1328^2 batch-4 = 15.0 s = **3.75 s/image** vs 4.5 s single. Batch 8 at 1024^2 should fit. |
| **Wan cost scales worse than linearly** | 720p is 2.3x the pixels of 480p but **3.6x** the time. 1080p is 2.25x the pixels of 720p but **4.3x** the time. Two 81 f clips cut together are cheaper AND faster than one 121 f clip. |
| **CONFIRMED OOM** | RealESRGAN `ImageUpscaleWithModel` processes an entire frame batch at once with **no chunking**. 161 frames at 5120x2880 float32 is ~28 GB and **OOM-killed the server**. `07_video_upres.json` was deleted 14 min after creation. **Never chain a GAN upscale after frame interpolation.** |
| **CONFIRMED VRAM CONFLICT** | FLUX.2 (52.7 GB wanted) cannot co-reside with Qwen on 32 GB. **Batch by model; never interleave shots.** |
| **BROKEN** | `qwen_2.5_vl_7b` as a generation encoder crashes: `Qwen25_7BVLI_Config has no attribute stop_tokens` (`llama.py:883`) - an upstream ComfyUI bug. Use Gemma. Qwen2.5-VL still works for conditioning. |
| **PARTIAL** | SDPose handles **ONE person**. Multi-person needs RTDETR weights, which are missing (node present, weights absent). |
| **PARTIAL** | FLUX Fill object removal **fails on the subject of a product shot** - no background to infer, and the composition itself says an object belongs there. Works only on a small object in a contextful scene. Regenerate the plate empty instead. Outpainting on the same model is excellent. |
| **MASK-INVERSION TRAP** (cost two wrong renders) | `SAM3_Detect` and `RemoveBackground` both return FOREGROUND masks. `JoinImageWithAlpha` inverts internally (`alpha = 1.0 - mask`); `ImageCompositeMasked` does **not**. Skip the `InvertMask` before a join and you save the background and throw the subject away - **invisible, because RGB stays intact.** Both matting workflows save a `*_proof_on_magenta` render for exactly this reason. |
| **Qwen-Edit 2511 gotcha** | `FluxKontextMultiReferenceLatentMethod` is **MANDATORY even for one reference**. Omit it and edits drift off source. Most common reason a 2509 graph breaks on 2511. |
| **LTX two-stage rules** | Stage-2 sigmas MUST start below 1.0 (`0.85, 0.7250, 0.4219, 0.0`); at 1.0 you discard stage 1. Must `LTXVSeparateAVLatent` before upsampling and `LTXVConcatAVLatent` the audio back before stage 2. Use `VAEDecodeTiled` with `tile_size 768, overlap 64, temporal_size 4096` to **disable** temporal tiling (temporal tiles seam on motion). |
| **Audio limits** | ACE-Step 1.5: 48 kHz stereo, -17.9 LUFS / 14.7 LU measured spread, **no hit-point conditioning so it CANNOT spot to picture** - generate longer than picture and trim in. Stable Audio 3: duration lands ~30 ms short of request (19.969 s for 20). Chatterbox: 24 kHz **MONO**, 25 tokens ~ 1 s, hard cap 4096 tokens ~ 163 s/call, `exaggeration` floor **0.25** (below is a hard HTTP 500 that aborts the run). |
| **TTS SILENT-OUTPUT TRAP** | Six engines tested, **all six reported job success, FIVE returned 1.06 s of digital silence** (VibeVoice, Higgs Audio, F5-TTS, CosyVoice, MOSS). Only IndexTTS-2 and Echo-TTS worked at first test; Higgs V3 was later made to work and became the house engine. **Always verify:** `ffmpeg -i out.mp3 -af astats=metadata=1 -f null - \| grep 'RMS level dB'` (`-inf` means silence). |
| **IndexTTS-2 install** | `descript-audiotools` is not installed by `install.py` (fails `No module named 'audiotools'`); `ComfyUI/temp/` must exist. |
| **New model files** | Picked up **without a restart** - loaders re-scan per `/object_info`. **Exception: voice reference files** - that dropdown is built at node-registration time and needs a restart. |
| **LoRA strength** | Accelerator LoRAs have **ONE correct value: 1.0** - it is sampler config, not a taste dial. **1.3 is damage, not more style** (harsh contrast, oversharpened edges, streaky artifacts). Style LoRAs 0.6-1.0 with TOTAL stacked strength near 1.0. Accelerator first in the chain, then styles. 54 distinct LoRAs are referenced by the 268 local templates; you have ~18. |

### 8.6 Capability folders

25 `verified` (01-text-to-image, 02-image-editing, 03-controlnet, 04-upscaling, 05-image-to-video, 06-text-to-video-with-audio, 07-frame-interpolation, 08-music, 09-sound-effects, 10-voice, 12-segmentation-matting, 13-llm-prompt-studio, 14-ltx-two-stage-upscale, 15-product-composite, 16-style-range, 17-lora-mechanics, 18-audio-to-video, 19-llm-lyrics-song, 20-qwen-edit-2511, 21-3d-generation, 22-flux2, 23-control-maps, 24-outpaint-removal, 25-music-remix, 26-vision-caption) - 7 `installed-untested` (28-vace, 29-hunyuanvideo, 30-camera-control, 31-character-identity, 32-seedvr2, 33-zimage, 34-flf2v) - 1 `not-explored` (27-lora-training). **Folders 27-34 carry a blue NOT YET EXPLORED badge, `"workflow": "not built yet"` and `"verdict": "planned"`. They are plans, not results.**

`11-short-film/` and `12-shorts/` exist on disk but have **no `CAPABILITY.json`** and do not appear in the 33-row audit. [PARTIAL]

### 8.7 The `CAPABILITY.json` schema

Fields: `title, claim, look_at, status, verdict, updated, model, released, vram, cost, workflow, limits[], strong[], weak[], alternatives[], next_steps[], panels[]`. `status` in `{verified, installed-untested, not-explored}`; `verdict` in `{works, mixed, failed, planned}`. Panel types: whole image `{file}`; 1:1 crop `{file, crop:[cx,cy,frac]}`; video strip `{file, frames:n}`. `file` may be `../other-folder/x.png` or `-` for an empty slot. Audio-only folders declare no panels. Commands: `python3 scripts/_write_caps.py` then `~/ComfyUI/venv/bin/python scripts/capcard.py [--list]` and `scripts/gallery.py --max-per-folder 12 --thumb 400`.

---

## 9. Craft rules that must be encoded

Everything here is measured on this box or learned by getting it wrong first. The docs are `FILMCRAFT.md` (the synthesis), `FILM-CRAFT-AUDIT.md` (a **separate** 372-line six-specialist audit, indexed by nothing), `FILMMAKING.md` (partly superseded), and `craft/{STORY,CINEMATOGRAPHY,EDITING,SOUND,VOICE,ANIME_MODELS,ANIME_EPISODE}.md`. **`FILMCRAFT.md` indexes only four of the seven craft docs** - VOICE, ANIME_MODELS and ANIME_EPISODE were added later and are unindexed.

### 9.1 The eight laws (`FILMCRAFT.md`)

1. **Generate in dependency order.** Speak every line first, measure with ffprobe, then derive each shot's frame count from the real duration. Nothing ever needs padding. Counter-intuitively cheaper: LTX charges the same for 193 frames as 97, while every extra shot costs a keyframe PLUS a clip.
2. **A cut is the default; a dissolve is a statement.** Cuts should win roughly half the boundaries. Runs of cuts stream-copy, so cuts are free.
3. **Chain the last frame when the event is continuous** (`"from_prev": true`). The only way past the ~241-frame ceiling. **Do not chain more than 2-3 deep** - the frame comes from 1280x704 video, not the 1664x928 keyframe, so it softens.
4. **Faces drift; design around it or pay for it.** (a) Cast something with no face. (b) The `characters` block WORDING matters more than its detail: gender before physique; never put a weapon in the block if a shot might also put one in frame; spell out absences (*"no eyes and no mouth"*); anchor attributes to their owner (*"at her own throat"*); give hero props character blocks too; **two specified items beat five**. (c) Budget a ~20% off-brief rate at 4 steps.
5. **A style LoRA is a palette as much as a style.** See 9.4.
6. **Normalise every stem; never trust a fixed multiplier.** See 9.5.
7. **Silence is a tool and must be authored.** Cut narration on the biggest image; cut the score dead. Duck the score from a **narration-only** key stem.
8. **Adapting someone else's story: the line is expression, not facts.** Write your own narration; evoke silhouettes, don't itemise costumes (role + silhouette + ONE signature detail); same rule for music (idiom yes, melodies no); never use the original soundtrack.

### 9.2 Pace and story (`craft/STORY.md`, measured on CHRONO)

| | wordless short | dialogue short | narrated long-form |
|---|---|---|---|
| shots/min | 25 | ~20 | **10.4** |
| words/min | 0 | 45-65 | **124** |

**"The one number to internalise: narration halves your cutting rate."** Every narrated shot costs `LEAD 0.30 + speech + TAIL 1.15` = **1.45 s of dead air per line**.

Measured narration clock: 1,301 words -> 446.6 s speech. Spoken rate **2.89 words/sec** (median 2.90, range 1.60-3.63). Raw Chatterbox ~3.4 w/s before `rate: 0.85`. Finished film 627.6 s = 10:28. **2.07 words per second of screen time. 124 words per minute of finished film.** Median line **14 words** (min 2, max 23).

**Budgets:** a 10-minute narrated film is ~1,250-1,300 words. One minute = ~124 words = ~9 lines = ~10 shots. A line is 8-20 words, **14 is the sweet spot**. `shot_seconds = words/2.89 + 1.45`. Measured speech duty cycle on a recap: **72%**.

### 9.3 Rhythm and coverage (`craft/EDITING.md`, `craft/CINEMATOGRAPHY.md`)

- **No more than six consecutive shots without one under 3.5 s. One short shot every ~25 s.** CHRONO's first shot under 4 s arrived **219 seconds in**.
- CHRONO's 109-shot length distribution: `<=3.4 s` 6, `3.7-4.4` **19**, `4.7-6.4` **45**, `6.7-8.0` **36**, `>=8.4` 3 - **81% inside a single 4-second band.** Healthy target is closer to **15 / 25 / 35 / 20 / 5**.
- LTX's 8n+1 quantisation at 24 fps gives steps of 0.333 s and collapsed **twelve** CHRONO shots to a byte-identical 4.0417 s. Practical floor is `1.45 s + speech`.
- **Never three consecutive shots at the same DELIVERED scale** - check the contact sheet, not the prompt: **Qwen quietly promotes wides to mediums when a character block is present.**
- CHRONO's delivered scale across 109 shots: XW 15, W 42, M 40, C 9, **XCU 0**, Macro 3 - *not one extreme close-up in a ten-minute film.*
- **A macro insert is the cheapest shot you can make**: no character, no face, no consistency risk, near-perfect prompt adherence, 4.5 s of GPU. **One insert per act minimum, and make it an object.**
- **Coverage is faked by scale contrast, not by matching.** No video model here has a persistent 3D space, so you cannot cut from a wide to a matching close-up of the same room and have the room agree. Build sequences where the CU is of a *thing* (hand, dial, water, eye) whose surroundings are out of frame. **"Insert-heavy grammar isn't a style choice; it's what the constraint permits."**

### 9.4 Prompting and style (`craft/CINEMATOGRAPHY.md`, `craft/ANIME_MODELS.md`)

- **The camera clause comes first and names ONE move only.** `PROMPTING.md`'s Wan ordering - camera -> subject motion -> ambient motion - is the load-bearing rule and applies unchanged to LTX-2.3; LTX additionally wants a soundscape clause.
- **Nine named LTX motion failure shapes:** 1 sequential beats (*"X, then Y"*), 2 multiple actors with separate actions, 3 motion contradicting the keyframe, 4 subjects entering/leaving frame, 5 dematerialisation / structural destruction, 6 hand-to-hand prop exchanges, 7 screen/display content changes, 8 time-lapse, 9 split-screen/multi-panel. Plus micro-face actions (blink, laugh, eyes opening). **CHRONO's 109 motion fields violated "one camera move, one action" about 45 times.** Ambient motion (cloth, hair, water, smoke, dust, embers, foliage, light) is safe **three or four at a time**.
- **Style LoRA hijacks the palette.** `qwen_image_2512_storybook_anime_lora` at `style_strength 0.9`: ten shots asking for grey/colourless/dead came back blue-sky-or-golden-hour. Clean A/B control: THE HOLLOW CHOIR with **no** style LoRA rendered **23/23 correctly bleak**. Verdict: global default **0.75**; **0.50-0.55** for dark acts; **0.85-0.9** for bright acts. And **split the global style string** - *"warm hand painted background, vivid saturated colour, dramatic sky"* sits last in the encoded text and **wins over the shot's own palette request**.
- **Off-brief rate:** earlier films ~20%; CHRONO with a style LoRA on the 4-step path **~28% (30 of 109)**, ~10 bad enough to hurt the story. **"A style LoRA raises your off-brief rate."** Budget **1.3 keyframes per finished shot**. Triage: ~70% fine, ~20% needs rewrite + `quality: true`, ~10% fixable by dropping `style_strength` plus explicit palette words.
- **"Qwen at 4 steps is a superb production designer and a mediocre stage director."**
- **The Pixar trap:** a strong style block collapsed **6 of 22** PUDDLE shots into the same front-facing cute portrait. Fixes in order of effect: (1) `quality: true` per shot (20-step path, ~30 s vs ~4.5 s) - *"the single biggest win"*; (2) per-shot negative for *not the default pose* AND *not the default emotion*; (3) lead with camera and action, put the character description last. **For a wide where the character should be a speck, omit the character description entirely.**
- **Anime checkpoints want the OPPOSITE prompt style from Qwen.** Animagine wants danbooru tags subject-first-then-camera-then-scene. Feeding Qwen-style cinematic prose to Animagine produced **abstract coloured shapes** at denoise 1.0. Quality tokens `masterpiece, best quality, very aesthetic, absurdres` are **load-bearing**. **`motion blur` belongs in the NEGATIVE, never the positive.** Settings: 1344x768 or 1216x832, 28 steps, cfg 5.0, euler_ancestral/normal.
- **STILL OPEN [BROKEN]:** *"Night and dark-background tags are not reliably obeyed - stadium backgrounds come back bright regardless. Fix before the next full render."* (The grade-based day-for-night in `short.py` is the workaround, not a fix.)
- **UNFIXED [BROKEN]:** multi-character clash shots break anatomically. **8 of 35 beats (23% of THE DERBY)** had merged bodies and distorted limbs, **concentrated on the action beats** - i.e. the damage lands exactly where the piece should be strongest. This is `roadmap/blocking.md`'s motivation.

### 9.5 Sound and mix (`craft/SOUND.md`)

**Measured generator spreads** - this is why every stem must be normalised:

| generator | spread |
|---|---|
| ACE-Step music | **20.5 LU** (-11.4 to -31.9 LUFS across six cues) under a `level` range of 0.19-0.25 = 2.4 dB of control |
| LTX ambience bed | **39.0 dB** across 91 clips (-51.2 / median -24.7 / -12.2) under one x0.14 multiplier |
| Chatterbox voice | 3.9 LU raw, **widened to 5.8 LU (47% worse) by the rubberband + dynaudnorm chain** |
| Stable Audio SFX | ~15 dB, some files peaking at **exactly 0.0 dBFS** |

**Mix bus targets (integrated LUFS per stem, two-pass loudnorm):**

| stem | under narration | no narration |
|---|---|---|
| Narration | **-20** (TP -4 dBFS), never multiplied above unity | |
| Designed SFX | -30 | -24 |
| Hero SFX | -24 | -20 |
| LTX ambience | -34 | -28 |
| Score | -26, ducked to -31 | |
| **Delivery** | **-16 LUFS, -1.5 dBTP**, one pass at the very end | (for the feed-loud shorts format: **-9.5**) |

Ratios: narration - score = **6 dB unducked / 11 dB ducked**; narration - designed SFX = **10 dB**; narration - ambience = **14 dB**.

**Ducking recipe, measured:** `sidechaincompress=threshold=0.15:ratio=4:attack=20:release=350:makeup=1:link=maximum` gives a clean **5.0 dB** duck while speaking and returns to 0.0 dB in the gaps. Threshold sweep: 0.05 -> -11.3 dB, 0.10 -> -7.3, **0.15 -> -5.0**, 0.25 -> -2.4, 0.40 -> -0.8. **The key stem MUST be narration-only** - keying off the finished programme wandered between -0.1 and -4.4 dB tracking *ambience* loudness with no relation to speech. **Do not go below `release=250`.**

**Voice clipping evidence:** `volume=1.9` on files peaking at -0.5 dBFS produced ~**+5 dBFS** on every line; the AAC intermediate lost another 1.7 dB into its own clipping; one 4-second segment had **277 samples pinned at full scale**. Shipped films measured `the-hollow-choir_scored` -14.4 LUFS / -0.3 dBTP / **375 clipped samples**; `the-last-good-year_scored` -15.9 / +0.1 / **193 clipped**. The recommended chain delivers -16.2 / -1.4 / **zero clipped**.

**Casting, not pitch-shifting.** *"A character is cast by pointing at a distinct REFERENCE VOICE, never by pitch-shifting one voice pack. Rubberband past about +/-10% wrecks formants, and the first cut of this film used 0.70 and 0.55 - which is why five characters sounded like one actor on a varispeed tape."* The whole rubberband block was **removed** from `epic.py` on 2026-07-30T20:52:55Z. **Four voice packs are clones of real people (Clint Eastwood, David Attenborough, Morgan Freeman, Sophie Anderson) and must not be cast.**

**cfg 1.0 is not a bug on a distilled model.** It IS a bug on Stable Audio (not distilled), which moved from 8 steps/cfg 1.0/lcm to **100 steps / cfg 7 / dpmpp_3m_sde** with ONE SOUND PER BED plus a normalise pass (cfg 7 clips). It is CORRECT on ACE-Step 1.5 turbo, which a listening test confirmed beats the larger v1 3.5B.

### 9.6 Episode direction (`craft/ANIME_EPISODE.md`, `scene_templates.py`)

- Every `say` beat auto-generates a `react` beat on the listener. *"That reaction is not decoration. It is where an episode earns its emotion, and it is exactly what the rejected 20-minute film had none of. Making it automatic means it cannot be forgotten on a tired scene."*
- **WEAR damage continuity:** a 5-level tag list appended to character tags with `wear_seen = max(wear_seen, wear)` so damage never heals.
  `0` clean uniform, neat hair - `1` sweaty, damp hair, flushed - `2` sweaty, dirt on uniform, messy hair, breathing hard - `3` torn uniform, dirt and grass stains, exhausted, dishevelled - `4` torn bloodied uniform, cut on face, utterly exhausted, trembling
- Director's toolkit: scene grammar, dialogue, **pillow shots** (Ozu's cutaway with no people in it), withhold, **sakuga discipline**, silence before impact, rule of three. Honest scale estimate for a 20-minute episode: **~400 shots, ~3 hours GPU**.
- The one rule for want/effort/struggle/success: **"Show the price, and the audience infers the desire."**

### 9.7 Camera-move reliability [INFERRED, NOT MEASURED]

The audit's own caveat: *"There is no measured evidence on this box for which move phrasings land - the table is inferred from shipped prompts, not tested."* Its #2 ranked recommendation was to go and measure it via a `sweeps/camera.txt` sweep. **That sweep was never run.**

| move | inferred reliability |
|---|---|
| locked-off / static | highest |
| slow push-in / forward dolly | high |
| handheld drift / subtle float | high |
| crane up / tilt | medium (no measured sample) |
| orbit / arc | low without control |
| rack focus | **unverified - treat as untested** |
| whip pan, dolly zoom, crash zoom | **not available** |

### 9.8 The user's own verdicts (the design brief, verbatim)

| when | quote |
|---|---|
| 2026-07-30T11:57 | *"i noticed the voices are really bad, maybe 1/10 quality. are there better text to voice ai with different styles?"* |
| 2026-07-30T12:22 | *"the music and sound effects are terrible too."* |
| 2026-07-30T14:09 | *"the voices are much much better, i can hear some personality in them. if there are more of this caliber get them"* |
| **2026-07-31T00:50** | **"it's terrible. i don't think anyone would watch it."** (the 20-minute Berserk film) |
| 2026-07-31T03:40 | *"the short is nothing like the one i posted. it's cartoony but not anime-like, is this because of our models? audio is glitched, why is it raining?"* |
| 2026-07-31T05:30 | *"slightly better because the beat in the audio kind of match with the pink glow effect so it feels like it's intentionally artistically done. however, **there's no substance to the clips. they feel random. there's no context to it.** much better but a lot of room for improvement."* |
| 2026-07-31T05:36 | *"i see a caption giving it context. great. but the images don't match the context too well. it still feels like random clips. **it needs to be clear enough that the context is known without captions.**"* |
| 2026-07-31T06:11 | *"can we make a 20 minute version of this episode and focus on the context via storytelling with video? think of it like an episode to an anime. there are drawn out scenes, pauses, dialogue. right now, it looks like an OVA music video style where there are fast cuts everywhere. ... introduce the protagonist and antagonist, the context of the episode, and walk us through the suspense as it climaxes and the episode finishes. use whatever else a master seasoned director might use"* |
| **2026-07-31T11:19** | **"immediate problems: there seems to be a left pan for every single video clip. is that the best you can do for transitions? is there a book on how to transition a movie? take notes from that. all the scenes are just a few seconds. the story seems one dimensional. compare that to a novel or manga someone is reading. we need to create a framework for making movies. and a timeline that the user can edit for more control in each scene. maybe make the script into a template that we can edit. that's the goal"** |
| 2026-07-31T11:56 | *"i guess what i mean is there a user version where i can edit each scene with a framework. so movie encapsulates chapters. chapters encapsulates scenes. each scene has x, y, z, ... variables that i can change. it can be transitions from previous scene as a variable, characters, type of scene, dialogue, pan/zoom, special effects, etc."* |
| 2026-07-31T13:55 | *"there are too many variables. can we group them into categories..."* |

**The last two are the spec for the entire `studio/` layer. Nothing built in response to them has ever rendered a frame.**

### 9.9 Recurring self-inflicted failure

**Blind string-replace patching that silently matched nothing and reported success.** Hit **three times in one session**. *"my dialogue parser lowercased the key before testing isupper(), so every line of dialogue was silently swallowed - locker compiled to 0 beats. Worse, I tried to patch it with a string replace that matched nothing and reported success."* / *"The blind-patch one is the recurring theme - I've now hit it three times this session, and reading the file before editing is faster than re-running."*

Also fixed and worth remembering: **three servers were bound to port 8777 simultaneously.** `socketserver allow_reuse_address` on Windows lets a second process bind rather than erroring, and the OS round-robins, so stale servers served old code and edits appeared to work at random. `serve.py` now probes the port first and refuses to start with a clear message.

---

## 10. The gap list, prioritised

Ordered by what unblocks the most.

| # | Gap | Status | Cost | Unblocks |
|---|---|---|---|---|
| **1** | **Wire `compile.py` -> `short.py`.** `compile.py` must emit `sheets`, `anime_sheets`, `voices`, `music`, and `short.py` must be callable on its output. | [NOT BUILT] | **The single biggest item.** Requires resolving characters/voices/cues from the (empty) `studio/characters/`, `studio/cues/` folders, or hardcoding a bridge for one film first. | **Everything.** Until this exists, the 461 variables, 87 presets, 206 cards and the whole web app are documentation of a machine that does not run. |
| **2** | **Verify the 976 panels.** Build contact sheets (one image per card, not eight), then Read them and write `look_at` + `verdict` from pixels. | [BROKEN - died on usage limit] | 126 sheets via ffmpeg (cheap) + ~126 image Reads. **Do NOT re-run the 13-agent workflow** - all agents errored so nothing replays from cache, and only 109 of 976 PNGs were opened before it died. | Turns 976 unlooked-at pixels into knowledge of which enum values actually work. Two of two earlier predictions were **wrong** when checked, so this cannot be shortcut. |
| **3** | **Fix `app.html` for the Gen-2 card shape.** `drawCardTab()` prints `${c.look_at}` unconditionally -> literal `undefined` on all 198; no branch for `not_visual`, `panels: []`, `control`, `review[]`. | [BROKEN] | Small - one function. | Makes the card system usable at all. Currently the app actively misrepresents 198 of its 206 cards. |
| **4** | **Preset -> census-variable resolver.** No mapping exists between `weather/rain.json`'s `wind` and `world.wind_speed`. | [NOT BUILT] | A mapping table + a resolve step in `compile.py`. | The whole two-tier preset promise ("pick a word, override one field, or set raw variables"). Depends on #1 to matter. |
| **5** | **`layer.depth_map`.** Depth Anything 3 is already installed. | [NOT BUILT - roadmap] | One capability, one workflow. | **Best value on the partials list by some distance** - unblocks per-plane blur, parallax, `dolly_zoom` AND `rack_focus` in one piece of work. |
| **6** | **L-cuts / J-cuts (audio-picture offset).** Add an `offset` field to each cue; add `b.get("audio_lead", 0)` to `line_start`; expose as `transition: l_cut/j_cut` = +/-0.6 s. | [NOT BUILT] | **~20 lines.** | *"THE single highest-value missing feature ... we cut picture and sound on the same frame at every transition, which is the loudest tell of an amateur edit."* Highest craft-value-per-line item in the whole project. **Risk:** cues can now collide - the compiler must detect overlapping voice cues and warn. |
| **7** | **A grade stage.** `FILM-CRAFT-AUDIT.md`'s ranked #1: *"grep proves no script does any colour work."* | [NOT BUILT] | Medium. | `look`/`grade.*` presets currently do nothing beyond prompt tags. |
| **8** | **Actually direct the cameras.** All 216 beats in `episode01.json` say `static`. The mechanism is wired; zero decisions have been made; nothing has been re-rendered. | [PARTIAL] | Authoring time + one ~2 h render. | The user's #1 stated complaint ("a left pan for every single video clip"). Also needs the camera-move sweep (9.7) to know which phrasings land. |
| **9** | **Back-port `slam()`'s 192k-oversampled limiter into `epic.py`.** Its shipped chain (`alimiter 0.708`) was measured at **+1.03 dBTP**. | [BROKEN] | Small - port a working function. | Any future `epic.py` render. Currently `--stage edit` produces a clipping master. |
| **10** | **Blocking / 180-degree rule via tags.** `facing left` / `facing right` per character per scene, held consistent. | [NOT BUILT - roadmap] | *"Costs nothing"* - a compiler feature, not a model feature. | The 23%-of-shots multi-character anatomy failure. Escalation path: SDPose/ControlNet pose conditioning (real work), or two single-character generations composited. |
| **11** | **Fix the two over-blanked `shot.framing_type` panels** (`insert_object`, `empty_frame` - the `no humans` danbooru tag was caught by the negation regex). | [BROKEN] | Two re-renders. | Card accuracy. |
| **12** | **The 33 audio/dialogue/caption cards** - "a different kind of card" was never designed. | [NOT BUILT] | Design + build. | Audio variables have zero demonstrable evidence. |
| **13** | **Add a `beats`-aware branch to `analyze_shots.py`.** It reads `film['shots']` and calls `epic.clip_parts()`. | [PARTIAL] | Small. | THE DERBY and Ep.1 have **never been measured with the instrument that condemned the Berserk film** (mean motion 2.25, 50 shots under half mean motion = 33% of screen time). |
| **14** | **Add frame-count verification to `short.py`'s concat**, as `epic.py concat_copy()` already has. | [NOT BUILT] | ~5 lines. | Every 219-shot render currently depends on an ffmpeg call that exits 0 on failure. |
| **15** | **Fix the 19 wrong `renderable` flags** flagged by the review and never acted on; re-render affected cards. | [NOT BUILT] | Medium. | Card correctness. |
| **16** | **Re-map the 12 orphaned review problems** (compound `variable` strings matched no card, so they are invisible in the app). | [NOT BUILT] | Small. | Review coverage. |
| **17** | **Enforce what `compile.py` documents.** fps/canvas are described as LOCKED and are not; `blocking` and audio-offset produce no warning despite roadmap files. | [BROKEN] | Small. | The file's own stated principle *"NOTHING SILENTLY DOES NOTHING."* |
| **18** | **`char.emotion` -> TTS.** Emotion presets already carry `voice_style` and `voice_rate`. | [NOT BUILT - roadmap #2] | *"mostly plumbing"* | Performance from the authoring layer. |
| **19** | **`audio.*` levels and ducking.** Soundscape presets carry `bed_level`, `music_level`, `duck` that nothing reads. | [NOT BUILT - roadmap #3] | Medium. | |
| **20** | **`light.ratio` / `light.temp` biasing the grade** rather than only emitting tags. | [NOT BUILT - roadmap #4] | Medium. Depends on #7. | |
| **21** | **Update the stale docs** (README custom-nodes, card 10-voice, card 31-character-identity, `make_audio_library.py` header, CAPABILITIES.md's -35 dBFS claim, `_doc.py`'s dead `weather` ORDER entry). | [BROKEN] | Small each. | Stops future work being misled. |
| **22** | **Reach the five installed-but-unreachable capabilities** (LTX ID-LoRA, LTX IC-LoRA, SDPose, Depth Anything 3, MoGe-2). | [NOT BUILT] | Per-capability. | Note the LTX ones need a rewire to dev-fp8 + distilled-LoRA@0.5, **not a download**. |
| **23** | **`weather.wind` / particle motion.** | [NOT BUILT - roadmap #5] | Waits on video-level control. | *"should be last."* |
| **24** | **`shot.keyframe_mode`** (start_only / start_end / start_mid_end). No renderer has a first-last-frame or interpolation path. | [NOT BUILT] | Needs an FLF2V workflow (34-flf2v is `installed-untested`). | |
| **25** | Lipsync. Recommended path is **NOT** post-hoc mouth driving: *"anime uses three mouth positions, not lip sync"* - generate phoneme mouth shapes and cut between them (option 2), or direct around it with off-screen/back-to-camera/wide coverage (option 3, free). **Try 2 and 3 before 1.** | [NOT BUILT - roadmap] | | |
| **26** | `studio/places/`, `studio/characters/`, `studio/cues/` are empty directories. | [NOT BUILT] | Authoring. | Blocks #1 - `compile.py` needs characters and cues to emit `voices` and `music`. |

**Deferral honesty note.** The partials work (#18-20, 23) was explicitly deferred **twice**: *"Partials - still not started, and I want to be straight that this is the second time I've deferred it. 155 variables and 41 presets. I'm not going to claim progress I haven't made."*

---

## 11. Must-check-on-the-box list

Run once the SMB share is back. **Never inline `pkill -f 'main.py --listen'` over ssh.**

### 11.1 Is the box even alive

```bash
ssh -i ~/.ssh/saltmark_ed25519 k4shix@192.168.1.46 \
  'pgrep -af main.py; tail -50 /tmp/comfy.log; curl -s --max-time 3 http://127.0.0.1:8188/system_stats'
# if down:
ssh ... 'bash ~/shared/comfy-studio/scripts/restart-comfy.sh'
# the systemd question NOBODY has ever answered:
ssh ... 'systemctl list-units | grep -i comfy; systemctl --user list-units | grep -i comfy; ls /etc/systemd/system/ ~/.config/systemd/user/ 2>/dev/null'
df -h /home
```

### 11.2 Did the last command survive?

```bash
ls -la /z/shared/comfy-studio/studio/samples/sheets/ | head -40
ls /z/shared/comfy-studio/studio/samples/sheets/ | wc -l     # was 0 at last check
pgrep -af make_sheets.py                                      # is bzw4z7ex3 still running?
grep -l '"sheet"' /z/shared/comfy-studio/studio/cards/*.json | wc -l   # expect 0
```

### 11.3 The variable model

```bash
ls -la /z/shared/comfy-studio/studio/
python3 -c "import json;V=json.load(open('/z/shared/comfy-studio/studio/variables.json'));import collections;print(len(V), collections.Counter(v['status'] for v in V), collections.Counter(v['level'] for v in V))"
# expect: 461  {'ready':280,'partial':155,'roadmap':26}  {'shot':180,'any':157,'scene':69,'movie':41,'chapter':14}
ls -la /z/shared/comfy-studio/studio/roadmap/            # expect NINE files incl. VARIABLES-TODO.md and FINISH-PARTIAL.md
wc -c /z/shared/comfy-studio/studio/roadmap/FINISH-PARTIAL.md   # its generator timed out at exit 143
ls /z/shared/comfy-studio/studio/{places,characters,cues}/       # expect EMPTY
# confirm the self-deleting generators really are gone:
ls /z/shared/comfy-studio/studio/{_ingest.py,_doc.py,_presets.py,_finish.py,_ingest_cards.py,_enums.json,_enums_slim.json,_wf.js} 2>&1
# the shot.fx leaf-and-branch collision:
python3 -c "import json;V=json.load(open('/z/shared/comfy-studio/studio/variables.json'));print([v['name'] for v in V if v['name'].startswith('shot.fx')])"
# is there ANY preset->variable mapping table anywhere?
grep -rn "wind_speed\|ground_state\|weather_intensity" /z/shared/comfy-studio/studio/ | grep -v variables.json | grep -v VARIABLES
```

### 11.4 The cards

```bash
ls /z/shared/comfy-studio/studio/cards/*.json | wc -l                 # expect 206
find /z/shared/comfy-studio/studio/samples/vars -name '*.png' | wc -l # expect 1026
grep -L '"verdict"' /z/shared/comfy-studio/studio/cards/*.json | wc -l # expect 204
grep -l '"verdict"' /z/shared/comfy-studio/studio/cards/*.json         # expect shot_size.json, shot_angle.json ONLY
grep -l '"look_at"' /z/shared/comfy-studio/studio/cards/*.json | wc -l # expect 8 (the Gen-1 set)
grep -l '"not_visual"' /z/shared/comfy-studio/studio/cards/*.json | wc -l # expect 72
grep -c '"control": true' /z/shared/comfy-studio/studio/cards/*.json | awk -F: '{s+=$2} END{print s}'  # expect 77
python3 -c "import json;S=json.load(open('/z/shared/comfy-studio/studio/cards_spec.json'));print(len(S), sum(1 for c in S if c.get('renderable')), sum(1 for c in S if c.get('review')))"
# expect 198 / 126 / 91   -- cards_spec.json was never deleted
# the over-blanked negation panels: are these the plain boy instead of an empty frame?
ls -la /z/shared/comfy-studio/studio/samples/vars/shot_framing_type/
# open insert_object.png and empty_frame.png and LOOK at them
```

### 11.5 The render pipeline

```bash
ls -la /z/shared/comfy-studio/workflows/         # expect 38 files; confirm the 7 number collisions
ls /z/shared/comfy-studio/workflows/{32_train_character_lora,33_ltx_ic_control,34_ltx_id_lora,35_seedvr2_upscale,36_zimage_turbo}.json 2>&1  # expect ALL MISSING
ls -la /z/shared/comfy-studio/scripts/           # confirm analyze_shots.py, and note there are TWO make_sheets.py
md5sum /z/shared/comfy-studio/studio/compile.py  # has anyone extended it past 25 variables?
grep -n 'variables.json\|short.py\|import short' /z/shared/comfy-studio/studio/compile.py   # expect NO hits
grep -n 'alimiter' /z/shared/comfy-studio/scripts/epic.py                                   # expect limit=0.708 (still broken)
grep -n 'aresample=192000' /z/shared/comfy-studio/scripts/epic.py                            # expect NO hits
python3 -c "import ast;ast.parse(open('/z/shared/comfy-studio/scripts/epic.py').read());print('epic ok')"
wc -l /z/shared/comfy-studio/scripts/{epic.py,short.py,screenplay.py,scene_templates.py}     # expect 1069 / 630 / 276 / 349
python3 -c "import sys;sys.path.insert(0,'/z/shared/comfy-studio/scripts');import scene_templates as t;print(len(t.TEMPLATES), len(t.SPORTS_CLASH_50S))"  # expect 17 / 35
```

### 11.6 Which `episode01.json` is on disk?

```bash
python3 -c "import json;f=json.load(open('/z/shared/comfy-studio/films/episode01.json'));print(len(f['beats']), f.get('canvas'), sum(1 for b in f['beats'] if b.get('caption')), set(b.get('camera') for b in f['beats']))"
# 216 beats / [1920,1080] / 0 captions / {'static'}  => the screenplay version (NOT what shipped)
# 180 beats                                          => the build_episode.py version (what shipped)
```

### 11.7 Does a `.movie` render at all?

```bash
cd /z/shared/comfy-studio
python3 studio/compile.py studio/movies/derby-ep1.movie --timeline   # read every '!' warning line
python3 -c "import json;f=json.load(open('studio/movies/derby-ep1.json'));print(sorted(f.keys()))"
# expect NO sheets / anime_sheets / voices / music  -> confirms the 4.1 dead end
python3 scripts/short.py studio/movies/derby-ep1.json --stage voices  # expect KeyError on cfg['voice']
python3 studio/compile.py --vars | head -30    # confirm it prints 25 flat names, not 461
```

### 11.8 Models and nodes

```bash
ls -laR /z/ComfyUI/models/ | head -200            # last full listing was 2026-07-30T02:10
ls /z/ComfyUI/custom_nodes/                        # expect 4 packs, NOT "Manager only"
ls -la /z/ComfyUI/models/checkpoints/ | grep -i 'animagine\|illustrious'   # Illustrious FAILED to download
ls -la /z/ComfyUI/models/latent_upscale_models/    # is hunyuanvideo15_latent_upsampler_1080p actually there?
ls -la /z/ComfyUI/models/ipadapter/ /z/ComfyUI/models/clip_vision/
ls -la /z/ComfyUI/models/diffusion_models/ | grep -i 'z_image'
ls -la /z/ComfyUI/models/text_encoders/ | grep -i 'qwen_3_4b'
ls -la /z/ComfyUI/input/sheet_*.png                # sheet_rask, sheet_viro, sheet_anime_rask, sheet_anime_viro,
                                                    # sheet_guts/griffith/casca/judeau/zodd
python3 -c "import json;print(json.load(open('/z/shared/comfy-studio/workflows/22_anime_kf_ipadapter.json'))['4']['inputs']['weight'])"  # expect 0.6
ls -d /z/ComfyUI/venv/lib/python3.14/site-packages/audiotools 2>&1   # IndexTTS-2 prerequisite
ls -d /z/ComfyUI/temp 2>&1                                            # wiped on every restart
```

### 11.9 Capability cards and craft docs

```bash
~/ComfyUI/venv/bin/python /z/shared/comfy-studio/scripts/capcard.py --list   # expect 33 rows: 25 verified / 7 untested / 1 not-explored
ls -la /z/shared/comfy-studio/{FILMCRAFT.md,FILM-CRAFT-AUDIT.md,FILMMAKING.md}   # THREE different docs
ls -la /z/shared/comfy-studio/craft/       # 7 .md + _relines.json + _rerolls.json + _recues.json
cat /z/shared/comfy-studio/craft/_recues.json  # expect exactly 7 cue ids
# were the audits' re-renders ever actually run? reconcile.py was written to a LOCAL scratchpad, not the box
```

### 11.10 Open questions with no command yet

1. **Did `make_sheets.py` (studio) ever finish, or is it still hung on SMB paths?** ffmpeg with 12-16 inputs and a long `filter_complex` over an SMB share is the suspect.
2. **`films/episode01.json`'s mtime is ~32 min after the recorded compile.** What wrote it? No transcript activity covers that window.
3. **Did the census workflow's ~640 dropped/merged variable names survive?** Check `.../74b2253e-.../subagents/workflows/wf_95ebc01a-55d/journal.jsonl` and the 11 per-agent files (logs say *"901 variables proposed across 6 departments"* then *"completeness pass found 200 additional variables"* = 1,101 proposed, deduped to 461).
4. **Is any `films/*.json` authored with an explicit `cuts` array rather than a `template`?** `expand()` honours it but no builder emits it - confirm whether that branch is dead code.
5. **Are the `hud` values and the anime character sheets reproducible?** Both were hand-injected / made by ad-hoc heredocs. No committed script regenerates the anime sheets. Consider a `make_sheets.py --anime` mode before the next full render.
6. **Machine B** (`C:/Users/Kashix/Documents/ComfyUI`, claimed 16 packs / 153 GB) has never been inspected. Decide whether it matters at all.
