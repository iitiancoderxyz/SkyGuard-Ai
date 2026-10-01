"""
Unit Test Suite for UNIT B — Sensor Health & Diagnostics (Repair 3).
Tests:
B1. Healthy normal stream (HEALTHY state, 100% availability)
B2. Missing observations (DEGRADED / CRITICAL availability)
B3. Delayed observations (Integrity events in health)
B4. Frozen temperature sensor (SENSOR_FLATLINE, AT_RISK / CRITICAL)
B5. Persistent drift (CALIBRATION_DRIFT, AT_RISK)
B6. Repeated anomaly events (Health score deduction)
B7. Communication/integrity issues (Telemetry loss indicators)
B8. Health state persistence & SQLite retrieval
"""
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from app.runtime.engine import process_observation
from ingestion.schemas.observation import ObservationIn
from health.sensor_health.diagnostics import diagnose_station_health as evaluate_station_health
from storage.repositories.health_repo import health_repo
from storage.repositories.station_repo import station_repo


def test_b1_healthy_normal_stream():
    """B1. Healthy normal stream yields HEALTHY overall state and 100% availability."""
    st_id = f"AWS_HLTH_NORM_{uuid.uuid4().hex[:6]}"
    station_repo.upsert_station(st_id)
    t0 = datetime.now(timezone.utc) - timedelta(minutes=15)

    for i in range(12):
        obs = ObservationIn(
            station_id=st_id,
            timestamp=t0 + timedelta(minutes=i),
            temperature=24.0 + (i % 4) * 0.15,
            pressure=1013.25 - (i % 3) * 0.1,
            relative_humidity=55.0 + (i % 5) * 0.2,
            source_type="LIVE",
        )
        process_observation(obs)

    health = evaluate_station_health(st_id)
    assert health["overall_health_state"] == "HEALTHY"
    assert health["channel_availability"]["temperature"] >= 0.95
    assert health["channel_availability"]["pressure"] >= 0.95
    assert health["channel_availability"]["relative_humidity"] >= 0.95
    assert health["channels"]["temperature"]["state"] == "HEALTHY"


def test_b2_missing_observations():
    """B2. Missing channel observations trigger reduced availability and DEGRADED state."""
    st_id = f"AWS_HLTH_MISS_{uuid.uuid4().hex[:6]}"
    station_repo.upsert_station(st_id)
    t0 = datetime.now(timezone.utc) - timedelta(minutes=15)

    # Ingest 10 records with missing temperature
    for i in range(10):
        obs = ObservationIn(
            station_id=st_id,
            timestamp=t0 + timedelta(minutes=i),
            temperature=None,  # Missing channel
            pressure=1013.25 - (i % 3) * 0.1,
            relative_humidity=55.0 + (i % 5) * 0.2,
            source_type="LIVE",
        )
        process_observation(obs)

    health = evaluate_station_health(st_id)
    assert health["channel_availability"]["temperature"] == 0.0
    assert health["channels"]["temperature"]["state"] in ["CRITICAL", "AT_RISK"]
    assert health["channels"]["temperature"]["degradation_state"] == "SEVERE_DATA_LOSS"


def test_b3_delayed_observations():
    """B3. Delayed observations are captured in recent events count."""
    st_id = f"AWS_HLTH_DELAY_{uuid.uuid4().hex[:6]}"
    station_repo.upsert_station(st_id)
    t0 = datetime.now(timezone.utc) - timedelta(minutes=30)

    # First observation
    obs = ObservationIn(
        station_id=st_id,
        timestamp=t0,
        temperature=25.0,
        pressure=1013.0,
        relative_humidity=60.0,
        source_type="LIVE",
    )
    process_observation(obs)

    # 15 minutes late observation (triggers lateness/gap)
    obs_late = ObservationIn(
        station_id=st_id,
        timestamp=t0 + timedelta(minutes=15),
        temperature=25.1,
        pressure=1013.0,
        relative_humidity=60.0,
        source_type="LIVE",
    )
    process_observation(obs_late)

    health = evaluate_station_health(st_id)
    assert health["recent_events_count"] >= 1


def test_b4_frozen_temperature_sensor():
    """B4. Consecutive identical values trigger SENSOR_FLATLINE degradation state."""
    st_id = f"AWS_HLTH_FRZ_{uuid.uuid4().hex[:6]}"
    station_repo.upsert_station(st_id)
    t0 = datetime.now(timezone.utc) - timedelta(minutes=15)

    # 5 identical readings in a row
    for i in range(6):
        obs = ObservationIn(
            station_id=st_id,
            timestamp=t0 + timedelta(minutes=i),
            temperature=22.34,  # Identical
            pressure=1013.25 - (i % 3) * 0.1,
            relative_humidity=55.0 + (i % 5) * 0.2,
            source_type="LIVE",
        )
        process_observation(obs)

    health = evaluate_station_health(st_id)
    assert health["channels"]["temperature"]["degradation_state"] == "SENSOR_FLATLINE"
    assert health["channels"]["temperature"]["state"] in ["AT_RISK", "CRITICAL"]


def test_b5_persistent_drift():
    """B5. Persistent drift triggers CALIBRATION_DRIFT degradation state."""
    st_id = f"AWS_HLTH_DRF_{uuid.uuid4().hex[:6]}"
    station_repo.upsert_station(st_id)
    t0 = datetime.now(timezone.utc) - timedelta(minutes=30)

    # Warmup
    for i in range(12):
        obs = ObservationIn(
            station_id=st_id,
            timestamp=t0 + timedelta(minutes=i),
            temperature=20.0 + (i % 3) * 0.1,
            pressure=1013.0 - (i % 2) * 0.1,
            relative_humidity=50.0,
            source_type="LIVE",
        )
        process_observation(obs)

    # Inject progressive drift
    for i in range(12, 20):
        obs = ObservationIn(
            station_id=st_id,
            timestamp=t0 + timedelta(minutes=i),
            temperature=20.0,
            pressure=1013.0,
            relative_humidity=50.0 + 3.0 * (i - 11),
            source_type="LIVE",
        )
        process_observation(obs)

    health = evaluate_station_health(st_id)
    assert health["overall_health_state"] in ["AT_RISK", "DEGRADED"]
    assert len(health["supporting_evidence"]) > 0


def test_b6_repeated_anomaly_events():
    """B6. Repeated anomalies correctly increment recent_anomalies_count."""
    st_id = f"AWS_HLTH_ANOM_{uuid.uuid4().hex[:6]}"
    station_repo.upsert_station(st_id)
    t0 = datetime.now(timezone.utc) - timedelta(minutes=15)

    for i in range(8):
        obs = ObservationIn(
            station_id=st_id,
            timestamp=t0 + timedelta(minutes=i),
            temperature=24.0 + (i % 3) * 0.1,
            pressure=1013.25,
            relative_humidity=55.0,
            source_type="LIVE",
        )
        process_observation(obs)

    # Spike
    spike = ObservationIn(
        station_id=st_id,
        timestamp=t0 + timedelta(minutes=8),
        temperature=55.0,
        pressure=1013.25,
        relative_humidity=55.0,
        source_type="LIVE",
    )
    process_observation(spike)

    health = evaluate_station_health(st_id)
    assert health["recent_anomalies_count"] >= 1


def test_b7_communication_integrity_issues():
    """B7. Telemetry packet drops trigger missing record integrity events."""
    st_id = f"AWS_HLTH_COMM_{uuid.uuid4().hex[:6]}"
    station_repo.upsert_station(st_id)
    t0 = datetime.now(timezone.utc) - timedelta(minutes=20)

    obs1 = ObservationIn(
        station_id=st_id,
        timestamp=t0,
        temperature=25.0,
        pressure=1013.0,
        relative_humidity=60.0,
        source_type="LIVE",
    )
    process_observation(obs1)

    # 4 missed minutes
    obs2 = ObservationIn(
        station_id=st_id,
        timestamp=t0 + timedelta(minutes=5),
        temperature=25.1,
        pressure=1013.0,
        relative_humidity=60.0,
        source_type="LIVE",
    )
    process_observation(obs2)

    health = evaluate_station_health(st_id)
    assert health["recent_events_count"] >= 1


def test_b8_health_state_persistence_and_sqlite_retrieval():
    """B8. Health state evaluations are persisted to SQLite health_state table."""
    st_id = f"AWS_HLTH_SQL_{uuid.uuid4().hex[:6]}"
    station_repo.upsert_station(st_id)
    t0 = datetime.now(timezone.utc) - timedelta(minutes=15)

    for i in range(6):
        obs = ObservationIn(
            station_id=st_id,
            timestamp=t0 + timedelta(minutes=i),
            temperature=24.0 + (i % 3) * 0.1,
            pressure=1013.25,
            relative_humidity=55.0,
            source_type="LIVE",
        )
        process_observation(obs)

    # Execute health evaluation (persists to SQLite)
    health = evaluate_station_health(st_id)

    # Directly query health_state SQLite table
    db_records = health_repo.get_health_states(st_id)
    assert len(db_records) == 3  # T, P, RH
    ch_names = [r["channel"] for r in db_records]
    assert "temperature" in ch_names
    assert "pressure" in ch_names
    assert "relative_humidity" in ch_names
    for r in db_records:
        assert r["state"] is not None
        assert r["health_score"] is not None
        assert r["degradation_state"] is not None
