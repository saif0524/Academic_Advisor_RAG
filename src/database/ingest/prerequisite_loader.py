"""data/prerequisites.json → prerequisite/corequisite edges (FC11, FC29).

The file maps a canonical course id (4-digit corpus id for CSE courses,
full code otherwise) to `{"prereq": [...], "coreq": [...]}`. It is a labeled
MOCK demo graph — never presented as registrar data.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def load_prerequisites(data_dir: Path = DATA_DIR) -> Dict[str, Dict[str, List[str]]]:
    """{course_id: {"prereq": [...], "coreq": [...]}}; a missing file means no edges."""
    path = data_dir / "prerequisites.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text())
    edges: Dict[str, Dict[str, List[str]]] = {}
    for course_id, spec in (payload.get("courses") or {}).items():
        edges[str(course_id)] = {
            "prereq": [str(x) for x in spec.get("prereq", [])],
            "coreq": [str(x) for x in spec.get("coreq", [])],
        }
    return edges
