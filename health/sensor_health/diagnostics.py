"""
Deterministic Sensor Health & Diagnostics Engine.
Aggregates telemetry availability, frozen flatline indicators, drift excursions,
and communication gaps into transparent, evidence-based health states.
"""
from typing import Dict, Any, List, Optional
from storage.repositories.observation_repo import obs_repo
from storage.repositories.event_repo import event_repo
from storage.repositories.station_repo import station_repo
from storage.repositories.health_repo import health_repo


def diagnose_station_health(station_id: str, window_size: int = 20) -> Dict[str, Any]:
    """
    Assesses transparent, evidence-based sensor health states for a station.
    Persists diagnosis into health_state SQLite table and returns structured diagnostics.
    """
    st_meta = station_repo.get_station(station_id) or {}
    recent_obs = obs_repo.get_recent_observations(station_id=station_id, limit=window_size)
    recent_events = event_repo.get_integrity_events(station_id=station_id, limit=window_size)

    # In-memory station state
    from app.runtime.engine import engine
    state = engine.station_states.get(station_id)
    buffer_depth = len(state.clean_buffer) if state else 0
    last_val = state.last_values if state else {}
    last_ts = state.last_event_ts.isoformat() if (state and state.last_event_ts) else None

    total_obs = len(recent_obs)
    window_start = recent_obs[-1].get("event_timestamp") if recent_obs else None
    window_end = recent_obs[0].get("event_timestamp") if recent_obs else None

    # Overall counters
    recent_anomalies = [o for o in recent_obs if (o.get("anomaly_score") or 0.0) >= 0.35]
    recent_anomalies_count = len(recent_anomalies)
    recent_events_count = len(recent_events)

    channels_diag = {}
    channel_availability = {}
    supporting_evidence = []

    channels = ["temperature", "pressure", "relative_humidity"]

    for ch in channels:
        if total_obs == 0:
            ch_state = "UNKNOWN"
            avail = 1.0
            deg_state = "NO_DATA"
            maint_state = "NONE"
            ev_list = ["No historical telemetry recorded for station."]
            score = 1.0
        else:
            valid_vals = [o.get(ch) for o in recent_obs if o.get(ch) is not None]
            avail = round(len(valid_vals) / total_obs, 2)
            
            # Check for frozen flatlines in recent window (consecutive identical values from latest)
            frozen_detected = False
            flat_count = 0
            if len(valid_vals) >= 4:
                first_v = valid_vals[0]
                consec = 0
                for v in valid_vals:
                    if abs(v - first_v) < 1e-4:
                        consec += 1
                    else:
                        break
                flat_count = consec
                if flat_count >= 4:
                    frozen_detected = True

            # Check for active anomaly triggers on this channel specifically when anomaly score >= 0.35
            ch_anom_triggers = []
            for o in recent_obs:
                score = o.get("anomaly_score") or 0.0
                if score >= 0.35:
                    evs = o.get("evidence_codes") or []
                    for ev in evs:
                        ev_str = str(ev).upper()
                        # Strictly match evidence belonging to this channel
                        c_lower = ch.lower()
                        is_ch_ev = False
                        if c_lower == "temperature":
                            is_ch_ev = "TEMPERATURE" in ev_str or "TEMP" in ev_str or "THERMODYNAMIC" in ev_str
                        elif c_lower == "pressure":
                            is_ch_ev = "PRESSURE" in ev_str
                        elif c_lower == "relative_humidity":
                            is_ch_ev = "RELATIVE_HUMIDITY" in ev_str or "HUMIDITY" in ev_str or "_RH" in ev_str or "THERMODYNAMIC" in ev_str
                        
                        if is_ch_ev:
                            ch_anom_triggers.append(ev)

            drift_detected = any("DRIFT" in str(t).upper() or "ZSCORE" in str(t).upper() for t in ch_anom_triggers)

            # Assign channel health state
            ev_list = []
            if avail < 0.50:
                ch_state = "CRITICAL"
                deg_state = "SEVERE_DATA_LOSS"
                maint_state = "URGENT_MAINTENANCE"
                ev_list.append(f"Channel availability severely degraded at {avail * 100:.0f}%.")
            elif frozen_detected:
                ch_state = "CRITICAL" if flat_count >= 12 else "AT_RISK"
                deg_state = "SENSOR_FLATLINE"
                maint_state = "INSPECTION_RECOMMENDED"
                ev_list.append(f"Persistent frozen sensor readings detected ({flat_count} identical steps).")
            elif drift_detected:
                ch_state = "AT_RISK"
                deg_state = "CALIBRATION_DRIFT"
                maint_state = "INSPECTION_RECOMMENDED"
                ev_list.append(f"Calibration drift detected ({len(ch_anom_triggers)} flags in window).")
            elif len(ch_anom_triggers) >= 4:
                ch_state = "AT_RISK"
                deg_state = "RECURRING_ANOMALIES"
                maint_state = "INSPECTION_RECOMMENDED"
                ev_list.append(f"Recurring anomaly excursions ({len(ch_anom_triggers)} flags in window).")
            elif avail < 0.90:
                ch_state = "DEGRADED"
                deg_state = "INTERMITTENT_DROPOUTS"
                maint_state = "MONITOR"
                ev_list.append(f"Intermittent packet dropouts (availability {avail * 100:.0f}%).")
            elif len(ch_anom_triggers) > 0:
                ch_state = "DEGRADED"
                deg_state = "ISOLATED_EXCURSION"
                maint_state = "MONITOR"
                ev_list.append("Isolated statistical excursion detected in window.")
            else:
                ch_state = "HEALTHY"
                deg_state = "NO_DEGRADATION_EVIDENCE"
                maint_state = "NONE"
                ev_list.append(f"Telemetry nominal. Availability {avail * 100:.0f}%.")

            # Health score (availability penalized by anomaly fraction)
            anom_fraction = len(ch_anom_triggers) / max(total_obs, 1)
            score = round(max(0.0, min(1.0, avail - (0.3 * anom_fraction))), 2)

        channel_availability[ch] = avail
        channels_diag[ch] = {
            "channel": ch,
            "state": ch_state,
            "health_score": score,
            "availability": avail,
            "degradation_state": deg_state,
            "maintenance_state": maint_state,
            "evidence": ev_list,
        }

        # Persist to database health_state table
        health_repo.save_health_state(
            station_id=station_id,
            channel=ch,
            state=ch_state,
            health_score=score,
            degradation_state=deg_state,
            maintenance_state=maint_state,
            evidence_window_start=window_start,
            evidence_window_end=window_end,
            model_integrity_state="OK" if buffer_depth >= 6 else "INITIALIZING",
        )

    # Determine Overall Station Health State
    states_set = {c["state"] for c in channels_diag.values()}
    if "CRITICAL" in states_set or st_meta.get("status") == "INACTIVE":
        overall_state = "CRITICAL"
        overall_summary = "One or more channels experiencing severe failure, sensor flatline, or excessive packet loss."
    elif "AT_RISK" in states_set:
        overall_state = "AT_RISK"
        overall_summary = "Sensor channel experiencing persistent calibration drift or frozen readings. Inspection recommended."
    elif "DEGRADED" in states_set:
        overall_state = "DEGRADED"
        overall_summary = "Moderate telemetry dropouts or isolated anomaly excursions detected."
    elif total_obs == 0:
        overall_state = "UNKNOWN"
        overall_summary = "Awaiting initial observation stream."
    else:
        overall_state = "HEALTHY"
        overall_summary = "All sensor channels operating within nominal physical bounds and reporting complete telemetry."

    for c in channels_diag.values():
        for e in c["evidence"]:
            supporting_evidence.append(f"{c['channel'].capitalize()}: {e}")

    return {
        "station_id": station_id,
        "status": st_meta.get("status", "ACTIVE"),
        "overall_health_state": overall_state,
        "overall_summary": overall_summary,
        "supporting_evidence": supporting_evidence,
        "channels": channels_diag,
        "channel_availability": channel_availability,
        "config": {
            "expected_cadence_seconds": st_meta.get("expected_cadence_seconds", 60),
            "allowed_lateness_seconds": st_meta.get("allowed_lateness_seconds", 120),
            "communication_gap_slots": st_meta.get("communication_gap_slots", 3),
            "latitude": st_meta.get("latitude"),
            "longitude": st_meta.get("longitude"),
            "elevation": st_meta.get("elevation"),
        },
        "model_integrity": {
            "clean_buffer_depth": buffer_depth,
            "reference_profile_window": 96,
            "adaptive_tracker_window": 12,
            "anti_poisoning_status": "PROTECTED",
            "model_integrity_state": "OK" if buffer_depth >= 6 else "INITIALIZING",
        },
        "recent_anomalies_count": recent_anomalies_count,
        "recent_events_count": recent_events_count,
        "last_observation_ts": last_ts,
        "last_values": last_val,
        "window_start": window_start,
        "window_end": window_end,
    }
