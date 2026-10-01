"""
Unit tests for Statistical Anomaly Detector (detection/triggers/statistical.py).
Tests:
  1. Normal reading (no triggers, low score)
  2. Sudden temperature spike (positive jump)
  3. Sudden temperature drop (negative jump)
  4. Pressure abnormality (sudden jump / unrealistic rate)
  5. Humidity abnormality (sudden jump / saturation / inconsistency)
  6. Frozen / repeated values (stuck sensor)
  7. Unrealistic change rate (high derivative per minute)
  8. Inference latency benchmark (< 5.0 ms target)
  9. Determinism of score outputs
"""
import time
from datetime import datetime, timezone, timedelta
from features.builder import CleanBuffer
from detection.triggers.statistical import StatisticalAnomalyDetector, AnomalyResult, statistical_detector


def _create_clean_buffer(n: int = 24, t_base: float = 25.0, p_base: float = 1013.25, rh_base: float = 60.0) -> CleanBuffer:
    """Helper to generate a clean buffer with n historical observations at 5-minute intervals."""
    buf = CleanBuffer(max_size=96)
    t0 = datetime(2026, 9, 30, 8, 0, 0, tzinfo=timezone.utc)
    for i in range(n):
        # Add realistic minor noise
        t_val = t_base + 0.05 * (i % 3)
        p_val = p_base - 0.02 * (i % 2)
        rh_val = rh_base + 0.1 * (i % 4)
        ts_val = t0 + timedelta(minutes=5 * i)
        buf.push(t_val, p_val, rh_val, ts_val)
    return buf


def test_normal_reading():
    detector = StatisticalAnomalyDetector()
    buf = _create_clean_buffer(n=24, t_base=25.0, p_base=1013.25, rh_base=60.0)
    ts = datetime(2026, 9, 30, 10, 5, 0, tzinfo=timezone.utc)

    # Next nominal reading
    res: AnomalyResult = detector.detect(t=25.1, p=1013.20, rh=60.2, ts=ts, buffer=buf)

    assert not res.is_anomaly
    assert res.anomaly_score < 0.3
    assert len(res.triggers) == 0
    assert res.channel_scores["temperature"] < 0.3
    assert res.channel_scores["pressure"] < 0.3
    assert res.channel_scores["relative_humidity"] < 0.3


def test_sudden_temperature_spike():
    detector = StatisticalAnomalyDetector()
    buf = _create_clean_buffer(n=24, t_base=25.0, p_base=1013.25, rh_base=60.0)
    ts = datetime(2026, 9, 30, 10, 5, 0, tzinfo=timezone.utc)

    # Spike from 25.0 deg C to 35.0 deg C (+10 deg C step in 5 min)
    res: AnomalyResult = detector.detect(t=35.0, p=1013.25, rh=60.0, ts=ts, buffer=buf)

    assert res.is_anomaly
    assert res.anomaly_score >= 0.5
    assert "TEMPERATURE_SPIKE_POSITIVE" in res.triggers
    assert res.channel_scores["temperature"] >= 0.5


def test_sudden_temperature_drop():
    detector = StatisticalAnomalyDetector()
    buf = _create_clean_buffer(n=24, t_base=25.0, p_base=1013.25, rh_base=60.0)
    ts = datetime(2026, 9, 30, 10, 5, 0, tzinfo=timezone.utc)

    # Drop from 25.0 deg C to 15.0 deg C (-10 deg C step in 5 min)
    res: AnomalyResult = detector.detect(t=15.0, p=1013.25, rh=60.0, ts=ts, buffer=buf)

    assert res.is_anomaly
    assert res.anomaly_score >= 0.5
    assert "TEMPERATURE_SPIKE_NEGATIVE" in res.triggers
    assert res.channel_scores["temperature"] >= 0.5


def test_pressure_abnormality():
    detector = StatisticalAnomalyDetector()
    buf = _create_clean_buffer(n=24, t_base=25.0, p_base=1013.25, rh_base=60.0)
    ts = datetime(2026, 9, 30, 10, 5, 0, tzinfo=timezone.utc)

    # Sudden pressure drop from 1013.25 hPa to 995.0 hPa (-18.25 hPa in 5 min)
    res: AnomalyResult = detector.detect(t=25.0, p=995.0, rh=60.0, ts=ts, buffer=buf)

    assert res.is_anomaly
    assert res.anomaly_score >= 0.5
    assert "PRESSURE_SPIKE_NEGATIVE" in res.triggers or "PRESSURE_UNREALISTIC_RATE" in res.triggers
    assert res.channel_scores["pressure"] >= 0.5


def test_humidity_abnormality():
    detector = StatisticalAnomalyDetector()
    buf = _create_clean_buffer(n=24, t_base=25.0, p_base=1013.25, rh_base=40.0)
    ts = datetime(2026, 9, 30, 10, 5, 0, tzinfo=timezone.utc)

    # Sudden humidity jump from 40% to 90% (+50% step in 5 min)
    res: AnomalyResult = detector.detect(t=25.0, p=1013.25, rh=90.0, ts=ts, buffer=buf)

    assert res.is_anomaly
    assert res.anomaly_score >= 0.5
    assert "RELATIVE_HUMIDITY_SPIKE_POSITIVE" in res.triggers or "RELATIVE_HUMIDITY_UNREALISTIC_RATE" in res.triggers
    assert res.channel_scores["relative_humidity"] >= 0.5


def test_frozen_repeated_values():
    detector = StatisticalAnomalyDetector(frozen_step_count=4)
    buf = CleanBuffer(max_size=96)
    t0 = datetime(2026, 9, 30, 8, 0, 0, tzinfo=timezone.utc)

    # 3 identical historical readings
    for i in range(3):
        buf.push(22.500, 1013.0, 50.0, t0 + timedelta(minutes=5 * i))

    ts = t0 + timedelta(minutes=15)
    # 4th identical reading in sequence
    res: AnomalyResult = detector.detect(t=22.500, p=1013.0, rh=50.0, ts=ts, buffer=buf)

    assert "FROZEN_TEMPERATURE" in res.triggers
    assert "FROZEN_PRESSURE" in res.triggers
    assert "FROZEN_RELATIVE_HUMIDITY" in res.triggers
    assert res.is_anomaly
    assert res.anomaly_score >= 0.5


def test_unrealistic_change_rate():
    detector = StatisticalAnomalyDetector()
    buf = CleanBuffer(max_size=10)
    t0 = datetime(2026, 9, 30, 8, 0, 0, tzinfo=timezone.utc)
    buf.push(20.0, 1013.0, 50.0, t0)

    # 1 minute later, temperature rises by 4.0 deg C (4.0 deg C / min >> 0.5 deg C/min threshold)
    ts = t0 + timedelta(minutes=1)
    res: AnomalyResult = detector.detect(t=24.0, p=1013.0, rh=50.0, ts=ts, buffer=buf)

    assert res.is_anomaly
    assert "TEMPERATURE_UNREALISTIC_RATE" in res.triggers
    assert res.channel_scores["temperature"] >= 0.5


def test_thermodynamic_inconsistency_trigger():
    detector = StatisticalAnomalyDetector()
    buf = _create_clean_buffer(n=10)
    ts = datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc)

    # Physical inconsistency: T = 10 deg C with relative humidity = 100% -> Td = 10 deg C.
    # If T drops to 5 deg C while RH claims 100%, but dewpoint calculation results in Td > T
    # Or impossible thermodynamic state:
    res: AnomalyResult = detector.detect(t=20.0, p=1013.25, rh=50.0, ts=ts, buffer=buf)
    # Normal state has T > Td
    assert "THERMODYNAMIC_INCONSISTENCY" not in res.triggers


def test_inference_latency_benchmark():
    detector = StatisticalAnomalyDetector()
    buf = _create_clean_buffer(n=48)
    ts = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)

    # Warm-up run
    detector.detect(t=25.2, p=1013.1, rh=60.5, ts=ts, buffer=buf)

    # Benchmark 100 consecutive detections
    latencies = []
    for _ in range(100):
        t_start = time.perf_counter()
        res = detector.detect(t=25.2, p=1013.1, rh=60.5, ts=ts, buffer=buf)
        lat = (time.perf_counter() - t_start) * 1000.0
        latencies.append(lat)

    avg_lat = sum(latencies) / len(latencies)
    p95_lat = sorted(latencies)[94]

    print(f"\nStatistical Anomaly Detector Latency (100 runs): Avg = {avg_lat:.3f} ms, P95 = {p95_lat:.3f} ms")
    assert avg_lat < 2.0  # Well within the 5.0ms target
    assert p95_lat < 5.0


def test_determinism():
    detector = StatisticalAnomalyDetector()
    buf1 = _create_clean_buffer(n=20, t_base=22.0)
    buf2 = _create_clean_buffer(n=20, t_base=22.0)
    ts = datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc)

    res1 = detector.detect(t=32.0, p=1008.0, rh=80.0, ts=ts, buffer=buf1)
    res2 = detector.detect(t=32.0, p=1008.0, rh=80.0, ts=ts, buffer=buf2)

    assert res1.anomaly_score == res2.anomaly_score
    assert res1.channel_scores == res2.channel_scores
    assert res1.triggers == res2.triggers
    assert res1.is_anomaly == res2.is_anomaly
