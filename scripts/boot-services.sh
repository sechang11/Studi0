#!/usr/bin/env bash
# Bring the studio back after a reboot. Installed as a user @reboot crontab entry,
# which needs no root - a systemd USER unit would need `loginctl enable-linger` and a
# SYSTEM unit would need root to install.
#
# The starting logic itself lives in scripts/studio.sh so there is exactly one
# implementation; this file only adds the things that are specific to boot.
set -uo pipefail
LOG=/tmp/boot-services.log
{
  echo "=== boot $(date -Is) ==="
  # The network is not necessarily up when cron fires. Both services bind 0.0.0.0 and
  # DHCP may still be settling, so give it a moment before claiming a port.
  sleep 15
  bash "$HOME/shared/comfy-studio/scripts/studio.sh" start
  echo "=== done $(date -Is) ==="
} >>"$LOG" 2>&1
