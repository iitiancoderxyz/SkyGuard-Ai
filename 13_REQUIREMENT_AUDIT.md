# 13_REQUIREMENT_AUDIT — SIH26073

**Agent:** GUARD AGENT 13 — REQUIREMENTGUARD
**Date:** 29 September 2026
**Scope:** Compliance only. This audit does not redesign the idea, improve novelty, or add features.
**Baseline audited against:** `00_MASTER_BRIEF.md` (authoritative requirements)
**Artifact audited:** `12_FINAL_SOLUTION.md` (TRUST-TWIN — Quarantine-Gated Sequential Evidence Monitor)

---

## 0. How to read this audit

**Important limitation.** The only artifact supplied is a *design document*. No source code, sample data, dashboard, README, or use-case document was provided. Therefore:

- **"Implementation"** = what `12_FINAL_SOLUTION.md` specifies.
- **"Demonstrable?"** = does the design define a concrete scenario or measurement that could show this requirement once built? **No requirement is runnable today**, because nothing has been built yet. Every "Yes" below means "demonstrable by design, pending implementation".
- **"Missing?"** = required by the Master Brief and absent from the design.
- **"Partial?"** = present but under-specified, unmeasurable, or not on the build plan.
- **Severity scale:**
  - **CRITICAL**: a mandatory Master Brief item is absent, undefined, or not on the build plan. Submission would be non-compliant.
  - **MEDIUM**: mandatory item is present but under-specified enough that an implementer could build it non-compliantly.
  - **MINOR**: requirement is satisfied; wording, labelling, or precision gap.
  - **NONE**: satisfied by design.

### Scorecard

| ID | Requirement | Status | Severity |
|---|---|---|---|
| R01 | Temperature | Satisfied (design) | NONE |
| R02 | Pressure | Satisfied (design) | MINOR |
| R03 | Humidity | Satisfied (design) | NONE |
| R04 | Real-time operation | Partial | MEDIUM |
| R05 | Temporal patterns | Satisfied (design) | MINOR |
| R06 | Seasonal patterns | Partial | MEDIUM |
| R07 | Spikes | Satisfied (design) | NONE |
| R08 | Frozen values | Satisfied (design) | NONE |
| R09 | Communication failures | Partial | MEDIUM |
| R10 | Multivariate consistency | Partial | MEDIUM |
| R11 | Genuine weather events | Partial | MEDIUM |
| R12 | Sensor/data anomaly distinction | Satisfied (design) | NONE |
| R13 | Confidence | Partial | MEDIUM |
| R14 | Explainability | Satisfied (design) | MINOR |
| R15 | Root cause | Satisfied (design) | MINOR |
| R16 | Sensor health | Partial | MEDIUM |
| R17 | Degradation | Partial | MEDIUM |
| R18 | Maintenance | Partial | MEDIUM |
| R19 | Correction (optional) | Satisfied (design) | NONE |
| R20 | Visualization | Designed, **not on build plan** | CRITICAL |
| R21 | Scalability | Partial | MEDIUM |
| R22 | Practical deployment | Partial | MEDIUM |
| R23 | Edge / energy | Partial | MEDIUM |
| R24 | Executable code | **Missing** | CRITICAL |
| R25 | Example usage | **Missing** | CRITICAL |
| R26 | Documentation / use cases | **Missing** | CRITICAL |
| X01 | Severity definition (Brief 5.2, Rule 8) | **Missing** | CRITICAL |
| X02 | Alerts (Brief 5.1) | Partial | MEDIUM |
| X03 | Dataset + injection protocol (Brief 3.4, 11.12) | **Missing** | CRITICAL |
| X04 | Stream/data assumptions (Brief 3.4) | Partial | MEDIUM |
| X05 | Reference SIH example (55 °C, neighbours normal) | Partial | MEDIUM |
| X06 | Core mechanism specification (tracker, adjudicator, envelope) | Partial | MEDIUM |
| X07 | Rule 15 labelling (mandatory vs implementation-specific) | Partial | MINOR |
| X08 | Document hygiene | Partial | MINOR |

---

## 1. Per-requirement audit

### R01 — Temperature (°C)

| Field | Finding |
|---|---|
| Requirement | Temperature (°C) is a mandatory core input (Brief 3.1, Rule 1). |
| Implementation | `temperature` float, °C, "Mandatory core input" in the Input Schema. Requirement matrix row "Temperature input". |
| Demonstrable? | Yes, by design: live/replay schema; Scenarios 1 and 2 exercise T. Not yet runnable. |
| Missing? | No. |
| Partial? | No. |
| Severity | NONE |
| Exact Fix | None. Build the schema exactly as specified. |

### R02 — Atmospheric Pressure (hPa)

| Field | Finding |
|---|---|
| Requirement | Atmospheric pressure (hPa) is a mandatory core input. |
| Implementation | `pressure` float, hPa, mandatory in the Input Schema. Optional `elevation` is listed "for network normalization". |
| Demonstrable? | Yes, by design (Scenario 1 references abnormal pressure behaviour). |
| Missing? | No. |
| Partial? | Minor gap: the design never states whether `pressure` is station-level pressure or sea-level-reduced pressure. This changes the meaning of every pressure residual and any network comparison. |
| Severity | MINOR |
| Exact Fix | Add one line to the Input Schema: "`pressure` is [station-level / MSLP] in hPa; this is an implementation assumption." If MSLP is used, state where the reduction happens and that it uses only T, P and the optional elevation metadata. |

### R03 — Relative Humidity (%)

| Field | Finding |
|---|---|
| Requirement | Relative humidity (%) is a mandatory core input. |
| Implementation | `relative_humidity` float, %, mandatory. Saturation/quantization is acknowledged in Scenario 3 and Failure mode 6. |
| Demonstrable? | Yes, by design (Scenarios 1, 3, 6). |
| Missing? | No. |
| Partial? | No. |
| Severity | NONE |
| Exact Fix | None. |

### R04 — Real-time operation

| Field | Finding |
|---|---|
| Requirement | Real-time / streaming detection; an offline-only implementation is insufficient (Brief 4.1, 9.4, Rule 11). Real-time claims need demonstrated latency/throughput (Claims We Must Not Make). |
| Implementation | Fast path / slow diagnostic path / slow health path; latency to be reported as p50/p95/p99, throughput, memory, queue depth; "bounded in-process/event-time stream". |
| Demonstrable? | Partly. A latency measurement plan exists (Handoff item 29). No stream simulator, replay-rate control, or ingestion entry point is specified. |
| Missing? | Nothing named in the Handoff phases creates the streaming ingestion loop, its replay driver, or the latency harness as deliverables. FastAPI is in the stack but appears in no phase. |
| Partial? | Yes. "Real-time" is asserted by architecture but the streaming interface (generator, endpoint, or queue) is not defined. |
| Severity | MEDIUM |
| Exact Fix | Add to Phase 1: (a) a `StreamReplayer` that emits observations one at a time at a configurable rate, (b) a single ingest entry point (`process_observation(obs) -> Decision`) used by both replay and FastAPI, (c) a latency harness recording ingest→provisional alert, ingest→final diagnosis, and health-update time. Report only measured numbers. |

### R05 — Temporal patterns

| Field | Finding |
|---|---|
| Requirement | Account for how an observation relates to historical behaviour, not just an instantaneous value (Brief 4.3, 11.4). |
| Implementation | Level 2 learned predictor uses recent lags and trend; episode evidence tracks trajectory (spike returns, step persists, drift directional). |
| Demonstrable? | Yes, by design (Scenarios 2, 5; step/drift/spike replay). |
| Missing? | No. |
| Partial? | Minor: the diurnal (time-of-day) component is not named explicitly. Only "calendar/season features" appear. |
| Severity | MINOR |
| Exact Fix | In Level 2, list the calendar features explicitly: hour-of-day, day-of-year (or equivalent). One sentence. |

### R06 — Seasonal patterns

| Field | Finding |
|---|---|
| Requirement | Account for normal seasonal patterns (Brief 4.4, 11.4). |
| Implementation | "Seasonal/calendar baseline features" in the compact gradient-boosted predictor; "seasonal residual analysis" in the statistical stack. Matrix: "Held-out chronology". |
| Demonstrable? | Only if the dataset covers at least one full annual cycle and the test period spans a different season from training. Neither is guaranteed: Tier A dataset is unselected (see X03). |
| Missing? | No seasonal-specific evaluation and no minimum-history rule for seasonal features. |
| Partial? | Yes. Cold-start handling covers short history but does not say when seasonal terms are enabled or what happens for a station with under one year of data. |
| Severity | MEDIUM |
| Exact Fix | (1) State the minimum history required before seasonal features are trusted, and the fallback below it (link to `COLD_START`). (2) Add one evaluation slice: test data from a season not seen in training, plus a season-transition period, reported separately. (3) Add a demo scenario showing the same value judged normal in one season and suspect in another. |

### R07 — Spikes

| Field | Finding |
|---|---|
| Requirement | Detect abnormal spikes; define how represented, detected, reported (Brief 4.2). |
| Implementation | Classes `IMPULSIVE_SPIKE`, `REPEATED_SPIKE`; residual/rate evidence; episode logic (returns toward baseline). Scenario 2. Injection family 1 and 2. |
| Demonstrable? | Yes, by design (Scenario 2). |
| Missing? | No. |
| Partial? | No. |
| Severity | NONE |
| Exact Fix | None. Thresholds are implementation parameters; document them in config. |

### R08 — Frozen / stuck values

| Field | Finding |
|---|---|
| Requirement | Detect frozen/stuck values using temporal analysis, not range checks (Brief 4.2, 11.6). |
| Implementation | Level 1 flatline plus `FROZEN_STUCK` in Level 3; "resolution-aware run-length/flatness"; compare with other variables still moving; unresolved when quantization or saturation applies. Scenario 3. |
| Demonstrable? | Yes, by design (Scenario 3, including the quantized-flat false-positive stress test). |
| Missing? | No. |
| Partial? | No. Depends on instrument-resolution assumptions, which are covered under X04. |
| Severity | NONE |
| Exact Fix | None beyond X04. |

### R09 — Communication failures

| Field | Finding |
|---|---|
| Requirement | Detect/handle communication errors and distinguish them from meteorological anomalies: missing, malformed, delayed, repeated/stale data (Brief 4.2, 11.5). |
| Implementation | Level 1 deterministic integrity layer: schema, cadence, missing expected timestamps, duplicates, late/out-of-order, malformed, repeated values. Classes `MISSING_EXPECTED_RECORD`, `COMMUNICATION_GAP`, `DUPLICATE`, `DELAYED_OR_OUT_OF_ORDER`, `MALFORMED_RECORD`. Scenario 4, Scenario 8. |
| Demonstrable? | Yes for gaps (Scenario 4). Not for stale/repeated data. |
| Missing? | The rule that separates a **stale/retransmitted packet** (communication) from a **single frozen channel** (sensor) is not specified. Brief 11.5 lists "repeated/stale data" as a communication symptom. The design lists "repeated/stuck values" under Level 1 integrity and `FROZEN_STUCK` under Level 3 without separating them. Also, `MISSING_EXPECTED_RECORD` vs `COMMUNICATION_GAP` are not defined apart from each other. |
| Partial? | Yes. |
| Severity | MEDIUM |
| Exact Fix | Add a short disambiguation rule set: (a) all three channels identical to the previous record **and** timestamp/sequence repeated or non-advancing → communication stale/duplicate; (b) one channel flat while the others move → `FROZEN_STUCK` on that channel; (c) all channels flat for a long window with no timestamp fault → `UNRESOLVED` (do not force). Define `MISSING_EXPECTED_RECORD` (a single expected slot absent) vs `COMMUNICATION_GAP` (N consecutive absent slots, N configurable). |

### R10 — Multivariate consistency (T, P, RH)

| Field | Finding |
|---|---|
| Requirement | Analyse consistency among T, P, RH so that jointly inconsistent observations are caught even when each value passes a static threshold (Brief 4.5, 11.3, Rule 5). |
| Implementation | Level 2 predictors use cross-variable T/RH/P history; Evidence B compares joint residuals and derived thermodynamic coupling; class `MULTIVARIATE_INCONSISTENCY`. The only covariance-aware method (robust covariance, B2) appears in the baseline ladder, not in the final architecture's Level 2/3. |
| Demonstrable? | Partly. Matrix: "Coupled and incoherent traces". |
| Missing? | The final system's mechanism for **concurrent** joint inconsistency (e.g., T and RH at the same timestamp jointly implausible) is not specified. Cross-variable *history* as predictor inputs does not by itself test same-time joint plausibility. |
| Partial? | Yes. |
| Severity | MEDIUM |
| Exact Fix | State explicitly in Level 2/3 that the residual **vector** (T, RH, P) is scored jointly (for example a robust covariance/Mahalanobis-type distance on standardized residuals) in addition to per-channel residuals, and that `MULTIVARIATE_INCONSISTENCY` fires from that joint score. Keep derived thermodynamic terms labelled as soft evidence and as derived features. |

### R11 — Genuine weather events

| Field | Finding |
|---|---|
| Requirement | Do not treat every unusual value as faulty; a rare value must not be labelled sensor failure without contextual evidence; design around genuine unusual weather (Brief 4.6, 9.5, 11.1, Rule 6). |
| Implementation | Hypothesis set includes `NORMAL/REGIME` and `WEATHER_LIKE`; final states `WEATHER_SUPPORTED`, `MIXED_WEATHER_AND_FAULT`, `UNRESOLVED`; explicit `WAIT/ABSTAIN`; Scenarios 6, 7, 9; genuine-event hard negatives in evaluation; gate-censoring failure mode acknowledged. |
| Demonstrable? | Design defines scenarios; realism depends on data. |
| Missing? | No source of genuine-event hard negatives is identified. The design itself says event labels may be "surrogate" only. No minimum count or definition of a "genuine event" for the benchmark. |
| Partial? | Yes. The protection principle is fully designed; its **evidence base** is not. |
| Severity | MEDIUM |
| Exact Fix | Add to the evaluation section: (1) how genuine-event periods are identified (operational records, documented storm/heatwave/cold-front dates, or surrogate injection) and who labels them; (2) a minimum number of hard-negative episodes; (3) report false-fault rate on them separately from clean-data false alarms; (4) if only surrogates exist, say so in every result table. |

### R12 — Sensor/data anomaly distinction

| Field | Finding |
|---|---|
| Requirement | Distinguish genuine meteorological events from sensor/data anomalies, and communication/data-pipeline problems from atmospheric behaviour where possible (Brief 4.6, 11.5). |
| Implementation | Three-layer separation: deterministic transport/integrity classes (Level 1), observation-behaviour classes (Level 3), attribution states (`WEATHER_SUPPORTED`, `SENSOR_FAULT_SUPPORTED`, `MIXED…`, `UNRESOLVED`, `UNKNOWN/UNMODELED`). Communication faults are explicitly "not mislabeled as ML discoveries". |
| Demonstrable? | Yes, by design (Scenarios 4, 6, 8). |
| Missing? | No. Stale-vs-frozen ambiguity is tracked in R09. |
| Partial? | No. |
| Severity | NONE |
| Exact Fix | None. |

### R13 — Confidence

| Field | Finding |
|---|---|
| Requirement | Every detected anomaly has a confidence score whose meaning, scale and interpretation are documented; not decoration (Brief 4.7, 5.3, 11.8). |
| Implementation | "Decision confidence = empirical reliability of the current decision route at the chosen evidence horizon on held-out evaluation data." Six separate stored quantities: `anomaly_score`, `fault_evidence_score`, `decision_confidence`, `severity`, `uncertainty_interval`, `calibration_status`. Reliability/risk–coverage plots planned. |
| Demonstrable? | Semantically defined; numerically unproven. The evidence-card example shows "[measured after evaluation]". |
| Missing? | (1) No numeric scale is stated. (2) No statement of which confidence the user sees: detection ("is this observation bad?") or attribution ("is the cause X?"). (3) No rule for provisional alerts issued **before** calibration exists. (4) No statement that calibration on injected data is not field reliability. |
| Partial? | Yes. |
| Severity | MEDIUM |
| Exact Fix | Document: `decision_confidence ∈ [0,1]`, defined as the empirical accuracy of decisions of the same route, evidence horizon, and class among held-out injected-data decisions in the same calibration bin. Report **two** user-facing values: detection confidence and attribution confidence. Label provisional alerts `confidence: UNCALIBRATED (provisional)`. Add the sentence "calibrated on anomaly-injected data; not field-validated." Keep the other stored scores as internal diagnostics. |

### R14 — Explainability

| Field | Finding |
|---|---|
| Requirement | Human-readable reasoning for why an observation was anomalous (Brief 4.8, 5.7). SHAP/LIME are preferred but not mandatory (Brief 6.1, Rule 2). |
| Implementation | Native evidence card (raw, expected, residual, temporal behaviour, multivariate evidence, hypothesis gained/lost support, uncertainty, versions). Worked examples for spike and drift. SHAP optional for the compact ML predictor (Phase 5, item 32). |
| Demonstrable? | Yes, by design (Page 3 evidence card, Page 5 episode replay). |
| Missing? | No. |
| Partial? | Minor: the matrix promises a "Fidelity test" but the Evaluation Methodology lists no explainability metric. The PS states SHAP/LIME are preferable, and Explainability carries 10% of the score, yet the only SHAP mention is a Phase 5 optional item. |
| Severity | MINOR |
| Exact Fix | (1) Add one explainability check to the metrics: e.g., "evidence card cites the true injected channel and fault family in X% of correctly detected injected faults" (X measured, not assumed). (2) Keep SHAP optional per Rule 2, but keep it in Phase 5 with a stated intent to include one feature-attribution view for the ML predictor if time allows. |

### R15 — Root cause

| Field | Finding |
|---|---|
| Requirement | Classify a probable root cause category, distinct from mere detection; probabilistic, not definitive; cover the PS-required fault types (Brief 4.9, 5.4, 11.7). |
| Implementation | Hierarchical classes: transport/integrity, observation-behaviour, attribution/uncertainty; channel attribution `T/RH/P/MULTI/UNKNOWN`; `UNKNOWN_UNMODELED`; confusion matrix including `UNKNOWN/ABSTAIN`; no physical component claims. |
| Demonstrable? | Yes, by design (fault-family demo, confusion matrix). |
| Missing? | No. |
| Partial? | Minor: the Brief names "sensor faults/malfunctions" as a required category. The design decomposes it into `STEP_BIAS`, `GRADUAL_DRIFT`, `NOISE_INCREASE`, `CORRUPTED_VALUE`, `COMBINED_FAULT` but never states the mapping, so a reviewer cannot see where "sensor malfunction" is reported. |
| Severity | MINOR |
| Exact Fix | Add a small mapping table: PS category → design classes. Example: spikes → `IMPULSIVE_SPIKE`, `REPEATED_SPIKE`; frozen/stuck → `FROZEN_STUCK`; communication errors → the five transport classes; sensor faults/malfunctions → `STEP_BIAS`, `GRADUAL_DRIFT`, `NOISE_INCREASE`, `CORRUPTED_VALUE`, `MULTIVARIATE_INCONSISTENCY`, `COMBINED_FAULT`. |

### R16 — Sensor health

| Field | Finding |
|---|---|
| Requirement | Maintain a sensor health status with documented semantics (Brief 4.10, 5.6, Rule 9). |
| Implementation | Longitudinal state `HEALTHY / WATCH / DEGRADED / REVIEW_REQUIRED / UNKNOWN`, based on episodes, persistence, channel residual bias, variance change, recurrence, divergence, quarantine frequency. Separate model/baseline integrity state. |
| Demonstrable? | Yes, by design (long replay; Page 1 and 2 health trajectory). |
| Missing? | The Brief requires the **semantics** to be documented. The design names five states but does not define what each means, what moves a sensor between them, or the minimum evidence for `DEGRADED`/`REVIEW_REQUIRED`. Health is also not stated per-channel vs per-station. |
| Partial? | Yes. |
| Severity | MEDIUM |
| Exact Fix | Add a state table: state → meaning → entry condition → exit condition → whether a single anomaly can trigger it (must be "no", per Brief 11.10). State whether health is kept per channel (T, RH, P) with a station roll-up. |

### R17 — Degradation

| Field | Finding |
|---|---|
| Requirement | Address sensor degradation with early-warning indications of declining reliability, built from evidence over time, not one anomaly (Brief 4.11, 11.10, Rule 10). |
| Implementation | Change-point evidence, slope of unexplained reference/tracker divergence, channel-specific persistence, variance growth, quarantine fraction. Outputs `NO_DEGRADATION_EVIDENCE`, `POSSIBLE_DEGRADATION`, `PERSISTENT_DEGRADATION_REVIEW` with horizon, calibration state, uncertainty, affected channel. No RUL. |
| Demonstrable? | Yes, by design (Scenario 5 drift replay; "Long-horizon evaluation"). Evidence is synthetic drift only. |
| Missing? | No thresholds, minimum observation horizon, or drift-rate range for validation. The design itself notes supplied drift rates are "not established as physically realistic". |
| Partial? | Yes. |
| Severity | MEDIUM |
| Exact Fix | (1) State the minimum evidence horizon before `POSSIBLE_DEGRADATION` may be issued (ties to `COLD_START`). (2) Name the change-detection method(s) in use (the stack mentions EWMA/CUSUM). (3) Evaluate on drift replays across several drift rates and report warning lead time and false-warning rate, stating "synthetic drift; not field-validated". (4) Keep the "indication, not prediction of failure date" wording. |

### R18 — Maintenance

| Field | Finding |
|---|---|
| Requirement | Provide an evidence-based maintenance indication, not a guaranteed decision (Brief 4.12, 5.8). |
| Implementation | Maintenance indication block with priority, affected channel, evidence horizon, reasons, suggested action; explicit list of things not claimed. |
| Demonstrable? | Yes, by design (drift/recurrence demo). |
| Missing? | Trigger rule is not stated (which health/degradation state emits an indication). Only one priority value (`REVIEW`) is shown; no priority scale. |
| Partial? | Yes. |
| Severity | MEDIUM |
| Exact Fix | Map maintenance priority to health/degradation state, e.g. `WATCH` → no action / monitor, `DEGRADED` → `REVIEW`, `REVIEW_REQUIRED` → `PRIORITY_REVIEW`. Define each priority in one line. Keep the suggested-action list generic (inspect/calibrate/verify) and label it as a recommendation. |

### R19 — Correction / imputation (OPTIONAL)

| Field | Finding |
|---|---|
| Requirement | Optional. If implemented, estimated values must be clearly marked and never silently replace the original (Brief 5.9, 11.13, Rule 3). |
| Implementation | Raw observation immutable; estimated value and uncertainty stored in separate fields; no correction for ambiguous cases; validated on masked regions. |
| Demonstrable? | Yes, by design (gap/spike correction demo). |
| Missing? | No. |
| Partial? | No. |
| Severity | NONE |
| Exact Fix | None. Keep it out of the critical path (already stated). |

### R20 — Visualization / dashboard

| Field | Finding |
|---|---|
| Requirement | Mandatory dashboard showing incoming observations, anomaly status, severity/confidence, sensor health, explanations/diagnostics (Brief 4.15, 5.5, Rule 13). |
| Implementation | Five Streamlit + Plotly pages: network overview, station detail, evidence card, learning provenance, episode replay. Content coverage matches Brief 4.15. |
| Demonstrable? | Yes, by design. |
| Missing? | **The Handoff to Next Agent (Phases 1–5) contains no dashboard task.** Dashboard, FastAPI, README, and use-case document appear in no phase. Phase 2 (quarantine, rollback, provenance) precedes everything user-facing. |
| Partial? | The design is complete; the **build plan** omits it. |
| Severity | CRITICAL |
| Exact Fix | Add a dashboard item to the Handoff (recommended: end of Phase 3, before Phase 4 evaluation), with Pages 1–3 and 5 as the compliance minimum and Page 4 (provenance) as supporting. State that the dashboard reads the same decision record used by the API. |

### R21 — Scalability

| Field | Finding |
|---|---|
| Requirement | Design so the concept extends from one station to a network (Brief 4.13, 9.10, Rule 12). Claims need a credible architecture and/or evidence. |
| Implementation | Per-station state; independent processing; horizontal workers by station; network layer conditional and bounded; no Kafka/Kubernetes for the prototype. |
| Demonstrable? | Partly. Matrix says "Load test"; Handoff item 29 measures latency/throughput/memory but does not say it is run across many stations. |
| Missing? | (1) No multi-station load test defined. (2) SQLite is the only store yet horizontal workers are proposed; SQLite has a single-writer constraint, and no migration/sharding note is given. (3) One gradient-boosted model per station per variable raises training/memory cost as stations grow; no shared or fallback model is mentioned. |
| Partial? | Yes. |
| Severity | MEDIUM |
| Exact Fix | (1) Add a load-test script driving N synthetic stations and report throughput and memory at several values of N (measured only). (2) State the store scaling path in one paragraph (e.g., one DB file per worker/partition for the prototype; a server database if needed later) and label it a design note, not a tested claim. (3) State the per-station model memory/training assumption and the fallback for new stations (already `COLD_START`). |

### R22 — Practical deployment

| Field | Finding |
|---|---|
| Requirement | Address practical deployability including the real-time operational setting and resource/deployment considerations (Brief 4.14, 9.11, Rule 12). |
| Implementation | Python 3.11, NumPy/Pandas/SciPy/scikit-learn, FastAPI/Pydantic, SQLite, Streamlit/Plotly, pytest, optional Docker; fallback hierarchy (Levels 0–4); cold start; local buffering. |
| Demonstrable? | Yes, by design ("Clean local deployment"). |
| Missing? | No resource assumptions (CPU/RAM per station or per worker, expected cadence, expected station count). No setup instructions or dependency pinning is planned. |
| Partial? | Yes. |
| Severity | MEDIUM |
| Exact Fix | Add a "Deployment assumptions" block: assumed cadence, assumed stations for the demo, measured CPU/RAM from the load test, connectivity assumptions, and how the system behaves under intermittent links (already partly covered by local buffering). Pin dependencies (`requirements.txt`) and add a single-command run instruction. |

### R23 — Edge / energy considerations

| Field | Finding |
|---|---|
| Requirement | Energy efficiency is an evaluation criterion (5%). If edge deployment is proposed, compute, memory, latency and energy assumptions must be addressed (Brief 6.2, 9.11). ESP32 is a suggestion only (Rule 2). |
| Implementation | Edge is a "screening node": schema, sequence, cadence, range, small residual features, spike/freeze suspicion, buffering. Server does the rest. No ESP32 energy/latency claim without measurement. Edge prototype is Phase 5 optional. |
| Demonstrable? | No. Only "Board demo if implemented". |
| Missing? | The design proposes an edge role but states no compute/memory/latency/energy **assumptions** (target MCU class, RAM/flash budget, sampling interval, transmit interval, payload size). The Brief requires these to be addressed when edge is proposed. |
| Partial? | Yes. The no-unsupported-claims discipline is correct; the assumptions are absent. |
| Severity | MEDIUM |
| Exact Fix | Add an "Edge budget" table of **declared assumptions** (labelled assumptions, not results): target device class, RAM/flash budget, per-observation operations for each screening check, buffer size, and transmit interval. Provide a reference implementation of the edge screening checks with fixed-size buffers, and report **server-side CPU time per observation** as a proxy. State plainly that no ESP32 energy or latency figure exists until measured on a board. |

### R24 — Executable code

| Field | Finding |
|---|---|
| Requirement | Fully executable code (Brief 4.16, 9.8, Rule 14). |
| Implementation | None supplied. `12_FINAL_SOLUTION.md` is a design and handoff; it names a stack and five build phases. |
| Demonstrable? | No. |
| Missing? | Yes: all code. |
| Partial? | No. |
| Severity | CRITICAL |
| Exact Fix | Implement per the Handoff, and add the following to the plan so the code is verifiably executable: repository layout, `requirements.txt`, one entry point that runs the full replay end-to-end on bundled sample data, and `pytest` tests that run without network access. Do not describe the system as "implemented" or "working" in any document until this passes on a clean environment. |

### R25 — Example usage

| Field | Finding |
|---|---|
| Requirement | Example usage must be included (Brief 4.16, 5.10, 9.8, Rule 14). |
| Implementation | None supplied. Nine live-demo scenarios are described as narratives, with no commands, inputs or expected outputs. |
| Demonstrable? | No. |
| Missing? | Yes: runnable examples, bundled sample data, expected outputs. |
| Partial? | The scenarios are a good source but are not usage examples. |
| Severity | CRITICAL |
| Exact Fix | Add a Handoff item producing `examples/`: one script per scenario (1–9), each with a small deterministic input file, the exact command, and the expected decision record. Include one API call example and one dashboard launch command. Scenario 1 must use the PS example (see X05). |

### R26 — Documentation / use cases

| Field | Finding |
|---|---|
| Requirement | A document explaining various use cases (Brief 4.16, 5.10, 9.9, Rule 14). |
| Implementation | Only "documented use cases" listed under Mandatory Features. No documentation task in any phase. |
| Demonstrable? | No. |
| Missing? | Yes: README, use-case document, configuration/parameter documentation, glossary of outputs (severity, confidence, health, root-cause classes). |
| Partial? | The scenarios and evidence-card examples can seed the content. |
| Severity | CRITICAL |
| Exact Fix | Add a Handoff item producing `README.md` (install, run, test) and `docs/USE_CASES.md` covering at least: spike, frozen sensor, communication failure, sensor drift with maintenance indication, genuine weather event, ambiguous event, cold-start station, network-unavailable operation. Include an output glossary that defines severity, confidence, health, and root-cause classes (see X01, R13, R16). |

---

## 2. Additional mandatory items not on the request checklist

### X01 — Severity definition

| Field | Finding |
|---|---|
| Requirement | A severity indication for each anomaly; the implementation must document how severity is determined and what each level means (Brief 5.2, Rule 8, 11.9). Severity and confidence must not be conflated. |
| Implementation | Matrix: "Magnitude × duration × criticality rule". Decision record has `severity`. The evidence-card example shows `SEVERITY: HIGH`. |
| Demonstrable? | Matrix promises "High vs low severity cases" but no levels or rule exist to demonstrate. |
| Missing? | Levels, per-level meanings, and the exact rule. "Criticality" is undefined. It is unclear what it measures, and if it depends on downstream-use metadata (station importance), that is an input outside the three core variables and the three permitted metadata fields. |
| Partial? | The name and one phrase exist; nothing else. |
| Severity | CRITICAL |
| Exact Fix | Define a level scale (for example 4 levels) with a one-line meaning each, and an explicit rule computing it from measured quantities that exist in the system: deviation magnitude relative to the expected envelope, persistence/duration, and number of channels affected. Remove "criticality" unless it is defined and explicitly labelled an implementation-specific, optional, configurable station attribute. Add one worked example showing high severity with low confidence, and one showing low severity with high confidence, to show the two concepts are separate. |

### X02 — Alerts

| Field | Finding |
|---|---|
| Requirement | Real-time anomaly alerts (Brief 5.1). The PS example expects the system to "generate an alert, and suggest corrective action" (Brief section 2). |
| Implementation | "Immediate provisional alert" from the fast path; statuses `SUSPECT`, `FAULT_SUPPORTED`, etc.; evidence card; maintenance block with suggested action. |
| Demonstrable? | Partly (Scenario 1 expected flow ends at quarantine and an optional estimate). |
| Missing? | No alert object/schema; no distinction between provisional and confirmed alerts in the output; no per-alert **suggested corrective action** (only in the long-horizon maintenance block); no de-duplication for a long-running episode. Three overlapping enumerations exist (attribution states, decision states, root-cause classes) with no single output schema tying them together. |
| Partial? | Yes. |
| Severity | MEDIUM |
| Exact Fix | Define one `Alert` record: station, timestamp, alert stage (`PROVISIONAL` / `CONFIRMED` / `ABSTAINED`), decision state, root-cause class, channel, severity, detection confidence, attribution confidence, one-line evidence summary, `suggested_action`, episode ID. State that repeated observations inside one open episode update the same alert rather than creating new ones. |

### X03 — Dataset and injection protocol

| Field | Finding |
|---|---|
| Requirement | Evaluate on anomaly-injected data or a documented equivalent; define injected types, how injection is done, which observations are ground-truth anomalous, and which metrics are computed; accuracy claims need a defined protocol (Brief 7, 10.1, 11.12, Rule 16). |
| Implementation | 14 injection families listed; two-tier plan (historical archive + synthetic replay); metric list; chronological splits; injector-family holdout; baseline ladder B0–B8. |
| Demonstrable? | No. No dataset is selected ("must not claim a specific source is available until confirmed"). |
| Missing? | (1) No dataset. (2) No injection parameters (magnitude, duration and onset ranges, per-family recipes). (3) No ground-truth labelling rule (for example, which points in a drift ramp count as anomalous, and from when). (4) No numeric acceptance targets for false alarms or detection delay, which Brief 9.6 and 11.12 imply must at least be reported. |
| Partial? | The metric list and split rules are good; the concrete protocol is missing. |
| Severity | CRITICAL |
| Exact Fix | Produce an `evaluation_protocol` section or file containing: the chosen dataset (source, station count, cadence, licence, missingness, units) or, if none is confirmed, an explicitly documented synthetic-clean-base fallback labelled as such; a table of injection recipes (family, channel, magnitude range, duration range, onset rule, random seed); the ground-truth labelling rule per family; and the metrics to be reported. Any result must be stated as "evaluation on anomaly-injected data shows…". |

### X04 — Stream/data assumptions

| Field | Finding |
|---|---|
| Requirement | Explicit assumptions on sampling frequency, missing, malformed, delayed, duplicated records, and unavailable metadata (Brief 3.4). Do not assume a dataset format unless documented as an implementation choice. |
| Implementation | "The stream contract declares expected cadence"; integrity checks cover missing/malformed/duplicate/late; bounded watermark; optional location/elevation; network unavailable states. |
| Demonstrable? | Partly. |
| Missing? | The design never states the assumed cadence, the watermark size, the expected instrument resolution (needed for `FROZEN_STUCK`), or the plausible sensor ranges used in the range check. The dataset format is not documented as an implementation choice. |
| Partial? | Yes. |
| Severity | MEDIUM |
| Exact Fix | Add a "Stream contract" table of assumed values labelled **implementation choice**: cadence, allowed lateness, gap length N, per-channel resolution, per-channel physical range, timestamp timezone, and input file format/column names. |

### X05 — Reference SIH example

| Field | Finding |
|---|---|
| Requirement | The PS example: a station reports about 55 °C with very high humidity and abnormal pressure variation while neighbours stay normal; the system should analyse temporal **and spatial** consistency, identify a probable sensor anomaly, alert, and suggest corrective action (Brief section 2). |
| Implementation | Scenario 1 lists temporal + multivariate evidence, quarantine and an optional estimate. Network context is optional and Phase 5. |
| Demonstrable? | Temporal and multivariate parts, yes. The spatial part cannot be demonstrated as specified. |
| Missing? | Scenario 1 never includes neighbours, although the PS example does. The design's rule "network disagreement is never automatic fault evidence" is correct, but the headline example must still show the spatial evidence being used as supporting context. |
| Partial? | Yes. |
| Severity | MEDIUM |
| Exact Fix | Rewrite Scenario 1's input to include several simulated neighbouring stations with normal readings, and show the evidence card listing "neighbours normal" as **supporting** evidence and `NETWORK_UNRESOLVED` as the fallback when neighbours are absent. Keep it labelled contextual evidence (Brief 11.11). Move a minimal network-context demo out of the pure-optional Phase 5 so the reference example can run; the full network layer can remain optional. |

### X06 — Core mechanism specification

| Field | Finding |
|---|---|
| Requirement | AI/ML-based detection (Brief 10.1); algorithm choices "justified against the requirements" (Brief 6.3); detection mechanism must be implementable. |
| Implementation | Gradient-boosted regressors for T/RH/P with an "uncertainty envelope"; `REFERENCE_v` and `TRACKER_t`; "compact hypothesis-evidence scorer". |
| Demonstrable? | Not until specified. |
| Missing? | (1) How a gradient-boosted regressor is "adaptively updated only from admitted observations". Standard gradient-boosted models are not incremental, so the tracker mechanism is undefined. (2) How the uncertainty envelope is produced. (3) What the hypothesis-evidence scorer actually computes (rule scores, likelihood ratios, a small classifier?). (4) What "suspicion trigger" opens an episode. |
| Partial? | Yes. These are the core of the design and are described only by name. |
| Severity | MEDIUM |
| Exact Fix | Add a short "Mechanism specification" subsection stating, for each of REFERENCE, TRACKER, envelope, trigger and scorer, the concrete method and update rule, and label each as an implementation choice. Do not add new components; only fix which of the already-named ones is used and how it updates. |

### X07 — Rule 15 labelling

| Field | Finding |
|---|---|
| Requirement | Improvements must be labelled required-by-PS, suggested, optional, or implementation choice; invented requirements must not be presented as official SIH26073 requirements (Brief Rule 15). |
| Implementation | The Complete Requirement Matrix marks many rows "MANDATORY", including raw-data preservation, model versioning, decision provenance, cold start, model fallback, network-unavailable fallback, data-leakage prevention, independent injector testing, genuine-event hard negatives, quantization awareness, unknown-anomaly handling, and "explicit abstention — MANDATORY SAFETY FEATURE". These are good engineering practices, but they are **not** in the Master Brief's mandatory list (Brief 10.1). |
| Demonstrable? | Not applicable. |
| Missing? | The distinction between PS-mandatory and design-mandatory. |
| Partial? | Yes. |
| Severity | MINOR |
| Exact Fix | Add a column "Source" to the matrix with values `PS-MANDATORY`, `PS-SUGGESTED`, `PS-OPTIONAL`, `IMPLEMENTATION CHOICE`, and relabel the rows above as `IMPLEMENTATION CHOICE`. |

### X08 — Document hygiene

| Field | Finding |
|---|---|
| Requirement | Accuracy and precision of claims (Brief 9.7, Rule 16). |
| Implementation | (a) Stray, unresolved citation markers appear in the text (for example after the Final Project Concept, the Master Brief citation lines, and the Controlled Synthesis Record). (b) The header says "implementation-ready concept". (c) `elevation` is added to the optional metadata; the Brief permits station ID, timestamp and location. |
| Demonstrable? | Not applicable. |
| Missing? | Clean references; a precise status. |
| Partial? | Yes. |
| Severity | MINOR |
| Exact Fix | (a) Remove or replace the broken citation markers with plain file/section references. (b) Change "implementation-ready" to "design-complete; not implemented; open items listed in `13_REQUIREMENT_AUDIT.md`" until the CRITICAL items are closed. (c) Describe `elevation` as location-derived context metadata and note it is not a meteorological input. |

---

# CRITICAL MISSING REQUIREMENTS

1. **R24 — Executable code.** Nothing exists yet. The Handoff must add packaging (`requirements.txt`, single end-to-end entry point, tests).
2. **R25 — Example usage.** No commands, inputs, sample data, or expected outputs. Scenarios 1–9 are narratives only.
3. **R26 — Documentation / use cases.** No README and no use-case document, and no phase creates them.
4. **R20 — Visualization / dashboard.** Fully designed (five pages) but **absent from all five Handoff phases**; it must be scheduled.
5. **X01 — Severity.** Mandatory output whose levels, meanings and rule are undefined; "criticality" is an undefined term that may imply an unpermitted input.
6. **X03 — Dataset and injection protocol.** No dataset selected; no injection parameters; no ground-truth labelling rule. Blocks the seasonal, accuracy and hard-negative evidence.

# MEDIUM ISSUES

1. **R04** Real-time: no streaming interface, replay driver, or latency harness in the build plan.
2. **R06** Seasonal: no minimum-history rule and no cross-season evaluation slice.
3. **R09** Communication: no rule separating stale/retransmitted packets from a frozen single channel; `MISSING_EXPECTED_RECORD` vs `COMMUNICATION_GAP` undefined.
4. **R10** Multivariate: no explicit joint (concurrent) T/RH/P residual scoring in the final architecture.
5. **R11** Genuine events: no source, count, or labelling policy for hard negatives.
6. **R13** Confidence: no numeric scale, no single user-facing definition, no rule for pre-calibration provisional alerts, no "injected-data, not field-validated" statement.
7. **R16** Sensor health: five states named but their semantics and transitions undefined.
8. **R17** Degradation: no minimum horizon, thresholds, or drift-rate range for validation.
9. **R18** Maintenance: trigger rule and priority scale undefined.
10. **R21** Scalability: no multi-station load test; SQLite versus horizontal workers unresolved; per-station model cost unaddressed.
11. **R22** Practical deployment: no resource or deployment assumptions; no setup instructions.
12. **R23** Edge / energy: edge role proposed with no compute/memory/latency/energy assumptions.
13. **X02** Alerts: no alert schema, no provisional/confirmed stage, no per-alert suggested action, three overlapping enumerations.
14. **X04** Stream assumptions: cadence, resolution, ranges, watermark and file format not stated.
15. **X05** Reference SIH example: Scenario 1 omits the neighbouring-station element of the PS example.
16. **X06** Core mechanisms: tracker update rule for gradient-boosted models, uncertainty envelope, hypothesis scorer and episode trigger unspecified.

# MINOR ISSUES

1. **R02** State whether pressure is station-level or sea-level-reduced.
2. **R05** Name hour-of-day and day-of-year explicitly as calendar features.
3. **R14** Add an explainability metric to the evaluation; keep one SHAP/LIME view in Phase 5 given the PS preference and the 10% weight.
4. **R15** Add a mapping from PS fault categories to design classes (notably "sensor faults/malfunctions").
5. **X07** Relabel design-added "MANDATORY" rows as `IMPLEMENTATION CHOICE` (Rule 15).
6. **X08** Remove stray citation markers; replace "implementation-ready" wording; describe `elevation` as location-derived context metadata.

# REQUIREMENTS FULLY SATISFIED

Satisfied at design level with no gap that changes compliance (runnable proof still depends on R24–R26):

- **R01 Temperature** input and schema.
- **R03 Relative humidity** input and schema.
- **R07 Spikes**: classes, evidence logic, Scenario 2, injection families.
- **R08 Frozen/stuck values**: temporal, resolution-aware, Scenario 3.
- **R12 Sensor/data anomaly distinction**: separation of transport, observation-behaviour and attribution layers.
- **R19 Correction/imputation (optional)**: raw preserved, estimate stored separately, no correction when ambiguous (Brief 11.13).
- **Core-input constraint (Brief 3.1, 9.1, 9.2, Rule 1)**: only T/P/RH; wind, rain, solar, gust, visibility explicitly excluded; derived features labelled as derived.
- **Genuine-event protection principle (Brief 9.5, Rule 6)** and **false-alarm awareness (Brief 9.6)**: designed and carried into the metric list (false positives on clean data and on hard negatives). The evidence base is tracked under R11.
- **Prohibited-claims discipline (Brief "Claims We Must Not Make")**: no violation found; latency, energy, scalability and novelty are all stated as pending measurement, and self-healing, RUL and guaranteed maintenance are explicitly refused.
- **Degradation as indication, not prediction of failure date (Brief 11.10)**: correctly framed; only its thresholds are open (R17).
- **Satisfied with a minor note:** R02, R05, R14, R15 (see the Minor list).

---

## Recommended closing order (compliance only, no redesign)

1. Close the six CRITICAL items in the design: add dashboard, documentation, examples and packaging to the Handoff; define severity; define the dataset and injection protocol.
2. Close the MEDIUM specification gaps (X06, X04, X02, R09, R10, R16–R18) before coding starts, since they change what gets built.
3. Build and measure, then re-run this audit against the **code** and update every "Demonstrable?" cell from "by design" to "run".

Until step 3 is complete, no document should state that any requirement is implemented, working, measured, or validated.

**HANDOFF:** the next agent must treat the CRITICAL list above as blocking, and must not present any MEDIUM item as resolved without a corresponding change in the design or code.
