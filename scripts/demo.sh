#!/usr/bin/env bash
# Live demo (Task 21): generate a brand-new site and a clone with planted defects, audit the clone, score the tickets
# against the answer key, keep the report, delete the generated sites.
#   make demo                 random seed (printed)
#   SEED=1234 make demo       replay a run exactly
#   NO_OPEN=1 make demo       do not open the report
# Output (kept): runs/demo_live/<timestamp>_seed<N>/ (report.html, shots/, answer_key.json, scorecard.json).
# After a successful run both sites STAY UP, detached, on http://localhost:8101 (real) and :8102 (clone), or free ports
# if those are taken; runs/demo_live/.active_demo.json records them. `make end-demo` stops them and deletes the temp dir;
# `make demo-status` shows them. A new `make demo` ends an active one first.
# On failure or Ctrl-C before the run succeeds, the servers and the temp dir are removed, as before. Never clicks Pay.
# Fallback: make demo-classic (the Harbor Air fix-loop demo).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
STATE=runs/demo_live/.active_demo.json
[ -x "$PY" ] || { echo "Missing .venv: follow the Setup section of README.md first." >&2; exit 1; }
SEED="${SEED:-$(( (RANDOM << 15 | RANDOM) % 1000000 ))}"
[[ "$SEED" =~ ^[0-9]+$ ]] || { echo "SEED must be a non-negative integer" >&2; exit 2; }
if [ -e "$STATE" ]; then
  echo "A demo is still active; ending it first."
  "$PY" gen/active.py end
fi
OUT="runs/demo_live/$(date +%Y%m%d-%H%M%S)_seed${SEED}"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/ffdemo.XXXXXX")"
TMP="$(cd "$TMP" && pwd -P)"     # canonical path: it is also the pattern used to find leftover servers
KEEP=0
cleanup() {
  [ "$KEEP" = 1 ] && return 0                # successful run: the sites stay up until `make end-demo`
  pkill -f "$TMP/" 2>/dev/null || true       # servers run from $TMP; normally already stopped by the Python side
  rm -rf "$TMP"
  if [ -e "$STATE" ] && grep -qF "$TMP" "$STATE"; then rm -f "$STATE"; fi   # interrupted right after it was written
}
trap cleanup EXIT
trap 'echo "Interrupted; cleaning up." >&2; exit 130' INT TERM
echo "Seed: $SEED   (replay: SEED=$SEED make demo)"
echo "TMP $TMP"
start=$(date +%s)
"$PY" gen/demo.py --seed "$SEED" --tmp "$TMP" --out "$OUT"
KEEP=1
echo "Demo finished in $(( $(date +%s) - start )) s"
echo
if [ -z "${NO_OPEN:-}" ]; then
  opener=$(command -v open || command -v xdg-open || true)
  if [ -n "$opener" ]; then
    "$PY" -c 'import json,sys; s=json.load(open(sys.argv[1])); print(s["report"]); print(s["real"]["url"]); print(s["clone"]["url"])' "$STATE" |
      while read -r target; do "$opener" "$target" || true; done
  fi
fi
"$PY" gen/active.py banner
