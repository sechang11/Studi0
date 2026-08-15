#!/usr/bin/env bash
# Thin wrapper (ARCHITECTURE Phase 3): the generator lives in studio/_tools/generate.py,
# mode `roll`. Same flags as before - --hours/--minutes, --weights, --seed, --options,
# --dry, --stop, --status - and the same console line format, which generate_routes.status
# parses. The deadline is still the first feature: a budget is mandatory, because an
# unbounded loop once held this GPU for 17h22m and starved three jobs.
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$REPO/studio/_tools/generate.py" roll "$@"
