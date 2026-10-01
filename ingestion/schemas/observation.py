"""
Canonical observation schemas for TRUST-TWIN.
Enforces strict T/P/RH meteorological boundaries (extra='forbid').
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
import hashlib
import json


class SourceType(str, Enum):
    LIVE = "LIVE"
    HISTORICAL_REPLAY = "HISTORICAL_REPLAY"
    SIMULATED = "SIMULATED"


class ObservationIn(BaseModel):
    """
    Direct input payload schema.
    Strictly forbids non-core meteorological inputs.
    """
    model_config = ConfigDict(extra="forbid")

    station_id: str = Field(..., description="Station unique identifier")
    timestamp: datetime = Field(..., description="Observation event timestamp (RFC3339/ISO8601)")
    temperature: Optional[float] = Field(None, description="Temperature in deg C")
    pressure: Optional[float] = Field(None, description="Atmospheric pressure at station level in hPa")
    relative_humidity: Optional[float] = Field(None, description="Relative humidity in %")
    latitude: Optional[float] = Field(None, description="Station latitude context")
    longitude: Optional[float] = Field(None, description="Station longitude context")
    elevation: Optional[float] = Field(None, description="Location-derived elevation context metadata in meters")
    source_type: SourceType = Field(default=SourceType.LIVE, description="Origin of observation")
    source_sequence: Optional[str] = Field(None, description="Source-side sequence/packet number")

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value
        if isinstance(value, str):
            # Parse ISO string
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        raise ValueError(f"Invalid timestamp format: {value}")


def compute_payload_hash(raw_payload_str: str) -> str:
    """Compute SHA256 hash of payload string for immutability and provenance tracking."""
    return hashlib.sha256(raw_payload_str.encode("utf-8")).hexdigest()


def generate_observation_id(
    station_id: str,
    timestamp_iso: str,
    source_seq: Optional[str] = None,
    unique_salt: Optional[str] = None,
) -> str:
    """Generate deterministic observation_id for replay and audit consistency."""
    import uuid
    salt = unique_salt if unique_salt is not None else uuid.uuid4().hex[:8]
    key = f"{station_id}:{timestamp_iso}:{source_seq or 'none'}:{salt}"
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return f"obs-{station_id}-{h}"
