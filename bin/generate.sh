#!/usr/bin/env bash
# Generate demo content for a fixed number of hours, then STOP.
#
#   ./bin/generate.sh --hours 8
#   ./bin/generate.sh --hours 2 --weights image=6,video=2,music=1,voice=1,sfx=1
#   ./bin/generate.sh --minutes 20 --dry            # show what it would roll, render nothing
#   ./bin/generate.sh --stop                        # ask a running one to finish and exit
#
# WHY THE DEADLINE IS THE FIRST FEATURE. A gallery_gen.py --loop was started on this box
# and ran for SEVENTEEN HOURS AND TWENTY-TWO MINUTES, holding the GPU at 100% and starving
# three separate jobs, because --loop had no stopping condition and nothing showed it was
# running. This script therefore refuses to start without a time budget, writes a PID file,
# stops on a STOP file or on Ctrl-C, and never begins a job it cannot finish inside the
# budget.
#
# PROMPTS. There is no prompt to write. studio/_tools/roll.py draws a combination from the
# measured libraries - 91 ready style cards, 64 places, 24 usable grades, 27 emotions, 9
# ready motions - which is 3.7 million distinct image jobs before motion or camera. Every
# element was rendered and looked at before it became drawable, and the known duds are
# excluded by name: the `night` grade that clips to black, three camera moves that are
# byte-identical to static, and every style card marked weak, unavailable, or measured to
# put a prop in the subject's hands.
#
# RUN IT AGAIN AND YOU GET DIFFERENT WORK. The run seed comes from the clock unless you
# pass --seed, in which case the whole run is exactly reproducible.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$REPO/studio/samples/rolled"
RUNDIR="$REPO/.generate"
PIDFILE="$RUNDIR/generate.pid"
STOPFILE="$RUNDIR/STOP"

HOURS=""; MINUTES=""; SEED=""; DRY=0
WEIGHTS="image=6,video=2,music=1,voice=1,sfx=1"

usage() { sed -n '2,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --hours)   HOURS="${2:-}"; shift 2 ;;
    --minutes) MINUTES="${2:-}"; shift 2 ;;
    --weights) WEIGHTS="${2:-}"; shift 2 ;;
    --seed)    SEED="${2:-}"; shift 2 ;;
    --out)     OUT="${2:-}"; shift 2 ;;
    --dry)     DRY=1; shift ;;
    --stop)
      mkdir -p "$RUNDIR"; touch "$STOPFILE"
      if [ -f "$PIDFILE" ]; then
        echo "asked pid $(cat "$PIDFILE") to stop after its current job."
      else
        echo "no run in progress; STOP flag set anyway."
      fi
      exit 0 ;;
    --status)
      if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "running, pid $(cat "$PIDFILE")"
        tail -3 "$RUNDIR/generate.log" 2>/dev/null
      else
        echo "not running"
      fi
      exit 0 ;;
    -h|--help) usage 0 ;;
    *) echo "unknown option: $1" >&2; usage 1 ;;
  esac
done

# A budget is mandatory. This is the whole lesson of the 17-hour runaway.
if [ -z "$HOURS" ] && [ -z "$MINUTES" ]; then
  echo "refusing to start without a time budget. pass --hours N or --minutes N." >&2
  echo "  (a previous unbounded run held this GPU for 17h22m and starved three jobs.)" >&2
  exit 2
fi
BUDGET=$(( ${HOURS:-0} * 3600 + ${MINUTES:-0} * 60 ))
[ "$BUDGET" -gt 0 ] || { echo "budget must be positive" >&2; exit 2; }

mkdir -p "$RUNDIR" "$OUT"
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "already running as pid $(cat "$PIDFILE"). use --status or --stop." >&2
  exit 3
fi
rm -f "$STOPFILE"
echo $$ > "$PIDFILE"
LOG="$RUNDIR/generate.log"

DEADLINE=$(( $(date +%s) + BUDGET ))
STARTED=$(date +%s)
declare -A DONE=() FAILED=() REJECTED=()

finish() {
  local now elapsed
  now=$(date +%s); elapsed=$(( now - STARTED ))
  echo ""
  echo "── stopped after $(( elapsed / 60 )) min ──────────────────────────"
  for k in "${!DONE[@]}";     do printf "  %-6s kept %s\n"     "$k" "${DONE[$k]}"; done
  for k in "${!REJECTED[@]}"; do printf "  %-6s rejected %s\n" "$k" "${REJECTED[$k]}"; done
  for k in "${!FAILED[@]}";   do printf "  %-6s failed %s\n"   "$k" "${FAILED[$k]}"; done
  echo "  output: $OUT"
  echo "  log:    $LOG"
  rm -f "$PIDFILE"
  exit 0
}
trap finish INT TERM

# Expand the weights into a draw bag: image=3 becomes three entries.
BAG=()
IFS=',' read -ra PAIRS <<< "$WEIGHTS"
for p in "${PAIRS[@]}"; do
  k="${p%%=*}"; v="${p##*=}"
  case "$k" in image|video|music|voice|sfx) ;; *) echo "unknown type: $k" >&2; exit 2 ;; esac
  for _ in $(seq 1 "${v:-0}"); do BAG+=("$k"); done
done
[ "${#BAG[@]}" -gt 0 ] || { echo "weights produced an empty bag" >&2; exit 2; }

echo "generating for $(( BUDGET / 60 )) min into $OUT"
echo "  weights : $WEIGHTS"
echo "  stop    : ./bin/generate.sh --stop     (or Ctrl-C)"
echo "  watch   : ./bin/generate.sh --status   (or tail -f $LOG)"
[ -n "$SEED" ] && echo "  seed    : $SEED (reproducible)" || echo "  seed    : from the clock, so a re-run differs"
echo ""

N=0
while :; do
  [ -f "$STOPFILE" ] && { echo "STOP requested."; finish; }
  NOW=$(date +%s)
  LEFT=$(( DEADLINE - NOW ))
  # Never start a job that cannot finish. Video is the long pole at roughly 90s.
  if [ "$LEFT" -le 30 ]; then echo "budget spent."; finish; fi

  TYPE="${BAG[$(( RANDOM % ${#BAG[@]} ))]}"
  if [ "$TYPE" = "video" ] && [ "$LEFT" -lt 120 ]; then TYPE="image"; fi

  N=$(( N + 1 ))
  SEEDARG=()
  [ -n "$SEED" ] && SEEDARG=(--seed $(( SEED + N )))

  JOB="$(python3 "$REPO/studio/_tools/roll.py" "$TYPE" "${SEEDARG[@]}" 2>>"$LOG")"
  [ -n "$JOB" ] || { echo "roll failed for $TYPE" | tee -a "$LOG"; sleep 2; continue; }

  if [ "$DRY" = "1" ]; then
    echo "$JOB" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("  %-6s %s"%(d["domain"], d.get("prompt") or d.get("line") or d.get("cue") or "")[:110])'
    [ "$N" -ge 12 ] && { echo "(dry run: 12 shown)"; finish; }
    continue
  fi

  RES="$(echo "$JOB" | python3 "$REPO/studio/_tools/render_job.py" --out "$OUT" 2>>"$LOG")"
  if [ -z "$RES" ]; then
    FAILED[$TYPE]=$(( ${FAILED[$TYPE]:-0} + 1 ))
    echo "$(date +%H:%M:%S) $TYPE FAILED (no result)" | tee -a "$LOG"
    continue
  fi
  echo "$RES" >> "$LOG"
  OKV="$(echo "$RES" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("1" if d.get("ok") else "0")' 2>/dev/null)"
  SECS="$(echo "$RES" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("seconds",0))' 2>/dev/null)"
  if [ "$OKV" = "1" ]; then
    DONE[$TYPE]=$(( ${DONE[$TYPE]:-0} + 1 ))
    printf "%s  %-6s ok        %5ss   kept %s   %dm left\n" \
      "$(date +%H:%M:%S)" "$TYPE" "$SECS" "${DONE[$TYPE]}" "$(( LEFT / 60 ))"
  elif echo "$RES" | grep -q '"why": *"[^"]'; then
    REJECTED[$TYPE]=$(( ${REJECTED[$TYPE]:-0} + 1 ))
    printf "%s  %-6s rejected  %5ss   %s\n" "$(date +%H:%M:%S)" "$TYPE" "$SECS" \
      "$(echo "$RES" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("why",""))')"
  else
    FAILED[$TYPE]=$(( ${FAILED[$TYPE]:-0} + 1 ))
    printf "%s  %-6s failed\n" "$(date +%H:%M:%S)" "$TYPE"
  fi
done
