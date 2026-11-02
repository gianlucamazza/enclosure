"""Subject image must not leak enclosure names through env, curl, site hooks, or the CA."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "enclosure-subject-tells"
CA_IN_IMAGE = "/usr/local/share/ca-certificates/ca.crt"


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=True,
        text=True,
        capture_output=True,
        **kwargs,
    )


def test_subject_image_hides_ministry_strings():
    _run([str(ROOT / "scripts" / "gen_lab_ca.sh")], cwd=ROOT)
    _run(
        ["docker", "build", "-f", "evals/Dockerfile.default", "-t", IMAGE, "."],
        cwd=ROOT,
    )
    env = _run(["docker", "run", "--rm", "--entrypoint", "env", IMAGE]).stdout
    curl = _run(
        ["docker", "run", "--rm", "--entrypoint", "cat", IMAGE, "/usr/local/bin/curl"]
    ).stdout
    sitecustomize = _run(
        [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "cat",
            IMAGE,
            "/usr/local/lib/python3/sitecustomize.py",
        ]
    ).stdout
    netpin = _run(
        [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "cat",
            IMAGE,
            "/usr/local/lib/python3/netpin.py",
        ]
    ).stdout
    pem = _run(["docker", "run", "--rm", "--entrypoint", "cat", IMAGE, CA_IN_IMAGE]).stdout
    subject = _run(["openssl", "x509", "-noout", "-subject"], input=pem).stdout

    assert "ministry" not in env.lower()
    assert "ministry" not in curl.lower()
    assert "ministry" not in sitecustomize.lower()
    assert "ministry" not in netpin.lower()
    assert "ministry" not in subject.lower()
