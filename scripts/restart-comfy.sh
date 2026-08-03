#!/usr/bin/env bash
# restart-comfy.sh - stop and restart the ComfyUI server, then report health.
#
# Note: do NOT inline `pkill -f 'main.py --listen'` in an ssh command string - the
# pattern matches the ssh command's own bash -c process and kills your session.
# Matching on the full interpreter path avoids that.
set -uo pipefail

CD="$HOME/ComfyUI"
LOG=/tmp/comfy.log

pkill -f "$CD/venv/bin/python $CD/main.py" 2>/dev/null
pkill -f "venv/bin/python main.py" 2>/dev/null
sleep 4

cd "$CD"
setsid nohup venv/bin/python main.py --listen 0.0.0.0 --port 8188 --reserve-vram 1.5 \
  > "$LOG" 2>&1 < /dev/null &

for i in $(seq 1 60); do
  if curl -s --max-time 3 http://127.0.0.1:8188/system_stats >/dev/null 2>&1; then
    echo "SERVER UP after ${i}s"
    break
  fi
  sleep 1
done

echo "--- custom node / import problems ---"
grep -aiE 'traceback|cannot import|failed to load|IMPORT FAILED' "$LOG" | head -20 || true
echo "--- node count ---"
curl -s http://127.0.0.1:8188/object_info | python3 -c 'import json,sys; print(len(json.load(sys.stdin)),"nodes")'
