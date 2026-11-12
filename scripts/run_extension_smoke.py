"""Plan extension checks by default; share the cumulative budget with the pilot."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from enclosure.budget import BudgetLedger
from enclosure.campaign import run_campaign
from enclosure.times_eval import _samples, wire


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "logs/budget/shared.json",
    )
    args = parser.parse_args()
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
    root = (
        Path(__file__).resolve().parents[1]
        / "logs"
        / ("extension-smoke-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
    )
    print(
        json.dumps(
            run_campaign(
                {"deepseek-flash": samples},
                ledger=BudgetLedger(args.ledger),
                root=root,
                execute=args.execute,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
