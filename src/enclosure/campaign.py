"""Sequential paid-run entrypoint with durable shared reservations and no implicit probes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_UP, Decimal
from pathlib import Path

from enclosure.budget import BudgetLedger


@dataclass(frozen=True)
class Prices:
    model: str
    input: str
    output: str
    verified_on: str = "2026-11-12"
    context_upper: int = 1_100_000
    max_output: int = 1024
    sample_cost_limit: str = "0.25"

    def reservation(self) -> Decimal:
        # Cost-limit enforcement follows a response: reserve one worst-case overshoot.
        return (
            Decimal(self.sample_cost_limit)
            + (Decimal(self.input) * self.context_upper + Decimal(self.output) * self.max_output)
            / 1_000_000
        ).quantize(Decimal(".01"), rounding=ROUND_UP)

    def usage_cost(self, usage) -> Decimal:
        if usage.total_tokens < usage.output_tokens or usage.output_tokens < 0:
            raise ValueError("Malformed usage counters")
        # Inspect total_tokens includes cached inputs; the peak uncached price is an upper bound.
        return (
            Decimal(usage.total_tokens - usage.output_tokens) * Decimal(self.input)
            + Decimal(usage.output_tokens) * Decimal(self.output)
        ) / 1_000_000


PROFILES = {
    "deepseek-flash": Prices("deepseek-flash", ".30", "1.20"),
    "deepseek-v4-pro": Prices("deepseek-v4-pro", "1.32", "3.96"),
}


def run_campaign(
    samples_by_model: dict,
    *,
    ledger: BudgetLedger,
    root: Path,
    execute: bool = False,
    evaluate=None,
) -> dict:
    planned = {model: len(samples) for model, samples in samples_by_model.items()}
    if not execute:
        return {"mode": "dry-run", "samples": planned, "ledger": ledger.snapshot()}
    from inspect_ai import eval as inspect_eval
    from inspect_ai.model._model_data.model_data import ModelCost

    from enclosure.times_eval import _task

    today = datetime.now(UTC).date().isoformat()
    if any(PROFILES[model].verified_on != today for model in planned):
        raise ValueError(
            "Refresh and verify the official price profile before executing paid calls"
        )
    root.mkdir(parents=True, exist_ok=False)
    results = []
    for model, samples in samples_by_model.items():
        profile = PROFILES[model]
        for index, sample in enumerate(samples):
            key = f"{root.name}:{model}:{index}"
            ledger.reserve(
                key,
                profile.reservation(),
                description=f"{model} sample {index}; prices https://api-docs.deepseek.com/quick_start/pricing/",
            )
            try:
                sample.metadata = sample.metadata or {}
                sample.metadata["probe_policy"] = "disabled"
                sample.metadata["budget_reservation"] = key
                logs = (evaluate or inspect_eval)(
                    _task([sample]),
                    model="deepseek/" + model,
                    sandbox_prebuilt=True,
                    model_base_url="https://api.deepseek.com",
                    temperature=0,
                    reasoning_effort="none",
                    max_tokens=profile.max_output,
                    token_limit=100000,
                    turn_limit=30,
                    message_limit=100,
                    time_limit=600,
                    cost_limit=float(profile.sample_cost_limit),
                    model_cost_config={
                        "deepseek/" + model: ModelCost(
                            input=float(profile.input),
                            output=float(profile.output),
                            input_cache_write=float(profile.input),
                            input_cache_read=float(profile.input),
                        )
                    },
                    max_samples=1,
                    max_sandboxes=1,
                    max_retries=0,
                    retry_on_error=0,
                    log_dir=str(root),
                    display="none",
                )
                complete = bool(logs) and all(
                    log.status == "success"
                    and all(
                        not s.error and not (s.limit and s.limit.type == "time")
                        for s in log.samples or []
                    )
                    for log in logs
                )
                if not complete:
                    ledger.reconcile(key)
                    raise RuntimeError(
                        "Cancelled/incomplete usage: reservation held; no more calls scheduled"
                    )
                cost = sum(
                    (
                        profile.usage_cost(usage)
                        for log in logs
                        if log.stats
                        for usage in log.stats.model_usage.values()
                    ),
                    Decimal(0),
                )
            except BaseException:
                current = ledger.snapshot()["reservations"][key]
                if current["status"] == "pending":
                    ledger.reconcile(key)
                (root / "budget.json").write_text(json.dumps(ledger.snapshot(), indent=2))
                raise
            ledger.reconcile(key, cost)
            results.append(
                {
                    "reservation": key,
                    "model": model,
                    "sample": str(sample.id),
                    "cost_upper_usd": str(cost),
                }
            )
            (root / "budget.json").write_text(json.dumps(ledger.snapshot(), indent=2))
    return {"mode": "executed", "runs": results, "ledger": ledger.snapshot()}
