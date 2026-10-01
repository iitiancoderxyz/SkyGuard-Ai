"""
Unit & Integration Test Suite for UNIT B — Scenario Testbed & Progression Stages (Repair 2).
Verifies all 10 standard scenarios:
1. NOMINAL
2. SPIKE
3. FLATLINE
4. DRIFT
5. BIAS
6. NOISE
7. COMMUNICATION_GAP
8. MULTIVARIATE_INCONSISTENCY
9. GENUINE_WEATHER
10. COMBINED
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


ALL_SCENARIOS = [
    "NOMINAL",
    "SPIKE",
    "FLATLINE",
    "DRIFT",
    "BIAS",
    "NOISE",
    "COMMUNICATION_GAP",
    "MULTIVARIATE_INCONSISTENCY",
    "GENUINE_WEATHER",
    "COMBINED",
]


@pytest.mark.parametrize("scen_name", ALL_SCENARIOS)
def test_scenario_execution_and_stage_breakdown(client, scen_name):
    """Verifies that each scenario returns all 4 key stages and satisfies validation criteria."""
    station_id = f"AWS_SCEN_TEST_{scen_name}"
    res = client.post(
        f"/v1/simulator/scenarios/{scen_name}/run?station_id={station_id}&num_points=25&seed=42"
    )
    assert res.status_code == 200
    data = res.json()

    # 1. Structure Verification
    assert data["scenario"] == scen_name
    assert "target_channels" in data
    assert "baseline_decision" in data
    assert "transition_decision" in data
    assert "peak_decision" in data
    assert "final_decision" in data
    assert "validation" in data
    assert "sample_decisions" in data

    # 2. Key Stage Decision Verification
    baseline_d = data["baseline_decision"]
    transition_d = data["transition_decision"]
    peak_d = data["peak_decision"]
    final_d = data["final_decision"]

    assert baseline_d is not None
    assert transition_d is not None
    assert peak_d is not None
    assert final_d is not None

    # Baseline should be normal
    assert baseline_d["decision_state"] == "NORMAL"

    # Peak decision should have complete real backend intelligence fields
    assert "decision_state" in peak_d
    assert "anomaly_score" in peak_d
    assert "severity" in peak_d
    assert "root_cause_category" in peak_d
    assert "reasoning_summary" in peak_d
    assert "evidence_codes" in peak_d
    assert isinstance(peak_d["evidence_codes"], list)

    # 3. Acceptance Validation
    val = data["validation"]
    assert val["expected"] is not None
    assert val["actual"] is not None
    assert val["passed"] is True, f"Scenario {scen_name} failed validation: {val}"


def test_scenario_list_endpoint(client):
    """Verifies scenario catalog endpoint returns all standard scenarios."""
    res = client.get("/v1/simulator/scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) == 10
    names = [s["name"] for s in scenarios]
    for s in ALL_SCENARIOS:
        assert s in names
