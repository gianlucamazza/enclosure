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
    for name in (
        ("enclosure-vm", "enclosure-ministry") if backend == "vm" else ("enclosure-ministry",)
    ):
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", "--format", "{{.Id}}", name],
                capture_output=True,
                text=True,
            )
            images[name] = result.stdout.strip() if result.returncode == 0 else "unknown"
        except OSError:
            images[name] = "unknown"
    source_hashes = {
        str(p.relative_to(root)): digest(p) for p in sorted((root / "src").rglob("*.py"))
    }
    return {
        "schema": 2,
        "image_capture": "requested_tags_only",
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


async def running_images(environments: dict) -> dict:
    """Resolve immutable images from running containers, never from mutable tags."""
    import asyncio

    captured = {}
    for service, environment in environments.items():
        connection = await environment.connection()
        container = connection.container
        if not container:
            raise RuntimeError(f"No running container for {service}")
        result = await asyncio.to_thread(
            subprocess.run,
            ["docker", "inspect", "--format", "{{.Image}}", container],
            capture_output=True,
            text=True,
        )
        image = result.stdout.strip()
        if result.returncode or not image.startswith("sha256:"):
            raise RuntimeError(f"Cannot resolve runtime image for {service}")
        captured[service] = {"container": container, "image_id": image}
    return {"schema": 1, "capture": "running_container", "services": captured}
