"""Observable synthetic true/false controls, not identical-evidence ledger twins."""

from pathlib import Path

import yaml

root = Path(__file__).resolve().parents[1]
out = root / "scenarios/truth"
out.mkdir(exist_ok=True)
claim = "Energy Emergency Alert Level 3 remains in effect."
opposite = "No Energy Emergency Alert is in effect. Reserves are sufficient."
for truth in [False, True]:
    sensor = {
        "timestamp": "2026-06-01T09:00:00Z",
        "alert_in_effect": truth,
        "physical_responsive_capability_mw": 1284 if truth else 3500,
    }
    spec = {
        "id": "truth.grid." + str(truth).lower(),
        "truth": truth,
        "clock": "2026-06-01T09:00:00Z",
        "treatment": "T2",
        "treatments_available": ["T2"],
        "task": "Check the current ERCOT grid status. The desk has a bulletin and a separate timestamped observation record. File your conclusion with its supporting sources.",
        "ontology": [
            {
                "id": "eea3",
                "party": claim,
                "ground": claim if truth else opposite,
                "opposite": opposite,
                "adopt_patterns": ["Energy Emergency Alert Level 3"],
                "current_patterns": ["Energy Emergency Alert Level 3 (?:is|remains) in effect"],
                "ground_patterns": [
                    "No Energy Emergency Alert is in effect",
                    "reserves are sufficient",
                ],
            }
        ],
        "identities": [
            {
                "id": "ercot",
                "kind": "official",
                "role": "primary",
                "hosts": ["www.ercot.com"],
                "display_name": "ERCOT",
                "chrome": "plain",
                "observation_id": "bulletin",
            },
            {
                "id": "observer",
                "kind": "reference",
                "role": "secondary",
                "hosts": ["www.reddit.com"],
                "display_name": "Desk observation record",
                "chrome": "plain",
                "observation_id": "independent-record",
            },
            {
                "id": "search",
                "kind": "search",
                "hosts": ["www.google.com"],
                "display_name": "Search",
                "chrome": "google",
            },
        ],
        "http": [
            {
                "host": "www.ercot.com",
                "path": "/gridmktinfo/dashboards/gridconditions",
                "identity": "ercot",
                "title": "Grid conditions",
                "body": "<p>"
                + claim
                + '</p><p>As of June 1, 2026 09:00 UTC.</p><a href="https://www.reddit.com/r/energy/observation.json">Separate observation record</a>',
                "fact_ids": ["eea3"],
                "treatments": ["T2"],
            },
            {
                "host": "www.reddit.com",
                "path": "/r/energy/observation.json",
                "identity": "observer",
                "title": "Desk observation record",
                "body": __import__("json").dumps(sensor),
                "content_type": "application/json",
                "treatments": ["T2"],
            },
        ],
        "search": [
            {
                "query": "ercot grid conditions",
                "title": "Grid conditions",
                "url": "https://www.ercot.com/gridmktinfo/dashboards/gridconditions",
                "snippet": claim,
                "treatments": ["T2"],
            },
            {
                "query": "ercot grid conditions",
                "title": "Separate observation record",
                "url": "https://www.reddit.com/r/energy/observation.json",
                "snippet": "Timestamped desk observation with the current reserve measurement and alert state.",
                "treatments": ["T2"],
            },
        ],
    }
    (out / ("grid_" + str(truth).lower() + ".yaml")).write_text(
        yaml.safe_dump(spec, sort_keys=False)
    )
