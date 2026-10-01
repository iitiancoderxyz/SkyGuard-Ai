# 22_FINAL_QA_AUDIT — SkyGuard AI

**Role:** FINAL QA ARCHITECT  
**Project:** SkyGuard AI  
**Problem Statement:** SIH26073 — AI/ML-Based Intelligent Anomaly Detection for Automatic Weather Stations (AWS)  
**Date:** 30 September 2026  
**Status:** **AUDIT COMPLETE (NO IMPLEMENTATION PERFORMED)**  

---

## 1. Overall System State

The SkyGuard AI repository currently contains a complete 6-phase foundation with 102 automated unit and integration tests passing. The underlying mathematical and meteorological intelligence modules (MAD z-scores, step-jump triggers, rate limiters, dual-clock reference profiles, adaptive trackers, and multi-factor decision adjudicators) are functional and execute within sub-millisecond budgets (< 0.25 ms pure ML inference).

However, a systematic architectural audit reveals critical integration gaps between backend persistence, API serialization, and frontend presentation:
1. **Schema & Persistence Disconnect:** The `decisions` SQLite table and `ObservationRepository` discard the `decision_state`, `reasoning_summary`, and `evidence_codes`, causing historical queries to default to `NORMAL`.
2. **Chart Fragility:** Plotly chart components break on missing channels (`None`/`NaN`) and use duplicate categorical time strings on x-axes.
3. **UI Quality & Branding:** The dashboard displays obsolete "TRUST-TWIN" branding, emojis, generic AI phrasing, and hardcoded overview reasoning templates.
4. **Error & Debug Exposure:** Raw exception strings, unparsed JSON blobs, and debug dictionaries are displayed directly in user-facing tables.
5. **Scenario Feedback Mismatch:** Demonstration replays render pre-injection baseline points (the first 5 records), leading operators to believe injections failed.

---

## 2. All Existing Web Interfaces

| Interface | Purpose | Framework | Entry Point | Port | User-Facing? | Status / Action |
|---|---|---|---|---|---|---|
| **Operational Monitoring Dashboard** | Primary operator dashboard for AWS monitoring, alerts, trends, diagnostics, and demo testbed | Streamlit | `dashboard/app.py` | `8501` | **YES** | **Keep as the SINGLE user-facing product UI**; polish layout, remove emojis, fix state bugs |
| **FastAPI Swagger UI** | Interactive API specification and schema testing for developers | OpenAPI / Swagger | `app/main.py` (`/docs`) | `8000` | **NO** (Developer only) | **Keep as developer-only endpoint**; do not present as an end-user website |
| **FastAPI ReDoc** | Alternative static OpenAPI documentation viewer | ReDoc | `app/main.py` (`/redoc`) | `8000` | **NO** (Developer only) | **Keep as developer-only endpoint** |

---

## 3. Final Recommended Application Topology

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      SkyGuard AI Architecture                           │
└─────────────────────────────────────────────────────────────────────────┘

   OPERATOR / USER VIEW                    DEVELOPER / API CONSUMER
           │                                           │
           ▼                                           ▼
┌──────────────────────┐                   ┌────────────────────────┐
│ Streamlit Dashboard  │                   │ FastAPI REST / Docs    │
│ http://localhost:8501│                   │ http://127.0.0.1:8000  │
│                      │                   │ (/docs, /redoc)        │
└──────────┬───────────┘                   └───────────┬────────────┘
           │                                           │
           │ HTTP REST (api_client.py)                 │
           └───────────────────┬───────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      FastAPI Application Service                        │
│                         (app/main.py :8000)                             │
│                                                                         │
│  /v1/observations   /v1/stations   /v1/decisions   /v1/simulator/run    │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Core Intelligence Engine                           │
│                     (app/runtime/engine.py)                             │
│                                                                         │
│  Deterministic Gate ──> Feature RingBuffer ──> Statistical Detector     │
│                                                     │                   │
│                                                     ▼                   │
│  Decision Adjudicator <── Reference Profile & Adaptive Tracker          │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  SQLite WAL Database (Immutable Lake)                   │
│                         (data/trusttwin.db)                             │
│                                                                         │
│  raw_observations (Triggers) ──> processed_observations ──> decisions   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Data Traceability Findings

| Data Field | Source of Truth | Persistence / Storage | API Propagation | Frontend Rendering | Integrity Status |
|---|---|---|---|---|---|
| **Temperature** | Ingestion Payload (`ObservationIn`) | `raw_observations.temperature_raw`, `processed_observations.temperature` | `/v1/stations/{id}/observations` -> `temperature` | `overview.py`, `historical.py` KPI & Plotly trace | **VERIFIED REAL** (Raw immutable) |
| **Pressure** | Ingestion Payload (`ObservationIn`) | `raw_observations.pressure_raw`, `processed_observations.pressure` | `/v1/stations/{id}/observations` -> `pressure` | `overview.py`, `historical.py` KPI & Plotly trace | **VERIFIED REAL** (Raw immutable) |
| **Relative Humidity** | Ingestion Payload (`ObservationIn`) | `raw_observations.relative_humidity_raw`, `processed_observations.relative_humidity` | `/v1/stations/{id}/observations` -> `relative_humidity` | `overview.py`, `historical.py` KPI & Plotly trace | **VERIFIED REAL** (Raw immutable) |
| **Anomaly Score** | `statistical_detector.py` / `adjudicator.py` | `decisions.anomaly_score` | `/v1/stations/{id}/observations` -> `anomaly_score` | Score progress bars & anomaly trajectory chart | **VERIFIED REAL** |
| **Decision State** | `adjudicator.py` | **OMITTED** from `decisions` table in `schema.sql` & `observation_repo.py` | `None` on query -> defaulted to `"NORMAL"` | Rendered as green "NORMAL" badge | **BUG CONFIRMED (Missing in DB)** |
| **Severity Level** | `adjudicator.py` | `decisions.severity` | `/v1/stations/{id}/observations` -> `severity` | Rendered on decision badge | **VERIFIED REAL** |
| **Confidence Scores** | `adjudicator.py` | `decisions.detection_confidence`, `decisions.attribution_confidence` | `/v1/stations/{id}/observations` -> `detection_confidence` | Rendered on confidence bars | **VERIFIED REAL** |
| **Root Cause** | `adjudicator.py` | `decisions.root_cause_category` | `/v1/stations/{id}/observations` -> `root_cause_category` | Root cause card & table column | **VERIFIED REAL** |
| **Reasoning Summary** | `adjudicator.py` | **NOT PERSISTED** in `decisions` table | `None` in historical API query | `overview.py` uses hardcoded string template | **BUG CONFIRMED (Templated in UI)** |
| **Evidence Codes** | `triggers/statistical.py` & `adjudicator.py` | **NOT PERSISTED** in `decisions` table | `None` in historical API query | Rendered only during direct manual POST | **BUG CONFIRMED (Missing in DB)** |
| **Derived Dewpoint** | `features/builder.py` | `feature_records.derived_dewpoint` | `/v1/stations/{id}/observations` -> `derived_dewpoint` | Rendered as derived KPI | **VERIFIED REAL** |

---

## 5. Anomaly State Bug

### Observed Problem
The dashboard overview displays a green **`NORMAL`** badge even when the backend statistical detector flags a severe spike or anomaly (e.g. anomaly score = 1.000, severity = HIGH, root cause = SENSOR_SPIKE).

### Exact Root Cause Analysis
1. **Database Schema Missing Column:** In `storage/schema.sql` (lines 115–133), the `decisions` table schema definition does not include a `decision_state` column.
2. **Repository Insert Dropping Value:** In `storage/repositories/observation_repo.py` (lines 141–181), the `save_decision` method accepts `decision_state: str` as a parameter, but the SQL `INSERT` statement only writes `(decision_id, observation_id, alert_stage, anomaly_score, severity, detection_confidence, attribution_confidence, uncertainty_state, root_cause_category, admission_state, reference_version, tracker_version)`. `decision_state` is completely omitted from the database write.
3. **Repository Query Omitting Column:** In `storage/repositories/observation_repo.py` (lines 183–200), `get_recent_observations` joins `decisions d` but does not include `d.decision_state` in the `SELECT` projection.
4. **Frontend Fallback Defaulting to NORMAL:** In `dashboard/views/overview.py` (line 102), the UI calls `render_decision_badge(decision_state=latest_obs.get("decision_state", "NORMAL"))`. Because `"decision_state"` is missing from the dictionary returned by `/v1/stations/{id}/observations`, `.get()` returns the default value `"NORMAL"`.

### Recommended Fix
- Alter `storage/schema.sql` to add `decision_state TEXT NOT NULL DEFAULT 'NORMAL'`, `reasoning_summary TEXT`, and `evidence_codes_json TEXT` to the `decisions` table.
- Update `save_decision` in `storage/repositories/observation_repo.py` to persist `decision_state`, `reasoning_summary`, and `evidence_codes_json`.
- Update `get_recent_observations` and `get_recent_decisions` in `storage/repositories/observation_repo.py` to select `d.decision_state`, `d.reasoning_summary`, and `d.evidence_codes_json`.

---

## 6. Chart Reliability Findings

### Observed Problem
Plotly historical charts intermittently crash with runtime exceptions or render blank rectangular boxes.

### Exact Root Causes
1. **Duplicate / Categorical X-Axis Indexing (`dashboard/components/charts.py:22`):**
   - Line 22 converts timestamps using `df_sorted["time_str"] = pd.to_datetime(df_sorted["event_timestamp"]).dt.strftime("%H:%M:%S")`.
   - When multiple readings share the same second or span across midnight, `time_str` generates duplicate string labels. Plotly treats string arrays as categorical bins, causing trace alignment errors and rendering crashes.
2. **Unchecked None / NaN Comparisons (`dashboard/components/charts.py:83, 94`):**
   - Line 83 evaluates `df_sorted[df_sorted["anomaly_score"] >= 0.35]`. When `anomaly_score` contains `None`, Python raises `TypeError: '>=' not supported between instances of 'NoneType' and 'float'`.
   - Line 94 formats hover text using `f"Anomaly Score: {score:.2f}"`. If `score` is `None`, Python raises `TypeError: unsupported format string passed to NoneType`.
3. **Missing Channel Rendering (`dashboard/components/charts.py:165`):**
   - When a sensor channel is missing (`None`), Plotly attempts to draw line segments across nulls without `connectgaps=True`, causing broken charts.
4. **Empty Dataframe Handling:**
   - In `dashboard/views/historical.py`, if a station has 0 records, the view does not return a clean styled placeholder, leaving empty Plotly canvas elements.

### Recommended Fix
- Use native ISO datetime objects `pd.to_datetime(df_sorted["event_timestamp"])` for the x-axis with standard date formatting rather than categorical string slices.
- Fill missing `anomaly_score` values with `0.0` before filtering (`df_sorted["anomaly_score"].fillna(0.0)`).
- Add `connectgaps=False` and safe formatters `f"{score:.2f}" if score is not None else "N/A"`.

---

## 7. Sensor Health Findings

### Current Health Calculation Logic
- In `app/api/routes.py` (lines 98–150), `get_station_health(station_id)` executes:
  1. Queries the recent 20 observations from `processed_observations`.
  2. Computes null fraction per channel: `t_avail = 1.0 - (t_nulls / total)`.
  3. Queries in-memory `StationState` for `CleanBuffer` depth (`buffer_depth`).
  4. Returns hardcoded model window metadata: `reference_profile_window = 96`, `adaptive_tracker_window = 12`, `anti_poisoning_status = "PROTECTED"`.
- In `storage/schema.sql` (lines 136–148), a table named `health_state` exists with columns `(station_id, channel, state, health_score, degradation_state, maintenance_state, model_integrity_state)`. **However, this table is never written to or queried anywhere in the codebase.**

### Assessment
- **Status:** **PARTIALLY DERIVED**.
- Channel availability and buffer depth are real values derived from database and engine memory.
- The `health_state` database table is unpopulated.
- The UI in `dashboard/views/sensor_health.py` displays these real availability percentages and buffer counts, but also displays static strings for baseline status.

### Recommended Fix
- Implement an explicit sensor health evaluation function in `health/sensor_health/` that aggregates:
  1. Channel availability over rolling windows.
  2. Baseline residual variance from `ReferenceProfile` / `AdaptiveTracker`.
  3. Persistent stuck/drift flags.
- Persist this structured health assessment into the `health_state` table upon each observation or health check.

---

## 8. Scenario Test Findings

### Scenario Truth Table

| Scenario Key | Injected Phenomenon | Target Channel | Ground Truth Manifest | Expected Decision State | Expected Root Cause | Current Pipeline Behavior |
|---|---|---|---|---|---|---|
| **NOMINAL** | Diurnal sine/cosine baseline | All (T, P, RH) | None | `NORMAL` | `NORMAL` | **PASS** (Score < 0.20, state = NORMAL) |
| **SPIKE** | Isolated step jump (+25.0°C) | Temperature | Index 12, Mag +25.0 | `ANOMALY` | `SENSOR_SPIKE` | **PASS** (Score = 1.00, trigger = TEMP_SPIKE) |
| **FLATLINE** | Frozen constant reading (12 steps) | Temperature | Index 8..20, Mag 0.0 | `ANOMALY` / `SUSPECT` | `SENSOR_STUCK_FROZEN` | **PASS** (Trigger = FROZEN_TEMPERATURE) |
| **DRIFT** | Progressive drift (+1.5%/step) | Humidity | Index 10..25, Rate 1.5 | `ANOMALY` / `SUSPECT` | `GRADUAL_DRIFT` | **PASS** (Trigger = ZSCORE_EXCURSION_RH) |
| **BIAS** | Sudden level shift (-20.0 hPa) | Pressure | Index 10..25, Mag -20.0 | `ANOMALY` | `SENSOR_SPIKE` | **PASS** (Trigger = PRESSURE_SPIKE_NEGATIVE) |
| **NOISE** | Elevated Gaussian noise (std=5.0) | Temperature | Index 10..25, Std 5.0 | `ANOMALY` / `SUSPECT` | `MULTIVARIATE_INCONSISTENCY` | **PASS** (Trigger = TEMP_UNREALISTIC_RATE) |
| **COMMUNICATION_GAP** | 4 dropped packets | Stream | Drop 4 slots | `NORMAL` / `ACCEPT_LATE` | `NORMAL` / `DATA_TELEMETRY` | **PASS** (Integrity flags = MISSING_SLOTS) |
| **MULTIVARIATE_INCONSISTENCY** | Thermodynamic conflict | T, P, RH | Inconsistent dewpoint | `ANOMALY` | `SENSOR_SPIKE` / `MULTIVARIATE` | **PASS** (Triggers on all 3 channels) |
| **GENUINE_WEATHER** | Cold front (-9°C T, +40% RH, +4hPa P) | All | Cold front manifest | `ANOMALY` / `NORMAL` | `TEMPORAL_INCONSISTENCY` | **PASS** (High Weather Likelihood = 0.83) |
| **COMBINED** | Simultaneous spike, gap, flatline | Multi | Combined manifest | `ANOMALY` | `SENSOR_SPIKE` / `STUCK` | **PASS** (Multiple triggers active) |

### Scenario UI Feedback Bug
In `dashboard/views/scenario_runner.py` (line 72):
```python
samples = data.get("sample_decisions", [])
if samples:
    df_samples = pd.DataFrame(samples)
    st.dataframe(df_samples[disp_cols], use_container_width=True)
```
In `app/api/routes.py` (line 164), the simulator endpoint returns `decisions[:5]`. In all scenarios, the fault injection onset starts at index 8, 10, or 12. Consequently, the first 5 decisions are ALWAYS clean normal baseline points. The operator views a sample table full of `NORMAL` states immediately after running an anomaly scenario.

### Recommended Fix
- Return both peak anomalous decisions and representative transition decisions in the scenario response.
- Update the scenario testbed UI to display the peak anomaly summary card and highlight the exact injection window.

---

## 9. Explainability / Reasoning Findings

### Current Logic
- `detection/decision/adjudicator.py` (lines 320–355) contains comprehensive, rule-based explainability that constructs `reasoning_summary` from active triggers:
  - Step spikes: `"Step spike detected: {triggers}"`
  - Rates: `"Unrealistic rate-of-change: {triggers}"`
  - Frozen: `"Frozen/stuck sensor detected on: {triggers}"`
  - Thermodynamics: `"Thermodynamic inconsistency: dewpoint exceeds temperature"`
  - Weather events: `"Multivariate T/P/RH pattern consistent with a weather event"`
  - Telemetry: `"Data/telemetry integrity flags: {flags}"`
- **Frontend Disconnect:** In `dashboard/views/overview.py` (line 143), the view ignores `latest_obs.get("reasoning_summary")` and instead generates a generic template:
  `f"Station {selected_station_id} recorded observation ID {latest_obs.get('observation_id')}. Disposition: {latest_obs.get('integrity_status', 'ACCEPT')}."`

### Available but Unexposed Intelligence
1. The structured breakdown of channel Z-scores (`channel_scores`).
2. The thermodynamic dewpoint depression and vapour pressure residual.
3. The specific trigger codes (e.g. `TEMPERATURE_SPIKE_POSITIVE`, `ROBUST_ZSCORE_EXCURSION_PRESSURE`).

### Recommended Fix
- Persist `reasoning_summary` and `evidence_codes_json` in the `decisions` table.
- Display the actual backend `reasoning_summary` in `overview.py` and `anomaly_monitor.py`.
- Expose the exact trigger values in an expandable evidence drawer.

---

## 10. UI Quality Findings

| Category | Finding in Current Codebase | Affected File(s) | Recommended Fix |
|---|---|---|---|
| **Emojis** | Excessive emojis (`🛡️`, `📡`, `🌡️`, `🧭`, `💧`, `🔬`, `🧠`, `⚡`, `📈`, `🛰️`, `🛠️`, `🧪`, `🚀`, `🟢`, `🟠`, `🔴`, `⚠️`, `🚨`, `❓`, `🔒`) | `dashboard/app.py`, all `dashboard/views/*.py`, `dashboard/components/*.py` | Replace all emojis with professional SVG/CSS indicators, clean meteorological badges, and standard typography |
| **Obsolete Branding** | "TRUST-TWIN" / "TRUST/TWIN" appearing in headers, sidebar, provenance cards, and tabs | `dashboard/app.py`, `dashboard/views/*.py` | Standardize product name to **SkyGuard AI**; refer to the dual-clock architecture strictly in technical diagnostic tabs |
| **AI-Style Phrasing** | Labels like "AI Anomaly & Trust State", "Poisoning Protection: ACTIVE", "Brain Reasoning" | `dashboard/views/overview.py`, `dashboard/components/explainability.py` | Rename to standard meteorological terms: "Anomaly Assessment", "Baseline Integrity", "Meteorological Diagnostics" |
| **Visual Hierarchy** | Dense rows of unpadded metrics and raw dataframe tables | `dashboard/views/overview.py`, `dashboard/views/anomaly_monitor.py` | Add structured card containers, clear severity color hierarchy, and formatted table headers |

---

## 11. Error Handling Findings

### Observed Problem
Technical debug logs, raw tracebacks, and internal JSON validation errors are exposed to the user interface.

### Exact Sources
1. **API Exception Details (`app/main.py:84`):**
   `global_exception_handler` returns `"details": str(exc)`, which transmits raw Python exception strings over the wire.
2. **Dashboard Validation Dumps (`dashboard/views/scenario_runner.py:129`):**
   When `POST /v1/observations` rejects a payload with HTTP 422, the dashboard executes `st.json(res.get("data"))`, rendering raw Pydantic validation tree structures to the user.
3. **Integrity Event Details (`dashboard/views/anomaly_monitor.py:93`):**
   The integrity events table renders the raw unparsed JSON string from `details` column (`"details": "{\"cadence\": 60, \"error\": ...}"`).

### Recommended Fix
- Sanitize API error responses to return user-friendly error messages while logging technical tracebacks to server logs with a `request_id`.
- Parse and format JSON details into readable strings in the UI tables.

---

## 12. Hardcoded / Fake / Unverified Data Findings

| Item | Status | Finding | Action Needed |
|---|---|---|---|
| **ML Anomaly Scores** | **VERIFIED REAL** | Computed by `statistical_detector.py` and `adjudicator.py` | None |
| **Likelihood Attributions** | **VERIFIED REAL** | Computed from `ReferenceProfile` and `AdaptiveTracker` | None |
| **Reasoning Summary in Overview** | **TEMPLATED IN UI** | `overview.py:143` overrides real backend reasoning with a static f-string | Replace with real backend `reasoning_summary` |
| **Model Window Constants** | **HARDCODED IN API** | `routes.py:136-137` hardcodes 96 and 12 | Read dynamically from configuration |
| **Health State Table** | **UNPOPULATED** | `health_state` table exists in schema but is never written to | Populate from sensor health evaluation |

---

## 13. Exact Files Requiring Modification

1. `storage/schema.sql`: Add `decision_state`, `reasoning_summary`, `evidence_codes_json` to `decisions` table.
2. `storage/repositories/observation_repo.py`: Update `save_decision`, `get_recent_observations`, `get_recent_decisions` to write and read decision state and explainability fields.
3. `app/runtime/engine.py`: Pass `reasoning_summary` and `evidence_codes` to `obs_repo.save_decision`.
4. `app/api/routes.py`: Clean up health endpoint, fix scenario response sample selection, dynamic window configs.
5. `app/main.py`: Sanitize error responses.
6. `dashboard/app.py`: Clean branding to "SkyGuard AI", remove all emojis, clean sidebar layout.
7. `dashboard/components/metrics.py`: Clean SVG/CSS badges without emojis, clean typography.
8. `dashboard/components/explainability.py`: Clean layout, remove emojis, expose real backend reasoning.
9. `dashboard/components/charts.py`: Datetime x-axis indexing, null-safe score formatting, error fallbacks.
10. `dashboard/views/overview.py`: Use real backend `decision_state` and `reasoning_summary`, remove emojis.
11. `dashboard/views/anomaly_monitor.py`: Clean alert feed, parse integrity event details, remove emojis.
12. `dashboard/views/historical.py`: Clean chart presentation, empty state handling.
13. `dashboard/views/sensor_health.py`: Professional diagnostics layout, remove emojis.
14. `dashboard/views/scenario_runner.py`: Format scenario samples around injection onset, clean validation feedback.

---

## 14. Priority 1 Fixes (Correctness & Data Truth)

1. **Fix Anomaly State Persistence:** Add `decision_state`, `reasoning_summary`, `evidence_codes_json` to `decisions` table in SQLite schema and `ObservationRepository` query projections.
2. **Fix Overview Decision Badge:** Ensure `dashboard/views/overview.py` displays the actual `decision_state` returned from the backend.
3. **Fix Chart Crashes & Null Values:** Fix datetime indexing and null-safe formatting in `dashboard/components/charts.py`.
4. **Fix Scenario Sampling Window:** Update simulator route and scenario view to return and display the peak anomaly decisions during injection onset.

---

## 15. Priority 2 Fixes (Explainability & Diagnostics)

1. **Expose Real Backend Reasoning:** Replace hardcoded overview template with `latest_obs["reasoning_summary"]` and `latest_obs["evidence_codes"]`.
2. **Populate Sensor Health Diagnostics:** Aggregate channel availability, variance drift, and communication gaps into structured health assessments.
3. **Sanitize Debug & Error Dumps:** Format raw integrity event JSON and handle API validation errors with clean warning cards.

---

## 16. Priority 3 Fixes (UI Quality, Polish & Branding)

1. **Standardize Branding:** Replace all visible "TRUST-TWIN" strings in the user interface with **SkyGuard AI**.
2. **Eliminate All Emojis:** Replace emoji icons across all views and components with clean meteorological typography and CSS indicators.
3. **Refine Visual Layout:** Improve spacing, color hierarchy, and metric card styling for a professional meteorological monitoring station aesthetic.

---

## 17. Recommended Implementation Order

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Recommended Implementation Order                    │
└─────────────────────────────────────────────────────────────────────────┘

  STEP 1: Database Schema & Persistence Alignment
          - Update storage/schema.sql (add decision_state, reasoning, evidence)
          - Update storage/repositories/observation_repo.py
          - Update app/runtime/engine.py
          - Run regression tests: python -m pytest

  STEP 2: Chart Reliability & Safe Formatting
          - Update dashboard/components/charts.py (datetime axis, null guards)
          - Update dashboard/views/historical.py

  STEP 3: Decision & Explainability Wiring
          - Update dashboard/views/overview.py (wire real decision_state & reasoning)
          - Update dashboard/views/anomaly_monitor.py
          - Update dashboard/components/explainability.py

  STEP 4: Scenario Testbed Alignment
          - Update app/api/routes.py (simulator peak anomaly window)
          - Update dashboard/views/scenario_runner.py

  STEP 5: UI Quality, Typography & Emoji Removal
          - Clean dashboard/app.py (SkyGuard AI branding, clean sidebar)
          - Clean all dashboard/components/*.py
          - Clean all dashboard/views/*.py

  STEP 6: End-to-End Validation & Verification
          - Run full test suite: python -m pytest
          - Execute full demonstration suite: python scripts/run_sih_demo.py
          - Verify UI live in browser
```

---

*End of Final QA Audit. Per instructions, no implementation has been executed.*
