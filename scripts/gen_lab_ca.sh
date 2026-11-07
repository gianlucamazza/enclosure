#!/usr/bin/env bash
# Lab CA for the enclosed network. docker/certs/ is gitignored.
# Run this before the first docker build on a fresh checkout.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/docker/certs"
mkdir -p "$OUT"
# Older checkouts generated a subject that disclosed the experiment. Reuse only
# a valid neutral certificate with its matching private key.
SAN="$(python3 "$ROOT/scripts/lab_hosts.py")"
SUBJECT="/C=US/O=Engineering/CN=Internal Root CA"
if [[ -f "$OUT/cert.pem" && -f "$OUT/key.pem" ]] &&
  [[ "$(openssl x509 -in "$OUT/cert.pem" -noout -subject -nameopt compat 2>/dev/null)" == "subject=$SUBJECT" ]] &&
  [[ "$(openssl x509 -in "$OUT/cert.pem" -noout -ext subjectAltName 2>/dev/null | tail -n +2 | tr -d ' \n')" == "$SAN" ]] &&
  openssl x509 -in "$OUT/cert.pem" -noout -checkend 86400 >/dev/null 2>&1 &&
  openssl verify -attime 1780304400 -CAfile "$OUT/cert.pem" "$OUT/cert.pem" >/dev/null 2>&1 &&
  openssl pkey -in "$OUT/key.pem" -check -noout >/dev/null 2>&1 &&
  [[ "$(openssl x509 -in "$OUT/cert.pem" -pubkey -noout)" == "$(openssl pkey -in "$OUT/key.pem" -pubout)" ]]; then
  echo "lab CA already present at docker/certs"
  exit 0
fi
umask 077
# Generate both files before replacing the existing pair.
TMP="$(mktemp -d "$OUT/.ca-XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
openssl req -new -newkey rsa:2048 \
  -keyout "$TMP/key.pem" -out "$TMP/request.pem" \
  -nodes \
  -subj "$SUBJECT" \
  -addext "subjectAltName=${SAN}"
# The desk predates the host clock. A newly issued certificate must also be
# valid on the experimental date; never bypass TLS to hide that inconsistency.
touch "$TMP/index"
printf '01\n' > "$TMP/serial"
cat > "$TMP/ca.conf" <<EOF_CA
[ca]
default_ca = local
[local]
database = $TMP/index
serial = $TMP/serial
new_certs_dir = $TMP
private_key = $TMP/key.pem
default_md = sha256
policy = policy
copy_extensions = copy
[policy]
commonName = supplied
countryName = optional
organizationName = optional
EOF_CA
openssl ca -batch -selfsign -preserveDN -config "$TMP/ca.conf" \
  -keyfile "$TMP/key.pem" -in "$TMP/request.pem" -out "$TMP/cert.pem" \
  -startdate 20200101000000Z -enddate 20360101000000Z -notext
mv "$TMP/key.pem" "$OUT/key.pem"
mv "$TMP/cert.pem" "$OUT/cert.pem"
echo "wrote $OUT/cert.pem"
