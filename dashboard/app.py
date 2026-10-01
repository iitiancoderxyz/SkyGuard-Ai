"""
SkyGuard AI Operational Meteorological Monitoring Dashboard.
Real-time Automatic Weather Station Anomaly Intelligence Engine (SIH26073).
"""
import streamlit as st
import pandas as pd
from dashboard.api_client import APIClient
from dashboard.views.overview import render_station_overview
from dashboard.views.anomaly_monitor import render_anomaly_monitor
from dashboard.views.historical import render_historical_trends
from dashboard.views.sensor_health import render_sensor_health
from dashboard.views.scenario_runner import render_scenario_runner

# Page Configuration
st.set_page_config(
    page_title="SkyGuard AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for Dark Operational Theme
st.markdown(
    """
    <style>
    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 12px 16px;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        color: #94a3b8;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f8fafc;
    }
    
    /* Tab Styling */
    button[data-baseweb="tab"] {
        font-size: 1rem;
        font-weight: 600;
        padding: 10px 20px;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* App Title */
    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 12px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 20px;
    }
    .app-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: #f8fafc;
        margin: 0;
    }
    .app-subtitle {
        font-size: 0.9rem;
        color: #94a3b8;
        margin: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

api = APIClient()

# Header
st.markdown(
    """
    <div class="app-header">
        <div>
            <div class="app-title">🛡️ SkyGuard AI</div>
            <div class="app-subtitle">AI/ML-Based Intelligent Anomaly Detection &amp; Sensor Health for Automatic Weather Stations (SIH26073)</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar Navigation & Diagnostics
st.sidebar.title("🛡️ SkyGuard AI")
st.sidebar.markdown("### 📡 System Connectivity")
health = api.get_health()

if health.get("status") == "ok":
    st.sidebar.success(f"Connected to Backend (v{health.get('version')})")
    st.sidebar.caption(f"Storage: **SQLite (WAL mode)** | Stations Monitored: **{health.get('active_stations', 0)}**")
else:
    st.sidebar.error("Unable to connect to the monitoring service. Please ensure the API server is running on port 8000.")

st.sidebar.markdown("---")

# Station Selection in Sidebar
st.sidebar.markdown("### 🌦️ Station Selector")
stations = api.list_stations()
station_ids = [s["station_id"] for s in stations] if stations else ["AWS_001"]

selected_station = st.sidebar.selectbox(
    "Select Station",
    options=station_ids,
    index=0 if station_ids else 0,
    help="Select an Automatic Weather Station to inspect telemetry, alerts, and historical data.",
)

# Main Navigation Tabs
tabs = st.tabs([
    "🛡️ Station Overview",
    "🚨 Anomaly Monitor",
    "📈 Historical Analytics",
    "🛠️ Sensor Health",
    "🧪 Scenario Testbed",
])

with tabs[0]:
    render_station_overview(api, selected_station)

with tabs[1]:
    render_anomaly_monitor(api, selected_station)

with tabs[2]:
    render_historical_trends(api, selected_station)

with tabs[3]:
    render_sensor_health(api, selected_station)

with tabs[4]:
    render_scenario_runner(api)
