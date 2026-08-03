# Voice — casting and directing characters

Written 2026-07-30 after the first two Berserk films came back with voices a viewer rated
1/10. Everything measured on k4shix.

## The mistake that caused it

Chatterbox ships **one** voice pack. Five characters were faked by pitch-shifting it with
rubberband — Guts at 0.70 (30% down), Zodd at 0.55 (45% down), Mira at 1.26.

**Anything past about ±10% wrecks formants.** The result does not sound like five people; it
sounds like one actor on a varispeed tape, because that is exactly what it is. Pitch
shifting is a tool for nudging a voice, never for casting one.

## The fix: IndexTTS-2

`workflows/16_indextts2_voice.json`. Two levers, and they are independent:

1. **Base voice** — `narrator_voice` on `UnifiedTTSTextNode` picks a reference clip. The
   engine clones its timbre. This is casting.
2. **Emotion** — `IndexTTSEmotionOptionsNode` exposes eight dimensions, 0.0–1.0 each,
   scaled by `emotion_alpha` on the engine node. This is directing.

```
Happy · Angry · Sad · Surprised · Afraid · Disgusted · Calm · Melancholic
```

They blend, which is the part that matters. Casca reads best as `Angry 0.3 + Afraid 0.2` —
apprehension under the anger. No single label gets there, and no amount of pitch shifting
gets anywhere near it.

**~3 s per line.** Cheaper than the Chatterbox setup it replaces.

### Working character presets

| Role | Base voice | Emotion |
|---|---|---|
| Narrator | `higgs_audio/chadwick` | Calm 0.3 + Melancholic 0.2 |
| Guts | `male/male_01` | Angry 0.5 |
| Griffith | `male/male_02` | Calm 0.7 |
| Casca | `female/female_01` | Angry 0.3 + Afraid 0.2 |

## How many base voices

**11 usable English voices** are selectable out of the box. The dropdown lists 17: minus
`none`, minus one Chinese-language clip, minus four clones of real people (below).

The `voices_examples/` folder actually holds **26** files — the whole `vibevoice/` subfolder
is not exposed in the dropdown. Five of those are English and worth having; they are copied
into `male/` and `female/` and will appear **after a ComfyUI restart**.

Beyond that the number is **unlimited**: IndexTTS-2 clones from any reference wav, so any
clip dropped into `voices_examples/male/` or `/female/` becomes a base voice.

**Adding a voice requires a restart.** The dropdown is built at node-registration time and
the value is validated server-side, so a path added since startup is rejected outright
(`value_not_in_list`) — it is not enough to copy the file in.

```
bash ~/shared/comfy-studio/scripts/restart-comfy.sh
```

Also remember the real casting space is base voice × emotion, not base voice alone. Eleven
voices is far more than eleven characters.

### Voices not to use

The pack ships reference clips labelled **Clint Eastwood, David Attenborough, Morgan Freeman
and Sophie Anderson**. Those are clones of real identifiable people. Do not cast them, in
anything, published or not. The generic voices reach the same registers — `chadwick` and
`male_02` give the measured documentary read those clips usually get reached for.

## Engines: measure the output, do not trust the status

Six engines were tested by submitting a job and checking it completed. All six reported
success. **Five of them returned 1.06 seconds of digital silence.**

| Engine | Result |
|---|---|
| IndexTTS-2 | works — and has the emotion control |
| Echo-TTS | works |
| VibeVoice · Higgs Audio · F5-TTS · CosyVoice · MOSS | **silent output, job status OK** |

This is the same failure mode as `concat -c copy` exiting 0 on a broken file. A completed
job is not a rendered asset. One line settles it:

```
ffmpeg -hide_banner -i out.mp3 -af astats=metadata=1 -f null - 2>&1 | grep "RMS level dB"
```

`-inf` means silence. Add it to any batch that generates audio, and delete what fails.

## Installation gotchas, both hit for real

1. **`descript-audiotools` is not installed by `install.py`.** IndexTTS-2 fails with
   `No module named 'audiotools'` until you add it:
   `source ~/ComfyUI/venv/bin/activate && pip install descript-audiotools`
2. **`ComfyUI/temp/` must exist.** The engine writes a scratch wav there and does not
   create the directory, so it fails with a `FileNotFoundError` on a tmp path that looks
   like a bug in the node. `mkdir -p ~/ComfyUI/temp`.

## Rules carried over from the old setup

- **Never `volume` above unity on a voice stem.** `×1.9` on files already peaking at
  −0.5 dBFS clipped all 100 narration lines in the first Berserk cut. Normalise instead.
- **Not `dynaudnorm`.** ~1 s of context; it measurably *widened* line-to-line spread
  (3.9 → 5.8 LU) and hit the shortest, most important lines hardest.
- **Narration goes on its own continuous track**, never baked into each shot — otherwise
  `acrossfade` ducks the first word at every dissolve.
- **Generate narration first and measure it**, because shot length derives from it. Changing
  the TTS engine changes line durations, which means some clips need re-rendering to fit.
