# Releasing

The name `enclosure` on PyPI belongs to an unrelated project. This project is
**not** published to PyPI, and releases are git-only (tags on the repository).

Package-only installation (does not supply scenario/Compose assets for episodes):

```bash
uv pip install git+https://github.com/gianlucamazza/enclosure
```

For running experiments, use a source checkout:

```bash
git clone https://github.com/gianlucamazza/enclosure
cd enclosure
uv sync --group dev
```

The version lives only in `pyproject.toml`; `enclosure.__version__` is read
from the installed package metadata.


Before releasing the VM runtime, publish the implementation, run the dedicated
KVM CI job, and resolve [#36](https://github.com/gianlucamazza/enclosure/issues/36).
Validate `uv run pytest -q`, the opt-in
`ENCLOSURE_VM_TESTS=1 uv run pytest -q tests/test_vm_inspect.py`, lint, mypy and
`uv build`. The default suite skips the opt-in VM tests.

Build success and `enclosure --help` alone do not prove that a wheel can run an
episode. Asset packaging and the installed-runner smoke remain tracked in
[#41](https://github.com/gianlucamazza/enclosure/issues/41). Keep generated
certificates, private keys and unreviewed logs out of the release. Do not pool
new VM measurements with the historical container sittings.
