"""
Build Demo Snapshot Script for SkyGuard AI.
Exports a read-only compressed deployment snapshot from the local SQLite database
into storage/seeds/demo/<table>.jsonl.gz (one file per table) to bootstrap fresh
cloud deployments (e.g., Render) in a streaming, memory-safe manner.

This script operates in STRICT READ-ONLY mode with respect to data/trusttwin.db.
It NEVER modifies or deletes the local database.

Usage:
    python scripts/build_demo_snapshot.py

Output:
    storage/seeds/demo/stations.jsonl.gz
    storage/seeds/demo/raw_observations.jsonl.gz
    storage/seeds/demo/processed_observations.jsonl.gz
    storage/seeds/demo/decisions.jsonl.gz
    storage/seeds/demo/health_state.jsonl.gz
    storage/seeds/demo/integrity_events.jsonl.gz
    storage/seeds/demo/feature_records.jsonl.gz
    storage/seeds/demo/simulation_runs.jsonl.gz
    storage/seeds/demo/ground_truth_labels.jsonl.gz
"""
import sqlite3
import json
import gzip
import time
from pathlib import Path

# Insert order must respect FK constraints:
#   stations → raw_observations → processed_observations → feature_records
#   processed_observations → decisions
#   raw_observations → integrity_events
TABLES_ORDERED = [
    "stations",
    "raw_observations",
    "processed_observations",
    "feature_records",
    "decisions",
    "health_state",
    "simulation_runs",
    "ground_truth_labels",
    "integrity_events",
]

FETCH_CHUNK = 2000  # rows fetched from SQLite at a time (read-side)


def build_snapshot(db_path: Path = None, output_dir: Path = None) -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    db_file = db_path or (repo_root / "data" / "trusttwin.db")
    out_dir = output_dir or (repo_root / "storage" / "seeds" / "demo")
    stations_fallback = repo_root / "storage" / "seeds" / "stations.json"

    if not db_file.exists():
        raise FileNotFoundError(f"Source database not found at {db_file}")

    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading from source database: {db_file} (Read-Only)...")
    conn = sqlite3.connect(f"file:{db_file.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    total_rows = 0
    stations_data = None

    for table_name in TABLES_ORDERED:
        out_file = out_dir / f"{table_name}.jsonl.gz"
        t0 = time.time()
        row_count = 0

        try:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM {table_name}")

            with gzip.open(out_file, "wt", encoding="utf-8", compresslevel=9) as gz:
                while True:
                    chunk = cur.fetchmany(FETCH_CHUNK)
                    if not chunk:
                        break
                    for row in chunk:
                        gz.write(json.dumps(dict(row), default=str))
                        gz.write("\n")
                        row_count += 1

            elapsed = time.time() - t0
            size_kb = out_file.stat().st_size / 1024
            print(f"  {table_name:28s}: {row_count:7d} rows -> {size_kb:8.1f} KB ({elapsed:.1f}s)")
            total_rows += row_count

            # Capture stations data for fallback seed update
            if table_name == "stations" and row_count > 0:
                conn2 = sqlite3.connect(f"file:{db_file.resolve().as_posix()}?mode=ro", uri=True)
                conn2.row_factory = sqlite3.Row
                stations_data = [dict(r) for r in conn2.execute("SELECT * FROM stations").fetchall()]
                conn2.close()

        except sqlite3.OperationalError as e:
            print(f"  Skipping {table_name} ({e})")

    conn.close()

    # Update the stations.json fallback seed as well
    if stations_data:
        with open(stations_fallback, "w", encoding="utf-8") as f:
            json.dump(stations_data, f, indent=2)
        print(f"\n  Updated fallback stations seed: {stations_fallback} ({len(stations_data)} stations)")

    print(f"\nSuccessfully built per-table JSONL.gz snapshot in: {out_dir}")
    print(f"Total rows exported: {total_rows:,}")
    return out_dir


if __name__ == "__main__":
    build_snapshot()
