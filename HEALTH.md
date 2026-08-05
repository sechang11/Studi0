# HEALTH — is everything actually working?

Audited 2026-08-05 by rendering, fetching and measuring, not by reading. New tool:
`studio/_tools/healthcheck.py` (`--json` for machine output, or name sections:
`routes tools cards workflows movies defects`). Every claim below was produced by it or
by a measurement recorded alongside.

**The short answer: the APP is healthy. The TOOLBOX is dangerous. The RENDERER lies about
three things.** Nothing in the served application is broken. All 14 pages and all 19 GET
APIs answer 200 with sane bodies, HEAD agrees with GET on every one, all 7 POST endpoints
are routed and validate before they act, and all 1,303 media files the APIs advertise
were fetched and served. Every one of the 41 workflow JSONs parses with no dangling
wires, every node id the renderers write still exists in the graph they write it into,
all 4 `.movie` files compile, `check_refs.py` reports 1,925 references with 0 dangling,
and `lora_scan.py` reports clean.

---

## 0. WHAT I BROKE DURING THIS AUDIT — READ FIRST

I ran `--help` on all 60 tools in `studio/_tools/` to see which ones respond. **Seventeen
of them ignore `--help` and did their whole job instead.** This is not a hypothetical: it
overwrote committed data, wrote two workflow files, regenerated fifteen sample images and
put real jobs on the GPU. The damage is fully recoverable — everything is in git HEAD —
but it is not yet reverted, because `git checkout`/`git restore` were blocked by the
permission classifier and I did not force past it.

**The worst of it: `style_verdicts2.py` overwrote 10 style cards**, replacing measured
LoRA-rescue verdicts with stale wave-2 stubs and reverting engine routing. Example, on
`studio/styles/stop_motion_felt.json`:

- `engine` reverted `qwen` → `anime`
- `status` reverted `ready` → `unavailable`
- `verdict` — ~900 words of measured evidence ("*a needle-felted puppet … visible hand
  stitches down both lapels … present at every strength tested — 0.6, 0.8, 1.0, 1.2,
  1.5*") replaced with one stale sentence ("*No felt fibre, no armature … Ordinary
  anime.*")

`pointillism.json` lost an equivalent verdict the same way. Eight more style cards, two
capability cards, `panel_effects.json` and fifteen sample webps were rewritten.

**To restore, run these three lines yourself:**

```
cd ~/shared/comfy-studio
git checkout -- studio/styles studio/cards/look_deterministic.json \
  studio/cards/shot_fx_deterministic.json studio/panel_effects.json studio/samples/vars
rm -rf 'studio/_tools/--help'          # 66 style cards author_styles2.py wrote into a
                                        # directory literally named --help
```

Do **not** `git checkout` `scripts/` or `studio/*.py` — those edits are older than this
session and belong to another agent working concurrently. Same for the untracked
`studio/_tools/capability_scan.py`, `studio/capabilities.json`, `craft/INSPIRATION.md`
and `studio/_tools/prompt_recipes.json`.

Eighteen new untracked webps under `studio/samples/vars/look_deterministic/` are also
mine (`deterministic_panels.py`). They are additive and harmless; delete or keep.

`healthcheck.py` **never executes a tool** — it inspects them with `ast.parse`. That rule
is written into its docstring so nobody repeats this.

---

## THE RANKED LIST

### 1. BROKEN — 17 tools run their entire job when handed any argument

*Blocks: safely inspecting, documenting or scripting the toolbox. Cost me committed data
in this session and will cost the next person the same.*

They have no `argparse`, so `--help` is swallowed as a positional or ignored, and the work
happens at module level. What each one did when handed `--help`:

| tool | what `--help` actually did |
|---|---|
| `style_verdicts2.py` | rewrote 66 style cards, re-routed 1 |
| `style_verdicts.py` | rewrote style verdicts |
| `author_styles2.py` | wrote 66 style cards into a new dir named `--help` |
| `make_turnaround_wf.py` | overwrote `workflows/32_qwen_turnaround.json` |
| `make_train_wf.py` | overwrote `workflows/33_train_character_lora.json` |
| `make_cues.py` | rewrote 8 cue cards |
| `make_domains.py` | rewrote 5 domain descriptors |
| `make_prompts.py` | rewrote prompt cards |
| `deterministic_panels.py` | re-ran ffmpeg, rewrote 15 sample webps + 2 cards |
| `panel_diff.py` | rewrote `studio/panel_effects.json` |
| `damage_nouns.py`, `field_fix.py` | wrote jpegs |
| `terra_check.py` | **queued real GPU renders** (6.2 s/image) |
| `contact_sheets.py`, `to_webp.py`, `repoint_webp.py` | no-ops this time, would write |
| `camera_sweep.py` | errored looking for a source clip |

Fix: an `argparse` with no arguments at the top of each, or a `if __name__ == "__main__"`
guard plus a `main()`. Ten of the seventeen also write files at module level, which
`healthcheck.py` now flags as `WRONG` by name.

### 2. BROKEN — three camera moves are byte-identical to static

*Blocks: any shot that asks for depth. The wizard still offers them.*

Still real, re-verified. `scripts/short.py:fx_chain()` has no branch for `dolly_zoom`,
`orbit` or `rack_focus`, so the emitted filter chain is empty and the clip passes through
unchanged. The cards say so honestly (`status: unavailable`, mean abs pixel diff vs static
**exactly 0.00**, all four displacement axes +0px) and `short.py` prints a named warning —
but `compile.py` only downgrades to static for compiled films; a hand-authored
`films/*.json` reaches `short.py` and silently gets nothing. `orbit` is not achievable
post-hoc at all. `dolly_zoom` and `rack_focus` need one thing: a depth pass. Depth Anything
3 is already installed and driven by ComfyUI core nodes; what does not exist is a depth
workflow file and a stage in `short.py` between `keyframes()` and `cut()`.

### 3. BROKEN — the night grade does not darken, it clips to black

*Blocks: every dark insert, every night scene, in every film.*

Measured, not quoted. Flat grey plates pushed through the shipped grade
(`eq=brightness=-0.15:contrast=1.20:saturation=0.72,colorbalance=bs=0.05:rs=-0.03,eq=gamma=0.92`):

| input luma | 16 | 32 | 48 | 64 | 80 | 96 | 128 | 170 | 200 |
|---|---|---|---|---|---|---|---|---|---|
| **output** | **0** | **0** | **0** | **1** | 15 | 32 | 70 | 121 | 158 |

Everything at or below luma ~60 becomes **pure black**, not dark. The arithmetic is exact:
`-0.15` shifts the plate down, then `contrast=1.20` about the 0.5 midpoint drives anything
under 0.233 negative and it clips. This is worse than the previously reported "YAVG ~13" —
there is no detail left to recover. Same failure lives in `short.py`'s `NIGHT` day-for-night
fallback, which uses the identical string. Fix is to lift the black floor: drop
`brightness` to about `-0.06` and do the darkening with `gamma` instead, then re-measure
this table.

### 4. WRONG — the renderer sends no negative prompt on four of five graphs

*Blocks: any card, character or style that needs something excluded. Partly fixed since
last reported, and the fix does not cover the qwen path.*

`short.py` — the renderer the app and the wizard reach — writes the node feeding the
sampler's `negative` input on **exactly one** graph, `22_anime_kf_ipadapter.json`, where
`_negative()` subtracts from the shipped text any clause the positive is asking for. It
writes **no negative at all** on:

- `13_qwen_t2i_styled.json` (node 11)
- `14_qwen_edit_ref.json` (node 11)
- `12_ltx23_i2v_audio.json` (node 11) — the video pass
- `06_acestep_music.json` (node 10)

Those render with whatever text is committed in the JSON. Nothing an author writes can
reach it. `compile.py` already emits the warning that proves the hole is felt: *"90s cel
anime asks for extra words in the negative prompt (3d, modern anime style, clean digital
coloring, glossy, crisp lineart) but the renderer has no negative input wired"*. The
`negative_add` field exists on style cards and has no consumer.

Note the older `scripts/epic.py` **does** write node 11 on the qwen graphs. The two
renderers disagree, and the one the app uses is the weaker.

`healthcheck.py` finds the negative node by asking the graph which node feeds
`inputs.negative` — never by node number. The first version of that check grepped for
`set_path(wf, "11.` and reported all four graphs healthy, because `short.py` writes node
11 of a *different* workflow (a SaveImage prefix) and node 11 of a *third* (an audio
duration). It found the string and missed the fact.

### 5. WRONG — 21 of 29 beats in the real films resolve to a motion hold

*Blocks: the films moving. Every frame of those beats is the keyframe.*

Exactly as reported, still exactly true. Counted from compilation:

| film | beats | holding | from a motion card | derived from the shot line |
|---|---|---|---|---|
| `derby-ep1.movie` | 12 | **9** | 0 | 3 |
| `derby-qwen.movie` | 12 | **9** | 0 | 3 |
| `my-scene.movie` | 5 | **3** | 0 | 2 |
| *(total)* | **29** | **21** | **0** | 8 |
| `motion-proof.movie` | 12 | 3 | 6 | 2 |

`motion-proof.movie` is the control and shows the fix works: name a motion card and the
beat moves. **Not one beat in the three real films names a motion card.** 34 cards live in
`studio/motions/` and the authored films do not use them. The compiler already says so per
beat, with the list of cards that would fit. This is an authoring gap, not a broken
mechanism — but it is why the films look still.

### 6. WRONG — TERRA's headpiece is trained in wrong

*Blocks: any correction that does not involve a retrain.*

Still real. `TERRA.json` `tags` say `red hair ribbon`. The card's own `identity_note`
records that all 160 view renders and the sheets on **both** engines draw a large
pink-and-gold ornament with a red gem and two upswept prongs that read as horns. It is in
the source sheet, both engines inherit it, and it is now trained into
`character_terra_00001_v3.safetensors`. The tags are the prompt, so every future render
inherits the mismatch. This is the same class as the "pointed ears" caught at the sheet
stage — except this one was not caught, and fixing it now means a new sheet and a retrain,
not a tag edit. Two more live identity defects sit in the same note: the bodice colour
flips gold↔red seed by seed, and the two engines disagree about her hair (saturated teal
on qwen, pale yellow-mint on anime).

### 7. WRONG — one style card carries two badges that contradict each other

*Blocks: trusting the styles page.*

`stop_motion_felt` is served with `status: ready` **and** `compose: inert`, and
`styles.html` renders both flags, so the card simultaneously says *"Rendered and checked
against the control. It does what the card says"* and *"inert — no visible change from the
control … Picking it costs a full generation and buys nothing."* Its own verdict field
opens *"RESCUED BY A STYLE LoRA — the strongest positive result in the lora_rescue sweep."*

Exactly 1 card of 130 has the direct `ready + inert` contradiction. Seven more carry
`inert` alongside `weak`/`unavailable`, which is duplicative rather than contradictory.
(Note: this card is one of the ten `style_verdicts2.py` clobbered in §0 — the contradiction
predates that and will still be there after you restore.)

### 8. GAP — 8 tools want numpy and the system interpreter does not have it

*Blocks: the motion and cast measurement toolchain, under the interpreter every doc names.*

`python3` on this box has PIL but **no numpy, no torch**. The ComfyUI venv
(`~/ComfyUI/venv/bin/python`) has numpy 2.4.6, torch 2.13.0, matplotlib and librosa.

- `terra_styles.py` — **cannot start at all** (top-level `import numpy`). This is the tool
  the TERRA card names as the source of its whole-library style verdict.
- `cast_motion.py`, `cast_proof.py`, `cast_style.py`, `cast_voice.py`,
  `motion_examples.py`, `terra_views.py`, `terra_wardrobe.py` — import numpy inside
  functions, so they start fine and die partway through, after doing work.
- `cast_voice.py` additionally wants librosa and matplotlib; `terra_views.py` wants torch.

Every card and every compiler warning in this project says `python3 studio/_tools/...`.
Either install numpy for the system python or change the documented invocation.

### 9. GAP — 2 tools cannot be pointed at any character but TERRA

*Blocks: doing for NIKA/PIP/VIRO/BRACK/RASK/MANAGER what was done for TERRA.*

`terra_check.py` and `terra_possibilities.py` name TERRA in their bodies and take no
character argument. `terra_styles.py` and `terra_wardrobe.py` accept `--character` but
still hardcode TERRA in places. The rest of the cast tooling (`cast_*.py`, `dossier.py`,
`qwen_sheet.py`, `turnaround.py`, `face_quality.py`, `realism_ladder.py`) is properly
parameterised. **No tool contains an absolute path literal** — that class of defect is
clean.

### 10. GAP — 20 of 82 templates set no style, so they silently render on animagine

*Blocks: the wizard's promise that every choice is visible.*

`argument_small_room`, `bad_news`, `chase_on_foot`, `comeback_moment`, `confession`,
`dawn_hope`, `dread_before_a_door`, `duel_standoff`, `heroic_arrival`, `horror_approach`,
`lonely_night_city`, `noir_interrogation`, `nostalgic_flashback`, `quiet_aftermath`,
`rainy_window_melancholy`, `reconciliation`, `scifi_reveal`, `slice_of_life_morning`,
`sports_climax`, `training_montage`.

Style is the field that picks the engine. `/api/compose` on an empty stack answers
*"nothing chose an engine, so this falls back to anime"*. Those twenty templates therefore
commit the user to animagine without ever showing the choice — visible on `/wizard`, where
their cards have no `style` line while the other 62 do.

### 11. GAP — 72 of 209 capability cards have no rendered panels

*Blocks: `/verify`, which reports "4 of 137 cards verified · 133 left".*

This is the already-open task #2, quantified: 72 cards carry a claim and no evidence.

### 12. NOTE — five nameless cells in the gallery

`/api/gallery` serves 1,828 entries. Five carry `demonstrates: {variable: "-", value: "-"}`
and render as a cell labelled `-` with an audio player and no name:
`voice__1785778085`, `voice__1785776842`, `music__1785776964`, `music__1785776821`,
`sfx__1785776970`. Two of them also surface on `/make` as raw numeric ids next to the
properly named cues. Separately, 1,780 of 1,828 entries have no `domain` field, which is
why the `/make` audition strip only ever sees 48.

### 13. NOTE — `/make` says 19 and shows 9

`make.html` renders `byDom[d].slice(0,9)` under a header that reports the full count. The
page reads "Voice · 19 rendered" above nine players and "Sound effect · 21 rendered" above
nine. Nothing is broken; the cap is just undisclosed.

### 14. NOTE — place-card descriptions clip mid-word

Visible on `/places`: `pine_forest` renders "*…no sightline further than the n*". The card
data is complete ("*…than the next trunk*"); the grid cell clips with no ellipsis and no
overflow. Cosmetic, but it reads as corrupt data.

### 15. NOTE — 28 of the 41 workflows are not reachable from any script

Nothing loads them; they are hand-run only. Not a defect — several are deliberately
standalone capability demos — but it is the honest size of the gap between what this box
can do and what the film pipeline can ask for: `03_qwen_image_edit`, `05_qwen_controlnet`,
`07_video_interpolate`, `09_image_upscale`, `11_ltx23_t2v_audio`, `13_sam3_segment`,
`14_birefnet_matte`, `15_acestep_v1_full`, `15_llm_prompt_studio`, `16_llm_to_image`,
`17_ltx23_t2v_upscaled`, `18_ltx_prompt_enhancer`, `19_product_composite`,
`20_ltx_audio_to_video`, `21_llm_lyrics_to_song`, `21_sdxl_anime_restyle`,
`22_qwen_edit_2511`, `23_qwen_edit_2511_fusion`, `24_hunyuan3d_mesh`, `25_triposplat`,
`26_flux2_t2i`, `27_control_maps`, `28_flux_outpaint`, `29_flux_object_removal`,
`30_vision_caption`, `31_acestep_remix`, `32_qwen_turnaround`, `33_train_character_lora`.
`healthcheck.py --json` lists them under `detail.workflows.undriven`.

### 16. NOTE — the wizard says "1 that will fight" before you have chosen anything

On a fresh `/wizard` every layer reads `—` and the rail still shows one warning. It is a
real warning (`nothing moves in this shot`) and correct in substance, but attaching a
conflict count to an empty stack teaches the user to ignore the counter.

---

## THE CHECK NOBODY HAD DONE: I LOOKED AT ALL 14 PAGES

Screenshotted with `studio/_tools/shot.py`, then opened and read. **No page has a JS
error. No page is empty, broken or misleading in layout.** The app is genuinely good —
`/cast`, `/character/TERRA`, `/styles`, `/places`, `/loras`, `/video` and `/tags` are dense,
legible and honest, and several surface their own gaps in the UI (`/dossier` prints "no
turnaround rendered" for MANAGER and RASK; VIRO's cast card carries an amber
"NO BASE_TAGS" warning; `/make` says the 3D maker "has never been run end to end on this
box, so it has nothing to show yet and that is a gap, not a styling choice").

### And one finding about the looking itself

**`shot.py`'s default full-page mode photographs lazy-loaded grids as empty boxes.** Every
image below the fold on `/wizard`, `/character/TERRA`, `/styles`, `/gallery` and `/places`
carries `loading="lazy"`, and a full-page capture never scrolls, so those images never
decode. My first pass showed the entire TERRA style comparison — 94 rows × 2 seed columns —
as blank slots, and 74 of 82 wizard template thumbnails as grey rectangles.

Neither was real. I proved it two ways: every one of the 1,303 media URLs the APIs
advertise returns 200 when fetched, and a `--viewport-only` shot of one TERRA style band
shows all the pictures present and correct.

This matters beyond one screenshot: `shot.py` exists precisely because "for most of this
project nobody has ever LOOKED at these pages", and in its default mode it can only ever
verify the fold. Anything below it comes back blank whether the app is healthy or not.
Fix: scroll the page before capture, or set `img.loading = "eager"` in the launch script.
Until then, use `--viewport-only` with a scroll and take several.

---

## WHAT IS CLEAN

Recorded so that a future audit does not re-derive it.

- **Routes.** 14 pages, 19 GET APIs, 7 POST endpoints. All 200 (or a validating 4xx). No
  200 hides a traceback or an error object. HEAD matches GET everywhere — the old
  "everything 404s to HEAD" bug is genuinely fixed and commented in `serve.py`.
- **Media.** 1,303 file paths advertised across `/api/styles`, `/api/places`, `/api/cast`,
  `/api/loras`, `/api/templates`, `/api/tags` and `/api/character/TERRA` — every single one
  fetched and served. Zero empty boxes.
- **Workflows.** All 41 parse. Zero inputs wired to a node that does not exist. Every
  literal `set_path` target in `short.py`, `epic.py`, `film.py`, `pipeline.py`,
  `cartoon.py` and `make_audio_library.py` names a node that exists with an input of that
  name. Five writes are built at runtime and are not statically checkable.
- **Movies.** All 4 `.movie` files compile, exit 0.
- **Cards.** 25 libraries, 885 JSON files, all parse. Every `id` matches its filename
  stem. `check_refs.py`: 1,925 references, 0 dangling, 1 free-text style to eyeball.
  `lora_scan.py`: 22 cards, 25 files, no orphans either way, "RESULT: clean".
- **Card counts on the pages are true.** `/styles` says "130 of 130" against 131 files —
  the extra is `_control.json`, correctly withheld. `/cast` says 7 of 7. `/loras` 22 of 22.

## RUNNING IT AGAIN

```
cd ~/shared/comfy-studio
python3 studio/_tools/healthcheck.py                 # everything
python3 studio/_tools/healthcheck.py routes defects  # just those
python3 studio/_tools/healthcheck.py --json          # for a diff between runs
```

Exit status is 1 if anything is `BROKEN`, 0 otherwise. Severities: **BROKEN** does not
work · **WRONG** works and tells you something untrue · **GAP** missing, and the app does
not claim otherwise · **NOTE** worth knowing.
