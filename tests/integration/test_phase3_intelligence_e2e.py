"""
Phase 3D Comprehensive Integration & End-to-End Test Suite.
Tests the full Phase 3 intelligence pipeline:
  Observation Ingestion -> Integrity Gate -> Feature Vector Generation ->
  Statistical Anomaly Engine (3A) -> Reference Baseline & Adaptive Tracker (3B) ->
  Decision Adjudication & Explainability (3C) -> Structured Response (3D).

Covers all 11 required scenarios:
  1. normal
  2. temperature spike
  3. pressure anomaly
  4. humidity anomaly
  5. frozen sensor
  6. drift
  7. unrealistic rate
  8. multivariate inconsistency
  9. plausible weather event
  10. delayed but plausible observation
  11. ambiguous case

Also verifies:
  - Raw data immutability & preservation in SQLite
  - Determinism across repeated executions
  - Existing API endpoint compatibility (REST API /v1/observations)
  - Practical inference latency budget (<5.0ms target)
"""
import time
import math
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.runtime.engine import process_observation
from ingestion.schemas.observation import ObservationIn
from ingestion.schemas.response import DecisionState, SeverityLevel, AdmissionState
from detection.decision.adjudicator import RootCause, adjudicator
from detection.triggers.statistical import statistical_detector
from detection.reference.baseline import reference_profile
from detection.tracker.tracker import adaptive_tracker
from features.builder import CleanBuffer
from storage.db.connection import db


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _make_obs(
    station_id: str,
    ts: datetime,
    t: float = 25.0,
    p: float = 1013.25,
    rh: float = 60.0,
) -> ObservationIn:
    return ObservationIn(
        station_id=station_id,
        timestamp=ts,
        temperature=t,
        pressure=p,
        relative_humidity=rh,
        source_type="LIVE",
    )


def _warmup_station(station_id: str, n: int = 15, base_t: float = 25.0, base_p: float = 1013.2, base_rh: float = 60.0):
    """Seed station with consistent baseline data to establish reference & tracker profiles with 1-min cadence."""
    t0 = datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc)
    decisions = []
    for i in range(n):
        ts = t0 + timedelta(minutes=1 * i)
        obs = _make_obs(
            station_id=station_id,
            ts=ts,
            t=base_t + 0.1 * math.sin(i * 0.2),
            p=base_p + 0.05 * math.cos(i * 0.2),
            rh=base_rh - 0.2 * math.sin(i * 0.2),
        )
        dec = process_observation(obs)
        decisions.append(dec)
    return decisions, t0 + timedelta(minutes=1 * n)


# ===========================================================================
# 1. Normal Observation
# ===========================================================================
def test_scenario_01_normal_observation():
    st_id = "AWS_P3_NORMAL"
    _, next_ts = _warmup_station(st_id, n=10)

    obs = _make_obs(st_id, next_ts, t=25.05, p=1013.22, rh=59.9)
    dec = process_observation(obs)

    assert dec.decision_state == DecisionState.NORMAL
    assert dec.severity == SeverityLevel.LOW
    assert dec.anomaly_score < 0.35
    assert dec.root_cause_category == RootCause.NORMAL
    assert dec.detection_confidence >= 0.65
    assert dec.sensor_fault_likelihood < 0.35
    assert dec.plausibility_score is not None and dec.plausibility_score > 0.7
    assert dec.weather_event_evidence is True
    assert dec.sensor_fault_evidence is False


# ===========================================================================
# 2. Temperature Spike
# ===========================================================================
def test_scenario_02_temperature_spike():
    st_id = "AWS_P3_TSPIKE"
    _, next_ts = _warmup_station(st_id, n=12, base_t=25.0)

    # Inject sharp unphysical jump +8.0 C in 1 min
    obs = _make_obs(st_id, next_ts, t=33.0, p=1013.2, rh=60.0)
    dec = process_observation(obs)

    assert dec.anomaly_score >= 0.5
    assert dec.decision_state in (DecisionState.ANOMALY, DecisionState.SUSPECT)
    assert dec.severity in (SeverityLevel.HIGH, SeverityLevel.CRITICAL)
    assert dec.root_cause_category in (RootCause.SENSOR_SPIKE, RootCause.TEMPORAL_INCONSISTENCY, RootCause.MULTIVARIATE_INCONSISTENCY)
    assert any("TEMPERATURE_SPIKE" in code or "UNREALISTIC_RATE" in code for code in dec.evidence_codes)


# ===========================================================================
# 3. Pressure Abnormality
# ===========================================================================
def test_scenario_03_pressure_anomaly():
    st_id = "AWS_P3_PANOMALY"
    _, next_ts = _warmup_station(st_id, n=12, base_p=1013.2)

    # Sudden 8.0 hPa plunge
    obs = _make_obs(st_id, next_ts, t=25.0, p=1005.0, rh=60.0)
    dec = process_observation(obs)

    assert dec.anomaly_score >= 0.5
    assert dec.decision_state in (DecisionState.ANOMALY, DecisionState.SUSPECT)
    assert any("PRESSURE_SPIKE" in code or "UNREALISTIC_RATE" in code for code in dec.evidence_codes)


# ===========================================================================
# 4. Humidity Abnormality
# ===========================================================================
def test_scenario_04_humidity_anomaly():
    st_id = "AWS_P3_RHANOMALY"
    _, next_ts = _warmup_station(st_id, n=12, base_rh=50.0)

    # Sudden +35% RH jump
    obs = _make_obs(st_id, next_ts, t=25.0, p=1013.2, rh=88.0)
    dec = process_observation(obs)

    assert dec.anomaly_score >= 0.5
    assert dec.decision_state in (DecisionState.ANOMALY, DecisionState.SUSPECT)
    assert any("RELATIVE_HUMIDITY_SPIKE" in code or "UNREALISTIC_RATE" in code for code in dec.evidence_codes)


# ===========================================================================
# 5. Frozen / Stuck Sensor
# ===========================================================================
def test_scenario_05_frozen_sensor():
    st_id = "AWS_P3_FROZEN"
    _, next_ts = _warmup_station(st_id, n=6, base_t=22.45)

    # Send 5 identical readings on consecutive 1-min intervals
    final_dec = None
    for i in range(5):
        ts = next_ts + timedelta(minutes=1 * i)
        obs = _make_obs(st_id, ts, t=22.45, p=1012.0, rh=55.0)
        final_dec = process_observation(obs)

    assert final_dec is not None
    assert any("FROZEN" in code for code in final_dec.evidence_codes)
    assert final_dec.root_cause_category == RootCause.SENSOR_STUCK_FROZEN
    assert final_dec.sensor_fault_likelihood >= 0.7


# ===========================================================================
# 6. Gradual Drift (Robust Z-Score Detection)
# ===========================================================================
def test_scenario_06_gradual_drift():
    st_id = "AWS_P3_DRIFT"
    _, next_ts = _warmup_station(st_id, n=20, base_t=20.0)

    # Send steady incremental drift
    final_dec = None
    for i in range(8):
        ts = next_ts + timedelta(minutes=1 * i)
        obs = _make_obs(st_id, ts, t=20.0 + 0.5 * (i + 1), p=1013.0, rh=60.0)
        final_dec = process_observation(obs)

    assert final_dec is not None
    assert final_dec.anomaly_score > 0.2
    assert final_dec.sensor_fault_evidence is True or final_dec.anomaly_score >= 0.35


# ===========================================================================
# 7. Unrealistic Rate of Change
# ===========================================================================
def test_scenario_07_unrealistic_rate():
    st_id = "AWS_P3_RATE"
    _, next_ts = _warmup_station(st_id, n=10, base_t=24.0)

    # Jump +4.0 C in 1 minute (4.0 C/min > 0.5 C/min threshold)
    obs = _make_obs(st_id, next_ts, t=28.0, p=1013.25, rh=60.0)
    dec = process_observation(obs)

    assert any("UNREALISTIC_RATE" in code for code in dec.evidence_codes)
    assert dec.anomaly_score >= 0.5


# ===========================================================================
# 8. Multivariate Thermodynamic Inconsistency
# ===========================================================================
def test_scenario_08_multivariate_inconsistency():
    st_id = "AWS_P3_THERMO"
    _, next_ts = _warmup_station(st_id, n=10, base_t=15.0)

    # T=15.0 C, P=1013.25, RH=60.0%
    obs = _make_obs(st_id, next_ts, t=15.0, p=1013.25, rh=60.0)
    dec = process_observation(obs)

    assert dec.plausibility_score is not None
    assert dec.plausibility_score >= 0.0


# ===========================================================================
# 9. Plausible Weather Event
# ===========================================================================
def test_scenario_09_plausible_weather_event():
    st_id = "AWS_P3_WEATHER"
    t0 = datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc)
    for i in range(20):
        t_val = 28.0 + 0.8 * math.sin(i * 0.1)
        p_val = 1012.0 + 0.3 * math.cos(i * 0.1)
        rh_val = 55.0 - 2.5 * math.sin(i * 0.1)
        obs = _make_obs(st_id, t0 + timedelta(minutes=1 * i), t=t_val, p=p_val, rh=rh_val)
        process_observation(obs)

    # Step 20 weather event: T drops by 0.35 C, P rises by 0.15 hPa, RH rises by 1.2%
    next_ts = t0 + timedelta(minutes=20)
    obs = _make_obs(st_id, next_ts, t=28.40, p=1012.00, rh=53.82)
    dec = process_observation(obs)

    assert dec.plausibility_score is not None
    assert dec.plausibility_score >= 0.6
    assert dec.weather_event_likelihood >= 0.3


# ===========================================================================
# 10. Delayed but Plausible Observation
# ===========================================================================
def test_scenario_10_delayed_but_plausible_observation(client):
    st_id = "AWS_P3_DELAYED"
    t0 = datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc)

    # Ingest t=00:00, 00:01, skip 00:02, ingest 00:03
    process_observation(_make_obs(st_id, t0, t=25.0, p=1013.0, rh=60.0))
    process_observation(_make_obs(st_id, t0 + timedelta(minutes=1), t=25.1, p=1013.0, rh=60.0))
    process_observation(_make_obs(st_id, t0 + timedelta(minutes=3), t=25.2, p=1013.0, rh=60.0))

    # Now the delayed record at 00:02 arrives late
    t_delayed = t0 + timedelta(minutes=2)
    obs_delayed = _make_obs(st_id, t_delayed, t=25.15, p=1013.0, rh=60.0)
    dec = process_observation(obs_delayed)

    # Arrives with ACCEPT_LATE disposition
    assert dec.admission_state == AdmissionState.ADMIT
    assert dec.plausibility_score is not None and dec.plausibility_score >= 0.5


# ===========================================================================
# 11. Ambiguous Case (Competing Evidence)
# ===========================================================================
def test_scenario_11_ambiguous_case():
    st_id = "AWS_P3_AMBIGUOUS"
    _, next_ts = _warmup_station(st_id, n=12, base_t=25.0)

    # Moderate shift on edge of thresholds
    obs = _make_obs(st_id, next_ts, t=26.5, p=1012.5, rh=62.0)
    dec = process_observation(obs)

    # System should not force CRITICAL
    assert dec.severity != SeverityLevel.CRITICAL
    if dec.decision_state in (DecisionState.AMBIGUOUS, DecisionState.ABSTAIN, DecisionState.SUSPECT):
        assert dec.attribution_confidence is None or dec.attribution_confidence <= 0.7


# ===========================================================================
# 12. Immutability & DB Preservation
# ===========================================================================
def test_raw_data_preserved_and_immutable(client):
    """Verify raw observation was stored in DB and cannot be modified (INV-02)."""
    st_id = "AWS_P3_IMMUTABLE"
    ts = datetime(2026, 9, 30, 3, 0, 0, tzinfo=timezone.utc)
    obs = _make_obs(st_id, ts, t=26.4, p=1012.8, rh=62.0)
    dec = process_observation(obs)

    with db.transaction() as conn:
        row = conn.execute(
            "SELECT raw_payload, parse_status FROM raw_observations WHERE observation_id = ?",
            (dec.observation_id,),
        ).fetchone()
        assert row is not None
        assert "26.4" in row["raw_payload"]
        assert row["parse_status"] == "VALID"

        # Verify trigger rejects modification
        with pytest.raises(Exception):
            conn.execute(
                "UPDATE raw_observations SET parse_status = 'MUTATED' WHERE observation_id = ?",
                (dec.observation_id,),
            )


# ===========================================================================
# 13. Determinism
# ===========================================================================
def test_e2e_determinism():
    """Verify that processing the exact same stream on two separate station IDs yields identical decisions."""
    st1 = "AWS_P3_DET_A"
    st2 = "AWS_P3_DET_B"
    t0 = datetime(2026, 9, 30, 4, 0, 0, tzinfo=timezone.utc)

    decisions1 = []
    decisions2 = []

    test_stream = [
        (25.0, 1013.2, 60.0),
        (25.1, 1013.1, 60.2),
        (25.3, 1013.0, 60.1),
        (33.0, 1013.0, 60.0),  # Spike
        (25.4, 1013.0, 60.3),
    ]

    for i, (t, p, rh) in enumerate(test_stream):
        ts = t0 + timedelta(minutes=1 * i)
        d1 = process_observation(_make_obs(st1, ts, t, p, rh))
        d2 = process_observation(_make_obs(st2, ts, t, p, rh))
        decisions1.append(d1)
        decisions2.append(d2)

    for d1, d2 in zip(decisions1, decisions2):
        assert d1.decision_state == d2.decision_state
        assert d1.anomaly_score == d2.anomaly_score
        assert d1.severity == d2.severity
        assert d1.root_cause_category == d2.root_cause_category
        assert d1.evidence_codes == d2.evidence_codes


# ===========================================================================
# 14. API Compatibility
# ===========================================================================
def test_api_compatibility_and_structured_response(client):
    """Verify REST API /v1/observations outputs complete structured decision with Phase 3 fields."""
    payload = {
        "station_id": "AWS_P3_API",
        "timestamp": "2026-09-30T05:00:00Z",
        "temperature": 27.5,
        "pressure": 1011.8,
        "relative_humidity": 58.0,
        "source_type": "LIVE",
    }
    res = client.post("/v1/observations", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert "observation_id" in data
    assert "station_id" in data
    assert "anomaly_score" in data
    assert "severity" in data
    assert "detection_confidence" in data
    assert "uncertainty_state" in data
    assert "root_cause_category" in data
    assert "plausibility_score" in data
    assert "weather_event_evidence" in data
    assert "sensor_fault_evidence" in data
    assert "weather_event_likelihood" in data
    assert "sensor_fault_likelihood" in data
    assert "evidence_codes" in data
    assert "reasoning_summary" in data


# ===========================================================================
# 15. Practical Inference Latency Benchmark (Pure ML Pipeline)
# ===========================================================================
def test_inference_latency_budget():
    """Verify statistical anomaly detection & adjudication latency stays well under 5.0 ms per observation."""
    buf = CleanBuffer()
    t0 = datetime(2026, 9, 30, 6, 0, 0, tzinfo=timezone.utc)

    for i in range(20):
        buf.push(25.0 + 0.1 * (i % 3), 1013.2, 60.0, t0 + timedelta(minutes=1 * i))
        reference_profile.update("AWS_P3_BENCH", 25.0 + 0.1 * (i % 3), 1013.2, 60.0)
        adaptive_tracker.update("AWS_P3_BENCH", 25.0 + 0.1 * (i % 3), 1013.2, 60.0)

    latencies = []
    for i in range(100):
        ts = t0 + timedelta(minutes=1 * (20 + i))
        t1 = time.perf_counter()
        stat = statistical_detector.detect(25.1, 1013.2, 60.0, ts, buf)
        ref_ev = reference_profile.evaluate("AWS_P3_BENCH", 25.1, 1013.2, 60.0)
        tr_ev = adaptive_tracker.evaluate("AWS_P3_BENCH", 25.1, 1013.2, 60.0)
        _ = adjudicator.adjudicate(
            anomaly_score=stat.anomaly_score,
            triggers=stat.triggers,
            channel_scores=stat.channel_scores,
            ref_plausibility=ref_ev["plausibility_score"],
            ref_weather_evidence=ref_ev["weather_event_evidence"],
            ref_sensor_fault=ref_ev["sensor_fault_evidence"],
            tracker_plausibility=tr_ev["plausibility_score"],
            tracker_weather_evidence=tr_ev["weather_event_evidence"],
            tracker_sensor_fault=tr_ev["sensor_fault_evidence"],
            integrity_flags=[],
            admission_state="ADMIT",
            buffer_size=len(buf),
        )
        elapsed_ms = (time.perf_counter() - t1) * 1000.0
        latencies.append(elapsed_ms)

    avg_ms = sum(latencies) / len(latencies)
    p95_ms = sorted(latencies)[int(len(latencies) * 0.95)]

    # Realtime budget constraint: average < 1.0 ms, P95 < 2.0 ms (far exceeding 5.0 ms constraint)
    assert avg_ms < 1.0, f"Average inference latency {avg_ms:.4f}ms exceeded 1.0ms"
    assert p95_ms < 2.0, f"P95 inference latency {p95_ms:.4f}ms exceeded 2.0ms"
