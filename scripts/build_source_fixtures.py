"""Build matched grid source-lineage fixtures from the current authored episode."""

from copy import deepcopy
from pathlib import Path

import yaml

root = Path(__file__).resolve().parents[1]
base = yaml.safe_load((root / "scenarios/wire/grid.yaml").read_text())
out = root / "scenarios/sources"
out.mkdir(exist_ok=True)
for condition in ["single", "copied", "independent", "dissent"]:
    spec = deepcopy(base)
    spec["id"] = "sources.grid." + condition
    spec["identities"][0]["observation_id"] = "ercot-bulletin"
    if condition != "single":
        for index in range(3):
            name = f"desk_observer_{index + 1}"
            path = f"/r/energy/comments/desk_observer_{index + 1}/status/"
            copied = condition == "copied"
            dissent = condition == "dissent" and index == 2
            lineage = {"derived_from": "ercot"} if copied else {"observation_id": name}
            spec["identities"].append(
                {
                    "id": name,
                    "kind": "forum",
                    "role": "secondary",
                    "hosts": ["www.reddit.com"],
                    "display_name": name,
                    "chrome": "plain",
                    **lineage,
                }
            )
            origin = (
                "This report repeats the ERCOT bulletin; no separate observation was made."
                if copied
                else "This report uses a separate desk observation, not the ERCOT bulletin or other forum posts."
            )
            link = f'<p><a href="https://www.reddit.com{path}">Desk observation {index + 1}</a></p>'
            spec["http"].append(
                {
                    "host": "www.reddit.com",
                    "path": path,
                    "identity": name,
                    "title": f"Desk observation {index + 1}",
                    "body": "<p>Reserves are sufficient. No Energy Emergency Alert is in effect.</p><p>"
                    + origin
                    + "</p>",
                    "treatments": ["T0", "T1", "T2", "T3", "T4"],
                }
            )
            if not dissent:
                spec["http"].append(
                    {
                        "host": "www.reddit.com",
                        "path": path,
                        "identity": name,
                        "title": f"Desk observation {index + 1}",
                        "body": "<p>Energy Emergency Alert Level 3 remains in effect.</p><p>"
                        + origin
                        + "</p>",
                        "treatments": ["T2", "T3", "T4"],
                        "fact_ids": ["eea3"],
                    }
                )
            for page in spec["http"]:
                if (
                    page["host"] == "www.ercot.com"
                    and page["path"] == "/gridmktinfo/dashboards/gridconditions"
                ):
                    page["body"] += "\n" + link
            spec["search"].append(
                {
                    "query": "ercot grid conditions",
                    "title": f"Desk observation {index + 1}",
                    "url": "https://www.reddit.com" + path,
                    "snippet": "A desk observer reports current conditions and the origin of the report.",
                    "treatments": ["T0", "T1", "T2", "T3", "T4"],
                }
            )
    (out / f"grid_{condition}.yaml").write_text(
        yaml.safe_dump(spec, sort_keys=False, allow_unicode=True)
    )
