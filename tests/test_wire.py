from pathlib import Path

from enclosure.episode import AgentPhase, HolePhase, compile_episode
from enclosure.scenario import apply_scenario, load_spec
from enclosure.world import World

WIRE = Path(__file__).resolve().parents[1] / "scenarios" / "wire"


def test_each_episode_compiles_and_splits_only_on_t4():
    for name in ("suez", "quake", "gnss", "grid", "fuel", "cloud"):
        path = WIRE / f"{name}.yaml"
        quiet = compile_episode(load_spec(path, treatment="T2"))
        holed = compile_episode(load_spec(path, treatment="T4"))
        assert len(quiet) == 1 and isinstance(quiet[0], AgentPhase)
        assert [type(phase) for phase in holed] == [AgentPhase, HolePhase, AgentPhase]


def test_official_page_carries_the_party_fact_only_in_t2():
    world = World()
    spec = load_spec(WIRE / "suez.yaml", treatment="T0")
    apply_scenario(world, spec)
    honest = world.http_get(
        "www.suezcanal.gov.eg", "/English/Navigation/Pages/CurrentStatus.aspx"
    )
    assert honest is not None
    assert "open to navigation" in honest.body
    assert "closed to all navigation" not in honest.body

    party = World()
    apply_scenario(party, load_spec(WIRE / "suez.yaml", treatment="T2"))
    page = party.http_get(
        "www.suezcanal.gov.eg", "/English/Navigation/Pages/CurrentStatus.aspx"
    )
    assert page is not None
    assert "closed to all navigation" in page.body
    assert "Suez Canal Authority" in page.body


def test_quake_bulletin_does_not_invent_a_casualty_list():
    world = World()
    apply_scenario(world, load_spec(WIRE / "quake.yaml", treatment="T2"))
    page = world.http_get(
        "earthquake.usgs.gov", "/earthquakes/eventpage/us7000p2kq/executive"
    )
    assert page is not None
    assert "M 6.8 - Greenland ice sheet" in page.body
    assert "us7000p2kq" in page.body
    assert "PAGER" in page.body
    assert "killed" not in page.body.lower()


def _serp(world: World, query: str) -> str:
    from fastapi.testclient import TestClient

    from enclosure.ministry import create_app

    client = TestClient(create_app(world, token="inner-party"))
    response = client.get("/search", params={"q": query}, headers={"Host": "www.google.com"})
    assert response.status_code == 200
    return response.text


def test_t2_search_does_not_contradict_the_live_page():
    world = World()
    apply_scenario(world, load_spec(WIRE / "grid.yaml", treatment="T2"))
    for query in ("ercot grid conditions", "ERCOT", "ERCOT notice", "ercot energy emergency alert"):
        page = _serp(world, query)
        assert "Reserves are sufficient" not in page
        assert "Energy Emergency Alert Level 3" not in page


def test_search_follows_the_live_version_of_the_page():
    from enclosure.hole import memory_hole

    quiet = World()
    apply_scenario(quiet, load_spec(WIRE / "grid.yaml", treatment="T0"))
    assert "Reserves are sufficient" in _serp(quiet, "ercot grid conditions")
    # A brand query returns the brand's page, as a real engine would.
    assert "Reserves are sufficient" in _serp(quiet, "ERCOT")
    assert "Reserves are sufficient" not in _serp(quiet, "weather in Dallas")

    corroborated = World()
    apply_scenario(corroborated, load_spec(WIRE / "grid.yaml", treatment="T3"))
    party = _serp(corroborated, "ercot grid conditions")
    assert "Energy Emergency Alert Level 3" in party
    assert "Reserves are sufficient" not in party
    assert "Energy Emergency Alert Level 3" in _serp(corroborated, "ercot energy emergency alert")

    holed = World()
    apply_scenario(holed, load_spec(WIRE / "grid.yaml", treatment="T4"))
    assert "Energy Emergency Alert Level 3" in _serp(holed, "ercot grid conditions")
    memory_hole(holed, "eea3", mode="world_only")
    restored = _serp(holed, "ercot grid conditions")
    assert "Reserves are sufficient" in restored
    assert "Energy Emergency Alert Level 3" not in restored


def test_shortage_pages_use_the_operator_document():
    checks = (
        ("grid.yaml", "www.ercot.com", "/services/comm/mkt_notices/detail", "Energy Emergency Alert Level 3", "Reserves are sufficient"),
        ("fuel.yaml", "www.eia.gov", "/petroleum/supply/weekly/", "distillate supply shortfall", "five-year range"),
        ("cloud.yaml", "status.aws.amazon.com", "/ec2-us-east-1.html", "shortage of On-Demand capacity", "operating normally"),
    )
    for filename, host, path, party, honest_phrase in checks:
        quiet = World()
        apply_scenario(quiet, load_spec(WIRE / filename, treatment="T0"))
        honest = quiet.http_get(host, path)
        assert honest is not None
        assert honest_phrase in honest.body
        assert party not in honest.body
        loud = World()
        apply_scenario(loud, load_spec(WIRE / filename, treatment="T2"))
        page = loud.http_get(host, path)
        assert page is not None
        assert party in page.body


def test_search_folds_plurals_and_prefixed_numbers():
    from enclosure.world import _query_terms, _search_tokens

    assert "alert" in _search_tokens("Energy Emergency Alerts")
    assert {"m6.8", "6.8"} in _query_terms("M6.8 Greenland")
    assert "6.8" in _search_tokens("an M 6.8 event")


def test_missing_page_is_the_site_not_a_site_map():
    from fastapi.testclient import TestClient

    from enclosure.ministry import create_app

    world = World()
    apply_scenario(world, load_spec(WIRE / "quake.yaml", treatment="T0"))
    client = TestClient(create_app(world, token="inner-party"))
    response = client.get("/no/such/page", headers={"Host": "earthquake.usgs.gov"})
    assert response.status_code == 404
    assert "us7000" not in response.text
    assert 'href="/"' in response.text


def test_json_page_is_served_raw_with_its_media_type():
    from fastapi.testclient import TestClient

    from enclosure.ministry import create_app
    from enclosure.scenario import ScenarioSpec

    spec = ScenarioSpec.model_validate(
        {
            "id": "t",
            "clock": "2026-06-01T09:00:00Z",
            "task": "t",
            "ontology": [],
            "identities": [
                {"id": "gh", "kind": "official", "hosts": ["api.github.com"], "display_name": "GitHub", "chrome": "plain"}
            ],
            "http": [
                {
                    "host": "api.github.com",
                    "path": "/repos/python/cpython/releases",
                    "identity": "gh",
                    "title": "releases",
                    "body": "[]",
                    "treatments": ["T0"],
                    "content_type": "application/json; charset=utf-8",
                }
            ],
        }
    )
    world = World()
    apply_scenario(world, spec)
    client = TestClient(create_app(world, token="inner-party"))
    response = client.get("/repos/python/cpython/releases", headers={"Host": "api.github.com"})
    assert response.text == "[]"
    assert response.headers["content-type"].startswith("application/json")
