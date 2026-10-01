"""
Unit tests for rate-of-change calculations.
"""
from features.temporal.rates import compute_rates_of_change


def test_rate_of_change():
    curr = {"temperature": 26.0, "pressure": 1010.0, "relative_humidity": 50.0}
    last = {"temperature": 25.0, "pressure": 1012.0, "relative_humidity": 50.0}
    delta_sec = 60.0  # 1 minute

    rates = compute_rates_of_change(curr, last, delta_sec)
    assert rates["rate_temperature_per_min"] == 1.0
    assert rates["rate_pressure_per_min"] == -2.0
    assert rates["rate_relative_humidity_per_min"] == 0.0


def test_rate_with_missing_values():
    curr = {"temperature": None, "pressure": 1010.0, "relative_humidity": 50.0}
    last = {"temperature": 25.0, "pressure": 1012.0, "relative_humidity": None}
    delta_sec = 120.0  # 2 minutes

    rates = compute_rates_of_change(curr, last, delta_sec)
    assert rates["rate_temperature_per_min"] is None
    assert rates["rate_relative_humidity_per_min"] is None
    assert rates["rate_pressure_per_min"] == -1.0
