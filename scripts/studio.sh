#!/usr/bin/env bash
#
# studio.sh - start, stop and inspect the studio web app and ComfyUI together.
#
#     bash scripts/studio.sh            # same as start
#     bash scripts/studio.sh start
#     bash scripts/studio.sh stop
#     bash scripts/studio.sh restart
#     bash scripts/studio.sh status
#     bash scripts/studio.sh logs
#
# The web app is useless without ComfyUI - every render it triggers goes through it -
# so this starts both and reports both.
#
# TWO RULES THIS FILE FOLLOWS, both learned the hard way on this box:
#
#  1. Never `pkill -f` a pattern that could match your own command. `pkill -f
#     "main.py --listen"` over ssh matches the bash -c wrapper running it and kills
#     your own session. Processes are found by WHICH PORT THEY HOLD instead.
#
#  2. Never report success you have not checked. An earlier version of the boot
#     script logged "studio server started" immediately after launching it, which
#     read as success during the window when the port was not yet listening.
#     Everything below waits for the port and reports what it observed.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMFY="${COMFY_ROOT:-$HOME/ComfyUI}"
STUDIO_PORT="${STUDIO_PORT:-8777}"
COMFY_PORT="${COMFY_PORT:-8188}"
STUDIO_LOG=/tmp/studio-serve.log
COMFY_LOG=/tmp/comfy.log

c_ok=$'\e[32m'; c_bad=$'\e[31m'; c_dim=$'\e[2m'; c_off=$'\e[0m'
ok()  { printf "  ${c_ok}OK${c_off}    %s\n" "$*"; }
bad() { printf "  ${c_bad}FAIL${c_off}  %s\n" "$*"; }
dim() { printf "  ${c_dim}%s${c_off}\n" "$*"; }

listening() { ss -tln 2>/dev/null | grep -q ":$1 "; }
pid_on()    { ss -tlnp 2>/dev/null | grep ":$1 " | grep -oP 'pid=\K[0-9]+' | head -1; }
lan_ip()    { hostname -I 2>/dev/null | awk '{print $1}'; }

wait_for() {  # port, seconds
  for _ in $(seq 1 "$2"); do listening "$1" && return 0; sleep 1; done
  return 1
}

start_comfy() {
  if listening "$COMFY_PORT"; then ok "ComfyUI already up on $COMFY_PORT"; return 0; fi
  dim "starting ComfyUI ..."
  bash "$ROOT/scripts/restart-comfy.sh" >/dev/null 2>&1
  if wait_for "$COMFY_PORT" 60; then ok "ComfyUI up on $COMFY_PORT"
  else bad "ComfyUI did not bind $COMFY_PORT - see $COMFY_LOG"; return 1; fi
}

start_studio() {
  if listening "$STUDIO_PORT"; then ok "studio already up on $STUDIO_PORT"; return 0; fi
  dim "starting studio ..."
  ( cd "$ROOT" && setsid nohup python3 studio/serve.py >>"$STUDIO_LOG" 2>&1 </dev/null & )
  if wait_for "$STUDIO_PORT" 25; then ok "studio up on $STUDIO_PORT"
  else bad "studio did not bind $STUDIO_PORT - see $STUDIO_LOG"; return 1; fi
}

stop_one() {  # port, label
  local p; p="$(pid_on "$1")"
  if [ -z "$p" ]; then dim "$2 was not running"; return 0; fi
  kill "$p" 2>/dev/null
  for _ in $(seq 1 10); do listening "$1" || break; sleep 1; done
  if listening "$1"; then kill -9 "$p" 2>/dev/null; sleep 2; fi
  listening "$1" && bad "$2 (pid $p) would not die" || ok "$2 stopped (pid $p)"
}

urls() {
  local ip; ip="$(lan_ip)"
  echo
  printf "  %-34s %s\n" "direct a scene"        "http://${ip}:${STUDIO_PORT}/wizard"
  printf "  %-34s %s\n" "library + capability cards" "http://${ip}:${STUDIO_PORT}/"
  printf "  %-34s %s\n" "ComfyUI"               "http://${ip}:${COMFY_PORT}"
  echo
}

status() {
  local ip; ip="$(lan_ip)"
  listening "$COMFY_PORT"  && ok "ComfyUI  listening on $COMFY_PORT  (pid $(pid_on $COMFY_PORT))"  || bad "ComfyUI  down"
  listening "$STUDIO_PORT" && ok "studio   listening on $STUDIO_PORT  (pid $(pid_on $STUDIO_PORT))" || bad "studio   down"
  if listening "$COMFY_PORT"; then
    local v; v=$(curl -s --max-time 4 "http://127.0.0.1:$COMFY_PORT/system_stats" \
                 | python3 -c 'import json,sys; d=json.load(sys.stdin); g=d["devices"][0]; print("%s, %.1f GB free of %.1f" % (g["name"], g["vram_free"]/2**30, g["vram_total"]/2**30))' 2>/dev/null)
    [ -n "$v" ] && dim "$v"
  fi
  [ -n "$ip" ] && urls
}

case "${1:-start}" in
  start)   start_comfy; start_studio; urls ;;
  stop)    stop_one "$STUDIO_PORT" "studio"; stop_one "$COMFY_PORT" "ComfyUI" ;;
  restart) stop_one "$STUDIO_PORT" "studio"; stop_one "$COMFY_PORT" "ComfyUI"; sleep 2; start_comfy; start_studio; urls ;;
  status)  status ;;
  logs)    echo "--- $STUDIO_LOG ---"; tail -20 "$STUDIO_LOG" 2>/dev/null
           echo "--- $COMFY_LOG ---";  tail -20 "$COMFY_LOG"  2>/dev/null ;;
  *)       echo "usage: $0 [start|stop|restart|status|logs]"; exit 2 ;;
esac
