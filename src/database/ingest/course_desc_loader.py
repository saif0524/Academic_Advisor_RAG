"""data/course-desc.jsonl → Course entities (FC35 seed corpus ingest)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from core.entities.course import Course

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def load_course_desc(data_dir: Path = DATA_DIR) -> List[Course]:
    """The 75-line CSE course corpus, losslessly → Course entities.

    Corpus rows carry id/title/description only — credit hours stay None
    here and get backfilled from the degree-requirement tables at seed time.
    """
    path = data_dir / "course-desc.jsonl"
    courses: List[Course] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        courses.append(Course(
            course_id=str(record["id"]).strip(),
            title=record["title"].strip(),
            description=(record.get("description") or "").strip() or None,
            department="CSE",
        ))
    return courses