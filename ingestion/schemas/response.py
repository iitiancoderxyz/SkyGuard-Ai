"""
Response and Decision models for Phase 1.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from ingestion.schemas.integrity import IntegrityFlag, IntegrityDisposition


class DecisionState(str, Enum):
    NORMAL = "NORMAL"
    SUSPECT = "SUSPECT"
    ANOMALY = "ANOMALY"
    WAIT = "WAIT"
    ABSTAIN = "ABSTAIN"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN = "UNKNOWN"
    QUARANTINED = "QUARANTINED"
    DEGRADED = "DEGRADED"


class AlertStage(str, Enum):
    NONE = "NONE"
    PROVISIONAL = "PROVISIONAL"
    CONFIRMED = "CONFIRMED"
    ABSTAINED = "ABSTAINED"
    CLOSED = "CLOSED"


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AdmissionState(str, Enum):
    ADMIT = "ADMIT"
    QUARANTINE = "QUARANTINE"
    REJECT = "REJECT"
    UNKNOWN = "UNKNOWN"


class Decision(BaseModel):
    """
    Standard single-observation decision output from process_observation.
    """
    observation_id: str
    station_id: str
    event_timestamp: datetime
    integrity_status: str
    disposition: IntegrityDisposition
    integrity_flags: List[IntegrityFlag]
    alert_stage: AlertStage = AlertStage.NONE
    decision_state: DecisionState = DecisionState.NORMAL
    anomaly_score: Optional[float] = None
    severity: Optional[SeverityLevel] = None
    detection_confidence: Optional[float] = None
    attribution_confidence: Optional[float] = None
    uncertainty_state: str = "NONE"
    root_cause_category: Optional[str] = None
    admission_state: AdmissionState = AdmissionState.ADMIT
    episode_id: Optional[str] = None
    system_mode: str = "NORMAL"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    disclaimer: str = Field(default="Phase 3 Core Intelligence active.")
    # Phase 3 evidence & likelihood fields
    plausibility_score: Optional[float] = None
    weather_event_evidence: Optional[bool] = None
    sensor_fault_evidence: Optional[bool] = None
    weather_event_likelihood: Optional[float] = None
    sensor_fault_likelihood: Optional[float] = None
    evidence_codes: Optional[List[str]] = None
    reasoning_summary: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0-phase1"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    database: str = "connected"
    storage_mode: str = "WAL"
    active_stations: int = 0
