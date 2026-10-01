# SkyGuard AI

**AI/ML-Based Intelligent Anomaly Detection for Automatic Weather Stations**

> **SIH 2026 | Problem Statement: SIH26073**

SkyGuard AI is a real-time AI/ML-powered monitoring platform that ingests telemetry from Automatic Weather Stations (AWS), detects anomalous observations caused by sensor hardware faults or data communication failures, and intelligently distinguishes these sensor faults from genuine meteorological events. Built for operational meteorologists, field engineers, and national weather service operators, the platform provides traceable, evidence-based anomaly explanations, longitudinal sensor health diagnostics, and multi-scenario validation — all accessible through a single web dashboard and REST API. It fills a specific need: knowing not just *that* a reading is unusual, but *why*, *how confident* the system is, and *whether the next action should be instrument maintenance or a weather advisory*.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Solution Overview](#2-solution-overview)
3. [Value Proposition](#3-value-proposition)
4. [Key Features](#4-key-features)
5. [Inputs](#5-what-inputs-does-the-system-use)
6. [System Workflow](#6-system-workflow)
7. [System Architecture](#7-system-architecture)
8. [Core AI / ML Methodology](#8-core-ai--ml-methodology)
9. [Explainability](#9-explainability)
10. [Sensor Health](#10-sensor-health)
11. [Data Integrity](#11-data-integrity)
12. [Dashboard](#12-dashboard)
13. [Scenario Lab](#13-scenario-lab)
14. [Validation & Testing](#14-validation--testing)
15. [Performance](#15-performance)
16. [Deployment](#16-deployment)
17. [Tech Stack](#17-tech-stack)
18. [API Overview](#18-api-overview)
19. [Project Structure](#19-project-structure)
20. [Demo Workflow](#20-demo-workflow)
21. [PPT-Ready Content](#21-ppt-ready-content)
22. [Innovation / Differentiation](#22-innovation--differentiation)
23. [Operational Impact](#23-operational-impact)
24. [Limitations](#24-limitations)
25. [Future Scope](#25-future-scope)
26. [Requirement Coverage](#26-requirement-coverage)
27. [Technical Q&A Preparation](#27-technical-qa-preparation)
28. [One-Page Project Fact Sheet](#28-one-page-project-fact-sheet)
29. [Run Instructions](#29-run-instructions)

---

## 1. Problem Statement

### The Problem

Automatic Weather Stations continuously generate meteorological telemetry — temperature, barometric pressure, relative humidity, and derived quantities — at fixed sampling cadences (typically every 60 seconds). A national network of AWS stations can produce millions of observations per day.

Sensor hardware degrades. Electronic components drift. Communication links drop packets. When a faulty reading enters the meteorological record unchecked, it can corrupt climatological baselines, trigger erroneous weather warnings, or mislead downstream forecasting models.

Traditional quality-control approaches apply fixed threshold rules: *"if temperature > X, flag it."* These rules can detect obvious outliers, but they suffer from well-known limitations:
- They cannot distinguish a legitimate sudden cold front from a stuck temperature sensor.
- They do not track *gradual* degradation — a sensor drifting slowly over weeks will pass threshold checks until it is severely out of range.
- They provide no longitudinal health memory for individual sensor channels.
- They offer no traceable explanation that an operator can act upon.

False positives burden operators with alerts that require manual investigation. False negatives allow faulty data to silently enter the record.

### The Project's Interpretation of the Problem

SIH26073 asks for an **AI/ML-based intelligent anomaly detection system** specifically designed for AWS. This prototype's interpretation is:

> *Build a system that can detect anomalies in real time, explain each decision in plain language, assess whether the anomaly is more likely a hardware fault or a genuine weather event, track sensor health over time, and allow operators to validate and understand system behaviour through structured demonstrations.*

---

## 2. Solution Overview

SkyGuard AI implements a multi-layer intelligent detection pipeline where every AWS observation is processed through a sequence of deterministic and statistical steps before a final decision is persisted and displayed.

**End-to-end flow:**

```
AWS Observation (Temperature, Pressure, Relative Humidity)
        │
        ▼
Integrity Gate
 • Validates payload schema and physical bounds
 • Detects duplicate timestamps, out-of-order packets
 • Flags communication gaps and delayed arrivals
        │
        ▼
Feature Processing
 • Rolling ring-buffer of recent observations
 • Rate-of-change computation
 • Thermodynamic derivations (dewpoint via Magnus-Tetens formula)
        │
        ▼
Anomaly Detection (Multi-Factor)
 • Step jump / spike detection
 • Frozen / flatline detection
 • Unrealistic rate-of-change detection
 • Robust statistical baseline comparison (MAD z-score)
 • Thermodynamic multivariate consistency
        │
        ▼
Dual-Clock Baseline Comparison
 • Long-term Reference Profile (96-step window)
 • Short-term Adaptive Tracker (12-step window)
        │
        ▼
Decision Adjudication
 • Evidence accumulation from all detectors
 • Weather-event consistency scoring
 • Sensor-fault likelihood scoring
 • Competing hypothesis resolution
        │
        ▼
Decision Outputs
 • Decision State (NORMAL / SUSPECT / AMBIGUOUS / ANOMALY)
 • Anomaly Score [0.0 – 1.0]
 • Detection Confidence + Attribution Confidence
 • Severity (LOW / MODERATE / HIGH / CRITICAL)
 • Root Cause Category
 • Reasoning Summary + Evidence Codes
        │
        ▼
Sensor Health Evaluation
 • Channel availability, degradation state, maintenance priority
        │
        ▼
Persistence → API → Streamlit Dashboard
```

What makes this different from a simple threshold alarm: the system combines **temporal context** (how fast is this changing?), **spatial context** (do all channels agree thermodynamically?), **historical context** (how does this compare to the station's own established baseline?), and **competing-hypothesis reasoning** (weather event or sensor fault?) — all in a single deterministic, explainable pipeline.

---

## 3. Value Proposition

| Operational Need | SkyGuard AI Capability |
|---|---|
| Know *immediately* when a sensor behaves abnormally | Sub-millisecond real-time detection per observation |
| Understand *why* an alert was raised | Traceable evidence codes + plain-English reasoning summary |
| Avoid false alarms during genuine weather events | Weather-event vs. sensor-fault likelihood assessment |
| Track long-term sensor degradation | Longitudinal sensor health diagnostics per channel |
| Review the history of anomaly decisions | Historical analytics with anomaly score trajectory |
| Reproduce and validate system behaviour | 10-scenario Scenario Lab with formal acceptance criteria |
| Preserve trustworthy raw measurements | Immutable raw observation store (SQLite trigger-enforced) |
| Integrate with existing infrastructure | RESTful FastAPI with OpenAPI documentation |
| Run on modest hardware | < 45 MB RAM, < 0.5 ms end-to-end per observation |

---

## 4. Key Features

| Feature | What It Does | Why It Matters |
|---|---|---|
| **Real-time anomaly detection** | Processes each observation through the full pipeline on arrival | Immediate detection without batch delay |
| **Step jump / spike detection** | Detects isolated positive/negative physical excursions exceeding calibrated delta thresholds | Catches sudden hardware failures and transient interference |
| **Frozen / flatline detection** | Monitors for repeated identical readings across consecutive sampling windows | Catches stuck sensors that threshold rules miss |
| **Rate-of-change limiters** | Flags temporal slopes that violate physical atmospheric limits | Detects unusually rapid but sub-threshold changes |
| **Robust MAD z-score baseline** | Uses Median Absolute Deviation for outlier-resistant station baseline | More robust than mean/std-dev against sensor drift and seasonal change |
| **Thermodynamic consistency** | Cross-checks temperature, pressure, humidity, and derived dewpoint against Magnus-Tetens physical laws | Detects multivariate conflicts invisible to single-channel rules |
| **Dual-clock baseline** | Maintains a 96-step long-term and 12-step short-term baseline in parallel | Long-term detects slow drift; short-term detects rapid shifts |
| **Baseline anti-poisoning** | Quarantines anomalous observations from updating baseline profiles | Prevents a persistent fault from normalising itself in the model |
| **Anomaly score** | Normalized composite score [0.0 – 1.0] reflecting deviation magnitude | Single interpretable severity indicator |
| **Detection confidence** | Confidence that the anomaly signal is real, not statistical noise | Distinguishes high-certainty from marginal detections |
| **Attribution confidence** | Confidence in the assigned root-cause category | Helps operator decide how strongly to trust the cause label |
| **Severity classification** | Classifies each detection as LOW / MODERATE / HIGH / CRITICAL | Enables prioritised operator triage |
| **Root-cause attribution** | Identifies SENSOR_SPIKE, SENSOR_STUCK_FROZEN, GRADUAL_DRIFT, MULTIVARIATE_INCONSISTENCY, DATA_TELEMETRY, WEATHER_EVENT, or COMPETING_EVIDENCE | Guides maintenance vs. weather advisory action |
| **Explainability** | Human-readable reasoning summary and category-coded evidence bullets | Operators understand and trust decisions |
| **Weather-event likelihood** | Measures how consistent the observation is with genuine atmospheric patterns | Prevents unnecessary maintenance callouts during real weather |
| **Sensor-fault likelihood** | Measures how consistent the observation is with known hardware fault patterns | Drives timely maintenance decisions |
| **Sensor health diagnostics** | Per-channel health state (HEALTHY / DEGRADED / AT_RISK / CRITICAL), availability %, degradation state, and maintenance priority | Longitudinal early warning before complete sensor failure |
| **Anomaly monitor** | Live alert timeline with severity filter and suspect review queue | Operator triage interface |
| **Historical analytics** | Multi-channel time-series and anomaly score trajectory charts | Trend visibility over time |
| **Scenario Lab** | 10 pre-configured meteorological fault and weather scenarios with formal validation | Reproducible system validation and demonstration |
| **Raw observation preservation** | Raw measurements stored immutably alongside processed values | Audit trail integrity; never silently overwrites field data |
| **REST API** | Full FastAPI with OpenAPI docs for integration | Easy integration with existing systems |

---

## 5. What Inputs Does the System Use?

### Primary Meteorological Variables (MVP)

| Variable | Symbol | Unit | Role |
|---|---|---|---|
| Temperature | T | °C | Primary detection channel; spike, drift, flatline, rate-of-change |
| Barometric Pressure | P | hPa | Primary detection channel; bias, spike, multivariate consistency |
| Relative Humidity | RH | % | Primary detection channel; drift, spike, thermodynamic checks |

The MVP is **intentionally focused on this thermodynamic trio**, which is the most universally deployed set of sensors across AWS networks and provides the richest multivariate physical relationships (dewpoint, vapour pressure, thermodynamic plausibility).

### Allowed Metadata

| Field | Description |
|---|---|
| `station_id` | Unique AWS station identifier |
| `timestamp` | ISO 8601 UTC observation timestamp |
| `latitude` | Geographic coordinate (optional) |
| `longitude` | Geographic coordinate (optional) |
| `elevation` | Station elevation in metres (optional) |
| `source_type` | Observation source (`LIVE`, `BATCH`, `SIMULATOR`) |

### Additional Channels (Future Work)

Wind speed, wind direction, solar radiation, and precipitation gauge channels are **FUTURE WORK**. The detector and adjudicator architecture is modular and designed to accommodate additional channels through the same trigger interface — but these are not currently implemented.

---

## 6. System Workflow

```
┌────────────────────────────────────────────────────────────────┐
│  AWS TELEMETRY INPUT                                           │
│  POST /v1/observations                                         │
│  { station_id, timestamp, temperature, pressure, humidity }   │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│  INTEGRITY GATE  (ingestion/integrity/gate.py)                 │
│  • Physical range validation (T: -90°C…+60°C, P: 800–1100hPa) │
│  • Duplicate timestamp detection                               │
│  • Communication gap detection (missing slots)                 │
│  • Lateness flagging (arrived past expected cadence)           │
│  → Assigns: ACCEPT / REJECT / QUARANTINE / ACCEPT_LATE         │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│  FEATURE PROCESSING  (features/builder.py)                     │
│  • Rolling ring-buffer: last N observations                    │
│  • Rate-of-change per channel (features/temporal/rates.py)     │
│  • Thermodynamics: dewpoint via Magnus-Tetens formula          │
│    (features/multivariate/thermodynamics.py)                   │
│  • Vapour pressure and dewpoint depression                     │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│  ANOMALY DETECTION  (detection/triggers/statistical.py)        │
│  • Spike / step jump triggers (positive + negative)            │
│  • Frozen / flatline triggers (consecutive identical values)   │
│  • Rate-of-change limiters (unrealistic temporal slopes)       │
│  • Robust MAD z-score excursion vs. Reference Profile          │
│  • Thermodynamic inconsistency (dewpoint > temperature check)  │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│  DUAL-CLOCK BASELINE  (detection/reference/ & tracker/)        │
│  • Reference Profile: 96-step long-term robust MAD baseline    │
│  • Adaptive Tracker: 12-step short-term rapid response         │
│  • Anti-poisoning: only ADMIT observations update baselines    │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│  DECISION ADJUDICATION  (detection/decision/adjudicator.py)    │
│  • Aggregates all trigger evidence                             │
│  • Computes weather_event_likelihood from multivariate pattern │
│  • Computes sensor_fault_likelihood from residual deviation    │
│  • Resolves competing hypotheses (WEATHER vs FAULT)            │
│  • Generates reasoning_summary + evidence_codes                │
│  • Outputs Decision State / Score / Confidence / Severity      │
│    / Root Cause / Attribution                                  │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│  SENSOR HEALTH EVALUATION  (health/sensor_health/diagnostics)  │
│  • Channel availability over rolling window                    │
│  • Degradation state, maintenance priority                     │
│  • Persisted to SQLite health_state table                      │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│  PERSISTENCE  (storage/ — SQLite WAL)                          │
│  raw_observations → processed_observations → decisions         │
│  → health_state → integrity_events → ground_truth_labels       │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                          REST API │ SSE Stream
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│  OPERATOR DASHBOARD  (dashboard/ — Streamlit :8501)            │
│  Station Overview · Anomaly Monitor · Historical Analysis      │
│  Sensor Health · Scenario Lab                                  │
└────────────────────────────────────────────────────────────────┘
```

---

## 7. System Architecture

```
   OPERATOR / USER VIEW                    DEVELOPER / API CONSUMER
           │                                           │
           ▼                                           ▼
┌──────────────────────┐                   ┌────────────────────────┐
│  Streamlit Dashboard │                   │  FastAPI REST / Docs   │
│  http://localhost:8501│                  │  http://127.0.0.1:8000 │
│  dashboard/app.py    │                   │  /docs  /redoc         │
└──────────┬───────────┘                   └───────────┬────────────┘
           │                                           │
           │  HTTP REST  (dashboard/api_client.py)     │
           └───────────────────┬───────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Application Service                   │
│                       app/main.py  :8000                        │
│                                                                 │
│  /v1/observations  /v1/stations  /v1/decisions                  │
│  /v1/simulator/scenarios/{name}/run  /v1/stream (SSE)           │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Core Intelligence Engine                     │
│                      app/runtime/engine.py                      │
│                                                                 │
│  Integrity Gate ──▶ Feature Ring-Buffer ──▶ Statistical Triggers│
│                                                   │             │
│                                                   ▼             │
│  Decision Adjudicator ◀── Reference Profile + Adaptive Tracker  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│               SQLite WAL Database  (data/trusttwin.db)          │
│                                                                 │
│  raw_observations (immutable) ──▶ processed_observations        │
│  decisions ──▶ health_state ──▶ integrity_events                │
└─────────────────────────────────────────────────────────────────┘
```

### Component Roles

| Component | File / Module | Role |
|---|---|---|
| FastAPI service | `app/main.py` | HTTP server, routing, SSE broadcast |
| Core engine | `app/runtime/engine.py` | Orchestrates the full detection pipeline |
| Integrity gate | `ingestion/integrity/gate.py` | Deterministic input validation |
| Feature builder | `features/builder.py` | Ring-buffer, rate-of-change, thermodynamics |
| Statistical detector | `detection/triggers/statistical.py` | Spike, flatline, rate, MAD z-score triggers |
| Reference profile | `detection/reference/baseline.py` | Long-term robust MAD baseline (96 steps) |
| Adaptive tracker | `detection/tracker/tracker.py` | Short-term rapid baseline (12 steps) |
| Decision adjudicator | `detection/decision/adjudicator.py` | Evidence accumulation, hypothesis resolution |
| Sensor health | `health/sensor_health/diagnostics.py` | Channel availability, degradation, maintenance |
| Storage layer | `storage/` | SQLite WAL via `connection.py`, repositories |
| Scenario suite | `simulator/scenarios/suite.py` | 10 physics-calibrated scenario generators |
| Stream replayer | `simulator/replay/replayer.py` | Executes observation sequences through engine |
| Dashboard | `dashboard/app.py` + `views/` | Streamlit operator interface |

---

## 8. Core AI / ML Methodology

### 8.1 Statistical Detection — Robust MAD Z-Score

The system uses **Median Absolute Deviation (MAD)** rather than the mean and standard deviation for statistical baseline comparison. This choice is deliberate:

- Standard deviation is highly sensitive to a single outlier. If a sensor spikes once, the standard deviation inflates, making the next normal reading appear borderline and reducing sensitivity.
- MAD is resistant to outliers because it measures variability using the *median* of deviations from the *median* — a single extreme value cannot substantially distort it.

The robust z-score for a new observation value *x* is:

```
z_robust = (x - median(window)) / (1.4826 × MAD(window))
```

The constant 1.4826 makes MAD consistent with the standard deviation for normally distributed data. Values exceeding a calibrated threshold trigger `ROBUST_ZSCORE_EXCURSION_*` evidence codes.

### 8.2 Temporal Detection

Four temporal detectors run independently on each observation:

| Detector | Mechanism | Evidence Code |
|---|---|---|
| Step spike (positive) | Instantaneous delta > physical threshold | `TEMPERATURE_SPIKE_POSITIVE`, `PRESSURE_SPIKE_POSITIVE`, etc. |
| Step spike (negative) | Instantaneous delta < –physical threshold | `TEMPERATURE_SPIKE_NEGATIVE`, etc. |
| Unrealistic rate of change | Rolling slope exceeds physical limit (e.g. > 0.5°C/min) | `TEMPERATURE_UNREALISTIC_RATE`, etc. |
| Frozen / flatline sensor | Consecutive identical values (within float tolerance) across consecutive steps | `FROZEN_TEMPERATURE`, `FROZEN_PRESSURE`, `FROZEN_RELATIVE_HUMIDITY` |

The frozen detector is especially important: a stuck sensor that emits a constant physically plausible value will pass every threshold rule and every statistical check against a rolling mean — but consecutive identical floating-point values over many minutes are physically impossible in real atmospheric data.

### 8.3 Multivariate Consistency

Temperature, pressure, and relative humidity are thermodynamically linked. The system verifies:

1. **Magnus-Tetens dewpoint:** Derives dewpoint temperature T_d from T and RH using the Magnus-Tetens formula. If T_d > T (dewpoint above air temperature), the observation is physically impossible — flagged as `THERMODYNAMIC_INCONSISTENCY`.
2. **Cross-channel pattern scoring:** When all three channels shift simultaneously in a physically coherent direction (e.g. temperature drops, humidity rises, pressure rises — consistent with a cold front), the system increases `weather_event_likelihood`. This multivariate coherence check is what distinguishes a real cold front from a pressure-sensor spike.

### 8.4 Dual-Clock Baseline System

Two baselines run in parallel for every station:

| Baseline | Window | Purpose |
|---|---|---|
| **Reference Profile** | 96 steps | Long-term robust baseline representing typical diurnal station behaviour over many hours. Detects gradual drift that short-term trackers miss. |
| **Adaptive Tracker** | 12 steps | Short-term rapid-response baseline tracking recent behaviour. Detects sudden level shifts that would appear normal relative to a long-term average. |

Using both simultaneously is key: a slow week-long drift will not change the 12-step tracker significantly, but will deviate from the 96-step profile. A sudden level shift will look normal to the 96-step profile (which averages over a long history) but will stand out against the 12-step tracker.

### 8.5 Baseline Anti-Poisoning

Observations that are flagged as anomalous or quarantined receive `AdmissionState = QUARANTINE` or `REJECT`. **Only observations with `AdmissionState = ADMIT` update the baseline profiles.** This prevents a stuck sensor or sustained hardware fault from gradually "training away" the anomaly — the system never normalises a fault by incorporating it into its own baseline.

Verified by unit test `test_b8_health_state_persistence_and_sqlite_retrieval` and invariant test `test_inv04_quarantine_does_not_update_clean_buffer`.

### 8.6 Anomaly Score

The anomaly score is a normalized composite value in **[0.0, 1.0]** computed by the adjudicator from the number and strength of triggered detectors. It is a relative severity indicator within the system — it is **not** a calibrated probability in the statistical sense. A score of 1.0 indicates the maximum detectable deviation; a score of 0.0 indicates no anomaly signals were triggered.

### 8.7 Confidence Scores

Two distinct confidence values are produced:

| Confidence | What It Measures |
|---|---|
| **Detection Confidence** | Certainty that the anomaly signal is real and not statistical noise or a cold-start artefact |
| **Attribution Confidence** | Certainty that the assigned root-cause category is correct |

These are different. A system can be highly confident that *something* anomalous occurred (high detection confidence) while being uncertain whether the cause is sensor drift or a genuine weather event (lower attribution confidence).

### 8.8 Severity Classification

| Severity | Typical Condition |
|---|---|
| `LOW` | Score < 0.35; minor excursions; routine monitoring |
| `MODERATE` | Score 0.35–0.65; noticeable deviation; inspect if persistent |
| `HIGH` | Score 0.65–0.90; significant anomaly; likely sensor issue |
| `CRITICAL` | Score > 0.90 or flatline detected; urgent maintenance |

### 8.9 Root Cause Categories

| Root Cause | Meaning |
|---|---|
| `NORMAL` | No anomaly detected |
| `SENSOR_SPIKE` | Isolated abrupt step change — likely hardware transient |
| `SENSOR_STUCK_FROZEN` | Consecutive identical readings — stuck sensor |
| `GRADUAL_DRIFT` | Progressive calibration loss |
| `MULTIVARIATE_INCONSISTENCY` | Cross-channel thermodynamic conflict |
| `TEMPORAL_INCONSISTENCY` | Abrupt step that violates rate-of-change limits |
| `DATA_TELEMETRY` | Communication gap, delayed packet, or integrity issue |
| `WEATHER_EVENT` | Genuine atmospheric event (multivariate consistent) |
| `COMPETING_EVIDENCE` | Both weather and fault evidence present; ambiguous |

### 8.10 Weather vs. Sensor Fault Reasoning

The adjudicator computes two likelihood scores:

- **`weather_event_likelihood`:** How consistent are the multi-channel patterns with genuine atmospheric activity? Increases when T, P, and RH change simultaneously in a physically plausible direction.
- **`sensor_fault_likelihood`:** How consistent is the observation with isolated hardware failure? Increases when only one channel spikes or flatlines while others remain normal.

These are evidence-based assessments. They are **not** an oracle that guarantees the physical ground truth — they are the system's best evidential assessment given the available observations. A cold front that causes a large rapid temperature drop will score high weather likelihood *and* may trigger a high anomaly score — the reasoning summary will explain both, and the operator makes the final call.

---

## 9. Explainability

The system answers "Why was this observation flagged?" through two mechanisms:

### Reasoning Summary

A plain-English sentence constructed by the adjudicator from active trigger codes. Example outputs:

- *"Step spike detected on TEMPERATURE_SPIKE_POSITIVE. Deviation significantly exceeds robust baseline."*
- *"Frozen/stuck sensor detected on FROZEN_TEMPERATURE. Consecutive identical readings across 12 steps."*
- *"Multivariate T/P/RH pattern consistent with a weather event. Weather likelihood: 0.83."*

### Evidence Codes

Structured trigger codes are presented as human-readable bullets in the dashboard:

```
• ⚠️ Rapid temperature increase detected — the temperature is changing
     at an unusually high rate compared with the expected operating pattern.

• ⚠️ Temperature differs significantly from the station's recent expected pattern.

• 🌦️ Multi-variable atmospheric changes move together in a pattern
      consistent with a genuine weather event.
```

### Full Example

**Observation:** Temperature jumps +25°C in a single sampling interval while pressure and humidity remain stable.

**Evidence:**
- `TEMPERATURE_SPIKE_POSITIVE` — Rapid unphysical temperature step detected
- `ROBUST_ZSCORE_EXCURSION_TEMPERATURE` — Deviation from 96-step baseline: critical
- No corresponding pressure/humidity shift — multivariate inconsistency present

**Assessment:**
- Decision State: `ANOMALY`
- Severity: `HIGH`
- Anomaly Score: `1.000`
- Detection Confidence: High
- Attribution Confidence: High
- Root Cause: `SENSOR_SPIKE`
- Weather Likelihood: `0.03` (single-channel only, no atmospheric coherence)
- Sensor Fault Likelihood: `0.97`

**Plain reasoning:** *"Step spike detected: temperature jumped beyond physical rate limits while pressure and humidity remain stable. Consistent with isolated sensor hardware fault, not atmospheric activity."*

> All evidence text is sanitized through a central HTML/CSS stripping layer before display, ensuring only clean, readable operator text is presented — never raw markup or code.

---

## 10. Sensor Health

### Station-Level Health

The system tracks the overall health of a station based on its recent telemetry behaviour, model baseline integrity, and communication regularity.

### Channel-Level Health States

Per-channel health is evaluated by `health/sensor_health/diagnostics.py` and persisted to the `health_state` SQLite table:

| State | Availability | Condition | Maintenance Priority |
|---|---|---|---|
| `HEALTHY` | ≥ 90% | Nominal baseline variance, no active anomaly triggers | `NONE` |
| `DEGRADED` | 70–90% | Intermittent dropouts or isolated statistical excursions | `MONITOR` |
| `AT_RISK` | 50–70% | Frozen flatline (4–7 steps) or recurring calibration drift | `INSPECTION_RECOMMENDED` |
| `CRITICAL` | < 50% | Persistent stuck sensor (8+ steps) or severe data loss | `URGENT_MAINTENANCE` |

### Availability vs. Health

- **Availability:** Did the expected observations arrive within the cadence window? (Data completeness)
- **Health State:** Does the observed data show evidence of degradation, calibration drift, or hardware fault? (Data quality)

A sensor can have 100% availability but be in a `CRITICAL` health state if it is stuck at a constant value — every packet arrives, but all packets are faulty.

---

## 11. Data Integrity

### Raw Observation Preservation

Every ingested observation is stored in two forms:

| Table | Content | Mutability |
|---|---|---|
| `raw_observations` | Exact ingested values (`temperature_raw`, `pressure_raw`, `relative_humidity_raw`) | **Immutable** — enforced by SQLite `BEFORE UPDATE` trigger |
| `processed_observations` | Processed values, derived quantities, and feature metadata | Read-only after insert |
| `decisions` | Full decision record including `decision_state`, `reasoning_summary`, `evidence_codes_json` | Append-only |

The database trigger `prevent_raw_observation_update` aborts any `UPDATE` attempt on `raw_observations`, ensuring the original field measurement can never be silently overwritten by the processing pipeline.

### SQLite WAL Mode

The database operates in **Write-Ahead Logging (WAL) mode**, which provides:
- Concurrent read access during write operations
- Improved durability and crash recovery
- Better write throughput for append-heavy observation workloads

### Handling Irregular Telemetry

| Condition | System Response |
|---|---|
| Duplicate timestamp, same values | Detected and logged as integrity event; second copy rejected |
| Duplicate timestamp, conflicting values | Flagged `CONFLICTING_DUPLICATE`; observation quarantined |
| Missing slots / communication gap | Gap count recorded; `COMMUNICATION_GAP` evidence raised |
| Delayed observation (arrived late) | Flagged as `DELAYED`; accepted with telemetry note |
| Out-of-physical-range value | Rejected with `RANGE_VIOLATION` |

---

## 12. Dashboard

The Streamlit dashboard (`http://localhost:8501`) is the **single user-facing product**. FastAPI's `/docs` and `/redoc` pages at port 8000 are developer tools, not end-user interfaces.

### Tab 1 — Station Overview

**Purpose:** Live snapshot of the most recent AWS observation and its decision.

**What the operator sees:**
- Station metadata (ID, coordinates, sampling cadence)
- Latest telemetry KPIs (Temperature, Barometric Pressure, Relative Humidity, Derived Dewpoint)
- Decision state badge (NORMAL / SUSPECT / ANOMALY)
- Anomaly score, detection confidence, and attribution confidence bars
- Weather-event consistency vs. sensor-fault evidence cards
- Plain-English evidence bullets: "Why this was flagged"
- Reasoning summary callout
- Recent station records table

### Tab 2 — Anomaly Monitor

**Purpose:** Alert timeline and operator review queue.

**What the operator sees:**
- Summary metrics: flagged events, cases requiring review, critical alerts, admitted-to-baseline count
- Suspect/borderline cases expanded for immediate review (root cause, evidence, reasoning)
- Chronological decision timeline table with severity filter
- Telemetry and communication integrity event log

### Tab 3 — Historical Analytics

**Purpose:** Trend visibility over recent observation history.

**What the operator sees:**
- Multi-channel time-series chart (Temperature, Pressure, Relative Humidity) on a native datetime axis
- Anomaly score trajectory chart with threshold indicators
- Raw vs. processed value comparison layer
- Empty-state handled gracefully with a styled notice

### Tab 4 — Sensor Health

**Purpose:** Longitudinal sensor health diagnostics.

**What the operator sees:**
- Station health banner (HEALTHY / DEGRADED / AT_RISK / CRITICAL)
- Per-channel availability percentage and health state cards
- Degradation state and maintenance priority for each channel
- Expandable diagnostic evidence per channel
- Dual-clock baseline depth (96-step and 12-step window fill status)
- Baseline protection status and ingestion contract parameters

### Tab 5 — Scenario Lab

**Purpose:** Reproducible system validation and demonstration.

**What the operator sees:**
- 10-scenario selector (described in Section 13)
- 4-stage progression dashboard (Baseline → Transition → Peak Anomaly → Final State)
- Peak anomaly card with full decision breakdown and evidence
- Formal acceptance validation (PASS / FAIL)
- Complete replay decision timeline
- Manual single-observation injection form

---

## 13. Scenario Lab

The Scenario Lab provides **10 pre-configured, physics-calibrated synthetic demonstration scenarios** that can be executed directly from the dashboard. Each scenario injects a specific meteorological fault type or weather event into a synthetic AWS data stream and validates that the detection pipeline responds as expected.

> These are **synthetic demonstrations** using physics-calibrated mathematical generators — not replays of real historical station archives. The scenario generators produce realistic diurnal curves (sine/cosine baseline profiles) with controlled fault injections at defined onset indices.

| # | Scenario Name | Injected Phenomenon | Target Channel | Expected Decision | Expected Root Cause |
|---|---|---|---|---|---|
| 1 | **NOMINAL** | Diurnal sine/cosine baseline — no faults | All (T, P, RH) | `NORMAL` | `NORMAL` |
| 2 | **SPIKE** | Isolated +25.0°C step jump at index 12 | Temperature | `ANOMALY` | `SENSOR_SPIKE` |
| 3 | **FLATLINE** | Consecutive frozen temperature (12 steps) | Temperature | `ANOMALY` | `SENSOR_STUCK_FROZEN` |
| 4 | **DRIFT** | Progressive +1.5%/step calibration drift | Relative Humidity | `ANOMALY` | `GRADUAL_DRIFT` |
| 5 | **MULTIVARIATE_INCONSISTENCY** | Thermodynamic conflict between T, P, and RH/dewpoint | T, P, RH | `ANOMALY` | `MULTIVARIATE_INCONSISTENCY` |
| 6 | **BIAS** | Sudden −20.0 hPa level shift at index 10 | Barometric Pressure | `ANOMALY` | `SENSOR_SPIKE` |
| 7 | **NOISE** | Elevated Gaussian sensor noise (σ = 5.0°C) | Temperature | `ANOMALY` | `TEMPORAL_INCONSISTENCY` |
| 8 | **COMMUNICATION_GAP** | 4 dropped telemetry packets | Data stream | `NORMAL` (integrity flagged) | `DATA_TELEMETRY` |
| 9 | **GENUINE_WEATHER** | Cold front: −9°C T, +40% RH, +4 hPa P | All (coordinated) | `ANOMALY` (Weather Likelihood = 0.83) | `TEMPORAL_INCONSISTENCY` / Weather |
| 10 | **COMBINED** | Simultaneous spike, communication gap, and flatline | Multi-channel | `ANOMALY` | `SENSOR_SPIKE` / `STUCK` |

All 10 scenarios achieved formal `PASS` status in the Final Release QA (verified against acceptance criteria tables — see Section 14).

---

## 14. Validation & Testing

### Final Test Baseline

The validated baseline from the Final Release QA (27_FINAL_RELEASE_QA.md):

```
python -m pytest -v
============================= 145 passed in 33.27s =============================
```

The current repository baseline (after evidence sanitization and branding updates) is:

```
python -m pytest -v
============================= 158 passed in ~35s ==============================
```

The additional 13 tests cover the central HTML/CSS evidence sanitization layer added post-release.

### Test Categories

| Test Module | Tests | Coverage |
|---|---|---|
| `tests/invariants/test_invariants.py` | 5 | Raw immutability, quarantine isolation, schema integrity |
| `tests/unit/test_all_14_faults.py` | 14 | All 14 distinct sensor fault types |
| `tests/unit/test_detection_triggers.py` | 10 | Spike, frozen, rate, thermodynamic, determinism, latency |
| `tests/unit/test_decision_adjudicator.py` | 14 | Full adjudicator state machine (all root causes) |
| `tests/unit/test_thermodynamics.py` | 4 | Vapour pressure, dewpoint, Magnus-Tetens |
| `tests/unit/test_integrity_gate.py` | 4 | Range violations, duplicates, communication gaps |
| `tests/unit/test_rates.py` | 2 | Rate-of-change computation |
| `tests/unit/test_feature_builder.py` | 3 | Ring-buffer, feature vector dimensions |
| `tests/unit/test_charts_unit_a.py` | 10 | Chart reliability (null safety, datetime axis, midnight) |
| `tests/unit/test_explainability_unit_a.py` | 8 | All 8 adjudicator explainability cases |
| `tests/unit/test_sensor_health_unit_b.py` | 8 | Channel health, persistence, SQLite retrieval |
| `tests/unit/test_scenario_testbed_unit_b.py` | 11 | All 10 scenarios + list endpoint |
| `tests/unit/test_evidence_sanitization.py` | 13 | Central HTML/CSS evidence sanitizer |
| `tests/unit/test_schemas.py` | 4 | Observation schema, ID determinism, payload hash |
| `tests/unit/test_fault_injector.py` | 3 | Fault injection (spike, frozen, gap) |
| `tests/unit/test_simulator.py` | 2 | Generator bounds, replayer completeness |
| `tests/unit/test_config_and_claims.py` | 3 | Configuration, disclaimer, settings |
| `tests/integration/` (5 modules) | 33 | End-to-end pipeline, data truth, phase integration |

**Key invariants verified:**
- `test_inv02_raw_immutability` — SQLite trigger prevents updates to raw observations
- `test_inv04_quarantine_does_not_update_clean_buffer` — Anomalous observations never poison baselines
- Determinism: same input always produces the same output (`test_determinism`)
- Latency budget: pure inference < 2.0 ms (`test_inference_latency_benchmark`)

---

## 15. Performance

Performance figures measured on a local test environment (Windows, Python 3.13.7, SQLite WAL). These figures represent local prototype conditions, not guaranteed production metrics.

| Metric | Measured Value | Budget |
|---|---|---|
| **Pure ML Inference Latency** | 0.12 ms per observation | < 2.0 ms |
| **End-to-End Pipeline (Ingest + ML + SQLite write) P50** | 0.38 ms | < 500 ms |
| **End-to-End Pipeline P95** | 0.45 ms | < 500 ms |
| **Base RAM Footprint (FastAPI engine)** | < 45 MB | — |
| **Test Suite Execution** | ~35 seconds (158 tests) | — |

> **Important:** These measurements were taken on a single-machine local development environment under controlled test conditions. Production performance across a nationwide multi-station network would depend on hardware, database backend, network topology, and concurrent station count.

---

## 16. Deployment

### Current Validated Deployment

The current prototype runs as two Python services communicating over localhost HTTP:

| Service | Technology | Command | Port |
|---|---|---|---|
| Backend API | FastAPI + Uvicorn | `uvicorn app.main:app` | 8000 |
| Dashboard | Streamlit | `streamlit run dashboard/app.py` | 8501 |
| Storage | SQLite WAL | Embedded in `data/trusttwin.db` | — |

### Docker

A `Dockerfile` is provided for containerised deployment:

```bash
docker build -t skyguard-ai:latest .
docker run -p 8000:8000 -p 8501:8501 skyguard-ai:latest
```

### Edge Deployment Feasibility

The core detection logic is deliberately lightweight: no GPU required, no external ML model serving infrastructure needed, < 45 MB RAM footprint. The architecture is designed for eventual edge deployment on ARM-based single-board computers or station gateway appliances. **The current prototype is validated as a Python server application and has not been tested directly on microcontrollers or embedded systems** — edge-specific runtimes and packaging are **FUTURE WORK**.

### Production Scale Considerations

The embedded SQLite backend is suitable for prototype and edge/single-station appliances. For nationwide deployments with thousands of concurrent stations, the repository layer can transition to PostgreSQL/TimescaleDB without changes to the core intelligence pipeline — only the storage repositories need replacement.

---

## 17. Tech Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Frontend** | Streamlit | ≥ 1.37.0 | Operator web dashboard |
| **Backend** | FastAPI | ≥ 0.110.0 | REST API and SSE broadcast |
| **ASGI Server** | Uvicorn | ≥ 0.29.0 | FastAPI runtime |
| **Database** | SQLite (WAL mode) | Built-in | Persistent observation and decision storage |
| **Data Processing** | Pandas | ≥ 2.1.0 | Tabular observation processing |
| **Numerical Computing** | NumPy | ≥ 1.26.0 | Vectorized feature computation |
| **Statistics** | SciPy | ≥ 1.11.0 | Statistical utilities |
| **ML / Scikit** | scikit-learn | ≥ 1.4.0 | Supporting ML utilities |
| **Schema Validation** | Pydantic + Pydantic-Settings | ≥ 2.6.0 | Request validation, configuration |
| **Visualization** | Plotly | ≥ 5.20.0 | Interactive time-series charts |
| **HTTP Client** | httpx + requests | ≥ 0.27.0 | API client communication |
| **Testing** | pytest + pytest-cov + hypothesis | ≥ 8.0.0 | Unit, integration, property-based tests |
| **Containerization** | Docker | Current | Optional containerised deployment |

---

## 18. API Overview

Base URL: `http://127.0.0.1:8000`

Interactive documentation: `http://127.0.0.1:8000/docs`

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | System health check (status, version, active station count) |
| `GET` | `/ready` | Database readiness probe |
| `GET` | `/v1/status` | System status (project metadata, station count, disclaimer) |
| `POST` | `/v1/observations` | Ingest a single AWS observation; returns full Decision |
| `GET` | `/v1/stations` | List all registered stations |
| `GET` | `/v1/stations/{id}` | Get metadata for a specific station |
| `GET` | `/v1/stations/{id}/observations` | Get recent observations with decisions for a station |
| `GET` | `/v1/stations/{id}/events` | Get integrity/communication events for a station |
| `GET` | `/v1/stations/{id}/health` | Get sensor health diagnostics for a station |
| `GET` | `/v1/decisions` | List recent decisions (optionally filtered by station) |
| `GET` | `/v1/simulator/scenarios` | List all 10 available demonstration scenarios |
| `POST` | `/v1/simulator/scenarios/{name}/run` | Execute a named scenario through the replay engine |
| `GET` | `/v1/stream` | Server-Sent Events stream of live decisions |

### Example: Submit an Observation

```bash
curl -X POST "http://127.0.0.1:8000/v1/observations" \
     -H "Content-Type: application/json" \
     -d '{
       "station_id": "AWS_STATION_01",
       "timestamp": "2026-09-30T12:00:00Z",
       "temperature": 28.5,
       "pressure": 1008.2,
       "relative_humidity": 65.0,
       "source_type": "LIVE"
     }'
```

**Response includes:** `decision_state`, `anomaly_score`, `severity`, `detection_confidence`, `attribution_confidence`, `root_cause_category`, `reasoning_summary`, `evidence_codes`, `weather_event_likelihood`, `sensor_fault_likelihood`.

---

## 19. Project Structure

```
sih/
├── app/                        # FastAPI application service
│   ├── main.py                 # Server entry point, lifecycle hooks
│   ├── api/routes.py           # All REST route handlers
│   ├── core/                   # Config, claims, logging
│   └── runtime/engine.py       # Core pipeline orchestrator
│
├── dashboard/                  # Streamlit operator dashboard
│   ├── app.py                  # Page config, layout, navigation
│   ├── api_client.py           # HTTP client for FastAPI
│   ├── components/             # Reusable UI components
│   │   ├── charts.py           # Plotly time-series charts
│   │   ├── explainability.py   # Evidence, reasoning, sanitization
│   │   └── metrics.py          # Decision badges, score bars
│   └── views/                  # Tab-level view modules
│       ├── overview.py         # Station Overview tab
│       ├── anomaly_monitor.py  # Anomaly Monitor tab
│       ├── historical.py       # Historical Analytics tab
│       ├── sensor_health.py    # Sensor Health tab
│       └── scenario_runner.py  # Scenario Lab tab
│
├── detection/                  # AI/ML detection intelligence
│   ├── triggers/statistical.py # Spike, flatline, rate, MAD z-score
│   ├── reference/baseline.py   # 96-step Reference Profile (long-term)
│   ├── tracker/tracker.py      # 12-step Adaptive Tracker (short-term)
│   └── decision/adjudicator.py # Evidence accumulation, hypothesis resolution
│
├── features/                   # Feature engineering
│   ├── builder.py              # Ring-buffer, feature vector construction
│   ├── temporal/rates.py       # Rate-of-change computation
│   └── multivariate/thermodynamics.py  # Dewpoint, vapour pressure
│
├── ingestion/                  # Observation ingestion pipeline
│   ├── integrity/gate.py       # Deterministic validation gate
│   └── schemas/                # Pydantic observation schemas
│
├── health/                     # Sensor health diagnostics
│   └── sensor_health/diagnostics.py
│
├── simulator/                  # Synthetic scenario generators
│   ├── scenarios/suite.py      # 10 scenario definitions
│   ├── replay/replayer.py      # Executes observation sequences
│   └── stream/generator.py     # Diurnal baseline generator
│
├── storage/                    # Persistence layer
│   ├── schema.sql              # SQLite DDL (WAL, triggers, tables)
│   ├── db/connection.py        # Connection management
│   └── repositories/           # Data access objects per entity
│
├── tests/                      # Full test suite (158 tests)
│   ├── unit/                   # Unit tests per module
│   ├── integration/            # End-to-end pipeline tests
│   └── invariants/             # Immutability and safety invariants
│
├── scripts/
│   └── run_sih_demo.py         # Automated SIH demo script (all 10 scenarios)
│
├── requirements.txt
├── RUN.md                      # Runbook
└── README.md                   # This document
```

---

## 20. Demo Workflow

**Target duration: 3–5 minutes**

### Step-by-Step Judge Demo

**1. Open the Dashboard**
- Navigate to `http://localhost:8501`
- Point out: this is the single operator-facing product — a live AWS monitoring dashboard.

**2. Show Normal Monitoring (Station Overview)**
- Select any station from the sidebar Station Selector.
- Show the live telemetry KPIs (Temperature, Pressure, Humidity, Dewpoint).
- Show the Decision State badge — `NORMAL`, low anomaly score, green indicators.
- *"This is what a healthy station looks like in real time."*

**3. Run a Fault Scenario (Scenario Lab tab)**
- Switch to the `🧪 Scenario Testbed` tab.
- Select **"2. Isolated Temperature Spike"**.
- Click **Run Scenario**.
- Show the 4-stage progression (Baseline → Transition → Peak Anomaly → Final State).
- Point out the PASS card and the anomaly score: `1.000`, Severity: `HIGH`.

**4. Show Anomaly State (Station Overview)**
- Switch back to Station Overview.
- Show the red `ANOMALY` badge and the filled anomaly score bar.

**5. Show Confidence and Severity**
- Point to Detection Confidence and Attribution Confidence bars.
- *"The system is not just flagging — it's telling us how confident it is."*

**6. Show "Why This Was Flagged" (Evidence section)**
- Scroll to the Evidence section.
- Show the plain-English bullet: *"Rapid temperature increase detected — the temperature is changing at an unusually high rate..."*
- Show the Reasoning summary callout box.

**7. Show Weather vs. Sensor Assessment**
- Show the Weather-Event Consistency and Sensor/Data Fault Evidence cards.
- *"Here the sensor fault evidence is 97%+, weather consistency is near zero — single channel spike, no atmospheric coherence."*

**8. Show the Genuine Cold Front Scenario**
- Go to Scenario Lab, select **"9. Genuine Cold Front Event"**.
- Show Weather Likelihood = 0.83 on the results card.
- *"When all three channels shift together in a physically consistent way — cold front — the system recognises it as likely weather, not sensor fault. Same anomaly score, very different attribution."*

**9. Open Sensor Health**
- Switch to the Sensor Health tab.
- Show per-channel availability, health state, and degradation assessment.
- *"This is longitudinal health tracking — not just per-observation alerts, but persistent quality diagnostics."*

**10. Historical Analysis**
- Switch to Historical Analytics.
- Show the multi-channel time-series chart and anomaly score trajectory.
- *"Full temporal context — operators can see when things started drifting."*

**11. Mention Raw Data Preservation**
- *"Everything ingested is stored immutably. The raw sensor reading is never silently overwritten. Full audit trail."*

---

## 21. PPT-Ready Content

### Slide 1 — Title

- **SkyGuard AI**
- AI/ML-Based Intelligent Anomaly Detection for Automatic Weather Stations
- SIH 2026 | Problem Statement SIH26073
- Real-time · Evidence-based · Explainable · Longitudinal

---

### Slide 2 — The Problem

- India's AWS network continuously streams temperature, pressure, and humidity telemetry
- Sensor hardware fails: spikes, flatlines, gradual drift, communication gaps
- Corrupted observations silently pollute meteorological records and forecasting baselines
- Traditional threshold rules flag outliers but cannot distinguish sensor faults from real weather events
- No longitudinal sensor health tracking → faults go undetected until catastrophic failure
- Operators face alert fatigue and unexplained flags without actionable context

---

### Slide 3 — Why Basic QC Is Insufficient

- **Fixed thresholds miss gradual drift** — a sensor drifting 0.1°C/day passes every rule for months
- **Thresholds cannot reason across channels** — a pressure spike with stable T and RH is very different from a simultaneous shift in all three
- **Threshold rules ignore baseline context** — a −10°C reading is normal in winter but anomalous in summer
- **No competing-hypothesis testing** — existing QC does not ask "weather or sensor fault?"
- **No longitudinal health state** — each observation evaluated in isolation, no channel-level memory

---

### Slide 4 — SkyGuard AI Solution

- Multi-layer detection pipeline: integrity gate → feature engineering → statistical + temporal + multivariate detection → dual-clock baseline → evidence adjudication
- **Competes two hypotheses** for every anomaly: genuine weather event vs. hardware fault
- Generates a **plain-English reasoning summary** and **category-coded evidence bullets** — no ML black box
- Tracks **longitudinal sensor health** per channel with maintenance priority
- Deterministic, reproducible, and validated through a 10-scenario test suite
- Lightweight: < 0.5 ms end-to-end, < 45 MB RAM — designed for eventual edge deployment

---

### Slide 5 — System Architecture

```
Observation → Integrity Gate → Feature Processing → Anomaly Detection
     → Dual-Clock Baseline → Decision Adjudication
     → Sensor Health → SQLite WAL → REST API → Streamlit Dashboard
```

- **Frontend:** Streamlit dashboard (5 operator tabs)
- **Backend:** FastAPI REST API + SSE live stream
- **Intelligence:** Statistical detector + temporal triggers + thermodynamic consistency + MAD z-score
- **Storage:** SQLite WAL with immutable raw observation layer
- **Scenarios:** 10-scenario validation suite

---

### Slide 6 — AI/ML Methodology

- **Robust MAD z-score:** Median Absolute Deviation baseline — resistant to outliers that inflate standard deviation
- **Temporal detectors:** Step spikes, rate-of-change limiters, frozen/flatline detection
- **Multivariate thermodynamics:** Magnus-Tetens dewpoint consistency across T, P, RH
- **Dual-clock baseline:** 96-step long-term + 12-step short-term — catches both slow drift and sudden shifts
- **Anti-poisoning:** Anomalous observations quarantined from baseline updates — system cannot normalise its own faults
- Sub-millisecond inference: 0.12 ms pure ML, 0.38 ms P50 end-to-end (measured locally)

---

### Slide 7 — Weather vs. Sensor Fault Reasoning

- Every anomaly assessed against two competing hypotheses simultaneously
- **Weather-event likelihood:** Are T, P, and RH shifting in a physically coherent pattern? (e.g. cold front: T↓, RH↑, P↑)
- **Sensor-fault likelihood:** Is only one channel affected? Does the shift violate thermodynamic physical laws?
- Genuine cold front scenario: Weather Likelihood = **0.83** — system correctly attributes to weather, not hardware
- Isolated temperature spike: Sensor Fault Likelihood = **0.97** — single channel, no atmospheric coherence
- Both likelihoods are shown transparently to the operator; the system assists — the operator decides

---

### Slide 8 — Explainability + Sensor Health

**Explainability:**
- Every decision backed by traceable evidence codes and plain-English reasoning
- Evidence: *"Rapid temperature increase detected... Deviation from recent pattern... No corresponding cross-channel shift"*
- No LLM hallucinations — reasoning is rule-based and verifiable

**Sensor Health:**
- Per-channel health states: HEALTHY → DEGRADED → AT_RISK → CRITICAL
- Availability tracking, degradation state, and maintenance priority
- Diagnostic evidence explains *why* a channel is flagged unhealthy
- Longitudinal memory: tracks patterns across many observations, not just the latest

---

### Slide 9 — Dashboard & Demo

**5 operator-facing tabs:**
1. Station Overview — live telemetry, decision badge, evidence, reasoning
2. Anomaly Monitor — alert timeline, suspect review queue, severity filter
3. Historical Analytics — multi-channel time-series, anomaly score trajectory
4. Sensor Health — per-channel diagnostics, baseline integrity, maintenance priority
5. Scenario Lab — 10 reproducible validation scenarios with formal acceptance testing

**Demo highlight:**
- Run "Isolated Temperature Spike" → observe ANOMALY, score 1.0, sensor fault evidence 97%+
- Run "Genuine Cold Front" → observe ANOMALY, weather likelihood 0.83 → correct attribution

---

### Slide 10 — Validation & Results

- **158 tests passing** (100% pass rate, 0 regressions)
- All **10 demonstration scenarios** achieve formal PASS against acceptance criteria
- **15 SIH26073 requirements** — 100% IMPLEMENTED and verified
- Data truth verified: every field from raw sensor input through database to dashboard rendering
- Immutability invariant verified: raw observations cannot be silently overwritten
- Anti-poisoning invariant verified: quarantined observations never update baselines

---

### Slide 11 — Innovation / Differentiation

- **Competing-hypothesis reasoning:** Simultaneously scores weather-event vs. sensor-fault evidence — not just "is it an outlier?" but "what kind of outlier?"
- **Dual-clock anti-poisoning baseline:** Two complementary windows prevent gradual sensor drift from self-normalising in the model
- **Thermodynamic multivariate consistency:** Physical law verification, not just per-channel statistics
- **Evidence-based explainability:** Plain-English reasoning without LLMs; deterministic, reproducible, and auditable
- **Longitudinal sensor health:** Health state memory across time, not observation-by-observation evaluation
- **Raw data immutability:** Field readings preserved by database trigger — full scientific audit trail

---

### Slide 12 — Impact + Future Scope

**Demonstrated capability:**
- Real-time anomaly detection with < 0.5 ms latency (measured locally)
- Transparent, evidence-backed explanations operators can act on
- 10-scenario validated demonstration suite

**Potential operational impact:**
- Earlier identification of faulty sensors before data quality degrades significantly
- Reduced operator manual inspection workload through prioritised, explainable alerts
- Reduced false-alarm burden during genuine weather events through weather-vs-fault reasoning

**Future scope:**
- Additional AWS channels: wind speed, solar radiation, rain gauge
- Production time-series database (TimescaleDB/PostgreSQL) for national networks
- Edge runtime packaging for station gateway appliances
- Real historical archive validation with labelled fault events
- Spatial cross-station consistency checks

---

## 22. Innovation / Differentiation

The following points of differentiation are supported by the implemented codebase:

**1. Competing-hypothesis reasoning (not just outlier detection)**
The adjudicator simultaneously scores weather-event likelihood and sensor-fault likelihood from the same observation evidence, producing a calibrated comparison rather than a binary anomaly flag.

**2. Dual-clock anti-poisoning baseline**
Running two temporal windows (96-step and 12-step) in parallel catches both slow drift (invisible to short windows) and sudden shifts (averaged away in long windows). The quarantine barrier ensures neither window can be contaminated by the faults it is designed to detect.

**3. Thermodynamic multivariate consistency as a first-class detector**
Physical law verification (Magnus-Tetens dewpoint, vapour pressure) is integrated into the detection pipeline as a formal detector, not an optional post-processing step. This makes multivariate inconsistency a structured evidence code rather than a visual inspection task.

**4. Fully traceable evidence-based explainability without LLMs**
Every decision can be reconstructed from its trigger codes and adjudicator state. There are no probabilistic language models involved — all reasoning is deterministic and auditable. The same input always produces the same output (verified by `test_determinism`).

**5. Longitudinal sensor health with maintenance priority**
The system maintains a health state per channel that persists across observations, generating a maintenance priority recommendation (NONE / MONITOR / INSPECTION_RECOMMENDED / URGENT_MAINTENANCE) rather than per-observation flags.

**6. Immutable raw observation store**
Raw sensor measurements are protected by a SQLite `BEFORE UPDATE` trigger, ensuring the original field reading cannot be modified by any pipeline step, bug, or reprocessing run.

---

## 23. Operational Impact

### Current Demonstrated Capability

- Real-time anomaly detection and classification on AWS telemetry (validated in prototype)
- Evidence-based plain-English explanations for every decision (demonstrated in prototype)
- Weather-event vs. sensor-fault discrimination (demonstrated for cold front and spike scenarios)
- Longitudinal per-channel sensor health tracking (demonstrated in prototype)
- 10-scenario reproducible validation suite with formal acceptance testing
- Raw observation preservation with database-enforced immutability

### Potential Operational Impact (If Deployed)

- **Earlier fault detection:** Gradual drift and flatline faults caught before they significantly corrupt the meteorological record
- **Reduced operator workload:** Explainable, prioritised alerts reduce the time spent on manual investigation of unexplained flags
- **Fewer unnecessary maintenance callouts:** Weather-vs-fault reasoning reduces false maintenance dispatches during genuine weather events
- **Improved data quality:** Quarantine barrier prevents faulty observations from contaminating baseline models
- **Trustworthy audit trail:** Immutable raw observation store supports post-event forensic analysis

> These potential impacts have not been measured in a production field deployment. They are projections based on system design and prototype validation.

---

## 24. Limitations

The following limitations are documented transparently:

1. **Thermodynamic trio MVP scope:** The current implementation evaluates Temperature, Barometric Pressure, and Relative Humidity. Wind speed, wind direction, solar radiation, and precipitation gauge channels are **FUTURE WORK**.

2. **Synthetic demonstration scenarios:** The Scenario Lab uses physics-calibrated mathematical generators. Scenario results should not be interpreted as performance on real historical station archives — that validation has not been conducted.

3. **SQLite persistence scale:** The embedded SQLite WAL backend is appropriate for prototype and edge/single-station appliances. Large-scale concurrent nationwide deployments (> 10,000 stations) would require a production time-series database such as TimescaleDB or PostgreSQL.

4. **Prototype deployment scope:** The system is validated as a Python server application on local hardware. Edge deployment on microcontrollers or embedded systems is a stated design goal but has not been implemented or tested.

5. **Performance measured locally:** Latency figures (0.12 ms inference, 0.38 ms P50 end-to-end) were measured on a local Windows development machine under single-station conditions. Production performance is expected to vary.

---

## 25. Future Scope

*All items below are **FUTURE WORK** — not currently implemented.*

| Future Capability | Rationale |
|---|---|
| Wind speed, solar radiation, rain gauge channels | Extend the same detector architecture to all standard AWS channels |
| Production time-series database (TimescaleDB/PostgreSQL) | Support nationwide multi-station concurrent deployments |
| Real historical station archive validation | Validate detection accuracy against labelled fault events from real AWS data |
| Edge runtime packaging | Deploy core detection logic on ARM-based gateway appliances or RPi-class hardware |
| Spatial cross-station consistency | Detect faults by comparing simultaneous readings from nearby stations |
| Adaptive threshold calibration | Learn station-specific physical rate limits rather than using universal defaults |
| Alert notification integration | Push critical anomalies to SMS/email/field-operations systems |

---

## 26. Requirement Coverage

| Requirement | Description | Status | Verification |
|---|---|---|---|
| REQ-01 | Real-time anomaly detection (sub-second) | **IMPLEMENTED** | `engine.process_observation` < 0.5 ms e2e |
| REQ-02 | Temporal anomaly detection (spikes, rates, bias) | **IMPLEMENTED** | `triggers/statistical.py`, 14 fault tests pass |
| REQ-03 | Multivariate consistency (T, P, RH, Td) | **IMPLEMENTED** | `thermodynamics.py`, multivariate scenario PASS |
| REQ-04 | Anomaly scoring [0.0–1.0] | **IMPLEMENTED** | `adjudicator.py` composite score |
| REQ-05 | Detection and attribution confidence scores | **IMPLEMENTED** | Two distinct confidence fields in decision |
| REQ-06 | Multi-level severity classification | **IMPLEMENTED** | LOW / MODERATE / HIGH / CRITICAL |
| REQ-07 | Traceable explainability (no LLM hallucination) | **IMPLEMENTED** | `reasoning_summary` + `evidence_codes` |
| REQ-08 | Root-cause attribution | **IMPLEMENTED** | 9 root-cause categories in adjudicator |
| REQ-09 | Weather vs. sensor-fault discrimination | **IMPLEMENTED** | `weather_event_likelihood` vs `sensor_fault_likelihood` |
| REQ-10 | Longitudinal sensor health diagnostics | **IMPLEMENTED** | `diagnostics.py`, `health_state` SQLite table |
| REQ-11 | Operator alerting and monitoring | **IMPLEMENTED** | Anomaly Monitor tab, suspect review queue |
| REQ-12 | Historical multi-channel analytics | **IMPLEMENTED** | Historical Analytics tab, Plotly datetime charts |
| REQ-13 | Raw data preservation (immutability) | **IMPLEMENTED** | SQLite BEFORE UPDATE trigger |
| REQ-14 | Dual-clock baseline with anti-poisoning | **IMPLEMENTED** | ReferenceProfile (96) + AdaptiveTracker (12) + Quarantine |
| REQ-15 | Deployability and portability | **IMPLEMENTED** | FastAPI + SQLite + Dockerfile + Streamlit |
| Wind/Solar/Rain channels | Extended AWS channel support | **FUTURE WORK** | Not in current MVP |
| Edge microcontroller runtime | Embedded systems deployment | **FUTURE WORK** | Designed for but not yet implemented |

---

## 27. Technical Q&A Preparation

**Q1: Why is this better than simple threshold rules?**
Fixed thresholds evaluate each reading in isolation against an absolute limit. SkyGuard AI evaluates relative to the station's own established baseline (so a –10°C reading is assessed against whether that is unusual *for this station at this time*), considers temporal context (rate-of-change), evaluates cross-channel consistency (thermodynamics), and distinguishes weather events from hardware faults. A sensor stuck at a constant physically plausible value will pass every threshold rule but is immediately caught by the frozen-sensor detector.

**Q2: How do you distinguish weather from sensor fault?**
By evaluating whether all three channels (T, P, RH) shift in a physically coherent direction simultaneously. A genuine cold front causes a coordinated drop in temperature, rise in humidity, and rise in pressure — all three consistent with atmospheric physics. A single-channel spike with stable other channels has no atmospheric explanation. The adjudicator scores both hypotheses from the evidence and the higher-scoring hypothesis is reported, along with the scores for both, so the operator can make an informed decision.

**Q3: Why use robust statistics (MAD) rather than standard deviation?**
Standard deviation is heavily influenced by outliers — a single severe spike inflates the standard deviation, making the next anomalous reading appear less unusual. MAD uses the median of deviations from the median, making it far more resistant to outliers. This means the baseline remains stable even when the station occasionally experiences transient faults, so sensitivity is maintained.

**Q4: Why maintain both a 96-step and a 12-step baseline?**
Each catches different fault types. A slow drift over weeks barely moves the 12-step tracker (it just follows the drift), but will deviate significantly from the 96-step profile. A sudden level shift that happened 50 observations ago is averaged into the 96-step profile, but the 12-step tracker will show it as a deviation. Running both simultaneously provides coverage across the full range of drift timescales.

**Q5: How do you prevent anomalous data from poisoning the baseline?**
Observations flagged as anomalous or quarantined receive `AdmissionState = QUARANTINE` or `REJECT`. Only observations with `AdmissionState = ADMIT` are included in baseline profile updates. This is enforced in the engine and verified by the test `test_inv04_quarantine_does_not_update_clean_buffer`.

**Q6: How is confidence different from severity?**
Severity describes *how strong* the anomaly signal is — a critically large deviation gets `CRITICAL` severity. Confidence describes *how certain* the system is about that assessment — a small baseline means low detection confidence even if the current deviation seems large. Attribution confidence separately measures certainty about the root-cause label. The system can have high severity with moderate attribution confidence (e.g. clear anomaly, but ambiguous between drift and spike).

**Q7: How is sensor health calculated?**
`health/sensor_health/diagnostics.py` evaluates: (1) channel availability — what fraction of expected observations arrived in the rolling window; (2) frozen/flatline patterns across recent readings; (3) anomaly event counts in the current window; (4) communication event counts. These metrics map to discrete health states (HEALTHY / DEGRADED / AT_RISK / CRITICAL) and maintenance priorities, persisted to the `health_state` SQLite table.

**Q8: How do you handle missing or delayed observations?**
The integrity gate detects missing slots by comparing the observation timestamp to the expected cadence. Missing slots raise a `MISSING_SLOTS` integrity event. Delayed observations (arrived after the expected window) are flagged `ACCEPT_LATE` and include a `DELAYED` evidence code. Both are logged to `integrity_events` and visible in the Anomaly Monitor's Telemetry Events log.

**Q9: How do you preserve raw data?**
The `raw_observations` table stores the original ingested sensor values (`temperature_raw`, `pressure_raw`, `relative_humidity_raw`) and is protected by a SQLite `BEFORE UPDATE` trigger (`prevent_raw_observation_update`) that aborts any update attempt. The pipeline can never silently overwrite what was received from the field instrument.

**Q10: What happens when the system is uncertain?**
When weather-event evidence and sensor-fault evidence are roughly equal, the adjudicator assigns `root_cause_category = COMPETING_EVIDENCE` and `decision_state = AMBIGUOUS`. The uncertainty state is set to `HIGH` and the reasoning summary explicitly states that the available evidence does not clearly separate the two hypotheses — prompting operator review rather than automated action.

**Q11: How does it scale to many stations?**
Each station has its own independent `StationState` in memory and its own rows in the database. The processing pipeline is stateless per request — it loads station state, processes one observation, and saves. The current SQLite backend handles prototype and edge/single-appliance scales. For nationwide networks, the storage repositories can be swapped to PostgreSQL/TimescaleDB without changing the detection logic.

**Q12: Can it run at the edge?**
The core detection logic requires no GPU, no model serving infrastructure, and uses < 45 MB RAM. It is designed for eventual edge deployment. The current prototype is a Python server application and has not been packaged for microcontrollers or embedded systems — that is explicitly documented as future work.

**Q13: What data was used for training?**
SkyGuard AI does not use a traditional supervised ML model trained on labelled historical datasets. The detection pipeline is based on physics-calibrated thresholds, robust statistical methods (MAD), and thermodynamic physical laws. The baseline profiles are built adaptively from each station's own incoming observation history. No external training dataset was required or used.

**Q14: Is this actually ML, or only rules?**
Both. The system combines rule-based detectors (step jumps, rate limits, frozen patterns) with statistical learning (MAD z-score baselines that adapt to each station's behaviour over time) and thermodynamic physical modelling. The adjudicator is a deterministic evidence-accumulation state machine. This hybrid approach is intentional: it provides the interpretability of rules with the adaptivity of statistical baselines.

**Q15: What are the current limitations?**
See [Section 24 — Limitations](#24-limitations). Key ones: MVP scope covers T/P/RH only; demonstration uses synthetic scenarios rather than real historical archives; persistence uses SQLite (suitable for edge, not nationwide scale); edge microcontroller deployment is future work; performance figures are local prototype measurements.

**Q16: How would this be deployed by a meteorological organisation?**
In a realistic deployment: (1) The FastAPI backend would run on a station gateway server or cloud appliance receiving MQTT/HTTP telemetry from field instruments; (2) the Streamlit dashboard would be hosted on an internal network for operator access; (3) SQLite would be replaced with TimescaleDB for nationwide concurrent station support; (4) the system would integrate with existing alerting infrastructure (SMS, email, field dispatch) via its REST API.

---

## 28. One-Page Project Fact Sheet

| Field | Value |
|---|---|
| **Project Name** | SkyGuard AI |
| **Problem Statement** | SIH26073 — AI/ML-Based Intelligent Anomaly Detection for Automatic Weather Stations |
| **Primary Inputs** | Temperature (°C), Barometric Pressure (hPa), Relative Humidity (%) |
| **Architecture** | FastAPI backend + Streamlit frontend + SQLite WAL persistence |
| **Frontend** | Streamlit dashboard (`http://localhost:8501`) — 5 operator tabs |
| **Backend** | FastAPI REST API + SSE stream (`http://127.0.0.1:8000`) |
| **Database** | SQLite WAL (immutable raw layer + decision persistence) |
| **Core Detection Methods** | Robust MAD z-score, spike/flatline/rate-of-change triggers, Magnus-Tetens thermodynamic consistency, dual-clock baseline |
| **Decision Outputs** | Decision State, Anomaly Score [0–1], Severity, Detection Confidence, Attribution Confidence, Root Cause, Reasoning Summary, Evidence Codes |
| **Weather vs. Fault** | `weather_event_likelihood` and `sensor_fault_likelihood` per observation |
| **Sensor Health** | Per-channel: HEALTHY / DEGRADED / AT_RISK / CRITICAL + maintenance priority |
| **Explainability** | Plain-English reasoning summary + category-coded evidence bullets (deterministic, no LLM) |
| **Scenario Count** | 10 (NOMINAL, SPIKE, FLATLINE, DRIFT, BIAS, NOISE, COMM_GAP, MULTIVARIATE, GENUINE_WEATHER, COMBINED) |
| **Test Count** | 158 passing (100% pass rate) |
| **Performance (local)** | Pure ML inference: 0.12 ms; End-to-end P50: 0.38 ms; P95: 0.45 ms; RAM: < 45 MB |
| **Current Limitations** | T/P/RH MVP only; synthetic scenarios; SQLite scale; prototype deployment |
| **Dashboard URL** | `http://localhost:8501` |
| **API Base URL** | `http://127.0.0.1:8000` |
| **API Docs** | `http://127.0.0.1:8000/docs` |
| **Entry Point (backend)** | `uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| **Entry Point (dashboard)** | `streamlit run dashboard/app.py --server.port 8501` |

---

## 29. Run Instructions

### Prerequisites

- Python 3.10+ (recommended: 3.11 or 3.13)
- pip
- (Optional) Docker

### Step 1 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2 — Run the Full Test Suite

```bash
python -m pytest -v
```

Expected: 158 passed (0 failures, ~35 seconds).

Run with coverage:

```bash
python -m pytest --cov=. --cov-report=term-missing
```

### Step 3 — Start Backend API (Terminal 1)

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- API Base URL: `http://127.0.0.1:8000`
- Interactive API Docs: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/health`

### Step 4 — Start Streamlit Dashboard (Terminal 2)

```bash
streamlit run dashboard/app.py --server.port 8501
```

- Dashboard: `http://localhost:8501`

### Step 5 — Run the SIH Demonstration Suite

Executes all 10 scenarios end-to-end with terminal trace output:

```bash
python scripts/run_sih_demo.py
```

### Step 6 — Submit a Single Observation via API

```bash
curl -X POST "http://127.0.0.1:8000/v1/observations" \
     -H "Content-Type: application/json" \
     -d '{
       "station_id": "AWS_STATION_01",
       "timestamp": "2026-09-30T12:00:00Z",
       "temperature": 28.5,
       "pressure": 1008.2,
       "relative_humidity": 65.0,
       "source_type": "LIVE"
     }'
```

### Docker Deployment (Optional)

```bash
docker build -t skyguard-ai:latest .
docker run -p 8000:8000 -p 8501:8501 skyguard-ai:latest
```

---

*SkyGuard AI — SIH26073 | Validated 2026-09-30 | 158 tests passing | Demonstration-ready*
