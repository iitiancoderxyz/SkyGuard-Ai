"""
End-to-end integration tests for Phase 1.
Tests FastAPI HTTP endpoints, database persistence, replay determinism, and simulator.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from app.main import app
from simulator.stream.generator import AWSStreamGenerator
from simulator.replay.replayer import StreamReplayer
from storage.db.connection import db


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_and_ready_endpoints(client):
    res_h = client.get("/health")
    assert res_h.status_code == 200
    data_h = res_h.json()
    assert data_h["status"] == "ok"
    assert data_h["database"] == "connected"

    res_r = client.get("/ready")
    assert res_r.status_code == 200
    assert res_r.json()["status"] == "READY"


def test_post_observation_success(client):
    payload = {
        "station_id": "AWS_E2E_01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": 28.5,
        "pressure": 1008.2,
        "relative_humidity": 65.0,
        "source_type": "LIVE",
    }
    res = client.post("/v1/observations", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["observation_id"].startswith("obs-AWS_E2E_01-")
    assert data["integrity_status"] == "ACCEPT"
    assert data["disposition"] == "ACCEPT"
    assert data["decision_state"] == "NORMAL"


def test_post_observation_extra_field_rejected(client):
    """INV-01: Extraneous meteorological variable triggers HTTP 422."""
    payload = {
        "station_id": "AWS_E2E_01",
        "timestamp": "2026-09-30T10:00:00Z",
        "temperature": 28.5,
        "pressure": 1008.2,
        "relative_humidity": 65.0,
        "wind_speed": 12.0,  # Invalid
    }
    res = client.post("/v1/observations", json=payload)
    assert res.status_code == 422
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_station_list_and_query(client):
    res = client.get("/v1/stations")
    assert res.status_code == 200
    stations = res.json()
    station_ids = [s["station_id"] for s in stations]
    assert "AWS_E2E_01" in station_ids

    res_obs = client.get("/v1/stations/AWS_E2E_01/observations")
    assert res_obs.status_code == 200
    obs_list = res_obs.json()
    assert len(obs_list) >= 1


def test_replay_determinism():
    gen1 = AWSStreamGenerator(station_id="AWS_DET", seed=123)
    gen2 = AWSStreamGenerator(station_id="AWS_DET", seed=123)
    t0 = datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc)
    
    seq1 = gen1.generate(start_time=t0, num_points=5)
    seq2 = gen2.generate(start_time=t0, num_points=5)

    for o1, o2 in zip(seq1, seq2):
        assert o1.temperature == o2.temperature
        assert o1.pressure == o2.pressure
        assert o1.relative_humidity == o2.relative_humidity
