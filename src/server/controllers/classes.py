"""Classes controller (FC13–FC14, FC20–FC21)."""
from server.schemas.classes import (
    AddClassRequest,
    DeleteClassResponse,
    StudentClass,
    StudentClassListResponse,
    UpdateClassRequest,
)
from server.schemas.students import StudentIdentity
from server.services.classes import ClassService


def list_classes(student: StudentIdentity, service: ClassService) -> StudentClassListResponse:
    return service.list_classes(student.student_id)


def add_class(
    student: StudentIdentity, payload: AddClassRequest, service: ClassService
) -> StudentClass:
    """FC14 — defaults to not_taken; confirmation not required for direct UI adds."""
    return service.add_class(student.student_id, payload)


def update_class(
    student: StudentIdentity, course_id: str, payload: UpdateClassRequest, service: ClassService
) -> StudentClass:
    """FC13/FC21. FC23's confirm-before-acting applies to assistant-initiated
    actions (chat flow), not user-driven UI dialogs."""
    return service.update_class(student.student_id, course_id, payload)


def remove_class(
    student: StudentIdentity, course_id: str, service: ClassService
) -> DeleteClassResponse:
    """FC20."""
    return service.remove_class(student.student_id, course_id)