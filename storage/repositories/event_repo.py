"""
Repository for recording integrity events, audit logs, and provenance.
"""
import uuid
import json
from typing import Optional, List, Dict, Any
from storage.db.connection import db


class EventRepository:
    def __init__(self, database=None):
        self.db = database or db

    def save_integrity_event(
        self,
        station_id: str,
        event_type: str,
        observation_id: Optional[str] = None,
        event_timestamp: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        event_id = f"evt-{uuid.uuid4().hex[:12]}"
        sql = """
        INSERT INTO integrity_events (
            integrity_event_id, observation_id, station_id,
            event_timestamp, event_type, details
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
        with self.db.transaction() as conn:
            conn.execute(
                sql,
                (
                    event_id,
                    observation_id,
                    station_id,
                    event_timestamp,
                    event_type,
                    json.dumps(details or {}),
                ),
            )
        return event_id

    def get_integrity_events(self, station_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        sql = """
        SELECT * FROM integrity_events
        WHERE station_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """
        with self.db.transaction() as conn:
            cur = conn.execute(sql, (station_id, limit))
            return [dict(row) for row in cur.fetchall()]


event_repo = EventRepository()
