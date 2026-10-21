"""Degree-plan service (FC1–FC7, FC25–FC26).

Wired now: persistence reads (list/get/versions — FC6/FC3 view/FC4). Every
plan CREATION/mutation comes from the deterministic engine in `core`
(`DegreePlanGenerator.generate_multi_year_plan` — FC2/FC25; `compare_plans`/
`simulate_major_switch` — FC26) and stays 501 until that zone lands; the
service only maps engine output / store rows into HTTP schemas and never asks
an LLM to produce or modify a plan.
"""
from typing import Any, List, Optional

from server.errors import NotWiredError
from server.schemas.plans import (
    GeneratePlanRequest,
    PlanComparisonResponse,
    PlanDetail,
    PlanListResponse,
    PlanSummary,
    PlanUpdateRequest,
    PlanVersionListResponse,
    PlanVersionSummary,
    RevertPlanRequest,
    SemesterEntry,
)


class PlanService:
    """Wiring: `sql_db_manager` (saved plans/versions) + core engine (step 2)."""

    def __init__(self, sql_db_manager: Any) -> None:
        self._sql_db_manager = sql_db_manager

    # ---------------------------------------------------------- wired reads

    def list_plans(self, student_id: str) -> PlanListResponse:
        """All of the student's plans (FC6) — readable even before generation
        exists (empty until the FC2 engine can create plans)."""
        rows = self._sql_db_manager.list_plans(student_id)
        summaries = [
            PlanSummary(
                plan_id=row["plan_id"],
                student_id=row["student_id"],
                target_major=row.get("target_major"),
                concentration=row.get("concentration"),
                includes_summer=bool(row.get("includes_summer")),
                semester_count=len(row.get("semesters") or []),
                created_at=row.get("created_at"),
            )
            for row in rows
        ]
        return PlanListResponse(results=summaries, count=len(summaries))

    def get_plan(self, student_id: str, plan_id: str) -> PlanDetail:
        """One plan (FC3 view); unknown id → 404 (handled envelope)."""
        row = self._sql_db_manager.get_plan(student_id, plan_id)
        return self._to_detail(row)

    def list_versions(self, student_id: str, plan_id: str) -> PlanVersionListResponse:
        """Version history (FC4); ownership checked (student_id)."""
        self._sql_db_manager.get_plan(student_id, plan_id)  # raises 404 when absent/foreign
        rows = self._sql_db_manager.list_plan_versions(plan_id)
        versions = [
            PlanVersionSummary(
                version_id=str(row["version_number"]),
                created_at=row.get("created_at"),
                label=row.get("note"),
            )
            for row in rows
        ]
        return PlanVersionListResponse(plan_id=plan_id, versions=versions)

    # --------------------------------------------------- unwired (core engine)

    def generate_plan(self, student_id: str, request: GeneratePlanRequest) -> PlanDetail:
        """→ `DegreePlanGenerator.generate_multi_year_plan` (FC2, FC25)."""
        raise NotWiredError(
            "Plan generation is not wired yet: needs DegreePlanGenerator (core — outline step 2) "
            "(SQLDatabaseManager persistence is ready)."
        )

    def update_plan(
        self, student_id: str, plan_id: str, request: PlanUpdateRequest
    ) -> PlanDetail:
        """Edit a plan (FC3). Engine-validated edits only; creates a new version (FC4)."""
        raise NotWiredError(
            "Plan editing is not wired yet: plan edits must be engine-validated "
            "(core — outline step 2) before a version is written (FC3/FC4)."
        )

    def revert_plan(self, student_id: str, plan_id: str, request: RevertPlanRequest) -> PlanDetail:
        """Revert to a previous version (FC5)."""
        raise NotWiredError(
            "Plan revert is not wired yet: requires the plan-edit validation path "
            "(core — outline step 2)."
        )

    def compare_plans(
        self, student_id: str, existing_plan_id: str, target_major: str, target_concentration: str
    ) -> PlanComparisonResponse:
        """Side-by-side comparison (FC26) via `DegreePlanGenerator.compare_plans`."""
        raise NotWiredError(
            "Plan comparison is not wired yet: needs DegreePlanGenerator (core — outline step 2)."
        )

    # ------------------------------------------------------------ mapping

    def _to_detail(self, row: dict) -> PlanDetail:
        return PlanDetail(
            plan_id=row["plan_id"],
            student_id=row["student_id"],
            target_major=row.get("target_major"),
            concentration=row.get("concentration"),
            includes_summer=bool(row.get("includes_summer")),
            semester_count=len(row.get("semesters") or []),
            created_at=row.get("created_at"),
            semesters=[
                SemesterEntry(
                    term=semester["term"],
                    year=semester["year"],
                    courses=list(semester.get("courses") or []),
                    credits=semester.get("credits"),
                )
                for semester in (row.get("semesters") or [])
            ],
        )