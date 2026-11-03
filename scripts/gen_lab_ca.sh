#!/usr/bin/env bash
# Lab CA for the enclosed network. docker/certs/ is gitignored.
# Run this before the first docker build on a fresh checkout.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/docker/certs"
mkdir -p "$OUT"
if [[ -f "$OUT/cert.pem" && -f "$OUT/key.pem" ]]; then
  echo "lab CA already present at docker/certs"
  exit 0
fi
SAN="$(python3 "$ROOT/src/enclosure/lab_hosts.py")"
umask 077
openssl req -x509 -newkey rsa:2048 \
  -keyout "$OUT/key.pem" -out "$OUT/cert.pem" \
  -days 3650 -nodes \
  -subj "/C=US/O=Engineering/CN=Internal Root CA" \
  -addext "subjectAltName=${SAN}"
echo "wrote $OUT/cert.pem"
