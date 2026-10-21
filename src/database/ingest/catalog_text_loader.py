"""Catalog text documents for the Chroma `catalog` collection (FC33).

Degree-requirement documents, the AI-certificate description, and the general
core document are ingested as text so semantic degree/requirement questions
(FC22 fuel) can be answered from the real catalog files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

DATA_DIR = Path(__file__).resolve().parents[3] / "data"

KINDS = {
    "CS-requirements-BCS.md": "degree_requirements",
    "SE-requirements-BSE.md": "degree_requirements",
    "AICertification.md": "certificate",
    "general-course.md": "general_core",
}


def load_catalog_documents(data_dir: Path = DATA_DIR) -> List[Dict[str, str]]:
    """[{id, text, metadata}] for every catalog text source (whole-file chunks)."""
    documents: List[Dict[str, str]] = []
    for filename, kind in KINDS.items():
        path = data_dir / filename
        if not path.exists():  # missing source is reported, not fabricated
            continue
        documents.append({
            "id": f"catalog:{filename}",
            "text": path.read_text().strip(),
            "metadata": {"kind": kind, "source": str(path.name)},
        })
    return documents