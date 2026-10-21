"""Classes-on-profile routes (FC13–FC14, FC20–FC21)."""
from fastapi import APIRouter, Depends, Path

from server.controllers import classes as classes_controller
from server.dependencies import get_class_service, get_current_student
from server.schemas.classes import (
    AddClassRequest,
    DeleteClassResponse,
    StudentClass,
    StudentClassListResponse,
    UpdateClassRequest,
)
from server.schemas.common import ErrorResponse
from server.schemas.students import StudentIdentity
from server.services.classes import ClassService

router = APIRouter(prefix="/classes", tags=["classes"])


@router.get(
    "",
    response_model=StudentClassListResponse,
    responses={501: {"model": ErrorResponse}},
    operation_id="list_classes",
)
def list_classes(
    student: StudentIdentity = Depends(get_current_student),
    service: ClassService = Depends(get_class_service),
) -> StudentClassListResponse:
    """All classes on the profile with their statuses (FC14, FC21)."""
    return classes_controller.list_classes(student, service)


@router.post(
    "",
    response_model=StudentClass,
    status_code=201,
    responses={501: {"model": ErrorResponse}},
    operation_id="add_class",
)
def add_class(
    payload: AddClassRequest,
    student: StudentIdentity = Depends(get_current_student),
    service: ClassService = Depends(get_class_service),
) -> StudentClass:
    """Add a class to the profile — defaults to `not_taken` (FC14).

    Unknown course ids fail against the catalog (404) — courses are never
    invented. Assistant-initiated adds go through chat with FC23 confirmation.
    """
    return classes_controller.add_class(student, payload, service)


@router.patch(
    "/{course_id}",
    response_model=StudentClass,
    responses={501: {"model": ErrorResponse}},
    operation_id="update_class",
)
def update_class(
    payload: UpdateClassRequest,
    course_id: str = Path(..., description="Course id on the profile."),
    student: StudentIdentity = Depends(get_current_student),
    service: ClassService = Depends(get_class_service),
) -> StudentClass:
    """Change a class's status (FC21: not_taken/in_progress/taken/passed/failed)
    or bookmark flag (FC13)."""
    return classes_controller.update_class(student, course_id, payload, service)


@router.delete(
    "/{course_id}",
    response_model=DeleteClassResponse,
    responses={501: {"model": ErrorResponse}},
    operation_id="remove_class",
)
def remove_class(
    course_id: str = Path(...),
    student: StudentIdentity = Depends(get_current_student),
    service: ClassService = Depends(get_class_service),
) -> DeleteClassResponse:
    """Remove a class from the profile (FC20)."""
    return classes_controller.remove_class(student, course_id, service)