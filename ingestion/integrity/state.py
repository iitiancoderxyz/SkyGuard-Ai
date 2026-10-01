"""
Station state for tracking integrity, cadence, flat runs, and order.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from features.builder import CleanBuffer


@dataclass
class StationState:
    station_id: str
    last_event_ts: Optional[datetime] = None
    last_received_ts: Optional[datetime] = None
    last_values: Dict[str, Optional[float]] = field(default_factory=lambda: {
        "temperature": None,
        "pressure": None,
        "relative_humidity": None,
    })
    flat_runs: Dict[str, int] = field(default_factory=lambda: {
        "temperature": 0,
        "pressure": 0,
        "relative_humidity": 0,
    })
    seen_timestamps: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # ts_iso -> {values, obs_id}
    missing_slot_count: int = 0
    total_received: int = 0
    clean_buffer: CleanBuffer = field(default_factory=CleanBuffer)

