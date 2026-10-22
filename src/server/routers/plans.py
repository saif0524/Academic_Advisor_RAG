"""Degree-plan routes (FC1–FC7, FC25–FC26)."""
from fastapi import APIRouter, Depends, Path

from server.dependencies import get_current_student, get_plan_service
from server.schemas.plans import (
    GeneratePlanRequest,
    PlanComparisonResponse,
    PlanCompareRequest,
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

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("")
def list_plans(
    student: StudentIdentity = Depends(get_current_student),
    service: PlanService = Depends(get_plan_service),
) -> PlanListResponse:
    """All of the student's plans — multiple per major/spec combo (FC6)."""
    return service.list_plans(student.student_id)


@router.post("/generate")
def generate_plan(
    payload: GeneratePlanRequest,
    student: StudentIdentity = Depends(get_current_student),
    service: PlanService = Depends(get_plan_service),
) -> PlanDetail:
    """Generate a semester-by-semester roadmap for a major + specialization
    (FC1, FC2, FC25 — optional summer). Produced only by the deterministic
    `DegreePlanGenerator`; the LLM summarizes, it never generates plans."""
    return service.generate_plan(student.student_id, payload)


@router.post("/compare")
def compare_plans(
    payload: PlanCompareRequest,
    student: StudentIdentity = Depends(get_current_student),
    service: PlanService = Depends(get_plan_service),
) -> PlanComparisonResponse:
    """Side-by-side comparison of the existing plan vs. a proposed
    major/concentration change, with advantages/disadvantages and trade-offs
    (FC26, FC5a–c). Deterministic compare, never LLM output."""
    return service.compare_plans(
        student.student_id, payload.existing_plan_id,
        payload.target_major, payload.target_concentration,
    )


@router.get("/options")
def get_plan_options(
    service: PlanService = Depends(get_plan_service),
) -> PlanOptionsResponse:
    """Generate-form inputs (FC1): majors from the degrees table."""
    return service.list_options()


@router.get("/active")
def get_active_plan(
    student: StudentIdentity = Depends(get_current_student),
    service: PlanService = Depends(get_plan_service),
) -> PlanDetail:
    """The student's single active plan (FC6) — 404 when nothing is active,
    so the Dashboard renders an honest empty state (never a made-up plan)."""
    return service.get_active_plan(student.student_id)


@router.post("/review")
def review_plan_draft(
    payload: PlanReviewRequest,
    student: StudentIdentity = Depends(get_current_student),
    service: PlanService = Depends(get_plan_service),
) -> PlanReviewResponse:
    """FC29–FC32 verdicts over an unsaved draft — the plan-check banner's
    deterministic surface (the LLM never grades drafts)."""
    return service.review_plan(student.student_id, payload)


@router.get("/{plan_id}/versions")
def list_plan_versions(
    plan_id: str = Path(...),
    student: StudentIdentity = Depends(get_current_student),
    service: PlanService = Depends(get_plan_service),
) -> PlanVersionListResponse:
    """Previous versions of a plan (FC4)."""
    return service.list_versions(student.student_id, plan_id)


@router.post("/{plan_id}/revert")
def revert_plan(
    payload: RevertPlanRequest,
    plan_id: str = Path(...),
    student: StudentIdentity = Depends(get_current_student),
    service: PlanService = Depends(get_plan_service),
) -> PlanDetail:
    """Revert a plan to a previous version (FC5)."""
    return service.revert_plan(student.student_id, plan_id, payload)


@router.patch("/{plan_id}/activate")
def activate_plan(
    plan_id: str = Path(...),
    student: StudentIdentity = Depends(get_current_student),
    service: PlanService = Depends(get_plan_service),
) -> PlanDetail:
    """The explicit activation step (FC6): a generated plan becomes the
    student's one active plan once it looks good — generate → edit → active."""
    return service.activate_plan(student.student_id, plan_id)


@router.get("/{plan_id}")
def get_plan(
    plan_id: str = Path(...),
    student: StudentIdentity = Depends(get_current_student),
    service: PlanService = Depends(get_plan_service),
) -> PlanDetail:
    """One plan with its semesters (FC3)."""
    return service.get_plan(student.student_id, plan_id)


@router.patch("/{plan_id}")
def update_plan(
    payload: PlanUpdateRequest,
    plan_id: str = Path(...),
    student: StudentIdentity = Depends(get_current_student),
    service: PlanService = Depends(get_plan_service),
) -> PlanDetail:
    """Edit an existing plan (FC3)."""
    return service.update_plan(student.student_id, plan_id, payload)