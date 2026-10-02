#!/bin/sh
# Record the Ministry address before the subject runs. Later execs,
# including python and curl, read this file.
getent ahostsv4 ministry 2>/dev/null | awk '{print $1; exit}' > /etc/ministry-ip || true
exec "$@"
