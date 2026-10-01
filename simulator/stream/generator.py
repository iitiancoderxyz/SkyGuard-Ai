"""
AWS Stream Generator: Generates synthetic, physically plausible clean T/P/RH time series
with deterministic diurnal cycles and reproducible random seeds.
Scope strictly limited to Temperature, Pressure, and Relative Humidity.
"""
import math
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Generator, List, Dict, Any, Optional
from ingestion.schemas.observation import ObservationIn, SourceType


class AWSStreamGenerator:
    def __init__(
        self,
        station_id: str = "AWS_001",
        base_temp: float = 25.0,
        temp_amplitude: float = 8.0,
        base_pressure: float = 1013.25,
        base_rh: float = 65.0,
        latitude: float = 23.1765,
        longitude: float = 79.9864,
        elevation: float = 411.0,
        cadence_seconds: int = 60,
        seed: int = 42,
    ):
        self.station_id = station_id
        self.base_temp = base_temp
        self.temp_amplitude = temp_amplitude
        self.base_pressure = base_pressure
        self.base_rh = base_rh
        self.latitude = latitude
        self.longitude = longitude
        self.elevation = elevation
        self.cadence_seconds = cadence_seconds
        self.rng = np.random.RandomState(seed)

    def generate(
        self,
        start_time: datetime,
        num_points: int,
    ) -> List[ObservationIn]:
        """
        Generate a sequence of clean observations.
        """
        observations: List[ObservationIn] = []
        current_time = start_time

        for i in range(num_points):
            # Diurnal cycle modeling
            hour = current_time.hour + (current_time.minute / 60.0) + (current_time.second / 3600.0)
            
            # Solar peak around 14:00 (phase offset ~ -14h)
            rad = 2 * math.pi * (hour - 14.0) / 24.0
            diurnal_temp = self.temp_amplitude * math.cos(rad)
            noise_temp = self.rng.normal(0, 0.2)
            temp = round(self.base_temp + diurnal_temp + noise_temp, 2)

            # Pressure diurnal tide (~ 2 hPa semidiurnal variation)
            tide = 1.2 * math.cos(4 * math.pi * (hour - 10.0) / 24.0)
            noise_p = self.rng.normal(0, 0.1)
            pressure = round(self.base_pressure + tide + noise_p, 2)

            # RH typically inversely correlated with temperature
            diurnal_rh = -1.5 * diurnal_temp
            noise_rh = self.rng.normal(0, 0.5)
            rh = max(5.0, min(99.0, round(self.base_rh + diurnal_rh + noise_rh, 1)))

            obs = ObservationIn(
                station_id=self.station_id,
                timestamp=current_time,
                temperature=temp,
                pressure=pressure,
                relative_humidity=rh,
                latitude=self.latitude,
                longitude=self.longitude,
                elevation=self.elevation,
                source_type=SourceType.SIMULATED,
                source_sequence=str(i + 1),
            )
            observations.append(obs)
            current_time += timedelta(seconds=self.cadence_seconds)

        return observations
