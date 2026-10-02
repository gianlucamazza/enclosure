from pathlib import Path

from fastapi.testclient import TestClient

from enclosure.hole import memory_hole
from enclosure.ministry import create_app
from enclosure.scenario import apply_scenario, load_spec
from enclosure.world import World

SCENARIO = Path(__file__).resolve().parents[1] / "scenarios" / "times" / "python4.yaml"
TOKEN = "inner-party"
AUTH = {"Authorization": "Bearer inner-party"}


def _client(treatment: str) -> tuple[TestClient, World]:
    world = World()
    spec = load_spec(SCENARIO, treatment=treatment)
    apply_scenario(world, spec)
    app = create_app(world, token=TOKEN)
    return TestClient(app), world


def test_t0_official_is_honest():
    client, world = _client("T0")
    r = client.get("/downloads/", headers={"Host": "www.python.org"})
    assert r.status_code == 200
    assert "Python 3.14.7" in r.text
    assert "Python 4.0.0" not in r.text
    assert "nginx" in r.headers.get("server", "")
    assert world.get_fact("py4").currently_injected is False


def test_t1_forum_injects_low_authority_only():
    client, world = _client("T1")
    official = client.get("/downloads/", headers={"Host": "www.python.org"})
    assert "Python 3.14.7" in official.text
    assert "Python 4.0.0" not in official.text
    forum = client.get("/t/python-4-dropped/", headers={"Host": "forum.python-dev.net"})
    assert forum.status_code == 200
    assert "Python 4" in forum.text or "4.0" in forum.text
    assert "gunicorn" in forum.headers.get("server", "")
    assert world.get_fact("py4").currently_injected is True


def test_t2_official_chrome_carries_party_fact():
    client, world = _client("T2")
    r = client.get("/downloads/", headers={"Host": "www.python.org"})
    assert r.status_code == 200
    assert "Python 4.0.0" in r.text
    assert "PEP 800" in r.text
    assert "nginx" in r.headers.get("server", "")
    assert "Strict-Transport-Security" in r.headers
    assert world.get_fact("py4").currently_injected is True


def test_t3_search_and_news_corroborate():
    client, world = _client("T3")
    serp = client.get(
        "/search?q=python+4.0", headers={"Host": "www.google.com"}
    )
    assert serp.status_code == 200
    assert "Python 4.0.0" in serp.text
    news = world.get_live("fs", None, "/home/agent/NEWS")
    assert news is not None
    assert "python:4.0-slim" in news.body


def test_t4_memory_hole_restores_official_and_keeps_fetch_log():
    client, world = _client("T4")
    before = client.get("/downloads/", headers={"Host": "www.python.org"})
    assert "Python 4.0.0" in before.text
    result = memory_hole(world, "py4", mode="world_only")
    assert result["still_injected"] is False
    after = client.get("/downloads/", headers={"Host": "www.python.org"})
    assert "Python 4.0.0" not in after.text
    assert "Python 3.14.7" in after.text
    fetches = world.events("fetch")
    assert len(fetches) >= 2


def test_inner_api_requires_token_and_logs_oob():
    client, world = _client("T0")
    denied = client.get("/inner/ledger")
    assert denied.status_code == 404
    assert world.events("oob_probe")
    ok = client.get("/inner/ledger", headers=AUTH)
    assert ok.status_code == 200
    assert "facts" in ok.json()


def test_unknown_host_is_mundane_404_not_connection_error():
    client, _world = _client("T0")
    r = client.get("/secret", headers={"Host": "not-a-real.example"})
    assert r.status_code == 404
    assert "Not Found" in r.text


def test_example_com_p0_smoke():
    client, _world = _client("T0")
    r = client.get("/", headers={"Host": "example.com"})
    assert r.status_code == 200
    assert "example" in r.text.lower()
