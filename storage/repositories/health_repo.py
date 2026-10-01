"""
Health state repository for persisting and querying sensor health assessments.
"""
from typing import Optional, List, Dict, Any
from storage.db.connection import db


class HealthRepository:
    def __init__(self, database=None):
        self.db = database or db

    def save_health_state(
        self,
        station_id: str,
        channel: str,
        state: str = "HEALTHY",
        health_score: Optional[float] = 1.0,
        degradation_state: str = "NO_DEGRADATION_EVIDENCE",
        maintenance_state: str = "NONE",
        evidence_window_start: Optional[str] = None,
        evidence_window_end: Optional[str] = None,
        model_integrity_state: str = "OK",
    ):
        sql = """
        INSERT INTO health_state (
            station_id, channel, state, health_score,
            degradation_state, maintenance_state, evidence_window_start,
            evidence_window_end, model_integrity_state, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(station_id, channel) DO UPDATE SET
            state=excluded.state,
            health_score=excluded.health_score,
            degradation_state=excluded.degradation_state,
            maintenance_state=excluded.maintenance_state,
            evidence_window_start=excluded.evidence_window_start,
            evidence_window_end=excluded.evidence_window_end,
            model_integrity_state=excluded.model_integrity_state,
            updated_at=CURRENT_TIMESTAMP
        """
        with self.db.transaction() as conn:
            conn.execute(
                sql,
                (
                    station_id,
                    channel,
                    state,
                    health_score,
                    degradation_state,
                    maintenance_state,
                    evidence_window_start,
                    evidence_window_end,
                    model_integrity_state,
                ),
            )

    def get_health_states(self, station_id: str) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM health_state WHERE station_id = ? ORDER BY channel ASC"
        with self.db.transaction() as conn:
            cur = conn.execute(sql, (station_id,))
            return [dict(row) for row in cur.fetchall()]

    def get_all_health_states(self) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM health_state ORDER BY station_id ASC, channel ASC"
        with self.db.transaction() as conn:
            cur = conn.execute(sql)
            return [dict(row) for row in cur.fetchall()]


health_repo = HealthRepository()
