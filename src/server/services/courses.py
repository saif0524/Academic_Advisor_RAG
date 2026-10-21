"""Course discovery service (FC8–FC12) — routes by data type per FC33.

Exact/structured lookups (keyword search, filters, sections) go to SQLite;
natural-language search goes to Chroma similarity search (FC9). Both sources
echo their `source` in the response — empty lookups return empty lists, and
unknown ids surface as 404 (handled in server/errors.py; never fabricated).
"""
from typing import Any, List, Optional

from server.schemas.courses import (
    CourseDetail,
    CourseListResponse,
    CourseSummary,
    SectionListResponse,
    SectionSummary,
)
from core.entities.course import Course, CourseSection


class CourseService:
    """Wiring: `sql_db_manager` (SQLite repos) + `vector_db_manager` (Chroma)."""

    def __init__(self, sql_db_manager: Any, vector_db_manager: Any) -> None:
        self._sql_db_manager = sql_db_manager
        self._vector_db_manager = vector_db_manager

    def search_exact(
        self,
        query: Optional[str],
        department: Optional[str],
        term: Optional[str],
    ) -> CourseListResponse:
        """Keyword search by name/instructor + filters (FC8, FC10) → SQLite."""
        courses = self._sql_db_manager.list_courses(query=query, department=department, term=term)
        return CourseListResponse(
            results=[_to_summary(c) for c in courses],
            count=len(courses),
            source="sql",  # FC33: the structured side answered
        )

    def search_semantic(self, query: str) -> CourseListResponse:
        """Natural-language search (FC9) → Chroma similarity search only.

        Hits carry id/title/hours/description in Chroma metadata (seeded with
        the chunk); zero hits stay zero — never backfilled from the SQL side.
        """
        if self._vector_db_manager is None:
            raise RuntimeError("VectorDatabaseManager is required for FC9 semantic search")
        hits = self._vector_db_manager.similarity_search("courses", query, k=10)
        results: List[CourseSummary] = []
        for hit in hits:
            metadata = hit.get("metadata") or {}
            course_id = metadata.get("course_id") or hit["id"].split(":", 1)[-1]
            results.append(CourseSummary(
                course_id=course_id,
                title=metadata.get("title", hit["text"].split(".")[0]),
                description=metadata.get("description"),
                credit_hours=metadata.get("credit_hours"),
            ))
        return CourseListResponse(results=results, count=len(results), source="chroma")

    def get_course(self, course_id: str) -> CourseDetail:
        """Detail page (FC11): course + prerequisites + sections (FC12).

        Lookup misses propagate `database.errors.RecordNotFoundError`, mapped
        to a 404 `not_found` envelope by the server error handlers.
        """
        course = self._sql_db_manager.get_course(course_id)  # raises on unknown id
        sections = self._sql_db_manager.list_sections(course_id)
        return CourseDetail(
            course_id=course.course_id,
            title=course.title,
            description=course.description,
            credit_hours=course.credit_hours,
            prerequisites=course.prerequisites,
            corequisites=course.corequisites,
            offered_terms=course.offered_terms,
            sections=[_to_section(s) for s in sections],
        )

    def list_sections(self, course_id: str) -> SectionListResponse:
        """Sections for one course (FC12) → SQLite (empty when none exist)."""
        sections = self._sql_db_manager.list_sections(course_id)
        return SectionListResponse(
            results=[_to_section(s) for s in sections],
            count=len(sections),
        )


def _to_summary(course: Course) -> CourseSummary:
    return CourseSummary(
        course_id=course.course_id,
        title=course.title,
        description=course.description,
        credit_hours=course.credit_hours,
    )


def _to_section(section: CourseSection) -> SectionSummary:
    return SectionSummary(
        section_id=section.section_id,
        course_id=section.course_id,
        term=section.semester_term,
        instructor=section.instructor,
        meeting_days=list(section.meeting_days),
        start_time=section.start_time,
        end_time=section.end_time,
    )