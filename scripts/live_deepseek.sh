#!/usr/bin/env bash
# Live Times smoke: ping DeepSeek, then one T0 episode in the Ministry sandbox.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CONFIG="${1:-evals/deepseek-flash-live.yaml}"

if [[ ! -f .env ]]; then
  echo "missing .env (copy .env.example and set DEEPSEEK_API_KEY)"
  exit 1
fi
set -a
# shellcheck disable=SC1091
source .env
set +a
if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "DEEPSEEK_API_KEY is empty"
  exit 1
fi
docker info >/dev/null

echo "== deepseek tool ping =="
uv run python scripts/deepseek_ping.py

echo "== inspect eval ${CONFIG} =="
mkdir -p logs/live
uv run inspect eval --run-config "$CONFIG" --log-dir logs/live --display plain
