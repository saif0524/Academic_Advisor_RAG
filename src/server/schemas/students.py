"""Student profile contracts (FC1, FC7, FC16–FC17, FC19, FC36).

`StudentIdentity` is the only contract that never touches a database: FC36
makes auth out of scope, so identity is the pre-authenticated header value
plus dev fallback.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class StudentIdentity(BaseModel):
    """Minimal pre-auth identity (FC36) — no fabricated profile fields."""

    student_id: str


class StudentProfile(BaseModel):
    """Profile view. Optional fields are None until SQLite is wired (honest data)."""

    student_id: str
    name: Optional[str] = None
    current_major: Optional[str] = None
    concentration: Optional[str] = None
    career_interest: Optional[str] = None


class MajorUpdateRequest(BaseModel):
    """Set major + specialization; one of each (FC1). Prior combos retained (FC7)."""

    major_name: str
    concentration: str


class MajorHistoryEntry(BaseModel):
    """A past major/concentration combination (FC7)."""

    major_name: str
    concentration: Optional[str] = None
    active: bool = False
    changed_at: Optional[datetime] = None


class MajorHistoryResponse(BaseModel):
    results: List[MajorHistoryEntry]
    count: int


class SelectDegreeRequest(BaseModel):
    """Select the tracked degree (FC17: one at a time; FC16 alignment enforced server-side)."""

    degree_id: str


class DegreeProgressResponse(BaseModel):
    """Progress toward the selected degree only (FC19)."""

    degree_id: Optional[str] = None
    completion_percent: Optional[float] = None
    completed_hours: Optional[int] = Field(
        default=None, description="Passed/taken hours that count (FC19 counting)."
    )
    in_progress_hours: Optional[int] = None
    total_credits_required: Optional[int] = Field(
        default=None, description="The degree's total credit ceiling."
    )
    outstanding_requirements: List[str] = Field(default_factory=list)


class PlanningPreferences(BaseModel):
    """Planning-preference inputs (FC25 summer toggle, FC32 cap input)."""

    max_credits_per_semester: Optional[int] = Field(
        default=None,
        description="Per-semester credit cap (FC32 input); None = not set yet.",
    )
    include_summer: bool = False
    preferred_class_times: Optional[str] = None