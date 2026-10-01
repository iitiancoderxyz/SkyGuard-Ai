"""
Unit tests for FaultInjector.
"""
from datetime import datetime, timezone
from simulator.stream.generator import AWSStreamGenerator
from injector.faults.injector import FaultInjector


def test_injector_spike():
    gen = AWSStreamGenerator(station_id="AWS_INJ_TEST", seed=42)
    t0 = datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc)
    clean = gen.generate(start_time=t0, num_points=10)

    orig_temp = clean[3].temperature
    injector = FaultInjector(seed=42)
    injected, manifest = injector.inject_spike(clean, index=3, channel="temperature", magnitude=20.0)

    assert injected[3].temperature == round(orig_temp + 20.0, 2)
    assert manifest["fault_class"] == "ISOLATED_SPIKE"
    assert manifest["affected_indices"] == [3]


def test_injector_frozen():
    gen = AWSStreamGenerator(station_id="AWS_INJ_TEST", seed=42)
    t0 = datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc)
    clean = gen.generate(start_time=t0, num_points=10)

    injector = FaultInjector(seed=42)
    injected, manifest = injector.inject_frozen(clean, start_index=2, duration=4, channel="relative_humidity")

    stuck_rh = clean[2].relative_humidity
    for i in range(2, 6):
        assert injected[i].relative_humidity == stuck_rh
    assert manifest["fault_class"] == "FROZEN_FLATLINE"
    assert len(manifest["affected_indices"]) == 4


def test_injector_communication_gap():
    gen = AWSStreamGenerator(station_id="AWS_INJ_TEST", seed=42)
    t0 = datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc)
    clean = gen.generate(start_time=t0, num_points=10)

    injector = FaultInjector(seed=42)
    injected, manifest = injector.inject_communication_gap(clean, start_index=3, drop_count=3)

    assert len(injected) == 7
    assert manifest["fault_class"] == "COMMUNICATION_FAILURE"
    assert manifest["dropped_count"] == 3
