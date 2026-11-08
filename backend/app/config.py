from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("CDER_DATA_DIR", REPO_ROOT / "data" / "raw"))
ONTOLOGY_PATH = Path(os.environ.get("CDER_ONTOLOGY", REPO_ROOT / "ontology.yaml"))
STATE_DIR = Path(os.environ.get("CDER_STATE_DIR", REPO_ROOT / "backend" / "state"))
STATE_DIR.mkdir(parents=True, exist_ok=True)

CSV_FILES = {
    "drug_shortages": DATA_DIR / "drug_shortages.csv",
    "applications": DATA_DIR / "applications.csv",
    "inspections": DATA_DIR / "inspections.csv",
}
