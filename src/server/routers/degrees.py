"""Degree catalog routes (FC15, FC18)."""
from fastapi import APIRouter, Depends, Path

from server.dependencies import get_degree_service
from server.schemas.degrees import DegreeDetail, DegreeListResponse
from server.services.degrees import DegreeService

router = APIRouter(prefix="/degrees", tags=["degrees"])


@router.get("")
def list_degrees(
    service: DegreeService = Depends(get_degree_service),
) -> DegreeListResponse:
    """Explore degrees offered across departments (FC15)."""
    return service.list_degrees()


@router.get("/{degree_id}")
def get_degree(
    degree_id: str = Path(..., description="Degree id, e.g. 'CSE-BS-CSE'."),
    service: DegreeService = Depends(get_degree_service),
) -> DegreeDetail:
    """All requirements for one degree (FC18) — core, concentration, elective
    rules, credit totals; sourced only from ingested catalog records."""
    return service.get_degree(degree_id)