"""
Explainability, traceable human-readable evidence, and competing hypotheses presentation component.
Translates real backend evidence codes and metrics into clear, professional operator language.
Provides a central sanitization layer to eliminate any raw HTML/CSS markup before rendering.
"""
import re
import html
from html.parser import HTMLParser
import streamlit as st
from typing import List, Optional, Dict, Any


# ── Central HTML/CSS Evidence Sanitizer ──────────────────────────────────────

class _HTMLTextExtractor(HTMLParser):
    """HTML parser that extracts text while ignoring style and script elements and preserving boundaries."""
    def __init__(self):
        super().__init__()
        self.result = []
        self.in_ignored_tag = False

    def handle_starttag(self, tag, attrs):
        if tag.lower() in ("style", "script"):
            self.in_ignored_tag = True
        else:
            self.result.append(" ")

    def handle_endtag(self, tag):
        if tag.lower() in ("style", "script"):
            self.in_ignored_tag = False
        else:
            self.result.append(" ")

    def handle_data(self, d):
        if not self.in_ignored_tag:
            self.result.append(d)

    def handle_entityref(self, name):
        if not self.in_ignored_tag:
            self.result.append(html.unescape(f"&{name};"))

    def handle_charref(self, name):
        if not self.in_ignored_tag:
            self.result.append(html.unescape(f"&#{name};"))


def sanitize_evidence_text(raw_evidence: Any) -> str:
    """
    Central sanitizer that transforms any evidence input into clean, safe plain text.
    Strips HTML tags, removes CSS declarations/fragments, decodes HTML entities,
    preserves emojis and readable text, and normalizes whitespace.
    """
    if raw_evidence is None:
        return ""
    if not isinstance(raw_evidence, str):
        text = str(raw_evidence)
    else:
        text = raw_evidence

    if not text or not text.strip():
        return ""

    # 1. Parse HTML tags and extract inner text
    try:
        extractor = _HTMLTextExtractor()
        extractor.feed(text)
        cleaned = "".join(extractor.result)
    except Exception:
        cleaned = re.sub(r"<[^>]+>", " ", text)

    # 2. Decode HTML entities (&amp;, &lt;, &gt;, &quot;, &#39;, etc.)
    cleaned = html.unescape(cleaned)

    # 3. Strip any residual style attributes or CSS declarations outside/inside tags
    css_patterns = [
        r"style\s*=\s*(?:\"[^\"]*\"|'[^']*'|\S+)",
        r"class\s*=\s*(?:\"[^\"]*\"|'[^']*'|\S+)",
        r"(?:display|align-items|justify-content|background(?:-color)?|color|border(?:-radius|-left|-right|-top|-bottom)?|padding(?:-left|-right|-top|-bottom)?|margin(?:-left|-right|-top|-bottom)?|font-(?:size|weight|family)|line-height|box-shadow|text-align|flex|gap)\s*:\s*[^;,\n)]+;?",
        r"rgba?\s*\([^)]*\)",
    ]
    for pattern in css_patterns:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    # 4. Remove any stray/broken markup brackets
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)

    # 5. Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def sanitize_evidence_list(evidence_list: Optional[List[Any]]) -> List[str]:
    """
    Sanitizes a collection of evidence items, returning a list of non-empty plain-text strings.
    """
    if not evidence_list:
        return []
    sanitized = []
    for item in evidence_list:
        cleaned = sanitize_evidence_text(item)
        if cleaned:
            sanitized.append(cleaned)
    return sanitized


# ── Human-Readable Dictionaries for Operators ────────────────────────────────

EVIDENCE_CODE_DESCRIPTIONS: Dict[str, str] = {
    # Temperature Triggers
    "TEMPERATURE_SPIKE_POSITIVE": "Rapid temperature increase detected — the temperature is changing at an unusually high rate compared with the expected operating pattern.",
    "TEMPERATURE_SPIKE_NEGATIVE": "Abrupt temperature drop detected — rapid negative excursion outside normal physical rate of change.",
    "TEMPERATURE_UNREALISTIC_RATE": "Unrealistic temperature rate of change exceeding physical atmospheric limits.",
    "ROBUST_ZSCORE_EXCURSION_TEMPERATURE": "Temperature differs significantly from the station's recent expected pattern.",
    "FROZEN_TEMPERATURE": "Temperature remained unchanged for an unusually long period, which may indicate a stuck sensor.",
    
    # Pressure Triggers
    "PRESSURE_SPIKE_POSITIVE": "Sudden barometric pressure surge detected exceeding physical rate limits.",
    "PRESSURE_SPIKE_NEGATIVE": "Sudden barometric pressure drop detected exceeding physical rate limits.",
    "PRESSURE_UNREALISTIC_RATE": "Unrealistic barometric pressure rate of change exceeding physical atmospheric limits.",
    "ROBUST_ZSCORE_EXCURSION_PRESSURE": "Pressure differs significantly from the station's recent expected pattern.",
    "FROZEN_PRESSURE": "Pressure remained unchanged for an extended period, which may indicate a stuck sensor.",
    
    # Humidity Triggers
    "RELATIVE_HUMIDITY_SPIKE_POSITIVE": "Sudden relative humidity surge detected exceeding physical rate limits.",
    "RELATIVE_HUMIDITY_SPIKE_NEGATIVE": "Sudden relative humidity drop detected exceeding physical rate limits.",
    "RELATIVE_HUMIDITY_UNREALISTIC_RATE": "Unrealistic relative humidity rate of change exceeding physical atmospheric limits.",
    "ROBUST_ZSCORE_EXCURSION_RELATIVE_HUMIDITY": "Relative humidity differs significantly from the station's recent expected pattern.",
    "ROBUST_ZSCORE_EXCURSION_RH": "Relative humidity differs significantly from the station's recent expected pattern.",
    "FROZEN_RELATIVE_HUMIDITY": "Relative humidity remained unchanged for an extended period, which may indicate a stuck sensor.",
    
    # Thermodynamic & Multivariate Triggers
    "THERMODYNAMIC_INCONSISTENCY": "Temperature, pressure, and humidity show an unusual thermodynamic relationship.",
    "WEATHER_EVENT_EVIDENCE": "Multi-variable atmospheric changes move together in a pattern consistent with a genuine weather event.",
    "WEATHER_EVENT_EVIDENCE_MULTIVARIATE_CONSISTENT": "Multi-variable atmospheric pattern is physically consistent with genuine weather activity.",
    "MULTIVARIATE_CONSISTENT": "Temperature, pressure, and humidity measurements move consistently with each other.",
    
    # Telemetry & Integrity Triggers
    "DATA_TELEMETRY_INTEGRITY_FLAG": "A data or communication issue affected this observation.",
    "MISSING_SLOTS": "Missing telemetry packet slots detected in the incoming data stream.",
    "COMMUNICATION_GAP": "Communication link interruption or packet loss detected.",
    "DELAYED": "Observation arrived late past the expected sampling cadence.",
    "COLD_START_INSUFFICIENT_HISTORY": "Station initialization in progress — accumulating statistical baseline observations.",
    "QUARANTINE": "Observation quarantined to protect adaptive baseline models from potential corruption.",
    "RANGE_VIOLATION": "Observed measurement falls outside plausible physical meteorological bounds.",
}

ROOT_CAUSE_DESCRIPTIONS: Dict[str, str] = {
    "NORMAL": "Normal Meteorological Conditions",
    "SENSOR_SPIKE": "Sensor Hardware Spike",
    "SENSOR_STUCK_FROZEN": "Sensor Flatline / Frozen",
    "GRADUAL_DRIFT": "Gradual Sensor Calibration Drift",
    "MULTIVARIATE_INCONSISTENCY": "Cross-Sensor Physical Inconsistency",
    "TEMPORAL_INCONSISTENCY": "Abrupt Temporal Step Change",
    "DATA_TELEMETRY": "Data Communication / Packet Loss",
    "WEATHER_EVENT": "Possible Genuine Weather Event",
    "COMPETING_EVIDENCE": "Ambiguous / Competing Hypotheses",
    "UNKNOWN": "Unclassified Event",
}

DEGRADATION_DESCRIPTIONS: Dict[str, str] = {
    "NO_DEGRADATION_EVIDENCE": "Nominal (No degradation detected)",
    "ISOLATED_EXCURSION": "Isolated Transient Excursion",
    "CALIBRATION_DRIFT": "Gradual Calibration Drift",
    "RECURRING_ANOMALIES": "Recurring Anomaly Triggers",
    "SENSOR_FLATLINE": "Sensor Flatline Detected",
    "INTERMITTENT_DROPOUTS": "Intermittent Packet Dropouts",
    "SEVERE_DATA_LOSS": "Severe Data Loss",
}

MAINTENANCE_DESCRIPTIONS: Dict[str, str] = {
    "NONE": "None required (Nominal)",
    "MONITOR": "Routine monitoring recommended",
    "INSPECTION_RECOMMENDED": "Field inspection recommended",
    "URGENT_MAINTENANCE": "Urgent maintenance required",
}


def humanize_evidence_code(code: Any) -> str:
    """Translate raw backend trigger code into clear operator language."""
    if code is None:
        return "Unknown trigger"
    cleaned = sanitize_evidence_text(code)
    if not cleaned:
        return "Unknown trigger"
    if cleaned in EVIDENCE_CODE_DESCRIPTIONS:
        return EVIDENCE_CODE_DESCRIPTIONS[cleaned]
    if cleaned.upper() in EVIDENCE_CODE_DESCRIPTIONS:
        return EVIDENCE_CODE_DESCRIPTIONS[cleaned.upper()]
    if "_" in cleaned and not any(cleaned.startswith(e) for e in ("⚠️", "🌦️", "📡", "🔍", "🚨", "🔧")):
        return cleaned.replace("_", " ").capitalize()
    return cleaned


def humanize_root_cause(cause: Optional[str]) -> str:
    """Translate raw backend root cause code into clear operator language."""
    if not cause:
        return "Normal"
    cause_str = sanitize_evidence_text(cause).upper()
    return ROOT_CAUSE_DESCRIPTIONS.get(cause_str, cause_str.replace("_", " ").title())


def humanize_degradation(deg: Optional[str]) -> str:
    """Translate raw backend degradation state into clear operator language."""
    if not deg:
        return "Nominal"
    deg_str = sanitize_evidence_text(deg).upper()
    return DEGRADATION_DESCRIPTIONS.get(deg_str, deg_str.replace("_", " ").title())


def humanize_maintenance(maint: Optional[str]) -> str:
    """Translate raw backend maintenance recommendation into clear operator language."""
    if not maint:
        return "None required"
    maint_str = sanitize_evidence_text(maint).upper()
    return MAINTENANCE_DESCRIPTIONS.get(maint_str, maint_str.replace("_", " ").title())


def render_evidence_chips(evidence_codes: Optional[List[Any]]):
    """
    Renders human-readable evidence items cleanly as plain English text.
    Uses safe native Streamlit markdown without exposing raw HTML tags or CSS.
    All items pass through the central sanitization layer.
    """
    if not evidence_codes:
        st.markdown("*No abnormal evidence triggers recorded.*")
        return

    cleaned_codes = sanitize_evidence_list(evidence_codes)
    if not cleaned_codes:
        st.markdown("*No abnormal evidence triggers recorded.*")
        return

    for item in cleaned_codes:
        human_text = humanize_evidence_code(item)
        c_upper = str(item).upper()
        
        # Check if human_text already begins with an emoji
        has_leading_emoji = any(human_text.startswith(e) for e in ("⚠️", "🌦️", "📡", "🔍", "🚨", "🔧", "•"))
        
        if has_leading_emoji:
            st.markdown(f"• {human_text}")
        else:
            if "WEATHER" in c_upper or "CONSISTENT" in c_upper:
                icon = "🌦️"
            elif any(k in c_upper for k in ("SPIKE", "STUCK", "FLATLINE", "FROZEN", "DRIFT", "FAULT", "ABNORMAL", "UNREALISTIC")):
                icon = "⚠️"
            elif any(k in c_upper for k in ("INTEGRITY", "LATE", "GAP", "DROPOUT", "LOSS", "MISSING", "TELEMETRY")):
                icon = "📡"
            else:
                icon = "🔍"
            st.markdown(f"• {icon} {human_text}")


def render_hypothesis_attribution(
    weather_likelihood: Optional[float],
    sensor_fault_likelihood: Optional[float],
    root_cause: Optional[str],
    plausibility: Optional[float],
):
    """Renders weather vs sensor fault consistency with operator explanations."""
    w_lik = 0.0 if weather_likelihood is None else float(weather_likelihood)
    s_lik = 0.0 if sensor_fault_likelihood is None else float(sensor_fault_likelihood)
    plaus = 1.0 if plausibility is None else float(plausibility)
    
    w_expl = (
        "Measurements follow a physical pattern consistent with genuine atmospheric activity."
        if w_lik >= 0.6
        else "Observed changes show weak correlation with expected atmospheric patterns."
    )
    s_expl = (
        "Abrupt single-channel change without expected atmospheric correlation."
        if s_lik >= 0.6
        else "Little to no isolated sensor defect signals detected."
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(
            f"""
            <div style="background-color: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                <div style="font-size: 0.85rem; color: #93c5fd; font-weight: 600; margin-bottom: 2px;">🌦️ Weather-Event Consistency</div>
                <div style="font-size: 1.4rem; font-weight: 700; color: #60a5fa;">{w_lik * 100:.1f}%</div>
                <div style="font-size: 0.78rem; color: #cbd5e1; margin-top: 3px; line-height: 1.4;">{w_expl}</div>
                <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Thermodynamic Plausibility: <b>{plaus:.2f}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
    with col2:
        cause_clean = humanize_root_cause(root_cause)
        st.markdown(
            f"""
            <div style="background-color: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                <div style="font-size: 0.85rem; color: #fca5a5; font-weight: 600; margin-bottom: 2px;">🛠️ Sensor / Data Fault Evidence</div>
                <div style="font-size: 1.4rem; font-weight: 700; color: #f87171;">{s_lik * 100:.1f}%</div>
                <div style="font-size: 0.78rem; color: #cbd5e1; margin-top: 3px; line-height: 1.4;">{s_expl}</div>
                <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Likely Cause: <b>{cause_clean}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_reasoning_box(reasoning_summary: Optional[str], uncertainty_state: Optional[str]):
    """Renders human-readable reasoning summary with operator uncertainty context."""
    raw_summary = reasoning_summary or "The observation is within normal physical limits and consistent with recent station behavior."
    summary = sanitize_evidence_text(raw_summary)
    u_state = (uncertainty_state or "LOW").upper()
    
    u_label_map = {
        "LOW": "High Assessment Certainty",
        "MODERATE": "Moderate Assessment Uncertainty",
        "HIGH": "High Uncertainty (Review Recommended)",
        "COLD_START": "Station Baseline Initialization",
    }
    u_label = u_label_map.get(u_state, f"Uncertainty: {u_state}")
    
    st.markdown(
        f"""
        <div style="background-color: rgba(30, 41, 59, 0.7); border-left: 4px solid #3b82f6; border-radius: 0 8px 8px 0; padding: 12px 16px; margin: 10px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="font-size: 0.85rem; font-weight: 600; color: #93c5fd;">🧠 Why This Was Flagged</span>
                <span style="font-size: 0.75rem; background-color: rgba(255, 255, 255, 0.1); color: #cbd5e1; padding: 2px 8px; border-radius: 4px;">{u_label}</span>
            </div>
            <div style="font-size: 0.92rem; color: #e2e8f0; line-height: 1.55;">
                {summary}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
