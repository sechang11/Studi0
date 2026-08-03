#!/usr/bin/env bash
# chain-fetch.sh - wait for a running fetch-models.sh to finish, then run more tiers.
#
#   bash scripts/chain-fetch.sh bigmodels explore vace
#
# First argument is the tier to WAIT FOR; the rest are run in order afterwards.
# Downloads are bandwidth-bound, so running tiers back to back beats running them
# in parallel - two concurrent pulls just halve each other's throughput.
#
# Self-match trap: pgrep -f 'fetch-models.sh bigmodels' also matches THIS script's
# own command line if the tier name is in our argv. Filter our own PID out, or the
# wait returns immediately (or never). Same class of bug as the pkill warning in
# README.md.
set -uo pipefail

WAIT_FOR="${1:?first arg: tier to wait for}"
shift
[[ $# -gt 0 ]] || { echo "give at least one tier to run afterwards" >&2; exit 1; }

HERE="$(cd "$(dirname "$0")" && pwd)"
SELF=$$

still_running() {
  local pids
  pids=$(pgrep -f "fetch-models.sh $WAIT_FOR" 2>/dev/null | grep -v "^${SELF}$" || true)
  [[ -n "$pids" ]]
}

echo "waiting for 'fetch-models.sh $WAIT_FOR' to finish..."
waited=0
while still_running; do
  sleep 60
  waited=$((waited + 60))
  (( waited % 600 == 0 )) && echo "  ... still waiting (${waited}s)"
  (( waited > 6*3600 )) && { echo "gave up after 6h" >&2; exit 3; }
done
echo "'$WAIT_FOR' finished after ${waited}s"

for tier in "$@"; do
  echo
  echo "################ $tier ################"
  bash "$HERE/fetch-models.sh" "$tier" || echo "!! tier '$tier' reported errors" >&2
done

echo
echo "chain complete. Verify and restart:"
echo "  bash $HERE/fetch-models.sh list"
echo "  bash $HERE/restart-comfy.sh"
