# Phase 2 Data Module Report — SIH26073 TRUST-TWIN

## Phase
**PHASE 2 — DATA + STREAMING**  
TRUST-TWIN: Quarantine-Gated Sequential Evidence Monitor for Automatic Weather Stations  
SIH Problem Statement: SIH26073

---

## Data Schema

### Core Meteorological Inputs (Immutable scope — INV-01)
| Variable | Unit | Range | Field |
|---|---|---|---|
| Temperature | °C | −80 to +60 | `temperature` |
| Atmospheric Pressure | hPa | 870 to 1084 | `pressure` |
| Relative Humidity | % | 0 to 100 | `relative_humidity` |

> No wind, rainfall, solar radiation, or other variables are accepted. The `extra="forbid"` Pydantic guard rejects them at ingestion boundary.

### Permitted Metadata
| Field | Type | Description |
|---|---|---|
| `station_id` | str | Station identity (preserved throughout pipeline) |
| `timestamp` | datetime (UTC) | Observation event time (ISO 8601, UTC-explicit) |
| `latitude` | float, optional | Station latitude |
| `longitude` | float, optional | Station longitude |
| `elevation` | float, optional | Station elevation (m) |
| `source_type` | enum | `LIVE` / `HISTORICAL_REPLAY` / `SIMULATED` |

### Storage Tables (from `storage/schema.sql`)
| Table | Purpose | Mutability |
|---|---|---|
| `raw_observations` | Source-of-truth raw ingestion | **IMMUTABLE** (UPDATE/DELETE triggers RAISE ABORT) |
| `processed_observations` | Validated, integrity-annotated copy | Append-only |
| `feature_records` | Derived thermodynamic/rate-of-change features | Append-only, FK → `processed_observations` |
| `ground_truth_labels` | Simulation ground truth (separate from runtime) | Append-only, isolated sidecar |
| `simulation_runs` | Simulation run metadata | Append-only |
| `integrity_events` | All integrity flag events per observation | Append-only |

---

## Components Implemented

### 1. AWS Observation Schema (`ingestion/schemas/observation.py`)
- `ObservationIn` Pydantic v2 model with `extra="forbid"` scope guard (INV-01)
- Deterministic `observation_id` from `station_id + timestamp` hash
- `payload_hash` for deduplication
- Accepts exactly: T, P, RH + permitted metadata

### 2. Ingestion & Preprocessing (`ingestion/preprocessing.py`)
- `Preprocessor` class wired into the single entry point in `engine.py`
- Computes thermodynamic quantities via `features/multivariate/thermodynamics.py`
- Computes rates of change via `features/temporal/rates.py`
- Adds calendar context (hour, month, is_daytime)
- Adds missingness flags per channel
- Runs on every observation through `EngineService.process_observation()`

### 3. Thermodynamic Feature Engine (`features/multivariate/thermodynamics.py`)
- Magnus-Tetens saturated vapour pressure: `e_s(T)`
- Actual vapour pressure: `e = (RH/100) × e_s`
- Dewpoint temperature (Magnus inverse formula)
- `compute_derived_meteorological_quantities()` — packages all as dict

### 4. Rate-of-Change Features (`features/temporal/rates.py`)
- `compute_rates_of_change()` — T/P/RH per-minute deltas vs. previous observation
- Returns `None` where no previous observation exists (first record)

### 5. Feature Repository (`storage/repositories/feature_repo.py`)
- `FeatureRepository.save_feature_record()` — stores features JSON + derived scalar columns
- `get_features_by_observation_id()` — retrieval by obs ID
- FK references `processed_observations(observation_id)` — correct ordering enforced in engine

### 6. Ground-Truth Repository (`storage/repositories/ground_truth_repo.py`)
- `GroundTruthRepository.save_simulation_run()` — persists scenario run metadata
- `save_ground_truth_label()` — persists per-observation fault class labels with injection metadata
- `get_labels_for_run()` — retrieval by run_id
- Isolated from runtime detection engine (INV-03): only imported lazily inside API route handler

### 7. Fault Injector — All 14 Fault Families (`injector/faults/injector.py`)
| # | Fault Class | Family |
|---|---|---|
| 1 | `ISOLATED_SPIKE` | Point anomaly |
| 2 | `REPEATED_SPIKES` | Periodic point anomalies |
| 3 | `SUDDEN_BIAS` | Step-change bias |
| 4 | `GRADUAL_DRIFT` | Slow systematic drift |
| 5 | `FROZEN_FLATLINE` | Sensor stuck at constant value |
| 6 | `STUCK_AT_VALUE` | Sensor stuck at specific value |
| 7 | `EXCESSIVE_NOISE` | Noise inflation |
| 8 | `MISSING_OBSERVATION` | Dropped records |
| 9 | `COMMUNICATION_FAILURE` | Transmission dropout |
| 10 | `DUPLICATE_OBSERVATION` | Exact/near-duplicate records |
| 11 | `DELAYED_OUT_OF_ORDER` | Out-of-order timestamp |
| 12 | `CORRUPTED_VALUE` | Value corruption (NaN/inf/illegal) |
| 13 | `MULTIVARIATE_INCONSISTENCY` | Thermodynamically inconsistent T/P/RH combination |
| 14 | `COMBINED_FAULTS` | Simultaneous multi-family fault |

Backwards-compatible alias methods: `inject_spike()`, `inject_frozen()`, `inject_drift()`, `inject_communication_gap()`

### 8. Weather Surrogate Generator (`injector/weather_surrogates/generator.py`)
- `WeatherEventSimulator.simulate_cold_front()` — rapid T drop, P rise, RH spike
- `simulate_heat_surge()` — gradual T rise, RH drop, P stable

### 9. Multi-Station Network (`simulator/stream/multi_station.py`)
- `MultiStationNetwork` — 5 default Indian AWS stations: Delhi, Mumbai, Kolkata, Chennai, Bengaluru
- `generate_network_streams(t0, n)` — generates `n` observations per station
- `generate_interleaved_stream(t0, n)` — chronologically merged stream from all stations

### 10. Scenario Suite (`simulator/scenarios/suite.py`)
10 named scenarios covering the full fault taxonomy:
`NOMINAL`, `SPIKE`, `DRIFT`, `FLATLINE`, `BIAS`, `NOISE`, `COMMUNICATION_GAP`, `MULTIVARIATE_INCONSISTENCY`, `GENUINE_WEATHER`, `COMBINED`

Each scenario returns `(observations, metadata)` where `metadata["manifests"]` contains ground-truth injection records.

### 11. Dataset Serialisation (`ingestion/replay/dataset.py`)
- Parquet round-trip: `save_dataset_parquet()` / `load_dataset_parquet()`
- CSV round-trip: `save_dataset_csv()` / `load_dataset_csv()`
- Ground truth Parquet: `save_ground_truth_parquet()` / `load_ground_truth_parquet()`
- `observations_to_dataframe()` / `dataframe_to_observations()`

---

## Fault Types Implemented

| Fault Type | Code | Method | Notes |
|---|---|---|---|
| SPIKE | `ISOLATED_SPIKE` | `inject_spike()` | Magnitude + channel configurable |
| DRIFT | `GRADUAL_DRIFT` | `inject_drift()` | Linear ramp over duration |
| FLATLINE | `FROZEN_FLATLINE` | `inject_frozen()` | Constant stuck value |
| BIAS | `SUDDEN_BIAS` | `inject_sudden_bias()` | Step offset |
| NOISE | `EXCESSIVE_NOISE` | `inject_excessive_noise()` | Gaussian std multiplier |
| MISSING | `MISSING_OBSERVATION` | `inject_missing()` | Record deletion |
| COMMUNICATION FAILURE | `COMMUNICATION_FAILURE` | `inject_communication_gap()` | Multi-record dropout |
| DUPLICATE | `DUPLICATE_OBSERVATION` | `inject_duplicate()` | Exact or near-duplicate insert |
| DELAYED/OUT-OF-ORDER | `DELAYED_OUT_OF_ORDER` | `inject_delayed_out_of_order()` | Timestamp reordering |
| CORRUPTED VALUE | `CORRUPTED_VALUE` | `inject_corrupted_value()` | NaN/inf/illegal replacement |
| MULTIVARIATE INCONSISTENCY | `MULTIVARIATE_INCONSISTENCY` | `inject_multivariate_inconsistency()` | Thermodynamic impossibility |
| REPEATED SPIKES | `REPEATED_SPIKES` | `inject_repeated_spikes()` | Periodic pattern |
| STUCK AT VALUE | `STUCK_AT_VALUE` | `inject_stuck_at_value()` | Pin to specific value |
| COMBINED | `COMBINED_FAULTS` | `inject_combined()` | Any subset simultaneously |
| GENUINE WEATHER | Weather surrogates | `simulate_cold_front()` / `simulate_heat_surge()` | Labelled as NOMINAL |

---

## Streaming

- **Real-time SSE:** `GET /v1/stream` — Server-Sent Events with optional `?station_id=` filter
- **Historical replay:** `StreamReplayer.replay(observations)` — drives all observations through the single `process_observation()` entry point
- **Multi-station interleaved stream:** `MultiStationNetwork.generate_interleaved_stream()` — chronological merge

---

## Tests

### Test Results: **47/47 PASSED**

| Test File | Tests | Coverage |
|---|---|---|
| `tests/unit/test_all_14_faults.py` | 14 | All 14 fault families injected and manifest-checked |
| `tests/unit/test_thermodynamics.py` | 4 | Magnus-Tetens, vapour pressure, dewpoint, packaging |
| `tests/unit/test_rates.py` | 2 | Rate-of-change computation, missing value handling |
| `tests/unit/test_fault_injector.py` | 3 | Backwards-compatible alias methods |
| `tests/unit/test_integrity_gate.py` | 4 | Nominal, range, duplicate, missing/comm-gap |
| `tests/unit/test_schemas.py` | 4 | Valid obs, scope guard, deterministic ID, payload hash |
| `tests/unit/test_simulator.py` | 2 | Generator bounds, replayer processes all |
| `tests/unit/test_config_and_claims.py` | 3 | Claims scope, disclaimers, settings defaults |
| `tests/invariants/test_invariants.py` | 5 | INV-01 scope, INV-02 raw immutability, INV-03 GT isolation, INV-10 dashboard isolation, INV-13 claims |
| `tests/integration/test_pipeline_e2e.py` | 5 | Health/ready, POST observation, extra field reject, stations, replay |
| `tests/integration/test_dashboard_connection.py` | 1 | Dashboard client smoke |

---

## Commands

```powershell
# Run full test suite
python -m pytest -v

# Verify multi-station and Parquet round-trip
python -c "from simulator.stream.multi_station import MultiStationNetwork; ..."

# Start backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Test scenario endpoint
curl -X POST "http://127.0.0.1:8000/v1/simulator/scenarios/SPIKE/run?station_id=AWS_TEST&num_points=15"

# Test observation ingestion
curl -X POST http://127.0.0.1:8000/v1/observations \
  -H "Content-Type: application/json" \
  -d '{"station_id":"AWS_TEST","timestamp":"2026-09-30T00:00:00Z","temperature":28.5,"pressure":1012.3,"relative_humidity":65.0,"source_type":"LIVE"}'
```

---

## What Works

- ✅ AWS observation schema (T/P/RH + station ID + timestamp + permitted metadata only)
- ✅ Raw observation immutability enforced by SQLite triggers (INV-02)
- ✅ Scope guard: extra meteorological fields rejected at Pydantic boundary (INV-01)
- ✅ Ground truth isolation: labels in sidecar tables, not readable by detection engine (INV-03)
- ✅ Preprocessing pipeline: thermodynamics + rates-of-change + missingness flags
- ✅ Feature records stored after processed observations (FK ordering correct)
- ✅ All 14 fault families injectable via `FaultInjector`
- ✅ Genuine weather event simulation (`cold_front`, `heat_surge`)
- ✅ Multi-station network (5 Indian stations) with interleaved streaming
- ✅ 10 pre-configured named scenarios with ground-truth manifests
- ✅ Parquet/CSV dataset serialisation round-trips verified
- ✅ SSE stream with optional per-station filter
- ✅ `POST /v1/simulator/scenarios/{name}/run` — runs scenario and stores labels
- ✅ `GET /v1/eval/labels/{run_id}` — retrieves ground-truth labels for evaluation
- ✅ Out-of-range observation correctly QUARANTINED (not silently accepted)
- ✅ 47/47 tests pass

---

## Known Issues

| Issue | Severity | Notes |
|---|---|---|
| `source_type` enum is `LIVE`/`HISTORICAL_REPLAY`/`SIMULATED` only — `PHYSICAL_SENSOR` rejected | Low | Correct by design; callers must use `LIVE` for live sensor data |
| Streamlit dashboard not yet updated for Phase 2 scenario/label endpoints | Low | Dashboard still uses Phase 1 API surface; Phase 3 work |
| FK enforcement: SQLite WAL mode with `PRAGMA foreign_keys = ON` required per connection | Low | Connection module already sets this on connect |
| Weather surrogate events label as `NOMINAL` (genuine weather is not a fault) — may need caller awareness for evaluation | Info | By design per architecture |

---

## Acceptance Criteria Status

| Criterion | Status |
|---|---|
| Data schema works (T/P/RH + metadata) | ✅ PASS |
| Observations can be generated | ✅ PASS |
| Observations can be stored (raw immutable) | ✅ PASS |
| Real-time stream works (SSE) | ✅ PASS |
| Multiple stations work | ✅ PASS |
| Fault injection works (all 14 families) | ✅ PASS |
| Historical replay works | ✅ PASS |
| Malformed/missing/duplicate/out-of-order handling works | ✅ PASS |
| Raw data remains immutable | ✅ PASS (INV-02 trigger test passing) |
| Ground truth isolated from detection engine | ✅ PASS (INV-03 passing) |
| Tests pass | ✅ PASS (47/47) |

---

## Handoff to Phase 3

### What Phase 3 can rely on:
- **Observation pipeline** fully operational: ingest → raw store → integrity gate → processed store → feature record → decision → SSE broadcast
- **Feature vector** per observation: dewpoint, vapour pressure, T/P/RH rates-of-change, calendar context, missingness flags
- **Scenario runner API**: `POST /v1/simulator/scenarios/{name}/run` generates labelled datasets ready for ML training evaluation
- **Ground truth labels**: accessible via `GET /v1/eval/labels/{run_id}` and `GroundTruthRepository.get_labels_for_run()`
- **Parquet serialisation**: `save_dataset_parquet()` / `load_dataset_parquet()` ready for offline ML workflows
- **5 Indian stations** with realistic diurnal physics + fault injection capability

### Phase 3 scope (NOT implemented here):
- ML anomaly detection baseline (C04 in architecture: isolation forest / statistical)
- Temporal model (C05: sliding window, LSTM placeholder)
- Explainability module (C06: SHAP or rule-based attribution)
- Correction/imputation module (C10)
- Sensor health scoring (C08)
- Full dashboard with live anomaly display

### Architecture authority for Phase 3:
- `14B_ANOMALY_DETECTION.md` (if exists)
- `14C_HEALTH_DEGRADATION.md` (if exists)
- `14D_CORRECTION.md` (if exists)
- `14_SYSTEM_ARCHITECTURE.md` — components C04–C10
