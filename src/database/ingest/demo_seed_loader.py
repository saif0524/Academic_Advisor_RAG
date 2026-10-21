"""Labeled MOCK demo seed data: student profile + course sections.

Files: data/student-demo.json, data/sections-mock.json — both loudly marked
as mock demo fixtures inside the file itself. The assistant must never present
them as real registrar/person data.

- sections: FC12 fuel (one full section → has_open_seats False; overlapping
  times across courses for FC31-style demos)
- student: one demo account matching FC36's pre-auth default id; profile
  properties, prior major history (FC7), classes with FC21 statuses + grades
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from core.entities.course import CourseSection

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def load_student_demo(data_dir: Path = DATA_DIR) -> Dict[str, Any]:
    """The demo student document (validated: FC21 statuses; graded states carry grades)."""
    payload = json.loads((data_dir / "student-demo.json").read_text())
    return payload


def load_sections_mock(data_dir: Path = DATA_DIR) -> List[CourseSection]:
    """Mock sections → CourseSection entities (FC12)."""
    payload = json.loads((data_dir / "sections-mock.json").read_text())
    return [CourseSection(
        section_id=s["section_id"],
        course_id=s["course_id"],
        semester_term=s["term"],
        instructor=s.get("instructor"),
        meeting_days=s.get("meeting_days", []),
        start_time=s.get("start_time"),
        end_time=s.get("end_time"),
        room_capacity=s.get("room_capacity"),
        enrolled_count=s.get("enrolled_count"),
    ) for s in payload["sections"]]