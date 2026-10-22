"""Student profile routes (FC1, FC7, FC16–FC17, FC19, FC25/FC32 prefs, FC36)."""
from fastapi import APIRouter, Depends

from server.dependencies import get_current_student, get_student_service
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


@router.get("/me")
def get_profile(
    student: StudentIdentity = Depends(get_current_student),
    service: StudentService = Depends(get_student_service),
) -> StudentProfile:
    """The current student's profile (FC36 — auth is out of scope).
    Fields with no data on record are None, never filled in."""
    return service.get_profile(student.student_id)


@router.patch("/me/major")
def update_major(
    payload: MajorUpdateRequest,
    student: StudentIdentity = Depends(get_current_student),
    service: StudentService = Depends(get_student_service),
) -> StudentProfile:
    """Set major + specialization — one of each (FC1); prior combos kept in
    history (FC7). When the assistant initiates this, it carries a FC23
    confirmation from the chat flow instead of a direct patch."""
    return service.update_major(student.student_id, payload)


@router.get("/me/major-history")
def get_major_history(
    student: StudentIdentity = Depends(get_current_student),
    service: StudentService = Depends(get_student_service),
) -> MajorHistoryResponse:
    """Current + previous major/specialty combinations (FC7)."""
    return service.get_major_history(student.student_id)


@router.put("/me/degree")
def select_degree(
    payload: SelectDegreeRequest,
    student: StudentIdentity = Depends(get_current_student),
    service: StudentService = Depends(get_student_service),
) -> StudentProfile:
    """Select the tracked degree — one at a time (FC17); alignment to the
    student's major enforced server-side (FC16)."""
    return service.select_degree(student.student_id, payload)


@router.get("/me/degree/progress")
def get_degree_progress(
    student: StudentIdentity = Depends(get_current_student),
    service: StudentService = Depends(get_student_service),
) -> DegreeProgressResponse:
    """Track progress toward the selected degree only (FC19)."""
    return service.get_degree_progress(student.student_id)


@router.get("/me/preferences")
def get_preferences(
    student: StudentIdentity = Depends(get_current_student),
    service: StudentService = Depends(get_student_service),
) -> PlanningPreferences:
    """Planning-preference inputs (FC25 summer toggle, FC32 cap) — honest
    defaults when nothing was saved yet."""
    return service.get_preferences(student.student_id)


@router.put("/me/preferences")
def update_preferences(
    payload: PlanningPreferences,
    student: StudentIdentity = Depends(get_current_student),
    service: StudentService = Depends(get_student_service),
) -> PlanningPreferences:
    """Save planning preferences; plan generation consumes them (FC25/FC32)."""
    return service.update_preferences(student.student_id, payload)