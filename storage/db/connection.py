import sqlite3
import os
import json
import gzip
from pathlib import Path
from typing import Generator
from contextlib import contextmanager
from app.core.config import settings
from app.core.logging import logger


class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.db_path
        self._ensure_dir()
        self.init_db()

    def _ensure_dir(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(settings.spool_dir).mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path,
            timeout=10.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        # Set WAL mode and busy timeout
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database transaction error: {e}")
            raise
        finally:
            conn.close()

    def init_db(self):
        schema_path = Path(__file__).parent.parent / "schema.sql"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found at {schema_path}")
        
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
            
        with self.transaction() as conn:
            conn.executescript(schema_sql)
            self._migrate_db(conn)
            self._seed_demo_snapshot_if_empty(conn)
        logger.info(f"Database initialized at {self.db_path} with WAL mode")

    def _seed_demo_snapshot_if_empty(self, conn: sqlite3.Connection):
        """
        Seed baseline demo telemetry snapshot on empty database for seamless cloud deployment.
        Loads storage/seeds/demo_snapshot.json.gz if available, or falls back to stations.json.
        """
        cur = conn.execute("SELECT COUNT(*) FROM raw_observations;")
        raw_count = cur.fetchone()[0]
        cur = conn.execute("SELECT COUNT(*) FROM processed_observations;")
        proc_count = cur.fetchone()[0]

        # If observations already exist, do NOT overwrite or re-seed
        if raw_count > 0 or proc_count > 0:
            return

        snapshot_path = Path(__file__).parent.parent / "seeds" / "demo_snapshot.json.gz"
        if snapshot_path.exists():
            try:
                with gzip.open(snapshot_path, "rb") as f:
                    snapshot_data = json.loads(f.read().decode("utf-8"))

                tables_ordered = [
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

                total_inserted = 0
                for table_name in tables_ordered:
                    rows = snapshot_data.get(table_name, [])
                    if not rows:
                        continue
                    cols = list(rows[0].keys())
                    placeholders = ",".join(["?"] * len(cols))
                    sql = f"INSERT OR IGNORE INTO {table_name} ({','.join(cols)}) VALUES ({placeholders})"
                    records = [[r.get(c) for c in cols] for r in rows]
                    conn.executemany(sql, records)
                    total_inserted += len(records)
                logger.info(f"Successfully seeded demo snapshot into fresh database ({total_inserted} records across {len(tables_ordered)} tables)")
                return
            except Exception as e:
                logger.error(f"Failed to load demo snapshot: {e}")

        # Fallback to station-only seed if snapshot is unavailable
        self._seed_stations_fallback(conn)

    def _seed_stations_fallback(self, conn: sqlite3.Connection):
        """Fallback seed station metadata if snapshot is absent."""
        cur = conn.execute("SELECT COUNT(*) FROM stations;")
        count = cur.fetchone()[0]
        if count > 0:
            return

        seed_path = Path(__file__).parent.parent / "seeds" / "stations.json"
        if not seed_path.exists():
            return

        try:
            with open(seed_path, "r", encoding="utf-8") as f:
                stations_data = json.load(f)

            if isinstance(stations_data, list) and stations_data:
                sql = """
                INSERT OR IGNORE INTO stations (
                    station_id, latitude, longitude, elevation,
                    expected_cadence_seconds, allowed_lateness_seconds,
                    communication_gap_slots, config_version, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                records = [
                    (
                        s.get("station_id"),
                        s.get("latitude"),
                        s.get("longitude"),
                        s.get("elevation"),
                        s.get("expected_cadence_seconds", 60),
                        s.get("allowed_lateness_seconds", 120),
                        s.get("communication_gap_slots", 3),
                        s.get("config_version", "v1"),
                        s.get("status", "ACTIVE"),
                    )
                    for s in stations_data
                    if s.get("station_id")
                ]
                conn.executemany(sql, records)
                logger.info(f"Seeded {len(records)} stations from fallback seed")
        except Exception as e:
            logger.error(f"Failed to seed fallback stations: {e}")

    def _migrate_db(self, conn: sqlite3.Connection):
        """Safely ensure all required columns exist in existing SQLite tables."""
        cur = conn.execute("PRAGMA table_info(decisions);")
        existing_cols = {row["name"] for row in cur.fetchall()}
        
        needed_cols = {
            "decision_state": "TEXT DEFAULT 'NORMAL'",
            "reasoning_summary": "TEXT",
            "evidence_codes_json": "TEXT",
            "plausibility_score": "REAL",
            "weather_event_likelihood": "REAL",
            "sensor_fault_likelihood": "REAL",
        }
        
        for col, col_type in needed_cols.items():
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE decisions ADD COLUMN {col} {col_type};")
                logger.info(f"Migrated decisions table: added column {col} {col_type}")


db = Database()


def get_db() -> Database:
    return db
