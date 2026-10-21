"""Exact/structured lookups — SQLite side of the FC33 routing split (FC8,
FC11, FC12, FC14/FC21 state, FC1/FC7/FC16–FC19 profile data, FC6 plans).

Thin bridges over SQLDatabaseManager; tools never contain constraint logic
(the validator in core owns FC29–FC32)."""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from core.entities.course import Course, CourseSection
from core.entities.degree import DegreeRequirement
from core.entities.student import EnrollmentRecord, Student
from core.engine.progress import compute_degree_progress

from agent.tools.course_ids import normalize_course_id


class ScheduleTools:
    """Closure-style toolset over the SQL manager (rebuildable per process)."""

    def __init__(self, sql_db_manager) -> None:
        self._sql = sql_db_manager

    def find_course(self, raw_id: str) -> Optional[Course]:
        """Resolve user-supplied id text against the catalog (FC11)."""
        candidates = []
        normalized = normalize_course_id(raw_id)
        candidates.append(normalized)
        upper = (raw_id or "").strip().upper()
        if upper and upper not in candidates:
            candidates.append(upper)  # exact provenance form as given
        for candidate in candidates:
            try:
                return self._sql.get_course(candidate)
            except Exception:
                continue
        return None

    def search_courses(
        self, query: Optional[str] = None, department: Optional[str] = None,
        term: Optional[str] = None,
    ) -> List[Course]:
        """FC8 keyword + FC10 filters (SQLite is the structured side)."""
        return self._sql.list_courses(query=query, department=department, term=term)

    def sections(self, course_id: str) -> List[CourseSection]:
        """FC12."""
        return self._sql.list_sections(course_id)

    def schedule_for_term(self, course_id: str, term: str) -> List[CourseSection]:
        return self._sql.get_course_schedule(term, course_id)

    def student_profile(self, student_id: str) -> Optional[Student]:
        return self._sql.get_student_record(student_id)

    def student_classes(self, student_id: str) -> List[EnrollmentRecord]:
        """FC14/FC21 state (the FC29–FC32 input)."""
        return self._sql.list_student_classes(student_id)

    def selected_degree(self, student_id: str) -> Optional[DegreeRequirement]:
        student = self.student_profile(student_id)
        if student is None or not student.selected_degree_id:
            return None
        try:
            return self._sql.get_degree(student.selected_degree_id)
        except Exception:
            return None

    def hours_by_ids(self, course_ids: Sequence[str]) -> Dict[str, Optional[int]]:
        if not course_ids:
            return {}
        placeholders = ", ".join("?" for _ in course_ids)
        rows = self._sql.execute_query(
            f"SELECT course_id, credit_hours FROM courses WHERE course_id IN ({placeholders})",
            tuple(course_ids),
        )
        return {r["course_id"]: r["credit_hours"] for r in rows if r["credit_hours"] is not None}

    def degree_progress(self, student_id: str) -> Optional[dict]:
        """FC19 deterministic counting (core engine shared with the service)."""
        student = self.student_profile(student_id)
        if student is None or not student.selected_degree_id:
            return None
        try:
            degree = self._sql.get_degree(student.selected_degree_id)
        except Exception:
            return None
        classes = self.student_classes(student_id)
        hours: Dict[str, int] = {}
        if classes:
            hours = self.hours_by_ids({c.course_id for c in classes})
        return compute_degree_progress(degree, classes, hours)

    def list_degrees(self) -> List[DegreeRequirement]:
        """FC15 — major-name resolution for change-major proposals."""
        return self._sql.list_degrees()

    def active_plan(self, student_id: str) -> Optional[dict]:
        """FC6: the student's newest saved plan (if any) — read only."""
        rows = self._sql.list_plans(student_id)
        return rows[0] if rows else None