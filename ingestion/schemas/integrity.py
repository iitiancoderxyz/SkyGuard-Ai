"""
Integrity flags, dispositions, and result schemas.
"""
from enum import Enum
from typing import List, Set, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class IntegrityDisposition(str, Enum):
    ACCEPT = "ACCEPT"
    ACCEPT_LATE = "ACCEPT_LATE"
    REJECT = "REJECT"
    QUARANTINE = "QUARANTINE"


class IntegrityFlag(str, Enum):
    OK = "OK"
    MALFORMED_RECORD = "MALFORMED_RECORD"
    MISSING_VALUE = "MISSING_VALUE"
    MISSING_TEMPERATURE = "MISSING_TEMPERATURE"
    MISSING_PRESSURE = "MISSING_PRESSURE"
    MISSING_RELATIVE_HUMIDITY = "MISSING_RELATIVE_HUMIDITY"
    MISSING_EXPECTED_RECORD = "MISSING_EXPECTED_RECORD"
    COMMUNICATION_GAP = "COMMUNICATION_GAP"
    DUPLICATE = "DUPLICATE"
    CONFLICTING_DUPLICATE = "CONFLICTING_DUPLICATE"
    DELAYED = "DELAYED"
    LATE_OUT_OF_ORDER = "LATE_OUT_OF_ORDER"
    STALE_RETRANSMISSION = "STALE_RETRANSMISSION"
    RANGE_VIOLATION = "RANGE_VIOLATION"
    RANGE_TEMP_LOW = "RANGE_TEMP_LOW"
    RANGE_TEMP_HIGH = "RANGE_TEMP_HIGH"
    RANGE_PRESSURE_LOW = "RANGE_PRESSURE_LOW"
    RANGE_PRESSURE_HIGH = "RANGE_PRESSURE_HIGH"
    RANGE_RH_LOW = "RANGE_RH_LOW"
    RANGE_RH_HIGH = "RANGE_RH_HIGH"
    FROZEN_STUCK_CANDIDATE = "FROZEN_STUCK_CANDIDATE"


class IntegrityResult(BaseModel):
    disposition: IntegrityDisposition = IntegrityDisposition.ACCEPT
    flags: List[IntegrityFlag] = Field(default_factory=lambda: [IntegrityFlag.OK])
    missing_slots: List[datetime] = Field(default_factory=list)
    channel_nulls: List[str] = Field(default_factory=list)
    flat_runs: Dict[str, int] = Field(default_factory=dict)
    late_by_seconds: float = 0.0
    duplicate_of_observation_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
