"""Degree catalog controller (FC15, FC18)."""
from server.schemas.degrees import DegreeDetail, DegreeListResponse
from server.schemas.students import StudentIdentity
from server.services.degrees import DegreeService


def list_degrees(student: StudentIdentity, service: DegreeService) -> DegreeListResponse:
    """FC15."""
    return service.list_degrees()


def get_degree(
    student: StudentIdentity, degree_id: str, service: DegreeService
) -> DegreeDetail:
    """FC18."""
    return service.get_degree(degree_id)