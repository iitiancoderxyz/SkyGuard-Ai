"""
Integration test for Dashboard API Client against live FastAPI server.
"""
from dashboard.api_client import APIClient
from fastapi.testclient import TestClient
from app.main import app
import pytest


def test_dashboard_client_smoke(monkeypatch):
    """Verify that Dashboard API client interacts correctly with backend routes."""
    test_client = TestClient(app)

    # Monkeypatch requests calls in APIClient to route through TestClient
    def mock_get(url, *args, **kwargs):
        path = url.replace("http://127.0.0.1:8000", "")
        return test_client.get(path, params=kwargs.get("params"))

    def mock_post(url, *args, **kwargs):
        path = url.replace("http://127.0.0.1:8000", "")
        return test_client.post(path, json=kwargs.get("json"), params=kwargs.get("params"))

    monkeypatch.setattr("requests.get", mock_get)
    monkeypatch.setattr("requests.post", mock_post)

    client = APIClient(base_url="http://127.0.0.1:8000")
    
    # 1. Health check
    h = client.get_health()
    assert h["status"] == "ok"
    assert h["database"] == "connected"

    # 2. Status check
    st = client.get_status()
    assert "project" in st
    assert st["project"] == "TRUST-TWIN"

    # 3. Observation submit
    payload = {
        "station_id": "AWS_DASH_01",
        "timestamp": "2026-09-30T11:00:00Z",
        "temperature": 27.2,
        "pressure": 1010.5,
        "relative_humidity": 70.0,
        "source_type": "LIVE",
    }
    res = client.submit_observation(payload)
    assert res["status_code"] == 200
    assert res["data"]["station_id"] == "AWS_DASH_01"

    # 4. Station observations & decisions
    obs = client.get_station_observations("AWS_DASH_01", limit=10)
    assert len(obs) >= 1
    assert obs[0]["station_id"] == "AWS_DASH_01"
    assert "temperature" in obs[0]
    assert "anomaly_score" in obs[0]

    # 5. Station health diagnostics
    health_diag = client.get_station_health("AWS_DASH_01")
    assert health_diag["station_id"] == "AWS_DASH_01"
    assert "channel_availability" in health_diag
    assert "model_integrity" in health_diag
    assert health_diag["model_integrity"]["anti_poisoning_status"] == "PROTECTED"

    # 6. Decisions listing
    decs = client.list_decisions(station_id="AWS_DASH_01", limit=10)
    assert len(decs) >= 1

    # 7. Scenarios listing
    scens = client.list_scenarios()
    assert len(scens) >= 10
    scen_names = [s["name"] for s in scens]
    assert "NOMINAL" in scen_names
    assert "SPIKE" in scen_names
    assert "GENUINE_WEATHER" in scen_names

    # 8. Scenario execution via simulator API
    sim_res = client.run_scenario("SPIKE", station_id="AWS_SIM_TEST", num_points=15, seed=42)
    assert sim_res["status_code"] == 200
    assert sim_res["data"]["scenario"] == "SPIKE"
    assert sim_res["data"]["decisions_count"] == 15
