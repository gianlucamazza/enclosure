import json
from pathlib import Path

from enclosure.scenario import apply_scenario, load_spec
from enclosure.times_eval import _samples
from enclosure.world import World

ROOT = Path(__file__).resolve().parents[1]


def test_truth_controls_have_observable_distinguishing_evidence():
    primary = []
    sensors = []
    for truth in [False, True]:
        path = f"scenarios/truth/grid_{str(truth).lower()}.yaml"
        spec = load_spec(ROOT / path)
        assert spec.truth is truth
        assert spec.ontology[0].opposite != spec.ontology[0].party
        world = World()
        apply_scenario(world, spec)
        assert world.get_fact("eea3").ground_truth == spec.ontology[0].ground
        primary.append(
            world.http_get("www.ercot.com", "/gridmktinfo/dashboards/gridconditions").body
        )
        sensor = json.loads(world.http_get("www.reddit.com", "/r/energy/observation.json").body)
        assert sensor["alert_in_effect"] is truth
        sensors.append(sensor)
        assert _samples(path, "T2")[0].metadata["event_truth"] is truth
    assert primary[0] == primary[1]
    assert sensors[0] != sensors[1]
