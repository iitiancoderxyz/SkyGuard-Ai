"""
Thermodynamic calculations derived strictly from Temperature and Relative Humidity.
Labeled as 'derived' features (Principle P9, Scope Guard).
No extra meteorological inputs used.
"""
import math
from typing import Optional, Tuple, Dict, Any


def compute_saturated_vapour_pressure(temp_c: float) -> float:
    """
    Compute saturated vapour pressure e_s (hPa) using standard Magnus-Tetens formula.
    Valid for meteorological temperature range.
    """
    return 6.112 * math.exp((17.67 * temp_c) / (temp_c + 243.5))


def compute_vapour_pressure(temp_c: float, rh_pct: float) -> float:
    """
    Compute actual vapour pressure e (hPa).
    """
    rh_clamped = max(0.0, min(100.0, rh_pct))
    e_s = compute_saturated_vapour_pressure(temp_c)
    return round((rh_clamped / 100.0) * e_s, 2)


def compute_dewpoint(temp_c: float, rh_pct: float) -> Optional[float]:
    """
    Compute dew point temperature T_d (°C) using Magnus-Tetens formula inversion.
    """
    if rh_pct <= 0:
        return None
    rh_clamped = max(0.1, min(100.0, rh_pct))
    a = 17.67
    b = 243.5
    alpha = ((a * temp_c) / (b + temp_c)) + math.log(rh_clamped / 100.0)
    if a - alpha == 0:
        return None
    t_d = (b * alpha) / (a - alpha)
    return round(t_d, 2)


def compute_derived_meteorological_quantities(
    temp_c: Optional[float],
    pressure_hpa: Optional[float],
    rh_pct: Optional[float],
) -> Dict[str, Optional[float]]:
    """
    Computes derived thermodynamic quantities and labels them as derived.
    """
    if temp_c is None or rh_pct is None:
        return {
            "derived_dewpoint_c": None,
            "derived_vapour_pressure_hpa": None,
            "derived_saturated_vapour_pressure_hpa": None,
        }

    e_s = compute_saturated_vapour_pressure(temp_c)
    e = compute_vapour_pressure(temp_c, rh_pct)
    td = compute_dewpoint(temp_c, rh_pct)

    return {
        "derived_dewpoint_c": td,
        "derived_vapour_pressure_hpa": e,
        "derived_saturated_vapour_pressure_hpa": round(e_s, 2),
    }
