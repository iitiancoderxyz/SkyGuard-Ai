"""
Ground truth and simulation repository.
Strictly used for evaluation / benchmark sidecars, never queried by the runtime detection engine (INV-03).
"""
import uuid
from typing import Optional, List, Dict, Any
from storage.db.connection import db


class GroundTruthRepository:
    def __init__(self, database=None):
        self.db = database or db

    def save_simulation_run(
        self,
        run_id: str,
        scenario_name: str,
        station_id: str,
        start_time: str,
        end_time: Optional[str],
        seed: int,
        status: str = "COMPLETED",
    ):
        sql = """
        INSERT INTO simulation_runs (
            run_id, scenario_name, station_id, start_time, end_time, seed, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        with self.db.transaction() as conn:
            conn.execute(
                sql,
                (run_id, scenario_name, station_id, start_time, end_time, seed, status),
            )

    def save_ground_truth_label(
        self,
        run_id: str,
        station_id: str,
        event_timestamp: str,
        label_type: str,
        fault_class: Optional[str] = None,
        channel: Optional[str] = None,
        onset: Optional[str] = None,
        offset: Optional[str] = None,
        injection_id: Optional[str] = None,
        source_observation_id: Optional[str] = None,
        label_source: str = "INJECTION_MANIFEST",
        seed: Optional[int] = None,
    ) -> str:
        label_id = f"lbl-{uuid.uuid4().hex[:12]}"
        sql = """
        INSERT INTO ground_truth_labels (
            label_id, run_id, station_id, event_timestamp,
            label_type, fault_class, channel, onset, offset,
            injection_id, source_observation_id, label_source, seed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self.db.transaction() as conn:
            conn.execute(
                sql,
                (
                    label_id,
                    run_id,
                    station_id,
                    event_timestamp,
                    label_type,
                    fault_class,
                    channel,
                    onset,
                    offset,
                    injection_id,
                    source_observation_id,
                    label_source,
                    seed,
                ),
            )
        return label_id

    def get_labels_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM ground_truth_labels WHERE run_id = ? ORDER BY event_timestamp ASC"
        with self.db.transaction() as conn:
            cur = conn.execute(sql, (run_id,))
            return [dict(row) for row in cur.fetchall()]


ground_truth_repo = GroundTruthRepository()
