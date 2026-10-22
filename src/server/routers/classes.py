"""Classes-on-profile routes (FC13–FC14, FC20–FC21)."""
from fastapi import APIRouter, Depends, Path

from server.dependencies import get_class_service, get_current_student
from server.schemas.classes import (
    AddClassRequest,
    DeleteClassResponse,
    StudentClass,
    StudentClassListResponse,
    UpdateClassRequest,
)
from server.schemas.students import StudentIdentity
from server.services.classes import ClassService

router = APIRouter(prefix="/classes", tags=["classes"])


@router.get("")
def list_classes(
    student: StudentIdentity = Depends(get_current_student),
    service: ClassService = Depends(get_class_service),
) -> StudentClassListResponse:
    """All classes on the profile with their statuses (FC14, FC21)."""
    return service.list_classes(student.student_id)


@router.post("", status_code=201)
def add_class(
    payload: AddClassRequest,
    student: StudentIdentity = Depends(get_current_student),
    service: ClassService = Depends(get_class_service),
) -> StudentClass:
    """Add a class to the profile — defaults to `not_taken` (FC14).

    Unknown course ids fail against the catalog (404) — courses are never
    invented. Assistant-initiated adds go through chat with FC23 confirmation.
    """
    return service.add_class(student.student_id, payload)


@router.patch("/{course_id}")
def update_class(
    payload: UpdateClassRequest,
    course_id: str = Path(..., description="Course id on the profile."),
    student: StudentIdentity = Depends(get_current_student),
    service: ClassService = Depends(get_class_service),
) -> StudentClass:
    """Change a class's status (FC21: not_taken/in_progress/taken/passed/failed)
    or bookmark flag (FC13)."""
    return service.update_class(student.student_id, course_id, payload)


@router.delete("/{course_id}")
def remove_class(
    course_id: str = Path(...),
    student: StudentIdentity = Depends(get_current_student),
    service: ClassService = Depends(get_class_service),
) -> DeleteClassResponse:
    """Remove a class from the profile (FC20)."""
    return service.remove_class(student.student_id, course_id)