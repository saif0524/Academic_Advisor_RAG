"""Audit service (FC24) — deterministic checks only (FC29–FC32).

Both endpoints answer by running the core engine's
`CourseRecommendationValidator` / progress counting against SQLite state —
the LLM never decides eligibility. WIRED: the validator zone exists (built
alongside the agent)."""
from core.entities.course import Course
from core.engine.validator import CourseRecommendationValidator
from database.errors import RecordNotFoundError
from server.schemas.audit import (
    ConstraintCheck,
    CourseAuditRequest,
    CourseAuditResponse,
    DegreeAuditRequest,
    DegreeAuditResponse,
)


class AuditService:
    """Wiring: `sql_db_manager` (student/section data) + core validator (same
    path the agent's audit tools use — one deterministic source of truth)."""

    def __init__(self, sql_db_manager, vector_db_manager=None) -> None:
        self._sql_db_manager = sql_db_manager
        self._vector_db_manager = vector_db_manager

    def course_check(self, student_id: str, request: CourseAuditRequest) -> CourseAuditResponse:
        """Can the student take this course? (FC24) → validator checks FC29
        (prereqs), FC30 (not already passed), FC31 (section conflict when the
        section is given), FC32 (credit caps)."""
        from agent.tools.plan_tools import PlanTools

        plan = PlanTools(self._sql_db_manager)
        course = plan.find_course(request.course_id)
        if course is None:
            raise RecordNotFoundError(f"Course {request.course_id!r} not found in the catalog")
        if request.section_id and not any(
            s.section_id == request.section_id for s in self._sql_db_manager.list_sections(course.course_id)
        ):
            raise RecordNotFoundError(
                f"Section {request.section_id!r} not found for course {course.course_id!r}")
        audit = plan.course_audit(student_id, course.course_id, request.section_id)
        result = audit["result"]
        checks = [ConstraintCheck(**c) for c in result["checks"]]
        return CourseAuditResponse(
            student_id=student_id, course_id=course.course_id,
            eligible=result["eligible"], checks=checks,
        )

    def degree_check(self, student_id: str, request: DegreeAuditRequest) -> DegreeAuditResponse:
        """Degree-requirements status (FC24 second half) — remaining blocks +
        progress percent from the core counting (FC19)."""
        from agent.tools.plan_tools import PlanTools

        plan = PlanTools(self._sql_db_manager)
        audit = plan.degree_audit(student_id, request.degree_id)
        if audit is None:
            if request.degree_id:
                raise RecordNotFoundError(f"Degree {request.degree_id!r} not found")
            return DegreeAuditResponse(student_id=student_id)  # no degree selected — honest Nones
        checks = [ConstraintCheck(**c) for c in audit["checks"]]
        return DegreeAuditResponse(
            student_id=student_id, degree_id=audit["degree_id"],
            completion_percent=audit["completion_percent"], checks=checks,
        )