"""
Dashboard metric cards, status badges, and confidence meters.
Translates internal flags into clear operator status indicators.
"""
import streamlit as st
from typing import Optional, Dict, Any


def render_decision_badge(decision_state: str, severity: Optional[str] = None):
    state_upper = (decision_state or "NORMAL").upper()
    sev_upper = (severity or "LOW").upper()
    
    color_map = {
        "NORMAL": {"bg": "rgba(34, 197, 94, 0.15)", "text": "#4ade80", "border": "#22c55e", "icon": "🟢", "label": "Normal"},
        "SUSPECT": {"bg": "rgba(245, 158, 11, 0.15)", "text": "#fbbf24", "border": "#f59e0b", "icon": "🟠", "label": "Needs Review"},
        "ANOMALY": {"bg": "rgba(239, 68, 68, 0.15)", "text": "#f87171", "border": "#ef4444", "icon": "🔴", "label": "Anomalous"},
        "ANOMALOUS": {"bg": "rgba(239, 68, 68, 0.15)", "text": "#f87171", "border": "#ef4444", "icon": "🔴", "label": "Anomalous"},
        "AMBIGUOUS": {"bg": "rgba(249, 115, 22, 0.15)", "text": "#fb923c", "border": "#f97316", "icon": "⚠️", "label": "Ambiguous"},
        "ABSTAIN": {"bg": "rgba(148, 163, 184, 0.15)", "text": "#cbd5e1", "border": "#94a3b8", "icon": "⚪", "label": "Insufficient Baseline"},
        "QUARANTINED": {"bg": "rgba(168, 85, 247, 0.15)", "text": "#c084fc", "border": "#a855f7", "icon": "🔒", "label": "Quarantined"},
        "CRITICAL": {"bg": "rgba(239, 68, 68, 0.25)", "text": "#fca5a5", "border": "#ef4444", "icon": "🚨", "label": "Critical Anomaly"},
    }
    
    style = color_map.get(state_upper, {"bg": "rgba(148, 163, 184, 0.15)", "text": "#cbd5e1", "border": "#94a3b8", "icon": "⚪", "label": state_upper.title()})
    
    sev_map = {"LOW": "Low", "MODERATE": "Moderate", "HIGH": "High", "CRITICAL": "Critical"}
    sev_clean = sev_map.get(sev_upper, sev_upper.title())
    sev_badge = f"<span style='background-color:rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; margin-left: 8px;'>Severity: {sev_clean}</span>" if state_upper in ["ANOMALY", "ANOMALOUS", "SUSPECT", "AMBIGUOUS", "CRITICAL"] else ""
    
    badge_html = f"""
    <div style="
        display: inline-flex;
        align-items: center;
        background-color: {style['bg']};
        color: {style['text']};
        border: 1px solid {style['border']};
        padding: 6px 14px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 1rem;
        letter-spacing: 0.3px;
        margin-bottom: 8px;
    ">
        <span style="margin-right: 6px;">{style['icon']}</span>
        <span>{style['label']}</span>
        {sev_badge}
    </div>
    """
    st.markdown(badge_html, unsafe_allow_html=True)


def render_admission_badge(admission_state: str):
    adm_upper = (admission_state or "ADMIT").upper()
    color_map = {
        "ADMIT": {"color": "#4ade80", "icon": "🟢", "label": "Accepted", "desc": "Admitted to adaptive baseline"},
        "QUARANTINE": {"color": "#fb923c", "icon": "🟠", "label": "Quarantined", "desc": "Isolated to protect baseline against poisoning"},
        "REJECT": {"color": "#f87171", "icon": "🔴", "label": "Rejected", "desc": "Blocked by data integrity gate"},
    }
    info = color_map.get(adm_upper, {"color": "#94a3b8", "icon": "⚪", "label": adm_upper.title(), "desc": "Unknown handling state"})
    st.markdown(
        f"""<div style='font-size: 0.85rem; color: {info['color']}; padding: 4px 0;'>
        {info['icon']} <strong>Data Handling Status:</strong> {info['label']} <span style='color: #94a3b8;'>({info['desc']})</span>
        </div>""",
        unsafe_allow_html=True,
    )


def render_score_bar(label: str, value: Optional[float], max_val: float = 1.0, color: str = "#3b82f6", warn_threshold: float = 0.35, crit_threshold: float = 0.65):
    val = 0.0 if value is None else float(value)
    pct = min(max(val / max_val * 100.0, 0.0), 100.0)
    
    # Dynamic coloring if warning thresholds provided
    bar_color = color
    if val >= crit_threshold:
        bar_color = "#ef4444"
    elif val >= warn_threshold:
        bar_color = "#f59e0b"
        
    st.markdown(
        f"""
        <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 4px;">
                <span style="font-weight: 500; color: #cbd5e1;">{label}</span>
                <span style="font-weight: 700; color: {bar_color};">{val:.3f}</span>
            </div>
            <div style="background-color: rgba(255, 255, 255, 0.1); border-radius: 4px; height: 8px; width: 100%; overflow: hidden;">
                <div style="background-color: {bar_color}; width: {pct}%; height: 100%; border-radius: 4px; transition: width 0.4s ease;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
