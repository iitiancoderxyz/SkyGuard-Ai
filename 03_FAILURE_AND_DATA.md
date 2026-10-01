# Data Strategy

Based on the parameters defined in "00_MASTER_BRIEF.md", the meteorological domain context from "01_DOMAIN_RESEARCH.md", and the pipeline constraints in "02_EXISTING_SOLUTIONS.md", the data strategy for SIH26073 relies on semi-supervised learning and synthetic augmentation. 

Given the lack of a massive, perfectly labelled dataset of real sensor faults, we will utilize **Clean-State Replay with Synthetic Injection**. We will source high-quality, verified historical weather observations (e.g., from meticulously maintained climatological stations) to serve as our "ground truth" normal state. We will then programmatically inject realistic fault patterns into this clean time-series data to create a robust, balanced benchmark dataset containing known ground-truth anomalies.

# Fault Taxonomy

Below are the 14 realistic anomaly classes, defined for injection into the base clean data $X = \{x_1, x_2, \dots, x_T\}$.

### 1. Isolated Spike
*   **Injection Mechanism**: Addition or subtraction of a large scalar to a single timestamp.
*   **Mathematical Formulation**: $x'_t = x_t + \delta \quad \text{where} \quad |\delta| \gg \sigma$
*   **Magnitude**: $3\sigma$ to $10\sigma$ deviation from local mean.
*   **Duration**: 1 timestep.
*   **Severity**: High amplitude, low temporal impact.
*   **Realism**: Simulates transient electrical interference or a single bird landing on a tipping bucket.
*   **Affected Variables**: Any (especially wind gust, precipitation).
*   **Expected Detector Behavior**: Immediate flagging; corrected via median filter imputation.

### 2. Repeated Spikes
*   **Injection Mechanism**: High-frequency periodic impulse addition.
*   **Mathematical Formulation**: $x'_t = x_t + \delta \cdot I(t \pmod p = 0)$
*   **Magnitude**: $2\sigma$ to $6\sigma$.
*   **Duration**: Sustained over $k$ periods.
*   **Severity**: Moderate to High.
*   **Realism**: Simulates a loose wire causing intermittent short circuits during wind gusts.
*   **Affected Variables**: Humidity, Temperature, Solar Radiation.
*   **Expected Detector Behavior**: Flagged as a localized anomaly cluster; pattern recognition needed.

### 3. Sudden Bias
*   **Injection Mechanism**: Step-function shift in the baseline reading.
*   **Mathematical Formulation**: $x'_t = x_t + C \quad \text{for} \quad t \ge t_{fault}$
*   **Magnitude**: $1\sigma$ to $4\sigma$.
*   **Duration**: Permanent until maintenance.
*   **Severity**: Severe (ruins climatological baselines).
*   **Realism**: Physical damage to the sensor housing, calibration loss, or permanent debris accumulation.
*   **Affected Variables**: Temperature, Pressure.
*   **Expected Detector Behavior**: Flagged via step-change detection; corrected by subtracting the estimated bias $C$.

### 4. Gradual Drift
*   **Injection Mechanism**: Linear or exponential trend superimposed on the signal.
*   **Mathematical Formulation**: $x'_t = x_t + \alpha (t - t_{fault}) \quad \text{for} \quad t \ge t_{fault}$
*   **Magnitude**: $\alpha$ ranges from $0.01\sigma$ to $0.1\sigma$ per day.
*   **Duration**: Weeks to months.
*   **Severity**: Highly severe (insidious and hard to detect).
*   **Realism**: Sensor degradation, battery decay, or bio-fouling (e.g., algae on a pyranometer).
*   **Affected Variables**: Humidity, Solar Radiation, Wind Speed.
*   **Expected Detector Behavior**: Long-term trend analysis divergence from neighbor stations.

### 5. Frozen/Flatline Sensor
*   **Injection Mechanism**: Value remains exactly constant despite changing environmental conditions.
*   **Mathematical Formulation**: $x'_t = c \quad \text{for} \quad t_{start} \le t \le t_{end}$
*   **Magnitude**: Local variance drops to 0.
*   **Duration**: Hours to days.
*   **Severity**: Moderate (easy to spot, but total data loss).
*   **Realism**: Freezing rain locking an anemometer, or software ADC crash.
*   **Affected Variables**: Wind Direction, Wind Speed, Temperature.
*   **Expected Detector Behavior**: Variance approaches zero; flagged rapidly.

### 6. Stuck-at Value
*   **Injection Mechanism**: Clamping the output to a specific hardware limit (e.g., max rail).
*   **Mathematical Formulation**: $x'_t = V_{max} \quad \text{or} \quad x'_t = V_{min}$
*   **Magnitude**: Absolute maximum or minimum of the sensor range.
*   **Duration**: Continuous until reset.
*   **Severity**: Extreme.
*   **Realism**: Short circuit to power or ground.
*   **Affected Variables**: Any.
*   **Expected Detector Behavior**: Rule-based limits should immediately catch this.

### 7. Excessive Noise
*   **Injection Mechanism**: Increase in the variance of the Gaussian noise floor.
*   **Mathematical Formulation**: $x'_t = x_t + \epsilon, \quad \epsilon \sim \mathcal{N}(0, \sigma_{fault}^2)$
*   **Magnitude**: $\sigma_{fault} > 3 \sigma_{normal}$.
*   **Duration**: Intermittent or continuous.
*   **Severity**: Moderate.
*   **Realism**: Failing components, water ingress causing erratic resistance.
*   **Affected Variables**: Temperature, Relative Humidity.
*   **Expected Detector Behavior**: Rolling variance exceeds dynamic thresholds.

### 8. Missing Observation (NaN)
*   **Injection Mechanism**: Complete drop of data payload.
*   **Mathematical Formulation**: $x'_t = \text{NaN}$
*   **Magnitude**: N/A
*   **Duration**: Single timestep to several hours.
*   **Severity**: Low to High (depending on duration).
*   **Realism**: Packet collision, temporary power loss.
*   **Affected Variables**: All variables simultaneously (usually).
*   **Expected Detector Behavior**: Imputation model triggered to fill gaps.

### 9. Communication Failure
*   **Injection Mechanism**: Disconnect resulting in no data row existing for the timestamp.
*   **Mathematical Formulation**: Timestamp $t$ is removed from the sequence.
*   **Magnitude**: N/A
*   **Duration**: Hours.
*   **Severity**: High.
*   **Realism**: Cellular network outage or gateway failure.
*   **Affected Variables**: Station-wide.
*   **Expected Detector Behavior**: Time-alignment preprocessing must insert NaNs, then flag as network failure.

### 10. Duplicate Observation
*   **Injection Mechanism**: Same data packet received and logged twice.
*   **Mathematical Formulation**: $x'_{t} = x'_{t-1} = x_{t-1}$
*   **Magnitude**: Zero difference between steps.
*   **Duration**: 1 to 2 timesteps.
*   **Severity**: Low.
*   **Realism**: Network retry logic failures.
*   **Affected Variables**: Station-wide.
*   **Expected Detector Behavior**: Data deduplication layer catches this before ML models.

### 11. Delayed Observation
*   **Injection Mechanism**: Data arrives out of order with a shifted timestamp.
*   **Mathematical Formulation**: Data for $t$ is recorded at $t + \Delta t$.
*   **Magnitude**: Delay of minutes to hours.
*   **Duration**: Transient.
*   **Severity**: Moderate (causes temporal misalignment).
*   **Realism**: High latency on satellite links (e.g., ARGOS network).
*   **Affected Variables**: Station-wide.
*   **Expected Detector Behavior**: Inconsistent rate-of-change; requires sequence re-ordering.

### 12. Corrupted Value
*   **Injection Mechanism**: Bit-flip or decoding error resulting in gibberish.
*   **Mathematical Formulation**: $x'_t = \text{Random}(min, max)$
*   **Magnitude**: Unpredictable.
*   **Duration**: Single timestep.
*   **Severity**: Moderate.
*   **Realism**: Serial protocol parity errors.
*   **Affected Variables**: Single random variable.
*   **Expected Detector Behavior**: Flagged as extreme physically impossible spike.

### 13. Multivariate Inconsistency
*   **Injection Mechanism**: Decoupling physically linked variables (e.g., raining but humidity drops).
*   **Mathematical Formulation**: $x'_{rh, t} = 40\% \quad \text{while} \quad x'_{precip, t} > 5mm$
*   **Magnitude**: Moderate deviation from physical laws.
*   **Duration**: Hours.
*   **Severity**: High.
*   **Realism**: Sensor housing breached, altering local microclimate for one sensor but not others.
*   **Affected Variables**: Temperature vs. Humidity, Wind Speed vs. Gust.
*   **Expected Detector Behavior**: Graph/Cross-attention layers detect broken correlation.

### 14. Combined Faults
*   **Injection Mechanism**: Superposition of multiple faults.
*   **Mathematical Formulation**: E.g., Drift + Noise: $x'_t = x_t + \alpha t + \mathcal{N}(0, \sigma_{fault}^2)$
*   **Magnitude**: Variable.
*   **Duration**: Variable.
*   **Severity**: Extreme.
*   **Realism**: Complete sensor end-of-life degradation.
*   **Affected Variables**: Multiple.
*   **Expected Detector Behavior**: High-confidence anomaly flag, model may struggle with specific root-cause classification.

# Synthetic Anomaly Generator

The anomaly generator will take clean multivariate time-series data and a configuration matrix mapping fault types to probabilities. 
1. **Seed Initialization**: Ensure deterministic randomization.
2. **Mask Generation**: Generate binary masks representing normal (0) and anomalous (1) states for every sensor and timestamp.
3. **Application**: Apply the mathematical transformations over the clean data where the mask is 1.
4. **Metadata**: Output a parallel metadata file indicating the exact onset, offset, magnitude, and root cause of every injection for perfect evaluation.

# Genuine Weather Events

To ensure low False Positive Rates (FPR), the test set MUST include "True Weather Scenarios" that look anomalous but are physically valid:
*   **Squall Lines / Microbursts**: Sudden, massive spikes in wind speed and extreme drops in temperature occurring in just minutes.
*   **Solar Eclipses**: Rapid, unnatural drop in solar radiation (pyranometer) during midday, coupled with minor temperature drops.
*   **Temperature Inversions**: Bizarre altitude-temperature profiles where mountain stations record significantly higher temperatures than valley stations.
*   **Frontal Passages**: Rapid step-changes in pressure and wind direction. 

# Benchmark Design

The benchmark will evaluate models on three distinct tasks:
1.  **Detection**: Binary classification of whether an anomaly exists.
2.  **Root-Cause Isolation**: Multi-class classification mapping the anomaly to one of the 14 taxonomy classes.
3.  **Imputation**: Reconstructing the "true" value underneath the anomaly.

# Train/Validation/Test Strategy

*   **Train Split (60%)**: Mostly clean historical data with minor natural noise. Used to establish normal baselines and train autoencoders/transformers.
*   **Validation Split (20%)**: Contains synthetically injected faults. Used for threshold tuning, hyperparameter optimization, and early stopping.
*   **Test Split (20%)**: Strictly sequestered. Contains complex Combined Faults and extreme Genuine Weather Events to test robustness.

# Leakage Risks

*   **Temporal Leakage**: Data must be split strictly sequentially (e.g., Train: 2015-2020, Val: 2021, Test: 2022). Random shuffling will allow the model to cheat by looking into the future.
*   **Spatial (Station) Leakage**: If evaluating Spatial Graph networks, testing must involve either a completely unseen time period for all stations, or a set of "hold-out" stations that the model has never trained on.

# Evaluation Metrics

*   **Detection Metrics**: F1-Score, Area Under the Precision-Recall Curve (PR-AUC). We prioritize PR-AUC over ROC-AUC due to the extreme class imbalance.
*   **Detection Latency Evaluation**: For continuous faults (e.g., Drift, Bias), evaluate the time delay ($t_{detected} - t_{fault}$) before the alarm triggers.
*   **Root-Cause Classification Metrics**: Macro-averaged F1-score across the 14 fault classes.
*   **Correction/Imputation Evaluation**: Root Mean Square Error (RMSE) and Mean Absolute Error (MAE) evaluated *only* on the masked anomalous regions comparing the imputed value to the original clean ground truth.
*   **Confidence Evaluation**: Expected Calibration Error (ECE) to ensure the model's anomaly probability outputs are reliable.

# Reproducibility Requirements

*   All random seeds for the Synthetic Anomaly Generator must be hardcoded and logged.
*   The raw clean data version, synthetic injection scripts, and final benchmark dataset must be version-controlled (e.g., via DVC or HuggingFace Datasets).

# Data Limitations

*   **Assumption of Cleanliness**: Historical data is never 100% clean. The "clean" baseline may contain latent, undetected real-world faults that could confuse training.
*   **Simulation Gap**: Mathematical injection cannot perfectly mimic the physical complexity of a dying sensor's electrical noise.

# HANDOFF TO NEXT AGENT
**Agent 04 (ARCHITECTURE & ML DESIGN)**: Please consume this Data Strategy and Fault Taxonomy. Your task is to design a model architecture that can handle multivariate time-series data, prevent temporal leakage, gracefully handle missing values (NaNs), and optimize for both detection (F1) and correction (RMSE) as defined in this document.