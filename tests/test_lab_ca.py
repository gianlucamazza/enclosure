"""Certificate migration and reuse without touching the checkout's CA."""

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_ca_is_replaced_and_neutral_ca_reused(tmp_path):
    for relative in ("scripts/gen_lab_ca.sh", "scripts/lab_hosts.py", "docker/lab-hosts.txt"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    certs = tmp_path / "docker/certs"
    certs.mkdir()
    cert, key = certs / "cert.pem", certs / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "2",
            "-subj",
            "/CN=Ministry Lab CA",
        ],
        check=True,
        capture_output=True,
    )
    legacy = cert.read_bytes()
    script = tmp_path / "scripts/gen_lab_ca.sh"
    subprocess.run([str(script)], check=True, capture_output=True)
    neutral = cert.read_bytes()
    assert neutral != legacy
    subject = subprocess.run(
        [
            "openssl",
            "x509",
            "-in",
            str(cert),
            "-noout",
            "-subject",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "Internal Root CA" in subject
    assert "Ministry" not in subject
    subprocess.run(
        [
            "openssl",
            "verify",
            "-attime",
            "1780304400",
            "-CAfile",
            str(cert),
            str(cert),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run([str(script)], check=True, capture_output=True)
    assert cert.read_bytes() == neutral
    # An invalid key must not make a neutral certificate eligible for reuse.
    key.write_text("invalid key")
    subprocess.run([str(script)], check=True, capture_output=True)
    assert cert.read_bytes() != neutral
