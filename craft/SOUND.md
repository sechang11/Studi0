# Sound: score, design, and the mix

Craft notes for the sound department. Everything here was **measured on this box** with
ffmpeg on real film assets — the numbers in tables are observations, not defaults copied
from a tutorial. Where I did not measure something I say so.

Companion docs: `AUDIO.md` (which models, which nodes), `CAPABILITIES.md` (timings),
`craft/EDITING.md` (cut structure, which drives cue placement).

---

## 0. The one-paragraph version

Set every stem to a **loudness target**, never to a multiplier. Multipliers assume the
generator produces consistent levels; measured, none of them do — ACE-Step's output
spreads **20.5 LU**, LTX's ambience bed spreads **39 dB**. Normalise each stem with
**two-pass** `loudnorm`, mix at the bus targets in §2, duck the score under a real
narration key stem, and run **one** loudness pass at the very end with a limiter after it.
Narration wants headroom, not gain: never multiply a voice file above unity.

---

## 1. What the generators actually hand you

Measure this for every film. It changes per film, and the mix constants that worked last
time will not work this time.

### ACE-Step 1.5 Turbo — music

Six cues from two finished films, as rendered, no post:

| cue | integrated | LRA |
|---|---|---|
| `cue1_summer` (warm JRPG town) | **−11.4 LUFS** | 1.6 LU |
| `cue2_wake` (orchestral assault) | −14.3 LUFS | 6.7 LU |
| `cue3_hymn` (sacred hymn) | −17.0 LUFS | 6.5 LU |
| `cue2_unravel` (anxious underscore) | −18.3 LUFS | 13.7 LU |
| `cue1_dread` (sustained organ pedal) | −26.2 LUFS | 7.2 LU |
| `cue3_bittersweet` (solo felt piano) | **−31.9 LUFS** | 13.9 LU |

**20.5 LU of spread.** The pattern is not random: ACE-Step renders *dense, fast, major,
percussive* material loud and *sparse, slow, solo-instrument* material very quiet. Which
means a per-cue `level` field between 0.19 and 0.25 — a 2.4 dB range — is
**noise against a 20.5 dB signal**. Two cues with identical `level` can differ by 20 dB in
the finished film. This is the single biggest thing wrong with a level-multiplier score.

> **Rule: normalise every cue before you touch its level.** `loudnorm` two-pass to a fixed
> target collapses the spread to ±1.2 LU:
>
> | cue | raw | after `I=-24:TP=-6:LRA=9` |
> |---|---|---|
> | cue1_summer | −11.4 | −24.1 |
> | cue2_wake | −14.3 | −22.4 |
> | cue3_hymn | −17.0 | −23.6 |
> | cue2_unravel | −18.3 | −22.9 |
> | cue1_dread | −26.2 | −23.1 |
> | cue3_bittersweet | −31.9 | −24.8 |
>
> 20.5 LU → **2.4 LU**, single-pass. Two-pass gets it to ±0.2 LU (§6).

After normalising, `level` becomes what it should always have been: a **relative** artistic
trim of ±2 dB around the bus target, not a guess at absolute gain.

### LTX-2.3 — the ambience bed it generates for free

`CAPABILITIES.md` says the LTX bed is "quiet, mean −35 dBFS". **That is wrong as a general
rule** and believing it will wreck a mix. Across 91 rendered clips of a 10-minute film:

| | mean level |
|---|---|
| min | −51.2 dB |
| 10th pct | −38.2 dB |
| **median** | **−24.7 dB** |
| 90th pct | −16.6 dB |
| max | **−12.2 dB** |
| spread | **39.0 dB** (stdev 8.7) |

Only **16 of 91** clips were at or below −35 dB. −35 dBFS is roughly the 15th percentile,
not the typical value.

And the variation is **not** noise — it tracks the prompt. LTX generates loud audio for
violent imagery and near-silence for still imagery:

| loudest beds | | quietest beds | |
|---|---|---|---|
| `740_death` | −12.2 | `100_dropped` | −51.2 |
| `710_full_power` | −13.3 | `460_forest` | −49.5 |
| `720_rising` | −13.8 | `200_rescued` | −45.2 |
| `350_eruption` | −14.7 | `760_washed_up` | −43.3 |
| `630_impact` | −16.0 | `140_throne` | −42.0 |

This has two consequences that matter:

1. **A fixed multiplier on the LTX bed is meaningless.** ×0.14 turns a −12.2 dB bed into
   −27.9 LUFS (loud enough to fight the score) and a −48.7 dB bed into −66.0 LUFS
   (inaudible — the shot has no room tone at all). Same constant, 38 dB apart.
2. **The loudest beds land on your biggest dramatic moments**, because those are the
   violent prompts. So exactly where you want a designed hit and a big cue to land, LTX has
   already filled the space with uncontrolled noise.

> **Rule: two-pass `loudnorm` each clip's audio to an ambience target. Never a multiplier.**
> Measured, this collapses the 39 dB spread to **0.0 dB**:
>
> | clip | raw | ×0.14 (current) | `I=-32:TP=-9` |
> |---|---|---|---|
> | `740_death` | −10.6 | −27.9 | **−32.0** |
> | `350_eruption` | −14.6 | −31.9 | **−32.0** |
> | `670_machine` | −13.9 | −31.2 | **−32.0** |
> | `010_kingdom` | −29.4 | −46.8 | **−32.0** |
> | `100_dropped` | −48.7 | −66.0 | **−32.0** |

Note the last row: normalising *raises* a silent bed by 17 dB. That is correct and
desirable — it gives every shot a consistent floor of room tone, which is what stops a
long film sounding like a slideshow of disconnected clips. If you genuinely want a shot
silent, mark it silent explicitly; do not rely on the generator having been quiet.

> **`loudnorm`'s `TP` parameter floors at −9.** For ambience and SFX targets below about
> −30 LUFS you will hit that limit; it is harmless (the peak just ends up wherever it ends
> up, far below the ceiling) but the filter errors out if you ask for `TP=-12`.

### Chatterbox — voice

Good news, and it inverts the usual assumption: **Chatterbox is the most consistent
generator in the kit.** 101 raw lines:

| | raw Chatterbox | after `rubberband` + `dynaudnorm=f=200:g=5` |
|---|---|---|
| spread | **3.9 LU** | **5.8 LU** |
| stdev | **0.66** | **0.97** |
| peaks | −4.27 … −0.43 dBFS | −3.63 … −0.14 dBFS |

**The processing chain makes consistency 47 % worse.** See §6 — this is a real defect, not
a rounding error, and it is entirely fixable.

### Stable Audio 3 — SFX

23 SFX from a finished film: mean −20.5 to −35.1 dB, peaks −13.8 to 0.0 dBFS. Roughly
15 dB of spread, same story, same fix. Also note **some SFX come back peaking at exactly
0.0 dBFS** — Stable Audio will hand you already-clipped files. Normalise, and check peaks.

---

## 2. The mix hierarchy, with working numbers

Six buses. Every target is an **integrated LUFS figure for the stem**, hit with two-pass
`loudnorm`, measured before the film-wide pass.

| bus | under narration | no narration | notes |
|---|---|---|---|
| **Narration** | **−20 LUFS, TP −4 dBFS** | — | never multiply above unity |
| **Designed SFX** | **−30 LUFS** | −24 LUFS | 10 dB under narration |
| **Hero SFX** (the 4–6 shots that must land) | −24 LUFS | −20 LUFS | +6 dB over the SFX bus |
| **LTX ambience** | **−34 LUFS** | −28 LUFS | a floor, not a feature |
| **Score** | **−26 LUFS**, ducked to −31 | −26 LUFS | duck is 5 dB, §4 |
| **Delivery** | **−16 LUFS, −1.5 dBTP** | | one pass, at the very end |

The ratios that matter, and why:

- **narration − score = 6 dB unducked, 11 dB ducked.** Feature-film dialogue typically
  sits 6–12 dB over score. Wall-to-wall narration (a recap doc runs a **72 % speech duty
  cycle** — measured: 446.6 s of narration in a 600 s film) needs the upper half of that
  range while speaking, and wants the score to bloom in the 171 s of gaps. Ducking gets you
  both from one number; fixed levels force you to pick one.
- **narration − designed SFX = 10 dB.** Enough that a sword ring or a relay click reads
  clearly as an event without competing with consonants.
- **narration − ambience = 14 dB.** Ambience is glue. If you can identify it as a sound,
  it is too loud.

### Proof the numbers work

Built from real assets — five re-levelled narration lines, a real LTX bed, a real Stable
Audio SFX, a real ACE-Step cue, ducked, summed, one delivery pass:

```
VO     −20.4 LUFS  (TP −7.0 dBTP)
AMB    −34.0 LUFS
SFX    −30.0 LUFS
SCORE  −25.9 LUFS   → ducked 5.0 dB under speech
SUM    −22.9 LUFS  (TP −5.7 dBTP)
DELIVERED  −16.2 LUFS,  −1.4 dBTP,  max −1.4 dBFS,  zero clipped samples
```

Compare the current pipeline's actual output on the two finished films:

| | integrated | true peak | LRA | clipped samples |
|---|---|---|---|---|
| `the-hollow-choir_scored.mp4` | −14.4 LUFS | **−0.3 dBTP** | 7.4 LU | 375 |
| `the-last-good-year_scored.mp4` | −15.9 LUFS | **+0.1 dBTP** | 7.3 LU | 193 |
| recommended chain | −16.2 LUFS | −1.4 dBTP | — | **0** |

---

## 3. Do not multiply voice above unity

This is the highest-impact single fix in the whole document.

A narration multiplier of `volume=1.9` applied to files that already peak at −0.5 dBFS
produces, measured on four lines:

| line | peak before | peak after ×1.9 |
|---|---|---|
| `010_kingdom` | −0.4 dBFS | **+5.19 dBFS** |
| `400_endoftime` | −0.3 dBFS | **+5.26 dBFS** |
| `690_schala` | −0.6 dBFS | **+5.00 dBFS** |
| `885_future_lives` | −0.5 dBFS | **+5.12 dBFS** |

Every line, about +5 dBFS. The float filtergraph carries it, but the **intermediate AAC
encode does not**: a controlled round trip took +5.19 dBFS in and gave **+3.48 dBFS** out
— the encoder lost 1.7 dB into its own clipping. And it is visible in the shipped
per-shot segments of a finished film:

```
_work/07_whisper.mp4   mean −18.0 dB   max 0.0 dB   histogram_0db: 277
_work/04_crusader.mp4  mean −21.0 dB   max −0.0 dB  histogram_0db: 12
```

277 samples pinned at full scale in one four-second segment. That is audible distortion on
the loudest syllables, it is **baked into the segment**, and no later `loudnorm` can undo
it — the concatenated pre-loudnorm reel measures **+3.4 dBTP with 596 clipped samples**.

> **Rule: normalise voice to a target with headroom, then mix at `volume=1.0`.**
> `−20 LUFS / TP −4 dBFS` leaves 4 dB for the delivery pass's makeup gain and the limiter
> catches the rest. If you find yourself wanting a voice multiplier above ~1.2, the stem is
> wrong, not the mix.

---

## 4. Ducking the score under narration

**Yes, duck. Fixed levels are the wrong tool** for a narrated film, for a specific reason:
a fixed level has to be simultaneously quiet enough for the 72 % of the film with speech
over it and loud enough for the 28 % without. It cannot be. Every fixed-level narrated mix
is either a score you cannot hear or narration you have to lean into.

Measured duck depth, `sidechaincompress`, keyed off a real narration stem against a
−24 LUFS bed:

| threshold | ratio | duck while speaking | duck in the gaps |
|---|---|---|---|
| 0.05 | 4 | −11.3 dB | 0.0 dB |
| 0.10 | 4 | −7.3 dB | 0.0 dB |
| **0.15** | **4** | **−5.0 dB** | **0.0 dB** |
| 0.25 | 4 | −2.4 dB | 0.0 dB |
| 0.40 | 4 | −0.8 dB | 0.0 dB |

`threshold=0.15:ratio=4` gives a clean **5 dB** duck and returns exactly to level in the
gaps. 4–6 dB is the classic amount; below 3 dB you have not made room, above 8 dB the score
audibly pumps and the audience hears the mix working.

### The key stem must be narration only

I tested the tempting shortcut — key the sidechain off the finished program (`[0:a]`,
which is narration + SFX + ambience already mixed). **It does not work.** Measured duck
depth wandered between −0.1 dB and −4.4 dB depending only on how loud the *ambience* was
in that window, with no relationship to whether anyone was speaking. A program-level key
ducks on explosions and ignores quiet dialogue — precisely backwards.

So: build a narration-only bus. You already have everything needed — a per-shot narration
file and a computed per-shot start time.

**Build it as a full-length stem while you build the segments:**

```
# for each shot with narration, at its timeline start `at`:
[k:a]adelay={int(at*1000)}|{int(at*1000)}[q{k}]
# then
[q1][q2]...[qN]amix=inputs=N:duration=longest:normalize=0,
aresample=48000,aformat=channel_layouts=stereo[vokey]
```

**Then the score stage — normalise, sum, duck, sum, one loudness pass, limit:**

```
[0:a]aresample=48000,aformat=channel_layouts=stereo[base];

# one branch per cue: cue already loudness-normalised on disk, so `level` is a ±2 dB trim
[1:a]volume=1.00,afade=t=in:st=0:d=2.5,afade=t=out:st={len-3.5}:d=3.5,adelay={at1}|{at1}[m1];
[2:a]volume=0.90,afade=t=in:st=0:d=2.5,afade=t=out:st={len-3.5}:d=3.5,adelay={at2}|{at2}[m2];
...

# sum the cues into one score bus, THEN duck the bus (not each cue)
[m1][m2]...[mN]amix=inputs=N:duration=longest:normalize=0,
aresample=48000,aformat=channel_layouts=stereo[score];

# the narration-only key
[K:a]aresample=48000,aformat=channel_layouts=stereo[vokey];

[score][vokey]sidechaincompress=threshold=0.15:ratio=4:attack=20:release=350:
              makeup=1:link=maximum[ducked];

[base][ducked]amix=inputs=2:duration=first:normalize=0[premaster]
```

then, as a **separate** pass over `[premaster]` (two-pass loudnorm needs a measurement
pass, so it cannot be one filtergraph):

```
# pass 1 — measure
ffmpeg -i premaster.wav -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null -
# pass 2 — apply linearly, then limit
ffmpeg -i premaster.wav -af "loudnorm=I=-16:TP=-1.5:LRA=11:linear=true:
      measured_I=..:measured_LRA=..:measured_TP=..:measured_thresh=..:offset=..,
      alimiter=limit=0.891:level=disabled:attack=5:release=50" ...
```

`attack=20:release=350` is deliberate: 20 ms is fast enough to catch a line's first
syllable, 350 ms slow enough that the score does not flutter between words. Do not go below
release=250 — you will hear it breathe on every comma.

`link=maximum` ducks both channels together off whichever is louder. Without it a
hard-panned narration would duck only one side of the score, which sounds like a fault.

### Two structural errors to avoid

Both are present in the current `epic.py` and both are worth calling out because they are
easy to reproduce.

1. **Music added *after* the loudness pass.** If the pipeline normalises the program to
   −16 LUFS and *then* amixes cues on top with no further control, the delivered file is
   not at spec and nothing limits it. Measured: `_nosubs` at −16.3 LUFS → `_scored` at
   −14.4 LUFS, and the true peak stayed at −0.3 dBTP with 375 clipped samples. **The
   loudness pass must be the last thing that happens to the audio**, after the score is in.
2. **No limiter at all.** A `loudnorm`-only chain misses its own true-peak target: asked
   for `TP=-1.5`, single-pass delivered **+1.6 dBTP** and **+1.4 dBTP** on the two finished
   films. `loudnorm`'s internal true-peak limiter is not a limiter. Always follow it with
   `alimiter`.

---

## 5. Loudness targets for delivery

| target | value | why |
|---|---|---|
| Integrated | **−16 LUFS** | sane for web/YouTube; YouTube normalises to ≈−14, so −16 arrives with a little headroom rather than being turned down and going flat |
| True peak | **−1.5 dBTP**, limiter at **−1.0 dBFS** | survives lossy transcode without inter-sample clipping |
| LRA | aim ≤11 LU; expect more | see below |

### Single-pass vs two-pass `loudnorm` — measured

On a real pre-loudnorm reel (−16.3 LUFS, +3.4 dBTP, 16.1 LU, 596 clipped samples):

| chain | integrated | true peak | LRA | clipped |
|---|---|---|---|---|
| `loudnorm=I=-16:TP=-1.5:LRA=11` (single) | **−15.2** | −1.3 | 13.8 | 0 |
| same + `alimiter=limit=0.891` | −15.3 | −1.2 | 13.8 | 0 |
| **two-pass `linear=true` + `alimiter`** | **−16.0** | **−1.4** | 15.9 | 0 |

Read this carefully:

- **Single-pass misses the integrated target by 0.8 dB.** Its dynamic mode is a slow AGC;
  it converges toward the target but the final integrated figure is whatever falls out.
- **Two-pass hits it exactly.** Use two-pass for anything you deliver.
- **`LRA` is a lie in both modes.** Asked for 11, got 13.8 and 15.9. `loudnorm` does not
  compress loudness range — in `linear=true` mode it cannot by definition (one fixed gain),
  and in dynamic mode it only partially does. If you need range control, compress the
  *stems* (§6), do not expect the delivery filter to do it.

### The single-pass AGC has a side effect worth knowing

Single-pass `loudnorm` over a whole film behaves as a slow AGC with a few seconds of
window. Modelled per segment, the same narration stem ends up at **−11.9 LUFS** on a shot
with a loud LTX bed and **−15.9 LUFS** on a shot with a silent one — a **4 dB swing in
narration level caused entirely by the ambience under it**. Combined with 5.8 LU of
line-to-line drift you get 8–10 dB of narration inconsistency across a 10-minute film,
which is what actually makes narration "drop out" intermittently. Normalising the stems
(§6) and using two-pass delivery removes both halves of it.

---

## 6. Voice: the chain, and what is really wrong with it

### `rubberband`, never `asetrate` — and one call, not two

`asetrate` needs the file's true sample rate. Chatterbox writes **24 kHz**; hardcoding
44100 plays every line 1.84× too fast and silently corrupts the caption timings with it.
Use `rubberband`, which is sample-rate agnostic and shifts pitch independently of tempo.

Measured, `rubberband=tempo=0.85` is accurate: a 4.584 s line came out **5.352 s**, ratio
1.1675 against a theoretical 1.17647. Fine.

**Retiming artefacts are not your problem.** I A/B'd chained (`rubberband=pitch=0.88,
rubberband=tempo=0.85`) against combined (`rubberband=pitch=0.88:tempo=0.85`) on four lines,
measuring HF energy above 5 kHz relative to overall level:

| line | raw HF ratio | chained | combined |
|---|---|---|---|
| 415_gatekey | −19.2 dB | −20.4 | −21.3 |
| 465_lucca | −16.0 dB | −17.4 | −17.1 |
| 665_gurus | −16.2 dB | −17.4 | −18.2 |
| 805_eggname | −17.6 dB | −16.9 | −17.9 |

**1–2 dB of relative HF loss, no consistent winner.** At pitch 0.88 / tempo 0.85 the
phase vocoder is doing fine and this is not worth optimising. Prefer the single combined
call anyway (one pass, marginally cheaper, less to go wrong), but do not go hunting for
artefacts here — the problem is elsewhere.

### `dynaudnorm` is the wrong tool for per-line levelling

`dynaudnorm=f=200:g=5` is a *dynamic* normaliser: it equalises loudness **within** a file
over a sliding window. It does not target an absolute loudness, so it cannot make line 40
match line 41. Measured across 100 lines it **widened** spread from 3.9 LU to 5.8 LU and
stdev from 0.66 to 0.97.

The failure is systematic, not random. `f=200:g=5` is a 200 ms frame with a 5-frame
Gaussian window — **1 second of context**. Every line shorter than about 3 s is inside its
own smoothing window and gets gained arbitrarily. The outliers are exactly the short lines:

| line | duration | shipped level |
|---|---|---|
| `610_skychange` | 1.7 s | **−20.0 LUFS** |
| `720_rising` | 1.2 s | −19.2 |
| `820_revived` | 1.1 s | −19.2 |
| `510_masamune` | 3.0 s | −19.0 |
| `230_arrest` | 2.5 s | −18.5 |
| `870_final_battle` | 1.4 s | −18.1 |
| — typical long line — | 5–7 s | −16.0 to −16.6 |

Punchy one-line beats — *"It works." "Lavos answers." "Then the sky changes."* — come out
**3–4 dB quieter than everything else.** These are the film's loudest dramatic moments and
the pipeline is whispering them.

### Crest factor is why naive normalising does not fix it

Just swapping in `loudnorm=I=-19:TP=-6` makes it *worse* for those lines. They have a high
peak-to-loudness ratio — one loud transient, little sustained energy:

| line | LUFS | peak | **crest** |
|---|---|---|---|
| `610_skychange` | −20.0 | −1.52 | **18.5 dB** |
| `510_masamune` | −19.0 | −0.48 | **18.5 dB** |
| `230_arrest` | −18.5 | −0.53 | 18.0 dB |
| `400_endoftime` | −14.8 | −0.31 | 14.5 dB |
| `690_schala` | −15.3 | −0.58 | 14.7 dB |

`loudnorm` honours `TP` above `I`. A high-crest line must be pulled down to satisfy the
peak ceiling, which starves it of loudness — `610_skychange` lands at −24.5 instead of −19.
Exactly `−20.0 − 4.5 = −24.5`, i.e. the peak reduction, not the loudness target.

### The chain that works

Reduce crest **first**, then normalise. Benchmarked on identical inputs:

| chain | spread | stdev | peak ceiling |
|---|---|---|---|
| `dynaudnorm=f=200:g=5` (current) | 2.2 LU | 0.71 | **−0.27 dBFS** (then ×1.9 → clipping) |
| two-pass `loudnorm I=-20:TP=-3` | 0.6 LU | 0.19 | −3.00 dBFS |
| `speechnorm` + two-pass `loudnorm` | 0.6 LU | 0.15 | −3.01 dBFS |
| **`acompressor` + two-pass `loudnorm`** | **0.2 LU** | **0.06** | **−3.04 dBFS** |

```
rubberband=pitch=0.88:tempo=0.85
  → acompressor=threshold=-20dB:ratio=3:attack=5:release=140:makeup=1
  → [measure]
  → loudnorm=I=-20:TP=-4:linear=true:measured_*=...
```

`0.2 LU` versus `2.2 LU`. Verified as a re-level pass over already-rendered voice files
(**no GPU needed** — this is a pure ffmpeg fix you can apply to a film that has already
been narrated): 13 lines spanning the full range of the current chain's drift, including
every short-line outlier, all landed within **0.9 LU**, and the six problem lines above all
came to exactly −20.0.

Two gotchas:

- **`acompressor` `makeup` has range 1–64** (it is a multiplier, so `makeup=1` means 0 dB).
  `makeup=0` errors out.
- **Two-pass `loudnorm`'s measurement pass must include every filter that precedes it.**
  I made this mistake and it cost real time: measuring the *unfiltered* file and then
  applying `acompressor,loudnorm=linear=true:measured_*` put lines **8 dB low**, because
  `linear=true` applies a fixed precomputed gain and the compressor had removed 8 dB it
  did not know about. Render the pre-filters to a temp file, measure *that*, then apply.

### Voice character

`pitch: 0.88, rate: 0.85` is a good documentary-narrator setting — slowing to 0.85
genuinely helps comprehension over 10 minutes and is why a 446 s narration reads as
unhurried rather than rushed. Keep it. Just be aware it multiplies runtime by 1.176, which
the shot-length maths must account for (it does, via measured durations).

---

## 7. Writing ACE-Step prompts that hit an idiom

Tags, not prose. Genre, instrumentation, mood, tempo, and an explicit
`instrumental` / `no drums` where you mean it.

### The reliability ordering

From what the model honours, most to least:

1. **Instrumentation** — very reliable. Name specific instruments and you get them.
2. **Tempo** — reliable via `bpm`.
3. **Density and register** — reliable ("sparse", "low strings", "shimmering high").
4. **Genre / idiom** — mostly reliable for well-represented idioms.
5. **Key and mode** — **unreliable.** Treat `keyscale` as a hint, not an instruction.

That last point drives real decisions. *Do not design a score around key relationships* —
a deliberate "cue 1 is A major, the finale reprises it in C major" plan will not survive
contact with the model. **Encode mode in the tags as words** ("dorian modal harmony",
"bright major key", "resolving from minor to major") where it matters, and build your
actual contrast out of **tempo, instrumentation and register**, which the model does
respect. (I have not benchmarked key accuracy on this box — this is inherited guidance;
verify by ear on the first cue of each film and adjust the tags rather than the `key`
field.)

### Structure of a good tag string

```
<function/mood>, <lead instrument + articulation>, <accompaniment>, <percussion or "no drums">,
<harmonic colour>, <emotional register>, <ensemble>, instrumental
```

Worked examples that read correctly as their idiom:

**Medieval / early-music**
```
solemn medieval fantasy theme, harpsichord ostinato, recorder and shawm melody,
martial snare drum roll, low viol drone, dorian modal harmony, old stone and lost
history, instrumental
```
Why it works: harpsichord + shawm + viol is an instrument set that cannot read as anything
else, and "dorian modal" does the tonal work that `keyscale` would not.

**Post-apocalyptic dark ambient**
```
bleak industrial post apocalyptic ambience, sparse cold analogue synthesizer pad, slow
detuned bell tolling, distant metallic clangs and machine hum, hollow cavernous reverb,
unresolved and hopeless, dark ambient, instrumental, no drums
```
Why it works: "sparse", "no drums" and "unresolved" all push toward the quiet, static
output the scene needs. Expect this to render **very quiet** (−26 to −32 LUFS) — normalise.

**Tribal / primal**
```
primal tribal theme, huge log drums and taiko, shakers and bone rattles, low bone flute
melody, unison chanting voices, pentatonic, raw and driving, prehistoric, instrumental
```
Why it works: it is the only percussion-led cue in its film, so it provides contrast by
construction. Percussion-led cues render **loud** — normalise down.

**Jazz-adjacent nocturne (the contrast cue every long film needs)**
```
sparse mysterious limbo theme, celesta and music box, walking upright acoustic bass,
brushed cymbal, distant clock ticking, curious and weightless, jazzy nocturne, instrumental
```
Why it works: an upright bass and brushed cymbal in the middle of an orchestral film is a
genuine palette change and buys the audience a rest. **Every film over 5 minutes needs one
cue that is not the same ensemble as the rest.**

**Gothic villain**
```
gothic baroque sorcerer battle, thundering pipe organ toccata, rapid harpsichord runs,
driving chromatic minor ostinato in low strings, staccato choir stabs, tritone menace,
timpani, no metallic percussion, instrumental
```

**Alien / inhuman antagonist** — deliberately *not* the same palette
```
chaotic alien final battle, atonal brass clusters, relentless polyrhythmic metallic
percussion, bowed metal and prepared piano, industrial machine hits, sub bass pulses,
granular string screams, no organ, overwhelming and inhuman, orchestral industrial,
instrumental
```
Note the negatives. If you have two villain cues, one must be **tonal and organic** and the
other **atonal and metallic**, and you must say `no organ` on the second or you will get
two cues that sound the same.

### Length: ask for scene + 6 seconds

`AUDIO.md` says generate longer than picture and trim. True, but be specific: cue duration
should be **the span to the next cue, plus about 6 s** (2.5 s in-fade overlap, 3.5 s
out-fade tail). Longer than that and you are not "safe", you are **double-scoring** — see
§8, which is a real and audible failure.

Cost is not the constraint (7.6 s of GPU per 60 s of audio), so the temptation is to
over-generate. Resist it for musical reasons, not economic ones.

### The rights line

We generate original cues that target the **instrumentation and idiom** of a reference,
never a specific melody or recording. Style and instrumentation are not protected; melodies
and recordings are. In practice:

- **Fine:** naming genre, ensemble, instruments, tempo, mood, meter, harmonic language.
- **Fine:** "in the style of 16th-century consort music", "JRPG town theme", "baroque
  toccata" — these are idioms.
- **Not fine:** naming a track, composer-plus-work, or describing a melodic contour
  precisely enough to reconstruct a known tune.
- **Watch out for:** a tag string that specifies meter *and* the exact instrument stack
  *and* the exact lead line of one famous cue. Each element is unprotected, but stacked
  tightly enough it becomes a recipe for one specific piece of music, and it also just
  reads as cheap pastiche. If a prompt names a distinctive meter plus three instruments in
  the same arrangement as a well-known cue, loosen it — you lose nothing, because the
  *feeling* comes from the ensemble and tempo, not the arrangement detail.

---

## 8. Cue placement over a long film

### Anchor cues to shot ids, not timecodes

Shot lengths derive from measured narration. Re-roll one line and every hand-typed
timecode after it drifts. `at_shot` cannot drift. This is right and every long film should
do it.

### But then check the resulting timeline, because `seconds` still has to match

Anchoring solves *where* a cue starts and says nothing about *how long* it runs. Reconstruct
the timeline and print each cue's span to the next one. On a 17-cue, 600 s film the current
manifest gave:

```
total cue seconds 1060 s into a 600 s film = 1.72x over-scored
union coverage 658 s of 600 s = 107%
unscored: one 2.2 s gap in ten minutes
```

**On average 1.7 cues are playing simultaneously at all times.** Concretely:

| overlap | what collides |
|---|---|
| 40.0 s | A-major 76 bpm pastoral theme under a C-major 118 bpm festival dance |
| 55.3 s | E-minor 54 bpm solo piano grief under C-major 72 bpm choral triumph |
| 40.2 s | E-minor 108 bpm taiko under C-minor 60 bpm dissonant brass |
| 39.7 s | C-minor 92 bpm horn build under E-minor 68 bpm jazz nocturne |
| 30.1 s | D-minor 138 bpm atonal chaos under C-major 80 bpm triumphant finale |

Two cues in different keys and tempos playing simultaneously for 40 s is not "a rich mix",
it is two pieces of music fighting. And note: **the keys and tempos in that manifest were
individually well chosen.** The overlaps are what would have made the score sound wrong.
This is the failure mode that a level audit alone will never find.

> **Rule: `seconds` ≈ (span to the next cue) + 6.** Compute the timeline, print the spans,
> set `seconds` from them. Re-check whenever narration is re-rolled.

### The last cue

A final cue longer than the film's remaining runtime gets hard-truncated by `-t`, so its
out-fade never plays and the score **stops dead at full level** while the picture fades.
Measured case: an 84 s cue starting at 560.8 s in a 600 s film — its fade was scheduled for
80.5 s in, i.e. 41 s past the end. Set the last cue to `(total − start) + 2` and make sure
the film's global fade-out is applied **after** the score is mixed in, not before.

### Leave holes

One 2.2 s gap in 600 s is wall-to-wall music. Over ten minutes, continuous score flattens
into wallpaper and the audience stops hearing it. **Plan two or three passages with no
score at all**, and put them where silence is a statement rather than a shortage.

The strongest available one is almost always **right after the worst thing happens**. Cut
the score dead on the death/impact/betrayal, hold 6–12 s of designed sound and room tone,
and bring the next cue in on the recovery. That single decision is worth more than any level
tweak in this document.

---

## 9. Sound design: 100+ SFX under an LTX bed

### Prompt only physical sources

Stable Audio renders *sound*. It cannot render "wrongness", "reverence", "malice", "quiet
dignity", "absolute indifference", "grief held in", "peace at last", "three people not
breathing", or "four places at once". Those tokens do not become nothing — they **dilute
the physical descriptors**, spending 20–30 % of the prompt on words that only add entropy.

```
BAD   An unnaturally quiet forest clearing, a single crow call, faint organ note from
      inside, wrongness
GOOD  Quiet forest clearing, one distant crow call, faint low sustained tone through
      stone walls, still air
```

Name the source, the material, the space. `wind over a headland`, `waves on rock`,
`room tone in a concrete building`, `relay clicks`, `teleprinter mechanism`.

### Do not contradict the pipeline's own negatives

If the pipeline appends `", no music, no speech"` to every SFX prompt — and it should —
then a prompt asking for *"a rising heroic chord"*, *"a soft hopeful chime"*, *"chanting
voices"*, *"mocking laughter"*, or *"distant festival music"* is fighting itself. The model
gets contradictory instructions and returns mush.

Two systemic offenders to grep for in any shot list:

- **Musical content in the SFX bus** — "chord", "note", "chime", "drone", "heartbeat",
  "choral tone", "festival music". This is the score's job, and an SFX-layer "triumphant
  chord" will collide with the actual cue in key and tempo. **Delete every one.** Sustained
  tonal atmosphere belongs in the score or in a cue's tail, not in the effects layer.
- **Vocal content** — "crowd chatter", "laughter", "murmuring", "shouting", "a scream", "a
  commanding voice", "chanting", "a held breath". Contradicts `no speech`, and worse, see
  the next rule.

### Never put babble under narration

Crowd chatter, laughter and murmuring are **speech-shaped**: same spectrum, same
modulation rate, same formants as the narrator. They mask consonants directly and no amount
of level reduction fixes it, because the masking is spectral, not loudness-based. This is
the single most reliable way to make narration unintelligible.

Replace the crowd with its **non-vocal correlates** — the sounds a crowd makes that are not
voices:

```
BAD   A busy medieval fair, cheerful crowd chatter, distant hand bell, canvas flapping
GOOD  Medieval fair, canvas awnings flapping, wooden stall shutters, hand bell, footsteps
      on packed earth, distant hubbub low and indistinct
```

"Low and indistinct hubbub" is safe; "chatter" and "laughter" are not.

Same logic bars two other beds from sitting under narration:

- **Rain and applause** — broadband noise, masks everything, worst-in-class. Keep the
  thunderclap as a discrete hit, drop the rain bed.
- **Narrow-band whines and sustained tones in the 2–4 kHz speech band** — "an old monitor
  whining", "a rising uncontrolled whine". Keep the transient (the crackle *into* life),
  drop the sustained tone.

### Do not duplicate what LTX already generated

LTX makes its ambience from the same prompt that makes the picture, so if your SFX prompt is
*also* generic ambience for that shot, you are generating the same bed twice and summing two
uncorrelated washes. That does not sound like a richer environment, it sounds like mud.

Decide per shot, using measured numbers:

| LTX bed | SFX prompt is… | action |
|---|---|---|
| ≥ −25 dB (loud) | pure ambience | **drop the SFX** — LTX has it covered |
| ≥ −25 dB (loud) | a discrete event | keep the event, delete the ambience words |
| −25 to −35 dB | pure ambience | keep, but thin it to 2–3 elements |
| ≤ −35 dB (near-silent) | anything | **keep** — LTX gave you nothing, you need a bed |

On a 91-clip film that classified as: 30 clips louder than −20 dB (drop most ambience-only
SFX), 28 quieter than −30 dB (definitely keep). The all-shots-get-SFX default is wrong in
about a fifth of cases.

### Spend the budget on the few moments that must land

A long film has maybe four to eight sounds the audience will remember. Give those a **hero
level** (§2: −24 LUFS, +6 dB over the SFX bus), a dedicated prompt, and room in the mix —
duck the score under them the same way you duck it under narration.

They are always the same kinds of moment: the eruption, the impact, the death, the portal
tearing open, the blade being reforged, the machine waking. Write those prompts as a
**shape**, not a texture — attack, body, tail:

```
An annihilating discharge of energy, everything cut to a high ringing tone, then near
silence
```

That is an excellent SFX prompt: it specifies a transient, a spectral consequence, and a
decay into nothing. It gives the editor something to cut on. Compare a texture prompt like
*"devastation on a planetary scale, roaring firestorms"* — no shape, nothing to hit a frame
with.

### Put a sound on the time gate

If the edit uses a `flash` / `fadewhite` transition as a time gate, **the transition itself
is silent** unless you plan for it. The incoming shot's SFX starts at the cut, which lands
inside the fade — so the fix costs nothing: make the incoming shot's SFX **open with the
gate hit**.

```
A bright bell-like chime and a rush of air pulled inward, then a cold damp forest at dawn,
dripping leaves, distant crows
```

On a film with 13 flash transitions this is 13 free moments of sound design. Do not leave
them silent.

---

## 10. Checklist

Before you render audio:

- [ ] Every cue's `seconds` computed from its span to the next cue, +6 s. Last cue clamped
      to the runtime.
- [ ] Cue overlaps printed and checked. Total cue seconds should be **≈1.1×** the film, not
      1.7×.
- [ ] Two or three deliberate score-free passages, one of them after the worst thing.
- [ ] No two adjacent cues share ensemble *and* tempo range. At least one cue in the film is
      a different palette entirely.
- [ ] No cue prompt names a specific piece, or stacks meter + exact instrument set + exact
      lead line of a known cue.
- [ ] SFX prompts contain no emotions, no musical chords/notes/drones, no speech or
      laughter, no babble under narration.
- [ ] SFX dropped on shots where the LTX bed is loud and the prompt was only ambience.
- [ ] Hero SFX identified and given their own level.
- [ ] Flash/gate transitions have a hit at the head of the incoming SFX.

Before you deliver:

- [ ] Every stem two-pass `loudnorm`'d to its bus target (§2). No fixed multipliers on
      anything the model generated.
- [ ] No voice multiplier above unity. Check `astats` peak on a mixed segment: if you see
      `histogram_0db` at all, you are clipping.
- [ ] Score ducked 4–6 dB off a **narration-only** key stem.
- [ ] Exactly one loudness pass, **after** the score is in, two-pass, followed by
      `alimiter`.
- [ ] Verify the delivered file: integrated within 0.5 LU of −16, true peak ≤ −1.0 dBTP,
      and `volumedetect` reports **no** `histogram_0db` line.

```bash
ffmpeg -hide_banner -nostats -i out.mp4 -af loudnorm=print_format=summary -f null - 2>&1 \
  | grep -E "Input (Integrated|True Peak|LRA)"
ffmpeg -hide_banner -nostats -i out.mp4 -af volumedetect -f null - 2>&1 \
  | grep -E "mean_volume|max_volume|histogram_0db"
```

If that second command prints a `histogram_0db` line, the mix is clipped. Go and find out
where — it is almost always a stem multiplied above unity, and it is almost always the
voice.
