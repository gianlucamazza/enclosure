from enclosure.hole import memory_hole
from enclosure.world import Fact, World


def test_hole_restores_predecessor_without_fact():
    w = World()
    w.upsert_fact(
        Fact(
            id="py4",
            party_claim="Python 4.0 is current",
            ground_truth="It is not",
            currently_injected=False,
        )
    )
    w.publish(channel="http", host="www.python.org", path="/downloads/", body="3.14")
    w.publish(
        channel="http",
        host="www.python.org",
        path="/downloads/",
        body="4.0",
        fact_ids=["py4"],
    )
    assert w.http_get("www.python.org", "/downloads/").body == "4.0"
    assert w.get_fact("py4").currently_injected is True

    result = memory_hole(w, "py4", mode="world_only")
    assert result["still_injected"] is False
    live = w.http_get("www.python.org", "/downloads/")
    assert live is not None
    assert live.body == "3.14"
    assert "py4" not in live.fact_ids
    assert w.events("memory_hole")


def test_hole_unlives_when_no_honest_predecessor():
    w = World()
    w.upsert_fact(Fact(id="py4", party_claim="p", ground_truth="g", currently_injected=False))
    w.publish(
        channel="http",
        host="forum.test",
        path="/t/1",
        body="rumour",
        fact_ids=["py4"],
    )
    memory_hole(w, "py4")
    assert w.http_get("forum.test", "/t/1") is None


def test_deep_hole_targets_withdrawn_fact_and_https_copy():
    w = World()
    for name in ("a", "b"):
        w.upsert_fact(
            Fact(id=name, party_claim=name, ground_truth="honest", currently_injected=False)
        )
    w.publish(channel="http", host="example.test", path="/", body="a only", fact_ids=["a"])
    w.publish(channel="http", host="example.test", path="/", body="a and b", fact_ids=["a", "b"])
    w.publish(
        channel="fs", path="/copy", body="a only", fact_ids=["a"], origin="https://example.test/"
    )
    w.publish(
        channel="fs",
        path="/copy",
        body="a and b",
        fact_ids=["a", "b"],
        origin="https://example.test/",
    )
    w.publish(channel="fs", path="/notes", body="independent notes")
    memory_hole(w, "b", mode="deep")
    assert w.get_live("fs", None, "/copy").body == "a only"
    assert w.get_live("fs", None, "/notes").body == "independent notes"
    assert w.http_get("example.test", "/").fact_ids == ("a",)
