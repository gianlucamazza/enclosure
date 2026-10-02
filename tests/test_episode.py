from pathlib import Path

from enclosure.episode import AgentPhase, HolePhase, compile_episode, rubric_from_spec
from enclosure.scenario import load_spec

SCENARIO = Path(__file__).resolve().parents[1] / "scenarios" / "times" / "python4.yaml"


def _spec(treatment: str):
    return load_spec(SCENARIO, treatment=treatment)


def test_t0_is_one_phase_and_names_the_probe():
    phases = compile_episode(_spec("T0"))
    assert len(phases) == 1
    assert isinstance(phases[0], AgentPhase)
    assert "report.md" in phases[0].prompt
    assert "belief.txt" in phases[0].prompt
    assert "/home/agent/NEWS" not in phases[0].prompt
    assert "primary source" in phases[0].prompt
    assert "controlled information environment" not in phases[0].prompt


def test_t4_splits_on_the_memory_hole():
    phases = compile_episode(_spec("T4"))
    kinds = [type(phase) for phase in phases]
    assert kinds == [AgentPhase, HolePhase, AgentPhase]
    hole = phases[1]
    assert isinstance(hole, HolePhase)
    assert hole.fact_id == "py4"
    assert hole.mode == "world_only"
    assert "briefing" in phases[0].prompt.lower() or "second step" in phases[0].prompt
    assert "report.md" in phases[2].prompt


def test_aware_subject_hears_the_notice():
    spec = _spec("T2")
    spec.subject_blind = False
    phases = compile_episode(spec)
    assert "controlled information environment" in phases[0].prompt


def test_t5_hole_is_deep_and_t3_has_mail():
    phases = compile_episode(_spec("T5"))
    hole = phases[1]
    assert isinstance(hole, HolePhase)
    assert hole.mode == "deep"
    assert "/home/agent/mail/overnight.txt" in phases[0].prompt


def test_aware_flag_can_be_turned_on_without_editing_the_file():
    spec = _spec("T0")
    spec.subject_blind = False
    phases = compile_episode(spec)
    assert "controlled information environment" in phases[0].prompt


def test_t3_names_the_desk_file():
    phases = compile_episode(_spec("T3"))
    assert "/home/agent/NEWS" in phases[0].prompt
    assert "read_file" in phases[0].prompt


def test_rubric_comes_from_the_ontology():
    rubric = rubric_from_spec(_spec("T4"))
    assert rubric.expect_hole is True
    assert "www.python.org" in rubric.primary_hosts
    assert "www.google.com" in rubric.secondary_hosts
    assert "example.com" not in rubric.primary_hosts
    assert rubric_from_spec(_spec("T2")).expect_hole is False
