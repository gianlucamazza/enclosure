"""Validate a human review bundle; never fabricate reviewer decisions."""

import argparse
import json
from datetime import date
from pathlib import Path

import yaml

LABELS = {"affirms", "denies", "uncertain", "absent"}
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("review", type=Path)
parser.add_argument(
    "--labels-output", type=Path, help="Write a new YAML label file after successful validation"
)
args = parser.parse_args()
rows = json.loads(args.review.read_text())
seen = set()
errors = []
for row in rows:
    key = (row.get("log"), row.get("sample"), row.get("channel"))
    if key in seen:
        errors.append(f"duplicate {key}")
    seen.add(key)
    if row.get("label") not in LABELS or not row.get("reviewer") or not row.get("rationale"):
        errors.append(f"incomplete {key}")
    try:
        date.fromisoformat(row.get("date") or "")
    except ValueError:
        errors.append(f"invalid date {key}")
if not rows:
    errors.append("empty review")
if errors:
    print("\n".join(errors))
    raise SystemExit(1)
print(
    f"{len(rows)} reviewed records with label, reviewer, date and rationale. Reviewer identity is self-reported."
)

if args.labels_output:
    labels = {}
    for row in rows:
        if row["channel"] not in {"belief", "memo"}:
            raise SystemExit("Only belief and memo channels can be converted")
        channels = labels.setdefault(row["sample"], {})
        if row["channel"] in channels:
            raise SystemExit("Multiple logs/epochs share a sample key; export separate review sets")
        channels[row["channel"]] = row["label"]
    if any(set(channels) != {"belief", "memo"} for channels in labels.values()):
        raise SystemExit("Need both channels for each sample")
    with args.labels_output.open("x") as stream:
        yaml.safe_dump(labels, stream, sort_keys=False)
    print(f"Wrote separate reviewed-label file: {args.labels_output}")
