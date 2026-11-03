"""Hostnames the lab serves. Stdlib only so gen_lab_ca.sh can run this before uv sync."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def lab_hosts_path() -> Path:
    start = Path(__file__).resolve()
    for parent in (start.parent, *start.parents):
        candidate = parent / "docker" / "lab-hosts.txt"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("docker/lab-hosts.txt")


def load_lab_hosts(path: Path | None = None) -> list[str]:
    text = (path or lab_hosts_path()).read_text(encoding="utf-8")
    hosts: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        hosts.append(line)
    if not hosts:
        raise ValueError("lab host list is empty")
    return hosts


def san_extension(hosts: Iterable[str] | None = None) -> str:
    """OpenSSL -addext subjectAltName value: DNS:a,DNS:b,..."""
    names = list(hosts) if hosts is not None else load_lab_hosts()
    if not names:
        raise ValueError("SAN host list is empty")
    return ",".join(f"DNS:{name}" for name in names)


if __name__ == "__main__":
    print(san_extension())
