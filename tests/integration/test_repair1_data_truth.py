"""
Validation Suite for REPAIR 1: DATA TRUTH and DECISION PERSISTENCE.
Verifies that:
1. Normal observation -> decision_state persists as NORMAL.
2. Known anomalous observation -> anomaly_score, severity, root cause persist, and decision_state persists as ANOMALY/ANOMALOUS.
3. Suspect observation -> decision_state persists as SUSPECT.
4. reasoning_summary survives persistence and retrieval via API/repository.
5. evidence_codes survive persistence and retrieval via API/repository.
6. Raw observations remain strictly immutable.
7. Existing observation, station, and decisions endpoints return complete data truth.
"""
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from storage.repositories.observation_repo import obs_repo
from storage.repositories.station_repo import station_repo


@pytest.fixture
def client():
    return TestClient(app)


def test_1_normal_observation_persistence(client):
    """TEST 1: Normal observation -> decision_state persists -> API returns NORMAL."""
    station_id = f"AWS_TRUTH_NORM_{uuid.uuid4().hex[:8]}"
    station_repo.upsert_station(station_id)
    t0 = datetime.now(timezone.utc) - timedelta(minutes=15)

    # Ingest clean diurnal observations to warm up baseline
    for i in range(12):
        payload = {
            "station_id": station_id,
            "timestamp": (t0 + timedelta(minutes=i)).isoformat(),
            "temperature": 24.0 + (i % 4) * 0.15,
            "pressure": 1013.25 - (i % 3) * 0.1,
            "relative_humidity": 55.0 + (i % 5) * 0.2,
            "source_type": "LIVE",
        }
        res = client.post("/v1/observations", json=payload)
        assert res.status_code == 200

    # Query historical observations endpoint
    res_obs = client.get(f"/v1/stations/{station_id}/observations?limit=5")
    assert res_obs.status_code == 200
    records = res_obs.json()
    assert len(records) > 0
    latest = records[0]

    assert latest["decision_state"] == "NORMAL"
    assert latest["anomaly_score"] is not None
    assert latest["anomaly_score"] < 0.35
    assert latest["root_cause_category"] == "NORMAL"


def test_2_anomalous_observation_persistence(client):
    """TEST 2: Known anomalous observation -> anomaly_score/severity/root cause persist -> decision_state persists as ANOMALY/ANOMALOUS."""
    station_id = f"AWS_TRUTH_SPIKE_{uuid.uuid4().hex[:8]}"
    station_repo.upsert_station(station_id)
    t0 = datetime.now(timezone.utc) - timedelta(minutes=15)

    # Warm up with 10 clean varied points
    for i in range(10):
        client.post("/v1/observations", json={
            "station_id": station_id,
            "timestamp": (t0 + timedelta(minutes=i)).isoformat(),
            "temperature": 24.0 + (i % 3) * 0.2,
            "pressure": 1013.0 - (i % 2) * 0.1,
            "relative_humidity": 50.0 + (i % 4) * 0.2,
            "source_type": "LIVE",
        })

    # Ingest severe temperature spike (+30°C)
    spike_payload = {
        "station_id": station_id,
        "timestamp": (t0 + timedelta(minutes=11)).isoformat(),
        "temperature": 55.0,
        "pressure": 1013.0,
        "relative_humidity": 50.0,
        "source_type": "LIVE",
    }
    res_spike = client.post("/v1/observations", json=spike_payload)
    assert res_spike.status_code == 200
    spike_dec = res_spike.json()
    assert spike_dec["decision_state"] in ["ANOMALY", "ANOMALOUS"]
    assert spike_dec["anomaly_score"] >= 0.65
    assert spike_dec["root_cause_category"] == "SENSOR_SPIKE"

    # Query historical observations from database
    res_hist = client.get(f"/v1/stations/{station_id}/observations?limit=5")
    assert res_hist.status_code == 200
    hist_records = res_hist.json()
    latest_hist = hist_records[0]

    # PROVE: decision_state, anomaly_score, severity, root cause survived persistence
    assert latest_hist["decision_state"] in ["ANOMALY", "ANOMALOUS"]
    assert latest_hist["anomaly_score"] >= 0.65
    assert latest_hist["severity"] in ["HIGH", "CRITICAL"]
    assert latest_hist["root_cause_category"] == "SENSOR_SPIKE"


def test_3_suspect_observation_persistence(client):
    """TEST 3: Suspect observation -> decision_state persists as SUSPECT."""
    station_id = f"AWS_TRUTH_SUSPECT_{uuid.uuid4().hex[:8]}"
    station_repo.upsert_station(station_id)
    t0 = datetime.now(timezone.utc) - timedelta(minutes=20)

    # Warm up buffer with 12 clean points
    for i in range(12):
        client.post("/v1/observations", json={
            "station_id": station_id,
            "timestamp": (t0 + timedelta(minutes=i)).isoformat(),
            "temperature": 22.0 + (i % 4) * 0.15,
            "pressure": 1012.0 - (i % 3) * 0.1,
            "relative_humidity": 55.0 + (i % 5) * 0.2,
            "source_type": "LIVE",
        })

    # Submit mild rate jump (0.55 deg C in 1 min, above max rate 0.50 C/min -> score 0.55 -> SUSPECT)
    last_t = 22.0 + (11 % 4) * 0.15
    suspect_payload = {
        "station_id": station_id,
        "timestamp": (t0 + timedelta(minutes=12)).isoformat(),
        "temperature": last_t + 0.55,
        "pressure": 1012.0,
        "relative_humidity": 55.0,
        "source_type": "LIVE",
    }
    res_sus = client.post("/v1/observations", json=suspect_payload)
    assert res_sus.status_code == 200
    dec = res_sus.json()
    assert dec["decision_state"] in ["SUSPECT", "AMBIGUOUS"]
    assert 0.35 <= dec["anomaly_score"] < 0.65

    # Verify database persistence
    res_hist = client.get(f"/v1/stations/{station_id}/observations?limit=5")
    assert res_hist.status_code == 200
    hist_records = res_hist.json()
    latest_hist = hist_records[0]
    assert latest_hist["decision_state"] in ["SUSPECT", "AMBIGUOUS"]
    assert 0.35 <= latest_hist["anomaly_score"] < 0.65


def test_4_and_5_reasoning_and_evidence_codes_persistence(client):
    """TEST 4 & 5: reasoning_summary and evidence_codes survive persistence and retrieval."""
    station_id = f"AWS_TRUTH_EXPLAIN_{uuid.uuid4().hex[:8]}"
    station_repo.upsert_station(station_id)
    t0 = datetime.now(timezone.utc) - timedelta(minutes=15)

    # Warm up buffer
    for i in range(10):
        client.post("/v1/observations", json={
            "station_id": station_id,
            "timestamp": (t0 + timedelta(minutes=i)).isoformat(),
            "temperature": 22.0 + (i % 4) * 0.15,
            "pressure": 1012.0 - (i % 3) * 0.1,
            "relative_humidity": 50.0 + (i % 5) * 0.2,
            "source_type": "LIVE",
        })

    # Step spike on pressure (-25 hPa)
    payload = {
        "station_id": station_id,
        "timestamp": (t0 + timedelta(minutes=10)).isoformat(),
        "temperature": 22.0,
        "pressure": 987.0,
        "relative_humidity": 50.0,
        "source_type": "LIVE",
    }
    res = client.post("/v1/observations", json=payload)
    assert res.status_code == 200
    dec = res.json()

    assert dec["reasoning_summary"] is not None
    assert len(dec["reasoning_summary"]) > 0
    assert len(dec["evidence_codes"]) > 0
    assert "PRESSURE_SPIKE_NEGATIVE" in dec["evidence_codes"] or any("PRESSURE" in c for c in dec["evidence_codes"])

    # Query historical observations endpoint
    res_hist = client.get(f"/v1/stations/{station_id}/observations?limit=5")
    assert res_hist.status_code == 200
    latest_hist = res_hist.json()[0]

    # PROVE: reasoning_summary and evidence_codes are returned from database query
    assert latest_hist["reasoning_summary"] == dec["reasoning_summary"]
    assert isinstance(latest_hist["evidence_codes"], list)
    assert set(latest_hist["evidence_codes"]) == set(dec["evidence_codes"])


def test_6_and_7_raw_observation_immutability(client):
    """TEST 7: Raw observations remain immutable under database triggers."""
    station_id = f"AWS_TRUTH_IMMUT_{uuid.uuid4().hex[:8]}"
    payload = {
        "station_id": station_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": 28.5,
        "pressure": 1008.2,
        "relative_humidity": 65.0,
        "source_type": "LIVE",
    }
    res = client.post("/v1/observations", json=payload)
    assert res.status_code == 200
    obs_id = res.json()["observation_id"]

    # Attempt to update raw observation in SQLite directly -> MUST ABORT
    with pytest.raises(Exception) as excinfo:
        with obs_repo.db.transaction() as conn:
            conn.execute(
                "UPDATE raw_observations SET temperature_raw = 99.9 WHERE observation_id = ?",
                (obs_id,),
            )
    assert "Raw observations are strictly immutable" in str(excinfo.value)


def test_8_observation_by_id_and_decisions_endpoint(client):
    """TEST 8: Direct get_observation_by_id and /v1/decisions endpoints return complete data."""
    station_id = f"AWS_TRUTH_DEC_{uuid.uuid4().hex[:8]}"
    payload = {
        "station_id": station_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": 45.0,
        "pressure": 1000.0,
        "relative_humidity": 30.0,
        "source_type": "LIVE",
    }
    res = client.post("/v1/observations", json=payload)
    obs_id = res.json()["observation_id"]

    # Test obs_repo.get_observation_by_id
    obs_record = obs_repo.get_observation_by_id(obs_id)
    assert obs_record is not None
    assert obs_record["observation_id"] == obs_id
    assert obs_record["decision_state"] is not None
    assert isinstance(obs_record["evidence_codes"], list)

    # Test /v1/decisions endpoint
    res_decs = client.get(f"/v1/decisions?station_id={station_id}&limit=5")
    assert res_decs.status_code == 200
    decs_list = res_decs.json()
    assert len(decs_list) >= 1
    d_item = decs_list[0]
    assert d_item["decision_state"] is not None
    assert isinstance(d_item["evidence_codes"], list)
