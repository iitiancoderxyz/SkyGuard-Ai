"""
Phase 1 Foundation Demo Script.
Generates synthetic data, applies fault injection, executes replay through process_observation,
and verifies storage and integrity results.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone
from simulator.stream.generator import AWSStreamGenerator
from simulator.replay.replayer import StreamReplayer
from injector.faults.injector import FaultInjector
from storage.repositories.station_repo import station_repo
from storage.repositories.observation_repo import obs_repo
from storage.repositories.event_repo import event_repo


def run_demo():
    print("=== TRUST-TWIN Phase 1 Foundation Demonstration ===")
    
    # 1. Generate clean sequence
    generator = AWSStreamGenerator(station_id="AWS_DEMO_01", seed=42)
    start_ts = datetime(2026, 9, 30, 8, 0, 0, tzinfo=timezone.utc)
    clean_obs = generator.generate(start_time=start_ts, num_points=10)
    print(f"1. Generated {len(clean_obs)} clean observations for station {clean_obs[0].station_id}")

    # 2. Inject an impulsive spike fault
    injector = FaultInjector(seed=42)
    injected_obs, manifest = injector.inject_spike(clean_obs, index=5, channel="temperature", magnitude=35.0)
    print(f"2. Injected spike fault at index 5 (Manifest ID: {manifest['injection_id']}, Class: {manifest['fault_class']})")

    # 3. Replay through the single engine entry point
    replayer = StreamReplayer()
    print("3. Replaying stream through process_observation()...")
    decisions = replayer.replay(injected_obs)
    
    print(f"4. Successfully processed {len(decisions)} observations.")
    print("   Sample decisions:")
    for i, dec in enumerate(decisions):
        print(f"   Slot {i:02d} [{dec.event_timestamp.strftime('%H:%M:%S')}]: Temp={injected_obs[i].temperature}°C, Disposition={dec.disposition}, Flags={[f.value for f in dec.integrity_flags]}")

    # 5. Check persistence
    recent = obs_repo.get_recent_observations(station_id="AWS_DEMO_01", limit=10)
    events = event_repo.get_integrity_events(station_id="AWS_DEMO_01", limit=10)
    print(f"5. Database verification: {len(recent)} observations in processed_observations, {len(events)} integrity events recorded.")
    print("=== Phase 1 Demonstration Completed Successfully ===")


if __name__ == "__main__":
    run_demo()
