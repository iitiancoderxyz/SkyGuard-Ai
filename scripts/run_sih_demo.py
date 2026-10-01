"""
TRUST-TWIN / SkyGuard AI -- End-to-End SIH Demonstration Script (Phase 6).
Demonstrates all 9 required operational scenarios through the live pipeline:
1. NORMAL Diurnal Observations
2. Isolated Temperature Spike
3. Temperature Drop (Genuine Cold Front Event vs Fault)
4. Frozen / Stuck Flatline Sensor
5. Gradual Sensor Calibration Drift
6. Rapid Unrealistic Change (Pressure Bias Jump)
7. Excessive High-Frequency Sensor Noise
8. Multivariate Thermodynamic Inconsistency
9. Communication Gap / Packet Loss with Late Recovery
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone
from simulator.scenarios.suite import ScenarioSuite
from simulator.replay.replayer import StreamReplayer
from storage.repositories.observation_repo import obs_repo
from storage.repositories.station_repo import station_repo


def run_full_sih_demo():
    print("=" * 80)
    print("SKYGUARD AI / TRUST-TWIN: SIH26073 DEMONSTRATION SUITE")
    print("AI/ML Intelligent Anomaly Detection & Sensor Health for Automatic Weather Stations")
    print("=" * 80)

    suite = ScenarioSuite(seed=42)
    replayer = StreamReplayer()

    scenarios = [
        ("NOMINAL", "1. Nominal Diurnal Stream", "Clean meteorological cycles"),
        ("SPIKE", "2. Isolated Temperature Spike", "+25.0 C sensor spike on T channel"),
        ("GENUINE_WEATHER", "3. Genuine Cold Front Event", "Drop in T (-9 C), surge in RH (+40%), jump in P (+4 hPa)"),
        ("FLATLINE", "4. Frozen / Stuck Sensor", "Temperature sensor stuck for consecutive steps"),
        ("DRIFT", "5. Gradual Sensor Drift", "Progressive +1.5%/step calibration drift on RH"),
        ("BIAS", "6. Sudden Pressure Bias", "Sudden -20.0 hPa barometric step shift"),
        ("NOISE", "7. Excessive Noise", "Degraded circuit with high variance noise"),
        ("MULTIVARIATE_INCONSISTENCY", "8. Multivariate Inconsistency", "Thermodynamic conflict between T, P, and Dewpoint"),
        ("COMMUNICATION_GAP", "9. Communication Packet Loss", "Missing telemetry slots with late recovery"),
        ("COMBINED", "10. Combined Fault Suite", "Simultaneous spike, gap, and flatline fault injection"),
    ]

    for code, title, desc in scenarios:
        print(f"\n[Scenario] Running: {title}")
        print(f"  Description: {desc}")
        
        station_id = f"AWS_DEMO_{code}"
        obs_list, meta = suite.create_scenario(scenario_name=code, station_id=station_id, num_points=15)
        decisions = replayer.replay(obs_list)
        
        # Analyze decisions
        anom_count = sum(1 for d in decisions if d.decision_state.value in ["ANOMALY", "SUSPECT", "AMBIGUOUS"])
        max_score = max((d.anomaly_score or 0.0) for d in decisions)
        
        # Pick representative decision (the peak anomaly if any, else normal)
        rep_dec = max(decisions, key=lambda d: d.anomaly_score or 0.0) if decisions else None
        
        print(f"  Processed: {len(decisions)} observations through single-entry pipeline")
        print(f"  Flagged Anomalies/Suspects: {anom_count}/{len(decisions)}")
        print(f"  Peak Anomaly Score: {max_score:.3f}")
        
        if rep_dec:
            print(f"  Representative Decision:")
            print(f"    - State: {rep_dec.decision_state.value} | Severity: {rep_dec.severity.value if rep_dec.severity else 'LOW'}")
            print(f"    - Root Cause: {rep_dec.root_cause_category or 'NORMAL'}")
            print(f"    - Detection Conf: {rep_dec.detection_confidence:.2f} | Attribution Conf: {rep_dec.attribution_confidence:.2f}")
            print(f"    - Weather Likelihood: {rep_dec.weather_event_likelihood:.2f} | Sensor Fault Likelihood: {rep_dec.sensor_fault_likelihood:.2f}")
            print(f"    - Evidence Codes: {rep_dec.evidence_codes}")
            print(f"    - Baseline Admission: {rep_dec.admission_state.value}")
            print(f"    - Reasoning Summary: {rep_dec.reasoning_summary}")

    print("\n" + "=" * 80)
    print("SUCCESS: All 10 SIH Demonstration Scenarios Executed Successfully.")
    print("All decisions persisted in SQLite WAL database and available in Streamlit Dashboard.")
    print("=" * 80)


if __name__ == "__main__":
    run_full_sih_demo()
