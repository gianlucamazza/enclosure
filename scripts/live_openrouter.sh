#!/usr/bin/env bash
# Live Times smoke through OpenRouter: tool ping, then one T0 episode.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CONFIG="${1:-evals/openrouter/gemini-3.8-flash-live.yaml}"

if [[ ! -f .env ]]; then
  echo "missing .env (copy .env.example and set OPENROUTER_API_KEY)"
  exit 1
fi
set -a
# shellcheck disable=SC1091
source .env
set +a
if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "OPENROUTER_API_KEY is empty"
  exit 1
fi
docker info >/dev/null

echo "== openrouter tool ping =="
uv run python scripts/openrouter_ping.py

echo "== inspect eval ${CONFIG} =="
mkdir -p logs/live
uv run inspect eval --run-config "$CONFIG" --log-dir logs/live --display plain
