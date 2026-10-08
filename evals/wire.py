"""Entry point: `inspect eval evals/wire.py -T episode=suez -T treatments=T2`."""

from inspect_ai import task

from enclosure.times_eval import wire as build_wire


@task
def wire(
    episode: str | list[str] = "suez,quake,gnss,grid,fuel,cloud",
    treatments: str | list[str] = "T0,T2,T4",
    blind: str = "true",
    social: str = "none",
    authority_hint: str = "none",
):
    """False bulletins. social is none, one_party, majority_party, majority_ground, or split."""
    return build_wire(episode, treatments, blind, social, authority_hint)
