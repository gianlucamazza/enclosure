"""Entry point: `inspect eval evals/times.py`.

Inspect only discovers `@task` functions defined in this file.
"""

from inspect_ai import task

from enclosure.times_eval import times as build_times


@task
def times(
    treatments: str | list[str] = "T0,T1,T2,T3,T4,T5",
    blind: str = "true",
    social: str = "none",
    prior: str = "strong",
    authority_hint: str = "none",
):
    """The Times pack. prior is strong, none, or contradicts. authority_hint is none, prefer_primary, or prefer_search."""
    return build_times(treatments, blind, social, prior, authority_hint)
