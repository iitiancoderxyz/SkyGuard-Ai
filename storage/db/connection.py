"""
SQLite database manager with WAL mode and transaction support.
"""
import sqlite3
import os
import json
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
            self._seed_stations_if_empty(conn)
        logger.info(f"Database initialized at {self.db_path} with WAL mode")

    def _seed_stations_if_empty(self, conn: sqlite3.Connection):
        """Seed station metadata on empty database to preserve default network stations."""
        cur = conn.execute("SELECT COUNT(*) FROM stations;")
        count = cur.fetchone()[0]
        if count > 0:
            return  # Already populated, never duplicate

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
                logger.info(f"Seeded {len(records)} stations into fresh database")
        except Exception as e:
            logger.error(f"Failed to seed stations: {e}")

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
