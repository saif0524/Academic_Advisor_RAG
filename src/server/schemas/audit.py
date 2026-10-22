"""Audit contracts (FC24).

Audits are produced only by the deterministic engine (FC29–FC32): every check
carries the FC id that owns it, so the client can render per-check pass/fail
with reasons — the LLM just summarizes, never decides.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class CourseAuditRequest(BaseModel):
    """Ask whether the student can take a course (FC24 first half)."""

    course_id: str
    section_id: Optional[str] = Field(
        default=None,
        description="Schedule-conflict check (FC31) runs against this section when given.",
    )


class ConstraintCheck(BaseModel):
    """One deterministic safeguard result — `check_id` names its owning FC."""

    check_id: str = Field(examples=["FC29"], description="Owning FC id (FC29–FC32).")
    description: str
    passed: Optional[bool] = Field(
        default=None, description="None when the check has no data to decide on."
    )
    reason: Optional[str] = None


class CourseAuditResponse(BaseModel):
    student_id: str
    course_id: str
    eligible: Optional[bool] = None
    checks: List[ConstraintCheck] = Field(default_factory=list)


class DegreeAuditRequest(BaseModel):
    """Degree-requirements status (FC24 second half; defaults to selected degree)."""

    degree_id: Optional[str] = None


class DegreeAuditResponse(BaseModel):
    student_id: str
    degree_id: Optional[str] = None
    completion_percent: Optional[float] = None
    checks: List[ConstraintCheck] = Field(default_factory=list)