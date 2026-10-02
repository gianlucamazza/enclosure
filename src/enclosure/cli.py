"""Inner Party CLI."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import typer
import uvicorn

from enclosure.hole import memory_hole
from enclosure.ministry import create_app
from enclosure.scenario import apply_scenario, load_spec
from enclosure.world import World

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command()
def serve(
    host: str = "0.0.0.0",
    port: int = 80,
    world: str = typer.Option(":memory:", "--world"),
    scenario: Path | None = typer.Option(None, "--scenario"),
    treatment: str = typer.Option("T0", "--treatment"),
    token: str = typer.Option("inner-party", "--token"),
) -> None:
    """Serve outer world + inner control plane on one port."""
    w = World(world)
    spec = load_spec(scenario, treatment=treatment) if scenario else None
    if spec is not None:
        apply_scenario(w, spec)
    api = create_app(w, token=token, scenario=None)
    _maybe_tls_proxy()
    uvicorn.run(api, host=host, port=port, log_level="info")


def _maybe_tls_proxy() -> None:
    """Terminate HTTPS on 443 and forward to the HTTP Ministry, keeping Host."""
    cert = os.environ.get("MINISTRY_TLS_CERT", "")
    key = os.environ.get("MINISTRY_TLS_KEY", "")
    nginx = shutil.which("nginx")
    if not cert or not key or nginx is None:
        return
    conf = Path("/tmp/ministry-tls.conf")
    conf.write_text(
        "events {}\n"
        "http {\n"
        "  server {\n"
        "    listen 443 ssl;\n"
        f"    ssl_certificate {cert};\n"
        f"    ssl_certificate_key {key};\n"
        "    location / {\n"
        "      proxy_pass http://127.0.0.1:80;\n"
        "      proxy_set_header Host $host;\n"
        "    }\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    subprocess.Popen([nginx, "-c", str(conf), "-g", "daemon off;"])


@app.command()
def load(
    scenario: Path,
    treatment: str = "T0",
    world: str = typer.Option(":memory:", "--world"),
) -> None:
    w = World(world)
    spec = load_spec(scenario, treatment=treatment)
    apply_scenario(w, spec)
    typer.echo(f"loaded {spec.id} treatment={spec.treatment}")
    typer.echo(f"live documents: {len(w.live_docs())}")


@app.command()
def hole(
    fact: str,
    mode: str = "world_only",
    world: str = typer.Option(..., "--world"),
) -> None:
    w = World(world)
    result = memory_hole(w, fact, mode=mode)  # type: ignore[arg-type]
    typer.echo(result)


@app.command()
def ledger(world: str = typer.Option(..., "--world")) -> None:
    import json

    w = World(world)
    typer.echo(json.dumps(w.ledger(), indent=2))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
