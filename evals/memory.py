"""Compare silent replacement, explicit correction and ordinary resolution."""

from inspect_ai import task

from enclosure.times_eval import _samples, _task


@task
def memory(explanation: str = "silent", treatments: str = "T4,T5", backend: str = "vm"):
    if explanation not in {"silent", "correction", "resolution"}:
        raise ValueError("Unknown restoration explanation")
    samples = _samples(f"scenarios/memory/grid_{explanation}.yaml", treatments)
    for sample in samples:
        sample.metadata = sample.metadata or {}
        sample.metadata["restoration_explanation"] = explanation
    return _task(samples, backend)
