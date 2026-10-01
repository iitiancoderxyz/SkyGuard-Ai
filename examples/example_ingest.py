"""
Example script demonstrating direct ingestion of observation through Python engine.
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.schemas.observation import ObservationIn
from app.runtime.engine import process_observation


def main():
    example_file = Path(__file__).parent / "example_observation.json"
    with open(example_file, "r") as f:
        data = json.load(f)

    print("Loaded observation:", data)
    obs = ObservationIn(**data)
    decision = process_observation(obs)
    print("\n--- Decision Result ---")
    print(decision.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
