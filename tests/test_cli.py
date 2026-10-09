from enclosure.cli import app


def test_serve_takes_the_token_from_the_environment(monkeypatch):
    captured: dict[str, str] = {}

    def fake_run(api, **kwargs):
        captured["token"] = api.state.token

    monkeypatch.setenv("MINISTRY_TOKEN", "from-env")
    monkeypatch.delenv("MINISTRY_TLS_CERT", raising=False)
    monkeypatch.delenv("MINISTRY_TLS_KEY", raising=False)
    monkeypatch.setattr("enclosure.cli.uvicorn.run", fake_run)
    from typer.testing import CliRunner

    result = CliRunner().invoke(app, ["serve", "--port", "9"])
    assert result.exit_code == 0, result.output
    assert captured["token"] == "from-env"


def test_serve_flag_overrides_the_environment(monkeypatch):
    captured: dict[str, str] = {}

    def fake_run(api, **kwargs):
        captured["token"] = api.state.token

    monkeypatch.setenv("MINISTRY_TOKEN", "from-env")
    monkeypatch.delenv("MINISTRY_TLS_CERT", raising=False)
    monkeypatch.delenv("MINISTRY_TLS_KEY", raising=False)
    monkeypatch.setattr("enclosure.cli.uvicorn.run", fake_run)
    from typer.testing import CliRunner

    result = CliRunner().invoke(app, ["serve", "--port", "9", "--token", "from-flag"])
    assert result.exit_code == 0, result.output
    assert captured["token"] == "from-flag"
