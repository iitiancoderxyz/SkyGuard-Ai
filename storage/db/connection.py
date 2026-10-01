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

    # Insert order must respect FK constraints:
    #   stations → raw_observations → processed_observations → feature_records
    #   processed_observations → decisions
    #   raw_observations → integrity_events
    _SEED_TABLES_ORDERED = [
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
    _SEED_BATCH_SIZE = 500  # rows inserted per executemany call — keeps RAM <10 MB peak
    _SEED_DIR = Path(__file__).parent.parent / "seeds" / "demo"

    def _seed_demo_snapshot_if_empty(self, conn: sqlite3.Connection):
        """
        Seed baseline demo telemetry snapshot on empty database for seamless cloud deployment.

        Loads one per-table JSONL.gz file at a time from storage/seeds/demo/<table>.jsonl.gz,
        streaming rows in batches of _SEED_BATCH_SIZE to stay well inside Render Free 512 MB RAM.
        Falls back to stations.json if the demo/ directory is absent.
        """
        raw_count = conn.execute("SELECT COUNT(*) FROM raw_observations;").fetchone()[0]
        proc_count = conn.execute("SELECT COUNT(*) FROM processed_observations;").fetchone()[0]

        # If observations already exist, do NOT overwrite or re-seed
        if raw_count > 0 or proc_count > 0:
            return

        seed_dir = self._SEED_DIR
        if not seed_dir.exists():
            logger.warning(
                f"Demo seed directory not found at {seed_dir}. Falling back to station-only seed."
            )
            self._seed_stations_fallback(conn)
            return

        total_inserted = 0
        tables_loaded = 0

        for table_name in self._SEED_TABLES_ORDERED:
            file_path = seed_dir / f"{table_name}.jsonl.gz"
            if not file_path.exists():
                logger.debug(f"Seed file absent, skipping: {file_path.name}")
                continue

            try:
                table_rows = 0
                batch: list = []

                with gzip.open(file_path, "rt", encoding="utf-8") as gz_f:
                    for line in gz_f:
                        line = line.strip()
                        if not line:
                            continue
                        batch.append(json.loads(line))
                        if len(batch) >= self._SEED_BATCH_SIZE:
                            inserted = self._insert_seed_batch(conn, table_name, batch)
                            table_rows += inserted
                            batch = []

                    # Flush remaining rows
                    if batch:
                        table_rows += self._insert_seed_batch(conn, table_name, batch)

                total_inserted += table_rows
                tables_loaded += 1
                logger.debug(f"Seeded {table_rows:,} rows into {table_name}")

            except Exception as e:
                logger.error(f"Failed to seed {table_name} from {file_path.name}: {e}")

        if total_inserted > 0:
            logger.info(
                f"Successfully seeded demo snapshot ({total_inserted:,} rows across "
                f"{tables_loaded} tables) from {seed_dir}"
            )
        else:
            logger.warning("Demo seed directory present but no rows inserted; falling back to stations.json.")
            self._seed_stations_fallback(conn)

    @staticmethod
    def _insert_seed_batch(conn: sqlite3.Connection, table_name: str, batch: list) -> int:
        """Insert a batch of row dicts into table_name using INSERT OR IGNORE. Returns rows inserted."""
        if not batch:
            return 0
        cols = list(batch[0].keys())
        placeholders = ",".join(["?"] * len(cols))
        sql = f"INSERT OR IGNORE INTO {table_name} ({','.join(cols)}) VALUES ({placeholders})"
        records = [[row.get(c) for c in cols] for row in batch]
        conn.executemany(sql, records)
        return len(records)

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
