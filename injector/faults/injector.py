"""
Comprehensive Fault Injection Framework for TRUST-TWIN.
Implements the 14 anomaly families strictly in Temperature, Pressure, Relative Humidity.
Produces sidecar ground-truth labels and manifests for evaluation (INV-03).
"""
import uuid
import copy
import random
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple, Optional
from ingestion.schemas.observation import ObservationIn, SourceType


class FaultInjector:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.RandomState(seed)

    # 1. Isolated Spike
    def inject_isolated_spike(
        self,
        observations: List[ObservationIn],
        index: int,
        channel: str = "temperature",
        magnitude: float = 15.0,
    ) -> Tuple[List[ObservationIn], Dict[str, Any]]:
        injected = [obs.model_copy(deep=True) for obs in observations]
        target = injected[index]
        curr = getattr(target, channel)
        if curr is not None:
            setattr(target, channel, round(curr + magnitude, 2))

        manifest = {
            "injection_id": f"inj-{uuid.uuid4().hex[:8]}",
            "fault_class": "ISOLATED_SPIKE",
            "channel": channel,
            "magnitude": magnitude,
            "onset_ts": target.timestamp.isoformat(),
            "offset_ts": target.timestamp.isoformat(),
            "affected_indices": [index],
            "seed": self.seed,
        }
        return injected, manifest

    # 2. Repeated Spikes
    def inject_repeated_spikes(
        self,
        observations: List[ObservationIn],
        start_index: int,
        duration: int,
        period: int = 2,
        channel: str = "temperature",
        magnitude: float = 10.0,
    ) -> Tuple[List[ObservationIn], Dict[str, Any]]:
        injected = [obs.model_copy(deep=True) for obs in observations]
        affected = []
        for step, i in enumerate(range(start_index, min(len(injected), start_index + duration))):
            if step % period == 0:
                curr = getattr(injected[i], channel)
                if curr is not None:
                    setattr(injected[i], channel, round(curr + magnitude, 2))
                    affected.append(i)

        manifest = {
            "injection_id": f"inj-{uuid.uuid4().hex[:8]}",
            "fault_class": "REPEATED_SPIKES",
            "channel": channel,
            "period": period,
            "magnitude": magnitude,
            "onset_ts": injected[start_index].timestamp.isoformat(),
            "offset_ts": injected[min(len(injected) - 1, start_index + duration - 1)].timestamp.isoformat(),
            "affected_indices": affected,
            "seed": self.seed,
        }
        return injected, manifest

    # 3. Sudden Bias
    def inject_sudden_bias(
        self,
        observations: List[ObservationIn],
        start_index: int,
        duration: int,
        channel: str = "pressure",
        bias_magnitude: float = -12.0,
    ) -> Tuple[List[ObservationIn], Dict[str, Any]]:
        injected = [obs.model_copy(deep=True) for obs in observations]
        affected = []
        for i in range(start_index, min(len(injected), start_index + duration)):
            curr = getattr(injected[i], channel)
            if curr is not None:
                setattr(injected[i], channel, round(curr + bias_magnitude, 2))
                affected.append(i)

        manifest = {
            "injection_id": f"inj-{uuid.uuid4().hex[:8]}",
            "fault_class": "SUDDEN_BIAS",
            "channel": channel,
            "bias_magnitude": bias_magnitude,
            "onset_ts": injected[start_index].timestamp.isoformat(),
            "offset_ts": injected[affected[-1]].timestamp.isoformat(),
            "affected_indices": affected,
            "seed": self.seed,
        }
        return injected, manifest

    # 4. Gradual Drift
    def inject_gradual_drift(
        self,
        observations: List[ObservationIn],
        start_index: int,
        duration: int,
        channel: str = "relative_humidity",
        drift_rate_per_step: float = 0.5,
    ) -> Tuple[List[ObservationIn], Dict[str, Any]]:
        injected = [obs.model_copy(deep=True) for obs in observations]
        affected = []
        for step, i in enumerate(range(start_index, min(len(injected), start_index + duration))):
            curr = getattr(injected[i], channel)
            if curr is not None:
                offset = (step + 1) * drift_rate_per_step
                new_val = max(0.0, min(100.0, curr + offset))
                setattr(injected[i], channel, round(new_val, 2))
                affected.append(i)

        manifest = {
            "injection_id": f"inj-{uuid.uuid4().hex[:8]}",
            "fault_class": "GRADUAL_DRIFT",
            "channel": channel,
            "drift_rate": drift_rate_per_step,
            "onset_ts": injected[start_index].timestamp.isoformat(),
            "offset_ts": injected[affected[-1]].timestamp.isoformat(),
            "affected_indices": affected,
            "seed": self.seed,
        }
        return injected, manifest

    # 5. Frozen / Flatline
    def inject_frozen_flatline(
        self,
        observations: List[ObservationIn],
        start_index: int,
        duration: int,
        channel: str = "temperature",
    ) -> Tuple[List[ObservationIn], Dict[str, Any]]:
        injected = [obs.model_copy(deep=True) for obs in observations]
        stuck_val = getattr(injected[start_index], channel)
        affected = []
        for i in range(start_index, min(len(injected), start_index + duration)):
            setattr(injected[i], channel, stuck_val)
            affected.append(i)

        manifest = {
            "injection_id": f"inj-{uuid.uuid4().hex[:8]}",
            "fault_class": "FROZEN_FLATLINE",
            "channel": channel,
            "stuck_value": stuck_val,
            "onset_ts": injected[start_index].timestamp.isoformat(),
            "offset_ts": injected[affected[-1]].timestamp.isoformat(),
            "affected_indices": affected,
            "seed": self.seed,
        }
        return injected, manifest

    # 6. Stuck-at Value (Rail Clamp)
    def inject_stuck_at_value(
        self,
        observations: List[ObservationIn],
        start_index: int,
        duration: int,
        channel: str = "relative_humidity",
        clamped_value: float = 100.0,
    ) -> Tuple[List[ObservationIn], Dict[str, Any]]:
        injected = [obs.model_copy(deep=True) for obs in observations]
        affected = []
        for i in range(start_index, min(len(injected), start_index + duration)):
            setattr(injected[i], channel, clamped_value)
            affected.append(i)

        manifest = {
            "injection_id": f"inj-{uuid.uuid4().hex[:8]}",
            "fault_class": "STUCK_AT_VALUE",
            "channel": channel,
            "clamped_value": clamped_value,
            "onset_ts": injected[start_index].timestamp.isoformat(),
            "offset_ts": injected[affected[-1]].timestamp.isoformat(),
            "affected_indices": affected,
            "seed": self.seed,
        }
        return injected, manifest

    # 7. Excessive Noise
    def inject_excessive_noise(
        self,
        observations: List[ObservationIn],
        start_index: int,
        duration: int,
        channel: str = "temperature",
        noise_std: float = 4.0,
    ) -> Tuple[List[ObservationIn], Dict[str, Any]]:
        injected = [obs.model_copy(deep=True) for obs in observations]
        affected = []
        for i in range(start_index, min(len(injected), start_index + duration)):
            curr = getattr(injected[i], channel)
            if curr is not None:
                noise = self.rng.normal(0, noise_std)
                setattr(injected[i], channel, round(curr + noise, 2))
                affected.append(i)

        manifest = {
            "injection_id": f"inj-{uuid.uuid4().hex[:8]}",
            "fault_class": "EXCESSIVE_NOISE",
            "channel": channel,
            "noise_std": noise_std,
            "onset_ts": injected[start_index].timestamp.isoformat(),
            "offset_ts": injected[affected[-1]].timestamp.isoformat(),
            "affected_indices": affected,
            "seed": self.seed,
        }
        return injected, manifest

    # 8. Missing Observation (NaN / null in channel)
    def inject_missing_observation(
        self,
        observations: List[ObservationIn],
        index: int,
        channel: str = "temperature",
    ) -> Tuple[List[ObservationIn], Dict[str, Any]]:
        injected = [obs.model_copy(deep=True) for obs in observations]
        setattr(injected[index], channel, None)

        manifest = {
            "injection_id": f"inj-{uuid.uuid4().hex[:8]}",
            "fault_class": "MISSING_OBSERVATION",
            "channel": channel,
            "onset_ts": injected[index].timestamp.isoformat(),
            "offset_ts": injected[index].timestamp.isoformat(),
            "affected_indices": [index],
            "seed": self.seed,
        }
        return injected, manifest

    # 9. Communication Failure (Dropped Rows)
    def inject_communication_failure(
        self,
        observations: List[ObservationIn],
        start_index: int,
        drop_count: int = 3,
    ) -> Tuple[List[ObservationIn], Dict[str, Any]]:
        injected = [obs.model_copy(deep=True) for obs in observations]
        dropped = injected[start_index : start_index + drop_count]
        del injected[start_index : start_index + drop_count]

        manifest = {
            "injection_id": f"inj-{uuid.uuid4().hex[:8]}",
            "fault_class": "COMMUNICATION_FAILURE",
            "dropped_count": len(dropped),
            "onset_ts": dropped[0].timestamp.isoformat() if dropped else None,
            "offset_ts": dropped[-1].timestamp.isoformat() if dropped else None,
            "dropped_timestamps": [d.timestamp.isoformat() for d in dropped],
            "seed": self.seed,
        }
        return injected, manifest

    # 10. Duplicate Observation
    def inject_duplicate(
        self,
        observations: List[ObservationIn],
        target_index: int,
    ) -> Tuple[List[ObservationIn], Dict[str, Any]]:
        injected = [obs.model_copy(deep=True) for obs in observations]
        dup = injected[target_index].model_copy(deep=True)
        injected.insert(target_index + 1, dup)

        manifest = {
            "injection_id": f"inj-{uuid.uuid4().hex[:8]}",
            "fault_class": "DUPLICATE_OBSERVATION",
            "duplicate_index": target_index + 1,
            "event_ts": dup.timestamp.isoformat(),
            "seed": self.seed,
        }
        return injected, manifest

    # 11. Delayed / Out-of-order Observation
    def inject_delayed_out_of_order(
        self,
        observations: List[ObservationIn],
        from_index: int,
        insert_after_index: int,
    ) -> Tuple[List[ObservationIn], Dict[str, Any]]:
        injected = [obs.model_copy(deep=True) for obs in observations]
        elem = injected.pop(from_index)
        injected.insert(insert_after_index, elem)

        manifest = {
            "injection_id": f"inj-{uuid.uuid4().hex[:8]}",
            "fault_class": "DELAYED_OUT_OF_ORDER",
            "original_index": from_index,
            "new_index": insert_after_index,
            "event_ts": elem.timestamp.isoformat(),
            "seed": self.seed,
        }
        return injected, manifest

    # 12. Corrupted Value
    def inject_corrupted_value(
        self,
        observations: List[ObservationIn],
        index: int,
        channel: str = "temperature",
    ) -> Tuple[List[ObservationIn], Dict[str, Any]]:
        injected = [obs.model_copy(deep=True) for obs in observations]
        corrupted_val = -999.0 if self.rng.rand() > 0.5 else 999.99
        setattr(injected[index], channel, corrupted_val)

        manifest = {
            "injection_id": f"inj-{uuid.uuid4().hex[:8]}",
            "fault_class": "CORRUPTED_VALUE",
            "channel": channel,
            "corrupted_value": corrupted_val,
            "onset_ts": injected[index].timestamp.isoformat(),
            "offset_ts": injected[index].timestamp.isoformat(),
            "affected_indices": [index],
            "seed": self.seed,
        }
        return injected, manifest

    # 13. Multivariate Inconsistency
    def inject_multivariate_inconsistency(
        self,
        observations: List[ObservationIn],
        start_index: int,
        duration: int,
    ) -> Tuple[List[ObservationIn], Dict[str, Any]]:
        """
        Inject impossible physical decoupling:
        Temperature jumps to extreme heat (55°C) while RH simultaneously saturates at 98% and Pressure plummets.
        (Directly models the SIH reference anomaly scenario).
        """
        injected = [obs.model_copy(deep=True) for obs in observations]
        affected = []
        for i in range(start_index, min(len(injected), start_index + duration)):
            injected[i].temperature = 55.0
            injected[i].relative_humidity = 98.0
            injected[i].pressure = 940.0
            affected.append(i)

        manifest = {
            "injection_id": f"inj-{uuid.uuid4().hex[:8]}",
            "fault_class": "MULTIVARIATE_INCONSISTENCY",
            "channel": "multi",
            "description": "Unphysical simultaneous extreme temperature, saturated RH, and abnormal pressure drop",
            "onset_ts": injected[start_index].timestamp.isoformat(),
            "offset_ts": injected[affected[-1]].timestamp.isoformat(),
            "affected_indices": affected,
            "seed": self.seed,
        }
        return injected, manifest

    # 14. Combined Faults
    def inject_combined_fault(
        self,
        observations: List[ObservationIn],
        start_index: int,
        duration: int,
    ) -> Tuple[List[ObservationIn], Dict[str, Any]]:
        """Superposition of gradual drift + excessive noise + occasional missing value."""
        injected = [obs.model_copy(deep=True) for obs in observations]
        affected = []
        for step, i in enumerate(range(start_index, min(len(injected), start_index + duration))):
            curr_t = injected[i].temperature
            if curr_t is not None:
                drift = (step + 1) * 0.3
                noise = self.rng.normal(0, 2.0)
                injected[i].temperature = round(curr_t + drift + noise, 2)
            if step == 3:
                injected[i].pressure = None  # Intermittent missingness
            affected.append(i)

        manifest = {
            "injection_id": f"inj-{uuid.uuid4().hex[:8]}",
            "fault_class": "COMBINED_FAULTS",
            "components": ["GRADUAL_DRIFT", "EXCESSIVE_NOISE", "MISSING_VALUE"],
            "channel": "multi",
            "onset_ts": injected[start_index].timestamp.isoformat(),
            "offset_ts": injected[affected[-1]].timestamp.isoformat(),
            "affected_indices": affected,
            "seed": self.seed,
        }
        return injected, manifest

    # Convenience alias for backwards compatibility
    def inject_spike(self, *args, **kwargs):
        return self.inject_isolated_spike(*args, **kwargs)

    def inject_frozen(self, *args, **kwargs):
        return self.inject_frozen_flatline(*args, **kwargs)

    def inject_drift(self, *args, **kwargs):
        return self.inject_gradual_drift(*args, **kwargs)

    def inject_communication_gap(self, *args, **kwargs):
        return self.inject_communication_failure(*args, **kwargs)
