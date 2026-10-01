"""
Anomaly Monitoring, Alert Timeline, and Suspect / Human Review Queue.
"""
import json
import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional
from dashboard.api_client import APIClient
from dashboard.components.metrics import render_decision_badge, render_admission_badge, render_score_bar
from dashboard.components.explainability import (
    render_evidence_chips,
    render_hypothesis_attribution,
    render_reasoning_box,
    humanize_root_cause,
)


def _format_event_details(raw_details: Any) -> str:
    """Safely format JSON details into a readable operator string."""
    if not raw_details:
        return "None"
    if isinstance(raw_details, dict):
        return ", ".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in raw_details.items())
    if isinstance(raw_details, str):
        try:
            parsed = json.loads(raw_details)
            if isinstance(parsed, dict):
                return ", ".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in parsed.items())
            return str(parsed)
        except Exception:
            return raw_details
    return str(raw_details)


def render_anomaly_monitor(api: APIClient, selected_station_id: Optional[str] = None):
    st.subheader("🚨 Anomaly Assessment & Operator Review Queue")

    col_filter1, col_filter2 = st.columns([2, 1])
    with col_filter1:
        st.caption("Displaying active anomaly events, suspect cases requiring review, and traceable adjudications.")
    with col_filter2:
        severity_filter = st.multiselect(
            "Filter Severity",
            options=["CRITICAL", "HIGH", "MODERATE", "LOW"],
            default=["CRITICAL", "HIGH", "MODERATE", "LOW"],
        )

    # Fetch decisions
    decisions = api.list_decisions(station_id=selected_station_id, limit=60)
    events = api.get_station_events(selected_station_id, limit=30) if selected_station_id else []

    if not decisions:
        st.info("No recorded decisions available. Ingest observations or trigger a scenario to monitor live anomalies.")
        return

    df_dec = pd.DataFrame(decisions)
    
    # Filter by severity if present
    if "severity" in df_dec.columns and severity_filter:
        df_filtered = df_dec[df_dec["severity"].str.upper().isin(severity_filter)]
    else:
        df_filtered = df_dec

    # Metrics Summary Row
    total_anomalies = sum(1 for d in decisions if d.get("anomaly_score", 0) and d.get("anomaly_score", 0) >= 0.35)
    suspect_count = sum(1 for d in decisions if str(d.get("decision_state", "")).upper() in ["SUSPECT", "AMBIGUOUS", "WAIT"])
    critical_count = sum(1 for d in decisions if str(d.get("severity", "")).upper() == "CRITICAL")
    admitted_count = sum(1 for d in decisions if str(d.get("admission_state", "")).upper() == "ADMIT")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Flagged Events", total_anomalies)
    c2.metric("Cases Requiring Review", suspect_count)
    c3.metric("Critical Alerts", critical_count)
    c4.metric("Admitted to Baseline", f"{admitted_count}/{len(decisions)}")

    st.markdown("---")

    # Suspect / Human Review Callout (Priority 1)
    suspect_decisions = [d for d in decisions if str(d.get("decision_state", "")).upper() in ["SUSPECT", "AMBIGUOUS", "WAIT"]]
    if suspect_decisions:
        st.markdown("### ⚠️ Operator Review Required: Borderline & Ambiguous Cases")
        st.caption("These observations exhibit borderline statistical anomalies, competing hypotheses, or telemetry lateness.")
        
        for s_dec in suspect_decisions[:3]:
            stn_id = s_dec.get('station_id') or "AWS"
            ts_str = s_dec.get('event_timestamp', '—')
            score_num = s_dec.get('anomaly_score', 0) or 0
            with st.expander(f"⚠️ Station {stn_id} — {ts_str} | Anomaly Score: {score_num:.2f}", expanded=True):
                s_col1, s_col2 = st.columns([1, 1.2])
                with s_col1:
                    render_decision_badge(s_dec.get("decision_state", "SUSPECT"), s_dec.get("severity", "LOW"))
                    render_admission_badge(s_dec.get("admission_state", "ADMIT"))
                    render_score_bar("Normalized Anomaly Score", s_dec.get("anomaly_score", 0.4), warn_threshold=0.35, crit_threshold=0.65)
                    render_score_bar("Detection Confidence", s_dec.get("detection_confidence", 1.0), color="#10b981")
                with s_col2:
                    rc_human = humanize_root_cause(s_dec.get('root_cause_category'))
                    st.markdown(f"**Likely Cause:** {rc_human}")
                    st.markdown(f"**Temperature:** `{s_dec.get('temperature')} °C` | **Pressure:** `{s_dec.get('pressure')} hPa` | **RH:** `{s_dec.get('relative_humidity')} %`")
                    ev_codes = s_dec.get("evidence_codes")
                    if not ev_codes and s_dec.get("evidence_codes_json"):
                        try:
                            ev_codes = json.loads(s_dec.get("evidence_codes_json"))
                        except Exception:
                            ev_codes = []
                    render_evidence_chips(ev_codes or [])
                    render_reasoning_box(s_dec.get("reasoning_summary"), s_dec.get("uncertainty_state"))
        st.markdown("---")

    # Full Alert & Decision Feed Table
    st.markdown("### 📜 Chronological Decision Timeline")
    
    display_cols = [c for c in [
        "event_timestamp", "station_id", "decision_state", "severity", "anomaly_score",
        "root_cause_category", "uncertainty_state", "admission_state", "reasoning_summary", "observation_id"
    ] if c in df_filtered.columns]

    st.dataframe(
        df_filtered[display_cols],
        use_container_width=True,
        height=320,
    )

    # Integrity Events Log if available
    if events:
        st.markdown("### 📡 Telemetry & Communication Events")
        df_events = pd.DataFrame(events)
        if "details" in df_events.columns:
            df_events["details_formatted"] = df_events["details"].apply(_format_event_details)
        ev_cols = [c for c in ["created_at", "station_id", "event_type", "event_timestamp", "details_formatted", "details"] if c in df_events.columns]
        st.dataframe(df_events[ev_cols], use_container_width=True, height=220)
