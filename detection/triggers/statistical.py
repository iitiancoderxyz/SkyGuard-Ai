"""
Statistical Anomaly Detector (Phase 3A) — TRUST-TWIN.
Robust, deterministic, lightweight statistical and temporal anomaly triggers.
Operates on the three allowed meteorological channels (T, P, RH) and station history.
"""
import time
import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from features.builder import CleanBuffer, _dewpoint, _magnus_tetens, _rolling_mean_std


@dataclass
class AnomalyResult:
    """Detailed result of statistical anomaly detection for a single observation."""
    anomaly_score: float                        # Composite score in [0.0, 1.0]
    is_anomaly: bool                            # True if anomaly_score >= threshold
    channel_scores: Dict[str, float]            # Per-channel score in [0.0, 1.0]
    triggers: List[str]                         # Trigger codes for active detections
    metrics: Dict[str, float]                   # Calculated derivatives, z-scores, MADs
    execution_time_ms: float                    # Inference latency in milliseconds


def _robust_median_mad(arr: np.ndarray, window: int = 24) -> Tuple[float, float]:
    """
    Compute sample median and Median Absolute Deviation (MAD) over the last `window` valid points.
    MAD is scaled by 1.4826 for normal-distribution consistency.
    """
    valid = arr[~np.isnan(arr)]
    if len(valid) < 3:
        return np.nan, np.nan
    slc = valid[-window:] if len(valid) >= window else valid
    med = float(np.median(slc))
    abs_dev = np.abs(slc - med)
    mad = float(np.median(abs_dev) * 1.4826) + 1e-6
    return med, mad


class StatisticalAnomalyDetector:
    """
    Deterministic, robust statistical and rate-of-change detector.
    
    Evaluates:
      1. Rate-of-change violations (per-minute derivatives and single-step jumps)
      2. Sudden spikes (positive excursions) and drops (negative excursions)
      3. Persistence / frozen sensor flatlines
      4. Robust rolling Median Absolute Deviation (MAD) excursions
      5. Thermodynamic consistency violations (dewpoint exceeding temperature)
    """

    def __init__(
        self,
        # Max realistic meteorological rate of change per minute (15-min equivalent in parens)
        max_rate_per_min: Optional[Dict[str, float]] = None,
        # Hard single-step jump thresholds (independent of delta-t)
        step_thresholds: Optional[Dict[str, float]] = None,
        # Frozen value threshold: consecutive readings with identical value (|delta| <= eps)
        frozen_step_count: int = 4,
        frozen_eps: float = 1e-4,
        # Robust MAD z-score threshold (3.5 MAD ~ 99.9% in normal distribution)
        mad_z_threshold: float = 3.5,
        # Composite score threshold for binary anomaly flag
        anomaly_threshold: float = 0.5,
    ):
        self.max_rate_per_min = max_rate_per_min or {
            "temperature": 0.5,        # 0.5 deg C/min (7.5 deg C in 15m)
            "pressure": 0.4,           # 0.4 hPa/min (6.0 hPa in 15m)
            "relative_humidity": 2.5,  # 2.5 %/min (37.5 % in 15m)
        }
        self.step_thresholds = step_thresholds or {
            "temperature": 6.0,        # 6.0 deg C jump
            "pressure": 5.0,           # 5.0 hPa jump
            "relative_humidity": 25.0, # 25.0 % jump
        }
        self.frozen_step_count = frozen_step_count
        self.frozen_eps = frozen_eps
        self.mad_z_threshold = mad_z_threshold
        self.anomaly_threshold = anomaly_threshold

    def detect(
        self,
        t: Optional[float],
        p: Optional[float],
        rh: Optional[float],
        ts: datetime,
        buffer: CleanBuffer,
    ) -> AnomalyResult:
        """
        Execute statistical anomaly detection against the observation and clean history.
        Returns AnomalyResult with composite score in [0.0, 1.0], channel breakdown, and latency.
        """
        start_t = time.perf_counter()

        channel_scores = {"temperature": 0.0, "pressure": 0.0, "relative_humidity": 0.0}
        triggers: List[str] = []
        metrics: Dict[str, float] = {}

        # If all channels are None (e.g. communication drop), return zero score without crash
        if t is None and p is None and rh is None:
            exec_time = (time.perf_counter() - start_t) * 1000.0
            return AnomalyResult(
                anomaly_score=0.0,
                is_anomaly=False,
                channel_scores=channel_scores,
                triggers=["MISSING_ALL_CHANNELS"],
                metrics={},
                execution_time_ms=round(exec_time, 4),
            )

        # -------------------------------------------------------------
        # 1. Rate of Change & Step Jumps
        # -------------------------------------------------------------
        if len(buffer) >= 1 and buffer.ts_buf:
            prev_ts = buffer.ts_buf[-1]
            delta_min = (ts - prev_ts).total_seconds() / 60.0 if prev_ts else 0.0

            # Evaluate each channel
            for ch_name, cur_val, buf_arr in [
                ("temperature", t, buffer.t_buf),
                ("pressure", p, buffer.p_buf),
                ("relative_humidity", rh, buffer.rh_buf),
            ]:
                if cur_val is None:
                    continue

                prev_val = buffer.last_valid(buf_arr)
                if prev_val is not None:
                    diff = cur_val - prev_val
                    abs_diff = abs(diff)
                    metrics[f"{ch_name}_step_diff"] = round(diff, 3)

                    # Step jump trigger
                    step_thresh = self.step_thresholds[ch_name]
                    if abs_diff >= step_thresh:
                        rate_score = min(1.0, abs_diff / (step_thresh * 1.5))
                        channel_scores[ch_name] = max(channel_scores[ch_name], rate_score)
                        direction = "POSITIVE" if diff > 0 else "NEGATIVE"
                        triggers.append(f"{ch_name.upper()}_SPIKE_{direction}")

                    # Rate-of-change trigger (per minute)
                    if delta_min > 0:
                        rate_per_min = abs_diff / delta_min
                        metrics[f"{ch_name}_rate_per_min"] = round(rate_per_min, 4)
                        max_rate = self.max_rate_per_min[ch_name]
                        if rate_per_min >= max_rate:
                            rate_score = min(1.0, rate_per_min / (max_rate * 2.0))
                            channel_scores[ch_name] = max(channel_scores[ch_name], rate_score)
                            triggers.append(f"{ch_name.upper()}_UNREALISTIC_RATE")

        # -------------------------------------------------------------
        # 2. Persistence / Frozen Flatline Detection
        # -------------------------------------------------------------
        for ch_name, cur_val, buf_arr in [
            ("temperature", t, buffer.t_buf),
            ("pressure", p, buffer.p_buf),
            ("relative_humidity", rh, buffer.rh_buf),
        ]:
            if cur_val is None or len(buf_arr) < (self.frozen_step_count - 1):
                continue

            # Count consecutive trailing values within frozen_eps
            flat_count = 1
            for prev_v in reversed(buf_arr):
                if prev_v is not None and abs(cur_val - prev_v) <= self.frozen_eps:
                    flat_count += 1
                else:
                    break

            metrics[f"{ch_name}_flat_count"] = flat_count
            if flat_count >= self.frozen_step_count:
                persist_score = min(1.0, 0.5 + 0.1 * (flat_count - self.frozen_step_count + 1))
                channel_scores[ch_name] = max(channel_scores[ch_name], persist_score)
                triggers.append(f"FROZEN_{ch_name.upper()}")

        # -------------------------------------------------------------
        # 3. Robust Statistical Z-Score / MAD Excursions
        # -------------------------------------------------------------
        if len(buffer) >= 6:
            for ch_name, cur_val, buf_arr in [
                ("temperature", t, buffer.t_buf),
                ("pressure", p, buffer.p_buf),
                ("relative_humidity", rh, buffer.rh_buf),
            ]:
                if cur_val is None:
                    continue

                arr = buffer.as_array(buf_arr)
                med, mad = _robust_median_mad(arr, window=24)
                if not np.isnan(med) and mad > 1e-5:
                    robust_z = abs(cur_val - med) / mad
                    metrics[f"{ch_name}_robust_z"] = round(robust_z, 3)
                    if robust_z >= self.mad_z_threshold:
                        z_score = min(1.0, (robust_z - 2.5) / 3.5)
                        channel_scores[ch_name] = max(channel_scores[ch_name], z_score)
                        triggers.append(f"ROBUST_ZSCORE_EXCURSION_{ch_name.upper()}")

        # -------------------------------------------------------------
        # 4. Thermodynamic Physical Consistency
        # -------------------------------------------------------------
        thermo_score = 0.0
        if t is not None and rh is not None:
            try:
                dp = _dewpoint(t, rh)
                depression = t - dp
                metrics["dewpoint_c"] = round(dp, 2)
                metrics["dewpoint_depression"] = round(depression, 2)

                # Dewpoint cannot physically exceed temperature by > 0.5 deg C (allow minor sensor tolerance)
                if depression < -0.5:
                    thermo_score = min(1.0, abs(depression) / 3.0)
                    channel_scores["temperature"] = max(channel_scores["temperature"], thermo_score)
                    channel_scores["relative_humidity"] = max(channel_scores["relative_humidity"], thermo_score)
                    triggers.append("THERMODYNAMIC_INCONSISTENCY")
            except (ValueError, ZeroDivisionError, OverflowError):
                pass

        # -------------------------------------------------------------
        # 5. Composite Normalized Anomaly Score
        # -------------------------------------------------------------
        composite_score = max(
            channel_scores["temperature"],
            channel_scores["pressure"],
            channel_scores["relative_humidity"],
            thermo_score,
        )
        composite_score = max(0.0, min(1.0, float(composite_score)))

        exec_time = (time.perf_counter() - start_t) * 1000.0

        return AnomalyResult(
            anomaly_score=round(composite_score, 4),
            is_anomaly=(composite_score >= self.anomaly_threshold),
            channel_scores={k: round(v, 4) for k, v in channel_scores.items()},
            triggers=triggers,
            metrics=metrics,
            execution_time_ms=round(exec_time, 4),
        )


# Module-level singleton
statistical_detector = StatisticalAnomalyDetector()
