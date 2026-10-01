"""
Operational Station Overview and Live Telemetry View.
"""
import json
import streamlit as st
import pandas as pd
from typing import Dict, Any, List
from dashboard.api_client import APIClient
from dashboard.components.metrics import render_decision_badge, render_admission_badge, render_score_bar
from dashboard.components.explainability import (
    render_reasoning_box,
    render_evidence_chips,
    render_hypothesis_attribution,
    humanize_root_cause,
)


def render_station_overview(api: APIClient, selected_station_id: str):
    stations = api.list_stations()
    if not stations:
        st.warning("No Automatic Weather Stations registered in system. Use the Scenario Testbed tab to simulate incoming station telemetry.")
        return

    # Fetch station metadata & latest observations
    st_meta = api.get_station_health(selected_station_id) if selected_station_id else {}
    obs_list = api.get_station_observations(selected_station_id, limit=30) if selected_station_id else []

    # Top Metadata Row
    col_meta1, col_meta2, col_meta3, col_meta4 = st.columns(4)
    with col_meta1:
        st.metric("Station Identifier", selected_station_id)
    with col_meta2:
        status_val = st_meta.get("status", "ACTIVE")
        st.metric("Station Status", "Active" if str(status_val).upper() == "ACTIVE" else status_val)
    with col_meta3:
        cfg = st_meta.get("config", {})
        coords = f"{cfg.get('latitude', 'N/A')}, {cfg.get('longitude', 'N/A')}" if cfg.get('latitude') else "Field Deployment"
        st.metric("Coordinates / Location", coords)
    with col_meta4:
        cadence = cfg.get("expected_cadence_seconds", 60)
        st.metric("Sampling Cadence", f"{cadence}s")

    st.markdown("---")

    if not obs_list:
        st.info(f"No observation telemetry recorded yet for {selected_station_id}. Submit an observation or launch a scenario from the Scenario Testbed tab.")
        return

    latest_obs = obs_list[0]

    # Latest Live Telemetry Cards
    st.subheader("Latest Meteorological Telemetry")
    t_col, p_col, rh_col, td_col = st.columns(4)

    with t_col:
        t_val = latest_obs.get("temperature")
        t_str = f"{t_val:.1f} °C" if t_val is not None else "N/A"
        raw_t = latest_obs.get("temperature_raw")
        raw_sub = f"Raw: {raw_t:.1f}°C" if raw_t is not None else "Raw: N/A"
        st.metric(
            label="Temperature",
            value=t_str,
            help=f"Raw sensor reading: {raw_sub}",
        )
        if raw_t is not None and t_val is not None and abs(raw_t - t_val) > 0.001:
            st.caption(f"Raw measurement: {raw_sub}")

    with p_col:
        p_val = latest_obs.get("pressure")
        p_str = f"{p_val:.1f} hPa" if p_val is not None else "N/A"
        raw_p = latest_obs.get("pressure_raw")
        raw_sub = f"Raw: {raw_p:.1f}hPa" if raw_p is not None else "Raw: N/A"
        st.metric(
            label="Barometric Pressure",
            value=p_str,
            help=f"Raw sensor reading: {raw_sub}",
        )
        if raw_p is not None and p_val is not None and abs(raw_p - p_val) > 0.001:
            st.caption(f"Raw measurement: {raw_sub}")

    with rh_col:
        rh_val = latest_obs.get("relative_humidity")
        rh_str = f"{rh_val:.1f} %" if rh_val is not None else "N/A"
        raw_rh = latest_obs.get("relative_humidity_raw")
        raw_sub = f"Raw: {raw_rh:.1f}%" if raw_rh is not None else "Raw: N/A"
        st.metric(
            label="Relative Humidity",
            value=rh_str,
            help=f"Raw sensor reading: {raw_sub}",
        )
        if raw_rh is not None and rh_val is not None and abs(raw_rh - rh_val) > 0.001:
            st.caption(f"Raw measurement: {raw_sub}")

    with td_col:
        dewpoint = latest_obs.get("derived_dewpoint")
        dew_str = f"{dewpoint:.1f} °C" if dewpoint is not None else "—"
        st.metric(
            label="Derived Dewpoint",
            value=dew_str,
            help="Calculated thermodynamic estimate from temperature and humidity.",
        )

    st.markdown("---")

    # Latest Anomaly & Intelligence Assessment
    st.subheader("Anomaly Assessment")
    dec_col1, dec_col2 = st.columns([1, 1.2])

    with dec_col1:
        st.markdown("**Decision State & Confidence**")
        render_decision_badge(
            decision_state=latest_obs.get("decision_state", "NORMAL"),
            severity=latest_obs.get("severity", "LOW"),
        )
        render_admission_badge(latest_obs.get("admission_state", "ADMIT"))

        st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
        render_score_bar(
            label="Normalized Anomaly Score",
            value=latest_obs.get("anomaly_score", 0.0),
            color="#3b82f6",
        )
        render_score_bar(
            label="Detection Confidence",
            value=latest_obs.get("detection_confidence", 1.0),
            color="#10b981",
        )
        render_score_bar(
            label="Cause Confidence",
            value=latest_obs.get("attribution_confidence", 1.0),
            color="#8b5cf6",
        )

    with dec_col2:
        st.markdown("**Likely Cause & Attribution**")
        render_hypothesis_attribution(
            weather_likelihood=latest_obs.get("weather_event_likelihood"),
            sensor_fault_likelihood=latest_obs.get("sensor_fault_likelihood"),
            root_cause=latest_obs.get("root_cause_category"),
            plausibility=latest_obs.get("plausibility_score"),
        )

        st.markdown("**Evidence**")
        # Real backend evidence codes
        ev_codes = latest_obs.get("evidence_codes")
        if not ev_codes and latest_obs.get("evidence_codes_json"):
            try:
                ev_codes = json.loads(latest_obs.get("evidence_codes_json"))
            except Exception:
                ev_codes = []
        render_evidence_chips(ev_codes or [])

        # Real backend reasoning summary
        reasoning_summary = latest_obs.get("reasoning_summary")
        dec_state = str(latest_obs.get("decision_state", "NORMAL")).upper()
        if not reasoning_summary:
            if dec_state in ["ANOMALY", "ANOMALOUS"]:
                rc_name = humanize_root_cause(latest_obs.get("root_cause_category"))
                reasoning_summary = f"Observation flagged as anomalous. Likely Cause: {rc_name}."
            elif dec_state in ["SUSPECT", "AMBIGUOUS"]:
                reasoning_summary = "The observation is unusual, but the available evidence does not clearly separate a sensor issue from a genuine atmospheric change."
            else:
                reasoning_summary = "The latest observation is consistent with the station's recent behavior. No significant anomaly detected."

        render_reasoning_box(
            reasoning_summary=reasoning_summary,
            uncertainty_state=latest_obs.get("uncertainty_state", "LOW"),
        )

    # Recent Observations Table
    st.markdown("---")
    st.subheader("Recent Station Records")
    df_obs = pd.DataFrame(obs_list)
    display_cols = [c for c in [
        "event_timestamp", "observation_id", "temperature", "pressure", "relative_humidity",
        "derived_dewpoint", "anomaly_score", "severity", "decision_state", "root_cause_category",
        "reasoning_summary"
    ] if c in df_obs.columns]
    
    st.dataframe(
        df_obs[display_cols],
        use_container_width=True,
        height=280,
    )
