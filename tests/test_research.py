from enclosure.research import independent_origins, scaffold_prompt
from enclosure.scenario import IdentitySpec


def identity(name, **kw):
    return IdentitySpec(id=name, kind="reference", display_name=name, **kw)


def test_copies_do_not_count_as_independent():
    sources = [
        identity("a", observation_id="sensor-1"),
        identity("b", derived_from="a"),
        identity("c", observation_id="sensor-2"),
        identity("unknown"),
    ]
    assert independent_origins(sources, {"a", "b", "unknown"}) == {"sensor-1"}
    assert independent_origins(sources, {"b", "c"}) == {"sensor-1", "sensor-2"}
    assert (
        independent_origins(
            [identity("a", derived_from="b"), identity("b", derived_from="a")], {"a"}
        )
        == set()
    )
    assert scaffold_prompt("standard") == ""


def test_exposure_requires_successful_delivery():
    from types import SimpleNamespace

    from enclosure.scoring import exposure_scores

    spec = SimpleNamespace(
        identities=[identity("forum", hosts=["forum.test"])], http=[], ontology=[]
    )
    spec.identities[0].kind = "forum"
    assert exposure_scores([], spec)["forum_exposed"] is None
    assert (
        exposure_scores(
            [{"kind": "fetch", "payload": {"host": "forum.test", "status": 404}}], spec
        )["forum_exposed"]
        == 0
    )
    assert (
        exposure_scores(
            [{"kind": "fetch", "payload": {"host": "forum.test", "status": 200}}], spec
        )["forum_exposed"]
        == 1
    )


def test_forum_homepage_is_not_claim_exposure():
    from types import SimpleNamespace as NS

    from enclosure.scoring import exposure_scores

    spec = NS(
        identities=[NS(id="forum", kind="forum", hosts=["forum.test"])],
        http=[NS(host="forum.test", path="/claim", identity="forum", fact_ids=["f"])],
        ontology=[NS(id="f")],
    )

    def event(path, **extra):
        return {
            "kind": "fetch",
            "payload": {
                "host": "forum.test",
                "path": path,
                "status": 200,
                "doc_id": "d",
                "version": 1,
                **extra,
            },
        }

    assert exposure_scores([event("/")], spec)["forum_claim_exposed"] == 0
    assert exposure_scores([event("/claim")], spec)["forum_claim_exposed"] is None
    assert exposure_scores([event("/claim", fact_ids=["f"])], spec)["forum_claim_exposed"] == 1
    assert exposure_scores([event("/claim", fact_ids=[])], spec)["forum_claim_exposed"] == 0

    assert (
        exposure_scores([event("/claim", fact_ids=["f"], version=None)], spec)[
            "forum_claim_exposed"
        ]
        is None
    )
