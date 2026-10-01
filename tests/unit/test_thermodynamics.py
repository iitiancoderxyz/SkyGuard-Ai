"""
Unit tests for derived thermodynamic calculations.
"""
import pytest
from features.multivariate.thermodynamics import (
    compute_saturated_vapour_pressure,
    compute_vapour_pressure,
    compute_dewpoint,
    compute_derived_meteorological_quantities,
)


def test_saturated_vapour_pressure():
    # At 0°C, e_s ≈ 6.11 hPa
    e_0 = compute_saturated_vapour_pressure(0.0)
    assert round(e_0, 1) == 6.1

    # At 20°C, e_s ≈ 23.38 hPa
    e_20 = compute_saturated_vapour_pressure(20.0)
    assert 23.0 < e_20 < 24.0


def test_vapour_pressure():
    # At 20°C and 50% RH, e = 0.5 * e_s(20) ≈ 11.69 hPa
    e = compute_vapour_pressure(20.0, 50.0)
    assert 11.5 < e < 12.0


def test_dewpoint_physical_properties():
    # When RH = 100%, T_d == T
    td_100 = compute_dewpoint(25.0, 100.0)
    assert abs(td_100 - 25.0) < 0.1

    # When RH < 100%, T_d < T
    td_50 = compute_dewpoint(25.0, 50.0)
    assert td_50 < 25.0
    assert 13.0 < td_50 < 15.0


def test_derived_quantities_packaging():
    q = compute_derived_meteorological_quantities(25.0, 1013.25, 60.0)
    assert "derived_dewpoint_c" in q
    assert "derived_vapour_pressure_hpa" in q
    assert "derived_saturated_vapour_pressure_hpa" in q
    assert q["derived_dewpoint_c"] is not None
    assert q["derived_vapour_pressure_hpa"] is not None
