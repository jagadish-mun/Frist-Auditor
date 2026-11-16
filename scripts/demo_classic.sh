#!/usr/bin/env bash
# One-command demo (Task 16): audit clone_mid against the real Harbor Air, apply one fix, re-audit, open both reports.
#   ./scripts/demo_classic.sh        (or: make demo-classic)
# Starts its own servers on free ports and stops them when done. Output: runs/demo_live/clone_mid/iter_00 (before)
# and iter_01 (after one fix). Never clicks Pay.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[ -x "$PY" ] || { echo "Missing .venv: follow the Setup section of README.md first." >&2; exit 1; }
start=$(date +%s)
"$PY" tools/fix_loop.py clone_mid --iters 1 --out-root runs/demo_live
echo "Demo finished in $(( $(date +%s) - start )) s"
for r in runs/demo_live/clone_mid/iter_00/report.html runs/demo_live/clone_mid/iter_01/report.html; do
  if [ -n "${NO_OPEN:-}" ]; then echo "Report: $r"; elif command -v open >/dev/null; then open "$r"; elif command -v xdg-open >/dev/null; then xdg-open "$r"; else echo "Report: $r"; fi
done
