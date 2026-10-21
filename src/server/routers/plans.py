"""Degree-plan routes (FC1–FC7, FC25–FC26)."""
from fastapi import APIRouter, Depends, Path

from server.controllers import plans as plans_controller
from server.dependencies import get_current_student, get_plan_service
from server.schemas.common import ErrorResponse
from server.schemas.plans import (
    GeneratePlanRequest,
    PlanComparisonResponse,
    PlanCompareRequest,
    PlanDetail,
    PlanListResponse,
    PlanUpdateRequest,
    PlanVersionListResponse,
    RevertPlanRequest,
)
from server.schemas.students import StudentIdentity
from server.services.plans import PlanService

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get(
    "",
    response_model=PlanListResponse,
    responses={501: {"model": ErrorResponse}},
    operation_id="list_plans",
)
def list_plans(
    student: StudentIdentity = Depends(get_current_student),
    service: PlanService = Depends(get_plan_service),
) -> PlanListResponse:
    """All of the student's plans — multiple per major/spec combo (FC6)."""
    return plans_controller.list_plans(student, service)


@router.post(
    "/generate",
    response_model=PlanDetail,
    responses={501: {"model": ErrorResponse}},
    operation_id="generate_plan",
)
def generate_plan(
    payload: GeneratePlanRequest,
    student: StudentIdentity = Depends(get_current_student),
    service: PlanService = Depends(get_plan_service),
) -> PlanDetail:
    """Generate a semester-by-semester roadmap for a major + specialization
    (FC1, FC2, FC25 — optional summer). Produced only by the deterministic
    `DegreePlanGenerator`; the LLM summarizes, it never generates plans."""
    return plans_controller.generate_plan(student, payload, service)


@router.post(
    "/compare",
    response_model=PlanComparisonResponse,
    responses={501: {"model": ErrorResponse}},
    operation_id="compare_plans",
)
def compare_plans(
    payload: PlanCompareRequest,
    student: StudentIdentity = Depends(get_current_student),
    service: PlanService = Depends(get_plan_service),
) -> PlanComparisonResponse:
    """Side-by-side comparison of the existing plan vs. a proposed
    major/concentration change, with advantages/disadvantages and trade-offs
    (FC26, FC5a–c). Deterministic compare, never LLM output."""
    return plans_controller.compare_plans(student, payload, service)


@router.get(
    "/{plan_id}/versions",
    response_model=PlanVersionListResponse,
    responses={501: {"model": ErrorResponse}},
    operation_id="list_plan_versions",
)
def list_plan_versions(
    plan_id: str = Path(...),
    student: StudentIdentity = Depends(get_current_student),
    service: PlanService = Depends(get_plan_service),
) -> PlanVersionListResponse:
    """Previous versions of a plan (FC4)."""
    return plans_controller.list_versions(student, plan_id, service)


@router.post(
    "/{plan_id}/revert",
    response_model=PlanDetail,
    responses={501: {"model": ErrorResponse}},
    operation_id="revert_plan",
)
def revert_plan(
    payload: RevertPlanRequest,
    plan_id: str = Path(...),
    student: StudentIdentity = Depends(get_current_student),
    service: PlanService = Depends(get_plan_service),
) -> PlanDetail:
    """Revert a plan to a previous version (FC5)."""
    return plans_controller.revert_plan(student, plan_id, payload, service)


@router.get(
    "/{plan_id}",
    response_model=PlanDetail,
    responses={501: {"model": ErrorResponse}},
    operation_id="get_plan",
)
def get_plan(
    plan_id: str = Path(...),
    student: StudentIdentity = Depends(get_current_student),
    service: PlanService = Depends(get_plan_service),
) -> PlanDetail:
    """One plan with its semesters (FC3)."""
    return plans_controller.get_plan(student, plan_id, service)


@router.patch(
    "/{plan_id}",
    response_model=PlanDetail,
    responses={501: {"model": ErrorResponse}},
    operation_id="update_plan",
)
def update_plan(
    payload: PlanUpdateRequest,
    plan_id: str = Path(...),
    student: StudentIdentity = Depends(get_current_student),
    service: PlanService = Depends(get_plan_service),
) -> PlanDetail:
    """Edit an existing plan (FC3)."""
    return plans_controller.update_plan(student, plan_id, payload, service)