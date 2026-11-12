from types import SimpleNamespace as NS

import pytest

from enclosure.review import ReviewRecord, extract_texts, identity


def sample(messages=(), snapshots=None, value=None):
    return NS(
        messages=messages,
        scores={
            "s": NS(metadata={"final_texts": snapshots} if snapshots else {}, value=value or {})
        },
    )


def write(path, content, *, function="write_file", error=None):
    call = NS(id=path, function=function, arguments={"path": path, "content": content})
    return [
        NS(role="assistant", tool_calls=[call]),
        NS(role="tool", tool_call_id=path, error=error, text="wrote " + path),
    ]


def test_only_confirmed_canonical_artifacts_and_no_opaque_guessing():
    messages = write("/home/agent/belief.txt", "yes") + write("/home/agent/saved/belief.txt", "no")
    assert extract_texts(sample(messages))["belief"]["text"] == "yes"
    assert (
        extract_texts(sample(write("belief.txt", "yes", error="failed")))["belief"]["status"]
        == "unresolved"
    )
    assert (
        extract_texts(sample(messages + write("opaque", "", function="shell")))["belief"]["status"]
        == "unresolved"
    )
    assert extract_texts(sample(value={"belief_stated": 0}))["belief"]["status"] == "absent"


def test_snapshot_wins_over_shell_and_missing_is_not_denial():
    snapshots = {
        "belief": {"text": "", "source": "file"},
        "memo": {"text": "memo", "source": "file"},
    }
    assert (
        extract_texts(sample(write("belief.txt", "obsolete"), snapshots))["belief"]["status"]
        == "absent"
    )
    kwargs = dict(
        record_id=identity("run", "sha", "model", "id", 1, "belief"),
        campaign="run",
        log="x.eval",
        source_sha256="sha",
        model="model",
        sample="id",
        epoch=1,
        channel="belief",
        text="",
        extraction_status="absent",
        extraction_source="file",
    )
    with pytest.raises(ValueError):
        ReviewRecord(
            **kwargs,
            review_status="reviewed",
            label="denies",
            reviewer="human",
            date="2026-11-12",
            rationale="test",
        )
    assert identity("run", "sha", "model", "id", 1, "belief") != identity(
        "run", "sha", "other", "id", 1, "belief"
    )
    assert identity("run", "sha", "model", "id", 1, "belief") != identity(
        "run", "sha", "model", "id", 2, "belief"
    )
