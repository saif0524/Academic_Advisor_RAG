"""SQLDatabaseManager — all SQLite reads and writes (FC33, FC34).

Plain stdlib `sqlite3`, no ORM. Every public method opens its own connection
via `_connect()` (commits on success, rolls back on error), so FastAPI's
thread pool never shares a connection. The schema lives in numbered .sql
files under `migrations/`, applied once each by `connect()`.

Sections below: lifecycle · students · profile classes · courses · degrees ·
plans · preferences · chat · seed writes · row mappers.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from core.entities.course import Course, CourseSection
from core.entities.degree import DegreeBlock, DegreeBlockCourse, DegreePlan, DegreeRequirement
from core.entities.student import EnrollmentRecord, Student
from database.base import DatabaseManager
from database.errors import RecordNotFoundError

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
CLASS_STATUSES = ("not_taken", "in_progress", "taken", "passed", "failed")  # FC21


class SQLDatabaseManager(DatabaseManager):

    def __init__(self, path: str) -> None:
        super().__init__(path)
        self.path = path

    # ------------------------------------------------------------- lifecycle

    def connect(self) -> bool:
        """Create the db file if needed and apply any new migrations."""
        if self.is_connected:
            return True
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
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
        self.is_connected = True
        return True

    def disconnect(self) -> None:
        self.is_connected = False  # connections are per-operation; nothing to close

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
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

    def execute_query(self, query: str, params: Any = None) -> List[dict]:
        """Run any SQL and return rows as dicts."""
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(query, params or ()).fetchall()]

    # -------------------------------------------------------------- students

    def get_student_record(self, student_id: str) -> Optional[Student]:
        """Student plus their enrollment history, or None."""
        with self._connect() as conn:
            student = _get_student(conn, student_id)
            if student is not None:
                student.completed_courses = _enrollment_history(conn, student_id)
            return student

    def ensure_student(self, student_id: str, name: Optional[str] = None) -> Student:
        """Create the student row on first use (FC36: no sign-up flow)."""
        with self._connect() as conn:
            return _ensure_student(conn, student_id, name)

    def update_student_major(
        self, student_id: str, major_name: str, concentration: Optional[str],
        record_history: bool = True,
    ) -> Student:
        """Set major + concentration (FC1) and record the change in history (FC7).

        History keeps one row per (major, concentration) combo; only the
        current one is `active`. `record_history=False` is used by the seed
        to set the initial major without logging a "change".
        """
        with self._connect() as conn:
            current = _ensure_student(conn, student_id)
            if record_history:
                conn.execute("UPDATE major_history SET active = 0 WHERE student_id = ?", (student_id,))
                if current.current_major and not _history_row(
                        conn, student_id, current.current_major, current.concentration):
                    conn.execute(
                        "INSERT INTO major_history (student_id, major_name, concentration, active) "
                        "VALUES (?, ?, ?, 0)",
                        (student_id, current.current_major, current.concentration),
                    )
                existing = _history_row(conn, student_id, major_name, concentration)
                if existing is None:
                    conn.execute(
                        "INSERT INTO major_history (student_id, major_name, concentration, active, changed_at) "
                        "VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)",
                        (student_id, major_name, concentration),
                    )
                else:
                    conn.execute(
                        "UPDATE major_history SET active = 1, changed_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (existing["id"],),
                    )
            conn.execute(
                "UPDATE students SET current_major = ?, concentration = ?, updated_at = CURRENT_TIMESTAMP "
                "WHERE student_id = ?",
                (major_name, concentration, student_id),
            )
            return _get_student(conn, student_id)  # type: ignore[return-value]

    def get_major_history(self, student_id: str) -> List[dict]:
        """FC7."""
        rows = self.execute_query(
            "SELECT major_name, concentration, active, changed_at FROM major_history "
            "WHERE student_id = ? ORDER BY changed_at, id",
            (student_id,),
        )
        for row in rows:
            row["active"] = bool(row["active"])
        return rows

    def set_selected_degree(self, student_id: str, degree_id: str) -> None:
        """FC17: one selected degree at a time (rules are checked in the service)."""
        with self._connect() as conn:
            _ensure_student(conn, student_id)
            conn.execute(
                "UPDATE students SET selected_degree_id = ?, updated_at = CURRENT_TIMESTAMP "
                "WHERE student_id = ?",
                (degree_id, student_id),
            )

    def update_profile_fields(
        self, student_id: str,
        career_interest: Optional[str] = None, include_summer_sessions: Optional[bool] = None,
    ) -> None:
        """Update whichever profile fields are given (None = leave unchanged)."""
        with self._connect() as conn:
            _ensure_student(conn, student_id)
            if career_interest is not None:
                conn.execute("UPDATE students SET career_interest = ? WHERE student_id = ?",
                             (career_interest, student_id))
            if include_summer_sessions is not None:
                conn.execute("UPDATE students SET include_summer_sessions = ? WHERE student_id = ?",
                             (int(include_summer_sessions), student_id))
            conn.execute("UPDATE students SET updated_at = CURRENT_TIMESTAMP WHERE student_id = ?",
                         (student_id,))

    def append_major_history(
        self, student_id: str, major_name: str,
        concentration: Optional[str], active: bool = False,
    ) -> None:
        """Seed helper: add a past major (FC7) without changing the current one."""
        with self._connect() as conn:
            _ensure_student(conn, student_id)
            conn.execute(
                "INSERT INTO major_history (student_id, major_name, concentration, active) "
                "VALUES (?, ?, ?, ?)",
                (student_id, major_name, concentration, int(active)),
            )

    # -------------------------------------------------------- profile classes

    def list_student_classes(self, student_id: str) -> List[EnrollmentRecord]:
        """All classes on the profile, any status (FC14)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM student_classes WHERE student_id = ? ORDER BY added_at, course_id",
                (student_id,),
            ).fetchall()
            return [_to_enrollment(r) for r in rows]

    def add_student_class(
        self, student_id: str, course_id: str,
        status: str = "not_taken", bookmarked: bool = False,
        grade: Optional[str] = None, semester_taken: Optional[str] = None,
    ) -> EnrollmentRecord:
        """Add a class to the profile (FC14). Re-adding an existing class is a no-op."""
        _check_status(status)
        with self._connect() as conn:
            if conn.execute("SELECT 1 FROM courses WHERE course_id = ?", (course_id,)).fetchone() is None:
                raise RecordNotFoundError(f"Course {course_id!r} not found in the catalog")
            conn.execute(
                "INSERT INTO student_classes (student_id, course_id, status, bookmarked, grade, semester_taken) "
                "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (student_id, course_id) DO NOTHING",
                (student_id, course_id, status, int(bookmarked), grade, semester_taken),
            )
            return _get_student_class(conn, student_id, course_id)  # type: ignore[return-value]

    def update_student_class(
        self, student_id: str, course_id: str,
        status: Optional[str] = None, bookmarked: Optional[bool] = None,
        grade: Optional[str] = None, semester_taken: Optional[str] = None,
    ) -> EnrollmentRecord:
        """Change status (FC21) or bookmark (FC13); None fields stay unchanged."""
        with self._connect() as conn:
            current = _get_student_class(conn, student_id, course_id)
            if current is None:
                raise RecordNotFoundError(f"Course {course_id!r} is not on student {student_id!r}'s profile")
            if status is not None:
                _check_status(status)
            conn.execute(
                "UPDATE student_classes SET status = ?, bookmarked = ?, grade = ?, semester_taken = ?, "
                "updated_at = CURRENT_TIMESTAMP WHERE student_id = ? AND course_id = ?",
                (
                    status or current.status,
                    int(current.bookmarked if bookmarked is None else bookmarked),
                    current.grade if grade is None else grade,
                    current.semester_taken if semester_taken is None else semester_taken,
                    student_id, course_id,
                ),
            )
            return _get_student_class(conn, student_id, course_id)  # type: ignore[return-value]

    def remove_student_class(self, student_id: str, course_id: str) -> bool:
        """FC20. True if a row was deleted."""
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM student_classes WHERE student_id = ? AND course_id = ?",
                (student_id, course_id),
            )
            return cursor.rowcount > 0

    def get_enrollment_history(self, student_id: str) -> List[EnrollmentRecord]:
        """Classes actually taken or in progress — the validator's input (FC29–FC32)."""
        with self._connect() as conn:
            return _enrollment_history(conn, student_id)

    # --------------------------------------------------------------- courses

    def list_courses(
        self, query: Optional[str] = None, department: Optional[str] = None, term: Optional[str] = None
    ) -> List[Course]:
        """Keyword search on title or instructor (FC8) with filters (FC10).

        A course counts as "offered in a term" when it has a section in that term.
        """
        sql = "SELECT DISTINCT c.* FROM courses c"
        params: List[Any] = []
        if query:
            sql += " LEFT JOIN sections s ON s.course_id = c.course_id"
        if term:
            sql += " JOIN sections ts ON ts.course_id = c.course_id AND ts.term = ?"
            params.append(term)
        conditions: List[str] = []
        if query:
            conditions.append("(UPPER(c.title) LIKE ? OR UPPER(s.instructor) LIKE ?)")
            params += [f"%{query.upper()}%", f"%{query.upper()}%"]
        if department:
            conditions.append("c.department = ?")
            params.append(department.upper())
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY c.course_id"
        with self._connect() as conn:
            return [_to_course(r) for r in conn.execute(sql, params).fetchall()]

    def get_course(self, course_id: str) -> Course:
        """Course with prerequisites and offered terms (FC11). Raises if unknown."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM courses WHERE course_id = ?", (course_id,)).fetchone()
            if row is None:
                raise RecordNotFoundError(f"Course {course_id!r} not found in the catalog")
            course = _to_course(row)
            reqs = conn.execute(
                "SELECT required_course_id, kind FROM course_prerequisites WHERE course_id = ? "
                "ORDER BY kind, required_course_id",
                (course_id,),
            ).fetchall()
            course.prerequisites = [r["required_course_id"] for r in reqs if r["kind"] == "prereq"]
            course.corequisites = [r["required_course_id"] for r in reqs if r["kind"] == "coreq"]
            terms = conn.execute(
                "SELECT DISTINCT term FROM sections WHERE course_id = ? ORDER BY term", (course_id,)
            ).fetchall()
            course.offered_terms = [r["term"] for r in terms]
            return course

    def get_catalog(self) -> Dict[str, Course]:
        """Every course by id, with prerequisites attached (input for the plan engine)."""
        catalog = {c.course_id: c for c in self.list_courses()}
        for row in self.execute_query(
                "SELECT course_id, required_course_id FROM course_prerequisites WHERE kind = 'prereq'"):
            course = catalog.get(row["course_id"])
            if course is not None and row["required_course_id"] not in course.prerequisites:
                course.prerequisites.append(row["required_course_id"])
        return catalog

    def list_sections(self, course_id: str) -> List[CourseSection]:
        """FC12."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM sections WHERE course_id = ? ORDER BY section_id", (course_id,)
            ).fetchall()
            return [_to_section(r) for r in rows]

    def get_course_schedule(self, term: str, course_id: str) -> List[CourseSection]:
        """Sections of one course in one term."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM sections WHERE course_id = ? AND term = ? ORDER BY section_id",
                (course_id, term),
            ).fetchall()
            return [_to_section(r) for r in rows]

    # --------------------------------------------------------------- degrees

    def list_degrees(self) -> List[DegreeRequirement]:
        """FC15."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM degrees ORDER BY degree_id").fetchall()
            return [_to_degree(conn, r) for r in rows]

    def get_degree(self, degree_id: str) -> DegreeRequirement:
        """FC18. Raises if unknown."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM degrees WHERE degree_id = ?", (degree_id,)).fetchone()
            if row is None:
                raise RecordNotFoundError(f"Degree {degree_id!r} not found")
            return _to_degree(conn, row)

    def get_degree_requirement_rows(self, degree_id: str) -> List[dict]:
        """Requirement blocks with their courses, for progress counting (FC19)."""
        with self._connect() as conn:
            return _requirement_rows(conn, degree_id)

    # ----------------------------------------------------------------- plans

    def save_degree_plan(self, plan: DegreePlan, payload: Optional[dict] = None) -> bool:
        """Store a new plan + its version 1 (FC2, FC4).

        New plans start inactive; the student makes one active explicitly (FC6).
        """
        payload = payload or plan.to_payload()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO plans (plan_id, student_id, degree_id, target_major, "
                "concentration, includes_summer, is_active) VALUES (?, ?, ?, ?, ?, ?, 0)",
                (plan.plan_id, plan.student_id, plan.degree_id, plan.target_major,
                 plan.concentration, int(plan.includes_summer)),
            )
            conn.execute(
                "INSERT OR IGNORE INTO plan_versions (plan_id, version_number, payload, note) "
                "VALUES (?, 1, ?, 'initial generation')",
                (plan.plan_id, json.dumps(payload)),
            )
        return True

    def list_plans(self, student_id: str) -> List[dict]:
        """FC6: every plan the student has."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM plans WHERE student_id = ? ORDER BY created_at, plan_id", (student_id,)
            ).fetchall()
            return [_to_plan(conn, r) for r in rows]

    def get_plan(self, student_id: str, plan_id: str) -> dict:
        """One plan at its latest version. Raises if unknown or not the student's."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM plans WHERE plan_id = ? AND student_id = ?", (plan_id, student_id)
            ).fetchone()
            if row is None:
                raise RecordNotFoundError(f"Plan {plan_id!r} not found for student {student_id!r}")
            return _to_plan(conn, row)

    def get_active_plan(self, student_id: str) -> Optional[dict]:
        """FC6: the active plan, or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM plans WHERE student_id = ? AND is_active = 1 ORDER BY created_at DESC",
                (student_id,),
            ).fetchone()
            return _to_plan(conn, row) if row else None

    def activate_plan(self, student_id: str, plan_id: str) -> bool:
        """Make this the student's only active plan (FC6). False if not found."""
        with self._connect() as conn:
            owned = conn.execute(
                "SELECT 1 FROM plans WHERE plan_id = ? AND student_id = ?", (plan_id, student_id)
            ).fetchone()
            if owned is None:
                return False
            conn.execute("UPDATE plans SET is_active = 0 WHERE student_id = ?", (student_id,))
            conn.execute("UPDATE plans SET is_active = 1 WHERE plan_id = ?", (plan_id,))
            return True

    def update_plan_meta(self, plan_id: str, includes_summer: Optional[bool] = None) -> None:
        if includes_summer is not None:
            with self._connect() as conn:
                conn.execute("UPDATE plans SET includes_summer = ? WHERE plan_id = ?",
                             (int(includes_summer), plan_id))

    def list_plan_versions(self, plan_id: str) -> List[dict]:
        """FC4: version history, oldest first."""
        with self._connect() as conn:
            _require_plan(conn, plan_id)
            rows = conn.execute(
                "SELECT version_number, payload, note, created_at FROM plan_versions "
                "WHERE plan_id = ? ORDER BY version_number",
                (plan_id,),
            ).fetchall()
        return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]

    def create_plan_version(self, plan_id: str, payload: dict, note: Optional[str] = None) -> int:
        """FC4: save an edit as the next version number."""
        with self._connect() as conn:
            _require_plan(conn, plan_id)
            next_number = conn.execute(
                "SELECT COALESCE(MAX(version_number), 0) + 1 FROM plan_versions WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO plan_versions (plan_id, version_number, payload, note) VALUES (?, ?, ?, ?)",
                (plan_id, next_number, json.dumps(payload), note),
            )
            return next_number

    # ----------------------------------------------------------- preferences

    def get_student_preferences(self, student_id: str) -> Optional[dict]:
        """Planning preferences (FC25/FC32), or None if never saved."""
        rows = self.execute_query(
            "SELECT max_credits_per_semester, include_summer, preferred_class_times "
            "FROM student_preferences WHERE student_id = ?",
            (student_id,),
        )
        if not rows:
            return None
        rows[0]["include_summer"] = bool(rows[0]["include_summer"])
        return rows[0]

    def update_student_preferences(
        self, student_id: str, max_credits_per_semester: Optional[int],
        include_summer: bool, preferred_class_times: Optional[str],
    ) -> dict:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO student_preferences
                       (student_id, max_credits_per_semester, include_summer, preferred_class_times)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(student_id) DO UPDATE SET
                       max_credits_per_semester = excluded.max_credits_per_semester,
                       include_summer = excluded.include_summer,
                       preferred_class_times = excluded.preferred_class_times,
                       updated_at = CURRENT_TIMESTAMP""",
                (student_id, max_credits_per_semester, int(include_summer), preferred_class_times),
            )
        return self.get_student_preferences(student_id)  # type: ignore[return-value]

    # ------------------------------------------------------------------ chat

    def ensure_chat_session(self, student_id: str) -> str:
        """Reuse the student's most recent chat session, or start one (FC27/FC34)."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT session_id FROM chat_sessions WHERE student_id = ? "
                "ORDER BY last_active_at DESC LIMIT 1",
                (student_id,),
            ).fetchone()
            if row is not None:
                session_id = row["session_id"]
                _touch_session(conn, session_id)
            else:
                session_id = f"sess-{uuid.uuid4()}"
                conn.execute("INSERT INTO chat_sessions (session_id, student_id) VALUES (?, ?)",
                             (session_id, student_id))
            return session_id

    def create_chat_session(self, student_id: str) -> str:
        """Always start a fresh chat session (new-chat button, FC27/FC34)."""
        session_id = f"sess-{uuid.uuid4()}"
        with self._connect() as conn:
            conn.execute("INSERT INTO chat_sessions (session_id, student_id) VALUES (?, ?)",
                         (session_id, student_id))
        return session_id

    def append_chat_message(self, session_id: str, student_id: str, role: str, content: str) -> None:
        """FC34: store one turn (role is 'user' or 'assistant')."""
        if role not in {"user", "assistant"}:
            raise ValueError(f"Invalid chat role {role!r}")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO chat_messages (session_id, student_id, role, content) VALUES (?, ?, ?, ?)",
                (session_id, student_id, role, content),
            )
            _touch_session(conn, session_id)

    def get_chat_history(self, student_id: str, session_id: str) -> List[dict]:
        """FC34: messages oldest-first. Raises if the session isn't the student's."""
        if not self.chat_session_exists(student_id, session_id):
            raise RecordNotFoundError(f"Chat session {session_id!r} not found for student {student_id!r}")
        return self.execute_query(
            "SELECT role, content, created_at FROM chat_messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        )

    def chat_session_exists(self, student_id: str, session_id: str) -> bool:
        """True only if the session exists AND belongs to this student."""
        rows = self.execute_query("SELECT student_id FROM chat_sessions WHERE session_id = ?", (session_id,))
        return bool(rows) and rows[0]["student_id"] == student_id

    def list_chat_sessions(self, student_id: str) -> List[dict]:
        """Chat history list, newest first; title = first user message (FC34)."""
        rows = self.execute_query(
            """SELECT s.session_id, s.created_at, s.last_active_at,
                      (SELECT SUBSTR(m.content, 1, 80) FROM chat_messages m
                       WHERE m.session_id = s.session_id AND m.role = 'user'
                       ORDER BY m.id LIMIT 1) AS title
               FROM chat_sessions s
               WHERE s.student_id = ?
               ORDER BY s.last_active_at DESC""",
            (student_id,),
        )
        for row in rows:
            row["title"] = row["title"] or "(no messages yet)"
        return rows

    # FC23 pending actions: an assistant-proposed action waits here until the
    # student confirms or cancels it (survives server restarts).

    def create_pending_action(
        self, session_id: str, student_id: str, action_type: str, description: str, payload: dict
    ) -> str:
        action_id = f"act-{uuid.uuid4()}"
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO chat_pending_actions "
                "(action_id, session_id, student_id, action_type, description, payload) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (action_id, session_id, student_id, action_type, description, json.dumps(payload)),
            )
        return action_id

    def get_pending_action(self, action_id: str) -> Optional[dict]:
        rows = self.execute_query(
            "SELECT action_id, session_id, student_id, action_type, description, payload, status, created_at "
            "FROM chat_pending_actions WHERE action_id = ?",
            (action_id,),
        )
        if not rows:
            return None
        rows[0]["payload"] = json.loads(rows[0]["payload"])
        return rows[0]

    def get_open_pending_action(self, session_id: str) -> Optional[dict]:
        """The session's newest still-open proposal (restores the confirm card on reload)."""
        rows = self.execute_query(
            "SELECT action_id, action_type, description FROM chat_pending_actions "
            "WHERE session_id = ? AND status = 'open' ORDER BY created_at DESC, rowid DESC LIMIT 1",
            (session_id,),
        )
        return rows[0] if rows else None

    def resolve_pending_action(self, action_id: str, status: str) -> bool:
        """Mark an open action 'confirmed' or 'cancelled'. False if not open/unknown."""
        if status not in {"confirmed", "cancelled"}:
            raise ValueError(f"Invalid pending-action status {status!r}")
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE chat_pending_actions SET status = ?, resolved_at = CURRENT_TIMESTAMP "
                "WHERE action_id = ? AND status = 'open'",
                (status, action_id),
            )
            return cursor.rowcount > 0

    # ------------------------------------------------------------ seed writes

    def upsert_course(self, course: Course, source: str = "corpus") -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO courses (course_id, department, number, title, description, "
                "credit_hours, course_code, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (course.course_id, course.department, course.number, course.title,
                 course.description, course.credit_hours, course.course_code, source),
            )

    def upsert_section(self, section: CourseSection) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sections (section_id, course_id, term, instructor, meeting_days, "
                "start_time, end_time, room_capacity, enrolled_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (section.section_id, section.course_id, section.semester_term, section.instructor,
                 json.dumps(section.meeting_days), section.start_time, section.end_time,
                 section.room_capacity, section.enrolled_count),
            )

    def upsert_degree(self, degree: DegreeRequirement, source_file: str) -> None:
        """Replace a degree and all of its requirement blocks/courses."""
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO degrees (degree_id, major_name, total_credits_required, "
                "max_semester_credits, institution, source_file) VALUES (?, ?, ?, ?, ?, ?)",
                (degree.degree_id, degree.major_name, degree.total_credits_required,
                 degree.max_semester_credits, degree.institution, source_file),
            )
            conn.execute("DELETE FROM degree_requirement_courses WHERE degree_id = ?", (degree.degree_id,))
            conn.execute("DELETE FROM degree_requirement_blocks WHERE degree_id = ?", (degree.degree_id,))
            for order, block in enumerate(degree.blocks):
                block_id = conn.execute(
                    "INSERT INTO degree_requirement_blocks (degree_id, block_name, kind, "
                    "credits_required, elective_bucket, sort_order) VALUES (?, ?, ?, ?, ?, ?)",
                    (degree.degree_id, block.name, block.kind, block.credits_required,
                     block.elective_bucket, order),
                ).lastrowid
                for row in block.courses:
                    conn.execute(
                        "INSERT INTO degree_requirement_courses (degree_id, block_id, course_code, "
                        "course_id, title, credit_hours, option_group) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (degree.degree_id, block_id, row.course_code, row.course_id,
                         row.title, row.credit_hours, row.option_group),
                    )

    def clear_seed_tables(self) -> None:
        """Empty the tables the seed reloads from data/ on every startup.
        Chat, plan, and preference tables are user data and are kept (FC34)."""
        with self._connect() as conn:
            for table in (
                "student_classes", "major_history", "students", "sections", "courses",
                "degree_requirement_courses", "degree_requirement_blocks", "degrees",
            ):
                conn.execute(f"DELETE FROM {table}")


# ------------------------------------------------------------------ helpers
# These take an open connection so a public method can use several of them
# inside one transaction.

def _get_student(conn: sqlite3.Connection, student_id: str) -> Optional[Student]:
    row = conn.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
    if row is None:
        return None
    return Student(
        student_id=row["student_id"],
        name=row["name"],
        current_major=row["current_major"],
        concentration=row["concentration"],
        career_interest=row["career_interest"],
        selected_degree_id=row["selected_degree_id"],
        include_summer_sessions=bool(row["include_summer_sessions"]),
    )


def _ensure_student(conn: sqlite3.Connection, student_id: str, name: Optional[str] = None) -> Student:
    conn.execute("INSERT OR IGNORE INTO students (student_id, name) VALUES (?, ?)", (student_id, name))
    return _get_student(conn, student_id)  # type: ignore[return-value]


def _history_row(conn, student_id: str, major: str, concentration: Optional[str]):
    return conn.execute(
        "SELECT id FROM major_history WHERE student_id = ? AND major_name = ? AND concentration IS ?",
        (student_id, major, concentration),
    ).fetchone()


def _check_status(status: str) -> None:
    if status not in CLASS_STATUSES:
        raise ValueError(f"Invalid class status {status!r}: must be one of {', '.join(CLASS_STATUSES)} (FC21)")


def _get_student_class(conn, student_id: str, course_id: str) -> Optional[EnrollmentRecord]:
    row = conn.execute(
        "SELECT * FROM student_classes WHERE student_id = ? AND course_id = ?", (student_id, course_id)
    ).fetchone()
    return _to_enrollment(row) if row else None


def _enrollment_history(conn, student_id: str) -> List[EnrollmentRecord]:
    rows = conn.execute(
        "SELECT * FROM student_classes WHERE student_id = ? AND status != 'not_taken' "
        "ORDER BY semester_taken IS NULL, added_at",
        (student_id,),
    ).fetchall()
    return [_to_enrollment(r) for r in rows]


def _touch_session(conn, session_id: str) -> None:
    conn.execute("UPDATE chat_sessions SET last_active_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                 (session_id,))


def _require_plan(conn, plan_id: str) -> None:
    if conn.execute("SELECT 1 FROM plans WHERE plan_id = ?", (plan_id,)).fetchone() is None:
        raise RecordNotFoundError(f"Plan {plan_id!r} not found")


def _requirement_rows(conn, degree_id: str) -> List[dict]:
    blocks = conn.execute(
        "SELECT id, block_name, kind, credits_required, elective_bucket "
        "FROM degree_requirement_blocks WHERE degree_id = ? ORDER BY sort_order, id",
        (degree_id,),
    ).fetchall()
    result = []
    for block in blocks:
        courses = conn.execute(
            "SELECT course_code, course_id, title, credit_hours, option_group "
            "FROM degree_requirement_courses WHERE block_id = ? ORDER BY id",
            (block["id"],),
        ).fetchall()
        result.append({
            "block_id": block["id"],
            "block_name": block["block_name"],
            "kind": block["kind"],
            "credits_required": block["credits_required"],
            "elective_bucket": block["elective_bucket"],
            "courses": [dict(c) for c in courses],
        })
    return result


# ------------------------------------------------------------ row mappers

def _to_enrollment(row: sqlite3.Row) -> EnrollmentRecord:
    return EnrollmentRecord(
        student_id=row["student_id"],
        course_id=row["course_id"],
        status=row["status"],
        bookmarked=bool(row["bookmarked"]),
        grade=row["grade"],
        semester_taken=row["semester_taken"],
        added_at=row["added_at"],
    )


def _to_course(row: sqlite3.Row) -> Course:
    return Course(
        course_id=row["course_id"],
        title=row["title"],
        description=row["description"],
        credit_hours=row["credit_hours"],
        department=row["department"],
        number=row["number"],
        course_code=row["course_code"],
    )


def _to_section(row: sqlite3.Row) -> CourseSection:
    return CourseSection(
        section_id=row["section_id"],
        course_id=row["course_id"],
        semester_term=row["term"],
        instructor=row["instructor"],
        meeting_days=json.loads(row["meeting_days"]),
        start_time=row["start_time"],
        end_time=row["end_time"],
        room_capacity=row["room_capacity"],
        enrolled_count=row["enrolled_count"],
    )


def _to_degree(conn, row: sqlite3.Row) -> DegreeRequirement:
    """Build a DegreeRequirement; core/concentration/elective lists are derived from its blocks."""
    blocks = [
        DegreeBlock(
            name=b["block_name"], kind=b["kind"], credits_required=b["credits_required"],
            elective_bucket=b["elective_bucket"],
            courses=[DegreeBlockCourse(**c) for c in b["courses"]],
        )
        for b in _requirement_rows(conn, row["degree_id"])
    ]

    def ids(kind: str) -> List[str]:
        return [c.course_id or c.course_code for b in blocks if b.kind == kind
                for c in b.courses if c.course_id or c.course_code]

    return DegreeRequirement(
        degree_id=row["degree_id"],
        major_name=row["major_name"],
        total_credits_required=row["total_credits_required"],
        max_semester_credits=row["max_semester_credits"],
        core_courses=ids("major_core"),
        concentration_courses=ids("concentration"),
        elective_rules={b.elective_bucket: b.credits_required or 0
                        for b in blocks if b.kind == "electives" and b.elective_bucket},
        blocks=blocks,
    )


def _to_plan(conn, row: sqlite3.Row) -> dict:
    """Plan row + its latest version's semesters/notes."""
    latest = conn.execute(
        "SELECT version_number, payload FROM plan_versions WHERE plan_id = ? "
        "ORDER BY version_number DESC LIMIT 1",
        (row["plan_id"],),
    ).fetchone()
    payload = json.loads(latest["payload"]) if latest else {}
    return {
        "plan_id": row["plan_id"],
        "student_id": row["student_id"],
        "degree_id": row["degree_id"],
        "target_major": row["target_major"],
        "concentration": row["concentration"],
        "includes_summer": bool(row["includes_summer"]),
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "version_number": latest["version_number"] if latest else 0,
        "semesters": payload.get("semesters", []),
        "notes": payload.get("notes", []),
    }
