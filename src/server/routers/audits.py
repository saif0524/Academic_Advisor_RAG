"""Audit routes (FC24) — deterministic checks FC29–FC32 only."""
from fastapi import APIRouter, Depends

from server.controllers import audit as audit_controller
from server.dependencies import get_audit_service, get_current_student
from server.schemas.audit import (
    CourseAuditRequest,
    CourseAuditResponse,
    DegreeAuditRequest,
    DegreeAuditResponse,
)
from server.schemas.students import StudentIdentity
from server.services.audit import AuditService

router = APIRouter(prefix="/audits", tags=["audits"])


@router.post(
    "/course-check",
    response_model=CourseAuditResponse,
    operation_id="audit_course_eligibility",
)
def course_check(
    payload: CourseAuditRequest,
    student: StudentIdentity = Depends(get_current_student),
    service: AuditService = Depends(get_audit_service),
) -> CourseAuditResponse:
    """Audit whether the student can take a course (FC24).

    Each `check` names its owning safeguard: prerequisites (FC29),
    already-passed (FC30), section schedule conflict when given (FC31),
    credit caps (FC32). Produced by the deterministic validator, never the LLM.
    """
    return audit_controller.course_check(student, payload, service)


@router.post(
    "/degree-check",
    response_model=DegreeAuditResponse,
    operation_id="audit_degree_progress",
)
def degree_check(
    payload: DegreeAuditRequest,
    student: StudentIdentity = Depends(get_current_student),
    service: AuditService = Depends(get_audit_service),
) -> DegreeAuditResponse:
    """Audit status toward degree requirements (FC24) — defaults to the
    selected degree (FC17), same numbers FC19 tracks. Deterministic only."""
    return audit_controller.degree_check(student, payload, service)