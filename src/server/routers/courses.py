"""Course discovery routes (FC8–FC12)."""
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query

from server.controllers import courses as courses_controller
from server.dependencies import get_course_service, get_current_student
from server.schemas.common import ErrorResponse
from server.schemas.courses import (
    CourseDetail,
    CourseListResponse,
    SectionListResponse,
)
from server.schemas.students import StudentIdentity
from server.services.courses import CourseService

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get(
    "",
    response_model=CourseListResponse,
    responses={501: {"model": ErrorResponse}},
    operation_id="search_courses",
)
def search_courses(
    q: Optional[str] = Query(
        None, description="Keyword search by course name or instructor (FC8)."
    ),
    department: Optional[str] = Query(None, description="Department filter (FC10)."),
    term: Optional[str] = Query(None, description="Semester-offered filter (FC10)."),
    student: StudentIdentity = Depends(get_current_student),
    service: CourseService = Depends(get_course_service),
) -> CourseListResponse:
    """Keyword course search with filters — structured lookup, answered by
    SQLite (FC8, FC10, FC33). Empty results are empty lists, never filler."""
    return courses_controller.search(student, q=q, department=department, term=term, service=service)


@router.get(
    "/search/semantic",
    response_model=CourseListResponse,
    responses={501: {"model": ErrorResponse}},
    operation_id="search_courses_semantic",
)
def search_courses_semantic(
    q: str = Query(..., min_length=1, description="Natural-language course query (FC9)."),
    student: StudentIdentity = Depends(get_current_student),
    service: CourseService = Depends(get_course_service),
) -> CourseListResponse:
    """Natural-language course discovery — semantic similarity over course
    descriptions in Chroma (FC9, FC33: vector side of the split)."""
    return courses_controller.search_semantic(student, q, service)


@router.get(
    "/{course_id}",
    response_model=CourseDetail,
    responses={501: {"model": ErrorResponse}},
    operation_id="get_course",
)
def get_course(
    course_id: str = Path(..., description="Catalog course id, e.g. '1105'."),
    student: StudentIdentity = Depends(get_current_student),
    service: CourseService = Depends(get_course_service),
) -> CourseDetail:
    """Full course detail: title, description, credits, prerequisites,
    corequisites, related degrees (FC11) plus its sections (FC12)."""
    return courses_controller.get_course(student, course_id, service)


@router.get(
    "/{course_id}/sections",
    response_model=SectionListResponse,
    responses={501: {"model": ErrorResponse}},
    operation_id="list_course_sections",
)
def list_course_sections(
    course_id: str = Path(...),
    student: StudentIdentity = Depends(get_current_student),
    service: CourseService = Depends(get_course_service),
) -> SectionListResponse:
    """Sections with date/times, days, and instructors (FC12)."""
    return courses_controller.list_sections(student, course_id, service)