"""Degree catalog routes (FC15, FC18)."""
from fastapi import APIRouter, Depends, Path

from server.controllers import degrees as degrees_controller
from server.dependencies import get_current_student, get_degree_service
from server.schemas.common import ErrorResponse
from server.schemas.degrees import DegreeDetail, DegreeListResponse
from server.schemas.students import StudentIdentity
from server.services.degrees import DegreeService

router = APIRouter(prefix="/degrees", tags=["degrees"])


@router.get(
    "",
    response_model=DegreeListResponse,
    responses={501: {"model": ErrorResponse}},
    operation_id="list_degrees",
)
def list_degrees(
    student: StudentIdentity = Depends(get_current_student),
    service: DegreeService = Depends(get_degree_service),
) -> DegreeListResponse:
    """Explore degrees offered across departments (FC15)."""
    return degrees_controller.list_degrees(student, service)


@router.get(
    "/{degree_id}",
    response_model=DegreeDetail,
    responses={501: {"model": ErrorResponse}},
    operation_id="get_degree",
)
def get_degree(
    degree_id: str = Path(..., description="Degree id, e.g. 'CSE-BS-CSE'."),
    student: StudentIdentity = Depends(get_current_student),
    service: DegreeService = Depends(get_degree_service),
) -> DegreeDetail:
    """All requirements for one degree (FC18) — core, concentration, elective
    rules, credit totals; sourced only from ingested catalog records."""
    return degrees_controller.get_degree(student, degree_id, service)