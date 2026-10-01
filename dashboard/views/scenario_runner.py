"""
Interactive Scenario Testbed & Demonstration Suite.
Allows one-click replay of real-world meteorological faults and genuine weather events.
Presents representative baseline, transition, peak anomaly, and final state stages.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from dashboard.api_client import APIClient
from dashboard.components.metrics import render_decision_badge, render_admission_badge, render_score_bar
from dashboard.components.explainability import render_evidence_chips, render_hypothesis_attribution, render_reasoning_box


def render_scenario_runner(api: APIClient):
    st.subheader("🧪 Interactive Scenario Testbed & Demonstration Suite")
    st.caption("Replay pre-configured meteorological anomalies, genuine atmospheric events, and data telemetry faults through the live single-entry pipeline.")

    scenarios = api.list_scenarios()
    
    tab_suite, tab_manual = st.tabs(["⚡ Demonstration Scenarios", "📝 Manual Observation Ingestion"])

    with tab_suite:
        col_ctl1, col_ctl2, col_ctl3 = st.columns([2, 1, 1])
        
        scenario_map = {s["name"]: f"{s['label']}" for s in scenarios} if scenarios else {
            "NOMINAL": "1. Nominal / Normal Clean Stream",
            "SPIKE": "2. Isolated Temperature Spike",
            "FLATLINE": "3. Frozen Sensor Flatline",
            "DRIFT": "4. Gradual Sensor Drift",
            "MULTIVARIATE_INCONSISTENCY": "5. Multivariate Inconsistency",
            "BIAS": "6. Sudden Pressure Bias Jump",
            "NOISE": "7. Excessive High-Frequency Noise",
            "COMMUNICATION_GAP": "8. Communication / Packet Loss Gap",
            "GENUINE_WEATHER": "9. Genuine Cold Front Event",
            "COMBINED": "10. Combined Fault Suite",
        }

        with col_ctl1:
            sel_scen = st.selectbox(
                "Select Demonstration Scenario",
                options=list(scenario_map.keys()),
                format_func=lambda k: scenario_map[k],
            )
        with col_ctl2:
            sim_station = st.text_input("Target Station ID", value="AWS_DEMO_01")
        with col_ctl3:
            num_pts = st.number_input("Stream Points", min_value=10, max_value=50, value=25)

        # Show scenario description
        desc_dict = {s["name"]: s["description"] for s in scenarios} if scenarios else {}
        st.info(f"**Scenario Description:** {desc_dict.get(sel_scen, 'Executes automated stream generation with synthetic injection.')}")

        run_btn = st.button("🚀 Replay Scenario through Pipeline", type="primary", use_container_width=True)

        if run_btn:
            with st.spinner(f"Replaying {sel_scen} through SkyGuard AI ML engine..."):
                res = api.run_scenario(
                    scenario_name=sel_scen,
                    station_id=sim_station,
                    num_points=num_pts,
                    seed=42,
                )
                if res.get("status_code") == 200:
                    data = res.get("data", {})
                    st.success(f"Successfully processed {data.get('observations_count')} observations into station `{sim_station}`!")
                    
                    # 1. Scenario Metadata & Validation Card
                    st.markdown("#### 📋 Scenario Manifest & Acceptance Validation")
                    val = data.get("validation", {})
                    is_pass = val.get("passed", False)
                    badge_color = "#22c55e" if is_pass else "#ef4444"
                    badge_text = "🟢 PASS" if is_pass else "🔴 FAIL"

                    st.markdown(
                        f"""
                        <div style="background-color: rgba(30, 41, 59, 0.5); border: 1px solid {badge_color}; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span style="font-size: 1.1rem; font-weight: 700; color: #f8fafc;">Scenario: {sel_scen}</span>
                                <span style="background-color: {badge_color}; color: #0f172a; padding: 4px 12px; border-radius: 12px; font-weight: 700; font-size: 0.9rem;">{badge_text}</span>
                            </div>
                            <div style="font-size: 0.9rem; color: #cbd5e1; line-height: 1.6;">
                                <div><strong>Target Channel(s):</strong> {data.get('target_channels', 'All')}</div>
                                <div><strong>Injection Window:</strong> Onset: {data.get('injection_onset') or 'N/A'} | Offset: {data.get('injection_offset') or 'N/A'}</div>
                                <div><strong>Expected Behavior:</strong> {val.get('expected', 'N/A')}</div>
                                <div><strong>Actual Result:</strong> {val.get('actual', 'N/A')}</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # 2. Key Scenario Stages
                    st.markdown("#### ⏱️ Scenario Progression Stages")
                    s_col1, s_col2, s_col3, s_col4 = st.columns(4)
                    
                    baseline_d = data.get("baseline_decision") or {}
                    transition_d = data.get("transition_decision") or {}
                    peak_d = data.get("peak_decision") or {}
                    final_d = data.get("final_decision") or {}

                    with s_col1:
                        st.markdown("**1. Pre-Injection Baseline**")
                        st.caption(f"Obs: `{baseline_d.get('observation_id', 'N/A')}`")
                        render_decision_badge(baseline_d.get("decision_state", "NORMAL"), baseline_d.get("severity", "LOW"))
                        render_score_bar("Anomaly Score", baseline_d.get("anomaly_score", 0.0))

                    with s_col2:
                        st.markdown("**2. Fault Onset Transition**")
                        st.caption(f"Obs: `{transition_d.get('observation_id', 'N/A')}`")
                        render_decision_badge(transition_d.get("decision_state", "NORMAL"), transition_d.get("severity", "LOW"))
                        render_score_bar("Anomaly Score", transition_d.get("anomaly_score", 0.0))

                    with s_col3:
                        st.markdown("**3. Peak Anomaly Stage**")
                        st.caption(f"Obs: `{peak_d.get('observation_id', 'N/A')}`")
                        render_decision_badge(peak_d.get("decision_state", "NORMAL"), peak_d.get("severity", "LOW"))
                        render_score_bar("Anomaly Score", peak_d.get("anomaly_score", 0.0), color="#ef4444")

                    with s_col4:
                        st.markdown("**4. Post-Injection Recovery**")
                        st.caption(f"Obs: `{final_d.get('observation_id', 'N/A')}`")
                        render_decision_badge(final_d.get("decision_state", "NORMAL"), final_d.get("severity", "LOW"))
                        render_score_bar("Anomaly Score", final_d.get("anomaly_score", 0.0))

                    # 3. Deep Dive into Peak Anomaly Decision
                    st.markdown("#### 🔬 Peak Anomaly Deep Dive & Explainability")
                    p_col1, p_col2 = st.columns([1, 1.2])
                    with p_col1:
                        st.markdown("**Adjudicated Decision & Handling**")
                        render_decision_badge(peak_d.get("decision_state", "NORMAL"), peak_d.get("severity", "LOW"))
                        render_admission_badge(peak_d.get("admission_state", "ADMIT"))
                        render_score_bar("Anomaly Score", peak_d.get("anomaly_score", 0.0))
                        render_score_bar("Detection Confidence", peak_d.get("detection_confidence", 1.0), color="#10b981")
                        render_score_bar("Cause Confidence", peak_d.get("attribution_confidence", 1.0), color="#8b5cf6")

                    with p_col2:
                        st.markdown("**Likely Cause & Attribution**")
                        render_hypothesis_attribution(
                            weather_likelihood=peak_d.get("weather_event_likelihood"),
                            sensor_fault_likelihood=peak_d.get("sensor_fault_likelihood"),
                            root_cause=peak_d.get("root_cause_category"),
                            plausibility=peak_d.get("plausibility_score"),
                        )
                        render_evidence_chips(peak_d.get("evidence_codes"))
                        render_reasoning_box(peak_d.get("reasoning_summary"), peak_d.get("uncertainty_state"))

                    # 4. Full Decision Sequence Table
                    st.markdown("#### 📜 Complete Replay Decision Timeline")
                    samples = data.get("sample_decisions", [])
                    if samples:
                        df_samples = pd.DataFrame(samples)
                        disp_cols = [c for c in ["observation_id", "decision_state", "severity", "anomaly_score", "root_cause_category", "uncertainty_state", "admission_state"] if c in df_samples.columns]
                        st.dataframe(df_samples[disp_cols], use_container_width=True)
                else:
                    st.error("Scenario execution failed. Please verify the station ID and try again.")

    with tab_manual:
        st.markdown("#### 📡 Inject Single Raw Observation")
        st.caption("Directly invokes `POST /v1/observations` single-entry decision endpoint.")

        with st.form("manual_ingest"):
            m_station = st.text_input("Station ID", value="AWS_MANUAL_01")
            m_col1, m_col2, m_col3 = st.columns(3)
            with m_col1:
                m_temp = st.number_input("Temperature (°C)", value=32.5)
            with m_col2:
                m_press = st.number_input("Barometric Pressure (hPa)", value=1005.0)
            with m_col3:
                m_rh = st.number_input("Relative Humidity (%)", value=78.0)
            
            sub_btn = st.form_submit_button("🚀 Submit Single Observation", type="primary")

            if sub_btn:
                payload = {
                    "station_id": m_station,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "temperature": m_temp,
                    "pressure": m_press,
                    "relative_humidity": m_rh,
                    "source_type": "LIVE",
                }
                with st.spinner("Submitting observation to SkyGuard AI engine..."):
                    res = api.submit_observation(payload)
                    if res.get("status_code") == 200:
                        dec = res.get("data", {})
                        st.success("Observation processed by SkyGuard AI engine!")
                        
                        r_col1, r_col2 = st.columns([1, 1.2])
                        with r_col1:
                            render_decision_badge(dec.get("decision_state"), dec.get("severity"))
                            render_admission_badge(dec.get("admission_state"))
                            render_score_bar("Normalized Anomaly Score", dec.get("anomaly_score"))
                            render_score_bar("Detection Confidence", dec.get("detection_confidence"), color="#10b981")
                            render_score_bar("Cause Confidence", dec.get("attribution_confidence"), color="#8b5cf6")
                        with r_col2:
                            render_hypothesis_attribution(
                                weather_likelihood=dec.get("weather_event_likelihood"),
                                sensor_fault_likelihood=dec.get("sensor_fault_likelihood"),
                                root_cause=dec.get("root_cause_category"),
                                plausibility=dec.get("plausibility_score"),
                            )
                            render_evidence_chips(dec.get("evidence_codes"))
                            render_reasoning_box(dec.get("reasoning_summary"), dec.get("uncertainty_state"))
                    else:
                        err_data = res.get("data")
                        err_msg = "Observation could not be processed."
                        if isinstance(err_data, dict) and "error" in err_data:
                            api_msg = err_data["error"].get("message", "")
                            if api_msg:
                                err_msg = f"Observation could not be processed: {api_msg}"
                        st.error(err_msg)
                        if isinstance(err_data, dict) and "error" in err_data:
                            detail = err_data["error"].get("details")
                            if detail and isinstance(detail, list):
                                st.warning("Some observation fields are invalid. Please check the entered values.")
