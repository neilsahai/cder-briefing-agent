#!/usr/bin/env bash
# Builds the submission ZIP: source (tracked files only — never .env or state), docs, deliverables, scorecard.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-../cder-briefing-agent-submission.zip}"
rm -f "$OUT"
git ls-files -z | xargs -0 zip -q "$OUT"
[ -d frontend/dist ] && zip -qr "$OUT" frontend/dist
zip -q "$OUT" evals/results/SCORECARD.md evals/results/latest_*.json 2>/dev/null || true
echo "wrote $OUT ($(du -h "$OUT" | cut -f1))"
unzip -l "$OUT" | tail -1
