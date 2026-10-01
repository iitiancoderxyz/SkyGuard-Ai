"""
Unit tests for canonical observation schema and validation rules.
"""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from ingestion.schemas.observation import (
    ObservationIn,
    SourceType,
    compute_payload_hash,
    generate_observation_id,
)


def test_valid_observation():
    obs = ObservationIn(
        station_id="AWS_001",
        timestamp=datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc),
        temperature=25.4,
        pressure=1012.3,
        relative_humidity=60.0,
        latitude=23.1765,
        longitude=79.9864,
        elevation=411.0,
        source_type=SourceType.LIVE,
    )
    assert obs.station_id == "AWS_001"
    assert obs.temperature == 25.4
    assert obs.pressure == 1012.3
    assert obs.relative_humidity == 60.0


def test_extra_meteorological_fields_forbidden():
    """INV-01: Non-core meteorological fields must raise ValidationError (extra='forbid')."""
    payload = {
        "station_id": "AWS_001",
        "timestamp": "2026-09-30T10:00:00Z",
        "temperature": 25.4,
        "pressure": 1012.3,
        "relative_humidity": 60.0,
        "wind_speed": 5.2,  # Prohibited
    }
    with pytest.raises(ValidationError):
        ObservationIn(**payload)


def test_deterministic_observation_id():
    ts = "2026-09-30T10:00:00+00:00"
    id1 = generate_observation_id("AWS_001", ts, "seq1", unique_salt="salt1")
    id2 = generate_observation_id("AWS_001", ts, "seq1", unique_salt="salt1")
    id3 = generate_observation_id("AWS_001", ts, "seq2", unique_salt="salt2")
    assert id1 == id2
    assert id1 != id3
    assert id1.startswith("obs-AWS_001-")


def test_payload_hash():
    s1 = '{"temp": 25.0}'
    s2 = '{"temp": 25.0}'
    s3 = '{"temp": 26.0}'
    assert compute_payload_hash(s1) == compute_payload_hash(s2)
    assert compute_payload_hash(s1) != compute_payload_hash(s3)
