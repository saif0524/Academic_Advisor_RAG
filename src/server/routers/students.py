"""Student profile routes (FC1, FC7, FC16–FC17, FC19, FC25/FC32 prefs, FC36)."""
from fastapi import APIRouter, Depends

from server.controllers import students as students_controller
from server.dependencies import get_current_student, get_student_service
from server.schemas.common import ErrorResponse
from server.schemas.students import (
    DegreeProgressResponse,
    MajorHistoryResponse,
    MajorUpdateRequest,
    PlanningPreferences,
    SelectDegreeRequest,
    StudentIdentity,
    StudentProfile,
)
from server.services.students import StudentService

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/me", response_model=StudentProfile, operation_id="get_my_profile")
def get_profile(
    student: StudentIdentity = Depends(get_current_student),
    service: StudentService = Depends(get_student_service),
) -> StudentProfile:
    """Pre-authenticated student identity (FC36 — auth is out of scope).

    Implemented scaffold method: echoes the header identity; profile fields
    stay None until SQLite is wired (never fabricated).
    """
    return students_controller.get_profile(student, service)


@router.patch(
    "/me/major",
    response_model=StudentProfile,
    responses={501: {"model": ErrorResponse}},
    operation_id="update_my_major",
)
def update_major(
    payload: MajorUpdateRequest,
    student: StudentIdentity = Depends(get_current_student),
    service: StudentService = Depends(get_student_service),
) -> StudentProfile:
    """Set major + specialization — one of each (FC1); prior combos kept in
    history (FC7). When the assistant initiates this, it carries a FC23
    confirmation from the chat flow instead of a direct patch."""
    return students_controller.update_major(student, payload, service)


@router.get(
    "/me/major-history",
    response_model=MajorHistoryResponse,
    responses={501: {"model": ErrorResponse}},
    operation_id="get_my_major_history",
)
def get_major_history(
    student: StudentIdentity = Depends(get_current_student),
    service: StudentService = Depends(get_student_service),
) -> MajorHistoryResponse:
    """Current + previous major/specialty combinations (FC7)."""
    return students_controller.get_major_history(student, service)


@router.put(
    "/me/degree",
    response_model=StudentProfile,
    responses={501: {"model": ErrorResponse}},
    operation_id="select_my_degree",
)
def select_degree(
    payload: SelectDegreeRequest,
    student: StudentIdentity = Depends(get_current_student),
    service: StudentService = Depends(get_student_service),
) -> StudentProfile:
    """Select the tracked degree — one at a time (FC17); alignment to the
    student's major enforced server-side (FC16)."""
    return students_controller.select_degree(student, payload, service)


@router.get(
    "/me/degree/progress",
    response_model=DegreeProgressResponse,
    responses={501: {"model": ErrorResponse}},
    operation_id="get_my_degree_progress",
)
def get_degree_progress(
    student: StudentIdentity = Depends(get_current_student),
    service: StudentService = Depends(get_student_service),
) -> DegreeProgressResponse:
    """Track progress toward the selected degree only (FC19)."""
    return students_controller.get_degree_progress(student, service)


@router.get(
    "/me/preferences",
    response_model=PlanningPreferences,
    operation_id="get_my_planning_preferences",
)
def get_preferences(
    student: StudentIdentity = Depends(get_current_student),
    service: StudentService = Depends(get_student_service),
) -> PlanningPreferences:
    """Planning-preference inputs (FC25 summer toggle, FC32 cap) — honest
    defaults when nothing was saved yet."""
    return students_controller.get_preferences(student, service)


@router.put(
    "/me/preferences",
    response_model=PlanningPreferences,
    operation_id="update_my_planning_preferences",
)
def update_preferences(
    payload: PlanningPreferences,
    student: StudentIdentity = Depends(get_current_student),
    service: StudentService = Depends(get_student_service),
) -> PlanningPreferences:
    """Save planning preferences; plan generation consumes them (FC25/FC32)."""
    return students_controller.update_preferences(student, payload, service)