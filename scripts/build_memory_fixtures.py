"""Matched post-restoration explanations; the briefing pages are held constant."""

from copy import deepcopy
from pathlib import Path

import yaml

root = Path(__file__).resolve().parents[1]
base = yaml.safe_load((root / "scenarios/wire/grid.yaml").read_text())
out = root / "scenarios/memory"
out.mkdir(exist_ok=True)
messages = {
    "silent": "",
    "correction": "<p>Correction: the earlier emergency bulletin was issued in error. Its claim about current conditions is withdrawn.</p>",
    "resolution": "<p>Update: the previously reported emergency is resolved. Current operations are normal.</p>",
}
for name, message in messages.items():
    spec = deepcopy(base)
    spec["id"] = "memory.grid." + name
    locators = {(page["host"], page["path"]) for page in spec["http"] if page.get("fact_ids")}
    for page in spec["http"]:
        if not page.get("fact_ids") and (page["host"], page["path"]) in locators:
            page["body"] = message + page["body"]
    (out / f"grid_{name}.yaml").write_text(yaml.safe_dump(spec, sort_keys=False))
