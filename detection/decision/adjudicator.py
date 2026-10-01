# -*- coding: utf-8 -*-
"""Phase 3C — Decision Adjudicator for TRUST-TWIN.

This module provides the deterministic decision layer that sits between the
raw anomaly detection signals (Phase 3A statistical triggers) and the
multivariate evidence (Phase 3B reference/tracker) and produces a final,
human-traceable decision.

Responsibilities
----------------
1. **Severity** – how serious is the current anomaly?
2. **Detection confidence** – how reliable is the current detection signal?
3. **Uncertainty state** – is the system in a confident, ambiguous, or
   cold-start mode?
4. **Decision state** – NORMAL / SUSPECT / ANOMALOUS / AMBIGUOUS / ABSTAIN
5. **Root-cause category** – what is the most likely behavioural fault class?
6. **Evidence / reason codes** – traceable list of contributing signals.
7. **Weather-event likelihood** – float in [0, 1].
8. **Sensor-fault likelihood** – float in [0, 1].

Design constraints
------------------
* Deterministic: same inputs always produce the same outputs.
* No external sensor channels beyond T / P / RH.
* Ambiguous evidence is never forced into a high-confidence fault decision.
* Raw observations are never modified.
* All reasoning is traceable to actual signals used.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# ---------------------------------------------------------------------------
# Root-cause categories (behavioural)
# ---------------------------------------------------------------------------
class RootCause:
    NORMAL = "NORMAL"
    SENSOR_SPIKE = "SENSOR_SPIKE"
    SENSOR_STUCK_FROZEN = "SENSOR_STUCK_FROZEN"
    GRADUAL_DRIFT = "GRADUAL_DRIFT"
    TEMPORAL_INCONSISTENCY = "TEMPORAL_INCONSISTENCY"
    MULTIVARIATE_INCONSISTENCY = "MULTIVARIATE_INCONSISTENCY"
    POSSIBLE_WEATHER_EVENT = "POSSIBLE_WEATHER_EVENT"
    DATA_TELEMETRY_ISSUE = "DATA_TELEMETRY_ISSUE"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Uncertainty states
# ---------------------------------------------------------------------------
class UncertaintyState:
    COLD_START = "COLD_START"        # Not enough history
    LOW = "LOW"                       # High confidence
    MODERATE = "MODERATE"             # Mixed evidence
    HIGH = "HIGH"                     # Strongly competing hypotheses
    ABSTAIN = "ABSTAIN"               # Cannot decide


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------
@dataclass
class AdjudicationResult:
    """Complete output of the decision adjudicator for a single observation."""
    decision_state: str                             # NORMAL / SUSPECT / ANOMALOUS / AMBIGUOUS / ABSTAIN
    severity: str                                   # LOW / MODERATE / HIGH / CRITICAL
    detection_confidence: float                     # [0, 1]
    attribution_confidence: float                   # [0, 1] confidence in root-cause
    uncertainty_state: str                          # UncertaintyState values
    root_cause_category: str                        # RootCause values
    evidence_codes: List[str]                       # Traceable trigger/evidence codes
    weather_event_likelihood: float                 # [0, 1]
    sensor_fault_likelihood: float                  # [0, 1]
    anomaly_score: float                            # Forwarded from statistical detector
    plausibility_score: float                       # Combined from reference/tracker
    weather_event_evidence: bool                    # Combined from reference/tracker
    sensor_fault_evidence: bool                     # Combined from reference/tracker
    reasoning_summary: str                          # Human-readable trace


# ---------------------------------------------------------------------------
# Adjudicator
# ---------------------------------------------------------------------------
class DecisionAdjudicator:
    """Deterministic rule-based adjudicator.

    Combines outputs from:
    - Phase 3A: ``AnomalyResult`` (anomaly_score, triggers, channel_scores)
    - Phase 3B: reference/tracker evidence dicts (plausibility_score,
      weather_event_evidence, sensor_fault_evidence)
    - Integrity flags from the ingestion gate

    into a final ``AdjudicationResult``.
    """

    # Thresholds (deterministic, documented)
    ANOMALY_SCORE_SUSPECT = 0.35      # anomaly_score >= this → SUSPECT
    ANOMALY_SCORE_ANOMALOUS = 0.65    # anomaly_score >= this → ANOMALOUS
    PLAUSIBILITY_LOW = 0.4            # plausibility < this → low confidence
    MIN_EVIDENCE_FOR_CONFIDENT = 3    # need >= 3 evidence codes for HIGH confidence

    def adjudicate(
        self,
        *,
        # Phase 3A outputs
        anomaly_score: float,
        triggers: List[str],
        channel_scores: Dict[str, float],
        # Phase 3B outputs (reference)
        ref_plausibility: float,
        ref_weather_evidence: bool,
        ref_sensor_fault: bool,
        # Phase 3B outputs (tracker)
        tracker_plausibility: float,
        tracker_weather_evidence: bool,
        tracker_sensor_fault: bool,
        # Integrity context
        integrity_flags: Optional[List[str]] = None,
        admission_state: str = "ADMIT",
        # History size for cold-start detection
        buffer_size: int = 0,
    ) -> AdjudicationResult:
        """Produce a complete, traceable decision."""

        integrity_flags = integrity_flags or []
        evidence_codes: List[str] = list(triggers)  # start with statistical triggers

        # ------------------------------------------------------------------
        # 1. Cold-start detection
        # ------------------------------------------------------------------
        cold_start = buffer_size < 6
        if cold_start:
            evidence_codes.append("COLD_START_INSUFFICIENT_HISTORY")

        # ------------------------------------------------------------------
        # 2. Combine plausibility from reference and tracker
        # ------------------------------------------------------------------
        # Weight reference more heavily (long-term) unless we are cold-starting
        if buffer_size >= 6:
            combined_plausibility = 0.6 * ref_plausibility + 0.4 * tracker_plausibility
        else:
            # Cold-start: tracker has no data, use reference only
            combined_plausibility = ref_plausibility

        # ------------------------------------------------------------------
        # 3. Combine weather / fault evidence from reference and tracker
        # ------------------------------------------------------------------
        # Fault is flagged if EITHER reference OR tracker says fault
        combined_fault = ref_sensor_fault or tracker_sensor_fault
        # Weather requires BOTH to agree (conservative)
        combined_weather = ref_weather_evidence and tracker_weather_evidence

        if combined_fault:
            evidence_codes.append("SENSOR_FAULT_EVIDENCE_FROM_REFERENCE_OR_TRACKER")
        if combined_weather:
            evidence_codes.append("WEATHER_EVENT_EVIDENCE_MULTIVARIATE_CONSISTENT")

        # ------------------------------------------------------------------
        # 4. Integrity-flag based evidence
        # ------------------------------------------------------------------
        data_issue_flags = {
            "COMMUNICATION_GAP", "MISSING_EXPECTED_RECORD",
            "LATE_OUT_OF_ORDER", "DUPLICATE", "CONFLICTING_DUPLICATE",
        }
        has_data_issue = any(f in data_issue_flags for f in integrity_flags)
        if has_data_issue:
            evidence_codes.append("DATA_TELEMETRY_INTEGRITY_FLAG")

        range_violation = "RANGE_VIOLATION" in integrity_flags
        if range_violation:
            evidence_codes.append("HARD_RANGE_VIOLATION")

        quarantined = admission_state in ("QUARANTINE", "REJECT")
        if quarantined:
            evidence_codes.append("OBSERVATION_QUARANTINED_OR_REJECTED")

        # ------------------------------------------------------------------
        # 5. Root-cause classification
        # ------------------------------------------------------------------
        frozen_triggers = [t for t in triggers if "FROZEN" in t]
        spike_triggers = [t for t in triggers if "SPIKE" in t]
        rate_triggers = [t for t in triggers if "UNREALISTIC_RATE" in t]
        thermo_triggers = [t for t in triggers if "THERMODYNAMIC" in t]
        z_triggers = [t for t in triggers if "ROBUST_ZSCORE" in t]

        root_cause = RootCause.NORMAL

        if has_data_issue and anomaly_score < self.ANOMALY_SCORE_SUSPECT:
            root_cause = RootCause.DATA_TELEMETRY_ISSUE
        elif frozen_triggers:
            root_cause = RootCause.SENSOR_STUCK_FROZEN
        elif spike_triggers and combined_fault:
            root_cause = RootCause.SENSOR_SPIKE
        elif spike_triggers and combined_weather:
            root_cause = RootCause.POSSIBLE_WEATHER_EVENT
        elif thermo_triggers or (combined_fault and not spike_triggers and not frozen_triggers):
            root_cause = RootCause.MULTIVARIATE_INCONSISTENCY
        elif rate_triggers:
            root_cause = RootCause.TEMPORAL_INCONSISTENCY
        elif z_triggers and not combined_fault:
            root_cause = RootCause.GRADUAL_DRIFT
        elif combined_weather and anomaly_score >= self.ANOMALY_SCORE_SUSPECT:
            root_cause = RootCause.POSSIBLE_WEATHER_EVENT
        elif anomaly_score >= self.ANOMALY_SCORE_SUSPECT:
            root_cause = RootCause.UNKNOWN

        # ------------------------------------------------------------------
        # 6. Decision state
        # ------------------------------------------------------------------
        if quarantined:
            decision_state = "ANOMALOUS"
        elif anomaly_score >= self.ANOMALY_SCORE_ANOMALOUS:
            decision_state = "ANOMALOUS"
        elif anomaly_score >= self.ANOMALY_SCORE_SUSPECT:
            # AMBIGUOUS when weather and fault evidence conflict
            if combined_weather and combined_fault:
                decision_state = "AMBIGUOUS"
            else:
                decision_state = "SUSPECT"
        elif has_data_issue:
            decision_state = "SUSPECT"
        else:
            decision_state = "NORMAL"

        # ABSTAIN when evidence is too thin and ambiguous
        competing = combined_weather and combined_fault
        if competing and anomaly_score >= self.ANOMALY_SCORE_SUSPECT and not frozen_triggers:
            decision_state = "ABSTAIN"

        # ------------------------------------------------------------------
        # 7. Severity
        # ------------------------------------------------------------------
        if decision_state == "NORMAL":
            severity = "LOW"
        elif decision_state in ("SUSPECT", "AMBIGUOUS", "ABSTAIN"):
            if anomaly_score >= 0.55 or combined_fault:
                severity = "HIGH"
            else:
                severity = "MODERATE"
        else:  # ANOMALOUS
            if frozen_triggers or thermo_triggers:
                severity = "CRITICAL"
            elif spike_triggers:
                severity = "HIGH"
            else:
                severity = "MODERATE"

        # ------------------------------------------------------------------
        # 8. Confidence
        # ------------------------------------------------------------------
        n_evidence = len([e for e in evidence_codes if not e.startswith("COLD")])

        # Detection confidence: based on anomaly score and evidence count
        if cold_start:
            detection_confidence = 0.4
        elif decision_state == "NORMAL":
            detection_confidence = max(0.7, 1.0 - anomaly_score)
        else:
            base = min(0.9, 0.4 + 0.1 * n_evidence)
            # Reduce confidence when evidence is ambiguous
            if competing:
                base = max(0.3, base - 0.2)
            detection_confidence = round(base, 3)

        # Attribution confidence: how sure we are about root cause
        if root_cause == RootCause.NORMAL:
            attribution_confidence = detection_confidence
        elif root_cause == RootCause.UNKNOWN or decision_state == "ABSTAIN":
            attribution_confidence = 0.2
        elif competing:
            attribution_confidence = 0.35
        else:
            attribution_confidence = min(0.9, 0.35 + 0.1 * n_evidence)
        attribution_confidence = round(attribution_confidence, 3)

        # ------------------------------------------------------------------
        # 9. Uncertainty state
        # ------------------------------------------------------------------
        if cold_start:
            uncertainty_state = UncertaintyState.COLD_START
        elif decision_state == "ABSTAIN":
            uncertainty_state = UncertaintyState.ABSTAIN
        elif competing or combined_plausibility < self.PLAUSIBILITY_LOW:
            uncertainty_state = UncertaintyState.HIGH
        elif n_evidence <= 1 and decision_state != "NORMAL":
            uncertainty_state = UncertaintyState.MODERATE
        else:
            uncertainty_state = UncertaintyState.LOW

        # ------------------------------------------------------------------
        # 10. Likelihood scores
        # ------------------------------------------------------------------
        # Weather likelihood: increases when weather evidence, decreases with fault
        if combined_weather and not combined_fault:
            weather_likelihood = max(0.5, combined_plausibility)
        elif combined_weather and combined_fault:
            weather_likelihood = 0.4  # ambiguous
        elif combined_fault:
            weather_likelihood = max(0.0, combined_plausibility - 0.3)
        else:
            weather_likelihood = combined_plausibility * 0.5  # mild

        # Sensor fault likelihood: inverse of weather, boosted by triggers
        if frozen_triggers:
            fault_likelihood = 0.9
        elif combined_fault and not combined_weather:
            fault_likelihood = min(0.9, 0.4 + 0.1 * len(spike_triggers + thermo_triggers))
        elif combined_fault and combined_weather:
            fault_likelihood = 0.4  # ambiguous
        else:
            fault_likelihood = anomaly_score * 0.4

        weather_likelihood = round(min(1.0, max(0.0, float(weather_likelihood))), 3)
        fault_likelihood = round(min(1.0, max(0.0, float(fault_likelihood))), 3)

        # ------------------------------------------------------------------
        # 11. Reasoning summary
        # ------------------------------------------------------------------
        reasons = []
        if frozen_triggers:
            reasons.append(f"Frozen/stuck sensor detected on: {', '.join(frozen_triggers)}")
        if spike_triggers:
            reasons.append(f"Step spike detected: {', '.join(spike_triggers)}")
        if rate_triggers:
            reasons.append(f"Unrealistic rate-of-change: {', '.join(rate_triggers)}")
        if thermo_triggers:
            reasons.append("Thermodynamic inconsistency: dewpoint exceeds temperature")
        if z_triggers:
            reasons.append(f"Statistical Z-score excursion: {', '.join(z_triggers)}")
        if combined_weather:
            reasons.append("Multivariate T/P/RH pattern consistent with a weather event")
        if combined_fault:
            reasons.append("Reference or tracker deviation suggests possible sensor fault")
        if has_data_issue:
            reasons.append(f"Data/telemetry integrity flags: {', '.join(f for f in integrity_flags if f in data_issue_flags)}")
        if cold_start:
            reasons.append("Cold-start: insufficient history for robust assessment")
        if not reasons:
            reasons.append("No anomaly signals detected; observation within expected range")

        reasoning_summary = " | ".join(reasons)

        return AdjudicationResult(
            decision_state=decision_state,
            severity=severity,
            detection_confidence=round(detection_confidence, 3),
            attribution_confidence=attribution_confidence,
            uncertainty_state=uncertainty_state,
            root_cause_category=root_cause,
            evidence_codes=evidence_codes,
            weather_event_likelihood=weather_likelihood,
            sensor_fault_likelihood=fault_likelihood,
            anomaly_score=round(float(anomaly_score), 4),
            plausibility_score=round(float(combined_plausibility), 4),
            weather_event_evidence=bool(combined_weather),
            sensor_fault_evidence=bool(combined_fault),
            reasoning_summary=reasoning_summary,
        )


# Module-level singleton
adjudicator = DecisionAdjudicator()
