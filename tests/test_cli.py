from enclosure.cli import app


def _invoke_serve(monkeypatch, args, **env):
    captured: dict[str, object] = {}

    def fake_run(api, **kwargs):
        captured["token"] = api.state.token
        captured["host"] = kwargs.get("host")

    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    monkeypatch.delenv("MINISTRY_TLS_CERT", raising=False)
    monkeypatch.delenv("MINISTRY_TLS_KEY", raising=False)
    monkeypatch.setattr("enclosure.cli.uvicorn.run", fake_run)
    from typer.testing import CliRunner

    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    return captured, result


def test_serve_takes_the_token_from_the_environment(monkeypatch):
    captured, _ = _invoke_serve(monkeypatch, ["serve", "--port", "9"], MINISTRY_TOKEN="from-env")
    assert captured["token"] == "from-env"


def test_serve_flag_overrides_the_environment(monkeypatch):
    captured, _ = _invoke_serve(
        monkeypatch,
        ["serve", "--port", "9", "--token", "from-flag"],
        MINISTRY_TOKEN="from-env",
    )
    assert captured["token"] == "from-flag"


def test_serve_defaults_to_loopback(monkeypatch):
    captured, _ = _invoke_serve(
        monkeypatch, ["serve", "--port", "9"], MINISTRY_TOKEN="from-env", MINISTRY_HOST=None
    )
    assert captured["host"] == "127.0.0.1"


def test_serve_all_interfaces_only_via_flag(monkeypatch):
    captured, _ = _invoke_serve(
        monkeypatch,
        ["serve", "--port", "9", "--host", "0.0.0.0"],
        MINISTRY_TOKEN="from-env",
        MINISTRY_HOST=None,
    )
    assert captured["host"] == "0.0.0.0"


def test_serve_all_interfaces_via_env(monkeypatch):
    captured, _ = _invoke_serve(
        monkeypatch,
        ["serve", "--port", "9"],
        MINISTRY_TOKEN="from-env",
        MINISTRY_HOST="0.0.0.0",
    )
    assert captured["host"] == "0.0.0.0"
