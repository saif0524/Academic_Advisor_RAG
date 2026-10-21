"""Classes-on-profile service (FC13–FC14, FC20–FC21) — pure SQLite CRUD.

Direct UI actions: add defaults to `not_taken` (FC14), status changes (FC21)
and bookmarking (FC13) are validated enum/bool updates, removal is FC20.
Unknown course ids 404 against the catalog — no invented courses.
Assistant-initiated versions of these same mutations go through the chat
service with a confirmation token instead (FC23) — never through here.
"""
from datetime import datetime
from typing import Any

from server.schemas.classes import (
    AddClassRequest,
    DeleteClassResponse,
    StudentClass,
    StudentClassListResponse,
    UpdateClassRequest,
)
from core.entities.course import Course
from core.entities.student import EnrollmentRecord


class ClassService:
    """Wiring: `sql_db_manager` (student_classes + courses, FC33)."""

    def __init__(self, sql_db_manager: Any) -> None:
        self._sql_db_manager = sql_db_manager

    def list_classes(self, student_id: str) -> StudentClassListResponse:
        """All classes on the profile with statuses (FC14/FC21 view)."""
        records = self._sql_db_manager.list_student_classes(student_id)
        classes = [self._to_schema(record) for record in records]
        return StudentClassListResponse(results=classes, count=len(classes))

    def add_class(self, student_id: str, request: AddClassRequest) -> StudentClass:
        """Add a course, defaulting to not_taken (FC14). Unknown course ids
        raise RecordNotFoundError → 404 (grounded catalog only)."""
        record = self._sql_db_manager.add_student_class(student_id, request.course_id)
        return self._to_schema(record)

    def update_class(
        self, student_id: str, course_id: str, request: UpdateClassRequest
    ) -> StudentClass:
        """Change status (FC21) / bookmark (FC13) for one profile class.

        FC23 note: this endpoint serves direct UI dialogs only; the assistant's
        equivalents travel through the chat flow with `confirmed_action_id`.
        """
        record = self._sql_db_manager.update_student_class(
            student_id, course_id, status=request.status, bookmarked=request.bookmarked
        )
        return self._to_schema(record)

    def remove_class(self, student_id: str, course_id: str) -> DeleteClassResponse:
        """Remove a class from the profile (FC20)."""
        removed = self._sql_db_manager.remove_student_class(student_id, course_id)
        return DeleteClassResponse(course_id=course_id, removed=removed)

    def _to_schema(self, record: EnrollmentRecord) -> StudentClass:
        title = self._catalog_title(record.course_id)
        added_at = record.added_at
        if isinstance(added_at, str):  # sqlite CURRENT_TIMESTAMP format → ISO
            added_at = datetime.fromisoformat(added_at.replace("Z", ""))
        return StudentClass(
            course_id=record.course_id,
            title=title,
            status=record.status,  # type: ignore[arg-type] — enum enforced at boundary + repo
            bookmarked=bool(record.bookmarked),
            added_at=added_at,
        )

    def _catalog_title(self, course_id: str) -> str:
        """Resolve display title from the catalog; None → honest unknown."""
        try:
            course = self._sql_db_manager.get_course(course_id)
        except Exception:
            return None  # type: ignore[return-value] — title stays unknown
        return course.title if isinstance(course, Course) else None