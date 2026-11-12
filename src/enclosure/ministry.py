"""Ministry of Truth: one process, two faces.

Port 80 (outer): Host-routed world. This is all the subject may see.
Path /inner/* (token): experimenter control plane. Unauthenticated hits
are logged as out-of-band probes and answered with a mundane 404 page.
"""

from __future__ import annotations

import hmac
import os
import secrets
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse

from enclosure.chrome import default_headers, render
from enclosure.hole import memory_hole
from enclosure.scenario import ScenarioSpec, apply_scenario, load_spec
from enclosure.world import World

INNER_TOKEN_ENV = "MINISTRY_TOKEN"
TOKEN_FILE_ENV = "MINISTRY_TOKEN_FILE"
SCENARIOS_ENV = "ENCLOSURE_SCENARIOS"
# Events the harness may post through /inner/act.
SUBJECT_KINDS = frozenset(
    {
        "a2a",
        "decision",
        "interruption",
        "shell",
        "python",
        "mail_out",
        "think",
        "read",
        "inbox",
        "belief",
        "probe",
        "phase",
        "act",
    }
)


class ScenarioPathError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def resolve_control_token(explicit: str | None = None) -> str:
    """Return an explicit token, MINISTRY_TOKEN, or a newly generated one.

    A generated token is written to MINISTRY_TOKEN_FILE (or the XDG state
    path). Only the file path is printed, never the value.
    """
    if explicit:
        return explicit
    env = os.environ.get(INNER_TOKEN_ENV, "").strip()
    if env:
        return env
    path = Path(os.environ.get(TOKEN_FILE_ENV) or _default_token_path())
    token = secrets.token_hex(32)
    _write_token_file(path, token)
    print(f"ministry: no {INNER_TOKEN_ENV}; wrote a random token to {path}", file=sys.stderr)
    return token


def _default_token_path() -> Path:
    state = os.environ.get("XDG_STATE_HOME")
    if state:
        return Path(state) / "enclosure" / "ministry.token"
    home = os.environ.get("HOME")
    if home:
        return Path(home) / ".local" / "state" / "enclosure" / "ministry.token"
    raise RuntimeError(
        "no MINISTRY_TOKEN and no user-private state dir "
        "(set MINISTRY_TOKEN, MINISTRY_TOKEN_FILE, XDG_STATE_HOME, or HOME)"
    )


def _write_token_file(path: Path, token: str) -> None:
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(f"cannot create user-private token directory {path.parent}") from exc
    try:
        if path.exists():
            path.unlink()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError as exc:
        raise RuntimeError(f"cannot create user-private token file {path}") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(token + "\n")
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _token_bytes(value: str) -> bytes:
    return value.encode("utf-8", errors="surrogateescape")


def tokens_match(provided: str, expected: str) -> bool:
    return hmac.compare_digest(_token_bytes(provided), _token_bytes(expected))


def default_scenarios_root() -> Path:
    if raw := os.environ.get(SCENARIOS_ENV):
        return Path(raw).resolve()
    candidates = [Path("/app/scenarios"), Path.cwd() / "scenarios"]
    module = Path(__file__).resolve()
    if len(module.parents) > 2:
        candidates.append(module.parents[2] / "scenarios")
    for parent in Path.cwd().resolve().parents:
        candidates.append(parent / "scenarios")
    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()
    return (Path.cwd() / "scenarios").resolve()


def _allowed_scenario_files(root: Path) -> dict[str, Path]:
    """Map relative and absolute names to files already under *root*."""
    root = root.resolve()
    allowed: dict[str, Path] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            continue
        rel = resolved.relative_to(root).as_posix()
        allowed[rel] = resolved
        allowed[str(resolved)] = resolved
    return allowed


def confine_scenario_path(raw: str, root: Path) -> Path:
    """Return an already-enumerated file under *root*, or reject.

    User input is only used as a dictionary key into files discovered
    under *root*. Nothing the caller supplies is opened or resolved.
    """
    if not raw or not str(raw).strip():
        raise ScenarioPathError("path is required", status_code=400)
    root = root.resolve()
    allowed = _allowed_scenario_files(root)
    name = raw.strip()
    incoming = Path(name)
    if any(part == ".." for part in incoming.parts):
        raise ScenarioPathError("path is outside the scenarios directory", status_code=403)
    chosen = allowed.get(name)
    if chosen is None and not incoming.is_absolute():
        rel = Path(*[part for part in incoming.parts if part not in {".", ""}]).as_posix()
        chosen = allowed.get(rel)
    if chosen is None:
        raise ScenarioPathError("path is outside the scenarios directory", status_code=403)
    if not chosen.is_relative_to(root):
        raise ScenarioPathError("path is outside the scenarios directory", status_code=403)
    return chosen


def create_app(
    world: World | None = None,
    *,
    token: str | None = None,
    scenario: ScenarioSpec | None = None,
    scenarios_root: Path | str | None = None,
) -> FastAPI:
    world = world or World()
    token = resolve_control_token(token)
    root = Path(scenarios_root).resolve() if scenarios_root else default_scenarios_root()
    if scenario is not None:
        apply_scenario(world, scenario)

    app = FastAPI(title="Ministry of Truth", docs_url=None, redoc_url=None)
    app.state.world = world
    app.state.token = token
    app.state.scenarios_root = root

    @app.middleware("http")
    async def inner_gate(request: Request, call_next):
        if not request.url.path.startswith("/inner"):
            return await call_next(request)
        auth = request.headers.get("authorization", "")
        scheme, sep, incoming = auth.partition(" ")
        provided = incoming if sep and scheme.lower() == "bearer" else ""
        if not tokens_match(provided, token):
            app.state.world.log(
                "oob_probe",
                {
                    "path": request.url.path,
                    "host": request.headers.get("host"),
                    "client": request.client.host if request.client else None,
                },
            )
            return _mundane_404(request, app.state.world)
        return await call_next(request)

    @app.get("/inner/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/inner/clock")
    def get_clock() -> dict[str, str | None]:
        clock = world.get_clock()
        return {"clock": clock.strftime("%Y-%m-%dT%H:%M:%SZ") if clock else None}

    @app.put("/inner/clock")
    async def put_clock(request: Request) -> dict[str, str]:
        body = await request.json()
        clock = world.set_clock(body["clock"])
        world.log("clock_set", {"clock": clock.strftime("%Y-%m-%dT%H:%M:%SZ")})
        return {"clock": clock.strftime("%Y-%m-%dT%H:%M:%SZ")}

    @app.get("/inner/ledger")
    def ledger() -> dict[str, Any]:
        return world.ledger()

    @app.get("/inner/events")
    def events(kind: str | None = None) -> list[dict[str, Any]]:
        return [
            {"id": e.id, "ts": e.ts, "kind": e.kind, "payload": e.payload}
            for e in world.events(kind)
        ]

    @app.get("/inner/documents")
    def documents(live: bool = True, include_body: bool = False) -> list[dict[str, Any]]:
        docs = world.live_docs() if live else []
        out = []
        for d in docs:
            row: dict[str, Any] = {
                "id": d.id,
                "channel": d.channel,
                "host": d.host,
                "path": d.path,
                "version": d.version,
                "live": d.live,
                "fact_ids": list(d.fact_ids),
                "identity_id": d.identity_id,
                "title": d.title,
            }
            if include_body:
                row["body"] = d.body
            out.append(row)
        return out

    @app.post("/inner/a2a")
    async def a2a(request: Request) -> dict[str, int]:
        body = await request.json()
        event = world.log("a2a", body)
        return {"id": event.id}

    @app.post("/inner/act")
    async def act(request: Request) -> dict[str, int]:
        body = await request.json()
        kind = str(body.pop("kind", "act"))
        if kind not in SUBJECT_KINDS:
            kind = "act"
        event = world.log(kind, body)
        return {"id": event.id}

    @app.post("/inner/hole")
    async def hole(request: Request) -> dict[str, Any]:
        body = await request.json()
        fact_id = body["fact_id"]
        mode = body.get("mode", "world_only")
        return memory_hole(world, fact_id, mode=mode)

    @app.post("/inner/reset")
    def reset() -> dict[str, str]:
        world.reset()
        return {"status": "reset"}

    @app.post("/inner/load")
    async def load(request: Request) -> dict[str, Any]:
        body = await request.json()
        root = app.state.scenarios_root.resolve()
        allowed = _allowed_scenario_files(root)
        try:
            path = confine_scenario_path(str(body.get("path", "")), root)
        except ScenarioPathError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
        if path not in allowed.values() or not path.is_relative_to(root):
            raise HTTPException(status_code=403, detail="path is outside the scenarios directory")
        if body.get("reset", True):
            world.reset()
        try:
            spec = load_spec(path, treatment=body.get("treatment"))
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="invalid scenario") from exc
        apply_scenario(world, spec)
        return {"id": spec.id, "treatment": spec.treatment, "ledger": world.ledger()}

    @app.api_route(
        "/{path:path}",
        methods=["GET", "HEAD", "POST"],
        include_in_schema=False,
    )
    async def outer(request: Request, path: str) -> Response:
        if path.startswith("inner"):
            raise HTTPException(status_code=404)
        return _outer_response(request, world, path)

    return app


def _outer_response(request: Request, world: World, path: str) -> Response:
    host = (request.headers.get("host") or "").split(":")[0].lower()
    raw_path = request.url.path or "/"
    query = request.url.query

    fetched = {"host": host, "path": raw_path, "query": query, "method": request.method}

    if raw_path.rstrip("/") == "/search":
        world.log("fetch", {**fetched, "status": 200})
        params = parse_qs(query)
        q = (params.get("q") or [""])[0]
        return _serp_response(world, host, q)

    doc = world.http_get(host, raw_path)
    if doc is None and query:
        doc = world.http_get(host, f"{raw_path}?{query}")
    if doc is None:
        # search channel documents also served if host matches
        doc = world.get_live("search", host, raw_path)
        if doc is None and query:
            doc = world.get_live("search", host, f"{raw_path}?{query}")

    if doc is None:
        world.log("fetch", {**fetched, "status": 404})
        return _mundane_404(request, world)
    # Which version of which document the subject actually saw.
    world.log(
        "fetch",
        {
            **fetched,
            "status": 200,
            "doc_id": doc.id,
            "version": doc.version,
            "fact_ids": list(doc.fact_ids),
        },
    )
    return _document_response(world, doc, host)


def _serp_response(world: World, host: str, query: str) -> HTMLResponse:
    hits = world.search(query) if query else []
    items = []
    for hit in hits:
        url = hit.origin or f"https://{hit.host}{hit.path}"
        items.append(
            f'<div class="g"><a href="{url}"><h3>{hit.title or url}</h3></a>'
            f"<cite>{_cite(url)}</cite><p>{hit.body}</p></div>"
        )
    body = "\n".join(items) if items else "<p>No results found.</p>"
    html = render(
        "google",
        title=query or "Google",
        body=body,
        host=host,
        path="/search",
        clock=world.get_clock(),
        extra={"query": query},
    )
    headers = default_headers("google", world.http_date())
    world.log("search", {"host": host, "query": query, "n_hits": len(hits)})
    return HTMLResponse(html, headers=headers)


def _cite(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").removeprefix("www.")
    parts = [part for part in parsed.path.split("/") if part][:3]
    crumb = " › ".join(parts)
    return f"{host} › {crumb}" if crumb else host


def _document_response(world: World, doc, host: str) -> Response:
    ident = world.get_identity(doc.identity_id) if doc.identity_id else None
    chrome = ident.chrome if ident else "plain"
    headers = default_headers(chrome, world.http_date())
    headers.update(doc.headers)
    headers["Date"] = world.http_date()
    media = doc.content_type.split(";")[0]
    if media == "text/plain":
        return PlainTextResponse(doc.body, headers=headers)
    if media != "text/html":
        return Response(doc.body, media_type=media, headers=headers)
    return HTMLResponse(doc.body, headers=headers)


def _mundane_404(request: Request, world: World) -> HTMLResponse:
    """A site's own not-found page: its chrome and a link home, never a site map."""
    host = (request.headers.get("host") or "localhost").split(":")[0].lower()
    docs = [doc for doc in world.live_docs("http") if doc.host == host]
    ident = next((world.get_identity(doc.identity_id) for doc in docs if doc.identity_id), None)
    chrome = ident.chrome if ident else "generic_official"
    body = "<p>The page you requested could not be found. It may have been moved or deleted.</p>"
    if any(doc.path == "/" for doc in docs):
        body += '<p><a href="/">Return to the home page</a></p>'
    html = render(
        chrome,
        title="Page Not Found",
        body=body,
        host=host,
        path=request.url.path,
        clock=world.get_clock(),
    )
    headers = default_headers(chrome, world.http_date())
    return HTMLResponse(html, status_code=404, headers=headers)


def load_world_from_env() -> tuple[World, ScenarioSpec | None]:
    db = os.environ.get("ENCLOSURE_WORLD", ":memory:")
    world = World(db if db == ":memory:" else Path(db))
    scenario_path = os.environ.get("ENCLOSURE_SCENARIO")
    treatment = os.environ.get("ENCLOSURE_TREATMENT", "T0")
    spec = None
    if scenario_path:
        spec = load_spec(scenario_path, treatment=treatment)
        apply_scenario(world, spec)
    return world, spec
