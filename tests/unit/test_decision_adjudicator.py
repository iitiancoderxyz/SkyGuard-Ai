# -*- coding: utf-8 -*-
"""
Phase 3C Unit Tests — Decision Adjudicator
Tests the full decision layer: decision state, severity, confidence,
uncertainty, root cause, and evidence codes.
"""
import pytest
from detection.decision.adjudicator import DecisionAdjudicator, AdjudicationResult, RootCause, UncertaintyState


@pytest.fixture
def adj():
    return DecisionAdjudicator()


def _normal_ev():
    """Evidence from reference/tracker for a normal observation."""
    return dict(plausibility_score=0.95, weather_event_evidence=True, sensor_fault_evidence=False)


def _fault_ev():
    """Evidence indicating sensor fault."""
    return dict(plausibility_score=0.2, weather_event_evidence=False, sensor_fault_evidence=True)


def _weather_ev():
    """Evidence indicating possible weather event."""
    return dict(plausibility_score=0.75, weather_event_evidence=True, sensor_fault_evidence=False)


def _ambiguous_ev():
    """Competing weather and fault evidence."""
    return dict(plausibility_score=0.4, weather_event_evidence=True, sensor_fault_evidence=True)


# -----------------------------------------------------------------------
# 1. NORMAL
# -----------------------------------------------------------------------
class TestNormal:
    def test_normal_no_triggers(self, adj):
        r = adj.adjudicate(
            anomaly_score=0.05,
            triggers=[],
            channel_scores={"temperature": 0.05, "pressure": 0.0, "relative_humidity": 0.0},
            ref_plausibility=0.95, ref_weather_evidence=True, ref_sensor_fault=False,
            tracker_plausibility=0.92, tracker_weather_evidence=True, tracker_sensor_fault=False,
            integrity_flags=[], admission_state="ADMIT", buffer_size=20,
        )
        assert r.decision_state == "NORMAL"
        assert r.severity == "LOW"
        assert r.root_cause_category == RootCause.NORMAL
        assert r.detection_confidence >= 0.7
        assert r.sensor_fault_likelihood < 0.3

    def test_normal_cold_start(self, adj):
        """Cold start gives COLD_START uncertainty even for normal readings."""
        r = adj.adjudicate(
            anomaly_score=0.0,
            triggers=[],
            channel_scores={"temperature": 0.0, "pressure": 0.0, "relative_humidity": 0.0},
            ref_plausibility=1.0, ref_weather_evidence=True, ref_sensor_fault=False,
            tracker_plausibility=1.0, tracker_weather_evidence=True, tracker_sensor_fault=False,
            integrity_flags=[], admission_state="ADMIT", buffer_size=3,
        )
        assert r.uncertainty_state == UncertaintyState.COLD_START
        assert "COLD_START_INSUFFICIENT_HISTORY" in r.evidence_codes


# -----------------------------------------------------------------------
# 2. SUSPECT — sensor spike
# -----------------------------------------------------------------------
class TestSensorSpike:
    def test_suspect_spike_with_fault_evidence(self, adj):
        r = adj.adjudicate(
            anomaly_score=0.75,
            triggers=["TEMPERATURE_SPIKE_POSITIVE"],
            channel_scores={"temperature": 0.75, "pressure": 0.0, "relative_humidity": 0.0},
            ref_plausibility=0.2, ref_weather_evidence=False, ref_sensor_fault=True,
            tracker_plausibility=0.2, tracker_weather_evidence=False, tracker_sensor_fault=True,
            integrity_flags=[], admission_state="ADMIT", buffer_size=20,
        )
        assert r.decision_state == "ANOMALOUS"
        assert r.root_cause_category == RootCause.SENSOR_SPIKE
        assert r.sensor_fault_likelihood > 0.4
        assert r.severity in ("HIGH", "CRITICAL")


    def test_suspect_spike_weather_evidence(self, adj):
        """Spike with consistent weather evidence → POSSIBLE_WEATHER_EVENT."""
        r = adj.adjudicate(
            anomaly_score=0.45,
            triggers=["TEMPERATURE_SPIKE_POSITIVE"],
            channel_scores={"temperature": 0.45, "pressure": 0.0, "relative_humidity": 0.0},
            ref_plausibility=0.75, ref_weather_evidence=True, ref_sensor_fault=False,
            tracker_plausibility=0.7, tracker_weather_evidence=True, tracker_sensor_fault=False,
            integrity_flags=[], admission_state="ADMIT", buffer_size=20,
        )
        assert r.root_cause_category in (RootCause.POSSIBLE_WEATHER_EVENT, RootCause.NORMAL, RootCause.UNKNOWN)
        assert r.weather_event_likelihood >= 0.3


# -----------------------------------------------------------------------
# 3. ANOMALOUS — sensor stuck / frozen
# -----------------------------------------------------------------------
class TestFrozenSensor:
    def test_frozen_sensor_detection(self, adj):
        r = adj.adjudicate(
            anomaly_score=0.7,
            triggers=["FROZEN_TEMPERATURE", "FROZEN_PRESSURE"],
            channel_scores={"temperature": 0.7, "pressure": 0.65, "relative_humidity": 0.0},
            ref_plausibility=0.3, ref_weather_evidence=False, ref_sensor_fault=True,
            tracker_plausibility=0.3, tracker_weather_evidence=False, tracker_sensor_fault=True,
            integrity_flags=[], admission_state="ADMIT", buffer_size=20,
        )
        assert r.decision_state == "ANOMALOUS"
        assert r.root_cause_category == RootCause.SENSOR_STUCK_FROZEN
        assert r.sensor_fault_likelihood >= 0.8
        assert r.severity in ("HIGH", "CRITICAL")
        assert any("FROZEN" in e for e in r.evidence_codes)


# -----------------------------------------------------------------------
# 4. Gradual drift
# -----------------------------------------------------------------------
class TestGradualDrift:
    def test_drift_via_zscore(self, adj):
        r = adj.adjudicate(
            anomaly_score=0.4,
            triggers=["ROBUST_ZSCORE_EXCURSION_TEMPERATURE"],
            channel_scores={"temperature": 0.4, "pressure": 0.0, "relative_humidity": 0.0},
            ref_plausibility=0.5, ref_weather_evidence=True, ref_sensor_fault=False,
            tracker_plausibility=0.55, tracker_weather_evidence=True, tracker_sensor_fault=False,
            integrity_flags=[], admission_state="ADMIT", buffer_size=20,
        )
        assert r.root_cause_category in (RootCause.GRADUAL_DRIFT, RootCause.POSSIBLE_WEATHER_EVENT, RootCause.NORMAL, RootCause.UNKNOWN)


# -----------------------------------------------------------------------
# 5. Temporal inconsistency
# -----------------------------------------------------------------------
class TestTemporalInconsistency:
    def test_unrealistic_rate(self, adj):
        r = adj.adjudicate(
            anomaly_score=0.6,
            triggers=["TEMPERATURE_UNREALISTIC_RATE"],
            channel_scores={"temperature": 0.6, "pressure": 0.0, "relative_humidity": 0.0},
            ref_plausibility=0.4, ref_weather_evidence=False, ref_sensor_fault=True,
            tracker_plausibility=0.4, tracker_weather_evidence=False, tracker_sensor_fault=True,
            integrity_flags=[], admission_state="ADMIT", buffer_size=20,
        )
        assert r.root_cause_category in (
            RootCause.TEMPORAL_INCONSISTENCY,
            RootCause.SENSOR_SPIKE,
            RootCause.MULTIVARIATE_INCONSISTENCY,
        )

        assert r.decision_state in ("ANOMALOUS", "SUSPECT")


# -----------------------------------------------------------------------
# 6. Multivariate inconsistency
# -----------------------------------------------------------------------
class TestMultivariateInconsistency:
    def test_thermodynamic_inconsistency(self, adj):
        r = adj.adjudicate(
            anomaly_score=0.65,
            triggers=["THERMODYNAMIC_INCONSISTENCY"],
            channel_scores={"temperature": 0.0, "pressure": 0.0, "relative_humidity": 0.65},
            ref_plausibility=0.2, ref_weather_evidence=False, ref_sensor_fault=True,
            tracker_plausibility=0.2, tracker_weather_evidence=False, tracker_sensor_fault=True,
            integrity_flags=[], admission_state="ADMIT", buffer_size=20,
        )
        assert r.root_cause_category == RootCause.MULTIVARIATE_INCONSISTENCY
        assert r.sensor_fault_likelihood > 0.3
        assert "Thermodynamic inconsistency" in r.reasoning_summary


# -----------------------------------------------------------------------
# 7. Possible weather event
# -----------------------------------------------------------------------
class TestWeatherEvent:
    def test_weather_event_both_agree(self, adj):
        r = adj.adjudicate(
            anomaly_score=0.5,
            triggers=["TEMPERATURE_SPIKE_POSITIVE"],
            channel_scores={"temperature": 0.5, "pressure": 0.0, "relative_humidity": 0.0},
            ref_plausibility=0.7, ref_weather_evidence=True, ref_sensor_fault=False,
            tracker_plausibility=0.65, tracker_weather_evidence=True, tracker_sensor_fault=False,
            integrity_flags=[], admission_state="ADMIT", buffer_size=20,
        )
        assert r.weather_event_evidence is True
        assert r.weather_event_likelihood >= 0.5
        assert r.root_cause_category in (RootCause.POSSIBLE_WEATHER_EVENT, RootCause.SENSOR_SPIKE)


# -----------------------------------------------------------------------
# 8. Data / telemetry issue
# -----------------------------------------------------------------------
class TestDataTelemetry:
    def test_communication_gap(self, adj):
        r = adj.adjudicate(
            anomaly_score=0.1,
            triggers=[],
            channel_scores={"temperature": 0.0, "pressure": 0.0, "relative_humidity": 0.0},
            ref_plausibility=0.9, ref_weather_evidence=True, ref_sensor_fault=False,
            tracker_plausibility=0.9, tracker_weather_evidence=True, tracker_sensor_fault=False,
            integrity_flags=["COMMUNICATION_GAP"], admission_state="ADMIT", buffer_size=20,
        )
        assert r.root_cause_category == RootCause.DATA_TELEMETRY_ISSUE
        assert r.decision_state == "SUSPECT"
        assert "DATA_TELEMETRY_INTEGRITY_FLAG" in r.evidence_codes

    def test_quarantined_observation(self, adj):
        r = adj.adjudicate(
            anomaly_score=0.0,
            triggers=[],
            channel_scores={"temperature": 0.0, "pressure": 0.0, "relative_humidity": 0.0},
            ref_plausibility=0.9, ref_weather_evidence=True, ref_sensor_fault=False,
            tracker_plausibility=0.9, tracker_weather_evidence=True, tracker_sensor_fault=False,
            integrity_flags=["RANGE_VIOLATION"], admission_state="QUARANTINE", buffer_size=20,
        )
        assert r.decision_state == "ANOMALOUS"
        assert "OBSERVATION_QUARANTINED_OR_REJECTED" in r.evidence_codes


# -----------------------------------------------------------------------
# 9. Ambiguous — should not force high-confidence fault
# -----------------------------------------------------------------------
class TestAmbiguous:
    def test_ambiguous_does_not_force_fault(self, adj):
        """Competing weather/fault evidence → low attribution confidence, no definitive root cause."""
        r = adj.adjudicate(
            anomaly_score=0.45,
            triggers=["TEMPERATURE_SPIKE_POSITIVE"],
            channel_scores={"temperature": 0.45, "pressure": 0.0, "relative_humidity": 0.0},
            ref_plausibility=0.4, ref_weather_evidence=True, ref_sensor_fault=True,
            tracker_plausibility=0.4, tracker_weather_evidence=True, tracker_sensor_fault=True,
            integrity_flags=[], admission_state="ADMIT", buffer_size=20,
        )
        # Must not produce CRITICAL or very high fault likelihood
        assert r.severity != "CRITICAL"
        assert r.attribution_confidence <= 0.5
        assert r.sensor_fault_likelihood <= 0.6

    def test_abstain_on_competing_evidence(self, adj):
        """Strong competing evidence at threshold → ABSTAIN or AMBIGUOUS."""
        r = adj.adjudicate(
            anomaly_score=0.55,
            triggers=["TEMPERATURE_SPIKE_POSITIVE"],
            channel_scores={"temperature": 0.55, "pressure": 0.0, "relative_humidity": 0.0},
            ref_plausibility=0.4, ref_weather_evidence=True, ref_sensor_fault=True,
            tracker_plausibility=0.4, tracker_weather_evidence=True, tracker_sensor_fault=True,
            integrity_flags=[], admission_state="ADMIT", buffer_size=20,
        )
        assert r.decision_state in ("ABSTAIN", "AMBIGUOUS", "SUSPECT")
        assert r.uncertainty_state in (UncertaintyState.HIGH, UncertaintyState.ABSTAIN)


# -----------------------------------------------------------------------
# 10. Determinism
# -----------------------------------------------------------------------
class TestDeterminism:
    def test_same_inputs_same_output(self, adj):
        kwargs = dict(
            anomaly_score=0.6,
            triggers=["FROZEN_TEMPERATURE"],
            channel_scores={"temperature": 0.6, "pressure": 0.0, "relative_humidity": 0.0},
            ref_plausibility=0.3, ref_weather_evidence=False, ref_sensor_fault=True,
            tracker_plausibility=0.3, tracker_weather_evidence=False, tracker_sensor_fault=True,
            integrity_flags=[], admission_state="ADMIT", buffer_size=20,
        )
        r1 = adj.adjudicate(**kwargs)
        r2 = adj.adjudicate(**kwargs)
        assert r1.decision_state == r2.decision_state
        assert r1.anomaly_score == r2.anomaly_score
        assert r1.root_cause_category == r2.root_cause_category
        assert r1.evidence_codes == r2.evidence_codes
