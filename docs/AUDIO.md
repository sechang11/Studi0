# Sound: music, effects, and voice

Three separate problems with three separate answers. Two are solved by stock ComfyUI
plus weights; the third needs a third-party node pack.

| Need | Model | Stock ComfyUI? | Size |
|---|---|---|---|
| Music, songs with sung vocals | **ACE-Step 1.5 Turbo** | ✅ nodes built in | ~10 GB |
| SFX, ambience, sound design | **Stable Audio 3 Medium** | ✅ nodes built in | ~13 GB |
| Video with natively synced audio | **LTX-2.3 22B** | ✅ nodes built in | ~40 GB |
| **Spoken narration / voice cloning** | see below | ❌ **needs a custom pack** | 1–10 GB |

---

## 1. Music — ACE-Step 1.5

Nodes: `TextEncodeAceStepAudio1.5`, `EmptyAceStep1.5LatentAudio`, `VAEDecodeAudio`,
`SaveAudioMP3` / `SaveAudioOpus` / `SaveAudioAdvanced`.

Loaders (from `audio_ace_step_1_5_split`):

```
UNETLoader      acestep_v1.5_turbo.safetensors
DualCLIPLoader  qwen_0.6b_ace15.safetensors + qwen_1.7b_ace15.safetensors, type "ace"
VAELoader       ace_1.5_vae.safetensors
```

Templates to open: **ACE-Step 1.5 Music Generation Workflow**, **ACE-Step 1.5 AI Lyric
Song Generation** (an LLM writes the lyrics, ACE-Step sings them), **ACE-Step v1 Text to
Instrumentals Music**, **ACE Step v1 M2M Editing** (remix/extend an existing track).

Prompting is **tags plus lyrics**, not prose. The tag field wants genre/instrumentation/
mood/tempo:

```
cinematic orchestral, low strings, sparse piano, slow build, melancholic, 60 bpm, no drums
```

For a film score, generate **instrumentals** and make them longer than the picture, then
trim to the cut. Asking for exactly 45 s tends to produce something that ends abruptly.

## 2. Sound design — Stable Audio 3 Medium

Loaders (from `audio_stable_audio_3_medium`):

```
CheckpointLoaderSimple  stable_audio_3_medium.safetensors
CLIPLoader              t5gemma_b_b_ul2.safetensors     type "stable_audio"
CLIPLoader              qwen3.5_2b_bf16.safetensors     type "stable_diffusion"
```

This is the one for **wind over a headland**, **waves on rock**, **room tone in a
concrete building**, **relay clicks**, **teleprinter mechanism**. Generate each element
separately and layer them — `AudioMerge`, `AudioAdjustVolume`, `AudioEqualizer3Band`,
`AudioConcat` and `TrimAudioDuration` are all stock nodes, so you can do a basic mix
inside ComfyUI without leaving for a DAW.

For *THE LAST SIGNAL* the mix would be: one continuous ACE-Step instrumental bed, plus
per-shot Stable Audio elements (mist/wind, dust-still room tone, needle tick, storm,
mast hum, relay cascade, tape mechanism, waves + beam, wind + dawn).

## 3. Video with synced audio — LTX-2.3

Different approach: instead of generating picture and sound separately, LTX-2.3 does both
at once from one prompt (`video_ltx2_3_t2v`), or animates a still **to a supplied audio
track** (`video_ltx2_3_ia2v`) — which is how you get lip-sync and motion that hits the beat.

Everything loads from one 22 GB checkpoint: `LTXVAudioVAELoader`, `LTXAVTextEncoderLoader`
and `CheckpointLoaderSimple` all point at `ltx-2.3-22b-dev-fp8.safetensors`. It's the
heaviest thing you'll run — expect it to be tight in 32 GB alongside the Gemma-3-12B
text encoder.

---

## 4. Voice — the gap in stock ComfyUI

**Every speech node in your install is a paid cloud API**: `ElevenLabsTextToSpeech`,
`ElevenLabsInstantVoiceClone`, `ElevenLabsSpeechToSpeech`, `HeyGenTextToSpeechNode`,
`KlingLipSyncAudioToVideoNode`, `SyncLipSyncNode`. They need API keys and credits.
ComfyUI 0.28.0 ships **no local TTS**.

For on-box voice you install a custom node pack via ComfyUI-Manager. The realistic
options, all of which run comfortably on a 5090:

| Pack | Repo | Best for | Licence note |
|---|---|---|---|
| **Chatterbox** | `wildminder/ComfyUI-Chatterbox`, `ShmuelRonen/ComfyUI_ChatterBox_Voice` | Zero-shot cloning from ~10 s of reference audio, emotion/exaggeration control. Fast. | Resemble AI, MIT — cleanest licence of the group |
| **VibeVoice** | `wildminder/ComfyUI-VibeVoice`, `Enemyx-net/VibeVoice-ComfyUI` | **Long-form** narration (tens of minutes), up to 4 distinct speakers in one pass. Best for documentary VO. | Microsoft pulled the original weights from HF; packs now pull community mirrors. Check provenance yourself. |
| **IndexTTS 2** | `snicolast/ComfyUI-IndexTTS2` | Precise duration control — you can force a line to fit an exact number of seconds. Very useful for cutting to picture. | Apache-2.0 |
| **F5-TTS** | `niknah/ComfyUI-F5-TTS` | Mature, stable, zero-shot cloning. The safe boring choice. | MIT |
| **Higgs Audio v3** | `Saganaki22/Higgs_v3-TTS-ComfyUI` | Newest, most expressive; heavier. | check repo |
| **Kokoro** | `stavsap/comfyui-kokoro` | Tiny (~350 MB), fast, no cloning — fixed preset voices. Good for placeholder VO. | Apache-2.0 |
| **Piper** | `yuvraj108c/ComfyUI-PiperTTS` | CPU-only, instant, robotic. Fine for temp tracks. | MIT |

Supporting nodes worth knowing: `ComfyUI-Whisper` (transcription → auto subtitles),
`ComfyUI_FL-ClearVoice` (denoise/enhance recorded voice before cloning).

### ⚠ The install risk on this box

Your venv is **Python 3.14.6 / torch 2.13.0+cu130 / transformers 5.14.1**. That's a very
new stack, and most TTS packs still pin `transformers<5` or an older torch. A naive
`pip install -r requirements.txt` will happily **downgrade transformers and break the
stock ComfyUI nodes that depend on 5.x**, or downgrade torch and break CUDA 13 support
for the 5090.

Always install with a constraints file that forbids touching the critical packages:

```bash
printf 'torch==2.13.0+cu130\ntransformers==5.14.1\n' > /tmp/keep.txt && ~/ComfyUI/venv/bin/pip install -r <pack>/requirements.txt -c /tmp/keep.txt
```

If pip reports it cannot resolve, that pack is genuinely incompatible — **stop**, don't
force it. Better to run TTS in a separate venv and import the WAV via `LoadAudio` than to
break a working ComfyUI.

`scripts/install-tts.sh` in this kit does the constrained install and verifies that torch
and transformers survived.

---

## Mixing the film

Once you have music and SFX, `scripts/mixdown.sh` muxes an audio bed onto a finished cut:

```bash
bash scripts/mixdown.sh ~/ComfyUI/output/claude-generated/film-the-last-signal/the-last-signal_720p.mp4 score.mp3
```

It loops or trims the audio to picture length, applies a 1.5 s fade in/out, and writes
`*_scored.mp4` alongside the original. Everything stays in `claude-generated/`.
