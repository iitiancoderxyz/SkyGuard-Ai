"""
Unit tests for configuration and claims definitions.
"""
from app.core.config import settings, get_settings
from app.core.claims import (
    PROJECT_NAME,
    PROJECT_FULL_NAME,
    ALLOWED_METEOROLOGICAL_INPUTS,
    DISCLAIMER_EVALUATION,
    DISCLAIMER_HEALTH,
    DISCLAIMER_DEGRADATION,
    DISCLAIMER_MAINTENANCE,
    DISCLAIMER_CALIBRATION,
    DISCLAIMER_NETWORK_CONTEXT,
    DISCLAIMER_CORRECTION,
)


def test_core_claims_scope():
    assert PROJECT_NAME == "TRUST-TWIN"
    assert "temperature" in ALLOWED_METEOROLOGICAL_INPUTS
    assert "pressure" in ALLOWED_METEOROLOGICAL_INPUTS
    assert "relative_humidity" in ALLOWED_METEOROLOGICAL_INPUTS
    assert len(ALLOWED_METEOROLOGICAL_INPUTS) == 3


def test_disclaimers_present():
    assert len(DISCLAIMER_EVALUATION) > 0
    assert len(DISCLAIMER_HEALTH) > 0
    assert len(DISCLAIMER_DEGRADATION) > 0
    assert len(DISCLAIMER_MAINTENANCE) > 0
    assert len(DISCLAIMER_CALIBRATION) > 0
    assert len(DISCLAIMER_NETWORK_CONTEXT) > 0
    assert len(DISCLAIMER_CORRECTION) > 0


def test_settings_defaults():
    s = get_settings()
    assert s.app_name == "TRUST-TWIN"
    assert s.expected_cadence_seconds == 60
    assert s.allowed_lateness_seconds == 120
    assert s.communication_gap_slots == 3
