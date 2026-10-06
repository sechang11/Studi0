# Sound: score, design, and the mix

Craft notes for the sound department. Everything here was **measured on this box** with
ffmpeg on real film assets — the numbers in tables are observations, not defaults copied
from a tutorial. Where I did not measure something I say so.

Companion docs: `AUDIO.md` (which models, which nodes), `CAPABILITIES.md` (timings),
`craft/EDITING.md` (cut structure, which drives cue placement).

---

## 0. The one-paragraph version

**Music is picked by ear.** No generated music goes into a film unless the director has listened to it
and chosen it: a written brief, an audition bank (one variable at a time, the same length, the same
seed, levelled to the same loudness), a pick, then the full cue from the pick. Never a cue nobody has
heard, never tags alone, tempo and key always set, never unrelated cues crossfaded into one score
(§0.1 - the rule CLAUDE.md, §95 and METHOD.md point at, held by `method_check.py`).

Set every stem to a **loudness target**, never to a multiplier. Multipliers assume the
generator produces consistent levels; measured, none of them do — ACE-Step's output
spreads **20.5 LU**, LTX's ambience bed spreads **39 dB**. Normalise each stem with
**two-pass** `loudnorm`, mix at the bus targets in §2, duck the score under a real
narration key stem, and run **one** loudness pass at the very end with a limiter after it.
Narration wants headroom, not gain: never multiply a voice file above unity.

### 0.1 Why music is picked by ear (2026-10-01)

**What must never be heard in our work again.** THE DUEL IN THE CLEARING was scored by the fight
tools themselves (`fight._ace_cue`, `set_film.py music / sections`): ACE-Step 1.5 turbo from a tag
line alone - "epic anime battle score, fast taiko drums, driving strings, brass stabs, electric
guitar" - one take a cue, never listened to by anyone, five cues for five acts crossfaded at the act
breaks, mixed at 0.55 on top of the takes' own sound. The verdict on the film: the effects were good
(they were H3's own), the music awful, and that music never again in any project. What made it:

| fault | what it did |
|---|---|
| tempo and key never set | `_ace_cue` set the tags, the length and the seed and nothing else, so every cue of every fight film played at workflow 06's own **64 BPM in D minor** - under tags that said "fast", "frantic", "pounding" |
| a tag line of four idioms | taiko + orchestra + brass + rock guitar in one breath: the model averages them |
| one take, unheard | no audition, no second seed, nobody chose it |
| five unrelated cues stitched | each cue its own tempo, key and palette, crossfaded over 1.5 s at the act breaks |
| mixed on top of the effects | score at a fixed 0.55, one single-pass loudnorm over the lot, peaks over 0 dBFS from the generator |

**What made good music on the same model.** The Sour Pickle Cafe songs came out of ACE-Step through
the same workflow (`06_acestep_music.json`) - `~/sourpickle/style_bank.py`, `songwriter.py`: a sung
hook ("name the voice, then stop"), ONE idiom per audition with its instruments named, `bpm` and
`keyscale` set for every style, fifty 22-second auditions on one seed and one chorus, all levelled to
-16 LUFS so they A/B fairly, picked by ear, then built into full songs. The model was the same; the
process was the difference.

**The process, every film - score casting** (`studio/_tools/score_casting.py`): **auditions** (round 1, a
bank as varied as the brief allows) -> **callbacks** (rounds closer to the director's picks: new seeds, tempo
nudges, hand-written variants for a word like "heavier drums") -> a **shortlist** (kept along the way) ->
**finalists** (each built into a full piece the scene's length and mixed under its picture) -> one **cast**
into the film, the rest kept as **understudies**. Every round is a listening sheet (`sheet_r<N>.html`,
self-contained): each sample playable, its recipe and parent shown, pick / keep ticks that build the reply.
Open it in a browser (Chrome): the Claude desktop panel renders the page but does not play its audio.
First casting: the duel's 30-second fight, 2026-10-01 (`studio/samples/casting/forest-duel/the-30s/`).

The steps underneath it:

1. **A brief** per stretch of film that wants music: function, idiom, lead instrument, tempo, key or
   mode, the arc (how it starts, builds, ends), how long. One idiom.
2. **An audition bank**: 4-8 short takes (20-35 s) varying ONE thing (the idiom, or the engine, or the
   seed), same length, levelled to -16 LUFS with a limiter (peaks under -1.5 dBFS) - a level gain and a
   limiter, not loudnorm's "linear" mode, which quietly falls back to dynamic and leaves files 1.5 LU apart.
3. **The director picks** by listening. Nothing past this point is chosen by a number.
4. **The full cue IS the pick**: the exact take, made the picture's length by an edit of its own bars
   (`score_casting.py final`: the take itself if the picture is shorter; else it jumps back at a bar line
   to a matching point and loops its own music, then plays its own ending). A new render of the same recipe
   at a new length is different music - the director noticed at once (2026-10-01) - so that is only on
   request (`--fresh`). Loops are scored on the join, the repeats and the overshoot: #5 of the duel's
   casting became 3:04 by looping its whole 22 s middle 7 times; a 29 s take could only loop 11 s, 15 times.
   The director heard that 15-times loop at once ("audibly looping"). The answer is **develop**
   (`score_casting.py develop <finalist> --plan`): the finalist's own edit is covered once per arrangement
   (the cover engine below: the tune kept, every instrument re-played), each cover the edit's full length
   and in time with it to within 17 ms, and the piece moves from arrangement to arrangement at the plan's
   times - each switch on a bar line, crossfaded - so every repeat of the bars is the same tune further
   orchestrated (strings, then the full orchestra, a build, full force with choir, the climax, a soft
   piano ending), the arc on the film's acts. Close covers (denoise 0.62-0.68) change the sound only as
   much as a remix (timbre distance 64-76 against the take); bolder (0.70-0.85) 72-86 and 100, the tune
   still 0.88-0.93 - both kept as finalists (the duel's f-05, f-06) for the ear to choose.
5. **The mix**: the takes' own sound leads (H3's effects are the best sound this studio makes); the
   score goes under it and ducks under it (`set_film.py cut --duck`, `scripts/sound_dept.py`), one
   two-pass loudness at the end, a limiter after it.

### 0.2 Covers: the key told in a spelling the model plays, one pass, measured (2026-10-05)

Four rounds of TerraTheme covers kept the tune and still sounded wrong - the director: "not only did they
not sound good - something else was wrong, I can't really describe it" (and before it, "sound effect
stuff ... not musical"). Measured, three faults, none of them the tune:

| fault | what it did | the fix |
|---|---|---|
| the key told as "Ab minor" | ACE-Step 1.5 turbo plays the key it is told only for some spellings (`work/music/key_spelling_probe.py`: every black-key root, both spellings, from silence): **C#, F# (major and minor) and G# minor play true; Db, Eb, Gb, Bb either way, D#, A#, G# major and Ab minor do not** ("Ab minor" came back D major / Eb major). The tune came from the source's codes, the harmony under it from the label: phrase by phrase the covers turned to Ab major or F minor (`work/music/section_check.py`). Harmony held (below): r3 0.39-0.62, r4 0.20-0.63 - **two unrelated passages of the song score 0.53 against each other** | `score_casting.key_label()`: a key told as itself when that label plays true, else as its relative (the same notes) - Ab minor -> "G# minor", Eb minor -> "F# major", Eb major -> "C minor", Bb major -> "G minor". The recipe keeps the real key |
| two passes (`refine`) | a cover of a cover: haze between the notes, a rising sweep, a noise burst, a dull top end (spectrograms: `work/music/spec_panel.py`) - the "sound effect stuff" | one pass |
| the XL-SFT model | noisier covers (noise share 0.07-0.12 against 0.02-0.06), not fixed by CFG 7, 4 or 2 | the base turbo model |

**What works** (round 5, 12 covers, `sheet_r5.html`): `ReferenceTimbreAudio` wiring, **denoise 0.55** (0.6 for
an idiom far from the source), `strength` 0.5, one pass, the key through `key_label`: tune kept 0.82-0.92,
harmony held 0.76-0.89, one render 3 s (the whole 3:53 song in 12 s). The codes-only node
(`AceStep15SourceCodes`, `"codes": true`) is cleaner but bends a phrase in a second key centre to the told
key - kept as an option. **Speed** by `"stretch"` (rubberband before the cover, the pitch kept): 0.8 and 1.25
hold; 1.5 broke the harmony on a cut across a section change (0.47-0.55) and held on one inside a section
(0.76). **A song can move between key centres** (TerraTheme: Ab minor and Eb minor phrases, the second theme
split evenly) - measure the key of the cut (`work/music/cut_keys.py`), not the song's.

**Every cover is measured before the director hears it.** `round` stores, and the sheet shows, *tune kept*
and **harmony held**: the correlation of the source's and the cover's pitch classes over each 6 s window
(two bars at 81 BPM), the mean and the weakest window. Under ~0.7 = a phrase in the wrong harmony. Screen
two seeds per slot and let only takes without a technical fault reach the sheet (`work/music/r5_probe.py`);
which of those is good is still the director's ear.

### 0.3 Covers from the notes, not the sound (2026-10-05)

After round 5 the director: "the remixes do not sound good". Every cover so far re-coloured the recording - its
latent half-erased (denoise 0.55) and repainted - so each sample was half the old orchestra and half the new
instrument; erase more and the tune goes (from silence the codes keep the rhythm, not the tune). The same cover
engine sounded fine on THE FIRE ESPER's music (f-14 / f-15: covers of the model's own clean MiniMax take). So the
song's NOTES come out of the recording and are played again - `studio/_tools/notes_cover.py`:

| step | how | TerraTheme |
|---|---|---|
| `prepare SONG SOURCE` | stems by Hybrid Demucs (torchaudio's HDEMUCS_HIGH_MUSDB_PLUS, 319 MB, GPU in 10 s chunks, 1.6 GB VRAM, under `systemd-run --user --scope -p MemoryMax`); notes by Basic Pitch (ONNX) from the instrument and bass stems; the LEAD SHEET: the beat grid, bar lines where the bass changes pitch, the melody (the top voice of the loud notes), one chord a bar or half bar, the bass line | 3066 + 982 notes; Abm Ebm Abm Ebm B Gb E-Dbm Abm, one bar each (2.98 s, 80.75 BPM) |
| the check | the notes played plainly on piano against the recording (`_chroma` / `_harmony`) | **tune 0.87, harmony 0.93** - truer than any ACE cover (0.76-0.89) |
| `render SONG STYLE START SECS SPEED OUT` | piano (the Salamander grand) / strings / band (GeneralUser GS) at any speed - exact, nothing stretched | piano 0.91, strings 0.95, band 0.87 harmony |
| score_casting engine `notes` + `polish` | ACE-Step covers THAT render at denoise 0.6: the instruments already right, so it re-plays them for realism instead of morphing an orchestra | strings 0.89, band 0.90 |

Two traps in the transcription: **a held note re-struck in sixteenths** (TerraTheme's top line shimmers on its
long notes) read note by note is a motor rhythm, not the tune - merge same-pitch repeats into one note before
picking the top voice; and **the downbeat comes from where the bass changes pitch**, not from its long notes (it
plays eighths). Round 6 (`sheet_r6.html`, verdict pending): solo piano, strings and band polished, and the two
before the AI pass. The tools live outside the repo, in `~/music-tools` (lib: basic-pitch, pretty_midi, mido,
mir_eval, tinysoundfont; sf: Salamander Grand Piano V3, CC-BY 3.0, Alexander Holm, and GeneralUser GS; work:
each song's stems and lead sheet).

**Rounds 6-7 (2026-10-05).** The director on round 6: "this sounds 1000 times better" - and a metallic sound in
the first seconds of the two AI-polished samples only. It was the held notes: an AI pass renders a still, held note
as a steady pure tone without vibrato (evenly spaced overtones, nothing moving), most exposed in the first bar where
nothing else moves. The original never holds them still (it shimmers on them), so **a held note must MOVE in
anything the AI re-plays**: the strings bow it tremolo, the band's lead sings it with vibrato (re-striking it in
sixteenths confused the AI inside a dense band: harmony 0.71-0.85). **The polish is seed-sensitive** (one recipe
0.59-0.93 harmony across sources and seeds): screen three or four seeds and keep the best. **Layers mix styles**
(`layers`: the real piano with an AI-polished band joining at bar 9, the real piano over strings - harmony
0.92-0.94); `--mode major` plays the tune in its parallel major. **ACE-Step cannot sing words onto an existing
tune**: a cover of an instrumental never grows a voice (lyrics and a singer in the tags, denoise 0.6-1.0, strength
0.25-0.5: 2-4 % voice, none) - its codes say "instrumental"; text-to-music sings the lyrics clearly (84 % voice) on
a melody of its own (15 % on the tune's notes). Singing a given tune needs a singing synthesizer (notes + words in,
voice out) - not on the box. The codes-only wiring (`"codes": true`) crashed the shared ComfyUI on a 47.9 s source
(CUDA device-side assert, "scatter gather kernel index out of bounds") - score_casting refuses it past 30 s.

**Round 8 (2026-10-05).** The director on round 7: the piano best, the music box not bad, the rest below average;
the polished strings still metallic ("strings don't sound like strings"); the lyrics should be sung on the tune.
**The metallic sound is ACE-Step's audio codec**, not the re-play alone: the sampled strings passed through the VAE
only (encoded, decoded, nothing generated) keep their waves below ~500 Hz (coherence 0.75) and are rebuilt above
(0.40 at 0.5-1.5 kHz, 0.09 at 1.5-3 kHz, 0.01 above) - every ACE output's top end is synthesised, which a sustained
string tone gives away and a piano never went through (`sheet_r8.html` #5/#6, the ear test). Real string samples,
not a polish, are the fix for strings. **MusicGen-Melody** (Meta; the weights CC BY-NC 4.0 - NON-COMMERCIAL ONLY,
said on every card; ~/music-tools/models/musicgen-melody, 5.9 GB) writes the arrangement from scratch around the
melody (`notes_cover.py musicgen`, score_casting engine `musicgen`: the melody played alone as its guide, three
seeds, the best kept by harmony held; 30 s a take): tune 0.82-0.86, harmony 0.80-0.86. **transformers 5.x breaks
it**: the (empty) cache exists before the first step and MusicGen-Melody drops its conditioning whenever a cache
exists - prompt and melody both ignored (four prompts, two guidance scales: bit-identical takes); patched in
`cmd_musicgen` (the first step keeps the conditioning). Engine `file` puts a reference clip on a sheet (an A/B).

**Round 9 (2026-10-06).** The director on round 8: "all MusicGen sound wrong" (dropped: an old model, and the
transformers 5.x port already broken once), the GM strings "muffled, unnatural". **Recorded instruments, no AI**:
VSCO-2 Community Edition (CC0, 3.1 GB at ~/music-tools/sf/vsco) - violin, viola and cello sections, double bass,
solo violin, pizzicato, tremolo, harp - played by a small SFZ player in `notes_cover.py` (`Sfz`: regions by key and
velocity, round robins, soxr pitch shift to the key, the recording's own attack; each instrument calibrated to one
level first - raw they differ ~4x and the violins sat under the violas - then a section balance) as style
`vsco_strings`: harmony 0.83-0.86, with the piano 0.91. Two traps: `default_path` holds spaces ("Strings\Violin
Section\") and the .sfz case differs from the disk's. **Singing on the tune**: SoulX-Singer (Soul AI Lab, Feb 2026,
Apache-2.0; ~/music-tools/svs, model.pt 2.8 GB; NOT the 6.9 GB preprocess pack - the metadata is written from the
lead sheet: one WORD per note, the stressed word on the held note, the tune an octave down, a breath at each line's
end, one segment per line, `svs_meta.py`). It needs shims on transformers 5.x (LlamaConfig keywords only; LlamaAttention
takes the rotary embeddings and returns two values) and torchaudio 2.11 (no `load` - soundfile), all in `svs_run.py`,
which also loads the checkpoint weights-only. Voiced 87 % of the melody's time, 79 % of it on the note. The voice
is the model's example English prompt - a TEST voice; anything kept gets an AI-made voice. Layers can now be a
finished file (`{"file": ...}`): the singer over the real piano.

**The engines on this box:**

| engine | how | notes |
|---|---|---|
| ACE-Step 1.5 turbo | workflow `06_acestep_music.json` | ALWAYS set `bpm` and `keyscale` (node 10) - the key in a spelling it plays true (`score_casting.key_label`, §0.2); one idiom, named instruments (§7); fades past ~45 s |
| MiniMax Music 3 | ComfyUI's template `audio_minimax_music_3.json`; studio/samples/settest/work/music/music3_test.py | on disk since 2026-08-20, first wired 2026-10-01. Caption in three parts: **Global Metadata** (idiom, BPM, key, mood arc, production) -> **Vocal Details** ("No vocals at all. Fully instrumental.") -> **Arrangement** (instruments, then section by section); structure only from the lyric section tags (`[Intro]`, `[Instrumental]`, `[Outro]`...). **It does not keep the caption's tempo or key**: the duel's 155 BPM F sharp minor came back 185 BPM in C major (r2-03) and F major (r1-08) - measure a take before covering or scoring to it. Up to ~5 minutes. 34 s rendered in 26 s. It may end a piece before `max_duration` (an orchestral 34 s came back 22 s): **a piece's length comes from its structure, not from `max_duration`** - a 30-second recipe asked for 187 s came back 28 and 35 s. Measured on one instrumental recipe asked for 187 s: 4 section tags gave 28-35 s, 9 gave 64-88 s, 23 gave 134 s, 31 gave 111-134 s - it levels off near two minutes without lyrics to carry it; a form written in bars gave 72 s. `score_casting.py final` writes one tag per ~6 s and a sentence naming the whole form; a full 3-minute instrumental is still open. Peaks above 0 dBFS: limit. |
| Cover (a reimagining - Suno's word) | `score_casting.py` engine `cover`: ACE-Step 1.5's cover mode - ComfyUI's `ReferenceTimbreAudio` on the source latent sets `is_covers`, so the model's tokenizer turns the source into its 5 Hz semantic codes and the DiT plays them again | measured 2026-10-01 on TerraTheme and the duel. **From silence (denoise 1.0) the codes keep the rhythm and sections but NOT the tune**: chroma 0.46-0.54 against the source on three sources, no better than text alone (decoded, the hints themselves measure 0.75 - the ComfyUI port matches the official code line for line). **The hybrid works**: start from the source's own latent renoised (denoise 0.70-0.76 = ACE's `cover_noise_strength` 0.24-0.30) with the codes guiding the first half of the steps (`strength` 0.5): the tune and key kept (0.69-0.84) where a plain remix at the same denoise loses them (0.57) - the codes buy about 0.1 more denoise for the same tune, i.e. more of the sound re-made. 20 steps make denoise move in 0.05 steps. TerraTheme round 2 = 8 covers. ComfyUI's node also uses the source as the timbre reference (the official code uses silence), which pulls toward the source's sound; the plain tags guide the second half of the steps for that reason. **2026-10-05, superseded in part (§0.2)**: the covers above were told "Ab minor", which the model does not play true; with the key told by `key_label` and one pass, denoise 0.55 keeps the tune 0.82-0.92 and the harmony 0.76-0.89. |
| Notes (a cover from the song's notes) | `studio/_tools/notes_cover.py` (`prepare` once per song, `render` a style) and score_casting engine `notes`, `polish` for an ACE-Step pass over the render | §0.3: the recording transcribed (Demucs stems, Basic Pitch notes, a lead sheet), played again on sampled instruments - a recorded grand piano, GeneralUser GS - at any speed; nothing of the recording's sound used. TerraTheme: harmony 0.87-0.95 against the recording, polished 0.89-0.90. A song someone else wrote stays a test. |
| MusicGen-Melody (NON-COMMERCIAL) | `notes_cover.py musicgen` / score_casting engine `musicgen` | Meta's melody-conditioned model, weights CC BY-NC 4.0: tell the director whenever a take uses it. Writes the whole arrangement around the transcribed melody; 32 kHz mono, 30 s a take; seed-sensitive (best of three). Needs the first-step conditioning patch on transformers 5.x (§0.3). |
| Recorded instruments (VSCO-2 CE) | `notes_cover.py` class `Sfz`, style `vsco_strings` | a CC0 orchestral library played from the lead sheet - the strings that sound like strings (§0.3, round 9). No AI, no codec. |
| Singing (SoulX-Singer) | ~/music-tools/svs: `svs_meta.py` (lyrics on the melody's notes) -> `svs_run.py` | Apache-2.0; sings exact notes and words in a prompt voice; layered over the piano as a `file` layer. The example prompt voice is for tests only (§0.3). |
| Remix (your own recording) | `score_casting.py` engine `remix`: ACE-Step 1.5 audio-to-audio from the recording (workflow 06 + LoadAudio / VAEEncodeAudio), or ACE-Step v1 (`31_acestep_remix.json`) | the `denoise` dial: how much of the original survives, measured as chroma match on TerraTheme (2026-10-01): 0.35 -> 0.95, 0.45 -> 0.87, 0.50 -> 0.82-0.84, 0.65 -> 0.75. 2-6 s a 32 s remix. MiniMax Music 3 takes no audio. A recording's melody survives a remix: someone else's music is for tests, not for publishing. |
| H3's own audio | every H3 take | the effects for fights: keep them, lead the mix with them |
| Stable Audio 3 | workflow `10_stableaudio_sfx.json` | one-off effects (§1) |

Online, not downloaded (2026-10-01): ACE-Step 1.5 **XL-SFT** (April 2026, "peak quality"; 9.97 GB model +
8.38 GB 4B text encoder, Comfy-Org/ace_step_1.5_ComfyUI_files), HeartMuLa (Apache-2.0, moody pop/rock
songs, slow); for effects from a finished video the **LTX-2.3 Foley LoRA** (0.23 GB,
FuzzPuppy/LTX-2.3-Foley-LoRA) and Foley-Omni (MIT, video in, speech + effects + music out). The paid
orchestral specialists (AIVA, Udio) are out of scope.

**The first listening test** (`studio/samples/music3/listen/`, all at -16 LUFS): 0 the duel's score as
used; 1 ACE-Step on a J-rock fight brief with tempo and key set; 2 MiniMax Music 3 on the same brief;
3 MiniMax Music 3 orchestral. **The director's verdict: 1, 2 and 3 all great, "leaps and bounds better
than 0".** Both engines on the box are good enough once the process is right - the model was never the
problem. No more downloads for music; the XL-SFT and the Foley LoRA wait until a film needs what they add.

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
