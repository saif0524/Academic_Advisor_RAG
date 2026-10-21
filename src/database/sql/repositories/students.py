"""Student + major-history + profile-class queries (FC1/FC7/FC13/FC14/FC20/FC21, FC34-adjacent)."""
from __future__ import annotations

import sqlite3
from typing import List, Optional

from core.entities.student import EnrollmentRecord, Student

_FC21_STATUSES = ("not_taken", "in_progress", "taken", "passed", "failed")


def get_student(conn: sqlite3.Connection, student_id: str) -> Optional[Student]:
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


def ensure_student(conn: sqlite3.Connection, student_id: str, name: Optional[str] = None) -> Student:
    """FC36: lazy row creation on first write; optional fields stay NULL/False."""
    conn.execute(
        "INSERT OR IGNORE INTO students (student_id, name) VALUES (?, ?)", (student_id, name)
    )
    conn.commit()
    return get_student(conn, student_id)  # type: ignore[return-value]


def update_major(
    conn: sqlite3.Connection, student_id: str, major_name: str,
    concentration: Optional[str], record_history: bool = True,
) -> Student:
    """FC1 (one major + one concentration) + FC7 (prior combos retained, flagged inactive).

    `record_history=False` is for seeding the *initial* major (an initial value
    is not a change event; history starts empty)."""
    if record_history:
        current = get_student(conn, student_id)
        # close active rows, record/premark previous combo (FC7: one row per combo)
        conn.execute("UPDATE major_history SET active = 0 WHERE student_id = ?", (student_id,))
        if current.current_major:
            row = conn.execute(
                "SELECT id FROM major_history WHERE student_id = ? AND major_name = ? "
                "AND concentration IS ?",
                (student_id, current.current_major, current.concentration),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO major_history (student_id, major_name, concentration, active) "
                    "VALUES (?, ?, ?, 0)",
                    (student_id, current.current_major, current.concentration),
                )
        row = conn.execute(
            "SELECT id FROM major_history WHERE student_id = ? AND major_name = ? AND concentration IS ?",
            (student_id, major_name, concentration),
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO major_history (student_id, major_name, concentration, active, changed_at) "
                "VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)",
                (student_id, major_name, concentration),
            )
        else:
            # reactivating a previous combo: changed_at becomes the change event
            conn.execute(
                "UPDATE major_history SET active = 1, changed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (row["id"],),
            )
    conn.execute(
        """UPDATE students
           SET current_major = ?, concentration = ?, updated_at = CURRENT_TIMESTAMP
           WHERE student_id = ?""",
        (major_name, concentration, student_id),
    )
    conn.commit()
    return get_student(conn, student_id)  # type: ignore[return-value]


def get_major_history(conn: sqlite3.Connection, student_id: str) -> List[dict]:
    rows = conn.execute(
        "SELECT major_name, concentration, active, changed_at FROM major_history "
        "WHERE student_id = ? ORDER BY changed_at, id",
        (student_id,),
    ).fetchall()
    return [
        {
            "major_name": r["major_name"],
            "concentration": r["concentration"],
            "active": bool(r["active"]),
            "changed_at": r["changed_at"],
        }
        for r in rows
    ]


def set_selected_degree(conn: sqlite3.Connection, student_id: str, degree_id: str) -> None:
    """FC17: one selected degree at a time (a plain column update)."""
    conn.execute(
        "UPDATE students SET selected_degree_id = ?, updated_at = CURRENT_TIMESTAMP WHERE student_id = ?",
        (degree_id, student_id),
    )
    conn.commit()


def update_profile_fields(
    conn: sqlite3.Connection, student_id: str,
    career_interest: Optional[str] = None, include_summer_sessions: Optional[bool] = None,
) -> None:
    """FC25 preference (/ students profile fields the seed files carry)."""
    assignments = ["updated_at = CURRENT_TIMESTAMP"]
    params: list = []
    if career_interest is not None:
        assignments.append("career_interest = ?")
        params.append(career_interest)
    if include_summer_sessions is not None:
        assignments.append("include_summer_sessions = ?")
        params.append(int(include_summer_sessions))
    params.append(student_id)
    conn.execute(f"UPDATE students SET {', '.join(assignments)} WHERE student_id = ?", params)
    conn.commit()


def append_major_history(
    conn: sqlite3.Connection, student_id: str, major_name: str,
    concentration: Optional[str], active: bool = False,
) -> None:
    """FC7 seed-side entry (previous combos recorded without touching current)."""
    conn.execute(
        "INSERT INTO major_history (student_id, major_name, concentration, active) VALUES (?, ?, ?, ?)",
        (student_id, major_name, concentration, int(active)),
    )
    conn.commit()


def get_student_class(conn: sqlite3.Connection, student_id: str, course_id: str) -> Optional[EnrollmentRecord]:
    row = conn.execute(
        "SELECT * FROM student_classes WHERE student_id = ? AND course_id = ?",
        (student_id, course_id),
    ).fetchone()
    return _row_to_record(row) if row else None


def list_student_classes(conn: sqlite3.Connection, student_id: str) -> List[EnrollmentRecord]:
    rows = conn.execute(
        "SELECT * FROM student_classes WHERE student_id = ? ORDER BY added_at, course_id",
        (student_id,),
    ).fetchall()
    return [_row_to_record(r) for r in rows]


def add_student_class(
    conn: sqlite3.Connection, student_id: str, course_id: str,
    status: str = "not_taken", bookmarked: bool = False,
    grade: Optional[str] = None, semester_taken: Optional[str] = None,
) -> EnrollmentRecord:
    """FC14: added classes default to not_taken; UNIQUE(student,course) makes
    re-adds idempotent updates of the existing row."""
    if status not in _FC21_STATUSES:
        raise ValueError(f"Invalid class status {status!r}: must be one of {', '.join(_FC21_STATUSES)} (FC21)")
    conn.execute(
        """INSERT INTO student_classes
               (student_id, course_id, status, bookmarked, grade, semester_taken)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT (student_id, course_id) DO NOTHING""",
        (student_id, course_id, status, int(bookmarked), grade, semester_taken),
    )
    conn.commit()
    return get_student_class(conn, student_id, course_id)  # type: ignore[return-value]


def update_student_class(
    conn: sqlite3.Connection, student_id: str, course_id: str,
    status: Optional[str] = None, bookmarked: Optional[bool] = None,
    grade: Optional[str] = None, semester_taken: Optional[str] = None,
) -> EnrollmentRecord:
    """FC21/FC13. Unknown (student, course) row → RecordNotFoundError."""
    from database.errors import RecordNotFoundError

    current = get_student_class(conn, student_id, course_id)
    if current is None:
        raise RecordNotFoundError(f"Course {course_id!r} is not on student {student_id!r}'s profile")
    if status is not None and status not in _FC21_STATUSES:
        raise ValueError(f"Invalid class status {status!r}: must be one of {', '.join(_FC21_STATUSES)} (FC21)")
    conn.execute(
        """UPDATE student_classes
           SET status = ?, bookmarked = ?, grade = ?, semester_taken = ?, updated_at = CURRENT_TIMESTAMP
           WHERE student_id = ? AND course_id = ?""",
        (
            status or current.status,
            int(bookmarked) if bookmarked is not None else int(current.bookmarked),
            grade if grade is not None else current.grade,
            semester_taken if semester_taken is not None else current.semester_taken,
            student_id, course_id,
        ),
    )
    conn.commit()
    return get_student_class(conn, student_id, course_id)  # type: ignore[return-value]


def remove_student_class(conn: sqlite3.Connection, student_id: str, course_id: str) -> bool:
    """FC20: True when a row was deleted, False when it wasn't there."""
    cursor = conn.execute(
        "DELETE FROM student_classes WHERE student_id = ? AND course_id = ?",
        (student_id, course_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def get_enrollment_history(conn: sqlite3.Connection, student_id: str) -> List[EnrollmentRecord]:
    """§4 contract: real enrollment states only (feed for FC29–FC32 checks)."""
    rows = conn.execute(
        "SELECT * FROM student_classes WHERE student_id = ? AND status != 'not_taken' "
        "ORDER BY semester_taken IS NULL, added_at",
        (student_id,),
    ).fetchall()
    return [_row_to_record(r) for r in rows]


def _row_to_record(row: sqlite3.Row) -> EnrollmentRecord:
    return EnrollmentRecord(
        student_id=row["student_id"],
        course_id=row["course_id"],
        status=row["status"],
        bookmarked=bool(row["bookmarked"]),
        grade=row["grade"],
        semester_taken=row["semester_taken"],
        added_at=row["added_at"],
    )