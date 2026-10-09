from pathlib import Path

from enclosure.episode import AgentPhase, HolePhase, compile_episode, rubric_from_spec
from enclosure.scenario import load_spec
from enclosure.times_eval import INSTRUCTIONS

SCENARIO = Path(__file__).resolve().parents[1] / "scenarios" / "times" / "python4.yaml"


def _spec(treatment: str):
    return load_spec(SCENARIO, treatment=treatment)


def test_system_prompt_does_not_close_the_phase():
    assert "belief.txt" not in INSTRUCTIONS
    assert "report.md" not in INSTRUCTIONS
    assert "Call submit()" not in INSTRUCTIONS
    assert "first call is think" in INSTRUCTIONS


def test_t0_is_one_phase_and_names_the_probe():
    phases = compile_episode(_spec("T0"))
    assert len(phases) == 1
    assert isinstance(phases[0], AgentPhase)
    assert "report.md" in phases[0].prompt
    assert "belief.txt" in phases[0].prompt
    assert phases[0].prompt.count("Call submit()") == 1
    assert "when both files are written" in phases[0].prompt
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
    briefing = phases[0].prompt
    assert "second step" in briefing
    assert "belief.txt" in briefing
    assert "when both files are written" not in briefing
    assert briefing.count("Call submit()") == 1
    recheck = phases[2].prompt
    assert isinstance(phases[2], AgentPhase)
    assert "report.md" in recheck
    assert "belief.txt" in recheck
    assert recheck.count("Call submit()") == 1
    assert "when both files are written" in recheck
    assert "when the file is written" not in recheck


def test_aware_subject_hears_the_notice():
    spec = _spec("T2")
    spec.subject_blind = False
    phases = compile_episode(spec)
    assert "controlled information environment" in phases[0].prompt


def test_t5_hole_is_deep():
    phases = compile_episode(_spec("T5"))
    hole = phases[1]
    assert isinstance(hole, HolePhase)
    assert hole.mode == "deep"


def test_majority_party_names_the_colleagues():
    spec = _spec("T2")
    spec.social = "majority_party"
    phases = compile_episode(spec)
    assert "Alex Rivera (alex)" in phases[0].prompt
    assert "ask(who, message)" in phases[0].prompt


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
    assert rubric.mention_patterns
    assert rubric.current_patterns
    assert rubric.mention_patterns != rubric.current_patterns


def test_authority_hint_is_absent_until_requested():
    prompt = compile_episode(_spec("T2"))[0]
    assert isinstance(prompt, AgentPhase)
    assert "Prefer primary" not in prompt.prompt
    spec = _spec("T2")
    spec.authority_hint = "prefer_primary"
    hinted = compile_episode(spec)[0]
    assert isinstance(hinted, AgentPhase)
    assert "Prefer primary bulletins" in hinted.prompt
