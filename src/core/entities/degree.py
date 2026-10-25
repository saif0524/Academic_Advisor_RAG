"""Degree & plan entities (§1 requirement records + §2 planning models).

`DegreeRequirement` gains `blocks` — the block-level requirement structure
behind FC18/FC19 (parsed from the degree requirement documents). Engine
classes (§2 validator/generator) are separate and NOT defined here.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
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
    kind: str  # general_core | math_science | major_core | concentration | electives
    credits_required: Optional[int] = None
    elective_bucket: Optional[str] = None  # set when this block is an elective rule
    concentration: Optional[str] = None  # set on kind="concentration" blocks: which track owns them
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

    @property
    def concentrations(self) -> List[str]:
        """Names of the concentration tracks this degree offers (FC1/FC15)."""
        names: List[str] = []
        for block in self.blocks:
            if block.kind == "concentration" and block.concentration and block.concentration not in names:
                names.append(block.concentration)
        return names

    def for_concentration(self, concentration: Optional[str]) -> "DegreeRequirement":
        """The degree as it applies to one concentration track (FC1, FC19, FC25).

        Keeps the chosen track's requirement block and drops the other tracks'.
        The track's credit hours replace the same number of elective hours so
        the degree total stays what the catalog says. An unknown or empty name
        (or "General") yields the plain degree with no track attached.
        """
        wanted = (concentration or "").strip().lower()
        match = next((n for n in self.concentrations if n.lower() == wanted), None)
        base_blocks = [b for b in self.blocks if b.kind != "concentration"]
        track_blocks = [b for b in self.blocks if b.kind == "concentration" and b.concentration == match]
        blocks = list(base_blocks)
        if match is not None:
            to_replace = sum(b.credits_required or 0 for b in track_blocks)
            blocks = []
            for block in base_blocks:
                if block.kind == "electives" and to_replace > 0 and block.credits_required:
                    cut = min(to_replace, block.credits_required)
                    to_replace -= cut
                    if block.credits_required - cut <= 0:
                        continue  # bucket fully covered by the track
                    block = replace(block, credits_required=block.credits_required - cut)
                blocks.append(block)
            blocks.extend(track_blocks)
        return replace(
            self,
            concentration_name=match,
            concentration_courses=[
                row.course_id or row.course_code
                for b in track_blocks for row in b.courses if row.course_id or row.course_code
            ],
            elective_rules={
                b.elective_bucket: b.credits_required or 0
                for b in blocks if b.kind == "electives" and b.elective_bucket
            },
            blocks=blocks,
        )

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