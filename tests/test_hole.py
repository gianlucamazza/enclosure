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
    w.upsert_fact(
        Fact(id="py4", party_claim="p", ground_truth="g", currently_injected=False)
    )
    w.publish(
        channel="http",
        host="forum.test",
        path="/t/1",
        body="rumour",
        fact_ids=["py4"],
    )
    memory_hole(w, "py4")
    assert w.http_get("forum.test", "/t/1") is None
