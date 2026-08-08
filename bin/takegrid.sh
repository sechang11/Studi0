#!/usr/bin/env bash
# Contact sheet of every take for one scene, labelled with take id and seed.
#
#   takegrid.sh <story> <chapter-prefix>/<scene> [out.jpg]
#
# This is the interface. Four keyframes side by side with their ids under them is how a
# scene actually gets chosen - clips are slow to scan and the keyframe decides the clip
# anyway, so the grid is what you look at and the clip is what you render afterwards.
set -uo pipefail
ROOT=/home/k4shix/shared/comfy-studio
ST="${1:?story}"; PATHSPEC="${2:?chapter/scene}"; OUT="${3:-/tmp/takes.jpg}"
CH="${PATHSPEC%%/*}"; SC="${PATHSPEC##*/}"

CHDIR=$(find "$ROOT/stories/$ST/chapters" -maxdepth 1 -name "$CH*" | head -1)
[ -n "$CHDIR" ] || { echo "no chapter matching $CH" >&2; exit 1; }
TD="$CHDIR/scenes/$SC/takes"
[ -d "$TD" ] || { echo "no takes for $SC" >&2; exit 1; }

SEL=$(cat "$CHDIR/scenes/$SC/SELECTED" 2>/dev/null | tr -d '[:space:]')
ARGS=(); FC=""; N=0
for d in "$TD"/t*; do
  K="$d/keyframe.png"; [ -f "$K" ] || continue
  T=$(basename "$d")
  SEED=$(python3 -c "import json,sys;print(json.load(open('$d/inputs.json')).get('seed',''))" 2>/dev/null)
  MARK="$T  seed $SEED"
  [ "$T" = "$SEL" ] && MARK="$MARK  <SELECTED>"
  ARGS+=(-i "$K")
  # Label burnt in: a grid of unlabelled thumbnails cannot be acted on, because the whole
  # point is to say "t03" afterwards.
  FC="$FC[$N:v]scale=520:-1,drawtext=text='$MARK':fontsize=26:fontcolor=white:box=1:boxcolor=black@0.65:x=12:y=12[c$N];"
  N=$((N+1))
done
[ "$N" -gt 0 ] || { echo "no rendered keyframes" >&2; exit 1; }

if [ "$N" = 1 ]; then
  FC="$FC[c0]null[v]"
else
  COLS=2; [ "$N" -le 2 ] && COLS=$N
  LAYOUT=""
  for i in $(seq 0 $((N-1))); do
    X=$(( (i % COLS) )); Y=$(( i / COLS ))
    LAYOUT="$LAYOUT|${X}_${Y}"
  done
  # xstack layout wants w0_h0 style offsets; build them from the scaled cell size instead
  # of pixel maths so a non-16:9 scene still tiles.
  LAYOUT=""
  for i in $(seq 0 $((N-1))); do
    X=$(( i % COLS )); Y=$(( i / COLS ))
    if [ "$X" = 0 ]; then XE=0; else XE="w0"; fi
    if [ "$Y" = 0 ]; then YE=0; else YE="h0"; fi
    LAYOUT="$LAYOUT|${XE}_${YE}"
  done
  LAYOUT="${LAYOUT#|}"
  IN=""; for i in $(seq 0 $((N-1))); do IN="$IN[c$i]"; done
  # fill= matters: an odd take count leaves empty canvas, and xstack fills that with
  # BRIGHT GREEN by default.
  FC="$FC${IN}xstack=inputs=$N:fill=0x111111:layout=$LAYOUT[v]"
fi

ffmpeg -y -v error "${ARGS[@]}" -filter_complex "$FC" -map "[v]" -frames:v 1 "$OUT" \
  && echo "$OUT  ($N takes${SEL:+, selected $SEL})"
