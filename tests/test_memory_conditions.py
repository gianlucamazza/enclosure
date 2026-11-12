from pathlib import Path

from enclosure.hole import memory_hole
from enclosure.scenario import apply_scenario, load_spec
from enclosure.world import World

ROOT = Path(__file__).resolve().parents[1]


def test_briefings_match_and_retractions_differ():
    before = []
    after = {}
    for name in ["silent", "correction", "resolution"]:
        world = World()
        spec = load_spec(ROOT / f"scenarios/memory/grid_{name}.yaml", treatment="T4")
        apply_scenario(world, spec)
        path = "/gridmktinfo/dashboards/gridconditions"
        before.append(world.http_get("www.ercot.com", path).body)
        memory_hole(world, "eea3")
        after[name] = world.http_get("www.ercot.com", path).body
    assert len(set(before)) == 1
    assert "Correction:" in after["correction"]
    assert "Update:" in after["resolution"]
    assert "Correction:" not in after["silent"]
