"""
Unit tests for Dashboard APIClient configuration and base URL resolution.
Verifies environment-variable based configuration (SKYGUARD_API_URL) and safe endpoint construction.
"""
import pytest
from dashboard.api_client import APIClient, DEFAULT_API_BASE_URL


def test_api_client_default_url(monkeypatch):
    """Verify default base URL is http://127.0.0.1:8000 when no env var is set."""
    monkeypatch.delenv("SKYGUARD_API_URL", raising=False)
    client = APIClient()
    assert client.base_url == "http://127.0.0.1:8000"
    assert client.base_url == DEFAULT_API_BASE_URL


def test_api_client_env_override(monkeypatch):
    """Verify SKYGUARD_API_URL environment variable overrides the default."""
    monkeypatch.setenv("SKYGUARD_API_URL", "https://skyguard-api.onrender.com")
    client = APIClient()
    assert client.base_url == "https://skyguard-api.onrender.com"


def test_api_client_env_trailing_slash_stripped(monkeypatch):
    """Verify trailing slashes in SKYGUARD_API_URL are cleanly stripped to prevent double slashes."""
    monkeypatch.setenv("SKYGUARD_API_URL", "https://skyguard-api.onrender.com///")
    client = APIClient()
    assert client.base_url == "https://skyguard-api.onrender.com"


def test_api_client_env_whitespace_stripped(monkeypatch):
    """Verify leading/trailing whitespace in SKYGUARD_API_URL is stripped."""
    monkeypatch.setenv("SKYGUARD_API_URL", "  https://skyguard-api.onrender.com/  ")
    client = APIClient()
    assert client.base_url == "https://skyguard-api.onrender.com"


def test_api_client_explicit_arg_overrides_env(monkeypatch):
    """Verify explicitly passed base_url takes precedence over env var."""
    monkeypatch.setenv("SKYGUARD_API_URL", "https://env-url.example.com")
    client = APIClient(base_url="https://explicit-url.example.com/")
    assert client.base_url == "https://explicit-url.example.com"


def test_api_client_empty_env_fallback(monkeypatch):
    """Verify empty string in SKYGUARD_API_URL safely falls back to default."""
    monkeypatch.setenv("SKYGUARD_API_URL", "")
    client = APIClient()
    assert client.base_url == "http://127.0.0.1:8000"
