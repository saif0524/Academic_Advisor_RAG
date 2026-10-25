"""Degree-plan service (FC1–FC7, FC25–FC26).

Every plan is created, checked, and compared by `DegreePlanGenerator` in
`core` — never by an LLM. This service loads inputs from SQLite, calls the
engine, saves the result, and maps it to HTTP schemas.

Flow: generate → edit → make active. New plans start inactive.
"""
from __future__ import annotations

import uuid
from typing import Any, List, Optional, Tuple

from core.engine.generator import DegreePlanGenerator, semesters_payload
from core.entities.degree import DegreeRequirement, SemesterPlan
from core.entities.student import Student
from server.errors import InvalidRequestError, RecordNotFoundError
from server.schemas.plans import (
    GeneratePlanRequest,
    PlanComparisonResponse,
    PlanDetail,
    PlanListResponse,
    PlanOptionsResponse,
    PlanOption,
    PlanReviewRequest,
    PlanReviewResponse,
    PlanSummary,
    PlanUpdateRequest,
    PlanVersionListResponse,
    PlanVersionSummary,
    ProfileUpdate,
    RevertPlanRequest,
    SemesterEntry,
)


class PlanService:
    """Wiring: `sql_db_manager` (catalog/degrees/plans, FC33) + core engine."""

    # Always offered: the degree without a concentration track (FC1).
    GENERAL_CONCENTRATION = "General"

    def __init__(self, sql_db_manager: Any) -> None:
        self._sql_db_manager = sql_db_manager

    # ---------------------------------------------------- reads (FC6/FC3/FC4)

    def list_plans(self, student_id: str) -> PlanListResponse:
        """All of the student's plans (FC6); `active` echoes which one is live."""
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

    def get_active_plan(self, student_id: str) -> PlanDetail:
        """The Dashboard's plan (FC6): the single active one, 404 when none."""
        row = self._sql_db_manager.get_active_plan(student_id)
        if row is None:
            raise RecordNotFoundError(f"No active degree plan for student {student_id!r}")
        return self._to_detail(row)

    def activate_plan(self, student_id: str, plan_id: str) -> PlanDetail:
        """Make a plan active — the explicit "make active" step (FC6); the
        profile follows it (FC1/FC17)."""
        if not self._sql_db_manager.activate_plan(student_id, plan_id):
            raise RecordNotFoundError(f"Plan {plan_id!r} not found for student {student_id!r}")
        changed = self._sql_db_manager.sync_profile_to_plan(student_id, plan_id)
        return self._detail_with_profile(student_id, plan_id, changed)

    def list_options(self) -> PlanOptionsResponse:
        """Generate-form inputs (FC1): majors from the degrees table."""
        majors: List[PlanOption] = []
        seen = set()
        for degree in self._sql_db_manager.list_degrees():
            if degree.major_name in seen:
                continue
            seen.add(degree.major_name)
            majors.append(PlanOption(
                name=degree.major_name,
                concentrations=[*degree.concentrations, self.GENERAL_CONCENTRATION],
            ))
        return PlanOptionsResponse(majors=majors)

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

    # ------------------------------------------------- engine-backed writes

    def generate_plan(self, student_id: str, request: GeneratePlanRequest) -> PlanDetail:
        """Generate a semester roadmap (FC2, FC25) via DegreePlanGenerator;
        persists as a NEW versioned plan and makes it the ACTIVE plan (FC6:
        any plan change activates the changed plan by default); no FC23 gate
        applies (creating plans is not an on-behalf action)."""
        degree = self._resolve_degree(request.major_name)
        concentration = self._resolve_concentration(degree, request.concentration)
        student = self._student(student_id)
        prefs = self._sql_db_manager.get_student_preferences(student_id) or {}
        cap = request.max_credits_per_semester or prefs.get("max_credits_per_semester")
        include_summer = request.include_summer or bool(prefs.get("include_summer"))

        catalog = self._sql_db_manager.get_catalog()
        result = DegreePlanGenerator.generate_multi_year_plan(
            student, degree, catalog,
            include_summer=include_summer, max_credits_per_sem=cap,
            concentration=concentration,
        )
        plan = result.plan
        plan.concentration = concentration
        plan.plan_id = f"plan-{uuid.uuid4().hex[:10]}"
        self._sql_db_manager.save_degree_plan(plan, payload={
            "semesters": semesters_payload(plan.semesters, catalog),
            "includes_summer": plan.includes_summer,
            "notes": list(result.notes),
        })
        return self._activate(student_id, plan.plan_id)  # FC6: changed plan → active

    def update_plan(
        self, student_id: str, plan_id: str, request: PlanUpdateRequest
    ) -> PlanDetail:
        """Edit a plan (FC3) — engine-validated, then a new version (FC4).

        Blocking issues (FC30 re-planning a passed course, FC32 cap breach)
        reject the save with 422; advisory FC29 ordering issues save with the
        verdicts available via POST /plans/review."""
        row = self._sql_db_manager.get_plan(student_id, plan_id)
        if request.semesters is None and request.includes_summer is None:
            return self._to_detail(row)  # nothing to change (FC3 no-op)
        catalog = self._sql_db_manager.get_catalog()
        records = self._sql_db_manager.list_student_classes(student_id)
        cap = self._degree_cap(row.get("degree_id"))

        semesters = self._to_engine_semesters(
            request.semesters if request.semesters is not None else row["semesters"])
        includes_summer = (
            request.includes_summer if request.includes_summer is not None
            else bool(row.get("includes_summer")))

        review = DegreePlanGenerator.review_plan_semesters(
            semesters, records, catalog, max_credits_per_sem=cap)
        blocking = review.blocking()
        if blocking:
            raise InvalidRequestError(
                "The plan edit violates deterministic safeguards — nothing was saved",
                details=[issue["text"] for issue in blocking],
            )

        notes = row.get("notes") or []
        payload = {
            "semesters": semesters_payload(semesters, catalog),
            "includes_summer": includes_summer,
            "notes": notes,
        }
        self._sql_db_manager.create_plan_version(plan_id, payload, note="edited plan (FC3)")
        if request.includes_summer is not None:
            self._sql_db_manager.update_plan_meta(plan_id, includes_summer=includes_summer)
        return self._activate(student_id, plan_id)  # FC6: changed plan → active

    def revert_plan(self, student_id: str, plan_id: str, request: RevertPlanRequest) -> PlanDetail:
        """Revert to a previous version (FC5) — history-style: the restored
        payload becomes a NEW version so the timeline stays honest."""
        row = self._sql_db_manager.get_plan(student_id, plan_id)
        try:
            version_number = int(request.version_id)
        except ValueError:
            raise InvalidRequestError(f"Version id {request.version_id!r} is not a number")
        versions = self._sql_db_manager.list_plan_versions(plan_id)
        target = next((v for v in versions if v["version_number"] == version_number), None)
        if target is None:
            raise RecordNotFoundError(
                f"Version {request.version_id!r} not found for plan {plan_id!r}")
        payload = dict(target.get("payload") or {"semesters": []})
        payload.setdefault("notes", row.get("notes") or [])
        self._sql_db_manager.create_plan_version(
            plan_id, payload, note=f"reverted to version {version_number} (FC5)")
        if "includes_summer" in payload:
            self._sql_db_manager.update_plan_meta(
                plan_id, includes_summer=bool(payload["includes_summer"]))
        return self._activate(student_id, plan_id)  # FC6: changed plan → active

    def compare_plans(
        self, student_id: str, existing_plan_id: str, target_major: str,
        target_concentration: str,
    ) -> PlanComparisonResponse:
        """FC26 comparison: the existing plan vs the would-be plan for the
        target major/concentration — engine-generated and diffed, never LLM."""
        row = self._sql_db_manager.get_plan(student_id, existing_plan_id)  # 404 grounded
        degree = self._resolve_degree(target_major)
        concentration = self._resolve_concentration(degree, target_concentration)
        student = self._student(student_id)
        catalog = self._sql_db_manager.get_catalog()

        new_result = DegreePlanGenerator.simulate_major_switch(
            student, degree, catalog, concentration=concentration)
        existing_sems = [
            SemesterPlan(term=s["term"], year=s["year"],
                         course_ids=list(s.get("courses") or []))
            for s in (row.get("semesters") or [])
        ]
        comparison = DegreePlanGenerator.compare_plans(
            existing_sems, new_result.plan.semesters, catalog)
        return PlanComparisonResponse(
            existing_plan_id=existing_plan_id,
            target_major=target_major,
            target_concentration=concentration,
            advantages=comparison.advantages,
            disadvantages=comparison.disadvantages,
            retained_courses=comparison.retained,
            lost_courses=comparison.lost,
            added_courses=comparison.added,
            retained_hours=int(comparison.retained_hours),
            lost_hours=int(comparison.lost_hours),
            added_hours=int(comparison.added_hours),
            graduation_estimate=comparison.graduation_estimate,
        )

    def review_plan(self, student_id: str, request: PlanReviewRequest) -> PlanReviewResponse:
        """Engine verdicts over an unsaved draft (FC29–FC32 display surface)."""
        records = self._sql_db_manager.list_student_classes(student_id)
        catalog = self._sql_db_manager.get_catalog()
        cap = request.max_credits_per_semester or self._selected_degree_cap(student_id)
        review = DegreePlanGenerator.review_plan_semesters(
            self._to_engine_semesters(request.semesters), records, catalog, max_credits_per_sem=cap)
        return PlanReviewResponse(
            status=review.status, issues=review.issues, semester_issues=review.semester_issues)

    # ------------------------------------------------------------ plumbing

    def _student(self, student_id: str) -> Student:
        """Lazy-profile student with hydrated class records (FC30 fuel)."""
        student = self._sql_db_manager.get_student_record(student_id)
        if student is None:
            return Student(student_id=student_id)
        student.completed_courses = self._sql_db_manager.list_student_classes(student_id)
        return student

    def _resolve_degree(self, major_name: str) -> DegreeRequirement:
        """Degree lookup by major name (case-insensitive); 404 when unknown."""
        wanted = (major_name or "").strip().lower()
        for degree in self._sql_db_manager.list_degrees():
            if (degree.major_name or "").strip().lower() == wanted:
                return degree
        raise RecordNotFoundError(f"No degree on record for major {major_name!r}")

    def _resolve_concentration(self, degree: DegreeRequirement, requested: Optional[str]) -> str:
        """Match a requested track against the degree's offered concentrations
        (case-insensitive). 'General'/empty means no track; anything else that
        isn't offered is a 422 listing the real options — never guessed."""
        wanted = (requested or "").strip()
        if wanted.lower() in ("", self.GENERAL_CONCENTRATION.lower()):
            return self.GENERAL_CONCENTRATION
        match = next((n for n in degree.concentrations if n.lower() == wanted.lower()), None)
        if match is None:
            offered = ", ".join([*degree.concentrations, self.GENERAL_CONCENTRATION])
            raise InvalidRequestError(
                f"{degree.major_name} has no {wanted!r} concentration",
                details=[f"offered concentrations: {offered}"],
            )
        return match

    def _degree_cap(self, degree_id: Optional[str]) -> Optional[int]:
        if not degree_id:
            return None
        try:
            return self._sql_db_manager.get_degree(degree_id).max_semester_credits
        except RecordNotFoundError:
            return None  # unknown degree → review without a cap

    def _selected_degree_cap(self, student_id: str) -> Optional[int]:
        student = self._sql_db_manager.get_student_record(student_id)
        if student is None or not student.selected_degree_id:
            return None
        return self._degree_cap(student.selected_degree_id)

    @staticmethod
    def _to_engine_semesters(entries) -> List[tuple]:
        """Schema entries or stored dicts → (term, year, courses) tuples for the engine."""
        tuples: List[Tuple[str, int, List[str]]] = []
        for entry in entries:
            if isinstance(entry, dict):
                term, year, courses = entry.get("term"), entry.get("year"), list(entry.get("courses") or [])
            else:
                term, year, courses = entry.term, entry.year, list(entry.courses)
            tuples.append((str(term), int(year), courses))
        return tuples

    def _activate(self, student_id: str, plan_id: str) -> PlanDetail:
        """FC6: make the plan active AND make the profile follow it (major,
        concentration FC1, tracked degree FC17) — the one activation path
        every plan write uses, so plan and profile never disagree."""
        self._sql_db_manager.activate_plan(student_id, plan_id)
        changed = self._sql_db_manager.sync_profile_to_plan(student_id, plan_id)
        return self._detail_with_profile(student_id, plan_id, changed)

    def _detail_with_profile(self, student_id: str, plan_id: str, changed) -> PlanDetail:
        detail = self.get_plan(student_id, plan_id)
        if changed:
            detail.profile_updated = ProfileUpdate(**changed)
        return detail

    def _to_detail(self, row: dict) -> PlanDetail:
        return PlanDetail(
            plan_id=row["plan_id"],
            student_id=row["student_id"],
            target_major=row.get("target_major"),
            concentration=row.get("concentration"),
            includes_summer=bool(row.get("includes_summer")),
            semester_count=len(row.get("semesters") or []),
            created_at=row.get("created_at"),
            notes=[str(note) for note in (row.get("notes") or [])],
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