"""Degree & plan entities (§1 requirement records + §2 planning models).

`DegreeRequirement` gains `blocks` — the block-level requirement structure
behind FC18/FC19 (parsed from the degree requirement documents). Engine
classes (§2 validator/generator) are separate and NOT defined here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class DegreeBlockCourse:
    """One required-course row inside a requirement block (FC18)."""

    course_code: str  # e.g. "CSE 1105" / "ENGL 1301" — exactly as the catalog states it
    title: Optional[str] = None
    credit_hours: Optional[int] = None
    course_id: Optional[str] = None  # normalized canonical id ("1105") when resolvable
    option_group: Optional[str] = None  # select-one grouping for FC18 rendering


@dataclass
class DegreeBlock:
    """A requirement block, e.g. 'Creative Arts (3 Hours)' or an elective bucket."""

    name: str
    kind: str  # general_core | math_science | major_core | electives
    credits_required: Optional[int] = None
    elective_bucket: Optional[str] = None  # set when this block is an elective rule
    courses: List[DegreeBlockCourse] = field(default_factory=list)


@dataclass
class DegreeRequirement:
    """§1 degree requirement record; blocks feed FC18 views and FC19 counting."""

    degree_id: str
    major_name: str
    concentration_name: Optional[str] = None
    total_credits_required: Optional[int] = None
    max_semester_credits: Optional[int] = None
    institution: Optional[str] = None
    core_courses: List[str] = field(default_factory=list)
    concentration_courses: List[str] = field(default_factory=list)
    elective_rules: Dict[str, int] = field(default_factory=dict)
    blocks: List[DegreeBlock] = field(default_factory=list)

    def is_course_applicable(self, course_id: str) -> bool:
        """§1 helper: course appears in any block's course rows (canonical ids)."""
        return any(
            row.course_id == course_id
            for block in self.blocks
            for row in block.courses
            if row.course_id is not None
        )

    def get_remaining_requirements(self, completed_courses: List[Any]) -> List[str]:
        """§1 helper (FC19/FC24 fuel): hours remaining per block, counting
        passed/taken records only. Accepts EnrollmentRecords or plain
        (course_id, status, credit_hours) tuples."""
        credits_by_block: Dict[str, float] = {}
        for record in completed_courses:
            if hasattr(record, "status"):
                course_id, status, hours = record.course_id, record.status, record.credit_hours
            else:
                course_id, status, hours = record[0], record[1], record[2]
            if status not in {"passed", "taken"}:
                continue
            for block in self.blocks:
                if any(row.course_id == course_id for row in block.courses):
                    credits_by_block[block.name] = credits_by_block.get(block.name, 0.0) + float(hours)
                    break  # a course counts toward its first matching block
        remaining: List[str] = []
        for block in self.blocks:
            if block.credits_required is None or not block.courses:
                continue
            got = credits_by_block.get(block.name, 0.0)
            left = max(block.credits_required - got, 0.0)
            remaining.append(f"{block.name}: {left:g} of {block.credits_required} hours remaining")
        return remaining


@dataclass
class SemesterPlan:
    """§2 planning model (pure data — generation logic stays in the engine)."""

    term: str
    year: int
    course_ids: List[str] = field(default_factory=list)
    max_credit_limit: Optional[int] = None

    def to_payload(self) -> dict:
        return {"term": self.term, "year": self.year, "courses": list(self.course_ids)}


@dataclass
class DegreePlan:
    """§2 planning model (pure data). Persisted via SQLDatabaseManager.save_degree_plan.
    Plans belong to one major/concentration combo (FC6) — target_major/concentration
    carry that for persistence; degree_id ties the plan to its requirement record."""

    plan_id: str
    student_id: str
    degree_id: Optional[str] = None
    target_major: Optional[str] = None
    concentration: Optional[str] = None
    semesters: List[SemesterPlan] = field(default_factory=list)
    includes_summer: bool = False
    creation_date: Optional[datetime] = None

    def to_payload(self) -> dict:
        return {
            "semesters": [s.to_payload() for s in self.semesters],
            "includes_summer": self.includes_summer,
        }

    def get_total_planned_credits(self) -> int:
        return sum(len(s.course_ids) for s in self.semesters)