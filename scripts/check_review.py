"""Validate review coverage and authorship; no AI annotation is certified as human."""

import argparse
import json
from pathlib import Path

import yaml

from enclosure.review import apply_annotations, load_records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review", type=Path)
    parser.add_argument("--source-bundle", type=Path)
    parser.add_argument("--expected-manifest", type=Path)
    parser.add_argument("--require-human", action="store_true")
    parser.add_argument("--labels-output", type=Path)
    args = parser.parse_args()
    if args.source_bundle:
        records = apply_annotations(
            load_records(args.source_bundle), json.loads(args.review.read_text()), complete=True
        )
    else:
        data = json.loads(args.review.read_text())
        if data and isinstance(data, list) and "schema_version" not in data[0]:
            raise SystemExit(
                "Legacy bundle: migrate by rebuilding from source logs; authorship and coverage are unspecified"
            )
        records = load_records(args.review)
    if not records or any(r.review_status != "reviewed" for r in records):
        raise SystemExit("Review incomplete")
    if args.expected_manifest:
        expected = {
            r["record_id"]: r["source_sha256"]
            for r in json.loads(args.expected_manifest.read_text())["expected_records"]
        }
        if expected != {r.record_id: r.source_sha256 for r in records}:
            raise SystemExit("Review differs from expected coverage")
    if args.require_human and any(r.reviewer_type != "human" for r in records):
        raise SystemExit("AI/unspecified annotation is not human validation")
    if args.labels_output:
        labels = {}
        for r in records:
            channels = labels.setdefault(r.sample, {})
            if r.channel in channels:
                raise SystemExit(
                    "Legacy YAML would collide across model/log/epoch; use the versioned record sidecar"
                )
            channels[r.channel] = r.label
        if any(set(row) != {"belief", "memo"} for row in labels.values()):
            raise SystemExit("Both channels required")
        with args.labels_output.open("x") as stream:
            yaml.safe_dump(labels, stream, sort_keys=False)
    print(
        f"{len(records)} reviewed records; human={sum(r.reviewer_type == 'human' for r in records)}, AI={sum(r.reviewer_type == 'ai' for r in records)}"
    )


if __name__ == "__main__":
    main()
