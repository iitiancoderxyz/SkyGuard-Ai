# User-Friendly Explainability & UI Report

**Project:** SkyGuard AI — TRUST-TWIN  
**Problem Statement:** SIH26073 — AI/ML-Based Intelligent Anomaly Detection for Automatic Weather Stations (AWS)  
**Role:** Final User Experience + Explainability Cleanup Engineer  
**Status:** **CLEANUP COMPLETE & VERIFIED**  
**Regression Status:** **145/145 passed in 38.16s (100% Pass Rate)**

---

## 1. Reasoning Improvements

- **Human-Readable Evidence Translation:** Built comprehensive operator dictionaries that automatically translate raw backend trigger codes into natural meteorological descriptions (e.g. `TEMPERATURE_SPIKE_POSITIVE` → *"Rapid temperature spike (+)"*, `ROBUST_ZSCORE_EXCURSION_TEMPERATURE` → *"Temperature deviates from recent expected pattern"*, `FROZEN_TEMPERATURE` → *"Temperature reading remained unchanged (flatline)"*, `THERMODYNAMIC_INCONSISTENCY` → *"Inconsistent temperature, humidity, and dewpoint relationship"*, `WEATHER_EVENT_EVIDENCE` → *"Multi-channel trend consistent with genuine weather front"*).
- **Concise Reasonings by Condition:**
  - **Normal Observations:** *"The latest observation is consistent with the station's recent behavior. No significant anomaly detected."*
  - **Suspect / Ambiguous Observations:** *"The observation is unusual, but the available evidence does not clearly separate a sensor issue from a genuine atmospheric change."*
  - **Anomalous Observations:** Displays the human-readable likely cause and supporting multi-channel evidence tags without generic AI filler.
- **Weather vs Sensor Explanation:** Explains what the likelihood percentages mean in context (e.g. *"Measurements follow a physical pattern consistent with genuine atmospheric activity"* vs *"Abrupt single-channel change without expected atmospheric correlation"*).

---

## 2. Technical Labels Replaced

| Internal / Technical Label | User-Friendly Operator Label | Context / Location |
|---|---|---|
| `Active AWS Stations` | `Stations Monitored` | Sidebar connectivity block |
| `Engine Reasoning` | `Why This Was Flagged` | Explainability component / Overview tab |
| `Active Evidence Triggers` / `Evidence Codes` | `Evidence` | Anomaly assessment panel |
| `Root-Cause Hypothesis Attribution` | `Likely Cause & Attribution` | Attribution panel & cards |
| `Attribution Confidence` | `Cause Confidence` | Metric score bars across all views |
| `Baseline Admission` / `Admission State` | `Data Handling Status` | Decision & admission badge block |
| `Reference Profile` | `Long-Term Baseline` | Sensor health & architecture summary |
| `Adaptive Tracker` | `Recent Baseline` | Sensor health & architecture summary |
| `Anti-Poisoning Barrier` | `Baseline Protection` | Sensor health & architecture summary |
| `SENSOR_SPIKE` | `Sensor Hardware Spike` | Root cause indicator |
| `SENSOR_STUCK_FROZEN` | `Sensor Flatline / Frozen` | Root cause indicator |
| `GRADUAL_DRIFT` | `Gradual Sensor Calibration Drift` | Root cause indicator |
| `MULTIVARIATE_INCONSISTENCY` | `Cross-Sensor Physical Inconsistency` | Root cause indicator |
| `DATA_TELEMETRY` | `Data Communication / Packet Loss` | Root cause indicator |
| `WEATHER_EVENT` | `Possible Genuine Weather Event` | Root cause indicator |

---

## 3. Station Metric Naming

- **Identified Meaning:** Evaluated `api.get_health().get("active_stations")`, which counts total registered stations in the SQLite database.
- **Operator Label:** Standardized to **`Stations Monitored: {count}`** in the sidebar. This accurately represents the stations tracked by the system without falsely implying physical remote hardware state.

---

## 4. Error Cleanup

- **Zero Raw Exceptions:** Eliminated raw Python tracebacks, internal dictionary keys, and exception names from user-facing surfaces.
- **Friendly Operational Error Messages:**
  - Connection failures: *"Unable to connect to the monitoring service. Please ensure the API server is running on port 8000."*
  - Diagnostics loading: *"Unable to load sensor health diagnostics. Please try again."*
  - Invalid input: *"Some observation fields are invalid. Please check the entered values."*
  - Scenario execution issues: *"Scenario execution failed. Please verify the station ID and try again."*

---

## 5. User-Facing Code Removed

- Verified zero user-facing `AWS_DBG`, `Traceback`, `KeyError`, `ValueError`, or unparsed JSON dictionary dumps.
- Telemetry event details in the Anomaly Monitor are parsed and formatted as clean key-value text (*"Channel: Temperature, Delta: +25.0°C"*).

---

## 6. Pages Updated

1. **Station Overview (`dashboard/views/overview.py`):** User-friendly labels (`Decision State & Confidence`, `Cause Confidence`, `Likely Cause & Attribution`, `Evidence`), non-alarming normal condition summaries, raw telemetry subtitles.
2. **Anomaly Monitor (`dashboard/views/anomaly_monitor.py`):** Header updated to `🚨 Anomaly Assessment & Operator Review Queue`, metrics labeled (`Cases Requiring Review`, `Critical Alerts`), suspect expanders display humanized causes and evidence chips.
3. **Historical Analysis (`dashboard/views/historical.py`):** Time-series plots labeled clearly with humanized channel names and explanations of raw immutability.
4. **Sensor Health (`dashboard/views/sensor_health.py`):** Channel degradation states and maintenance recommendations translated to plain language (`Nominal`, `Routine monitoring recommended`, `Field inspection recommended`). Dual-clock baseline monitoring explained clearly.
5. **Scenario Lab (`dashboard/views/scenario_runner.py`):** Replay stages titled clearly (`Pre-Injection Baseline`, `Fault Onset Transition`, `Peak Anomaly Stage`, `Post-Injection Recovery`), clean PASS/FAIL validation card.

---

## 7. Data Integrity Preserved

- **Zero Backend Calculations Modified:** All values (anomaly scores, detection confidences, likelihoods, plausibility scores, health states, degradation states) are sourced directly from existing backend APIs and repositories.
- **Zero Mocking:** No hardcoded placeholders or fabricated values introduced.

---

## 8. Browser Validation

- **Backend Service:** Active on `http://127.0.0.1:8000` (FastAPI / SQLite WAL).
- **Streamlit Frontend:** Active on `http://localhost:8501`.
- **Operator Readability Confirmed:**
  - Station status and telemetry clear at a glance.
  - Anomaly reasons and evidence are easy to understand without software engineering background.
  - Sensor health states clearly distinguish between data availability (% received) and signal quality (flatlines/drift).

---

## 9. Tests

- **Command:** `python -m pytest -v`
- **Result:** **145 passed in 38.16s**

---

## 10. Regression Result

- **Total Tests Collected:** 145
- **Passed:** 145 (100%)
- **Failed:** 0
- **Regressions:** 0

---

## 11. Remaining Issues

**None.** The application maintains its original dark operational theme and layout while presenting clear, professional, operator-accessible explainability.
