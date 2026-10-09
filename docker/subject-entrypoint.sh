#!/bin/sh
# Record the Ministry address before the subject runs. Later execs,
# including python and curl, read this file.
getent ahostsv4 ministry 2>/dev/null | awk '{print $1; exit}' > /etc/ministry-ip || true
# LD_PRELOAD is already on, so this file has to exist in the image. Recreate
# the stopped desk clock only if a start wiped it.
if [ ! -s /etc/faketimerc ]; then
  printf '%s\n' '2026-06-01 09:00:00' > /etc/faketimerc || true
fi
exec "$@"
