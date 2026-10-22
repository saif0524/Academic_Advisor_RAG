"""Classes-on-profile contracts (FC13–FC14, FC20–FC21)."""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

# FC21 statuses. Kept as a Literal so invalid statuses are rejected at the
# HTTP boundary, not by hand-written checks downstream.
ClassStatus = Literal["not_taken", "in_progress", "taken", "passed", "failed"]


class StudentClass(BaseModel):
    """One class on the student's profile."""

    course_id: str
    title: Optional[str] = Field(
        default=None, description="From the catalog; None when unknown."
    )
    status: ClassStatus = Field(
        default="not_taken", description="Added classes default to not_taken (FC14)."
    )
    bookmarked: bool = False  # FC13
    added_at: Optional[datetime] = None


class StudentClassListResponse(BaseModel):
    results: List[StudentClass]
    count: int


class AddClassRequest(BaseModel):
    """Add a course to the profile; status defaults to not_taken (FC14)."""

    course_id: str


class UpdateClassRequest(BaseModel):
    """Change a class's status (FC21) and/or bookmark flag (FC13).

    This is a direct UI action. Assistant-initiated equivalents travel through
    the chat flow with a confirmation token instead (FC23).
    """

    status: Optional[ClassStatus] = None
    bookmarked: Optional[bool] = None


class DeleteClassResponse(BaseModel):
    """Result of removing a class from the profile (FC20)."""

    course_id: str
    removed: bool