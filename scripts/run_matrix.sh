#!/usr/bin/env bash
# One model, one slice of the wire pack. Writes Inspect logs under logs/matrix.
# Usage: ./scripts/run_matrix.sh [run-config] [episode] [treatments]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CONFIG="${1:-evals/deepseek-flash.yaml}"
EPISODE="${2:-grid}"
TREATMENTS="${3:-T0,T2}"

if [[ ! -f .env ]]; then
  echo "missing .env"
  exit 1
fi
set -a
# shellcheck disable=SC1091
source .env
set +a
docker info >/dev/null

mapfile -t ARGS < <(uv run python - "$CONFIG" <<'PY'
import sys
from inspect_ai._cli.eval import parse_run_config
params = parse_run_config(sys.argv[1])
model = params.get("model")
if not model:
    raise SystemExit("run config has no model")
print("--model")
print(model)
base = params.get("model_base_url")
if base:
    print("--model-base-url")
    print(base)
PY
)

mkdir -p logs/matrix
uv run inspect eval evals/wire.py \
  "${ARGS[@]}" \
  -T "episode=${EPISODE}" \
  -T "treatments=${TREATMENTS}" \
  --log-dir logs/matrix \
  --display plain
uv run python scripts/matrix_table.py logs/matrix
