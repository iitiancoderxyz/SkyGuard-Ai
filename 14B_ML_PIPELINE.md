# 14B_ML_PIPELINE.md: ML & Statistical Pipeline Specification

## Document Metadata
- **Project Identifier**: SIH26073
- **Document Role**: Machine Learning & Statistical Pipeline Architecture Specification
- **Core Parameters**: Temperature ($T$, °C), Barometric Pressure ($P$, hPa), Relative Humidity ($RH$, %)
- **System Objective**: Continuous real-time anomaly detection, fault isolation, genuine weather vs. sensor anomaly attribution, sensor health degradation tracking, and physics-constrained data imputation for Automated Weather Stations (AWS).

---

# ML Architecture

The ML architecture operates as a hybrid hierarchical system combining physics-based thermodynamic boundary checks, unsupervised manifold modeling for anomaly detection, supervised fault isolation, and conformal uncertainty quantification. 

```
+-----------------------------------------------------------------------------------+
|                                 RAW AWS METRICS                                   |
|               Temperature (T)  |  Pressure (P)  |  Humidity (RH)                  |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                       STAGE 1: PREPROCESSING & SANITIZATION                       |
|   - Hard physical limits validation                                               |
|   - Missing value tagging                                                         |
|   - Spike / NaN handling                                                          |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                    STAGE 2: MULTIVARIATE FEATURE ENGINEERING                      |
|   - Temporal & Cyclical Encoding (Hour, Day, Month)                               |
|   - Moving Statistics & Rates of Change (dT/dt, dP/dt, dRH/dt)                    |
|   - Thermodynamic Indicators (Dew Point, Vapor Pressure, Psychrometric Delta)      |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                 STAGE 3: DUAL-PATH ANOMALY & CONSISTENCY DETECTOR                 |
|  +---------------------------------------+ +-----------------------------------+  |
|  | Unsupervised Deep Autoencoder         | | Thermodynamic & Physical Consistency|  |
|  | Reconstruction Error -> Anomaly Score | | Mathematical Rules Engine         |  |
|  +---------------------------------------+ +-----------------------------------+  |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                 STAGE 4: WEATHER-VS-SENSOR ATTRIBUTION ENGINE                     |
|   - Cross-variable derivative correlation analysis                                |
|   - Multi-parameter coupled shift validation vs single-variable isolated jump    |
|   - Pressure tendency storm classification                                        |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|            STAGE 5: ROOT-CAUSE FAULT CLASSIFICATION & HEALTH MONITORING           |
|   - Fault Classifier: Spike, Flatline, Drift, Noise, Calibration Shift            |
|   - Degradation Accumulator -> Sensor Health Index (0-100%)                       |
|   - Maintenance Signal Generator                                                  |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|              STAGE 6: CONFIDENCE, UNCERTAINTY & IMPUTATION ENGINE                 |
|   - Ensemble variance -> Epistemic Uncertainty                                    |
|   - Conformal Prediction Calibration -> Confidence Interval                       |
|   - Physics-Constrained Bidirectional LSTM Imputer (Applied ONLY if Sensor Fault) |
+-----------------------------------------------------------------------------------+
```

---

# Feature Engineering

All feature extraction runs strictly on $T$, $P$, and $RH$, along with the temporal coordinate $t$.

### 1. Temporal & Seasonal Features
*   **Hour Encoding**:
    $$\text{Hour}_{\sin} = \sin\left(\frac{2\pi \cdot h}{24}\right), \quad \text{Hour}_{\cos} = \cos\left(\frac{2\pi \cdot h}{24}\right)$$
*   **Day of Year Encoding**:
    $$\text{DOY}_{\sin} = \sin\left(\frac{2\pi \cdot \text{doy}}{365.25}\right), \quad \text{DOY}_{\cos} = \cos\left(\frac{2\pi \cdot \text{doy}}{365.25}\right)$$

### 2. Temporal Derivatives & Rates of Change
Computed over sliding windows $W \in \{1 \text{ step}, 3 \text{ steps}, 6 \text{ steps}\}$ (where 1 step = 15 minutes default):
*   **First Derivatives**:
    $$\dot{T}_t = \frac{T_t - T_{t-1}}{\Delta t}, \quad \dot{P}_t = \frac{P_t - P_{t-1}}{\Delta t}, \quad \dot{RH}_t = \frac{RH_t - RH_{t-1}}{\Delta t}$$
*   **Second Derivatives**:
    $$\ddot{T}_t = \frac{\dot{T}_t - \dot{T}_{t-1}}{\Delta t}, \quad \ddot{P}_t = \frac{\dot{P}_t - \dot{P}_{t-1}}{\Delta t}, \quad \ddot{RH}_t = \frac{\dot{RH}_t - \dot{RH}_{t-1}}{\Delta t}$$

### 3. Rolling Context Statistics
For each parameter $X \in \{T, P, RH\}$ over windows $W \in \{1\text{h}, 6\text{h}, 24\text{h}\}$:
*   **Rolling Mean**: $\mu_X(W)$
*   **Rolling Standard Deviation**: $\sigma_X(W)$
*   **Z-score**: $Z_X = \frac{X_t - \mu_X(W)}{\sigma_X(W) + \epsilon}$
*   **Diurnal Range**: $R_X(24\text{h}) = \max_{24\text{h}}(X) - \min_{24\text{h}}(X)$

### 4. Multivariate Thermodynamic Physics Features
Using the **Magnus-Tetens Approximation** derived exclusively from $T$ and $RH$:
*   **Saturation Vapor Pressure ($e_s$, hPa)**:
    $$e_s(T) = 6.112 \cdot \exp\left(\frac{17.67 \cdot T}{T + 243.5}\right)$$
*   **Actual Vapor Pressure ($e$, hPa)**:
    $$e(T, RH) = e_s(T) \cdot \frac{RH}{100.0}$$
*   **Dew Point Temperature ($T_d$, °C)**:
    $$\gamma(T, RH) = \ln\left(\frac{RH}{100.0}\right) + \frac{17.67 \cdot T}{T + 243.5}$$
    $$T_d = \frac{243.5 \cdot \gamma(T, RH)}{17.67 - \gamma(T, RH)}$$
*   **Dew Point Depression ($\Delta T_d$, °C)**:
    $$\Delta T_d = T - T_d$$
*   **Psychrometric Anti-Correlation Ratio ($\rho_{T, RH}$)**:
    $$\rho_{T, RH} = \frac{\text{Cov}(T, RH)_{24\text{h}}}{\sigma_T(24\text{h}) \cdot \sigma_{RH}(24\text{h})}$$
    *(Under normal diurnal cycles, $\rho_{T, RH} \approx -0.85$ to $-0.98$. Significant positive divergence indicates potential single-sensor corruption).*

---

# Training Pipeline

The offline training pipeline trains three distinct core components sequentially using historical operational AWS data enriched with synthetic fault injection.

```
                  +-----------------------------------+
                  |     Historical AWS Dataset        |
                  |     (T, P, RH Time-Series)        |
                  +-----------------------------------+
                                    |
                                    v
                  +-----------------------------------+
                  |   Synthetic Fault Injector        |
                  |   (Spikes, Drift, Flatline, Noise)|
                  +-----------------------------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+-----------------------+                       +-----------------------+
|  Unsupervised Path    |                       |    Supervised Path    |
| (Clean Data Only)     |                       | (Synthetically Faulty)|
+-----------------------+                       +-----------------------+
            |                                               |
            v                                               v
+-----------------------+                       +-----------------------+
| Train LSTM Autoencoder|                       | Train XGBoost Fault   |
| Baseline Model        |                       | Classifier            |
+-----------------------+                       +-----------------------+
            |                                               |
            +-----------------------+-----------------------+
                                    |
                                    v
                  +-----------------------------------+
                  | Conformal Calibration & Threshold |
                  | Tuning on Validation Set          |
                  +-----------------------------------+
```

### 1. Data Split Protocol
*   **Chronological Splitting**: Non-overlapping temporal splits to eliminate data leakage.
    *   **Train Set (70%)**: Uncorrupted baseline weather data for autoencoder manifold learning.
    *   **Validation Set (15%)**: Calibrating anomaly thresholds and conformal prediction error bounds.
    *   **Test Set (15%)**: Holdout evaluation including synthetic and real operational fault events.

### 2. Synthetic Fault Injection Engine (For Supervised Calibration)
Applied to $15\%$ of training time windows to create balanced fault ground truth:
*   **Flatline / Stuck**: Set $X_{t:t+k} = X_t + \mathcal{N}(0, 0.001)$ for $k \in [4, 48]$ steps.
*   **Single-Point Spike**: $X_t = X_t \pm k \cdot \sigma_X$ where $k \in [4, 10]$.
*   **Linear Calibration Drift**: $X_{t+i} = X_{t+i} + \delta \cdot i$ where $\delta = 0.05 \cdot \sigma_X / \text{step}$.
*   **High-Frequency Noise Inflation**: Add $\mathcal{N}(0, 3 \cdot \sigma_X)$ over $k \in [12, 96]$ steps.
*   **Out-of-Bounds Excursion**: Force $X_t > X_{\text{max\_physical}}$ or $X_t < X_{\text{min\_physical}}$.

---

# Inference Pipeline

Real-time streaming pipeline processing incoming 15-minute AWS payloads.

```
Incoming Stream (T, P, RH, t)
   |
   v
[ Step 1: Preprocessing ] ---> Range Check Breach? ---> YES ---> [ Hard Bounds Fault Triggered ]
   | NO
   v
[ Step 2: Feature Engineering ] (Extract derivatives, thermodynamics, rolling z-scores)
   |
   v
[ Step 3: Reconstruction Engine (LSTM-AE) ] ---> Compute Reconstruction Loss L_rec
   |
   v
[ Step 4: Weather vs. Sensor Attribution ]
   |
   +---> Multi-variable physical co-variation valid? ---> YES ---> [ Flag: Genuine Extreme Weather ]
   |                                                                  (Do NOT impute)
   | NO
   v
[ Step 5: Fault Classifier ] ---> Identify Root Cause (Spike/Drift/Flatline/Noise)
   |
   v
[ Step 6: Confidence & Uncertainty Calculation ]
   |
   v
[ Step 7: Imputation ] ---> (Only execute if Sensor Fault confirmed & Uncertainty < Threshold)
   |
   v
[ Output Payload: JSON Stream ]
```

---

# Algorithmic Specification: Models & Components

### Component 1: Preprocessing & Physical Range Sanitizer
*   **INPUT**: Raw sensor readings $T_t$, $P_t$, $RH_t$.
*   **PROCESS**:
    *   Evaluate physical domain limits:
        $$-50.0\text{ °C} \le T_t \le 60.0\text{ °C}$$
        $$500.0\text{ hPa} \le P_t \le 1100.0\text{ hPa}$$
        $$0.0\% \le RH_t \le 100.0\%$$
    *   Evaluate maximum allowable step change ($\Delta_{\text{max}}$):
        $$|T_t - T_{t-1}| > 10.0\text{ °C} \implies \text{Spike Flag}$$
        $$|P_t - P_{t-1}| > 12.0\text{ hPa} \implies \text{Spike Flag}$$
        $$|RH_t - RH_{t-1}| > 45.0\% \implies \text{Spike Flag}$$
*   **OUTPUT**: Sanitized features + Binary Flag Vectors $\mathbf{f}_{\text{range}}, \mathbf{f}_{\text{step}}$.

### Component 2: Unsupervised Reconstruction Model (LSTM Autoencoder)
*   **INPUT**: Sequence window $\mathbf{X}_{t-W:t} \in \mathbb{R}^{W \times 14}$ (features included).
*   **PROCESS**:
    *   Encoder maps input sequence to latent distribution $\mathbf{z} \in \mathbb{R}^{16}$.
    *   Decoder reconstructs sequence $\mathbf{\hat{X}}_{t-W:t}$.
    *   Compute Mean Squared Reconstruction Error across meteorological core variables ($T, P, RH$):
        $$L_{\text{rec}} = \frac{1}{3} \sum_{m \in \{T, P, RH\}} \frac{(m_t - \hat{m}_t)^2}{\sigma_m^2}$$
*   **OUTPUT**: Reconstruction Error Vector $\mathbf{E}_t \in \mathbb{R}^3$, Scalar Reconstruction Loss $L_{\text{rec}}$.

### Component 3: Root-Cause Fault Classifier (XGBoost Classifier)
*   **INPUT**: Vector $\mathbf{V}_t = [\mathbf{E}_t, L_{\text{rec}}, \dot{T}, \dot{P}, \dot{RH}, \ddot{T}, \ddot{P}, \ddot{RH}, \mu_T, \sigma_T, \dots, \Delta T_d, \rho_{T, RH}]$.
*   **PROCESS**:
    *   Pass $\mathbf{V}_t$ through a multi-class Gradient Boosted Decision Tree ensemble.
    *   Compute output probabilities over classes:
        $$\mathcal{C} = \{\text{NORMAL}, \text{SPIKE}, \text{FLATLINE}, \text{DRIFT}, \text{NOISE}, \text{CALIBRATION\_SHIFT}\}$$
*   **OUTPUT**: Predicted Class $\hat{c}$, Probability Distribution $\mathbf{P}(\mathcal{C})$.

### Component 4: Physics-Constrained Data Imputer (Bi-LSTM Model)
*   **INPUT**: Sequence with detected sensor fault masked out $\mathbf{X}_{\text{masked}}$.
*   **PROCESS**:
    *   Bidirectional LSTM processes forward past context and backward future context (in batch/delayed mode) or forward-only autoregressive estimation (in real-time mode).
    *   Apply thermodynamic constraint post-projection:
        $$\hat{T}_{d, t} = f(\hat{T}_t, \hat{RH}_t)$$
        $$\text{Enforce: } \hat{T}_t \ge \hat{T}_{d, t} \quad \text{and} \quad 0 \le \hat{RH}_t \le 100$$
*   **OUTPUT**: Imputed values $\hat{T}_t, \hat{P}_t, \hat{RH}_t$.

---

# Metric Disambiguation: Anomaly Score vs Severity vs Confidence vs Uncertainty

To ensure operational clarity, these four parameters are defined distinctly and mathematically separated:

```
+-------------------+---------------------------------------------------------+------------------------------------------+
| Metric            | Mathematical Definition                                 | Operational Meaning                      |
+-------------------+---------------------------------------------------------+------------------------------------------+
| ANOMALY SCORE (A) | Normalized Reconstruction Loss / Mahalanobis Distance   | How unexpected is this value relative to |
|                   | A = min(1.0, L_rec / Threshold_99)                      | normal historical patterns?              |
+-------------------+---------------------------------------------------------+------------------------------------------+
| SEVERITY (S)      | Absolute Distance from Safe Domain / Critical Threshold | How dangerous/damaging is the deviation  |
|                   | S = max(|T - T_mean| / Delta_max, Physical_Breach_Ratio)| to data integrity or meteorology?        |
+-------------------+---------------------------------------------------------+------------------------------------------+
| CONFIDENCE (C)    | Class Probability / Ensemble Agreement Ratio            | How sure is the model in its specific    |
|                   | C = max_c P(Class = c)                                  | fault or weather classification?         |
+-------------------+---------------------------------------------------------+------------------------------------------+
| UNCERTAINTY (U)   | Epistemic Variance + Conformal Interval Width           | How much model ambiguity or data noise   |
|                   | U = Var(Ensemble_Outputs) + Interval_Width              | exists in this decision?                 |
+-------------------+---------------------------------------------------------+------------------------------------------+
```

### Detailed Mathematical Formulations

1.  **Anomaly Score ($A_t \in [0, 1]$)**:
    $$A_t = 1 - \exp\left(-\frac{L_{\text{rec}, t}}{\tau_{\text{rec}}}\right)$$
    Where $\tau_{\text{rec}}$ is calibrated at the 95th percentile of validation reconstruction loss.

2.  **Severity ($S_t \in [0, 1]$)**:
    $$S_t = \max\left( A_t, \frac{|\dot{P}_t|}{10.0}, \frac{|\dot{T}_t|}{8.0}, \mathbf{I}(\text{Out of Physical Bounds}) \right)$$
    Where $\mathbf{I}(\cdot)$ is an indicator function yielding 1.0 on bound breach.

3.  **Confidence ($C_t \in [0, 1]$)**:
    $$C_t = \text{Top1Prob}(\text{XGBoost}) \times \left(1 - \frac{\text{Entropy}(\mathbf{P}(\mathcal{C}))}{\log_2(|\mathcal{C}|)}\right)$$

4.  **Uncertainty ($U_t \in [0, 1]$)**:
    Combine Epistemic Uncertainty ($\sigma^2_{\text{ensemble}}$) and Aleatoric Uncertainty ($\sigma^2_{\text{data}}$):
    $$U_{\text{epistemic}} = \frac{1}{M}\sum_{m=1}^{M} (\hat{y}_m - \bar{y})^2$$
    $$U_t = \min\left(1.0, \frac{U_{\text{epistemic}}}{\sigma^2_{\text{baseline}}} + \frac{\text{ConformalIntervalWidth}_t}{\text{MaxRange}}\right)$$

---

# Fault Classification

The system isolates root causes based on distinct temporal and multi-variable statistical signatures:

```
                                  FAULT TAXONOMY MATRIX
+--------------------+-------------------------------------------+---------------------------------------------+
| Fault Type         | Key Feature Signatures                    | Physical Verification                       |
+--------------------+-------------------------------------------+---------------------------------------------+
| SPIKE / TRANSIENT  | |dX/dt| > Threshold_step;               | Uncorrelated with other variables;          |
|                    | d^2X/dt^2 alters sign in t+1              | Return to baseline within <= 2 steps        |
+--------------------+-------------------------------------------+---------------------------------------------+
| FLATLINE / STUCK   | Var(X)_{12h} < 0.001;                     | T or RH flatlines while diurnal solar cycle |
|                    | dX/dt = 0 for > 4 consecutive readings    | demands fluctuation                         |
+--------------------+-------------------------------------------+---------------------------------------------+
| CALIBRATION DRIFT  | Monotonic trend in Z_X over > 7 days;     | Psychrometric anti-correlation fails:       |
|                    | No corresponding trend in neighboring parameters | Cov(T, RH) > 0 over extended periods  |
+--------------------+-------------------------------------------+---------------------------------------------+
| NOISE INFLATION    | High-frequency variance > 3x baseline;    | P, T, RH spectral density shifts to         |
|                    | Autocorrelation lag-1 drops near zero     | white noise characteristic                  |
+--------------------+-------------------------------------------+---------------------------------------------+
| OUT OF BOUNDS      | X_t > Max_Physical OR X_t < Min_Physical  | Direct hardware sensor element failure      |
+--------------------+-------------------------------------------+---------------------------------------------+
```

---

# Weather-vs-Sensor Attribution

Distinguishing a **genuine severe meteorological event** (e.g., cloudburst, cold front, squall line) from a **hardware sensor failure** is critical to avoid suppressing real weather data.

```
                               WEATHER vs SENSOR ATTRIBUTION DECISION TREE
                                                    |
                                       High Anomaly Score (A >= 0.75)
                                                    |
                                                    v
                                  Are MULTIPLE Core Variables Moving?
                                 (Co-variation of T, P, RH evaluated)
                                                    |
                       +----------------------------+----------------------------+
                       | YES                                                     | NO
                       v                                                         v
         Does Co-variation Satisfy                                  Isolate Faulty Variable:
            Thermodynamics?                                           Single Variable Outlier
    (e.g., P drops sharply + T drops                                             |
         + RH surges -> Storm)                                                   v
                       |                                            [ FLAG: SENSOR ANOMALY ]
         +-------------+-------------+                              Route to Fault Classifier
         | YES                       | NO
         v                           v
  [ FLAG: GENUINE WEATHER ]   [ FLAG: THERMODYNAMIC VIOLATION ]
  Suppress Imputation;        Flag multi-sensor issue / Calibration
  Trigger Weather Alert       Conflict
```

### Attribution Rules Engine

1.  **Genuine Microburst / Frontal Event Signature**:
    *   $\Delta P / \Delta t < -2.0 \text{ hPa/hr}$ (Rapid pressure drop) **AND**
    *   $\Delta T / \Delta t < -3.0 \text{ °C/15min}$ (Rapid cooling) **AND**
    *   $\Delta RH / \Delta t > +20.0\% / 15\text{min}$ (Rapid humidity increase).
    *   **Attribution Result**: `GENUINE_EXTREME_WEATHER`.
    *   **Action**: Anomaly Score set high, but Sensor Fault Flag set to `FALSE`. Imputation is **disabled**. Real-time alert dispatched.

2.  **Sensor Failure Signature (Single Variable Isolation)**:
    *   $T$ spikes by $+8.0 \text{ °C}$ within 15 minutes, but $P$ and $RH$ show $0.0\%$ deviation.
    *   **Physical Rule Check**: In ambient atmospheric conditions, an unconfined $+8.0 \text{ °C}$ heating event **must** alter local relative humidity ($RH$). Lack of response in $RH$ confirms sensor element fault.
    *   **Attribution Result**: `SENSOR_FAULT_SINGLE_VARIABLE`.
    *   **Action**: Flag affected variable, execute physics-constrained imputation.

### Resolution of Conflicting Model Evidence & High Uncertainty

When models provide conflicting signals (e.g., Autoencoder indicates anomaly $A_t > 0.85$, but Thermodynamic Check passes with high confidence, OR Uncertainty $U_t > 0.50$):

```
+-----------------------------------------------------------------------------------+
|                            CONFLICT RESOLUTION MATRIX                             |
+--------------------+---------------------+--------------------+-------------------+
| Anomaly Score (A)  | Uncertainty (U)     | Attribution State  | Automated Action  |
+--------------------+---------------------+--------------------+-------------------+
| A >= 0.80          | U < 0.25 (Low)      | Confident Sensor   | Auto-Impute &     |
|                    |                     | Fault              | Ticket Generation |
+--------------------+---------------------+--------------------+-------------------+
| A >= 0.80          | U >= 0.50 (High)    | AMBIGUOUS_EVENT    | SUPPRESS AUTO-    |
|                    |                     |                    | IMPUTE. Flag for  |
|                    |                     |                    | Human Review      |
+--------------------+---------------------+--------------------+-------------------+
| A >= 0.80          | Thermodynamic Rule  | GENUINE WEATHER    | Retain Raw Data;  |
|                    | Validated           |                    | High Priority     |
|                    |                     |                    | Weather Event     |
+--------------------+---------------------+--------------------+-------------------+
```

*   **Fallback Procedure for Ambiguous Events ($U_t \ge 0.50$)**:
    1.  **Do NOT overwrite raw data** in the primary ledger.
    2.  Mark observation flag as `AMBIGUOUS_WEATHER_OR_FAULT`.
    3.  Route payload to Central Server for multi-station spatial cross-validation (if adjacent stations exist).
    4.  Set Imputation mode to **Passive Hold** (forward-fill with explicit uncertainty bounds attached).

---

# Confidence & Uncertainty

### Epistemic & Aleatoric Uncertainty Quantification
1.  **Epistemic Uncertainty ($U_e$)**: Measured via Monte Carlo Dropout across 10 forward passes in the Autoencoder at inference time:
    $$U_e = \frac{1}{10} \sum_{i=1}^{10} (\hat{\mathbf{X}}_i - \bar{\mathbf{X}})^2$$
2.  **Aleatoric Uncertainty ($U_a$)**: Estimated via a dedicated residual regression head estimating standard deviation $\hat{\sigma}_t$:
    $$U_a = \hat{\sigma}_t^2$$

### Conformal Prediction Calibration
To guarantee coverage guarantees ($1 - \alpha = 0.95$), conformal intervals are generated on error residuals $R_i = |X_i - \hat{X}_i|$ from the validation set:
$$q_{\text{val}} = \text{Quantile}\left(R_1, \dots, R_N; \frac{\lceil (N+1)(1-\alpha) \rceil}{N}\right)$$
The real-time prediction interval for imputed metric $\hat{X}_{t}$ is:
$$\mathcal{I}_t = \left[ \hat{X}_t - q_{\text{val}}, \hat{X}_t + q_{\text{val}} \right]$$

---

# Sensor Health & Degradation

The **Sensor Health Index ($H_s \in [0, 100\%]$)** aggregates immediate anomalies and long-term performance drift over rolling 30-day windows.

```
                                SENSOR HEALTH INDEX ACCUMULATOR
+-----------------------------------------------------------------------------------+
| Daily Penalty Accumulation:                                                       |
|                                                                                   |
|  Penalty_day = (N_spikes * 1.5) + (N_flatlines * 5.0) + (Mean_Z_Drift * 10.0)      |
|                                                                                   |
| Health Index (30-Day Moving Window):                                              |
|                                                                                   |
|  H_s(t) = max(0.0, 100.0 - sum_{d=1}^{30} Penalty_day * decay_factor^(30-d) )    |
+-----------------------------------------------------------------------------------+
                                          |
        +---------------------------------+---------------------------------+
        |                                 |                                 |
        v                                 v                                 v
  H_s >= 80%                     50% <= H_s < 80%                       H_s < 50%
[ HEALTHY STATUS ]           [ DEGRADATION WARNING ]             [ CRITICAL MAINTENANCE ]
Normal Operation             Schedule Preventive Inspection      Automated Calibration Ticket
```

### Maintenance Signal Triggers
*   **Preventive Maintenance Flag**: Issued when $H_s < 70\%$ for 3 consecutive days OR cumulative drift Z-score exceeds $2.5\sigma$ continuously over 48 hours.
*   **Sensor Replacement Alert**: Issued when $H_s < 40\%$ OR severe flatline persists $> 24$ hours.

---

# Correction & Imputation

Imputation is governed by strict conditional logic to prevent data corruption during real weather extremes.

```
INPUT: Raw Reading X_t, Attribution Flag, Anomaly Score A_t, Uncertainty U_t
  |
  v
Is Attribution Flag == SENSOR_FAULT?
  |
  +---> NO (Attribution == GENUINE_WEATHER or NORMAL)
  |      |
  |      v
  |    [ PRESERVE RAW VALUE ] -> Do not impute. Output raw X_t.
  |
  +---> YES (Sensor Fault Confirmed)
         |
         v
       Is Uncertainty U_t < 0.40?
         |
         +---> YES ---> [ RUN BI-LSTM IMPUTER ]
         |              Generate X_imputed_t
         |              Apply Thermodynamic Hard Bounds Enforcer
         |              Output X_imputed_t with Quality Flag = IMPUTED_HIGH_CONF
         |
         +---> NO ----> [ FALLBACK IMPUTER ]
                        Forward-Fill / Linear Interpolation
                        Output X_imputed_t with Quality Flag = IMPUTED_LOW_CONF
```

---

# Model Serving & Runtime Specifications

### Runtime Stack
*   **Inference Engine**: ONNX Runtime (C++ / Rust binding for Edge; Python 3.11 Runtime for Central Server).
*   **Serialization Format**: ONNX (Open Neural Network Exchange) v1.14 with FP16 quantization for edge targets.
*   **Model Storage Structure**:
    ```
    /models/sih26073/v1.2/
    ├── encoder_quantized.onnx       # LSTM Encoder (320 KB)
    ├── decoder_quantized.onnx       # LSTM Decoder (410 KB)
    ├── fault_xgboost.onnx           # Fault Classifier (1.2 MB)
    ├── bi_lstm_imputer.onnx         # Imputer Network (850 KB)
    ├── conformal_calibration.json   # Quantile scalar thresholds
    └── metadata.json                # Model hash, train timestamp, hyperparams
    ```

### Latency Budget (Per 15-Minute Processing Cycle)
```
+------------------------------------+------------------+------------------+
| Pipeline Stage                     | Target Latency   | Max SLA Limit    |
+------------------------------------+------------------+------------------+
| Preprocessing & Range Checks       | < 2 ms           | 5 ms             |
| Feature Extraction & Derivatives   | < 5 ms           | 10 ms            |
| LSTM AE Reconstruction             | < 15 ms          | 40 ms            |
| Fault Classifier Inference         | < 8 ms           | 20 ms            |
| Uncertainty & Conformal Bounds     | < 5 ms           | 15 ms            |
| Imputation Engine (if triggered)   | < 12 ms          | 30 ms            |
| Payload Serialization & Dispatch   | < 3 ms           | 10 ms            |
+------------------------------------+------------------+------------------+
| TOTAL END-TO-END LATENCY           | ~ 50 ms          | < 130 ms         |
+------------------------------------+------------------+------------------+
```

---

# Edge vs Server Strategy

```
+-----------------------------------------------------------------------------------+
|                                 EDGE LAYER (MCU / IoT Gateway)                    |
|  - Executed on Microcontroller / Embedded Linux Gateway                           |
|  - Lightweight ONNX Model Execution (Quantized FP16 / INT8)                        |
|  - Micro-tasks:                                                                   |
|      1. Hard Physical Bounds Enforcement                                          |
|      2. First-pass Transient Spike Detection                                      |
|      3. Immediate Data Buffering & Fallback Imputation                            |
|      4. Telemetry Bandwidth Optimization (Flag-only transmission on normal)       |
+-----------------------------------------------------------------------------------+
                                          |
                                   Cellular / LORAWAN
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                               CENTRAL SERVER LAYER                                |
|  - Executed on Central Server Hub / Cloud Microservices                           |
|  - Tasks:                                                                         |
|      1. Full Multivariate LSTM Autoencoder Reconstruction                         |
|      2. Complex XGBoost Fault Root-Cause Isolation                                |
|      3. Weather-vs-Sensor Attribution Engine                                      |
|      4. Conformal Uncertainty Estimation & Calibration                            |
|      5. 30-Day Sensor Health Accumulation & Maintenance Ticket Routing            |
|      6. Model Retraining Triggering & Spatial Cross-Validation                    |
+-----------------------------------------------------------------------------------+
```

---

# Retraining & Update Strategy

```
                                RETRAINING TRIGGER LOGIC
+-----------------------------------------------------------------------------------+
| Triggers:                                                                         |
|  1. Data Drift Trigger: Population Stability Index (PSI) > 0.25 on features       |
|  2. Performance Trigger: Reconstruction Error baseline shifts > 20% over 14 days  |
|  3. Temporal Schedule: Automated bi-monthly retraining window                     |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| Retraining Workflow:                                                              |
|  1. Extract last 90 days of validated clean weather data                          |
|  2. Execute Synthetic Fault Injection pipeline                                    |
|  3. Train candidate models (AE + XGBoost)                                         |
|  4. Evaluate on Holdout Benchmark Dataset                                         |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| Automated Shadow Deployment Gate:                                                 |
|  - Candidate must outperform Production Model on F1-Score (F1_cand > F1_prod)     |
|  - Candidate False Positive Weather Alert Rate must be < 1.0%                     |
|  - If PASSED: Hot-swap ONNX model binary via Zero-Downtime Deployment             |
|  - If FAILED: Rollback and notify ML Engineer                                     |
+-----------------------------------------------------------------------------------+
```

---

# Testing Strategy

### 1. Synthetic Fault Injection Testing
Automated test suite injecting 500 ground-truth fault traces across historical clean datasets:
*   **Test Case 1 (Spike Test)**: Single step $+10\text{ °C}$ jump. Criteria: Isolated in Step 1, $C \ge 0.90$.
*   **Test Case 2 (Stuck Test)**: Flatline 12 steps. Criteria: Flagged by step 5, Fault class = `FLATLINE`.
*   **Test Case 3 (Drift Test)**: Slope $+0.1\text{ °C/hr}$ over 72 hours. Criteria: Isolated by hour 24, Fault class = `DRIFT`.

### 2. Historical Weather Extreme Backtesting
Stress tests run against real historical severe weather datasets (e.g., severe squalls, sudden temperature drops, cyclone passages):
*   **Test Case 4 (Squall Line Test)**: Rapid pressure drop $-4 \text{ hPa}$ in 30 minutes with coincidental temperature drop $-6\text{ °C}$.
    *   **Success Criterion**: Attribution engine MUST tag as `GENUINE_EXTREME_WEATHER`. Zero sensor fault tickets generated. Imputation MUST NOT run.

---

# Evaluation Metrics

1.  **Fault Classification Performance**:
    $$\text{Precision} = \frac{TP}{TP + FP}, \quad \text{Recall} = \frac{TP}{TP + FN}, \quad F_1 = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$
2.  **False Positive Weather Attribution Rate ($FPAR$)**:
    $$FPAR = \frac{\text{Genuine Weather Events Misclassified as Sensor Faults}}{\text{Total Verified Genuine Weather Events}} \le 1.0\%$$
3.  **Imputation Error (MAE / RMSE)**:
    $$\text{MAE} = \frac{1}{N} \sum_{i=1}^{N} |X_{\text{true}, i} - \hat{X}_{\text{imputed}, i}|$$
    $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (X_{\text{true}, i} - \hat{X}_{\text{imputed}, i})^2}$$

---

# Acceptance Criteria

To be approved for production deployment, the pipeline must satisfy all of the following non-negotiable benchmarks:

```
+-----------------------------------------+-----------------------------------+--------------------+
| Benchmark Metric                        | Required Threshold                | Evaluation Method  |
+-----------------------------------------+-----------------------------------+--------------------+
| Fault Isolation F1-Score                | >= 0.92                           | 500-trace test set |
| False Positive Weather Alert Rate       | < 1.0%                            | Historical extreme |
| End-to-End Processing Latency           | <= 100 ms (P95)                   | Stress test stream |
| Imputation MAE (Temperature)            | <= 0.45 °C                        | Masked validation  |
| Imputation MAE (Pressure)               | <= 0.60 hPa                       | Masked validation  |
| Imputation MAE (Relative Humidity)      | <= 2.5 %                          | Masked validation  |
| Model Binary Memory Footprint (Edge)    | <= 5 MB total                     | ONNX artifact size |
| Zero Crash Resilience under NaN / Nulls | 100% graceful handling (fallback) | Chaos injection    |
+-----------------------------------------+-----------------------------------+--------------------+
```

---

# Handoff to Antigravity Engine

### 1. Artifact Export Contracts
All trained models are exported directly to `/artifacts/models/latest/` with the following explicit schema interface:

*   **Input Tensor Schema (`onnx_input`)**:
    *   Name: `input_sequence`
    *   Shape: `[BatchSize, SequenceLength=24, FeatureCount=14]`
    *   Type: `Float32`
    *   Features Order: `[T, P, RH, dT_dt, dP_dt, dRH_dt, d2T_dt2, d2P_dt2, d2RH_dt2, T_d, delta_Td, Z_T, Z_P, Z_RH]`

*   **Output Tensor Schema (`onnx_output`)**:
    *   Name: `reconstructed_sequence` -> Shape `[BatchSize, 24, 14]`
    *   Name: `anomaly_scores` -> Shape `[BatchSize, 1]` (`Float32`, range $[0, 1]$)
    *   Name: `fault_logits` -> Shape `[BatchSize, 6]` (`Float32`, class probabilities)

### 2. Output Payload JSON Structure (API Output Contract)
```json
{
  "station_id": "AWS_STATION_1024",
  "timestamp": "2026-09-29T22:50:00Z",
  "raw_metrics": {
    "temperature": 28.4,
    "pressure": 1008.2,
    "humidity": 78.5
  },
  "processed_metrics": {
    "temperature": 28.4,
    "pressure": 1008.2,
    "humidity": 78.5
  },
  "analytics": {
    "anomaly_score": 0.12,
    "severity": 0.05,
    "confidence": 0.96,
    "uncertainty": 0.08,
    "attribution": "NORMAL",
    "fault_type": "NONE",
    "sensor_health_index": 98.5
  },
  "imputation": {
    "is_imputed": false,
    "imputed_variables": [],
    "conformal_interval_95": {
      "temperature": [28.05, 28.75],
      "pressure": [1007.6, 1008.8],
      "humidity": [76.0, 81.0]
    }
  },
  "flags": {
    "range_breach": false,
    "thermodynamic_violation": false,
    "maintenance_recommended": false
  }
}
```

### 3. Integration Endpoint Interface
```python
# System Entrypoint Interface for Antigravity Integration
def process_aws_payload(raw_json_payload: str) -> str:
    """
    Accepts raw JSON payload string from AWS MQTT message broker.
    Executes 6-stage ML pipeline.
    Returns validated, attributed, and corrected JSON payload.
    """
    payload = parse_json(raw_json_payload)
    sanitized = preprocess_range_check(payload)
    features = extract_multivariate_features(sanitized)
    
    rec_loss, score = run_autoencoder_inference(features)
    attribution = determine_weather_vs_sensor(features, score)
    
    if attribution == "SENSOR_FAULT":
        fault_class, conf = classify_fault(features)
        uncert = calculate_uncertainty(features)
        imputed_metrics, intervals = run_physics_imputer(features, uncert)
    else:
        fault_class = "NONE"
        conf = 1.0 - score
        uncert = calculate_uncertainty(features)
        imputed_metrics = payload["raw_metrics"]
        intervals = calculate_conformal_intervals(features)
        
    health_idx = update_sensor_health(payload["station_id"], fault_class)
    
    return format_output_payload(
        payload, score, conf, uncert, attribution, fault_class, imputed_metrics, intervals, health_idx
    )
```