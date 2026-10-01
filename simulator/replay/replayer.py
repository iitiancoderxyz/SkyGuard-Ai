"""
Historical and simulated stream replayer.
Executes replay through the identical process_observation() entry point (Principle P1).
"""
import time
from datetime import datetime, timezone
from typing import List, Optional, Callable
from ingestion.schemas.observation import ObservationIn
from ingestion.schemas.response import Decision
from app.runtime.engine import process_observation


class StreamReplayer:
    def __init__(
        self,
        processor_fn: Callable[[ObservationIn], Decision] = process_observation,
    ):
        self.processor_fn = processor_fn

    def replay(
        self,
        observations: List[ObservationIn],
        speed_multiplier: float = 0.0,  # 0.0 = as fast as possible
    ) -> List[Decision]:
        """
        Replay observations through the single engine entry point.
        """
        results: List[Decision] = []
        last_event_ts: Optional[datetime] = None

        for obs in observations:
            if speed_multiplier > 0 and last_event_ts is not None:
                delta_sec = (obs.timestamp - last_event_ts).total_seconds()
                if delta_sec > 0:
                    time.sleep(delta_sec / speed_multiplier)

            decision = self.processor_fn(obs)
            results.append(decision)
            last_event_ts = obs.timestamp

        return results
