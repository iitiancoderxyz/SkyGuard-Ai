"""
Build Demo Snapshot Script for SkyGuard AI.
Exports a read-only compressed deployment snapshot from the local SQLite database
into storage/seeds/demo_snapshot.json.gz to bootstrap fresh cloud deployments (e.g., Render).

This script operates in STRICT READ-ONLY mode with respect to data/trusttwin.db.
It NEVER modifies or deletes the local database.
"""
import sqlite3
import json
import gzip
import time
from pathlib import Path

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


def build_snapshot(db_path: Path = None, output_path: Path = None) -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    db_file = db_path or (repo_root / "data" / "trusttwin.db")
    out_file = output_path or (repo_root / "storage" / "seeds" / "demo_snapshot.json.gz")
    stations_fallback = repo_root / "storage" / "seeds" / "stations.json"

    if not db_file.exists():
        raise FileNotFoundError(f"Source database not found at {db_file}")

    print(f"Reading from source database: {db_file} (Read-Only)...")
    conn = sqlite3.connect(f"file:{db_file.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    data_export = {}
    for table_name in TABLES_ORDERED:
        try:
            cur.execute(f"SELECT * FROM {table_name}")
            rows = [dict(r) for r in cur.fetchall()]
            data_export[table_name] = rows
            print(f"  Exported {table_name:25s}: {len(rows):7d} rows")
        except sqlite3.OperationalError as e:
            print(f"  Skipping {table_name} ({e})")
    conn.close()

    # Ensure output directory exists
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Write compressed snapshot
    t0 = time.time()
    raw_json_bytes = json.dumps(data_export, default=str).encode("utf-8")
    with gzip.open(out_file, "wb", compresslevel=9) as f:
        f.write(raw_json_bytes)
    t_elapsed = time.time() - t0

    # Also update stations.json fallback
    if "stations" in data_export:
        with open(stations_fallback, "w", encoding="utf-8") as f:
            json.dump(data_export["stations"], f, indent=2)
        print(f"  Updated fallback stations seed: {stations_fallback} ({len(data_export['stations'])} stations)")

    compressed_mb = out_file.stat().st_size / (1024 * 1024)
    print(f"\nSuccessfully built demo snapshot: {out_file}")
    print(f"Size: {compressed_mb:.2f} MB ({out_file.stat().st_size:,} bytes) in {t_elapsed:.2f}s")
    return out_file


if __name__ == "__main__":
    build_snapshot()
