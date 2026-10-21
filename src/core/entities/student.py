"""Student entities (§1): Student + EnrollmentRecord.

FC36: identity is pre-authenticated; `Student` rows are created lazily on
first write (name stays NULL when unknown — honest).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

PASSING_GRADES = frozenset({"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "P", "CR"})


@dataclass
class EnrollmentRecord:
    """Profile-class row (FC14/FC21) doubling as the §1 EnrollmentRecord.

    `status` uses the FC21 enum; grade/semester_taken are the historical
    fields a passed/failed record carries.
    """

    student_id: str
    course_id: str
    semester_taken: Optional[str] = None
    grade: Optional[str] = None
    status: str = "not_taken"  # FC21: not_taken|in_progress|taken|passed|failed
    bookmarked: bool = False
    added_at: Optional[datetime] = None

    def is_passing_grade(self) -> bool:
        """FC30 fuel: what counts as previously passed."""
        return self.grade in PASSING_GRADES


@dataclass
class Student:
    """§1 Student. `current_major` holds the major_name string (the
    DegreeRequirement object is loaded on demand — see domain-model note)."""

    student_id: str
    name: Optional[str] = None
    current_major: Optional[str] = None
    concentration: Optional[str] = None
    career_interest: Optional[str] = None
    selected_degree_id: Optional[str] = None
    include_summer_sessions: bool = False
    completed_courses: List[EnrollmentRecord] = field(default_factory=list)

    def has_passed_course(self, course_id: str) -> bool:
        """FC30 fuel: any taken/passing record for the course id."""
        return any(
            r.course_id == course_id and r.status in {"passed", "taken"}
            for r in self.completed_courses
        )

    def get_completed_credit_hours(self, hours_for: Optional[dict] = None) -> int:
        """Hours of passed/taken records; `hours_for` maps course_id→hours
        when the caller has the catalog (otherwise counts records)."""
        return sum(
            (hours_for or {}).get(r.course_id, 1)
            for r in self.completed_courses
            if r.status in {"passed", "taken"}
        )