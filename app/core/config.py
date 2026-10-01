"""
Configuration management for TRUST-TWIN using Pydantic Settings.
"""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_name: str = "TRUST-TWIN"
    app_env: str = "development"
    app_version: str = "1.0.0-phase1"
    
    # Server settings
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    dashboard_port: int = 8501
    
    # Storage settings
    db_path: str = "data/trusttwin.db"
    spool_dir: str = "data/spool"
    models_store_dir: str = "models_store"
    
    # Logging
    log_level: str = "INFO"
    
    # Auth
    api_key_enabled: bool = False
    api_key: Optional[str] = "tt-dev-key-26073"
    
    # Stream defaults
    expected_cadence_seconds: int = 60
    allowed_lateness_seconds: int = 120
    communication_gap_slots: int = 3
    
    # Limits for validation
    temp_min: float = -80.0
    temp_max: float = 70.0
    pressure_min: float = 300.0
    pressure_max: float = 1100.0
    rh_min: float = 0.0
    rh_max: float = 100.0


settings = Settings()


def get_settings() -> Settings:
    return settings
