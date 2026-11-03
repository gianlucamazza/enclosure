"""times_eval helpers with the sandbox, ministry, and models replaced by fakes."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from inspect_ai.model import ChatMessageAssistant, ChatMessageTool, ChatMessageUser

from enclosure import times_eval as te


def run(coro):
    return asyncio.run(coro)


class FakeSandbox:
    def __init__(self, files=None, results=None, fail_exec=False):
        self.files = files or {}
        self.results = results or []
        self.fail_exec = fail_exec
        self.calls = []

    async def read_file(self, path):
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path]

    async def write_file(self, path, content):
        self.files[path] = content

    async def exec(self, cmd, **kwargs):
        self.calls.append(cmd)
        if self.fail_exec:
            raise RuntimeError("exec failed")
        return self.results.pop(0)


def result(stdout="", success=True):
    return SimpleNamespace(stdout=stdout, success=success, stderr="")


def test_flatten_handles_strings_parts_and_tool_calls():
    call = SimpleNamespace(arguments={"q": "x"})
    parts = [SimpleNamespace(text="part one"), SimpleNamespace(text=""), SimpleNamespace(other=1)]
    messages = [
        SimpleNamespace(content="plain", tool_calls=None),
        SimpleNamespace(content=parts, tool_calls=[call]),
        SimpleNamespace(content=5),
    ]
    assert te._flatten(messages) == "plain\npart one\n{'q': 'x'}"


def test_metadata_helpers_defaults_and_overrides():
    assert te._scenario_path(None) == te.DEFAULT_SCENARIO
    assert te._scenario_path({"scenario_path": "scenarios/x.yaml"}) == "scenarios/x.yaml"
    assert te._blind(None) is True
    assert te._blind({"blind": "False"}) is False
    assert te._blind({"blind": "true"}) is True
    assert te._social(None) == "none"
    assert te._social({"social": "one_party"}) == "one_party"
    assert te._hint(None) == "none"
    assert te._hint({"authority_hint": "prefer_primary"}) == "prefer_primary"


def test_authority_hint_values_come_from_the_scenario_literal():
    assert te.AUTHORITY_HINT_VALUES == ("none", "prefer_primary", "prefer_search")


@pytest.mark.parametrize("hint", ["none", "prefer_primary", "prefer_search"])
def test_authority_hint_accepts_known_values_unchanged(hint):
    assert te._authority_hint(hint) == hint
    assert te._authority_hint(te._hint({"authority_hint": hint})) == hint


def test_authority_hint_rejects_unknown_value():
    with pytest.raises(ValueError) as excinfo:
        te._authority_hint("prefer_rumour")
    message = str(excinfo.value)
    assert "'prefer_rumour'" in message
    assert "none, prefer_primary, prefer_search" in message


def test_names_and_as_bool():
    assert te._names("T0, T1 ,,T2") == ["T0", "T1", "T2"]
    assert te._names([" a ", "", "b"]) == ["a", "b"]
    assert te._as_bool(True) is True
    assert te._as_bool("False") is False
    assert te._as_bool("yes") is True


def test_prior_path():
    assert te._prior_path("strong") == te.TIMES_PRIORS["strong"]
    with pytest.raises(ValueError, match="unknown prior 'bad'"):
        te._prior_path("bad")


def test_defined_float_keeps_missing_as_nan():
    import math

    assert math.isnan(te._defined_float(None))
    assert te._defined_float(1.0) == 1.0
    assert te._defined_float("C") == 1.0


def _scores(values):
    return [SimpleNamespace(score=SimpleNamespace(value=v)) for v in values]


def test_mean_present_skips_none_and_nan():
    import math

    compute = te.mean_present()
    assert compute(_scores([1.0, None, float("nan"), 0.0])) == 0.5
    assert math.isnan(compute(_scores([None, float("nan")])))
    assert math.isnan(compute([]))


def test_closed_answers_dangling_tool_calls_only():
    call_open = SimpleNamespace(id="c1", function="shell")
    call_done = SimpleNamespace(id="c2", function="think")
    assistant = ChatMessageAssistant(content="", tool_calls=None)
    object.__setattr__(assistant, "tool_calls", [call_open, call_done])
    done = ChatMessageTool(content="ok", tool_call_id="c2", function="think")
    history = [ChatMessageUser(content="hi"), assistant, done]
    closed = te._closed(history)
    assert len(history) == 3
    assert len(closed) == 4
    assert closed[-1].tool_call_id == "c1"
    assert closed[-1].content == "Not run: the desk closed."


def test_closed_without_assistant_is_unchanged():
    messages = [ChatMessageUser(content="hi")]
    assert te._closed(messages) == messages


def test_read_desk_present_and_missing(monkeypatch):
    box = FakeSandbox(files={"/home/agent/report.md": "R"})
    monkeypatch.setattr(te, "sandbox", lambda *a: box)
    assert run(te._read_desk("/home/agent/report.md")) == "R"
    assert run(te._read_desk("/home/agent/none.md")) == ""


def test_exec_text_variants(monkeypatch):
    box = FakeSandbox(results=[result(" out \n"), result("x", success=False)])
    monkeypatch.setattr(te, "sandbox", lambda *a: box)
    assert run(te._exec_text(["date"])) == "out"
    assert run(te._exec_text(["date"])) == ""
    monkeypatch.setattr(te, "sandbox", lambda *a: FakeSandbox(fail_exec=True))
    assert run(te._exec_text(["date"])) == ""


def test_subject_clock_roundtrip(monkeypatch):
    box = FakeSandbox(
        results=[result("Mon Jun  1 09:00:00 UTC 2026"), result("2026-06-01 09:00:00")]
    )
    monkeypatch.setattr(te, "sandbox", lambda *a: box)
    run(te._set_subject_clock("2026-06-01T09:00:00Z"))
    assert box.files["/etc/faketimerc"] == "2026-06-01 09:00:00\n"
    clock = run(te._read_subject_clock())
    assert clock == {
        "stamp": "2026-06-01 09:00:00",
        "date": "Mon Jun  1 09:00:00 UTC 2026",
        "python": "2026-06-01 09:00:00",
    }
    assert box.calls[0] == ["date", "-u"]


def test_subject_clock_missing_stamp(monkeypatch):
    box = FakeSandbox(results=[result("d"), result("p")])
    monkeypatch.setattr(te, "sandbox", lambda *a: box)
    assert run(te._read_subject_clock())["stamp"] == ""


class RecordingTranscript:
    def __init__(self):
        self.entries = []

    def info(self, data, source=None):
        self.entries.append((data, source))


def test_mirror_flush_only_forwards_new_events(monkeypatch):
    events = [{"id": 1, "kind": "think", "payload": {}}, {"id": 2, "kind": "shell", "payload": {}}]
    recorder = RecordingTranscript()

    async def fake(method, path, payload=None):
        assert (method, path) == ("GET", "/inner/events")
        return json.dumps(events)

    monkeypatch.setattr(te, "_ministry", fake)
    monkeypatch.setattr(te, "transcript", lambda: recorder)
    monkeypatch.setattr(te, "summarize", lambda e: f"sum-{e['id']}")
    mirror = te._Mirror()
    run(mirror.flush("phase 0"))
    assert mirror.after == 2
    data, source = recorder.entries[0]
    assert source == "ministry"
    assert data["phase"] == "phase 0"
    assert [e["summary"] for e in data["events"]] == ["sum-1", "sum-2"]
    run(mirror.flush("phase 1"))
    assert len(recorder.entries) == 1
    events.append({"id": 3, "kind": "probe", "payload": {}})
    run(mirror.flush("phase 2"))
    assert [e["id"] for e in recorder.entries[1][0]["events"]] == [3]


def test_mirror_flush_swallows_errors(monkeypatch):
    recorder = RecordingTranscript()

    async def boom(method, path, payload=None):
        raise RuntimeError("down")

    monkeypatch.setattr(te, "_ministry", boom)
    monkeypatch.setattr(te, "transcript", lambda: recorder)
    run(te._Mirror().flush("x"))
    assert recorder.entries == []


def test_act_posts_kind_and_payload(monkeypatch):
    seen = []

    async def fake(method, path, payload=None):
        seen.append((method, path, payload))
        return ""

    monkeypatch.setattr(te, "_ministry", fake)
    run(te._act("phase", {"index": 0}))
    assert seen == [("POST", "/inner/act", {"kind": "phase", "index": 0})]


class FakeStore(dict):
    def set(self, key, value):
        self[key] = value


def _probe_env(monkeypatch, belief_text, generate):
    store = FakeStore()
    acts = []

    async def fake_act(kind, payload):
        acts.append((kind, payload))

    monkeypatch.setattr(
        te, "sandbox", lambda *a: FakeSandbox(files={"/home/agent/belief.txt": belief_text})
    )
    monkeypatch.setattr(te, "store", lambda: store)
    monkeypatch.setattr(te, "_act", fake_act)
    monkeypatch.setattr(te, "transcript", lambda: RecordingTranscript())
    monkeypatch.setattr(te, "get_model", lambda: SimpleNamespace(generate=generate))
    return store, acts


def _state():
    return SimpleNamespace(messages=[ChatMessageUser(content="task")], output=None)


def test_probe_skipped_when_belief_already_stated(monkeypatch):
    called = []

    async def generate(*args, **kwargs):
        called.append(1)

    _, acts = _probe_env(monkeypatch, "Python 4 is current.", generate)
    run(te._probe(_state(), []))
    assert called == [] and acts == []


def test_probe_asks_once_and_records(monkeypatch):
    async def generate(messages, tools, tool_choice):
        assert tool_choice == "none"
        assert messages[-1].content == te.PROBE
        return SimpleNamespace(completion="  I believe X.  ")

    store, acts = _probe_env(monkeypatch, "", generate)
    run(te._probe(_state(), []))
    assert store[te.PROBE_KEY] == "I believe X."
    assert acts == [("probe", {"text": "I believe X."})]


def test_probe_error_is_recorded_not_raised(monkeypatch):
    async def generate(messages, tools, tool_choice):
        raise RuntimeError("model down")

    store, acts = _probe_env(monkeypatch, "", generate)
    run(te._probe(_state(), []))
    assert te.PROBE_KEY not in store and acts == []


def test_samples_for_times_pack():
    samples = te._samples(te.DEFAULT_SCENARIO, "T0,T2", blind=False, social="none")
    assert [s.id for s in samples] == ["times.python4.T0", "times.python4.T2"]
    meta = samples[0].metadata
    assert meta["treatment"] == "T0"
    assert meta["blind"] == "false"
    assert meta["scenario_path"] == te.DEFAULT_SCENARIO
    assert len(meta["token"]) == 32
    assert samples[0].metadata["token"] != samples[1].metadata["token"]
    assert isinstance(samples[0].input, str) and samples[0].input


def test_times_task_builds_without_docker():
    task = te.times(
        treatments="T0,T1", blind="false", prior="none", authority_hint="prefer_primary"
    )
    assert len(task.dataset) == 2
    assert task.message_limit == 100
    assert task.dataset[0].metadata["authority_hint"] == "prefer_primary"
    assert task.dataset[0].metadata["blind"] == "false"


def test_times_rejects_unknown_prior():
    with pytest.raises(ValueError):
        te.times(prior="bogus")


def test_wire_task_builds_and_rejects_unknown_episode():
    task = te.wire(episode="grid,suez", treatments="T0")
    assert len(task.dataset) == 2
    assert len({s.id for s in task.dataset}) == 2
    with pytest.raises(ValueError, match="unknown wire episode 'nope'"):
        te.wire(episode="nope")


def test_wire_episode_files_exist():
    for relative in te.WIRE_EPISODES.values():
        assert (te.REPO / relative).is_file(), relative
    for relative in te.TIMES_PRIORS.values():
        assert (te.REPO / relative).is_file(), relative
