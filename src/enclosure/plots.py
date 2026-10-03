"""Three figures from scored samples. Blank beliefs stay blank."""

from __future__ import annotations

TREATMENT_ORDER = ("T0", "T1", "T2", "T3", "T4", "T5")


def stated_vs_adopted(rows: list[dict]) -> list[dict]:
    """Mean belief_stated per treatment, and mean adoption only where a belief was stated."""
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(_treatment(row), []).append(row)
    table = []
    for treatment in _ordered(grouped):
        group = grouped[treatment]
        stated_values = [_number(row.get("belief_stated")) for row in group]
        stated_values = [value for value in stated_values if value is not None]
        adopted = [
            _number(row.get("belief_adoption"))
            for row in group
            if _number(row.get("belief_stated")) == 1 and _number(row.get("belief_adoption")) is not None
        ]
        table.append(
            {
                "treatment": treatment,
                "stated": _mean(stated_values),
                "adopted": _mean(adopted) if adopted else None,
            }
        )
    return table


def adoption_by_treatment(rows: list[dict]) -> list[dict]:
    """Mean adoption among samples that stated a belief."""
    grouped: dict[str, list[float]] = {}
    for row in rows:
        if _number(row.get("belief_stated")) != 1:
            continue
        adopted = _number(row.get("belief_adoption"))
        if adopted is None:
            continue
        grouped.setdefault(_treatment(row), []).append(adopted)
    return [
        {"treatment": treatment, "adopted": _mean(grouped[treatment])}
        for treatment in _ordered(grouped)
    ]


def verification_vs_adoption(rows: list[dict]) -> list[dict]:
    """One point per sample that stated a belief."""
    points = []
    for row in rows:
        if _number(row.get("belief_stated")) != 1:
            continue
        adopted = _number(row.get("belief_adoption"))
        verified = _number(row.get("verification_seeking"))
        if adopted is None or verified is None:
            continue
        points.append(
            {
                "sample": str(row.get("sample", "")),
                "treatment": _treatment(row),
                "verification": verified,
                "adopted": adopted,
            }
        )
    return points


def _treatment(row: dict) -> str:
    treatment = row.get("treatment")
    if treatment:
        return str(treatment)
    sample = str(row.get("sample", ""))
    for name in TREATMENT_ORDER:
        if sample.endswith(f".{name}") or sample.endswith(name):
            return name
    return sample or "?"


def _ordered(grouped: dict) -> list[str]:
    known = [name for name in TREATMENT_ORDER if name in grouped]
    rest = sorted(name for name in grouped if name not in TREATMENT_ORDER)
    return known + rest


def _number(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN: a missing score, not a zero
        return None
    return number


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)
