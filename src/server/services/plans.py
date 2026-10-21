"""Degree-plan service (FC1–FC7, FC25–FC26).

Every plan comes from the deterministic engine in `core` (outline step 2):
`DegreePlanGenerator.generate_multi_year_plan` (FC2, FC25),
`compare_plans`/`simulate_major_switch` (FC26, FC5a–c). This service maps
engine output into HTTP schemas and persists via `SQLDatabaseManager`; it
never asks an LLM to produce or modify a plan.
"""
from typing import List, Optional

from server.errors import NotWiredError
from server.schemas.plans import (
    GeneratePlanRequest,
    PlanComparisonResponse,
    PlanDetail,
    PlanListResponse,
    PlanUpdateRequest,
    PlanVersionListResponse,
    RevertPlanRequest,
)


class PlanService:
    """Wiring: `sql_db_manager` (saved plans/versions) + core engine (outline step 2)."""

    def __init__(self, sql_db_manager) -> None:
        self._sql_db_manager = sql_db_manager

    def list_plans(self, student_id: str) -> PlanListResponse:
        """All of the student's plans (FC6)."""
        raise NotWiredError(
            "Plan listing is not wired yet: needs SQLDatabaseManager (database — outline step 3)."
        )

    def generate_plan(self, student_id: str, request: GeneratePlanRequest) -> PlanDetail:
        """→ `DegreePlanGenerator.generate_multi_year_plan` (FC2, FC25)."""
        raise NotWiredError(
            "Plan generation is not wired yet: needs DegreePlanGenerator (core — outline step 2) "
            "and SQLDatabaseManager (outline step 3)."
        )

    def get_plan(self, student_id: str, plan_id: str) -> PlanDetail:
        """One plan (FC3 view)."""
        raise NotWiredError(
            "Plan detail is not wired yet: needs SQLDatabaseManager (database — outline step 3)."
        )

    def update_plan(
        self, student_id: str, plan_id: str, request: PlanUpdateRequest
    ) -> PlanDetail:
        """Edit a plan (FC3). Engine-validated edits only; creates a new version (FC4)."""
        raise NotWiredError(
            "Plan editing is not wired yet: needs SQLDatabaseManager (database — outline step 3)."
        )

    def list_versions(self, student_id: str, plan_id: str) -> PlanVersionListResponse:
        """Version history (FC4)."""
        raise NotWiredError(
            "Plan versions are not wired yet: needs SQLDatabaseManager (database — outline step 3)."
        )

    def revert_plan(
        self, student_id: str, plan_id: str, request: RevertPlanRequest
    ) -> PlanDetail:
        """Revert to a prior version (FC5). Creates a new version carrying the revert."""
        raise NotWiredError(
            "Plan revert is not wired yet: needs SQLDatabaseManager (database — outline step 3)."
        )

    def compare_plans(
        self,
        student_id: str,
        existing_plan_id: str,
        target_major: str,
        target_concentration: str,
    ) -> PlanComparisonResponse:
        """Side-by-side comparison + trade-offs (FC26, FC5a–c simulation)."""
        raise NotWiredError(
            "Plan comparison is not wired yet: needs DegreePlanGenerator.compare_plans "
            "(core — outline step 2) and SQLDatabaseManager (outline step 3)."
        )