# Releasing

The name `enclosure` on PyPI belongs to an unrelated project. This project is
**not** published to PyPI, and releases are git-only (tags on the repository).

Install from source:

```bash
uv pip install git+https://github.com/gianlucamazza/enclosure
```

or clone and sync:

```bash
git clone https://github.com/gianlucamazza/enclosure
cd enclosure
uv sync
```

The version lives only in `pyproject.toml`; `enclosure.__version__` is read
from the installed package metadata.
