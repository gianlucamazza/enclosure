"""Redact known credentials from a JSON log snapshot; still requires publication review."""

from __future__ import annotations

import re

SENSITIVE = re.compile(
    r"^(?:(?:.*[_-])?(?:token|api[_-]?key|password|secret)|authorization|account(?:_id)?|email)$",
    re.I,
)
BEARER = re.compile(r"(?i)Bearer\s+[^\s\"'<>]+")
EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
LOCAL_PATH = re.compile(r"/(?:home|Users)/[^/\s\"']+")


def sanitize(snapshot: dict, private_paths: tuple[str, ...] = ()) -> dict:
    secrets: set[str] = set()

    def collect(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if SENSITIVE.search(str(key)) and isinstance(item, str) and len(item) >= 4:
                    secrets.add(item)
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(snapshot)

    def clean(value):
        if isinstance(value, dict):
            return {
                str(k): "[REDACTED]" if SENSITIVE.search(str(k)) else clean(v)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [clean(v) for v in value]
        if isinstance(value, str):
            for secret in sorted(secrets, key=len, reverse=True):
                value = value.replace(secret, "[REDACTED]")
            for path in sorted(private_paths, key=len, reverse=True):
                if len(path) > 1:
                    value = value.replace(path, "[LOCAL_PATH]")
            return LOCAL_PATH.sub(
                "/home/[USER]", EMAIL.sub("[EMAIL]", BEARER.sub("Bearer [REDACTED]", value))
            )
        return value

    return clean(snapshot)
