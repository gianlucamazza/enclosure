#!/usr/bin/env bash
# Asch curve on one episode: 0, 1, and 3 party colleagues.
# Templates unless ENCLOSURE_COLLEAGUE_MODEL is set.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CONFIG="${1:-evals/deepseek-flash.yaml}"
EPISODE="${2:-grid}"
TREATMENTS="${3:-T2}"
mkdir -p logs/asch
for social in none one_party three_party; do
  echo "== social=${social} =="
  LOG_DIR="logs/asch" ./scripts/run_matrix.sh "$CONFIG" "$EPISODE" "$TREATMENTS" "$social"
done
uv run python scripts/matrix_table.py logs/asch
