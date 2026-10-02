"""Pin every hostname to the Ministry address. Used by the subject curl wrapper."""

from __future__ import annotations

import re

URL_HOST = re.compile(r"https?://([^/:]+)")


def resolve_args(args: list[str], ministry_ip: str) -> list[str]:
    if not ministry_ip:
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
                f"{host}:443:{ministry_ip}",
                "--resolve",
                f"{host}:80:{ministry_ip}",
            ]
        )
    if extra:
        extra.append("--insecure")
    return extra + list(args)
