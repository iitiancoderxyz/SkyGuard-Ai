"""
Temporal rate-of-change and persistence calculations.
"""
from typing import Optional, Dict, Any
from datetime import datetime


def compute_rates_of_change(
    curr_values: Dict[str, Optional[float]],
    last_values: Dict[str, Optional[float]],
    delta_seconds: float,
) -> Dict[str, Optional[float]]:
    """
    Computes rate of change per minute for Temperature (°C/min), Pressure (hPa/min), and RH (%/min).
    """
    if delta_seconds <= 0:
        return {
            "rate_temp_per_min": None,
            "rate_pressure_per_min": None,
            "rate_rh_per_min": None,
        }

    dt_minutes = delta_seconds / 60.0
    rates = {}

    for ch in ["temperature", "pressure", "relative_humidity"]:
        curr = curr_values.get(ch)
        last = last_values.get(ch)
        if curr is not None and last is not None:
            rate = (curr - last) / dt_minutes
            rates[f"rate_{ch}_per_min"] = round(rate, 4)
        else:
            rates[f"rate_{ch}_per_min"] = None

    return rates
