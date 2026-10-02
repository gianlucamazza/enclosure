"""Point every Python socket at the Ministry. The public network is not there."""

from __future__ import annotations

import socket
import ssl

_real_getaddrinfo = socket.getaddrinfo


def _ministry_ip() -> str:
    try:
        return open("/etc/ministry-ip", encoding="utf-8").read().strip()
    except OSError:
        return ""


def _getaddrinfo(host, port, *args, **kwargs):
    ip = _ministry_ip()
    if ip and host not in {"localhost", "127.0.0.1", "::1", "ministry"}:
        host = ip
    return _real_getaddrinfo(host, port, *args, **kwargs)


socket.getaddrinfo = _getaddrinfo
ssl._create_default_https_context = ssl._create_unverified_context
