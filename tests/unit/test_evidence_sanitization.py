"""
Unit tests for Evidence HTML/CSS Sanitization and Normalization Layer.
Tests central evidence sanitization to ensure zero raw HTML/CSS leaks to operators.
"""
import pytest
from dashboard.components.explainability import (
    sanitize_evidence_text,
    sanitize_evidence_list,
    humanize_evidence_code,
)


def test_1_plain_text():
    """TEST 1 — Plain text passes through intact."""
    inp = "Rapid temperature increase detected."
    assert sanitize_evidence_text(inp) == "Rapid temperature increase detected."


def test_2_nested_span():
    """TEST 2 — Nested span elements are unpacked to clean plain text."""
    inp = "<span><span>⚠️</span><span>Pressure reading remained unchanged (flatline)</span></span>"
    assert sanitize_evidence_text(inp) == "⚠️ Pressure reading remained unchanged (flatline)"


def test_3_styled_span():
    """TEST 3 — Styled span with inline CSS is stripped cleanly."""
    inp = "<span style='display:inline-flex; color:#f87171; border:1px solid red;'>⚠️ Rapid temperature increase detected</span>"
    assert sanitize_evidence_text(inp) == "⚠️ Rapid temperature increase detected"


def test_4_multiple_html_blocks():
    """TEST 4 — Multiple HTML blocks in one evidence string."""
    inp = "<span>⚠️ Temperature anomaly</span> <span>Rapid change detected</span>"
    assert sanitize_evidence_text(inp) == "⚠️ Temperature anomaly Rapid change detected"


def test_5_html_entities():
    """TEST 5 — HTML entities decoded properly."""
    inp = "<span>Temperature &gt; expected range &amp; rapid change detected</span>"
    assert sanitize_evidence_text(inp) == "Temperature > expected range & rapid change detected"


def test_6_css_fragments_outside_tags():
    """TEST 6 — CSS fragments outside tags are removed while keeping readable text."""
    inp = "display: inline-flex; background-color: red; border: 1px solid red; Rapid temperature increase detected."
    assert sanitize_evidence_text(inp) == "Rapid temperature increase detected."


def test_7_none_input():
    """TEST 7 — None returns safe empty string without exception."""
    assert sanitize_evidence_text(None) == ""


def test_8_empty_string():
    """TEST 8 — Empty string returns safe empty string."""
    assert sanitize_evidence_text("") == ""
    assert sanitize_evidence_text("   ") == ""


def test_9_multiple_evidence_items():
    """TEST 9 — Multiple evidence items in a list are independently sanitized."""
    raw_list = [
        "Rapid temperature increase detected.",
        "<span><span>⚠️</span><span>Pressure reading remained unchanged (flatline)</span></span>",
        "<span style='display:inline-flex; color:#f87171; border:1px solid red;'>⚠️ Rapid temperature increase detected</span>",
        None,
        "",
        "<span>Temperature &gt; expected range &amp; rapid change detected</span>",
    ]
    expected = [
        "Rapid temperature increase detected.",
        "⚠️ Pressure reading remained unchanged (flatline)",
        "⚠️ Rapid temperature increase detected",
        "Temperature > expected range & rapid change detected",
    ]
    assert sanitize_evidence_list(raw_list) == expected


def test_10_emoji_preservation():
    """TEST 10 — Emojis in evidence are preserved intact."""
    inp = "<span>⚠️</span><span>Frozen temperature detected</span>"
    assert sanitize_evidence_text(inp) == "⚠️ Frozen temperature detected"


def test_complex_full_markup_example():
    """Tests the exact complex example from the problem specification."""
    inp = """<span style="display: inline-flex; align-items: center; background-color: rgba(239, 68, 68, 0.1); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); padding: 4px 12px; border-radius: 14px;">
<span style="margin-right: 6px;">⚠️</span>
<span>Pressure reading remained unchanged (flatline)</span>
</span>"""
    assert sanitize_evidence_text(inp) == "⚠️ Pressure reading remained unchanged (flatline)"


def test_non_string_types():
    """Tests handling of integers, floats, dicts or unexpected objects safely."""
    assert sanitize_evidence_text(123) == "123"
    assert sanitize_evidence_text(99.5) == "99.5"


def test_humanize_evidence_code_integration():
    """Tests that humanize_evidence_code correctly integrates sanitization."""
    assert humanize_evidence_code("TEMPERATURE_SPIKE_POSITIVE") == "Rapid temperature increase detected — the temperature is changing at an unusually high rate compared with the expected operating pattern."
    
    # HTML formatted trigger code
    html_input = "<span><span>⚠️</span><span>Pressure reading remained unchanged (flatline)</span></span>"
    assert humanize_evidence_code(html_input) == "⚠️ Pressure reading remained unchanged (flatline)"
