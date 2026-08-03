#!/usr/bin/env bash
# restart-fetch.sh - stop any running model fetch and relaunch it detached.
# Kept as a script (not an inline ssh command) so pkill patterns cannot match
# the ssh session's own shell and kill the connection.
set -uo pipefail
TIER="${1:-sound}"
LOG="$HOME/shared/comfy-studio/fetch.log"

pkill -f 'bash .*fetch-models.sh' 2>/dev/null
pkill -f 'curl -fL -C -' 2>/dev/null
sleep 3

cd "$HOME/shared/comfy-studio"
setsid nohup bash scripts/fetch-models.sh "$TIER" >> "$LOG" 2>&1 < /dev/null &
disown 2>/dev/null || true
sleep 5
echo "relaunched tier=$TIER -> $LOG"
pgrep -f 'fetch-models.sh' >/dev/null && echo RUNNING || echo "NOT RUNNING - check $LOG"
