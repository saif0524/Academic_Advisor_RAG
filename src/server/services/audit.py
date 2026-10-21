"""Audit service (FC24) — deterministic checks only (FC29–FC32).

Both endpoints answer by running `CourseRecommendationValidator` /
requirement checks from `core` (outline step 2) against SQLite state — the
LLM never decides eligibility.
"""
from server.errors import NotWiredError
from server.schemas.audit import CourseAuditResponse, CourseAuditRequest, DegreeAuditRequest, DegreeAuditResponse


class AuditService:
    """Wiring: `sql_db_manager` (student/section data) + core validator (outline step 2)."""

    def __init__(self, sql_db_manager, vector_db_manager) -> None:
        self._sql_db_manager = sql_db_manager
        self._vector_db_manager = vector_db_manager

    def course_check(self, student_id: str, request: CourseAuditRequest) -> CourseAuditResponse:
        """Can the student take this course? (FC24) → validator checks FC29 (prereqs),
        FC30 (not already passed), FC31 (section conflict when section given)."""
        raise NotWiredError(
            "Course audits are not wired yet: needs CourseRecommendationValidator "
            "(core — outline step 2) and SQLDatabaseManager (outline step 3)."
        )

    def degree_check(self, student_id: str, request: DegreeAuditRequest) -> DegreeAuditResponse:
        """Degree-requirements status (FC24) — remaining requirements + progress."""
        raise NotWiredError(
            "Degree audits are not wired yet: needs DegreeRequirement.remaining checks "
            "(core — outline step 2) and SQLDatabaseManager (outline step 3)."
        )