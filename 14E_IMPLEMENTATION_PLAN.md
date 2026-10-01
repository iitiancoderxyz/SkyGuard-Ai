# 14E_IMPLEMENTATION_PLAN — SIH26073

## Implementation Role

This document converts the approved TRUST-TWIN architecture into one sequential, quota-efficient implementation roadmap for Google Antigravity Free.

### Source authority

Use this order during implementation:

1. `12_FINAL_SOLUTION.md` — final architecture and non-negotiable decisions.
2. `14_SYSTEM_ARCHITECTURE.md` — master implementation architecture, runtime behavior, technology stack, and dependency order.
3. `13_REQUIREMENT_AUDIT.md` — compliance gaps and blocking fixes.
4. `14A_DATA_PIPELINE.md` — data contract, ingestion, replay, storage, simulator, and pipeline tests.
5. `14B_ML_PIPELINE.md` — ML/statistical component specification and evaluation details.
6. `14C_UI_SPEC.md` — dashboard and operator interaction specification.
7. `14D_DEMO_PLAN.md` — judge-facing scenarios and demonstration verification.

`12_FINAL_SOLUTION.md` and `14_SYSTEM_ARCHITECTURE.md` are immutable source-of-truth files. Lower-level documents may expand them but must not redesign them. In particular, the MVP must remain T/P/RH-only at the meteorological input boundary, station-first, local/reproducible, and free of unnecessary Kafka/Kubernetes/GNN/transformer/foundation-model infrastructure.

---

# Implementation Dependency Graph

```text
PROJECT SETUP
    │
    ├── backend shell ──────────────┐
    ├── frontend/dashboard shell ──┤
    └── config + dependencies      │
                                   ▼
                           DATA CONTRACTS
                                   │
                                   ▼
                    INGESTION + INTEGRITY GATE
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
              RAW/PROCESSED                 STREAM REPLAY
                 STORAGE                  + FAULT SIMULATOR
                    │                             │
                    └──────────────┬──────────────┘
                                   ▼
                       PREPROCESS + FEATURES
                                   │
                                   ▼
                 REFERENCE + ADAPTIVE TRACKER
                                   │
                                   ▼
                    FAST ANOMALY EVIDENCE
                                   │
                                   ▼
                        EPISODE MANAGER
                                   │
                                   ▼
                    SEQUENTIAL ADJUDICATOR
                                   │
                 ┌─────────────────┼─────────────────┐
                 ▼                 ▼                 ▼
             ROOT CAUSE       WEATHER VS        CONFIDENCE /
             CLASSIFICATION   SENSOR            UNCERTAINTY
                 │                 │                 │
                 └─────────────────┼─────────────────┘
                                   ▼
                      EXPLANATION + EVIDENCE
                                   │
                                   ▼
                        SENSOR HEALTH STATE
                                   │
                           ┌───────┴───────┐
                           ▼               ▼
                      DEGRADATION    MAINTENANCE
                           │
                           ▼
                  OPTIONAL SAFE CORRECTION
                                   │
                                   ▼
                          FASTAPI + SSE
                                   │
                                   ▼
                     DASHBOARD + SIMULATOR
                                   │
                                   ▼
                        EVALUATION LAB
                                   │
                                   ▼
                     END-TO-END / FINAL QA
```

### Dependency rules

- No learned model is connected to live learning before admission/quarantine provenance exists.
- No health/maintenance output is treated as authoritative before longitudinal logic is tested.
- No dashboard feature becomes the inference source; the dashboard reads backend decisions.
- Ground truth is evaluation-only and never enters the runtime detector.
- Training and calibration remain off the realtime path.
- Optional network context can enrich a station decision but must never block station-local processing.
- Correction/imputation never overwrites raw observations.

---

# Recommended Project Directory

```text
sih26073/
├── app/
│   ├── api/
│   ├── core/
│   ├── config/
│   └── runtime/
├── ingestion/
│   ├── adapters/
│   ├── schemas/
│   ├── integrity/
│   └── replay/
├── features/
│   ├── temporal/
│   ├── seasonal/
│   ├── multivariate/
│   └── lineage/
├── detection/
│   ├── reference/
│   ├── tracker/
│   ├── triggers/
│   ├── episodes/
│   └── adjudication/
├── attribution/
│   ├── weather/
│   ├── sensor/
│   ├── network/
│   └── uncertainty/
├── health/
│   ├── sensor_health/
│   ├── degradation/
│   └── maintenance/
├── correction/
│   └── optional/
├── storage/
│   ├── repositories/
│   ├── migrations/
│   └── db/
├── simulator/
│   ├── stream/
│   ├── scenarios/
│   └── replay/
├── injector/
│   ├── faults/
│   ├── weather_surrogates/
│   └── manifests/
├── eval/
│   ├── metrics/
│   ├── baselines/
│   ├── calibration/
│   ├── robustness/
│   └── load/
├── dashboard/
│   ├── views/
│   ├── components/
│   └── stream/
├── models_store/
│   ├── reference/
│   ├── tracker/
│   ├── classifiers/
│   └── calibration/
├── data/
│   ├── replay/
│   ├── simulated/
│   └── ground_truth/
├── scripts/
├── examples/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── behavioral/
│   ├── invariants/
│   ├── contract/
│   └── browser/
├── docs/
├── requirements.txt
├── requirements-optional.txt
├── Makefile
└── Dockerfile
```

---

# PHASE 1 — FOUNDATION + DATA

## Purpose

Create the runnable deterministic substrate: project setup, backend/frontend shells, SQLite database, canonical schemas, immutable raw storage, ingestion/integrity gate, AWS simulator, replay, bounded realtime stream, and fault injection.

## Input specification files

- `12_FINAL_SOLUTION.md`
- `13_REQUIREMENT_AUDIT.md`
- `14_SYSTEM_ARCHITECTURE.md`
- `14A_DATA_PIPELINE.md`
- relevant simulator/API sections of `14C_UI_SPEC.md` and `14D_DEMO_PLAN.md`

## Files/folders to create

- Repository tree from the recommended directory.
- `requirements.txt`, optional dependency file, local configuration.
- FastAPI/Uvicorn application shell.
- Pydantic canonical observation schemas.
- SQLite/WAL initialization and repositories.
- Raw, processed, quality, station, and operational entities.
- Event-time station state/buffer structures.
- Shared processing contract.
- Replay engine.
- Deterministic AWS simulator.
- Fault-injection engine and ground-truth manifest format.
- Initial pytest suite.
- Minimal dashboard shell that proves backend connectivity only.

## Files to modify

None of the seven specification files. Only newly created implementation/test/config files are modified in this phase.

## Dependencies

None. This is the root phase and must finish before Phase 2.

## Implementation tasks

1. Create the Python 3.11+ environment and pin only the required prototype stack: NumPy, Pandas, SciPy, scikit-learn, FastAPI, Pydantic, Uvicorn, Streamlit, Plotly, pytest.
2. Implement the canonical fields exactly: `station_id`, `timestamp`, `temperature`, `pressure`, `relative_humidity`, optional location/elevation metadata, `source_type`, and optional source sequence.
3. Preserve `received_at`, ingestion sequence, payload hash, parse status, schema/normalization/processor versions as ingestion metadata.
4. Persist the original payload before downstream processing. Raw data is immutable.
5. Implement explicit states for malformed, missing, duplicate, conflicting duplicate, stale/retransmitted, delayed, out-of-order, range-invalid, and communication-gap conditions.
6. Center all live/replay/simulation/API processing on `process_observation(observation) -> processing_result / decision`.
7. Build deterministic replay with time range, station subset, replay rate, seed/run ID, and reproducible arrival ordering.
8. Build the AWS simulator for clean T/P/RH streams and transport faults.
9. Build injection families for spike, repeated spike, step/bias, drift, freeze/stuck, noise, missing/communication failure, duplicate/delay, and malformed/corrupt data.
10. Record onset/offset, parameters, seed, and scenario ID in a sidecar manifest; never pass the manifest to detection.
11. Expose one ingestion API and a minimal event stream. Do not add a broker.
12. Add example input and a minimal local run path.

## Tests

- Schema/type/range validation.
- Observation-ID determinism.
- Raw-data immutability.
- Cadence, expected-slot, duplicate, delay, and ordering tests.
- Replay determinism and identical-seed determinism.
- Live/replay use the same processing function.
- Ground-truth isolation.
- Fault-injection onset/offset correctness.
- Bounded-stream startup/shutdown and reconnection behavior.
- SQLite rebuild from a clean state.

## Expected outputs

A local system that can ingest one observation, preserve it, classify integrity, store it, replay it, simulate it, inject deterministic faults, and expose basic backend/stream status without any ML dependency.

## Acceptance criteria

- Clean T/P/RH observation completes end-to-end.
- Malformed observation is retained and classified.
- Missing/duplicate/delayed/out-of-order conditions are deterministic.
- Raw records never change after downstream processing.
- Replay and live paths use the same engine.
- Simulator output is reproducible from seed/configuration.
- Ground truth is separate from runtime detection.
- FastAPI starts cleanly.
- Bounded stream starts/stops cleanly.
- Phase 1 tests pass.

## Stop condition

**STOP PHASE 1** when this is reproducible without ML:

```text
payload → raw record → integrity gate → processed record → storage → replay/simulation
```

Do not proceed while ordering, raw immutability, replay determinism, or ground-truth isolation is broken.

---

# PHASE 2 — CORE INTELLIGENCE

## Purpose

Build preprocessing, feature engineering, the approved lightweight learned/statistical architecture, trusted reference, adaptive tracker, anomaly evidence, admission/quarantine, episode management, root-cause classification, weather-vs-sensor attribution, confidence, and uncertainty.

## Input specification files

- `12_FINAL_SOLUTION.md`
- `13_REQUIREMENT_AUDIT.md`
- `14_SYSTEM_ARCHITECTURE.md`
- `14A_DATA_PIPELINE.md`
- `14B_ML_PIPELINE.md`

## Files/folders to create

- `features/`
- `detection/reference/`
- `detection/tracker/`
- `detection/triggers/`
- `detection/episodes/`
- `detection/adjudication/`
- `attribution/weather/`
- `attribution/sensor/`
- `attribution/uncertainty/`
- training/calibration scripts and versioned artifact metadata
- baseline implementations and evaluation fixtures

## Files to modify

- Phase 1 processing engine.
- Station state objects.
- Decision and API schemas.
- Realtime event schemas.

## Dependencies

Complete Phase 1 only.

## Implementation tasks

1. Preprocess only T/P/RH plus time/context metadata, with explicit missingness and cold-start behavior.
2. Add hour-of-day and seasonal/day-of-year encodings, lags, rates, persistence/flatness, rolling robust statistics, residuals, and permitted T/P/RH-derived thermodynamic features.
3. Implement the approved lightweight prototype normality path: compact learned temporal/seasonal prediction plus transparent robust/statistical evidence.
4. Create versioned `REFERENCE_v` and `TRACKER_t` state objects.
5. Implement admission states `ADMIT`, `QUARANTINE`, `REJECT`, `UNKNOWN` with full provenance.
6. Ensure only admitted observations update the adaptive tracker.
7. Implement fast evidence for spike, freeze/stuck, bias/step, drift, noise, residual, and integrity failures.
8. Implement an episode manager with onset, affected channels, evidence window, provisional alert, updates, and closure.
9. Implement sequential adjudication with `DECIDE`, `WAIT`, `ABSTAIN`, `AMBIGUOUS`, `UNKNOWN_UNMODELED`, and `MIXED` outcomes.
10. Attribute weather vs sensor using temporal trajectory, joint T/P/RH consistency, reference-vs-tracker divergence, integrity evidence, and conditional network context only when resolvable.
11. Return `NETWORK_UNRESOLVED` when network coverage/timing is insufficient; never equate isolation with sensor failure.
12. Implement behavioral root-cause classes and an explicit unknown path.
13. Calibrate confidence on a held-out calibration set and keep confidence distinct from severity.
14. Implement uncertainty outputs and measure risk-coverage/abstention behavior.

### Conflict rule for `14B_ML_PIPELINE.md`

Where a lower-level ML prescription conflicts with the master architecture, the master architecture wins. Do not make a heavy deep sequence model, GNN, transformer, exact conformal guarantee, or other excluded component a mandatory MVP dependency merely because it appears in a subordinate specification.

## Tests

- Feature calculations and cold-start tests.
- Chronological train/validation/test separation and leakage tests.
- Deterministic artifact load/prediction tests.
- Admission/quarantine/tracker-provenance state tests.
- Rollback/replay tests.
- Episode lifecycle/state-machine tests.
- Weather-like hard negative versus sensor-fault tests.
- Network-unresolved/unavailable tests.
- Calibration/reliability/risk-coverage tests.
- Reproducibility of decisions from identical inputs/artifacts/seeds.

## Expected outputs

```text
processed T/P/RH
→ features
→ reference + tracker
→ fast evidence
→ episode
→ sequential adjudication
→ attribution
→ root cause
→ confidence / uncertainty
→ auditable decision
```

## Acceptance criteria

- Approved lightweight intelligence is active in runtime.
- Tracker updates only for admitted observations.
- Quarantined observations cannot silently poison adaptive state.
- Reference/tracker divergence is persisted.
- Episodes accumulate evidence.
- Explicit wait/abstain states work.
- Weather-vs-sensor can remain unresolved.
- Root cause includes unknown/unmodeled behavior.
- Confidence and uncertainty are separate.
- Held-out calibration artifacts are produced.
- Identical inputs/artifacts reproduce identical decisions.

## Stop condition

**STOP PHASE 2** only after this replay is reproducible:

```text
stable → slow drift → adaptive-learning pressure → quarantine → protected tracker → evidence episode → decide/wait/abstain
```

---

# PHASE 3 — TRUST + SENSOR HEALTH

## Purpose

Turn decisions into operational trust outputs: explainability, correction safeguards, sensor health, degradation indication, maintenance indication, provenance visibility, and fallback states.

## Input specification files

- `12_FINAL_SOLUTION.md`
- `13_REQUIREMENT_AUDIT.md`
- `14_SYSTEM_ARCHITECTURE.md`
- `14A_DATA_PIPELINE.md`
- `14B_ML_PIPELINE.md`

## Files/folders to create

- `health/sensor_health/`
- `health/degradation/`
- `health/maintenance/`
- evidence-card serializers/templates
- provenance query helpers
- correction eligibility module
- health/degradation evaluation utilities

## Files to modify

- Phase 2 decision/episode records.
- Storage repositories.
- API schemas/endpoints.
- Realtime event schema for health/maintenance updates.

## Dependencies

Requires Phase 2 decisions, episodes, provenance, confidence, and uncertainty.

## Implementation tasks

1. Create an evidence card for every non-normal decision: what happened, affected channel, temporal evidence, multivariate evidence, integrity evidence, reference/tracker comparison, network state, counter-evidence, decision state, confidence, uncertainty, and version metadata.
2. Keep SHAP/model attribution optional and subordinate to the native evidence card.
3. Build longitudinal sensor health using recurrence, persistence, residual behavior, reference/tracker divergence, and data-path behavior; a single unusual point must not equal long-term failure.
4. Build degradation as an indication, not a failure-date prediction.
5. Build maintenance as an evidence-based indication with affected channel, evidence horizon, reason, priority/state, and generic recommendation.
6. Keep correction/imputation optional and outside the critical path. Store estimate and uncertainty separately; never overwrite raw; do not correct unresolved cases.
7. Implement visible fallback states: network unavailable, model unavailable, cold start, and storage interruption.
8. Keep fallback behavior honest: no false confidence and no fabricated normal result.

## Tests

- Evidence cards match stored decision evidence.
- Explanation/version fields are correct.
- Clean long replay does not accumulate false degradation.
- Transient anomalies have bounded health impact.
- Persistent anomalies accumulate longitudinal evidence.
- Communication failures do not falsely degrade physical sensors.
- Maintenance transitions are deterministic and auditable.
- Correction never overwrites raw and never activates for unresolved cases.
- Fallback behavior is tested for each supported degraded mode.

## Expected outputs

Each operational episode has an auditable package containing anomaly decision, severity, confidence, uncertainty, explanation, root cause, health, degradation, maintenance indication, optional corrected estimate, and provenance.

## Acceptance criteria

- Every non-normal episode has a structured explanation.
- Health and degradation are longitudinal, not single-point labels.
- Maintenance is an indication/recommendation, not a guaranteed action.
- Raw data remain immutable.
- Unresolved cases remain unresolved rather than being auto-corrected.
- Fallback states are explicit and tested.
- Full operational decisions are queryable via API.

## Stop condition

**STOP PHASE 3** when one episode can be traced end-to-end:

```text
raw observation → anomaly evidence → adjudication → explanation → health → degradation → maintenance → provenance
```

---

# PHASE 4 — DASHBOARD + EVALUATION

## Purpose

Build the operational dashboard and evaluation laboratory on top of the stable API and decision records. The dashboard is a presentation layer, not a second inference engine.

## Input specification files

- `12_FINAL_SOLUTION.md`
- `13_REQUIREMENT_AUDIT.md`
- `14_SYSTEM_ARCHITECTURE.md`
- `14A_DATA_PIPELINE.md`
- `14B_ML_PIPELINE.md`
- `14C_UI_SPEC.md`
- `14D_DEMO_PLAN.md`

## Files/folders to create

- `dashboard/views/`
- `dashboard/components/`
- realtime stream UI handling
- simulator control UI
- anomaly/evidence inspector
- health/maintenance views
- episode replay view
- evaluation-lab view
- baseline comparison view
- evaluation metrics and load scripts
- browser tests and UI fixtures

## Files to modify

- API contracts/endpoints.
- SSE/event stream.
- Simulator/injection endpoints.
- Phase 1 dashboard shell.

## Dependencies

Requires complete Phase 3 backend outputs plus deterministic simulator, ground truth, and evaluation data paths.

## Implementation tasks

1. Implement the architecture-approved MVP dashboard stack from `14_SYSTEM_ARCHITECTURE.md`: Streamlit + Plotly + API-backed data. Do not replace the approved prototype stack with a separate frontend architecture.
2. Implement compliance views: network overview, station inspector, anomaly center, evidence/diagnostic inspector, sensor health, maintenance, episode replay, provenance support, and simulation/demo lab.
3. Show stream status, ingestion rate, active anomalies, severity, confidence, uncertainty, root cause, health, and explanations from backend responses.
4. Implement simulator controls for nominal, spike, bias/step, drift, stuck, communication outage, delayed/out-of-order, ambiguity/abstention, and compliant T/P/RH weather-surrogate scenarios.
5. Build the evaluation laboratory with clean baseline, anomaly injections, baseline ladder, chronological split, injector holdout, genuine-event hard negatives, unknown/unmodeled cases, poisoning experiment, calibration/risk-coverage, realtime benchmarks, and multi-station load.
6. Implement metrics for pointwise PR-AUC/precision-recall, F1, clean false positives, hard-negative false positives, event recall, detection delay, root-cause confusion including unknown/abstain, calibration error, risk-coverage, forced-label rate, health/maintenance errors, latency, throughput, memory, active episodes, and queue depth.
7. Implement browser checks for startup, navigation, realtime updates, anomaly details, explanation, health, simulator controls, replay/reset, and API failure/reconnect behavior.
8. Ensure no UI metric is fabricated or hard-coded as a measured result.

## Tests

- UI/API contract tests.
- Realtime reconnection tests.
- Simulator-control integration tests.
- Evaluation metric tests.
- Chronological split and leakage audit.
- Ground-truth isolation.
- Reproducibility by seed.
- Browser tests on a clean session.
- Increasing-station and increasing-stream-rate load tests.

## Expected outputs

- Operational dashboard.
- Simulation lab.
- Evaluation laboratory.
- Baseline comparison reports.
- Calibration/risk-coverage artifacts.
- Realtime performance measurements.
- Browser-verification evidence.
- Reproducible evaluation entry points.

## Acceptance criteria

- Dashboard reads backend truth.
- Simulator controls produce real backend events.
- Evidence, health, and maintenance are visible.
- Evaluation runs from a clean environment and fixed seed.
- Baseline comparison is reproducible.
- Genuine-event hard negatives are separate.
- Unknown/abstain behavior is measured.
- Poisoning experiment is runnable.
- Calibration/risk-coverage are runnable.
- Multi-station load results are recorded.
- Browser tests pass.
- No fabricated metrics appear in the UI.

## Stop condition

**STOP PHASE 4** when an operator can run:

```text
start stream → select station → inject scenario → observe live alert → inspect evidence → inspect confidence/uncertainty → inspect health → replay episode → open evaluation result
```

and the result is reproducible from the non-UI evaluation path.

---

# PHASE 5 — INTEGRATION + FINAL QA

## Purpose

Integrate every subsystem, execute end-to-end and adversarial tests, verify the browser experience, measure performance, verify demo scenarios, close compliance gaps, and make the repository handoff-ready.

## Input specification files

All seven specification files plus this plan and all implementation/test artifacts from Phases 1–4.

## Files/folders to create

Only final QA/release-support artifacts: reproducibility manifests, final runbook/checklists, benchmark output locations, and any regression tests discovered during integration.

## Files to modify

Existing implementation/test files only when fixing integration defects, plus README/use-case documentation, dependency pinning, demo configuration, and release scripts as needed.

`12_FINAL_SOLUTION.md` and `14_SYSTEM_ARCHITECTURE.md` must not be modified.

## Dependencies

Every preceding phase acceptance condition must already be green.

## Implementation tasks

1. Run one full end-to-end golden path:

```text
input → raw → validation → preprocess → features → reference/tracker → detection → episode → adjudication → attribution → confidence/uncertainty → explanation → health → degradation → maintenance → API → dashboard
```

2. Failure-test malformed input, duplicate/conflicting duplicate, delayed/out-of-order data, communication outage/backfill, network unavailable, model unavailable, storage interruption, cold start, ambiguous episode, unknown anomaly, repeated anomaly, and simultaneous station events.
3. Verify the repository does not introduce prohibited/unsupported additions: non-core meteorological inputs, GNN/transformer/foundation-model core, Kafka/Kubernetes, exact RUL, guaranteed maintenance, exact physical component diagnosis, correction of ambiguous events, or ground-truth runtime access.
4. Measure provisional-alert latency, final-diagnosis latency, p50/p95/p99, throughput, memory, queue depth, and active-episode scaling. Report the workload/configuration with every measurement.
5. Perform clean-browser verification: fresh startup, navigation, realtime stream, station detail, anomaly drill-down, explanation, health, maintenance, simulation, replay, and recovery after stream interruption.
6. Run the judge-facing scenarios from `14D_DEMO_PLAN.md`, using only implementation-compatible T/P/RH evidence at the detector boundary. Cover nominal, genuine weather/regime, spike, stuck, drift/bias, communication failure, T/P/RH multivariate inconsistency, high-confidence anomaly, ambiguous/abstain, poisoning, and network-unresolved behavior.
7. Verify documentation: setup, startup, dashboard, simulator, evaluation, tests, artifacts, limitations, claims discipline, demo runbook, and recovery.
8. Re-run `13_REQUIREMENT_AUDIT.md` against the actual implementation; unresolved items remain explicitly marked, never silently upgraded to complete.

## Tests

- Full unit/invariant/contract/integration/state-machine suite.
- Behavioral/evaluation suite.
- Load/performance suite.
- Browser suite.
- End-to-end golden replay.
- Ground-truth leakage test.
- Regression test for every defect fixed in Phase 5.

## Expected outputs

- Integrated runnable repository.
- Passing test suite.
- Reproducible demo.
- Measured performance report.
- Browser-verified dashboard.
- Updated requirement-audit evidence.
- Complete runbook and documentation.

## Acceptance criteria

- Golden replay passes.
- Major failure-mode tests pass.
- Architecture boundaries are intact.
- Browser verification passes.
- Simulator/dash/reset/replay procedures work from a clean environment.
- Performance measurements are captured for the tested workload.
- Requirement audit has runnable evidence for implemented requirements.
- README/example usage works from a fresh environment.
- Model/data artifacts are versioned and referenced by configuration.
- Unsupported accuracy, latency, energy, scalability, novelty, failure-date, physical-component, or maintenance-guarantee claims are absent.

## Stop condition

**STOP PHASE 5** only when the repository passes the Final Acceptance Criteria below and the full demo can be run from a clean local environment without architectural changes.

---

# Testing Strategy

## 1. Deterministic contract testing

Schema, event-time ordering, station state, immutability, replay determinism, and ground-truth isolation.

## 2. State-machine testing

Admission, quarantine, rejection, unknown, episode lifecycle, wait, abstain, ambiguous, network unresolved, cold start, and model-unavailable states.

## 3. Behavioral testing

Every major fault family gets normal and held-out parameterizations; report event-level metrics and detection delay.

## 4. Genuine-weather protection

Evaluate documented genuine-event hard negatives separately. Label T/P/RH-only weather surrogates as surrogates.

## 5. Poisoning test

Compare ordinary adaptive learning against protected TRUST-TWIN behavior on the predeclared poisoning failure mode.

## 6. Uncertainty testing

Calibration error, reliability, risk-coverage, abstention precision, forced-label rate, and time-to-abstain.

## 7. Long-horizon health testing

Clean long replay, drift replay, recurrence replay, false maintenance warnings, and missed degradation episodes.

## 8. Realtime testing

Provisional/final latency, p50/p95/p99, throughput, memory, queue depth, active episodes.

## 9. Multi-station testing

Increase station count, stream rate, and concurrent episodes while preserving station-local operation.

## 10. Browser/E2E testing

Clean-browser operator flow plus stream/API failure and recovery behavior.

---

# Antigravity Model Allocation

As of 29 September 2026, Google Antigravity's current free individual model catalog includes Gemini 3.8 Flash, Gemini 3.7 Flash, Gemini 3.6 Flash, Gemini 3.1 Pro, Claude Sonnet 4.6, Claude Opus 4.6, and GPT-OSS-120b. This plan intentionally uses Flash for routine implementation and Pro only for the hardest reasoning-heavy phases.

| Phase | Recommended model | Reasoning level | Primary use |
|---|---|---|---|
| Phase 1 | **Gemini 3.8 Flash** | Medium | Setup, schemas, storage, simulator, APIs, tests |
| Phase 2 | **Gemini 3.1 Pro** | High | ML architecture, admission/quarantine, sequential adjudication, calibration, evaluation |
| Phase 3 | **Gemini 3.8 Flash** | Medium | Explainability, health, degradation, maintenance, correction safeguards |
| Phase 4 | **Gemini 3.8 Flash** | Medium | Dashboard, simulator UI, metrics, browser tests |
| Phase 5 | **Gemini 3.1 Pro** | High | Cross-system integration, failure reasoning, regression diagnosis, final QA |

Avoid defaulting to Claude Opus or switching among several models inside one work package. Use a stronger model only when reasoning crosses subsystem boundaries, evaluation results conflict, or a final QA issue requires deep multi-file analysis.

---

# Free-Tier Quota Strategy

1. Use **one primary Antigravity implementation agent**.
2. Work through the five phases sequentially; do not split the same phase across many overlapping agents.
3. Keep one request focused on one coherent work package.
4. Run tests locally before using another agent turn to interpret failures.
5. Use Gemini Flash for deterministic coding and repetitive fixes.
6. Reserve Gemini Pro for Phase 2 and Phase 5 hard reasoning.
7. Keep the same model/context for closely related tasks; avoid repeated re-grounding.
8. At phase start, provide only the relevant source files plus this plan, current tree, and current test status.
9. Require explicit stop-condition checks at the end of each phase.
10. Do not ask agents to invent features to fill gaps; missing/unclear requirements must be handled by the master documents and this plan.

### Agent-count rule

Use **one active implementation agent at a time**. A second agent is appropriate only for an isolated review after the primary agent has stopped editing the reviewed area.

---

# Checkpoints

## Checkpoint A — Foundation locked

After Phase 1: data contract, raw storage, replay, simulator, integrity tests, and backend shell are stable.

## Checkpoint B — Core intelligence locked

After Phase 2: tracker protection, admission/quarantine, episode adjudication, confidence, uncertainty, and attribution are reproducible.

## Checkpoint C — Operational trust locked

After Phase 3: evidence cards, health, degradation, maintenance, provenance, and correction safeguards are stable.

## Checkpoint D — Evaluation/UI locked

After Phase 4: dashboard, simulator controls, evaluation laboratory, baseline comparison, performance metrics, and browser tests are operational.

## Checkpoint E — Release locked

After Phase 5: end-to-end, failure, browser, performance, demo, documentation, and requirement-audit gates all pass.

---

# Final Acceptance Criteria

The implementation is accepted only if all conditions are true:

1. Core detector boundary is Temperature, Pressure, Relative Humidity plus permitted metadata/context.
2. Raw observations are immutable.
3. Live and replay use one processing contract.
4. Missing, duplicate, delayed, malformed, and out-of-order conditions are explicit.
5. Simulator/injector is deterministic and ground truth never reaches runtime detection.
6. Trusted reference and adaptive tracker are both present.
7. Only admitted observations update the tracker.
8. Quarantined observations remain auditable and replayable.
9. Suspicious observations can enter episodes rather than being forced immediately into a cause.
10. `WAIT`, `ABSTAIN`, `UNKNOWN_UNMODELED`, `MIXED`, and `NETWORK_UNRESOLVED` are operationally usable.
11. Anomaly score, severity, confidence, and uncertainty are distinct.
12. Root-cause classification includes an unknown/unmodeled path.
13. Genuine-event hard negatives are evaluated separately.
14. Health and degradation are longitudinal.
15. Maintenance is an indication/recommendation, not a guarantee.
16. Correction never overwrites raw and does not act on unresolved cases.
17. Dashboard reads the same backend decision records exposed by the API.
18. Realtime performance is measured, not guessed.
19. Multi-station performance is measured under an explicit workload.
20. Baselines and TRUST-TWIN are compared under the same protocol.
21. Poisoning and risk-coverage experiments are runnable.
22. Browser verification passes on a clean run.
23. Major demo scenarios are reproducible from the simulator.
24. Example usage and use-case documentation work from a clean environment.
25. Unsupported accuracy/latency/energy/scalability/novelty and guarantee claims are absent.
26. `12_FINAL_SOLUTION.md` and `14_SYSTEM_ARCHITECTURE.md` are unchanged.

---

# Handoff to Antigravity

## What files should be given to Antigravity before the build begins?

Give Antigravity these seven source specifications before Phase 1:

1. `12_FINAL_SOLUTION.md`
2. `13_REQUIREMENT_AUDIT.md`
3. `14_SYSTEM_ARCHITECTURE.md`
4. `14A_DATA_PIPELINE.md`
5. `14B_ML_PIPELINE.md`
6. `14C_UI_SPEC.md`
7. `14D_DEMO_PLAN.md`

Also provide `14E_IMPLEMENTATION_PLAN.md`, the workspace/repository, and any approved dataset files when available.

Before coding, instruct Antigravity explicitly:

- Treat `12_FINAL_SOLUTION.md` and `14_SYSTEM_ARCHITECTURE.md` as immutable.
- Do not redesign the solution.
- Do not add non-core meteorological inputs to the detector.
- Do not create dozens of micro-phases.
- Use the five phases in this file sequentially.
- Use one implementation agent unless an isolated review task is justified.
- Stop at each phase's acceptance/stop condition.

## What files should each implementation phase read?

### Phase 1 — FOUNDATION + DATA

Read `12_FINAL_SOLUTION.md`, `13_REQUIREMENT_AUDIT.md`, `14_SYSTEM_ARCHITECTURE.md`, and `14A_DATA_PIPELINE.md`. Also read the relevant simulator/API parts of `14C_UI_SPEC.md` and `14D_DEMO_PLAN.md`.

### Phase 2 — CORE INTELLIGENCE

Read `12_FINAL_SOLUTION.md`, `13_REQUIREMENT_AUDIT.md`, `14_SYSTEM_ARCHITECTURE.md`, `14A_DATA_PIPELINE.md`, and `14B_ML_PIPELINE.md`.

### Phase 3 — TRUST + SENSOR HEALTH

Read `12_FINAL_SOLUTION.md`, `13_REQUIREMENT_AUDIT.md`, `14_SYSTEM_ARCHITECTURE.md`, `14A_DATA_PIPELINE.md`, and `14B_ML_PIPELINE.md`.

### Phase 4 — DASHBOARD + EVALUATION

Read all seven source specifications, with `14_SYSTEM_ARCHITECTURE.md` controlling runtime technology and `14C_UI_SPEC.md` controlling operator-facing behavior.

### Phase 5 — INTEGRATION + FINAL QA

Read all seven source specifications, this `14E_IMPLEMENTATION_PLAN.md`, all implementation files from Phases 1–4, all tests, and all benchmark/evaluation outputs.

## Final implementation rule

Build the smallest system that can demonstrate the approved TRUST-TWIN behavior end-to-end and measure it honestly.

The implementation is complete only when:

```text
DATA INTEGRITY
      +
TRUSTED ADAPTATION
      +
SEQUENTIAL DIAGNOSIS
      +
EXPLICIT UNCERTAINTY
      +
LONGITUDINAL HEALTH
      +
MEASURED EVALUATION
      +
REPRODUCIBLE DEMONSTRATION
```

all work together without violating the approved architecture.
