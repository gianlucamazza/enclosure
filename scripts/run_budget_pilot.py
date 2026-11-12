"""Plan the pilot by default; --execute uses the shared cumulative $5 ledger."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from enclosure.budget import BudgetLedger
from enclosure.campaign import run_campaign
from enclosure.times_eval import wire


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "logs/budget/shared.json",
    )
    args = parser.parse_args()
    ledger = BudgetLedger(args.ledger)
    samples = {
        model: list(wire(episode="grid", treatments="T0,T2,T4,T5").dataset)
        for model in ["deepseek-flash", "deepseek-v4-pro"]
    }
    root = (
        Path(__file__).resolve().parents[1]
        / "logs"
        / ("vm-budget-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
    )
    print(
        json.dumps(run_campaign(samples, ledger=ledger, root=root, execute=args.execute), indent=2)
    )


if __name__ == "__main__":
    main()
