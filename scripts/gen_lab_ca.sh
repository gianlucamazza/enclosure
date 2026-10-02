#!/usr/bin/env bash
# Lab CA for the enclosed network. The key is gitignored (*.pem).
# Run this before the first docker build on a fresh checkout.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/docker/certs"
mkdir -p "$OUT"
if [[ -f "$OUT/cert.pem" && -f "$OUT/key.pem" ]]; then
  echo "lab CA already present at docker/certs"
  exit 0
fi
umask 077
openssl req -x509 -newkey rsa:2048 \
  -keyout "$OUT/key.pem" -out "$OUT/cert.pem" \
  -days 3650 -nodes \
  -subj "/CN=Ministry Lab CA" \
  -addext "subjectAltName=DNS:ministry,DNS:www.python.org,DNS:python.org,DNS:docs.python.org,DNS:discuss.python.org,DNS:example.com,DNS:www.example.com,DNS:www.google.com,DNS:google.com,DNS:www.reddit.com,DNS:www.suezcanal.gov.eg,DNS:earthquake.usgs.gov,DNS:www.swpc.noaa.gov,DNS:www.ercot.com,DNS:www.eia.gov,DNS:status.aws.amazon.com,DNS:health.aws.amazon.com"
echo "wrote $OUT/cert.pem"
