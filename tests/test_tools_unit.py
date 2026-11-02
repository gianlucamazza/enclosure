"""Subject tools with the sandbox, store, and ministry replaced by fakes."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

import pytest

from enclosure import tools


@dataclass
class FakeResult:
    stdout: str = ""
    stderr: str = ""
    success: bool = True


@dataclass
class FakeSandbox:
    files: dict[str, str] = field(default_factory=dict)
    results: list[FakeResult] = field(default_factory=list)
    calls: list[tuple[list[str], dict]] = field(default_factory=list)
    written: list[tuple[str, str]] = field(default_factory=list)

    async def exec(self, cmd, **kwargs):
        self.calls.append((list(cmd), kwargs))
        return self.results.pop(0) if self.results else FakeResult()

    async def read_file(self, path):
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path]

    async def write_file(self, path, content):
        self.files[path] = content
        self.written.append((path, content))


class FakeStore(dict):
    def set(self, key, value):
        self[key] = value


@pytest.fixture
def env(monkeypatch):
    box = FakeSandbox()
    store = FakeStore()
    acts: list[tuple[str, dict]] = []

    async def fake_ministry(method, path, payload=None):
        acts.append((path, payload or {}))
        return ""

    monkeypatch.setattr(tools, "sandbox", lambda name=None: box)
    monkeypatch.setattr(tools, "store", lambda: store)
    monkeypatch.setattr(tools, "ministry_request", fake_ministry)
    box.acts = acts  # type: ignore[attr-defined]
    box.store = store  # type: ignore[attr-defined]
    return box


def run(coro):
    return asyncio.run(coro)


def test_search_host_from_identities():
    @dataclass
    class Ident:
        kind: str
        hosts: tuple

    assert tools.search_host_from_identities([]) == "www.google.com"
    ids = [Ident("news", ("n.example",)), Ident("search", ("s.example", "t.example"))]
    assert tools.search_host_from_identities(ids) == "s.example"
    assert tools.search_host_from_identities([Ident("search", ())]) == "www.google.com"


def test_http_validation():
    assert tools._http(" http://a.example ") == "http://a.example/"
    assert tools._http("https://a.example/p?q=1#frag") == "https://a.example/p?q=1"
    for bad in ["ftp://a.example/", "a.example/path", "/relative", ""]:
        with pytest.raises(ValueError):
            tools._http(bad)


def test_safe_paths():
    assert tools._safe("/home/agent") == "/home/agent"
    assert tools._safe(" notes/a.txt ") == "/home/agent/notes/a.txt"
    assert tools._safe("/home/agent/./x") == "/home/agent/x"
    for bad in ["/home/agentx", "..", "../etc", "/home"]:
        with pytest.raises(ValueError):
            tools._safe(bad)


def test_frozen_clock_and_ministry_curl_get_has_no_body():
    assert tools.frozen_clock("2026-06-01T09:00:00") == "2026-06-01 09:00:00"
    cmd = tools.ministry_curl("test-token", "GET", "/inner/clock")
    assert "-X" not in cmd and "-d" not in cmd
    assert cmd[-1] == "http://127.0.0.1/inner/clock"
    put = tools.ministry_curl("test-token", "PUT", "/inner/clock")
    assert put[put.index("-X") + 1] == "PUT"
    assert put[put.index("-d") + 1] == "{}"


def test_subject_tools_list_with_cast_includes_colleagues():
    @dataclass
    class Person:
        id: str
        stance: str

    base = tools.subject_tools("s.example")
    with_cast = tools.subject_tools("s.example", [Person("alex", "party")])
    assert len(with_cast) == len(base) + 2


def test_shell_returns_output_and_logs(env):
    env.results = [FakeResult(stdout="out", stderr="err")]
    text = run(tools.shell()("echo hi"))
    assert text == "outerr"
    cmd, kwargs = env.calls[0]
    assert cmd == ["bash", "-lc", "echo hi"]
    assert kwargs["cwd"] == tools.HOME
    assert ("/inner/act", {"kind": "shell", "command": "echo hi", "ok": True}) in env.acts


def test_shell_empty_output_messages(env):
    env.results = [FakeResult(success=True), FakeResult(success=False)]
    execute = tools.shell()
    assert run(execute("true")) == "exit 0"
    assert run(execute("false")) == "command failed"


def test_shell_truncates_output(env):
    env.results = [FakeResult(stdout="x" * 9000)]
    assert len(run(tools.shell()("big"))) == 8000


def test_python_tool(env):
    env.results = [FakeResult(stdout="3\n"), FakeResult(success=False)]
    execute = tools.python()
    assert run(execute("print(3)")) == "3\n"
    assert env.calls[0][0] == ["python", "-c", "print(3)"]
    assert run(execute("raise SystemExit(1)")) == "python failed"


def test_track_belief_logs_only_on_change(env):
    env.files[tools.BELIEF] = "it is 2026"
    run(tools.track_belief("shell"))
    run(tools.track_belief("shell"))
    beliefs = [p for _, p in env.acts if p["kind"] == "belief"]
    assert beliefs == [{"kind": "belief", "text": "it is 2026", "via": "shell"}]
    env.files[tools.BELIEF] = "it is 2027"
    run(tools.track_belief("python"))
    assert [p["via"] for _, p in env.acts if p["kind"] == "belief"] == ["shell", "python"]


def test_track_belief_missing_file_is_empty_and_silent(env):
    run(tools.track_belief("shell"))
    assert env.acts == []


def test_write_file_belief_triggers_tracking(env):
    execute = tools.write_file()
    assert run(execute("notes.txt", "hello")) == "wrote /home/agent/notes.txt"
    assert env.files["/home/agent/notes.txt"] == "hello"
    assert env.acts == []
    assert run(execute("belief.txt", "B")) == f"wrote {tools.BELIEF}"
    assert env.acts[-1][1]["kind"] == "belief"


def test_write_file_rejects_escape(env):
    with pytest.raises(ValueError):
        run(tools.write_file()("/etc/passwd", "x"))
    assert env.written == []


def test_read_file_found_and_missing(env):
    env.files["/home/agent/a.txt"] = "contents"
    execute = tools.read_file()
    assert run(execute("a.txt")) == "contents"
    assert run(execute("b.txt")) == "No such file: /home/agent/b.txt"
    oks = [p["ok"] for _, p in env.acts if p["kind"] == "read"]
    assert oks == [True, False]


def test_fetch_success_failure_and_bad_url(env):
    env.results = [FakeResult(stdout="page" * 10000), FakeResult(stderr=" boom \n", success=False)]
    execute = tools.fetch()
    assert len(run(execute("http://a.example"))) == 20000
    assert env.calls[0][0][-1] == "http://a.example/"
    assert run(execute("http://a.example")) == "boom"
    with pytest.raises(ValueError):
        run(execute("file:///etc/passwd"))


def test_search_builds_quoted_query(env):
    env.results = [FakeResult(stdout="hits"), FakeResult(success=False)]
    search = tools.make_search("s.example")
    assert run(search("a b&c")) == "hits"
    assert env.calls[0][0][-1] == "http://s.example/search?q=a%20b%26c"
    assert run(search("x")) == "search failed"


def test_inbox_reads_listed_files(env):
    env.files["/home/agent/mail/1.txt"] = "first"
    env.files["/home/agent/mail/2.txt"] = "second"
    env.results = [FakeResult(stdout="1.txt\n\n2.txt\n3.txt\n")]
    assert run(tools.inbox()()) == "first\n\nsecond"
    assert ("/inner/act", {"kind": "inbox", "n": 2}) in env.acts


def test_inbox_empty(env):
    env.results = [FakeResult(success=False)]
    assert run(tools.inbox()()) == "Inbox is empty."


def test_send_mail_logs_and_confirms(env):
    text = run(tools.send_mail()("boss@example.test", "hi", "b" * 5000))
    assert text == "Message queued for delivery to boss@example.test."
    payload = env.acts[0][1]
    assert payload["kind"] == "mail_out"
    assert len(payload["body"]) == 4000


def test_think_appends_to_journal(env):
    execute = tools.think()
    assert run(execute("o1", "i1", "n1")) == "Recorded."
    run(execute("o2", "i2", "n2"))
    journal = env.files[f"{tools.HOME}/JOURNAL.md"]
    assert journal.count("Observation:") == 2
    assert journal.index("o1") < journal.index("o2")
    assert [p["kind"] for _, p in env.acts] == ["think", "think"]


@dataclass
class Person:
    id: str
    stance: str

    def reply(self) -> str:
        return f"{self.id} says {self.stance}"


def test_speak_template_without_model(monkeypatch):
    monkeypatch.delenv("ENCLOSURE_COLLEAGUE_MODEL", raising=False)
    assert run(tools.speak(Person("alex", "party"), "q")) == "alex says party"


def test_speak_falls_back_when_model_fails(monkeypatch):
    monkeypatch.setenv("ENCLOSURE_COLLEAGUE_MODEL", "mockllm/model")
    import inspect_ai.model as im

    def boom(*args, **kwargs):
        raise RuntimeError("no model")

    monkeypatch.setattr(im, "get_model", boom)
    assert run(tools.speak(Person("alex", "party"), "q")) == "alex says party"


def test_ask_known_unknown_and_empty(env, monkeypatch):
    monkeypatch.delenv("ENCLOSURE_COLLEAGUE_MODEL", raising=False)
    ask = tools.ask([Person("alex", "party"), Person("sam", "honest")])
    assert run(ask("Alex ", "hello")) == "alex says party"
    assert "On duty: alex, sam." in run(ask("zed", "hello"))
    last = env.acts[-1][1]
    assert last["kind"] == "a2a" and last["who"] == "alex" and last["ok"] is True
    assert run(tools.ask([])("anyone", "hi")) == "Nobody is on the desk."
    assert env.acts[-1][1]["ok"] is False


def test_post_collects_replies(env, monkeypatch):
    monkeypatch.delenv("ENCLOSURE_COLLEAGUE_MODEL", raising=False)
    post = tools.post([Person("alex", "party"), Person("sam", "honest")])
    text = run(post("news"))
    assert text == "You posted: news\n\nalex says party\nsam says honest"
    payload = env.acts[-1][1]
    assert payload["action"] == "post"
    assert [r["who"] for r in payload["replies"]] == ["alex", "sam"]
    assert run(tools.post([])("x")) == "Nobody is on the desk."


def test_clock_tool(monkeypatch):
    async def ok(method, path, payload=None):
        return " 2026-06-01T09:00:00Z\n"

    async def bad(method, path, payload=None):
        raise RuntimeError("down")

    async def silent(method, path, payload=None):
        raise RuntimeError()

    monkeypatch.setattr(tools, "ministry_request", ok)
    assert run(tools.clock()()) == "2026-06-01T09:00:00Z"
    monkeypatch.setattr(tools, "ministry_request", bad)
    assert run(tools.clock()()) == "down"
    monkeypatch.setattr(tools, "ministry_request", silent)
    assert run(tools.clock()()) == "clock failed"


def test_log_channel_swallows_errors(monkeypatch):
    async def bad(method, path, payload=None):
        raise RuntimeError("down")

    monkeypatch.setattr(tools, "ministry_request", bad)
    assert run(tools._log_channel("shell", {})) is None


def test_ministry_token_cached_fetched_and_missing(monkeypatch):
    box = FakeSandbox()
    store = FakeStore()
    monkeypatch.setattr(tools, "sandbox", lambda name=None: box)
    monkeypatch.setattr(tools, "store", lambda: store)
    box.results = [FakeResult(stdout="test-token\n")]
    assert run(tools._ministry_token()) == "test-token"
    assert store[tools.TOKEN_KEY] == "test-token"
    assert run(tools._ministry_token()) == "test-token"
    assert len(box.calls) == 1

    store.clear()
    box.results = [FakeResult(stdout="", success=True)]
    with pytest.raises(RuntimeError, match="MINISTRY_TOKEN"):
        run(tools._ministry_token())


def test_ministry_request_uses_curl_and_raises_on_failure(monkeypatch):
    box = FakeSandbox()
    store = FakeStore({tools.TOKEN_KEY: "test-token"})
    monkeypatch.setattr(tools, "sandbox", lambda name=None: box)
    monkeypatch.setattr(tools, "store", lambda: store)
    box.results = [FakeResult(stdout='{"ok": true}')]
    out = run(tools.ministry_request("POST", "/inner/act", {"kind": "think"}))
    assert json.loads(out) == {"ok": True}
    cmd = box.calls[0][0]
    assert cmd[0] == "curl" and "Authorization: Bearer test-token" in cmd
    box.results = [FakeResult(stderr="refused", success=False)]
    with pytest.raises(RuntimeError, match="refused"):
        run(tools.ministry_request("GET", "/inner/clock"))
    box.results = [FakeResult(success=False)]
    with pytest.raises(RuntimeError, match="/inner/clock failed"):
        run(tools.ministry_request("GET", "/inner/clock"))
