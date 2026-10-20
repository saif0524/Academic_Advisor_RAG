"""Audit controller (FC24; deterministic checks FC29–FC32)."""
from server.schemas.audit import (
    CourseAuditRequest,
    CourseAuditResponse,
    DegreeAuditRequest,
    DegreeAuditResponse,
)
from server.schemas.students import StudentIdentity
from server.services.audit import AuditService


def course_check(
    student: StudentIdentity, payload: CourseAuditRequest, service: AuditService
) -> CourseAuditResponse:
    """FC24 course eligibility via validator checks FC29/FC30/FC31."""
    return service.course_check(student.student_id, payload)


def degree_check(
    student: StudentIdentity, payload: DegreeAuditRequest, service: AuditService
) -> DegreeAuditResponse:
    """FC24 degree-requirements status; defaults to the selected degree (FC17)."""
    return service.degree_check(student.student_id, payload)