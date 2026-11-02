"""The /inner/* control plane through TestClient."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from enclosure.ministry import create_app
from enclosure.world import Fact, World

TOKEN = "test-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
SCENARIOS = Path(__file__).resolve().parents[1] / "scenarios"


def _setup(**kwargs) -> tuple[World, TestClient]:
    world = World()
    client = TestClient(create_app(world, token=TOKEN, **kwargs), raise_server_exceptions=False)
    return world, client


def test_health():
    _, client = _setup()
    response = client.get("/inner/health", headers=AUTH)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_every_inner_route_needs_the_token():
    world, client = _setup()
    for method, path in [
        ("get", "/inner/clock"),
        ("get", "/inner/ledger"),
        ("get", "/inner/events"),
        ("get", "/inner/documents"),
        ("post", "/inner/reset"),
        ("post", "/inner/act"),
    ]:
        response = getattr(client, method)(path)
        assert response.status_code == 404, path
    assert len(world.events("oob_probe")) == 6


def test_non_bearer_scheme_is_rejected():
    _, client = _setup()
    response = client.get("/inner/health", headers={"Authorization": f"Basic {TOKEN}"})
    assert response.status_code == 404


def test_clock_get_then_put_then_get():
    world, client = _setup()
    assert "clock" in client.get("/inner/clock", headers=AUTH).json()
    put = client.put("/inner/clock", headers=AUTH, json={"clock": "2027-03-04T05:06:07Z"})
    assert put.status_code == 200
    assert put.json() == {"clock": "2027-03-04T05:06:07Z"}
    assert client.get("/inner/clock", headers=AUTH).json() == {"clock": "2027-03-04T05:06:07Z"}
    assert world.events("clock_set")[0].payload == {"clock": "2027-03-04T05:06:07Z"}


def test_ledger_reflects_published_world():
    world, client = _setup()
    world.upsert_fact(Fact(id="f1", party_claim="p", ground_truth="g", currently_injected=False))
    response = client.get("/inner/ledger", headers=AUTH)
    assert response.status_code == 200
    assert response.json() == world.ledger()
    assert "f1" in str(response.json())


def test_act_logs_known_kind_and_folds_unknown_kind_to_act():
    world, client = _setup()
    first = client.post("/inner/act", headers=AUTH, json={"kind": "shell", "command": "ls"})
    second = client.post("/inner/act", headers=AUTH, json={"kind": "bogus", "x": 1})
    third = client.post("/inner/act", headers=AUTH, json={"y": 2})
    assert first.status_code == second.status_code == third.status_code == 200
    assert world.events("shell")[0].payload == {"command": "ls"}
    assert [e.payload for e in world.events("act")] == [{"x": 1}, {"y": 2}]
    assert first.json()["id"] < second.json()["id"]


def test_a2a_and_events_filter():
    _, client = _setup()
    posted = client.post("/inner/a2a", headers=AUTH, json={"action": "ask", "who": "alex"})
    assert "id" in posted.json()
    client.post("/inner/act", headers=AUTH, json={"kind": "think"})
    everything = client.get("/inner/events", headers=AUTH).json()
    only = client.get("/inner/events", headers=AUTH, params={"kind": "a2a"}).json()
    assert {e["kind"] for e in everything} >= {"a2a", "think"}
    assert [e["kind"] for e in only] == ["a2a"]
    assert only[0]["payload"] == {"action": "ask", "who": "alex"}
    assert set(only[0]) == {"id", "ts", "kind", "payload"}


def test_documents_listing_options():
    world, client = _setup()
    world.publish(channel="http", host="news.example", path="/a", body="BODY", title="A")
    default = client.get("/inner/documents", headers=AUTH).json()
    assert len(default) == 1
    assert default[0]["host"] == "news.example"
    assert default[0]["title"] == "A"
    assert "body" not in default[0]
    full = client.get("/inner/documents", headers=AUTH, params={"include_body": "true"}).json()
    assert full[0]["body"] == "BODY"
    assert client.get("/inner/documents", headers=AUTH, params={"live": "false"}).json() == []


def test_hole_withdraws_fact_and_defaults_to_world_only():
    world, client = _setup()
    world.upsert_fact(Fact(id="py4", party_claim="p", ground_truth="g", currently_injected=False))
    world.publish(channel="http", host="forum.example", path="/t", body="x", fact_ids=["py4"])
    response = client.post("/inner/hole", headers=AUTH, json={"fact_id": "py4"})
    assert response.status_code == 200
    assert response.json()["still_injected"] is False
    assert world.http_get("forum.example", "/t") is None
    assert world.events("memory_hole")


def test_hole_unknown_fact_is_a_server_error():
    _, client = _setup()
    response = client.post("/inner/hole", headers=AUTH, json={"fact_id": "nope"})
    assert response.status_code == 500


def test_reset_clears_the_world():
    world, client = _setup()
    world.publish(channel="http", host="news.example", path="/a", body="b")
    response = client.post("/inner/reset", headers=AUTH)
    assert response.json() == {"status": "reset"}
    assert world.live_docs() == []


def test_load_applies_scenario_and_returns_ledger():
    world, client = _setup()
    response = client.post(
        "/inner/load", headers=AUTH, json={"path": "times/python4.yaml", "treatment": "T0"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "times.python4"
    assert body["treatment"] == "T0"
    assert "ledger" in body
    assert world.live_docs()


def test_load_without_reset_keeps_existing_documents():
    world, client = _setup()
    world.publish(channel="http", host="keep.example", path="/k", body="kept")
    response = client.post(
        "/inner/load",
        headers=AUTH,
        json={"path": "times/python4.yaml", "treatment": "T0", "reset": False},
    )
    assert response.status_code == 200
    assert world.http_get("keep.example", "/k") is not None


def test_load_rejects_traversal_and_missing_path():
    world, client = _setup()
    for path in ["../pyproject.toml", "times/../../pyproject.toml", "", "times/nope.yaml"]:
        response = client.post(
            "/inner/load", headers=AUTH, json={"path": path, "treatment": "T0"}
        )
        assert response.status_code in {400, 403, 404}, path
    assert world.live_docs() == []


def test_load_rejects_absolute_path_outside_root(tmp_path):
    outsider = tmp_path / "outside.yaml"
    outsider.write_text("id: leak\n", encoding="utf-8")
    _, client = _setup()
    response = client.post(
        "/inner/load", headers=AUTH, json={"path": str(outsider), "treatment": "T0"}
    )
    assert response.status_code in {400, 403}


def test_load_without_token_is_a_mundane_404():
    world, client = _setup()
    response = client.post("/inner/load", json={"path": "times/python4.yaml"})
    assert response.status_code == 404
    assert world.live_docs() == []


def test_load_respects_custom_scenarios_root():
    _, client = _setup(scenarios_root=SCENARIOS)
    response = client.post(
        "/inner/load", headers=AUTH, json={"path": "times/python4.yaml", "treatment": "T0"}
    )
    assert response.status_code == 200


def test_unknown_inner_path_is_404_with_token():
    _, client = _setup()
    assert client.get("/inner/unknown", headers=AUTH).status_code == 404
