"""Image decode coverage for the locked Pillow (JPEG + plot PNG path)."""

from __future__ import annotations

import importlib.util
from io import BytesIO
from pathlib import Path

from PIL import Image

_path = Path(__file__).resolve().parents[1] / "scripts" / "plot_matrix.py"
_spec = importlib.util.spec_from_file_location("plot_matrix", _path)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
write_figures = _mod.write_figures

ROWS = [
    {
        "sample": "wire.grid.T0",
        "treatment": "T0",
        "belief_stated": 1,
        "belief_adoption": 0.0,
        "verification_seeking": 1.0,
    },
    {
        "sample": "wire.grid.T2",
        "treatment": "T2",
        "belief_stated": 1,
        "belief_adoption": 1.0,
        "verification_seeking": 0.25,
    },
]


def test_jpeg_decode_roundtrip():
    source = Image.new("RGB", (16, 12), color=(200, 40, 60))
    buffer = BytesIO()
    source.save(buffer, format="JPEG")
    buffer.seek(0)

    loaded = Image.open(buffer)
    loaded.load()

    assert loaded.format == "JPEG"
    assert loaded.size == (16, 12)
    assert loaded.mode == "RGB"
    assert loaded.getpixel((0, 0))[0] > 128


def test_png_via_plot_matrix_write_figures(tmp_path):
    written = write_figures(ROWS, tmp_path)
    pngs = [path for path in written if path.suffix == ".png"]
    assert pngs, "write_figures should emit at least one PNG"

    for path in pngs:
        with Image.open(path) as loaded:
            loaded.load()
            assert loaded.format == "PNG"
            assert loaded.size[0] > 0
            assert loaded.size[1] > 0
            loaded.getpixel((0, 0))
