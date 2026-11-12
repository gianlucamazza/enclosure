"""Export final texts for human review without changing original labels."""

import argparse
import hashlib
import json
from pathlib import Path

from inspect_ai.log import read_eval_log
from judge_logs import final_files

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("logs", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
rows = []
for path in sorted(args.logs.glob("*.eval")):
    log = read_eval_log(str(path))
    for sample in log.samples or []:
        files = final_files(sample)
        for channel, filename in [("belief", "belief.txt"), ("memo", "report.md")]:
            rows.append(
                {
                    "log": path.name,
                    "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "sample": str(sample.id),
                    "channel": channel,
                    "text": files.get(filename, ""),
                    "label": None,
                    "reviewer": None,
                    "date": None,
                    "rationale": None,
                }
            )
with args.output.open("x") as stream:
    json.dump(rows, stream, indent=2, ensure_ascii=False)
print(f"{len(rows)} review records; no labels assigned")
