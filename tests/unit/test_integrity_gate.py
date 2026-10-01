"""
Unit tests for IntegrityGate checks.
"""
from datetime import datetime, timezone, timedelta
from ingestion.schemas.observation import ObservationIn
from ingestion.schemas.integrity import (
    IntegrityFlag,
    IntegrityDisposition,
)
from ingestion.integrity.gate import IntegrityGate
from ingestion.integrity.state import StationState


def test_nominal_integrity_check():
    gate = IntegrityGate()
    state = StationState(station_id="AWS_01")
    obs = ObservationIn(
        station_id="AWS_01",
        timestamp=datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc),
        temperature=25.0,
        pressure=1010.0,
        relative_humidity=50.0,
    )
    res = gate.check(obs, state, received_at=obs.timestamp)
    assert res.disposition == IntegrityDisposition.ACCEPT
    assert IntegrityFlag.OK in res.flags


def test_range_violations():
    gate = IntegrityGate(temp_min=-40.0, temp_max=50.0)
    state = StationState(station_id="AWS_01")
    obs = ObservationIn(
        station_id="AWS_01",
        timestamp=datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc),
        temperature=55.0,  # Exceeds max
        pressure=1010.0,
        relative_humidity=50.0,
    )
    res = gate.check(obs, state, received_at=obs.timestamp)
    assert IntegrityFlag.RANGE_TEMP_HIGH in res.flags
    assert IntegrityFlag.RANGE_VIOLATION in res.flags


def test_duplicate_and_conflicting_duplicate():
    gate = IntegrityGate()
    state = StationState(station_id="AWS_01")
    obs1 = ObservationIn(
        station_id="AWS_01",
        timestamp=datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc),
        temperature=25.0,
        pressure=1010.0,
        relative_humidity=50.0,
    )
    # First check
    gate.check(obs1, state, received_at=obs1.timestamp)
    state.seen_timestamps[obs1.timestamp.isoformat()] = {
        "values": {"temperature": 25.0, "pressure": 1010.0, "relative_humidity": 50.0},
        "obs_id": "obs-1",
    }

    # Exact duplicate
    res_dup = gate.check(obs1, state, received_at=obs1.timestamp)
    assert IntegrityFlag.DUPLICATE in res_dup.flags

    # Conflicting duplicate
    obs_conflict = ObservationIn(
        station_id="AWS_01",
        timestamp=datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc),
        temperature=35.0,  # Different value
        pressure=1010.0,
        relative_humidity=50.0,
    )
    res_conf = gate.check(obs_conflict, state, received_at=obs_conflict.timestamp)
    assert IntegrityFlag.CONFLICTING_DUPLICATE in res_conf.flags
    assert res_conf.disposition == IntegrityDisposition.QUARANTINE


def test_missing_slots_and_communication_gap():
    gate = IntegrityGate(expected_cadence_seconds=60, communication_gap_slots=3)
    state = StationState(station_id="AWS_01")
    
    t0 = datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc)
    obs0 = ObservationIn(station_id="AWS_01", timestamp=t0, temperature=20.0, pressure=1000.0, relative_humidity=50.0)
    gate.check(obs0, state, received_at=t0)

    # Skip 4 intervals (240s)
    t1 = t0 + timedelta(seconds=240)
    obs1 = ObservationIn(station_id="AWS_01", timestamp=t1, temperature=20.0, pressure=1000.0, relative_humidity=50.0)
    res = gate.check(obs1, state, received_at=t1)

    assert IntegrityFlag.MISSING_EXPECTED_RECORD in res.flags
    assert IntegrityFlag.COMMUNICATION_GAP in res.flags
    assert len(res.missing_slots) == 3
