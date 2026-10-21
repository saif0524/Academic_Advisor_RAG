"""Student profile service (FC1, FC7, FC16–FC17, FC19, FC36)."""

from server.errors import NotWiredError
from server.schemas.students import (
    DegreeProgressResponse,
    MajorHistoryResponse,
    MajorUpdateRequest,
    SelectDegreeRequest,
    StudentProfile,
)


class StudentService:
    """Identity is header-only (FC36); profile state lives in SQL (FC33)."""

    def __init__(self, sql_db_manager) -> None:
        self._sql_db_manager = sql_db_manager

    def get_profile(self, student_id: str) -> StudentProfile:
        """Implemented scaffold method: identity mapping only (FC36).

        Name/major/interests are None until SQLite is wired — this endpoint
        never invents profile data. Optional fields fill in when the
        SQLDatabaseManager lands (outline step 3).
        """
        return StudentProfile(student_id=student_id)

    def update_major(
        self, student_id: str, request: MajorUpdateRequest
    ) -> StudentProfile:
        """Set major + specialization (FC1); records the prior combo in history (FC7).

        Enforces one major + one specialization (FC1). When the agent proposes
        this action, it arrives with a confirmation token instead (FC23).
        """
        raise NotWiredError(
            "Major changes are not wired yet: needs SQLDatabaseManager (database — outline step 3)."
        )

    def get_major_history(self, student_id: str) -> MajorHistoryResponse:
        """Current + previous major/specialty combinations (FC7)."""
        raise NotWiredError(
            "Major history is not wired yet: needs SQLDatabaseManager (database — outline step 3)."
        )

    def select_degree(self, student_id: str, request: SelectDegreeRequest) -> StudentProfile:
        """Select the tracked degree (FC17: one at a time).

        FC16 (degree aligned to the major) must be validated here against the
        catalog before persisting — not delegated to the LLM.
        """
        raise NotWiredError(
            "Degree selection is not wired yet: needs SQLDatabaseManager (database — outline step 3)."
        )

    def get_degree_progress(self, student_id: str) -> DegreeProgressResponse:
        """Progress toward the selected degree only (FC19)."""
        raise NotWiredError(
            "Degree progress is not wired yet: needs SQLDatabaseManager (database — outline step 3)."
        )
