"""Degree catalog service (FC15, FC18) — served from SQLite requirement records.

Degree requirement records are parsed/seeded from the catalog documents
(FC35). Structured requirement fields (core/concentration/elective rules)
come from the requirement tables — no fabricated requirements; semantic
degree text questions (FC22 fuel) stay on the Chroma side for the agent.
"""
from typing import Any

from server.schemas.degrees import DegreeDetail, DegreeListResponse, DegreeSummary


class DegreeService:
    """Wiring: `sql_db_manager` (degrees/requirement tables, FC33)."""

    def __init__(self, sql_db_manager: Any, vector_db_manager: Any) -> None:
        self._sql_db_manager = sql_db_manager
        self._vector_db_manager = vector_db_manager  # reserved for FC22 semantic degree Q&A

    def list_degrees(self) -> DegreeListResponse:
        """Degrees across departments (FC15) — exactly the ingested records."""
        degrees = self._sql_db_manager.list_degrees()
        return DegreeListResponse(
            results=[self._to_summary(d) for d in degrees],
            count=len(degrees),
        )

    def get_degree(self, degree_id: str) -> DegreeDetail:
        """All requirements for a degree (FC18); 404 when unknown."""
        degree = self._sql_db_manager.get_degree(degree_id)  # raises RecordNotFoundError
        return DegreeDetail(
            degree_id=degree.degree_id,
            major_name=degree.major_name,
            concentration_name=degree.concentration_name,
            total_credits_required=degree.total_credits_required,
            max_semester_credits=degree.max_semester_credits,
            core_courses=degree.core_courses,
            concentration_courses=degree.concentration_courses,
            concentration_tracks={
                name: [row.course_id or row.course_code
                       for block in degree.blocks if block.concentration == name
                       for row in block.courses]
                for name in degree.concentrations
            },
            concentrations=degree.concentrations,
            elective_rules=dict(degree.elective_rules) if degree.elective_rules else None,
        )

    def _to_summary(self, degree) -> DegreeSummary:
        return DegreeSummary(
            degree_id=degree.degree_id,
            major_name=degree.major_name,
            concentration_name=degree.concentration_name,
            total_credits_required=degree.total_credits_required,
            concentrations=degree.concentrations,
        )