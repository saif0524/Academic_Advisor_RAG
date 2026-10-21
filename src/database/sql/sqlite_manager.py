"""SQLDatabaseManager (§4) — SQLite via stdlib, no ORM (dependency-light).

One connection per operation (`_connect()` context manager) so FastAPI's
threadpool never shares a connection across threads. Migrations are numbered
forward-only .sql files in `migrations/` tracked by `schema_migrations`.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, List, Optional, Tuple

from core.entities.course import Course, CourseSection
from core.entities.degree import DegreePlan, DegreeRequirement
from core.entities.student import EnrollmentRecord, Student
from database.base import DatabaseManager
from database.errors import RecordNotFoundError
from database.sql.repositories import (
    chat as chat_repo,
    courses as courses_repo,
    degrees as degree_repo,
    plans as plans_repo,
    students as student_repo,
)

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


class SQLDatabaseManager(DatabaseManager):
    """§4 SQL side (FC33, FC34). All repository methods are thin and explicit."""

    def __init__(self, path: str) -> None:
        super().__init__(path)
        self.path = path

    # ------------------------------------------------------------- lifecycle

    def connect(self) -> bool:
        """Open a probe connection + apply pending migrations (idempotent)."""
        if self.is_connected:
            return True
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)  # sqlite can't create parents
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "    version TEXT PRIMARY KEY,"
                "    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            applied = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations")}
            for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
                if migration.name not in applied:
                    conn.executescript(migration.read_text())
                    conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (migration.name,))
            conn.commit()
        self.is_connected = True
        return True

    def disconnect(self) -> None:
        self.is_connected = False  # connections are per-operation; nothing cached

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """One fresh connection per operation; commits on success, rolls back
        on error — every manager method is atomic from the caller's view."""
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        self.is_connected = True

    def execute_query(self, query: str, params: Any = None) -> List[dict]:
        """§4 generic escape hatch — always returns list[dict]."""
        with self._connect() as conn:
            rows = conn.execute(query, params or ()).fetchall()
            return [dict(r) for r in rows]

    # ---------------------------------------------------------- students (§4)

    def get_student_record(self, student_id: str) -> Optional[Student]:
        with self._connect() as conn:
            student = student_repo.get_student(conn, student_id)
            if student is not None:
                student.completed_courses = student_repo.get_enrollment_history(conn, student_id)
            return student

    def ensure_student(self, student_id: str, name: Optional[str] = None) -> Student:
        """FC36: lazy row creation for the pre-auth session id."""
        with self._connect() as conn:
            return student_repo.ensure_student(conn, student_id, name)

    def update_student_major(
        self, student_id: str, major_name: str, concentration: Optional[str],
        record_history: bool = True,
    ) -> Student:
        """FC1 + FC7; record_history=False seeds the initial major (no event)."""
        with self._connect() as conn:
            student_repo.ensure_student(conn, student_id)
            return student_repo.update_major(
                conn, student_id, major_name, concentration, record_history=record_history
            )

    def get_major_history(self, student_id: str) -> List[dict]:
        """FC7."""
        with self._connect() as conn:
            return student_repo.get_major_history(conn, student_id)

    def set_selected_degree(self, student_id: str, degree_id: str) -> None:
        """FC16/FC17 enforcement happens in the service; this is persistence."""
        with self._connect() as conn:
            student_repo.ensure_student(conn, student_id)
            student_repo.set_selected_degree(conn, student_id, degree_id)

    def update_profile_fields(
        self, student_id: str,
        career_interest: Optional[str] = None, include_summer_sessions: Optional[bool] = None,
    ) -> None:
        with self._connect() as conn:
            student_repo.ensure_student(conn, student_id)
            student_repo.update_profile_fields(
                conn, student_id, career_interest=career_interest,
                include_summer_sessions=include_summer_sessions,
            )

    def append_major_history(
        self, student_id: str, major_name: str,
        concentration: Optional[str], active: bool = False,
    ) -> None:
        """FC7 seed-side history entry (does not change the current major)."""
        with self._connect() as conn:
            student_repo.ensure_student(conn, student_id)
            student_repo.append_major_history(conn, student_id, major_name, concentration, active)

    # ----------------------------------------------------------- classes (§4)

    def list_student_classes(self, student_id: str) -> List[EnrollmentRecord]:
        """FC14 view (profile classes with statuses)."""
        with self._connect() as conn:
            return student_repo.list_student_classes(conn, student_id)

    def add_student_class(
        self, student_id: str, course_id: str,
        status: str = "not_taken", bookmarked: bool = False,
        grade: Optional[str] = None, semester_taken: Optional[str] = None,
    ) -> EnrollmentRecord:
        """FC14 (default not_taken); unknown course → RecordNotFoundError (404)."""
        with self._connect() as conn:
            if courses_repo.get_course(conn, course_id) is None:
                raise RecordNotFoundError(f"Course {course_id!r} not found in the catalog")
            return student_repo.add_student_class(
                conn, student_id, course_id, status=status, bookmarked=bookmarked,
                grade=grade, semester_taken=semester_taken,
            )

    def update_student_class(
        self, student_id: str, course_id: str,
        status: Optional[str] = None, bookmarked: Optional[bool] = None,
        grade: Optional[str] = None, semester_taken: Optional[str] = None,
    ) -> EnrollmentRecord:
        """FC21 (status) / FC13 (bookmark)."""
        with self._connect() as conn:
            return student_repo.update_student_class(
                conn, student_id, course_id, status=status, bookmarked=bookmarked,
                grade=grade, semester_taken=semester_taken,
            )

    def remove_student_class(self, student_id: str, course_id: str) -> bool:
        """FC20."""
        with self._connect() as conn:
            return student_repo.remove_student_class(conn, student_id, course_id)

    def get_enrollment_history(self, student_id: str) -> List[EnrollmentRecord]:
        """§4 contract: real states only (FC29–FC32 validator inputs)."""
        with self._connect() as conn:
            return student_repo.get_enrollment_history(conn, student_id)

    # ----------------------------------------------------------- courses (§4)

    def list_courses(
        self, query: Optional[str] = None, department: Optional[str] = None, term: Optional[str] = None
    ) -> List[Course]:
        """FC8 (keyword: title or instructor) + FC10 filters."""
        with self._connect() as conn:
            return courses_repo.list_courses(conn, query=query, department=department, term=term)

    def get_course(self, course_id: str) -> Course:
        """FC11 base fields; RecordNotFoundError when absent."""
        with self._connect() as conn:
            course = courses_repo.get_course(conn, course_id)
            if course is None:
                raise RecordNotFoundError(f"Course {course_id!r} not found in the catalog")
            prereqs, coreqs = courses_repo.get_course_prerequisites(conn, course_id)
            course.prerequisites, course.corequisites = prereqs, coreqs
            course.offered_terms = self._offered_terms(conn, course_id)
            return course

    def list_sections(self, course_id: str) -> List[CourseSection]:
        """FC12."""
        with self._connect() as conn:
            return courses_repo.list_sections(conn, course_id)

    def get_course_schedule(self, term: str, course_id: str) -> List[CourseSection]:
        """§4 contract."""
        with self._connect() as conn:
            return courses_repo.get_course_schedule(conn, term, course_id)

    def _offered_terms(self, conn: sqlite3.Connection, course_id: str) -> List[str]:
        rows = conn.execute(
            "SELECT DISTINCT term FROM sections WHERE course_id = ? ORDER BY term", (course_id,)
        ).fetchall()
        return [r["term"] for r in rows]

    # ----------------------------------------------------------- degrees (§4)

    def list_degrees(self) -> List[DegreeRequirement]:
        """FC15."""
        with self._connect() as conn:
            return degree_repo.list_degrees(conn)

    def get_degree(self, degree_id: str) -> DegreeRequirement:
        """FC18; RecordNotFoundError when absent."""
        with self._connect() as conn:
            degree = degree_repo.get_degree(conn, degree_id)
            if degree is None:
                raise RecordNotFoundError(f"Degree {degree_id!r} not found")
            return degree

    def get_degree_requirement_rows(self, degree_id: str) -> List[dict]:
        """FC19 fuel: block-level rows for deterministic counting."""
        with self._connect() as conn:
            return degree_repo.get_degree_requirement_rows(conn, degree_id)

    # ------------------------------------------------------------- plans (§4)

    def save_degree_plan(self, plan: DegreePlan) -> bool:
        """§4 contract (FC2 destination + FC4 first version)."""
        with self._connect() as conn:
            return plans_repo.save_degree_plan(conn, plan)

    def list_plans(self, student_id: str) -> List[dict]:
        """FC6."""
        with self._connect() as conn:
            return plans_repo.list_plans(conn, student_id)

    def get_plan(self, student_id: str, plan_id: str) -> dict:
        with self._connect() as conn:
            return plans_repo.get_plan(conn, student_id, plan_id)

    def list_plan_versions(self, plan_id: str) -> List[dict]:
        """FC4."""
        with self._connect() as conn:
            return plans_repo.list_plan_versions(conn, plan_id)

    def create_plan_version(self, plan_id: str, payload: dict, note: Optional[str] = None) -> int:
        with self._connect() as conn:
            return plans_repo.create_plan_version(conn, plan_id, payload, note)

    # -------------------------------------------------------------- chat (§4+

    def ensure_chat_session(self, student_id: str) -> str:
        """FC27/FC34."""
        with self._connect() as conn:
            return chat_repo.ensure_chat_session(conn, student_id)

    def append_chat_message(self, session_id: str, student_id: str, role: str, content: str) -> None:
        """FC34."""
        with self._connect() as conn:
            chat_repo.append_chat_message(conn, session_id, student_id, role, content)

    def get_chat_history(self, student_id: str, session_id: str) -> List[dict]:
        """FC34; unknown session → RecordNotFoundError."""
        with self._connect() as conn:
            return chat_repo.get_chat_history(conn, student_id, session_id)

    def create_pending_action(
        self, session_id: str, student_id: str, action_type: str, description: str, payload: dict
    ) -> str:
        """FC23 groundwork (agent step consumes this)."""
        with self._connect() as conn:
            return chat_repo.create_pending_action(conn, session_id, student_id, action_type, description, payload)

    def get_pending_action(self, action_id: str) -> Optional[dict]:
        with self._connect() as conn:
            return chat_repo.get_pending_action(conn, action_id)

    def resolve_pending_action(self, action_id: str, status: str) -> bool:
        with self._connect() as conn:
            return chat_repo.resolve_pending_action(conn, action_id, status)

    # ------------------------------------------------------ seed-side writes

    def upsert_course(self, course: Course, source: str = "corpus") -> None:
        with self._connect() as conn:
            courses_repo.upsert_course(conn, course, source)

    def upsert_section(self, section: CourseSection) -> None:
        with self._connect() as conn:
            courses_repo.upsert_section(conn, section)

    def upsert_degree(self, degree: DegreeRequirement, source_file: str) -> None:
        with self._connect() as conn:
            degree_repo.upsert_degree(conn, degree, source_file)

    def clear_seed_tables(self) -> None:
        """Reload semantics (product decision): seed-owned tables are refreshed
        from data/ on every startup; user-owned chat/plan tables persist (FC34)."""
        with self._connect() as conn:
            for table in (
                "student_classes", "major_history", "students", "sections", "courses",
                "degree_requirement_courses", "degree_requirement_blocks", "degrees",
            ):
                conn.execute(f"DELETE FROM {table}")
            conn.commit()
