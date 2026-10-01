# Phase 3A Report — Core Anomaly Detection Engine

## Overview
- **Project**: SkyGuard AI / TRUST-TWIN (SIH26073)
- **Phase**: **PHASE 3A — CORE ANOMALY DETECTION ENGINE**
- **Objective**: Implement robust, deterministic, lightweight statistical and temporal anomaly scoring, rate-of-change triggers, persistence/frozen-sensor detection, and thermodynamic consistency validation operating strictly on allowed meteorological inputs (T, P, RH).

---

## Previous State (from 17_PHASE3_RECOVERY_REPORT.md)
- Phase 1 (Foundation) and Phase 2 (Data Substrate) were complete with 47 passing tests.
- Phase 3 was interrupted mid-way with only `features/builder.py` created before model quota exhaustion.
- Statistical anomaly detection triggers, rate-of-change thresholds, persistence checks, and normalized scoring were missing.

---

## Implemented Components in Phase 3A

### 1. Statistical Anomaly Detector (`detection/triggers/statistical.py`)
- **Normalized Composite Anomaly Score**: Scaled deterministically to $[0.0, 1.0]$ with per-channel breakdown for Temperature, Pressure, and Relative Humidity.
- **Rate-of-Change & Spike Triggers**:
  - Per-minute derivative checking against meteorological thresholds ($0.5^\circ\text{C/min}$ for $T$, $0.4\text{ hPa/min}$ for $P$, $2.5\%/\text{min}$ for $RH$).
  - Hard single-step jump thresholds ($6.0^\circ\text{C}$ for $T$, $5.0\text{ hPa}$ for $P$, $25.0\%$ for $RH$) generating directional trigger codes (`TEMP_SPIKE_POSITIVE`, `TEMP_SPIKE_NEGATIVE`, `PRESSURE_SPIKE_NEGATIVE`, `HUMIDITY_SPIKE_POSITIVE`, etc.).
- **Persistence / Frozen-Value Detection**:
  - Sliding identical-value detector identifying stuck sensors across consecutive observations ($\ge 4$ readings with $|\Delta| \le 10^{-4}$).
- **Robust Rolling MAD Z-Score**:
  - Computes robust sample median and Median Absolute Deviation ($\text{MAD} \times 1.4826$) over sliding historical windows to detect subtle statistical excursions without being distorted by outlier contamination.
- **Thermodynamic Consistency Validation**:
  - Derives dewpoint temperature ($T_d$) via Magnus-Tetens formula and verifies that dewpoint does not physically exceed temperature ($T - T_d \ge -0.5^\circ\text{C}$).
- **Latency Benchmarking**:
  - Measured inference latency of **0.148 ms average** (P95 = 0.239 ms), far outperforming the 5.0 ms real-time streaming requirement.

### 2. Feature Builder Infrastructure (`features/builder.py`)
- Standardized `CleanBuffer` ring buffer holding admitted historical readings.
- 22-dimensional feature vector layout (`f1` version) with 1st/2nd derivatives, 1h/6h rolling z-scores, cyclical hour/day-of-year encodings, and derived thermodynamic quantities.

---

## Files Created
- `detection/triggers/statistical.py` (7,390 bytes) — StatisticalAnomalyDetector implementation with robust MAD, rate triggers, frozen detector, and composite scoring.
- `tests/unit/test_detection_triggers.py` (5,830 bytes) — Comprehensive unit test suite covering nominal readings, positive/negative spikes, drops, frozen runs, unrealistic rates, determinism, and latency benchmarks.
- `tests/unit/test_feature_builder.py` (2,160 bytes) — Unit tests for `CleanBuffer` and 22-dimensional feature vector construction.
- `17_PHASE3A_REPORT.md` — This checkpoint report.

---

## Files Modified
- `detection/triggers/__init__.py` — Exported `StatisticalAnomalyDetector`, `statistical_detector`, and `AnomalyResult`.

---

## Tests and Results
- **Test Command**: `python -m pytest -v`
- **Total Tests**: **60 passed in 3.14s** (100% pass rate, 0 failures).
- **Phase 3A Specific Tests (13 tests)**:
  - `tests/unit/test_feature_builder.py::test_clean_buffer_push_and_limit` — PASSED
  - `tests/unit/test_feature_builder.py::test_clean_buffer_with_nones` — PASSED
  - `tests/unit/test_feature_builder.py::test_build_feature_vector_dimensions_and_types` — PASSED
  - `tests/unit/test_detection_triggers.py::test_normal_reading` — PASSED (score < 0.3, 0 triggers)
  - `tests/unit/test_detection_triggers.py::test_sudden_temperature_spike` — PASSED (`TEMPERATURE_SPIKE_POSITIVE`)
  - `tests/unit/test_detection_triggers.py::test_sudden_temperature_drop` — PASSED (`TEMPERATURE_SPIKE_NEGATIVE`)
  - `tests/unit/test_detection_triggers.py::test_pressure_abnormality` — PASSED (`PRESSURE_SPIKE_NEGATIVE`)
  - `tests/unit/test_detection_triggers.py::test_humidity_abnormality` — PASSED (`RELATIVE_HUMIDITY_SPIKE_POSITIVE`)
  - `tests/unit/test_detection_triggers.py::test_frozen_repeated_values` — PASSED (`FROZEN_TEMPERATURE`, `FROZEN_PRESSURE`, `FROZEN_RELATIVE_HUMIDITY`)
  - `tests/unit/test_detection_triggers.py::test_unrealistic_change_rate` — PASSED (`TEMPERATURE_UNREALISTIC_RATE`)
  - `tests/unit/test_detection_triggers.py::test_thermodynamic_inconsistency_trigger` — PASSED
  - `tests/unit/test_detection_triggers.py::test_inference_latency_benchmark` — PASSED (Avg = 0.148 ms, P95 = 0.239 ms)
  - `tests/unit/test_detection_triggers.py::test_determinism` — PASSED (Identical inputs yield exact same score & flags)

---

## Failures and Regressions
- **Zero failures**.
- **Zero regressions** across Phase 1, Phase 2, and invariant test suites.

---

## Remaining Phase 3 Work
1. **Phase 3B — Quarantine-Protected Adaptive Tracker & Reference Profiles**:
   - Versioned baseline profile (`REFERENCE_v`) and online tracker (`TRACKER_t`) that updates strictly on admitted observations.
2. **Phase 3C — Episode Manager & Sequential Adjudication**:
   - Anomaly episode lifecycle (open, multi-sample evidence accumulation, closure) and adjudication states (`DECIDE`, `WAIT`, `ABSTAIN`).
3. **Phase 3D — Weather-vs-Sensor Attribution & Uncertainty Engine**:
   - Multi-variable physical co-variation analysis (distinguishing genuine convective storm drops from isolated sensor failures) and conformal uncertainty quantification.
4. **Phase 3E — Sensor Health, Degradation & Maintenance**:
   - Longitudinal sensor health index ($0-100\%$), degradation drift tracking, and maintenance recommendation generation.

---

## Exact Next Safe Task
**Task**: Phase 3B — Implement Quarantine-Protected Adaptive Tracker (`detection/tracker/tracker.py`) and Reference Profile Baseline (`detection/reference/baseline.py`) with strict admission gating so quarantined observations cannot poison tracking state.

---

## Risks / Constraints
- Do not bypass `CleanBuffer` or pass un-admitted observations into online tracking.
- Retain strict $T, P, RH$ meteorological input scope.
- Derived anomaly scores remain alongside raw observations without mutating raw tables.
