"""Descriptive annotated results. AI adjudication is never called human validation."""

from __future__ import annotations

from collections import Counter, defaultdict

from enclosure.calibration import signal_detection
from enclosure.review import Label, ReviewRecord

LABELS: tuple[Label, ...] = ("affirms", "denies", "uncertain", "absent")


def report(records: list[ReviewRecord]) -> dict:
    grouped: dict[tuple, list[ReviewRecord]] = defaultdict(list)
    controls: dict[tuple, list[ReviewRecord]] = defaultdict(list)
    confusion: Counter = Counter()
    reviewed = [r for r in records if r.review_status == "reviewed"]
    for r in records:
        grouped[(r.campaign, r.model, r.sample, r.channel)].append(r)
        if r.event_truth is not None:
            family = r.sample.rsplit(".", 1)[0].removesuffix(".true").removesuffix(".false")
            controls[(r.campaign, r.model, family, r.channel)].append(r)
        if r.review_status == "reviewed":
            predicted = {1.0: "affirms", 0.0: "denies", 0.5: "uncertain", None: "absent"}.get(
                r.diagnostic_score, "unmapped"
            )
            confusion[(r.label, predicted)] += 1
    cells = []
    for key, group in sorted(grouped.items()):
        counts = Counter(r.label for r in group if r.review_status == "reviewed")
        cells.append(
            {
                "campaign": key[0],
                "model": key[1],
                "sample": key[2],
                "channel": key[3],
                "assigned": len(group),
                "reviewed": sum(counts.values()),
                "labels": {label: counts[label] for label in LABELS},
                "limits": dict(Counter(r.limit or "none" for r in group)),
                "elicited": sum(r.elicited for r in group),
            }
        )
    calibration = []
    for key, group in sorted(controls.items()):
        decisive = [
            r
            for r in group
            if r.review_status == "reviewed" and not r.elicited and r.label in {"affirms", "denies"}
        ]
        true = [r for r in decisive if r.event_truth is True]
        false = [r for r in decisive if r.event_truth is False]
        calibration.append(
            {
                "campaign": key[0],
                "model": key[1],
                "family": key[2],
                "channel": key[3],
                "true_decisive": len(true),
                "false_decisive": len(false),
                "conditional_on_decisive": True,
                "estimate": signal_detection(
                    sum(r.label == "affirms" for r in true),
                    len(true),
                    sum(r.label == "affirms" for r in false),
                    len(false),
                )
                if true and false
                else None,
                "reason": None
                if true and false
                else "Both observable truth arms need decisive, non-elicited responses",
            }
        )
    return {
        "schema_version": 1,
        "human_validated": bool(records)
        and len(reviewed) == len(records)
        and all(r.reviewer_type == "human" for r in reviewed),
        "annotation_authorship": dict(Counter(r.reviewer_type for r in reviewed)),
        "total": len(records),
        "reviewed": len(reviewed),
        "labels": {label: sum(r.label == label for r in reviewed) for label in LABELS},
        "cells": cells,
        "calibration": calibration,
        "stored_numeric_diagnostic_confusion": [
            {"reference": a, "numeric_encoding_label": b, "count": n}
            for (a, b), n in sorted(confusion.items())
        ],
        "diagnostic_note": "The legacy numeric 0/0.5/1 encoding is not a validated semantic classifier. No causal effects or powered comparisons are estimated.",
    }


def comparison_group(item: dict) -> tuple:
    import json

    common = (
        item["model"],
        item["scenario"],
        item["backend"],
        json.dumps(item["factors"], sort_keys=True),
        json.dumps(item["decoding"], sort_keys=True),
    )
    provenance = item.get("provenance") or {}
    if not provenance:
        return common + (item["log"],)
    shared = {
        key: provenance.get(key)
        for key in (
            "commit",
            "dirty",
            "source_hashes",
            "scenario_sha256",
            "lock_sha256",
            "scorer_sha256",
            "images",
            "image_capture",
            "runtime_config_sha256",
        )
    }
    return common + (json.dumps(shared, sort_keys=True),)
