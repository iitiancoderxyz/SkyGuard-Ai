# Repair 3 — Explainability & Sensor Health Report

## 1. Previous Problems
Prior to Repair 3:
1. **Templated & Ignored Explainability:**
   - `dashboard/views/overview.py` ignored real backend `reasoning_summary` and substituted a hardcoded template string.
   - Evidence codes in `overview.py` were artificially generated from `integrity_status` and `root_cause` strings instead of displaying the actual statistical/temporal trigger codes.
   - `dashboard/views/anomaly_monitor.py` did not expose real reasoning or evidence chips in operator review cards, and dumped raw unparsed JSON string blobs in integrity logs.
2. **Unpopulated & Static Sensor Health:**
   - The `health_state` table existed in SQLite schema but was never written to or queried.
   - Sensor health diagnostics in `app/api/routes.py` hardcoded model window metadata (`reference_profile_window = 96`, `adaptive_tracker_window = 12`) and lacked structured degradation states, maintenance recommendations, and evidence-based health classifications.
   - The dashboard lacked per-channel physical diagnostics and supporting evidence for assigned health states.

---

## 2. Explainability Changes (UNIT A)
1. **True Backend Reasoning Integration:**
   - `dashboard/views/overview.py` and `dashboard/views/anomaly_monitor.py` now directly render the real, deterministic `reasoning_summary` string produced by `adjudicator.adjudicate(...)`.
   - `render_hypothesis_attribution` is wired to display real `weather_event_likelihood`, `sensor_fault_likelihood`, `plausibility_score`, and `root_cause_category`.
   - Detection confidence, attribution confidence, and severity are distinctly presented as separate indicators.
2. **Traceable Evidence Presentation:**
   - Display real detector trigger codes (`TEMPERATURE_SPIKE_POSITIVE`, `FROZEN_TEMPERATURE`, `ROBUST_ZSCORE_EXCURSION_PRESSURE`, `DATA_TELEMETRY_INTEGRITY_FLAG`, etc.) using category-coded evidence chips.
   - Integrity event log in `anomaly_monitor.py` cleanly formats JSON details into readable key-value strings.

---

## 3. Evidence Now Exposed
- **Channel Derivative & Spike Signals:** Exposes positive/negative step jumps and unrealistic rate-of-change triggers.
- **Persistence & Flatlines:** Exposes consecutive identical readings count (`FROZEN_*`).
- **Statistical Z-Scores:** Exposes robust MAD rolling excursions.
- **Thermodynamics & Dewpoint:** Exposes thermodynamic consistency checks and plausibility scores.
- **Competing Hypotheses:** Exposes dual-clock weather likelihood vs sensor fault likelihood.
- **Telemetry Integrity:** Exposes late arrivals, missing slots, and communication gaps.

---

## 4. Sensor Health Changes (UNIT B)
1. **Deterministic Diagnostics Engine (`health/sensor_health/diagnostics.py`):**
   - Implemented `diagnose_station_health(station_id, window_size=20)` to compute multi-factor sensor health from real telemetry, in-memory station state buffers, and integrity logs.
2. **Transparent Health States:**
   - Evaluates transparent discrete states (`HEALTHY`, `DEGRADED`, `AT_RISK`, `CRITICAL`) for individual channels and overall station.
   - Generates supporting diagnostic evidence items for each channel explaining the exact justification for the assigned state.
3. **Database Persistence:**
   - Created `storage/repositories/health_repo.py` to persist channel health records into the `health_state` SQLite table on every health query/check.

---

## 5. Health Logic
- **`HEALTHY`**: Channel availability >= 90%, zero active anomaly triggers, nominal baseline variance. Maintenance: `NONE`.
- **`DEGRADED`**: Channel availability 70%–90% (intermittent dropouts), or isolated statistical excursions in window. Maintenance: `MONITOR`.
- **`AT_RISK`**: Channel availability 50%–70%, or persistent frozen flatline (4–7 steps), or recurring calibration drift. Maintenance: `INSPECTION_RECOMMENDED`.
- **`CRITICAL`**: Channel availability < 50% (severe data loss), persistent stuck flatline (8+ steps), or station marked INACTIVE. Maintenance: `URGENT_MAINTENANCE`.
- **Overall Station Health**: Evaluated as the worst-case of all channel states.

---

## 6. Persistence Changes
- Populates SQLite `health_state` table with `(station_id, channel, state, health_score, degradation_state, maintenance_state, evidence_window_start, evidence_window_end, model_integrity_state, updated_at)`.
- Updates records using `ON CONFLICT(station_id, channel) DO UPDATE SET ...` to maintain fresh longitudinal state.

---

## 7. API Changes
- Endpoint `GET /v1/stations/{station_id}/health`:
  - Dynamically evaluates sensor health via `diagnose_station_health`.
  - Persists health assessment to SQLite.
  - Returns structured diagnostics payload containing overall health state, summary, supporting evidence, per-channel degradation/maintenance states, model integrity metrics from live station buffers, and station configuration.

---

## 8. Dashboard Changes
- **`dashboard/views/overview.py`**: Wires real backend reasoning summary, hypothesis likelihoods, and evidence chips.
- **`dashboard/views/anomaly_monitor.py`**: Exposes reasoning and evidence chips in suspect expanders; formats integrity event details.
- **`dashboard/views/sensor_health.py`**:
  - Section 1: Overall Station Health Assessment banner with state badge and summary.
  - Section 2: Per-Channel Physical Diagnostics cards (Temperature, Pressure, Humidity) showing health state, availability %, degradation state, maintenance advice, and expandable evidence.
  - Section 3: Dual-Clock Model Integrity & Anti-Poisoning state.
  - Section 4: Ingestion contract, lateness budgets, and anomaly/event counters.

---

## 9. Tests Performed
1. **Unit A Explainability Suite (`tests/unit/test_explainability_unit_a.py`):** 8 tests covering normal, spike, frozen, drift, multivariate, genuine weather, suspect, and telemetry lateness scenarios.
2. **Unit B Sensor Health Suite (`tests/unit/test_sensor_health_unit_b.py`):** 8 tests covering healthy normal streams, missing channel data, delayed observations, frozen sensors, persistent drift, repeated anomalies, communication issues, and SQLite persistence.
3. **Invariants Suite (`tests/invariants/test_invariants.py`):** 5 tests verifying scope guards, raw immutability, ground truth isolation (INV-03), dashboard isolation, and claims discipline.
4. **Full System Regression Suite (`pytest`):** Full 145-test suite across all modules.

---

## 10. Test Results
- `tests/unit/test_explainability_unit_a.py`: **8 / 8 PASSED**
- `tests/unit/test_sensor_health_unit_b.py`: **8 / 8 PASSED**
- `tests/invariants/test_invariants.py`: **5 / 5 PASSED**

---

## 11. Full Regression Result
- **Total Tests Collected:** 145
- **Total Tests Passed:** 145
- **Total Tests Failed:** 0
- **Total Execution Time:** 34.36s
- **Status:** **100% GREEN (Zero Failures, Zero Regressions)**

---

## 12. Known Limitations
- Dashboard navigation, page titles, and components still contain legacy "TRUST-TWIN" branding and emoji icons, scheduled for complete professional cleanup and standardization in Repair 4.

---

## 13. Exact Starting Point for Repair 4
- **Topic:** Repair 4 — UI Quality, Branding Standardization & End-to-End Polish.
- **Files to address:**
  1. `dashboard/app.py`: Replace "TRUST-TWIN" branding with "SkyGuard AI", remove emojis from sidebar and navigation.
  2. `dashboard/components/metrics.py`: Clean SVG/CSS badge indicators without emojis.
  3. `dashboard/components/explainability.py`: Clean typography without emojis.
  4. `dashboard/views/overview.py`, `dashboard/views/anomaly_monitor.py`, `dashboard/views/historical.py`, `dashboard/views/sensor_health.py`, `dashboard/views/scenario_runner.py`: Remove all emojis, standardize meteorological terminology, and polish layout.
  5. `app/main.py`: Sanitize API error responses to prevent technical traceback leakage.
