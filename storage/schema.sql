-- TRUST-TWIN Database Schema (SQLite WAL mode)
-- Enforces raw immutability via SQLite triggers

PRAGMA foreign_keys = ON;

-- Stations Table
CREATE TABLE IF NOT EXISTS stations (
    station_id TEXT PRIMARY KEY,
    latitude REAL,
    longitude REAL,
    elevation REAL,
    expected_cadence_seconds INTEGER DEFAULT 60,
    allowed_lateness_seconds INTEGER DEFAULT 120,
    communication_gap_slots INTEGER DEFAULT 3,
    config_version TEXT DEFAULT 'v1',
    status TEXT DEFAULT 'ACTIVE',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Raw Observations Table (Immutable Source of Truth)
CREATE TABLE IF NOT EXISTS raw_observations (
    observation_id TEXT PRIMARY KEY,
    station_id TEXT NOT NULL,
    event_timestamp TEXT NOT NULL,
    temperature_raw REAL,
    pressure_raw REAL,
    relative_humidity_raw REAL,
    latitude_raw REAL,
    longitude_raw REAL,
    elevation_raw REAL,
    source_type TEXT NOT NULL,
    source_sequence TEXT,
    received_at TEXT NOT NULL,
    ingestion_sequence INTEGER,
    payload_hash TEXT NOT NULL,
    raw_payload TEXT NOT NULL,
    parse_status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Invariant INV-02: Prevent UPDATE and DELETE on raw_observations
CREATE TRIGGER IF NOT EXISTS abort_raw_update
BEFORE UPDATE ON raw_observations
BEGIN
    SELECT RAISE(ABORT, 'Raw observations are strictly immutable. UPDATE is forbidden.');
END;

CREATE TRIGGER IF NOT EXISTS abort_raw_delete
BEFORE DELETE ON raw_observations
BEGIN
    SELECT RAISE(ABORT, 'Raw observations are strictly immutable. DELETE is forbidden.');
END;

-- Processed Observations Table
CREATE TABLE IF NOT EXISTS processed_observations (
    observation_id TEXT PRIMARY KEY,
    station_id TEXT NOT NULL,
    event_timestamp TEXT NOT NULL,
    temperature REAL,
    pressure REAL,
    relative_humidity REAL,
    expected_slot TEXT,
    late_by_seconds REAL DEFAULT 0.0,
    ordering_status TEXT DEFAULT 'IN_ORDER',
    duplicate_of_observation_id TEXT,
    missing_temperature INTEGER DEFAULT 0,
    missing_pressure INTEGER DEFAULT 0,
    missing_relative_humidity INTEGER DEFAULT 0,
    integrity_status TEXT DEFAULT 'OK',
    normalization_version TEXT DEFAULT 'v1',
    schema_version TEXT DEFAULT 'v1',
    processor_version TEXT DEFAULT 'v1',
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (observation_id) REFERENCES raw_observations(observation_id)
);

-- Integrity Events
CREATE TABLE IF NOT EXISTS integrity_events (
    integrity_event_id TEXT PRIMARY KEY,
    observation_id TEXT,
    station_id TEXT NOT NULL,
    event_timestamp TEXT,
    event_type TEXT NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (observation_id) REFERENCES raw_observations(observation_id)
);

-- Feature Records
CREATE TABLE IF NOT EXISTS feature_records (
    feature_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL,
    feature_version TEXT NOT NULL,
    derived_dewpoint REAL,
    derived_vapour_pressure REAL,
    features_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (observation_id) REFERENCES processed_observations(observation_id)
);

-- Anomaly Episodes
CREATE TABLE IF NOT EXISTS anomaly_episodes (
    episode_id TEXT PRIMARY KEY,
    station_id TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN',
    decision_state TEXT NOT NULL DEFAULT 'PROVISIONAL',
    root_cause TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Decisions Table
CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL,
    episode_id TEXT,
    alert_stage TEXT DEFAULT 'NONE',
    decision_state TEXT DEFAULT 'NORMAL',
    anomaly_score REAL,
    severity TEXT,
    detection_confidence REAL,
    attribution_confidence REAL,
    uncertainty_state TEXT DEFAULT 'NONE',
    root_cause_category TEXT,
    admission_state TEXT DEFAULT 'ADMIT',
    reasoning_summary TEXT,
    evidence_codes_json TEXT,
    plausibility_score REAL,
    weather_event_likelihood REAL,
    sensor_fault_likelihood REAL,
    explanation_id TEXT,
    reference_version TEXT,
    tracker_version TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (observation_id) REFERENCES processed_observations(observation_id),
    FOREIGN KEY (episode_id) REFERENCES anomaly_episodes(episode_id)
);

-- Health State Table
CREATE TABLE IF NOT EXISTS health_state (
    station_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'UNKNOWN',
    health_score REAL,
    degradation_state TEXT DEFAULT 'NO_DEGRADATION_EVIDENCE',
    maintenance_state TEXT DEFAULT 'NONE',
    evidence_window_start TEXT,
    evidence_window_end TEXT,
    model_integrity_state TEXT DEFAULT 'OK',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (station_id, channel)
);

-- Corrections Table (Optional, Separate from Raw)
CREATE TABLE IF NOT EXISTS corrections (
    correction_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL,
    estimated_temperature REAL,
    estimated_pressure REAL,
    estimated_relative_humidity REAL,
    method TEXT NOT NULL,
    uncertainty REAL,
    bounds_json TEXT,
    eligibility_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (observation_id) REFERENCES processed_observations(observation_id)
);

-- Model Versions
CREATE TABLE IF NOT EXISTS model_versions (
    model_version TEXT PRIMARY KEY,
    component TEXT NOT NULL,
    artifact_uri TEXT NOT NULL,
    training_window TEXT,
    calibration_status TEXT DEFAULT 'UNCALIBRATED',
    feature_version TEXT DEFAULT 'v1',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parent_version TEXT,
    promotion_state TEXT DEFAULT 'RETIRED'
);

-- Provenance Events
CREATE TABLE IF NOT EXISTS provenance_events (
    provenance_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    from_version TEXT,
    to_version TEXT,
    admission_state TEXT,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Simulation / Ground Truth Entities (Evaluation Only)
CREATE TABLE IF NOT EXISTS simulation_runs (
    run_id TEXT PRIMARY KEY,
    scenario_name TEXT NOT NULL,
    station_id TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    seed INTEGER NOT NULL,
    status TEXT DEFAULT 'COMPLETED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ground_truth_labels (
    label_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    station_id TEXT NOT NULL,
    event_timestamp TEXT NOT NULL,
    label_type TEXT NOT NULL,
    fault_class TEXT,
    channel TEXT,
    onset TEXT,
    offset TEXT,
    injection_id TEXT,
    source_observation_id TEXT,
    label_source TEXT,
    seed INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit Log Table
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    actor TEXT DEFAULT 'system',
    details_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Helpful indices for fast querying
CREATE INDEX IF NOT EXISTS idx_raw_station_ts ON raw_observations(station_id, event_timestamp);
CREATE INDEX IF NOT EXISTS idx_proc_station_ts ON processed_observations(station_id, event_timestamp);
CREATE INDEX IF NOT EXISTS idx_decisions_obs ON decisions(observation_id);
