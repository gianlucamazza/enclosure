"""Materialize planted filesystem documents into the subject's workspace."""

from __future__ import annotations

import os
from pathlib import Path

from enclosure.world import World

SUBJECT_PREFIX = "/home/agent/"
ROOT_ENV = "SUBJECT_FS_ROOT"


def subject_rel(path: str) -> str:
    if path.startswith(SUBJECT_PREFIX):
        return path[len(SUBJECT_PREFIX) :]
    return path.lstrip("/")


def sync_subject_fs(world: World, root: str | Path | None = None) -> list[str]:
    """Write live planted files and remove holed ones under root."""
    root_s = str(root or os.environ.get(ROOT_ENV) or "")
    if not root_s:
        return []
    root_p = Path(root_s)
    root_p.mkdir(parents=True, exist_ok=True)

    live_rel: set[str] = set()
    written: list[str] = []
    for doc in world.live_docs("fs"):
        rel = subject_rel(doc.path)
        live_rel.add(rel)
        dest = root_p / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(doc.body, encoding="utf-8")
        written.append(str(dest))

    for path in world.all_paths("fs"):
        rel = subject_rel(path)
        if rel in live_rel:
            continue
        dest = root_p / rel
        if dest.is_file():
            dest.unlink()

    return written


def maybe_sync(world: World) -> list[str]:
    return sync_subject_fs(world)
