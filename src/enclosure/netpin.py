"""Pin every hostname to a single upstream address. Used by the subject curl wrapper."""

from __future__ import annotations

import re

URL_HOST = re.compile(r"https?://([^/:]+)")


def resolve_args(args: list[str], upstream_ip: str) -> list[str]:
    if not upstream_ip:
        return list(args)
    extra: list[str] = []
    for arg in args:
        match = URL_HOST.match(arg)
        if not match:
            continue
        host = match.group(1)
        extra.extend(
            [
                "--resolve",
                f"{host}:443:{upstream_ip}",
                "--resolve",
                f"{host}:80:{upstream_ip}",
            ]
        )
    return extra + list(args)
