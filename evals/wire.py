"""Entry point: `inspect eval evals/wire.py -T episode=suez -T treatments=T2`."""

from inspect_ai import task

from enclosure.times_eval import wire as build_wire


@task
def wire(
    episode: str | list[str] = "suez,quake,gnss,grid,fuel,cloud",
    treatments: str | list[str] = "T0,T2,T4",
    blind: str = "true",
):
    """False bulletins, including grid, fuel, and cloud shortages. T5 is the deep hole."""
    return build_wire(episode, treatments, blind)
