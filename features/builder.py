"""
Feature Builder (C03) — TRUST-TWIN Phase 3.
Deterministic, versioned feature construction from T/P/RH observations
and their history in a per-station clean ring buffer.

Feature vector layout (f1 version, 22 features):
    [0]  temperature
    [1]  pressure
    [2]  relative_humidity
    [3]  dT_dt           (rate of change, per minute)
    [4]  dP_dt
    [5]  dRH_dt
    [6]  d2T_dt2         (second derivative)
    [7]  d2P_dt2
    [8]  d2RH_dt2
    [9]  z_T_1h          (z-score vs 1-hour rolling window)
    [10] z_P_1h
    [11] z_RH_1h
    [12] z_T_6h
    [13] z_P_6h
    [14] z_RH_6h
    [15] hour_sin        (cyclical time-of-day)
    [16] hour_cos
    [17] doy_sin         (cyclical day-of-year)
    [18] doy_cos
    [19] dewpoint_c      (derived thermodynamic)
    [20] vapour_pressure_hpa
    [21] dewpoint_depression
"""
import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

FEATURE_VERSION = "f1"
FEATURE_DIM = 22

# Ring buffer sizes
BUF_1H = 12    # 12 x 5-min steps = 1 hour
BUF_6H = 72    # 6 hours
BUF_96 = 96    # ~8 hours general history


@dataclass
class CleanBuffer:
    """
    Per-station ring buffer holding the last N admitted
    (or integrity-OK) observations for each channel.
    Uses a simple list-based circular approach.
    """
    max_size: int = BUF_96
    t_buf: List[Optional[float]] = field(default_factory=list)
    p_buf: List[Optional[float]] = field(default_factory=list)
    rh_buf: List[Optional[float]] = field(default_factory=list)
    ts_buf: List[Optional[datetime]] = field(default_factory=list)

    def push(self, t: Optional[float], p: Optional[float],
             rh: Optional[float], ts: Optional[datetime]) -> None:
        self.t_buf.append(t)
        self.p_buf.append(p)
        self.rh_buf.append(rh)
        self.ts_buf.append(ts)
        if len(self.t_buf) > self.max_size:
            self.t_buf.pop(0)
            self.p_buf.pop(0)
            self.rh_buf.pop(0)
            self.ts_buf.pop(0)

    def last_valid(self, buf: List[Optional[float]]) -> Optional[float]:
        for v in reversed(buf):
            if v is not None:
                return v
        return None

    def as_array(self, buf: List[Optional[float]]) -> np.ndarray:
        return np.array([v if v is not None else np.nan for v in buf])

    def __len__(self) -> int:
        return len(self.t_buf)


def _rolling_mean_std(arr: np.ndarray, window: int):
    """Compute mean and std of the last `window` non-NaN values."""
    valid = arr[~np.isnan(arr)]
    if len(valid) == 0:
        return np.nan, np.nan
    slc = valid[-window:] if len(valid) >= window else valid
    return float(np.mean(slc)), float(np.std(slc) + 1e-9)


def _magnus_tetens(t: float) -> float:
    """Saturated vapour pressure in hPa."""
    return 6.112 * math.exp((17.67 * t) / (t + 243.5))


def _dewpoint(t: float, rh: float) -> float:
    """Dewpoint via Magnus-Tetens inverse."""
    rh_safe = max(rh, 0.01)
    gamma = math.log(rh_safe / 100.0) + (17.67 * t) / (t + 243.5)
    return (243.5 * gamma) / (17.67 - gamma)


def build_feature_vector(
    obs_t: float,
    obs_p: float,
    obs_rh: float,
    obs_ts: datetime,
    buf: "CleanBuffer",
) -> np.ndarray:
    """
    Build the 22-element feature vector from the current observation
    and the station clean buffer.

    Returns ndarray[float32, shape=(22,)].
    NaN is used for unavailable lag-based features (warm-up period).
    """
    fv = np.full(FEATURE_DIM, np.nan, dtype=np.float32)

    # --- Slot 0-2: raw values ---
    fv[0] = obs_t
    fv[1] = obs_p
    fv[2] = obs_rh

    # --- Slots 3-5: first derivatives (per minute) ---
    if len(buf) >= 2:
        t_arr = buf.as_array(buf.t_buf)
        p_arr = buf.as_array(buf.p_buf)
        rh_arr = buf.as_array(buf.rh_buf)
        ts_arr = buf.ts_buf

        prev_t = t_arr[-1] if not np.isnan(t_arr[-1]) else None
        prev_p = p_arr[-1] if not np.isnan(p_arr[-1]) else None
        prev_rh = rh_arr[-1] if not np.isnan(rh_arr[-1]) else None
        prev_ts = ts_arr[-1] if ts_arr else None

        if prev_ts is not None and obs_ts is not None:
            delta_min = (obs_ts - prev_ts).total_seconds() / 60.0
            if delta_min > 0:
                if prev_t is not None:
                    fv[3] = (obs_t - prev_t) / delta_min
                if prev_p is not None:
                    fv[4] = (obs_p - prev_p) / delta_min
                if prev_rh is not None:
                    fv[5] = (obs_rh - prev_rh) / delta_min

        # --- Slots 6-8: second derivatives ---
        if len(buf) >= 3 and not np.isnan(fv[3]):
            # previous first derivative
            prev2_t = t_arr[-2] if len(t_arr) >= 2 and not np.isnan(t_arr[-2]) else None
            prev2_ts = ts_arr[-2] if len(ts_arr) >= 2 else None
            if prev2_t is not None and prev2_ts is not None and prev_t is not None and prev_ts is not None:
                dt_prev = (prev_ts - prev2_ts).total_seconds() / 60.0
                if dt_prev > 0:
                    prev_dT = (prev_t - prev2_t) / dt_prev
                    if not np.isnan(fv[3]):
                        delta_min_cur = (obs_ts - prev_ts).total_seconds() / 60.0
                        if delta_min_cur > 0:
                            fv[6] = (fv[3] - prev_dT) / delta_min_cur

        # --- Slots 9-14: z-scores ---
        t_arr_full = np.append(t_arr, obs_t)
        p_arr_full = np.append(p_arr, obs_p)
        rh_arr_full = np.append(rh_arr, obs_rh)

        mu1h_t, s1h_t = _rolling_mean_std(t_arr_full, BUF_1H)
        mu1h_p, s1h_p = _rolling_mean_std(p_arr_full, BUF_1H)
        mu1h_rh, s1h_rh = _rolling_mean_std(rh_arr_full, BUF_1H)
        if not np.isnan(mu1h_t):
            fv[9] = (obs_t - mu1h_t) / s1h_t
            fv[10] = (obs_p - mu1h_p) / s1h_p
            fv[11] = (obs_rh - mu1h_rh) / s1h_rh

        mu6h_t, s6h_t = _rolling_mean_std(t_arr_full, BUF_6H)
        mu6h_p, s6h_p = _rolling_mean_std(p_arr_full, BUF_6H)
        mu6h_rh, s6h_rh = _rolling_mean_std(rh_arr_full, BUF_6H)
        if not np.isnan(mu6h_t):
            fv[12] = (obs_t - mu6h_t) / s6h_t
            fv[13] = (obs_p - mu6h_p) / s6h_p
            fv[14] = (obs_rh - mu6h_rh) / s6h_rh
    else:
        # Warm-up: z-scores undefined
        pass

    # --- Slots 15-18: cyclical time encoding ---
    hour = obs_ts.hour + obs_ts.minute / 60.0 if obs_ts else 0.0
    doy = obs_ts.timetuple().tm_yday if obs_ts else 1
    fv[15] = math.sin(2 * math.pi * hour / 24.0)
    fv[16] = math.cos(2 * math.pi * hour / 24.0)
    fv[17] = math.sin(2 * math.pi * doy / 365.25)
    fv[18] = math.cos(2 * math.pi * doy / 365.25)

    # --- Slots 19-21: thermodynamic derived features ---
    try:
        dp = _dewpoint(obs_t, obs_rh)
        vp = _magnus_tetens(obs_t) * (obs_rh / 100.0)
        fv[19] = dp
        fv[20] = vp
        fv[21] = obs_t - dp  # depression
    except (ValueError, ZeroDivisionError, OverflowError):
        pass

    return fv


class FeatureBuilder:
    """
    Stateless builder. Per-station state lives in CleanBuffer (held in StationProcessor).
    """
    feature_version: str = FEATURE_VERSION
    feature_dim: int = FEATURE_DIM

    def build(
        self,
        t: float,
        p: float,
        rh: float,
        ts: datetime,
        buf: CleanBuffer,
    ) -> np.ndarray:
        """Return the 22-element feature vector."""
        return build_feature_vector(t, p, rh, ts, buf)


# Module-level singleton
feature_builder = FeatureBuilder()
