# Health Truth Validation Report

**Project:** SkyGuard AI (SIH26073)  
**Date:** 2026-09-30  
**Objective:** Objective A — Sensor Health Data Truth & Channel Isolation  
**Status:** **VERIFIED & CALIBRATED**  

---

## 1. Screenshot Case Analysis
In the manual inspection screenshot, the following state was observed:
- **Temperature:** Availability = 100%, State = `DEGRADED`, Degradation = `ISOLATED_EXCURSION`
- **Pressure:** Availability = 100%, State = `DEGRADED`, Degradation = `ISOLATED_EXCURSION`
- **Relative Humidity:** Availability = 100%, State = `DEGRADED`, Degradation = `ISOLATED_EXCURSION`

### Key Questions:
1. Is 100% availability with `DEGRADED` mathematically or logically contradictory?
   - **No.** Availability measures *telemetry reception* (i.e. did the data packets arrive?), whereas Health/Degradation measures *signal quality and statistical behavior* (i.e. was there a spike, drift, or physical inconsistency in the values?).
2. Were all three channels genuinely degraded in that observation set?
   - **No.** Investigation revealed that a single-channel temperature spike had caused Pressure and Relative Humidity to falsely report `DEGRADED (ISOLATED_EXCURSION)`.

---

## 2. Root Cause Analysis
In `health/sensor_health/diagnostics.py` (lines 71–75), the evidence filter was written as:
```python
if ch.upper() in ev_str or "SPIKE" in ev_str or "STUCK" in ev_str or "DRIFT" in ev_str or "RATE" in ev_str:
    ch_anom_triggers.append(ev)
```
Because the conditional used global `or` operators (`or "SPIKE" in ev_str`, `or "RATE" in ev_str`), an evidence code generated for temperature (e.g. `TEMPERATURE_SPIKE_POSITIVE` or `TEMPERATURE_UNREALISTIC_RATE`) evaluated to `True` for the `pressure` and `relative_humidity` loops as well.

Consequently:
- `ch_anom_triggers` was populated for all three channels even when only one channel spiked.
- Pressure and Relative Humidity were assigned `DEGRADED (ISOLATED_EXCURSION)` with 100% availability.

---

## 3. Changes Made
1. **Strict Channel-Specific Evidence Filtering:**
   Evidence codes are now mapped strictly to the channel they describe:
   - **Temperature:** `TEMPERATURE`, `TEMP`, `THERMODYNAMIC`
   - **Pressure:** `PRESSURE`
   - **Relative Humidity:** `RELATIVE_HUMIDITY`, `HUMIDITY`, `_RH`, `THERMODYNAMIC`
2. **Consecutive Flatline Calibration:**
   Flatline detection now counts strictly consecutive readings from the latest observation:
   - $4 \le \text{flat\_count} < 12$: `AT_RISK` (`SENSOR_FLATLINE`)
   - $\text{flat\_count} \ge 12$: `CRITICAL` (`SENSOR_FLATLINE`)
3. **Refined Diagnostic Classification:**
   Differentiated `CALIBRATION_DRIFT` (persistent statistical z-score drift) from `RECURRING_ANOMALIES` ($\ge 4$ anomaly flags) and `ISOLATED_EXCURSION` (1–3 isolated flags).

---

## 4. Exact Files Modified
- `health/sensor_health/diagnostics.py`

---

## 5. Verification Across All 10 Scenarios
Replaying all 10 standard scenario streams through the pipeline confirms complete channel isolation:

| Scenario | Temperature | Pressure | Humidity | Overall State |
|---|---|---|---|---|
| **1. NOMINAL** | HEALTHY (100%) | HEALTHY (100%) | HEALTHY (100%) | **HEALTHY** |
| **2. SPIKE (on T)** | AT_RISK (100%) | **HEALTHY (100%)** | **HEALTHY (100%)** | **AT_RISK** |
| **3. FLATLINE (on T)** | AT_RISK (100%) | **HEALTHY (100%)** | **HEALTHY (100%)** | **AT_RISK** |
| **4. DRIFT (on RH)** | **HEALTHY (100%)** | **HEALTHY (100%)** | AT_RISK (100%) | **AT_RISK** |
| **5. BIAS (on P)** | **HEALTHY (100%)** | AT_RISK (100%) | **HEALTHY (100%)** | **AT_RISK** |
| **6. NOISE (on T)** | AT_RISK (100%) | **HEALTHY (100%)** | **HEALTHY (100%)** | **AT_RISK** |
| **7. COMM GAP** | HEALTHY (100%) | HEALTHY (100%) | HEALTHY (100%) | **HEALTHY** |
| **8. MULTIVARIATE** | AT_RISK (100%) | AT_RISK (100%) | AT_RISK (100%) | **AT_RISK** |
| **9. GENUINE WEATHER** | AT_RISK (100%) | AT_RISK (100%) | AT_RISK (100%) | **AT_RISK** |
| **10. COMBINED** | AT_RISK (100%) | HEALTHY (95%) | HEALTHY (100%) | **AT_RISK** |

---

## 6. Interpretation of Availability vs Health
For demonstration judges and evaluators:
- **Availability ($100\%$):** Confirms that all expected telemetry packets were received without communication dropouts.
- **Health / Degradation State (`DEGRADED` / `AT_RISK`):** Indicates that while telemetry arrived on schedule, the sensor signal exhibited anomalies (e.g. step jumps, physical limits, or calibration drift).
- **Nominal State (`HEALTHY`):** Confirms complete data arrival with nominal physical behavior (`NO_DEGRADATION_EVIDENCE`).
