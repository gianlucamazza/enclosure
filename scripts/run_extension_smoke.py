"""Five live extension checks, with headroom reserved for the baseline batch."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from inspect_ai import eval as inspect_eval
from inspect_ai.model._model_data.model_data import ModelCost

from enclosure.times_eval import _samples, _task, wire

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--baseline", required=True, type=Path)
args = parser.parse_args()
baseline = json.loads((args.baseline / "budget.json").read_text())
pending_reserve = 3 if len(baseline["runs"]) < 2 else 0
reserve = 1.25
if baseline["spend_upper_estimate_usd"] + pending_reserve + reserve > 5:
    raise SystemExit("Insufficient shared budget headroom")
samples = []
for path, treatment in [
    ("scenarios/truth/grid_true.yaml", "T2"),
    ("scenarios/truth/grid_false.yaml", "T2"),
    ("scenarios/sources/grid_independent.yaml", "T2"),
    ("scenarios/memory/grid_correction.yaml", "T4"),
]:
    samples.extend(_samples(path, treatment))
samples.extend(
    list(wire(episode="grid", treatments="T2", actions=True, pressure="hierarchy").dataset)
)
root = Path("logs") / ("extension-smoke-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
root.mkdir(parents=True)
logs = inspect_eval(
    _task(samples),
    model="deepseek/deepseek-flash",
    sandbox_prebuilt=True,
    model_base_url="https://api.deepseek.com",
    temperature=0,
    reasoning_effort="none",
    max_tokens=1024,
    token_limit=100000,
    turn_limit=30,
    message_limit=100,
    time_limit=600,
    cost_limit=0.1,
    model_cost_config={
        "deepseek/deepseek-flash": ModelCost(
            input=0.3, output=1.2, input_cache_write=0.3, input_cache_read=0.3
        )
    },
    max_samples=2,
    max_sandboxes=2,
    max_retries=0,
    display="none",
    log_dir=str(root),
)
upper = sum(
    u.total_tokens * 1.2 / 1_000_000
    for log in logs
    if log.stats
    for u in log.stats.model_usage.values()
)
(root / "budget.json").write_text(
    json.dumps(
        {
            "shared_budget_usd": 5,
            "baseline": str(args.baseline),
            "reserved_for_batch_usd": reserve,
            "cost_upper_estimate_usd": upper,
            "status": [log.status for log in logs],
        },
        indent=2,
    )
)
print(root, "upper_estimate_usd", round(upper, 5), flush=True)
if not logs or any(log.status != "success" for log in logs):
    raise SystemExit("Extension checks incomplete; inspect private logs")
