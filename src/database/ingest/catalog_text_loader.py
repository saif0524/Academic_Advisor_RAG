"""Catalog text documents for the Chroma `catalog` collection (FC33).

Degree-requirement documents, the AI-certificate description, and the general
core document are ingested as text so semantic degree/requirement questions
(FC22 fuel) can be answered from the real catalog files.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

DATA_DIR = Path(__file__).resolve().parents[3] / "data"

# (glob relative to data/, kind) — every source is a JSON file
SOURCES = (
    ("degrees/*.json", "degree_requirements"),
    ("AICertification.json", "certificate"),
    ("general-core.json", "general_core"),
)


def load_catalog_documents(data_dir: Path = DATA_DIR) -> List[Dict[str, str]]:
    """[{id, text, metadata}] for every catalog JSON source (whole-file chunks).

    `text` is the pretty-printed JSON, so the embedded chunk carries the exact
    requirement data (codes, titles, hours) — nothing is paraphrased.
    """
    documents: List[Dict[str, str]] = []
    for pattern, kind in SOURCES:
        for path in sorted(data_dir.glob(pattern)):  # missing source is skipped, not fabricated
            record = json.loads(path.read_text())
            documents.append({
                "id": f"catalog:{path.stem}",
                "text": json.dumps(record, indent=2, ensure_ascii=False),
                "metadata": {"kind": kind, "source": path.name},
            })
    return documents
