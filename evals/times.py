"""Entry point: `inspect eval evals/times.py`.

Inspect only discovers `@task` functions defined in this file.
"""

from inspect_ai import task

from enclosure.times_eval import times as build_times


@task
def times(treatments: str = "T0,T1,T2,T3,T4,T5", blind: str = "true"):
    """The Times pack. T5 is the deep hole. blind=false tells the subject."""
    return build_times(treatments, blind)
