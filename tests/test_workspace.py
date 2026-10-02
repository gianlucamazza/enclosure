from pathlib import Path

from enclosure.hole import memory_hole
from enclosure.scenario import apply_scenario, load_spec
from enclosure.workspace import sync_subject_fs
from enclosure.world import World

SCENARIO = Path(__file__).resolve().parents[1] / "scenarios" / "times" / "python4.yaml"


def test_planted_news_syncs_and_reverts_on_hole(tmp_path):
    world = World()
    apply_scenario(world, load_spec(SCENARIO, treatment="T4"))
    written = sync_subject_fs(world, tmp_path)
    news = tmp_path / "NEWS"
    assert news.exists()
    assert "python:4.0-slim" in news.read_text()
    assert any(path.endswith("NEWS") for path in written)

    memory_hole(world, "py4", mode="world_only")
    sync_subject_fs(world, tmp_path)
    text = news.read_text()
    assert "python:4.0-slim" not in text
    assert "3.14" in text
