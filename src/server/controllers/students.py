"""Student profile controller (FC1, FC7, FC16–FC17, FC19, FC36)."""
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


def get_profile(student: StudentIdentity, service: StudentService) -> StudentProfile:
    """FC36 identity → profile view (optional fields None until SQLite wires in)."""
    return service.get_profile(student.student_id)


def update_major(
    student: StudentIdentity, payload: MajorUpdateRequest, service: StudentService
) -> StudentProfile:
    """FC1 setting + FC7 history; agent-initiated changes carry FC23 confirmation."""
    return service.update_major(student.student_id, payload)


def get_major_history(student: StudentIdentity, service: StudentService) -> MajorHistoryResponse:
    """FC7."""
    return service.get_major_history(student.student_id)


def select_degree(
    student: StudentIdentity, payload: SelectDegreeRequest, service: StudentService
) -> StudentProfile:
    """FC16/FC17."""
    return service.select_degree(student.student_id, payload)


def get_degree_progress(
    student: StudentIdentity, service: StudentService
) -> DegreeProgressResponse:
    """FC19."""
    return service.get_degree_progress(student.student_id)


def get_preferences(student: StudentIdentity, service: StudentService) -> PlanningPreferences:
    """Planning-preference inputs (FC25/FC32) for the UI + plan generation."""
    return service.get_preferences(student.student_id)


def update_preferences(
    student: StudentIdentity, payload: PlanningPreferences, service: StudentService
) -> PlanningPreferences:
    """Persist planning preferences; the engine consumes them on generate."""
    return service.update_preferences(student.student_id, payload)