"""Reconstructable inputs for new campaigns; never infer historical metadata."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


def digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def manifest(root: Path, scenario: str, prompt: str, backend: str) -> dict:
    def git(*args: str) -> str:
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else "unknown"

    images = {}
    for name in ("enclosure-vm", "enclosure-ministry"):
        result = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{.Id}}", name],
            capture_output=True,
            text=True,
        )
        images[name] = result.stdout.strip() if result.returncode == 0 else "unknown"
    source_hashes = {
        str(p.relative_to(root)): digest(p) for p in sorted((root / "src").rglob("*.py"))
    }
    return {
        "schema": 1,
        "commit": git("rev-parse", "HEAD"),
        "dirty": bool(git("status", "--porcelain")),
        "backend": backend,
        "scenario_sha256": digest(root / scenario),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "lock_sha256": digest(root / "uv.lock"),
        "scorer_sha256": digest(root / "src/enclosure/scoring.py"),
        "runtime_config_sha256": digest(
            root / ("evals/compose.vm.yaml" if backend == "vm" else "evals/compose.yaml")
        ),
        "images": images,
        "source_hashes": source_hashes,
        "labels": "unreviewed",
    }
