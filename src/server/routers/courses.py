"""Course discovery routes (FC8–FC12)."""
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query

from server.dependencies import get_course_service
from server.schemas.courses import (
    CourseDetail,
    CourseListResponse,
    SectionListResponse,
)
from server.services.courses import CourseService

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("")
def search_courses(
    q: Optional[str] = Query(
        None, description="Keyword search by course name or instructor (FC8)."
    ),
    department: Optional[str] = Query(None, description="Department filter (FC10)."),
    term: Optional[str] = Query(None, description="Semester-offered filter (FC10)."),
    service: CourseService = Depends(get_course_service),
) -> CourseListResponse:
    """Keyword course search with filters — structured lookup, answered by
    SQLite (FC8, FC10, FC33). Empty results are empty lists, never filler."""
    return service.search_exact(query=q, department=department, term=term)


@router.get("/search/semantic")
def search_courses_semantic(
    q: str = Query(..., min_length=1, description="Natural-language course query (FC9)."),
    service: CourseService = Depends(get_course_service),
) -> CourseListResponse:
    """Natural-language course discovery — semantic similarity over course
    descriptions in Chroma (FC9, FC33: vector side of the split)."""
    return service.search_semantic(q)


@router.get("/{course_id}")
def get_course(
    course_id: str = Path(..., description="Catalog course id, e.g. '1105'."),
    service: CourseService = Depends(get_course_service),
) -> CourseDetail:
    """Full course detail: title, description, credits, prerequisites,
    corequisites, related degrees (FC11) plus its sections (FC12)."""
    return service.get_course(course_id)


@router.get("/{course_id}/sections")
def list_course_sections(
    course_id: str = Path(...),
    service: CourseService = Depends(get_course_service),
) -> SectionListResponse:
    """Sections with date/times, days, and instructors (FC12)."""
    return service.list_sections(course_id)