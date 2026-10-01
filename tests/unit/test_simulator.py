"""
Unit tests for AWS stream generator and replayer.
"""
from datetime import datetime, timezone
from simulator.stream.generator import AWSStreamGenerator
from simulator.replay.replayer import StreamReplayer
from ingestion.schemas.observation import SourceType


def test_generator_fields_and_bounds():
    gen = AWSStreamGenerator(station_id="AWS_SIM_TEST", seed=99)
    t0 = datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc)
    obs_list = gen.generate(start_time=t0, num_points=24)

    assert len(obs_list) == 24
    for obs in obs_list:
        assert obs.station_id == "AWS_SIM_TEST"
        assert obs.source_type == SourceType.SIMULATED
        assert -80.0 <= obs.temperature <= 70.0
        assert 300.0 <= obs.pressure <= 1100.0
        assert 0.0 <= obs.relative_humidity <= 100.0


def test_replayer_processes_all():
    gen = AWSStreamGenerator(station_id="AWS_REPLAY_TEST", seed=10)
    t0 = datetime(2026, 9, 30, 6, 0, 0, tzinfo=timezone.utc)
    obs_list = gen.generate(start_time=t0, num_points=5)

    replayer = StreamReplayer()
    decisions = replayer.replay(obs_list)

    assert len(decisions) == 5
    for dec in decisions:
        assert dec.station_id == "AWS_REPLAY_TEST"
        assert dec.disposition.value == "ACCEPT"
