# 12_FINAL_SOLUTION — SIH26073

**Agent:** DECISION AGENT 12 — FINALARBITER  
**Date:** 29 September 2026  
**Decision type:** Final architecture selection and controlled synthesis  
**Status:** **FINAL ARCHITECTURE SELECTED — implementation-ready concept, empirical claims pending validation**

---

# Final Project Concept

## TRUST-TWIN: Quarantine-Gated Sequential Evidence Monitor for AWS

The final SIH26073 architecture is a **station-first, contamination-resistant anomaly detection system** built around a **trusted reference + adaptive tracker**, with a **lightweight sequential evidence adjudicator** for short-lived anomalies and an **optional conditional network-context layer** when multi-station evidence is actually resolvable.

The selected foundation is the **TWIN-CLOCK / dual-baseline architecture** because it addresses a failure mode that directly threatens the integrity of any adaptive AI system: a degrading sensor can teach the detector that faulty behavior is normal.

The foundation is repaired with only two justified additions:

1. **Sequential evidence adjudication** from RACE, used only for active anomaly episodes so the system can wait for evidence and abstain instead of forcing a diagnosis.
2. **Conditional network context** from the network-attribution family, used only when station coverage and timing are sufficient; network disagreement never becomes automatic evidence of sensor failure.

The final system deliberately does **not** combine every candidate idea. CONserve-style physics transformations, DEMIX, GNNs, conformal/Simes “guarantee” machinery, heavy deep sequence models, cryptographic novelty layers, exact RUL prediction, and automatic component-level maintenance actions are excluded from the core architecture unless later experiments prove a specific need.

The mandatory problem scope remains exactly the SIH26073 scope: **Temperature, Atmospheric Pressure, and Relative Humidity** as the core meteorological inputs. Timestamp, station ID, and location are contextual metadata; T/P/RH-derived quantities are labelled as derived features. fileciteturn0file0L15-L44

---

# One-Sentence Problem

AWS stations continuously produce Temperature, Pressure, and Relative Humidity observations, but faults such as spikes, freezes, drift, and communication errors can look like unusual weather, so the system must detect bad observations in real time without incorrectly rejecting genuine atmospheric events.

# One-Sentence Solution

**TRUST-TWIN** preserves raw observations, uses a versioned trusted reference to protect an adaptive ML baseline from poisoning, adjudicates suspicious episodes by accumulating temporal/multivariate evidence with explicit abstention, and optionally uses resolvable network context to distinguish regional weather from shared data failures.

---

# Core Innovation

The final innovation is a **trust-preserving decision loop**, not a new algorithm:

> **A trusted reference controls which observations are allowed to update an adaptive station model; suspicious observations enter an evidence-accumulation episode rather than being immediately assigned a fault cause; unresolved cases remain explicitly abstained; and every model update is provenance-traceable and reversible.**

This produces three behavior-level capabilities that are relevant to the SIH problem:

### 1. Learning without self-poisoning

A model is not allowed to silently learn from its own suspect observations.

The system maintains:

- `REFERENCE_v` — versioned, slower-changing reference;
- `TRACKER_t` — adaptive normal model updated only from admitted observations.

A suspicious observation can be quarantined without deleting it.

### 2. Diagnosis that can wait

A suspicious point produces an immediate provisional alert, but the system does not pretend that one observation always contains enough information to distinguish:

- spike,
- step/bias,
- drift,
- freeze,
- noise,
- genuine event,
- or unknown behavior.

The episode adjudicator accumulates evidence over subsequent observations and can return:

`DECIDE`, `WAIT`, `ABSTAIN`, or `AMBIGUOUS`.

### 3. Network evidence only when resolvable

Neighboring-station information is supporting context, not a mandatory truth source.

The system first checks whether:

- enough stations are available,
- timestamps are sufficiently precise,
- station geometry can resolve onset differences,
- and missingness is itself trustworthy.

If not, the system returns:

`NETWORK_UNRESOLVED`

and falls back to station-local evidence.

These choices are consistent with the project findings that common rules, Isolation Forest, LSTM/GRU autoencoders, SHAP, neighbor comparison, health scores, correction, dashboards, edge deployment, and generic hybrids are already crowded prior-art territory; differentiation therefore has to be behavioral and measured. fileciteturn0file1L12-L52

---

# Why Existing Approaches Are Insufficient

The project evidence does not justify building a “more sophisticated anomaly detector” merely because the task requests AI/ML.

## Rules alone

Range, step, persistence, duplicate, missingness, and similar rules are necessary and should remain in the system, but they cannot by themselves model seasonal behavior or determine whether a complex T/P/RH trajectory is an extreme event or a sensor fault.

## One adaptive model

A purely adaptive model can absorb a degrading sensor and slowly turn the fault into the new normal. This is the central model-poisoning problem identified throughout the supplied materials.

## Frozen baseline only

A frozen baseline avoids poisoning but can mistake legitimate regime changes, station changes, seasonal evolution, or long-term site changes for sensor degradation.

## Static anomaly score

A scalar anomaly score can answer “unusual or not,” but not reliably:

- whether a spike returns to baseline,
- whether a deviation persists,
- whether the other variables support the move,
- whether the cause is distinguishable,
- or whether the correct decision is to wait.

## Generic supervised fault classifier

Synthetic fault labels are labels for an injection mechanism, not proof of real physical failure. The supplied red-team reviews explicitly identify injector memorization and lack of real maintenance labels as major risks.

## Neighbor comparison alone

Spatial QC is already established. “No neighbor agrees” is not equivalent to “the station is faulty,” because genuine localized events exist and communication failures can be correlated.

## Generic explainability

SHAP or a feature importance chart can explain a model’s dependence on inputs, but it is not proof of a physical component failure. Explanations must present **evidence supporting a decision**, not causal certainty.

---

# What Is Actually Different

The final architecture differs from a standard “rules + ML + dashboard” stack in the **decision state machine** and **learning provenance**:

| Ordinary hybrid pipeline | TRUST-TWIN |
|---|---|
| Detector scores each point | Detector opens an evidence episode when justified |
| Adaptive model may learn from its own output | Reference-controlled admission prevents silent poisoning |
| One score often becomes one label | Decision can wait or abstain |
| “Confidence” is often an arbitrary number | Confidence has a defined calibration target |
| Health is a rolling score | Health is longitudinal evidence with model-integrity state |
| Neighbors can act as a hard rule | Network evidence is conditional and can return unresolved |
| Corrections may become replacement values | Raw and estimated values are schema-separated |
| Retraining is often opaque | Every admitted update is provenance-traceable and replayable |

The dual-baseline mechanism, sequential evidence logic, abstention, network context, health tracking, and dashboards are individually not claimed as universally novel. Only a **measured behavior improvement over strong baselines** can support the final differentiation claim.

---

# Complete System Architecture

```text
                        ┌──────────────────────────────┐
                        │  AWS STREAM: T / RH / P      │
                        │  + timestamp + station_id   │
                        │  + optional location         │
                        └──────────────┬───────────────┘
                                       │
                                       v
                    ┌─────────────────────────────────────┐
                    │ 1. INGESTION + INTEGRITY GATE       │
                    │ cadence / ordering / duplicates     │
                    │ missing / malformed / late data    │
                    └──────────────┬──────────────────────┘
                                   │
                    raw immutable  │  normalized stream
                    record         │
                                   v
                 ┌──────────────────────────────────────────┐
                 │ 2. FEATURE + CONTEXT LAYER               │
                 │ seasonal/time features                  │
                 │ lags / rates / persistence / flatness   │
                 │ T/RH/P derived thermodynamic features   │
                 │ robust residuals                         │
                 └──────────────┬───────────────────────────┘
                                │
                ┌───────────────┴────────────────┐
                v                                v
      ┌───────────────────┐            ┌─────────────────────┐
      │ 3A. REFERENCE     │            │ 3B. ADAPTIVE        │
      │ REFERENCE_v       │            │ TRACKER_t           │
      │ slow / versioned  │            │ admitted data only   │
      └──────────┬────────┘            └──────────┬──────────┘
                 │                                │
                 └───────────────┬────────────────┘
                                 v
                    ┌─────────────────────────────┐
                    │ 4. FAST DETECTION EVIDENCE  │
                    │ spike / freeze / step       │
                    │ noise / residual / integrity│
                    └────────────┬────────────────┘
                                 │
                          suspicion trigger
                                 v
                    ┌─────────────────────────────┐
                    │ 5. EPISODE MANAGER          │
                    │ OPEN -> UPDATE -> CLOSE     │
                    └────────────┬────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              v                  v                  v
        H_WEATHER          H_SENSOR_FAULT      H_UNKNOWN
        /regime            spike/step/drift    out-of-family
        hypothesis         freeze/noise
              \                  |                  /
               \                 |                 /
                └──────── sequential evidence ────┘
                                 │
                 ┌───────────────┼────────────────┐
                 v               v                v
               DECIDE           WAIT           ABSTAIN
                 │                                │
                 └───────────────┬────────────────┘
                                 v
                  ┌──────────────────────────────┐
                  │ 6. OPTIONAL NETWORK CONTEXT │
                  │ only if resolvability passes│
                  │ propagation / synchronization│
                  └────────────┬─────────────────┘
                               v
                 ┌──────────────────────────────┐
                 │ 7. DECISION + CONFIDENCE     │
                 │ severity / cause / uncertainty│
                 │ sensor health / maintenance   │
                 └─────────────┬────────────────┘
                               │
             ┌─────────────────┼─────────────────────┐
             v                 v                     v
        QUARANTINE        UPDATE TRACKER        NO CORRECTION
        /rollback         only when safe        if ambiguous
             │
             v
       versioned state
             │
             v
       Dashboard / API / audit record
```

The system is intentionally **station-first**. The network module is not a single point of failure for the whole submission.

---

# Input Schema

## Core meteorological fields

| Field | Type | Unit | Role |
|---|---|---|---|
| `temperature` | float | °C | Mandatory core input |
| `pressure` | float | hPa | Mandatory core input |
| `relative_humidity` | float | % | Mandatory core input |

## Context metadata

| Field | Type | Role |
|---|---|---|
| `timestamp` | datetime | Temporal ordering, seasonal context |
| `station_id` | string | Per-station state |
| `latitude` | float, optional | Network context |
| `longitude` | float, optional | Network context |
| `elevation` | float, optional | Network normalization/context |

Derived quantities such as:

- dew point,
- vapour pressure,
- mixing ratio,
- potential temperature,
- rate-of-change,
- lagged values,
- residuals,

are **derived features**, not additional meteorological inputs.

No wind, rainfall, solar radiation, visibility, soil moisture, wind gust, or similar variable is required by the core model.

---

# Data Pipeline

## Stage 1 — Ingestion contract

Every reading receives a stable observation identifier derived from station, timestamp, and ingestion sequence.

The stream contract declares expected cadence.

Communication failure is **not** inferred from a missing row without knowing that a row was expected.

## Stage 2 — Integrity checks

Deterministic processing handles:

- malformed records;
- impossible field formats;
- missing observations;
- missing expected timestamps;
- duplicate observations;
- delayed/out-of-order observations;
- cadence violations;
- repeated/stuck values;
- explicit sensor-range violations.

Communication and stream-integrity faults are therefore not mislabeled as ML discoveries.

## Stage 3 — Raw-data preservation

For every input:

```text
raw_observation
integrity_flags
processed_features
reference_version
tracker_version
decision_state
severity
confidence
root_cause_category
health_state
correction_estimate
correction_uncertainty
```

The raw observation is never overwritten.

## Stage 4 — Feature generation

Features are constructed only from:

- current T/RH/P;
- historical T/RH/P;
- timestamp;
- permitted metadata;
- T/RH/P-derived quantities.

Feature generation is deterministic and versioned.

---

# Detection Pipeline

The detection system uses **three levels of increasing cost**.

## Level 1 — Integrity

Fast deterministic processing:

- schema;
- cadence;
- missingness;
- duplicate;
- late record;
- flatline;
- obvious range/format issue.

## Level 2 — Learned normality

The station receives a learned seasonal/temporal normal model.

A practical MVP can use compact gradient-boosted regression models or similarly lightweight supervised predictors for T, RH and P using:

- calendar/season features;
- recent lags;
- recent trend;
- cross-variable T/RH/P history.

This satisfies the AI/ML requirement without requiring a large deep model.

The model outputs an expectation and uncertainty envelope.

## Level 3 — Active episode adjudication

A point becomes an **episode** only after a predefined suspicion trigger.

Each episode evaluates evidence for:

- `NORMAL/REGIME`
- `SPIKE`
- `STEP_BIAS`
- `GRADUAL_DRIFT`
- `FREEZE_STUCK`
- `NOISE_BURST`
- `WEATHER_LIKE`
- `UNKNOWN`

At each new sample the system asks:

> Has enough evidence accumulated to make a decision, or should it wait?

The system is not required to use a large Bayesian generative engine. A compact hypothesis-evidence scorer with held-out calibration is preferred for the first implementation.

---

# Weather-vs-Sensor Attribution

The key rule is:

> **Unusual does not mean faulty.**

Attribution uses multiple evidence types.

## Evidence A — Temporal trajectory

Examples:

- spike → returns toward baseline quickly;
- step → new stable level persists;
- drift → persistent directional movement;
- freeze → expected environmental movement continues but one signal remains effectively fixed;
- noise → variance increases without coherent displacement.

## Evidence B — Multivariate T/RH/P coherence

The system compares:

- joint residuals,
- cross-variable movement,
- derived thermodynamic coupling,
- and whether variables move consistently with the station’s learned normal regime.

Thermodynamic features are **soft evidence**, not universal physical rules.

## Evidence C — Reference vs tracker divergence

This is the main long-horizon evidence.

A legitimate regime shift may move both the tracker and the current observation away from an old reference.

A persistent channel-specific unexplained movement can instead support a sensor-degradation hypothesis.

## Evidence D — Optional spatial evidence

When a resolvable network is available:

- multiple stations changing in a coherent temporal sequence supports a regional weather interpretation;
- synchronized missing/delayed/duplicated changes support a shared data event;
- lack of propagation does **not** automatically mean sensor fault.

## Final attribution states

```text
WEATHER_SUPPORTED
SENSOR_FAULT_SUPPORTED
MIXED_WEATHER_AND_FAULT
UNRESOLVED
UNKNOWN/UNMODELED
```

---

# Fault Classification

The classification is hierarchical and deliberately does not claim physical component identity from T/RH/P alone.

## Transport/integrity classes

- `MISSING_EXPECTED_RECORD`
- `COMMUNICATION_GAP`
- `DUPLICATE`
- `DELAYED_OR_OUT_OF_ORDER`
- `MALFORMED_RECORD`

## Observation behavior classes

- `IMPULSIVE_SPIKE`
- `REPEATED_SPIKE`
- `STEP_BIAS`
- `GRADUAL_DRIFT`
- `NOISE_INCREASE`
- `FROZEN_STUCK`
- `CORRUPTED_VALUE`
- `MULTIVARIATE_INCONSISTENCY`
- `COMBINED_FAULT`

## Attribution/uncertainty classes

- `WEATHER_OR_REGIME`
- `MIXED`
- `UNKNOWN_UNMODELED`
- `UNRESOLVED`

Channel attribution may be:

`T`, `RH`, `P`, `MULTI`, or `UNKNOWN`.

Physical claims such as “replace Pt100 element” are excluded from the core output because T/P/RH alone generally cannot identify the exact hardware cause.

---

# Confidence Mechanism

Confidence is not a generic 0–100 score.

The system stores separate quantities:

```text
anomaly_score
fault_evidence_score
decision_confidence
severity
uncertainty_interval
calibration_status
```

## Decision confidence definition

For the final prototype:

> **Decision confidence = empirical reliability of the current decision route at the chosen evidence horizon on held-out evaluation data.**

Calibration is performed on data that are not used to tune the final test result.

Where formal conformal methods are used, the project will describe them as a calibration/evidence layer under their tested assumptions, **not** as a universal posterior probability of fault and not as an exact long-run guarantee.

## Abstention

Confidence does not have to be high enough to justify a forced class.

Outputs can remain:

`UNKNOWN / ABSTAIN`

and this is counted as a measured system outcome.

---

# Explainability

The system should explain every non-normal decision through an **evidence card**.

Example:

```text
STATION: AWS-012
STATUS: SUSPECT
PRIMARY EVIDENCE:
- Temperature residual increased sharply.
- RH and pressure did not show corresponding movement.
- Next two observations returned toward the previous baseline.
- Step-bias hypothesis lost support.
- Spike hypothesis gained support.
CONFIDENCE: calibrated decision reliability = [measured after evaluation]
SEVERITY: HIGH
ROOT-CAUSE CATEGORY: IMPULSIVE_SPIKE
MODEL VERSION: reference_07 / tracker_12
CORRECTION: not applied
```

For drift:

```text
- tracker/reference divergence persistent over long horizon;
- RH-specific residual bias increasing;
- T and P remain comparatively coherent;
-  observations during the suspect interval were quarantined;
- tracker was not updated from quarantined values;
RESULT: POSSIBLE_RH_DEGRADATION
```

The explanation is explicitly framed as **evidence supporting the decision**, not proof of physical causality.

SHAP may be added for the compact ML predictor if it improves explanation fidelity, but the native residual/evidence explanation remains primary.

---

# Sensor Health

Sensor health is a longitudinal operational state:

```text
HEALTHY
WATCH
DEGRADED
REVIEW_REQUIRED
UNKNOWN
```

Health is based on:

- repeated anomaly episodes;
- persistence;
- channel-specific residual bias;
- residual variance changes;
- recurrence;
- tracker/reference divergence;
- quarantine frequency;
- decision stability;
- and evidence consistency.

A single unusual value does not make a sensor “unhealthy.”

A separate **MODEL/BASELINE INTEGRITY state** records:

- reference version;
- tracker version;
- admitted sample count;
- quarantined sample count;
- rollback count;
- cold-start state;
- reference age.

This avoids confusing sensor health with model health.

---

# Degradation Prediction

The system provides **degradation indication**, not guaranteed remaining useful life.

The degradation layer monitors:

- slope of unexplained divergence;
- change-point evidence;
- persistence of channel-specific deviation;
- variance growth;
- repeated recalibration-like episodes;
- increasing quarantine fraction.

Possible outputs:

`NO_DEGRADATION_EVIDENCE`

`POSSIBLE_DEGRADATION`

`PERSISTENT_DEGRADATION_REVIEW`

The output includes:

- observation horizon;
- confidence/calibration state;
- uncertainty;
- affected channel;
- supporting evidence.

No exact failure date is produced unless future real maintenance/failure data justify such a model.

---

# Maintenance

Maintenance output is an **evidence-based indication**.

Example:

```text
MAINTENANCE INDICATION
Priority: REVIEW
Affected channel: RH
Evidence horizon: [measured period]
Reason:
- persistent unexplained RH divergence;
- repeated anomalous episodes;
- adaptive baseline quarantined suspect data.
Suggested action:
- inspect/calibrate RH sensor;
- verify installation/environment;
- compare against an independent reference if available.
```

The system must not claim:

- exact remaining life;
- guaranteed failure;
- exact spare part;
- guaranteed field action;
- automated dispatch as fact.

---

# Correction/Imputation

Correction is **optional**, not a core innovation.

When enabled:

1. raw observation remains untouched;
2. estimated replacement is stored separately;
3. uncertainty is stored;
4. cause/evidence supporting the estimate is stored;
5. ambiguous cases receive **no correction**.

## Safe correction targets

### Communication gaps

Optional temporal imputation can reconstruct missing values when sufficient history exists.

### Clearly isolated spikes

A local/model estimate may be produced when:

- the anomaly is isolated;
- neighboring temporal observations support the replacement;
- cause attribution is strong;
- and the correction method has passed evaluation.

### Stable single-channel drift

Optional correction may be used only when:

- the reference is trusted;
- the bias trajectory is stable;
- attribution is sufficiently specific;
- and correction error is validated.

## No correction

For:

- ambiguous weather/fault cases;
- unresolved regime shifts;
- unmodeled anomalies;
- network-unresolved events;
- low-confidence attribution.

These remain flagged rather than “fixed.”

---

# Uncertainty and Abstention

Uncertainty has first-class status.

The system can return:

```text
PASS
SUSPECT
FAULT_SUPPORTED
WEATHER_SUPPORTED
MIXED
WAIT
ABSTAIN
UNKNOWN_UNMODELED
NETWORK_UNRESOLVED
COLD_START
MODEL_UNAVAILABLE
```

## Abstention triggers

- out-of-family behavior;
- competing hypotheses remain close;
- insufficient future evidence;
- poor calibration regime;
- insufficient station history;
- reference is stale/untrusted;
- network geometry is not resolvable;
- model disagreement exceeds a predeclared threshold.

The project will measure **risk–coverage** so that abstention is treated as a controlled operating mode instead of hiding uncertain cases.

---

# Realtime Architecture

## Fast path

Runs for every observation:

```text
ingest
→ integrity
→ feature update
→ learned baseline residual
→ spike/freeze/step suspicion
→ provisional status
```

## Slow diagnostic path

Runs only for active episodes:

```text
episode state
→ sequential evidence update
→ weather/fault hypothesis update
→ confidence
→ final/abstain decision
```

## Slow health path

Runs over longer history:

```text
tracker/reference divergence
→ change-point
→ degradation evidence
→ maintenance indication
```

## Latency reporting

The system will report separate measured quantities for:

- ingest → provisional alert;
- ingest → final episode diagnosis;
- health/degradation update time.

No compute-latency claim will be presented as diagnosis latency.

Required measurements:

- p50;
- p95;
- p99 where practical;
- throughput;
- memory;
- queue depth under load.

---

# Scalability

The primary state is **per station**:

- model parameters;
- recent feature state;
- reference version;
- tracker state;
- admission counters;
- quarantine pointers;
- health state.

Stations can be processed independently.

A central service can horizontally scale workers by station.

The project does **not** require:

- Kubernetes;
- Kafka;
- distributed databases;
- graph neural networks;
- cloud infrastructure,

for the first reproducible implementation.

Those may be added later only if a measured workload requires them.

---

# Edge Strategy

The edge device is a **screening node**, not the full reasoning engine.

## Edge responsibilities

- packet/schema validation;
- timestamp sequence checks;
- cadence/heartbeat;
- simple range/format checks;
- small residual features;
- spike/freeze suspicion;
- local buffering during temporary connectivity loss.

## Server responsibilities

- reference/tracker management;
- episode adjudication;
- calibration;
- health/degradation;
- provenance;
- dashboard;
- optional network context.

No ESP32 energy or latency claim is made before board-level measurement.

If a chosen edge board cannot support the complete model, the system degrades gracefully to integrity + lightweight anomaly screening while preserving raw data for later server analysis.

---

# Dashboard

The dashboard is an operational view rather than a decorative chart.

## Page 1 — Network overview

Shows:

- station status;
- active anomaly episodes;
- health state;
- network/data-quality events;
- unresolved cases.

## Page 2 — Station detail

Shows:

- T/RH/P time series;
- expected/reference band;
- adaptive tracker;
- residuals;
- episode markers;
- health trajectory;
- quarantine periods.

## Page 3 — Evidence card

Shows:

- current decision;
- severity;
- confidence meaning;
- evidence supporting weather;
- evidence supporting fault;
- counterevidence;
- uncertainty;
- model/reference versions.

## Page 4 — Learning provenance

Shows:

- which records were admitted;
- which were quarantined;
- tracker version;
- reference version;
- rollback history.

## Page 5 — Episode replay

Shows the same event as a movie/replay:

`normal → suspicion → evidence accumulation → decision`

This is the main judge-facing demonstration.

---

# Dataset Strategy

The supplied data strategy proposes clean-state replay with synthetic injection, but the red-team review identifies important limitations:

- the dataset is not fully specified by source/cadence/licence;
- a curated clean archive can have survivorship bias;
- latent faults can exist in a “clean” set;
- supplied drift rates are not established as physically realistic;
- some taxonomy examples incorrectly depend on wind/rain/solar;
- the evaluator's injection mechanism is unknown.

Therefore the final benchmark has two tiers.

## Tier A — Historical T/P/RH archive

Use a documented, licensed historical dataset that meets the project’s observation requirements.

The selected dataset must document:

- source;
- station count;
- station identifiers;
- geographic coverage;
- timestamp resolution/cadence;
- missingness;
- units;
- licensing;
- known QC procedures.

The system must not claim a specific source is available until the source has been confirmed and documented.

## Tier B — Controlled synthetic replay

Use known clean segments plus deterministic fault injection.

The clean base is only a **normal-state approximation**.

It is not labelled as physically perfect ground truth.

## Genuine-event hard negatives

The evaluation should include real historically observed unusual periods where possible.

If the event label comes from manual/operational records, label it as such.

If the event is only a synthetic “front-like” surrogate, call it a **surrogate**, not proof of real-front generalization.

---

# Fault Injection

The supplied 14-class taxonomy is repaired to obey the T/P/RH boundary.

## Required injected behavior families

1. Isolated spike
2. Repeated spike
3. Sudden bias
4. Gradual drift
5. Frozen/flatline
6. Stuck-at value
7. Excessive noise
8. Missing observation
9. Communication failure
10. Duplicate
11. Delayed/out-of-order observation
12. Corrupted value
13. Multivariate inconsistency
14. Combined fault

## Important corrections to the inherited taxonomy

Out-of-scope examples involving:

- wind;
- wind direction;
- gust;
- rainfall;
- solar radiation;

must not enter the core model or core benchmark.

Injection generators must vary:

- magnitude;
- duration;
- onset;
- channel;
- multi-channel coupling;
- sampling interval;
- quantization;
- missingness;
- overlap.

The benchmark must include multiple independent generator recipes for major fault families.

---

# Evaluation Methodology

## Hard evaluation rules

### Chronological split

Use chronological train/validation/test splits.

Do not shuffle overlapping time windows across splits.

### Injector separation

Supervised diagnosis must be evaluated using a held-out injector family or independently generated fault recipe.

### Station separation where appropriate

For network components, use station holdouts or time-separated station evaluation.

### No test tuning

Thresholds, calibration, model selection, and event-label policies must be fixed before the final test.

---

## Baseline ladder

At minimum compare:

### B0 — Integrity rules

- range;
- cadence;
- missing;
- duplicate;
- order;
- flatline.

### B1 — Robust temporal statistics

- seasonal robust baseline;
- Hampel/MAD;
- change detection.

### B2 — Multivariate statistical baseline

- robust residuals;
- covariance-aware T/P/RH consistency.

### B3 — ML baseline

- compact learned temporal/seasonal predictor.

### B4 — Adaptive baseline

- naïve adaptive tracker.

### B5 — Trusted reference + periodic retraining

This tests whether TRUST-TWIN actually adds value over a simpler strategy.

### B6 — TRUST-TWIN

- reference;
- adaptive tracker;
- admission/quarantine;
- rollback.

### B7 — TRUST-TWIN + sequential episode adjudicator

The final architecture.

### B8 — Optional network context

Only tested where network data are available and resolvable.

---

## Required metrics

### Detection

- pointwise PR-AUC;
- thresholded F1;
- false positives on clean data;
- false positives on genuine-event hard negatives;
- event-level recall;
- detection delay.

### Persistent anomaly evaluation

For drift/bias/freeze:

- detection delay;
- event-level recall;
- false alarms per station-time.

### Root cause

Confusion matrix by behavioral class, including:

`UNKNOWN/ABSTAIN`.

Do not rely on a misleading flat 14-class macro-F1 when classes are observationally indistinguishable from T/P/RH.

### Uncertainty

- calibration error;
- reliability plots;
- risk–coverage;
- false forced-label rate;
- abstention precision;
- time-to-abstain.

### Health/degradation

- false maintenance warnings;
- missed degradation episodes;
- warning lead time where labels exist;
- no-fault-found rate where maintenance records exist.

### Realtime

- p50/p95/p99 latency;
- throughput;
- memory;
- active episode count;
- queue depth.

### Edge

When edge deployment is actually implemented:

- RAM;
- flash/model size;
- CPU utilization;
- energy per observation or per sustained interval;
- latency on the actual board.

---

# Live Demo Scenarios

## Scenario 1 — Required SIH example

One station suddenly reports an extreme temperature with unusual humidity/pressure behavior while surrounding stations are normal.

Expected demonstration:

```text
SUSPECT
→ temporal + multivariate evidence
→ sensor-fault-supported
→ behavioral root cause
→ confidence + severity
→ quarantine
→ optional safe estimate
```

No exact hardware component is named.

## Scenario 2 — Spike

One-point extreme T excursion followed by return.

Expected:

`IMPULSIVE_SPIKE`

with low information latency.

## Scenario 3 — Frozen sensor

T or RH remains effectively flat while the other variables and expected environmental variation continue.

The flatline detector is resolution-aware.

Expected:

`FROZEN_STUCK`

unless quantization/saturation makes the state unresolved.

## Scenario 4 — Communication failure

Expected timestamp does not arrive.

The integrity layer identifies:

`COMMUNICATION_GAP`

without waiting for ML.

## Scenario 5 — Adaptive baseline poisoning test

Replay:

`stable → slow drift → naïve adaptive baseline absorbs drift → TRUST-TWIN quarantines suspect observations`

The dashboard shows exactly which observations updated the tracker.

## Scenario 6 — Genuine regime shift

A long, coherent T/RH/P change.

Expected:

`WEATHER_OR_REGIME`

or `UNRESOLVED`, depending on evidence.

The key demonstration is **not incorrectly forcing a sensor fault**.

## Scenario 7 — Ambiguous event

Construct a case where weather and sensor hypotheses remain competitive.

Expected:

`WAIT → ABSTAIN`

rather than false certainty.

## Scenario 8 — Network data fault

Several stations experience synchronized missing/delayed observations.

Expected:

`SYNCHRONIZED_DATA_OR_TELEMETRY_EVENT`

with network-health evidence rising without falsely marking every station as physically degraded.

## Scenario 9 — Isolated genuine event

Only one station changes.

Expected:

`NO_NETWORK_CONFIRMATION`

rather than automatic sensor failure.

---

# Failure Modes

## Failure mode 1 — Wrong reference

If the reference archive contains latent faults, both reference and health logic can become biased.

Mitigation:

- versioned reference;
- reference qualification;
- reference aging checks;
- later clean-data recalibration;
- explicit `REFERENCE_UNTRUSTED`.

## Failure mode 2 — Gate censoring

Quarantining suspicious points can remove valid extremes from the adaptive learning set.

Mitigation:

- separate reference from tracker;
- measure admission ratio;
- preserve quarantined records;
- use held-out calibration;
- test genuine-event tail retention.

Do not claim a special censoring correction works unless the experiment proves it.

## Failure mode 3 — Extreme weather mistaken for fault

Mitigation:

- multivariate context;
- trajectory evidence;
- episode waiting;
- optional network support;
- abstention.

## Failure mode 4 — Fault mistaken for weather

Mitigation:

- single-channel divergence;
- tracker/reference behavior;
- persistence;
- hypothesis competition;
- quarantine.

## Failure mode 5 — Unknown fault forced into known class

Mitigation:

`UNKNOWN_UNMODELED`

and risk–coverage evaluation.

## Failure mode 6 — Quantization mistaken for freeze

Mitigation:

- resolution-aware thresholds;
- run-length evidence;
- compare with other variables;
- calibration by instrument resolution.

## Failure mode 7 — New station cold start

Mitigation:

`COLD_START`

with lower long-horizon confidence until sufficient station-specific history exists.

## Failure mode 8 — Model unavailable

Mitigation:

deterministic integrity + lightweight statistical fallback.

## Failure mode 9 — Late observations

Mitigation:

- event-time ordering;
- bounded watermark;
- idempotent ingestion;
- explicit rules for which past decisions may be revised.

## Failure mode 10 — Network unavailable

Mitigation:

station-local operation continues; network-dependent fields become:

`NETWORK_UNAVAILABLE`

not false certainty.

---

# Fallback Behavior

The system has an explicit degradation hierarchy.

## Level 0 — Full system

- integrity;
- ML temporal/seasonal predictor;
- dual baselines;
- episode adjudication;
- network context;
- health/degradation;
- dashboard.

## Level 1 — No network context

- all station-local functions remain;
- network fields become `NETWORK_UNAVAILABLE`.

## Level 2 — ML unavailable

- integrity;
- robust temporal baseline;
- simple residual statistics;
- deterministic fault classes;
- no false confidence.

Status:

`MODEL_UNAVAILABLE`

## Level 3 — Short history / cold start

Use population/default initial parameters only for provisional screening.

Status:

`COLD_START`

Long-horizon degradation output is restricted.

## Level 4 — Storage/database interruption

Continue in bounded local memory/buffer where practical and preserve sequence IDs for replay.

The system must not silently drop observations.

---

# Exact Technology Stack

## Core

- **Python 3.11+**
- **NumPy**
- **Pandas**
- **SciPy**
- **scikit-learn**

## ML

- Gradient-boosted regression for compact learned T/RH/P temporal/seasonal prediction;
- calibrated lightweight episode classifier/evidence scorer only where ablations justify it.

## Statistical

- robust median/MAD;
- robust covariance;
- EWMA/CUSUM or related change detection;
- seasonal residual analysis.

These are transparent baselines and supporting components, not claimed innovations.

## API

- **FastAPI**
- **Pydantic**

## Storage

- **SQLite** for the reproducible local prototype;
- Parquet/CSV for replay datasets.

## Dashboard

- **Streamlit**
- **Plotly**

## Testing

- **pytest**
- deterministic replay tests;
- unit tests;
- state-machine tests;
- benchmark scripts.

## Deployment

- local Python environment first;
- optional Docker packaging after reproducibility is established.

## Streaming

The initial implementation uses a bounded in-process/event-time stream.

MQTT or another broker is optional and will not be introduced merely to make the architecture look “industrial.”

---

# Mandatory Features

These are required by the SIH26073 brief and must exist in the final implementation:

- AI/ML-based anomaly detection;
- T/RH/P core inputs;
- real-time/streaming operation;
- spike detection;
- frozen/stuck detection;
- sensor malfunction detection;
- communication-error handling;
- temporal analysis;
- seasonal analysis;
- multivariate T/RH/P consistency;
- genuine weather vs sensor anomaly reasoning;
- anomaly alert;
- severity;
- confidence;
- explainable reasoning;
- root-cause classification;
- sensor health;
- degradation indication;
- maintenance indication;
- scalability design;
- practical deployment;
- visualization/dashboard;
- anomaly-injected evaluation;
- executable code;
- example usage;
- documented use cases.

These requirements are explicitly identified as mandatory in the Master Brief. fileciteturn0file0L157-L236

---

# Optional Features

- corrected/imputed values;
- SHAP for the compact ML model;
- LIME;
- optional network-context layer when data are available;
- edge implementation on a measured board;
- MQTT;
- richer frontend beyond Streamlit;
- cryptographic audit lineage if a real requirement emerges.

Optional features must not delay or weaken the mandatory detector.

---

# Features We Will NOT Build

The first implementation will **not** build:

1. A transformer/foundation-model detector.
2. A GNN as the primary detector.
3. DEMIX/group-sparse source separation.
4. CONSERVE as the core decision mechanism.
5. A full Bayesian/sequential generative model with large parameter grids.
6. Simes/e-value fusion as a required layer.
7. Exact conformal false-alarm guarantees.
8. A cryptographic/Merkle ledger as the novelty mechanism.
9. Exact remaining-useful-life prediction.
10. Automated spare-part selection.
11. Guaranteed maintenance dispatch.
12. Physical component diagnosis from T/P/RH alone.
13. Automatic correction of ambiguous events.
14. Hidden use of wind, rain, solar, gust, visibility, or other non-core meteorological variables.
15. Full edge inference unless measured on the actual target hardware.
16. Kubernetes/Kafka/distributed infrastructure without a demonstrated workload requirement.
17. A generic 0–100 “health score” as the main contribution.

The decision is intentionally biased toward **minimum complexity that satisfies the PS plus one measurable innovation mechanism**.

---

# SIH Criteria Mapping

The official SIH26073 weighting is:

| Criterion | Weight |
|---|---:|
| Innovation & Novelty | 25 |
| Detection Accuracy | 20 |
| Real-Time Capability | 15 |
| Explainability | 10 |
| Scalability | 10 |
| Practical Deployability | 10 |
| Visualization/UI | 5 |
| Energy Efficiency | 5 |
| **Total** | **100** |

## Innovation & Novelty — 25

Defensible contribution:

- poisoning-resistant adaptive learning;
- explicit admission/quarantine;
- sequential episode adjudication;
- measured abstention behavior;
- reversible model-learning provenance.

No algorithm is claimed novel by itself.

## Detection Accuracy — 20

The system combines:

- deterministic fault handling;
- learned temporal/seasonal residual detection;
- multivariate T/RH/P evidence;
- active episode adjudication;
- optional network context.

Evaluation is based on pointwise, event-level, hard-negative, unseen-injector and calibration metrics.

## Real-Time Capability — 15

Fast path:

- integrity;
- immediate suspicion.

Diagnostic path:

- active episode evidence accumulation.

Health path:

- slower degradation detection.

Latency is measured rather than asserted.

## Explainability — 10

Native evidence cards:

- raw value;
- expected value;
- residual;
- temporal behavior;
- multivariate evidence;
- hypothesis evidence;
- uncertainty;
- model/reference version.

## Scalability — 10

Station-local state with horizontal processing.

Network analysis is conditional and bounded.

## Practical Deployability — 10

Local reproducible implementation:

- Python;
- FastAPI;
- SQLite;
- Streamlit;
- deterministic replay.

No unnecessary distributed infrastructure.

## Visualization/UI — 5

The dashboard exposes:

- live station state;
- episode replay;
- dual-baseline history;
- evidence explanation;
- quarantine history;
- network context.

## Energy Efficiency — 5

Edge role is intentionally lightweight.

Actual energy performance is measured only if edge hardware is implemented.

---

# Defensible Novelty Claims

The project should use narrow, behavior-based wording.

## Claim 1

> **“TRUST-TWIN uses a versioned trusted reference to control admission into an adaptive AWS baseline, so suspect observations are quarantined rather than silently becoming the new normal.”**

This is a **candidate differentiator**, not a claim that frozen/adaptive baselines themselves are new.

## Claim 2

> **“TRUST-TWIN treats the time required to accumulate diagnostic evidence as an explicit operating variable, allowing provisional alerts followed by WAIT/ABSTAIN decisions rather than forcing an immediate root-cause label.”**

Again, this must be validated against static/standard sequential baselines.

## Claim 3

> **“The system makes every adaptive-baseline update auditable and reversible, including which observations were admitted or quarantined.”**

This is an engineering behavior, not a cryptographic novelty claim.

## Claim 4

If experiments support it:

> **“On the SIH26073 benchmark, the proposed admission-and-adjudication mechanism reduces [predeclared failure mode] relative to [predeclared baseline] under [predeclared test condition].”**

The exact metric/value must be filled only after measurement.

---

# Claims We MUST NOT Make

Never claim:

- 100% accuracy;
- zero false positives;
- perfect weather/fault separation;
- guaranteed fault prediction;
- guaranteed maintenance decisions;
- guaranteed sensor failure dates;
- official IMD adoption;
- national-scale deployment;
- production deployment;
- field-tested performance without field testing;
- real-world performance from synthetic anomalies alone;
- first-ever architecture;
- unique novelty based only on a name;
- exact conformal false-alarm guarantees without the required assumptions and evidence;
- exact physical hardware cause from T/P/RH only;
- “true value” for an imputed observation;
- real-time latency unless measured;
- edge energy unless measured;
- scalability claims without workload evidence;
- “self-healing” unless the system actually performs validated automatic recovery.

The Master Brief expressly prohibits unsupported versions of these claims. fileciteturn0file0L520-L590

---

# HANDOFF TO NEXT AGENT

## Final architecture name

**TRUST-TWIN — Quarantine-Gated Sequential Evidence Monitor**

## What the next implementation agent must build first

### Phase 1 — Non-negotiable foundation

1. Canonical T/RH/P schema.
2. Event-time ingestion contract.
3. Missing/duplicate/delayed handling.
4. Raw-data immutable record.
5. Deterministic spike/freeze/communication checks.
6. Learned temporal/seasonal T/RH/P predictor.
7. Reference/tracker state objects.

### Phase 2 — Core differentiation

8. Admission state machine:
   - `ADMIT`
   - `QUARANTINE`
   - `REJECT`
   - `UNKNOWN`
9. Tracker update provenance.
10. Reference/tracker divergence.
11. Rollback/replay.
12. Active episode manager.
13. Sequential evidence adjudication.
14. `WAIT` / `ABSTAIN` / `AMBIGUOUS`.

### Phase 3 — Operational outputs

15. Confidence calibration.
16. Severity.
17. Root-cause category.
18. Health state.
19. Degradation indication.
20. Maintenance indication.
21. Evidence explanation.

### Phase 4 — Evaluation

22. Baseline ladder.
23. Chronological splits.
24. Injector-family holdout.
25. Genuine-event hard negatives.
26. Unknown/unmodeled cases.
27. Poisoning experiment.
28. Calibration/risk–coverage analysis.
29. latency/throughput/memory measurement.

### Phase 5 — Optional extensions

30. Network context.
31. Optional correction.
32. SHAP.
33. Edge prototype.

These extensions must not precede the core evaluation gates.

---

# Hard-Gate Decision Record

The final arbitration applies the required hard gates before weighted evaluation.

| Candidate | Hard-gate result | Decision |
|---|---|---|
| **Architecture 1 — Sequential Evidence Race** | Meets mandatory scope when wrapped in common compliance shell; strong event-level adjudication, but weaker long-horizon anti-poisoning foundation | **Survives gate; not selected as foundation** |
| **Architecture 2 — Twin-Clock Quarantine Monitor** | Meets mandatory scope with explicit short-fault compliance shell; directly addresses adaptive baseline poisoning; implementable without requiring a network dataset | **Survives gate; selected as foundation** |
| **Architecture 3 — Conditional Network Attribution** | Network attribution is meaningful only under sufficient synchronized multi-station data; core value is therefore condition-dependent | **Rejected as primary architecture; retained as optional context layer** |

The technical review gave the three architectures provisional architecture-readiness totals of 77, 80, and 70 respectively, with the explicit warning that empirical performance remains UNKNOWN. fileciteturn2file1L51-L69

The final decision does **not** treat those numbers as measured detection performance. They are only supporting design-readiness evidence.

---

# Controlled Synthesis Record

## Selected foundation

**Twin-Clock / Quarantine architecture**

Reason:

- directly targets adaptive baseline poisoning;
- high practical feasibility;
- strong scalability shape;
- explicit provenance and rollback;
- naturally supports long-horizon sensor health/degradation;
- does not require synchronized network data.

The technical evaluation identified it as the strongest of the three architecture-level foundations under the supplied evidence, while also identifying its weakness: it must not rely on a sophisticated selection-conditional gate unless that gate proves better than a simpler alternative. fileciteturn2file1L121-L147

## Repair added from Sequential Evidence Race

Only the **behavioral core** is retained:

- evidence accumulates over the next observations;
- compute latency and information latency are separated;
- `WAIT` and `ABSTAIN` are explicit;
- explanations show why a hypothesis gained or lost support.

The unsupported “anytime-valid guarantee” language is excluded.

The synthesis preserves the red-team warning that sequential validity does not automatically solve weather-vs-fault attribution. fileciteturn2file3L84-L103

## Repair added from Network Attribution

Only the **conditional context layer** is retained:

- use neighbors when resolvable;
- distinguish propagation evidence from synchronized data failure;
- never infer sensor fault from isolation alone;
- return `NETWORK_UNRESOLVED` when timing/coverage are insufficient.

The full network-first architecture is not selected because its central benefit is conditional on data that the current project package has not established.

---

# Complete Requirement Matrix

| Requirement | Implementation | Demonstration | Evidence | Status |
|---|---|---|---|---|
| Temperature input | `temperature` field | Live/replay schema | Master Brief | **MANDATORY — BUILD** |
| Pressure input | `pressure` field | Live/replay schema | Master Brief | **MANDATORY — BUILD** |
| Relative humidity input | `relative_humidity` field | Live/replay schema | Master Brief | **MANDATORY — BUILD** |
| Real-time anomaly detection | Streaming ingestion + fast path | Continuous replay | Required PS + measured latency | **MANDATORY — BUILD/MEASURE** |
| Spike detection | Residual/rate + episode evidence | Spike replay | Fault injector + detection metrics | **MANDATORY — BUILD/MEASURE** |
| Frozen/stuck detection | Resolution-aware run-length/flatness | Freeze replay | Detection delay + FPR | **MANDATORY — BUILD/MEASURE** |
| Sensor malfunction detection | Episode classification | Bias/noise/drift replay | Root-cause confusion | **MANDATORY — BUILD/MEASURE** |
| Communication-error handling | Cadence/heartbeat/integrity layer | Removed timestamps | Event labels | **MANDATORY — BUILD/MEASURE** |
| Temporal analysis | Lags/trends/episode evidence | Step/drift/spike replay | Detection delay | **MANDATORY — BUILD** |
| Seasonal analysis | Seasonal/calendar baseline features | Seasonal replay | Held-out chronology | **MANDATORY — BUILD** |
| Multivariate consistency | Joint T/RH/P residuals | Coupled and incoherent traces | Per-class metrics | **MANDATORY — BUILD/MEASURE** |
| Genuine weather vs sensor fault | Weather hypothesis + fault hypotheses + abstention | Genuine-event hard negative | Independent event evidence | **MANDATORY — BUILD/VALIDATE** |
| Confidence | Calibrated decision reliability | Reliability/risk–coverage plot | Held-out calibration set | **MANDATORY — BUILD/MEASURE** |
| Severity | Magnitude × duration × criticality rule | High vs low severity cases | Operational definition | **MANDATORY — BUILD** |
| Explainability | Native evidence card | Episode replay | Fidelity test | **MANDATORY — BUILD/MEASURE** |
| Root-cause classification | Hierarchical behavioral categories | Fault-family demo | Confusion matrix incl. UNKNOWN | **MANDATORY — BUILD/MEASURE** |
| Sensor health | Longitudinal evidence state | Long replay | Health false-warning metrics | **MANDATORY — BUILD/MEASURE** |
| Degradation indication | Change-point + persistent divergence | Drift replay | Long-horizon evaluation | **MANDATORY — BUILD/MEASURE** |
| Maintenance indication | Review recommendation state | Drift/recurrence demo | Real maintenance labels where available | **MANDATORY — BUILD/VALIDATE** |
| Scalability | Per-station state + horizontal workers | Load test | throughput/memory measurements | **MANDATORY — DESIGN/MEASURE** |
| Practical deployability | Python/FastAPI/SQLite/Streamlit | Clean local deployment | Reproducible setup | **MANDATORY — BUILD/TEST** |
| Visualization/dashboard | Streamlit + Plotly | Live station + episode replay | UI walkthrough | **MANDATORY — BUILD** |
| Raw-data preservation | Immutable raw record | Show raw vs estimate | Storage/schema test | **MANDATORY — BUILD/TEST** |
| T/P/RH-derived features | Explicit derived feature module | Feature audit | Schema audit | **MANDATORY — BUILD** |
| Trusted reference | Versioned slow baseline | Reference/tracker overlay | Model version/provenance | **CORE INNOVATION — BUILD** |
| Adaptive tracker | Admission-gated update | Poisoning replay | Ablation | **CORE INNOVATION — BUILD/MEASURE** |
| Quarantine | `ADMIT/QUARANTINE/REJECT/UNKNOWN` | Suspect stream replay | State-machine test | **CORE INNOVATION — BUILD/TEST** |
| Rollback | Checkpoint + replay | Inject contamination then rollback | Recovery experiment | **CORE INNOVATION — BUILD/MEASURE** |
| Sequential adjudication | Episode manager + hypothesis evidence | Spike vs step vs weather | Risk–coverage/time-to-decision | **CONTROLLED SYNTHESIS — BUILD/MEASURE** |
| Explicit abstention | `WAIT/ABSTAIN/UNKNOWN` | Ambiguous episode | OOD + abstention metrics | **MANDATORY SAFETY FEATURE — BUILD/MEASURE** |
| Network context | Optional conditional module | Propagation/data-fault replay | Resolvability tests | **OPTIONAL — BUILD ONLY IF DATA EXISTS** |
| Correction/imputation | Separate estimated field + uncertainty | Gap/spike correction demo | RMSE/MAE on masked regions | **OPTIONAL — VALIDATE** |
| Model versioning | Versioned artifacts | Show version in evidence card | Reproducibility test | **MANDATORY SUPPORTING FEATURE** |
| Decision provenance | Admission/evidence/version record | Learning-provenance page | Replay equivalence | **MANDATORY SUPPORTING FEATURE** |
| Cold start | `COLD_START` state | New-station replay | Performance vs history length | **MANDATORY — BUILD/MEASURE** |
| Model fallback | Integrity/statistical fallback | Disable ML during replay | Chaos/state tests | **MANDATORY — BUILD/TEST** |
| Network-unavailable fallback | Local-only operation | Remove network context | Same-case comparison | **MANDATORY — BUILD/TEST** |
| Data leakage prevention | Chronological split + holdout injectors | Evaluation report | Split audit | **MANDATORY — VALIDATE** |
| Independent injector testing | Multiple generator families | OOD fault replay | Cross-injector results | **MANDATORY — VALIDATE** |
| Genuine-event hard negatives | Independent event set | Event replay | False-positive metrics | **MANDATORY — VALIDATE** |
| Quantization awareness | Resolution-aware freeze logic | Flat quantized replay | False-positive stress test | **MANDATORY — VALIDATE** |
| Unknown anomaly handling | Open `UNKNOWN_UNMODELED` path | Novel fault replay | Forced-label rate | **MANDATORY — VALIDATE** |
| Edge screening | Lightweight integrity/trigger | Board demo if implemented | CPU/RAM/energy measurements | **OPTIONAL — MEASURE** |
| SHAP/LIME | Optional ML explanation | Feature attribution | Fidelity test | **OPTIONAL** |
| Cryptographic ledger | Not part of MVP | None | N/A | **NOT BUILDING** |
| Transformer/foundation model | Not part of MVP | None | N/A | **NOT BUILDING** |
| GNN | Not part of MVP | None | N/A | **NOT BUILDING** |
| Exact RUL model | Not part of MVP | None | N/A | **NOT BUILDING** |
| Physical component diagnosis | Not claimed | None | N/A | **NOT BUILDING** |
| Guaranteed maintenance | Not claimed | None | N/A | **NOT BUILDING** |
| Unsupported edge/scalability numbers | Not used | None | N/A | **PROHIBITED CLAIM** |

---

# Final Decision

## Selected architecture

**TRUST-TWIN — Quarantine-Gated Sequential Evidence Monitor**

### Foundation
**Twin-Clock / trusted-reference + adaptive-tracker**

### Controlled additions
**Sequential evidence adjudication + conditional network context**

### Core operating principle

```text
DO NOT LET THE SENSOR TEACH THE MODEL THAT ITS OWN FAULT IS NORMAL.

DO NOT FORCE A CAUSE WHEN THE OBSERVATION DOES NOT CONTAIN ENOUGH EVIDENCE.

DO NOT USE NETWORK DISAGREEMENT AS PROOF OF SENSOR FAILURE.

DO NOT OVERWRITE THE OBSERVATION OF RECORD.
```

This architecture is intentionally narrower than the full candidate universe. It preserves every mandatory SIH26073 requirement while concentrating the differentiating engineering effort on two problems that the supplied evidence repeatedly identifies as both consequential and testable:

1. **adaptive-baseline poisoning**, and
2. **safe diagnosis under incomplete evidence**.

The final architecture is therefore ready to be handed to the implementation agent, with all performance, latency, energy, scalability, calibration, and novelty claims remaining **pending their specified validation experiments**.
