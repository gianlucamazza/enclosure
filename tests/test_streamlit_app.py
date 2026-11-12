"""Log-directory confinement for the experimenter Streamlit view."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def _constrain_log_directory():
    """Load constrain_log_directory without running Streamlit UI side effects."""
    tree = ast.parse(_APP.read_text(encoding="utf-8"))
    kept: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "pathlib":
            kept.append(node)
        elif isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == "LOGS_DIR" for target in node.targets
            ):
                kept.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in {
            "_allowed_log_dirs",
            "constrain_log_directory",
        }:
            kept.append(node)
    module = ast.Module(body=kept, type_ignores=[])
    ast.fix_missing_locations(module)
    namespace: dict[str, object] = {}
    exec(compile(module, str(_APP), "exec"), namespace)
    return namespace["constrain_log_directory"]


constrain_log_directory = _constrain_log_directory()


def test_constrain_log_directory_rejects_traversal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "logs").mkdir()
    outside = tmp_path / "secret"
    outside.mkdir()
    (outside / "leak.eval").write_text("nope", encoding="utf-8")

    with pytest.raises(ValueError, match="must stay inside"):
        constrain_log_directory(str(outside))
    with pytest.raises(ValueError, match="must stay inside"):
        constrain_log_directory("logs/../secret")


def test_constrain_log_directory_accepts_logs_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    campaign = tmp_path / "logs" / "run1"
    campaign.mkdir(parents=True)
    (campaign / "sample.eval").write_text("ok", encoding="utf-8")

    assert constrain_log_directory("logs") == (tmp_path / "logs").resolve()
    assert constrain_log_directory("logs/run1") == campaign.resolve()
    assert constrain_log_directory(str(campaign)) == campaign.resolve()
