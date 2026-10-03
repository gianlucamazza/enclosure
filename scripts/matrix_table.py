"""Read Inspect logs and print treatment × model × metric."""

from __future__ import annotations

import math
import sys
from pathlib import Path

from inspect_ai.log import read_eval_log

METRICS = (
    "belief_stated",
    "belief_adoption",
    "task_drift",
    "verification_seeking",
    "hole_notice",
    "task_completion",
    "oob_probe",
)


def rows_from_log(path: Path) -> list[dict[str, str]]:
    log = read_eval_log(str(path))
    model = getattr(log.eval, "model", "") or ""
    rows = []
    for sample in log.samples or []:
        scores = sample.scores or {}
        value = next(iter(scores.values())).value if scores else {}
        if not isinstance(value, dict):
            value = {}
        meta = sample.metadata or {}
        row = {
            "model": model,
            "sample": str(sample.id),
            "social": str(meta.get("social", "")),
            "status": log.status or "",
        }
        for metric in METRICS:
            cell = value.get(metric, "")
            unstated = metric == "belief_adoption" and value.get("belief_stated") in (0, 0.0)
            unfiled = metric == "task_drift" and value.get("report_filed") in (0, 0.0)
            missing = cell is None or cell == ""
            if isinstance(cell, float) and math.isnan(cell):
                missing = True
            if missing or unstated or unfiled:
                row[metric] = "—"
            else:
                row[metric] = f"{float(cell):.2f}"
        rows.append(row)
    return rows


def format_table(rows: list[dict[str, str]]) -> str:
    columns = ("model", "sample", "social", *METRICS)
    if not rows:
        return "no samples"
    header = "| " + " | ".join(columns) + " |"
    rule = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| " + " | ".join(row.get(column, "") for column in columns) + " |"
        for row in rows
    ]
    return "\n".join([header, rule, *body])


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else "logs/matrix")
    logs = sorted(root.glob("*.eval"))
    rows: list[dict[str, str]] = []
    for path in logs:
        rows.extend(rows_from_log(path))
    print(format_table(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
