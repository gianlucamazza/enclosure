from enclosure.plots import (
    adoption_by_treatment,
    stated_vs_adopted,
    verification_vs_adoption,
)

ROWS = [
    {
        "sample": "wire.grid.T0",
        "treatment": "T0",
        "belief_stated": 1,
        "belief_adoption": 0.0,
        "verification_seeking": 1.0,
    },
    {
        "sample": "wire.grid.T2",
        "treatment": "T2",
        "belief_stated": 0,
        "belief_adoption": None,
        "verification_seeking": 1.0,
    },
]


def test_unstated_belief_does_not_become_zero_adoption():
    stated = stated_vs_adopted(ROWS)
    by_treatment = {row["treatment"]: row for row in stated}
    assert by_treatment["T0"]["stated"] == 1
    assert by_treatment["T0"]["adopted"] == 0.0
    assert by_treatment["T2"]["stated"] == 0
    assert by_treatment["T2"]["adopted"] is None

    adopted = adoption_by_treatment(ROWS)
    assert [row["treatment"] for row in adopted] == ["T0"]

    points = verification_vs_adoption(ROWS)
    assert len(points) == 1
    assert points[0]["treatment"] == "T0"
    assert points[0]["adopted"] == 0.0
