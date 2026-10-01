"""
Unit tests for station metadata seeding mechanism.
Verifies that a fresh database initializes with all seed stations and does not duplicate on repeat init.
"""
import pytest
import sqlite3
import tempfile
from pathlib import Path
from storage.db.connection import Database
from storage.repositories.station_repo import StationRepository


def test_station_seed_on_empty_database():
    """Verify that a fresh SQLite database automatically populates the 658 seed stations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db_path = str(Path(tmpdir) / "test_seed.db")

        # Initialize fresh database
        test_db = Database(db_path=tmp_db_path)

        repo = StationRepository(database=test_db)
        stations = repo.list_stations()

        assert len(stations) == 658
        station_ids = [s["station_id"] for s in stations]
        assert "AWS-001" in station_ids
        assert "AWS_DEMO_01" in station_ids
        assert "AWS_DEMO_SPIKE" in station_ids
        assert "AWS_DEMO_GENUINE_WEATHER" in station_ids


def test_station_seed_idempotency_no_duplicates():
    """Verify that repeat initialization does not duplicate stations or error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db_path = str(Path(tmpdir) / "test_seed_repeat.db")

        # 1. First initialization
        test_db = Database(db_path=tmp_db_path)
        repo = StationRepository(database=test_db)
        assert len(repo.list_stations()) == 658

        # 2. Second initialization on existing populated DB
        test_db.init_db()
        assert len(repo.list_stations()) == 658


def test_local_database_station_count():
    """Verify that the primary local database maintains all seed stations."""
    from storage.repositories.station_repo import station_repo
    stations = station_repo.list_stations()
    assert len(stations) >= 658
    station_ids = {s["station_id"] for s in stations}
    assert "AWS-001" in station_ids
    assert "AWS_DEMO_01" in station_ids
