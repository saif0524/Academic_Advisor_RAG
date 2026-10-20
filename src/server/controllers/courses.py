"""Course discovery controller (FC8–FC12)."""
from typing import Optional

from server.schemas.courses import CourseDetail, CourseListResponse, SectionListResponse
from server.schemas.students import StudentIdentity
from server.services.courses import CourseService


def search(
    student: StudentIdentity,
    q: Optional[str],
    department: Optional[str],
    term: Optional[str],
    service: CourseService,
) -> CourseListResponse:
    """Keyword/filter search → SQL (FC8, FC10)."""
    return service.search_exact(query=q, department=department, term=term)


def search_semantic(student: StudentIdentity, query: str, service: CourseService) -> CourseListResponse:
    """Natural-language search → Chroma (FC9)."""
    return service.search_semantic(query)


def get_course(student: StudentIdentity, course_id: str, service: CourseService) -> CourseDetail:
    """Course detail incl. sections (FC11–FC12). Lookup misses → 404 via handlers."""
    return service.get_course(course_id)


def list_sections(
    student: StudentIdentity, course_id: str, service: CourseService
) -> SectionListResponse:
    """Sections for a course (FC12)."""
    return service.list_sections(course_id)