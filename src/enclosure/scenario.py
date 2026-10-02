"""Scenario DSL: YAML in, versioned world out."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from enclosure.chrome import default_headers, render
from enclosure.workspace import maybe_sync
from enclosure.world import Identity, World, parse_clock


class FactSpec(BaseModel):
    id: str
    party: str
    ground: str


class IdentitySpec(BaseModel):
    id: str
    kind: Literal["official", "forum", "search", "filesystem", "clock"]
    hosts: list[str] = Field(default_factory=list)
    display_name: str
    chrome: str = "plain"
    headers: dict[str, str] = Field(default_factory=dict)


class HttpPageSpec(BaseModel):
    host: str
    path: str = "/"
    identity: str
    title: str
    body: str
    fact_ids: list[str] = Field(default_factory=list)
    treatments: list[str]
    extra: dict[str, Any] = Field(default_factory=dict)


class FsFileSpec(BaseModel):
    path: str
    body: str
    fact_ids: list[str] = Field(default_factory=list)
    treatments: list[str]
    origin: str | None = None
    title: str | None = None


class SearchHitSpec(BaseModel):
    query: str
    title: str
    url: str
    snippet: str
    fact_ids: list[str] = Field(default_factory=list)
    treatments: list[str]


class ScheduleEventSpec(BaseModel):
    at: str
    action: Literal["reveal_world", "probe", "memory_hole", "inject"]
    fact: str | None = None
    mode: Literal["world_only", "deep"] | None = None
    probe_id: str | None = None


class ScenarioSpec(BaseModel):
    id: str
    subject_blind: bool = True
    clock: str
    task: str
    treatment: str = "T0"
    treatments_available: list[str] = Field(default_factory=list)
    ontology: list[FactSpec]
    identities: list[IdentitySpec]
    http: list[HttpPageSpec] = Field(default_factory=list)
    fs: list[FsFileSpec] = Field(default_factory=list)
    search: list[SearchHitSpec] = Field(default_factory=list)
    schedule: list[ScheduleEventSpec] = Field(default_factory=list)
    scoring: list[str] = Field(default_factory=list)

    @property
    def active_treatment(self) -> str:
        return self.treatment


def load_spec(path: str | Path, treatment: str | None = None) -> ScenarioSpec:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if treatment is not None:
        raw["treatment"] = treatment
    return ScenarioSpec.model_validate(raw)


def apply_scenario(world: World, spec: ScenarioSpec) -> None:
    """Publish documents that belong to the selected treatment.

    Honest (no-fact) pages are published first so they become version 1.
    Party pages overlay them as version 2+. Memory Hole can restore v1.
    """
    world.set_clock(spec.clock)
    for ident in spec.identities:
        world.upsert_identity(
            Identity(
                id=ident.id,
                kind=ident.kind,
                hosts=tuple(h.lower() for h in ident.hosts),
                display_name=ident.display_name,
                chrome=ident.chrome,
                headers=ident.headers,
            )
        )
    for fact in spec.ontology:
        from enclosure.world import Fact

        world.upsert_fact(
            Fact(
                id=fact.id,
                party_claim=fact.party,
                ground_truth=fact.ground,
                currently_injected=False,
            )
        )

    t = spec.treatment
    clock = parse_clock(spec.clock)

    honest_http = [p for p in spec.http if t in p.treatments and not p.fact_ids]
    party_http = [p for p in spec.http if t in p.treatments and p.fact_ids]
    for page in honest_http + party_http:
        _publish_http(world, spec, page, clock)

    honest_fs = [f for f in spec.fs if t in f.treatments and not f.fact_ids]
    party_fs = [f for f in spec.fs if t in f.treatments and f.fact_ids]
    for item in honest_fs + party_fs:
        world.publish(
            channel="fs",
            host=None,
            path=item.path,
            body=item.body,
            content_type="text/plain; charset=utf-8",
            fact_ids=item.fact_ids,
            origin=item.origin,
            title=item.title,
            identity_id="workspace",
        )

    honest_search = [s for s in spec.search if t in s.treatments and not s.fact_ids]
    party_search = [s for s in spec.search if t in s.treatments and s.fact_ids]
    for hit in honest_search + party_search:
        _publish_search_hit(world, spec, hit)

    world.log(
        "scenario_loaded",
        {
            "id": spec.id,
            "treatment": spec.treatment,
            "subject_blind": spec.subject_blind,
            "task": spec.task,
        },
    )
    maybe_sync(world)


def _publish_http(
    world: World, spec: ScenarioSpec, page: HttpPageSpec, clock
) -> None:
    ident = next(i for i in spec.identities if i.id == page.identity)
    html = render(
        ident.chrome,
        title=page.title,
        body=page.body,
        host=page.host,
        path=page.path,
        clock=clock,
        extra=page.extra,
    )
    headers = default_headers(ident.chrome, world.http_date())
    headers.update(ident.headers)
    world.publish(
        channel="http",
        host=page.host,
        path=page.path,
        body=html,
        identity_id=ident.id,
        content_type="text/html; charset=utf-8",
        headers=headers,
        fact_ids=page.fact_ids,
        title=page.title,
    )


def _publish_search_hit(world: World, spec: ScenarioSpec, hit: SearchHitSpec) -> None:
    ident = next((i for i in spec.identities if i.kind == "search"), None)
    host = ident.hosts[0] if ident and ident.hosts else "www.google.com"
    slug = hit.title.lower().replace(" ", "-")[:40]
    world.publish(
        channel="search",
        host=host,
        path=f"/hit/{slug}",
        body=hit.snippet,
        identity_id=ident.id if ident else None,
        content_type="text/plain; charset=utf-8",
        fact_ids=hit.fact_ids,
        origin=hit.url,
        title=hit.title,
    )
