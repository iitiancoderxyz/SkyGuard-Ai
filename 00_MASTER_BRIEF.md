# 00_MASTER_BRIEF — SIH26073

## Purpose of This Brief

This document is the **authoritative requirements baseline** for all future AI agents, researchers, architects, developers, critics, and documentation agents working on SIH26073.

Future agents must treat this file as the source of truth for **what the problem requires**. They may propose implementation choices, algorithms, architectures, datasets, interfaces, and improvements only after respecting the requirements and constraints defined here.

This brief **does not prescribe a final solution**. It converts the original problem statement into precise, testable, and unambiguous requirements.

---

# 1. Problem Statement

SIH26073 requires the development of an **AI/ML-based intelligent anomaly detection system for Automatic Weather Stations (AWS)**.

The system must automatically identify abnormal, inconsistent, or faulty observations from AWS data **in real time**, using the following three core meteorological parameters:

1. **Temperature (°C)**
2. **Atmospheric Pressure (hPa)**
3. **Relative Humidity (%)**

The system must distinguish between:

- genuine meteorological events, and
- sensor/data anomalies or faults.

The system should minimize false alarms while supporting scalable deployment across large AWS observation networks.

The required anomaly-detection capability includes identifying faults such as:

- abnormal spikes,
- frozen/stuck values,
- sensor malfunctions,
- communication errors,
- and other abnormal or corrupted observations detectable from the allowed data.

The system is expected to learn normal behavior across:

- temporal patterns,
- seasonal patterns,
- and multivariate relationships among temperature, pressure, and humidity.

It must provide useful operational outputs including anomaly alerts, severity/confidence information, root-cause classification, visualization, sensor health assessment, and indications of possible degradation or maintenance needs.

The expected submission must include:

- **fully executable code,**
- **example usage,**
- and **documentation explaining various use cases.**

---

# 2. Background

Automatic Weather Stations are important components of meteorological observation networks. They continuously collect atmospheric observations that can support:

- weather forecasting,
- climate monitoring,
- disaster management,
- aviation,
- agriculture,
- and scientific research.

AWS observations can become unreliable because of:

- sensor malfunction,
- communication failures,
- calibration drift,
- power fluctuations,
- harsh environmental conditions,
- and data corruption.

Erroneous observations can negatively affect weather forecasting and downstream decision-making systems.

Traditional threshold-based quality-control methods may fail to identify more complex, hidden, contextual, temporal, or multivariate anomalies.

Therefore, SIH26073 calls for an intelligent AI/ML-based approach that can evaluate AWS observations in real time and distinguish abnormal sensor/data behavior from legitimate meteorological variation.

The example described in the problem statement is a station suddenly reporting approximately **55°C temperature with extremely high humidity and abnormal pressure variation while neighboring stations remain normal**. The required system behavior is to analyze temporal and spatial consistency, identify the reading as a probable sensor anomaly, generate an alert, and suggest corrective action.

**Important interpretation:** Spatial context may be used as supporting/contextual information when available, but the three core meteorological model inputs remain strictly limited to temperature, pressure, and humidity as defined below.

---

# 3. Exact Required Inputs

## 3.1 Core Meteorological Model Inputs — ONLY These Three

The core meteorological model inputs are exactly:

| Parameter | Unit | Status |
|---|---|---|
| Temperature | °C | **Mandatory** |
| Atmospheric Pressure | hPa | **Mandatory** |
| Relative Humidity | % | **Mandatory** |

These three variables are the **only core meteorological variables explicitly allowed by the problem statement**.

### Strict rule

Future agents **must not silently introduce additional meteorological variables** such as, for example:

- wind speed,
- wind direction,
- rainfall,
- solar radiation,
- dew point,
- visibility,
- soil moisture,
- cloud cover,
- or any other meteorological measurement

as if they were required inputs of SIH26073.

A future agent may discuss such variables only if their role is explicitly identified as **outside the required core scope**, a non-core optional research extension, or contextual information that does not replace or redefine the required three-variable input specification.

## 3.2 Contextual Metadata

The following may be treated as contextual metadata rather than additional core meteorological variables:

- **Station ID**
- **Timestamp**
- **Station location**

They may support temporal analysis, station-wise health tracking, network context, neighboring-station comparison, visualization, or operational identification.

They **do not change the definition of the core meteorological input set**.

## 3.3 Data Sources Permitted by the PS

Participants may use:

- historical AWS datasets,
- simulated/injected anomalies,
- streaming sensor data,

provided that the core meteorological observations used for the problem are temperature, atmospheric pressure, and relative humidity.

## 3.4 Required Data Characteristics

The system should support data organized as a time series/stream so that it can evaluate observations in real time and learn or use normal temporal behavior.

The implementation must be explicit about assumptions regarding:

- sampling frequency,
- missing records,
- malformed records,
- delayed data,
- duplicated records,
- and unavailable contextual metadata.

Agents must not assume a particular dataset format unless the format is documented as an implementation choice.

---

# 4. Mandatory Objectives

The following objectives are **MANDATORY** because they are explicitly required by the problem statement.

## 4.1 Real-Time Anomaly Detection

The system must identify abnormal AWS observations in a real-time or streaming processing workflow.

## 4.2 Fault/Anomaly Detection

The system must be capable of identifying, at minimum, the following explicitly named anomaly/fault types:

- **sensor faults/malfunctions**
- **spikes**
- **frozen/stuck values**
- **communication errors**

The implementation should clearly define how each required anomaly category is represented, detected, and reported.

## 4.3 Temporal Pattern Learning

The system must account for normal temporal behavior in temperature, pressure, and humidity.

This means the system should consider how an observation relates to relevant historical behavior rather than relying only on a single instantaneous value.

## 4.4 Seasonal Pattern Learning

The system must account for normal seasonal patterns.

The exact modeling technique is not prescribed by the PS; future agents may choose an appropriate method.

## 4.5 Multivariate Consistency Analysis

The system must analyze consistency among:

- temperature,
- pressure,
- humidity.

The system should therefore be capable of identifying observations that are suspicious because the variables jointly behave inconsistently, even when an individual value might not violate a simple static threshold.

## 4.6 Genuine Event vs Sensor/Data Anomaly Distinction

A central requirement is to distinguish:

- a legitimate/genuine meteorological event,
from
- a sensor/data anomaly.

Future designs must therefore avoid treating every unusual value as automatically faulty.

## 4.7 Confidence Scores

Detected anomalies must have an associated **confidence score** or equivalent confidence indication.

The meaning, scale, and interpretation of the confidence measure must be documented.

## 4.8 Explainable Reasoning

The system must provide explainable reasoning for anomaly decisions.

The explanation should communicate, in understandable terms, **why the observation was considered anomalous**, based on the evidence available to the system.

The PS specifically prefers explainable AI approaches such as SHAP/LIME.

## 4.9 Root-Cause Classification

The system must classify or identify a likely root cause/category for detected abnormal observations, especially among the required fault/anomaly types.

Root-cause classification must be distinguished from mere anomaly detection.

## 4.10 Sensor Health Status

The system must maintain or provide a **sensor health status**.

This can be expressed through an appropriate health indicator or state, provided its semantics are documented.

## 4.11 Degradation Prediction

The system must address the possibility of **sensor degradation** and identify indications of declining sensor reliability.

This requirement concerns early warning/assessment of deteriorating sensor behavior, not only instantaneous anomaly detection.

## 4.12 Maintenance Indication

The system must provide an indication of possible **maintenance requirements** based on detected behavior and/or sensor health/degradation evidence.

A future agent must not present maintenance decisions as guaranteed facts unless supported by evidence; the system should instead communicate an evidence-based indication/recommendation according to the implemented logic.

## 4.13 Scalability

The system must be designed with scalability in mind so that the concept can extend from an individual station to a larger AWS observation network.

## 4.14 Practical Deployment

The solution must address practical deployability, including the real-time operational setting and resource/deployment considerations.

## 4.15 Visualization / Dashboard

The expected solution must provide a visualization/dashboard capability for relevant operational information such as:

- incoming observations,
- anomaly status,
- severity/confidence,
- sensor health,
- and related explanations/diagnostics.

The exact visual design is not prescribed.

## 4.16 Executable Submission

The final submission must include:

- **fully executable code,**
- **example usage,**
- and a **document explaining various use cases.**

---

# 5. Expected Outputs

The system should produce the following outputs.

## 5.1 Real-Time Anomaly Alerts — MANDATORY

Alerts for detected anomalies in the AWS stream.

## 5.2 Severity Scores — MANDATORY

A severity indication for detected anomalies.

The implementation must document how severity is determined and what each severity level means.

## 5.3 Confidence Scores — MANDATORY

A confidence score/indicator associated with the anomaly decision.

## 5.4 Root-Cause Classification — MANDATORY

A probable anomaly/fault/root-cause category.

At minimum, the implementation must address the fault categories explicitly required by the PS.

## 5.5 Visualization Dashboard — MANDATORY

An operational interface showing relevant measurements, detections, and system status.

## 5.6 Sensor Health Status — MANDATORY

A current or rolling estimate/status of sensor health.

## 5.7 Explainable Reasoning — MANDATORY

A human-readable explanation of the evidence contributing to the detection.

## 5.8 Degradation / Maintenance Indication — MANDATORY

An indication of possible sensor degradation and/or maintenance need.

## 5.9 Corrected / Imputed Values — OPTIONAL

The system may optionally estimate corrected or imputed values for anomalous observations.

This capability is **not mandatory** and must never be presented as required core functionality.

## 5.10 Example Usage and Use-Case Documentation — MANDATORY

The submission must demonstrate example usage and document various applicable use cases.

---

# 6. Suggested Technologies

The following are **SUGGESTED / PREFERRED**, not mandatory unless a later implementation explicitly adopts them.

## 6.1 Explainable AI

The PS states that explainable AI such as:

- **SHAP**
- **LIME**

is preferable.

The brief therefore treats explainability as mandatory, while SHAP/LIME specifically are suggested implementation technologies rather than mandatory libraries.

## 6.2 Edge AI

The PS suggests **Edge AI for low-power deployment on ESP32**.

This is a suggested deployment direction.

If used, agents must ensure that the implementation is actually compatible with the computational, memory, and energy constraints of the selected hardware.

## 6.3 Machine Learning / AI

The problem does not prescribe one specific ML algorithm.

Future agents may evaluate suitable approaches for:

- time-series anomaly detection,
- multivariate anomaly detection,
- online/streaming detection,
- classification,
- health scoring,
- and degradation estimation.

Algorithm selection must be justified against the requirements rather than assumed.

## 6.4 Dashboard / Visualization Stack

No specific dashboard framework is mandated by the PS.

Agents may select a suitable technology based on:

- rapid prototype development,
- real-time updates,
- usability,
- deployment simplicity,
- and maintainability.

## 6.5 Data / Streaming Technology

No specific database, message broker, or stream-processing framework is mandated.

Any selected technology must serve the real-time and scalability requirements without introducing unnecessary complexity.

---

# 7. Evaluation Criteria

The official evaluation criteria and weightages stated in the PS are:

| Criterion | Weightage |
|---|---:|
| Innovation & Novelty | **25%** |
| Detection Accuracy | **20%** |
| Real-Time Capability | **15%** |
| Explainability | **10%** |
| Scalability | **10%** |
| Practical Deployability | **10%** |
| Visualization/UI | **5%** |
| Energy Efficiency | **5%** |

## Interpretation Rules for Future Agents

Future agents must use these criteria when evaluating proposed solution approaches.

However:

- the criteria are **evaluation dimensions**, not permission to invent extra problem requirements;
- higher weightage does not mean lower-weighted requirements can be ignored;
- innovation/novelty claims must be evidence-based;
- accuracy claims must be tied to a defined evaluation dataset/protocol;
- real-time capability must be demonstrated or measured rather than merely asserted;
- energy efficiency is particularly relevant if edge deployment is proposed.

The PS states that evaluation is to be performed on **anomaly-injected data**. Future evaluation plans must make the anomaly-injection methodology explicit rather than using vague claims.

---

# 8. Grand Challenge

The grand challenge stated by the PS is:

> **Can AI build a self-aware and self-healing weather observation network capable of delivering trustworthy atmospheric data under all environmental conditions?**

Future agents may use this statement as the broader vision behind the project.

However, the phrase **“self-aware”** or **“self-healing”** must not be interpreted as permission to claim capabilities that are not actually implemented and evaluated.

For example, a system that flags anomalies and suggests maintenance is not automatically equivalent to a fully autonomous self-healing network.

---

# 9. Constraints

## 9.1 Core Input Constraint

The core meteorological inputs are **ONLY**:

- Temperature (°C)
- Atmospheric Pressure (hPa)
- Relative Humidity (%)

This restriction must remain explicit throughout all downstream work.

## 9.2 No Silent Expansion of Meteorological Inputs

Future agents must not silently add other meteorological measurements as required model inputs.

If a proposal uses another signal, it must explicitly state:

1. what the signal is,
2. why it is being used,
3. whether it is contextual metadata or an optional/non-core extension,
4. and that it is not part of the three required core meteorological inputs.

## 9.3 Contextual Metadata

Station ID, timestamp, and location may be used as metadata/context.

They must not be incorrectly described as additional meteorological parameters.

## 9.4 Real-Time Constraint

The project is explicitly about real-time anomaly detection.

A purely offline batch-only solution does not satisfy the real-time requirement by itself.

## 9.5 Genuine-Event Protection

The system must account for the possibility that unusual measurements can represent real atmospheric events.

A rare value must not automatically be labeled as sensor failure without contextual evidence.

## 9.6 False-Alarm Awareness

The PS explicitly emphasizes minimizing false alarms.

Future designs and evaluations must therefore consider false positives and not optimize only for anomaly detection rate.

## 9.7 Evidence-Based Claims

Performance and deployment claims must be supported by actual measurements, experiments, documentation, or appropriate evidence.

## 9.8 Executability

The submitted implementation must be fully executable and include example usage.

## 9.9 Documentation

The project must include documentation covering its various use cases.

## 9.10 Scalability

The architecture should be capable of extending beyond a single AWS station toward a larger station network.

## 9.11 Energy / Edge Consideration

Energy efficiency is an explicit evaluation criterion. If edge deployment is claimed or proposed, compute, memory, latency, and energy assumptions must be addressed.

---

# 10. Mandatory vs Optional Requirements

## 10.1 MANDATORY

The following must be present in the final solution concept and implementation:

- AI/ML-based anomaly detection
- Real-time/streaming anomaly detection capability
- Core inputs limited to:
  - Temperature (°C)
  - Atmospheric Pressure (hPa)
  - Relative Humidity (%)
- Detection of sensor faults/malfunctions
- Detection of spikes
- Detection of frozen/stuck values
- Detection/handling of communication errors
- Temporal pattern learning/analysis
- Seasonal pattern learning/analysis
- Multivariate consistency analysis among temperature, pressure, and humidity
- Distinction between genuine meteorological events and sensor/data anomalies
- Anomaly alerts
- Severity scoring/indication
- Confidence scoring/indication
- Explainable reasoning
- Root-cause classification
- Sensor health status
- Sensor degradation prediction/indication
- Maintenance indication
- Scalability consideration
- Practical deployment consideration
- Visualization/dashboard
- Evaluation using anomaly-injected data or an appropriately documented equivalent consistent with the PS
- Fully executable code
- Example usage
- Documentation explaining various use cases

## 10.2 SUGGESTED / PREFERRED

These are recommended by the PS but are not individually mandatory:

- SHAP
- LIME
- Edge AI
- ESP32-oriented low-power deployment
- Other technologies appropriate for scalable real-time deployment

Using a different implementation technology is allowed when it better satisfies the requirements and is technically justified.

## 10.3 OPTIONAL

The following is explicitly optional:

- Corrected/imputed value estimation for anomalous observations.

Optional functionality must not displace or weaken mandatory requirements.

---

# 11. Scientific/Operational Constraints

This section defines important constraints that future solution agents must respect to avoid scientifically misleading behavior.

## 11.1 Anomaly Does Not Automatically Mean False Observation

An unusual atmospheric observation can be a real meteorological event.

Therefore, anomaly detection must be interpreted as a **decision under uncertainty**, not automatic proof that the sensor reading is wrong.

## 11.2 Context Matters

The system should consider the observation's relationship with:

- recent observations,
- longer historical/seasonal behavior,
- the other two required meteorological parameters,
- and, where available, contextual station/network information.

## 11.3 Multivariate Relationships Are Required

The system must not reduce the complete problem to three independent threshold checks.

The PS specifically requires **multivariate consistency analysis**.

## 11.4 Temporal and Seasonal Behavior Are Required

A value can be normal at one time and abnormal at another.

Therefore, future agents must account for time-dependent and seasonal context rather than assuming one universal static threshold is sufficient.

## 11.5 Communication Errors Are Distinct From Meteorological Anomalies

Communication failure may produce:

- missing data,
- malformed data,
- delayed data,
- repeated/stale data,
- or related stream integrity problems.

Future designs must distinguish communication/data-pipeline problems from genuine atmospheric behavior where technically possible.

## 11.6 Frozen/Stuck Sensors Are Temporal Problems

A frozen value may remain numerically plausible while becoming suspicious because it fails to change as expected over time.

Detection therefore requires temporal behavior analysis rather than only value-range checks.

## 11.7 Root Cause Is Not the Same as Detection

The system may determine that an observation is anomalous without being certain of the exact physical cause.

Where certainty is unavailable, root-cause output should be represented as a probable classification/confidence rather than an unsupported definitive diagnosis.

## 11.8 Confidence Must Be Interpretable

A confidence score must have a documented meaning.

Future agents must not use a numerical confidence value merely as decoration without defining what it represents.

## 11.9 Severity and Confidence Are Different Concepts

- **Severity** should represent the operational seriousness/impact of the anomaly.
- **Confidence** should represent how strongly the system's evidence supports its detection/classification.

They must not be conflated without explanation.

## 11.10 Degradation and Maintenance Are Longitudinal

Sensor degradation and maintenance indication generally require evidence accumulated over time.

A single unusual observation should not automatically be represented as proof of long-term sensor degradation.

## 11.11 Spatial Information Must Be Treated Carefully

The example use case mentions neighboring stations and spatial consistency.

If station location and neighboring-station information are available, they may be used as contextual evidence.

However, this must not be used to silently redefine the core meteorological input specification.

## 11.12 Ground Truth and Evaluation

Because the PS explicitly refers to anomaly-injected evaluation data, future agents must clearly define:

- what anomaly types are injected,
- how injection is performed,
- which observations are ground-truth anomalous,
- and which metrics are calculated.

Accuracy claims without a defined evaluation protocol are not sufficient.

## 11.13 Operational Safety of Corrections

If corrected/imputed values are implemented, they must be clearly marked as estimated values rather than silently replacing original observations.

The original reading and the system's estimated replacement should remain distinguishable in the system design.

---

# 12. Non-Negotiable Rules

These rules apply to **every future AI agent** working from this brief.

### Rule 1 — Preserve the Core Inputs Exactly

The core meteorological model inputs are **ONLY**:

- Temperature (°C)
- Atmospheric Pressure (hPa)
- Relative Humidity (%)

Do not replace, remove, or silently extend these inputs.

### Rule 2 — Do Not Turn Suggestions Into Requirements

SHAP, LIME, ESP32, Edge AI, and specific libraries/frameworks are suggestions/preferred technologies unless explicitly adopted later as implementation decisions.

### Rule 3 — Do Not Turn the Optional Feature Into a Requirement

Corrected/imputed values are optional.

### Rule 4 — Preserve All Explicitly Required Detection Types

At minimum, the design must address:

- spikes,
- frozen/stuck values,
- sensor faults/malfunctions,
- communication errors.

### Rule 5 — Preserve Temporal + Seasonal + Multivariate Analysis

These are core requirements and must not be reduced to simple threshold checking.

### Rule 6 — Preserve Genuine Event vs Anomaly Distinction

The system must be designed around the possibility that unusual weather can be genuine.

### Rule 7 — Preserve Explainability

The system must provide understandable reasoning for detections.

### Rule 8 — Preserve Confidence + Severity

Both confidence and severity must be represented and clearly defined.

### Rule 9 — Preserve Root Cause + Sensor Health

Root-cause classification and sensor-health assessment must remain explicit outputs.

### Rule 10 — Preserve Degradation + Maintenance Indication

Long-term sensor reliability and maintenance indication are part of the required scope.

### Rule 11 — Preserve Real-Time Operation

A purely offline-only implementation is insufficient.

### Rule 12 — Preserve Scalability and Practical Deployment

Future architecture decisions must consider expansion to a network of AWS stations and realistic deployment constraints.

### Rule 13 — Preserve Visualization

A usable dashboard/visualization capability is part of the expected solution.

### Rule 14 — Preserve Executable Deliverables

The final implementation must include:

- fully executable code,
- example usage,
- use-case documentation.

### Rule 15 — Do Not Invent Unstated Requirements

Future agents may propose improvements, but must label them as:

- required by PS,
- suggested/preferred,
- optional,
- or implementation choice.

They must not present invented requirements as official SIH26073 requirements.

### Rule 16 — Do Not Make Unsupported Performance Claims

Any accuracy, latency, false-positive, scalability, energy, or deployment claim must be supported by a documented experiment, benchmark, measurement, or clearly stated assumption.

---

# CLAIMS WE MUST NOT MAKE

The following claims must **not** be made unless they are genuinely demonstrated with appropriate evidence:

- **100% accuracy**
- **zero false positives**
- **perfect anomaly detection**
- **perfect distinction between weather events and sensor faults**
- **guaranteed prediction of sensor failure**
- **guaranteed maintenance decisions**
- **production deployment by IMD**
- **official IMD adoption**
- **real-world performance without real-world evidence**
- **field-tested performance without field testing**
- **national-scale deployment without supporting evidence**
- **unsupported claims of novelty**
- **“first-ever” or equivalent novelty claims without credible prior-art verification**
- **claims that the system is fully self-healing when it only detects/flags anomalies**
- **claims of edge/ESP32 deployment unless it is actually implemented or technically demonstrated**
- **claims of real-time performance unless latency/throughput behavior has been demonstrated**
- **claims of scalability without a credible architecture and/or evidence**
- **claims that an anomaly classification is certain when the model only provides probabilistic evidence**
- **claims that estimated/imputed values are the true values**
- **claims that all genuine meteorological events can be identified correctly**
- **claims based solely on synthetic/injected anomalies being equivalent to field performance**

When evidence is limited, agents must use precise language such as:

- “prototype demonstrates…”
- “evaluation on anomaly-injected data shows…”
- “under the tested conditions…”
- “the model estimates…”
- “the system provides a probable classification…”

rather than presenting unverified results as facts.

---

# HANDOFF TO NEXT AGENT

Every future AI agent working on SIH26073 must read this file **before performing its assigned task**.

The agent must use this document to determine:

1. **What the official problem requires**
2. **What the core inputs are**
3. **Which objectives and outputs are mandatory**
4. **Which technologies are only suggested/preferred**
5. **Which functionality is explicitly optional**
6. **Which scientific and operational assumptions must be respected**
7. **Which claims are prohibited unless supported by evidence**
8. **Which boundaries must not be silently crossed**

The next agent must **not invent a final solution merely from this brief**. Instead, it should use this requirements baseline as the foundation for its assigned task.

Any proposed idea, architecture, algorithm, dataset strategy, UI, evaluation method, deployment design, or improvement must be traceable back to these requirements and must clearly identify anything that is:

- **MANDATORY**
- **SUGGESTED / PREFERRED**
- **OPTIONAL**
- **IMPLEMENTATION-SPECIFIC**

If a later agent identifies an ambiguity or conflict, it must preserve the original PS requirements and explicitly flag the issue rather than silently changing the specification.

## Required Handoff Checklist

Before handing work to another agent, confirm that the work has preserved:

- Temperature (°C)
- Atmospheric Pressure (hPa)
- Relative Humidity (%)
- real-time anomaly detection
- spikes
- frozen/stuck values
- communication errors
- temporal patterns
- seasonal patterns
- multivariate consistency
- genuine meteorological event vs sensor/data anomaly distinction
- confidence scores
- explainable reasoning
- root-cause classification
- sensor health
- degradation prediction/indication
- maintenance indication
- scalability
- practical deployment
- visualization/dashboard
- edge/energy considerations
- fully executable code
- example usage
- use-case documentation

Any omission from this checklist must be treated as a requirements gap and explicitly reported.

---

## MASTER BRIEF STATUS

**Document:** `00_MASTER_BRIEF.md`  
**Problem Statement:** SIH26073  
**Role:** Authoritative requirements baseline  
**Final solution:** Not defined by this document  
**Core meteorological inputs:** Temperature + Atmospheric Pressure + Relative Humidity only  
**Metadata permitted:** Station ID + Timestamp + Location  
**Output expectation:** Executable implementation + example usage + use-case documentation
