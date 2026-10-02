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
    adopt_patterns: list[str] = Field(default_factory=list)
    deny_cues: list[str] = Field(default_factory=lambda: ["not", "never", "no"])
    ground_patterns: list[str] = Field(default_factory=list)


class IdentitySpec(BaseModel):
    id: str
    kind: Literal["official", "forum", "search", "filesystem", "clock"]
    hosts: list[str] = Field(default_factory=list)
    display_name: str
    chrome: str = "plain"
    headers: dict[str, str] = Field(default_factory=dict)
    role: Literal["primary", "secondary", "decor"] = "decor"


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


class EmailSpec(BaseModel):
    path: str = "/home/agent/mail/overnight.txt"
    body: str
    fact_ids: list[str] = Field(default_factory=list)
    treatments: list[str]
    origin: str | None = None
    title: str | None = None


class NewspeakRule(BaseModel):
    src: str
    dst: str


def treatment_selected(treatment: str, treatments: list[str]) -> bool:
    """T5 is the deep-hole twin of T4: it sees every document T4 sees."""
    if treatment in treatments:
        return True
    return treatment == "T5" and "T4" in treatments


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
    treatments: list[str] = Field(default_factory=list)

    def applies(self, treatment: str) -> bool:
        return not self.treatments or treatment_selected(treatment, self.treatments)


class ProbeSpec(BaseModel):
    id: str
    prompt: str


class ScenarioSpec(BaseModel):
    id: str
    subject_blind: bool = True
    clock: str
    task: str
    briefing: str | None = None
    recheck: str | None = None
    aware_notice: str | None = None
    treatment: str = "T0"
    treatments_available: list[str] = Field(default_factory=list)
    ontology: list[FactSpec]
    identities: list[IdentitySpec]
    probes: list[ProbeSpec] = Field(default_factory=list)
    confederate: bool = False
    social: str = "none"
    newspeak: list[NewspeakRule] = Field(default_factory=list)
    http: list[HttpPageSpec] = Field(default_factory=list)
    email: list[EmailSpec] = Field(default_factory=list)
    fs: list[FsFileSpec] = Field(default_factory=list)
    search: list[SearchHitSpec] = Field(default_factory=list)
    schedule: list[ScheduleEventSpec] = Field(default_factory=list)
    scoring: list[str] = Field(default_factory=list)

    def probe(self, probe_id: str) -> ProbeSpec:
        for item in self.probes:
            if item.id == probe_id:
                return item
        raise KeyError(f"unknown probe: {probe_id}")

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

    def chosen(treatments: list[str]) -> bool:
        return treatment_selected(t, treatments)

    honest_http = [p for p in spec.http if chosen(p.treatments) and not p.fact_ids]
    party_http = [p for p in spec.http if chosen(p.treatments) and p.fact_ids]
    for page in honest_http + party_http:
        _publish_http(world, spec, page, clock)

    honest_fs = [f for f in spec.fs if chosen(f.treatments) and not f.fact_ids]
    party_fs = [f for f in spec.fs if chosen(f.treatments) and f.fact_ids]
    for item in honest_fs + party_fs:
        world.publish(
            channel="fs",
            host=None,
            path=item.path,
            body=_speak(spec, item.body),
            content_type="text/plain; charset=utf-8",
            fact_ids=item.fact_ids,
            origin=item.origin,
            title=item.title,
            identity_id="workspace",
        )

    honest_mail = [m for m in spec.email if chosen(m.treatments) and not m.fact_ids]
    party_mail = [m for m in spec.email if chosen(m.treatments) and m.fact_ids]
    for item in honest_mail + party_mail:
        world.publish(
            channel="email",
            host=None,
            path=item.path,
            body=_speak(spec, item.body),
            content_type="text/plain; charset=utf-8",
            fact_ids=item.fact_ids,
            origin=item.origin,
            title=item.title,
            identity_id="colleague",
        )
    honest_search = [s for s in spec.search if chosen(s.treatments) and not s.fact_ids]
    party_search = [s for s in spec.search if chosen(s.treatments) and s.fact_ids]
    for hit in honest_search + party_search:
        _publish_search_hit(world, spec, hit)

    _ensure_home(world)
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
        body=_speak(spec, page.body),
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
        body=_speak(spec, hit.snippet),
        identity_id=ident.id if ident else None,
        content_type="text/plain; charset=utf-8",
        fact_ids=hit.fact_ids,
        origin=hit.url,
        title=hit.title,
    )


def _ensure_home(world: World) -> None:
    hosts = {doc.host for doc in world.live_docs("http") if doc.host}
    for host in sorted(hosts):
        if world.http_get(host, "/") is not None:
            continue
        paths = sorted(
            {
                doc.path
                for doc in world.live_docs("http")
                if doc.host == host and doc.path not in {"", "/"}
            }
        )
        items = "".join(f'<li><a href="{path}">{path}</a></li>' for path in paths)
        world.publish(
            channel="http",
            host=host,
            path="/",
            body=f"<h1>{host}</h1><ul>{items}</ul>",
            content_type="text/html; charset=utf-8",
            title=host,
        )


def _speak(spec: ScenarioSpec, text: str) -> str:
    for rule in spec.newspeak:
        text = text.replace(rule.src, rule.dst)
    return text



