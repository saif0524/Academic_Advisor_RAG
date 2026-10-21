"""Degree-plan contracts (FC1–FC7, FC25–FC26).

Generated plans come exclusively from `DegreePlanGenerator` (deterministic,
FC2/FC25/FC26); these models describe its output for HTTP, nothing more.
"""
from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class SemesterEntry(BaseModel):
    """One semester of a roadmap (FC25)."""

    term: str = Field(examples=["Fall"])
    year: int = Field(examples=[2026])
    courses: List[str] = Field(default_factory=list, description="Planned course ids.")
    credits: Optional[int] = None


class PlanSummary(BaseModel):
    """List-view fields of a saved plan (FC6 — multiple plans per major/spec)."""

    plan_id: str
    student_id: str
    target_major: Optional[str] = None
    concentration: Optional[str] = None
    includes_summer: bool = Field(default=False, description="Optional summer sessions (FC25).")
    semester_count: int = 0
    created_at: Optional[datetime] = None


class PlanDetail(PlanSummary):
    """Full plan: summary fields + the semester-by-semester roadmap (FC25)."""

    semesters: List[SemesterEntry] = Field(default_factory=list)
    notes: List[str] = Field(
        default_factory=list,
        description="Grounded caveats from the deterministic engine "
        "(unfulfilled buckets, excluded rows) — never invented away.",
    )


class PlanListResponse(BaseModel):
    results: List[PlanSummary]
    count: int


class GeneratePlanRequest(BaseModel):
    """Generate a plan for a major + specialization (FC1, FC2, FC25).

    Executed by the deterministic `DegreePlanGenerator` — never by the LLM.
    """

    major_name: str
    concentration: str
    include_summer: bool = False
    max_credits_per_semester: Optional[int] = Field(
        default=None,
        description="Override the degree's per-semester cap; defaults come from the degree (FC32).",
    )


class PlanUpdateRequest(BaseModel):
    """Edit an existing plan (FC3)."""

    includes_summer: Optional[bool] = None
    semesters: Optional[List[SemesterEntry]] = None


class PlanVersionSummary(BaseModel):
    """One historical version of a plan (FC4 view, FC5 revert target)."""

    version_id: str
    created_at: Optional[datetime] = None
    label: Optional[str] = None


class PlanOption(BaseModel):
    name: str
    concentrations: List[str]


class PlanOptionsResponse(BaseModel):
    """Generate-form inputs (FC1): majors from the degrees table with their
    selectable concentrations. Concentrations are not modeled in the degrees
    seed data — 'General' is the honest default offering."""

    majors: List[PlanOption]


class PlanReviewRequest(BaseModel):
    """Draft review input: unsaved semesters get the engine's FC29–FC32
    verdicts (the deterministic surface the UI's plan-check banner shows)."""

    semesters: List[SemesterEntry] = Field(default_factory=list)
    max_credits_per_semester: Optional[int] = Field(
        default=None, description="Cap override; defaults to the tracked degree's cap."
    )


class PlanReviewIssue(BaseModel):
    code: str
    course: Optional[str] = None
    text: str
    severity: Literal["blocking", "warning"]


class PlanReviewResponse(BaseModel):
    status: Literal["ok", "issues"]
    issues: List[str] = Field(default_factory=list)
    semester_issues: Dict[str, List[PlanReviewIssue]] = Field(default_factory=dict)


class PlanVersionListResponse(BaseModel):
    plan_id: str
    versions: List[PlanVersionSummary]


class RevertPlanRequest(BaseModel):
    """Revert to a previous version (FC5)."""

    version_id: str


class PlanCompareRequest(BaseModel):
    """Compare the current plan against a proposed major/concentration (FC26).

    Backed by `DegreePlanGenerator.compare_plans` / `simulate_major_switch`
    (deterministic), never by the LLM.
    """

    existing_plan_id: str
    target_major: str
    target_concentration: str


class PlanComparisonResponse(BaseModel):
    """Side-by-side comparison with trade-offs (FC26; also FC5a–c simulation)."""

    existing_plan_id: str
    target_major: str
    target_concentration: str
    advantages: List[str] = Field(default_factory=list)
    disadvantages: List[str] = Field(default_factory=list)
    retained_courses: List[str] = Field(
        default_factory=list, description="Course ids that carry over to the new plan."
    )
    lost_courses: List[str] = Field(
        default_factory=list, description="Course ids that no longer count under the new plan."
    )
    added_courses: List[str] = Field(
        default_factory=list, description="Course ids newly required by the new plan."
    )
    retained_hours: Optional[int] = None
    lost_hours: Optional[int] = None
    added_hours: Optional[int] = None
    graduation_estimate: Optional[str] = Field(
        default=None,
        description="Proposed plan's final term — grounded in the generated roadmap.",
    )