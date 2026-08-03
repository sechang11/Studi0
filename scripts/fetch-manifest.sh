#!/usr/bin/env bash
# fetch-manifest.sh - download the files listed in a plan-models.py manifest.
#
#   python3 scripts/plan-models.py <templates...> -o /tmp/plan.tsv
#   bash scripts/fetch-manifest.sh /tmp/plan.tsv                 # everything
#   bash scripts/fetch-manifest.sh /tmp/plan.tsv --max-gib 5     # skip the whales
#   bash scripts/fetch-manifest.sh /tmp/plan.tsv --only lora     # only rows whose dir matches
#   bash scripts/fetch-manifest.sh /tmp/plan.tsv --dry-run
#
# Manifest is TSV: directory <TAB> filename <TAB> bytes <TAB> url
#
# Reuses fetch-models.sh's get() so you inherit its resume, size-verification and
# hf-xet-then-curl fallback rather than reimplementing them badly here.
set -uo pipefail

MANIFEST="${1:?usage: fetch-manifest.sh <manifest.tsv> [--max-gib N] [--only SUBSTR] [--dry-run]}"
shift
[[ -f "$MANIFEST" ]] || { echo "no such manifest: $MANIFEST" >&2; exit 1; }

MAX_GIB=""; ONLY=""; DRY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-gib) MAX_GIB="$2"; shift 2 ;;
    --only)    ONLY="$2";    shift 2 ;;
    --dry-run) DRY=1;        shift ;;
    *) echo "unknown flag: $1" >&2; exit 1 ;;
  esac
done

HERE="$(cd "$(dirname "$0")" && pwd)"
# Pull in get(), remote_size(), $M and the auth/staging setup. `list` is a no-op
# tier that prints what is installed, so sourcing it has no side effects.
# shellcheck disable=SC1090
source "$HERE/fetch-models.sh" list >/dev/null 2>&1 || true

skipped=0; total=0
while IFS=$'\t' read -r dir name bytes url; do
  [[ -n "${url:-}" ]] || continue
  if [[ -n "$ONLY" && "$dir" != *"$ONLY"* ]]; then continue; fi
  if [[ -n "$MAX_GIB" && -n "$bytes" && "$bytes" -gt 0 ]]; then
    if (( bytes > $(printf '%.0f' "$(echo "$MAX_GIB * 1073741824" | bc)") )); then
      printf '  skip %-52s (%.1f GiB > --max-gib %s)\n' "$name" \
        "$(echo "scale=3;$bytes/1073741824" | bc)" "$MAX_GIB"
      skipped=$((skipped + 1)); continue
    fi
  fi
  total=$((total + 1))
  if (( DRY )); then
    printf '  would fetch %-18s %s\n' "$dir" "$name"
  else
    get "$dir" "$url" "$name"
  fi
done < "$MANIFEST"

echo
echo "manifest done: $total fetched, $skipped skipped by filter"
echo "  bash $HERE/fetch-models.sh list"
