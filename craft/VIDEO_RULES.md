# Video rules

Hard rules for how films get made here. **Add a rule every time you spot a bug.** This file
is not documentation — it is read by `studio/_tools/filmrules.py`, which checks films
against it and fails the build when a rule is broken.

## How to add a rule

Copy the block, give it the next number in its family, and write it as an instruction, not
a description. Then either point `enforced_by` at the code that guarantees it, or write a
`check` that can prove it from the file.

    ### SOUND-07 — One-line instruction in the imperative
    ```rule
    id: SOUND-07
    status: proposed          # proposed | enforced | checked | wontfix
    severity: error           # error | warning
    enforced_by: scripts/epic.py:mix       # code that makes it true, if any
    check: none                            # a filmrules.py check id, if any
    ```
    **The bug.** What you saw or heard, concretely.
    **Why it happens.** The mechanism, once known. `unknown` is an honest answer.
    **The rule.** What must always be true from now on.

`status` means:

- **proposed** — written down, nothing enforces it yet. Still useful: it is a real report.
- **enforced** — the code cannot produce a violation. The rule records *why* the code is
  shaped that way, so nobody quietly undoes it.
- **checked** — `filmrules.py` proves it from the film JSON or the finished file.
- **wontfix** — deliberately accepted, with the reason. Say so rather than deleting it.

Run it:

```bash
python3 studio/_tools/filmrules.py --list
python3 studio/_tools/filmrules.py --check films/salt_road_ep01.json
python3 studio/_tools/filmrules.py --check films/salt_road_ep01.json --output <film>.mp4
```

---

## SOUND

### SOUND-01 — No sound effect may play at full level under narration
```rule
id: SOUND-01
status: enforced
severity: error
enforced_by: scripts/epic.py:edit
check: sfx_under_speech
reported_by: user
```
**The bug.** Loud sound effects fire on top of narration, in what sounds like a separate
track that is not listening to the voice. Reported after watching THE SALT ROAD.

**Why it happens.** Effects were **baked into each picture segment** at a fixed
`volume=0.42`, and they were the one bed in the mixer never loudness-normalised — the
ambience was pinned to a measured LUFS, the score was pinned, effects were whatever Stable
Audio happened to output, times a constant. Two consequences, and the second is the real
one:

1. A fixed multiplier over an un-normalised source is not level control. Measured spread
   between Stable Audio renders is roughly 20 dB, so `0.42` meant nothing in particular.
2. Once baked into the segment, the effect lives in `[0:a]` welded to the ambience, so the
   mix pass **cannot duck it independently**. The score was sidechained under narration;
   effects structurally could not be.

**The rule.** Every bed that is not speech ducks under speech. Effects are laid as their
own normalised stem over the finished picture and sidechained against the narration stem,
never baked into a segment. Effects duck harder and sooner than score
(`threshold 0.10, ratio 8` against the score's `0.15, ratio 4`) because a pad under a word
is a mix choice and a door slam under a word is a mistake.

### SOUND-02 — Every non-speech bed must be pinned to a measured LUFS, never to a raw multiplier
```rule
id: SOUND-02
status: enforced
severity: error
enforced_by: scripts/epic.py:edit
check: none
```
**The bug.** A third of music cues were inaudible while others fought the narration.

**Why it happens.** Generative audio does not come out at a consistent level. Measured:
ACE-Step spans **over 20 LU** between a dense orchestral cue and a solo piano one; LTX's own
ambience bed spans **~39 dB** across clips (−51.2 to −12.2 LUFS). A single multiplier is
therefore wrong by up to 34 dB.

**The rule.** Normalise first, then trim with `level`. Targets: score −26, ambience −34
(−28 on shots with no narration), effects −30 LUFS.

### SOUND-03 — Narration is never baked into a picture segment
```rule
id: SOUND-03
status: enforced
severity: error
enforced_by: scripts/epic.py:edit
check: none
```
**The bug.** The first word of narration was quiet at all 31 dissolves.

**Why it happens.** `acrossfade` ramps an incoming segment's audio up from silence across
the transition, so a line starting at `LEAD=0.30` inside a 0.70s dissolve entered at 43%
gain.

**The rule.** Narration is laid as one continuous track over the finished picture. This
also means changing a line no longer requires rebuilding its segment.

### SOUND-04 — Loudness is a two-pass measurement, never an adaptive single pass
```rule
id: SOUND-04
status: enforced
severity: warning
enforced_by: scripts/epic.py:edit
check: none
```
**The bug.** Audible pumping across a long film.

**Why it happens.** A single adaptive `loudnorm` pass rides the gain across ten minutes of
alternating quiet narration and loud effects.

**The rule.** Measure, then apply. Master to −16 LUFS.

### SOUND-05 — Never send a key ACE-Step does not spell
```rule
id: SOUND-05
status: checked
severity: error
enforced_by: studio/_tools/render_job.py:keyscale
check: music_keys
```
**The bug.** 20 of 137 music jobs died in one run reporting only `failed (no result)`.

**Why it happens.** `keyscale` is a fixed 34-item combo that spells keys `Bb minor`. A cue
card written the way a musician writes — `B flat minor` — is a hard prompt-validation
error, so ComfyUI refuses the whole graph and the renderer dies before printing anything.

**The rule.** Keys come from the node's own list, read from the running server rather than
copied. Anything unmatched is dropped: an unkeyed cue is fine, a refused graph is not.

---

## PICTURE

### PICTURE-01 — A title's `scale` is a fraction of frame height
```rule
id: PICTURE-01
status: checked
severity: error
enforced_by: none
check: title_scale
```
**The bug.** `THE SALT ROAD` rendered so large that only four letters fit the frame.

**Why it happens.** `scale` is multiplied by frame height to get a font size. Written as if
it were a multiplier (`1.0`), it asks for a font the height of the picture.

**The rule.** Main titles ~0.075, subtitles and episode cards ~0.034. Anything above 0.15
is a bug, not a style choice.

### PICTURE-02 — Titles are single-line
```rule
id: PICTURE-02
status: checked
severity: warning
enforced_by: none
check: title_lines
```
**The rule.** Break a long title into two title entries with their own timing, or shorten
it. Embedded newlines are untested in the `drawtext` path.

### PICTURE-03 — Never hold a still frame to cover a long line
```rule
id: PICTURE-03
status: enforced
severity: error
enforced_by: scripts/epic.py:edit
check: none
```
**The bug.** Minutes of frozen picture in an early long-form attempt.

**Why it happens.** The short-film path pads an overrunning line with
`tpad=stop_mode=clone`, which is invisible on a 4-second beat and catastrophic over ten
narrated minutes.

**The rule.** Narration is measured first and picture is sized to fit it. If a line still
overruns, slow the picture rather than freeze it.

### PICTURE-04 — Never ask for a camera move that measured identical to static
```rule
id: PICTURE-04
status: checked
severity: warning
enforced_by: studio/_tools/roll.py
check: dead_cameras
```
**The bug.** Three camera moves do nothing at all.

**Why it happens.** `dolly_zoom`, `orbit` and `rack_focus` came back **byte-identical** to a
static render — mean absolute pixel difference exactly 0.00. They need a depth pass that
does not exist yet (open task #22).

**The rule.** Do not use them until the depth pass lands.

### PICTURE-05 — Never grade a shot with the `night` look
```rule
id: PICTURE-05
status: checked
severity: error
enforced_by: studio/_tools/roll.py
check: banned_looks
```
**The bug.** Dark inserts came back pure black.

**Why it happens.** The measured transfer curve clips rather than darkens: luma 48 → 0,
64 → 1.

**The rule.** Use `moonlit`, `noir` or `cold`. Open task #26.

---

## WRITING

### WRITE-01 — No published adventure text
```rule
id: WRITE-01
status: enforced
severity: error
enforced_by: none
check: none
```
**The rule.** Published modules are copyrighted. The furniture of the genre — the tavern
hook, the sealed door, the dragon that would rather talk — belongs to nobody. Write an
original story in the idiom.

### WRITE-02 — Never cast a voice pack that clones a real person
```rule
id: WRITE-02
status: checked
severity: error
enforced_by: studio/_tools/roll.py, studio/_tools/render_job.py
check: blocked_voices
```
**The rule.** Four packs on this box are clones of named real people. They are
`status: blocked`, never cast, never un-blocked, and a film that names one fails this check.
