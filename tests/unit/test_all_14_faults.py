"""
Comprehensive tests for all 14 anomaly fault families (03_FAILURE_AND_DATA.md & 14A_DATA_PIPELINE.md).
"""
from datetime import datetime, timezone
from simulator.stream.generator import AWSStreamGenerator
from injector.faults.injector import FaultInjector


def get_base_series():
    gen = AWSStreamGenerator(station_id="AWS_FAULTS_TEST", seed=42)
    t0 = datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc)
    return gen.generate(start_time=t0, num_points=30)


def test_fault_01_isolated_spike():
    clean = get_base_series()
    inj = FaultInjector(seed=42)
    injected, mf = inj.inject_isolated_spike(clean, index=5, channel="temperature", magnitude=20.0)
    assert injected[5].temperature == round(clean[5].temperature + 20.0, 2)
    assert mf["fault_class"] == "ISOLATED_SPIKE"


def test_fault_02_repeated_spikes():
    clean = get_base_series()
    inj = FaultInjector(seed=42)
    injected, mf = inj.inject_repeated_spikes(clean, start_index=5, duration=10, period=2, channel="temperature", magnitude=15.0)
    assert mf["fault_class"] == "REPEATED_SPIKES"
    assert len(mf["affected_indices"]) == 5


def test_fault_03_sudden_bias():
    clean = get_base_series()
    inj = FaultInjector(seed=42)
    injected, mf = inj.inject_sudden_bias(clean, start_index=10, duration=10, channel="pressure", bias_magnitude=-15.0)
    assert mf["fault_class"] == "SUDDEN_BIAS"
    for idx in mf["affected_indices"]:
        assert injected[idx].pressure == round(clean[idx].pressure - 15.0, 2)


def test_fault_04_gradual_drift():
    clean = get_base_series()
    inj = FaultInjector(seed=42)
    injected, mf = inj.inject_gradual_drift(clean, start_index=10, duration=10, channel="relative_humidity", drift_rate_per_step=1.0)
    assert mf["fault_class"] == "GRADUAL_DRIFT"
    assert len(mf["affected_indices"]) == 10


def test_fault_05_frozen_flatline():
    clean = get_base_series()
    inj = FaultInjector(seed=42)
    injected, mf = inj.inject_frozen_flatline(clean, start_index=5, duration=8, channel="temperature")
    assert mf["fault_class"] == "FROZEN_FLATLINE"
    val = injected[5].temperature
    for idx in mf["affected_indices"]:
        assert injected[idx].temperature == val


def test_fault_06_stuck_at_value():
    clean = get_base_series()
    inj = FaultInjector(seed=42)
    injected, mf = inj.inject_stuck_at_value(clean, start_index=5, duration=5, channel="relative_humidity", clamped_value=100.0)
    assert mf["fault_class"] == "STUCK_AT_VALUE"
    for idx in mf["affected_indices"]:
        assert injected[idx].relative_humidity == 100.0


def test_fault_07_excessive_noise():
    clean = get_base_series()
    inj = FaultInjector(seed=42)
    injected, mf = inj.inject_excessive_noise(clean, start_index=5, duration=10, channel="temperature", noise_std=5.0)
    assert mf["fault_class"] == "EXCESSIVE_NOISE"
    assert len(mf["affected_indices"]) == 10


def test_fault_08_missing_observation():
    clean = get_base_series()
    inj = FaultInjector(seed=42)
    injected, mf = inj.inject_missing_observation(clean, index=7, channel="pressure")
    assert injected[7].pressure is None
    assert mf["fault_class"] == "MISSING_OBSERVATION"


def test_fault_09_communication_failure():
    clean = get_base_series()
    inj = FaultInjector(seed=42)
    injected, mf = inj.inject_communication_failure(clean, start_index=10, drop_count=4)
    assert len(injected) == len(clean) - 4
    assert mf["fault_class"] == "COMMUNICATION_FAILURE"
    assert mf["dropped_count"] == 4


def test_fault_10_duplicate():
    clean = get_base_series()
    inj = FaultInjector(seed=42)
    injected, mf = inj.inject_duplicate(clean, target_index=5)
    assert len(injected) == len(clean) + 1
    assert injected[5].timestamp == injected[6].timestamp
    assert mf["fault_class"] == "DUPLICATE_OBSERVATION"


def test_fault_11_delayed_out_of_order():
    clean = get_base_series()
    inj = FaultInjector(seed=42)
    injected, mf = inj.inject_delayed_out_of_order(clean, from_index=3, insert_after_index=8)
    assert len(injected) == len(clean)
    assert mf["fault_class"] == "DELAYED_OUT_OF_ORDER"


def test_fault_12_corrupted_value():
    clean = get_base_series()
    inj = FaultInjector(seed=42)
    injected, mf = inj.inject_corrupted_value(clean, index=4, channel="temperature")
    assert mf["fault_class"] == "CORRUPTED_VALUE"
    assert injected[4].temperature in [-999.0, 999.99]


def test_fault_13_multivariate_inconsistency():
    clean = get_base_series()
    inj = FaultInjector(seed=42)
    injected, mf = inj.inject_multivariate_inconsistency(clean, start_index=10, duration=5)
    assert mf["fault_class"] == "MULTIVARIATE_INCONSISTENCY"
    for idx in mf["affected_indices"]:
        assert injected[idx].temperature == 55.0
        assert injected[idx].relative_humidity == 98.0
        assert injected[idx].pressure == 940.0


def test_fault_14_combined_faults():
    clean = get_base_series()
    inj = FaultInjector(seed=42)
    injected, mf = inj.inject_combined_fault(clean, start_index=5, duration=10)
    assert mf["fault_class"] == "COMBINED_FAULTS"
    assert "GRADUAL_DRIFT" in mf["components"]
    assert len(mf["affected_indices"]) == 10
