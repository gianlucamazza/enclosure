from decimal import Decimal
from types import SimpleNamespace as NS

import pytest

from enclosure.budget import BudgetLedger
from enclosure.campaign import PROFILES, Prices, run_campaign
from enclosure.times_eval import _samples


def test_cache_is_included_and_reservation_covers_response_overshoot():
    profile = Prices("x", ".3", "1.2")
    assert profile.usage_cost(NS(total_tokens=24211, output_tokens=1445)) == Decimal(".0085638")
    assert profile.reservation() == Decimal(".59")
    assert PROFILES["deepseek-v4-pro"].reservation() == Decimal("1.71")


def test_dry_run_never_evaluates_and_cancellation_holds_budget(tmp_path, monkeypatch):
    from datetime import UTC, datetime

    monkeypatch.setitem(
        PROFILES,
        "deepseek-flash",
        Prices("deepseek-flash", ".3", "1.2", verified_on=datetime.now(UTC).date().isoformat()),
    )
    samples = _samples("scenarios/wire/grid.yaml", "T0")
    ledger = BudgetLedger(tmp_path / "ledger.json")

    def cancelled(*args, **kwargs):
        assert args[0].dataset[0].metadata["probe_policy"] == "disabled"
        return []

    result = run_campaign(
        {"deepseek-flash": samples},
        ledger=ledger,
        root=tmp_path / "dry",
        evaluate=lambda *a, **kw: pytest.fail("dry run made a call"),
    )
    assert result["mode"] == "dry-run" and not (tmp_path / "dry").exists()
    with pytest.raises(RuntimeError):
        run_campaign(
            {"deepseek-flash": samples},
            ledger=ledger,
            root=tmp_path / "paid",
            execute=True,
            evaluate=cancelled,
        )
    reservation = next(iter(ledger.snapshot()["reservations"].values()))
    assert reservation["status"] == "unknown"
    assert ledger.snapshot()["opening_usd"] == "1.27642592"
