# Repair 2 — Chart & Scenario Report

## 1. Previous State
Prior to Repair 2:
1. **Chart Fragility & Crashes:**
   - Categorical time string formatting (`%H:%M:%S`) on Plotly x-axes caused duplicate bin collisions on multi-readings in the same second and cross-midnight sorting issues.
   - Unhandled `None` and `NaN` values in channel telemetry and `anomaly_score` triggered Python runtime type errors (`>=` comparisons on `NoneType`).
   - Plotly attempted to interpolate gaps across null channel values without `connectgaps=False`.
   - Empty station histories produced blank or corrupted chart canvas elements.
2. **Scenario Feedback Mismatch:**
   - Replay endpoint `/v1/simulator/scenarios/{name}/run` only returned the first 5 decisions (`decisions[:5]`).
   - Because fault injection begins at index 8–12, operators only saw clean baseline points and believed injection replays failed.
   - The scenario runner UI had no structured stage breakdown (baseline, transition, peak anomaly, final state) or acceptance criteria validation.

---

## 2. Chart Problems Fixed (UNIT A)
1. **Native Datetime X-Axis:**
   - Switched from categorical string slices (`HH:MM:SS`) to native `pd.to_datetime` datetime indexing across all three chart generators in `dashboard/components/charts.py`.
   - Guaranteed strict chronological ordering via `.sort_values(by="dt", ascending=True)`.
   - Sub-second, multi-reading per second, and cross-midnight timestamps now render distinctly and monotonically.
2. **Null & NaN Safe Operations:**
   - Channel telemetry and anomaly scores are safely parsed via `pd.to_numeric(..., errors="coerce")`.
   - Hover formatters and anomaly marker filters check for `pd.notnull` and display `N/A` rather than crashing or inventing fake values.
   - Marker colorscale safely uses `scores.fillna(0.0)` with explicit `cmin=0.0, cmax=1.0` ranges.
3. **Gap Handling:**
   - Added `connectgaps=False` to all Scatter line traces, accurately preserving telemetry dropouts and sensor communication gaps.
4. **Empty State Graceful Degradation:**
   - Implemented `_create_empty_chart` helper that renders clean, styled dark-themed notices when dataframes are empty or `None`.
   - Wrapped chart generators in top-level `try...except` blocks that produce clean user-facing fallback notices instead of unhandled exceptions.

---

## 3. Scenario Problems Fixed (UNIT B)
1. **Rich Scenario Endpoint (`app/api/routes.py`):**
   - Updated `/v1/simulator/scenarios/{scenario_name}/run` to locate injection onset, calculate peak anomaly index, and extract four structured decision stages:
     - `baseline_decision`: Pre-injection nominal baseline.
     - `transition_decision`: Onset transition point.
     - `peak_decision`: Maximum anomaly score / peak anomalous impact decision with full adjudicator metrics.
     - `final_decision`: Tail end-state decision.
   - Evaluated formal scenario acceptance criteria, returning a structured `validation: {expected, actual, passed}` payload.
   - Returned the complete `sample_decisions` sequence for timeline inspection.
2. **Interactive Scenario Testbed UI (`dashboard/views/scenario_runner.py`):**
   - Added a Scenario Manifest & Acceptance Validation card displaying target channel(s), injection onset/offset window, expected behavior, actual result, and a **PASS / FAIL** badge.
   - Added a 4-column Progression Stage dashboard comparing Baseline, Transition, Peak Anomaly, and Final State.
   - Added a Deep-Dive drawer for the Peak Anomaly stage displaying real backend decision state, severity, detection & attribution confidence, root-cause attribution, and evidence codes.
   - Preserved full decision sequence table with clean error handling on manual injection.

---

## 4. Files Modified
1. `dashboard/components/charts.py`: Implemented native datetime axis, null/NaN safe parsing, gap preservation, and empty state rendering.
2. `dashboard/views/scenario_runner.py`: Implemented 4-stage scenario progression, acceptance criteria validation cards, and peak deep dive.
3. `app/api/routes.py`: Updated `run_scenario` endpoint to compute baseline, transition, peak, final stages, and validation results.

---

## 5. Files Created
1. `tests/unit/test_charts_unit_a.py`: 10-test unit suite validating time series, anomaly trajectory, raw vs processed charts under complete, null, duplicate, cross-midnight, unsorted, and empty datasets.
2. `tests/unit/test_scenario_testbed_unit_b.py`: 11-test suite validating scenario replay, stage breakdown, and acceptance validation across all 10 standard scenario types.
3. `24_REPAIR2_CHART_SCENARIO_REPORT.md`: This completion report.

---

## 6. Tests Run
1. **Unit A Chart Reliability Suite:**
   ```powershell
   python -m pytest tests/unit/test_charts_unit_a.py -v
   ```
2. **Unit B Scenario Testbed Suite:**
   ```powershell
   python -m pytest tests/unit/test_scenario_testbed_unit_b.py -v
   ```
3. **Full System Regression Suite:**
   ```powershell
   python -m pytest -v
   ```

---

## 7. Test Results
- `tests/unit/test_charts_unit_a.py`: **10 / 10 PASSED**
- `tests/unit/test_scenario_testbed_unit_b.py`: **11 / 11 PASSED**
- All 10 scenario types (NOMINAL, SPIKE, FLATLINE, DRIFT, BIAS, NOISE, COMMUNICATION_GAP, MULTIVARIATE_INCONSISTENCY, GENUINE_WEATHER, COMBINED) verified **PASS**.

---

## 8. Full Regression Result
- **Total Tests Collected:** 129
- **Total Tests Passed:** 129
- **Total Tests Failed:** 0
- **Total Execution Time:** 25.11s
- **Test Suite Status:** 100% GREEN (Phase 1, Phase 3, Phase 4, Invariants, Repair 1 Verification, and Repair 2 Unit Tests all passing).

---

## 9. Known Limitations
- Dashboard overview and anomaly monitor views still contain legacy "TRUST-TWIN" branding, emojis, and hardcoded overview reasoning templates, which are scheduled for clean-up in subsequent repair phases.

---

## 10. Exact Starting Point for Repair 3
- **Topic:** Repair 3 — Explainability & Sensor Health Diagnostics Alignment.
- **Files to address:**
  1. `dashboard/views/overview.py`: Display real backend `reasoning_summary` and `evidence_codes` from persisted data rather than hardcoded string templates.
  2. `dashboard/views/anomaly_monitor.py`: Parse JSON detail strings cleanly for integrity events.
  3. `app/api/routes.py` & `dashboard/views/sensor_health.py`: Wire dynamic baseline window parameters and structured sensor health assessments.
