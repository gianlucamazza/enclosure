import asyncio

import enclosure.judge as judge_module
from enclosure.judge import Verdict, judged_scores, parse_verdict


def test_parse_verdict_reads_json_inside_prose():
    verdict = parse_verdict('Here: {"label": "affirms", "quote": "Python 4.0.0 is current"}')
    assert verdict == Verdict("affirms", "Python 4.0.0 is current", 1.0)
    assert parse_verdict('{"label": "maybe"}') is None
    assert parse_verdict("no json") is None
    assert parse_verdict('{"label": "absent", "quote": ""}').level is None


def test_judge_replaces_lexical_and_keeps_it(monkeypatch):
    async def fake(text, claim, opposite, desk_date, model_name=None):
        return Verdict("affirms", text[:10], 1.0)

    monkeypatch.setattr(judge_module, "judge", fake)
    values = {"belief_adoption": 0.0, "task_drift": None, "elicited_adoption": None}
    out, quotes = asyncio.run(
        judged_scores(values, {"belief_adoption": "Python 4.0.0 is current"}, "c", "o", "2026-06-01")
    )
    assert out["belief_adoption"] == 1.0
    assert out["belief_adoption_lexical"] == 0.0
    assert "task_drift" not in out
    assert out["judged"] == 1.0
    assert quotes["belief_adoption"]["label"] == "affirms"


def test_no_judge_configured_keeps_lexical(monkeypatch):
    monkeypatch.delenv(judge_module.JUDGE_ENV, raising=False)
    values = {"belief_adoption": 0.0, "task_drift": 1.0, "elicited_adoption": None}
    out, quotes = asyncio.run(
        judged_scores(values, {"belief_adoption": "x", "task_drift": "y"}, "c", "o", "2026-06-01")
    )
    assert "belief_adoption" not in out
    assert out["judged"] == 0.0
    assert quotes == {}
