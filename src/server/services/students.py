"""Student profile service (FC1, FC7, FC16–FC17, FC19, FC36).

Identity is header-only (FC36); profile state lives in SQL (FC33). FC16/FC17
(degree alignment/single selection) are deterministic store checks — never
delegated to an LLM. FC19 progress is deterministic credit counting.
"""
from typing import Any, Dict, List, Optional

from database.errors import RecordNotFoundError
from server.errors import InvalidRequestError
from server.schemas.students import (
    DegreeProgressResponse,
    MajorHistoryEntry,
    MajorHistoryResponse,
    MajorUpdateRequest,
    SelectDegreeRequest,
    StudentProfile,
)
from core.entities.degree import DegreeRequirement
from core.entities.student import Student


class StudentService:
    """Wiring: `sql_db_manager` (students/classes/degrees, FC33)."""

    def __init__(self, sql_db_manager: Any) -> None:
        self._sql_db_manager = sql_db_manager

    def get_profile(self, student_id: str) -> StudentProfile:
        """Profile view (FC36/FC1) — fields reflect the store; unknown ids
        keep their Nones (honest), rows are created lazily on first write."""
        student = self._sql_db_manager.get_student_record(student_id)
        return self._to_profile(student_id, student)

    def update_major(
        self, student_id: str, request: MajorUpdateRequest
    ) -> StudentProfile:
        """Set major + specialization (FC1); records the prior combo in
        history (FC7). When the agent proposes this action, it arrives with
        FC23 confirmation through the chat flow instead."""
        student = self._sql_db_manager.update_student_major(
            student_id, request.major_name, request.concentration
        )
        return self._to_profile(student_id, student)

    def get_major_history(self, student_id: str) -> MajorHistoryResponse:
        """Current + previous major/specialty combinations (FC7)."""
        rows = self._sql_db_manager.get_major_history(student_id)
        results = [
            MajorHistoryEntry(
                major_name=row["major_name"],
                concentration=row["concentration"],
                active=bool(row["active"]),
                changed_at=row["changed_at"],
            )
            for row in rows
        ]
        return MajorHistoryResponse(results=results, count=len(results))

    def select_degree(self, student_id: str, request: SelectDegreeRequest) -> StudentProfile:
        """Select the tracked degree (FC17: one at a time).

        FC16 first, deterministically: the degree must exist in the catalog
        (404 otherwise) and be aligned to the student's current major (422).
        """
        try:
            degree = self._sql_db_manager.get_degree(request.degree_id)
        except RecordNotFoundError:
            degree = None
        if degree is None:
            raise RecordNotFoundError(f"Degree {request.degree_id!r} not found in the catalog")
        student = self._sql_db_manager.get_student_record(student_id)
        if student is not None and student.current_major and student.current_major != degree.major_name:
            raise InvalidRequestError(
                "The selected degree is not aligned to your major (FC16)",
                details=[f"major {student.current_major!r} does not grant degree {degree.degree_id!r}"],
            )
        self._sql_db_manager.set_selected_degree(student_id, request.degree_id)
        return self.get_profile(student_id)

    def get_degree_progress(self, student_id: str) -> DegreeProgressResponse:
        """Progress toward the selected degree only (FC19).

        Deterministic counting over SQLite state: passed/taken classes whose
        canonical course id matches a requirement course row count their
        credit hours; unmatched eligible courses fill elective buckets to
        their stated caps; nothing is invented for unmatched hours.

        completion_percent = matched hours / total_credits_required (FC19).
        Outstanding lines carry "in progress" hours separately — they are
        underway, not completed.
        """
        student = self._sql_db_manager.get_student_record(student_id)
        if student is None or student.selected_degree_id is None:
            return DegreeProgressResponse()  # no degree selected — honest Nones

        degree = self._sql_db_manager.get_degree(student.selected_degree_id)  # raises 404 if unknown

        classes = self._sql_db_manager.list_student_classes(student_id)
        hours_by_id = self._catalog_hours([c.course_id for c in classes])
        totals = _progress_math(degree, classes, hours_by_id)
        return DegreeProgressResponse(
            degree_id=degree.degree_id,
            completion_percent=totals["completion_percent"],
            outstanding_requirements=totals["outstanding_requirements"],
        )

    def _catalog_hours(self, course_ids: List[str]) -> Dict[str, int]:
        bulk = self._sql_db_manager.execute_query(
            "SELECT course_id, credit_hours FROM courses WHERE credit_hours IS NOT NULL"
        )
        return {row["course_id"]: row["credit_hours"] for row in bulk if row["credit_hours"]}

    @staticmethod
    def _to_profile(student_id: str, student: Optional[Student]) -> StudentProfile:
        if student is None:
            return StudentProfile(student_id=student_id)  # identity only (FC36)
        return StudentProfile(
            student_id=student.student_id,
            name=student.name,
            current_major=student.current_major,
            concentration=student.concentration,
            career_interest=student.career_interest,
        )


def _progress_math(degree: DegreeRequirement, classes, hours_by_id: Dict[str, int]) -> Dict:
    """FC19 deterministic counting (pure function — easy to unit-test/verify).

    Rule per class (status passed/taken = completed; in_progress = underway):
    1. Matched to a requirement course row → hours credit that block.
    2. Unmatched CSE courses fill elective buckets whose parsed level cutoff
       they satisfy (e.g. 'CSE 4000-level' → number >= 4000), until cap.
    3. Everything else is ignored (grounded: it maps to nothing in this degree).
    """
    completed: Dict[str, int] = {}      # course_id → hours (passed/taken)
    underway: Dict[str, int] = {}
    for entry in classes:
        if entry.status in {"passed", "taken"}:
            completed[entry.course_id] = completed.get(entry.course_id, 0) + (hours_by_id.get(entry.course_id) or 0)
        elif entry.status == "in_progress":
            underway[entry.course_id] = underway.get(entry.course_id, 0) + (hours_by_id.get(entry.course_id) or 0)

    per_block_done: Dict[str, float] = {}
    per_block_progress: Dict[str, float] = {}
    matched = set()
    for block in degree.blocks:
        if block.kind == "electives" or not block.courses:
            continue
        for row in block.courses:
            if row.course_id in completed:
                per_block_done[block.name] = per_block_done.get(block.name, 0.0) + (row.credit_hours or completed[row.course_id])
                matched.add(row.course_id)
            elif row.course_id in underway:
                per_block_progress[block.name] = per_block_progress.get(block.name, 0.0) + (row.credit_hours or underway[row.course_id])
                matched.add(row.course_id)

    # elective buckets: fill from unmatched classes via the bucket's level rule
    for bucket_name, hours_required in degree.elective_rules.items():
        cutoff = _elective_cutoff(bucket_name)
        filled = 0.0
        if cutoff is not None:
            for course_id, hours in list(completed.items()):
                if course_id in matched or filled >= hours_required:
                    continue
                if _satisfies_cutoff(course_id, cutoff):
                    take = min(hours, hours_required - filled)
                    filled += take
                    per_block_done[bucket_name] = per_block_done.get(bucket_name, 0.0) + take
            for course_id, hours in underway.items():
                if course_id in matched or filled >= hours_required:
                    continue
                if _satisfies_cutoff(course_id, cutoff):
                    take = min(hours, hours_required - filled)
                    per_block_progress[bucket_name] = per_block_progress.get(bucket_name, 0.0) + take

    total_done = sum(per_block_done.values())
    percentage = round(100.0 * total_done / degree.total_credits_required, 1) if degree.total_credits_required else None

    outstanding: List[str] = []
    for block in degree.blocks:
        if block.kind == "electives":
            required = block.credits_required or 0
        elif block.credits_required is not None:
            required = block.credits_required
        else:
            continue
        done = per_block_done.get(block.name, 0.0)
        progress = per_block_progress.get(block.name, 0.0)
        remaining = max(required - done, 0.0)
        suffix = f" ({progress:g} in progress)" if progress else ""
        outstanding.append(f"{block.name}: {remaining:g} of {required} hours remaining{suffix}")

    return {
        "completion_percent": percentage,
        "outstanding_requirements": outstanding,
        "completed_hours": total_done,
    }


def _elective_cutoff(bucket: str) -> Optional[tuple]:
    """Parse 'CSE 4000-level Technical Electives' / '...3000-level or 4000-level...'
    → ("CSE", min_level). Grounded in the two requirement docs' wording."""
    import re

    match = re.search(r"([A-Z]{2,5})\s(\d{4})-level", bucket)
    if not match:
        return None
    or_match = re.search(r"(\d{4})-level", bucket[len(match.group(0)):] )
    lower_bound = min(int(match.group(2)), int(or_match.group(1))) if or_match else int(match.group(2))
    return match.group(1), lower_bound


def _satisfies_cutoff(course_id: str, cutoff: tuple) -> bool:
    department, number = cutoff
    parts = course_id.split()
    if len(parts) != 2 or parts[0] != department:
        return False
    try:
        return int(parts[1]) >= number
    except ValueError:
        return False

