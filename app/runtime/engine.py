"""
TRUST-TWIN Core Engine Service.
Contains the single decision entry point: process_observation(obs) -> Decision (Principle P1).
"""
import uuid
import json
import threading
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from ingestion.schemas.observation import ObservationIn
from ingestion.schemas.response import (
    Decision,
    DecisionState,
    AlertStage,
    SeverityLevel,
    AdmissionState,
)
from ingestion.schemas.integrity import (
    IntegrityFlag,
    IntegrityDisposition,
    IntegrityResult,
)
from ingestion.integrity.gate import IntegrityGate, integrity_gate
from ingestion.integrity.state import StationState
from storage.repositories.observation_repo import obs_repo, ObservationRepository
from storage.repositories.station_repo import station_repo, StationRepository
from storage.repositories.event_repo import event_repo, EventRepository
from storage.repositories.feature_repo import feature_repo, FeatureRepository
from ingestion.preprocessing import preprocessor, Preprocessor
from app.runtime.bus import bus
from app.core.logging import logger
from app.core.claims import DISCLAIMER_EVALUATION
from detection.triggers.statistical import statistical_detector, AnomalyResult
from detection.reference.baseline import reference_profile
from detection.tracker.tracker import adaptive_tracker
from detection.decision.adjudicator import adjudicator



class EngineService:
    def __init__(
        self,
        observation_repo: Optional[ObservationRepository] = None,
        st_repo: Optional[StationRepository] = None,
        ev_repo: Optional[EventRepository] = None,
        f_repo: Optional[FeatureRepository] = None,
        gate: Optional[IntegrityGate] = None,
        prep: Optional[Preprocessor] = None,
    ):
        self.obs_repo = observation_repo or obs_repo
        self.station_repo = st_repo or station_repo
        self.event_repo = ev_repo or event_repo
        self.feature_repo = f_repo or feature_repo
        self.gate = gate or integrity_gate
        self.preprocessor = prep or preprocessor
        self.station_states: Dict[str, StationState] = {}
        self.locks: Dict[str, threading.Lock] = {}
        self.global_lock = threading.Lock()
        self.ingestion_counter = 0

    def _get_station_lock(self, station_id: str) -> threading.Lock:
        with self.global_lock:
            if station_id not in self.locks:
                self.locks[station_id] = threading.Lock()
            return self.locks[station_id]

    def _get_or_init_state(self, station_id: str) -> StationState:
        if station_id not in self.station_states:
            self.station_states[station_id] = StationState(station_id=station_id)
            # Register in stations table if not exists
            if not self.station_repo.get_station(station_id):
                self.station_repo.upsert_station(station_id=station_id)
        return self.station_states[station_id]

    def process_observation(
        self,
        observation: ObservationIn,
        raw_payload_str: Optional[str] = None,
        received_at: Optional[datetime] = None,
    ) -> Decision:
        """
        The single decision entry point (Principle P1).
        Receives observation, preserves raw data, executes integrity gate,
        stores processed observation, emits stream events, and returns Decision.
        """
        now_utc = received_at or datetime.now(timezone.utc)
        payload_text = raw_payload_str or json.dumps(observation.model_dump(mode="json"))

        with self.global_lock:
            self.ingestion_counter += 1
            seq = self.ingestion_counter

        station_id = observation.station_id
        lock = self._get_station_lock(station_id)

        with lock:
            # 1. Persist immutable raw observation
            obs_id = self.obs_repo.save_raw_observation(
                observation=observation,
                raw_payload_str=payload_text,
                received_at=now_utc,
                ingestion_sequence=seq,
                parse_status="VALID",
            )

            # 2. Retrieve station state and run integrity gate
            state = self._get_or_init_state(station_id)
            integrity: IntegrityResult = self.gate.check(
                obs=observation,
                state=state,
                received_at=now_utc,
            )

            # Record seen timestamp for duplicate resolution
            ts_key = observation.timestamp.isoformat()
            state.seen_timestamps[ts_key] = {
                "values": {
                    "temperature": observation.temperature,
                    "pressure": observation.pressure,
                    "relative_humidity": observation.relative_humidity,
                },
                "obs_id": obs_id,
            }

            # 3. Save integrity events if any non-OK flags or missing slots
            for flag in integrity.flags:
                if flag != IntegrityFlag.OK:
                    self.event_repo.save_integrity_event(
                        station_id=station_id,
                        event_type=flag.value,
                        observation_id=obs_id,
                        event_timestamp=observation.timestamp.isoformat(),
                        details=integrity.details,
                    )

            for missing_slot in integrity.missing_slots:
                self.event_repo.save_integrity_event(
                    station_id=station_id,
                    event_type=IntegrityFlag.MISSING_EXPECTED_RECORD.value,
                    observation_id=None,
                    event_timestamp=missing_slot.isoformat(),
                    details={"cadence": self.gate.expected_cadence_seconds},
                )

            # 4. Save processed observation (must precede feature_records due to FK constraint)
            ordering_status = "LATE_OUT_OF_ORDER" if IntegrityFlag.LATE_OUT_OF_ORDER in integrity.flags else "IN_ORDER"
            self.obs_repo.save_processed_observation(
                obs_id=obs_id,
                observation=observation,
                integrity=integrity,
                ordering_status=ordering_status,
            )

            # 5. Compute and save derived feature record (FK references processed_observations)
            features = self.preprocessor.process(
                obs=observation,
                last_values=state.last_values,
                last_ts=state.last_event_ts,
            )
            self.feature_repo.save_feature_record(
                observation_id=obs_id,
                features=features,
                feature_version="f1",
            )

            # 6. Map integrity disposition to admission state
            decision_id = f"dec-{uuid.uuid4().hex[:12]}"

            if integrity.disposition == IntegrityDisposition.REJECT:
                adm_state = AdmissionState.REJECT
            elif integrity.disposition == IntegrityDisposition.QUARANTINE:
                adm_state = AdmissionState.QUARANTINE
            else:
                adm_state = AdmissionState.ADMIT

            is_admitted = adm_state == AdmissionState.ADMIT

            # 7. Phase 3A — Statistical anomaly detection (runs on every observation)
            stat_result: AnomalyResult = statistical_detector.detect(
                t=observation.temperature,
                p=observation.pressure,
                rh=observation.relative_humidity,
                ts=observation.timestamp,
                buffer=state.clean_buffer,
            )

            # 8. Phase 3B — Reference profile and adaptive tracker
            #    Update only on admitted observations (quarantine-protection).
            if is_admitted:
                reference_profile.update(
                    station_id=station_id,
                    temperature=observation.temperature,
                    pressure=observation.pressure,
                    rh=observation.relative_humidity,
                )
                adaptive_tracker.update(
                    station_id=station_id,
                    temperature=observation.temperature,
                    pressure=observation.pressure,
                    rh=observation.relative_humidity,
                )

            ref_ev = reference_profile.evaluate(
                station_id=station_id,
                temperature=observation.temperature,
                pressure=observation.pressure,
                rh=observation.relative_humidity,
            )
            tracker_ev = adaptive_tracker.evaluate(
                station_id=station_id,
                temperature=observation.temperature,
                pressure=observation.pressure,
                rh=observation.relative_humidity,
            )

            # 9. Phase 3C — Adjudicator produces final decision
            integrity_flag_strs = [f.value for f in integrity.flags]
            adj_result = adjudicator.adjudicate(
                anomaly_score=stat_result.anomaly_score,
                triggers=stat_result.triggers,
                channel_scores=stat_result.channel_scores,
                ref_plausibility=ref_ev["plausibility_score"],
                ref_weather_evidence=ref_ev["weather_event_evidence"],
                ref_sensor_fault=ref_ev["sensor_fault_evidence"],
                tracker_plausibility=tracker_ev["plausibility_score"],
                tracker_weather_evidence=tracker_ev["weather_event_evidence"],
                tracker_sensor_fault=tracker_ev["sensor_fault_evidence"],
                integrity_flags=integrity_flag_strs,
                admission_state=adm_state.value,
                buffer_size=len(state.clean_buffer),
            )

            # Map adjudicator decision state to DecisionState enum
            _state_map = {
                "NORMAL": DecisionState.NORMAL,
                "SUSPECT": DecisionState.SUSPECT,
                "ANOMALOUS": DecisionState.ANOMALY,
                "AMBIGUOUS": DecisionState.AMBIGUOUS,
                "ABSTAIN": DecisionState.ABSTAIN,
            }
            dec_state = _state_map.get(adj_result.decision_state, DecisionState.UNKNOWN)

            # Map severity string to SeverityLevel enum
            _sev_map = {
                "LOW": SeverityLevel.LOW,
                "MODERATE": SeverityLevel.MODERATE,
                "HIGH": SeverityLevel.HIGH,
                "CRITICAL": SeverityLevel.CRITICAL,
            }
            severity = _sev_map.get(adj_result.severity, SeverityLevel.LOW)

            self.obs_repo.save_decision(
                decision_id=decision_id,
                observation_id=obs_id,
                integrity_status=integrity.disposition.value,
                alert_stage=AlertStage.NONE.value,
                decision_state=dec_state.value,
                admission_state=adm_state.value,
                anomaly_score=adj_result.anomaly_score,
                severity=severity.value,
                detection_confidence=adj_result.detection_confidence,
                attribution_confidence=adj_result.attribution_confidence,
                uncertainty_state=adj_result.uncertainty_state,
                root_cause_category=adj_result.root_cause_category,
                reasoning_summary=adj_result.reasoning_summary,
                evidence_codes=adj_result.evidence_codes,
                plausibility_score=adj_result.plausibility_score,
                weather_event_likelihood=adj_result.weather_event_likelihood,
                sensor_fault_likelihood=adj_result.sensor_fault_likelihood,
            )

            decision = Decision(
                observation_id=obs_id,
                station_id=station_id,
                event_timestamp=observation.timestamp,
                integrity_status=integrity.disposition.value,
                disposition=integrity.disposition,
                integrity_flags=integrity.flags,
                alert_stage=AlertStage.NONE,
                decision_state=dec_state,
                anomaly_score=adj_result.anomaly_score,
                severity=severity,
                detection_confidence=adj_result.detection_confidence,
                attribution_confidence=adj_result.attribution_confidence,
                uncertainty_state=adj_result.uncertainty_state,
                root_cause_category=adj_result.root_cause_category,
                admission_state=adm_state,
                episode_id=None,
                system_mode="NORMAL",
                created_at=now_utc,
                plausibility_score=adj_result.plausibility_score,
                weather_event_evidence=adj_result.weather_event_evidence,
                sensor_fault_evidence=adj_result.sensor_fault_evidence,
                weather_event_likelihood=adj_result.weather_event_likelihood,
                sensor_fault_likelihood=adj_result.sensor_fault_likelihood,
                evidence_codes=adj_result.evidence_codes,
                reasoning_summary=adj_result.reasoning_summary,
                disclaimer="TRUST-TWIN Phase 3: Core Intelligence active.",
            )

            # 10. Publish to SSE EventBus
            bus.publish({
                "type": "decision",
                "station_id": station_id,
                "observation_id": obs_id,
                "timestamp": observation.timestamp.isoformat(),
                "disposition": integrity.disposition.value,
                "decision_state": dec_state.value,
                "anomaly_score": adj_result.anomaly_score,
                "root_cause": adj_result.root_cause_category,
            })

            # 11. Advance station state
            if is_admitted:
                state.last_values = {
                    "temperature": observation.temperature,
                    "pressure": observation.pressure,
                    "relative_humidity": observation.relative_humidity,
                }
                state.last_event_ts = observation.timestamp
                state.clean_buffer.push(
                    observation.temperature,
                    observation.pressure,
                    observation.relative_humidity,
                    observation.timestamp,
                )

            return decision



engine = EngineService()


def process_observation(
    observation: ObservationIn,
    raw_payload_str: Optional[str] = None,
    received_at: Optional[datetime] = None,
) -> Decision:
    """Convenience functional wrapper for single decision entry point."""
    return engine.process_observation(observation, raw_payload_str, received_at)
