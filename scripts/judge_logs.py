"""Re-score finished logs offline: lexical scorer and LLM judge, against hand labels.

Reads the final belief.txt and report.md from each sample's write_file calls.

    uv run python scripts/judge_logs.py logs/pilot-v2 \
        --judge openrouter/anthropic/claude-opus-4.8 --labels papers/labels/pilot-v2.yaml
"""

from __future__ import annotations

import argparse
import asyncio
import glob
from pathlib import Path

import yaml
from inspect_ai.log import read_eval_log

from enclosure.episode import rubric_from_spec
from enclosure.judge import judge
from enclosure.scenario import load_spec
from enclosure.scoring import Trace, score_trace

ROOT = Path(__file__).resolve().parents[1]
LABEL = {"affirms": 1.0, "uncertain": 0.5, "denies": 0.0, "absent": None}


def final_files(sample) -> dict[str, str]:
    files: dict[str, str] = {}
    for message in sample.messages:
        for call in getattr(message, "tool_calls", None) or []:
            if call.function == "write_file":
                files[Path(call.arguments.get("path", "")).name] = call.arguments.get("content", "")
    return files


async def rescore(root: str, judge_model: str | None) -> list[dict]:
    rows = []
    for path in sorted(glob.glob(f"{root}/*.eval")):
        log = read_eval_log(path)
        if log.status != "success":
            continue
        for sample in log.samples or []:
            meta = sample.metadata or {}
            spec = load_spec(ROOT / meta["scenario_path"], treatment=meta["treatment"])
            files = final_files(sample)
            belief, report = files.get("belief.txt", ""), files.get("report.md", "")
            lexical = score_trace(Trace(belief=belief, report=report), rubric_from_spec(spec))
            row = {
                "sample": str(sample.id),
                "belief_lexical": lexical["belief_adoption"],
                "memo_lexical": lexical["task_drift"],
            }
            if judge_model:
                claim = " ".join(fact.party for fact in spec.ontology)
                opposite = " ".join(fact.ground for fact in spec.ontology)
                for key, text in (("belief", belief), ("memo", report)):
                    verdict = await judge(text, claim, opposite, spec.clock[:10], judge_model)
                    row[f"{key}_judge"] = verdict.level if verdict else None
                    row[f"{key}_quote"] = verdict.quote if verdict else ""
            rows.append(row)
    return rows


def agreement(rows: list[dict], labels: dict, scorer: str) -> str:
    hits, total, misses = 0, 0, []
    for row in rows:
        gold = labels.get(row["sample"])
        if not gold:
            continue
        for key in ("belief", "memo"):
            if f"{key}_{scorer}" not in row:
                continue
            total += 1
            if row[f"{key}_{scorer}"] == LABEL[gold[key]]:
                hits += 1
            else:
                misses.append(f"{row['sample']}.{key}: {row[f'{key}_{scorer}']} vs {gold[key]}")
    if not total:
        return f"{scorer}: no labelled rows"
    lines = [f"{scorer}: {hits}/{total} agree"] + [f"  miss {m}" for m in misses]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("--judge", default=None)
    parser.add_argument("--labels", default=None)
    args = parser.parse_args()
    rows = asyncio.run(rescore(args.root, args.judge))
    for row in rows:
        print(row)
    if args.labels:
        labels = yaml.safe_load(Path(args.labels).read_text())
        print(agreement(rows, labels, "lexical"))
        if args.judge:
            print(agreement(rows, labels, "judge"))


if __name__ == "__main__":
    main()
