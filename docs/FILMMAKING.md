# Making short films on one 5090

You can. The constraint is not quality — it's that **Wan 2.2 makes 5-second shots**, so
you make films the way films are actually made: shot by shot, then cut together.

## The pipeline

```bash
cd ~/shared/comfy-studio && python3 scripts/film.py films/the-last-signal.json
```

Three stages, and the staging is the whole trick:

| Stage | What | Cost (9 shots, 720p) |
|---|---|---|
| 1. keyframes | Qwen-Image renders every shot as a still | **45 s total** |
| 2. clips | Wan 2.2 animates every keyframe | ~20 min |
| 3. edit | ffmpeg: cross-dissolves, title cards, fades | ~20 s, no GPU |

**Why batch by model instead of shot-by-shot.** Qwen (19 GB) and Wan (2×13.3 GB) don't
co-reside in 32 GB. Doing shot 1 image → shot 1 video → shot 2 image → … forces a ~90 s
model reload at every switch. On a 9-shot film that's 16 swaps ≈ **24 wasted minutes**,
more than the render itself. Batching by model pays the load cost twice, total.

Every stage is resumable and skips work that already exists:

```bash
python3 scripts/film.py films/the-last-signal.json --stage clips
```

```bash
python3 scripts/film.py films/the-last-signal.json --stage edit
```

Delete a single clip from `clips/` and re-run `--stage clips` to redo just that shot.

## Workflow that actually works

1. **Preview pass at 480p.** `--res 480` renders the whole film in ~6 min instead of ~20.
   Watch it. Fix the shots that don't work. *Then* commit to 720p.
2. **Fix keyframes before animating.** A bad keyframe is 5 seconds of wasted GPU time as
   a still and 130 wasted seconds as a clip. Review the contact sheet first:
   ```bash
   cd ~/ComfyUI/output/claude-generated/film-<slug>/keyframes && ffmpeg -y -pattern_type glob -i '*.png' -vf scale=460:-1,tile=3x3 -frames:v 1 /tmp/sheet.png
   ```
3. **Re-roll individual shots by seed.** `--seed 2000` shifts every shot's seed; to redo
   one shot only, delete its keyframe and clip and re-run.
4. **Generate more than you need.** Shots are cheap at 480p. Make 14, cut 9.

## Writing a film JSON

```json
{
  "title": "THE LAST SIGNAL",
  "subtitle": "a wordless short",
  "ar": "16:9", "res": "720", "fps": 16, "seconds": 5, "transition": 0.6,
  "style": "shot on 35mm film, subtle grain, cool desaturated palette with warm practical lights",
  "shots": [
    { "id": "01_establish", "prompt": "…what the frame contains…", "motion": "…what moves…" }
  ]
}
```

- **`style`** is appended to every shot prompt. This is what holds the film together
  visually — one palette, one film stock, one lighting logic. Don't skip it.
- **`prompt`** describes the *frame*: subject, setting, light, lens. Include the focal
  length; it does more than any adjective.
- **`motion`** describes *movement only*: camera move, subject motion, ambient motion.
  Don't re-describe the scene — the keyframe already fixed it.
- **`id`** must sort alphabetically into cut order (`01_`, `02_`, …).

## Editing grammar that survives 5-second shots

The 5-second limit is a real constraint, so lean into a style that works with it:

- **Vary the scale.** Wide → interior → macro → wide. A run of same-scale shots reads as
  a slideshow; alternating scale reads as coverage.
- **One idea per shot.** One camera move, one action. Asking for a sequence of events in
  5 seconds is what produces morphing.
- **Cross-dissolves, not cuts,** when the shots weren't generated from a continuous
  space (which they never are). `transition: 0.6` s is a good default; 0.3 s feels like a
  cut, 1.2 s feels like a montage.
- **Let the audio carry continuity** — once you install ACE-Step. A single continuous
  music bed does more to make disconnected shots feel like one film than any visual trick.
- **Title and end cards are free.** `film.py` generates them with ffmpeg (no GPU). They
  also give the viewer's eye a rest between the hard cuts of generated footage.

## Getting past 5 seconds

Four options, best first:

1. **Cut two shots together.** Two 81-frame clips are cheaper *and* faster than one
   121-frame clip (129 s ×2 vs 253 s) and look better. This is just editing.
2. **`templates-6-key-frames` (Multi-Keyframe Video Stitching).** Built into your
   ComfyUI. Generate N keyframes, let the model interpolate between them. The proper
   answer for a continuous long take.
3. **`WanFirstLastFrameToVideo`** (node already installed). Give it the last frame of
   clip A as the first frame of clip B and you get a genuinely continuous move across
   two shots. Chain it for arbitrarily long takes.
4. **Raise `length`.** 121 frames = 7.6 s is about the practical ceiling before drift.

## Frame rate

Wan outputs **16 fps**, which is why generated video looks slightly stuttery. Two fixes:

- **FILM interpolation** (70 MB download): 16 → 32 fps, then set `CreateVideo.fps` to 32.
  Instantly more filmic. See [WORKFLOWS.md](WORKFLOWS.md#extending) for the node wiring.
- **Slow it down.** Retime 16 fps to 24 fps playback for a 0.67× slow-motion look that
  suits atmospheric material. Pure ffmpeg, no model needed:
  ```bash
  ffmpeg -i in.mp4 -vf "setpts=1.5*PTS" -r 24 out.mp4
  ```

## What's missing for a *finished* film

Honest list, in order of how much it would improve the result:

1. **Audio.** No music, no ambience, no SFX. ACE-Step 1.5 (~10 GB) fixes music and
   ambience; Stable Audio 3 (~8 GB) fixes SFX. This is the single largest quality gap —
   a wordless short with a score is a film, without one it's a moodboard.
2. **Frame interpolation** (70 MB) — 16 fps is the most obvious tell.
3. **Upscaling** (64 MB GAN, or 4 GB SeedVR2) — lets you deliver at 1440p from 720p
   renders instead of paying 4.3× to render 1080p natively.
4. **`WanFirstLastFrameToVideo` continuity** — no download needed, just workflow effort.
5. **Colour grading.** ffmpeg `curves`/`colorbalance`, or grade in DaVinci Resolve.
   Generated footage is flat by default and takes a grade well.

---

# Narrative shorts with characters and dialogue

`scripts/cartoon.py` is the second pipeline: characters, a story, spoken dialogue and
burnt-in captions.

```bash
cd ~/shared/comfy-studio && python3 scripts/cartoon.py films/last-light.json
```

Four stages, all resumable (`--stage keyframes|clips|voices|edit`):

| Stage | What | Cost (13 shots) |
|---|---|---|
| 1 keyframes | Qwen-Image renders every shot | ~60 s |
| 2 clips | **LTX-2.3 i2v** animates each keyframe + generates ambience | ~2.5 min |
| 3 voices | Chatterbox speaks each line, pitch-shifted per character | ~15 s |
| 4 edit | dissolves, titles, dialogue mix, captions burnt in | ~40 s |

**Total: about 6 minutes for a 56-second film with dialogue.** Using Wan for stage 2
instead of LTX would have made it ~30 minutes.

## Character consistency

The hard problem. Two things solve it:

1. A **`characters` block** whose descriptions are substituted verbatim into every shot
   prompt via `{PIP}` / `{ARCH}` placeholders. Identical wording every time — do not
   paraphrase between shots.
2. A shared **`style` string** appended to all prompts.

Then **LTX image-to-video** (`workflows/12`) animates *from that fixed keyframe*, so the
design cannot drift within a shot. This is why i2v beats t2v for character work even
though t2v is simpler: text-to-video re-invents your character every shot.

## Voices from a single TTS pack

Chatterbox ships one voice. Give each character a distinct timbre with `pitch` in the
`voices` block — `1.30` for a small robot, `0.72` for a big slow one — plus `rate` to
change delivery speed, and `exaggeration` / `cfg_weight` for performance.

⚠ Use **`rubberband=pitch=`**, not `asetrate`+`atempo`. `asetrate` needs the file's true
sample rate; Chatterbox writes **24 kHz**, and hardcoding 44100 makes every line play
1.84× too fast — which also silently corrupts the caption timings downstream. This bit me.

## Captions without speech recognition

There is no ASR installed, and you don't need any. You already know the exact dialogue,
so `cartoon.py` measures each rendered voice clip with `ffprobe` and writes the SRT from
real durations. That's frame-exact where Whisper would be guessing at text you wrote.

Captions are burnt in with `subtitles=…:force_style=…`, and `*_nosubs.mp4` is written
alongside so you can keep the clean plate or use the `.srt` as a soft-sub track.

If a line is longer than its shot, `cartoon.py` freezes the last frame for the shortfall
(`tpad=stop_mode=clone`) rather than re-rendering — cheap, and these shots are near-static.

## What makes the difference between films 2 and 3

`last-light.json` worked but felt slack. `carriage-seven.json` fixes five specific things,
and they are worth copying:

**1. Vary shot length.** LAST LIGHT used one duration for all 13 shots, which reads as a
metronome. Set `seconds` per shot: 5 s to establish, 2 s for a clue insert, and a run of
**four consecutive 2 s shots** for the action beat. LTX rounds to 8n+1 frames, so at 24 fps
you get 49 / 73 / 97 / 121 frames for 2 / 3 / 4 / 5 seconds.

**2. Write subtext, not exposition.** LAST LIGHT: *"The lamp went out. She needs the light!"* —
that states the plot. CARRIAGE SEVEN: *"Doors open every night. Nobody ever gets off."* — same
information, delivered as an observation. The Keeper never explains itself; it just says
*"The nine forty is always busy. Always."* and the audience does the work.

**3. Add a designed SFX layer.** Give any shot an `sfx` string and Stable Audio 3 generates
it, layered over LTX's own ambience at a lower level. LTX produces *a* soundscape but it has
no idea what a brass ticket punch sounds like. 16 named effects is the difference between a
cut that sounds generated and one that sounds designed.

**4. Use multiple music cues.** A `music` array with `at` timecodes. One 90-second bed cannot
be tense during the investigation and warm at the reveal. Three cues can — noir underscore at
0 s, an action cue at 40 s, a tender resolution at 64 s. Each fades in and out so consecutive
cues overlap instead of cutting.

**5. Filter a voice.** Any character can carry a `filter` field — an arbitrary ffmpeg chain.
`highpass=f=450,lowpass=f=2900,acrusher=bits=7:mode=log` turns Chatterbox's single voice
into a radio dispatch. Set `radio: true` and its captions render in italics, which is the
standard subtitle convention for an off-screen voice.

### Structure for a mystery

Clue → contradiction → escalation → reveal that recontextualises. CARRIAGE SEVEN drops three
physical clues (a child's drawing, obsessive tally marks, footprints that stop at a blank
wall), then has DISPATCH contradict the evidence (*"there is no track past the junction"*),
then turns that dread into an action run, and finally reveals the thing chasing him is not a
threat at all — it is a station robot still punching tickets for passengers who stopped
coming in 1987. The menace becomes grief. That turn is the whole film.

---

# Doing a Pixar-style short

`films/puddle.json` is a deliberate style flip from the noir. Three things define it:

**1. Wordless.** Real Pixar shorts (*Piper*, *Presto*, *For the Birds*, *La Luna*) have no
dialogue. The story is carried by action, reaction shots and music. `cartoon.py` handles a
film with no `line` fields: it skips the voice stage entirely and, because there are no
caption cues, skips the subtitle burn too — the scored cut is the deliverable. Character
"voice" becomes `sfx` instead: *"tiny high-pitched anxious duckling peep"*.

**2. High-key, warm, saturated.** The inverse of the noir style block. The load-bearing
phrases are `appealing stylized character design`, `oversized expressive glossy eyes`,
`subsurface scattering`, `soft ambient occlusion`, `warm high-key golden hour lighting`,
`feature animation render`. Drop *oversized expressive eyes* and it stops reading as Pixar
and becomes generic CGI.

**3. Comedy timing is shot length.** Setup (3 s) → action (2 s) → **reaction (2 s)**. The
reaction shot is where the joke actually lands. PUDDLE runs setup/gag/reaction three times
with escalating failure before the turn.

## ⚠ The trap: a strong style block hijacks your staging

This cost the most time on PUDDLE. An "appealing character design" style is so dominant
that Qwen collapsed **6 of 22 shots** into the same front-facing cute portrait. The aerial
scale gag, the pole-vault strain, the mid-air arc and a screaming-terror reaction all came
back as the duckling standing placidly, facing camera, smiling.

Three fixes, in order of effect:

- **`"quality": true` per shot.** Swaps the 4-step Lightning LoRA for the 20-step path.
  4 steps has far too little prompt adherence to resist a strong style block. Costs ~30 s
  instead of ~4.5 s and it is the single biggest win.
- **`"neg": "..."` per shot.** The only reliable way to say *"not the default pose"*:
  `facing camera, standing still, smiling, portrait, centred`. For an emotional beat you
  must negate the *default emotion* — `smiling, happy, grinning, cheerful` — or you get a
  cheerful duckling in a shot captioned "horror".
- **Lead with the camera and action, put the character description last.** `{DUCKLING}`
  expands to a long appearance description; if that lands early it dominates everything
  after it. Open with *"Strict side-on profile view, camera at ground level, subject seen
  entirely from the side…"* and only then name the character.

Also: for a wide shot where the character should be a speck, **omit the character
description entirely** and negate close-ups (`close-up, character portrait, detailed face,
eyes`). Describing a subject in detail guarantees the model renders it large.

And watch for **duplication** — the pole-vault shot produced two ducklings twice before
`two ducklings, duplicate character, twins, pair, group` in the negative fixed it. A
per-shot `"seed"` field lets you re-roll one shot without disturbing the others.

---

# 2D anime, and going long

`films/her-name.json` is 58 shots and 3:07 — four times the length of anything before it.
Two separate problems: holding a 2D style, and holding an audience.

## Holding 2D

Qwen's default for a detailed figure is a 3D render, and it drifts back toward one within
a few shots. Three things keep it flat:

- **In the prompt:** `2D anime key visual, crisp black ink linework, flat cel shading with
  hard-edged shadows, hand-painted matte background art`.
- **In the negative, on every single shot:** `3d render, photorealistic, cgi, octane
  render, unreal engine`. Use the film-wide **`neg_all`** field for this — a per-shot
  negative is not enough, it has to be on all of them.
- **`"step_print": 12`.** Decimates the finished cut to 12 distinct frames per second.
  Hand-drawn animation is shot "on twos", and that stepped cadence is a large part of why
  anime does not read as live action. Only use this on a 2D style; on the 3D films it
  reads as dropped frames.

**LTX preserves 2D better than expected** — ink lines and cel shading survive i2v cleanly,
with only hair, cloth and particles moving. Test one shot before committing to fifty, but
it works.

## Holding an audience for three minutes

The 72-second first cut of this film failed, and it is worth being precise about why: it
was **one emotional note**. Grim at the start, grim at the end. The sister the whole story
turns on existed only as two half-second bleached flashes. An audience cannot feel a loss
it was never given anything to lose.

What fixed it was not more plot. It was **spending the first third on warmth**:

1. **Give them the thing before you take it.** Act 1 has no ash, no armour, no sword —
   a village at harvest, a sister braiding hair, a shared apple, a small brother chasing
   chickens. ~60 seconds of nothing happening, on purpose.
2. **Let the lost character speak, once.** Mira has a single line in the whole film. It is
   the only time you hear her, and it is her last.
3. **Make the payment an image they have already seen.** The memory that burns at the
   climax is the *same shot* as the memory that burns at the bargain, pushed closer and
   destroyed completely. Reusing the frame is the point.
4. **Give the theft a reaction shot.** One tight, silent close-up of the character's face
   at the instant it is taken — grief crossing her features and finding nothing to attach
   to. Three seconds, no music. It is the smallest shot in the film and the worst.
5. **Plant an object; pay it off at the end.** A crimson cord tied on a wrist in Act 1,
   greyed with ash, still there through the fight, and at the very end she turns it over
   with total incomprehension and keeps it anyway. **The viewer remembers what it is. The
   character does not.** That gap is the whole film.

Point 5 is the one that does the work. Give the audience a piece of knowledge the
protagonist has lost and they will supply the emotion themselves.

## Practical notes for a 58-shot film

- **Reuse shot IDs when restructuring.** `cartoon.py` keys resume on `id`, and shot order
  comes from array position — so you can reorder freely and insert new shots around
  existing ones without re-rendering a thing. Extending this film from 23 to 58 shots
  reused all 23 originals.
- **Budget it:** 58 keyframes (28 at 20 steps) ≈ 25 min, 58 LTX clips ≈ 30 min, 52 SFX
  ≈ 9 min, 5 music cues ≈ 30 s, 7 voice lines ≈ 25 s, edit ≈ 4 min.
- **The box is shared.** Another session queued 57 LTX jobs mid-render and ComfyUI is
  FIFO, so everything stalled behind it. Do not kill someone else's queue — make every
  stage resumable and let it drain. `scripts/_run_hername.sh` is the pattern: loop each
  stage until the expected file count exists.
- ⚠ **Kill the runner, not just the python.** A launcher that only kills `cartoon.py`
  leaves the parent retry loop alive, and relaunching gives you **two runners racing
  through the same stages** — one ran `--stage audio` while the other ran `--stage sfx`
  against the same folder. `scripts/_launch_hername.sh` kills both, then verifies exactly
  one is running.

## Examples

| Film | Shots | Length | Notes |
|---|---|---|---|
| `films/the-last-signal.json` | 9 | 45.6 s | wordless, Wan 2.2, one music bed |
| `films/last-light.json` | 13 | 56 s | 2 characters, 7 lines, uniform 4 s shots |
| `films/carriage-seven.json` | 22 | 76.7 s | noir mystery, 3 voices, 16 SFX, 3 cues, variable cuts |
| `films/puddle.json` | 22 | 59 s | Pixar style, wordless, 22 SFX, per-shot negatives |
| `films/her-name.json` | 58 | **3:07** | **2D anime, 3 acts, 52 SFX, 5 cues, `neg_all` + `step_print`** |

All render into `output/claude-generated/11-short-film/`.

## Cost

CARRIAGE SEVEN, the largest of the three, at 1280×704:

| Stage | Time |
|---|---|
| 22 keyframes | ~1.5 min |
| 22 LTX i2v clips (with audio) | ~6 min |
| 16 sound effects | ~30 s |
| 3 music cues | ~14 s |
| 9 voice lines | ~1.5 min |
| Edit, mix, captions (CPU) | ~1 min |
| **Total** | **~11 min** |
