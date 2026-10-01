# 04_ML_METHODS — CANDIDATE METHOD RESEARCH

**Project:** SIH26073 — AI/ML-Based Intelligent Anomaly Detection for Automatic Weather Stations (AWS)
**Agent:** RESEARCH AGENT 04 — MLSCOUT
**Research snapshot:** 29 September 2026
**Inputs read:** `00_MASTER_BRIEF.md`, `01_DOMAIN_RESEARCH.md`, `02_EXISTING_SOLUTIONS.md`, `03_FAILURE_AND_DATA.md`
**Status:** Research only. **No final solution is chosen in this document.** Ratings are qualitative analyst judgements, not measurements. Nothing here has been run.

**Evidence tags used throughout**

| Tag | Meaning |
|---|---|
| **[V]** | Verified this session by web search. Source ID (S1…S18) is listed in *Unknowns → Source list*. |
| **[02 §x]** | Taken from `02_EXISTING_SOLUTIONS.md` (prior-art hunt). Not independently re-verified here. |
| **[K]** | Established background knowledge (textbook or long-standing literature). Not re-verified this session. |
| **[A]** | Analytic reasoning by this agent. Plausible, but untested on this problem. |
| **[H]** | Hypothesis that needs an experiment before anyone relies on it. |

---

# Executive Summary

## 0. Read first: issues in inherited artifacts that affect method choice

These are flagged, not silently fixed (Master Brief handoff rules and Rule 15: preserve the PS, flag conflicts rather than silently changing the specification).

1. **`03_FAILURE_AND_DATA.md` breaks the core-input boundary.** Its taxonomy names wind speed, wind direction, wind gust, precipitation and solar radiation as affected variables or examples in faults 1, 2, 4, 5 and 13, and its genuine-event set relies on wind (squall lines) and a pyranometer (solar eclipse). Master Brief §3.1 and §9.2 forbid silently adding those variables. **This report evaluates methods only on Temperature, Pressure and Relative Humidity**, plus timestamp, station ID, location and elevation as metadata. Consequences:
   - Fault 13's "raining but humidity drops" example cannot be reproduced without a rainfall channel. It must be re-expressed in T/P/RH terms (for example, a T–RH pair that violates learned or thermodynamic coupling).
   - The solar-eclipse scenario has no sensing channel. In T/P/RH it is at most a small, slow temperature dip, so it is a weak test of genuine-event protection.
   - Squall lines and gust fronts are usable only through their **T/RH/P signature** (sharp T drop, RH rise, pressure surge), not through wind.
   - The benchmark owner must re-scope this. Until then, any F1 or PR-AUC quoted from a 03-style benchmark that used out-of-scope channels should be treated as non-comparable.
2. **Derived features are allowed only if labelled as derived.** Dew point, vapour pressure, mixing ratio and rate-of-change are computed from T, RH and P. They are fine as engineered features, but must never be presented as extra meteorological inputs (Master Brief §9.2).
3. **Imputation and correction are optional** (Master Brief §5.9, Rule 3). `03`'s Task 3 and its handoff line "optimize … correction (RMSE)" over-weight an optional feature. Imputation appears below only where it is a free by-product (for example, a Kalman smoother).
4. **Several of `03`'s 14 fault classes are not ML problems.** Faults 8–11 (NaN, communication drop, duplicate, delayed) are stream-integrity properties that deterministic alignment, de-duplication and ordering logic handle. Some classes are also only weakly identifiable from T/P/RH alone (1 vs 12, 5 vs 6 vs 10, 8 vs 9). A 14-class macro-F1 will be capped by that ambiguity regardless of the model.
5. **"AI/ML-based" is an interpretation risk.** Master Brief §10.1 requires AI/ML-based detection. Robust statistics, CUSUM and Kalman filters fit statistical baselines from data, but a judge may not count them as "AI/ML" if they are the whole system. This favours designs where fitted or learned components are demonstrably doing work (see Unknowns).

## 1. Headline findings

1. **The problem decomposes; no single method covers it.** Each sub-problem below has a different natural method family.

| Sub-problem | Nature | Method families that fit |
|---|---|---|
| Stream integrity (F6, F8–F11) | Deterministic | Range, alignment, de-duplication, ordering rules (M1) |
| Point and short anomalies (F1, F2, F12) | Residual outlier | Robust z / Hampel (M2), forecast residuals (M9), Isolation Forest (M4) |
| Persistent shift and drift (F3, F4) | Sequential change | CUSUM / EWMA (M3), BOCPD (M12), Kalman bias state (M9, M20) |
| Flatline (F5) and noise (F7) | Second-moment change | Rolling variance / run-length rules (M1, M2), variance charts (M3) |
| Multivariate inconsistency (F13) | Joint structure | Robust Mahalanobis, PCA/DPCA, cross-variable regression (M11), autoencoders (M7) |
| Genuine event vs fault | Contextual / hypothesis test | Coupling features (M11), shape features (M19), competing hypotheses (M12), optional spatial evidence |
| Root cause | Classification | Rules for pipeline classes; GBM / ROCKET / Bayesian posterior for waveform classes (M10, M12, M19) |
| Confidence vs severity | Calibration vs rule/impact | Conformal or calibrated probabilities (M15, M16); severity from magnitude × duration × variable criticality |
| Health, degradation, maintenance | Longitudinal | Change-point detection, trend extrapolation, evidence accumulation (M20) |

2. **Simple and statistical methods are strong baselines, and deep models must earn their place.** A NeurIPS 2024 benchmark of 40 detectors on 1,070 curated series found that simpler architectures and statistical methods often beat more advanced neural ones, while neural nets looked promising on multivariate data and foundation models on point anomalies **[V S1]**. Here the data is three variables, so "multivariate" is small.
3. **Evaluation protocol can dominate the ranking.** Point-adjusted F1 can make a random anomaly score look state-of-the-art, and an untrained reconstruction model can match published methods when point-adjustment is forbidden **[V S2]**. `03` specifies F1 and PR-AUC without saying whether point-adjustment is used. Recommend point-adjust-free metrics, event-level recall, detection delay, and VUS-PR (identified by S1 as the most reliable measure).
4. **Genuine-event protection is not delivered by any off-the-shelf detector.** Unsupervised detectors score rare-but-real states as anomalous by construction; this is the failure mode `01` §19 warns about. The evidence available for discrimination is cross-variable coherence, trajectory shape, and (optionally) network context. Methods that expose those signals (M11, M19, M12) matter more here than the choice of autoencoder.
5. **Forecast-residual detectors have blind spots that follow from how they work [A].** An autoregressive forecaster that conditions on recent values *absorbs* sudden bias and slow drift after a short lag, and a persistence-style forecaster *predicts* a flatline. Anomalies of type F3, F4 and F5 therefore need either an anchored, slow baseline or separate variance and run-length logic.
6. **Conformal methods calibrate alarm rate, not meaning.** They give p-values with a distribution-free false-alarm interpretation under exchangeability **[V S4, S6]**. Time series violate exchangeability, and the guarantee degrades on dependent data and in loops where the monitor changes the learner **[V S5, S6]**. Guarantees are marginal, not conditional on regime **[V S7]**. Crucially, a 1% alarm rate on normal data still flags ~1% of *genuine* extremes. Conformal is a calibration layer, not a genuine-event filter.
7. **Supervised models trained on injected faults risk learning the injector.** Artificial anomalies always differ from real ones and models must bridge that gap **[V S15]**. Any GBM or ROCKET root-cause classifier needs leave-one-injector-family-out evaluation, or its accuracy on `03`-style data is circular.
8. **Adaptive baselines can poison themselves.** Contamination degrades unsupervised detectors as its ratio rises **[V S14]**, and contamination-mitigation gives the largest gains on time-series data at substantially higher compute **[V S14]**. Gating updates with the system's own detector introduces a censoring bias (see M14) that has not been quantified in the files reviewed.
9. **Single-station drift detection has a fundamental identifiability limit [A].** With one station and three variables there is no independent reference. Slow bias can only be separated from climate variability via own long-term climatology, cross-variable relationship shifts, or neighbour stations. This bounds what "degradation prediction" can honestly claim.
10. **Control-chart thresholds must be scaled to sampling rate [K/A].** A CUSUM with common textbook settings (k = 0.5σ, h = 5σ) has an in-control average run length of about 465 samples **[K]**. At 5-minute sampling that is under two days per variable per station, far too frequent for a network. False-alarm design needs simulation on the real, autocorrelated residuals.
11. **Prior art covers every algorithm here.** A dynamic-linear-model (Kalman) QC method for weather sensors, evaluated on temperature, wind and humidity, already exists **[V S9]**. Isolation Forest, LSTM/GRU autoencoders, SHAP, health scores, hybrid rule+ML and edge deployment are all red ocean **[02 §2, §8]**. Any differentiation has to be behavioural and measured, not algorithmic.
12. **Edge feasibility is a design constraint, not a headline.** Generic ESP32 has ~520 KB SRAM and 240 MHz cores **[V S17]**; the S3 variant lists 512 KB **[V S17]**. Streaming robust statistics and CUSUM fit trivially; small tree ensembles and tiny quantized autoencoders are plausible but unmeasured; LSTM-scale or transformer models are not credible on-device. No energy figure has been verified.

## 2. What this document does not do

- It does not choose a detector, architecture or ensemble. Section "Promising Architectures" lists candidates and the experiments that would discriminate between them.
- It reports no performance numbers. All accuracy, latency, footprint and energy statements are expectations that Master Brief Rule 16 requires the team to measure.
- It does not claim novelty for anything. Section "Potential Differentiation" lists directions that may pass the `02` §11 novelty tests, not ones that have.

---

# Method-by-Method Analysis

## Conventions

- **Working assumptions** (all unverified; see Unknowns): 1–15-minute reporting interval; sensor resolution around 0.1 °C / 0.1 hPa / 1 %RH; several years of history for a "mature" station; a multi-station archive may or may not exist.
- **Deseasonalized residual** means the observation minus a learned expected value that depends on time-of-day and season (harmonic regression, robust climatology or STL-type decomposition). Most methods below work far better on residuals than on raw values because T and RH have strong diurnal cycles and P has tidal plus synoptic structure **[01 §12]**.
- **Fault IDs (F1–F14)** are those in `03`, restricted to what T/P/RH can express.
- **Rating scale:** L / M / H are relative judgements among the candidates. **Latency classes** are expectation classes, not measurements: µs (arithmetic on a few floats), sub-ms, ms, 10s+ ms.
- **Numbering:** M1–M22 map to the method families requested in the task, plus extras that the Master Brief's mandatory outputs require (health/degradation, explainability/root cause) and that are needed to judge the rest.

---

## M1 — Deterministic QC layer (range, step, persistence, alignment, de-duplication)

**What it is.** Physical-limit, rate-of-change, repeated-value/variance, timestamp-alignment, duplicate and ordering checks. Not ML, but the mandatory floor and the reference against which any ML gain must be measured **[01 §7]**.

- **Anomaly types handled:** F6 (rail-clamped values), F8–F11 (missing, gap, duplicate, delayed, via alignment/dedup), F5 (persistence rule), F12 (when out of range). Weak on F1/F2 inside physical range, F3, F4, F7.
- **Temporal capability:** Low–Medium (previous-value and window rules only).
- **Multivariate capability:** Low (RH > 100 %, dew point > T, and similar hard consistency checks).
- **Labelled data:** None. Limits and windows come from WMO/IMD guidance and station history, which `01` §22 says must be verified before hard-coding.
- **Training complexity:** None.
- **Inference latency:** µs.
- **False-positive risks:** Medium–High. Step limits fire on genuine fronts **[01 §7.2]**. Persistence rules fire on legitimately stable states (fog near 100 % RH, stable nocturnal pressure) **[01 §6.2]**.
- **Explainability:** High (the rule that fired).
- **Robustness:** Medium. Thresholds are site- and season-dependent.
- **Edge feasibility:** High.
- **Scalability:** High.
- **Implementation difficulty:** Low.
- **Novelty:** None; red ocean **[02 §2.1–2.3]**.
- **Known weaknesses:** Cannot see subtle, slow or contextual faults. Quantized sensors can produce legitimately repeated values, so "exact repeat" must be resolution-aware **[A]**.
- **Role:** Baseline B0 and feature generator. Its flags feed the ML layers, and its comparison shows what ML adds.

---

## M2 — Robust statistics (median/MAD, robust z-score, Hampel filter, seasonal robust baselines)

**What it is.** Rolling or seasonally conditioned median and MAD. The modified z-score is 0.6745·(x − median)/MAD, commonly flagged above 3.5 **[K]**. The Hampel identifier uses median ± k·1.4826·MAD **[K]**. Seasonal versions condition the baseline on hour-of-day × time-of-year, using robust harmonic regression (Huber/Tukey loss) or robust STL/MSTL-type decomposition **[K]**.

- **Anomaly types handled:** F1, F2 (partially), F12; F3 only at onset within a short window; F7 via rolling MAD of first differences; F5 via MAD of differences equal to zero.
- **Temporal capability:** Medium (window, plus seasonal conditioning when used).
- **Multivariate capability:** Low; per-variable unless applied to a residual vector (see M11).
- **Labelled data:** None.
- **Training complexity:** Low (fit a seasonal baseline; window state is trivial).
- **Inference latency:** µs (streaming median via two-heap or P² quantile estimator **[K]**).
- **False-positive risks:** Medium–High on fronts and squalls, because a big single-variable move looks like an outlier.
- **Explainability:** High ("x is 6.2 robust-σ from the seasonal norm").
- **Robustness:** Good against isolated outliers. **MAD collapses to zero on quantized or flat data**, so the divisor must be floored at the sensor resolution or the detector divides by zero on flat spells **[A]**. A rolling window absorbs drift and bias once the window fills with faulty data.
- **Edge feasibility:** High (ring buffers of tens of floats per variable).
- **Scalability:** High.
- **Implementation difficulty:** Low.
- **Novelty:** None; red ocean **[02 §2, Collision 14]**.
- **Known weaknesses:** Univariate; window contamination; heteroscedasticity (variance depends on regime and season) unless the scale is conditioned too.
- **Role:** Baseline B1/B2. Also the natural first stage that produces standardized residuals for M3, M11 and M14.

---

## M3 — EWMA, CUSUM, Page–Hinkley (sequential change and variance charts)

**What it is.** Accumulate small deviations of standardized residuals so persistent shifts become visible. CUSUM: S_t = max(0, S_{t-1} + z_t − k), alarm when S_t > h. EWMA: exponentially weighted mean. CUSUM is well suited to step changes, EWMA to noisy, gradual shifts **[V S13, blog-grade]**. Both are long-standing tools in process monitoring **[V S12]**. Running them on *squared* residuals or log-variance gives variance charts (noise increase F7, and the low side detects flatline F5).

- **Anomaly types handled:** F3 (step), F4 (drift), F7 (variance chart), F2 (persistent repeats); weak on single spikes (F1) because one impulse barely moves the statistic.
- **Temporal capability:** High (inherently sequential).
- **Multivariate capability:** Low as used here; multivariate EWMA/CUSUM exist **[K]**.
- **Labelled data:** None. Needs nominal residual σ from clean data.
- **Training complexity:** Low.
- **Inference latency:** µs (O(1) state per variable).
- **False-positive risks:** Medium. Any persistent real shift alarms, including a frontal passage or seasonal misfit. Residual autocorrelation inflates false alarms unless the residual is pre-whitened. **ARL0 must be matched to sampling rate:** k = 0.5σ, h = 5σ gives ARL0 ≈ 465 samples **[K]**, under two days at 5-minute sampling, so h must be much larger and set by simulation **[A]**.
- **Explainability:** High (the accumulated evidence and its start time).
- **Robustness:** Medium. Sensitive to burn-in and outliers in the reference estimate **[V S12 reports sensitivity tables for CUSUM to burn-in and outliers]**.
- **Edge feasibility:** High (a few floats per variable).
- **Scalability:** High.
- **Implementation difficulty:** Low, but tuning is subtle.
- **Novelty:** None; red ocean.
- **Known weaknesses:** Detects *any* change, so it cannot by itself tell drift from a real regime shift; needs a reset/acknowledge policy; detection delay for slow drift depends on σ, slope, k and h and must be measured (`03` already asks for delay evaluation).
- **Role:** Baseline B3. Also a health-signal generator (CUSUM of daily residual mean/variance) feeding M20.

---

## M4 — Isolation Forest (batch), including Extended IF

**What it is.** Random-partition trees; anomalies isolate in fewer splits. Defaults in common libraries are 100 trees on 256-sample subsamples **[K]**. Feature quality decides everything here: raw values give a pointwise detector, whereas windowed differences, rolling std, residuals, hour/season encodings and cross-variable residuals give a contextual one.

- **Anomaly types handled:** F1, F12 (strong); contextual points if context is encoded; F13 partially if cross-variable residual features are supplied; poor on F3/F4 (slow, small deviations).
- **Temporal capability:** Low by itself (order-blind); relies on engineered temporal features.
- **Multivariate capability:** Medium–High, but axis-aligned splits miss dependence structure unless features expose it (Extended IF helps **[K]**).
- **Labelled data:** None (clean-ish training data preferred).
- **Training complexity:** Low.
- **Inference latency:** sub-ms per sample.
- **False-positive risks:** **High for genuine extremes**: a rare state is isolated by construction. Contamination parameter is a guess; scores are uncalibrated. Score distributions shift with season.
- **Explainability:** Medium. TreeSHAP works on tree ensembles **[K]**; run on alert only, not per sample.
- **Robustness:** Medium. Performance degrades as training contamination rises **[V S14]**.
- **Edge feasibility:** Medium. Small pruned forests may fit; footprint is unmeasured **[H]**.
- **Scalability:** High.
- **Implementation difficulty:** Low.
- **Novelty:** None; explicit collision **[02 §2.6, Collision 3–4]**.
- **Known weaknesses:** Raw-value Isolation Forest is the "naive black-box" that `01` §19 names as a common mistake.
- **Role:** Baseline B5. Test both an engineered-feature version and a raw-value version as a straw man.

---

## M5 — Streaming tree/forest detectors (Half-Space Trees, RRCF, xStream-class)

**What it is.** Online anomaly detectors with bounded memory. Half-Space Trees (HST) use a reference window and mass profile **[K]**; Robust Random Cut Forest (RRCF) maintains a sketch of the stream and scores by the influence of a point on the tree **[V S10]**. River, a Python online-learning library, lists anomaly detection among its algorithm families **[V S11]**; HST ships in River and RRCF exists in separate implementations **[K, not re-verified]**.

- **Anomaly types handled:** Same as M4 (pointwise/contextual outliers) with slow adaptation.
- **Temporal capability:** Low–Medium (adaptive windows, not order-aware).
- **Multivariate capability:** Medium.
- **Labelled data:** None.
- **Training complexity:** None (learns online).
- **Inference latency:** sub-ms expected **[H]**.
- **False-positive risks:** High on genuine extremes, plus **self-contamination**: the reference window drifts toward faulty data (see M14).
- **Explainability:** Low–Medium.
- **Robustness:** Medium–Low without update gating.
- **Edge feasibility:** Medium (bounded memory; footprint unmeasured).
- **Scalability:** High (per-stream state).
- **Implementation difficulty:** Medium (window sizing, feature scaling for HST).
- **Novelty:** Low; established.
- **Known weaknesses:** Adapts to whatever the stream does, including faults; needs quarantined updates.
- **Role:** Watch/Component candidate for the online path; a comparator for M4.

---

## M6 — One-class and density/distance methods (OC-SVM, SVDD, LOF, kNN distance)

**What it is.** Learn a boundary or density of "normal" and score distance from it.

- **Anomaly types handled:** Pointwise/contextual outliers; F13 partially with suitable features.
- **Temporal capability:** Low.
- **Multivariate capability:** Medium.
- **Labelled data:** None.
- **Training complexity:** Medium–High. OC-SVM training scales poorly with sample count **[K]**; LOF/kNN must store the reference set.
- **Inference latency:** Medium (proportional to support vectors or stored points).
- **False-positive risks:** High on genuine extremes. Sensitive to kernel width and ν/contamination settings **[K]**.
- **Explainability:** Low.
- **Robustness:** Low–Medium.
- **Edge feasibility:** Low.
- **Scalability:** Low–Medium.
- **Implementation difficulty:** Low.
- **Novelty:** None. Already compared in published meteorological anomaly work **[02 §3.5]**.
- **Known weaknesses:** Rarely beats Isolation Forest or Mahalanobis on low-dimensional data; expensive to retrain per station.
- **Role:** Comparator only. Include one row in the benchmark and move on.

---

## M7 — Autoencoders (dense, convolutional, denoising, variational)

**What it is.** Compress and reconstruct a window of the three variables (for example 12 steps × 3 = 36 inputs). High reconstruction error, or low ELBO for a VAE, marks an anomaly. A VAE-based family was reported to detect pattern-wise anomalies well in an industrial benchmark **[V S3]**.

- **Anomaly types handled:** F13 (learns the joint T/RH/P manifold, at least in principle), F7, F1 when large; F3/F4 weak because small consistent offsets reconstruct fine; F5 possible via window shape.
- **Temporal capability:** Low–Medium (only via the input window).
- **Multivariate capability:** High.
- **Labelled data:** None.
- **Training complexity:** Medium.
- **Inference latency:** ms.
- **False-positive risks:** High on genuine extremes, which are out of distribution. Hyperparameter and threshold sensitivity; AEs can generalize so well they reconstruct anomalies.
- **Explainability:** Medium. Per-feature reconstruction error is a cheap native attribution; SHAP on autoencoders is costly and unstable **[K]**.
- **Robustness:** Low–Medium. Contaminated training data hurts **[V S14]**. Missing values need pre-imputation.
- **Edge feasibility:** Medium (a small quantized dense AE is plausible; microcontroller toolchains with autoencoder anomaly flows exist **[V S17]**, but ESP32 fit is unmeasured).
- **Scalability:** Medium. One model per station is a maintenance burden; a shared model with station embeddings or per-station scaling is an option. Per-series training was named an unaffordable-maintenance obstacle in industrial deployments **[V S3]**.
- **Implementation difficulty:** Medium.
- **Novelty:** None; red ocean, with peer-reviewed meteorological use **[02 §2.8, §3.4, §3.5]**.
- **Known weaknesses:** The "untrained reconstruction model" sanity baseline can match reported methods without point-adjust **[V S2]**, so include it.
- **Role:** Baseline B6 (one deep baseline). Also a candidate component for F13.

---

## M8 — LSTM/GRU/TCN autoencoders and sequence models

**What it is.** Recurrent or temporal-convolutional encoders that preserve order; stateful inference is possible in streaming.

- **Anomaly types handled:** F5, F7, F13; contextual and shape anomalies over longer windows; F4 only weakly.
- **Temporal capability:** High.
- **Multivariate capability:** High.
- **Labelled data:** None (clean-ish training).
- **Training complexity:** Medium–High; sensitive to window length and hyperparameters.
- **Inference latency:** ms (10s of ms for larger stacks).
- **False-positive risks:** High on genuine extremes.
- **Explainability:** Low–Medium.
- **Robustness:** Low–Medium.
- **Edge feasibility:** Low–Medium. KB-scale recurrent cells exist (for example FastGRNN listed among tiny-ML papers **[V S18]**), but nothing verified for this task.
- **Scalability:** Medium.
- **Implementation difficulty:** Medium.
- **Novelty:** None. LSTM-AE flatline detection on AWS air temperature is already published **[02 §3.6]**, ECMWF uses LSTM-AE **[02 §3.3]**, and "LSTM-AE + IF" is Collision 4.
- **Known weaknesses:** Whether an LSTM-AE beats a rolling-variance/run-length rule on flatline is not established in the reviewed files. For 3 variables the gain over a dense window AE is unproven; benchmark evidence favours simpler methods often **[V S1]**.
- **Role:** Watch. Include one sequence model to test whether order-awareness adds value beyond M7 and M9.


---

## M9 — Forecast-residual methods (AR / harmonic regression, Kalman / dynamic linear models, ML forecasters, pretrained forecasting models)

**What it is.** Predict the next observation from history, seasonal terms and (optionally) the other two variables; the standardized residual is the anomaly evidence. Sub-families:
- **(a) Climatology + AR(k) on the deseasonalized series.** Linear and cheap.
- **(b) State-space / dynamic linear models (Kalman).** Local level + seasonal + noise, with predictive variance. A Kalman step on a missing observation simply skips the update, so **NaNs and irregular timestamps are handled natively** **[K]**. A Bayesian DLM/Kalman QC method for weather sensors, using the same model and hyper-parameters across stations and variables, has been published for temperature, wind and humidity **[V S9]**; its abstract and introduction disagree on whether the reported ~11% figure is a false-negative or false-positive rate, and results are self-reported, so treat them cautiously.
- **(c) ML forecasters** (ridge or gradient boosting on lags and Fourier terms; TCN/LSTM).
- **(d) Pretrained forecasting foundation models** (Chronos/TimesFM-type families **[K]**; current versions not checked). One ICLR 2026 paper wraps such models in adaptive conformal calibration so the anomaly score maps to a false-alarm rate **[V S6]**.

- **Anomaly types handled:** F1, F2, F12, F7 (residual variance), F13 (via cross-variable prediction: predict one variable from the other two plus time). **F3 and F4 only if the forecaster is anchored to a slow baseline**; a forecaster that conditions on recent values adapts to the bias and stops flagging it **[A]**. **F5 is missed by persistence-style forecasters**, which predict a flat line **[A]**; a cross-variable predictor can catch a frozen variable while the others keep moving.
- **Temporal capability:** High. Seasonal capability is explicit.
- **Multivariate capability:** Medium–High (cross-variable predictors).
- **Labelled data:** None.
- **Training complexity:** Low (a, b) to Medium (c) to High (d, if fine-tuned).
- **Inference latency:** µs for (a, b); sub-ms to ms for (c); 10s–100s ms plausible for (d) **[H]**.
- **False-positive risks:** Medium–High on genuine events, because the forecaster does not know a front is coming. Residual variance is regime-dependent, so a fixed σ over-alarms at frontal times.
- **Explainability:** High ("expected 21.4 °C given RH, P and time; observed 27.9 °C").
- **Robustness:** Medium. Kalman handles gaps; contamination of the fit is the main issue.
- **Edge feasibility:** High for (a, b); Low for (d).
- **Scalability:** High for (a–c); Low–Medium for (d).
- **Implementation difficulty:** Low–Medium.
- **Novelty:** Low. Kalman/DLM for weather QC and Kalman-based sensor correction both have prior art **[V S9; 02 §3.8, Collision 12]**.
- **Known weaknesses:** Blind spots above (F3/F4/F5); not a genuine-event detector by itself; no natural handling of *why* a residual is large.
- **Role:** Baseline B7 (linear/Kalman) and a core component candidate. Regression-based consistency is a long-established QC idea in climatology **[K]**.

---

## M10 — Gradient boosting (supervised detection, root-cause classification, stacking, quantile forecasting)

**What it is.** LightGBM/XGBoost-type trees on engineered features (robust z, run lengths, rolling stats, cross-variable residuals, integrity flags). Three distinct roles: (i) supervised fault detector/classifier trained on injected faults; (ii) stacking meta-learner over detector scores; (iii) quantile-regression forecaster giving prediction intervals.

- **Anomaly types handled:** Any class present in the training injections (F1–F7, F12, F13 and combinations); pipeline classes only via integrity-flag features.
- **Temporal capability:** Medium (through lag/window features).
- **Multivariate capability:** Medium–High (through cross-variable features).
- **Labelled data:** **High.** Requires labelled examples, which here come from the synthetic injector.
- **Training complexity:** Low–Medium.
- **Inference latency:** sub-ms.
- **False-positive risks:** Depend entirely on whether genuine-event examples are in the training data. If genuine events are absent, the classifier has no notion of them; if they are synthetic, it learns the synthesizer.
- **Explainability:** Medium–High (TreeSHAP on alert).
- **Robustness:** **Low against sim-to-real gap.** Injected anomalies differ from true ones **[V S15]**; models can learn injector parameterization instead of physical fault signatures **[A]**. Probabilities from boosted trees typically need calibration **[K]**.
- **Edge feasibility:** Medium (small trees export to C).
- **Scalability:** High.
- **Implementation difficulty:** Low.
- **Novelty:** None; red ocean **[02 Collision 6]**.
- **Known weaknesses:** Circularity between generator and classifier. Class imbalance. Unseen fault shapes get forced into the nearest class unless an "insufficient evidence" outcome exists.
- **Role:** Baseline B8 (supervised reference and upper-bound-style comparator) and candidate root-cause component. Must be evaluated with leave-one-injector-family-out splits.

---

## M11 — Multivariate statistical methods (robust Mahalanobis, PCA/DPCA, cross-variable regression, physics-derived residuals)

**What it is.**
- **Robust Mahalanobis distance** of the deseasonalized residual vector r = (T, P, RH). Under multivariate normality d² ~ χ²(3), which gives an interpretable p-value. Robust covariance via MCD **[K]**.
- **PCA / dynamic PCA** with Hotelling T² and SPE/Q statistics; lag-stacked variants monitor temporal structure (a standard process-monitoring approach **[K]**).
- **Leave-one-variable-out consistency:** for Gaussian residuals, the standardized residual of variable *i* given the others is (Ω r)_i / √Ω_ii, where Ω is the precision matrix **[K]**. This is a principled "which variable is the odd one out" signal.
- **Physics-derived residuals:** saturation vapour pressure e_s(T) = 6.112·exp(17.67T/(T+243.5)) and RH = e/e_s × 100 **[01 §11]**. Dew point or vapour pressure is a deterministic function of T and RH; treat as a derived feature (see Executive Summary §0.2) and as a *soft* residual, not a rigid rule **[01 §11, 02 §7.7]**.

Mechanism relevant to genuine events **[A]**: Mahalanobis distance measures deviation *relative to the covariance*. A coherent move along a high-variance physical direction (for example T down, RH up) scores lower than the same Euclidean move against the correlation structure. This is the mathematical form of the "thermodynamic coupling as evidence" idea in `01` §10, but a large enough coherent event still scores high.

- **Anomaly types handled:** F13 (primary), joint spikes F1/F12, F3 partly, F7 partly; not F4, F5.
- **Temporal capability:** Low (higher with lag-stacking).
- **Multivariate capability:** High.
- **Labelled data:** None.
- **Training complexity:** Low.
- **Inference latency:** µs (3×3 or lag-stacked 18×18 matrix arithmetic).
- **False-positive risks:** Medium. Covariance is regime-dependent (fronts change variance and correlation), so a single Σ over-alarms in active weather. RH is bounded and skewed and pressure is heavy-tailed, so the Gaussian reference is approximate **[A]**.
- **Explainability:** High (per-variable conditional z, contribution plots).
- **Robustness:** Medium with MCD; masking is possible if the training set is heavily contaminated.
- **Edge feasibility:** High.
- **Scalability:** High.
- **Implementation difficulty:** Low.
- **Novelty:** None. Classical, and internal multivariate consistency is red ocean **[02 §2.4]**.
- **Known weaknesses:** Linear/Gaussian; needs regime-conditional covariance or conformal recalibration; cannot see slow uniform drift.
- **Role:** Baseline B4. Strongest cheap candidate for the mandatory multivariate-consistency requirement.

---

## M12 — Probabilistic methods (predictive densities, quantile models, state-space/GP, HMM/switching, BOCPD, Bayesian hypothesis posteriors)

**What it is.**
- **Heteroscedastic predictive densities** (Student-t or mixture; volatility-style variance models) turn residuals into log-likelihood scores without assuming constant σ.
- **Quantile regression** (trees or linear) gives distribution-free-style intervals without a Gaussian assumption.
- **Gaussian processes** (O(n³) exact; state-space/sparse forms reduce this) are mostly a Kalman-equivalent here **[K]**.
- **HMM / switching state-space** models regimes (calm, frontal, faulty) with a posterior over regime; unsupervised regimes may not align with semantic classes **[A]**.
- **Bayesian online change-point detection (BOCPD):** posterior over run length, updated online, giving a probability that a change occurred at every step **[V S12]**. Truncated and constant-time variants exist **[V S12]**.
- **Bayesian hypothesis posterior** (naive-Bayes or small Bayesian network over fault and event hypotheses) with an explicit "insufficient evidence" outcome. Conditional-independence assumptions are usually violated (temporal and cross-variable dependence), which tends to yield overconfident posteriors that must be calibrated **[A]**.

- **Anomaly types handled:** Broad. Predictive densities: F1, F3, F7. BOCPD: F3, F4, regime changes. Hypothesis posterior: root-cause and event-vs-fault reasoning.
- **Temporal capability:** High.
- **Multivariate capability:** Medium (multivariate models exist but grow complex).
- **Labelled data:** None for densities and BOCPD; Low–Medium to fit hypothesis likelihoods.
- **Training complexity:** Medium (EM for HMMs; hazard-rate priors for BOCPD).
- **Inference latency:** µs–ms.
- **False-positive risks:** Medium. Lower where uncertainty is modelled explicitly, but prior and hazard settings drive behaviour.
- **Explainability:** Medium–High (posterior over named hypotheses is readable; HMM states less so).
- **Robustness:** Medium–High when uncertainty is explicit.
- **Edge feasibility:** Medium (Kalman, truncated BOCPD and small HMMs plausible; full posterior machinery is not).
- **Scalability:** Medium–High.
- **Implementation difficulty:** Medium.
- **Novelty:** Components are red ocean. A competing-hypothesis engine with calibrated abstention is a possible differentiation area, unproven **[02 §7.5, §9.5]**.
- **Known weaknesses:** Model misspecification; priors are hard to justify without real fault data; BOCPD runtime grows with run length unless truncated **[V S12]**.
- **Role:** Component candidates (Kalman backbone, BOCPD for health, hypothesis posterior for root cause).

---

## M13 — Ensemble and evidence-fusion methods

**What it is.** Combine detectors: score averaging or max, rank/ECDF normalization, stacking (logistic/GBM), cascades (cheap first), mixture-of-experts gating, and evidence combination (Bayesian, Dempster–Shafer, p-value or e-value combination).

- **Anomaly types handled:** Inherits from members; diversity is what adds coverage.
- **Temporal / multivariate capability:** Inherits.
- **Labelled data:** None for averaging or cascades; Medium for stacking.
- **Training complexity:** Medium.
- **Inference latency:** Sum of members (cascades reduce the average).
- **False-positive risks:** Can reduce them if members err differently; can also compound them if members are correlated. Raw scores from different detectors are not comparable, so normalization is required. Conformal p-values from different detectors *are* a common currency, but they are positively dependent on the same observation, so independence-based combination (Fisher) is not valid; dependence-robust rules (Simes, Bonferroni-style, e-values) are safer **[K/A]**.
- **Explainability:** Medium (harder as members multiply).
- **Robustness:** Medium–High if diverse.
- **Edge feasibility:** Low–Medium (only cascades of tiny members).
- **Scalability:** Medium.
- **Implementation difficulty:** Medium.
- **Novelty:** None. "Hybrid" and "LSTM-AE + IF ensemble" are explicit collisions **[02 Collisions 1, 4]**.
- **Known weaknesses:** Arbitrary voting; correlated members add little; harder to explain. The open question is **conflict resolution**: what happens when temporal evidence says fault and spatial or physical evidence says weather **[02 §9.2]**.
- **Role:** Component, only after ablations show gain over the best single member.

---

## M14 — Online and adaptive methods (incremental statistics, adaptive filters, drift detectors, gated retraining)

**What it is.** Streaming estimators (Welford mean/variance, P² quantiles), recursive least squares, Kalman with innovation-based adaptive noise, drift detectors on error (ADWIN, Page–Hinkley) **[K]**, periodic retraining, and **gated updating** in which suspect data are excluded from baseline updates (quarantine buffer, trusted reference snapshot, baseline versioning, rollback) **[02 §7.3, §9.3]**.

- **Anomaly types handled:** Reduces false alarms from seasonal and regime shift. **Actively hides F3/F4** unless gated, because the baseline adapts to the fault.
- **Temporal capability:** High.
- **Multivariate capability:** Medium.
- **Labelled data:** None.
- **Training complexity:** None to Low.
- **Inference latency:** µs.
- **False-positive risks:** Lower under seasonal change; higher risk of *missed* faults through absorption.
- **Explainability:** Medium.
- **Robustness:** Low unless gated. Evidence for the danger: contamination degrades detectors as ratio rises **[V S14]**; conformal test martingales' guarantees fail inside feedback loops where the monitor modifies the learner **[V S5]**.
- **Edge feasibility:** Medium–High.
- **Scalability:** High.
- **Implementation difficulty:** Medium–High (gate design and testing).
- **Novelty:** Adaptive learning is red ocean. Baseline-contamination resistance is named as underexplored **[02 §7.3, §9.3, Target 1]**.
- **Known weaknesses [A]:** Gating with the system's own detector is a **censored-sampling loop**. Points near the threshold are excluded, so the baseline variance is underestimated, thresholds tighten, more points are quarantined, and false alarms creep. This effect has not been quantified in the files reviewed; it is testable (Experiment E3).
- **Role:** Component and differentiation candidate; the mechanism, not the model, is the interesting part.

---

## M15 — Uncertainty estimation and calibration

**What it is.** Ways to attach a meaningful confidence to detection and classification: deep ensembles, MC dropout, quantile heads, Bayesian last layers, evidential models; and post-hoc calibration (Platt, isotonic, temperature scaling) **[K]**. Evaluation via reliability diagrams, Brier score, ECE and selective-risk curves **[02 §9.1]**.

- **Anomaly types handled:** N/A (a layer on other detectors). Separates aleatoric noise from epistemic (out-of-distribution) uncertainty, which matters because an extreme but coherent event is out-of-distribution *without* being a fault.
- **Temporal / multivariate capability:** Inherits.
- **Labelled data:** Medium. Calibration needs labelled or clean-reference data.
- **Training complexity:** Medium (5× for ensembles).
- **Inference latency:** ×k for ensembles or MC dropout.
- **False-positive risks:** Helps if used for abstention; harmful if confidence is decorative (Master Brief §11.8).
- **Explainability:** Medium.
- **Robustness:** Medium. Calibration degrades under distribution shift.
- **Edge feasibility:** Low for ensembles; High for a calibration lookup table.
- **Scalability:** Medium.
- **Implementation difficulty:** Medium.
- **Novelty:** None as a method.
- **Known weaknesses:** ECE with 1–5% positive prevalence is unstable (few positives per bin), so `03`'s ECE metric should be supplemented with Brier score, per-class reliability diagrams and risk–coverage curves **[A]**. MC dropout is cheap but often poorly calibrated **[K]**.
- **Role:** Component (calibration layer). Deep ensembles for uncertainty are a Watch/overengineering risk given cheaper options (M16).


---

## M16 — Conformal approaches

**What it is.** Turn any score into a p-value with a finite-sample interpretation, using a calibration set. Variants relevant here:
- **Split conformal anomaly detection:** p = (1 + #{calibration scores ≥ s}) / (n + 1), valid under exchangeability. A Python library packages this on top of detectors such as Isolation Forest **[V S4]**.
- **Conformalized quantile regression** for adaptive-width intervals **[K]**.
- **Adaptive conformal inference (ACI):** updates the miscoverage level online so long-run coverage tracks the target without exchangeability **[K]**.
- **Weighted / time-decayed conformal:** an ICLR 2026 paper learns weights over past predictions to keep false-alarm control under distribution shift **[V S6]**.
- **Mondrian (group-conditional) conformal:** separate calibration per group (for example hour-of-day bin, season, station regime) for conditional rather than marginal coverage **[V S8; K]**.
- **Conformal test martingales with a Ville threshold:** the probability of ever crossing level λ under the null is at most 1/λ, so λ = 100 corresponds to at most a 1% anytime false-alarm bound **[V S4]**; useful for change detection.

- **Anomaly types handled:** N/A directly; it calibrates a residual or detector score.
- **Temporal capability:** Depends on the score; ACI and weighted variants add adaptivity.
- **Multivariate capability:** Depends on the score.
- **Labelled data:** A **clean calibration set** only (not fault labels). Contaminated calibration data inflates thresholds and causes misses **[A]**.
- **Training complexity:** Low.
- **Inference latency:** µs (quantile table lookup).
- **False-positive risks:** Controls the *rate* of alarms on nominal data, not their *meaning*: genuine extremes still occupy the calibrated tail **[A]**. Guarantees are marginal, not conditional; they can be weakest exactly where test data deviate from calibration **[V S7]**.
- **Explainability:** High (a p-value reads as an alarm rate).
- **Robustness:** Medium. Exchangeability is often violated in time series **[V S6]**; the guarantee is conditional on exchangeability, hardest to satisfy on dependent data and in feedback loops **[V S5]**.
- **Edge feasibility:** High (a stored quantile table).
- **Scalability:** High.
- **Implementation difficulty:** Low–Medium.
- **Novelty:** Method is established. Conformal anomaly detection, martingale monitoring and time-series variants all exist **[V S4–S7]**. One targeted search this session did not surface conformal calibration applied to AWS/weather-sensor QC; this is **not evidence of absence** and needs the `02` §11 prior-art test.
- **Known weaknesses:** Needs time-aware calibration (chronological split, per-regime groups) and a monitoring plan for coverage drift. Any claim must say "approximate under temporal dependence," not "guaranteed."
- **Role:** Component and differentiation candidate for calibrated confidence and abstention (Master Brief §4.7, §11.8).

---

## M17 — Lightweight edge models

**What it is.** What can plausibly run on an ESP32-class logger. Budget facts: generic ESP32 lists 520 KB SRAM, 4 MB flash and a 240 MHz core **[V S17]**; ESP32-S3 boards list 512 KB SRAM **[V S17]**. Usable application RAM after the network stack and OS is lower and is not verified here **[K/H]**. Tools exist for on-device time-series anomaly and autoencoder flows on microcontrollers **[V S17]**.

Candidate edge components, ordered by plausibility **[A]**:
1. **Integrity and persistence rules** (M1): trivial memory.
2. **Streaming robust statistics and Hampel filters** (M2): a few dozen floats per variable.
3. **CUSUM/EWMA/variance charts** (M3): a few floats per variable.
4. **Small exported tree ensembles** (M4/M10): tens of KB, unmeasured.
5. **Tiny quantized dense autoencoder** (M7): plausible; measure flash, RAM and latency.
6. **KB-scale recurrent cells** (M8): possible in principle; not verified for this task.
Not credible on-device: transformers, large LSTM stacks, conformal martingale machinery with big buffers, pretrained forecasting models.

- **Anomaly types handled:** Those of the included components; realistically F1, F3, F5–F7 and pipeline flags at the edge.
- **Temporal / multivariate capability:** Low–Medium.
- **Labelled data:** None for statistical components.
- **Training complexity:** Trained or fitted off-device.
- **Inference latency:** µs–ms.
- **False-positive risks:** Same as members; the edge layer should emit flags and sufficient statistics rather than final verdicts, so a server can override with more context **[A]**.
- **Explainability:** High for rules/statistics.
- **Robustness:** Medium.
- **Edge feasibility:** By definition; energy is **not verified** and is dominated in practice by radio and sensing duty cycle rather than arithmetic **[H]**.
- **Scalability:** High (distributes compute).
- **Implementation difficulty:** Medium (firmware, fixed-point).
- **Novelty:** None. ESP32/edge deployment is explicitly suggested by the PS and is red ocean **[02 §2.16]**.
- **Known weaknesses:** Master Brief §9.11 and the claims list forbid edge or energy claims without a demonstrated implementation.
- **Role:** Component. Design the edge layer as "cheap, robust, raw-preserving," and measure it.

---

## M18 — Hybrid statistical + ML patterns

**What it is.** Patterns for combining M1–M17. This is an architectural family, not one algorithm.

| Pattern | Idea | Strength | Risk |
|---|---|---|---|
| **P1 Residual-then-ML** | Statistical baseline produces standardized residuals and flags; ML consumes them as features | Stable inputs; smaller models; explainable features | ML inherits baseline mistakes |
| **P2 Cascade** | Cheap tests gate expensive ones | Latency and edge cost | Early stage can hide what later stages would catch |
| **P3 ML detector + physics/rule veto** | Rules override ML alarms when coupling is coherent | Genuine-event protection | Vetoes become hand-tuned thresholds |
| **P4 Diverse detectors + calibrated fusion + abstention** | Combine M11/M9/M4/M7 via p-values/posteriors; route conflicts to "suspect / human review" | Honest uncertainty | Complexity; needs calibration data |

- **Known weakness common to all:** "Hybrid" is not novel in itself **[02 Collision 1, 22]**. Value is in the decision logic and evidence, not the stack.
- **Role:** Framing for "Promising Architectures".

---

## M19 — Shape and trajectory methods (matrix profile, ROCKET-style classifiers, feature-based classifiers)

**What it is.** Treat anomalies as short trajectories rather than points **[02 §9.5]**.
- **Matrix profile / discords:** subsequence nearest-neighbour distance; streaming variants exist **[K]**.
- **ROCKET/MiniRocket:** random convolutional kernels plus a linear classifier for fast time-series classification **[K]**; suited to window-level root-cause classes (spike-and-recover, step, ramp, flat, noise burst, coherent excursion).
- **Feature-based classification:** hand-designed shape features (slope, curvature, return-to-baseline ratio, variance ratio, run length, cross-variable lag correlation) into GBM. Often competitive and more interpretable **[A]**.

- **Anomaly types handled:** F1 vs F12 vs coherent event shape, F3 (step), F4 (ramp), F5 (flat), F7 (noise burst), F13 (cross-variable lag structure).
- **Temporal capability:** High.
- **Multivariate capability:** Medium (multi-dimensional matrix profile exists; ROCKET can take multichannel windows).
- **Labelled data:** High for ROCKET and feature-GBM (synthetic labels); None for discords.
- **Training complexity:** Low–Medium.
- **Inference latency:** ms; naive streaming matrix profile cost grows with history unless windowed **[K/H]**.
- **False-positive risks:** Medium. Shape evidence could separate coherent events from faults, but this is **untested** **[H]**.
- **Explainability:** Medium (features/shapelets high; ROCKET low).
- **Robustness:** Low–Medium; same injector-circularity risk as M10.
- **Edge feasibility:** Low.
- **Scalability:** Medium.
- **Implementation difficulty:** Medium.
- **Novelty:** Methods established. "Event-shape vs fault-shape modeling" is named underexplored **[02 §9.5]**, but that names an opportunity, not a demonstrated result.
- **Known weaknesses:** Requires labelled windows; real fault shapes may deviate from synthetic ones.
- **Role:** Watch; a strong candidate for root-cause classification experiments.

---

## M20 — Health, degradation and maintenance methods

**What it is.** Mandatory outputs (Master Brief §4.10–4.12) that are longitudinal by nature.
- **Fault-rate indicators** (EMA of alert rate): red ocean **[02 §2.10]**.
- **Residual-statistic control charts:** CUSUM/EWMA on *daily* residual mean and variance per variable as drift and noise indicators (M3).
- **Change-point trajectory:** BOCPD or CUSUM on health indicators to detect regime changes (stable → rising variance → recurring transients → persistent bias) **[02 §7.8]**.
- **Latent bias tracking:** a Kalman state for slowly varying bias. **Identifiability caveat [A]:** without an independent reference, bias cannot be separated from real climate variability; references are neighbour stations, cross-variable relationship shifts, or own climatology.
- **Time-to-threshold estimates:** extrapolate a fitted drift rate with an uncertainty interval to a tolerance limit (limits to be verified against WMO/IMD guidance **[01 §22]**).
- **Survival / RUL models:** need real failure labels, which the synthetic benchmark cannot provide.

- **Anomaly types handled:** F3, F4, F7 longitudinally and recurrence of transient faults.
- **Temporal capability:** High.
- **Multivariate capability:** Medium.
- **Labelled data:** None for statistical indicators; **real failure or maintenance records** would be needed to validate prediction, and none are known.
- **Training complexity:** Low–Medium.
- **Inference latency:** µs (daily update).
- **False-positive risks:** False maintenance alarms if a single event or a real climate shift is read as degradation (Master Brief §11.10).
- **Explainability:** High for indicators and change points.
- **Robustness:** Medium.
- **Edge feasibility:** Medium.
- **Scalability:** High.
- **Implementation difficulty:** Medium.
- **Novelty:** Health scores and predictive maintenance are red ocean **[02 §2.10, §2.12]**; change-point trajectories with evidence accumulation are a possible differentiator if statistically estimated and evaluated **[02 §7.8, §9.7]**.
- **Known weaknesses:** No real degradation ground truth; must be labelled "indication", never "guaranteed prediction" (Master Brief claims list).
- **Role:** Component (mandatory output); differentiation candidate through evidence accumulation.

---

## M21 — Heavy deep architectures (Transformers, graph networks, foundation models, diffusion/GAN detectors)

**What it is.** Anomaly Transformer/TranAD-type models, graph neural networks over station neighbourhoods, pretrained time-series foundation models, diffusion-based detectors.

- **Anomaly types handled:** Multivariate/temporal; graph models add spatial context if neighbour data exist (Met Office applied a graph network to rainfall **[02 §3.14]**).
- **Temporal / multivariate capability:** High.
- **Labelled data:** None to Low.
- **Training complexity:** High.
- **Inference latency:** ms to 100s ms.
- **False-positive risks:** High on genuine extremes unless explicitly regularised.
- **Explainability:** Low.
- **Robustness:** Low–Medium. One benchmark reports simpler methods often win **[V S1]**; industrial benchmark work reports general time-series models struggling to beat dedicated anomaly detectors **[V S3]**.
- **Edge feasibility:** Not credible.
- **Scalability:** Low–Medium (per-station models are costly to maintain **[V S3]**).
- **Implementation difficulty:** High.
- **Novelty:** Low; "GNN" is explicit red ocean **[02 Collision 11]**.
- **Known weaknesses:** Cost and opacity for three variables; multi-station data required for graph models.
- **Role:** Overengineering risk unless a specific experiment shows a measurable gain.

---

## M22 — Cross-cutting: explainability and root-cause techniques

**Explainability options** (Master Brief §4.8 makes explainability mandatory; SHAP/LIME are only *preferred*, Rule 2):

| Technique | Applies to | Cost | Faithfulness / caveat |
|---|---|---|---|
| Rule fired + threshold | M1 | trivial | Exact, but only for rules |
| Per-variable standardized residual; expected-vs-observed | M2, M9, M11 | trivial | Native, exact for the model |
| Leave-one-out conditional z | M11 | trivial | Names the odd-one-out variable |
| Per-feature reconstruction error | M7, M8 | cheap | Native, but reflects model, not physics |
| TreeSHAP | M4, M10 | low (on alert only) | Exact for tree models **[K]** |
| SHAP (Kernel/Deep) on AE/LSTM | M7, M8 | high | Costly, unstable **[K]** |
| LIME | any | medium | Local surrogate; can be unstable **[K]** |
| Hypothesis-likelihood table | M12 | low | Explains root cause, not just score |

Notes: SHAP for anomaly explanation is red ocean **[02 §2.9, Collision 5]**. Run heavy explainers on alerts only, not per sample **[A]**.

**Root-cause classification options:**
1. **Rules / fault tree** for pipeline classes and obvious signatures (patent-level prior art exists **[02 §2.11]**).
2. **Supervised classifier** (GBM, ROCKET) on synthetic labels; circularity risk (M10, M19).
3. **Bayesian hypothesis comparison** with explicit abstention (M12).
4. **Hybrid:** rules for pipeline classes; ML for waveform classes; "insufficient evidence" as a first-class label **[01 §16]**.

**Identifiability warning [A].** Some `03` classes are indistinguishable from T/P/RH alone: F12 (random value) vs F1 (large spike) overlap by magnitude; F5 (frozen) vs F6 (stuck at rail) vs F10 (duplicate, 1–2 steps) differ mainly by duration and value; F8 (NaN) vs F9 (missing row) differ by row presence. A hierarchical label set (integrity → waveform → cause) and confusion-matrix reporting will be more honest than a flat 14-way macro-F1.

---

# Comparison Matrix

**How to read.** Ratings are analyst judgements from the method blocks above, not measurements. L / M / H are relative among candidates. "—" means not applicable. Latency values are expectation classes **[H]**. M13–M18 and M22 are combination, calibration or cross-cutting layers and do not have their own rows in the fault-coverage map.

## Table A — Capability

| ID | Method | Anomaly types (F#) | Temporal | Multivariate | Labelled data needed | Explainability |
|---|---|---|---|---|---|---|
| M1 | Deterministic QC layer | F5, F6, F8–F11, F12 (range) | L–M | L | None | H |
| M2 | Robust stats / Hampel / seasonal MAD | F1, F2, F12, F3 (onset), F7 | M | L | None | H |
| M3 | EWMA / CUSUM / variance charts | F3, F4, F7, F5 (low side), F2 | H | L | None | H |
| M4 | Isolation Forest (batch) | F1, F12, contextual pts, F13 (w/ features) | L | M–H | None | M |
| M5 | Streaming trees (HST, RRCF) | Same as M4, adaptive | L–M | M | None | L–M |
| M6 | One-class / kNN / LOF | Pointwise outliers | L | M | None | L |
| M7 | Autoencoders (dense/conv/VAE) | F13, F7, F1 (large) | L–M | H | None | M |
| M8 | LSTM/GRU/TCN AE | F5, F7, F13, shape anomalies | H | H | None | L–M |
| M9 | Forecast residual (AR, Kalman, ML, TSFM) | F1, F2, F7, F13; F3/F4 only if anchored | H | M–H | None | H |
| M10 | Gradient boosting (supervised/stack) | Any injected class | M | M–H | **H** (synthetic) | M–H |
| M11 | Robust Mahalanobis / PCA / cross-variable | F13, joint F1/F12 | L (M lagged) | H | None | H |
| M12 | Probabilistic (densities, HMM, BOCPD, Bayes) | F1, F3, F4, F7, root cause | H | M | None–M | M–H |
| M19 | Shape/trajectory (MP, ROCKET, features) | F1/F12 shape, F3, F4, F5, F7 | H | M | **H** (ROCKET/features) | M |
| M20 | Health / degradation | F3, F4, F7 (longitudinal) | H | M | None (validation needs real records) | H |
| M21 | Transformers / GNN / foundation / diffusion | Multivariate, temporal | H | H | None–L | L |

## Table B — Operational

| ID | Training complexity | Inference latency | FP risk on genuine events | Robustness | Edge feasibility | Scalability | Implementation difficulty |
|---|---|---|---|---|---|---|---|
| M1 | None | µs | M–H | M | H | H | L |
| M2 | L | µs | M–H | M–H (MAD floor; window absorbs drift) | H | H | L |
| M3 | L | µs | M | M (autocorr., ARL0 tuning) | H | H | L |
| M4 | L | sub-ms | **H** | M (contamination) | M | H | L |
| M5 | None | sub-ms | **H** | M–L (self-contamination) | M | H | M |
| M6 | M–H | M | **H** | L–M | L | L–M | L |
| M7 | M | ms | **H** | L–M | M | M | M |
| M8 | M–H | ms | **H** | L–M | L–M | M | M |
| M9 | L–M | µs–ms (TSFM: 10s+ ms) | M–H | M | H (a, b) / L (TSFM) | H / L–M | L–M |
| M10 | L–M | sub-ms | Depends on training coverage | **L** (sim-to-real) | M | H | L |
| M11 | L | µs | M | M | H | H | L |
| M12 | M | µs–ms | M | M–H | M | M–H | M |
| M19 | L–M | ms | M (untested) | L–M | L | M | M |
| M20 | L–M | µs (daily) | Risk = false maintenance | M | M | H | M |
| M21 | **H** | ms–100s ms | H | L–M | ✗ | L–M | **H** |

## Table C — Novelty, weaknesses, role

| ID | Novelty (prior art) | Principal weakness | Role (candidate, not decision) |
|---|---|---|---|
| M1 | None [02 §2.1–2.3] | Rigid; misses subtle faults | **Baseline** (mandatory floor) |
| M2 | None | Univariate; MAD→0 on flats; window absorbs drift | **Baseline** |
| M3 | None | Detects any change; ARL0 vs sampling rate | **Baseline** / health input |
| M4 | None [02 Coll. 3–4] | Flags rare-but-real states; uncalibrated | **Baseline** |
| M5 | Low | Self-contamination; adapts to faults | Watch / component |
| M6 | None | Cost; rarely beats M4/M11 | Comparator only |
| M7 | None [02 §2.8] | Generalizes to anomalies; OOD extremes flagged | **Baseline** (one deep) |
| M8 | None [02 §3.6, Coll. 2] | Gain over M7/M9 unproven for 3 variables | Watch |
| M9 | Low (DLM weather QC prior art, S9) | Absorbs F3/F4, misses F5 (persistence) | **Baseline** / component |
| M10 | None [02 Coll. 6] | Learns the injector | **Baseline** (supervised ref.) / root-cause component |
| M11 | None (classical) | Gaussian/linear; regime-varying Σ | **Baseline** |
| M12 | Components none; hypothesis engine possible | Priors without real fault data | Component |
| M19 | Methods none; event-shape modelling underexplored [02 §9.5] | Needs labelled windows | Watch / experiment |
| M20 | Scores none; change-point evidence accumulation possible | No real degradation ground truth | Component / differentiation candidate |
| M21 | Low | Cost, opacity, needs multi-station data (GNN) | **Overengineering risk** |

## Table D — Fault-family coverage map

Legend: ✓ strong · ~ partial or conditional · ✗ weak or none. "Genuine-event protection" = does the method *by itself* avoid alarming on a coherent real event. Entries are expectations from the mechanism **[A]**, to be replaced by measured per-class results (Experiment E1).

| ID | Spike (F1, F2, F12) | Step bias (F3) | Drift (F4) | Frozen / stuck (F5, F6) | Noise (F7) | Pipeline (F8–F11) | Cross-variable (F13) | Genuine-event protection |
|---|---|---|---|---|---|---|---|---|
| M1 | ~ | ~ | ✗ | ✓ | ✗ | ✓ | ~ | ✗ |
| M2 | ✓ | ~ | ✗ | ~ | ~ | ✗ | ✗ | ✗ |
| M3 | ~ | ✓ | ✓ | ~ | ✓ | ✗ | ✗ | ✗ |
| M4 | ✓ | ~ | ✗ | ~ | ~ | ✗ | ~ | ✗ |
| M5 | ✓ | ~ | ✗ | ✗ | ~ | ✗ | ~ | ✗ |
| M6 | ✓ | ~ | ✗ | ✗ | ~ | ✗ | ~ | ✗ |
| M7 | ✓ | ~ | ✗ | ~ | ✓ | ✗ | ✓ | ~ |
| M8 | ✓ | ~ | ~ | ✓ | ✓ | ✗ | ✓ | ~ |
| M9 | ✓ | ~ | ~ | ✗ (persistence) / ~ (cross-var.) | ✓ | ~ (Kalman gaps) | ✓ | ~ |
| M10 | ✓ | ✓ | ~ | ✓ | ✓ | ~ | ✓ | ~ (training-dependent) |
| M11 | ✓ | ~ | ✗ | ✗ | ~ | ✗ | ✓ | ~ (coupling-aware) |
| M12 | ✓ | ✓ | ~ | ~ | ✓ | ~ | ~ | ~ |
| M19 | ~ | ~ | ~ | ✓ | ✓ | ✗ | ~ | ~ (untested) |
| M20 | ✗ | ✓ | ✓ | ~ | ✓ | ~ | ~ | ~ (needs event discount) |
| M21 | ✓ | ~ | ~ | ✓ | ✓ | ✗ | ✓ | ~ |

**Reading the map.** No single row is strong on every column. Drift (F4) is the weakest column for almost everything except sequential change detectors and health methods. The genuine-event column has no ✓ anywhere, which supports Executive Summary finding 4: genuine-event protection is an unsolved sub-problem that must be addressed by evidence design, not by picking a stronger detector. M13–M18 change how these rows are combined or calibrated; they do not add coverage.

---

# Baseline Methods

**Purpose.** A baseline ladder establishes what each layer of complexity buys, and protects against unsupported novelty or accuracy claims (Master Brief Rule 16). Only sanity baselines and cheap, well-understood methods appear here. **A baseline is not a recommendation to use it in a final system.**

## A. Good baselines

| ID | Baseline | Represents | Key knobs | Expected failure modes | Cost |
|---|---|---|---|---|---|
| **B-S0** | Random score; "always normal"; previous-value residual | Sanity floor | none | If a "real" method barely beats these under a point-adjust-free metric, the evaluation or model is suspect **[V S2]** | Trivial |
| **B-S1** | **Randomly initialized (untrained) reconstruction model** | "Does training matter?" | architecture | Kim et al. found an untrained model comparable to published methods without point-adjust **[V S2]** | Trivial |
| **B0** | Deterministic QC (M1) | Traditional threshold QC **[01 §7]** | limits, step, persistence window | Genuine fronts, subtle faults | Trivial |
| **B1** | Seasonal robust z-score (M2) | Best "no-ML" univariate contextual detector | seasonal basis, MAD floor | Fronts, drift absorption | Very low |
| **B2** | Hampel + persistence/variance rule (M2 + M1) | Spike and flatline reference | window, k | Quantization, real flat spells | Very low |
| **B3** | EWMA/CUSUM on deseasonalized residuals (M3) | Shift, drift, variance reference | k, h (ARL0 by simulation) | ARL0 vs sampling rate; real regime shifts | Low |
| **B4** | Robust Mahalanobis (± lag stack) on residual vector (M11) | Multivariate consistency reference | MCD support, lags, regime split | Regime-varying Σ | Low |
| **B5** | Isolation Forest, engineered features (M4); plus raw-value IF as straw man | Default "ML" reference | features, contamination | Genuine extremes; uncalibrated | Low |
| **B6** | One dense window autoencoder (M7) | Default "deep" reference | window, bottleneck, threshold rule | OOD extremes; generalizes to anomalies | Medium |
| **B7** | Linear/Kalman forecast residual (M9) | Temporal + seasonal reference | seasonal terms, noise model | F3/F4 absorbed, F5 missed | Low |
| **B8** | GBM on engineered features (M10), leave-one-family-out | Supervised reference | features, class weights | Circularity with injector | Low–Medium |

**Baseline protocol notes** **[A/V]**
- Report **point-adjust-free** F1, PR-AUC, event-level recall/precision, detection delay, and VUS-PR (recommended by S1). Also report point-adjusted numbers once, to show how far they inflate.
- Tune thresholds to a **false-alarm budget on clean, chronologically later data**, not to F1 on injected faults. `03`'s validation set holds simpler injections than the test set, so F1-tuned thresholds may not transfer.
- Give every baseline the **same deseasonalization** so differences reflect the detector, not the preprocessing.

## Where a baseline combination is likely to be hard to beat **[H]**

- **B4 (robust Mahalanobis on residuals)** for the mandatory multivariate-consistency requirement on modest data.
- **B3 (CUSUM/EWMA)** for small persistent shifts.
- **B1/B2** for spikes and flatlines.
Deep and supervised models should be judged on *incremental* value over the best of these, per fault class and on genuine-event false alarms.

---

# Promising Architectures

**Scope note.** These are *candidate patterns*, each betting on a different idea. They are composable rather than mutually exclusive, and **none is selected here**. Each lists what it bets on, what it covers, its main risk, and the experiment that would discriminate (see *Recommended Experiments*). Requirement references are to the Master Brief.

## A1 — Layered evidence pipeline (calibrated fusion with abstention)

```text
Raw record (immutable)
   │
   ▼
[Integrity layer M1]  align · de-dup · order · range · persistence flags
   │
   ▼
[Baseline + residuals M2/M9]  seasonal expectation, standardized residuals (NaN-tolerant)
   │
   ├─► temporal evidence   (M3 CUSUM/EWMA, robust z)
   ├─► multivariate evidence (M11 Mahalanobis / leave-one-out z)
   ├─► learned evidence    (M4 / M7, optional)
   └─► shape evidence      (M19 features: spike-recover, step, ramp, flat)
   │
   ▼
[Calibration M16]  each evidence stream → p-value / calibrated score
   │
   ▼
[Fusion + conflict measure M13]  dependence-aware combination; disagreement flagged
   │
   ▼
[Hypothesis layer M12/M10]  normal · suspect · fault-type · genuine event · insufficient evidence
   │
   ├─► severity (rule-based: magnitude × duration × variable criticality)
   ├─► explanation (M22, on alert only)
   └─► health / degradation / maintenance (M20)
```

- **Bets on:** independent-ish evidence streams, calibrated to a common scale, reduce genuine-event false alarms without losing recall.
- **Covers:** temporal, seasonal, multivariate (§4.3–4.5); event-vs-anomaly (§4.6); confidence vs severity (§4.7, §11.9); explainability (§4.8); root cause (§4.9); health (§4.10–4.12).
- **Main risk:** fusion becomes arbitrary voting; complexity; evidence streams correlated, so fusion gains are small; calibration data must be clean.
- **Falsifier:** an ablation showing the fused system does not beat the best single stream on false-alarm rate at matched recall on the genuine-event set (E2, E10).

## A2 — State-space backbone (Kalman/DLM innovations + conformal + change detection)

```text
Raw record → Kalman/DLM (level + seasonal + cross-variable terms)
              │  (missing obs: predict-only step)
              ▼
        standardized innovations
              │
   ┌──────────┼─────────────┐
   ▼          ▼             ▼
 conformal   CUSUM / BOCPD  Mahalanobis on
 thresholds  on innovations innovation vector
 (Mondrian/  → shift, drift → cross-variable
  ACI)         health         consistency
```

- **Bets on:** one probabilistic model supplies residuals, missing-data handling, uncertainty and drift detection; ML sits on top only where needed (for example root cause). Prior art shows the Kalman/DLM route for weather sensor QC is workable **[V S9]**.
- **Covers:** streaming, gaps and out-of-order handling (§3.4), temporal/seasonal, explainable residuals, edge-plausible core.
- **Main risk:** linear-Gaussian assumptions; innovations *absorb* bias and drift unless the model is anchored to a slow baseline **[A]**; weak on flatline and genuine events unless supplemented.
- **Falsifier:** E1 (per-class coverage) and E8 (drift detectability) show it misses drift or flatline that a simple add-on rule fixes, making the "one model" advantage moot.

## A3 — Shape-feature hypothesis classifier with abstention

```text
Detector-agnostic candidate window (from cheap triggers)
   │
   ▼
Shape + coupling features (slope, recovery ratio, run length, variance ratio,
                           cross-variable lag correlation, Mahalanobis, dew-point residual)
   │
   ▼
Supervised classifier (GBM / ROCKET), trained with leave-one-family-out design
   │
   ▼
Calibrated posterior → conformal prediction set (may contain several causes)
   │
   ├─ single cause  → report with confidence
   ├─ several causes → "ambiguous" + candidates
   └─ empty / low    → "insufficient evidence / human review"
```

- **Bets on:** root cause and event-vs-fault are better learned from trajectory shape and coupling features than from a scalar anomaly score. Set-valued conformal outputs can contain more than one label, which represents uncertainty directly **[V S8]**.
- **Covers:** root-cause classification (§4.9), uncertainty routing **[01 §16]**, explainability via features.
- **Main risk:** circularity with the injector **[V S15; A]**; genuine-event class needs real or realistic examples; class identifiability (see M22 warning).
- **Falsifier:** E5 (train on injector family A, test on family B with different shapes and overlapping faults) shows a large accuracy drop.

## A4 — Edge–server split

```text
EDGE (ESP32-class): M1 rules + M2 robust stats + M3 CUSUM (+ optional tiny model)
   emits: raw value + integrity flags + sufficient statistics + local flags   (raw preserved)
        │
        ▼  (telemetry)
SERVER: M11 / M9 / M4 or M7 / fusion / shape features / explanation / health / network context
```

- **Bets on:** a cheap, robust edge layer catches most gross faults and pipeline issues; server-side context handles ambiguity, so on-device compute stays tiny (`01` §18 anticipates this split).
- **Covers:** energy/edge criterion, scalability, practical deployment (§4.13–4.14, §9.11).
- **Main risk:** two code paths to keep consistent; edge claims require hardware measurement (claims list); edge flags may cause double-counting on the server.
- **Falsifier:** E11 shows the edge layer's recall or false-alarm rate is too far from the full pipeline to justify the split, or that measured resource use is not credibly low.

## A5 — Contamination-resistant adaptive baseline

```text
Trusted reference baseline (frozen, versioned)  ◄── rollback
        │
        ├── divergence measured ──► drift-vs-regime signal
        ▼
Adaptive baseline (updates only from non-quarantined data)
        ▲
Quarantine buffer ◄── suspect points excluded from updates
        │
Censoring-aware variance estimation (corrects truncation from gating)
```

- **Bets on:** preventing self-poisoning, and using disagreement between frozen and adaptive baselines as evidence, makes drift and regime shifts distinguishable **[02 §7.3, §9.3]**.
- **Covers:** seasonal and regime adaptation (§4.4) without silently absorbing degradation (§11.10).
- **Main risk:** the censored-sampling loop described in M14; added state and rollback logic; needs long histories to establish a trusted reference.
- **Falsifier:** E3 shows the gated baseline is no better than a periodically retrained frozen baseline on detection delay and false-alarm creep.

## A6 — Competing-hypothesis likelihood engine ("analysis by synthesis")

```text
Candidate window
   │
   ├─ H0 normal (seasonal + noise model)
   ├─ H1 spike-and-recover      ├─ H5 noise burst
   ├─ H2 step bias              ├─ H6 coherent T/RH/P event (physical coupling)
   ├─ H3 linear/exponential ramp├─ H7 pipeline artifact (gap / duplicate / stale)
   └─ H4 flat / stuck           
   │
   ▼
Penalized marginal likelihood per hypothesis → posterior → abstain if none dominates
```

- **Bets on:** explicit generative hypotheses are interpretable, need few labels, and generalize to unseen combinations through model comparison; the counterfactual question "what would we expect if H were true?" is answered directly **[02 §7.5]**.
- **Covers:** root cause with uncertainty (§11.7), explainability via hypothesis table.
- **Main risk:** hypothesis families may be written from the same formulas as `03`'s injector, so scoring well on `03` data is circular; misspecification; abstention calibration.
- **Falsifier:** E5/E6 with an independently written injector containing out-of-family shapes (for example smooth spikes, saturating drift, intermittent freezes).

## Design questions common to every architecture

1. **Where does genuine-event evidence come from?** Options: cross-variable coherence (M11), trajectory shape (M19), hypothesis H6 (A6), network context (needs multi-station data; spatial evidence is allowed as context but must not redefine the three-variable input set, Master Brief §11.11).
2. **What exactly does "confidence" mean?** Candidates: conformal p-value (alarm-rate interpretation), calibrated posterior of the reported hypothesis, or both, reported separately (Master Brief §11.8).
3. **How is severity defined independently of confidence?** Rule-based impact (magnitude × duration × variable criticality) is easiest to justify; must not be conflated with confidence (Master Brief §11.9).
4. **How are gaps handled?** Native (Kalman) vs impute-then-detect (AE, IF); the choice interacts with F8/F9 detection.
5. **Where is explanation computed?** On alert only, not per sample.

---

# Overengineering Risks

The following are likely to add cost, opacity or maintenance burden without proportionate value for a **three-variable, real-time, explainable, network-scalable** problem. "Probably" reflects judgement from cited evidence and the mechanisms above, not measurement; each has a condition under which it would be justified.

| Approach | Why it is probably overengineered here | Supporting evidence | Justified only if |
|---|---|---|---|
| **Transformer / TranAD-type detectors** | Three variables give little for attention to exploit; opaque; heavy | Simpler methods often win on a large benchmark **[V S1]** | E1 shows a measurable per-class gain over M7/M9 |
| **Pretrained forecasting foundation models** as the core residual generator | Latency, size, no edge path; unclear gain on 3 variables | Foundation models looked strongest on point anomalies only **[V S1]**; used with conformal wrapper in one recent paper **[V S6]** | Compared against B7 at matched latency and a clear win on genuine-event FP |
| **Graph neural networks over stations** | Needs a synchronized multi-station archive that may not exist; TITAN already covers spatial QC operationally | GNN is red ocean **[02 Coll. 11]**; TITAN **[02 §3.1]** | The dataset has many neighbouring stations and E16 shows gain over kNN-style spatial checks |
| **Diffusion / GAN anomaly detectors** | Heavy training; hard to explain; no evidence of benefit on 3 variables | None found this session | Never, for this scope, without a specific hypothesis |
| **LSTM-AE for flatline detection** | A rolling variance / run-length rule is the obvious comparator | Published LSTM-AE flatline work exists **[02 §3.6]**; its margin over a simple rule is not established in the files | A rule-based flatline detector is shown to fail on resolution-quantized or legitimately flat data |
| **Deep ensembles / Bayesian NNs for uncertainty** | Conformal and quantile calibration give calibrated scores at far lower cost | M16 vs M15 | Calibration on residual scores demonstrably fails |
| **Per-station deep models at network scale** | Maintenance cost of thousands of models | Per-series models named an unaffordable-maintenance obstacle **[V S3]** | A shared model with station scaling fails on cold-start stations |
| **Survival / RUL models** | No real failure labels to fit or validate; would invite "guaranteed failure prediction" claims | Master Brief claims list | Real maintenance records become available |
| **On-device neural training or large on-device models** | ESP32 memory (~520 KB SRAM) and energy; not verified | **[V S17]** | A measured prototype fits memory and latency |
| **"Ensemble of everything" plus SHAP on every member** | Correlated members, explanation cost, latency | M13 | Ablation shows each member adds gain |
| **A flat 14-class classifier** | Several classes are not identifiable from T/P/RH (M22 warning); macro-F1 will be capped | `03` taxonomy | A hierarchical label set is adopted and confusion structure reported |
| **RL-tuned thresholds / learned severity policies** | No reward signal or operational cost data | `02` §9.1 notes cost weights are missing | Operational cost ratios are known |
| **Complex causal graphs without data** | Cannot be fitted or validated from the available synthetic benchmark | — | Real multi-station fault records exist |

**Complexity that is *not* overengineering here:** the integrity layer, seasonal baselining, robust Mahalanobis, CUSUM/EWMA, and calibrated thresholds. They address mandatory requirements and are cheap.

---

# Potential Differentiation

**Ground rules.** `02` §8–§12 establishes that algorithms, hybrids, SHAP, health scores, dashboards, GNNs, Kalman filters, fault injection and ESP32 deployment are red ocean. **Nothing below is claimed novel.** Each item is a direction that maps to a `02` differentiation target, with (i) the method mechanism, (ii) what would be measured, and (iii) prior-art status as far as this session could tell. A direction becomes a novelty claim only after passing the `02` §11 tests (feature, algorithm, architecture, behaviour-level, evidence-level, benchmark-level).

## D1 — Contamination-resistant adaptive baseline with censoring-aware estimation *(02 Target 1)*
- **Mechanism:** trusted frozen reference + adaptive baseline + quarantine + rollback (A5); estimate baseline variance with a truncated/censored likelihood so gating does not shrink it (M14).
- **Measure:** deviation of baseline parameters from an oracle baseline fitted on truly clean data; detection delay for slow drift injected during the adaptation stream; false-alarm creep over months; comparison across frozen, naive online, gated, and dual-baseline.
- **Prior art:** contamination-robust anomaly detection is a studied area **[V S14]**; monitoring guarantees are known to break when the monitor modifies the learner **[V S5]**; a gated, weather-station-specific baseline was not found in this session's searches (**unverified**).
- **Effort / risk:** Medium / Medium (gate design; needs long simulated histories).

## D2 — Calibrated multi-evidence fusion with abstention *(02 Target 3; §7.1, §9.1–9.2)*
- **Mechanism:** per-stream conformal p-values (Mondrian by hour-of-day and season, ACI or weighted for drift), dependence-robust combination, an explicit conflict measure, and abstention thresholds set from operational cost ratios (M13, M16).
- **Measure:** risk–coverage curves; harmful false alarms on the genuine-event set at fixed recall; Brier score and reliability diagrams (alongside ECE); coverage drift by season and hour.
- **Prior art:** conformal anomaly detection, martingale monitoring and time-series conformal variants exist **[V S4–S6]**. One targeted search did not surface conformal calibration applied to AWS QC; **not evidence of absence**.
- **Effort / risk:** Medium / Medium (dependence between streams; exchangeability violations).

## D3 — Competing-hypothesis diagnosis with shape likelihoods *(02 Target 3; §7.5, §9.5)*
- **Mechanism:** A6, or A3 with set-valued output.
- **Measure:** accuracy on **out-of-family** fault shapes; abstention quality; explanation fidelity (does the hypothesis table point at the true fault?).
- **Prior art:** fault trees, decision trees and root-cause labels exist **[02 §2.11]**; a calibrated, abstaining hypothesis comparison on weather T/P/RH was not found (**unverified**).
- **Effort / risk:** Medium–High / High (circularity with the injector).

## D4 — Health change-point trajectory with evidence accumulation *(02 Target 6; §7.8, §9.7)*
- **Mechanism:** CUSUM/BOCPD on daily residual mean and variance plus recurrence of transient faults; maintenance indication only when accumulated evidence passes a calibrated level; single events and real climate anomalies are discounted (M3, M12, M20).
- **Measure:** detection delay against **false maintenance alarms per station-year**; behaviour during a genuine anomalous month (for example a long heat spell) as a negative control.
- **Prior art:** health scores and predictive maintenance are red ocean **[02 §2.10, §2.12]**; statistically estimated regime-change trajectories are named as a possible gap.
- **Effort / risk:** Medium / Medium (no real degradation ground truth; must be labelled an indication, not a prediction).

## D5 — Coupling-aware genuine-event protection using physics as a soft residual *(02 §7.7)*
- **Mechanism:** learn the conditional distribution of a derived quantity (dew point or vapour pressure, labelled as derived) given T, P and season by quantile regression; calibrate with conformal; combine with Mahalanobis coherence (M11, M16).
- **Measure:** false alarms on coherent events; F13 detection at graded magnitudes versus pure statistical baselines; abstention rate when physics is not decisive.
- **Prior art:** thermodynamic consistency checks are established **[02 §2.4]**; the differentiator would be the calibrated, learned soft residual, not the formula **[02 §7.7]**.
- **Effort / risk:** Low–Medium / Medium (the relationship may be non-decisive; abstain when so).

## D6 — Shared-cause discrimination across stations *(02 Target 2; §7.4, §9.4, §9.9)*
- **Mechanism:** cluster anomaly onsets across stations; test propagation-lag plausibility for weather versus simultaneous onset for a shared infrastructure fault.
- **Measure:** separation of a propagating front from a synchronized comm/firmware fault in multi-station injections.
- **Prior art:** spatial QC is mature (TITAN **[02 §3.1]**); shared-cause attribution is named underexplored.
- **Effort / risk:** High / High. **Conditional on a synchronized multi-station archive**, which is unknown. Location metadata is allowed as context, but the three-variable input set must not be redefined (Master Brief §11.11).

## D7 — Empirically learned sensor-response envelope *(02 §7.6)*
- **Mechanism:** learn per-station, per-regime distributions of one-step change and flag implausibly fast changes, conformally calibrated.
- **Measure:** detection of impulsive faults that stay within absolute limits; false alarms on real fronts.
- **Prior art:** step checks are red ocean; the physical-response prior needs validation against actual sensor specs **[01 §13]**.
- **Effort / risk:** Low / Low–Medium (reporting-interval averaging may mask response time).

## D8 — Reproducible, realistic benchmark and evaluation protocol *(02 Target 7; §7.10)*
- **Mechanism:** independent injector families, overlapping and intermittent faults, saturating drift, pipeline disorder, genuine-event surrogates expressed in T/P/RH only, hold-out injector families, point-adjust-free metrics, VUS-PR, detection delay and false-maintenance rate.
- **Measure:** whether method rankings persist across injector families (a ranking that flips across families signals injector overfitting).
- **Prior art:** fault injection is common **[02 §2.14]**; learned and diverse anomaly generators exist **[V S16]**; the differentiator is the protocol and its honesty about circularity.
- **Effort / risk:** Medium / Low. Arguably the most defensible contribution, because the Master Brief already requires a documented injection methodology (§11.12).

## D9 — Immutable decision ledger *(02 §9.10)*
- **Mechanism:** store raw value, evidence streams, model/baseline versions, rules fired, and quarantine decisions per alert. Engineering rather than ML.
- **Measure:** ability to reconstruct any decision after the fact.
- **Effort / risk:** Low–Medium / Low.

## D10 — Uncertainty-gated correction *(02 Target 5; §9.6)* — **optional feature**
- **Mechanism:** provide an estimate only with an interval, evidence source and reason; refuse when uncertainty is high; raw value always preserved (Master Brief §11.13).
- **Note:** correction is optional (Master Brief §5.9, Rule 3); do not let it displace mandatory work.

## Investigation priority (not a selection)

| Priority | Directions | Reason |
|---|---|---|
| **High** | D8, D2, D1, D5 | Measurable with synthetic data plus a clean archive; directly tied to false-alarm control and genuine-event protection |
| **Medium** | D4, D3, D7 | Valuable but depend on injector realism or lack real ground truth |
| **Conditional** | D6 (data), D9 (engineering), D10 (optional) | Depend on data availability or are outside the mandatory core |

---

# Recommended Experiments

**Purpose.** Decide *between* candidates using evidence. Each experiment states what result would change which candidate's status. All are proposals; none has been run. "Re-scoped benchmark" means `03`'s benchmark restricted to T/P/RH (Executive Summary §0.1).

| Priority | Experiments |
|---|---|
| **P0** | E0, E1, E2, E5 |
| **P1** | E3, E4, E6, E7, E8, E9, E12 |
| **P2** | E10, E11, E13, E14, E15, E16 |

## E0 — Metric sanity and inflation check
- **Question:** How much do evaluation choices alone move the ranking?
- **Setup:** Score B-S0 (random, always-normal, previous-value) and B-S1 (untrained AE) alongside B0–B6, with and without point adjustment.
- **Metrics:** point-adjust-free F1, PR-AUC, VUS-PR, event recall/precision; point-adjusted F1 once for contrast.
- **Decision use:** if random or untrained baselines look competitive under any reported metric, that metric is unfit for ranking **[V S2]**.

## E1 — Baseline ladder, per fault class
- **Question:** What does each layer of complexity buy on each fault family?
- **Setup:** B0–B8 on the re-scoped benchmark; identical deseasonalization; thresholds set to a fixed false-alarm budget on clean, chronologically later data.
- **Metrics:** per-class detection metrics; detection delay for F3/F4; false-alarm rate on clean data; runtime.
- **Decision use:** replaces Table D's expected ✓/~/✗ with measured values; demotes any deep or supervised method that does not beat the best cheap baseline on a class it is meant to handle.

## E2 — Genuine-event false-alarm stress
- **Question:** Which detectors and evidence types alarm on coherent real events?
- **Setup:** build a T/P/RH-only genuine-event set from the clean archive using selection criteria **independent of the detectors' features** (for example externally defined pressure-tendency thresholds; verify definitions) and, if available, weather-service event logs; hold it out chronologically; ablate coupling features (M11, D5).
- **Metrics:** false-alarm rate on events per detector; recall on injected faults at the same threshold; effect of coupling features.
- **Caveats:** eclipse cannot be tested; squalls only via T/RH/P signature. Events selected by a criterion that resembles a detector's features can flatter it, so document the criterion and test with alternatives.
- **Decision use:** central test for Master Brief §4.6/§9.5; informs whether A1's fusion or A3's shape evidence is worth its complexity.

## E3 — Baseline-poisoning test
- **Question:** Do adaptive baselines learn faults as normal, and does gating fix it without a censoring bias?
- **Setup:** inject 30/60/90-day drifts and biases into the adaptation stream; compare frozen, naive online, gated, dual-baseline (A5), and periodic retrain from a frozen reference.
- **Metrics:** baseline-parameter deviation from oracle; drift detection delay; false-alarm creep over time; estimated variance versus true variance (censoring check).
- **Decision use:** promotes or demotes D1/A5.

## E4 — Conformal calibration under temporal dependence
- **Question:** Is the nominal alarm rate achieved across hours, seasons and regimes?
- **Setup:** chronological calibration/test; split conformal versus Mondrian (hour × season), ACI, weighted conformal; also with contaminated calibration sets (for example 1% and 5% faults).
- **Metrics:** empirical alarm rate versus nominal by group; coverage drift; miss rate impact of contamination.
- **Decision use:** decides whether M16 is a calibration layer worth adopting and which variant; supports precise wording ("approximate under temporal dependence") **[V S5–S7]**.

## E5 — Cross-injector generalization (circularity test)
- **Question:** Do supervised classifiers learn faults or the injector?
- **Setup:** train B8/M19 on injector family A; test on an **independently implemented** family B (different shapes and parameter ranges, overlapping and intermittent faults); also leave-one-fault-class-out for "unseen fault" behaviour.
- **Metrics:** macro-F1 drop A→B; abstention rate on unseen classes; rank stability of methods.
- **Decision use:** if accuracy collapses, supervised root-cause claims need heavy qualification, and A6/A3-with-abstention gain relative value **[V S15]**.

## E6 — Root-cause identifiability
- **Question:** Which of `03`'s 14 classes are separable from T/P/RH?
- **Setup:** oracle-feature classifier upper bound; confusion matrix; merge classes hierarchically (integrity → waveform → cause).
- **Metrics:** confusion structure; performance by hierarchy level.
- **Decision use:** fixes the label set and the honest macro-F1 ceiling (M22 warning).

## E7 — Frozen-sensor detection under quantization and legitimate flats
- **Question:** Can flatline rules be resolution-aware without alarming on real flat spells?
- **Setup:** vary sensor resolution; include RH near 100% (fog) and stable pressure; compare run-length rules, variance charts, cross-variable checks and AE.
- **Metrics:** detection delay; false-alarm rate on legitimate flats; benefit of using the other two variables (one frozen vs all frozen).
- **Decision use:** tests whether ML adds anything for F5 beyond rules.

## E8 — Drift detectability limits
- **Question:** How fast can drift be detected, and what limits it?
- **Setup:** drift slopes covering `03`'s 0.01–0.1σ/day range; single-station versus with a reference (cross-variable, or neighbours if available); CUSUM, EWMA, BOCPD, Kalman bias; negative control with a genuine long warm or cold spell.
- **Metrics:** detection delay versus slope; false drift alarms on the negative control.
- **Decision use:** defines what "degradation prediction" can honestly claim from three variables at one station.

## E9 — Multivariate consistency
- **Question:** Which method best catches T–RH–P decoupling without alarming on coherent moves?
- **Setup:** decoupling injections re-expressed in T/P/RH at graded magnitudes; global versus regime-conditional Σ; Mahalanobis, leave-one-out z, cross-variable regression, AE, IF.
- **Metrics:** detection at each magnitude; false alarms on coherent events; attribution correctness (which variable).
- **Decision use:** selects the multivariate layer without adding a deep model unless it earns it.

## E10 — Fusion and abstention comparison
- **Question:** Does calibrated fusion beat the best single stream?
- **Setup:** max, mean-rank, dependence-robust p-value combination, logistic stacking, naive-Bayes posterior; add a conflict measure and abstention.
- **Metrics:** risk–coverage; FPR on genuine events at matched recall; Brier/ECE.
- **Decision use:** validates or kills A1's fusion.

## E11 — Latency, throughput, footprint and edge measurement
- **Question:** What do the candidates actually cost?
- **Setup:** per-sample latency (p50, p99) on server CPU; vectorized multi-stream throughput at several network sizes; ESP32 build of edge-candidate components measuring flash, RAM, cycle time and, if instrumented, current draw.
- **Metrics:** latency distribution; throughput per core; memory; energy per sample if measured.
- **Decision use:** Master Brief Rules 12 and 16 and §9.11; edge and energy claims are allowed only with these numbers. If energy is not measured, say so.

## E12 — Missing data and stream disorder
- **Question:** How do methods behave after gaps, duplicates and out-of-order arrivals?
- **Setup:** NaN bursts of varying length (F8/F9), duplicates, delays; Kalman versus windowed versus AE-with-imputation.
- **Metrics:** detection quality; false alarms in the window after a gap resumes.
- **Decision use:** tests the Kalman-native-gap advantage (A2).

## E13 — Leakage audit
- **Question:** Is the evaluation clean?
- **Setup:** chronological splits, threshold and calibration on validation only, shuffled-label control, check station/time features for leakage.
- **Decision use:** guards `03`'s temporal and spatial leakage risks.

## E14 — Cold start and seasonal data requirement
- **Question:** How much history does seasonal learning need, and what happens at a new station?
- **Setup:** vary training length (months to years); climatology-prior or shared-model initialization for a new station.
- **Metrics:** false-alarm rate and detection versus history length.
- **Decision use:** sets minimum data requirements; cold start is a named deployment obstacle **[V S3]**.

## E15 — Explanation fidelity
- **Question:** Do explanations point at the right variable and stay stable?
- **Setup:** compare native residual attribution, leave-one-out z, TreeSHAP, SHAP on AE, and LIME against injected-variable ground truth; measure cost per explanation and stability across adjacent windows.
- **Metrics:** top-1 attribution accuracy; stability; cost.
- **Decision use:** decides whether SHAP/LIME (preferred, not mandatory) add value beyond native attribution.

## E16 — Spatial-context value *(conditional on multi-station data)*
- **Question:** Does neighbour evidence improve genuine-event protection and drift detection?
- **Setup:** add elevation-aware neighbour comparison to the best single-station pipeline; include shared-cause injections versus propagating fronts.
- **Metrics:** change in genuine-event false alarms, drift delay, shared-cause discrimination.
- **Decision use:** decides whether D6 and any graph-based method are warranted.

---

# Unknowns

## A. Data and setting
1. **Dataset identity, sampling interval, length and station count.** No file fixes these. Seasonal learning, ARL0 design, cold-start behaviour and edge cost all depend on them (Master Brief §3.4 requires these assumptions to be explicit).
2. **Whether a synchronized multi-station archive exists.** Determines whether spatial evidence, shared-cause diagnosis (D6) and graph methods are even testable.
3. **Sensor resolution and specifications** (quantization, response time, accuracy class). Needed for resolution-aware flatline rules and any sensor-response prior **[01 §13, §22]**.
4. **Whether any real labelled faults or maintenance records exist.** Without them, degradation and maintenance claims cannot be validated, and the sim-to-real gap cannot be measured.
5. **How clean the "clean" archive really is.** `03` itself notes latent faults may be present; this affects baselines, calibration sets and the genuine-event set.
6. **Timestamp quality** (time zone, clock drift, DST), which interacts with delayed/out-of-order faults.

## B. Scope and interpretation
7. **Out-of-scope variables in `03`.** Whether the benchmark owner will re-scope to T/P/RH or propose an explicitly labelled non-core extension (Master Brief §9.2). This report assumes re-scope.
8. **"AI/ML-based" reading** of statistical, state-space and control-chart methods (Master Brief §10.1) when they carry much of the detection.
9. **How much judges will weigh SHAP/LIME versus native explanations.** SHAP/LIME are *preferred*, not mandatory (Master Brief §6.1, Rule 2).
10. **Operational cost ratio** of a false alarm versus a missed fault, and human-review capacity. Needed for abstention thresholds and any decision-theoretic design; not present in any file (`02` §9.1 makes the same point).
11. **Acceptable false-alarm budget** per station per year and the real-time latency/throughput target (`01` §17.4 mentions potentially sub-second central latency, but no throughput target exists).

## C. Method-level open questions (all testable)
12. Do the cheap baselines (B1–B4) already saturate an injected benchmark, leaving no measurable room for ML? (E1)
13. How far do synthetic faults represent real ones, and how strongly do supervised methods overfit the injector? (E5)
14. Can genuine events be represented adequately using T/P/RH alone, given that eclipse and wind-defined events are out of scope? (E2)
15. How well does conformal calibration hold under dependence, seasonality and contaminated calibration data in this domain? (E4)
16. What is the real detection limit for slow drift at a single station with three variables? (E8)
17. How large is the censoring bias of self-gated baselines? (E3)
18. Do shape and coupling features actually separate coherent events from faults? (E2, E5, E9)
19. Does an anchored Kalman/DLM close its F3/F4/F5 blind spots without extra rules? (E1, E8)
20. How much of the fusion gain in A1 survives ablation? (E10)

## D. Edge and deployment
21. **Usable RAM, flash and energy on the actual logger.** Generic ESP32 lists ~520 KB SRAM **[V S17]**, but application-available memory and energy per inference are unverified. Edge and energy claims require a build and a measurement (Master Brief §9.11).
22. **Firmware constraints** (fixed-point maths, no dynamic allocation) affecting which components port cleanly.

## E. Prior-art and novelty checks still pending
23. Whether conformal calibration on AWS QC, gated/quarantined station baselines, and calibrated hypothesis-abstention on weather T/P/RH exist in the literature. This session ran a small number of targeted searches, found none, and treats that as inconclusive. A systematic prior-art check per `02` §11 is required before any novelty wording.
24. Library and model versions (for example current time-series foundation models) were not checked and may have changed.

## F. Limits of this research
- **Search breadth.** About fifteen targeted searches; mostly abstracts and snippets. Full papers were not read. Several results are recent preprints and self-reported.
- **Evidence grade.** Blog and repository sources (S11, S13, S17, S18) are weak evidence and were used only for orientation or resource budgets.
- **Textbook items marked [K]** were not re-verified this session.
- **Ratings** in the matrices are judgements; no experiment was run.

## Source list (verified this session)

| ID | Source | URL | Grade* |
|---|---|---|---|
| S1 | Liu & Paparrizos, "The Elephant in the Room: Towards A Reliable Time-Series Anomaly Detection Benchmark" (TSB-AD), NeurIPS 2024 Datasets & Benchmarks | https://nips.cc/virtual/2024/poster/97690 ; https://pypi.org/project/TSB-AD/ | A |
| S2 | Kim et al., "Towards a Rigorous Evaluation of Time-Series Anomaly Detection", AAAI 2022 | https://ojs.aaai.org/index.php/AAAI/article/view/20680 ; https://arxiv.org/pdf/2109.05257 | A |
| S3 | TimeSeriesBench: an industrial-grade benchmark for TSAD | https://arxiv.org/pdf/2402.10802 | B |
| S4 | "Conformal Anomaly Detection in Python: … with nonconform" (conformal martingales, Ville threshold) | https://arxiv.org/pdf/2605.13642 | B |
| S5 | Han & Qu, "When the Martingale Never Stops Firing: Anytime-Valid Gating on Real Forecast Streams" | https://arxiv.org/pdf/2608.30502 | B |
| S6 | Martinez Gil et al., "Adaptive Conformal Anomaly Detection with Time Series Foundation Models for Signal Monitoring", ICLR 2026 | https://arxiv.org/pdf/2604.20122 ; https://openreview.net/pdf/169ecffbad3490cb14471f160d2649e3fba477e8.pdf | A/B |
| S7 | Fault detection and diagnosis with temporal convolutional autoencoder and calibrated classifiers (conformal section: guarantees are marginal) | https://arxiv.org/pdf/2507.13022 | B |
| S8 | Localized anomaly detection via differentiable D-vine copulas (conformal background, Mondrian, set-valued outputs) | https://arxiv.org/pdf/2607.25020 | B |
| S9 | "Quality Control in Weather Monitoring with Dynamic Linear Models" | https://arxiv.org/pdf/2211.04528 | B |
| S10 | Guha et al., "Robust Random Cut Forest Based Anomaly Detection on Streams" (abstract) | https://astro.paperswithcode.com/paper/robust-random-cut-forest-based-anomaly | A (abstract only) |
| S11 | River online-learning library, feature list (seen in mirrors/forks) | https://github.com/ogozuacik/river | C |
| S12 | Online changepoint detection: BOCPD description; "on a budget"; CUSUM/EWMA in quality control | https://arxiv.org/pdf/2305.11976 ; https://arxiv.org/pdf/2201.03710 ; https://arxiv.org/pdf/2305.06630 | B |
| S13 | MetricGate, "CUSUM vs EWMA: Change Detection Compared" (April 2026, blog) | https://metricgate.com/blogs/cusum-vs-ewma-change-detection/ | C |
| S14 | Training-data contamination in unsupervised anomaly detection: inaccurate contamination ratio; Deep Isolation Forest robustness study; PHM evaluation of contamination-mitigating techniques | https://arxiv.org/pdf/2408.07718 ; https://arxiv.org/pdf/2206.06602 ; https://papers.phmsociety.org/index.php/phme/article/view/4880 | B |
| S15 | "Neural Contextual Anomaly Detection for Time Series" (generalization from injected anomalies) | https://arxiv.org/pdf/2107.07702 | B |
| S16 | GenIAS: Generator for Instantiating Anomalies in Time Series | https://arxiv.org/pdf/2502.08262 | B |
| S17 | ESP32 and microcontroller ML resources: OTA-TinyML board table (ESP32 520 KB SRAM); esp32-ai (ESP32-S3 512 KB); TI tinyml-tensorlab (autoencoder anomaly flows) | https://www.github.com/bharathsudharsan/OTA-TinyML ; https://github.com/slvDev/esp32-ai ; https://github.com/texasinstruments/tinyml-tensorlab | C |
| S18 | TinyML papers and projects list (includes FastGRNN) | https://www.github.com/gigwegbe/tinyml-papers-and-projects | C |

*Grade: A = peer-reviewed venue; B = preprint or technical report; C = repository, documentation or blog.

---

# HANDOFF TO NEXT AGENT

**Agent 05 (ARCHITECTURE & IDEA DESIGN)** — please consume this document together with `00`–`03`.

## What this document gives you

1. A **method inventory (M1–M22)** with per-method assessment of anomaly types, temporal and multivariate capability, label needs, cost, latency, false-positive risk, explainability, robustness, edge feasibility, scalability, difficulty, novelty and weaknesses.
2. A **fault-family coverage map** (Table D) showing that no single method is strong across fault families and that **genuine-event protection is unsolved by any detector on its own**.
3. A **baseline ladder** (B-S0…B8) that any proposed component must beat, per fault class.
4. **Six composable candidate architectures** (A1–A6) with explicit falsifiers.
5. A list of **overengineering risks** and **differentiation directions (D1–D10)** tied to `02` targets, none claimed novel.
6. **Seventeen experiments (E0–E16)** with decision rules.

## What you must preserve (Master Brief)

- Core inputs **only** Temperature, Pressure, Relative Humidity; timestamp, station ID, location, elevation as metadata; derived features labelled as derived.
- Real-time operation; temporal + seasonal + multivariate analysis; genuine-event vs anomaly distinction; confidence ≠ severity; root cause with uncertainty; sensor health; degradation and maintenance as *indications*; raw data immutability; explainability; scalability and practical deployment; dashboard; executable code, example usage, use-case documentation.
- Correction/imputation is **optional**. SHAP/LIME and ESP32 are **suggested**.

## Decisions this document deliberately does not make

1. Which detectors, if any, are adopted beyond the baselines.
2. Where genuine-event evidence comes from (coupling, shape, hypothesis comparison, network context).
3. What "confidence" is (conformal p-value, calibrated posterior, or both, reported separately).
4. Edge/server split, and whether any edge claim will be backed by hardware measurement.
5. Which differentiation directions to pursue, and whether any survive `02` §11.
6. Whether to use spatial evidence (depends on data availability).

## Suggested gates for whatever you design

- **Beat the baselines per class (E1).** A component that does not beat the best cheap baseline on the class it targets should not stay in the design.
- **Calibrate the alarm rate on clean, later data**, not F1 on injections.
- **Evaluate supervised parts with independent injector families (E5)**, and report both the in-family and cross-family results.
- **No novelty wording** without a specific prior-art comparison and behaviour-level difference (`02` §11 and the Master Brief claims list).
- **No edge, energy, latency or scalability claims** without measurements (E11).
- **Conformal wording:** "approximately calibrated under temporal dependence," never "guaranteed."

## Issues to resolve with other owners

- **Agent 03 / benchmark owner:** re-scope the taxonomy and genuine-event set to T/P/RH; separate optional imputation metrics from mandatory detection metrics; specify point-adjust-free evaluation; consider hierarchical root-cause labels; add an independent second injector family.
- **Master Brief owner:** confirm treatment of derived features and of "AI/ML-based" for statistical components.

## Master Brief handoff checklist

| Item | Status in this document |
|---|---|
| Temperature, Pressure, Relative Humidity | Preserved; `03`'s out-of-scope variables flagged |
| Real-time anomaly detection | Preserved; latency classes are expectations pending E11 |
| Spikes, frozen/stuck, communication errors, sensor faults | Covered (M1, M2, M3, M9, M11; Table D) |
| Temporal and seasonal patterns | Covered (seasonal baselines M2/M9; sequential M3/M12) |
| Multivariate consistency | Covered (M11, M7, M9 cross-variable) |
| Genuine event vs anomaly | Flagged as unsolved by any single detector; A1/A3/A6, D5, E2 |
| Confidence scores | Options M15/M16; definition left open (Design question 2) |
| Explainable reasoning | M22, E15 |
| Root-cause classification | M10, M12, M19; identifiability warning |
| Sensor health | M20 |
| Degradation prediction/indication | M20; identifiability and validation limits stated |
| Maintenance indication | M20, D4; must be an indication, not a guarantee |
| Scalability | Considered per method; A4; E11 pending |
| Practical deployment | Considered (A4, edge feasibility); pending measurements |
| Visualization/dashboard | **Not in scope of this research document; gap for later agents** |
| Edge/energy considerations | M17, E11; energy **unverified** |
| Fully executable code, example usage, use-case documentation | **Not in scope here; gap for later agents** |

## Core handoff question

> **Given that cheap statistical baselines are likely strong and no detector solves genuine-event protection alone, what evidence design and decision mechanism can SIH26073 add, and which experiment (E1, E2, E3, E4 or E5) will show it measurably?**

---

## DOCUMENT STATUS

**Document:** `04_ML_METHODS.md`
**Agent:** RESEARCH AGENT 04 — MLSCOUT
**Final solution:** Not chosen
**Core inputs respected:** Temperature, Pressure, Relative Humidity only (metadata: timestamp, station ID, location, elevation)
**Evidence basis:** `00`–`03`, plus targeted web searches (sources S1–S18); no experiments run
