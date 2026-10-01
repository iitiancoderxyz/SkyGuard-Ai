# 14A_DATA_PIPELINE — SIH26073

## Scope

This file expands the approved `14_SYSTEM_ARCHITECTURE.md` only. It defines the implementation-facing data contract, ingestion/integrity flow, replay and simulation flow, storage model, APIs, error handling, and data-pipeline tests for TRUST-TWIN.

The core meteorological inputs remain exactly:

- `temperature` — °C
- `pressure` — hPa
- `relative_humidity` — %

`station_id`, `timestamp`, and station location are contextual metadata. `elevation` is treated as location-derived context metadata, not as a meteorological input. No other meteorological variables are introduced.

The live processing contract is shared by streaming, replay, simulation, and API submission:

```text
process_observation(observation) -> processing_result / decision
```

Raw observations are immutable. Processed records, decisions, corrections, and ground-truth labels are stored separately.

---

# Data Architecture

```text
                AUTOMATIC WEATHER STATION
                         │
                         │ T / P / RH + metadata
                         ▼
                ┌─────────────────┐
                │ 1. INGESTION    │
                │ parse + preserve│
                └────────┬────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼
   RAW DATA (immutable)       integrity / quarantine
            │                         │
            └────────────┬────────────┘
                         ▼
                ┌─────────────────┐
                │ 2. VALIDATION   │
                │ schema/cadence  │
                │ duplicate/order │
                │ missing/malformed│
                └────────┬────────┘
                         ▼
                ┌─────────────────┐
                │ 3. PREPROCESS   │
                │ canonical units │
                │ event-time order│
                │ missingness flags│
                └────────┬────────┘
                         ▼
                PROCESSED DATA
                         │
                         ▼
                TRUST-TWIN ENGINE
        temporal / seasonal / T-P-RH evidence
                         │
                         ▼
             decisions / episodes / health
                         │
                         ▼
                    API / UI

SIMULATED DATA
clean historical segment
        │
        ▼
fault / weather-surrogate generator
        │
        ├──────────────► simulated stream
        │
        └──────────────► GROUND TRUTH sidecar

GROUND TRUTH
injection metadata + genuine-event label provenance
        │
        └──► evaluation only
             (never passed to detection engine)
```

### Component contracts

| Component | INPUT | PROCESS | OUTPUT |
|---|---|---|---|
| Ingestion | source payload | preserve payload, assign ingestion metadata, parse envelope | immutable raw record + parse status |
| Validation | raw record | schema, type, cadence, range, duplicate, delay/order checks | integrity status + integrity events |
| Time handler | accepted timestamps + station cadence config | event-time ordering, watermark/late policy, expected-slot tracking | ordered processed record + lateness/missing flags |
| Preprocessing | valid numeric fields | canonical units, finite-value checks, missingness representation, versioned normalization | processed observation |
| Feature context | processed observation + station history | lags, rates, persistence/flatness, calendar/season context, T/P/RH-derived features | versioned feature record |
| Live engine | processed observation + features | TRUST-TWIN detection path | provisional/final decision |
| Historical replay | replay dataset | emit records through same processing path | reproducible decisions |
| Fault injector | clean base + seed + recipe | inject one or more supported fault families | simulated data + injection manifest |
| Genuine-weather generator | historical T/P/RH hard-negative segment or T/P/RH-only surrogate recipe | preserve plausible multivariate trajectory | simulated hard-negative stream + provenance |
| Ground truth builder | injection manifest / event provenance | assign point/episode labels | ground-truth labels |
| Storage | raw/processed/decision entities | transactional persistence | queryable operational state |
| API | JSON request/query | call same engine/repositories | response / event stream |

---

# Input Schema

## Canonical observation schema

The canonical internal observation is:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `station_id` | string | yes | station identifier |
| `timestamp` | RFC3339 datetime | yes | **event time** of the observation |
| `temperature` | float | yes for a complete observation | °C |
| `pressure` | float | yes for a complete observation | hPa; prototype interpretation: station-level pressure |
| `relative_humidity` | float | yes for a complete observation | % |
| `latitude` | float | optional | station location context |
| `longitude` | float | optional | station location context |
| `elevation` | float | optional | location-derived context metadata |
| `source_type` | enum | yes | `LIVE`, `HISTORICAL_REPLAY`, `SIMULATED` |
| `source_sequence` | string/int | optional | source-side ordering/packet sequence when available |

`received_at` / ingestion time is created by the pipeline and is **not** a meteorological input.

### Input rules

1. Canonical live/replay payloads use °C, hPa, and %; unit conversion is performed in a source adapter before the canonical ingestion contract.
2. A missing numeric field is represented as `null` at the raw boundary, never silently replaced.
3. A non-numeric or structurally invalid field is retained as raw payload and classified as malformed.
4. Latitude/longitude/elevation may be unavailable. Missing context must not block station-local processing.
5. No extra meteorological fields are required or forwarded into the core model.
6. `pressure` is stored as the station-level reported pressure. No automatic sea-level reduction is required by this pipeline.

### Example payload

```json
{
  "station_id": "AWS_001",
  "timestamp": "2026-09-29T16:30:00Z",
  "temperature": 28.4,
  "pressure": 1004.8,
  "relative_humidity": 71.2,
  "latitude": 23.1765,
  "longitude": 79.9864,
  "elevation": 411.0,
  "source_type": "LIVE",
  "source_sequence": "884201"
}
```

---

# Metadata

## Ingestion metadata

Created by the pipeline and stored separately from station measurements:

- `observation_id`
- `received_at`
- `ingestion_sequence`
- `payload_hash`
- `parse_status`
- `normalization_version`
- `schema_version`
- `processor_version`

`observation_id` must be deterministic/stable for replay and audit. The implementation should derive it from `station_id`, event timestamp, and the source/ingestion sequence where available.

## Station metadata

The `stations` table stores the latest configured context:

- `station_id`
- `latitude`
- `longitude`
- `elevation`
- `expected_cadence_seconds`
- `allowed_lateness_seconds`
- `status`
- `config_version`

Station metadata updates never modify historical raw observation records.

---

# Ingestion

## Live ingestion

**INPUT**  
Single observation payload.

**PROCESS**

1. Receive payload.
2. Record `received_at` and ingestion sequence.
3. Persist the original payload before feature generation.
4. Parse against the schema.
5. Assign `observation_id`.
6. Send the parsed observation through the integrity gate.
7. Forward only the canonical processed representation to downstream detection.

**OUTPUT**

- immutable raw record;
- integrity status/events;
- processed observation, or quarantined parse result;
- immediate processing result when sufficient data exists.

## Historical replay ingestion

Historical replay must use the same `process_observation()` engine as live data.

```text
Parquet/CSV
   → source adapter
   → canonical observation
   → process_observation()
   → same integrity + detection path
```

Replay controls:

- start/end time;
- station subset;
- replay rate;
- preserve original event-time ordering;
- optionally reproduce recorded arrival order for late/out-of-order tests;
- deterministic run identifier and seed.

## Multi-station ingestion

Each station has station-scoped:

- event-time buffer;
- recent history;
- reference/tracker state;
- episode state;
- health state;
- provenance.

The ingestion layer may interleave records from many stations, but station-local ordering and state are maintained independently.

---

# Validation

Validation is deterministic and precedes ML inference.

## Schema validation

Check:

- required identifiers exist;
- timestamp parses;
- T/P/RH are numeric when present;
- latitude/longitude/elevation are numeric when present;
- no unexpected meteorological field is required by the core schema.

Malformed payloads are never silently repaired into measured values.

## Value validation

Prototype sanity bounds are implementation configuration, not official SIH26073 requirements:

```yaml
temperature:
  min: -80.0
  max: 70.0

pressure:
  min: 300.0
  max: 1100.0

relative_humidity:
  min: 0.0
  max: 100.0
```

A deployment may replace these with sensor-class-specific configured limits. A range violation is an integrity signal and is not by itself proof of physical sensor failure.

## Duplicate validation

A record is a duplicate when the same station/time/source identity is received again with the same measurement payload.

Policy:

- keep both arrival records in raw storage;
- mark the later arrival `DUPLICATE`;
- do not feed the duplicate twice into adaptive learning;
- expose the relationship through `duplicate_of_observation_id`.

If the same station/time key carries different values, classify it as `CONFLICTING_DUPLICATE` and quarantine it for adjudication/replay rather than silently selecting one value.

## Missing values

Missing numeric values are represented as null/missingness flags.

Policy:

- raw payload remains unchanged;
- no raw imputation;
- processed record carries `missing_temperature`, `missing_pressure`, `missing_relative_humidity`;
- ML features that require the missing value are marked unavailable;
- the system may continue with integrity/network evidence and later episode processing;
- optional correction is a separate downstream feature and never changes the raw record.

For a **missing expected observation slot**, there may be no raw row at all. The time-alignment layer creates an expected-slot integrity event without inventing an observation.

## Malformed records

Malformed means the payload cannot be safely parsed into the canonical contract.

**INPUT → PROCESS → OUTPUT**

```text
raw payload
→ preserve original payload + parse error
→ quarantine record with MALFORMED status
```

Malformed data must not enter the normal model path.

---

# Time Handling

## Event time and ingestion time

Two timestamps are tracked internally:

- `timestamp` = station/event time; used for temporal analysis.
- `received_at` = system ingestion time; used for delay/order diagnostics.

The event timestamp is never overwritten to hide communication delay.

## Cadence

Sampling cadence is configuration, not a hard-coded SIH26073 requirement.

Prototype default for demonstration:

```yaml
expected_cadence_seconds: 60
allowed_lateness_seconds: 120
communication_gap_slots: 3
```

Per-station configuration can override these values.

## Expected slots and communication failure

The pipeline tracks expected event-time slots.

- one missing expected slot → `MISSING_EXPECTED_RECORD`;
- `N` consecutive missing expected slots, with `N` configured above → `COMMUNICATION_GAP`;
- missing rows are not converted into fake sensor observations.

This distinction requires a known expected cadence; a completely unconfigured stream cannot be declared a communication failure merely because a row is absent.

## Delayed records

A delayed record has a valid event timestamp but arrives after the expected arrival window.

**INPUT → PROCESS → OUTPUT**

```text
late arrival
→ compare received_at vs event-time expectation
→ mark late_by_seconds + lateness class
→ retain original event time
→ continue through event-time ordering/replay policy
```

## Out-of-order records

Records are retained in arrival order for audit and processed using event time.

Policy:

- within the configured watermark/window: reorder before temporal feature updates;
- beyond the watermark: retain and flag `LATE_OUT_OF_ORDER`;
- do not silently rewrite prior raw records;
- any retroactive state correction is performed by explicit historical replay, not hidden mutation of live state.

## Stale/retransmitted data versus frozen sensor

Disambiguation rule:

- all channels repeat and timestamp/sequence is repeated or non-advancing → communication stale/duplicate;
- one channel is flat while other channels continue changing → supports `FROZEN_STUCK` for that channel;
- all channels remain flat for a long window with no timestamp fault → `UNRESOLVED`, not an automatic sensor-fault diagnosis.

---

# Streaming

## Fast path

Every observation follows:

```text
ingest
→ integrity
→ time alignment
→ feature update
→ baseline residual
→ spike/freeze/step suspicion
→ provisional result
```

The fast path must not wait for long-horizon health processing.

## Buffered diagnostic path

Active episodes retain a bounded evidence window:

```text
episode
→ subsequent observations
→ sequential evidence update
→ weather/fault hypotheses
→ confidence / uncertainty
→ final, WAIT, ABSTAIN, AMBIGUOUS
```

One active episode produces one evolving alert record rather than one new alert for every sample.

## Long-horizon path

```text
history
→ reference/tracker divergence
→ change/trend evidence
→ health
→ degradation indication
→ maintenance indication
```

## Stream reliability

The runtime uses the approved bounded in-process/event-time stream for the prototype. No Kafka, Kubernetes, or distributed database is required.

Measured streaming tests must report:

- ingest → provisional alert p50/p95/p99 where practical;
- ingest → final episode decision;
- throughput;
- queue depth;
- memory.

---

# Historical Replay

## Replay dataset contract

Primary replay storage:

- Parquet for benchmark/replay data;
- CSV accepted through a source adapter.

A replay manifest contains:

```yaml
run_id: replay_20260929_001
source_ref: <dataset-or-file-reference>
stations: ["AWS_001", "AWS_002"]
start: "2026-01-01T00:00:00Z"
end: "2026-01-31T23:59:00Z"
replay_rate: 60
arrival_mode: event_time
seed: 42
```

## Replay modes

1. `EVENT_TIME` — ordered by event timestamp.
2. `RECORDED_ARRIVAL` — reproduces recorded order where available.
3. `FAULT_INJECTED` — clean base plus deterministic injected fault stream.
4. `GENUINE_HARD_NEGATIVE` — historically unusual T/P/RH trajectory or explicitly labelled T/P/RH-only surrogate.

All modes use the same processing engine.

## Replay isolation

Ground-truth labels are not passed to `process_observation()`.

```text
SIMULATED DATA ──► detection engine
GROUND TRUTH  ──► evaluator only
```

This prevents label leakage.

---

# Fault Injection

Fault injection is an evaluation/simulation component, not part of live detection.

## Supported behavior families

The approved taxonomy is retained, constrained to the T/P/RH scope:

1. isolated spike
2. repeated spike
3. sudden bias
4. gradual drift
5. frozen/flatline
6. stuck-at value
7. excessive noise
8. missing observation
9. communication failure
10. duplicate
11. delayed/out-of-order observation
12. corrupted value
13. multivariate inconsistency
14. combined fault

Any inherited example that relies on wind, rainfall, solar radiation, or another non-core meteorological variable is excluded from the core benchmark.

## Injection configuration

Each injection recipe must specify:

- `fault_class`
- `station_id` scope
- `channel` = `temperature | pressure | relative_humidity | multi`
- `start_time` or onset-selection rule
- duration / end rule
- magnitude / noise parameters
- affected-channel coupling
- sampling interval
- quantization behavior where relevant
- missingness behavior
- overlap with other faults
- random seed
- injector version

### Injection contract

```text
clean base
→ select onset
→ create anomaly mask
→ apply deterministic transform
→ emit simulated stream
→ emit exact injection manifest
```

The clean base is a **normal-state approximation**, not assumed physically perfect truth.

---

# Genuine-Weather Simulation

The pipeline must distinguish genuine unusual weather from injected faults.

## Preferred source

Use real historical periods containing unusual T/P/RH trajectories when documented event labels or operational records are available.

## T/P/RH-only surrogate mode

When no verified genuine-event record is available, a synthetic hard negative may be created from real T/P/RH trajectories while preserving realistic temporal and multivariate structure.

Such a case must be labelled:

```text
label_type = GENUINE_EVENT_SURROGATE
label_source = SYNTHETIC_SURROGATE
```

It must not be described as proof of real-weather generalization.

No non-core meteorological variable is required to create or evaluate the surrogate.

---

# Ground Truth

Ground truth is created only for simulation/benchmark evaluation.

## Ground-truth entities

A label can be:

- `NORMAL`
- `ANOMALY`
- `GENUINE_EVENT`
- `GENUINE_EVENT_SURROGATE`
- `UNKNOWN_REFERENCE_CASE`

For anomaly injection, the label must include:

| Field | Meaning |
|---|---|
| `run_id` | simulation/evaluation run |
| `station_id` | affected station |
| `event_timestamp` | labelled event-time slot |
| `label_type` | normal/anomaly/event class |
| `fault_class` | one of the 14 supported families when applicable |
| `channel` | affected core channel or `multi` |
| `onset` | exact episode onset |
| `offset` | exact episode end when known |
| `injection_id` | links to injection manifest |
| `source_observation_id` | clean-base observation when one exists |
| `label_source` | injection manifest / historical record / surrogate |
| `seed` | deterministic generator seed where applicable |

## Point and episode labels

Each injection must generate:

1. point-level labels for affected timestamps;
2. episode-level onset/offset labels.

For missing/communication faults, the ground-truth label can reference an **expected slot** even when no raw observation exists.

### Ground-truth rule

The evaluator must never infer ground truth from the detector's output. Ground truth comes only from:

- the injection manifest, or
- independently documented historical/genuine-event provenance.

---

# Storage

## Storage principles

The approved prototype uses:

- **SQLite + WAL** for live/local operational state;
- **Parquet/CSV** for replay and benchmark datasets.

Raw, processed, simulated, and ground-truth data remain logically separate.

## Database structure

### `stations`

Station configuration and contextual location.

```text
station_id PK
latitude
longitude
elevation
expected_cadence_seconds
allowed_lateness_seconds
communication_gap_slots
config_version
status
updated_at
```

### `raw_observations`

Immutable source record. Parsed fields may be null when the payload is malformed/incomplete.

```text
observation_id PK
station_id
event_timestamp
temperature_raw
pressure_raw
relative_humidity_raw
latitude_raw
longitude_raw
elevation_raw
source_type
source_sequence
received_at
ingestion_sequence
payload_hash
raw_payload
parse_status
created_at
```

**Invariant:** no update operation may modify the measured/raw fields.

### `processed_observations`

Canonical, versioned processing result.

```text
observation_id PK/FK
station_id
event_timestamp
temperature
pressure
relative_humidity
expected_slot
late_by_seconds
ordering_status
duplicate_of_observation_id
missing_temperature
missing_pressure
missing_relative_humidity
integrity_status
normalization_version
schema_version
processor_version
processed_at
```

### `integrity_events`

```text
integrity_event_id PK
observation_id nullable
station_id
event_timestamp nullable
event_type
details
created_at
```

Examples:

```text
MALFORMED_RECORD
MISSING_EXPECTED_RECORD
COMMUNICATION_GAP
DUPLICATE
CONFLICTING_DUPLICATE
DELAYED
LATE_OUT_OF_ORDER
RANGE_VIOLATION
MISSING_VALUE
STALE_RETRANSMISSION
```

### `feature_records`

Versioned derived/temporal evidence, never source measurements.

```text
feature_id PK
observation_id FK
feature_version
lag/rate/persistence/flatness fields
calendar/season fields
T_P_RH_derived_fields
reference_version
tracker_version
created_at
```

### `anomaly_episodes`

```text
episode_id PK
station_id
start_time
end_time nullable
status
decision_state
created_at
updated_at
```

### `decisions`

```text
decision_id PK
observation_id FK
episode_id nullable
alert_stage
anomaly_score
severity
detection_confidence
attribution_confidence
uncertainty_state
root_cause_category
admission_state
explanation_id
reference_version
tracker_version
created_at
```

### `health_state`

```text
station_id
scope
state
health_score nullable
degradation_state
maintenance_state
evidence_window_start
evidence_window_end
model_integrity_state
updated_at
```

### `corrections`

Optional and permanently separate from raw data.

```text
correction_id PK
observation_id FK
estimated_temperature nullable
estimated_pressure nullable
estimated_relative_humidity nullable
method
uncertainty
bounds
eligibility_reason
created_at
```

### `model_versions`

```text
model_version PK
component
artifact_uri
training_window
calibration_status
feature_version
created_at
parent_version nullable
promotion_state
```

### `provenance_events`

```text
provenance_id PK
entity_type
entity_id
event_type
from_version nullable
to_version nullable
admission_state nullable
reason
created_at
```

### Simulation/evaluation records

`simulation_runs` and `ground_truth_labels` are evaluation entities. They are never joined into the live detection input path.

---

# APIs

## Common observation interface

### `POST /v1/observations`

Accept one canonical observation.

**INPUT**

```json
{
  "station_id": "AWS_001",
  "timestamp": "2026-09-29T16:30:00Z",
  "temperature": 28.4,
  "pressure": 1004.8,
  "relative_humidity": 71.2,
  "latitude": 23.1765,
  "longitude": 79.9864,
  "elevation": 411.0,
  "source_type": "LIVE"
}
```

**PROCESS**

`process_observation(observation)`

**OUTPUT**

```json
{
  "observation_id": "obs-...",
  "integrity_status": "OK",
  "alert_stage": "PROVISIONAL",
  "decision_state": "NORMAL",
  "anomaly_score": 0.03,
  "severity": "LOW",
  "detection_confidence": 0.94,
  "attribution_confidence": 0.94,
  "uncertainty_state": "NONE",
  "root_cause_category": null,
  "episode_id": null
}
```

The example values are illustrative only; implementation and evaluation must not claim those values as measured performance.

## Station APIs

- `GET /v1/stations`
- `GET /v1/stations/{station_id}`
- `GET /v1/stations/{station_id}/observations`
- `GET /v1/stations/{station_id}/health`

## Alert/episode APIs

- `GET /v1/alerts`
- `GET /v1/episodes/{episode_id}`
- `GET /v1/episodes/{episode_id}/evidence`

## Explanation/API outputs

- `GET /v1/decisions/{decision_id}/explanation`

## Correction API

- `GET /v1/observations/{observation_id}/correction`

Correction endpoints expose estimates separately from measured/raw values.

## Operations/provenance

- `GET /v1/models`
- `GET /v1/provenance/{entity_id}`
- `GET /v1/readiness`

## Replay

`POST /v1/replay` or an equivalent local replay command must invoke the same engine used by live ingestion.

Replay must never bypass validation or inject labels into the detection engine.

## Realtime events

`GET /v1/events` may use Server-Sent Events for:

- decision updates;
- alert/episode updates;
- health updates.

---

# Error Handling

| Condition | Pipeline behavior | API/runtime result |
|---|---|---|
| malformed payload | preserve raw payload, quarantine | 422-style validation result |
| missing required core field | preserve raw, integrity event | non-normal processing result; no silent fill |
| range violation | retain + flag | accepted for audit when parseable; flagged integrity status |
| duplicate | retain both arrivals | accepted with `DUPLICATE`; no duplicate learning update |
| conflicting duplicate | retain both, quarantine for resolution | `CONFLICTING_DUPLICATE` |
| delayed/out-of-order | retain, reorder within watermark, flag beyond watermark | accepted with lateness status |
| expected slot missing | create integrity event, no fake raw row | communication/missing status |
| live model unavailable | fall back to deterministic/statistical evidence | degraded mode explicitly marked |
| network context unavailable | station-local processing | `NETWORK_UNAVAILABLE` / `NETWORK_UNRESOLVED` |
| database failure | do not silently drop; use bounded operational buffer where feasible; do not advance learning state without safe provenance | service/storage error |
| storage buffer full | stop accepting unsafe state transitions | 503-style service result |
| uncertain attribution | preserve uncertainty | `WAIT` / `ABSTAIN` / `AMBIGUOUS` / `UNKNOWN` |
| replay failure | stop run and preserve run/error manifest | failed replay status |

No error path may fabricate a normal observation.

---

# Testing

## 1. Schema and contract tests

Test:

- valid observation;
- missing core field;
- null value;
- malformed number;
- malformed timestamp;
- unavailable location;
- unexpected non-core meteorological field;
- source-type routing.

## 2. Integrity tests

Test independently:

- single missing expected slot;
- multi-slot communication gap;
- duplicate;
- conflicting duplicate;
- stale/retransmitted packet;
- delayed observation;
- out-of-order sequence;
- malformed record;
- range violation;
- flatline versus repeated packet.

## 3. Time/replay tests

- event-time sorting;
- watermark behavior;
- late record within watermark;
- late record beyond watermark;
- replay determinism;
- identical seed → identical simulation and labels;
- same `process_observation()` behavior for live and replay.

## 4. Storage invariants

- raw row is immutable;
- processed record links to exactly one raw observation;
- correction never overwrites raw;
- decision references correct model/reference versions;
- ground truth cannot be read by the live detector;
- station state remains station-scoped.

## 5. Fault-injection tests

For every supported fault family verify:

- injection occurs only in T/P/RH or stream structure;
- onset/offset are recorded;
- parameters and seed are recorded;
- ground-truth labels exactly match the injected region;
- detector receives only the simulated stream, not the injection manifest.

Use independent generator recipes and held-out parameterizations for major families to reduce injector memorization risk.

## 6. Genuine-event hard-negative tests

- real documented T/P/RH unusual periods where available;
- T/P/RH-only surrogate cases when real labels are unavailable;
- verify these labels are not marked as injected faults;
- report surrogate cases as surrogates.

## 7. Multi-station tests

Increase:

- number of stations;
- stream rate;
- concurrent active episodes.

Measure:

- throughput;
- memory;
- queue depth;
- decision latency.

Station-local processing must remain valid when network context is absent.

## 8. End-to-end golden replay

A deterministic scenario must pass:

```text
input
→ raw storage
→ validation
→ preprocessing
→ feature record
→ detection
→ decision
→ episode
→ health/provenance
→ API query
```

The resulting decision and provenance should be reproducible from the same input, configuration, model artifacts, and seed.

## 9. Ground-truth leakage test

The evaluator must prove that removing the ground-truth sidecar from runtime inputs does not change the detector execution path.

## 10. Realtime measurement

Report measured:

- ingest → provisional alert;
- ingest → final episode decision;
- p50/p95/p99 where practical;
- throughput;
- memory;
- queue depth.

Do not convert these measurements into unsupported field-deployment claims.

---

# Acceptance Criteria

1. The pipeline accepts only Temperature, Pressure, and Relative Humidity as core meteorological inputs.
2. Station ID, timestamp, latitude, longitude, and elevation are treated as contextual metadata only.
3. Raw payloads and raw observations are immutable.
4. Malformed, missing, duplicate, delayed, and out-of-order conditions have explicit integrity states.
5. Communication gaps are detected only when an expected cadence/slot is known.
6. Event time and ingestion time are both preserved for ordering and audit.
7. Replay and live ingestion use the same `process_observation()` engine.
8. Historical/replay data can be processed deterministically from a manifest and seed.
9. Simulated fault data is stored separately from clean/base data.
10. Ground truth is generated from injection/event provenance and is never passed to the detector.
11. Genuine-weather hard negatives are represented separately from injected anomalies.
12. SQLite/WAL is the live/local transactional store; Parquet/CSV is the replay/benchmark format.
13. Optional corrected values are stored separately and never overwrite raw measurements.
14. Multi-station state is partitioned by station ID.
15. Storage/API failure does not silently advance adaptive learning state.
16. The pipeline supports provisional decisions and explicit unresolved outcomes without forcing a fault label.
17. Unit, integration, replay, fault-injection, ground-truth-isolation, and multi-station tests are executable.
18. Measured realtime and scalability results are produced by tests rather than assumed.

---

# Handoff to Antigravity

Implement `14A_DATA_PIPELINE.md` in the following order without changing `14_SYSTEM_ARCHITECTURE.md`:

### Phase 1 — Contracts and persistence

- Implement Pydantic canonical observation schema.
- Implement station configuration.
- Implement SQLite/WAL repositories for raw, processed, integrity, episode, decision, health, correction, model, and provenance records.
- Add immutable-raw tests.

### Phase 2 — Integrity and time

- Implement `process_observation()`.
- Implement schema validation.
- Implement expected-slot tracking.
- Implement duplicate/conflicting-duplicate detection.
- Implement event-time ordering, watermark, late and out-of-order handling.
- Implement stale/retransmission versus frozen-channel distinction.

### Phase 3 — Replay and streaming

- Implement bounded in-process event-time stream.
- Implement Parquet/CSV replay adapter.
- Implement replay-rate control and deterministic replay manifests.
- Ensure live and replay share the same processing path.

### Phase 4 — Simulation and ground truth

- Implement the 14 supported fault-injection families under the T/P/RH-only boundary.
- Implement deterministic seeds and injection manifests.
- Implement genuine-event historical hard-negative ingestion and clearly labelled T/P/RH-only surrogate mode.
- Implement ground-truth sidecar generation.
- Enforce that the detector never receives ground-truth labels.

### Phase 5 — API and verification

- Implement FastAPI observation, station, alert/episode, explanation, correction, provenance, readiness, and event interfaces.
- Add golden replay and failure-injection tests.
- Add multi-station load tests.
- Add realtime latency/throughput/memory measurement.
- Provide example requests and expected schema-level outputs.

### Handoff boundary

This file defines the data contract and storage/transport behavior only. The ML mechanism, confidence calibration, severity semantics, sequential adjudication logic, health/degradation models, dashboard details, and demo orchestration remain owned by the corresponding architecture sub-files and must consume these pipeline contracts without redesigning the approved TRUST-TWIN architecture.
