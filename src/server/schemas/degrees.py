"""Degree catalog contracts (FC15, FC18).

Degree requirement text/records are ingested into Chroma from
`data/cse_undergrad_courses.pdf` (FC35); structured requirement fields land
here once the database zone parses them.
"""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DegreeSummary(BaseModel):
    """Browse-view fields (FC15 — degrees offered across departments)."""

    degree_id: str = Field(examples=["CSE-BS-CSE"])
    major_name: str = Field(examples=["BS in Computer Science"])
    concentration_name: Optional[str] = Field(
        default=None, description="Specialization, e.g. 'Cybersecurity' (FC1: one per student)."
    )
    total_credits_required: Optional[int] = None


class DegreeListResponse(BaseModel):
    results: List[DegreeSummary]
    count: int


class DegreeDetail(DegreeSummary):
    """All requirements for one degree (FC18)."""

    max_semester_credits: Optional[int] = Field(
        default=None, description="Per-semester cap enforced by FC32 (e.g. 18)."
    )
    core_courses: List[str] = Field(default_factory=list, description="Core course ids.")
    concentration_courses: List[str] = Field(default_factory=list)
    elective_rules: Optional[Dict[str, int]] = Field(
        default=None,
        description="Elective buckets, e.g. {'Technical Electives': 9, 'General Ed': 12}.",
    )