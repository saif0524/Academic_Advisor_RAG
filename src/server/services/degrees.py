"""Degree catalog service (FC15, FC18) — Chroma-backed catalog text.

Degree requirement records are ingested from `data/cse_undergrad_courses.pdf`
(FC35). Structured requirement fields (core/concentration/elective rules) are
returned only once the database zone parses them — no fabricated requirements.
"""
from server.errors import NotWiredError
from server.schemas.degrees import DegreeDetail, DegreeListResponse


class DegreeService:
    """Wiring: `vector_db_manager` (catalog/requirement text) + SQLite requirements."""

    def __init__(self, sql_db_manager, vector_db_manager) -> None:
        self._sql_db_manager = sql_db_manager
        self._vector_db_manager = vector_db_manager

    def list_degrees(self) -> DegreeListResponse:
        """Degrees across departments (FC15)."""
        raise NotWiredError(
            "Degree listing is not wired yet: needs ingested requirement records "
            "(database — outline step 3, degree PDF ingest)."
        )

    def get_degree(self, degree_id: str) -> DegreeDetail:
        """All requirements for a degree (FC18)."""
        raise NotWiredError(
            "Degree requirements are not wired yet: needs ingested requirement records "
            "(database — outline step 3, degree PDF ingest)."
        )