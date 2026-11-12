"""Signal-detection summaries for an explicitly defined, observable truth task.

These functions do not turn adoption of identical-evidence twins into truth
 discrimination. Callers must specify denominators and report uncertainty,
absence and elicited responses separately before choosing a binary decision rule.
"""

from __future__ import annotations

from math import sqrt
from statistics import NormalDist


def wilson(successes: int, trials: int) -> tuple[float, float]:
    if not 0 <= successes <= trials or trials < 1:
        raise ValueError("Need 0 <= successes <= trials and positive trials")
    z = NormalDist().inv_cdf(0.975)
    p = successes / trials
    denominator = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denominator
    radius = z * sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return max(0.0, center - radius), min(1.0, center + radius)


def signal_detection(hits: int, true_trials: int, false_alarms: int, false_trials: int) -> dict:
    hit_interval = wilson(hits, true_trials)
    false_interval = wilson(false_alarms, false_trials)
    # Log-linear correction, applied to every cell, including endpoint rates.
    zh = NormalDist().inv_cdf((hits + 0.5) / (true_trials + 1))
    zf = NormalDist().inv_cdf((false_alarms + 0.5) / (false_trials + 1))
    return {
        "hit_rate": hits / true_trials,
        "false_alarm_rate": false_alarms / false_trials,
        "hit_rate_interval_95": hit_interval,
        "false_alarm_interval_95": false_interval,
        "d_prime": zh - zf,
        "criterion": -0.5 * (zh + zf),
        "correction": "log-linear +0.5 / n+1",
    }
