"""Degree-plan controller (FC1–FC7, FC25–FC26)."""
from server.schemas.plans import (
    GeneratePlanRequest,
    PlanComparisonResponse,
    PlanDetail,
    PlanListResponse,
    PlanOptionsResponse,
    PlanReviewRequest,
    PlanReviewResponse,
    PlanUpdateRequest,
    PlanVersionListResponse,
    RevertPlanRequest,
)
from server.schemas.students import StudentIdentity
from server.services.plans import PlanService


def list_plans(student: StudentIdentity, service: PlanService) -> PlanListResponse:
    """FC6."""
    return service.list_plans(student.student_id)


def generate_plan(
    student: StudentIdentity, payload: GeneratePlanRequest, service: PlanService
) -> PlanDetail:
    """FC2/FC25 — deterministic generator output only."""
    return service.generate_plan(student.student_id, payload)


def get_plan(student: StudentIdentity, plan_id: str, service: PlanService) -> PlanDetail:
    """FC3 (view)."""
    return service.get_plan(student.student_id, plan_id)


def update_plan(
    student: StudentIdentity, plan_id: str, payload: PlanUpdateRequest, service: PlanService
) -> PlanDetail:
    """FC3 (edit)."""
    return service.update_plan(student.student_id, plan_id, payload)


def list_versions(
    student: StudentIdentity, plan_id: str, service: PlanService
) -> PlanVersionListResponse:
    """FC4."""
    return service.list_versions(student.student_id, plan_id)


def revert_plan(
    student: StudentIdentity, plan_id: str, payload: RevertPlanRequest, service: PlanService
) -> PlanDetail:
    """FC5."""
    return service.revert_plan(student.student_id, plan_id, payload)


def compare_plans(
    student: StudentIdentity, payload, service: PlanService
) -> PlanComparisonResponse:
    """FC26/FC5a–c."""
    return service.compare_plans(
        student.student_id,
        payload.existing_plan_id,
        payload.target_major,
        payload.target_concentration,
    )


def get_plan_options(service: PlanService) -> PlanOptionsResponse:
    """FC1: generate-form inputs from the degrees table."""
    return service.list_options()


def get_active_plan(student: StudentIdentity, service: PlanService) -> PlanDetail:
    """FC6: the dashboard's single active plan (404 when none is active)."""
    return service.get_active_plan(student.student_id)


def activate_plan(student: StudentIdentity, plan_id: str, service: PlanService) -> PlanDetail:
    """The explicit 'make active' step (FC6): generate → edit → activate."""
    return service.activate_plan(student.student_id, plan_id)


def review_plan(
    student: StudentIdentity, payload: PlanReviewRequest, service: PlanService
) -> PlanReviewResponse:
    """Engine verdicts over an unsaved draft (FC29–FC32 display surface)."""
    return service.review_plan(student.student_id, payload)