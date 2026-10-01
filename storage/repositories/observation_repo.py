"""
Observation repository for immutable raw observations and canonical processed records.
"""
import sqlite3
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from storage.db.connection import db
from ingestion.schemas.observation import ObservationIn, compute_payload_hash, generate_observation_id
from ingestion.schemas.integrity import IntegrityResult, IntegrityFlag, IntegrityDisposition


class ObservationRepository:
    def __init__(self, database=None):
        self.db = database or db

    def save_raw_observation(
        self,
        observation: ObservationIn,
        raw_payload_str: str,
        received_at: datetime,
        ingestion_sequence: int,
        parse_status: str = "VALID",
    ) -> str:
        """
        Saves immutable raw observation.
        """
        obs_id = generate_observation_id(
            observation.station_id,
            observation.timestamp.isoformat(),
            observation.source_sequence,
        )
        payload_hash = compute_payload_hash(raw_payload_str)

        sql = """
        INSERT INTO raw_observations (
            observation_id, station_id, event_timestamp,
            temperature_raw, pressure_raw, relative_humidity_raw,
            latitude_raw, longitude_raw, elevation_raw,
            source_type, source_sequence, received_at,
            ingestion_sequence, payload_hash, raw_payload, parse_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self.db.transaction() as conn:
            conn.execute(
                sql,
                (
                    obs_id,
                    observation.station_id,
                    observation.timestamp.isoformat(),
                    observation.temperature,
                    observation.pressure,
                    observation.relative_humidity,
                    observation.latitude,
                    observation.longitude,
                    observation.elevation,
                    observation.source_type.value,
                    observation.source_sequence,
                    received_at.isoformat(),
                    ingestion_sequence,
                    payload_hash,
                    raw_payload_str,
                    parse_status,
                ),
            )
        return obs_id

    def save_malformed_raw(
        self,
        station_id: str,
        raw_payload_str: str,
        received_at: datetime,
        error_msg: str,
    ) -> str:
        """
        Preserve raw payload when parsing fails.
        """
        payload_hash = compute_payload_hash(raw_payload_str)
        obs_id = f"obs-malformed-{payload_hash[:12]}"
        sql = """
        INSERT INTO raw_observations (
            observation_id, station_id, event_timestamp,
            source_type, received_at, payload_hash, raw_payload, parse_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self.db.transaction() as conn:
            conn.execute(
                sql,
                (
                    obs_id,
                    station_id or "UNKNOWN",
                    received_at.isoformat(),
                    "LIVE",
                    received_at.isoformat(),
                    payload_hash,
                    raw_payload_str,
                    f"MALFORMED: {error_msg}",
                ),
            )
        return obs_id

    def save_processed_observation(
        self,
        obs_id: str,
        observation: ObservationIn,
        integrity: IntegrityResult,
        ordering_status: str = "IN_ORDER",
    ):
        sql = """
        INSERT INTO processed_observations (
            observation_id, station_id, event_timestamp,
            temperature, pressure, relative_humidity,
            late_by_seconds, ordering_status, duplicate_of_observation_id,
            missing_temperature, missing_pressure, missing_relative_humidity,
            integrity_status, normalization_version, schema_version, processor_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self.db.transaction() as conn:
            conn.execute(
                sql,
                (
                    obs_id,
                    observation.station_id,
                    observation.timestamp.isoformat(),
                    observation.temperature,
                    observation.pressure,
                    observation.relative_humidity,
                    integrity.late_by_seconds,
                    ordering_status,
                    integrity.duplicate_of_observation_id,
                    1 if observation.temperature is None else 0,
                    1 if observation.pressure is None else 0,
                    1 if observation.relative_humidity is None else 0,
                    integrity.disposition.value,
                    "v1",
                    "v1",
                    "v1",
                ),
            )

    def save_decision(
        self,
        decision_id: str,
        observation_id: str,
        integrity_status: str,
        alert_stage: str,
        decision_state: str,
        admission_state: str,
        anomaly_score: Optional[float] = None,
        severity: Optional[str] = None,
        detection_confidence: Optional[float] = None,
        attribution_confidence: Optional[float] = None,
        uncertainty_state: str = "NONE",
        root_cause_category: Optional[str] = None,
        reasoning_summary: Optional[str] = None,
        evidence_codes: Optional[List[str]] = None,
        plausibility_score: Optional[float] = None,
        weather_event_likelihood: Optional[float] = None,
        sensor_fault_likelihood: Optional[float] = None,
    ):
        evidence_json = json.dumps(evidence_codes or [])
        sql = """
        INSERT INTO decisions (
            decision_id, observation_id, alert_stage, decision_state,
            anomaly_score, severity, detection_confidence, attribution_confidence,
            uncertainty_state, root_cause_category, admission_state,
            reasoning_summary, evidence_codes_json, plausibility_score,
            weather_event_likelihood, sensor_fault_likelihood,
            reference_version, tracker_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self.db.transaction() as conn:
            conn.execute(
                sql,
                (
                    decision_id,
                    observation_id,
                    alert_stage,
                    decision_state,
                    anomaly_score,
                    severity,
                    detection_confidence,
                    attribution_confidence,
                    uncertainty_state,
                    root_cause_category,
                    admission_state,
                    reasoning_summary,
                    evidence_json,
                    plausibility_score,
                    weather_event_likelihood,
                    sensor_fault_likelihood,
                    "v1-phase1",
                    "v1-phase1",
                ),
            )

    def get_recent_observations(self, station_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        sql = """
        SELECT p.*, r.received_at, r.source_type, r.temperature_raw, r.pressure_raw, r.relative_humidity_raw,
               d.decision_id, d.alert_stage, d.decision_state, d.anomaly_score, d.severity,
               d.detection_confidence, d.attribution_confidence, d.uncertainty_state,
               d.root_cause_category, d.admission_state, d.reasoning_summary, d.evidence_codes_json,
               d.plausibility_score, d.weather_event_likelihood, d.sensor_fault_likelihood,
               f.derived_dewpoint, f.derived_vapour_pressure
        FROM processed_observations p
        JOIN raw_observations r ON p.observation_id = r.observation_id
        LEFT JOIN decisions d ON p.observation_id = d.observation_id
        LEFT JOIN feature_records f ON p.observation_id = f.observation_id
        WHERE p.station_id = ?
        ORDER BY p.event_timestamp DESC
        LIMIT ?
        """
        with self.db.transaction() as conn:
            cur = conn.execute(sql, (station_id, limit))
            records = []
            for row in cur.fetchall():
                d_row = dict(row)
                if d_row.get("evidence_codes_json"):
                    try:
                        d_row["evidence_codes"] = json.loads(d_row["evidence_codes_json"])
                    except Exception:
                        d_row["evidence_codes"] = []
                else:
                    d_row["evidence_codes"] = []
                records.append(d_row)
            return records

    def get_recent_decisions(self, station_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        if station_id:
            sql = """
            SELECT d.*, p.station_id, p.event_timestamp, p.temperature, p.pressure, p.relative_humidity,
                   p.integrity_status, r.temperature_raw, r.pressure_raw, r.relative_humidity_raw
            FROM decisions d
            JOIN processed_observations p ON d.observation_id = p.observation_id
            JOIN raw_observations r ON p.observation_id = r.observation_id
            WHERE p.station_id = ?
            ORDER BY p.event_timestamp DESC
            LIMIT ?
            """
            params = (station_id, limit)
        else:
            sql = """
            SELECT d.*, p.station_id, p.event_timestamp, p.temperature, p.pressure, p.relative_humidity,
                   p.integrity_status, r.temperature_raw, r.pressure_raw, r.relative_humidity_raw
            FROM decisions d
            JOIN processed_observations p ON d.observation_id = p.observation_id
            JOIN raw_observations r ON p.observation_id = r.observation_id
            ORDER BY p.event_timestamp DESC
            LIMIT ?
            """
            params = (limit,)
        with self.db.transaction() as conn:
            cur = conn.execute(sql, params)
            records = []
            for row in cur.fetchall():
                d_row = dict(row)
                if d_row.get("evidence_codes_json"):
                    try:
                        d_row["evidence_codes"] = json.loads(d_row["evidence_codes_json"])
                    except Exception:
                        d_row["evidence_codes"] = []
                else:
                    d_row["evidence_codes"] = []
                records.append(d_row)
            return records

    def get_observation_by_id(self, obs_id: str) -> Optional[Dict[str, Any]]:
        sql = """
        SELECT r.*, p.integrity_status, p.ordering_status,
               d.decision_id, d.decision_state, d.alert_stage, d.anomaly_score, d.severity,
               d.detection_confidence, d.attribution_confidence, d.uncertainty_state,
               d.root_cause_category, d.admission_state, d.reasoning_summary, d.evidence_codes_json,
               d.plausibility_score, d.weather_event_likelihood, d.sensor_fault_likelihood
        FROM raw_observations r
        LEFT JOIN processed_observations p ON r.observation_id = p.observation_id
        LEFT JOIN decisions d ON r.observation_id = d.observation_id
        WHERE r.observation_id = ?
        """
        with self.db.transaction() as conn:
            cur = conn.execute(sql, (obs_id,))
            row = cur.fetchone()
            if not row:
                return None
            d_row = dict(row)
            if d_row.get("evidence_codes_json"):
                try:
                    d_row["evidence_codes"] = json.loads(d_row["evidence_codes_json"])
                except Exception:
                    d_row["evidence_codes"] = []
            else:
                d_row["evidence_codes"] = []
            return d_row


obs_repo = ObservationRepository()
