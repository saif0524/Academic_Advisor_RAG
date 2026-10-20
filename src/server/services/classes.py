"""Classes-on-profile service (FC13–FC14, FC20–FC21) — pure SQLite CRUD.

Direct UI actions: add defaults to `not_taken` (FC14), status changes (FC21)
and bookmarking (FC13) are validated enum/bool updates, removal is FC20.
Assistant-initiated versions of these same mutations go through the chat
service with a confirmation token instead (FC23) — never through here.
"""
from typing import Optional

from server.errors import NotWiredError
from server.schemas.classes import (
    AddClassRequest,
    DeleteClassResponse,
    StudentClass,
    StudentClassListResponse,
    UpdateClassRequest,
)


class ClassService:
    """Wiring: `sql_db_manager` (enrollments/profile tables, FC33)."""

    def __init__(self, sql_db_manager) -> None:
        self._sql_db_manager = sql_db_manager

    def list_classes(self, student_id: str) -> StudentClassListResponse:
        """All classes on the profile with statuses (FC14/FC21 view)."""
        raise NotWiredError(
            "Class listing is not wired yet: needs SQLDatabaseManager (database — outline step 3)."
        )

    def add_class(self, student_id: str, request: AddClassRequest) -> StudentClass:
        """Add a course, defaulting to not_taken (FC14). Unknown course ids must
        404 against the catalog once wired — no invented courses."""
        raise NotWiredError(
            "Adding classes is not wired yet: needs SQLDatabaseManager (database — outline step 3)."
        )

    def update_class(
        self, student_id: str, course_id: str, request: UpdateClassRequest
    ) -> StudentClass:
        """Change status (FC21) / bookmark (FC13) for one profile class."""
        raise NotWiredError(
            "Class updates are not wired yet: needs SQLDatabaseManager (database — outline step 3)."
        )

    def remove_class(self, student_id: str, course_id: str) -> DeleteClassResponse:
        """Remove a class from the profile (FC20)."""
        raise NotWiredError(
            "Class removal is not wired yet: needs SQLDatabaseManager (database — outline step 3)."
        )