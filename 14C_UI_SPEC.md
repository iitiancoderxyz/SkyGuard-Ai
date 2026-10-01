# SIH26073 - Frontend UI/UX Technical Specification
## Operational AWS Quality Control & Monitoring System (`14C_UI_SPEC.md`)

---

## 1. UX Goals

The **SIH26073 AWS Operational Monitoring Dashboard** is engineered to serve meteorological data managers, field engineers, and system operators. It transforms complex machine learning anomaly detection and sensor health telemetry into actionable, high-confidence insights.

### Core Design Principles
1. **Operational Mission-Critical Clarity**: High-contrast, dark-theme-first interface optimized for continuous 24/7 control-room monitoring (IMD/NOAA standard aesthetic).
2. **Sub-Second Anomaly Awareness**: Zero latency between backend ML execution and visual alert propagation across the network map and notification ticker.
3. **Explainable AI (XAI) First**: Anomaly flags are accompanied by natural-language explanations and SHAP feature attribution metrics so operators understand *why* a data point was flagged.
4. **Dual-Telemetry Integrity**: Direct overlay of raw telemetry against ML-corrected/imputed telemetry across all scientific parameters (Temperature, Atmospheric Pressure, Relative Humidity, Wind Vector, Precipitation, Solar Radiation).
5. **Interactive Fault & Genuine Weather Simulation**: Integrated sandbox allowing operators to inject synthetic sensor faults or simulate genuine extreme meteorological events (e.g., Cyclonic Depression, Squall) to test system resilience and model fidelity.

---

## 2. Global Layout

### Layout Architecture
The interface follows a persistent responsive shell:

```
+----------------------------------------------------------------------------------------------------+
| TOPBAR: System Status | Network Selector | Search Bar | Emergency Ticker | Theme | User Profile  |
+---------------------+------------------------------------------------------------------------------+
| SIDEBAR (Fixed/     | MAIN CONTENT VIEWPORT (Fluid CSS Grid / 12 Columns)                         |
| Collapsible)        |                                                                              |
|                     | [ Breadcrumb Navigation / Active Filter Bar ]                                 |
| - Network Overview  | +--------------------------------------------------------------------------+ |
| - Station Inspector | |                                                                          | |
| - Anomaly Center    | | View-Specific Components (Grid / Map / Charts / Tables)                   | |
| - Sensor Health     | |                                                                          | |
| - Maintenance       | |                                                                          | |
| - Demo / Simulation | +--------------------------------------------------------------------------+ |
+---------------------+------------------------------------------------------------------------------+
| FOOTER / TICKER: SSE Live Link Status | Ingestion Rate (msg/s) | Active Anomalies: 4 | UTC 14:32:05 |
+----------------------------------------------------------------------------------------------------+
```

### Visual Theme & Tokens
* **Base Palette (Dark Mode - Default)**:
  * Background Deep: `#0F172A` (Slate 900)
  * Surface Card: `#1E293B` (Slate 800)
  * Surface Border: `#334155` (Slate 700)
  * Primary Text: `#F8FAFC` (Slate 50)
  * Secondary Text: `#94A3B8` (Slate 400)
* **Status & Alert Colors**:
  * **Normal / Nominal**: `#10B981` (Emerald 500)
  * **Low / Info**: `#3B82F6` (Blue 500)
  * **Medium Severity Anomaly**: `#F59E0B` (Amber 500)
  * **High Severity Anomaly**: `#EF4444` (Red 500)
  * **Critical / Stuck / Hardware Fault**: `#8B5CF6` (Purple 500)
  * **Offline / Stale**: `#64748B` (Slate 500)
* **Scientific Parameter Accent Tokens**:
  * Temperature ($T$): `#F97316` (Orange)
  * Pressure ($P$): `#06B6D4` (Cyan)
  * Relative Humidity ($RH$): `#3B82F6` (Blue)
  * Wind Speed/Dir ($WS/WD$): `#10B981` (Emerald)
  * Precipitation ($RR$): `#6366F1` (Indigo)

---

## 3. Navigation

### Primary Navigation Items
1. **Network Dashboard (`/network`)**: Spatial map view and aggregate status of all AWS nodes.
2. **Station Inspector (`/station/:station_id`)**: Single-station deep dive with high-frequency telemetry, live gauges, and sensor-level health metrics.
3. **Anomaly Center (`/anomalies`)**: Operational triage list of all real-time and historical data anomalies with XAI diagnostic inspector.
4. **Sensor Health (`/health`)**: Degradation tracking, calibration drift analysis, and sensor stuck state analysis.
5. **Maintenance & Work Orders (`/maintenance`)**: Ticket dispatching, repair logs, and technician feedback loop for ML active learning.
6. **Simulation / Demo Lab (`/simulation`)**: Interactive fault injection and extreme weather scenario testing harness.

---

## 4. Network Dashboard

### Layout Strategy
3-column asymmetrical grid (25% Summary Sidebar | 50% Geospatial Map | 25% Alert Ticker & Health Distribution).

```
+---------------------------------------------------------------------------------------------------+
| Network Overview Header (Global KPI Metrics)                                                     |
+----------------------------+---------------------------------------+------------------------------+
| Regional Filter & Search   | Interactive Geospatial Map            | Realtime Anomaly Feed        |
| - Total Stations: 128      | (Leaflet/Mapbox vector layer)         | (Virtually Scrolled List)    |
| - Online: 122 | Degraded:4 | Color-coded station status markers   | [CRITICAL] AWS-104 Temp      |
| - Offline: 2               | Dynamic spatial interpolation overlays| [MEDIUM] AWS-088 Pressure    |
+----------------------------+---------------------------------------+------------------------------+
```

### Major Components

#### Component: `NETWORK_SUMMARY_CARDS`
* **NAME**: `NETWORK_SUMMARY_CARDS`
* **PURPOSE**: Display high-level counts of active stations, anomalies, and global network health index.
* **DATA SOURCE**: `backend_stats_service`
* **API**: `GET /api/v1/network/summary`
* **DATA DISPLAYED**: Total Active Stations, Online/Offline Ratio, Active Anomalies (Count by Severity), Mean Network Health Score (%).
* **USER INTERACTION**: Clicking an anomaly badge filters the Network Anomaly List to that severity level.
* **UPDATE FREQUENCY**: Every 5 seconds via SSE / Polling fallback.
* **ERROR BEHAVIOR**: Displays skeleton pulse loader on connection lag; turns card border red with retry icon on persistent API error.

#### Component: `GEOSPATIAL_STATION_MAP`
* **NAME**: `GEOSPATIAL_STATION_MAP`
* **PURPOSE**: Interactive spatial representation of all deployed AWS nodes with live status indicators and weather layer overlays.
* **DATA SOURCE**: `station_registry_service`, `live_telemetry_stream`
* **API**: `GET /api/v1/stations/geo`, `SSE /api/v1/stream/network-status`
* **DATA DISPLAYED**: Geographic coordinates (Latitude, Longitude, Altitude), Station Status Indicator (Normal, Degraded, Anomalous, Offline), Hover Tooltip (Station Name, ID, Latest Air Temp, Pressure, Humidity, Active Fault Flags).
* **USER INTERACTION**: Pan, Zoom, Layer toggle (Isobar/Isotherm Heatmap), Click station marker to open Quick Summary Popover or navigate directly to Station Dashboard.
* **UPDATE FREQUENCY**: Real-time push via SSE.
* **ERROR BEHAVIOR**: Falls back to cached offline map tile set; displays "Map Data Unreachable" overlay if geo-endpoint fails.

#### Component: `NETWORK_ANOMALY_FEED`
* **NAME**: `NETWORK_ANOMALY_FEED`
* **PURPOSE**: Live updating operational stream of detected data anomalies across all stations.
* **DATA SOURCE**: `ml_inference_pipeline`
* **API**: `SSE /api/v1/stream/anomalies`
* **DATA DISPLAYED**: Timestamp (UTC), Station ID, Parameter Flagged, Anomaly Type (Spike, Bias Drift, Stuck, Noise), Severity Score, Confidence Score (%).
* **USER INTERACTION**: Click item to open Anomaly Diagnostic Modal or focus map view on target station.
* **UPDATE FREQUENCY**: Real-time event-driven push.
* **ERROR BEHAVIOR**: Displays "Reconnecting to live stream..." banner at top of feed list.

---

## 5. Station Dashboard

### Layout Strategy
Top summary bar with metadata and quick controls, followed by a 2x3 telemetry grid for core sensor parameters.

```
+---------------------------------------------------------------------------------------------------+
| Station Header: AWS-108 (Jaipur East) | Lat: 26.9124 | Lon: 75.7873 | Elev: 431m | Status: DEGRADED |
+---------------------------------------------------------------------------------------------------+
| Live Gauges & Raw vs Corrected Sparklines                                                        |
| +-------------------------+ +-------------------------+ +-------------------------+             |
| | Temperature (Air)       | | Atmospheric Pressure    | | Relative Humidity       |             |
| | Raw: 34.2 C | QC: 31.0 C| | Raw: 1008 hPa | QC: 1008| | Raw: 65% | QC: 65%       |             |
| +-------------------------+ +-------------------------+ +-------------------------+             |
| +-------------------------+ +-------------------------+ +-------------------------+             |
| | Wind Vector (Speed/Dir) | | Rainfall Rate           | | Solar Radiation         |             |
| | Raw: 12 m/s @ 240 deg   | | Raw: 0.0 mm/hr          | | Raw: 820 W/m2          |             |
| +-------------------------+ +-------------------------+ +-------------------------+             |
+---------------------------------------------------------------------------------------------------+
| Time-Series Interactive Multi-Parameter QC Chart (Raw vs ML-Imputed overlay with confidence bands) |
+---------------------------------------------------------------------------------------------------+
```

### Major Components

#### Component: `STATION_HEADER_INFO`
* **NAME**: `STATION_HEADER_INFO`
* **PURPOSE**: Display station location metadata, operational status, ingestion mode, and quick maintenance controls.
* **DATA SOURCE**: `station_metadata_db`
* **API**: `GET /api/v1/stations/{station_id}`
* **DATA DISPLAYED**: WMO ID, Station Name, Coordinates, Altitude, Transmission Frequency (1-min / 10-min), Last Ping Timestamp, Battery Voltage, Solar Panel Output.
* **USER INTERACTION**: Click "Trigger Manual QC Scan" button, "Simulate Fault" button, or "Export Historical CSV" button.
* **UPDATE FREQUENCY**: Static metadata loaded on mount; heartbeat updated every 10 seconds.
* **ERROR BEHAVIOR**: Renders "Station Metadata Unavailable" alert banner if HTTP 404/500 returned.

#### Component: `PARAMETER_TELEMETRY_CARD`
* **NAME**: `PARAMETER_TELEMETRY_CARD`
* **PURPOSE**: Visualized single scientific parameter card displaying current raw telemetry, ML-corrected telemetry, status tag, and 1-hour trend sparkline.
* **DATA SOURCE**: `telemetry_qc_service`
* **API**: `GET /api/v1/stations/{station_id}/telemetry/latest`
* **DATA DISPLAYED**:
  * Parameter Name ($T, P, RH, WS, RR, SR$)
  * Raw Telemetry Value & Unit
  * ML-Corrected Telemetry Value (highlighted in cyan if correction applied)
  * QC Flag Status (PASS, MARGINAL, FAIL)
  * 60-minute sparkline chart showing raw line + corrected line overlay
* **USER INTERACTION**: Click card to highlight parameter on main time-series chart below.
* **UPDATE FREQUENCY**: Updated every incoming packet (e.g., 1 minute or sub-minute streaming).
* **ERROR BEHAVIOR**: Displays `--.-` value with grey dashed sparkline if missing or corrupted data frame received.

---

## 6. Live Data

### Scientific Telemetry Definition
The live observation feed explicitly monitors six core weather parameters:
1. **Air Temperature ($T$)**: Range $-50^\circ\text{C}$ to $+60^\circ\text{C}$, Precision $0.1^\circ\text{C}$
2. **Atmospheric Pressure ($P$)**: Range $500\text{ hPa}$ to $1100\text{ hPa}$, Precision $0.1\text{ hPa}$
3. **Relative Humidity ($RH$)**: Range $0\%$ to $100\%$, Precision $1\%$
4. **Wind Speed & Direction ($WS/WD$)**: Range $0\text{ m/s}$ to $75\text{ m/s}$, $0^\circ$ to $360^\circ$
5. **Rainfall Accumulation & Intensity ($RR$)**: Range $0\text{ mm/hr}$ to $250\text{ mm/hr}$
6. **Solar Radiation ($SR$)**: Range $0\text{ W/m}^2$ to $1500\text{ W/m}^2$

### Major Components

#### Component: `RAW_VS_CORRECTED_STREAM_VIEW`
* **NAME**: `RAW_VS_CORRECTED_STREAM_VIEW`
* **PURPOSE**: Real-time side-by-side stream comparison of incoming raw telemetry bytes against ML imputed values.
* **DATA SOURCE**: `ml_imputation_pipeline`
* **API**: `SSE /api/v1/stream/telemetry/{station_id}`
* **DATA DISPLAYED**:
  * Dual numerical readouts for raw vs corrected
  * Delta ($\Delta = \text{Raw} - \text{Corrected}$)
  * Imputation Confidence Score ($0.0\%$ to $100.0\%$)
  * Flagged anomaly reason tag (e.g., `SPIKE_REJECTED`, `DRIFT_COMPENSATED`)
* **USER INTERACTION**: Toggle switch to view raw values only, corrected values only, or dual overlay.
* **UPDATE FREQUENCY**: Push per packet arrival.
* **ERROR BEHAVIOR**: Highlights stream box in amber if latency exceeds 120 seconds.

---

## 7. Anomaly View

### Anomaly Diagnostic Architecture
The Anomaly View allows operators to filter, analyze, and resolve telemetry anomalies flagged by the ensemble ML pipeline (Isolation Forest, Autoencoder, and Spatial Cross-Validation).

```
+---------------------------------------------------------------------------------------------------+
| ANOMALY CENTER - Operational Triage Dashboard                                                    |
+---------------------------------------------------------------------------------------------------+
| Filters: [ Date Range ] [ Severity: ALL|HIGH|CRIT ] [ Station: ALL ] [ Parameter: ALL ] [ Export ] |
+---------------------------------------------------------------------------------------------------+
| Anomaly Queue Table                                                                              |
| ID      | Timestamp (UTC)     | Station | Parameter | Severity | ML Model | Conf % | Action     |
| AL-9042 | 2026-09-29 10:42:00 | AWS-108 | Temp ($T$)  | CRITICAL | Ensemble | 96.4%  | [ Inspect] |
| AL-9041 | 2026-09-29 10:38:12 | AWS-044 | Press ($P$) | HIGH     | Autoenc  | 89.1%  | [ Inspect] |
+---------------------------------------------------------------------------------------------------+
```

### Major Components

#### Component: `ANOMALY_TRIAGE_TABLE`
* **NAME**: `ANOMALY_TRIAGE_TABLE`
* **PURPOSE**: Tabular list of operational anomalies for quick filtering and batch triage.
* **DATA SOURCE**: `anomaly_db`
* **API**: `GET /api/v1/anomalies`
* **DATA DISPLAYED**: Anomaly Event ID, Timestamp, Station ID, Location Name, Flagged Sensor, Anomaly Pattern Type (Spike, Step Bias, Drift, Stuck Sensor, Extreme Noise), Severity Level Badge, Confidence Score %, Review Status (Unassigned, Investigating, Resolved, False Positive).
* **USER INTERACTION**: Multi-select rows for batch status updates; click row to open Explanation View drawer.
* **UPDATE FREQUENCY**: Refreshes on SSE event or manual table filter application.
* **ERROR BEHAVIOR**: Displays empty state illustration with message "No anomalies matching active filters."

---

## 8. Explanation View

### Explainable AI (XAI) Modal / Drawer
When an operator inspects an anomaly, a dedicated XAI drawer slides open, breaking down the exact ML decision logic and spatial context.

```
+---------------------------------------------------------------------------------------------------+
| ANOMALY DIAGNOSTIC & EXPLANATION INSPECTOR - Event #AL-9042                                       |
+---------------------------------------------------------------------------------------------------+
| Station: AWS-108 | Sensor: Air Temperature | Flagged: 2026-09-29 10:42:00 UTC                       |
+---------------------------------------------------------------------------------------------------+
| Natural Language Explanation Box:                                                                 |
| "Air Temperature registered an abrupt +12.4 C jump in 60 seconds (Raw: 43.6 C). Spatial neighbor |
| stations (AWS-107, AWS-109) report steady 31.2 C. High probability of thermal sensor hardware    |
| spike fault (Confidence: 96.4%)."                                                                 |
+----------------------------------------------------+----------------------------------------------+
| SHAP Feature Attribution Waterfall Chart           | Spatial Cross-Validation Neighbor Map        |
| Parameter      | SHAP Value | Contribution %       | Neighbor ID | Distance | Observed Temp       |
| Rate of Change | +0.48      | [==========] 48%    | AWS-107     | 4.2 km   | 31.1 C              |
| Spatial Delta  | +0.38      | [========  ] 38%    | AWS-109     | 6.8 km   | 31.3 C              |
| Dewpoint Check | +0.10      | [==        ] 10%    | AWS-112     | 11.0 km  | 30.9 C              |
+----------------------------------------------------+----------------------------------------------+
| Actions: [ Accept ML Imputed Value ] [ Flag False Positive ] [ Dispatch Technician ]             |
+---------------------------------------------------------------------------------------------------+
```

### Major Components

#### Component: `XAI_EXPLANATION_CARD`
* **NAME**: `XAI_EXPLANATION_CARD`
* **PURPOSE**: Render human-readable explanations generated by the ML pipeline explaining why an observation was flagged and whether it represents genuine extreme weather or a sensor fault.
* **DATA SOURCE**: `xai_explanation_service`
* **API**: `GET /api/v1/anomalies/{anomaly_id}/explanation`
* **DATA DISPLAYED**:
  * Natural language summary
  * Primary detection model (e.g., Isolation Forest, Spatial KNN, Physical Bounds Check)
  * Confidence score breakdown
  * Physical bounds check status (e.g., $T > 55^\circ\text{C}$ failed)
  * Spatial consistency score ($0.0$ to $1.0$)
* **USER INTERACTION**: Click "Copy Explanation Text" for maintenance logs; click "Trigger Rescan".
* **UPDATE FREQUENCY**: Loaded dynamically per anomaly inspection request.
* **ERROR BEHAVIOR**: Displays "Explanation Engine Unavailable" fallback block.

#### Component: `SHAP_ATTRIBUTION_WATERFALL`
* **NAME**: `SHAP_ATTRIBUTION_WATERFALL`
* **PURPOSE**: Interactive chart showing feature attribution scores (SHAP values) contributing to the anomaly classification.
* **DATA SOURCE**: `ml_xai_service`
* **API**: `GET /api/v1/anomalies/{anomaly_id}/shap`
* **DATA DISPLAYED**: Horizontal waterfall/bar chart listing top predictive features (e.g., Temporal Gradient, Spatial Neighbor Difference, Humidity-Temperature Thermodynamic Correlation) and their positive/negative push on the anomaly score.
* **USER INTERACTION**: Hover over bar for raw feature values and threshold comparisons.
* **UPDATE FREQUENCY**: On request per selected anomaly.
* **ERROR BEHAVIOR**: Shows text-based list of top contributing metrics if graphics render engine fails.

---

## 9. Sensor Health View

### Sensor Degradation & Health Analytics
This view tracks long-term sensor reliability, drift velocity, signal noise ratio (SNR), and stuck sensor indicators.

```
+---------------------------------------------------------------------------------------------------+
| SENSOR HEALTH & DEGRADATION MATRIX                                                                |
+---------------------------------------------------------------------------------------------------+
| Station Selection: [ AWS-108 (Jaipur East) v ] Overall Health Index: 72% (DEGRADED)                |
+---------------------------------------------------------------------------------------------------+
| Sensor Health Breakdown Cards                                                                     |
| +-------------------------+ +-------------------------+ +-------------------------+             |
| | Air Temperature Sensor  | | Barometric Pressure     | | Relative Humidity       |             |
| | Health: 42% (CRITICAL)  | | Health: 98% (NOMINAL)   | | Health: 88% (GOOD)      |             |
| | Issue: Positive Bias    | | Issue: None           | | Issue: Minor Noise    |             |
| | Drift Rate: +0.2C/week  | | SNR: 45 dB            | | SNR: 32 dB            |             |
| +-------------------------+ +-------------------------+ +-------------------------+             |
+---------------------------------------------------------------------------------------------------+
| Calibration Drift & Stuck Sensor Line Plot (90-Day Trend)                                          |
+---------------------------------------------------------------------------------------------------+
```

### Major Components

#### Component: `SENSOR_HEALTH_GAUGE_GRID`
* **NAME**: `SENSOR_HEALTH_GAUGE_GRID`
* **PURPOSE**: Display health scores ($0-100\%$) and degradation indicators for each physical transducer attached to the station.
* **DATA SOURCE**: `sensor_health_service`
* **API**: `GET /api/v1/stations/{station_id}/health`
* **DATA DISPLAYED**:
  * Health Percentage Dial Gauge
  * Calibration Drift Offset ($\pm$ unit)
  * Signal Noise Level (dB)
  * Stuck Value Detection Count (last 30 days)
  * Days Since Last Physical Calibration
* **USER INTERACTION**: Click individual sensor card to open 90-day drift trend visualization.
* **UPDATE FREQUENCY**: Calculated hourly backend; polled every 30 seconds by UI.
* **ERROR BEHAVIOR**: Displays gray disabled gauge with "Sensor Offline" status.

---

## 10. Maintenance View

### Operational Maintenance & Feedback Loop
Enables operators to create tickets, schedule physical calibrations, and feed ground-truth validation back into the ML pipeline.

```
+---------------------------------------------------------------------------------------------------+
| MAINTENANCE & FIELD WORK ORDER CENTER                                                             |
+---------------------------------------------------------------------------------------------------+
| Active Tickets (3) | Scheduled Maintenance (2) | ML Feedback Queue (5 Unreviewed)                     |
+---------------------------------------------------------------------------------------------------+
| Work Order Creator & ML Feedback Interface                                                        |
| Ticket ID: WO-2026-8812                                                                          |
| Station: AWS-108 | Assigned Unit: Jaipur Regional Maintenance Ops                                 |
| Triggering Issue: Persistent Temperature Sensor Drift (+1.8 C offset detected)                    |
| Technician Ground Truth Input:                                                                    |
| [ Select Verification Result v ]                                                                  |
|   - Confirmed Hardware Defect (Retrain ML with True Positive)                                     |
|   - Microclimate Genuine Event (Flag as False Positive / Retrain Bounds)                           |
|   - Physical Sensor Cleaned/Re-calibrated (Reset Baseline Offset)                                 |
| [ Submit Work Order & Update ML Feedback ]                                                        |
+---------------------------------------------------------------------------------------------------+
```

### Major Components

#### Component: `WORK_ORDER_MANAGER`
* **NAME**: `WORK_ORDER_MANAGER`
* **PURPOSE**: Manage lifecycle of physical AWS repairs and submit technician verification feedback to close the ML active learning loop.
* **DATA SOURCE**: `maintenance_db`, `active_learning_feedback_service`
* **API**: `GET /api/v1/maintenance/tickets`, `POST /api/v1/maintenance/feedback`
* **DATA DISPLAYED**: Ticket ID, Station ID, Targeted Sensor, Recommended Action (Replace Transducer, Re-calibrate, Clean Radiation Shield, Check Cable Harness), Status Badge (Open, Dispatched, Resolved), Ground-Truth Feedback Selector.
* **USER INTERACTION**: Create new ticket, assign priority, select technician feedback classification, click "Submit & Update Model Memory".
* **UPDATE FREQUENCY**: On-demand user action + polling every 1 minute.
* **ERROR BEHAVIOR**: Displays toast notification with error description if submission fails.

---

## 11. Simulation/Demo Mode

### Interactive Fault Injection & Genuine Weather Testing Harness
A dedicated operational sandbox allowing developers, meteorologists, and evaluators to inject synthetic sensor anomalies or simulate genuine extreme meteorological events to observe real-time system responses.

```
+---------------------------------------------------------------------------------------------------+
| FAULT INJECTION & GENUINE WEATHER SIMULATION LAB                                                  |
+---------------------------------------------------------------------------------------------------+
| SIMULATION TARGET: [ AWS-108 (Jaipur East) v ] Mode Status: [ SIMULATION ACTIVE (Red Border) ]   |
+-----------------------------------+---------------------------------------------------------------+
| SYNTHETIC FAULT INJECTOR          | GENUINE EXTREME WEATHER SCENARIO GENERATOR                    |
| Fault Type: [ Step Bias Shift v ] | Scenario: [ Cyclonic Depression Simulation v ]                |
| Target Sensor: [ Air Temp v ]    | - Rapid Pressure Drop (-18 hPa in 3 hrs)                      |
| Magnitude: [ +4.5 C        ]      | - Sustained Wind Speed Rise (> 28 m/s)                        |
| Duration:  [ 15 Minutes    ]      | - Heavy Precipitation Rate (> 45 mm/hr)                       |
| Noise Level: [ Low (0.2)   ]      |                                                               |
| [ INJECT FAULT INTO STREAM ]      | [ TRIGGER GENUINE EXTREME WEATHER SCENARIO ]                  |
+-----------------------------------+---------------------------------------------------------------+
| LIVE MODEL RESPONSE VERIFICATION PANEL                                                           |
| Detected Status: FAULT DETECTED (Bias Drift Flagged) | ML Classification: SENSOR_FAULT (Not Weather) |
| System Action: Imputed Value Substituted (Raw: 38.5 C -> Imputed: 34.0 C) | Confidence: 97.2%    |
+---------------------------------------------------------------------------------------------------+
```

### Major Components

#### Component: `SIMULATION_CONTROL_PANEL`
* **NAME**: `SIMULATION_CONTROL_PANEL`
* **PURPOSE**: Configure and execute synthetic fault injections (Spike, Step Bias, Drift, Stuck Sensor, Noise, Packet Loss) or Genuine Extreme Weather scenarios to validate backend ML resilience.
* **DATA SOURCE**: `simulation_engine_service`
* **API**: `POST /api/v1/simulation/inject`, `POST /api/v1/simulation/reset`
* **DATA DISPLAYED**: Mode Indicator (LIVE vs SIMULATION), Target Station ID, Active Injection Profile, Parameters Modified, Elapsed Run Time.
* **USER INTERACTION**: Select fault type/scenario, adjust sliders for magnitude and duration, click "INJECT FAULT", click "RESET TO REAL LIVE STREAM".
* **UPDATE FREQUENCY**: Real-time state reflection.
* **ERROR BEHAVIOR**: Reverts UI state back to LIVE with alert if simulation server disconnects.

---

## 12. Charts

### Interactive Scientific Time-Series Specification
All charts are implemented using high-performance Canvas/WebGL rendering (Recharts / Chart.js / Apache ECharts) capable of rendering 10,000+ data points smoothly.

* **Dual-Line Telemetry Plot**:
  * **X-Axis**: Time (UTC ISO 8601 string, auto-formatting scale from 15 minutes to 30 days).
  * **Y-Axis Left**: Primary Metric Raw vs Corrected Value ($^\circ\text{C}, \text{hPa}, \%, \text{m/s}$).
  * **Y-Axis Right**: Anomaly Confidence Score ($0.0 - 1.0$) or Spatial Neighbor Average.
  * **Visual Styling**:
    * **Raw Stream Line**: Dashed line with semi-transparent points (`#EF4444` when flagged, `#94A3B8` when nominal).
    * **ML-Corrected Line**: Solid green/cyan line (`#10B981` / `#06B6D4`).
    * **Uncertainty Band**: Semi-transparent shaded area surrounding corrected line representing the model's $95\%$ confidence interval.
    * **Anomaly Highlight Region**: Vertical red translucent band across x-axis during active fault windows.
* **Interactions**: Pinch-to-zoom, Drag-to-pan, Hover tooltip showing exact raw vs corrected numeric values and delta, Export plot as SVG/PNG.

---

## 13. Tables

### Operational Data Grid Standard
All tables throughout the dashboard share a uniform UX pattern:
* **Dense Layout**: High information density suited for monitoring stations.
* **Sticky Header**: Headers remain locked to top during scroll.
* **Pagination & Virtualization**: Virtual scrolling enabled for lists $> 100$ items to maintain 60 FPS performance.
* **Column Customization**: Toggable column visibility (e.g., Hide/Show Lat/Lon, Battery Voltage, WMO Code).
* **Inline Status Badges**:
  * `PASS`: Solid green pill tag.
  * `IMPUTED`: Cyan border pill tag with original value on hover.
  * `ANOMALOUS`: Solid red pill tag with pulse animation.
  * `STUCK`: Solid purple pill tag.

---

## 14. Filters

### Global & View-Level Filter Specifications
The active context filter bar sits persistently below the breadcrumb:

```
+---------------------------------------------------------------------------------------------------+
| FILTERS: [ Region: Rajasthan North v ] [ Station: AWS-108 v ] [ Time: Last 24 Hours v ] [ Clear ]  |
+---------------------------------------------------------------------------------------------------+
```

1. **Geographic / Region Filter**: Dropdown grouped by State -> District -> Sub-district.
2. **Station Multi-Select**: Autocomplete search input by Station ID or Station Name.
3. **Time Range Selector**: Quick presets (`1 Hour`, `6 Hours`, `24 Hours`, `7 Days`, `30 Days`, `Custom Range Picker`).
4. **Severity Level Toggles**: Checkboxes for `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`.
5. **QC Flag Toggles**: Filter by `RAW`, `IMPUTED_ONLY`, `FAULTS_ONLY`.

---

## 15. Realtime Updates

### Communication Strategy
* **Primary Protocol**: Server-Sent Events (SSE) via `/api/v1/stream/live-telemetry` for lightweight, uni-directional streaming of station telemetry and anomaly alerts.
* **Fallback Protocol**: Exponential backoff polling (5s interval) if SSE connection fails or proxy blocks persistent HTTP connections.
* **State Management Indicator**: Persistent status dot in the global topbar:
  * **Connected**: Green pulsing dot + "LIVE (SSE Active)".
  * **Reconnecting**: Amber blinking dot + "Reconnecting (Attempt 2/5)...".
  * **Disconnected**: Red dot + "OFFLINE (Polling Fallback)".

---

## 16. Error States, Loading & Empty States

### Component State Handling Patterns

| View / Component | Loading State | Empty State | Error State |
| :--- | :--- | :--- | :--- |
| **Geospatial Map** | Gray map skeleton with spinner overlay | "No stations deployed in selected region." | "Failed to load map geometry. Retrying in 5s..." + Refresh Button |
| **Telemetry Card** | Skeleton pulse box matching gauge dimensions | "Sensor not installed on this station." | `--.-` display + Amber exclamation icon + Tooltip error detail |
| **Anomaly Table** | Skeleton rows shimmer effect (5 rows) | Clean checkmark graphic + "Zero active anomalies detected." | Red callout box with API status code & retry request action |
| **XAI Inspector** | Skeleton waterfall chart lines | "Select an anomaly from the triage queue to inspect." | "Explanation generation timeout. Model inference engine busy." |

---

## 17. API Integration

### Complete Frontend-to-Backend API Contract Mapping

| Component Name | Endpoint | Method | Request Payload / Params | Response Data Schema |
| :--- | :--- | :--- | :--- | :--- |
| `NETWORK_SUMMARY_CARDS` | `/api/v1/network/summary` | `GET` | `?region={region_id}` | `{ total_stations: int, online: int, degraded: int, offline: int, active_anomalies: int, health_index: float }` |
| `GEOSPATIAL_STATION_MAP` | `/api/v1/stations/geo` | `GET` | `?bbox={min_lat,min_lon,max_lat,max_lon}` | `[ { id: str, name: str, lat: float, lon: float, status: str, temp: float, pressure: float } ]` |
| `NETWORK_ANOMALY_FEED` | `/api/v1/stream/anomalies` | `SSE` | None | Event Stream: `{ anomaly_id: str, timestamp: str, station_id: str, parameter: str, severity: str, confidence: float }` |
| `STATION_HEADER_INFO` | `/api/v1/stations/{id}` | `GET` | Path `id` | `{ id: str, wmo_code: str, location: str, battery_v: float, last_ping: str, status: str }` |
| `PARAMETER_TELEMETRY_CARD`| `/api/v1/stations/{id}/latest`| `GET` | Path `id` | `{ station_id: str, timestamp: str, telemetry: { temp: { raw: float, qc: float, status: str } } }` |
| `ANOMALY_TRIAGE_TABLE` | `/api/v1/anomalies` | `GET` | `?page=1&limit=20&severity=HIGH` | `{ total: int, items: [ { anomaly_id: str, timestamp: str, station_id: str, pattern: str, severity: str } ] }` |
| `XAI_EXPLANATION_CARD` | `/api/v1/anomalies/{id}/explain`| `GET` | Path `id` | `{ anomaly_id: str, text_explanation: str, model_used: str, confidence: float, spatial_check: bool }` |
| `SHAP_ATTRIBUTION_WATERFALL`| `/api/v1/anomalies/{id}/shap`| `GET` | Path `id` | `{ anomaly_id: str, base_value: float, features: [ { name: str, value: float, shap_value: float } ] }` |
| `SENSOR_HEALTH_GAUGE_GRID` | `/api/v1/stations/{id}/health` | `GET` | Path `id` | `{ station_id: str, sensors: [ { parameter: str, health_score: float, drift_rate: float, snr_db: float } ] }` |
| `WORK_ORDER_MANAGER` | `/api/v1/maintenance/feedback` | `POST` | `{ ticket_id: str, verification: str, notes: str }` | `{ success: bool, ticket_id: str, updated_at: str }` |
| `SIMULATION_CONTROL_PANEL` | `/api/v1/simulation/inject` | `POST` | `{ station_id: str, fault_type: str, parameter: str, magnitude: float }` | `{ simulation_id: str, status: "ACTIVE", injected_at: str }` |

---

## 18. Acceptance Criteria

To ensure the UI implementation fulfills all domain and operational mandates, the frontend implementation must satisfy the following checklist:

* [ ] **Design Aesthetic**: Interface uses dark-theme-first palette matching operational weather agency monitoring software (NOAA/IMD/ECMWF standard).
* [ ] **Realtime Latency**: SSE stream updates telemetry indicators within $< 500\text{ ms}$ of backend event arrival.
* [ ] **Telemetry Integrity**: All telemetry cards display raw value side-by-side with ML-corrected value whenever an anomaly or imputation is active.
* [ ] **XAI Availability**: Clicking any anomaly opens the Explanation Inspector displaying both natural language text and SHAP waterfall chart.
* [ ] **Fault Simulation**: Operator can trigger fault injection (Spike, Bias, Stuck) in Demo Mode and visually confirm that the ML pipeline catches and corrects the fault in real time.
* [ ] **Genuine Weather Handling**: Scenario generator can simulate genuine extreme weather (e.g. pressure drop + high wind) and verify that the system flags it as genuine weather rather than a false-positive sensor fault.
* [ ] **Responsive Rendering**: Dashboard scales smoothly across 1920x1080 (Control Room Display), 1440x900 (Laptop), and 1024x768 (Tablet).
* [ ] **Zero Fabricated Statistics**: All UI badges, charts, and metrics strictly bound to backend API responses.

---

## 19. Handoff to Antigravity

### Technical Stack Guidelines for Implementation Team
* **Framework**: React 18+ / Next.js (App Router) with TypeScript.
* **Styling**: Tailwind CSS with custom theme extensions defined in Section 2.
* **Iconography**: Lucide React (`lucide-react`) for clean operational icons.
* **Charting Engine**: Recharts or Apache ECharts React for high-density time-series plots.
* **Geospatial Engine**: Leaflet.js (`react-leaflet`) or Mapbox GL with custom vector pin markers.
* **State Management**: Zustand / TanStack React Query (v5) for backend API caching and synchronization.
* **Streaming Client**: EventSource API / SSE client hook with automatic exponential reconnection logic.

```bash
# Recommended project initialization structure
/src
  /components
    /global        # Topbar, Sidebar, FilterBar, NotificationTicker
    /network       # GeospatialMap, NetworkSummaryCards, NetworkAnomalyFeed
    /station       # StationHeaderInfo, ParameterTelemetryCard, TimeSeriesChart
    /anomaly       # AnomalyTriageTable, DiagnosticModal
    /xai           # XAIExplanationCard, SHAPAttributionWaterfall
    /health        # SensorHealthGaugeGrid, DriftTrendPlot
    /maintenance   # WorkOrderManager, FeedbackForm
    /simulation    # SimulationControlPanel, FaultInjector
  /hooks           # useSSETelemetry, useAnomalies, useStationHealth
  /services        # apiContract.ts, sseClient.ts
  /types           # telemetry.d.ts, anomaly.d.ts, simulation.d.ts
```

---
*End of Technical Specification (`14C_UI_SPEC.md`)*