# 25_REPAIR3A_EXPLAINABILITY_REPORT — SkyGuard AI

## 1. Previous Behavior
Prior to Repair 3 Unit A:
1. `dashboard/views/overview.py` ignored the real adjudicator `reasoning_summary` and instead generated a hardcoded template:
   `f"Station {selected_station_id} recorded observation ID {latest_obs.get('observation_id')}... "`.
2. `overview.py` generated synthetic evidence codes (`INTEGRITY_*`, `RC_*`) locally rather than displaying the real detector trigger codes from the backend.
3. `dashboard/views/anomaly_monitor.py` did not expose real reasoning or evidence chips in the suspect inspection callout cards, and rendered raw unparsed JSON string blobs in the integrity events log.

---

## 2. Root Cause
The adjudicator in `detection/decision/adjudicator.py` was generating detailed rule-based trace strings and evidence lists, and Repair 1 established database persistence and API propagation. However, the frontend views had not been reconnected to read `reasoning_summary` and `evidence_codes` from the API dictionary.

---

## 3. Files Changed
1. `dashboard/views/overview.py`:
   - Reconnected `reasoning_summary` and `evidence_codes` to real backend fields.
   - Connected `render_hypothesis_attribution` to display weather likelihood, sensor fault likelihood, plausibility, and root cause category.
   - Distinctly exposed detection confidence, attribution confidence, and severity.
2. `dashboard/views/anomaly_monitor.py`:
   - Added `render_evidence_chips` and `render_reasoning_box` to suspect/ambiguous review expanders.
   - Added `_format_event_details` helper to convert raw JSON detail blobs into clean human-readable key-value summaries.

---

## 4. Data Fields Used
- `decision_state`: Discrete decision state (`NORMAL`, `SUSPECT`, `ANOMALY`, `AMBIGUOUS`, `ABSTAIN`).
- `anomaly_score`: Normalized anomaly score `[0.0, 1.0]`.
- `severity`: Anomaly severity (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`).
- `detection_confidence`: Confidence in anomaly detection `[0.0, 1.0]`.
- `attribution_confidence`: Confidence in root cause attribution `[0.0, 1.0]`.
- `uncertainty_state`: Uncertainty mode (`LOW`, `MODERATE`, `HIGH`, `COLD_START`, `ABSTAIN`).
- `root_cause_category`: Behavioral fault classification.
- `weather_event_likelihood`: Physical atmospheric likelihood `[0.0, 1.0]`.
- `sensor_fault_likelihood`: Physical instrument fault likelihood `[0.0, 1.0]`.
- `plausibility_score`: Thermodynamic & reference profile plausibility `[0.0, 1.0]`.
- `evidence_codes`: Traceable trigger codes from statistical, temporal, and physical checks.
- `reasoning_summary`: Deterministic human-readable explanation from adjudicator.

---

## 5. UI Changes
- Overview tab now presents genuine rule-based reasoning from the backend without generic AI prose.
- Anomaly monitor tab displays evidence chips, root-cause classifications, and uncertainty modes for suspect events requiring human review.
- Low-level telemetry events display formatted key-value summaries instead of raw unparsed JSON strings.

---

## 6. Tests & Results
Created `tests/unit/test_explainability_unit_a.py` with 8 dedicated test cases:
- A1. Normal observation -> **PASSED**
- A2. Temperature spike -> **PASSED**
- A3. Frozen sensor -> **PASSED**
- A4. Drift -> **PASSED**
- A5. Multivariate inconsistency -> **PASSED**
- A6. Genuine-weather scenario -> **PASSED**
- A7. Ambiguous/suspect case -> **PASSED**
- A8. Telemetry/integrity issue -> **PASSED**

**Unit A Test Suite:** `8 passed in 5.62s` (100% pass rate).

---

## 7. Remaining Health Work (Unit B)
- Inspect `health/` and `health/sensor_health/` modules.
- Implement structured, evidence-based sensor health evaluation (`HEALTHY`, `DEGRADED`, `AT_RISK`, `CRITICAL`).
- Populate the `health_state` SQLite table with real derived health assessments.
- Update `/v1/stations/{id}/health` API to provide dynamic, explainable health diagnostics and configuration.
- Update `dashboard/views/sensor_health.py` to display explainable health states, channel availability, and supporting evidence.
