# Handover — 2026-08-03, overnight session

Everything below is on the box at `~/shared/comfy-studio`, committed to git, and reachable
at **http://192.168.1.46:8777** (browse) and **http://192.168.1.46:8777/wizard** (direct a
scene). ComfyUI is on **http://192.168.1.46:8188**.

---

## The headline

**The studio layer renders now.** It never had before.

`studio/movies/derby-ep1.movie` → `compile.py` → `short.py` → a finished film:
12 beats, 17 shots, 40.3s, 1920×1080, audio duration matching video,
−10.43 LUFS / −1.08 dBTP. Output at
`~/ComfyUI/output/claude-generated/12-shorts/derby-studio-test/derby-studio-test.mp4`.

Until today `compile.py` emitted a film dict with no `sheets`, no `anime_sheets`, no
`voices` and no `music`, so any `.movie` file containing a spoken line died on
`KeyError: 'voice'` partway through a render. That gap had been reported four times and
never closed, which meant the 461 variables, 98 presets, 206 cards and the web app were
documentation of a machine that did not run.

---

## What I found (the useful part)

### 1. Variables that name a THING land. Variables that name a QUALITY don't.

Rendered the first film, built a contact sheet, and looked at it:

| set to | rendered |
|---|---|
| `place: locker room, benches, hanging jerseys` | correct locker room |
| `characters: VIRO` (number 7, teal jersey) | correct, consistent across shots |
| `look: night` | **bright daylight** |
| `look: cold` | **blown-out white** |
| `wear: 4` (torn, bloodied) | **clean uniform** |
| `mood: melancholy, defeat` | character **smiling** |

This is the whole precision problem in one table, and it generalises: the model renders
nouns, not adjectives. Which points at the fix —

### 2. Move qualities out of the prompt and into deterministic stages

The codebase already knew this for day-for-night ("Grading is deterministic; prompting is
not") but had only applied it once. Two applications today:

**`look` now actually works.** Every look preset carries a tuned ffmpeg grade string,
`compile.py` wrote one onto every beat, and `short.py` never read it — it applied one
hardcoded night chain to everything. So `night`, `cold`, `golden` and `day_for_night` all
produced the same picture. Fixed and measured:

| window | look | before | after |
|---|---|---|---|
| 0–14s | `night` | 50.0 | **50.0** (unchanged — its grade *is* the old chain) |
| 14–33s | `cold` | 81.5 | **115.5** |

The unchanged control is the point: the change is surgical, not a global brightening.

**`wear` partially fixed.** The tag was present and ignored, because character tags
described a *pristine* jersey and the damage was appended afterwards as a separate claim —
the model resolves that contradiction in favour of the earlier, more specific description.
Damage has to modify the garment noun. Character cards now carry `wear_tags` (the garment
in five states) rather than a fixed garment plus a damage suffix. Result: exhaustion, dirt
and dishevelled hair now land; "torn" and "bloodied" still don't reliably. **Partial, and I
am not claiming more.**

**`emotion` now works, and it is the clearest demonstration of the whole principle.**
`studio/emotions/` already held nine presets built from *physical* descriptors — grief is
`face: crying, grieving / eyes: tears, downcast eyes / mouth: trembling / body: hunched` —
and nothing read them. `compile.py` now expands the emotion into those parts and places
them immediately after character identity, before the garment.

The same beat that previously rendered the character **smiling** on the line "...Again."
now renders him with downcast eyes, tears on the cheeks and a downturned mouth. A second
scene set `emotion: determined` renders sharp eyes and a furrowed brow. Both match their
preset unmistakably.

`mood: melancholy, defeat` → a smile. `emotion: grief` → grief. Never write the feeling;
write the face.

Order turned out to be load-bearing: identity → face → garment-in-its-damaged-state →
world. Earlier and more specific wins when tags conflict, which is the same mechanism that
made `wear` fail.

### 3. The capability cards mostly cannot support their own claims

206 cards, 1026 panels, and not one had ever been looked at. I built one contact sheet per
card (`studio/samples/sheets/`, 134 of them) so a card can be judged at a glance, then
measured all of them two ways — difference at 160×90 (variable + recomposition) and at 16×9
(gross layout only).

**133 of 134 cards show gross compositional difference between their options.** Every panel
uses one subject sentence and one seed, but changing any token shifts SDXL's conditioning
enough to recompose the shot.

For `shot.size` that is correct — extreme_wide and extreme_close *should* be different
pictures. For `grade.grain_size` it is fatal: its four panels (fine / normal / coarse /
clumpy) are **four unrelated portraits at different framings with no visible grain
difference at all**. The card claims to show what grain looks like and shows nothing of the
sort.

So a prompt-driven panel can only demonstrate a variable whose effect *is* composition.

**The fix, demonstrated:** `studio/_tools/deterministic_panels.py` takes ONE base image and
applies the real filter from `short.py`. Two cards rebuilt this way —
`look_deterministic` (7 grades) and `shot_fx_deterministic` (8 effects). The look card is
now readable at a glance: identical stadium in all seven panels, only the grade differs.
That is what a capability card is supposed to look like.

### 4. Camera moves — measured for the first time

The reliability table in the craft docs was explicitly *inferred*; the audit recommended a
sweep and it was never run. All eight moves land and the directions are correct mirrors
(`pan_l` vs `pan_r` differ by 70.9 mean absolute pixel value at the final frame; `tilt_u`
vs `tilt_d` by 65.0; `handheld` by 6.1 against static, subtle by design).

Worth knowing *why* the first attempt failed: I swept a generated **clip**, and its own
content changed by 78.6 between first and last frame — a face becoming a ball becoming a
dust cloud — which completely swamped a ~100px camera translation. Eight panels that looked
identical. Swept against a **still** instead and the moves are unmistakable. Same lesson as
the cards: hold everything still except the one variable.

Camera is the highest-leverage thing you own, because the move is **not asked of the video
model** — it is an ffmpeg operation on the finished clip. It is exact every time.

---

## What you can do now

```bash
# direct a scene in the browser
http://192.168.1.46:8777/wizard

# or by hand
cd ~/shared/comfy-studio
python3 studio/compile.py studio/movies/derby-ep1.movie --timeline
python3 scripts/short.py studio/movies/derby-ep1.json
```

The wizard walks format → look & pace → place & time → cast → shots → review, in render
dependency order (format first because getting it wrong is only discovered at the very
end). **Every option is labelled with where it takes effect** — deterministic post, graph
parameter, prompt tag, or not implemented — because two knobs that look identical in a form
can be an exact ffmpeg operation and a suggestion to a diffusion model. That map is
`studio/effects.json`, and it cites the code that consumes each variable.

`studio/prompts/` holds 9 demo prompts with rendered samples, each declaring its **dialect**
— Animagine wants danbooru tags subject-first, Qwen wants cinematic prose, LTX wants
camera-clause-first plus a soundscape. Using one dialect on the other model is the most
expensive mistake available here: feeding Animagine Qwen-style prose returns abstract
coloured shapes.

---

## Still broken / not done

| | |
|---|---|
| `mood` | still a free-text tag and still largely ignored. Use `emotion:` instead — it is the same intent expressed as physical tags, and it works. |
| `emotion` → TTS | the face lands; `voice_style` and `voice_rate` are still not routed to the TTS engines. compile.py warns per beat rather than failing silently. |
| `wear` | partial, see above |
| `transition` | **compiles but does nothing.** short.py is all hard cuts by design; the 12 transition presets change nothing. epic.py does honour them. |
| 131 prompt-driven cards | still unverified against their own claims. The contact sheets exist now, so this is a matter of looking, not of tooling. |
| `type`, `logline`, `negative`, `blocking`, `lipsync` | parsed and dropped |
| L-cuts / J-cuts | **built** — `audio_lead` on any beat, in seconds, negative to bring a line in early; `transition: l_cut` / `j_cut` is sugar for −0.6s on the scene's first line. Off by default. See the caveat below before using it. |
| `layer.depth_map` | unblocks dolly_zoom, rack_focus, parallax and per-plane blur together. Depth Anything 3 is already installed. |
| MANAGER | has no reference sheet, so IPAdapter drops to 0.0 on his shots and his face drifts. `compile.py` warns. |

---

## Housekeeping

- **git**: 3 commits on `master`, 1648 files, no remote yet. Ready for you to
  `git remote add origin … && git push -u origin master`.
- **Repo size**: card panels re-encoded PNG → WebP, **458 MB → 30.9 MB (14.8×)**. Whole
  project is 53 MB, down from 480 MB. Full-size originals untouched in
  `~/ComfyUI/output/claude-generated/studio_cards/` (1026 files, 1.3 GB).
- **Safety fix**: `short.py` derived its output directory from the title alone, so two films
  sharing a title silently overwrote each other. Your delivered 8m46s episode was one
  `ffmpeg -y` from being replaced by a 40-second test render. It now archives to
  `<slug>.prevN.mp4`, and I backed the original up to
  `~/ComfyUI/output/claude-generated/_delivered/`.
- **`short.py` default** `COMFY_ROOT` changed from `Z:/ComfyUI` to `~/ComfyUI`, matching
  `epic.py`. Driving from the box is the reliable mode.
- **ComfyUI** was bound to `127.0.0.1` (started with `--auto-launch` rather than
  `restart-comfy.sh`), which is why it looked closed from Windows. Restarted on `0.0.0.0`.

### One thing to be aware of

Transfers from the box to the Windows machine are broken above roughly 50 KB — 50 KB
arrives, 200 KB returns nothing at all. Same root cause as the SMB share wedging. It does
not affect the box or any render; it only limited how much I could pull back to look at, so
every contact sheet is deliberately sized under 46 KB. A reboot of the Windows machine is
the fix.

---

## The one that matters most: short.py breaks the project's own Law 1

Building L-cuts turned up something bigger than L-cuts.

I added a guard that warns when two voice cues collide. It fired on the very first run:

```
!! voice overlap: VIRO runs 1.59s into MANAGER at 20.94s
```

That is **not** caused by the audio offset. VIRO's tunnel line is 4.20s long and its beat
is shorter, so the voice already spilled about 1s into the next scene — and nothing had
ever reported it. Removing the 0.6s lead leaves 0.99s of overlap.

The root cause is structural. `FILMCRAFT.md`'s first law reads:

> Generate in dependency order. Speak every line first, measure with ffprobe, then derive
> each shot's frame count from the real duration. Nothing ever needs padding.

`epic.py` does exactly that. **`short.py` does not** — it renders keyframes and clips first,
voices fourth, and sizes every shot from a fixed template (`clip_secs: 6` scaled by pace).
So any line longer than its template silently overruns into the next scene, and the fixed
`min(vd, ...)` cap only ever shortened the *caption*, never the audio.

Consequence: `audio_lead` works, but this film's timing cannot absorb it. I reverted the
example scene to a plain `cut`. Using an L-cut is only safe once shot length follows
speech length.

**The fix** is to run `voices` before `clips` in `short.py`'s stage order and derive each
beat's `clip_secs` from the measured line duration plus the documented `LEAD 0.30 + TAIL
1.15`. That is a real change to the stage graph, not a tweak, which is why I stopped at
diagnosing it rather than starting it with an hour left.

## If I had another six hours

1. **Make shot length follow speech length in short.py** (see above). It unblocks L-cuts,
   removes the pre-existing dialogue overruns, and is the project's own stated first law.
2. **Look at the 131 unverified cards** and write their verdicts from the sheets. The
   tooling is done; this is now just looking.
3. **Rebuild every post-tier card deterministically.** The two I did prove the method; the
   rest of `grade.*`, `shot.lens.*` and `anime.draw.*` are the same job.
4. **`layer.depth_map`** — one piece of work, four variables unblocked.
5. **A `--check` flag on short.py** that validates a film dict before spending an hour of
   GPU on it.
