"""
IntegrityGate: Deterministic validation and transport/integrity checks.
No ML dependencies.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from ingestion.schemas.observation import ObservationIn, SourceType
from ingestion.schemas.integrity import (
    IntegrityResult,
    IntegrityFlag,
    IntegrityDisposition,
)
from ingestion.integrity.state import StationState
from app.core.config import settings
from app.core.logging import logger


class IntegrityGate:
    def __init__(
        self,
        temp_min: float = None,
        temp_max: float = None,
        pressure_min: float = None,
        pressure_max: float = None,
        rh_min: float = None,
        rh_max: float = None,
        expected_cadence_seconds: int = None,
        allowed_lateness_seconds: int = None,
        communication_gap_slots: int = None,
        flat_threshold: int = 10,
    ):
        self.temp_min = temp_min if temp_min is not None else settings.temp_min
        self.temp_max = temp_max if temp_max is not None else settings.temp_max
        self.pressure_min = pressure_min if pressure_min is not None else settings.pressure_min
        self.pressure_max = pressure_max if pressure_max is not None else settings.pressure_max
        self.rh_min = rh_min if rh_min is not None else settings.rh_min
        self.rh_max = rh_max if rh_max is not None else settings.rh_max
        self.expected_cadence_seconds = (
            expected_cadence_seconds
            if expected_cadence_seconds is not None
            else settings.expected_cadence_seconds
        )
        self.allowed_lateness_seconds = (
            allowed_lateness_seconds
            if allowed_lateness_seconds is not None
            else settings.allowed_lateness_seconds
        )
        self.communication_gap_slots = (
            communication_gap_slots
            if communication_gap_slots is not None
            else settings.communication_gap_slots
        )
        self.flat_threshold = flat_threshold

    def check(
        self,
        obs: ObservationIn,
        state: StationState,
        received_at: Optional[datetime] = None,
    ) -> IntegrityResult:
        flags: List[IntegrityFlag] = []
        disposition = IntegrityDisposition.ACCEPT
        missing_slots: List[datetime] = []
        channel_nulls: List[str] = []
        details: Dict[str, Any] = {}
        late_by_sec = 0.0
        duplicate_of = None

        now_utc = received_at or datetime.now(timezone.utc)
        if obs.timestamp.tzinfo is None:
            event_ts = obs.timestamp.replace(tzinfo=timezone.utc)
        else:
            event_ts = obs.timestamp

        # 1. Missing Core Values
        if obs.temperature is None:
            flags.append(IntegrityFlag.MISSING_TEMPERATURE)
            channel_nulls.append("temperature")
        if obs.pressure is None:
            flags.append(IntegrityFlag.MISSING_PRESSURE)
            channel_nulls.append("pressure")
        if obs.relative_humidity is None:
            flags.append(IntegrityFlag.MISSING_RELATIVE_HUMIDITY)
            channel_nulls.append("relative_humidity")
        if channel_nulls:
            flags.append(IntegrityFlag.MISSING_VALUE)

        # 2. Range Validation
        if obs.temperature is not None:
            if obs.temperature < self.temp_min:
                flags.append(IntegrityFlag.RANGE_TEMP_LOW)
                flags.append(IntegrityFlag.RANGE_VIOLATION)
            elif obs.temperature > self.temp_max:
                flags.append(IntegrityFlag.RANGE_TEMP_HIGH)
                flags.append(IntegrityFlag.RANGE_VIOLATION)

        if obs.pressure is not None:
            if obs.pressure < self.pressure_min:
                flags.append(IntegrityFlag.RANGE_PRESSURE_LOW)
                flags.append(IntegrityFlag.RANGE_VIOLATION)
            elif obs.pressure > self.pressure_max:
                flags.append(IntegrityFlag.RANGE_PRESSURE_HIGH)
                flags.append(IntegrityFlag.RANGE_VIOLATION)

        if obs.relative_humidity is not None:
            if obs.relative_humidity < self.rh_min:
                flags.append(IntegrityFlag.RANGE_RH_LOW)
                flags.append(IntegrityFlag.RANGE_VIOLATION)
            elif obs.relative_humidity > self.rh_max:
                flags.append(IntegrityFlag.RANGE_RH_HIGH)
                flags.append(IntegrityFlag.RANGE_VIOLATION)

        # 3. Duplicate and Conflicting Duplicate Checks
        ts_key = event_ts.isoformat()
        current_vals = {
            "temperature": obs.temperature,
            "pressure": obs.pressure,
            "relative_humidity": obs.relative_humidity,
        }

        if ts_key in state.seen_timestamps:
            prev = state.seen_timestamps[ts_key]
            duplicate_of = prev.get("obs_id")
            if prev["values"] == current_vals:
                flags.append(IntegrityFlag.DUPLICATE)
                details["duplicate_info"] = "Exact duplicate of prior observation"
            else:
                flags.append(IntegrityFlag.CONFLICTING_DUPLICATE)
                disposition = IntegrityDisposition.QUARANTINE
                details["duplicate_info"] = "Conflicting values for identical timestamp"

        # 4. Temporal Order, Latency, and Missing Slots
        if state.last_event_ts is not None:
            delta_sec = (event_ts - state.last_event_ts).total_seconds()

            if delta_sec < 0:
                # Arrived out of order
                flags.append(IntegrityFlag.LATE_OUT_OF_ORDER)
                disposition = IntegrityDisposition.ACCEPT_LATE
                details["order_issue"] = f"Arrived {abs(delta_sec):.1f}s earlier than last seen event"
            elif delta_sec == 0:
                # Same timestamp (stale or duplicate)
                if IntegrityFlag.DUPLICATE not in flags and IntegrityFlag.CONFLICTING_DUPLICATE not in flags:
                    flags.append(IntegrityFlag.STALE_RETRANSMISSION)
            else:
                # Advancing time: check expected slots
                cadence = self.expected_cadence_seconds
                if delta_sec > 1.5 * cadence:
                    # Missed at least one expected slot
                    missed_count = int(delta_sec // cadence) - 1
                    for step in range(1, missed_count + 1):
                        slot_ts = state.last_event_ts + timedelta(seconds=step * cadence)
                        missing_slots.append(slot_ts)
                    
                    flags.append(IntegrityFlag.MISSING_EXPECTED_RECORD)
                    state.missing_slot_count += missed_count
                    
                    if state.missing_slot_count >= self.communication_gap_slots:
                        flags.append(IntegrityFlag.COMMUNICATION_GAP)
                        details["communication_gap_slots"] = state.missing_slot_count
                else:
                    # Normal advancing slot resets consecutive missing slots
                    state.missing_slot_count = 0

        # Lateness relative to current clock (applies to LIVE stream telemetry)
        if obs.source_type == SourceType.LIVE:
            age_sec = (now_utc - event_ts).total_seconds()
            if age_sec > self.allowed_lateness_seconds:
                late_by_sec = age_sec
                flags.append(IntegrityFlag.DELAYED)
                if disposition == IntegrityDisposition.ACCEPT:
                    disposition = IntegrityDisposition.ACCEPT_LATE

        # 5. Flatline / Stuck candidate checking
        new_flat_runs = dict(state.flat_runs)
        for ch in ["temperature", "pressure", "relative_humidity"]:
            curr = current_vals[ch]
            last = state.last_values.get(ch)
            if curr is not None and last is not None and curr == last:
                new_flat_runs[ch] = new_flat_runs.get(ch, 0) + 1
                if new_flat_runs[ch] >= self.flat_threshold:
                    flags.append(IntegrityFlag.FROZEN_STUCK_CANDIDATE)
                    details[f"frozen_{ch}_run"] = new_flat_runs[ch]
            else:
                new_flat_runs[ch] = 0

        # Update mutable state object
        state.flat_runs = new_flat_runs
        for ch in ["temperature", "pressure", "relative_humidity"]:
            if current_vals[ch] is not None:
                state.last_values[ch] = current_vals[ch]
        
        if state.last_event_ts is None or event_ts > state.last_event_ts:
            state.last_event_ts = event_ts
        state.last_received_ts = now_utc
        state.total_received += 1

        if not flags:
            flags.append(IntegrityFlag.OK)

        return IntegrityResult(
            disposition=disposition,
            flags=flags,
            missing_slots=missing_slots,
            channel_nulls=channel_nulls,
            flat_runs=new_flat_runs,
            late_by_seconds=late_by_sec,
            duplicate_of_observation_id=duplicate_of,
            details=details,
        )


integrity_gate = IntegrityGate()
