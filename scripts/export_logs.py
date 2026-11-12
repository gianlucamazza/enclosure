"""Export redacted JSON snapshots. These are review candidates, not Inspect logs."""

import argparse
import hashlib
import json
from pathlib import Path

from inspect_ai.log import read_eval_log

import enclosure.export
from enclosure.export import sanitize

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("logs", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
for path in sorted(args.logs.glob("*.eval")):
    log = read_eval_log(str(path))
    snapshot = sanitize(
        log.model_dump(mode="json"),
        private_paths=(str(Path.cwd()), str(Path.home()), str(Path(__file__).resolve().parents[1])),
    )
    output = {
        "sanitizer_sha256": hashlib.sha256(
            Path(enclosure.export.__file__).read_bytes()
        ).hexdigest(),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "publication_review": "pending",
        "log": snapshot,
    }
    (args.output / (path.stem + ".json")).write_text(json.dumps(output, indent=2))
print("Exported redacted review candidates; inspect before publication.")
