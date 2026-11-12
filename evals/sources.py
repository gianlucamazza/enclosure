"""Matched source-lineage experiment: single, copied, independent, dissent."""

from inspect_ai import task

from enclosure.research import scaffold_prompt
from enclosure.times_eval import _samples, _task


@task
def sources(
    condition: str = "single",
    treatments: str = "T0,T2",
    scaffold: str = "standard",
    backend: str = "vm",
):
    if condition not in {"single", "copied", "independent", "dissent"}:
        raise ValueError("Unknown source condition")
    prompt = scaffold_prompt(scaffold)
    samples = _samples(f"scenarios/sources/grid_{condition}.yaml", treatments)
    for sample in samples:
        sample.metadata = sample.metadata or {}
        sample.metadata.update(source_condition=condition, scaffold=scaffold)
        sample.input = str(sample.input) + ("\n" + prompt if prompt else "")
    return _task(samples, backend)
