"""Course discovery contracts (FC8–FC12; routing per FC33).

Note the data-type split the service layer must honor: keyword/structured
search (FC8/FC10) hits SQLite, semantic/natural-language search (FC9) hits
Chroma — `CourseListResponse.source` echoes which backend answered.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class CourseSummary(BaseModel):
    """Compact course card — enough for result lists, not for detail pages."""

    course_id: str = Field(examples=["1105"], description="Catalog id (seed corpus ids are 4-digit).")
    title: str
    description: Optional[str] = None
    credit_hours: Optional[int] = None


class CourseListResponse(BaseModel):
    """Search results + which store answered (FC33 routing transparency).

    Empty lookups return `results: []` + a count of 0 — never fabricated filler.
    """

    results: List[CourseSummary]
    count: int
    source: Optional[Literal["sql", "chroma"]] = Field(
        default=None, description="Which store answered: SQLite (FC8/FC10) or Chroma (FC9)."
    )


class SectionSummary(BaseModel):
    """One scheduled section (FC12)."""

    section_id: str
    course_id: str
    term: Optional[str] = Field(default=None, examples=["Fall 2026"])
    instructor: Optional[str] = None
    meeting_days: List[str] = Field(default_factory=list, examples=[["Monday", "Wednesday"]])
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class SectionListResponse(BaseModel):
    results: List[SectionSummary]
    count: int


class CourseDetail(BaseModel):
    """Full course detail page payload (FC11) including its sections (FC12)."""

    course_id: str
    title: str
    description: Optional[str] = None
    credit_hours: Optional[int] = None
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisite course ids.")
    corequisites: List[str] = Field(default_factory=list)
    offered_terms: List[str] = Field(default_factory=list, examples=[["Fall", "Spring"]])
    sections: List[SectionSummary] = Field(default_factory=list)