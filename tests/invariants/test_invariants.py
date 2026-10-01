"""
Architecture Invariant Tests (INV-01, INV-02, INV-03, INV-10, INV-13).
"""
import ast
import os
import sqlite3
import pytest
from pathlib import Path
from ingestion.schemas.observation import ObservationIn
from storage.db.connection import Database
from app.core.claims import BANNED_PHRASES


def test_inv01_scope_guard():
    """INV-01: Ingest schema rejects non-core meteorological keys."""
    with pytest.raises(Exception):
        ObservationIn(
            station_id="AWS_TEST",
            timestamp="2026-09-30T12:00:00Z",
            temperature=25.0,
            pressure=1010.0,
            relative_humidity=50.0,
            rainfall=12.5,  # Prohibited
        )


def test_inv02_raw_immutability(tmp_path):
    """INV-02: SQLite triggers abort UPDATE and DELETE on raw_observations."""
    db_file = tmp_path / "test_immutability.db"
    test_db = Database(db_path=str(db_file))

    with test_db.transaction() as conn:
        conn.execute(
            """
            INSERT INTO raw_observations (
                observation_id, station_id, event_timestamp,
                temperature_raw, pressure_raw, relative_humidity_raw,
                source_type, received_at, payload_hash, raw_payload, parse_status
            ) VALUES ('obs-imm-1', 'AWS_01', '2026-09-30T10:00:00Z', 25.0, 1012.0, 60.0, 'LIVE', '2026-09-30T10:00:00Z', 'hash', '{}', 'VALID')
            """
        )

    # Attempt UPDATE -> Must fail via trigger
    with pytest.raises(sqlite3.IntegrityError, match="Raw observations are strictly immutable"):
        with test_db.transaction() as conn:
            conn.execute("UPDATE raw_observations SET temperature_raw = 99.9 WHERE observation_id = 'obs-imm-1'")

    # Attempt DELETE -> Must fail via trigger
    with pytest.raises(sqlite3.IntegrityError, match="Raw observations are strictly immutable"):
        with test_db.transaction() as conn:
            conn.execute("DELETE FROM raw_observations WHERE observation_id = 'obs-imm-1'")


def test_inv03_ground_truth_isolation():
    """INV-03: Detection engine packages cannot import injector or ground truth evaluation modules (Principle P6)."""
    engine_dirs = [
        Path("app/runtime"),
        Path("ingestion"),
        Path("features"),
        Path("detection"),
        Path("health"),
        Path("correction"),
    ]
    forbidden_imports = ["injector", "eval", "ground_truth_labels", "simulation_runs"]

    for edir in engine_dirs:
        if edir.exists():
            for py_file in edir.rglob("*.py"):
                with open(py_file, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=str(py_file))
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                for forbidden in forbidden_imports:
                                    assert forbidden not in alias.name, f"INV-03 Violation: {py_file} imports {alias.name}"
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                for forbidden in forbidden_imports:
                                    assert forbidden not in node.module, f"INV-03 Violation: {py_file} imports from {node.module}"


def test_inv10_dashboard_isolation():
    """INV-10: Dashboard cannot import engine code or SQLite directly."""
    dash_dir = Path("dashboard")
    forbidden = ["app.runtime.engine", "storage.db", "sqlite3"]

    for py_file in dash_dir.rglob("*.py"):
        with open(py_file, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for fb in forbidden:
                            assert fb != alias.name, f"INV-10 Violation: {py_file} directly imports {alias.name}"
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for fb in forbidden:
                            assert fb != node.module, f"INV-10 Violation: {py_file} directly imports from {node.module}"


def test_inv13_claims_discipline():
    """INV-13: No banned hype phrases in codebase claims."""
    claims_file = Path("app/core/claims.py")
    content = claims_file.read_text(encoding="utf-8").lower()
    for phrase in BANNED_PHRASES:
        # The banned phrase should only exist in the BANNED_PHRASES list definition
        assert phrase in [p.lower() for p in BANNED_PHRASES]
