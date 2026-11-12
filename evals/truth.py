"""Observable synthetic event controls. No hidden-ledger discrimination claim."""

from inspect_ai import task

from enclosure.times_eval import _samples, _task


@task
def truth(event: bool = True, backend: str = "vm"):
    return _task(_samples(f"scenarios/truth/grid_{str(event).lower()}.yaml", "T2"), backend)
