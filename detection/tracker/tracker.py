# -*- coding: utf-8 -*-
"""Adaptive tracker for Phase 3B (fixed CleanBuffer API).

Only admitted observations are fed to update().
Uses correct CleanBuffer.push(t, p, rh, ts) and as_array(buf) API.
"""
from __future__ import annotations

import math
from typing import Dict, Any, List

from features.builder import CleanBuffer


def _mean(values: List[float]) -> float:
    clean = [v for v in values if v is not None and not math.isnan(v)]
    return sum(clean) / len(clean) if clean else 0.0


def _std(values: List[float], mean: float) -> float:
    clean = [v for v in values if v is not None and not math.isnan(v)]
    if len(clean) < 2:
        return 1e-6
    variance = sum((v - mean) ** 2 for v in clean) / len(clean)
    return math.sqrt(variance) + 1e-6


class AdaptiveTracker:
    """Short-term adaptive model updated exclusively on admitted data.

    Uses a short rolling window (default 12) to capture recent behaviour.
    """

    def __init__(self, short_window: int = 12, fault_z_thresh: float = 2.5):
        self.short_window = short_window
        self.fault_z_thresh = fault_z_thresh
        self._buffers: Dict[str, CleanBuffer] = {}

    def _get_buffer(self, station_id: str) -> CleanBuffer:
        if station_id not in self._buffers:
            self._buffers[station_id] = CleanBuffer(max_size=self.short_window)
        return self._buffers[station_id]

    def update(self, station_id: str, temperature: float, pressure: float, rh: float) -> None:
        """Add an admitted observation."""
        from datetime import datetime, timezone
        buf = self._get_buffer(station_id)
        buf.push(temperature, pressure, rh, datetime.now(timezone.utc))

    def _z_score(self, value: float, values: List[float], min_scale: float = 0.5) -> float:
        # Guard against missing value
        if value is None:
            return 0.0
        clean = [v for v in values if v is not None and not math.isnan(v)]
        if len(clean) < 2:
            return 0.0
        m = _mean(clean)
        s = max(_std(clean, m), min_scale)
        return abs(value - m) / s

    def evaluate(
        self,
        station_id: str,
        temperature: float,
        pressure: float,
        rh: float,
    ) -> Dict[str, Any]:
        """Evaluate an observation against the short-term tracker.

        Returns:
            plausibility_score: float in [0, 1]
            weather_event_evidence: bool
            sensor_fault_evidence: bool
        """
        buf = self._get_buffer(station_id)
        t_vals = buf.as_array(buf.t_buf).tolist()
        p_vals = buf.as_array(buf.p_buf).tolist()
        rh_vals = buf.as_array(buf.rh_buf).tolist()

        z_t = self._z_score(temperature, t_vals, min_scale=0.5)
        z_p = self._z_score(pressure, p_vals, min_scale=0.5)
        z_rh = self._z_score(rh, rh_vals, min_scale=2.0)
        max_z = max(z_t, z_p, z_rh)

        plausibility = max(0.0, 1.0 - max_z / 8.0)
        sensor_fault = max_z > self.fault_z_thresh
        weather = not sensor_fault

        return {
            "plausibility_score": float(round(plausibility, 4)),
            "weather_event_evidence": bool(weather),
            "sensor_fault_evidence": bool(sensor_fault),
        }

    def clear(self) -> None:
        self._buffers.clear()


# Module-level singleton
adaptive_tracker = AdaptiveTracker()
