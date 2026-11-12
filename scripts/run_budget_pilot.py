"""Revised small VM pilot with a $5 ceiling and conservative peak-price accounting.

Two samples run concurrently, under per-sample cost/token limits. The first
feasibility campaign and auth checks are covered by a $0.50 prior-spend reserve.
Reserve $3 before each four-sample batch for in-flight requests and overshoot.
No judge calls, and no raw log is automatically published.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from inspect_ai import eval as inspect_eval
from inspect_ai.model._model_data.model_data import ModelCost

from enclosure.times_eval import wire

root = Path("logs") / ("vm-budget-v2-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
root.mkdir(parents=True)
ledger = {
    "budget_usd": 5.0,
    "price_source": "https://api-docs.deepseek.com/quick_start/pricing/",
    "spend_upper_estimate_usd": 0.50,
    "prior_campaign_and_auth_reserve_usd": 0.50,
    "runs": [],
}
if not os.environ.get("DEEPSEEK_API_KEY"):
    raise SystemExit("DEEPSEEK_API_KEY is required")
for model, input_rate, output_rate in [
    ("deepseek-flash", 0.30, 1.20),
    ("deepseek-v4-pro", 1.32, 3.96),
]:
    if ledger["spend_upper_estimate_usd"] + 3 > ledger["budget_usd"]:
        raise SystemExit("Insufficient remaining budget for a four-sample batch")
    logs = inspect_eval(
        wire(episode="grid", treatments="T0,T2,T4,T5", backend="vm"),
        model="deepseek/" + model,
        sandbox_prebuilt=True,
        cost_limit=0.25,
        model_cost_config={
            "deepseek/" + model: ModelCost(
                input=input_rate,
                output=output_rate,
                input_cache_write=input_rate,
                input_cache_read=input_rate,
            )
        },
        model_base_url="https://api.deepseek.com",
        temperature=0,
        reasoning_effort="none",
        max_tokens=1024,
        token_limit=100000,
        turn_limit=30,
        message_limit=100,
        time_limit=600,
        max_retries=0,
        max_samples=2,
        max_sandboxes=2,
        log_dir=str(root),
        display="none",
    )
    if not logs:
        raise SystemExit("Evaluation cancelled; no further calls scheduled")
    cost = 0.0
    for log in logs:
        if log.stats:
            cost += sum(
                u.total_tokens * max(input_rate, output_rate) / 1_000_000
                for u in log.stats.model_usage.values()
            )
        ledger["runs"].append(
            {
                "model": model,
                "treatments": ["T0", "T2", "T4", "T5"],
                "status": log.status,
                "cost_upper_estimate_usd": cost,
                "completed_samples": log.results.completed_samples if log.results else 0,
            }
        )
    ledger["spend_upper_estimate_usd"] += cost
    (root / "budget.json").write_text(json.dumps(ledger, indent=2))
    print(
        model,
        "status=" + ",".join(str(log.status) for log in logs),
        "estimated_usd=" + str(round(cost, 5)),
        flush=True,
    )
    if any(log.status != "success" for log in logs):
        raise SystemExit("Pilot stopped after unsuccessful batch; inspect private logs")
print(root, flush=True)
