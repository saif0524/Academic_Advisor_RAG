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
            # Each concentration track also gets its own short chunk so semantic
            # questions ("what is the Cybersecurity concentration?") retrieve it
            # whole instead of a truncated slice of the big degree record.
            for track in record.get("concentrations", []) if kind == "degree_requirements" else []:
                documents.append({
                    "id": f"catalog:{path.stem}:concentration:{_slug(track['name'])}",
                    "text": (
                        f"{record['major_name']} ({record['degree_id']}) — concentration: {track['name']}. "
                        f"{track.get('description', '')} Requires {track.get('credits_required')} credit hours "
                        "(taken in place of technical-elective hours):\n"
                        + json.dumps(track["courses"], indent=2, ensure_ascii=False)
                    ),
                    "metadata": {"kind": "concentration", "source": path.name,
                                 "degree_id": record["degree_id"], "concentration": track["name"]},
                })
    return documents


def _slug(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
