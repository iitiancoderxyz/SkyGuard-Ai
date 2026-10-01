"""
Unit and integration tests for SkyGuard AI demo snapshot loading and deployment bootstrapping.

Verifies that:
 - A fresh database initialises with full demo telemetry from per-table JSONL.gz files
   under storage/seeds/demo/
 - Loading is idempotent (re-running init_db never duplicates rows)
 - Existing databases with live telemetry are never overwritten
 - Batch-streaming behaviour: SEED_BATCH_SIZE constant is ≤ 1000 (memory-safety contract)
 - Repository queries return expected records against the seeded database
 - Sensor health state is present for demo stations
"""
import pytest
import tempfile
from pathlib import Path
from storage.db.connection import Database
from storage.repositories.station_repo import StationRepository
from storage.repositories.observation_repo import ObservationRepository
from storage.repositories.event_repo import EventRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fresh_seeded_db():
    """Create a temporary fresh database that initialises from storage/seeds/demo/*.jsonl.gz."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db_path = str(Path(tmpdir) / "fresh_demo_test.db")
        db_instance = Database(db_path=tmp_db_path)
        yield db_instance


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_fresh_database_loads_full_demo_snapshot(fresh_seeded_db):
    """Verify all tables load their exact counts into a fresh database."""
    with fresh_seeded_db.transaction() as conn:
        counts = {
            "stations": conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0],
            "raw_observations": conn.execute("SELECT COUNT(*) FROM raw_observations").fetchone()[0],
            "processed_observations": conn.execute("SELECT COUNT(*) FROM processed_observations").fetchone()[0],
            "decisions": conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0],
            "health_state": conn.execute("SELECT COUNT(*) FROM health_state").fetchone()[0],
        }

    assert counts["stations"] == 658
    assert counts["raw_observations"] == 24758
    assert counts["processed_observations"] == 24750
    assert counts["decisions"] == 24745
    assert counts["health_state"] == 966


def test_batch_size_is_memory_safe():
    """Confirm SEED_BATCH_SIZE contract: must be ≤ 1000 to stay within Render Free RAM budget."""
    assert Database._SEED_BATCH_SIZE <= 1000, (
        f"SEED_BATCH_SIZE={Database._SEED_BATCH_SIZE} exceeds 1000 — "
        "this risks Render Free 512 MB OOM during seeding."
    )
    assert Database._SEED_BATCH_SIZE >= 100, (
        f"SEED_BATCH_SIZE={Database._SEED_BATCH_SIZE} is suspiciously small; "
        "should be ≥ 100 for reasonable seeding throughput."
    )


def test_seed_dir_contains_required_files():
    """Verify that the required per-table JSONL.gz files exist in storage/seeds/demo/."""
    seed_dir = Path(__file__).resolve().parents[2] / "storage" / "seeds" / "demo"
    assert seed_dir.exists(), (
        f"Demo seed directory missing: {seed_dir}\n"
        "Run: python scripts/build_demo_snapshot.py"
    )
    required_tables = [
        "stations",
        "raw_observations",
        "processed_observations",
        "decisions",
        "health_state",
    ]
    for table in required_tables:
        seed_file = seed_dir / f"{table}.jsonl.gz"
        assert seed_file.exists(), f"Required seed file missing: {seed_file.name}"
        assert seed_file.stat().st_size > 0, f"Seed file is empty: {seed_file.name}"


def test_snapshot_seeding_idempotency(fresh_seeded_db):
    """Verify repeat init_db does not duplicate or corrupt seeded records."""
    fresh_seeded_db.init_db()

    with fresh_seeded_db.transaction() as conn:
        st_cnt = conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
        raw_cnt = conn.execute("SELECT COUNT(*) FROM raw_observations").fetchone()[0]
        proc_cnt = conn.execute("SELECT COUNT(*) FROM processed_observations").fetchone()[0]
        dec_cnt = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]

    assert st_cnt == 658
    assert raw_cnt == 24758
    assert proc_cnt == 24750
    assert dec_cnt == 24745


def test_existing_database_not_overwritten():
    """Verify a database that already has telemetry is not modified by a repeat init_db call.

    Flow:
    1. Database() constructor is called on an empty DB → seeds 24,758 raw_observations.
    2. Test inserts 1 additional custom observation (total = 24,759).
    3. init_db() is called again → must detect raw_count > 0 and skip seeding entirely.
    4. raw_count must remain exactly 24,759 (no rows added or removed).
    5. Custom station must still be present.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db_path = str(Path(tmpdir) / "custom_existing.db")

        # 1. Constructor seeds the DB with the full demo snapshot
        db_inst = Database(db_path=tmp_db_path)

        # Capture count immediately after seeding
        with db_inst.transaction() as conn:
            count_after_seed = conn.execute("SELECT COUNT(*) FROM raw_observations").fetchone()[0]

        # 2. Insert 1 additional custom record on top of the seeded data
        with db_inst.transaction() as conn:
            conn.execute("INSERT OR REPLACE INTO stations (station_id) VALUES ('AWS_CUSTOM_ONLY')")
            conn.execute("""
                INSERT OR REPLACE INTO raw_observations (
                    observation_id, station_id, event_timestamp, temperature_raw,
                    pressure_raw, relative_humidity_raw, source_type, received_at,
                    payload_hash, raw_payload, parse_status
                ) VALUES (
                    'OBS_CUSTOM_01', 'AWS_CUSTOM_ONLY', '2026-10-01T12:00:00Z',
                    25.0, 1013.0, 60.0, 'LIVE', '2026-10-01T12:00:01Z',
                    'hash123', '{"test": 1}', 'VALID'
                )
            """)
            conn.execute("""
                INSERT OR REPLACE INTO processed_observations (
                    observation_id, station_id, event_timestamp, temperature,
                    pressure, relative_humidity
                ) VALUES (
                    'OBS_CUSTOM_01', 'AWS_CUSTOM_ONLY', '2026-10-01T12:00:00Z',
                    25.0, 1013.0, 60.0
                )
            """)

        # 3. Re-run init_db — must be a no-op since observations exist
        db_inst.init_db()

        with db_inst.transaction() as c:
            raw_count = c.execute("SELECT COUNT(*) FROM raw_observations").fetchone()[0]

        # 4. Count must be exactly seed count + 1 custom row (no duplicate seeding)
        expected_count = count_after_seed + 1
        assert raw_count == expected_count, (
            f"Expected exactly {expected_count} raw_observations (seeded {count_after_seed} + 1 custom), "
            f"got {raw_count}. Second init_db() must not re-seed."
        )

        # 5. Custom station must be preserved
        st_repo = StationRepository(database=db_inst)
        assert "AWS_CUSTOM_ONLY" in [s["station_id"] for s in st_repo.list_stations()]


def test_repository_queries_on_seeded_database(fresh_seeded_db):
    """Verify ObservationRepository, EventRepository, and StationRepository return expected data."""
    st_repo = StationRepository(database=fresh_seeded_db)
    obs_repo = ObservationRepository(database=fresh_seeded_db)
    ev_repo = EventRepository(database=fresh_seeded_db)

    # 1. Station list
    stations = st_repo.list_stations()
    assert len(stations) == 658
    st_ids = {s["station_id"] for s in stations}
    assert "AWS_DEMO_SPIKE" in st_ids
    assert "AWS_P3_WEATHER" in st_ids

    # 2. Historical observations query with decision join
    spike_obs = obs_repo.get_recent_observations(station_id="AWS_DEMO_SPIKE", limit=50)
    assert len(spike_obs) > 0
    assert spike_obs[0]["station_id"] == "AWS_DEMO_SPIKE"
    assert "temperature" in spike_obs[0]
    assert "anomaly_score" in spike_obs[0]

    # 3. Decision listing
    decisions = obs_repo.get_recent_decisions(limit=50)
    assert len(decisions) == 50

    # 4. Integrity events query
    events = ev_repo.get_integrity_events(station_id="AWS_DEMO_SPIKE", limit=10)
    assert isinstance(events, list)


def test_health_diagnostics_on_seeded_station(fresh_seeded_db):
    """Verify sensor health states exist and are queryable for seeded stations."""
    with fresh_seeded_db.transaction() as conn:
        health_rows = conn.execute(
            "SELECT * FROM health_state WHERE station_id = 'AWS_DEMO_SPIKE'"
        ).fetchall()
        assert len(health_rows) > 0
        channels = [r["channel"] for r in health_rows]
        assert any(ch in channels for ch in ("temperature", "pressure", "relative_humidity"))
