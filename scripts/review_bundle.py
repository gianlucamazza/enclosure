"""Build versioned review records; extraction uncertainty is distinct from absence."""

import argparse
import json
from pathlib import Path

from enclosure.review import build_records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--campaign", type=Path, action="append", default=[])
    args = parser.parse_args()
    paths = []
    for source in [args.logs, *args.campaign]:
        paths.extend([source] if source.is_file() else sorted(source.glob("*.eval")))
    records = build_records(paths, Path(__file__).resolve().parents[1])
    with args.output.open("x") as stream:
        json.dump([r.model_dump() for r in records], stream, indent=2, ensure_ascii=False)
    manifest = {
        "schema_version": 2,
        "expected_records": [
            {"record_id": r.record_id, "source_sha256": r.source_sha256} for r in records
        ],
    }
    with args.output.with_suffix(".manifest.json").open("x") as stream:
        json.dump(manifest, stream, indent=2)
    print(
        f"{len(records)} records, {sum(r.extraction_status == 'unresolved' for r in records)} unresolved; no labels assigned"
    )


if __name__ == "__main__":
    main()
