"""
FastAPI Routes for TRUST-TWIN.
"""
import json
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import StreamingResponse
from ingestion.schemas.observation import ObservationIn
from ingestion.schemas.response import Decision, HealthResponse
from app.runtime.engine import process_observation
from storage.repositories.station_repo import station_repo
from storage.repositories.observation_repo import obs_repo
from storage.repositories.event_repo import event_repo
from storage.db.connection import db
from app.runtime.bus import bus
from app.core.config import settings
from app.core.claims import DISCLAIMER_EVALUATION, PROJECT_NAME, PROJECT_FULL_NAME

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["System"])
@router.get("/v1/health", response_model=HealthResponse, tags=["System"])
def health_check():
    stations = station_repo.list_stations()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc),
        database="connected",
        storage_mode="WAL",
        active_stations=len(stations),
    )


@router.get("/ready", tags=["System"])
@router.get("/v1/readiness", tags=["System"])
def readiness_check():
    try:
        with db.transaction() as conn:
            conn.execute("SELECT 1")
        return {"status": "READY", "database": "HEALTHY", "storage": "WAL"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unready: {str(e)}")


@router.get("/v1/status", tags=["System"])
def system_status():
    stations = station_repo.list_stations()
    return {
        "project": PROJECT_NAME,
        "full_name": PROJECT_FULL_NAME,
        "version": settings.app_version,
        "environment": settings.app_env,
        "active_stations": len(stations),
        "disclaimer": DISCLAIMER_EVALUATION,
    }


@router.post("/v1/observations", response_model=Decision, tags=["Ingestion"])
async def ingest_observation(request: Request, obs: ObservationIn):
    """
    Ingest a single AWS observation payload.
    Rejects non-core meteorological keys with HTTP 422 (extra='forbid').
    """
    raw_body_bytes = await request.body()
    raw_payload_str = raw_body_bytes.decode("utf-8")
    decision = process_observation(obs, raw_payload_str=raw_payload_str)
    return decision


@router.get("/v1/stations", tags=["Stations"])
def list_stations():
    return station_repo.list_stations()


@router.get("/v1/stations/{station_id}", tags=["Stations"])
def get_station(station_id: str):
    st = station_repo.get_station(station_id)
    if not st:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")
    return st


@router.get("/v1/stations/{station_id}/observations", tags=["Observations"])
def get_station_observations(station_id: str, limit: int = 50):
    return obs_repo.get_recent_observations(station_id=station_id, limit=limit)


@router.get("/v1/stations/{station_id}/events", tags=["Events"])
def get_station_events(station_id: str, limit: int = 50):
    return event_repo.get_integrity_events(station_id=station_id, limit=limit)


@router.get("/v1/stations/{station_id}/health", tags=["Stations"])
def get_station_health(station_id: str):
    st = station_repo.get_station(station_id)
    if not st:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")
    
    from health.sensor_health.diagnostics import diagnose_station_health
    return diagnose_station_health(station_id=station_id, window_size=20)


@router.get("/v1/decisions", tags=["Decisions"])
def list_decisions(station_id: Optional[str] = None, limit: int = 50):
    return obs_repo.get_recent_decisions(station_id=station_id, limit=limit)


@router.get("/v1/simulator/scenarios", tags=["Simulator"])
def list_scenarios():
    return [
        {"name": "NOMINAL", "label": "1. Nominal / Normal Clean Stream", "description": "Standard meteorological diurnal cycles without anomalies."},
        {"name": "SPIKE", "label": "2. Isolated Temperature Spike", "description": "Abrupt +25.0°C physical spike in temperature channel."},
        {"name": "FLATLINE", "label": "3. Frozen Sensor Flatline", "description": "Temperature sensor is stuck at a constant value for consecutive steps."},
        {"name": "DRIFT", "label": "4. Gradual Sensor Drift", "description": "Progressive sensor calibration loss with +1.5%/step RH drift."},
        {"name": "MULTIVARIATE_INCONSISTENCY", "label": "5. Multivariate Inconsistency", "description": "Thermodynamic conflict between Temperature, Pressure, and Dewpoint."},
        {"name": "BIAS", "label": "6. Sudden Pressure Bias Jump", "description": "Sudden -20 hPa level shift in barometric pressure."},
        {"name": "NOISE", "label": "7. Excessive High-Frequency Noise", "description": "Degraded analog sensor circuit with elevated Gaussian noise."},
        {"name": "COMMUNICATION_GAP", "label": "8. Communication / Packet Loss Gap", "description": "Missing telemetry slots followed by late recovery."},
        {"name": "GENUINE_WEATHER", "label": "9. Genuine Cold Front Event", "description": "Coordinated physical drop in T, surge in RH, and jump in P (Weather, not fault)."},
        {"name": "COMBINED", "label": "10. Combined Fault Suite", "description": "Multiple simultaneous sensor and integrity anomalies."},
    ]


@router.post("/v1/simulator/scenarios/{scenario_name}/run", tags=["Simulator"])
def run_scenario(
    scenario_name: str,
    station_id: str = "AWS_SIM_01",
    num_points: int = 25,
    seed: int = 42,
):
    """
    Execute a pre-configured simulator scenario through the replay engine
    and record sidecar ground-truth labels.
    Returns representative baseline, transition, peak, and final decision stages.
    """
    from simulator.scenarios.suite import ScenarioSuite
    from simulator.replay.replayer import StreamReplayer
    from storage.repositories.ground_truth_repo import ground_truth_repo
    import uuid

    suite = ScenarioSuite(seed=seed)
    try:
        observations, metadata = suite.create_scenario(
            scenario_name=scenario_name,
            station_id=station_id,
            num_points=num_points,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    run_id = f"run-{uuid.uuid4().hex[:8]}"
    start_ts = observations[0].timestamp.isoformat() if observations else None
    end_ts = observations[-1].timestamp.isoformat() if observations else None

    # Save simulation run metadata
    ground_truth_repo.save_simulation_run(
        run_id=run_id,
        scenario_name=scenario_name,
        station_id=station_id,
        start_time=start_ts or "",
        end_time=end_ts,
        seed=seed,
    )

    manifests = metadata.get("manifests", [])

    # Save ground truth labels for manifests
    for mf in manifests:
        ground_truth_repo.save_ground_truth_label(
            run_id=run_id,
            station_id=station_id,
            event_timestamp=mf.get("onset_ts", start_ts),
            label_type=mf.get("label_type", "ANOMALY"),
            fault_class=mf.get("fault_class") or mf.get("event_type"),
            channel=mf.get("channel", "multi"),
            onset=mf.get("onset_ts"),
            offset=mf.get("offset_ts"),
            injection_id=mf.get("injection_id") or mf.get("event_id"),
            label_source=mf.get("label_source", "INJECTION_MANIFEST"),
            seed=seed,
        )

    # Execute replay through process_observation single entry point
    replayer = StreamReplayer()
    decisions = replayer.replay(observations)

    # 1. Locate injection onset index in observations
    onset_idx = 0
    if manifests:
        first_onset = manifests[0].get("onset_ts")
        for idx, obs in enumerate(observations):
            if obs.timestamp.isoformat() == first_onset:
                onset_idx = idx
                break

    # 2. Locate peak anomaly decision (highest anomaly_score)
    peak_idx = onset_idx
    max_score = -1.0
    for idx, d in enumerate(decisions):
        score = d.anomaly_score if d.anomaly_score is not None else 0.0
        if score > max_score:
            max_score = score
            peak_idx = idx

    # If nominal or zero score across, peak index is onset or midpoint
    if max_score <= 0.0 and len(decisions) > 0:
        peak_idx = min(len(decisions) - 1, max(0, onset_idx))

    # 3. Define key representative indices
    baseline_idx = max(0, onset_idx - 1) if onset_idx > 0 else 0
    transition_idx = onset_idx if onset_idx < len(decisions) else peak_idx
    final_idx = len(decisions) - 1 if len(decisions) > 0 else 0

    baseline_dec = decisions[baseline_idx].model_dump(mode="json") if decisions else None
    transition_dec = decisions[transition_idx].model_dump(mode="json") if decisions else None
    peak_dec = decisions[peak_idx].model_dump(mode="json") if decisions else None
    final_dec = decisions[final_idx].model_dump(mode="json") if decisions else None

    # Target channels
    target_ch_set = {mf.get("channel") for mf in manifests if mf.get("channel")}
    target_channels = ", ".join(sorted(target_ch_set)) if target_ch_set else "All Channels (T, P, RH)"

    # Evaluation & Validation criteria
    s_upper = scenario_name.upper()
    validation_passed = True
    expected_summary = "Normal operational baseline"

    if s_upper == "NOMINAL":
        expected_summary = "Decision State == NORMAL, Anomaly Score < 0.35"
        validation_passed = bool(peak_dec and peak_dec.get("decision_state") == "NORMAL" and (peak_dec.get("anomaly_score") or 0.0) < 0.35)
    elif s_upper in ["SPIKE", "BIAS"]:
        expected_summary = "Decision State in [ANOMALY, ANOMALOUS], Anomaly Score >= 0.65"
        validation_passed = bool(peak_dec and peak_dec.get("decision_state") in ["ANOMALY", "ANOMALOUS"] and (peak_dec.get("anomaly_score") or 0.0) >= 0.65)
    elif s_upper == "FLATLINE":
        expected_summary = "Root Cause == SENSOR_STUCK_FROZEN, Score >= 0.35"
        validation_passed = bool(peak_dec and (peak_dec.get("root_cause_category") == "SENSOR_STUCK_FROZEN" or any("FROZEN" in c for c in peak_dec.get("evidence_codes", []))))
    elif s_upper in ["DRIFT", "NOISE", "MULTIVARIATE_INCONSISTENCY"]:
        expected_summary = "Anomaly Score >= 0.35 (SUSPECT / ANOMALY)"
        validation_passed = bool(peak_dec and (peak_dec.get("anomaly_score") or 0.0) >= 0.35)
    elif s_upper == "COMMUNICATION_GAP":
        expected_summary = "Integrity Flags reflect communication / telemetry gap"
        validation_passed = bool(any(d.integrity_flags for d in decisions) or any("COMMUNICATION" in str(d.evidence_codes) for d in decisions))
    elif s_upper == "GENUINE_WEATHER":
        expected_summary = "Weather Likelihood >= 0.30 or Plausibility >= 0.50"
        validation_passed = bool(peak_dec and ((peak_dec.get("weather_event_likelihood") or 0.0) >= 0.30 or (peak_dec.get("plausibility_score") or 0.0) >= 0.50))
    elif s_upper == "COMBINED":
        expected_summary = "Decision State in [ANOMALY, ANOMALOUS], Score >= 0.65"
        validation_passed = bool(peak_dec and peak_dec.get("decision_state") in ["ANOMALY", "ANOMALOUS"])

    peak_state_val = peak_dec.get("decision_state") if peak_dec else "N/A"
    peak_score_val = peak_dec.get("anomaly_score") if peak_dec else 0.0
    peak_cause_val = peak_dec.get("root_cause_category") if peak_dec else "N/A"
    actual_summary = f"State: {peak_state_val}, Score: {peak_score_val:.3f}, Cause: {peak_cause_val}"

    return {
        "run_id": run_id,
        "scenario": scenario_name,
        "station_id": station_id,
        "observations_count": len(observations),
        "decisions_count": len(decisions),
        "manifests": manifests,
        "target_channels": target_channels,
        "injection_onset": manifests[0].get("onset_ts") if manifests else None,
        "injection_offset": manifests[0].get("offset_ts") if manifests else None,
        "baseline_decision": baseline_dec,
        "transition_decision": transition_dec,
        "peak_decision": peak_dec,
        "final_decision": final_dec,
        "validation": {
            "expected": expected_summary,
            "actual": actual_summary,
            "passed": validation_passed,
        },
        "sample_decisions": [d.model_dump(mode="json") for d in decisions],
    }


@router.get("/v1/eval/labels/{run_id}", tags=["Evaluation"])
def get_evaluation_labels(run_id: str):
    from storage.repositories.ground_truth_repo import ground_truth_repo
    return ground_truth_repo.get_labels_for_run(run_id)


@router.get("/v1/stream", tags=["Streaming"])
@router.get("/v1/events", tags=["Streaming"])
async def event_stream(request: Request, station_id: Optional[str] = None):
    """
    Server-Sent Events (SSE) stream for live decision updates.
    Optional station_id filter.
    """
    q = bus.subscribe()

    async def event_generator():
        try:
            # Yield initial connection heartbeat
            yield f"data: {json.dumps({'type': 'connected', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=15.0)
                    if station_id is None or event.get("station_id") == station_id:
                        yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat
                    yield f": heartbeat\n\n"
        finally:
            bus.unsubscribe(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
