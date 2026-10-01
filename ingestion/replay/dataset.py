"""
Dataset serialization and loading utilities for Parquet and CSV formats.
Supports benchmark storage and historical stream replay.
"""
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import pandas as pd
from ingestion.schemas.observation import ObservationIn, SourceType


def observations_to_dataframe(observations: List[ObservationIn]) -> pd.DataFrame:
    records = []
    for obs in observations:
        records.append({
            "station_id": obs.station_id,
            "timestamp": obs.timestamp.isoformat(),
            "temperature": obs.temperature,
            "pressure": obs.pressure,
            "relative_humidity": obs.relative_humidity,
            "latitude": obs.latitude,
            "longitude": obs.longitude,
            "elevation": obs.elevation,
            "source_type": obs.source_type.value,
            "source_sequence": obs.source_sequence,
        })
    return pd.DataFrame(records)


def dataframe_to_observations(df: pd.DataFrame) -> List[ObservationIn]:
    observations = []
    for _, row in df.iterrows():
        # Handle nan / None
        t = None if pd.isna(row.get("temperature")) else float(row["temperature"])
        p = None if pd.isna(row.get("pressure")) else float(row["pressure"])
        rh = None if pd.isna(row.get("relative_humidity")) else float(row["relative_humidity"])
        lat = None if pd.isna(row.get("latitude")) else float(row["latitude"])
        lon = None if pd.isna(row.get("longitude")) else float(row["longitude"])
        elev = None if pd.isna(row.get("elevation")) else float(row["elevation"])
        seq = None if pd.isna(row.get("source_sequence")) else str(row["source_sequence"])
        src_type = SourceType(row.get("source_type", "HISTORICAL_REPLAY"))

        obs = ObservationIn(
            station_id=str(row["station_id"]),
            timestamp=row["timestamp"],
            temperature=t,
            pressure=p,
            relative_humidity=rh,
            latitude=lat,
            longitude=lon,
            elevation=elev,
            source_type=src_type,
            source_sequence=seq,
        )
        observations.append(obs)
    return observations


def save_dataset_parquet(observations: List[ObservationIn], filepath: str):
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    df = observations_to_dataframe(observations)
    df.to_parquet(filepath, index=False)


def load_dataset_parquet(filepath: str) -> List[ObservationIn]:
    df = pd.read_parquet(filepath)
    return dataframe_to_observations(df)


def save_dataset_csv(observations: List[ObservationIn], filepath: str):
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    df = observations_to_dataframe(observations)
    df.to_csv(filepath, index=False)


def load_dataset_csv(filepath: str) -> List[ObservationIn]:
    df = pd.read_csv(filepath)
    return dataframe_to_observations(df)


def save_ground_truth_parquet(labels: List[Dict[str, Any]], filepath: str):
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(labels)
    df.to_parquet(filepath, index=False)


def load_ground_truth_parquet(filepath: str) -> List[Dict[str, Any]]:
    df = pd.read_parquet(filepath)
    return df.to_dict(orient="records")
