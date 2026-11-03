# Changelog

## Unreleased (package version 0.3.1, not bumped)

- Lab hostnames live in `docker/lab-hosts.txt`. The CA SAN and both compose
  files are checked against that list (adds `en.wikipedia.org`,
  `peps.python.org`, `docs.aws.amazon.com`).
- Version is single-sourced from `pyproject.toml`; `enclosure.__version__` now
  reads installed package metadata (fallback `0.0.0+unknown`).
- `LICENSE` is included in wheel and sdist (SPDX `license = "MIT"`, `license-files`).
- Documented that the `enclosure` name on PyPI belongs to an unrelated project;
  install from git (see `RELEASING.md`).
- Bumped `opentelemetry-api` to 1.45.2 (GHSA-xcq7-p3pf-p88h).
