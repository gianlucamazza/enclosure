from pathlib import Path

from enclosure.research import independent_origins
from enclosure.scenario import apply_scenario, load_spec
from enclosure.world import World

ROOT = Path(__file__).resolve().parents[1]


def test_source_conditions_expose_lineage_and_independent_dissent():
    for condition, expected in [("single", 1), ("copied", 1), ("independent", 4), ("dissent", 4)]:
        spec = load_spec(ROOT / f"scenarios/sources/grid_{condition}.yaml", treatment="T2")
        world = World()
        apply_scenario(world, spec)
        observers = {i.id for i in spec.identities if i.id.startswith("desk_observer")} | {"ercot"}
        assert len(independent_origins(spec.identities, observers)) == expected
        pages = [
            d for d in world.live_docs("http") if (d.identity_id or "").startswith("desk_observer")
        ]
        assert len(pages) == (0 if condition == "single" else 3)
        if condition == "copied":
            assert all("no separate observation" in p.body for p in pages)
        if condition == "dissent":
            assert sum("No Energy Emergency Alert is in effect" in p.body for p in pages) == 1
