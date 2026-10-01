"""
Genuine Weather Event Simulator (T/P/RH Physical Surrogates).
Generates realistic hard-negative atmospheric events (frontal passage, cold pool, heat surge)
with coherent thermodynamic coupling, labelled with genuine event provenance.
Scope strictly limited to Temperature, Pressure, and Relative Humidity.
"""
import uuid
import copy
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from ingestion.schemas.observation import ObservationIn


class WeatherEventSimulator:
    def __init__(self, seed: int = 42):
        self.seed = seed

    def simulate_cold_front(
        self,
        observations: List[ObservationIn],
        start_index: int,
        duration: int = 15,
        temp_drop: float = -8.0,
        rh_surge: float = 35.0,
        pressure_jump: float = 3.5,
    ) -> Tuple[List[ObservationIn], Dict[str, Any]]:
        """
        Simulates a sharp cold front / convective outflow:
        Coherent rapid temperature drop, relative humidity surge, and pressure rise.
        Physically consistent genuine atmospheric event.
        """
        simulated = [obs.model_copy(deep=True) for obs in observations]
        affected = []

        for step, i in enumerate(range(start_index, min(len(simulated), start_index + duration))):
            # Sigmoidal / smooth transition over the duration
            progress = (step + 1) / float(duration)
            
            curr_t = simulated[i].temperature
            curr_rh = simulated[i].relative_humidity
            curr_p = simulated[i].pressure

            if curr_t is not None:
                simulated[i].temperature = round(curr_t + (temp_drop * progress), 2)
            if curr_rh is not None:
                simulated[i].relative_humidity = min(100.0, round(curr_rh + (rh_surge * progress), 1))
            if curr_p is not None:
                simulated[i].pressure = round(curr_p + (pressure_jump * progress), 2)

            affected.append(i)

        manifest = {
            "event_id": f"wevt-{uuid.uuid4().hex[:8]}",
            "event_type": "COLD_FRONT_PASSAGE",
            "label_type": "GENUINE_EVENT_SURROGATE",
            "label_source": "SYNTHETIC_SURROGATE",
            "description": "Coherent multi-channel frontal transition: T drop, RH surge, P rise",
            "onset_ts": simulated[start_index].timestamp.isoformat(),
            "offset_ts": simulated[affected[-1]].timestamp.isoformat(),
            "affected_indices": affected,
            "seed": self.seed,
        }
        return simulated, manifest

    def simulate_heat_surge(
        self,
        observations: List[ObservationIn],
        start_index: int,
        duration: int = 10,
        temp_rise: float = 6.0,
        rh_drop: float = -25.0,
    ) -> Tuple[List[ObservationIn], Dict[str, Any]]:
        """
        Simulates sudden dry adiabatic warming / heat surge:
        Rapid temperature rise with physically correlated RH drop.
        """
        simulated = [obs.model_copy(deep=True) for obs in observations]
        affected = []

        for step, i in enumerate(range(start_index, min(len(simulated), start_index + duration))):
            progress = (step + 1) / float(duration)
            
            curr_t = simulated[i].temperature
            curr_rh = simulated[i].relative_humidity

            if curr_t is not None:
                simulated[i].temperature = round(curr_t + (temp_rise * progress), 2)
            if curr_rh is not None:
                simulated[i].relative_humidity = max(5.0, round(curr_rh + (rh_drop * progress), 1))

            affected.append(i)

        manifest = {
            "event_id": f"wevt-{uuid.uuid4().hex[:8]}",
            "event_type": "HEAT_SURGE",
            "label_type": "GENUINE_EVENT_SURROGATE",
            "label_source": "SYNTHETIC_SURROGATE",
            "description": "Coherent dry adiabatic surge: T rise, RH drop",
            "onset_ts": simulated[start_index].timestamp.isoformat(),
            "offset_ts": simulated[affected[-1]].timestamp.isoformat(),
            "affected_indices": affected,
            "seed": self.seed,
        }
        return simulated, manifest
