# 14_SYSTEM_ARCHITECTURE — SIH26073

**Agent:** ARCHITECT AGENT 14 — SYSTEMARCHITECT
**Date:** 29 September 2026
**Inputs read:** `00_MASTER_BRIEF.md`, `03_FAILURE_AND_DATA.md`, `04_ML_METHODS.md`, `12_FINAL_SOLUTION.md`, `13_REQUIREMENT_AUDIT.md`
**Project:** TRUST-TWIN — Quarantine-Gated Sequential Evidence Monitor for AWS
**Status:** Implementation specification. **Nothing in this document has been built, run, or measured.** Every numeric default is a *starting value* (implementation choice) to be tuned on the validation split only. No performance, latency, energy, scalability, or novelty claim is made here.

**Label legend (Master Brief Rule 15):** `[PS-M]` PS-mandatory · `[PS-S]` PS-suggested · `[PS-O]` PS-optional · `[IC]` implementation choice made by this document.

---

# Architecture Overview

## 1. What is being built

A single-repository Python system that ingests a stream of Temperature / Pressure / Relative Humidity observations per station, and for every observation produces one **Decision record**. Suspicious observations open an **Episode**. An episode accumulates evidence over subsequent observations and ends in `DECIDED`, `WAIT`, or `ABSTAINED`. A versioned **Reference** model protects an adaptive **Tracker** from learning faulty data. Longitudinal **Health**, **Degradation**, and **Maintenance** outputs are derived from the episode history. A Streamlit **Dashboard** reads everything through a FastAPI **REST API**. A **Simulator** and **Injector** generate the demo and evaluation data.

The core idea of `12_FINAL_SOLUTION.md` is **not** redesigned. Where `12` and `13` leave a mechanism open, this document picks a concrete, simple option and labels it `[IC]`.

## 2. Architectural principles

| # | Principle | Consequence in the build |
|---|---|---|
| P1 | **One decision entry point.** | `process_observation(obs) -> Decision` is used by the API, the replayer, the tests, and the load test. There is no second code path. |
| P2 | **Raw is immutable.** | `raw_observations` has SQLite triggers that abort UPDATE/DELETE. Corrections live in a separate table. |
| P3 | **Learning is gated and traceable.** | Only `ADMIT`ted records update tracker state. Every admission decision is logged. Tracker state is checkpointed and replayable. |
| P4 | **Deterministic before statistical before learned.** | Integrity rules run first and never wait for ML. |
| P5 | **Abstention is a first-class output.** | `WAIT` and `ABSTAINED` are normal states, counted in metrics. |
| P6 | **Ground truth never reaches the engine.** | The engine package cannot import `injector` or read `injection_log`. Enforced by a test (INV-03). |
| P7 | **Station-local first, network optional.** | Every station-local output works with the network module off. |
| P8 | **Smallest stack that satisfies the PS.** | Python + FastAPI + SQLite + Streamlit. No Kafka, Kubernetes, GNN, or transformer. |
| P9 | **Claims are constants, not prose.** | All user-visible scope/calibration disclaimers come from `trusttwin/core/claims.py`. A lint test bans prohibited phrases (INV-13). |

## 3. Scope guard (Master Brief §3.1, §9.1–9.2)

* **Core meteorological inputs: `temperature` (°C), `pressure` (hPa), `relative_humidity` (%). Nothing else.**
* Metadata: `station_id`, `timestamp`, `latitude`, `longitude`; optional `elevation_m` (location-derived context metadata, **not** a meteorological input).
* `pressure` is **station-level pressure** in hPa. `[IC]` No sea-level reduction is performed. (Closes audit R02.)
* Derived features (`dewpoint_c`, `vapour_pressure_hpa`, rates, lags, residuals) are labelled `derived` in code and UI.
* The ingest schema uses `extra="forbid"`. A payload containing `wind_speed`, `rainfall`, `solar_radiation`, etc. is rejected with HTTP 422 (INV-01).

## 4. Technology stack `[IC]` (matches `12_FINAL_SOLUTION.md`)

| Layer | Technology | Version pin (in `requirements.txt`) |
|---|---|---|
| Language | Python | 3.11+ |
| Numerics | NumPy, Pandas, SciPy | numpy>=1.26, pandas>=2.1, scipy>=1.11 |
| ML | scikit-learn (`HistGradientBoostingRegressor`, `MinCovDet`, `IsotonicRegression`, `LogisticRegression`) | scikit-learn>=1.4 |
| Model persistence | joblib | joblib>=1.3 |
| API | FastAPI, Pydantic v2, Uvicorn | fastapi>=0.110, pydantic>=2.6, uvicorn[standard]>=0.29 |
| Storage | SQLite (WAL mode) via stdlib `sqlite3`; Parquet via pyarrow for replay/benchmark data | pyarrow>=15 |
| Config | PyYAML | pyyaml>=6 |
| Dashboard | Streamlit + Plotly + requests | streamlit>=1.37 (needed for `st.fragment(run_every=...)`), plotly>=5.20 |
| Optional XAI `[PS-S]` | SHAP (model-agnostic explainer) | shap (in `requirements-optional.txt`) |
| Tests | pytest, pytest-cov, hypothesis (property tests), httpx (FastAPI TestClient) | dev requirements |
| Packaging | Docker (optional, after local run works) | python:3.11-slim |

## 5. Runtime topology

```text
┌────────────────────────── one machine, no external services ──────────────────────────┐
│                                                                                        │
│  ┌──────────────────────────── API PROCESS (uvicorn) ───────────────────────────────┐ │
│  │  FastAPI routers ──► EngineService ──► StationProcessor (per-station state)       │ │
│  │       ▲                   │                   │                                    │ │
│  │       │                   │                   ├─► integrity / features / models    │ │
│  │  SSE /v1/stream ◄── EventBus                  ├─► episodes / adjudicator           │ │
│  │                           │                   ├─► confidence / severity / explain  │ │
│  │  HeartbeatWatchdog ───────┘                   └─► health / correction / network    │ │
│  │  SimulatorRunner (optional background task; DirectSink or HttpSink)                │ │
│  │  DBWriter thread (single writer, group commit) ──► SQLite (WAL)  data/trusttwin.db │ │
│  └──────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                        │
│  ┌── DASHBOARD PROCESS (streamlit) ──┐      ┌── OFFLINE (CLI scripts, not in path) ──┐ │
│  │ pages ► api_client ► HTTP (poll)  │      │ make_data · train · calibrate · eval   │ │
│  └───────────────────────────────────┘      │ loadtest · latency · export            │ │
│                                              └────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

The engine runs **inside** the API process (one deployable). The dashboard is a separate process and never imports engine code or opens the DB (INV-10).

## 6. Closure of `13_REQUIREMENT_AUDIT.md` findings

Status "Specified" means the gap is closed **in this design**, not in code. Nothing is "implemented" until the corresponding test in §Testing passes on a clean environment.

| Audit ID | Severity | Closed by (section) | Specified as |
|---|---|---|---|
| R24 Executable code | CRITICAL | Project Folder Structure, Deployment, Implementation Sequence M0/M10 | `requirements.txt`, `Makefile`, `make demo`, `make test`, offline-capable pytest |
| R25 Example usage | CRITICAL | Demo Architecture, Folder Structure (`examples/`) | One script + deterministic input + expected-output file per Scenario 1–9 |
| R26 Documentation | CRITICAL | Folder Structure (`docs/`), Implementation Sequence M10 | `README.md`, `docs/USE_CASES.md`, `docs/OUTPUT_GLOSSARY.md`, + 6 more |
| R20 Dashboard not on build plan | CRITICAL | Frontend, Implementation Sequence M2/M7 | Dashboard scheduled at M2 (skeleton) and M7 (full); not deferred |
| X01 Severity undefined | CRITICAL | ML Layer §Severity | 4 levels, explicit formula from magnitude / persistence / breadth; "criticality" removed |
| X03 Dataset + injection protocol | CRITICAL | Fault Injection | Two-tier data plan, recipe table with seeds, ground-truth labelling rule, metrics |
| R04 Real-time interface | MEDIUM | Realtime Layer, Backend | `process_observation`, `StreamReplayer`, latency harness |
| R06 Seasonal minimum history | MEDIUM | ML Layer §Seasonal mode | `FULL` vs `DIURNAL_ONLY`, minimum history rule, cross-season eval slice |
| R09 Stale vs frozen; MISSING vs GAP | MEDIUM | Data Schemas §Stream contract, ML Layer §Freeze | Disambiguation rules R-a/R-b/R-c; N_gap=2 |
| R10 Joint T/P/RH residual | MEDIUM | ML Layer §Joint consistency | Robust Mahalanobis + leave-one-out conditional z |
| R11 Hard-negative source | MEDIUM | Fault Injection §Genuine events | Surrogate generators, labelled "surrogate" in every table; real-event slot for Tier A |
| R13 Confidence definition | MEDIUM | ML Layer §Confidence | `[0,1]`, two values, isotonic calibration, provisional label, scope note |
| R16 Health semantics | MEDIUM | Sensor Health | State table with entry/exit rules, per channel + roll-up |
| R17 Degradation thresholds | MEDIUM | Sensor Health §Degradation | CUSUM + Theil–Sen, minimum horizons, drift-rate sweep |
| R18 Maintenance trigger | MEDIUM | Sensor Health §Maintenance | State → priority map |
| R21 Scalability evidence | MEDIUM | Realtime Layer §Scalability, Testing | N-station load test; shard note; per-station model cost |
| R22 Deployment assumptions | MEDIUM | Deployment | Assumptions block, pinned deps, one-command run |
| R23 Edge assumptions | MEDIUM | Deployment §Edge budget | Declared assumptions table + reference screening code |
| X02 Alert object | MEDIUM | Data Schemas §Alert | One `Alert` per episode, `PROVISIONAL/CONFIRMED/ABSTAINED/CLOSED`, suggested action |
| X04 Stream assumptions | MEDIUM | Data Schemas §Stream contract | Cadence, lateness, resolution, ranges, file format |
| X05 SIH example with neighbours | MEDIUM | Demo Architecture Scenario 1, ML Layer §Network | Minimal network-context module promoted from Phase 5 to M9 (before final demo) |
| X06 Mechanism specification | MEDIUM | ML Layer | Concrete reference, tracker, envelope, trigger, scorer |
| R05, R14, R15, X07, X08 | MINOR | ML Layer, Explainability, Data Schemas | Calendar features named; explain-fidelity metric; PS→class map; `Source` column; hygiene |

## 7. Flags on inherited inconsistencies (preserved, not silently fixed)

1. **`03_FAILURE_AND_DATA.md` uses out-of-scope variables** (wind, gust, precipitation, solar radiation) in faults 1, 2, 4, 5, 13 and in its genuine-event list. This spec re-expresses every injector recipe and every genuine-event surrogate in T/P/RH only (§Fault Injection). Results from any 03-style benchmark are non-comparable.
2. **"Criticality" in the severity rule of `12`** is dropped. It implied a station-importance input outside the permitted metadata. Severity uses only measured quantities.
3. **Gradient-boosted models are not incremental** (audit X06). "Adaptive tracker" therefore means *frozen model weights per version* + *online state that is updated only on admission* + *scheduled refit that creates a new version*. It does not mean online GBM training.
4. **Flat 14-class macro-F1 is not the headline root-cause metric.** Classes that are observationally indistinguishable from T/P/RH (`IMPULSIVE_SPIKE` vs `CORRUPTED_VALUE`; `MISSING_EXPECTED_RECORD` vs `COMMUNICATION_GAP`) are reported both separately and as merged groups.
5. **"AI/ML-based" interpretation risk** (`04` §0.5): the learned components that carry real weight are the per-station gradient-boosted predictors, the robust-covariance joint model, the isotonic calibrators, and the logistic weather-vs-fault evidence weights. The ablation table (eval B0→B7) is what shows they do work.

---

# Component Architecture

## Component map

| ID | Component | Package / path | Runs in |
|---|---|---|---|
| C01 | IngestionService + IntegrityGate | `trusttwin/integrity/` | live path (fast) |
| C02 | Storage layer (repos + DBWriter + spool) | `trusttwin/storage/` | live path |
| C03 | FeatureBuilder | `trusttwin/features/` | live path (fast) |
| C04 | Model layer (Reference, Tracker, Envelope, Joint, Fallback, Registry) | `trusttwin/models/` | live path (fast) |
| C05 | FastDetector (triggers) | `trusttwin/detection/` | live path (fast) |
| C06 | AdmissionController (+ checkpoints, rollback) | `trusttwin/admission/` | live path |
| C07 | EpisodeManager | `trusttwin/episodes/manager.py` | live path (diagnostic) |
| C08 | Adjudicator (sequential evidence) | `trusttwin/episodes/adjudicator.py` | live path (diagnostic) |
| C09 | NetworkContext (minimal, conditional) | `trusttwin/network/` | live path (diagnostic, optional) |
| C10 | ConfidenceEngine | `trusttwin/confidence/` | live path (diagnostic) |
| C11 | SeverityEngine | `trusttwin/severity/` | live path (diagnostic) |
| C12 | ExplanationEngine | `trusttwin/explain/` | live path (cheap) + on-demand |
| C13 | SensorHealthEngine | `trusttwin/health/engine.py` | health path (daily) |
| C14 | DegradationEngine | `trusttwin/health/degradation.py` | health path (daily) |
| C15 | MaintenanceEngine | `trusttwin/health/maintenance.py` | health path (daily) |
| C16 | CorrectionEngine `[PS-O]` | `trusttwin/correction/` | live path (optional) |
| C17 | StationProcessor / EngineService | `trusttwin/engine/` | live path (orchestrator) |
| C18 | API service | `trusttwin/api/` | API process |
| C19 | EventBus + SSE | `trusttwin/engine/bus.py`, `api/routers/stream.py` | API process |
| C20 | Simulator + StreamReplayer + HeartbeatWatchdog | `trusttwin/simulator/`, `integrity/watchdog.py` | API process / CLI |
| C21 | Anomaly Injector | `trusttwin/injector/` | offline + simulator |
| C22 | Training & Calibration pipeline | `trusttwin/models/training.py`, `scripts/` | offline |
| C23 | Evaluation harness | `trusttwin/eval/` | offline |
| C24 | Dashboard | `dashboard/` | separate process |
| C25 | Edge screening reference `[PS-S]` | `trusttwin/edge/` | offline / optional device |
| C26 | Cross-cutting: Auth, Config, Logging, Audit | `trusttwin/core/`, `api/auth.py` | everywhere |

Each spec below uses the same eight fields. Mechanism-level detail is in the later sections named in "Detail".

---

### C01 — IngestionService + IntegrityGate

* **Purpose:** Turn a raw packet into a validated, ordered, de-duplicated observation; detect all transport/integrity problems deterministically without ML. `[PS-M]` communication-error handling.
* **Technology:** Python, Pydantic v2 models, pure functions + small state object per station.
* **Inputs:** `ObservationIn` (JSON/CSV row); station config (cadence, resolution, ranges); `last_event_ts`, `last_values`, `flat_run_state` from `StationState`; a `Clock`.
* **Outputs:** `IntegrityResult { flags: set[IntegrityFlag], disposition: ACCEPT | ACCEPT_LATE | REJECT, missing_slots: list[datetime], channel_nulls: list[Channel], flat_runs: dict[Channel,int] }`.
* **Dependencies:** `core.schemas`, `core.clock`, station config from `storage`.
* **API:** internal `IntegrityGate.check(obs, state) -> IntegrityResult`. REST exposure: `POST /v1/observations` (via C18).
* **Tests:** unit — each flag from a minimal fixture; property tests (hypothesis) — gate never raises on arbitrary dict/float/None/NaN/inf/string input; duplicate idempotency; watermark boundary (exactly 2 cadences late); the R-a/R-b/R-c freeze-vs-stale rules (see ML Layer §Freeze); MISSING_SLOT vs GAP boundary at N_gap.
* **Failure behavior:** Never raises. Malformed input → `MALFORMED_RECORD`, disposition `REJECT`, raw payload still stored verbatim. Unknown station → HTTP 404 from the API (not from the gate). If station config is missing a field, defaults from `config/stream_contract.yaml` are used and `CONFIG_DEFAULTED` is logged.
* **Detail:** Data Schemas §Stream contract; ML Layer §Integrity rules.

### C02 — Storage layer

* **Purpose:** Persist everything needed for replay and audit; guarantee raw immutability; never silently drop data.
* **Technology:** stdlib `sqlite3` in WAL mode; one **DBWriter** thread with a bounded queue and group commit (≤ 50 ms or ≤ 100 rows); repository classes with plain SQL; a JSONL **spool** used when the DB is unavailable.
* **Inputs:** Persist commands from the engine (`SaveRaw`, `SaveDecision`, `UpsertEpisode`, `UpsertAlert`, `LogAdmission`, `SaveCheckpoint`, `SaveHealthSnapshot`, `SaveCorrection`, `Audit`).
* **Outputs:** Rows; read models for the API (`list_alerts`, `get_episode`, `timeseries`, …).
* **Dependencies:** `schema.sql`, `core.config`.
* **API:** internal repos; REST reads via C18.
* **Tests:** DDL applies from empty; UPDATE/DELETE on `raw_observations` aborts (INV-02); group-commit ordering; DB-locked chaos test → spool fills → replay on recovery → row count equals received count (INV-11); migration test using `PRAGMA user_version`.
* **Failure behavior:** Write failure → retry with backoff (3×) → spill to `data/spool/<station>.jsonl` → `system_mode` stays normal but `/ready` reports `storage: DEGRADED`. Spool full (10 000 records) → API returns **HTTP 503 + Retry-After** and increments `rejected_backpressure`. No silent drop.
* **Detail:** §Database.

### C03 — FeatureBuilder

* **Purpose:** Deterministic, versioned construction of features from T/P/RH, timestamp, and the station's **clean buffer**. `[PS-M]` temporal + seasonal.
* **Technology:** NumPy ring buffers; no Pandas in the hot path.
* **Inputs:** `Observation`, `CleanBuffer` (last 96 admitted-or-internally-filled slots per channel), station `seasonal_mode`.
* **Outputs:** `FeatureVector { ref_x: ndarray, trk_x: ndarray, derived: {dewpoint_c, vapour_pressure_hpa}, feature_version: "f1" }`.
* **Dependencies:** `features.calendar`, `features.buffers`.
* **API:** internal `FeatureBuilder.build(obs, buffer, seasonal_mode) -> FeatureVector`.
* **Tests:** golden feature vectors for fixed timestamps; NaN lag handling; `DIURNAL_ONLY` drops doy terms; identical output for identical input (determinism); derived features tagged `derived`.
* **Failure behavior:** Insufficient buffer → lag entries are `NaN` (HistGradientBoosting handles NaN natively) and `warmup=True` is returned. Never raises.
* **Detail:** §ML Layer.

### C04 — Model layer

* **Purpose:** Provide expectation, uncertainty envelope, and joint consistency for each channel. Holds `REFERENCE_v` and the `TRACKER` model per station.
* **Technology:** `HistGradientBoostingRegressor` (3 reference + 3 tracker per station); `MinCovDet` for joint Σ; robust-scale lookup tables; joblib artifacts; `ModelRegistry` with LRU cache.
* **Inputs:** `FeatureVector`, station id, requested version (default `active`).
* **Outputs:** `Expectation { ref_pred[3], trk_pred[3], scale[3], band_lo[3], band_hi[3], z_ref[3], z_trk[3], d2, loo_z[3], model_versions }`.
* **Dependencies:** artifacts in `models_store/<station>/`, table `model_versions`.
* **API:** internal `ModelRegistry.get(station) -> StationModels`; REST: `GET /v1/stations/{id}/model-versions`.
* **Tests:** artifact round-trip; determinism for fixed seed; envelope coverage on clean validation (reported, not asserted); registry falls back on corrupt artifact; version status `untrusted` is never selected.
* **Failure behavior:** Artifact missing/corrupt/unloadable → `FallbackDetector` (robust hour×month median/MAD) and `system_mode = MODEL_UNAVAILABLE` (or `COLD_START` if the station has never had a model). Confidence is `null` with `calibration_status = OUT_OF_DOMAIN`. No false certainty.
* **Detail:** §ML Layer.

### C05 — FastDetector

* **Purpose:** Cheap per-observation suspicion triggers. Opens episodes; never assigns a root cause by itself except deterministic integrity classes. `[PS-M]` spikes, frozen values, multivariate consistency.
* **Technology:** NumPy scalar arithmetic; CUSUM/EWMA state in `StationState`.
* **Inputs:** `Expectation`, `IntegrityResult`, `StationState.detector_state`.
* **Outputs:** `TriggerResult { triggered: bool, reasons: list[TriggerReason], channels: set[Channel], anomaly_score: float }`.
* **Dependencies:** C03, C04, `config/default.yaml` thresholds.
* **API:** internal only.
* **Tests:** each trigger fires on a synthetic input and stays quiet on clean validation replay (false-trigger rate reported per station-day); CUSUM reset policy; MAD/scale floor prevents divide-by-zero on flat data; quantization stress test (legitimately flat quantized RH does not trigger).
* **Failure behavior:** If `Expectation` is unavailable, only integrity triggers (range, flat-run, step) run; result carries `degraded=True`.
* **Detail:** §ML Layer §Triggers.

### C06 — AdmissionController (+ checkpoints, rollback)

* **Purpose:** Decide which observations may update the adaptive tracker; make every update traceable and reversible. **Core innovation.**
* **Technology:** Explicit state machine; JSON tracker snapshots; replay from `admission_log`.
* **Inputs:** `TriggerResult`, `IntegrityResult`, open episode (if any), `system_mode`.
* **Outputs:** `AdmissionDecision { state: ADMIT | QUARANTINE | REJECT | UNKNOWN, channel_states: {T,P,RH → ADMIT|QUARANTINE}, reason }`; side effects on tracker state; `tracker_checkpoints` rows.
* **Dependencies:** C04 (tracker), C02.
* **API:** `GET /v1/stations/{id}/provenance`, `POST /v1/stations/{id}/rollback` (admin).
* **Tests:** state-machine table test (every transition); **INV-04** property test (tracker state hash unchanged by quarantined-only sequences); rollback restores the exact hash of the checkpoint; replay of the admission log reproduces the current tracker state; release-on-weather re-admits held records.
* **Failure behavior:** Any exception → state `UNKNOWN` (record held, not admitted, not called fault), error logged with `obs_id`. Tracker is never updated on the exception path.
* **Detail:** §ML Layer §Admission and rollback.

### C07 — EpisodeManager

* **Purpose:** Own the episode lifecycle `OPEN → UPDATE → CLOSE`; create exactly one alert per episode.
* **Technology:** Plain Python state machine; persisted in `episodes` and `episode_steps`.
* **Inputs:** `TriggerResult`, `AdjudicationResult`, observation, `IntegrityResult`.
* **Outputs:** `Episode` (with `status`, `onset_est_ts`, `n_obs`, `channel`, `root_cause`, `attribution`), `Alert` upserts.
* **Dependencies:** C08, C10, C11, C02.
* **API:** `GET /v1/episodes/{id}`, `GET /v1/episodes/{id}/replay`, `GET /v1/alerts`.
* **Tests:** lifecycle table test; **INV-09** (exactly one alert per episode however many observations arrive); close-rule test (m consecutive in-band observations); maximum-age → `ABSTAINED` close; overlapping integrity and sensor episodes on the same station coexist; chronic-episode handling (> 72 h open).
* **Failure behavior:** Exception in adjudication → episode stays `OPEN` with `adjudicator_action = WAIT` and a `note`; alert stays `PROVISIONAL`. The observation is still stored and quarantined.
* **Detail:** §Data Flow DF-2.

### C08 — Adjudicator

* **Purpose:** Sequential evidence accumulation over competing hypotheses; returns `DECIDE`, `WAIT`, `ABSTAIN`, or `AMBIGUOUS`. `[PS-M]` genuine-event vs sensor-anomaly distinction, root cause.
* **Technology:** NumPy least-squares shape fits; `LogisticRegression` weights loaded from `adjudicator_params.json`.
* **Inputs:** Episode residual window (`z_trk`, `z_ref`, `d2`, `loo_z`, flat-run lengths), `NetworkContext` (optional), episode age.
* **Outputs:** `AdjudicationResult { scores: {h: float}, pseudo_posterior: {h: float}, action, top_hypothesis, runner_up, root_cause, channel, attribution, rationale: list[EvidenceItem] }`.
* **Dependencies:** C04, C09, `config/adjudicator.yaml`.
* **API:** internal; results exposed via `GET /v1/episodes/{id}`.
* **Tests:** one canonical residual sequence per hypothesis decides correctly with default params; a spike sequence never returns `STEP_BIAS` after a return-to-band observation; ambiguous sequence → `WAIT` then `ABSTAIN` at max age (Scenario 7); coherent T/RH/P shift → `WEATHER_OR_REGIME` (Scenario 6); out-of-family shape → `UNKNOWN_UNMODELED`; parameters loaded from file change behavior (no hard-coded constants).
* **Failure behavior:** Missing `adjudicator_params.json` → built-in defaults and `calibration_status = UNCALIBRATED_PROVISIONAL`. NaN in the window → NaN observations are skipped in fits; if fewer than `n_min` valid points → `WAIT`.
* **Detail:** §ML Layer §Adjudicator.

### C09 — NetworkContext (minimal, conditional) `[PS-S]` context, optional layer

* **Purpose:** Supply neighbour evidence when resolvable; otherwise say so. Never treat disagreement as proof of fault. Supports the PS reference example (audit X05).
* **Technology:** Haversine geometry; reads neighbours' latest **tracker z-scores** (not raw values, so elevation/climate differences cancel).
* **Inputs:** Station id, episode onset time, neighbours' latest decisions, station coordinates.
* **Outputs:** `NetworkContext { state: NETWORK_UNAVAILABLE | NETWORK_UNRESOLVED | NEIGHBORS_NORMAL | NEIGHBORS_ALSO_ANOMALOUS | SYNCHRONIZED_DATA_EVENT | NO_NETWORK_CONFIRMATION, n_neighbors_used, neighbor_summary }`.
* **Dependencies:** `stations` table, `decisions` table.
* **API:** `GET /v1/stations/{id}/network-context?at=<ts>`.
* **Tests:** ≥ 3 fresh neighbours → resolvable; < 3 → `NETWORK_UNRESOLVED`; neighbours with synchronized `MISSING_SLOT` → `SYNCHRONIZED_DATA_EVENT`; module disabled → `NETWORK_UNAVAILABLE` and station-local outputs unchanged (Level-1 fallback test); coordinates missing → `NETWORK_UNRESOLVED`.
* **Failure behavior:** Any failure → `NETWORK_UNAVAILABLE`. The adjudicator receives no network evidence and continues.
* **MVP limit:** onset-propagation timing (speed/direction of a front) is **not** implemented. Only coincident-anomaly context is. This is stated in the UI.
* **Detail:** §ML Layer §Network context.

### C10 — ConfidenceEngine

* **Purpose:** Provide interpretable, documented confidence. `[PS-M]` confidence scores.
* **Technology:** `IsotonicRegression` per (route, horizon bin, kind); JSON calibration artifact; scikit-learn.
* **Inputs:** Raw score(s), route (`POINT_TRIGGER` / `EPISODE_DECIDED`), evidence horizon `n_obs`, hypothesis class.
* **Outputs:** `Confidence { detection_confidence: float|null, attribution_confidence: float|null, calibration_status, scope_note }`.
* **Dependencies:** `models_store/calibration/calibration_v*.json`.
* **API:** internal; `GET /v1/calibration` returns the active calibration summary and reliability table.
* **Tests:** monotone mapping; bin-fallback order (bin → route-pooled → uncalibrated); `null` attribution while `WAIT`; provisional alert carries `UNCALIBRATED_PROVISIONAL` when no artifact exists (INV-12); ECE script reproduces on a fixed seed.
* **Failure behavior:** Artifact absent/stale → confidence `null`, `calibration_status = UNCALIBRATED_PROVISIONAL`, UI shows "not calibrated". Never fabricates a number.
* **Detail:** §ML Layer §Confidence.

### C11 — SeverityEngine

* **Purpose:** Operational seriousness, independent of confidence. `[PS-M]` severity.
* **Technology:** Pure function with YAML weights.
* **Inputs:** max |z| across channels, episode age, channels affected, integrity gap duration.
* **Outputs:** `Severity { score: 0..1, level: LOW | MODERATE | HIGH | CRITICAL, components }`.
* **Dependencies:** `config/severity.yaml`.
* **API:** internal.
* **Tests:** the two worked examples in §ML Layer §Severity (high severity/low confidence; low severity/high confidence) are asserted; monotonicity in each component; level thresholds at boundaries.
* **Failure behavior:** Missing inputs → component treated as 0 and `severity.incomplete=true`.

### C12 — ExplanationEngine

* **Purpose:** Human-readable evidence for every non-normal decision. `[PS-M]` explainability; SHAP `[PS-S]` optional.
* **Technology:** Deterministic template rendering from structured `EvidenceItem`s; optional model-agnostic `shap.Explainer`.
* **Inputs:** `Expectation`, `TriggerResult`, `AdjudicationResult`, `AdmissionDecision`, `NetworkContext`, versions.
* **Outputs:** `EvidenceCard` (structured JSON + rendered text), one-line `summary`.
* **Dependencies:** `explain/templates.py`.
* **API:** `GET /v1/episodes/{id}/evidence-card`, `GET /v1/episodes/{id}/shap` (optional).
* **Tests:** card contains raw value, expected value, residual, ≥ 1 supporting and (when present) ≥ 1 counter-evidence item; no template placeholder is ever left unrendered; text never contains a hardware-component claim; fidelity metric (§Explainability).
* **Failure behavior:** Template error → fallback card listing raw structured items; SHAP missing → `501 SHAP_UNAVAILABLE`.

### C13 — SensorHealthEngine

* **Purpose:** Longitudinal per-channel health state with a station roll-up. `[PS-M]`.
* **Technology:** Daily aggregation from `decisions` + threshold state machine with hysteresis.
* **Inputs:** Daily indicators, episode counts, quarantine fraction, degradation output.
* **Outputs:** `SensorHealth { station_state, channels: {T,P,RH → state, indicators}, model_integrity }`.
* **Dependencies:** C14, `config/health.yaml`.
* **API:** `GET /v1/stations/{id}/health`, `GET /v1/stations/{id}/health/history`.
* **Tests:** **INV-08** (a single anomaly can never move any channel beyond `WATCH`); table-driven transition tests; hysteresis; `REVIEW_REQUIRED` exits only by admin acknowledgement; cold start yields `UNKNOWN`.
* **Failure behavior:** Insufficient history → `UNKNOWN` (never `HEALTHY` by default).

### C14 — DegradationEngine

* **Purpose:** Early-warning indication of declining channel reliability; not a failure-date prediction. `[PS-M]`.
* **Technology:** Tabular two-sided CUSUM; `scipy.stats.theilslopes`; `scipy.stats.kendalltau`; EWMA variance ratio.
* **Inputs:** Daily reference-divergence series and variance ratio per channel, weather-coherence veto flag.
* **Outputs:** `Degradation { state: NO_DEGRADATION_EVIDENCE | POSSIBLE_DEGRADATION | PERSISTENT_DEGRADATION_REVIEW, channel, horizon_days, slope_per_day, slope_ci, cusum, calibration_status }`.
* **Dependencies:** C13, `config/health.yaml`, calibrated CUSUM `h` from `scripts/calibrate_cusum.py`.
* **API:** included in `GET /v1/stations/{id}/health`.
* **Tests:** synthetic drift sweep (several rates) — warning lead time recorded; clean replay — false-warning rate recorded; coherent regime shift is vetoed; minimum horizon respected; output has no field named `remaining_useful_life` or `failure_date`.
* **Failure behavior:** Fewer than `min_horizon_days` of admitted history → `NO_DEGRADATION_EVIDENCE` with `reason = INSUFFICIENT_HORIZON`.

### C15 — MaintenanceEngine

* **Purpose:** Evidence-based maintenance indication with a documented trigger rule. `[PS-M]`.
* **Technology:** Table lookup + templates.
* **Inputs:** Channel health state, degradation state, recurring root-cause classes.
* **Outputs:** `MaintenanceIndication { priority: NONE | MONITOR | REVIEW | PRIORITY_REVIEW, channel, reasons, suggested_action, status, disclaimer }`.
* **Dependencies:** C13, C14.
* **API:** `GET /v1/stations/{id}/maintenance`, `POST /v1/stations/{id}/maintenance/ack`.
* **Tests:** state→priority map; suggested action text is generic (inspect / clean / verify against an independent reference) and never names a part number; acknowledgement is audited.
* **Failure behavior:** Unknown state → `MONITOR` with reason `STATE_UNKNOWN`.

### C16 — CorrectionEngine `[PS-O]`

* **Purpose:** Optional estimated replacement values, always separate from raw. Not on the critical path.
* **Technology:** Linear/cubic interpolation, tracker prediction, bias subtraction; feature flag `correction.enabled`.
* **Inputs:** `Decision`, episode, `AdmissionDecision`, `Expectation`, attribution confidence.
* **Outputs:** `Correction { estimated_value, low, high, method, is_estimate: true, eligible_reason }` or `null` with `reason`.
* **Dependencies:** C04, C02.
* **API:** `GET /v1/stations/{id}/corrections`.
* **Tests:** **INV-06** (raw unchanged; estimates only in `corrections`); **INV-07** (no correction when `attribution ∈ {UNRESOLVED, MIXED, UNKNOWN_UNMODELED}` or `WEATHER_SUPPORTED`); masked-region RMSE/MAE reported by eval harness.
* **Failure behavior:** Any doubt → no correction; decision shows `correction: null, correction_reason: <code>`.

### C17 — StationProcessor / EngineService

* **Purpose:** Orchestrate the per-observation pipeline in a fixed order; hold per-station state; enforce per-station ordering.
* **Technology:** Plain Python class per station; `EngineService` keeps `dict[station_id, StationProcessor]` and a per-station `threading.Lock`; `ThreadPoolExecutor`.
* **Inputs:** `ObservationIn`.
* **Outputs:** `Decision` (persisted + emitted on the bus).
* **Dependencies:** C01–C16, C19.
* **API:** `process_observation(obs) -> Decision` (the single entry point, P1).
* **Tests:** end-to-end golden replay (INV-05); ordering under concurrent submission for the same station; concurrency across stations; chaos (model unavailable, DB down, network module off).
* **Failure behavior:** Every stage is wrapped; a stage failure degrades the decision (`system_mode`), never drops the observation.
* **Detail:** §Backend §Pipeline.

### C18 — API service

* **Purpose:** REST ingestion and read models; SSE stream; admin operations. `[IC]`
* **Technology:** FastAPI, Pydantic v2, Uvicorn.
* **Inputs/Outputs:** JSON contracts in §Data Schemas.
* **Dependencies:** C17, C02, C19, C26.
* **API:** §APIs.
* **Tests:** TestClient contract tests for every route; auth matrix; 422 on extra fields; OpenAPI export diff test.
* **Failure behavior:** Uniform error envelope `{error:{code,message,details,request_id}}`; 503 on backpressure; `/ready` reflects storage/model/simulator status.

### C19 — EventBus + SSE

* **Purpose:** Push `decision`, `alert`, `health`, `episode` events to subscribers. Optional for the dashboard (polling is the default).
* **Technology:** In-process pub/sub with bounded per-subscriber `asyncio.Queue`; `text/event-stream` route.
* **Inputs:** Events from C17. **Outputs:** SSE frames.
* **Dependencies:** none external.
* **API:** `GET /v1/stream?station_id=&types=`.
* **Tests:** slow subscriber drops oldest events without blocking the engine; unsubscribing frees the queue.
* **Failure behavior:** Bus failure is logged and ignored by the engine. The decision path never depends on the bus.

### C20 — Simulator + StreamReplayer + HeartbeatWatchdog

* **Purpose:** Produce clean-base T/P/RH streams, genuine-event surrogates, and scripted demo scenarios; replay them at a configurable rate; detect real-time comm loss via expected-slot schedule. `[PS-M]` real-time demonstrability.
* **Technology:** NumPy generators with fixed seeds; `Clock` abstraction (`SystemClock`, `SimClock`); `DirectSink` (calls `process_observation`) and `HttpSink` (POSTs to the API).
* **Inputs:** Scenario YAML, seed, speed factor, station set.
* **Outputs:** Observation stream; `injection_log` rows (demo mode only).
* **Dependencies:** C21 (injector), C17 or C18.
* **API:** `GET /v1/simulator/scenarios`, `POST /v1/simulator/scenarios/{name}/run`, `POST /v1/simulator/stop`, `GET /v1/simulator/status`.
* **Tests:** identical seed → byte-identical stream; replay-rate accuracy within tolerance; watchdog emits `MISSING_SLOT` at `slot + grace` under `SimClock`; the engine never reads `injection_log` (INV-03).
* **Failure behavior:** Runner error → run marked `FAILED`, API and engine unaffected.

### C21 — Anomaly Injector

* **Purpose:** Apply the 14 fault families (T/P/RH only) to clean series and produce exact ground-truth labels and metadata. `[PS-M]` anomaly-injected evaluation.
* **Technology:** NumPy; one class per family; independent `holdout` family (written from different parameterizations).
* **Inputs:** Clean frame, recipe YAML, seed.
* **Outputs:** Injected frame + `labels.parquet` + `injections.json`.
* **Dependencies:** none from `engine`.
* **API:** CLI `scripts/inject.py`; used by C20/C23.
* **Tests:** seeded determinism; label length equals frame length; label = 1 exactly where the family's labelling rule says; no channel outside {T,P,RH} can be targeted; overlap rules respected.
* **Failure behavior:** Invalid recipe → fail fast with the offending key named.
* **Detail:** §Fault Injection.

### C22 — Training & Calibration pipeline (offline)

* **Purpose:** Produce versioned artifacts: reference, tracker, scale tables, joint Σ, fallback stats, CUSUM `h`, adjudicator weights, calibration maps.
* **Technology:** scikit-learn, joblib, scripts.
* **Inputs:** Chronological train/validation splits from the benchmark builder.
* **Outputs:** `models_store/<station>/reference_v<n>/`, `tracker_v<n>/`, `models_store/calibration/`, `models_store/adjudicator/`, rows in `model_versions`.
* **Dependencies:** C03, C04, C21.
* **API:** CLI `scripts/train_station.py`, `calibrate.py`, `calibrate_cusum.py`, `fit_adjudicator.py`.
* **Tests:** artifact metadata records train window (no overlap with validation/test — INV-14); same seed → same artifact hash; refuses to train on a window containing rows flagged by the label file when `--clean-only` is set.
* **Failure behavior:** Failed training never overwrites `active`; new version is written as `retired` until promoted.

### C23 — Evaluation harness

* **Purpose:** Baseline ladder B0–B7 (B8 optional), metrics, poisoning experiment, calibration/risk–coverage, explanation fidelity, latency and load. `[PS-M]` evidence for accuracy claims.
* **Technology:** Pandas, scikit-learn metrics, Plotly/Matplotlib for report figures.
* **Inputs:** Test split, labels, held-out injector family, artifacts.
* **Outputs:** `reports/<run_id>/` (CSV, JSON, PNG, `REPORT.md`).
* **Dependencies:** C21, C22, C17.
* **API:** CLI `scripts/run_eval.py`.
* **Tests:** metric functions against hand-computed toy cases; point-adjust is **not** implemented (asserted absent); report generator refuses to write a headline number without the phrase "evaluation on anomaly-injected data".
* **Failure behavior:** A failing baseline is recorded as `FAILED` in the table; others continue.

### C24 — Dashboard

* **Purpose:** Operational view. `[PS-M]`. Pages in §Frontend.
* **Technology:** Streamlit multipage, Plotly, `requests`.
* **Inputs:** REST API only.
* **Outputs:** Browser UI.
* **Dependencies:** C18.
* **API:** consumes §APIs.
* **Tests:** `streamlit.testing.v1.AppTest` smoke test per page against a fixture API; **INV-10** import scan (no `trusttwin.engine`, no `sqlite3`).
* **Failure behavior:** API unreachable → banner "API unavailable" + last cached data flagged stale; no crash.

### C25 — Edge screening reference `[PS-S]`

* **Purpose:** Show the edge/server split honestly: fixed-memory screening checks only.
* **Technology:** Pure Python reference with fixed-size arrays (portable to C); optional Arduino/ESP32 sketch stub, **not** part of the MVP.
* **Inputs:** Raw samples. **Outputs:** `EdgePacket { seq, ts, T, P, RH, flags, suspicion_bits }`.
* **Dependencies:** none.
* **API:** `POST /v1/observations` accepts the packet's core fields; extra edge fields ride in `meta` (ignored by the engine).
* **Tests:** the reference produces identical flags to the server integrity rules on a shared fixture; memory footprint of the reference state is computed and asserted below the declared budget.
* **Failure behavior:** If the target device cannot host the checks, the device sends raw samples only (server does everything).
* **Claim discipline:** no ESP32 energy or latency figure exists until measured on a board.

### C26 — Cross-cutting: Auth, Config, Logging, Audit

* **Purpose:** API keys, config loading/validation, structured logs, audit trail.
* **Technology:** FastAPI dependencies; Pydantic Settings; stdlib `logging` with a JSON formatter; `audit_log` table.
* **Tests:** role matrix; config validation rejects unknown keys; log records carry `station_id/obs_id/episode_id`; audit rows for rollback/ack/config reload.
* **Failure behavior:** Invalid config at start → process exits with a message naming the key. Config reload failure → previous config retained, audited.
* **Detail:** §Backend §Authentication, §Logging.

