"""data/course-desc.json → Course entities (FC35 seed corpus ingest)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from core.entities.course import Course

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def load_course_desc(data_dir: Path = DATA_DIR) -> List[Course]:
    """The 75-course CSE corpus, losslessly → Course entities.

    Corpus rows carry id/title/description and, where the catalog states them,
    an optional `credit_hours`. Rows without hours stay None and are backfilled
    from the degree-requirement tables at seed time (the tables win on conflict).
    """
    path = data_dir / "course-desc.json"
    records = json.loads(path.read_text())
    return [
        Course(
            course_id=str(record["id"]).strip(),
            title=record["title"].strip(),
            description=(record.get("description") or "").strip() or None,
            department="CSE",
            credit_hours=record.get("credit_hours"),
        )
        for record in records
    ]
