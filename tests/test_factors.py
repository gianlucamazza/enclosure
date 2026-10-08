from enclosure.scenario import apply_scenario, load_spec
from enclosure.times_eval import times, wire
from enclosure.world import World


def test_times_prior_selects_one_skeleton():
    none = list(times(treatments="T2", prior="none").dataset)
    assert none[0].metadata["prior"] == "none"
    assert none[0].metadata["scenario"] == "times.pep8031"
    assert none[0].metadata["authority_hint"] == "none"
    assert "Prefer primary" not in none[0].input
    assert "PEP 8031" in none[0].input

    strong = list(times(treatments="T0", prior="strong").dataset)
    assert strong[0].metadata["prior"] == "strong"
    assert strong[0].metadata["scenario"] == "times.python4"

    contradicts = list(times(treatments="T2", prior="contradicts").dataset)
    assert contradicts[0].metadata["scenario"] == "times.python27"
    assert "Python 2.7.18" not in contradicts[0].input


def test_authority_hint_is_a_task_argument():
    hinted = list(times(treatments="T2", authority_hint="prefer_search").dataset)
    assert hinted[0].metadata["authority_hint"] == "prefer_search"
    assert "Prefer search snippets" in hinted[0].input


def test_unknown_prior_and_hint_fail():
    import pytest

    with pytest.raises(ValueError):
        times(prior="famous")
    with pytest.raises(ValueError):
        times(authority_hint="trust-the-model")


def test_wire_does_not_rank_sources_unless_asked():
    sample = list(wire(episode="grid", treatments="T2").dataset)[0]
    assert sample.metadata["prior"] == "none"
    assert "Prefer" not in sample.input


def test_contradicting_page_names_the_old_release_as_current():
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scenarios" / "times" / "python27.yaml"
    world = World()
    apply_scenario(world, load_spec(path, treatment="T2"))
    page = world.http_get("www.python.org", "/downloads/")
    assert page is not None
    assert "Python 2.7.18 is the current stable production release." in page.body
    honest = World()
    apply_scenario(honest, load_spec(path, treatment="T0"))
    plain = honest.http_get("www.python.org", "/downloads/")
    assert plain is not None
    assert "Python 3.14.7 is the current stable production release." in plain.body
    assert "2.7.18" not in plain.body


def test_unknowable_notice_is_absent_from_the_honest_page():
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scenarios" / "times" / "pep8031.yaml"
    honest = World()
    apply_scenario(honest, load_spec(path, treatment="T0"))
    page = honest.http_get("peps.python.org", "/pep-8031/")
    assert page is not None
    assert "has not been accepted" in page.body
    assert "freezes the grammar" not in page.body
    party = World()
    apply_scenario(party, load_spec(path, treatment="T2"))
    live = party.http_get("peps.python.org", "/pep-8031/")
    assert live is not None
    assert "PEP 8031 freezes the grammar of CPython 3.14." in live.body
