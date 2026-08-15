#!/usr/bin/env bash
# fetch-ltx25.sh - the five gated LTX-2.5 files, with the HF token read from
# ~/.cache/huggingface/token (or $HF_TOKEN). Never pass a token on the command line.
set -u
TOK="${HF_TOKEN:-$(cat ~/.cache/huggingface/token 2>/dev/null || true)}"
[ -n "$TOK" ] || { echo "no HF token: see docs/LTX25-RUNBOOK.md" >&2; exit 2; }
cd ~/ComfyUI/models || exit 1
mkdir -p latent_upscale_models
get(){ d=$1; f=$2; u="https://huggingface.co/Lightricks/LTX-2.5/resolve/main/$3"
  if [ -s "$d/$f" ] && [ "$(stat -c%s "$d/$f")" -gt 1000000 ]; then echo "have $f"; return; fi
  echo "get $f"; curl -L --retry 5 -C - -H "Authorization: Bearer $TOK" -o "$d/$f.part" "$u" \
    && [ "$(stat -c%s "$d/$f.part")" -gt 1000000 ] && mv "$d/$f.part" "$d/$f" \
    || { echo "FAILED $f (gated? token valid? licence accepted?)" >&2; head -c 300 "$d/$f.part"; echo; return 1; }
  ls -la "$d/$f"; }
get diffusion_models ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors diffusion_models/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors
get text_encoders gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors text_encoders/gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors
get vae ltx-2.5-video-vae-bf16.safetensors vae/ltx-2.5-video-vae-bf16.safetensors
get vae ltx-2.5-audio-vae-bf16.safetensors vae/ltx-2.5-audio-vae-bf16.safetensors
get latent_upscale_models ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors
echo "done - now: python3 studio/_tools/model_cards.py && python3 studio/_tools/ltx25_probe.py"
