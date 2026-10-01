"""
Multi-Station AWS Network Simulator.
Simulates synchronized or interleaved observation streams across multiple stations
with realistic regional baselines, elevations, and coordinates.
"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from ingestion.schemas.observation import ObservationIn, SourceType
from simulator.stream.generator import AWSStreamGenerator


DEFAULT_STATIONS_CONFIG = [
    {
        "station_id": "AWS_DELHI_01",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "elevation": 216.0,
        "base_temp": 28.0,
        "temp_amplitude": 9.0,
        "base_pressure": 988.0,
        "base_rh": 55.0,
    },
    {
        "station_id": "AWS_MUMBAI_01",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "elevation": 14.0,
        "base_temp": 30.0,
        "temp_amplitude": 5.0,
        "base_pressure": 1010.0,
        "base_rh": 75.0,
    },
    {
        "station_id": "AWS_KOLKATA_01",
        "latitude": 22.5726,
        "longitude": 88.3639,
        "elevation": 9.0,
        "base_temp": 29.5,
        "temp_amplitude": 6.5,
        "base_pressure": 1011.0,
        "base_rh": 78.0,
    },
    {
        "station_id": "AWS_CHENNAI_01",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "elevation": 6.0,
        "base_temp": 31.0,
        "temp_amplitude": 4.5,
        "base_pressure": 1012.0,
        "base_rh": 72.0,
    },
    {
        "station_id": "AWS_BENGALURU_01",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "elevation": 920.0,
        "base_temp": 24.0,
        "temp_amplitude": 7.0,
        "base_pressure": 915.0,
        "base_rh": 60.0,
    },
]


class MultiStationNetwork:
    def __init__(
        self,
        stations_config: Optional[List[Dict[str, Any]]] = None,
        cadence_seconds: int = 60,
        seed: int = 42,
    ):
        self.configs = stations_config or DEFAULT_STATIONS_CONFIG
        self.cadence_seconds = cadence_seconds
        self.generators: Dict[str, AWSStreamGenerator] = {}

        for i, cfg in enumerate(self.configs):
            st_id = cfg["station_id"]
            self.generators[st_id] = AWSStreamGenerator(
                station_id=st_id,
                base_temp=cfg["base_temp"],
                temp_amplitude=cfg["temp_amplitude"],
                base_pressure=cfg["base_pressure"],
                base_rh=cfg["base_rh"],
                latitude=cfg["latitude"],
                longitude=cfg["longitude"],
                elevation=cfg["elevation"],
                cadence_seconds=cadence_seconds,
                seed=seed + i,
            )

    def generate_network_streams(
        self,
        start_time: datetime,
        num_points_per_station: int,
    ) -> Dict[str, List[ObservationIn]]:
        """
        Generate time series observations for all stations in network.
        """
        streams: Dict[str, List[ObservationIn]] = {}
        for st_id, gen in self.generators.items():
            streams[st_id] = gen.generate(start_time, num_points_per_station)
        return streams

    def generate_interleaved_stream(
        self,
        start_time: datetime,
        num_points_per_station: int,
    ) -> List[ObservationIn]:
        """
        Generate chronological interleaved observations across all stations.
        """
        streams = self.generate_network_streams(start_time, num_points_per_station)
        interleaved: List[ObservationIn] = []
        for i in range(num_points_per_station):
            for st_id in self.generators.keys():
                interleaved.append(streams[st_id][i])
        return interleaved
