"""Re-score finished logs offline: lexical scorer and LLM judge, against supplied labels (check their review status).

Reads the final belief.txt and report.md from each sample's write_file calls.

    uv run python scripts/judge_logs.py logs/pilot-v2 \
        --judge openrouter/anthropic/claude-opus-4.8 --labels papers/labels/pilot-v2.yaml
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import hashlib
from pathlib import Path

import yaml
from inspect_ai.log import read_eval_log

from enclosure.episode import rubric_from_spec
from enclosure.judge import judge
from enclosure.review import extract_texts, identity
from enclosure.scenario import load_spec
from enclosure.scoring import SCORER_VERSION, Trace, score_trace

ROOT = Path(__file__).resolve().parents[1]
LABEL = {"affirms": 1.0, "uncertain": 0.5, "denies": 0.0, "absent": None}


def final_files(sample) -> dict[str, str]:
    extracted = extract_texts(sample)
    return {
        "belief.txt" if channel == "belief" else "report.md": item["text"]
        for channel, item in extracted.items()
        if item["status"] != "unresolved"
    }


async def rescore(root: str, judge_model: str | None) -> list[dict]:
    rows = []
    for path in sorted(glob.glob(f"{root}/*.eval")):
        log = read_eval_log(path)
        if log.status != "success":
            continue
        for sample in log.samples or []:
            meta = sample.metadata or {}
            snapshot = Path(path).parent / "source-snapshot" / meta["scenario_path"]
            spec = load_spec(
                snapshot if snapshot.is_file() else ROOT / meta["scenario_path"],
                treatment=meta["treatment"],
            )
            files = final_files(sample)
            belief, report = files.get("belief.txt", ""), files.get("report.md", "")
            lexical = score_trace(Trace(belief=belief, report=report), rubric_from_spec(spec))
            row = {
                "sample": str(sample.id),
                "record_ids": {
                    channel: identity(
                        Path(path).parent.name,
                        hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                        str(log.eval.model),
                        str(sample.id),
                        int(sample.epoch or 1),
                        channel,
                    )
                    for channel in ("belief", "memo")
                },
                "diagnostic_version": SCORER_VERSION,
                "extraction": {
                    channel: item["status"] for channel, item in extract_texts(sample).items()
                },
                "belief_lexical": lexical["belief_adoption"],
                "memo_lexical": lexical["task_drift"],
            }
            if "belief.txt" not in files:
                row.pop("belief_lexical")
            if "report.md" not in files:
                row.pop("memo_lexical")
            if judge_model:
                claim = " ".join(fact.party for fact in spec.ontology)
                opposite = " ".join(fact.opposite or fact.ground for fact in spec.ontology)
                for key, text in (("belief", belief), ("memo", report)):
                    verdict = await judge(text, claim, opposite, spec.clock[:10], judge_model)
                    row[f"{key}_judge"] = verdict.level if verdict else None
                    row[f"{key}_quote"] = verdict.quote if verdict else ""
            rows.append(row)
    return rows


def agreement(rows: list[dict], labels: dict, scorer: str) -> str:
    versioned = labels.get("schema_version") == 2
    annotation_index = (
        {
            item["record_id"]: item["label"]
            for item in labels.get("records", [])
            if item.get("review_status") == "reviewed"
        }
        if versioned
        else {}
    )
    if not versioned and len({row["sample"] for row in rows}) != len(rows):
        raise ValueError(
            "Legacy YAML cannot distinguish multiple logs/models/epochs; use versioned annotations"
        )
    hits, total, misses = 0, 0, []
    classes = {label: [0, 0] for label in LABEL}
    for row in rows:
        gold = (
            {
                key: annotation_index.get(row.get("record_ids", {}).get(key))
                for key in ("belief", "memo")
            }
            if versioned
            else labels.get(row["sample"])
        )
        if not gold:
            continue
        for key in ("belief", "memo"):
            if f"{key}_{scorer}" not in row or gold.get(key) not in LABEL:
                continue
            total += 1
            classes[gold[key]][1] += 1
            if row[f"{key}_{scorer}"] == LABEL[gold[key]]:
                hits += 1
                classes[gold[key]][0] += 1
            else:
                misses.append(f"{row['sample']}.{key}: {row[f'{key}_{scorer}']} vs {gold[key]}")
    if not total:
        return f"{scorer}: no labelled rows"
    lines = [f"{scorer}: {hits}/{total} agree"] + [f"  miss {m}" for m in misses]
    lines.extend(f"  {label}: {counts[0]}/{counts[1]} correct" for label, counts in classes.items())
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
