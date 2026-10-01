"""
Pre-configured standard scenario suite for demonstration and evaluation.
Combines stream generation, fault injection, and genuine weather events.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
from ingestion.schemas.observation import ObservationIn
from simulator.stream.generator import AWSStreamGenerator
from simulator.stream.multi_station import MultiStationNetwork
from injector.faults.injector import FaultInjector
from injector.weather_surrogates.generator import WeatherEventSimulator


class ScenarioSuite:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.injector = FaultInjector(seed=seed)
        self.weather_sim = WeatherEventSimulator(seed=seed)

    def create_scenario(
        self,
        scenario_name: str,
        station_id: str = "AWS_001",
        num_points: int = 30,
        start_time: datetime = None,
    ) -> Tuple[List[ObservationIn], Dict[str, Any]]:
        """
        Builds a named scenario with clean base, injected fault or genuine event, and sidecar manifest.
        """
        t0 = start_time or datetime(2026, 9, 30, 8, 0, 0, tzinfo=timezone.utc)
        gen = AWSStreamGenerator(station_id=station_id, seed=self.seed)
        clean = gen.generate(start_time=t0, num_points=num_points)

        s_upper = scenario_name.upper()

        if s_upper == "NOMINAL":
            return clean, {"scenario": "NOMINAL", "manifests": []}

        elif s_upper == "SPIKE":
            injected, mf = self.injector.inject_isolated_spike(clean, index=12, channel="temperature", magnitude=25.0)
            return injected, {"scenario": "SPIKE", "manifests": [mf]}

        elif s_upper == "DRIFT":
            injected, mf = self.injector.inject_gradual_drift(clean, start_index=10, duration=15, channel="relative_humidity", drift_rate_per_step=1.5)
            return injected, {"scenario": "DRIFT", "manifests": [mf]}

        elif s_upper == "FLATLINE":
            injected, mf = self.injector.inject_frozen_flatline(clean, start_index=8, duration=12, channel="temperature")
            return injected, {"scenario": "FLATLINE", "manifests": [mf]}

        elif s_upper == "BIAS":
            injected, mf = self.injector.inject_sudden_bias(clean, start_index=10, duration=15, channel="pressure", bias_magnitude=-20.0)
            return injected, {"scenario": "BIAS", "manifests": [mf]}

        elif s_upper == "NOISE":
            injected, mf = self.injector.inject_excessive_noise(clean, start_index=10, duration=15, channel="temperature", noise_std=5.0)
            return injected, {"scenario": "NOISE", "manifests": [mf]}

        elif s_upper == "COMMUNICATION_GAP":
            injected, mf = self.injector.inject_communication_failure(clean, start_index=10, drop_count=4)
            return injected, {"scenario": "COMMUNICATION_GAP", "manifests": [mf]}

        elif s_upper == "MULTIVARIATE_INCONSISTENCY":
            injected, mf = self.injector.inject_multivariate_inconsistency(clean, start_index=10, duration=8)
            return injected, {"scenario": "MULTIVARIATE_INCONSISTENCY", "manifests": [mf]}

        elif s_upper == "GENUINE_WEATHER":
            simulated, mf = self.weather_sim.simulate_cold_front(clean, start_index=10, duration=12, temp_drop=-9.0, rh_surge=40.0, pressure_jump=4.0)
            return simulated, {"scenario": "GENUINE_WEATHER", "manifests": [mf]}

        elif s_upper == "COMBINED":
            injected, mf = self.injector.inject_combined_fault(clean, start_index=8, duration=15)
            return injected, {"scenario": "COMBINED", "manifests": [mf]}

        else:
            raise ValueError(f"Unknown scenario name: {scenario_name}")
