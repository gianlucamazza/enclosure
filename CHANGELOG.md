# Changelog

## Unreleased (package version 0.3.1, not bumped)

- New runs default to a per-sample QEMU/KVM subject (`backend=vm`), with
  an unprivileged guest, RTC initialized before boot, external DNS and TLS
  per hostname, and a TAP boundary that denies public egress and `/inner/`.
  `backend=docker` preserves the legacy runtime. VM mode requires KVM and
  TUN devices plus NET_ADMIN on the controller only; no guest hooks or
  shared workspace mounts are installed. VM acceptance tests run separately.
- Legacy CA generation migrates obsolete or mismatched certificates and
  validates the desk date. Legacy curl/Python now verify TLS.

- Ministry lock check reads `platform_machine` from the image and prints
  skipped direct-reference freeze lines; UV install flags stay off the
  ministry runtime env; lab host helper lives in `scripts/lab_hosts.py`.
- Lab hostnames live in `docker/lab-hosts.txt`. The CA SAN and both compose
  files are checked against that list (adds `en.wikipedia.org`,
  `peps.python.org`, `docs.aws.amazon.com`).
- Version is single-sourced from `pyproject.toml`; `enclosure.__version__` now
  reads installed package metadata (fallback `0.0.0+unknown`).
- `LICENSE` is included in wheel and sdist (SPDX `license = "MIT"`, `license-files`).
- Documented that the `enclosure` name on PyPI belongs to an unrelated project;
  install from git (see `RELEASING.md`).
- Bumped `opentelemetry-api` to 1.45.2 (GHSA-xcq7-p3pf-p88h).
