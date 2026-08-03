#!/usr/bin/env bash
# fetch-models.sh - download model tiers into ~/ComfyUI/models
#
#   bash fetch-models.sh utility   #  1.5 GB  upscale + interpolation + matting + segmentation
#   bash fetch-models.sh audio     # 10   GB  ACE-Step 1.5 Turbo (text -> music/song)
#   bash fetch-models.sh t2v       # 30   GB  Wan 2.2 text-to-video 14B
#   bash fetch-models.sh zimage    # 11   GB  Z-Image Turbo (fast ideation T2I)
#   bash fetch-models.sh anime     # 14   GB  Illustrious XL + Animagine XL (anime-native SDXL)
#   bash fetch-models.sh ipadapter #  2.5 GB  IPAdapter face models (character consistency on SDXL)
#   bash fetch-models.sh seedvr    #  4   GB  SeedVR2 diffusion upscaler (image + video)
#   bash fetch-models.sh control   #  2   GB  Depth Anything 3 + SDPose
#   bash fetch-models.sh edit2511  # 21   GB  Qwen-Image-Edit 2511 + 4-step Lightning LoRA
#   bash fetch-models.sh hunyuan3d #  7   GB  image -> 3D mesh (Unity/Blender ready)
#   bash fetch-models.sh ltxcontrol#  2   GB  LTX-2.3 IC-LoRA control + ID-LoRA identity lock
#   bash fetch-models.sh flux2     # 53   GB  FLUX.2 dev fp8 - second aesthetic
#   bash fetch-models.sh hunyuanvid# 50   GB  HunyuanVideo 1.5 720p T2V+I2V+1080p SR
#   bash fetch-models.sh quickwins # 35   GB  control+ltxcontrol+edit2511+hunyuan3d+seedvr
#   bash fetch-models.sh bigmodels #103   GB  flux2 + hunyuanvideo
#   bash fetch-models.sh tier1     # utility + audio + t2v
#   bash fetch-models.sh list      # show what is already installed
#
# URLs come from the workflow templates shipped with ComfyUI 0.28.0 / templates 0.11.17.
# Re-running is safe: curl -C - resumes, and finished files are skipped.
set -uo pipefail

M="${COMFY_MODELS:-$HOME/ComfyUI/models}"

# Hugging Face throttles unauthenticated downloads intermittently. Observed on this box
# on 2026-07-29: mostly 50-80 MB/s, but one sustained stretch of ~2 MB/s across both curl
# and hf-xet, which recovered on its own. A free read token raises the limits and makes
# this less likely; it is not required.
#
#   1. https://huggingface.co/settings/tokens -> New token -> type "Read"
#   2. echo 'export HF_TOKEN=hf_xxxxxxxx' >> ~/.bashrc && source ~/.bashrc
#
# Nothing here writes or logs the token; it is only forwarded to huggingface.co.
# If a transfer crawls, it is usually the Hub, not your link - the retry logic below
# will keep resuming, so leaving it running is normally the right move.
if [[ -n "${HF_TOKEN:-}" ]]; then
  echo "using HF_TOKEN (authenticated)"
  AUTH=(-H "Authorization: Bearer $HF_TOKEN")
else
  echo "NOTE: no HF_TOKEN set - transfers may intermittently throttle. See top of script."
  AUTH=()
fi

HF_CLI="$HOME/ComfyUI/venv/bin/hf"
STAGE="${TMPDIR:-/tmp}/hf-stage"

remote_size() { # echo the Content-Length for a URL, or nothing
  curl -sIL --max-time 25 "${AUTH[@]}" "$1" 2>/dev/null \
    | awk 'BEGIN{IGNORECASE=1} /^content-length:/{v=$2} END{gsub(/\r/,"",v); print v}'
}

get() { # get <dest-subdir> <url> [rename]
  local dir="$M/$1" url="$2" name="${3:-$(basename "$2")}"
  mkdir -p "$dir"

  # A non-empty file is NOT proof of a complete file - an interrupted download
  # leaves a valid-looking partial that silently fails to load later. Compare
  # against the remote Content-Length before deciding to skip.
  if [[ -s "$dir/$name" ]]; then
    local have want
    have=$(stat -c%s "$dir/$name")
    want=$(remote_size "$url")
    if [[ -z "$want" || "$have" == "$want" ]]; then
      printf '  = %-58s (present)\n' "$1/$name"
      return 0
    fi
    printf '  ~ %-58s (partial %s/%s - refetching)\n' "$1/$name" "$have" "$want"
    rm -f "$dir/$name"
  fi
  printf '  > %-58s\n' "$1/$name"

  # Prefer the hf CLI: hf-xet does parallel chunked transfer, which is far faster
  # than a single curl connection when the Hub throttles per-connection (observed
  # 2 MB/s on curl vs ~50 MB/s here for the same host).
  if [[ -x "$HF_CLI" && "$url" == https://huggingface.co/*/resolve/* ]]; then
    local rest="${url#https://huggingface.co/}"
    local repo="${rest%%/resolve/*}"
    local path="${rest#*/resolve/}"; path="${path#*/}"   # strip the revision segment
    mkdir -p "$STAGE"
    if "$HF_CLI" download "$repo" "$path" --local-dir "$STAGE" >/dev/null 2>&1; then
      mv -f "$STAGE/$path" "$dir/$name" && return 0
    fi
    echo "  .. hf download failed, falling back to curl" >&2
  fi

  # --speed-limit/--speed-time abort a stalled transfer so --retry can resume it.
  # Without them curl will sit on a dead HF connection forever.
  local try
  for try in 1 2 3 4 5; do
    if curl -fL -C - --retry 5 --retry-delay 5 --retry-all-errors \
            --speed-limit 51200 --speed-time 60 \
            --connect-timeout 30 --no-progress-meter "${AUTH[@]}" \
            -o "$dir/$name" "$url"; then
      return 0
    fi
    echo "  .. stalled/failed (attempt $try), resuming in 10s" >&2
    sleep 10
  done
  echo "  !! FAILED after 5 attempts: $name" >&2
  return 1
}

HF=https://huggingface.co

utility() {
  echo "== utility (~1.5 GB) =="
  get upscale_models      "$HF/Comfy-Org/Real-ESRGAN_repackaged/resolve/main/RealESRGAN_x4plus.safetensors"
  get frame_interpolation "$HF/Comfy-Org/frame_interpolation/resolve/main/frame_interpolation/film_net_fp16.safetensors"
  get background_removal  "$HF/Comfy-Org/BiRefNet/resolve/main/background_removal/birefnet.safetensors"
  # SAM 3.1 MUST land in checkpoints/ - it is loaded by CheckpointLoaderSimple, which does
  # not look in detection/. This originally fetched to detection/ and the model was invisible
  # to ComfyUI until a symlink was added. The template's own metadata says "checkpoints".
  get checkpoints         "$HF/Comfy-Org/sam3.1/resolve/main/checkpoints/sam3.1_multiplex_fp16.safetensors"
}

audio() {
  echo "== ACE-Step 1.5 Turbo (~10 GB) =="
  local B="$HF/Comfy-Org/ace_step_1.5_ComfyUI_files/resolve/main/split_files"
  get diffusion_models "$B/diffusion_models/acestep_v1.5_turbo.safetensors"
  get text_encoders    "$B/text_encoders/qwen_1.7b_ace15.safetensors"
  get text_encoders    "$B/text_encoders/qwen_0.6b_ace15.safetensors"
  get vae              "$B/vae/ace_1.5_vae.safetensors"
}

sfx() {
  echo "== Stable Audio 3 Medium - SFX / ambience (~13 GB) =="
  get checkpoints   "$HF/Comfy-Org/stable-audio-3/resolve/main/checkpoints/stable_audio_3_medium.safetensors"
  get text_encoders "$HF/Comfy-Org/stable-audio-3/resolve/main/text_encoders/t5gemma_b_b_ul2.safetensors"
  get text_encoders "$HF/Comfy-Org/Qwen3.5/resolve/main/text_encoders/qwen3.5_2b_bf16.safetensors"
}

ltx() {
  echo "== LTX-2.3 22B - video WITH synced audio (~40 GB) =="
  # the main checkpoint alone is 29.1 GB; budget an hour on a normal connection
  # single checkpoint carries DiT + video VAE + audio VAE; loaders read it from checkpoints/
  get checkpoints           "$HF/Lightricks/LTX-2.3-fp8/resolve/main/ltx-2.3-22b-dev-fp8.safetensors"
  get text_encoders         "$HF/Comfy-Org/ltx-2/resolve/main/split_files/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors"
  get loras                 "$HF/Comfy-Org/ltx-2/resolve/main/split_files/loras/gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors"
  get loras                 "$HF/Comfy-Org/ltx-2.3/resolve/main/split_files/loras/ltx_2.3_22b_distilled_1.1_lora_dynamic_fro09_avg_rank_111_bf16.safetensors"
  get latent_upscale_models "$HF/Lightricks/LTX-2.3/resolve/main/ltx-2.3-spatial-upscaler-x2-1.1.safetensors"
}

t2v() {
  echo "== Wan 2.2 T2V 14B (~30 GB) =="
  local B="$HF/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files"
  get diffusion_models "$B/diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"
  get diffusion_models "$B/diffusion_models/wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors"
  get loras            "$B/loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors"
  get loras            "$B/loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors"
}

anime() {
  echo "== anime-native SDXL checkpoints (~14 GB) =="
  # Qwen-Image is a photoreal/illustration model. Both of its "anime" LoRAs restyle
  # illustration rather than producing cel animation - measured side by side, and
  # `modern_anime` was WORSE than `storybook_anime`, more caricature. Matching a real
  # anime reference needs an anime-native checkpoint. These two are the current pair
  # worth having; they prompt differently, so keep both and A/B per production.
  #   Illustrious  - danbooru-tag prompting, strong on action poses and dynamic angles
  #   Animagine    - cleaner flat cel shading, more consistent faces
  get checkpoints "$HF/OnomaAIResearch/Illustrious-XL-v2.0/resolve/main/Illustrious-XL-v2.0.safetensors"
  get checkpoints "$HF/cagliostrolab/animagine-xl-4.0/resolve/main/animagine-xl-4.0.safetensors"
}

ipadapter() {
  echo "== IPAdapter face models for SDXL (~2.5 GB) =="
  # Character consistency for the anime checkpoints. Qwen-Image-Edit reference-locking
  # does not apply to SDXL, so this replaces it for Animagine/Illustrious keyframes.
  #
  # THE PAIRING MATTERS AND IS EASY TO GET WRONG: the adapter below is the *vit-h*
  # variant, so it needs the ViT-H image encoder, which lives at models/image_encoder/
  # in the h94 repo. The one under sdxl_models/image_encoder/ is ViT-bigG and will load
  # without complaint while producing garbage.
  local B="$HF/h94/IP-Adapter/resolve/main"
  get ipadapter  "$B/sdxl_models/ip-adapter-plus-face_sdxl_vit-h.safetensors"
  get clip_vision "$B/models/image_encoder/model.safetensors" CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors
}

zimage() {
  echo "== Z-Image Turbo (~11 GB) =="
  local B="$HF/Comfy-Org/z_image_turbo/resolve/main/split_files"
  get diffusion_models "$B/diffusion_models/z_image_turbo_bf16.safetensors"
  get text_encoders    "$B/text_encoders/qwen_3_4b.safetensors"
  get vae              "$B/vae/ae.safetensors" flux_ae.safetensors
}

seedvr() {
  echo "== SeedVR2 3B upscaler (~4 GB) =="
  get diffusion_models "$HF/Comfy-Org/SeedVR2/resolve/main/diffusion_models/seedvr2_3b_int8_convrot.safetensors"
  get vae              "$HF/Comfy-Org/SeedVR2/resolve/main/vae/seedvr2_ema_vae_fp16.safetensors"
}

control() {
  echo "== control signal generators (~3.7 GB) =="
  get geometry_estimation "$HF/Comfy-Org/Depth-Anything-3/resolve/main/geometry_estimation/depth_anything_3_mono_large.safetensors"
  # MoGe-2 normals: needed by video_ltx2_3_ic_lora as well as the MoGe depth templates.
  # Repo is Comfy-Org/MoGe (not MoGe-2) - the file is versioned, the repo is not.
  get geometry_estimation "$HF/Comfy-Org/MoGe/resolve/main/geometry_estimation/moge_2_vitl_normal_fp16.safetensors"
  # checkpoints/, not detection/ - same reason as SAM 3.1 above
  get checkpoints         "$HF/Comfy-Org/SDPose/resolve/main/checkpoints/sdpose_wholebody_fp16.safetensors"
}

ltxcontrol() {
  echo "== LTX-2.3 IC-LoRA control + ID-LoRA identity lock (~1.7 GB) =="
  # These are the LTX-2.3 LoRAs. Do NOT substitute the ltx-2-19b-* files - those are for the
  # older LTX-2 19B base and will not load against ltx-2.3-22b.
  # NB the IC-LoRA lives in a Lightricks repo of its own, NOT under Comfy-Org/ltx-2.3
  get loras "$HF/Lightricks/LTX-2.3-22b-IC-LoRA-Union-Control/resolve/main/ltx-2.3-22b-ic-lora-union-control-ref0.5.safetensors"
  get loras "$HF/Comfy-Org/ltx-2.3/resolve/main/split_files/loras/ltx-2.3-id-lora-talkvid-3k.safetensors"
  echo "  NOTE: the video_ltx2_3_ic_lora template also lists ltx-2.3-22b-distilled-fp8"
  echo "  (27.5 GB). Skipped on purpose - you already have ltx-2.3-22b-dev-fp8 plus the"
  echo "  distilled LoRA, which is the same path. Fetch it only if the IC-LoRA misbehaves."
}

flux2() {
  echo "== FLUX.2 dev fp8 - second aesthetic, best open photorealism (~53 GB) =="
  local B="$HF/Comfy-Org/flux2-dev/resolve/main/split_files"
  # fp8 encoder, NOT the 33 GB bf16 one - fp8 is the right choice on 32 GB VRAM
  get diffusion_models "$B/diffusion_models/flux2_dev_fp8mixed.safetensors"
  get text_encoders    "$B/text_encoders/mistral_3_small_flux2_fp8.safetensors"
  get vae              "$B/vae/flux2-vae.safetensors"
  get loras            "$B/loras/Flux2TurboComfyv2.safetensors"
}

hunyuanvideo() {
  echo "== HunyuanVideo 1.5 720p T2V + I2V + 1080p SR (~50 GB) =="
  # Physics and motion specialist. Complements LTX-2.3 (audio + control) and Wan 2.2
  # (photoreal humans). The 1080p SR stage is what makes native 1080p output possible.
  local B="$HF/Comfy-Org/HunyuanVideo_1.5_repackaged/resolve/main/split_files"
  get diffusion_models      "$B/diffusion_models/hunyuanvideo1.5_720p_t2v_fp16.safetensors"
  get diffusion_models      "$B/diffusion_models/hunyuanvideo1.5_720p_i2v_fp16.safetensors"
  get diffusion_models      "$B/diffusion_models/hunyuanvideo1.5_1080p_sr_distilled_fp16.safetensors"
  get vae                   "$B/vae/hunyuanvideo15_vae_fp16.safetensors"
  get latent_upscale_models "$B/latent_upscale_models/hunyuanvideo15_latent_upsampler_1080p.safetensors"
  get text_encoders         "$B/text_encoders/byt5_small_glyphxl_fp16.safetensors"
  get clip_vision           "$HF/Comfy-Org/sigclip_vision_384/resolve/main/sigclip_vision_patch14_384.safetensors"
}

edit2511() {
  echo "== Qwen-Image-Edit 2511 + Lightning (~21 GB) =="
  get diffusion_models "$HF/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors"
  get loras            "$HF/lightx2v/Qwen-Image-Edit-2511-Lightning/resolve/main/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
}

hunyuan3d() {
  echo "== Hunyuan3D 2.1 (~7 GB) =="
  get checkpoints "$HF/Comfy-Org/hunyuan3D_2.1_repackaged/resolve/main/hunyuan_3d_v2.1.safetensors"
}

triposplat() {
  echo "== TripoSplat - image -> 3D Gaussian splats (~2.8 GB) =="
  # VAST-AI, May 2026, MIT. Beat Hunyuan3D 2.1 and TRELLIS.2 in human preference
  # (Elo 1137 vs 996 / 992). Outputs .ply/.splat - NOT a mesh. Complements
  # hunyuan3d rather than replacing it: splats for looks, meshes for pipeline.
  local B="$HF/VAST-AI/TripoSplat/resolve/main"
  get diffusion_models "$B/diffusion_models/triposplat_fp16.safetensors"
  get vae              "$B/vae/triposplat_vae_decoder_fp16.safetensors"
  get clip_vision      "$B/clip_vision/dino_v3_vit_h.safetensors"
  # flux2-vae is shared with the flux2 tier; whichever runs first wins and the
  # other is skipped on the size check.
  get vae              "$B/vae/flux2-vae.safetensors"
}

acestep1() {
  echo "== ACE-Step 1 (3.5B) - music REMIX / extend / restyle (~7 GB) =="
  # Music-to-music editing exists ONLY in ACE-Step 1, not in the 1.5 you have.
  # This is the single cheapest brand-new capability on the box.
  get checkpoints "$HF/Comfy-Org/ACE-Step_ComfyUI_repackaged/resolve/main/all_in_one/ace_step_v1_3.5b.safetensors"
}

fluxfill() {
  echo "== FLUX.1 Fill + OneReward - outpainting & object removal (~21 GB) =="
  # The OneReward fp8 transformer (11 GB) rather than plain flux1-fill-dev (22 GB):
  # newer method, half the size, better at removal.
  get diffusion_models "$HF/Comfy-Org/OneReward_repackaged/resolve/main/split_files/diffusion_models/flux.1-fill-dev-OneReward-transformer_fp8.safetensors"
  get text_encoders    "$HF/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors"
  get text_encoders    "$HF/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors"
  get vae              "$HF/Comfy-Org/Lumina_Image_2.0_Repackaged/resolve/main/split_files/vae/ae.safetensors"
  get loras            "$HF/lrzjason/ObjectRemovalFluxFill/resolve/main/removal_timestep_alpha-2-1740.safetensors"
}

vace() {
  echo "== Wan 2.1 VACE 14B - video restyle + inpaint + outpaint (~33 GB) =="
  # Three new video capabilities from one model. 14B fp16 rather than the 1.3B:
  # the 1.3B works but is a clear quality step down.
  # The templates also list umt5_xxl_fp16 (10.6 GB) - skipped, your existing
  # umt5_xxl_fp8_e4m3fn_scaled serves the same role.
  get diffusion_models "$HF/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_vace_14B_fp16.safetensors"
  get loras            "$HF/Kijai/WanVideo_comfy/resolve/main/Wan21_CausVid_14B_T2V_lora_rank32.safetensors"
}

list() {
  find "$M" -type f \( -name '*.safetensors' -o -name '*.pth' -o -name '*.pt' -o -name '*.gguf' \) \
    -printf '%10s %p\n' | sort -k2 | awk -v m="$M/" '{gsub(m,"",$2); printf "%8.1f GB  %s\n", $1/1073741824, $2}'
}

# verify: re-check every file this script knows about against its remote size.
verify() {
  echo "== verifying downloaded sizes =="
  get() { # shadow: check only, never download
    local f="$M/$1/${3:-$(basename "$2")}"
    [[ -f "$f" ]] || { printf '  - %-58s MISSING\n' "$1/${3:-$(basename "$2")}"; return; }
    local have want; have=$(stat -c%s "$f"); want=$(remote_size "$2")
    if [[ -z "$want" ]]; then printf '  ? %-58s %s (remote size unknown)\n' "$1" "$have"
    elif [[ "$have" == "$want" ]]; then printf '  OK %-57s %s\n' "$1/${3:-$(basename "$2")}" "$have"
    else printf '  !! %-57s PARTIAL %s/%s\n' "$1/${3:-$(basename "$2")}" "$have" "$want"; fi
  }
  utility; audio; sfx; ltx
}

case "${1:-}" in
  utility|audio|sfx|ltx|t2v|zimage|seedvr|control|edit2511|hunyuan3d) "$1" ;;
  anime|ipadapter) "$1" ;;
  ltxcontrol|flux2|hunyuanvideo|triposplat|acestep1|fluxfill|vace|list|verify) "$1" ;;
  # brand-new capabilities rather than alternative aesthetics: Gaussian splats,
  # music remix, image outpainting/removal. ~31 GB for four things you cannot
  # currently do at all.
  explore) triposplat; acestep1; fluxfill ;;
  tier1) utility; audio; t2v ;;
  tier2) zimage; seedvr; control ;;
  sound) utility; audio; sfx; ltx ;;
  # 2026-07-29 second download session, cheap-and-high-value first so the
  # useful things land before the 100 GB of model weights
  quickwins) control; ltxcontrol; edit2511; hunyuan3d; seedvr ;;
  bigmodels) flux2; hunyuanvideo ;;
  *) sed -n '2,24p' "$0"; exit 1 ;;
esac

echo
echo "Done. Verify sizes, then restart ComfyUI to pick up new files:"
echo "  bash $(dirname "$0")/fetch-models.sh verify"
echo "  bash $(dirname "$0")/restart-comfy.sh"
