"""Host list is the single source for the lab CA SAN and compose aliases."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
_path = ROOT / "scripts" / "lab_hosts.py"
_spec = importlib.util.spec_from_file_location("lab_hosts", _path)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
load_lab_hosts = _mod.load_lab_hosts
san_extension = _mod.san_extension

COMPOSE_FILES = ("evals/compose.yaml", "docker/compose.yaml")
COMPOSE_SERVICE_DNS = "ministry"
REQUIRED_HOSTS = ("en.wikipedia.org", "peps.python.org", "docs.aws.amazon.com")
# Every DNS name already on the cert; the host list must keep them.
EXISTING_SAN_HOSTS = (
    "www.python.org",
    "python.org",
    "docs.python.org",
    "discuss.python.org",
    "example.com",
    "www.example.com",
    "www.google.com",
    "google.com",
    "www.reddit.com",
    "www.suezcanal.gov.eg",
    "earthquake.usgs.gov",
    "www.swpc.noaa.gov",
    "www.ercot.com",
    "www.eia.gov",
    "status.aws.amazon.com",
    "health.aws.amazon.com",
)


def _san_hosts(san: str) -> set[str]:
    hosts: set[str] = set()
    for part in san.split(","):
        part = part.strip()
        assert part.startswith("DNS:"), part
        hosts.add(part.removeprefix("DNS:"))
    return hosts


def _compose_data(relative: str) -> dict:
    return yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))


def _compose_subject_hosts(data: dict) -> set[str]:
    """Network aliases, extra_hosts, and the compose service DNS name."""
    hosts: set[str] = set()
    for name, service in (data.get("services") or {}).items():
        if name == COMPOSE_SERVICE_DNS:
            hosts.add(name)
        networks = service.get("networks") or {}
        if isinstance(networks, dict):
            for cfg in networks.values():
                if isinstance(cfg, dict):
                    hosts.update(cfg.get("aliases") or [])
        for entry in service.get("extra_hosts") or []:
            if isinstance(entry, str):
                host = entry.split(":", 1)[0]
                if host:
                    hosts.add(host)
            elif isinstance(entry, dict):
                hosts.update(entry)
    return hosts


def test_san_extension_formats_dns_entries():
    assert san_extension(["a.example", "b.example"]) == "DNS:a.example,DNS:b.example"


def test_lab_hosts_script_prints_san_extension():
    output = subprocess.check_output(
        ["python3", str(ROOT / "scripts" / "lab_hosts.py")],
        text=True,
    )
    assert output.strip() == san_extension()


def test_required_hosts_are_in_the_list_and_san():
    hosts = set(load_lab_hosts())
    san = _san_hosts(san_extension())
    missing = [host for host in REQUIRED_HOSTS if host not in hosts or host not in san]
    assert missing == []


def test_existing_sans_stay_in_the_list_and_san():
    hosts = set(load_lab_hosts())
    san = _san_hosts(san_extension())
    missing = [host for host in EXISTING_SAN_HOSTS if host not in hosts or host not in san]
    assert missing == []


def test_compose_aliases_and_extra_hosts_are_in_the_list_and_san():
    hosts = set(load_lab_hosts())
    san = _san_hosts(san_extension())
    missing: list[str] = []
    for relative in COMPOSE_FILES:
        for name in _compose_subject_hosts(_compose_data(relative)) - {COMPOSE_SERVICE_DNS}:
            if name not in hosts or name not in san:
                missing.append(f"{relative}:{name}")
    assert missing == []


def test_host_list_matches_both_compose_files():
    expected = set(load_lab_hosts()) - {COMPOSE_SERVICE_DNS}
    for relative in COMPOSE_FILES:
        found = _compose_subject_hosts(_compose_data(relative)) - {COMPOSE_SERVICE_DNS}
        assert found == expected, relative


def test_host_list_has_no_duplicates():
    hosts = load_lab_hosts()
    assert len(hosts) == len(set(hosts))


def test_gen_lab_ca_builds_san_from_the_host_list():
    script = (ROOT / "scripts" / "gen_lab_ca.sh").read_text(encoding="utf-8")
    assert "lab_hosts.py" in script or "lab-hosts.txt" in script
    assert "subjectAltName=DNS:" not in script
    assert "/C=US/O=Engineering/CN=Internal Root CA" in script
    assert "-startdate 20200101000000Z" in script


def test_control_service_is_not_in_public_certificate():
    assert "ministry" not in _san_hosts(san_extension())
