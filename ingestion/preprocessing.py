"""
Observation preprocessor: Coordinates canonical unit standardization,
finite-value validation, thermodynamic derivations, and temporal feature context.
"""
from typing import Dict, Any, Optional
from datetime import datetime
from ingestion.schemas.observation import ObservationIn
from features.multivariate.thermodynamics import compute_derived_meteorological_quantities
from features.temporal.rates import compute_rates_of_change


class Preprocessor:
    def __init__(self, feature_version: str = "f1"):
        self.feature_version = feature_version

    def process(
        self,
        obs: ObservationIn,
        last_values: Optional[Dict[str, Optional[float]]] = None,
        last_ts: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Produce preprocessed and derived feature record for an observation.
        """
        # 1. Derived thermodynamics
        thermo = compute_derived_meteorological_quantities(
            temp_c=obs.temperature,
            pressure_hpa=obs.pressure,
            rh_pct=obs.relative_humidity,
        )

        # 2. Temporal rates of change
        delta_sec = 0.0
        if last_ts is not None and obs.timestamp > last_ts:
            delta_sec = (obs.timestamp - last_ts).total_seconds()

        curr_vals = {
            "temperature": obs.temperature,
            "pressure": obs.pressure,
            "relative_humidity": obs.relative_humidity,
        }
        rates = compute_rates_of_change(
            curr_values=curr_vals,
            last_values=last_values or {},
            delta_seconds=delta_sec,
        )

        # 3. Calendar context (event time)
        dt = obs.timestamp
        calendar = {
            "hour_of_day": dt.hour + (dt.minute / 60.0),
            "day_of_year": dt.timetuple().tm_yday,
            "month": dt.month,
        }

        # 4. Missingness indicators
        missingness = {
            "missing_temperature": obs.temperature is None,
            "missing_pressure": obs.pressure is None,
            "missing_relative_humidity": obs.relative_humidity is None,
        }

        return {
            "feature_version": self.feature_version,
            "derived_dewpoint_c": thermo.get("derived_dewpoint_c"),
            "derived_vapour_pressure_hpa": thermo.get("derived_vapour_pressure_hpa"),
            "derived_saturated_vapour_pressure_hpa": thermo.get("derived_saturated_vapour_pressure_hpa"),
            "rates": rates,
            "calendar": calendar,
            "missingness": missingness,
        }


preprocessor = Preprocessor()
