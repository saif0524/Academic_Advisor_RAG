"""Course discovery service (FC8–FC12) — routes by data type per FC33.

Exact/structured lookups (keyword search, filters, sections) go to SQLite;
natural-language search goes to Chroma similarity search (FC9). Both sources
echo their `source` in the response — empty lookups stay empty.
"""
from typing import Optional

from server.errors import NotWiredError
from server.schemas.courses import (
    CourseDetail,
    CourseListResponse,
    SectionListResponse,
)


class CourseService:
    """Wiring: `sql_db_manager` (SQLite repos) + `vector_db_manager` (Chroma)."""

    def __init__(self, sql_db_manager, vector_db_manager) -> None:
        self._sql_db_manager = sql_db_manager
        self._vector_db_manager = vector_db_manager

    def search_exact(
        self,
        query: Optional[str],
        department: Optional[str],
        term: Optional[str],
    ) -> CourseListResponse:
        """Keyword search by name/instructor + filters (FC8, FC10) → SQLite."""
        raise NotWiredError(
            "Course search is not wired yet: needs SQLDatabaseManager (database — outline step 3)."
        )

    def search_semantic(self, query: str) -> CourseListResponse:
        """Natural-language search (FC9) → Chroma similarity search."""
        raise NotWiredError(
            "Semantic search is not wired yet: needs VectorDatabaseManager "
            "(database — outline step 3, after course-desc.jsonl ingest)."
        )

    def get_course(self, course_id: str) -> CourseDetail:
        """Detail page (FC11): course + prerequisites + sections (FC12)."""
        raise NotWiredError(
            "Course details are not wired yet: needs SQLDatabaseManager (database — outline step 3)."
        )

    def list_sections(self, course_id: str) -> SectionListResponse:
        """Sections for one course (FC12) → SQLite."""
        raise NotWiredError(
            "Sections are not wired yet: needs SQLDatabaseManager (database — outline step 3)."
        )