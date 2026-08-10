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
# Fixed cell size so xstack offsets can be plain pixel arithmetic. The previous version
# built offsets from "0 or w0" and "0 or h0", which only ever addresses a 2x2 grid - with
# six takes, t05 and t06 were drawn directly on top of t03 and t04 and two takes vanished
# from the sheet without a word. A chooser that silently hides options is worse than no
# chooser at all.
CELLW=520; CELLH=293
ARGS=(); FC=""; N=0
for d in "$TD"/t*; do
  K="$d/keyframe.png"; [ -f "$K" ] || continue
  T=$(basename "$d")
  SEED=$(python3 -c "import json;print(json.load(open('$d/inputs.json')).get('seed',''))" 2>/dev/null)
  MARK="$T  seed $SEED"
  [ "$T" = "$SEL" ] && MARK="$MARK  <SELECTED>"
  ARGS+=(-i "$K")
  FC="$FC[$N:v]scale=$CELLW:$CELLH:force_original_aspect_ratio=decrease,pad=$CELLW:$CELLH:(ow-iw)/2:(oh-ih)/2:color=0x111111,drawtext=text='$MARK':fontsize=24:fontcolor=white:box=1:boxcolor=black@0.65:x=10:y=10[c$N];"
  N=$((N+1))
done
[ "$N" -gt 0 ] || { echo "no rendered keyframes" >&2; exit 1; }

COLS=3; [ "$N" -le 4 ] && COLS=2; [ "$N" -le 1 ] && COLS=1
LAYOUT=""; IN=""
for i in $(seq 0 $((N-1))); do
  X=$(( (i % COLS) * CELLW )); Y=$(( (i / COLS) * CELLH ))
  LAYOUT="$LAYOUT|${X}_${Y}"; IN="$IN[c$i]"
done
LAYOUT="${LAYOUT#|}"
if [ "$N" = 1 ]; then
  FC="$FC[c0]null[v]"
else
  # fill= matters: an odd take count leaves empty canvas and xstack fills it bright green.
  FC="$FC${IN}xstack=inputs=$N:fill=0x111111:layout=$LAYOUT[v]"
fi

ffmpeg -y -v error "${ARGS[@]}" -filter_complex "$FC" -map "[v]" -frames:v 1 "$OUT"   && echo "$OUT  ($N takes${SEL:+, selected $SEL})"
