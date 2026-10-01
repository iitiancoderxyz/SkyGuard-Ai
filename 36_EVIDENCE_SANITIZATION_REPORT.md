# 36_EVIDENCE_SANITIZATION_REPORT.md

# SkyGuard AI (SIH26073) — Evidence HTML/CSS Sanitization & Normalization Report

**Date:** 2026-10-01  
**Status:** Completed & Validated  
**Test Baseline:** 158 / 158 Passing (100%)

---

## 1. Root Cause

In earlier versions of the dashboard components, evidence items and trigger badges were sometimes formatted with inline HTML/CSS markup (e.g. `<span style="...">`, nested `<span>`, or inline CSS attributes such as `display: inline-flex; border-radius: 14px;`). When evidence items containing HTML markup or CSS fragments passed through presentation functions into Streamlit without central parsing and sanitization, raw HTML/CSS strings could become visible to operators in the Evidence section.

---

## 2. Sanitization Function

A robust, centralized sanitization layer was implemented in `dashboard/components/explainability.py`:

- **`_HTMLTextExtractor(HTMLParser)`**:
  - Subclasses Python's standard `html.parser.HTMLParser`.
  - Safely extracts inner text across nested `<span>`, `<div>`, or other HTML elements.
  - Automatically inserts boundary spaces between consecutive tags to prevent word gluing.
  - Ignores internal text in `<style>` and `<script>` blocks.
  - Decodes character and entity references (`&amp;`, `&lt;`, `&gt;`, `&quot;`, `&#39;`).

- **`sanitize_evidence_text(raw_evidence: Any) -> str`**:
  - Accepts arbitrary inputs (`None`, empty strings, numbers, raw HTML, styled strings).
  - Feeds text to `_HTMLTextExtractor`.
  - Unescapes all HTML entities.
  - Strips any residual CSS property declarations or inline style fragments (e.g., `display:`, `background-color:`, `color:`, `border:`, `padding:`, `border-radius:`, `rgba(...)`).
  - Removes any remaining broken markup brackets.
  - Normalizes whitespace while preserving emojis (`⚠️`, `🌦️`, `📡`, `🔍`) and natural-language text.

- **`sanitize_evidence_list(evidence_list: Optional[List[Any]]) -> List[str]`**:
  - Sequentially and independently processes each evidence item through `sanitize_evidence_text`.
  - Filters out empty or null items.

---

## 3. Rendering Changes

1. **`humanize_evidence_code(code: Any) -> str`**:
   - Routes all trigger codes and strings through `sanitize_evidence_text`.
   - Checks dictionary lookup (`EVIDENCE_CODE_DESCRIPTIONS`) for standard codes.
   - For already sanitized natural-language strings, preserves the clean text directly without re-escaping or markup corruption.

2. **`render_evidence_chips(evidence_codes: Optional[List[Any]])`**:
   - Sanitizes the entire list via `sanitize_evidence_list`.
   - Formats clean plain-text bullets (`• ⚠️ Pressure reading remained unchanged (flatline)`).
   - Prevents duplicate leading emojis if already present in the sanitized string.
   - Uses native Streamlit markdown with zero raw HTML tags or styles.

3. **`render_reasoning_box` & `render_hypothesis_attribution`**:
   - Ensures reasoning summary text is sanitized with `sanitize_evidence_text` before rendering.

---

## 4. Evidence Paths Covered

All evidence rendering paths in the application now route through the central sanitizer:

1. **Station Overview (`dashboard/views/overview.py`)**:
   - Real backend evidence codes and reasoning summaries rendered via `render_evidence_chips()` and `render_reasoning_box()`.
2. **Anomaly Monitor (`dashboard/views/anomaly_monitor.py`)**:
   - Operator review queue cards and decision timeline evidence rendered via `render_evidence_chips()`.
3. **Scenario Testbed (`dashboard/views/scenario_runner.py`)**:
   - Peak anomaly cards and single-observation manual injection evidence rendered via `render_evidence_chips()`.
4. **Sensor Health (`dashboard/views/sensor_health.py`)**:
   - Diagnostic evidence per channel rendered via `render_evidence_chips()`.

---

## 5. Tests Added

A dedicated unit test suite was created in `tests/unit/test_evidence_sanitization.py` covering all 10 required test scenarios:

- **TEST 1 — Plain Text**: Unstyled text preserved intact.
- **TEST 2 — Nested Span**: Unpacks `<span><span>⚠️</span><span>Pressure reading remained unchanged (flatline)</span></span>` to `⚠️ Pressure reading remained unchanged (flatline)`.
- **TEST 3 — Styled Span**: Strips `<span style='display:inline-flex; color:#f87171; border:1px solid red;'>⚠️ Rapid temperature increase detected</span>` to `⚠️ Rapid temperature increase detected`.
- **TEST 4 — Multiple HTML Blocks**: Strips multiple adjacent HTML blocks into clean single-line text.
- **TEST 5 — HTML Entities**: Decodes `&gt;` and `&amp;` into `>` and `&`.
- **TEST 6 — CSS Fragments Outside Tags**: Removes loose CSS properties while preserving natural message text.
- **TEST 7 — None Input**: Returns `""` safely without throwing an exception.
- **TEST 8 — Empty String**: Returns `""` safely.
- **TEST 9 — Multiple Evidence Items**: Sanitizes mixed lists containing clean, styled, and empty items.
- **TEST 10 — Emoji Preservation**: Preserves emojis (`⚠️`, `🌦️`, `📡`, `🔍`) across HTML boundaries.
- **Complex Full Markup Example**: Tests complex multi-property styled HTML block.
- **Non-String Types**: Safely handles numeric and non-string inputs.
- **`humanize_evidence_code` Integration**: Verifies end-to-end translation and sanitization.

---

## 6. Test Results

```bash
python -m pytest -v tests/unit/test_evidence_sanitization.py
```
**Result: 13 passed in 1.23s (100% pass)**

---

## 7. Full Regression Result

```bash
python -m pytest -v
```
- **Previous Test Baseline:** 145 passed
- **New Tests Added:** 13 passed
- **Total Test Suite:** 158 passed
- **Failures / Errors:** 0
- **Regression Status:** Clean (0 regressions)

---

## 8. Browser Validation

- **Backend API:** `http://127.0.0.1:8000/health` (`200 OK`, WAL mode connected, 482 active stations)
- **Streamlit Dashboard:** `http://localhost:8501/_stcore/health` (`200 OK`)
- **Visual Checks:**
  1. Flatline / unchanged reading: Renders `• ⚠️ Pressure reading remained unchanged (flatline)`
  2. Rapid temperature increase: Renders `• ⚠️ Rapid temperature increase detected...`
  3. Abnormal pressure: Renders `• ⚠️ Sudden barometric pressure surge...`
  4. Normal observation: Renders `*No abnormal evidence triggers recorded.*`
  5. Multiple evidence items: Each item renders as an independent, clean bullet without raw HTML.
  6. Zero HTML tags (`<span>`, `<div>`), zero CSS properties (`display:`, `color:`, `border:`, `background-color:`), and zero raw code strings visible in the Evidence section across all views.

---

## 9. Remaining Issues

- **None.** Central sanitization and safe plain-text rendering are fully operational and verified across all views.
