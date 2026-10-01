"""
Unit Test Suite for UNIT A — Real Explainability & Evidence Presentation (Repair 3).
Tests:
A1. Normal observation (nominal reasoning trace)
A2. Temperature spike (step jump / spike explainability)
A3. Frozen sensor (persistence / flatline explainability)
A4. Drift (Z-score excursion explainability)
A5. Multivariate inconsistency (thermodynamic explainability)
A6. Genuine-weather scenario (weather likelihood & evidence)
A7. Ambiguous/suspect case (competing hypothesis explainability)
A8. Telemetry/integrity issue (gate flag explainability)
"""
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from app.runtime.engine import process_observation
from ingestion.schemas.observation import ObservationIn
from ingestion.schemas.response import DecisionState


def test_a1_normal_observation_explainability():
    """A1. Normal observation produces clean nominal reasoning and empty/cold-start evidence."""
    st_id = f"AWS_EXP_NORM_{uuid.uuid4().hex[:6]}"
    t0 = datetime.now(timezone.utc) - timedelta(minutes=15)
    
    # Send 10 clean diurnal points
    dec = None
    for i in range(10):
        obs = ObservationIn(
            station_id=st_id,
            timestamp=t0 + timedelta(minutes=i),
            temperature=24.0 + (i % 4) * 0.15,
            pressure=1013.25 - (i % 3) * 0.1,
            relative_humidity=55.0 + (i % 5) * 0.2,
            source_type="LIVE",
        )
        dec = process_observation(obs)

    assert dec is not None
    assert dec.decision_state == DecisionState.NORMAL
    assert dec.anomaly_score < 0.35
    assert dec.root_cause_category == "NORMAL"
    assert len(dec.reasoning_summary) > 0


def test_a2_temperature_spike_explainability():
    """A2. Temperature spike produces step spike trigger and human-readable reasoning trace."""
    st_id = f"AWS_EXP_SPIKE_{uuid.uuid4().hex[:6]}"
    t0 = datetime.now(timezone.utc) - timedelta(minutes=15)

    for i in range(10):
        obs = ObservationIn(
            station_id=st_id,
            timestamp=t0 + timedelta(minutes=i),
            temperature=24.0 + (i % 4) * 0.15,
            pressure=1013.25 - (i % 3) * 0.1,
            relative_humidity=55.0 + (i % 5) * 0.2,
            source_type="LIVE",
        )
        process_observation(obs)

    # Spike +30C
    spike_obs = ObservationIn(
        station_id=st_id,
        timestamp=t0 + timedelta(minutes=10),
        temperature=54.0,
        pressure=1013.25,
        relative_humidity=55.0,
        source_type="LIVE",
    )
    dec = process_observation(spike_obs)

    assert dec.decision_state == DecisionState.ANOMALY
    assert "TEMPERATURE_SPIKE_POSITIVE" in dec.evidence_codes
    assert "spike" in dec.reasoning_summary.lower()
    assert dec.sensor_fault_evidence is True
    assert dec.root_cause_category == "SENSOR_SPIKE"


def test_a3_frozen_sensor_explainability():
    """A3. Frozen sensor produces stuck sensor evidence and reasoning."""
    st_id = f"AWS_EXP_FROZEN_{uuid.uuid4().hex[:6]}"
    t0 = datetime.now(timezone.utc) - timedelta(minutes=15)

    # Ingest 10 clean points
    for i in range(8):
        obs = ObservationIn(
            station_id=st_id,
            timestamp=t0 + timedelta(minutes=i),
            temperature=22.0 + (i % 3) * 0.2,
            pressure=1012.0 - (i % 2) * 0.1,
            relative_humidity=50.0 + (i % 4) * 0.2,
            source_type="LIVE",
        )
        process_observation(obs)

    # Ingest 5 identical flatline points
    dec = None
    for i in range(8, 13):
        obs = ObservationIn(
            station_id=st_id,
            timestamp=t0 + timedelta(minutes=i),
            temperature=22.5,
            pressure=1012.0,
            relative_humidity=50.0,
            source_type="LIVE",
        )
        dec = process_observation(obs)

    assert dec is not None
    assert any("FROZEN" in c for c in dec.evidence_codes)
    assert dec.root_cause_category == "SENSOR_STUCK_FROZEN"
    assert "frozen" in dec.reasoning_summary.lower() or "stuck" in dec.reasoning_summary.lower()


def test_a4_drift_explainability():
    """A4. Progressive drift triggers statistical excursion reasoning."""
    st_id = f"AWS_EXP_DRIFT_{uuid.uuid4().hex[:6]}"
    t0 = datetime.now(timezone.utc) - timedelta(minutes=30)

    for i in range(15):
        obs = ObservationIn(
            station_id=st_id,
            timestamp=t0 + timedelta(minutes=i),
            temperature=20.0 + (i % 3) * 0.1,
            pressure=1013.0 - (i % 2) * 0.1,
            relative_humidity=50.0,
            source_type="LIVE",
        )
        process_observation(obs)

    dec = None
    for i in range(15, 24):
        obs = ObservationIn(
            station_id=st_id,
            timestamp=t0 + timedelta(minutes=i),
            temperature=20.0,
            pressure=1013.0,
            relative_humidity=50.0 + 3.0 * (i - 14),
            source_type="LIVE",
        )
        dec = process_observation(obs)

    assert dec is not None
    assert dec.anomaly_score >= 0.35
    assert len(dec.evidence_codes) > 0
    assert len(dec.reasoning_summary) > 0


def test_a5_multivariate_inconsistency_explainability():
    """A5. Thermodynamic / multivariate conflict produces explainable reasoning."""
    st_id = f"AWS_EXP_THERMO_{uuid.uuid4().hex[:6]}"
    t0 = datetime.now(timezone.utc) - timedelta(minutes=15)

    for i in range(10):
        obs = ObservationIn(
            station_id=st_id,
            timestamp=t0 + timedelta(minutes=i),
            temperature=25.0 + (i % 3) * 0.1,
            pressure=1013.0 - (i % 2) * 0.1,
            relative_humidity=60.0 + (i % 4) * 0.2,
            source_type="LIVE",
        )
        process_observation(obs)

    # Ingest severe step drop in pressure and jump in RH
    obs = ObservationIn(
        station_id=st_id,
        timestamp=t0 + timedelta(minutes=10),
        temperature=25.0,
        pressure=960.0,
        relative_humidity=99.0,
        source_type="LIVE",
    )
    dec = process_observation(obs)

    assert dec.anomaly_score >= 0.65
    assert dec.plausibility_score is not None
    assert len(dec.reasoning_summary) > 0


def test_a6_genuine_weather_explainability():
    """A6. Genuine coordinated weather event yields elevated weather likelihood and plausibility."""
    from simulator.scenarios.suite import ScenarioSuite
    from simulator.replay.replayer import StreamReplayer

    suite = ScenarioSuite(seed=42)
    obs_list, meta = suite.create_scenario("GENUINE_WEATHER", station_id=f"AWS_EXP_WX_{uuid.uuid4().hex[:6]}", num_points=25)
    replayer = StreamReplayer()
    decisions = replayer.replay(obs_list)

    peak_d = max(decisions, key=lambda d: d.weather_event_likelihood or 0.0)
    assert peak_d.weather_event_likelihood >= 0.30 or peak_d.plausibility_score >= 0.50
    assert len(peak_d.reasoning_summary) > 0


def test_a7_ambiguous_suspect_case_explainability():
    """A7. Ambiguous case clearly distinguishes detection confidence from attribution confidence."""
    st_id = f"AWS_EXP_AMBIG_{uuid.uuid4().hex[:6]}"
    t0 = datetime.now(timezone.utc) - timedelta(minutes=15)

    for i in range(12):
        obs = ObservationIn(
            station_id=st_id,
            timestamp=t0 + timedelta(minutes=i),
            temperature=22.0 + (i % 4) * 0.15,
            pressure=1012.0 - (i % 3) * 0.1,
            relative_humidity=55.0 + (i % 5) * 0.2,
            source_type="LIVE",
        )
        process_observation(obs)

    # Moderate rate jump (rate score = 0.55 -> SUSPECT)
    last_t = 22.0 + (11 % 4) * 0.15
    obs = ObservationIn(
        station_id=st_id,
        timestamp=t0 + timedelta(minutes=12),
        temperature=last_t + 0.55,
        pressure=1012.0,
        relative_humidity=55.0,
        source_type="LIVE",
    )
    dec = process_observation(obs)

    assert dec.decision_state in [DecisionState.SUSPECT, DecisionState.AMBIGUOUS]
    assert dec.detection_confidence is not None
    assert dec.attribution_confidence is not None
    assert dec.severity is not None


def test_a8_telemetry_integrity_explainability():
    """A8. Data lateness / telemetry flag is reflected in evidence and reasoning."""
    st_id = f"AWS_EXP_INTEG_{uuid.uuid4().hex[:6]}"
    t0 = datetime.now(timezone.utc) - timedelta(minutes=15)

    obs = ObservationIn(
        station_id=st_id,
        timestamp=t0,
        temperature=25.0,
        pressure=1013.0,
        relative_humidity=60.0,
        source_type="LIVE",
    )
    dec1 = process_observation(obs)

    # Send record 10 minutes late (gap)
    obs_late = ObservationIn(
        station_id=st_id,
        timestamp=t0 + timedelta(minutes=10),
        temperature=25.1,
        pressure=1013.0,
        relative_humidity=60.0,
        source_type="LIVE",
    )
    dec2 = process_observation(obs_late)

    assert any("TELEMETRY" in c or "INTEGRITY" in c or "GAP" in c or "MISSING" in c for c in dec2.evidence_codes)
    assert len(dec2.reasoning_summary) > 0
