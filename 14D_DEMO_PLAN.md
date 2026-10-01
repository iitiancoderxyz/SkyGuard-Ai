# Demo Objectives

The primary objective of this demonstration plan is to provide a rigorous, end-to-end, reproducible execution framework for evaluating the SIH26073 Automated Weather Station (AWS) Anomaly Detection and Health Monitoring System during the final Smart India Hackathon jury review.

The demonstration is structured to prove four core system capabilities:
1. **Precision Anomaly Discrimination:** Proving the system can distinguish between physical meteorological phenomena (extreme weather events) and technical hardware faults (sensor spikes, drift, frozen state, packet drops).
2. **Multivariate & Spatial Context Awareness:** Demonstrating real-time spatial cross-validation across neighboring stations and thermodynamic consistency checks across co-located sensors.
3. **Automated Health Quantification & Maintenance Workflow:** Showing how raw diagnostic telemetry feeds automated Health Index calculation, Remaining Useful Life (RUL) estimation, and work order generation.
4. **Data Integrity & Stream Correction:** Illustrating real-time data cleansing, automated imputation, and downstream data flag tagging without data loss.

---

# Scenario 1: Normal AWS Operation

### Initial State
* **Station ID:** `AWS-DEL-001` (Indira Gandhi International, Delhi)
* **Status:** Operational (Healthy)
* **Sensor Health Index (SHI):** 100% across all sensors (Temperature, Relative Humidity, Pressure, Wind Speed, Solar Radiation, Rain Gauge).
* **Pipeline Latency:** $< 200\text{ ms}$.
* **Active Stream:** Real-time ingestion enabled (1-minute intervals).

### Input
* Standard telemetry payload matching seasonal diurnal cycle (Temperature: $28.5^\circ\text{C} \rightarrow 29.1^\circ\text{C}$, RH: $62\% \rightarrow 60\%$, Pressure: $1011.2\text{ hPa}$, Wind: $3.2\text{ m/s}$, Solar: $650\text{ W/m}^2$).

### Simulator/Fault-Injection Control
* **Command:** `simulator_cli inject --station AWS-DEL-001 --profile NOMINAL --noise 0.02`

### Expected Detection
* **Status:** `NOMINAL`
* **Flags:** None (`0x0000`)

### Expected Anomaly Score
* $0.02 - 0.08$ (Nominal statistical baseline fluctuation)

### Expected Severity
* `NONE` (Green)

### Expected Confidence
* $99.8\%$ (High confidence in normal state)

### Expected Root Cause
* `N/A - Standard Atmospheric Telemetry`

### Expected Explanation
* "Telemetry vectors conform to physical diurnal envelope, local spatial correlation matrices ($r > 0.94$), and historical temporal ARIMA predictions."

### Expected Sensor-Health Effect
* Zero degradation. Health index maintained at $100.0\%$. RUL unchanged ($> 365\text{ days}$).

### Expected Dashboard Behavior
* Green station indicator on spatial map.
* Live line charts showing smooth, continuous sensor traces within shaded 2-sigma prediction bands.
* Event Log table empty / no active alerts.

### Reset Procedure
* None required (Baseline state).

### What the Presenter Should Demonstrate
1. Highlight real-time streaming architecture ingestion metrics on the System Overview panel.
2. Hover over station `AWS-DEL-001` to display healthy telemetry streams and confidence scores.
3. Show clean sensor status badges (all green).

### What the Scenario Proves
* Establishes the baseline operational fidelity of the ingestion pipeline and verifies zero false-positive generation under normal environmental noise.

---

# Scenario 2: Genuine Weather Event

### Initial State
* **Station Network:** `AWS-DEL-001`, `AWS-DEL-002`, `AWS-DEL-003` (Delhi Regional Cluster)
* **Status:** Operational
* **Initial Weather:** Mild conditions ($30^\circ\text{C}$, $1010\text{ hPa}$, Wind $2\text{ m/s}$).

### Input
* Convective thunderstorm passage across regional cluster over a 15-minute window:
  * Temperature drops abruptly by $8.5^\circ\text{C}$ ($30.0^\circ\text{C} \rightarrow 21.5^\circ\text{C}$).
  * Relative Humidity surges from $55\%$ to $95\%$.
  * Atmospheric Pressure drops by $4.2\text{ hPa}$ in 5 minutes before sharp recovery.
  * Wind Speed spikes from $2\text{ m/s}$ to $22.4\text{ m/s}$ (gusts $28\text{ m/s}$).
  * Rain accumulator triggers rapid tip increment ($35\text{ mm/hr}$).

### Simulator/Fault-Injection Control
* **Command:** `simulator_cli inject-event --cluster AWS-DEL-CLUSTER --event CONVECTIVE_STORM --front-velocity 45kmh --direction NW`

### Expected Detection
* **Status:** `WEATHER_EVENT_DETECTED` (Spatial-Temporal Validation Passed)

### Expected Anomaly Score
* Pointwise anomaly score spikes to $0.72$ (due to steep rate-of-change), but spatial-cross check suppresses fault classification.

### Expected Severity
* `INFO` / `METEOROLOGICAL_ALERT` (Amber highlight, not a hardware alert)

### Expected Confidence
* $96.4\%$ (Event validated by spatial neighbor correlation)

### Expected Root Cause
* `MET_EVENT_CONVECTIVE_FRONT`

### Expected Explanation
* "Rapid drop in temperature ($-8.5^\circ\text{C}/10\text{ min}$) accompanied by pressure surge and precipitation. Verified across neighboring stations `AWS-DEL-002` ($t+2\text{ min}$) and `AWS-DEL-003` ($t+5\text{ min}$). Physical consistency maintained."

### Expected Sensor-Health Effect
* No negative health degradation impact. All sensors remain at $100\%$ operational status.

### Expected Dashboard Behavior
* Map renders a dynamic meteorological event contour across the cluster.
* Event stream displays an informative banner: `METEOROLOGICAL EVENT IN PROGRESS`.
* Sensor graphs highlight steep gradient with blue background overlay (Weather Event Mode).

### Reset Procedure
* **Command:** `simulator_cli reset --cluster AWS-DEL-CLUSTER`

### What the Presenter Should Demonstrate
1. Point to the synchronized gradient across temperature, pressure, wind, and rain graphs.
2. Open Spatial Validation Panel showing `AWS-DEL-002` experiencing the identical shock vector with a 2-minute propagation lag.
3. Show how ML model rejects sensor fault hypothesis due to spatial cross-validation.

### What the Scenario Proves
* The platform avoids false-positive hardware alerts during extreme physical weather events using spatial-temporal neighborhood validation.

---

# Scenario 3: Sensor Spike

### Initial State
* **Station ID:** `AWS-DEL-001`
* **Sensor:** Air Temperature Sensor (`TEMP_01`)
* **Base Value:** $25.2^\circ\text{C}$

### Input
* Single-frame telemetry packet containing an instantaneous physically impossible spike to $88.5^\circ\text{C}$, followed immediately by a return to $25.3^\circ\text{C}$.

### Simulator/Fault-Injection Control
* **Command:** `simulator_cli inject-fault --station AWS-DEL-001 --sensor TEMP_01 --type SPIKE --value 88.5 --duration 1`

### Expected Detection
* **Status:** `ANOMALY_DETECTED`
* **Flag:** `INVALID_SPIKE_OUTLIER` (`0x0001`)

### Expected Anomaly Score
* $0.99$

### Expected Severity
* `HIGH` (Red)

### Expected Confidence
* $98.9\%$

### Expected Root Cause
* `TRANSIENT_ELECTRICAL_IMPULSE_OR_ADC_GLITCH`

### Expected Explanation
* "Single observation delta ($\Delta T = +63.3^\circ\text{C}/\text{min}$) exceeds maximum physical rate-of-change threshold ($5.0^\circ\text{C}/\text{min}$) and Z-score threshold ($Z = 12.4$). Co-located sensors and adjacent stations show no correlation."

### Expected Sensor-Health Effect
* Minor transient health strike on `TEMP_01` ($100\% \rightarrow 97\%$). Auto-recovers after 10 clean frames.

### Expected Dashboard Behavior
* Spike is highlighted with a prominent red marker dot on the live graph.
* Alert notification pop-up appears in top right corner.
* Imputed value (dotted blue line) seamlessly bridges the spike in the cleansed stream view.

### Reset Procedure
* Auto-clears on next valid frame; manual flush via `simulator_cli clear --station AWS-DEL-001`.

### What the Presenter Should Demonstrate
1. Trigger the single-frame spike live from the simulator panel.
2. Direct attention to the instantaneous red flag on the raw stream view.
3. Switch toggle to "Cleansed Stream" showing the inline interpolated value ($25.25^\circ\text{C}$) replacing the spike.

### What the Scenario Proves
* Robust single-frame impulse detection and instantaneous real-time filtering without service interruption.

---

# Scenario 4: Frozen Sensor

### Initial State
* **Station ID:** `AWS-BOM-002` (Mumbai Coastal)
* **Sensor:** Barometric Pressure Sensor (`PRESS_01`)
* **Base Value:** $1012.4\text{ hPa}$

### Input
* Telemetry stream emits identical floating point value $1012.4000\text{ hPa}$ continuously for 45 consecutive reporting intervals (45 minutes) despite active ambient micro-variations in temperature and wind.

### Simulator/Fault-Injection Control
* **Command:** `simulator_cli inject-fault --station AWS-BOM-002 --sensor PRESS_01 --type FROZEN --value 1012.4 --duration 45`

### Expected Detection
* **Status:** `ANOMALY_DETECTED`
* **Flag:** `SENSOR_STUCK_FLATLINE` (`0x0002`)

### Expected Anomaly Score
* $0.91$ (Triggers after threshold of $N=15$ zero-variance frames)

### Expected Severity
* `HIGH`

### Expected Confidence
* $97.2\%$

### Expected Root Cause
* `ADC_BUS_FREEZE_OR_I2C_STUCK_REGISTER`

### Expected Explanation
* "Zero variance detected over 45 consecutive observations ($\sigma^2 = 0.0000$). Expected atmospheric micro-fluctuation ($\sigma^2 \ge 0.08$) absent. Co-located station `AWS-BOM-001` exhibits active pressure tides ($\pm 0.6\text{ hPa}$)."

### Expected Sensor-Health Effect
* `PRESS_01` Sensor Health Score drops from $100\%$ to $45\%$. Sensor state marked as `DEGRADED_FROZEN`.

### Expected Dashboard Behavior
* Flatlined pressure line turns solid purple with a "FROZEN" badge.
* Health status table highlights `PRESS_01` in orange/red.
* Auto-generated diagnostic alert placed in maintenance queue.

### Reset Procedure
* **Command:** `simulator_cli inject-fault --station AWS-BOM-002 --sensor PRESS_01 --type CLEAR`

### What the Presenter Should Demonstrate
1. Point to the flatline on the Pressure graph versus active variation on neighboring streams.
2. Open the Variance Inspection Tool to show $\text{Var}(P) = 0.00$ trigger logic.
3. Show the resulting Health Index reduction on the sensor status card.

### What the Scenario Proves
* Ability to detect subtle frozen-value hardware faults where sensor readings stay within valid physical bounds but lack natural variance.

---

# Scenario 5: Gradual Drift / Degradation

### Initial State
* **Station ID:** `AWS-HYD-004` (Hyderabad North)
* **Sensor:** Relative Humidity Sensor (`RH_01`)
* **Base Value:** $65.0\%$

### Input
* Slow downward linear bias drift introduced at a rate of $-0.5\%$ per hour over a simulated 24-hour window, accumulating a $-12.0\%$ uncalibrated offset relative to ground truth and spatial neighbors.

### Simulator/Fault-Injection Control
* **Command:** `simulator_cli inject-drift --station AWS-HYD-004 --sensor RH_01 --rate -0.5 --duration 24h --accelerate 100x`

### Expected Detection
* **Status:** `ANOMALY_DETECTED`
* **Flag:** `GRADUAL_SENSOR_DRIFT` (`0x0004`)

### Expected Anomaly Score
* $0.84$ (Crosses threshold after $6\text{ hours}$ cumulative drift)

### Expected Severity
* `MEDIUM` $\rightarrow$ `HIGH` (Escalates as drift exceeds $10\%$)

### Expected Confidence
* $92.5\%$

### Expected Root Cause
* `HYGROSCOPIC_ELEMENT_CONTAMINATION_OR_CALIBRATION_DRIFT`

### Expected Explanation
* "Cumulative negative bias detected via Kalman Filter residual analysis. Deviation from spatial Kriging estimate exceeds $3.8\sigma$. Sensor drift rate estimated at $-0.51\%/\text{hr}$."

### Expected Sensor-Health Effect
* `RH_01` Sensor Health Index degrades progressively from $100\% \rightarrow 78\% \rightarrow 32\%$. RUL drops from $180\text{ days}$ to $14\text{ days}$.

### Expected Dashboard Behavior
* Live graph overlays the raw stream (drifting down) against the Spatial Ensemble Reconstruction stream (true ambient RH).
* Cumulative Drift Offset metric displayed in detail drawer (e.g., "Current Bias: $-11.8\%$").
* Trendline icon displays downward slope warning.

### Reset Procedure
* **Command:** `simulator_cli recalibrate --station AWS-HYD-004 --sensor RH_01`

### What the Presenter Should Demonstrate
1. Fast-forward drift simulation using acceleration control.
2. Show the widening gap between the raw sensor reading and the Spatial Kriging reference curve.
3. Display the estimated calibration offset calculated by the backend.

### What the Scenario Proves
* Capability to detect insidious, slow-moving sensor calibration loss before it invalidates long-term climate datasets.

---

# Scenario 6: Communication Failure

### Initial State
* **Station ID:** `AWS-BLR-003` (Bengaluru Rural)
* **Status:** Ingesting 1-minute telemetry smoothly.

### Input
* Complete network connectivity collapse at time $t_0$. Zero packets received for 15 minutes. At $t_0 + 15\text{ min}$, network restores and station flushes a burst backfill buffer of 15 missed records.

### Simulator/Fault-Injection Control
* **Command:** `simulator_cli network-outage --station AWS-BLR-003 --duration 15m --backfill true`

### Expected Detection
* **During Outage:** `COMMUNICATION_LOSS` (`0x0008`)
* **Upon Recovery:** `BACKFILL_PROCESSING` $\rightarrow$ `NOMINAL`

### Expected Anomaly Score
* **During Outage:** $1.00$ (Telemetry Timeout)
* **Upon Recovery:** $0.05$ (Valid backfilled data validated)

### Expected Severity
* `HIGH` (During outage) $\rightarrow$ `INFO` (During backfill ingestion)

### Expected Confidence
* $99.9\%$

### Expected Root Cause
* `CELLULAR_MODEM_DISCONNECT_OR_TOWER_OUTAGE`

### Expected Explanation
* **Outage:** "No telemetry frames received within threshold window ($t_{last} > 300\text{s}$)."
* **Recovery:** "Received 15 backfilled records with historical timestamps. Out-of-order pipeline re-sorting and validation completed successfully."

### Expected Sensor-Health Effect
* Modest decrease in Gateway/Comm Module health score ($100\% \rightarrow 80\%$), individual sensors remain physically unaffected ($100\%$).

### Expected Dashboard Behavior
* Station icon on map turns Grey/Offline with blinking border.
* "DATA GAP IN PROGRESS" card displays real-time timer ($15\text{m }00\text{s}$).
* Upon backfill, gap auto-fills on graphs, offline status clears, and backfill ingestion badge appears briefly.

### Reset Procedure
* Automated upon connection restoration.

### What the Presenter Should Demonstrate
1. Cut network link using simulator; watch station transition to Offline state on UI.
2. Highlight missing data window handling on chart.
3. Restore connection; demonstrate instant historical backfill, out-of-order re-indexing, and automated pipeline catch-up.

### What the Scenario Proves
* Resiliency of the pipeline against real-world transmission blackouts, supporting out-of-order timestamp processing and edge buffering.

---

# Scenario 7: Multivariate Inconsistency

### Initial State
* **Station ID:** `AWS-MAA-001` (Chennai Coastal)
* **Sensors:** Solar Radiation (`SOLAR_01`), Relative Humidity (`RH_01`), Rain Gauge (`RAIN_01`).

### Input
* Direct physical law violation injected: Solar Radiation reports $1150\text{ W/m}^2$ (clear sky peak intensity) while Relative Humidity simultaneously reports $99\%$ and Rain Gauge reports $45\text{ mm/hr}$ heavy precipitation.

### Simulator/Fault-Injection Control
* **Command:** `simulator_cli inject-multivariate-fault --station AWS-MAA-001 --payload '{"SOLAR_01": 1150, "RH_01": 99, "RAIN_01": 45}'`

### Expected Detection
* **Status:** `ANOMALY_DETECTED`
* **Flag:** `PHYSICAL_CROSS_VARIABLE_VIOLATION` (`0x0010`)

### Expected Anomaly Score
* $0.96$

### Expected Severity
* `HIGH`

### Expected Confidence
* $98.5\%$

### Expected Root Cause
* `SOLARIMETER_OPTICAL_OR_TRANSDUCER_FAILURE`

### Expected Explanation
* "Thermodynamic inconsistency detected: High solar irradiance ($1150\text{ W/m}^2$) is physically incompatible with $99\%$ RH and active heavy rainfall ($45\text{ mm/hr}$). Autoencoder reconstruction error on `SOLAR_01` exceeds limit ($R_e = 8.42$)."

### Expected Sensor-Health Effect
* `SOLAR_01` health drops to $20\%$ (`CRITICAL_FAULT`). `RH_01` and `RAIN_01` remain unaffected ($100\%$).

### Expected Dashboard Behavior
* Cross-variable correlation matrix widget highlights red cell at `SOLAR` vs `RAIN`.
* Explanation drawer lists the violated atmospheric physical rule: $\text{Solar} \propto 1 / \text{CloudCover} \propto 1 / \text{Rainfall}$.

### Reset Procedure
* **Command:** `simulator_cli reset --station AWS-MAA-001`

### What the Presenter Should Demonstrate
1. Show the conflicting parameter graphs (blazing sunshine vs torrential rain).
2. Open the Autoencoder Residual Matrix view showing how multivariate models flag sensor pairs that violate learned physical constraints.

### What the Scenario Proves
* Deep multivariate physics-informed machine learning capabilities beyond simple single-variable min/max threshold checks.

---

# Scenario 8: High-Confidence Anomaly

### Initial State
* **Station ID:** `AWS-KOL-001` (Kolkata Port)
* **Status:** Operational

### Input
* Simultaneous catastrophic failure: Internal sensor bus corruption causing Temperature ($120^\circ\text{C}$), Pressure ($400\text{ hPa}$), and Humidity ($-25\%$) to deliver corrupt out-of-bounds telemetry with invalid checksums.

### Simulator/Fault-Injection Control
* **Command:** `simulator_cli inject-fault --station AWS-KOL-001 --type BUS_CORRUPTION`

### Expected Detection
* **Status:** `CRITICAL_HARDWARE_FAILURE`
* **Flags:** `OUT_OF_BOUNDS` (`0x0020`), `CHECKSUM_FAIL` (`0x0040`), `MULTIPLE_SENSOR_FAULT` (`0x0080`)

### Expected Anomaly Score
* $1.00$

### Expected Severity
* `CRITICAL` (Dark Red / Flashing)

### Expected Confidence
* $99.99\%$

### Expected Root Cause
* `ANALOG_FRONT_END_OR_MAINBOARD_BUS_COLLAPSE`

### Expected Explanation
* "Catastrophic hardware failure detected across 3 primary channels. Values breach absolute physical bounds ($T > 60^\circ\text{C}, P < 800\text{ hPa}, RH < 0\%$). CRC-16 payload verification failed."

### Expected Sensor-Health Effect
* Station Overall Health Index collapses to $12.0\%$. All attached sensors flagged as `UNSERVICEABLE`.

### Expected Dashboard Behavior
* Emergency Red Banner across UI.
* Audio visual alert indicator on control room view.
* Immediate auto-generation of Priority-1 Dispatch Ticket in Maintenance Console.

### Reset Procedure
* **Command:** `simulator_cli repair --station AWS-KOL-001`

### What the Presenter Should Demonstrate
1. Inject bus failure. Observe immediate system-wide escalation.
2. Open Auto-Generated Work Order drawer to show pre-populated field report detailing bus checksum failure and hardware replacement requirements.

### What the Scenario Proves
* Unambiguous, immediate, high-confidence detection and automated operational response to severe system failure modes.

---

# Scenario 9: Uncertain / Ambiguous Event

### Initial State
* **Station ID:** `AWS-SHL-001` (Shillong Station)
* **Status:** Operational in complex mountainous terrain.

### Input
* Micro-climatic localized mist/fog event causing Temperature to drift down by $1.8^\circ\text{C}$ while RH jumps from $82\%$ to $98\%$ with zero wind speed, but nearest neighbor (`AWS-SHL-002`, $12\text{ km}$ away across ridge) reports no change due to terrain masking.

### Simulator/Fault-Injection Control
* **Command:** `simulator_cli inject-scenario --station AWS-SHL-001 --type TERRAIN_MICROCLIMATE_FOG`

### Expected Detection
* **Status:** `AMBIGUOUS_ANOMALY` / `UNCERTAIN`
* **Flag:** `SPATIAL_UNCERTAINTY_HIGH` (`0x0100`)

### Expected Anomaly Score
* $0.52$ (Sits precisely in the ambiguous decision band $[0.45, 0.65]$)

### Expected Severity
* `LOW` / `NEEDS_REVIEW` (Yellow/Dotted)

### Expected Confidence
* $48.2\%$ (Low statistical confidence to decisively assert hardware failure vs true local weather)

### Expected Root Cause
* `LOCALIZED_MICROCLIMATE_OR_EARLY_STAGE_SENSOR_DRIFT`

### Expected Explanation
* "Local sensor shift violates spatial prediction ($Z = 2.4$), but thermodynamic correlation ($T\downarrow, RH\uparrow$) is physically valid. High spatial variance due to complex terrain elevation differential ($\Delta h = 640\text{ m}$)."

### Expected Sensor-Health Effect
* Health Index unchanged ($100\%$), but placed on "Watchlist" ($12\text{-hour}$ observation buffer).

### Expected Dashboard Behavior
* Station marked with an Ambiguity/Question mark icon.
* System refrains from auto-discarding data; tags data stream with `FLAG_SUSPECT_NEEDS_VERIFICATION`.
* Shows Human-in-the-Loop (HITL) review button: `[Confirm Weather]` or `[Flag Fault]`.

### Reset Procedure
* **Command:** `simulator_cli clear --station AWS-SHL-001`

### What the Presenter Should Demonstrate
1. Point to the $48.2\%$ confidence score in the prediction breakdown.
2. Show how the ML system explicitly communicates uncertainty rather than forcing a wrong binary classification.
3. Demonstrate the Human-in-the-Loop review toggle button.

### What the Scenario Proves
* Explainable AI design: The system quantifies its own prediction uncertainty under complex edge cases, preventing invalid data rejection.

---

# Scenario 10: Sensor-Health Deterioration

### Initial State
* **Station ID:** `AWS-AMD-003` (Ahmedabad South)
* **Sensor:** Anemometer / Wind Speed (`WIND_01`)
* **Health Index:** $100\%$

### Input
* Multi-stage physical bearing degradation sequence over simulated time:
  1. *Stage 1:* Increased starting threshold (low wind speeds report 0).
  2. *Stage 2:* High-frequency mechanical vibration noise added to signal.
  3. *Stage 3:* Intermittent rotor lockup during gusts.

### Simulator/Fault-Injection Control
* **Command:** `simulator_cli run-degradation-sequence --station AWS-AMD-003 --sensor WIND_01 --stages 3 --speed 300x`

### Expected Detection
* **Stage 1:** `HEALTH_WARNING` (Health: $82\%$)
* **Stage 2:** `HEALTH_DEGRADED` (Health: $54\%$)
* **Stage 3:** `HEALTH_CRITICAL` (Health: $18\%$)

### Expected Anomaly Score
* Progressive increase: $0.22 \rightarrow 0.58 \rightarrow 0.92$

### Expected Severity
* `INFO` $\rightarrow$ `MEDIUM` $\rightarrow$ `HIGH`

### Expected Confidence
* $94.1\%$

### Expected Root Cause
* `ANEMOMETER_BEARING_WEAR_MECHANICAL_FRICTION`

### Expected Explanation
* "Spectral analysis indicates mechanical resonance at $14\text{ Hz}$ followed by dead-zone expansion at low wind speeds ($< 1.2\text{ m/s}$). Signal noise factor expanded by $410\%$."

### Expected Sensor-Health Effect
* Health Index trajectory smoothly decays over time. RUL updates dynamically from $120\text{ days} \rightarrow 28\text{ days} \rightarrow 3\text{ days}$.

### Expected Dashboard Behavior
* Sensor Health Trend Sparkline displays downward curve.
* Predictive Maintenance widget flags: `BEARING REPLACEMENT REQUIRED WITHIN 72 HOURS`.

### Reset Procedure
* **Command:** `simulator_cli replace-sensor --station AWS-AMD-003 --sensor WIND_01`

### What the Presenter Should Demonstrate
1. Accelerate degradation timeline.
2. Show the continuous Sensor Health Index (SHI) curve dropping in real time.
3. Open the RUL Estimation Panel to demonstrate predictive maintenance forecasting.

### What the Scenario Proves
* Proactive condition monitoring and Remaining Useful Life (RUL) estimation prior to catastrophic functional failure.

---

# Scenario 11: Maintenance Indication

### Initial State
* Triggered following Scenario 10 or injected manually on `AWS-AMD-003`.
* Sensor `WIND_01` in `HEALTH_CRITICAL` state ($18\%$).

### Input
* System automated cron execution evaluates health indices across all regional AWS assets and triggers the Maintenance Workflow Engine.

### Simulator/Fault-Injection Control
* **Command:** `simulator_cli trigger-maintenance-job`

### Expected Detection
* **Status:** `WORK_ORDER_GENERATED`

### Expected Anomaly Score
* $N/A$ (Administrative / Workflow state)

### Expected Severity
* `ACTION_REQUIRED`

### Expected Confidence
* $100\%$ (Rule-based ticket emission threshold met)

### Expected Root Cause
* `AUTOMATED_PREDICTIVE_MAINTENANCE_TRIGGER`

### Expected Explanation
* "Sensor `WIND_01` on station `AWS-AMD-003` crossed critical health threshold ($< 25\%$). Auto-generating Work Order #WO-2026-8841."

### Expected Sensor-Health Effect
* Status locks in `PENDING_MAINTENANCE` state. Downstream data streams automatically routed to auto-imputation mode.

### Expected Dashboard Behavior
* A new ticket appears on the Maintenance Operations Dashboard.
* Includes:
  * Station ID & Geolocation link.
  * Fault taxonomy: Mechanical Bearing Friction.
  * Required spare parts list: `Anemometer Rotor Assembly Model-B`.
  * Assigned Field Technician route optimization option.

### Reset Procedure
* **Command:** `simulator_cli resolve-ticket --ticket WO-2026-8841`

### What the Presenter Should Demonstrate
1. Navigate to Maintenance Operations Tab.
2. Click on the auto-generated Work Order for `AWS-AMD-003`.
3. Show automated diagnostics summary, recommended spare parts, and "Dispatch Field Crew" button.

### What the Scenario Proves
* Complete end-to-end operational integration from telemetry anomaly detection to field-service actionability.

---

# Scenario 12: Correction Where Appropriate

### Initial State
* **Station ID:** `AWS-DEL-001`
* **Condition:** Active sensor spike (Scenario 3) or frozen sensor segment (Scenario 4).
* **Data Stream:** Raw stream contains corrupted or missing values.

### Input
* Data Pipeline Quality Enforcement module receives invalid data points from degraded sensors.

### Simulator/Fault-Injection Control
* **Command:** `simulator_cli toggle-correction-engine --mode AUTO_CLEAN`

### Expected Detection
* **Status:** `STREAM_CORRECTED`
* **Flags Applied:** `DATA_IMPUTED_SPATIO_TEMPORAL` (`0x0200`), `QC_PASSED_POST_CORRECTION` (`0x0400`)

### Expected Anomaly Score
* Raw: $0.99$, Corrected Stream Anomaly Score: $0.02$

### Expected Severity
* Raw: `HIGH`, Cleansed Layer: `NOMINAL`

### Expected Confidence
* Imputation Confidence: $95.8\%$ (Spatial-Temporal Ensemble Model)

### Expected Root Cause
* `REALTIME_DATA_CLEANSING_AND_IMPUTATION`

### Expected Explanation
* "Raw corrupted payload detected and isolated. Value $88.5^\circ\text{C}$ replaced with interpolated estimate $25.28^\circ\text{C}$ derived from bi-directional LSTM temporal predictor and spatial Kriging matrix."

### Expected Sensor-Health Effect
* Raw sensor flagged for repair; downstream analytics continue running without bad data corruption.

### Expected Dashboard Behavior
* Dual-Trace View on UI:
  * *Red Dotted Line:* Raw corrupted sensor data.
  * *Solid Green Line:* Corrected, cleansed, auto-imputed stream.
* Data export toggle allows downloading "Raw", "Cleansed", or "Combined with QC Flags".

### Reset Procedure
* Toggle off correction engine or clear fault injection.

### What the Presenter Should Demonstrate
1. Toggle the "Show Raw vs Cleansed Stream" button on the UI chart.
2. Point out how downstream climate statistics remain unaffected by spikes/gaps.
3. Inspect the JSON export payload showing full transparency with metadata flags attached.

### What the Scenario Proves
* Automated data stream self-healing capability ensuring continuous high-quality meteorological feed delivery to weather forecasting models.

---

# Scenario 13: Multi-Station Behavior

### Initial State
* **Cluster:** 5 Regional Stations (`AWS-PNQ-001` to `AWS-PNQ-005`, Pune Region).
* **Status:** All stations streaming nominal background weather data.

### Input
* Ingest simultaneous multi-station stream where a regional cold front moves from West to East across all 5 stations over a 30-minute window, while `AWS-PNQ-003` experiences a localized hardware failure (stuck pressure sensor).

### Simulator/Fault-Injection Control
* **Command:** `simulator_cli run-multi-station-demo --cluster AWS-PNQ --weather-front COLD_FRONT --inject-fault-at AWS-PNQ-003`

### Expected Detection
* `AWS-PNQ-001, 002, 004, 005`: `METEOROLOGICAL_FRONT` (Valid, Health $100\%$)
* `AWS-PNQ-003`: `HARDWARE_FAULT_ISOLATED` (FROZEN PRESSURE, Health $42\%$)

### Expected Anomaly Score
* Regional Front Stations: Anomaly score transient $0.35 \rightarrow 0.08$
* Faulty Station `AWS-PNQ-003`: Anomaly score $0.94$

### Expected Severity
* Regional Front: `INFO`
* `AWS-PNQ-003`: `HIGH`

### Expected Confidence
* $97.8\%$ cluster-wide spatial disambiguation.

### Expected Root Cause
* `SPATIAL_CLUSTER_ISOLATION_OF_SINGLE_NODE_FAULT`

### Expected Explanation
* "Cluster cross-correlation confirms propagation of genuine atmospheric front across 4 of 5 nodes. `AWS-PNQ-003` failed to register pressure wave passage, confirming local sensor fault rather than weather divergence."

### Expected Sensor-Health Effect
* `AWS-PNQ-003` pressure sensor health degrades; all other cluster sensors remain pristine.

### Expected Dashboard Behavior
* Regional Map View displays animated temperature color map moving across the region.
* Station `AWS-PNQ-003` flashes red amid the passing blue cold front overlay.
* Spatial Correlation Matrix shows high cross-correlation ($>0.92$) between nodes 1,2,4,5, and near-zero correlation ($0.04$) for node 3.

### Reset Procedure
* **Command:** `simulator_cli reset --cluster AWS-PNQ`

### What the Presenter Should Demonstrate
1. Switch to Regional Multi-Station Map View.
2. Play the timeline animation showing the weather front sweeping across the region.
3. Show how node 3 is visually isolated and flagged as a hardware fault amidst regional weather movement.

### What the Scenario Proves
* Scalable multi-station spatial cross-validation preventing regional meteorological events from confusing network diagnostic tools.

---

# Scenario 14: Evaluation Evidence

### Initial State
* System connected to pre-loaded historical benchmarking datasets (e.g., 100,000 annotated records containing labeled sensor faults and extreme weather events).

### Input
* Presenter triggers execution of automated Evaluation & Benchmark Suite directly from UI control bar.

### Simulator/Fault-Injection Control
* **Command:** `python -m src.evaluation.run_benchmarks --dataset val_sih_2026_ground_truth.parquet`

### Expected Detection
* Execution of complete test suite validating Precision, Recall, F1-Score, False Positive Rate (FPR), and Ingestion Latency against benchmark goals.

### Expected Anomaly Score
* Aggregate benchmark statistical metrics displayed.

### Expected Severity
* `EVALUATION_MODE_ACTIVE`

### Expected Confidence
* Overall Model Validation Accuracy: $> 98.2\%$

### Expected Root Cause
* `AUTOMATED_SYSTEM_PERFORMANCE_VERIFICATION`

### Expected Explanation
* "Validation suite completed across 100,000 ground-truth samples. Zero regression detected. Latency SLA ($<200\text{ms}$) satisfied under $10,000\text{ msg/sec}$ load."

### Expected Sensor-Health Effect
* N/A (Offline Benchmark Execution)

### Expected Dashboard Behavior
* System opens Model Metrics & Benchmarks Dashboard displaying live-rendered plots:
  * Precision-Recall Curve (AUC = 0.986).
  * ROC Curve (AUC = 0.992).
  * Confusion Matrix (True Positives, False Positives, True Negatives, False Negatives).
  * Latency Histogram (p50 = $18\text{ms}$, p99 = $84\text{ms}$).
  * Table comparing baseline model vs SIH26073 ensemble.

### Reset Procedure
* Close Benchmark Modal.

### What the Presenter Should Demonstrate
1. Trigger live benchmark evaluation from UI top navigation bar.
2. Highlight Confusion Matrix showing $<0.5\%$ False Positive Rate on extreme weather events.
3. Point out latency metrics proving enterprise readiness for real-time deployment.

### What the Scenario Proves
* Unbiased, quantitatively verifiable engineering proof of system accuracy, throughput, and performance against pre-established standards.

---

# Required Simulator Controls

To enable seamless live demonstration without manual database manipulation, the simulator control panel (`simulator_cli` and UI Fault Injection Drawer) must expose the following controls:

| Control Parameter | Target Scope | Options / Range | Function |
| :--- | :--- | :--- | :--- |
| **Profile Selector** | Station / Cluster | `NOMINAL`, `CONVECTIVE_STORM`, `COLD_FRONT`, `MONSOON_BURST` | Simulates macro atmospheric physics across one or many stations. |
| **Fault Type Injector** | Individual Sensor | `SPIKE`, `FROZEN`, `DRIFT`, `NOISE_BURST`, `OUT_OF_BOUNDS` | Injects explicit hardware fault modes into sensor stream. |
| **Drift Rate Slider** | Individual Sensor | $-5.0\%$ to $+5.0\%$ per hour | Controls slope of linear offset degradation. |
| **Fault Duration** | Frame Counter | $1$ to $1000$ intervals | Sets duration of injected anomaly before auto-recovery. |
| **Network Outage Toggle** | Station / Gateway | `DISCONNECT`, `CONNECT_AND_BACKFILL` | Simulates loss of cellular telemetry and buffer recovery. |
| **Multi-Fault Combinator** | Station | `BUS_CORRUPTION`, `POWER_FLICKER`, `CROSS_VARIABLE_VIOLATION` | Triggers complex multi-sensor failure scenarios. |
| **Time Acceleration** | System Clock | `1x`, `10x`, `100x`, `300x` | Accelerates long-term drift and degradation timeline for demo efficiency. |

---

# Required Backend Support

To execute all 14 scenarios without failure, the backend infrastructure must provide:

1. **Dual-Stream Processing Pipeline:**
   * Raw Telemetry Ingestion Topic (`aws.telemetry.raw`).
   * Cleansed/Imputed Processing Topic (`aws.telemetry.cleansed`).
2. **Stateful Spatial-Temporal Windowing:**
   * In-memory sliding time window (minimum 60 minutes) in Redis/Flink for rate-of-change and drift computation.
   * Dynamic Spatial Neighbor Lookup Table indexing station latitude, longitude, and elevation.
3. **ML Inference Pipeline:**
   * Parallel execution of Rules Engine, Autoencoder Reconstruction, Isolation Forest, and Spatial Kriging models.
   * Real-time Bayesian Uncertainty Estimator returning numeric confidence scores $[0, 100\%]$.
4. **Health & RUL Engine:**
   * Continuous Sensor Health Index (SHI) updater processing cumulative diagnostic flags.
   * RUL degradation solver based on exponential decay models.
5. **Automated Work Order Engine:**
   * REST endpoint generating structured JSON tickets upon `CRITICAL` or `HEALTH_DEGRADED` triggers.

---

# Required UI Support

The Frontend Interface (`14C_UI_SPEC.md`) must explicitly incorporate the following interactive components:

1. **Live Simulator Drawer (Presenter Toggle Bar):** A hidden/collapsible side panel allowing the presenter to inject faults live with one click.
2. **Raw vs Cleansed Graph Overlay Switcher:** Dual-line rendering mode on telemetry charts showing raw uncorrected data (red/dotted) overlaid with auto-imputed clean streams (green/solid).
3. **Interactive Spatial Map with Weather Layers:** Color-coded station map nodes with spatial weather contour overlays and spatial correlation line connectors.
4. **Explainable AI Diagnostics Modal:** An expandable card on every alert detailing:
   * Feature Attribution Bar Chart (SHAP values).
   * Violated Atmospheric / Physical Rule text string.
   * Neighbor Verification Matrix.
5. **Maintenance & Work Order Tab:** Dedicated operational view displaying auto-generated field tickets, diagnostic logs, and spare part suggestions.
6. **Benchmark & Evaluation Modal:** Live modal displaying Precision/Recall curves, ROC plots, and pipeline execution latencies.

---

# Failure Recovery

During the live SIH evaluation, unpredictable system issues (e.g., browser crashes, network drops, simulator lockups) must be recoverable within **10 seconds** using the following protocols:

### 1. Local Emergency Backend Failover
* If cloud database or live stream stalls, execute local offline mock backend:
  ```bash
  ./scripts/demo_emergency_failover.sh --mode LOCAL_MOCK
  ```
  *This spins up a local pre-cached Redis + FastAPI instance loading identical telemetry streams instantly.*

### 2. UI Hard Reset Keybinding
* Pressing `Ctrl + Shift + R + 0` in the web application executes:
  * In-memory state wipe.
  * Re-initialization of WebSocket connection.
  * Reset of all simulator fault injections back to Scenario 1 (`NOMINAL`).

### 3. Simulator State Flushing
* If injected faults stack up unpredictably:
  ```bash
  simulator_cli hard-reset --all
  ```
  *Instantly purges all active fault queues and resumes standard baseline generator.*

---

# Acceptance Criteria

The demonstration will be deemed **100% successful** if all the following quantifiable criteria are satisfied before the jury:

1. **Detection Accuracy:**
   * $100\%$ of injected spikes, frozen values, and drift faults trigger alerts within $\le 2$ reporting intervals.
   * Zero physical weather events (Scenario 2) classified as hardware failures.
2. **Latency SLA:**
   * End-to-end processing latency from fault injection to UI alert rendering stays under **$200\text{ ms}$**.
3. **Correction & Integrity:**
   * Cleansed data stream successfully replaces invalid points with interpolated values having $< 3\%$ variance from ground truth.
4. **Maintenance Automation:**
   * Work order generation occurs automatically within $< 1\text{ second}$ of sensor health falling below $25\%$.
5. **Explainability & Trust:**
   * Every anomaly alert provides a human-readable text explanation, confidence score, and root-cause breakdown.

---

# Handoff to Antigravity

This document (`14D_DEMO_PLAN.md`) completes the architectural design phase for SIH26073. It is officially handed off to the **Antigravity Execution & Testing Team** for implementation and rehearsal.

### Antigravity Execution Checklist:
- [ ] Configure `simulator_cli` with all parameters and preset scenario hooks specified in Section "Required Simulator Controls".
- [ ] Implement backend event triggers matching the exact flags and fault schema outlined in Scenarios 1–14.
- [ ] Ensure UI components (Raw/Cleansed view, Explainability modal, Maintenance ticket drawer) are wired directly to live WebSocket feeds.
- [ ] Dry-run the complete 14-scenario sequence in sequence, verifying recovery protocols and timing constraints.

*Plan authored by DEMO ARCHITECT for SIH26073.*