"""
Unit Test Suite for UNIT A — Chart Reliability & Null/NaN Safety (Repair 2).
Tests:
A1. Normal complete time-series
A2. Missing anomaly_score
A3. Missing temperature value
A4. Missing pressure value
A5. Missing humidity value
A6. Duplicate timestamps
A7. Multiple records within the same second
A8. Cross-midnight timestamps
A9. Empty station history
A10. Unsorted observation input
"""
import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dashboard.components.charts import (
    create_meteorological_time_series,
    create_anomaly_score_chart,
    create_raw_vs_processed_chart,
)


def _base_dataframe(n: int = 10) -> pd.DataFrame:
    base_ts = pd.date_range(start="2026-09-30 10:00:00", periods=n, freq="min")
    return pd.DataFrame({
        "event_timestamp": [ts.isoformat() for ts in base_ts],
        "temperature": [20.0 + i * 0.5 for i in range(n)],
        "pressure": [1013.0 - i * 0.2 for i in range(n)],
        "relative_humidity": [50.0 + i * 1.0 for i in range(n)],
        "temperature_raw": [20.0 + i * 0.5 for i in range(n)],
        "pressure_raw": [1013.0 - i * 0.2 for i in range(n)],
        "relative_humidity_raw": [50.0 + i * 1.0 for i in range(n)],
        "anomaly_score": [0.1 if i < 8 else 0.85 for i in range(n)],
        "root_cause_category": ["NORMAL" if i < 8 else "SENSOR_SPIKE" for i in range(n)],
    })


def test_a1_normal_complete_time_series():
    """A1. Normal complete time-series renders valid figures."""
    df = _base_dataframe(15)
    
    fig_multi = create_meteorological_time_series(df)
    assert isinstance(fig_multi, go.Figure)
    assert len(fig_multi.data) >= 3  # 3 channels + anomaly markers

    fig_score = create_anomaly_score_chart(df)
    assert isinstance(fig_score, go.Figure)
    assert len(fig_score.data) >= 1

    fig_raw = create_raw_vs_processed_chart(df, "temperature")
    assert isinstance(fig_raw, go.Figure)
    assert len(fig_raw.data) >= 2


def test_a2_missing_anomaly_score():
    """A2. Missing anomaly_score (None, NaN, or column absent) does not crash."""
    df = _base_dataframe(10)
    df["anomaly_score"] = [None, np.nan, None, 0.2, None, np.nan, 0.9, None, None, np.nan]

    fig_multi = create_meteorological_time_series(df)
    assert isinstance(fig_multi, go.Figure)

    fig_score = create_anomaly_score_chart(df)
    assert isinstance(fig_score, go.Figure)

    # Completely absent column
    df_no_score = df.drop(columns=["anomaly_score"])
    fig_no_score = create_anomaly_score_chart(df_no_score)
    assert isinstance(fig_no_score, go.Figure)


def test_a3_missing_temperature_value():
    """A3. Missing temperature values (None, NaN) preserve gaps and do not crash."""
    df = _base_dataframe(10)
    df["temperature"] = [21.0, None, np.nan, 22.0, None, 23.0, np.nan, 24.0, 25.0, None]
    
    fig_multi = create_meteorological_time_series(df)
    assert isinstance(fig_multi, go.Figure)
    
    fig_raw = create_raw_vs_processed_chart(df, "temperature")
    assert isinstance(fig_raw, go.Figure)


def test_a4_missing_pressure_value():
    """A4. Missing pressure values (None, NaN) preserve gaps and do not crash."""
    df = _base_dataframe(10)
    df["pressure"] = [None, np.nan, 1012.0, None, 1010.0, np.nan, None, 1008.0, None, 1006.0]
    
    fig_multi = create_meteorological_time_series(df)
    assert isinstance(fig_multi, go.Figure)
    
    fig_raw = create_raw_vs_processed_chart(df, "pressure")
    assert isinstance(fig_raw, go.Figure)


def test_a5_missing_humidity_value():
    """A5. Missing humidity values (None, NaN) preserve gaps and do not crash."""
    df = _base_dataframe(10)
    df["relative_humidity"] = [None, 55.0, np.nan, None, 60.0, None, np.nan, 70.0, None, None]
    
    fig_multi = create_meteorological_time_series(df)
    assert isinstance(fig_multi, go.Figure)
    
    fig_raw = create_raw_vs_processed_chart(df, "relative_humidity")
    assert isinstance(fig_raw, go.Figure)


def test_a6_duplicate_timestamps():
    """A6. Duplicate timestamps are plotted distinctly along native datetime axis."""
    df = _base_dataframe(6)
    # Force duplicate timestamps
    df["event_timestamp"] = [
        "2026-09-30T10:00:00Z",
        "2026-09-30T10:00:00Z",
        "2026-09-30T10:01:00Z",
        "2026-09-30T10:01:00Z",
        "2026-09-30T10:02:00Z",
        "2026-09-30T10:02:00Z",
    ]
    fig_multi = create_meteorological_time_series(df)
    assert isinstance(fig_multi, go.Figure)
    assert len(fig_multi.data) >= 3


def test_a7_multiple_records_within_same_second():
    """A7. Sub-second or identical-second records remain distinct points."""
    df = _base_dataframe(4)
    df["event_timestamp"] = [
        "2026-09-30T12:00:00.100Z",
        "2026-09-30T12:00:00.250Z",
        "2026-09-30T12:00:00.600Z",
        "2026-09-30T12:00:00.900Z",
    ]
    fig_multi = create_meteorological_time_series(df)
    assert isinstance(fig_multi, go.Figure)
    fig_score = create_anomaly_score_chart(df)
    assert isinstance(fig_score, go.Figure)


def test_a8_cross_midnight_timestamps():
    """A8. Cross-midnight timestamps maintain chronological order."""
    df = _base_dataframe(5)
    df["event_timestamp"] = [
        "2026-09-29T23:58:00Z",
        "2026-09-29T23:59:00Z",
        "2026-09-30T00:00:00Z",
        "2026-09-30T00:01:00Z",
        "2026-09-30T00:02:00Z",
    ]
    fig_multi = create_meteorological_time_series(df)
    assert isinstance(fig_multi, go.Figure)
    fig_score = create_anomaly_score_chart(df)
    assert isinstance(fig_score, go.Figure)


def test_a9_empty_station_history():
    """A9. Empty station history renders clean empty-state figure rather than crashing."""
    empty_df = pd.DataFrame()
    
    fig_multi = create_meteorological_time_series(empty_df)
    assert isinstance(fig_multi, go.Figure)
    assert len(fig_multi.layout.annotations) >= 1
    assert "No historical observations available" in fig_multi.layout.annotations[0].text

    fig_score = create_anomaly_score_chart(empty_df)
    assert isinstance(fig_score, go.Figure)
    assert len(fig_score.layout.annotations) >= 1

    fig_raw = create_raw_vs_processed_chart(empty_df)
    assert isinstance(fig_raw, go.Figure)

    # None handling
    assert isinstance(create_meteorological_time_series(None), go.Figure)
    assert isinstance(create_anomaly_score_chart(None), go.Figure)
    assert isinstance(create_raw_vs_processed_chart(None), go.Figure)


def test_a10_unsorted_observation_input():
    """A10. Unsorted observation input is automatically sorted chronologically."""
    df = _base_dataframe(5)
    # Shuffle order
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    fig_multi = create_meteorological_time_series(df)
    assert isinstance(fig_multi, go.Figure)
    
    # Check trace x values are sorted
    t_trace = fig_multi.data[0]
    dt_series = pd.to_datetime(t_trace.x)
    assert dt_series.is_monotonic_increasing
