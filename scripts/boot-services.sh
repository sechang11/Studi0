#!/usr/bin/env bash
# Bring the studio back after a reboot. Installed as a user @reboot crontab entry,
# which needs no root - unlike systemd user units, which require `loginctl
# enable-linger` to run without an active login session.
#
# The box rebooted three times on 2026-08-03 and came back with nothing running.
#
# Every line this logs is CHECKED before it is written. An earlier version logged
# "studio server started" immediately after launching it, which was a claim rather
# than an observation - and it read as success during a window when the port was
# genuinely not yet listening.
set -uo pipefail
cd "$HOME/shared/comfy-studio" || exit 1
LOG=/tmp/boot-services.log
say() { echo "$(date -Is)  $*" >> "$LOG"; }

say "=== boot ==="
sleep 15   # let the network settle; ComfyUI binds 0.0.0.0 and DHCP may still be up

up() { ss -tln 2>/dev/null | grep -q ":$1 "; }

if up 8188; then
  say "comfyui already listening"
else
  bash scripts/restart-comfy.sh >> "$LOG" 2>&1
  for i in $(seq 1 30); do up 8188 && break; sleep 1; done
  up 8188 && say "comfyui UP after ${i}s" || say "comfyui FAILED to bind 8188"
fi

if up 8777; then
  say "studio already listening"
else
  setsid nohup python3 studio/serve.py >> /tmp/studio-serve.log 2>&1 < /dev/null &
  for i in $(seq 1 20); do up 8777 && break; sleep 1; done
  up 8777 && say "studio UP after ${i}s" || say "studio FAILED to bind 8777"
fi
say "done"
