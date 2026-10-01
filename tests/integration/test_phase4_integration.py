import time
import math
import statistics
from typing import List

import pytest
from datetime import datetime, timezone, timedelta

from app.runtime.engine import process_observation
from ingestion.schemas.observation import ObservationIn
from ingestion.schemas.response import DecisionState, SeverityLevel, AdmissionState
from detection.decision.adjudicator import RootCause

def _make_obs(
    station_id: str,
    ts: datetime,
    t: float | None = 25.0,
    p: float | None = 1013.25,
    rh: float | None = 60.0,
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
    t0 = datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc)
    for i in range(n):
        ts = t0 + timedelta(minutes=1 * i)
        obs = _make_obs(
            station_id=station_id,
            ts=ts,
            t=base_t + 0.1 * math.sin(i * 0.2),
            p=base_p + 0.05 * math.cos(i * 0.2),
            rh=base_rh - 0.2 * math.sin(i * 0.2),
        )
        process_observation(obs)
    return t0 + timedelta(minutes=1 * n)

latency_records: List[float] = []

def _timed_process(obs: ObservationIn):
    t0 = time.perf_counter()
    dec = process_observation(obs)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    latency_records.append(elapsed_ms)
    return dec

def test_scenario_01_normal():
    st_id = "AWS_P4_NORMAL"
    next_ts = _warmup_station(st_id, n=10)
    obs = _make_obs(st_id, next_ts, t=25.05, p=1013.22, rh=59.9)
    dec = _timed_process(obs)
    assert dec.decision_state == DecisionState.NORMAL
    assert dec.severity == SeverityLevel.LOW
    assert dec.anomaly_score < 0.35
    assert st_id in dec.observation_id

def test_scenario_02_temperature_spike():
    st_id = "AWS_P4_TSPIKE"
    next_ts = _warmup_station(st_id, n=12, base_t=25.0)
    obs = _make_obs(st_id, next_ts, t=33.0, p=1013.2, rh=60.0)
    dec = _timed_process(obs)
    assert dec.decision_state in (DecisionState.ANOMALY, DecisionState.SUSPECT)
    assert dec.anomaly_score >= 0.5
    assert st_id in dec.observation_id

def test_scenario_03_pressure_anomaly():
    st_id = "AWS_P4_PANOMALY"
    next_ts = _warmup_station(st_id, n=12, base_p=1013.2)
    obs = _make_obs(st_id, next_ts, t=25.0, p=1005.0, rh=60.0)
    dec = _timed_process(obs)
    assert dec.decision_state in (DecisionState.ANOMALY, DecisionState.SUSPECT)
    assert dec.anomaly_score >= 0.5

def test_scenario_04_humidity_anomaly():
    st_id = "AWS_P4_RHANOMALY"
    next_ts = _warmup_station(st_id, n=12, base_rh=50.0)
    obs = _make_obs(st_id, next_ts, t=25.0, p=1013.2, rh=88.0)
    dec = _timed_process(obs)
    assert dec.decision_state in (DecisionState.ANOMALY, DecisionState.SUSPECT)
    assert dec.anomaly_score >= 0.5

def test_scenario_05_frozen_sensor():
    st_id = "AWS_P4_FROZEN"
    next_ts = _warmup_station(st_id, n=6, base_t=22.45)
    dec = None
    for i in range(5):
        ts = next_ts + timedelta(minutes=1 * i)
        obs = _make_obs(st_id, ts, t=22.45, p=1012.0, rh=55.0)
        dec = _timed_process(obs)
    assert dec is not None
    assert any("FROZEN" in code for code in dec.evidence_codes)
    assert dec.root_cause_category == RootCause.SENSOR_STUCK_FROZEN

def test_scenario_06_drift():
    st_id = "AWS_P4_DRIFT"
    next_ts = _warmup_station(st_id, n=20, base_t=20.0)
    dec = None
    for i in range(8):
        ts = next_ts + timedelta(minutes=1 * i)
        obs = _make_obs(st_id, ts, t=20.0 + 0.5 * (i + 1), p=1013.0, rh=60.0)
        dec = _timed_process(obs)
    assert dec is not None
    assert dec.anomaly_score > 0.2

def test_scenario_07_multivariate_inconsistency():
    st_id = "AWS_P4_THERMO"
    next_ts = _warmup_station(st_id, n=10, base_t=15.0)
    obs = _make_obs(st_id, next_ts, t=15.0, p=1013.25, rh=60.0)
    dec = _timed_process(obs)
    assert dec.plausibility_score is not None

def test_scenario_08_delayed_observation():
    st_id = "AWS_P4_DELAYED"
    t0 = datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc)
    process_observation(_make_obs(st_id, t0, t=25.0, p=1013.0, rh=60.0))
    process_observation(_make_obs(st_id, t0 + timedelta(minutes=1), t=25.1, p=1013.0, rh=60.0))
    process_observation(_make_obs(st_id, t0 + timedelta(minutes=3), t=25.2, p=1013.0, rh=60.0))
    
    t_delayed = t0 + timedelta(minutes=2)
    obs_delayed = _make_obs(st_id, t_delayed, t=25.15, p=1013.0, rh=60.0)
    dec = _timed_process(obs_delayed)
    assert dec.admission_state == AdmissionState.ADMIT
    assert dec.integrity_flags and any("LATE" in str(f) or "DELAYED" in str(f) for f in dec.integrity_flags)

def test_scenario_09_missing_values():
    st_id = "AWS_P4_MISSING"
    t0 = datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc)
    obs = _make_obs(st_id, t0, t=None, p=None, rh=None)
    dec = _timed_process(obs)
    assert dec.integrity_flags and any("MISSING" in str(f) for f in dec.integrity_flags)

def test_scenario_10_duplicate_and_conflicting():
    st_id = "AWS_P4_DUP"
    t0 = datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc)
    obs1 = _make_obs(st_id, t0, t=25.0, p=1013.0, rh=60.0)
    process_observation(obs1)
    
    # Duplicate
    obs_dup = _make_obs(st_id, t0, t=25.0, p=1013.0, rh=60.0)
    dec_dup = _timed_process(obs_dup)
    assert dec_dup.integrity_flags and any("DUPLICATE" in str(f) for f in dec_dup.integrity_flags)

    # Conflicting duplicate
    obs_conf = _make_obs(st_id, t0, t=30.0, p=1013.0, rh=60.0)
    dec_conf = _timed_process(obs_conf)
    assert dec_conf.integrity_flags and any("CONFLICT" in str(f) for f in dec_conf.integrity_flags)

def test_scenario_11_ambiguous_case():
    st_id = "AWS_P4_AMBIGUOUS"
    next_ts = _warmup_station(st_id, n=12, base_t=25.0)
    obs = _make_obs(st_id, next_ts, t=26.5, p=1012.5, rh=62.0)
    dec = _timed_process(obs)
    assert dec.severity != SeverityLevel.CRITICAL

def test_phase4_inference_latency_benchmark():
    """Verify statistical anomaly detection & adjudication latency stays well under 5.0 ms per observation."""
    from features.builder import CleanBuffer
    from detection.triggers.statistical import statistical_detector
    from detection.reference.baseline import reference_profile
    from detection.tracker.tracker import adaptive_tracker
    from detection.decision.adjudicator import adjudicator

    buf = CleanBuffer()
    t0 = datetime(2026, 9, 30, 6, 0, 0, tzinfo=timezone.utc)

    for i in range(20):
        buf.push(25.0 + 0.1 * (i % 3), 1013.2, 60.0, t0 + timedelta(minutes=1 * i))
        reference_profile.update("AWS_P4_BENCH", 25.0 + 0.1 * (i % 3), 1013.2, 60.0)
        adaptive_tracker.update("AWS_P4_BENCH", 25.0 + 0.1 * (i % 3), 1013.2, 60.0)

    latencies = []
    for i in range(100):
        ts = t0 + timedelta(minutes=1 * (20 + i))
        t1 = time.perf_counter()
        stat = statistical_detector.detect(25.1, 1013.2, 60.0, ts, buf)
        ref_ev = reference_profile.evaluate("AWS_P4_BENCH", 25.1, 1013.2, 60.0)
        tr_ev = adaptive_tracker.evaluate("AWS_P4_BENCH", 25.1, 1013.2, 60.0)
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

    assert avg_ms < 2.0, f"Average inference latency {avg_ms:.4f}ms exceeded 2.0ms"
    assert p95_ms < 5.0, f"P95 inference latency {p95_ms:.4f}ms exceeded 5.0ms"

def test_phase4_e2e_pipeline_latency_summary():
    assert len(latency_records) >= 10, "Not enough latency records collected"
    avg_latency = statistics.mean(latency_records)
    p95_latency = statistics.quantiles(latency_records, n=100)[94] if len(latency_records) >= 100 else max(latency_records)
    # Full disk-bound synchronous SQLite per-observation write budget (e2e)
    assert avg_latency < 500.0, f"Average e2e latency too high: {avg_latency:.2f} ms"
    assert p95_latency < 1000.0, f"P95 e2e latency too high: {p95_latency:.2f} ms"
    global LATENCY_METRICS
    LATENCY_METRICS = {
        "e2e_average_ms": round(avg_latency, 3),
        "e2e_p95_ms": round(p95_latency, 3),
        "total_observations": len(latency_records),
    }
