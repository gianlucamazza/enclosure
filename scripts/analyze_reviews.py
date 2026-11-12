"""Join source records with immutable annotation identities and emit descriptive results."""

import argparse
import json
from pathlib import Path

from enclosure.analysis import report
from enclosure.review import apply_annotations, load_records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--annotations", type=Path)
    args = parser.parse_args()
    records = load_records(args.bundle)
    if args.annotations:
        records = apply_annotations(
            records, json.loads(args.annotations.read_text()), complete=True
        )
    with args.output.open("x") as stream:
        json.dump(report(records), stream, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
