# -*- coding: utf-8 -*-
"""Reference baseline profile for Phase 3B (fixed CleanBuffer API).

Only admitted observations (AdmissionState.ADMIT) are fed to update().
Uses correct CleanBuffer.push(t, p, rh, ts) and as_array(buf) API.
"""
from __future__ import annotations

import math
from typing import Dict, Any, List, Optional

from features.builder import CleanBuffer


def _median(values: List[float]) -> float:
    s = sorted(v for v in values if v is not None and not math.isnan(v))
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def _mad(values: List[float], med: float) -> float:
    devs = [abs(v - med) for v in values if v is not None and not math.isnan(v)]
    return _median(devs) * 1.4826 + 1e-6


def _dewpoint_simple(temperature: float, rh: float) -> float:
    rh_safe = max(rh, 0.01)
    gamma = math.log(rh_safe / 100.0) + (17.67 * temperature) / (temperature + 243.5)
    return (243.5 * gamma) / (17.67 - gamma)


class ReferenceProfile:
    """Versioned reference profile per station.

    Quarantine-protected: only admitted observations are accepted via update().
    """

    def __init__(self, window_size: int = 96, fault_z_thresh: float = 3.0):
        self.window_size = window_size
        self.fault_z_thresh = fault_z_thresh
        # Per-station CleanBuffers
        self._buffers: Dict[str, CleanBuffer] = {}

    def _get_buffer(self, station_id: str) -> CleanBuffer:
        if station_id not in self._buffers:
            self._buffers[station_id] = CleanBuffer(max_size=self.window_size)
        return self._buffers[station_id]

    def update(self, station_id: str, temperature: float, pressure: float, rh: float) -> None:
        """Add an admitted observation. Called only for AdmissionState.ADMIT."""
        from datetime import datetime, timezone
        buf = self._get_buffer(station_id)
        buf.push(temperature, pressure, rh, datetime.now(timezone.utc))

    def _get_channel_values(self, station_id: str) -> Dict[str, List[float]]:
        buf = self._get_buffer(station_id)
        import numpy as np
        t_arr = buf.as_array(buf.t_buf).tolist()
        p_arr = buf.as_array(buf.p_buf).tolist()
        rh_arr = buf.as_array(buf.rh_buf).tolist()
        return {"temperature": t_arr, "pressure": p_arr, "relative_humidity": rh_arr}

    def _z_score(self, value: float, values: List[float], min_scale: float = 0.5) -> float:
        # Guard against missing value
        if value is None:
            return 0.0
        clean = [v for v in values if v is not None and not math.isnan(v)]
        if len(clean) < 3:
            return 0.0
        med = _median(clean)
        mad = max(_mad(clean, med), min_scale)
        return abs(value - med) / mad

    def _thermodynamic_ok(self, temperature: float, rh: float) -> bool:
        try:
            td = _dewpoint_simple(temperature, rh)
            return (temperature - td) >= -0.5
        except Exception:
            return False

    def evaluate(
        self,
        station_id: str,
        temperature: float,
        pressure: float,
        rh: float,
    ) -> Dict[str, Any]:
        """Evaluate an observation against the reference profile.

        Returns:
            plausibility_score: float in [0, 1]
            weather_event_evidence: bool
            sensor_fault_evidence: bool
        """
        vals = self._get_channel_values(station_id)
        z_t = self._z_score(temperature, vals["temperature"], min_scale=0.5)
        z_p = self._z_score(pressure, vals["pressure"], min_scale=0.5)
        z_rh = self._z_score(rh, vals["relative_humidity"], min_scale=2.0)
        max_z = max(z_t, z_p, z_rh)

        plausibility = max(0.0, 1.0 - max_z / 10.0)
        thermo_ok = self._thermodynamic_ok(temperature, rh)
        sensor_fault = (max_z > self.fault_z_thresh) or (not thermo_ok)
        # Weather evidence: moderate deviation but thermodynamically plausible
        weather = (max_z <= self.fault_z_thresh) and thermo_ok

        return {
            "plausibility_score": float(round(plausibility, 4)),
            "weather_event_evidence": bool(weather),
            "sensor_fault_evidence": bool(sensor_fault),
        }

    def clear(self) -> None:
        self._buffers.clear()


# Module-level singleton
reference_profile = ReferenceProfile()
