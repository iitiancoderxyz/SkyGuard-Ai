"""
Sensor Health, Dual-Clock Anti-Poisoning State, and Hardware Diagnostics.
Presents transparent, evidence-based health states per channel and overall station.
"""
import streamlit as st
import pandas as pd
from typing import Optional
from dashboard.api_client import APIClient
from dashboard.components.explainability import (
    render_evidence_chips,
    humanize_evidence_code,
    humanize_degradation,
    humanize_maintenance,
)


def render_sensor_health(api: APIClient, selected_station_id: Optional[str] = None):
    st.subheader("🛠️ Sensor Health & Baseline Diagnostics")
    st.caption("Longitudinal tracking of sensor telemetry, data completeness, and baseline health.")

    if not selected_station_id:
        st.info("Select a station to inspect its health diagnostics.")
        return

    health = api.get_station_health(selected_station_id)
    if "error" in health:
        st.error("Unable to load sensor health diagnostics. Please try again.")
        return

    # Section 1: Overall Station Health State
    st.markdown("### 🏥 Overall Station Health Assessment")
    overall_state = health.get("overall_health_state", "UNKNOWN").upper()
    
    state_color_map = {
        "HEALTHY": {"bg": "rgba(34, 197, 94, 0.15)", "border": "#22c55e", "badge": "🟢 Healthy", "color": "#4ade80"},
        "DEGRADED": {"bg": "rgba(245, 158, 11, 0.15)", "border": "#f59e0b", "badge": "🟠 Degraded", "color": "#fbbf24"},
        "AT_RISK": {"bg": "rgba(249, 115, 22, 0.15)", "border": "#f97316", "badge": "🟠 At Risk", "color": "#fb923c"},
        "CRITICAL": {"bg": "rgba(239, 68, 68, 0.15)", "border": "#ef4444", "badge": "🔴 Critical", "color": "#f87171"},
        "UNKNOWN": {"bg": "rgba(148, 163, 184, 0.15)", "border": "#94a3b8", "badge": "⚪ Unknown", "color": "#cbd5e1"},
    }
    style = state_color_map.get(overall_state, state_color_map["UNKNOWN"])

    st.markdown(
        f"""
        <div style="background-color: {style['bg']}; border: 1px solid {style['border']}; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 1.2rem; font-weight: 700; color: #f8fafc;">Station: {selected_station_id}</span>
                <span style="background-color: {style['border']}; color: #0f172a; padding: 4px 12px; border-radius: 12px; font-weight: 700; font-size: 0.9rem;">{style['badge']}</span>
            </div>
            <div style="font-size: 0.95rem; color: #e2e8f0; margin-bottom: 4px;">{health.get('overall_summary', 'No summary available.')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Section 2: Per-Channel Sensor Health Cards
    st.markdown("### 🔬 Per-Channel Physical Diagnostics")
    st.caption("Availability measures data coverage (percentage of expected readings received). Health reflects signal quality (whether the measurements show sensor flatlines, calibration drift, or spikes).")
    
    channels = health.get("channels", {})

    c1, c2, c3 = st.columns(3)
    channel_order = [("temperature", "🌡️ Temperature", c1), ("pressure", "🧭 Barometric Pressure", c2), ("relative_humidity", "💧 Relative Humidity", c3)]

    for ch_key, ch_label, col in channel_order:
        ch_info = channels.get(ch_key, {})
        ch_state = ch_info.get("state", "HEALTHY").upper()
        ch_style = state_color_map.get(ch_state, state_color_map["UNKNOWN"])
        avail_pct = ch_info.get("availability", 1.0) * 100.0
        deg_clean = humanize_degradation(ch_info.get('degradation_state'))
        maint_clean = humanize_maintenance(ch_info.get('maintenance_state'))

        with col:
            st.markdown(
                f"""
                <div style="background-color: rgba(30, 41, 59, 0.5); border: 1px solid {ch_style['border']}; border-radius: 8px; padding: 14px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 1rem; font-weight: 600; color: #f8fafc;">{ch_label}</span>
                        <span style="color: {ch_style['color']}; font-weight: 700; font-size: 0.85rem;">{ch_state.title()}</span>
                    </div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #38bdf8; margin: 8px 0;">{avail_pct:.0f}% <span style="font-size: 0.8rem; color: #94a3b8; font-weight: normal;">Availability</span></div>
                    <div style="font-size: 0.85rem; color: #cbd5e1; line-height: 1.5;">
                        <div><strong>Signal Quality:</strong> {deg_clean}</div>
                        <div><strong>Maintenance:</strong> {maint_clean}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander("Diagnostic Evidence", expanded=False):
                ev_items = ch_info.get("evidence", [])
                render_evidence_chips(ev_items)

    st.markdown("---")

    # Section 3: Baseline Monitoring & Protection
    st.markdown("### ⏱️ Baseline Monitoring & Protection")
    st.markdown("""
    SkyGuard compares incoming observations with both long-term and recent station behavior to reduce false alarms. Suspicious observations are prevented from updating the statistical baseline:
    - **Long-Term Baseline (96-step window):** Rolling robust baseline representing typical multi-hour diurnal behavior.
    - **Recent Baseline (12-step window):** Rapid short-term tracker for transient meteorological fluctuations.
    - **Baseline Protection:** Anomaly observations are quarantined so hardware defects never poison the normal model.
    """)

    model_int = health.get("model_integrity", {})
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Clean Buffer Depth", f"{model_int.get('clean_buffer_depth', 0)} / 96")
    b2.metric("Long-Term Baseline Window", f"{model_int.get('reference_profile_window', 96)} steps")
    b3.metric("Recent Baseline Window", f"{model_int.get('adaptive_tracker_window', 12)} steps")
    b4.metric("Baseline Protection", "Active 🔒")

    st.markdown("---")

    # Section 4: Ingestion Gate Configuration & Cadence Budgets
    st.markdown("### 📋 Station Ingestion Contract & Budgets")
    cfg = health.get("config", {})
    
    cfg_df = pd.DataFrame([
        {"Parameter": "Expected Sampling Cadence", "Value": f"{cfg.get('expected_cadence_seconds', 60)} seconds"},
        {"Parameter": "Allowed Lateness Window", "Value": f"{cfg.get('allowed_lateness_seconds', 120)} seconds"},
        {"Parameter": "Max Allowed Packet Loss", "Value": f"{cfg.get('communication_gap_slots', 3)} slots"},
        {"Parameter": "Station Operational Status", "Value": "Active" if str(health.get("status")).upper() == "ACTIVE" else health.get("status", "Active")},
        {"Parameter": "Recent Flagged Events (Window)", "Value": str(health.get("recent_anomalies_count", 0))},
        {"Parameter": "Communication Events (Window)", "Value": str(health.get("recent_events_count", 0))},
        {"Parameter": "Baseline Protection State", "Value": "Nominal" if str(model_int.get("model_integrity_state")).upper() == "OK" else model_int.get("model_integrity_state", "Nominal")},
    ])
    st.table(cfg_df)
