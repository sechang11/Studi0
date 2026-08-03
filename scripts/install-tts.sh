#!/usr/bin/env bash
# install-tts.sh - install a local TTS custom node pack WITHOUT breaking ComfyUI.
#
#   bash install-tts.sh chatterbox     # Resemble Chatterbox: zero-shot voice clone (MIT)
#   bash install-tts.sh f5             # F5-TTS: mature, stable zero-shot clone (MIT)
#   bash install-tts.sh kokoro         # Kokoro: tiny, fixed voices, no cloning
#   bash install-tts.sh vibevoice      # VibeVoice: long-form multi-speaker narration
#   bash install-tts.sh indextts2      # IndexTTS 2: precise duration control
#
# Why the ceremony: this box runs python 3.14 / torch 2.13.0+cu130 / transformers 5.14.1.
# Most TTS packs pin transformers<5 or an older torch. An unconstrained
# `pip install -r requirements.txt` will silently downgrade them and break both the
# stock ComfyUI nodes and CUDA 13 support for the 5090.
#
# So: pin the critical packages, install under that constraint, then VERIFY. If the
# verify step fails the script tells you exactly what to roll back to.
set -uo pipefail

CN="$HOME/ComfyUI/custom_nodes"
PY="$HOME/ComfyUI/venv/bin/python"
PIP="$HOME/ComfyUI/venv/bin/pip"

case "${1:-}" in
  chatterbox) REPO=https://github.com/wildminder/ComfyUI-Chatterbox ;;
  f5)         REPO=https://github.com/niknah/ComfyUI-F5-TTS ;;
  kokoro)     REPO=https://github.com/stavsap/comfyui-kokoro ;;
  vibevoice)  REPO=https://github.com/wildminder/ComfyUI-VibeVoice ;;
  indextts2)  REPO=https://github.com/snicolast/ComfyUI-IndexTTS2 ;;
  *) sed -n '2,12p' "$0"; exit 1 ;;
esac

NAME=$(basename "$REPO")
echo "== pack: $NAME"

# ---- record the state we must not lose --------------------------------------
BEFORE=$("$PY" - <<'EOF'
import torch, transformers, numpy, torchaudio
print(f"{torch.__version__}|{transformers.__version__}|{numpy.__version__}|{torchaudio.__version__}")
EOF
)
IFS='|' read -r TORCH_V TFMR_V NUMPY_V TA_V <<< "$BEFORE"
echo "   protecting torch==$TORCH_V transformers==$TFMR_V numpy==$NUMPY_V torchaudio==$TA_V"

CONS=$(mktemp)
cat > "$CONS" <<EOF
torch==$TORCH_V
transformers==$TFMR_V
numpy==$NUMPY_V
torchaudio==$TA_V
EOF

# ---- fetch -------------------------------------------------------------------
if [[ -d "$CN/$NAME" ]]; then
  echo "   already cloned, pulling"
  git -C "$CN/$NAME" pull --ff-only || true
else
  git clone --depth 1 "$REPO" "$CN/$NAME" || exit 1
fi

REQ="$CN/$NAME/requirements.txt"
if [[ ! -f "$REQ" ]]; then
  echo "   no requirements.txt - nothing to install"
else
  echo "   requirements:"
  sed 's/^/      /' "$REQ"
  echo "   installing under constraint (dry run first)..."
  if ! "$PIP" install --dry-run -r "$REQ" -c "$CONS" >/tmp/tts-dryrun.log 2>&1; then
    echo
    echo "!! INCOMPATIBLE - pip cannot satisfy $NAME without changing torch/transformers."
    tail -20 /tmp/tts-dryrun.log
    echo
    echo "   Nothing was installed. Options:"
    echo "     - try another pack:  bash $0 kokoro"
    echo "     - or run this TTS in its own venv and import the wav with LoadAudio"
    echo "   Removing the clone so ComfyUI does not try to load a broken node."
    rm -rf "$CN/$NAME"
    exit 2
  fi
  "$PIP" install -r "$REQ" -c "$CONS" || { echo "!! install failed"; exit 1; }
fi

# ---- verify nothing important moved -----------------------------------------
AFTER=$("$PY" - <<'EOF'
try:
    import torch, transformers, numpy, torchaudio
    assert torch.cuda.is_available(), "CUDA lost"
    print(f"{torch.__version__}|{transformers.__version__}|{numpy.__version__}|{torchaudio.__version__}")
except Exception as e:
    print(f"BROKEN|{e}")
EOF
)
echo
if [[ "$AFTER" == "$BEFORE" ]]; then
  echo "OK  torch/transformers unchanged ($AFTER)"
  echo "    restart ComfyUI to load $NAME:"
  echo "      pkill -f 'main.py --listen'; cd ~/ComfyUI && nohup venv/bin/python main.py --listen 0.0.0.0 --port 8188 --reserve-vram 1.5 >/tmp/comfy.log 2>&1 &"
else
  echo "!! ENVIRONMENT CHANGED: was [$BEFORE] now [$AFTER]"
  echo "   restore with:"
  echo "     $PIP install 'torch==$TORCH_V' 'transformers==$TFMR_V' 'numpy==$NUMPY_V' 'torchaudio==$TA_V'"
  exit 3
fi
