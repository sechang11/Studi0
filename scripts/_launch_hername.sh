#!/usr/bin/env bash
# Launcher wrapper.
#
# Kept as a FILE, never inlined into `ssh host "..."`: a pkill pattern typed inside an
# ssh command string also matches that command's own shell and drops the connection.
#
# It must kill the RUNNER as well as the python it spawned. Killing only cartoon.py
# leaves _run_hername.sh alive in its retry loop, and relaunching then gives you two
# runners racing each other through the same stages - which is exactly what happened:
# one process ran --stage audio while another ran --stage sfx against the same folder.
set -uo pipefail
cd "$HOME/shared/comfy-studio"

SELF=$$
for pat in '_run_hername.sh' 'cartoon.py films/her-name'; do
  for pid in $(pgrep -f "$pat" 2>/dev/null); do
    [ "$pid" = "$SELF" ] && continue
    kill "$pid" 2>/dev/null
  done
done
sleep 3
# anything still alive gets SIGKILL
for pat in '_run_hername.sh' 'cartoon.py films/her-name'; do
  for pid in $(pgrep -f "$pat" 2>/dev/null); do
    [ "$pid" = "$SELF" ] && continue
    kill -9 "$pid" 2>/dev/null
  done
done
sleep 1

live=$(pgrep -fc '_run_hername.sh' 2>/dev/null || echo 0)
echo "runners alive after cleanup (expect 0-1, this script matches itself): $live"

setsid nohup bash scripts/_run_hername.sh > hername.log 2>&1 < /dev/null &
disown 2>/dev/null || true
sleep 6
n=$(pgrep -fc '_run_hername.sh' 2>/dev/null || echo 0)
echo "LAUNCHED (runner processes now: $n)"
