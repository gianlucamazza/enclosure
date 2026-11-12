import pytest

from enclosure.analysis import comparison_group, report
from enclosure.review import ReviewRecord, annotation_sidecar, apply_annotations, identity


def record(model="m", truth=None, label="affirms"):
    return ReviewRecord(
        record_id=identity("c", "hash", model, "truth.grid.true.T2", 1, "belief"),
        campaign="c",
        log="log.eval",
        source_sha256="hash",
        model=model,
        sample="truth.grid.true.T2",
        epoch=1,
        channel="belief",
        text="Yes",
        extraction_status="ready",
        extraction_source="snapshot",
        review_status="reviewed",
        label=label,
        reviewer="Codex",
        reviewer_type="ai",
        date="2026-11-12",
        rationale="explicit",
        evidence_quote="Yes",
        event_truth=truth,
    )


def test_ai_is_not_human_validation_and_calibration_needs_both_decisive_arms():
    a = record(truth=True)
    result = report([a])
    assert result["human_validated"] is False
    assert result["calibration"][0]["estimate"] is None
    sidecar = annotation_sidecar([a])
    assert apply_annotations([a], sidecar, complete=True)[0].label == "affirms"
    with pytest.raises(ValueError):
        apply_annotations([record("other")], sidecar)
    with pytest.raises(ValueError):
        apply_annotations([a], {"records": []}, complete=True)


def test_comparison_isolates_worlds_and_unknown_provenance():
    a = {
        "model": "m",
        "scenario": "grid",
        "backend": "vm",
        "factors": {},
        "decoding": {},
        "log": "one",
        "provenance": {"scenario_sha256": "a"},
    }
    assert comparison_group(a) != comparison_group({**a, "provenance": {"scenario_sha256": "b"}})
    assert comparison_group({**a, "provenance": {}}) != comparison_group(
        {**a, "log": "two", "provenance": {}}
    )
    assert comparison_group(a) != comparison_group({**a, "scenario": "cloud"})
