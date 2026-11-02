#!/usr/bin/env bash
# Prove the ministry image installed the uv.lock graph.
# Prints pip freeze from the image and diffs it against
# `uv export --frozen --no-dev` (markers evaluated for the image).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

IMAGE="${MINISTRY_LOCK_IMAGE:-enclosure-ministry-lock}"
if [ -z "${MINISTRY_LOCK_SKIP_BUILD:-}" ]; then
  docker build -f docker/Dockerfile.ministry -t "$IMAGE" .
fi

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT
EXPORT_FILE="$WORKDIR/uv-export.txt"
FREEZE_FILE="$WORKDIR/pip-freeze.txt"

uv export --frozen --no-dev >"$EXPORT_FILE"
echo "== uv export --frozen --no-dev"
cat "$EXPORT_FILE"

PY_FULL="$(docker run --rm --entrypoint python "$IMAGE" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')"
PY_MINOR="${PY_FULL%.*}"
SITE="$(docker run --rm --entrypoint python "$IMAGE" -c 'import site; print(site.getsitepackages()[0])')"
docker run --rm --entrypoint /usr/local/bin/python "$IMAGE" -m pip freeze --path "$SITE" >"$FREEZE_FILE"
echo "== pip freeze (ministry image, venv site-packages)"
cat "$FREEZE_FILE"

export EXPORT_FILE FREEZE_FILE PY_FULL PY_MINOR
uv run python - <<'PY'
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from packaging.markers import Marker, default_environment

SKIP = {"enclosure", "pip", "setuptools", "wheel"}

env = default_environment()
env.update(
    {
        "sys_platform": "linux",
        "platform_system": "Linux",
        "os_name": "posix",
        "platform_machine": "x86_64",
        "platform_python_implementation": "CPython",
        "python_version": os.environ["PY_MINOR"],
        "python_full_version": os.environ["PY_FULL"],
        "implementation_name": "cpython",
        "extra": "",
    }
)


def pep503(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def eval_marker(marker: str) -> bool:
    return Marker(marker).evaluate(env)


def logical_lines(text: str) -> list[str]:
    joined: list[str] = []
    buf: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.endswith("\\"):
            buf.append(line[:-1].rstrip())
            continue
        buf.append(line)
        joined.append(" ".join(part.strip() for part in buf if part.strip()))
        buf = []
    if buf:
        joined.append(" ".join(part.strip() for part in buf if part.strip()))
    return joined


def parse_export(text: str) -> dict[str, str]:
    pkgs: dict[str, str] = {}
    for line in logical_lines(text):
        line = re.sub(r"\s+--hash=sha256:[0-9a-fA-F]+", "", line).strip()
        if not line or line.startswith("#") or line.startswith("--"):
            continue
        if line.startswith("-e ") or line.startswith("-e\t"):
            continue
        marker = None
        if " ; " in line:
            line, marker = line.split(" ; ", 1)
            line, marker = line.strip(), marker.strip()
        match = re.match(r"^([A-Za-z0-9_.+-]+(?:\[[^\]]+\])?)==(.+)$", line)
        if not match:
            continue
        name, version = match.group(1), match.group(2).strip()
        name = re.sub(r"\[.*\]", "", name)
        key = pep503(name)
        if key in SKIP:
            continue
        if marker and not eval_marker(marker):
            continue
        pkgs[key] = version
    return pkgs


def parse_freeze(text: str) -> dict[str, str]:
    pkgs: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if " @ " in line:
            continue
        match = re.match(r"^([A-Za-z0-9_.+-]+)==(.+)$", line)
        if not match:
            continue
        name, version = match.group(1), match.group(2)
        key = pep503(name)
        if key in SKIP:
            continue
        pkgs[key] = version
    return pkgs


def fmt(pkgs: dict[str, str]) -> str:
    return "\n".join(f"{name}=={pkgs[name]}" for name in sorted(pkgs))


expected = parse_export(Path(os.environ["EXPORT_FILE"]).read_text(encoding="utf-8"))
actual = parse_freeze(Path(os.environ["FREEZE_FILE"]).read_text(encoding="utf-8"))

missing = sorted(name for name in expected if name not in actual)
extra = sorted(name for name in actual if name not in expected)
changed = sorted(
    f"{name}: lock {expected[name]} != image {actual[name]}"
    for name in expected
    if name in actual and expected[name] != actual[name]
)

print("== normalized lock (image platform)")
print(fmt(expected))
print("== normalized pip freeze")
print(fmt(actual))
print(f"== counts expected={len(expected)} actual={len(actual)}")

if missing or extra or changed:
    if missing:
        print("missing from image:")
        for name in missing:
            print(f"  {name}=={expected[name]}")
    if extra:
        print("extra in image:")
        for name in extra:
            print(f"  {name}=={actual[name]}")
    if changed:
        print("version mismatch:")
        for line in changed:
            print(f"  {line}")
    sys.exit(1)

print("ministry image matches uv.lock")
PY
