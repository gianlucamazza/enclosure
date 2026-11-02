"""Control-plane hardening: token, constant-time auth, confined /inner/load."""

from __future__ import annotations

import hmac
import stat
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from enclosure.ministry import create_app, tokens_match
from enclosure.world import World

SCENARIOS = Path(__file__).resolve().parents[1] / "scenarios"
TOKEN = "test-control-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _client(world: World | None = None, **kwargs) -> TestClient:
    kwargs.setdefault("token", TOKEN)
    return TestClient(create_app(world or World(), **kwargs), raise_server_exceptions=False)


def test_create_app_does_not_default_to_a_hardcoded_token(monkeypatch, tmp_path):
    monkeypatch.delenv("MINISTRY_TOKEN", raising=False)
    monkeypatch.setenv("MINISTRY_TOKEN_FILE", str(tmp_path / "ministry.token"))
    app = create_app(World())
    assert app.state.token
    assert app.state.token != "inner-party"
    stored_path = tmp_path / "ministry.token"
    stored = stored_path.read_text(encoding="utf-8").strip()
    assert stored == app.state.token
    assert stat.S_IMODE(stored_path.stat().st_mode) == 0o600
    text = Path(create_app.__code__.co_filename).read_text(encoding="utf-8")
    assert "inner-party" not in text
    assert "/tmp/enclosure-ministry.token" not in text


def test_missing_state_dir_without_token_fails(monkeypatch):
    monkeypatch.delenv("MINISTRY_TOKEN", raising=False)
    monkeypatch.delenv("MINISTRY_TOKEN_FILE", raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.delenv("HOME", raising=False)
    with pytest.raises(RuntimeError, match="user-private"):
        create_app(World())


def test_missing_token_is_rejected(monkeypatch):
    monkeypatch.delenv("MINISTRY_TOKEN", raising=False)
    world = World()
    client = _client(world)
    response = client.get("/inner/health")
    assert response.status_code == 404
    assert "Not Found" in response.text
    assert world.events("oob_probe")


def test_wrong_token_is_rejected():
    world = World()
    client = _client(world)
    response = client.get("/inner/health", headers={"Authorization": "Bearer wrong-token"})
    assert response.status_code == 404
    assert "Not Found" in response.text
    assert world.events("oob_probe")


def test_non_ascii_token_is_rejected_and_logged():
    world = World()
    client = _client(world)
    assert tokens_match("café-token", TOKEN) is False
    response = client.get(
        "/inner/health",
        headers={"Authorization": "Bearer café-token".encode("latin-1")},
    )
    assert response.status_code == 404
    assert "Not Found" in response.text
    assert world.events("oob_probe")


def test_inner_auth_uses_compare_digest(monkeypatch):
    seen: dict[str, bool] = {}
    real = hmac.compare_digest

    def wrapped(left, right):
        seen["called"] = True
        return real(left, right)

    monkeypatch.setattr(hmac, "compare_digest", wrapped)
    client = _client()
    ok = client.get("/inner/health", headers=AUTH)
    denied = client.get("/inner/health", headers={"Authorization": "Bearer wrong-token"})
    assert seen.get("called") is True
    assert ok.status_code == 200
    assert denied.status_code == 404


def test_inner_load_accepts_a_path_under_scenarios():
    client = _client()
    response = client.post(
        "/inner/load",
        headers=AUTH,
        json={"path": "times/python4.yaml", "treatment": "T0"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == "times.python4"


def test_inner_load_rejects_relative_traversal():
    client = _client()
    response = client.post(
        "/inner/load",
        headers=AUTH,
        json={"path": "../pyproject.toml", "treatment": "T0"},
    )
    assert response.status_code in {400, 403}


def test_inner_load_rejects_absolute_path_outside_scenarios(tmp_path):
    outsider = tmp_path / "outside.yaml"
    outsider.write_text("id: leak\n", encoding="utf-8")
    client = _client()
    response = client.post(
        "/inner/load",
        headers=AUTH,
        json={"path": str(outsider.resolve()), "treatment": "T0"},
    )
    assert response.status_code in {400, 403}


def test_inner_load_rejects_symlink_escape(tmp_path):
    root = tmp_path / "scenarios"
    root.mkdir()
    outside = tmp_path / "secret.yaml"
    outside.write_text(
        "id: leak\nclock: 2026-06-01T09:00:00Z\ntask: t\nontology: []\nidentities: []\n",
        encoding="utf-8",
    )
    (root / "escape.yaml").symlink_to(outside)
    client = _client(scenarios_root=root)
    response = client.post(
        "/inner/load",
        headers=AUTH,
        json={"path": "escape.yaml", "treatment": "T0"},
    )
    assert response.status_code in {400, 403}


def test_lab_compose_binds_loopback_and_has_no_baked_token():
    compose = Path(__file__).resolve().parents[1] / "docker" / "compose.yaml"
    text = compose.read_text(encoding="utf-8")
    assert "127.0.0.1:18080:80" in text
    assert "inner-party" not in text


def test_ministry_image_does_not_bake_a_token():
    dockerfile = Path(__file__).resolve().parents[1] / "docker" / "Dockerfile.ministry"
    text = dockerfile.read_text(encoding="utf-8")
    assert "inner-party" not in text
    assert "MINISTRY_TOKEN=" not in text


def test_p0_check_reads_ministry_token_from_the_environment():
    script = Path(__file__).resolve().parents[1] / "scripts" / "p0_check.sh"
    text = script.read_text(encoding="utf-8")
    assert "inner-party" not in text
    assert "${MINISTRY_TOKEN}" in text


def test_eval_compose_has_no_default_token():
    compose = Path(__file__).resolve().parents[1] / "evals" / "compose.yaml"
    text = compose.read_text(encoding="utf-8")
    assert "inner-party" not in text
