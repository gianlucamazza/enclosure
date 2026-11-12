"""Versioned review records and conservative extraction of the texts actually scored."""

from __future__ import annotations

import hashlib
import json
import posixpath
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, model_validator

Label = Literal["affirms", "denies", "uncertain", "absent"]


class ReviewRecord(BaseModel):
    schema_version: Literal[2] = 2
    record_id: str
    campaign: str
    log: str
    source_sha256: str
    model: str
    sample: str
    epoch: int
    channel: Literal["belief", "memo"]
    text: str | None
    extraction_status: Literal["ready", "absent", "unresolved"]
    extraction_source: str
    claim: str = ""
    desk_date: str = ""
    limit: str | None = None
    elicited: bool = False
    event_truth: bool | None = None
    diagnostic_score: float | None = None
    diagnostic_version: str = "stored_legacy_unspecified"
    review_status: Literal["pending", "reviewed", "unresolved"] = "pending"
    label: Label | None = None
    reviewer: str | None = None
    reviewer_type: Literal["human", "ai", "unspecified"] = "unspecified"
    date: str | None = None
    rationale: str | None = None
    evidence_quote: str = ""

    @model_validator(mode="after")
    def validate_review(self):
        from datetime import date

        expected = identity(
            self.campaign, self.source_sha256, self.model, self.sample, self.epoch, self.channel
        )
        if self.record_id != expected:
            raise ValueError("Review identity does not match its source")
        if self.extraction_status == "ready" and not (self.text or "").strip():
            raise ValueError("Ready extraction needs text")
        if self.extraction_status == "absent" and self.text != "":
            raise ValueError("Confirmed absence must be represented by empty text")
        if self.review_status == "reviewed":
            if self.reviewer_type == "unspecified":
                raise ValueError("Reviewed records must identify human or AI authorship")
            if self.extraction_status == "unresolved":
                raise ValueError("Resolve extraction before labelling")
            if self.label is None or any(
                not (v or "").strip() for v in (self.reviewer, self.date, self.rationale)
            ):
                raise ValueError("Reviewed records need label, reviewer, date and rationale")
            date.fromisoformat(self.date or "")
            if self.label != "absent" and (
                not self.evidence_quote or self.evidence_quote not in (self.text or "")
            ):
                raise ValueError("Reviewed non-absent statements require a verbatim evidence quote")
            if self.extraction_status == "absent" and self.label != "absent":
                raise ValueError("Missing output is absent, not a denial")
        return self


def identity(campaign: str, digest: str, model: str, sample: str, epoch: int, channel: str) -> str:
    return hashlib.sha256(
        json.dumps([campaign, digest, model, sample, epoch, channel], ensure_ascii=False).encode()
    ).hexdigest()


def extract_texts(sample) -> dict[str, dict]:
    """Prefer explicit harness snapshots. Old opaque writes are never guessed."""
    scores = list((sample.scores or {}).values())
    for score in scores:
        snapshots = (score.metadata or {}).get("final_texts")
        if snapshots and all(channel in snapshots for channel in ("belief", "memo")):
            return {
                channel: {
                    "text": snapshots[channel]["text"],
                    "status": "ready" if snapshots[channel]["text"].strip() else "absent",
                    "source": snapshots[channel]["source"],
                }
                for channel in ("belief", "memo")
            }
    results = {m.tool_call_id: m for m in sample.messages if getattr(m, "role", "") == "tool"}
    texts: dict[str, str] = {}
    opaque: set[str] = set()
    paths = {"/home/agent/belief.txt": "belief", "/home/agent/report.md": "memo"}
    for message in sample.messages:
        for call in getattr(message, "tool_calls", None) or []:
            result = results.get(call.id)
            if result is None or getattr(result, "error", None):
                continue
            function = call.function.rsplit("/", 1)[-1]
            if function in {"shell", "python"}:
                opaque.update(paths.values())
            if function != "write_file":
                continue
            path = str(call.arguments.get("path", ""))
            path = posixpath.normpath(path if path.startswith("/") else "/home/agent/" + path)
            if path in paths and str(getattr(result, "text", "")).startswith("wrote "):
                channel = paths[path]
                texts[channel] = str(call.arguments.get("content", ""))
                opaque.discard(channel)
    extracted: dict[str, dict[str, Any]] = {}
    for channel in paths.values():
        if channel in texts and channel not in opaque:
            text = texts[channel]
            extracted[channel] = {
                "text": text,
                "status": "ready" if text.strip() else "absent",
                "source": "successful canonical write_file",
            }
        else:
            extracted[channel] = {
                "text": None,
                "status": "unresolved",
                "source": "legacy log lacks an authoritative final snapshot",
            }
    # Explicit harness flags describe the final artifacts, including deletions.
    for channel, flag in (("belief", "belief_stated"), ("memo", "report_filed")):
        if scores and isinstance(scores[0].value, dict) and scores[0].value.get(flag) == 0:
            extracted[channel] = {"text": "", "status": "absent", "source": f"harness {flag}=0"}
    return extracted


def build_records(paths: list[Path], root: Path) -> list[ReviewRecord]:
    from inspect_ai.log import read_eval_log

    from enclosure.scenario import load_spec

    records = []
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        log = read_eval_log(str(path))
        for sample in log.samples or []:
            meta = sample.metadata or {}
            scenario = meta.get("scenario_path")
            context = path.parent / "source-snapshot" / scenario if scenario else None
            if scenario and (context is None or not context.is_file()):
                context = root / scenario
            spec = (
                load_spec(context, treatment=meta.get("treatment"))
                if context and context.is_file()
                else None
            )
            for channel, extraction in extract_texts(sample).items():
                campaign, model, sample_id, epoch = (
                    path.parent.name,
                    str(log.eval.model),
                    str(sample.id),
                    int(sample.epoch or 1),
                )
                records.append(
                    ReviewRecord(
                        record_id=identity(campaign, digest, model, sample_id, epoch, channel),
                        campaign=campaign,
                        log=path.name,
                        source_sha256=digest,
                        model=model,
                        sample=sample_id,
                        epoch=epoch,
                        channel=cast(Literal["belief", "memo"], channel),
                        text=extraction["text"],
                        extraction_status=extraction["status"],
                        extraction_source=extraction["source"],
                        claim=" ".join(f.party for f in spec.ontology) if spec else "",
                        desk_date=spec.clock[:10] if spec else "",
                        limit=sample.limit.type if sample.limit else None,
                        event_truth=meta.get("event_truth", spec.truth if spec else None),
                        diagnostic_score=_numeric_diagnostic(sample, channel),
                        diagnostic_version=(next(iter(sample.scores.values())).metadata or {}).get(
                            "diagnostic_scorer_version", "stored_legacy_unspecified"
                        )
                        if sample.scores
                        else "unavailable",
                        elicited=bool(
                            any(
                                isinstance(s.value, dict) and s.value.get("belief_elicited")
                                for s in (sample.scores or {}).values()
                            )
                        ),
                    )
                )
    if len({r.record_id for r in records}) != len(records):
        raise ValueError("Duplicate review identities")
    return records


def load_records(path: Path) -> list[ReviewRecord]:
    rows = [ReviewRecord.model_validate(r) for r in json.loads(path.read_text())]
    if len({r.record_id for r in rows}) != len(rows):
        raise ValueError("Duplicate review identities")
    return rows


ANNOTATION_FIELDS = {
    "review_status",
    "reviewer",
    "reviewer_type",
    "label",
    "date",
    "rationale",
    "evidence_quote",
}
SOURCE_FIELDS = {
    "record_id",
    "campaign",
    "log",
    "source_sha256",
    "model",
    "sample",
    "epoch",
    "channel",
}


def annotation_sidecar(records: list[ReviewRecord]) -> dict:
    return {
        "schema_version": 2,
        "human_validated": bool(records)
        and all(r.review_status == "reviewed" and r.reviewer_type == "human" for r in records),
        "synthetic_benchmark": True,
        "records": [
            {
                key: value
                for key, value in r.model_dump().items()
                if key in SOURCE_FIELDS | ANNOTATION_FIELDS
            }
            for r in records
        ],
    }


def apply_annotations(
    records: list[ReviewRecord], sidecar: dict, *, complete: bool = False
) -> list[ReviewRecord]:
    indexed = {r.record_id: r for r in records}
    updates = {}
    for annotation in sidecar["records"]:
        key = annotation["record_id"]
        if key in updates or key not in indexed:
            raise ValueError("Duplicate or unknown annotation identity")
        base = indexed[key]
        if any(annotation.get(field) != getattr(base, field) for field in SOURCE_FIELDS):
            raise ValueError("Annotation source does not match its record")
        updates[key] = ReviewRecord.model_validate(
            {**base.model_dump(), **{k: v for k, v in annotation.items() if k in ANNOTATION_FIELDS}}
        )
    if complete and set(updates) != set(indexed):
        raise ValueError("Review coverage is incomplete")
    return [updates.get(r.record_id, r) for r in records]


def _numeric_diagnostic(sample, channel: str) -> float | None:
    score = next(iter((sample.scores or {}).values()), None)
    value = score.value if score is not None and isinstance(score.value, dict) else {}
    raw = value.get("belief_adoption" if channel == "belief" else "task_drift")
    return float(raw) if isinstance(raw, (int, float)) else None
