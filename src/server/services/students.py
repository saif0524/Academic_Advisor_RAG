"""Student profile service (FC1, FC7, FC16–FC17, FC19, FC36).

Identity comes from the X-Student-ID header (FC36); profile data lives in
SQLite. Degree progress (FC19) is counted by `core.engine.progress` — the
same function the chat assistant uses.
"""
from typing import Any, Optional

from server.errors import InvalidRequestError
from server.schemas.students import (
    DegreeProgressResponse,
    MajorHistoryEntry,
    MajorHistoryResponse,
    MajorUpdateRequest,
    PlanningPreferences,
    SelectDegreeRequest,
    StudentProfile,
)
from core.engine.progress import compute_degree_progress
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
        degree = self._sql_db_manager.get_degree(request.degree_id)  # 404 if unknown
        student = self._sql_db_manager.get_student_record(student_id)
        if student is not None and student.current_major and student.current_major != degree.major_name:
            raise InvalidRequestError(
                "The selected degree is not aligned to your major (FC16)",
                details=[f"major {student.current_major!r} does not grant degree {degree.degree_id!r}"],
            )
        self._sql_db_manager.set_selected_degree(student_id, request.degree_id)
        return self.get_profile(student_id)

    def get_degree_progress(self, student_id: str) -> DegreeProgressResponse:
        """Progress toward the selected degree (FC19), counted by the core engine."""
        student = self._sql_db_manager.get_student_record(student_id)
        if student is None or student.selected_degree_id is None:
            return DegreeProgressResponse()  # no degree selected — honest Nones

        degree = self._sql_db_manager.get_degree(student.selected_degree_id)  # raises 404 if unknown

        classes = self._sql_db_manager.list_student_classes(student_id)
        hours_by_id = {c.course_id: c.credit_hours for c in self._sql_db_manager.list_courses()
                       if c.credit_hours}
        totals = compute_degree_progress(degree, classes, hours_by_id)
        in_progress_hours = sum(hours_by_id.get(c.course_id, 0) for c in classes if c.status == "in_progress")
        return DegreeProgressResponse(
            degree_id=degree.degree_id,
            completion_percent=totals["completion_percent"],
            completed_hours=int(totals["completed_hours"]),
            in_progress_hours=in_progress_hours,
            total_credits_required=degree.total_credits_required,
            outstanding_requirements=totals["outstanding_requirements"],
        )

    def get_preferences(self, student_id: str) -> PlanningPreferences:
        """Planning-preference inputs (FC25/FC32) — honest defaults when unset."""
        stored = self._sql_db_manager.get_student_preferences(student_id)
        if stored is None:
            return PlanningPreferences()  # no invented cap numbers (FC33)
        return PlanningPreferences(
            max_credits_per_semester=stored["max_credits_per_semester"],
            include_summer=stored["include_summer"],
            preferred_class_times=stored["preferred_class_times"],
        )

    def update_preferences(self, student_id: str, prefs: PlanningPreferences) -> PlanningPreferences:
        """Persist the planning inputs the deterministic engine consumes."""
        stored = self._sql_db_manager.update_student_preferences(
            student_id,
            max_credits_per_semester=prefs.max_credits_per_semester,
            include_summer=prefs.include_summer,
            preferred_class_times=prefs.preferred_class_times,
        )
        return PlanningPreferences(
            max_credits_per_semester=stored["max_credits_per_semester"],
            include_summer=stored["include_summer"],
            preferred_class_times=stored["preferred_class_times"],
        )

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
