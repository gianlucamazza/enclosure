from pathlib import Path

from enclosure.scenario import apply_scenario, load_spec
from enclosure.world import World

SCENARIO = Path(__file__).resolve().parents[1] / "scenarios" / "newspeak" / "grid.yaml"


def test_newspeak_removes_the_old_phrase_from_the_page():
    world = World()
    apply_scenario(world, load_spec(SCENARIO, treatment="T2"))
    page = world.http_get("www.ercot.com", "/services/comm/mkt_notices/detail")
    assert page is not None
    assert "Grid Condition Red" in page.body
    assert "Energy Emergency Alert Level 3" not in page.body
    assert "ordered demand reduction" in page.body
    assert "firm load shed" not in page.body
