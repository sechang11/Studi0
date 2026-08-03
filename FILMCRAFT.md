# FILMCRAFT — making films on one 5090

Written 2026-07-29 after three finished films and one 10-minute narrated feature, and
revised by four specialist audits of that feature. Everything here is measured on
**k4shix** or learned by getting it wrong first. Where a number appears, it was measured.

`README.md` and `CAPABILITIES.md` cover the hardware and the models. This covers the
**craft** — and the departments below exist because on a film this size, one pass by one
generalist misses things that are obvious to a specialist looking at one axis.

## The departments

| Doc | Owns | Read it when |
|---|---|---|
| **[craft/STORY.md](craft/STORY.md)** | structure, narration, factual accuracy, rights | before you write a shot list |
| **[craft/CINEMATOGRAPHY.md](craft/CINEMATOGRAPHY.md)** | prompts, character consistency, shot scale, style LoRAs | before you render keyframes |
| **[craft/EDITING.md](craft/EDITING.md)** | transition grammar, rhythm, assembly, xfade/concat behaviour | before you cut |
| **[craft/SOUND.md](craft/SOUND.md)** | score, sound design, the mix, loudness | before you mix |

## Which pipeline

| Script | Film shape | Length |
|---|---|---|
| `scripts/film.py` | wordless, atmospheric, Wan 2.2 | ~45 s |
| `scripts/cartoon.py` | characters + dialogue + captions, LTX i2v | ~60 s |
| `scripts/epic.py` | **narrated long-form**, all-motion, chunked assembly | 10 min+ |

`epic.py` is the one to extend. It exists because scaling `cartoon.py` up breaks in four
specific ways, each documented at the top of the file.

---

# The eight laws

Everything below cost something to learn.

## 1. Generate in the order the dependencies actually run

`cartoon.py` renders a fixed-length clip, then freezes its last frame if the dialogue
overruns. Fine for a 4-second beat. Over ten narrated minutes it would have produced
*minutes of still image* in a film explicitly required to be all-motion.

So `epic.py` inverts it: **speak every line first, measure it with ffprobe, then derive
each shot's frame count from the real duration.** Nothing ever needs padding.

This is also cheaper, which is the counter-intuitive part. LTX charges about the same for
193 frames as for 97 (13.7 s vs 13.5 s), while every extra shot costs a whole keyframe
*plus* a whole clip. Sizing shots to narration means fewer, longer shots — **less** GPU per
minute of film, not more.

## 2. A cut is the default; a dissolve is a statement

The first cut of the feature put an identical 0.4 s dissolve on all 109 boundaries. Every
boundary then carried the same weight, which reads as a mushy slideshow, and it wasted the
one transition the story was begging for.

The grammar that replaced it — full table in EDITING.md:

| | | reserved for |
|---|---|---|
| `cut` | 0 s | inside a scene. **The majority.** |
| `soft` | 0.28 s | two shots that are really one beat |
| `dissolve` | 0.70 s | scene change |
| `flash` (white) | 0.50 s | **one motif, exclusively** |
| `fade` (black) | 1.0–1.6 s | act breaks. Three in ten minutes. |

Reserve one transition for the film's central recurring event and let *nothing* else use
it. In the recap, 11 white flashes mean "we jumped era" — by the third one the audience
reads it without being told. Density matters: 13 flashes clustered at the resolution
diluted the motif; spacing them to one per ~55 s restored it.

Runs of cuts concatenate with a stream copy — frame-exact, no re-encode. **Cuts are free.**

## 3. Chain the last frame when the event is continuous

`"from_prev": true` takes the previous clip's final frame as this shot's start frame. The
motion carries through, so a `cut` between them is invisible and it reads as one unbroken
shot. Use it when one *event* spans two shots — an eruption rising then burning the sky, a
fall then an impact, a step forward then the flash that erases him. A cut there is a blink,
and a blink is relief.

It is also the only way past the ~241-frame (10 s) ceiling: chain two shots rather than
asking for an impossible clip. Don't chain more than 2–3 deep — the frame comes from
1280×704 video, not the 1664×928 keyframe, so it softens.

## 4. Faces drift; design around it or pay for it

Qwen re-invents a human face every keyframe, and a film is 100 keyframes. Ranked
solutions:

1. **Cast something with no face.** Automatons, a helmeted knight, a frog. Two of the three
   shorts did this and had zero drift.
2. **When you can't** (a recap with seven named humans), the `characters` block is the only
   lever, and how it's *worded* matters more than how much detail it has:
   - **Gender before physique.** "powerfully built prehistoric woman" rendered a man in
     every appearance; "a young woman, athletic but unmistakably female" fixed it.
   - **Never put a weapon in the block** if a shot might also put one in frame — you get
     two. Crono carried two swords in three shots.
   - **Spell out absences.** "one glowing amber optic band" produced *two glowing eyes*
     every time until the block said "no eyes and no mouth".
   - **Anchor attributes to their owner.** Two characters in one sentence let Marle's
     pendant migrate onto Crono's neck. "at her own throat" fixed it.
   - **Give hero props character blocks too.** The Epoch rendered as a car, then a Gundam,
     then a jet, because it had no block. Now it has one.
   - **Two specified items beat five.** A costume inventory is also the shape most likely
     to reproduce a copyrighted design — see law 8.
3. **Budget for a ~20 % off-brief rate** at 4 steps. It held across all three films.

## 5. A style LoRA is a palette as much as a style

The storybook-anime LoRA at 0.9 turned the recap unmistakably SNES-JRPG — and **hijacked
the palette of everything meant to be dead.** Ten shots asked for grey, colourless, ash;
they came back with blue sky, white clouds, golden hour, and in one case *grass growing
through the ruins of the apocalypse*. The control was clean: the same prompts with no style
LoRA produced 23/23 correctly bleak shots. The base model can do grey; that LoRA could not.

Two fixes, both necessary:
- **Per-act strength**, not global. 0.85 bright, 0.75 default, 0.50 for anything dead.
- **Split the style string.** One global string ending `warm hand painted background, vivid
  saturated colour, dramatic sky` is asserted over every prompt, sits last in the encoded
  text, and wins exactly where it must not. Keep named variants (`warm` / `cold` / `dark`)
  and select per shot.

Also: **make per-shot `seed` overridable.** Seeds derived from shot index mean deleting a
keyframe and re-rendering reproduces it *byte-identically* — "re-roll this shot" silently
isn't an operation. And offer a `quality` flag: 4 steps at cfg 1.0 cannot resist a strong
style block, and at cfg 1.0 the negative prompt does nothing either.

## 6. Normalise every stem; never trust a fixed multiplier

The generators' output levels vary far more than any hand-picked constant can absorb.
Measured:

| Stem | Spread across the film | Was |
|---|---|---|
| LTX's own ambience bed | **39 dB** (−51 to −12 LUFS) | one `×0.14` |
| ACE-Step music cues | **20.5 LU** | `level` 0.19–0.25, i.e. 2.4 dB of control |
| Chatterbox narration | 3.9 LU raw | `×1.9`, which **clipped all 100 lines** |

Two-pass `loudnorm` each stem to a target, then use `level` as a ±2 dB trim. Targets in
SOUND.md. Consequences of not doing it: a third of the cues inaudible, room tone erased on
quiet shots while the loudest beds fought the score — and the loudest beds were the biggest
moments in the film.

Related, all measured: `dynaudnorm` has ~1 s of context and made line-to-line spread
*worse* (3.9 → 5.8 LU), hitting the shortest, most important lines hardest. Use
`acompressor` then normalise. Never `volume` above unity on a stem that already peaks near
0 dBFS. Single-pass `loudnorm` overshot its requested true peak by ~3 dB on both finished
films — put a real `alimiter` after it. And **loudness goes last**, after the score, or the
score walks the master off target.

## 7. Silence is a tool, and it needs to be authored

Two of the strongest notes from the audits cost nothing to apply:

- **Cut the narration on the biggest image.** The death beat had a line over a white flash.
  Deleting it made that the only silent shot in the last third, which is what makes it land.
- **Cut the score dead.** The palace cue now ends exactly as Crono dies, leaving ~14 s
  unscored across the death and the fall of Zeal before the grief cue enters.

Ducking is the mechanical counterpart: at a 72 % speech duty cycle, fixed levels can't
work. Duck the score bus from a **narration-only key stem** — keying off the finished
programme tracks ambience instead of speech and wanders uselessly. Filtergraph in SOUND.md.

## 8. Adapting someone else's story: the line is expression, not facts

A plot summary is commentary and legitimate. Names of characters and places are facts. What
you must not reproduce is **protected expression**: the actual script, and the actual
character designs.

- **Write your own narration.** Don't paraphrase memorable lines closely; step around the
  most-quoted ones deliberately.
- **Evoke silhouettes, don't itemise costumes.** "a lean teenage swordsman with wild spiky
  crimson hair" is evocation. A five-item garment list is the copyrighted design written out
  longhand, and the render will reflect that. Role + silhouette + **one** signature detail.
  It also reads stronger, so this costs nothing.
- **Same rule for music.** Idiom and instrumentation are not protected; specific melodies
  and recordings are. Write cues that target the *register* of a scene — "harpsichord
  ostinato, recorder, martial snare, dorian" — and never name a track or a composer. Watch
  for prompts that stack meter + exact ensemble + lead instrument tightly enough to be a
  recipe for one specific well-known cue; loosen those.
- **Never use the original soundtrack.** Beyond the rights problem, an original score is
  the difference between a film you can publish and one you can't.

---

# Running an audit crew

Four specialists, one axis each, in parallel, on a film that is *already rendered* so
they're auditing reality rather than intentions. What made it work:

- **Give each one a single axis** and the authority to be blunt. The story editor found 12
  factual errors; the sound editor found narration clipping on every line; the
  cinematographer found the apocalypse had grass growing in it. A generalist pass had
  already missed all three.
- **Tell them to report, not patch.** Four agents editing one JSON concurrently will
  conflict. They return ranked lists; you apply centrally.
- **Forbid GPU work explicitly** if a render is in flight, or they'll contend for it.
- **Ask for a durable doc plus a ranked action list.** The doc is the compounding asset; the
  list is what you act on today.
- **Verify the headline claims yourself.** They were right nearly every time here — but
  "the ruined future has a blue sky" is a 30-second check and it governs 30 re-renders.
  One agent also corrected a false premise in its own brief, which is what you want.

## Pre-flight, in order

1. **Story** — facts checked, arc checked, no line describing what the picture shows.
2. **Narration** — generated and measured. Only now do shot lengths exist.
3. **Timeline** — computed. Anchor cues to **shot ids**, never hand-typed timecodes; shot
   lengths move the moment a line is re-rolled.
4. **Cue lengths** — set each to *span-to-next + ~6 s*. Check for **overlaps**, not just
   gaps: the first pass had 13 of 16 cue pairs overlapping by 20–40 s.
5. **Keyframes** — render, then build contact sheets and *look at all of them* before
   animating. A bad keyframe is 5 s of wasted GPU as a still and 20 s as a clip.
6. **Motion** — read every `motion` field with its keyframe open. One camera idea, one
   action. Ten fields contradicted their own frame (blowing off a door that's shut in shot).
7. **Clips** — batch-submit. On a shared box, one-at-a-time submission alternates with the
   other session and pays a 25–90 s model reload *per alternation*.
8. **Mix** — normalise stems, duck, then loudness-and-limit last.
9. **Assembly** — clear cached reels after any transition change; the cache is keyed by
   index and the index *is* the layout.

## Things that will silently lie to you

Every one of these was hit for real:

- **`ffprobe format=duration` is max(video, audio).** AAC padding makes it ~20 ms long per
  segment; summed, it pushed the final fade past the end of the film so there was no
  fade-out. Probe `stream=duration` on `v:0`.
- **`concat -c copy` exits 0 on failure.** A missing input or a resolution mismatch yields a
  truncated or garbled file and a zero exit code. Verify the frame count.
- **`acrossfade` ramps the incoming stream from silence**, so anything starting inside a
  transition is ducked — narration entered at 43 % gain at every dissolve. Lay narration as
  its own continuous track over the finished picture instead.
- **`fadeblack`/`fadewhite` do not touch audio.** The picture blinks to black and the bed
  sails through, which reads as a dropped frame rather than an act break.
- **ComfyUI increments output filenames.** Re-rendering writes `_00002_` while your code
  reads `_00001_`. Delete the old file; ComfyUI then reuses index 1.
- **The SMB share lags the server by minutes**, and sometimes never catches up inside a
  run. Read generated files over the `/view` HTTP endpoint, not off the share. A "missing"
  clip is indistinguishable from a failed job otherwise.
- **This ffmpeg build has no `-pattern_type glob`**, and a gap in a numbered sequence
  truncates it silently. Copy to sequential names.
- **fontconfig is unconfigured on Windows** and supplying a config segfaulted this build.
  Pass `fontfile=` explicitly, and escape the drive-letter colon inside filtergraphs.

## Costs, measured

| | |
|---|---|
| Keyframe, 4-step + style LoRA, 1664×928 | ~5 s (~30 s at `quality`) |
| LTX i2v clip, 1280×704, 97–209 f | 11–30 s, **near-flat in length** |
| Stable Audio sfx bed | ~1.5 s |
| ACE-Step cue, 40–70 s | 3–8 s |
| Chatterbox line | ~1.5 s |
| **10-minute narrated feature, 109 shots** | **~75 min GPU + ~15 min CPU** |
