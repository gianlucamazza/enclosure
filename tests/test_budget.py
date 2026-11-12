from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest

from enclosure.budget import BudgetExceeded, BudgetLedger


def test_resume_unknown_and_no_reset(tmp_path):
    path = tmp_path / "ledger.json"
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}")
    with pytest.raises(ValueError):
        BudgetLedger(invalid)
    ledger = BudgetLedger(path, ceiling="5", opening="1")
    ledger.reserve("first", "3")
    ledger.reconcile("first")
    assert BudgetLedger(path, ceiling="5", opening="1").snapshot()["available_usd"] == "1"
    with pytest.raises(BudgetExceeded):
        ledger.reserve("next", "2")
    with pytest.raises(ValueError):
        BudgetLedger(path, ceiling="5", opening="0")
    ledger.reconcile("first", "0.50")
    assert Decimal(ledger.snapshot()["available_usd"]) == Decimal("3.50")
    with pytest.raises(ValueError):
        ledger.reserve("first", "1")


def test_concurrent_reservations_and_overrun_are_durable(tmp_path):
    path = tmp_path / "ledger.json"
    ledger = BudgetLedger(path, ceiling="5", opening="0")

    def reserve(index):
        try:
            BudgetLedger(path, ceiling="5", opening="0").reserve(str(index), "3")
            return True
        except BudgetExceeded:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(reserve, range(2))) == 1
    key = next(iter(ledger.snapshot()["reservations"]))
    with pytest.raises(BudgetExceeded):
        ledger.reconcile(key, "4")
    assert ledger.snapshot()["reservations"][key]["actual_usd"] == "4"
    with pytest.raises(BudgetExceeded):
        ledger.reserve("after", "0.1")
