.PHONY: install test test-invariants run-api run-dashboard demo clean

install:
	pip install -r requirements.txt

test:
	pytest -v tests/

test-invariants:
	pytest -v tests/invariants/

run-api:
	uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

run-dashboard:
	streamlit run dashboard/app.py --server.port 8501

demo:
	python scripts/run_phase1_demo.py

clean:
	rm -rf __pycache__ .pytest_cache data/trusttwin.db data/spool/*
