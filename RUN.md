# RUN.md — SkyGuard AI (SIH26073)

**Authoritative Runbook for Evaluation, Deployment, and SIH Demonstration**

---

## 1. Quick Start

### Prerequisites
- Python 3.10+ (Recommended: Python 3.11 or 3.13)
- pip
- (Optional) Docker

### Installation
```bash
# 1. Clone or navigate to the repository
cd sih

# 2. Install core dependencies
pip install -r requirements.txt
```

---

## 2. Running Automated Tests

Run the complete 145-item test suite (unit, integrity invariants, and integration):
```bash
python -m pytest -v
```

Run specifically with coverage report:
```bash
python -m pytest --cov=. --cov-report=term-missing
```

---

## 3. Starting the System Services

### Terminal 1: Start FastAPI Backend Service
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Base URL: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`
- Health Endpoint: `http://127.0.0.1:8000/health`
- Live Decision SSE Stream: `http://127.0.0.1:8000/v1/stream`

### Terminal 2: Start Streamlit Operational Dashboard
```bash
streamlit run dashboard/app.py --server.port 8501
```
- Web Dashboard UI: `http://localhost:8501`

---

## 4. Executing the SIH Demonstration Suite

### Command-Line Demonstration (All 10 Scenarios)
Execute the automated end-to-end demonstration across all meteorological fault and genuine weather scenarios:
```bash
python scripts/run_sih_demo.py
```

### Interactive Web Dashboard Demonstration
1. Open `http://localhost:8501` in your browser.
2. Navigate to the **Scenario Lab** tab.
3. Select any of the 10 demonstration scenarios:
   - *1. Nominal / Normal Clean Stream*
   - *2. Isolated Temperature Spike*
   - *3. Frozen Sensor Flatline*
   - *4. Gradual Sensor Drift*
   - *5. Multivariate Inconsistency*
   - *6. Sudden Pressure Bias Jump*
   - *7. Excessive High-Frequency Noise*
   - *8. Communication Gap / Packet Loss*
   - *9. Genuine Cold Front Event* (Weather vs Sensor Fault demonstration)
   - *10. Combined Fault Suite*
4. Click **Run Scenario**.
5. Switch to **Station Overview**, **Anomaly Monitor**, **Historical Analysis**, or **Sensor Health** to inspect real-time results.

---

## 5. API Ingestion Example (cURL / Python)

### Submit a Single Live Observation
```bash
curl -X POST "http://127.0.0.1:8000/v1/observations" \
     -H "Content-Type: application/json" \
     -d '{
       "station_id": "AWS_STATION_01",
       "timestamp": "2026-09-30T12:00:00Z",
       "temperature": 28.5,
       "pressure": 1008.2,
       "relative_humidity": 65.0,
       "source_type": "LIVE"
     }'
```

### Python Requests Example
```python
import requests
from datetime import datetime, timezone

payload = {
    "station_id": "AWS_FIELD_01",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "temperature": 29.1,
    "pressure": 1012.4,
    "relative_humidity": 62.0,
    "source_type": "LIVE",
}
resp = requests.post("http://127.0.0.1:8000/v1/observations", json=payload)
decision = resp.json()
print("Decision State:", decision["decision_state"])
print("Anomaly Score:", decision["anomaly_score"])
print("Root Cause:", decision["root_cause_category"])
print("Reasoning:", decision["reasoning_summary"])
```

---

## 6. Docker Container Deployment

Build and run using Docker:
```bash
docker build -t skyguard-ai:latest .
docker run -p 8000:8000 -p 8501:8501 skyguard-ai:latest
```

