"""
Feature repository for persisting versioned derived feature records.
"""
import uuid
import json
from typing import Optional, Dict, Any, List
from storage.db.connection import db


class FeatureRepository:
    def __init__(self, database=None):
        self.db = database or db

    def save_feature_record(
        self,
        observation_id: str,
        features: Dict[str, Any],
        feature_version: str = "f1",
    ) -> str:
        feat_id = f"feat-{uuid.uuid4().hex[:12]}"
        sql = """
        INSERT INTO feature_records (
            feature_id, observation_id, feature_version,
            derived_dewpoint, derived_vapour_pressure, features_json
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
        with self.db.transaction() as conn:
            conn.execute(
                sql,
                (
                    feat_id,
                    observation_id,
                    feature_version,
                    features.get("derived_dewpoint_c"),
                    features.get("derived_vapour_pressure_hpa"),
                    json.dumps(features),
                ),
            )
        return feat_id

    def get_features_by_observation_id(self, observation_id: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM feature_records WHERE observation_id = ?"
        with self.db.transaction() as conn:
            cur = conn.execute(sql, (observation_id,))
            row = cur.fetchone()
            if row:
                d = dict(row)
                if d.get("features_json"):
                    d["features"] = json.loads(d["features_json"])
                return d
            return None


feature_repo = FeatureRepository()
