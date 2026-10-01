"""
Structured logging configuration.
"""
import logging
import sys
import json
from datetime import datetime, timezone
from app.core.config import settings


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "station_id"):
            log_entry["station_id"] = record.station_id
        if hasattr(record, "obs_id"):
            log_entry["obs_id"] = record.obs_id
        if hasattr(record, "episode_id"):
            log_entry["episode_id"] = record.episode_id
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_logging():
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"))
    
    # Remove existing handlers
    root.handlers.clear()
    root.addHandler(handler)


logger = logging.getLogger("trusttwin")
