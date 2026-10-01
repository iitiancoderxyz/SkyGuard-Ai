"""
Helper script to ensure exact architecture directory tree and package inits exist.
"""
from pathlib import Path

DIRECTORIES = [
    "app/api",
    "app/core",
    "app/config",
    "app/runtime",
    "ingestion/adapters",
    "ingestion/schemas",
    "ingestion/integrity",
    "ingestion/replay",
    "features/temporal",
    "features/seasonal",
    "features/multivariate",
    "features/lineage",
    "detection/reference",
    "detection/tracker",
    "detection/triggers",
    "detection/episodes",
    "detection/adjudication",
    "attribution/weather",
    "attribution/sensor",
    "attribution/network",
    "attribution/uncertainty",
    "health/sensor_health",
    "health/degradation",
    "health/maintenance",
    "correction/optional",
    "storage/repositories",
    "storage/migrations",
    "storage/db",
    "simulator/stream",
    "simulator/scenarios",
    "simulator/replay",
    "injector/faults",
    "injector/weather_surrogates",
    "injector/manifests",
    "eval/metrics",
    "eval/baselines",
    "eval/calibration",
    "eval/robustness",
    "eval/load",
    "dashboard/views",
    "dashboard/components",
    "dashboard/stream",
    "models_store/reference",
    "models_store/tracker",
    "models_store/classifiers",
    "models_store/calibration",
    "data/replay",
    "data/simulated",
    "data/ground_truth",
    "data/spool",
    "scripts",
    "examples",
    "tests/unit",
    "tests/integration",
    "tests/behavioral",
    "tests/invariants",
    "tests/contract",
    "tests/browser",
    "docs",
]

def init_tree():
    root = Path(__file__).parent.parent
    for dir_path in DIRECTORIES:
        p = root / dir_path
        p.mkdir(parents=True, exist_ok=True)
        # Add __init__.py if it is a python package directory
        if not dir_path.startswith("data") and not dir_path.startswith("models_store") and not dir_path.startswith("docs") and not dir_path.startswith("examples") and not dir_path.startswith("scripts"):
            init_file = p / "__init__.py"
            if not init_file.exists():
                init_file.write_text(f'"""Package {dir_path}"""\n', encoding="utf-8")
        else:
            gitkeep = p / ".gitkeep"
            if not gitkeep.exists():
                gitkeep.write_text("", encoding="utf-8")
    print("Exact folder structure initialized successfully.")

if __name__ == "__main__":
    init_tree()
