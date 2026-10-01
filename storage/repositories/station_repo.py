"""
Station repository for managing AWS metadata and configuration.
"""
from typing import Optional, List, Dict, Any
from storage.db.connection import db


class StationRepository:
    def __init__(self, database=None):
        self.db = database or db

    def upsert_station(
        self,
        station_id: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        elevation: Optional[float] = None,
        expected_cadence_seconds: int = 60,
        allowed_lateness_seconds: int = 120,
        communication_gap_slots: int = 3,
        status: str = "ACTIVE",
    ):
        sql = """
        INSERT INTO stations (
            station_id, latitude, longitude, elevation,
            expected_cadence_seconds, allowed_lateness_seconds, communication_gap_slots, status, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(station_id) DO UPDATE SET
            latitude=COALESCE(excluded.latitude, stations.latitude),
            longitude=COALESCE(excluded.longitude, stations.longitude),
            elevation=COALESCE(excluded.elevation, stations.elevation),
            expected_cadence_seconds=excluded.expected_cadence_seconds,
            allowed_lateness_seconds=excluded.allowed_lateness_seconds,
            communication_gap_slots=excluded.communication_gap_slots,
            status=excluded.status,
            updated_at=CURRENT_TIMESTAMP
        """
        with self.db.transaction() as conn:
            conn.execute(
                sql,
                (
                    station_id,
                    latitude,
                    longitude,
                    elevation,
                    expected_cadence_seconds,
                    allowed_lateness_seconds,
                    communication_gap_slots,
                    status,
                ),
            )

    def get_station(self, station_id: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM stations WHERE station_id = ?"
        with self.db.transaction() as conn:
            cur = conn.execute(sql, (station_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_stations(self) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM stations ORDER BY station_id ASC"
        with self.db.transaction() as conn:
            cur = conn.execute(sql)
            return [dict(row) for row in cur.fetchall()]


station_repo = StationRepository()
