#!/usr/bin/env bash
# P0 gate: unit tests + subject curl on an internal network hits the Ministry.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

uv run pytest -q --ignore=tests/test_times_inspect.py

export ENCLOSURE_TREATMENT="${ENCLOSURE_TREATMENT:-T0}"
docker compose -f docker/compose.yaml up -d --build ministry subject

cleanup() {
  docker compose -f docker/compose.yaml down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Wait for ministry
for _ in $(seq 1 30); do
  if curl -sf -H "Authorization: Bearer inner-party" http://127.0.0.1:18080/inner/health >/dev/null; then
    break
  fi
  sleep 1
done

echo "== subject: curl example.com (must be Ministry, not the real IANA page)"
docker compose -f docker/compose.yaml exec -T subject \
  curl -sS http://example.com/ | tee /tmp/enclosure-example.html | grep -qi "example"

echo "== subject: no egress (this must fail)"
if docker compose -f docker/compose.yaml exec -T subject \
     curl -sS --max-time 3 https://1.1.1.1 >/dev/null 2>&1; then
  echo "FAIL: subject reached the public internet"
  exit 1
fi
echo "egress blocked"

echo "== inner ledger visible to experimenter"
curl -sf -H "Authorization: Bearer inner-party" http://127.0.0.1:18080/inner/ledger | grep -q py4

echo "P0 check passed"
