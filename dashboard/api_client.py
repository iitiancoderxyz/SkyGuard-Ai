"""
Dashboard API Client: Communicates with FastAPI backend over HTTP.
Invariant INV-10: Never imports engine code or opens SQLite directly.
"""
import requests
from typing import Dict, Any, List, Optional


class APIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")

    def get_health(self) -> Dict[str, Any]:
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=3.0)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"status": "UNAVAILABLE", "error": str(e)}

    def get_status(self) -> Dict[str, Any]:
        try:
            resp = requests.get(f"{self.base_url}/v1/status", timeout=3.0)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"status": "UNAVAILABLE", "error": str(e)}

    def list_stations(self) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(f"{self.base_url}/v1/stations", timeout=3.0)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return []

    def get_station_observations(self, station_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(
                f"{self.base_url}/v1/stations/{station_id}/observations",
                params={"limit": limit},
                timeout=3.0,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return []

    def get_station_events(self, station_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(
                f"{self.base_url}/v1/stations/{station_id}/events",
                params={"limit": limit},
                timeout=3.0,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return []

    def get_station_health(self, station_id: str) -> Dict[str, Any]:
        try:
            resp = requests.get(
                f"{self.base_url}/v1/stations/{station_id}/health",
                timeout=3.0,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def list_decisions(self, station_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            params = {"limit": limit}
            if station_id:
                params["station_id"] = station_id
            resp = requests.get(
                f"{self.base_url}/v1/decisions",
                params=params,
                timeout=3.0,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return []

    def list_scenarios(self) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(f"{self.base_url}/v1/simulator/scenarios", timeout=3.0)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return []

    def run_scenario(
        self,
        scenario_name: str,
        station_id: str = "AWS_SIM_01",
        num_points: int = 25,
        seed: int = 42,
    ) -> Dict[str, Any]:
        try:
            resp = requests.post(
                f"{self.base_url}/v1/simulator/scenarios/{scenario_name}/run",
                params={"station_id": station_id, "num_points": num_points, "seed": seed},
                timeout=15.0,
            )
            return {"status_code": resp.status_code, "data": resp.json()}
        except Exception as e:
            return {"status_code": 500, "error": str(e)}

    def submit_observation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            resp = requests.post(
                f"{self.base_url}/v1/observations",
                json=payload,
                timeout=5.0,
            )
            return {"status_code": resp.status_code, "data": resp.json()}
        except Exception as e:
            return {"status_code": 500, "error": str(e)}
