"""
Interactive Plotly charts for time-series trends, anomaly markers, and raw vs processed comparisons.
Ensures robust datetime x-axis indexing, null/NaN safety, and graceful degradation on empty data.
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Optional


def _create_empty_chart(message: str = "No historical observations available for this station.", height: int = 280) -> go.Figure:
    """Helper to generate a styled empty state figure."""
    fig = go.Figure()
    fig.update_layout(
        height=height,
        margin=dict(l=40, r=20, t=40, b=30),
        template="plotly_dark",
        plot_bgcolor="#0e1117",
        paper_bgcolor="rgba(0,0,0,0)",
        annotations=[
            dict(
                text=message,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=14, color="#94a3b8"),
            )
        ],
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
    )
    return fig


def create_meteorological_time_series(df: Optional[pd.DataFrame]) -> go.Figure:
    """
    Creates a synchronized 3-panel time series chart for Temperature, Pressure, and RH
    with color-coded anomaly scatter markers.
    Uses native datetime x-axis, null-safe value handling, and connects no gaps over nulls.
    """
    if df is None or df.empty:
        return _create_empty_chart("No historical observations available for this station.", height=500)

    try:
        # Sort chronologically by native datetime
        df_sorted = df.copy()
        if "event_timestamp" in df_sorted.columns:
            df_sorted["dt"] = pd.to_datetime(df_sorted["event_timestamp"], errors="coerce")
            df_sorted = df_sorted.sort_values(by="dt", ascending=True)
        else:
            df_sorted["dt"] = pd.date_range(start=pd.Timestamp.now(), periods=len(df_sorted), freq="min")

        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=(
                "🌡️ Temperature (°C)",
                "🧭 Barometric Pressure (hPa)",
                "💧 Relative Humidity (%)",
            ),
        )

        # 1. Temperature trace
        t_vals = pd.to_numeric(df_sorted.get("temperature"), errors="coerce") if "temperature" in df_sorted.columns else None
        fig.add_trace(
            go.Scatter(
                x=df_sorted["dt"],
                y=t_vals,
                mode="lines+markers",
                name="Temperature",
                line=dict(color="#f97316", width=2.5),
                marker=dict(size=5),
                connectgaps=False,
                hovertemplate="Time: %{x|%Y-%m-%d %H:%M:%S}<br>Temp: %{y:.2f} °C<extra></extra>",
            ),
            row=1,
            col=1,
        )

        # 2. Pressure trace
        p_vals = pd.to_numeric(df_sorted.get("pressure"), errors="coerce") if "pressure" in df_sorted.columns else None
        fig.add_trace(
            go.Scatter(
                x=df_sorted["dt"],
                y=p_vals,
                mode="lines+markers",
                name="Pressure",
                line=dict(color="#3b82f6", width=2.5),
                marker=dict(size=5),
                connectgaps=False,
                hovertemplate="Time: %{x|%Y-%m-%d %H:%M:%S}<br>Pressure: %{y:.2f} hPa<extra></extra>",
            ),
            row=2,
            col=1,
        )

        # 3. Relative Humidity trace
        rh_vals = pd.to_numeric(df_sorted.get("relative_humidity"), errors="coerce") if "relative_humidity" in df_sorted.columns else None
        fig.add_trace(
            go.Scatter(
                x=df_sorted["dt"],
                y=rh_vals,
                mode="lines+markers",
                name="Humidity",
                line=dict(color="#10b981", width=2.5),
                marker=dict(size=5),
                connectgaps=False,
                hovertemplate="Time: %{x|%Y-%m-%d %H:%M:%S}<br>Humidity: %{y:.2f} %<extra></extra>",
            ),
            row=3,
            col=1,
        )

        # Highlight Anomalies safely if anomaly_score exists
        if "anomaly_score" in df_sorted.columns:
            scores_num = pd.to_numeric(df_sorted["anomaly_score"], errors="coerce")
            anom_mask = scores_num >= 0.35
            anom_df = df_sorted[anom_mask]
            if not anom_df.empty:
                hover_texts = []
                for _, r in anom_df.iterrows():
                    sc = r.get("anomaly_score")
                    sc_str = f"{sc:.2f}" if pd.notnull(sc) and isinstance(sc, (int, float)) else "N/A"
                    rc = r.get("root_cause_category") or "ANOMALY"
                    hover_texts.append(f"Anomaly Score: {sc_str} ({rc})")

                anom_t_vals = pd.to_numeric(anom_df.get("temperature"), errors="coerce") if "temperature" in anom_df.columns else None
                fig.add_trace(
                    go.Scatter(
                        x=anom_df["dt"],
                        y=anom_t_vals,
                        mode="markers",
                        name="Anomaly Event",
                        marker=dict(color="#ef4444", size=11, symbol="circle-open", line=dict(width=3, color="#ef4444")),
                        hoverinfo="text",
                        text=hover_texts,
                        connectgaps=False,
                    ),
                    row=1,
                    col=1,
                )

        fig.update_layout(
            height=620,
            margin=dict(l=40, r=20, t=40, b=30),
            template="plotly_dark",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="#0e1117",
            paper_bgcolor="rgba(0,0,0,0)",
        )

        fig.update_yaxes(gridcolor="rgba(255, 255, 255, 0.1)")
        fig.update_xaxes(gridcolor="rgba(255, 255, 255, 0.1)")

        return fig

    except Exception as e:
        return _create_empty_chart(f"Unable to render time series chart ({str(e)})", height=500)


def create_anomaly_score_chart(df: Optional[pd.DataFrame]) -> go.Figure:
    """
    Renders Anomaly Score progression with threshold boundaries.
    Uses native datetime x-axis and null-safe color scaling.
    """
    if df is None or df.empty or "anomaly_score" not in df.columns:
        return _create_empty_chart("No anomaly score data available.", height=280)

    try:
        df_sorted = df.copy()
        if "event_timestamp" in df_sorted.columns:
            df_sorted["dt"] = pd.to_datetime(df_sorted["event_timestamp"], errors="coerce")
            df_sorted = df_sorted.sort_values(by="dt", ascending=True)
        else:
            df_sorted["dt"] = pd.date_range(start=pd.Timestamp.now(), periods=len(df_sorted), freq="min")

        scores_num = pd.to_numeric(df_sorted["anomaly_score"], errors="coerce")
        marker_colors = scores_num.fillna(0.0)

        fig = go.Figure()

        # Score line
        fig.add_trace(
            go.Scatter(
                x=df_sorted["dt"],
                y=scores_num,
                mode="lines+markers",
                name="Anomaly Score",
                line=dict(color="#f59e0b", width=2.5),
                marker=dict(
                    size=7,
                    color=marker_colors,
                    colorscale=[[0, "#22c55e"], [0.35, "#f59e0b"], [0.65, "#ef4444"], [1.0, "#dc2626"]],
                    cmin=0.0,
                    cmax=1.0,
                    showscale=False,
                ),
                connectgaps=False,
                hovertemplate="Time: %{x|%Y-%m-%d %H:%M:%S}<br>Anomaly Score: %{y:.3f}<extra></extra>",
            )
        )

        # Threshold lines
        fig.add_hline(y=0.35, line_dash="dash", line_color="#f59e0b", annotation_text="Suspect Threshold (0.35)", annotation_position="top left")
        fig.add_hline(y=0.65, line_dash="dash", line_color="#ef4444", annotation_text="Anomaly Threshold (0.65)", annotation_position="top left")

        fig.update_layout(
            title="Composite Anomaly Score Trajectory",
            yaxis=dict(title="Score [0.0 - 1.0]", range=[0.0, 1.05], gridcolor="rgba(255, 255, 255, 0.1)"),
            xaxis=dict(title="Timestamp", gridcolor="rgba(255, 255, 255, 0.1)"),
            height=280,
            margin=dict(l=40, r=20, t=40, b=30),
            template="plotly_dark",
            plot_bgcolor="#0e1117",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    except Exception as e:
        return _create_empty_chart(f"Unable to render anomaly score chart ({str(e)})", height=280)


def create_raw_vs_processed_chart(df: Optional[pd.DataFrame], channel: str = "temperature") -> go.Figure:
    """
    Visualizes RAW vs PROCESSED observations to ensure total transparency.
    """
    if df is None or df.empty:
        return _create_empty_chart(f"No telemetry data available for {channel}.", height=260)

    try:
        df_sorted = df.copy()
        if "event_timestamp" in df_sorted.columns:
            df_sorted["dt"] = pd.to_datetime(df_sorted["event_timestamp"], errors="coerce")
            df_sorted = df_sorted.sort_values(by="dt", ascending=True)
        else:
            df_sorted["dt"] = pd.date_range(start=pd.Timestamp.now(), periods=len(df_sorted), freq="min")

        raw_col = f"{channel}_raw"
        proc_col = channel

        fig = go.Figure()

        if raw_col in df_sorted.columns:
            raw_vals = pd.to_numeric(df_sorted[raw_col], errors="coerce")
            fig.add_trace(
                go.Scatter(
                    x=df_sorted["dt"],
                    y=raw_vals,
                    mode="lines+markers",
                    name=f"RAW ({channel.capitalize()})",
                    line=dict(color="#94a3b8", width=2, dash="dot"),
                    marker=dict(symbol="circle-open", size=8),
                    connectgaps=False,
                    hovertemplate="Time: %{x|%Y-%m-%d %H:%M:%S}<br>RAW: %{y:.2f}<extra></extra>",
                )
            )

        if proc_col in df_sorted.columns:
            proc_vals = pd.to_numeric(df_sorted[proc_col], errors="coerce")
            fig.add_trace(
                go.Scatter(
                    x=df_sorted["dt"],
                    y=proc_vals,
                    mode="lines",
                    name=f"PROCESSED ({channel.capitalize()})",
                    line=dict(color="#38bdf8", width=2.5),
                    connectgaps=False,
                    hovertemplate="Time: %{x|%Y-%m-%d %H:%M:%S}<br>PROCESSED: %{y:.2f}<extra></extra>",
                )
            )

        fig.update_layout(
            title=f"RAW Telemetry vs Processed Channel ({channel.capitalize()})",
            height=260,
            margin=dict(l=40, r=20, t=40, b=30),
            template="plotly_dark",
            plot_bgcolor="#0e1117",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        fig.update_yaxes(gridcolor="rgba(255, 255, 255, 0.1)")
        fig.update_xaxes(gridcolor="rgba(255, 255, 255, 0.1)")
        return fig

    except Exception as e:
        return _create_empty_chart(f"Unable to render comparison chart ({str(e)})", height=260)
