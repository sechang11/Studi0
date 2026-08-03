#!/usr/bin/env bash
# Finish HER NAME (3-minute cut) unattended.
#
# The box is shared with other sessions, so the ComfyUI queue can be hundreds of jobs
# deep at any moment and a single stage may sit waiting a long time without being stuck.
# Every stage here is resumable and simply re-run until the expected file count exists.
set -uo pipefail
cd "$HOME/shared/comfy-studio"
FILM=films/her-name.json
D="$HOME/ComfyUI/output/claude-generated/11-short-film/her-name"
WANT=$(python3 -c "import json;print(len(json.load(open('$FILM'))['shots']))")
WANT_SFX=$(python3 -c "import json;print(sum(1 for s in json.load(open('$FILM'))['shots'] if s.get('sfx')))")

log() { echo "[$(date +%H:%M:%S)] $*"; }
count() { ls "$1" 2>/dev/null | wc -l; }

log "target: $WANT shots, $WANT_SFX sfx"

for a in $(seq 1 12); do
  n=$(count "$D/keyframes"); log "keyframes $n/$WANT (pass $a)"
  [ "$n" -ge "$WANT" ] && break
  python3 -u scripts/cartoon.py "$FILM" --stage keyframes || true
done

for a in $(seq 1 10); do
  n=$(count "$D/clips"); log "clips $n/$WANT (pass $a)"
  [ "$n" -ge "$WANT" ] && break
  python3 -u scripts/cartoon.py "$FILM" --stage clips --hd || true
done

for a in $(seq 1 6); do
  n=$(count "$D/sfx"); log "sfx $n/$WANT_SFX (pass $a)"
  [ "$n" -ge "$WANT_SFX" ] && break
  python3 -u scripts/cartoon.py "$FILM" --stage sfx || true
done

for a in 1 2 3 4; do
  n=$(count "$D/music"); log "music $n/5 (pass $a)"
  [ "$n" -ge 5 ] && break
  python3 -u scripts/cartoon.py "$FILM" --stage music || true
done

for a in 1 2 3 4; do
  n=$(ls "$D/voice" 2>/dev/null | grep -vc raw_ || true); log "voices $n/7 (pass $a)"
  [ "${n:-0}" -ge 7 ] && break
  python3 -u scripts/cartoon.py "$FILM" --stage voices || true
done

log "edit"
python3 -u scripts/cartoon.py "$FILM" --stage edit --hd
log "DONE"
