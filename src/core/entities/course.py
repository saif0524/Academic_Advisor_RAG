"""Course entities (§1): Course + CourseSection.

`Course.to_document_chunk` defines the chunk format embedded into Chroma
(FC33/FC35). `CourseSection.has_time_conflict` is the deterministic overlap
rule the FC31 validator builds on.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Course:
    """One catalog course. `course_id` is the canonical API id: the 4-digit
    corpus id for catalog-backed courses (e.g. "1105"), the full code
    (e.g. "ENGL 1301"/"CSE 2381") otherwise. NULL hours/description mean
    "not present in source data" — never invented (grounded-data rule)."""

    course_id: str
    title: str
    description: Optional[str] = None
    credit_hours: Optional[int] = None
    prerequisites: List[str] = field(default_factory=list)
    corequisites: List[str] = field(default_factory=list)
    offered_terms: List[str] = field(default_factory=list)
    department: Optional[str] = None
    number: Optional[str] = None
    course_code: Optional[str] = None  # provenance form, e.g. "CSE 1105"

    def get_prerequisites(self) -> List[str]:
        return list(self.prerequisites)

    def is_offered_in_term(self, term: str) -> bool:
        return term in self.offered_terms

    def to_document_chunk(self) -> str:
        """Embedding chunk: title + description (FC35 corpus format)."""
        return f"{self.title}.\n{self.description or ''}".strip()


@dataclass
class CourseSection:
    """One scheduled section (§1; FC12). Times are 'HH:MM' strings."""

    section_id: str
    course_id: str
    semester_term: str
    instructor: Optional[str] = None
    meeting_days: List[str] = field(default_factory=list)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    room_capacity: Optional[int] = None
    enrolled_count: Optional[int] = None

    def has_time_conflict(self, other_section: "CourseSection") -> bool:
        """FC31 fuel: day/time overlap against another candidate section."""
        if not (self.start_time and self.end_time and other_section.start_time and other_section.end_time):
            return False  # schedule data absent — cannot conflict
        shared_days = set(self.meeting_days) & set(other_section.meeting_days)
        if not shared_days:
            return False
        return self.start_time < other_section.end_time and other_section.start_time < self.end_time

    def has_open_seats(self) -> bool:
        if self.room_capacity is None or self.enrolled_count is None:
            return True  # unknown seat data — not enough information to say full
        return self.enrolled_count < self.room_capacity

    def get_schedule_string(self) -> str:
        days = "/".join(self.meeting_days) if self.meeting_days else "TBD"
        return f"{days} {self.start_time or 'TBD'}–{self.end_time or 'TBD'} ({self.instructor or 'TBA'})"