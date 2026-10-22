"""Degree-requirement JSON loading (FC15/FC18/FC32 records).

Reads data/degrees/*.json — one structured record per degree:
`degree_id`, `major_name`, credit totals, and `blocks` (kind one of
general_core | math_science | major_core | electives; courses carry
`option_group` for select-one rows; elective blocks carry `elective_bucket`).

Canonical course identity per repo rule: corpus-backed CSE courses use their
4-digit corpus id; everyone else keeps the full code ("ENGL 1301", "CSE 2381").
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.entities.course import Course
from core.entities.degree import DegreeBlock, DegreeBlockCourse, DegreeRequirement
from database.ingest.course_desc_loader import load_course_desc

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def load_degree_requirements(data_dir: Path = DATA_DIR) -> List[DegreeRequirement]:
    """Load every data/degrees/*.json into a DegreeRequirement with blocks."""
    corpus_ids = {c.course_id for c in load_course_desc(data_dir)}
    return [
        _build_degree(json.loads(path.read_text()), corpus_ids)
        for path in sorted((data_dir / "degrees").glob("*.json"))
    ]


def derive_courses_from_requirements(
    degrees: List[DegreeRequirement], corpus_ids: Optional[set] = None
) -> List[Course]:
    """Course rows for every concrete course referenced by requirement tables.

    Hours/titles come from the requirement tables; catalog-backed CSE courses
    keep their corpus id (and 4-digit identity), the rest keep full codes.
    """
    corpus_ids = corpus_ids if corpus_ids is not None else {c.course_id for c in load_course_desc()}
    merged: Dict[str, Course] = {}
    for degree in degrees:
        for block in degree.blocks:
            if block.kind == "electives":
                continue  # elective buckets hold no concrete course rows
            for row in block.courses:
                department, number, code = _normalize_code(row.course_code)
                course_id = _resolve_course_id(department, number, corpus_ids)
                course = merged.setdefault(course_id, Course(
                    course_id=course_id,
                    title=row.title or code,
                    description=None,
                    credit_hours=row.credit_hours,
                    department=department,
                    number=number,
                    course_code=code,
                ))
                if row.credit_hours is not None:
                    course.credit_hours = row.credit_hours
    return sorted(merged.values(), key=lambda c: c.course_id)


# ----------------------------------------------------------------- internals

def _build_degree(record: dict, corpus_ids: set) -> DegreeRequirement:
    blocks: List[DegreeBlock] = []
    for raw in record.get("blocks", []):
        courses: List[DegreeBlockCourse] = []
        for row in raw.get("courses", []):
            department, number, code = _normalize_code(row["course_code"])
            courses.append(DegreeBlockCourse(
                course_code=code,
                title=row.get("title"),
                credit_hours=row.get("credit_hours"),
                course_id=_resolve_course_id(department, number, corpus_ids),
                option_group=row.get("option_group"),
            ))
        blocks.append(DegreeBlock(
            name=raw["name"],
            kind=raw["kind"],
            credits_required=raw.get("credits_required"),
            courses=courses,
            elective_bucket=raw.get("elective_bucket"),
        ))
    return DegreeRequirement(
        degree_id=str(record["degree_id"]),
        major_name=str(record["major_name"]),
        total_credits_required=record.get("total_credits_required"),
        max_semester_credits=record.get("max_semester_credits"),
        institution=record.get("institution"),
        core_courses=_collect_ids(blocks, "major_core"),
        concentration_courses=_collect_ids(blocks, "concentration"),
        elective_rules={b.elective_bucket: b.credits_required or 0 for b in blocks if b.kind == "electives"},
        blocks=blocks,
    )


def _normalize_code(code: str) -> Tuple[str, str, str]:
    parts = code.strip().replace("\u00a0", " ").split()
    if len(parts) != 2:
        raise ValueError(f"Cannot parse requirement course code {code!r}")
    department, number = parts[0].upper(), parts[1]
    return department, number, f"{department} {number}"


def _resolve_course_id(department: str, number: str, corpus_ids: set) -> str:
    # Only catalog-backed CSE courses use the bare corpus id — other departments
    # keep full codes ("ENGL 1301") so ids never collide with CSE numbers:
    # ENGL 1301 and CSE 1301 are different courses.
    if corpus_ids and department == "CSE" and number in corpus_ids:
        return number
    return f"{department} {number}"


def _collect_ids(blocks: List[DegreeBlock], kind: str) -> List[str]:
    ids: List[str] = []
    for block in blocks:
        if block.kind == kind:
            for row in block.courses:
                if row.course_id or row.course_code:
                    ids.append(row.course_id or row.course_code)
    return ids