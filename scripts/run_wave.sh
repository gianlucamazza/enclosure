#!/usr/bin/env bash
# Wave 2. T0 and T2 on grid and python27, temperature 1, three epochs.
# Usage: ./scripts/run_wave.sh {flash|gemini|all|grid-band}
# Logs go to logs/wave-2. pilot-v2 and matrix are left alone.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ $# -ne 1 ]]; then
  echo "usage: ./scripts/run_wave.sh {flash|gemini|all|grid-band}" >&2
  exit 1
fi

TARGET="$1"
case "$TARGET" in
  flash|gemini|all|grid-band) ;;
  *)
    echo "unknown target: $TARGET" >&2
    echo "usage: ./scripts/run_wave.sh {flash|gemini|all|grid-band}" >&2
    exit 1
    ;;
esac

if [[ ! -f .env ]]; then
  echo "missing .env" >&2
  exit 1
fi
set -a
# shellcheck disable=SC1091
source .env
set +a
docker info >/dev/null

LOG_DIR="${LOG_DIR:-logs/wave-2}"
mkdir -p "$LOG_DIR"

run_eval() {
  local model="$1"
  local base_url="$2"
  local task="$3"
  shift 3
  local -a reasoning=()
  if [[ "$model" == deepseek/* ]]; then
    reasoning=(--reasoning-effort none)
  fi
  uv run inspect eval "$task" \
    --model "$model" \
    --model-base-url "$base_url" \
    --temperature 1 \
    --epochs 3 \
    --max-samples 1 \
    --max-sandboxes 1 \
    --log-dir "$LOG_DIR" \
    --display plain \
    "${reasoning[@]}" \
    "$@"
  # Inspect can return 0 after writing an error log. The log status is the check.
  uv run python - "$LOG_DIR" <<'PY'
import sys
from pathlib import Path
from inspect_ai.log import read_eval_log

root = Path(sys.argv[1])
logs = sorted(root.glob("*.eval"))
if not logs:
    raise SystemExit(f"no log in {root}")
log = read_eval_log(str(logs[-1]))
if log.status != "success":
    raise SystemExit(f"{logs[-1].name} status {log.status}")
PY
}

run_flash() {
  run_eval deepseek/deepseek-flash https://api.deepseek.com \
    evals/wire.py -T episode=grid -T treatments=T0,T2
  run_eval deepseek/deepseek-flash https://api.deepseek.com \
    evals/times.py -T prior=contradicts -T treatments=T0,T2
}

run_gemini() {
  run_eval openrouter/google/gemini-3.8-flash https://openrouter.ai/api/v1 \
    evals/wire.py -T episode=grid -T treatments=T0,T2
  run_eval openrouter/google/gemini-3.8-flash https://openrouter.ai/api/v1 \
    evals/times.py -T prior=contradicts -T treatments=T0,T2
}

run_grid_band() {
  # T2 is already in the flash wave. This adds the two corroboration levels.
  run_eval deepseek/deepseek-flash https://api.deepseek.com \
    evals/wire.py -T episode=grid -T treatments=T1,T3
}

case "$TARGET" in
  flash) run_flash ;;
  gemini) run_gemini ;;
  all)
    run_flash
    run_gemini
    ;;
  grid-band) run_grid_band ;;
esac

uv run python scripts/matrix_table.py "$LOG_DIR"
