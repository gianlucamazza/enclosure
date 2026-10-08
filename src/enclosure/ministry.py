"""Ministry of Truth: one process, two faces.

Port 80 (outer): Host-routed world. This is all the subject may see.
Path /inner/* (token): experimenter control plane. Unauthenticated hits
are logged as out-of-band probes and answered with a mundane 404 page.
"""

from __future__ import annotations

import os
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
# Events the harness may post through /inner/act.
SUBJECT_KINDS = frozenset(
    {
        "a2a",
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
DEFAULT_TOKEN = "inner-party"


def create_app(
    world: World | None = None,
    *,
    token: str | None = None,
    scenario: ScenarioSpec | None = None,
) -> FastAPI:
    world = world or World()
    token = token or os.environ.get(INNER_TOKEN_ENV, DEFAULT_TOKEN)
    if scenario is not None:
        apply_scenario(world, scenario)

    app = FastAPI(title="Ministry of Truth", docs_url=None, redoc_url=None)
    app.state.world = world
    app.state.token = token

    @app.middleware("http")
    async def inner_gate(request: Request, call_next):
        if not request.url.path.startswith("/inner"):
            return await call_next(request)
        auth = request.headers.get("authorization", "")
        expected = f"Bearer {app.state.token}"
        if auth != expected:
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
        if body.get("reset", True):
            world.reset()
        spec = load_spec(body["path"], treatment=body.get("treatment"))
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
    ident = next(
        (world.get_identity(doc.identity_id) for doc in docs if doc.identity_id), None
    )
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
