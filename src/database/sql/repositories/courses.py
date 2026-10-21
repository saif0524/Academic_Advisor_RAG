"""Course + section queries (FC8/FC10/FC11/FC12 + §4 get_course_schedule)."""
from __future__ import annotations

import json
import sqlite3
from typing import List, Optional, Tuple

from core.entities.course import Course, CourseSection


def get_course(conn: sqlite3.Connection, course_id: str) -> Optional[Course]:
    row = conn.execute("SELECT * FROM courses WHERE course_id = ?", (course_id,)).fetchone()
    return _row_to_course(row) if row else None


def list_courses(
    conn: sqlite3.Connection, query: Optional[str] = None,
    department: Optional[str] = None, term: Optional[str] = None,
) -> List[Course]:
    """FC8 keyword search (title or instructor via sections) + FC10 filters.

    A course is 'offered in a term' when a section of it exists in that term —
    derived from real schedule rows, never invented.
    """
    sql = ["SELECT DISTINCT c.* FROM courses c"]
    joins, conditions, params = [], [], []
    if query:
        joins.append("LEFT JOIN sections s ON s.course_id = c.course_id")
        conditions.append("(UPPER(c.title) LIKE ? OR UPPER(s.instructor) LIKE ?)")
        params += [f"%{query.upper()}%", f"%{query.upper()}%"]
    if department:
        conditions.append("c.department = ?")
        params.append(department.upper())
    if term:
        joins.append("JOIN sections ts ON ts.course_id = c.course_id AND ts.term = ?")
        params.append(term)
    for clause in joins:
        if clause not in sql:
            sql.append(clause)
    if conditions:
        sql.append("WHERE " + " AND ".join(conditions))
    sql.append("ORDER BY c.course_id")
    rows = conn.execute("\n".join(sql), params).fetchall()
    return [_row_to_course(r) for r in rows]


def get_course_prerequisites(
    conn: sqlite3.Connection, course_id: str
) -> Tuple[List[str], List[str]]:
    """FC11: (prerequisites, corequisites) — empty when data doesn't exist."""
    rows = conn.execute(
        "SELECT required_course_id, kind FROM course_prerequisites WHERE course_id = ? "
        "ORDER BY kind, required_course_id",
        (course_id,),
    ).fetchall()
    prereqs = [r["required_course_id"] for r in rows if r["kind"] == "prereq"]
    coreqs = [r["required_course_id"] for r in rows if r["kind"] == "coreq"]
    return prereqs, coreqs


def list_sections(conn: sqlite3.Connection, course_id: str) -> List[CourseSection]:
    """FC12: sections for one course (empty list when the course has none)."""
    rows = conn.execute(
        "SELECT * FROM sections WHERE course_id = ? ORDER BY section_id", (course_id,)
    ).fetchall()
    return [_row_to_section(r) for r in rows]


def get_course_schedule(
    conn: sqlite3.Connection, term: str, course_id: str
) -> List[CourseSection]:
    """§4 get_course_schedule contract."""
    rows = conn.execute(
        "SELECT * FROM sections WHERE course_id = ? AND term = ? ORDER BY section_id",
        (course_id, term),
    ).fetchall()
    return [_row_to_section(r) for r in rows]


def upsert_course(conn: sqlite3.Connection, course: Course, source: str) -> None:
    """Seed-side write (FC33): insert-or-replace catalog row."""
    conn.execute(
        """INSERT OR REPLACE INTO courses
               (course_id, department, number, title, description, credit_hours, course_code, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            course.course_id, course.department, course.number, course.title,
            course.description, course.credit_hours, course.course_code, source,
        ),
    )


def upsert_prerequisite(conn: sqlite3.Connection, course_id: str, required: str, kind: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO course_prerequisites (course_id, required_course_id, kind) VALUES (?, ?, ?)",
        (course_id, required, kind),
    )


def upsert_section(conn: sqlite3.Connection, section: CourseSection) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO sections
               (section_id, course_id, term, instructor, meeting_days, start_time, end_time,
                room_capacity, enrolled_count)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            section.section_id, section.course_id, section.semester_term, section.instructor,
            json.dumps(section.meeting_days), section.start_time, section.end_time,
            section.room_capacity, section.enrolled_count,
        ),
    )


def _row_to_course(row: sqlite3.Row) -> Course:
    return Course(
        course_id=row["course_id"],
        title=row["title"],
        description=row["description"],
        credit_hours=row["credit_hours"],
        department=row["department"],
        number=row["number"],
        course_code=row["course_code"],
    )


def _row_to_section(row: sqlite3.Row) -> CourseSection:
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