import math

import pytest

from enclosure.calibration import signal_detection


def test_equal_rates_have_no_discrimination_and_endpoints_are_finite():
    assert signal_detection(5, 10, 5, 10)["d_prime"] == 0
    scores = signal_detection(10, 10, 0, 10)
    assert math.isfinite(scores["d_prime"]) and scores["d_prime"] > 0
    assert scores["hit_rate_interval_95"][0] < 1
    with pytest.raises(ValueError):
        signal_detection(0, 0, 0, 10)
