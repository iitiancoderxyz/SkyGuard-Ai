"""
Historical Analytics, Multi-Channel Time-Series Trends, and RAW vs Processed Inspection.
"""
import streamlit as st
import pandas as pd
from typing import Optional
from dashboard.api_client import APIClient
from dashboard.components.charts import (
    create_meteorological_time_series,
    create_anomaly_score_chart,
    create_raw_vs_processed_chart,
)


def render_historical_trends(api: APIClient, selected_station_id: Optional[str] = None):
    st.subheader("📈 Multi-Channel Historical Telemetry & Analytics")

    if not selected_station_id:
        st.info("Please select a station to view historical time series.")
        return

    col_ctrl1, col_ctrl2 = st.columns([1, 2])
    with col_ctrl1:
        limit = st.select_slider(
            "Observation Window",
            options=[20, 50, 100, 200],
            value=50,
            help="Number of recent historical data points to chart.",
        )
    with col_ctrl2:
        st.caption(f"Continuous multi-channel diurnal cycles, physical step transitions, and statistical anomaly triggers for **{selected_station_id}**.")

    obs_list = api.get_station_observations(selected_station_id, limit=limit)
    if not obs_list:
        st.warning(f"No historical telemetry found for station {selected_station_id}.")
        return

    df_obs = pd.DataFrame(obs_list)

    # 1. Synchronized Meteorological Plot
    st.markdown("#### 🛰️ Synchronized Time Series (Temperature, Pressure, Humidity)")
    fig_multi = create_meteorological_time_series(df_obs)
    st.plotly_chart(fig_multi, use_container_width=True)

    # 2. Anomaly Score Trajectory
    st.markdown("#### ⚡ Normalized Anomaly Score Trajectory")
    fig_score = create_anomaly_score_chart(df_obs)
    st.plotly_chart(fig_score, use_container_width=True)

    # 3. RAW vs PROCESSED Verification
    st.markdown("#### 🔬 RAW Telemetry vs Processed Channel Verification")
    st.caption("Verifies raw observation immutability. Derived thermodynamic estimates are computed without modifying original sensor readings.")

    ch_col1, ch_col2 = st.columns([1, 3])
    with ch_col1:
        sel_channel = st.selectbox(
            "Inspect Channel",
            ["temperature", "pressure", "relative_humidity"],
            format_func=lambda x: {"temperature": "Temperature", "pressure": "Barometric Pressure", "relative_humidity": "Relative Humidity"}.get(x, x),
        )
    
    fig_raw = create_raw_vs_processed_chart(df_obs, channel=sel_channel)
    st.plotly_chart(fig_raw, use_container_width=True)
