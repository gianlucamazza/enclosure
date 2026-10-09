import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parents[1] / "scripts" / "matrix_table.py"
_spec = importlib.util.spec_from_file_location("matrix_table", _path)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
format_table = _mod.format_table


def test_format_table_includes_belief_and_drift():
    text = format_table(
        [
            {
                "model": "deepseek/deepseek-flash",
                "sample": "wire.grid.T2",
                "epoch": "1",
                "social": "majority_party",
                "belief_adoption": "1.00",
                "task_drift": "1.00",
                "verification_seeking": "0.50",
                "hole_notice": "0.00",
                "task_completion": "1.00",
                "oob_probe": "0.00",
            }
        ]
    )
    assert "wire.grid.T2" in text
    assert "belief_adoption" in text
    assert "1.00" in text
    assert "| epoch |" in text


def test_format_table_keeps_each_epoch():
    rows = [
        {
            "model": "deepseek/deepseek-flash",
            "sample": "wire.grid.T2",
            "epoch": str(epoch),
            "social": "none",
            "belief_adoption": "1.00",
        }
        for epoch in (1, 2, 3)
    ]
    text = format_table(rows)
    assert text.count("wire.grid.T2") == 3
    assert "| 1 |" in text
    assert "| 2 |" in text
    assert "| 3 |" in text
