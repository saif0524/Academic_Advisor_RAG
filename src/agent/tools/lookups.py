"""Read-only lookups the agent uses, split by data type (FC33):

- SQLite for exact facts: courses, sections, the student's classes, degrees, plans.
- Chroma for semantic search over course descriptions and catalog text (FC9).

Lookups never make eligibility decisions — that is the validator's job
(engine_tools.py). Missing data comes back as None / [] and is never invented.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from core.engine.progress import compute_degree_progress
from core.entities.course import Course, CourseSection
from core.entities.degree import DegreeRequirement
from core.entities.student import EnrollmentRecord, Student
from database.errors import RecordNotFoundError

from agent.tools.course_ids import normalize_course_id


class LookupTools:

    def __init__(self, sql_db_manager, vector_db_manager=None) -> None:
        self._sql = sql_db_manager
        self._vector = vector_db_manager

    # ------------------------------------------------------------ SQLite

    def find_course(self, raw_id: str) -> Optional[Course]:
        """Resolve user-typed course text ("CSE 4380", "4380", "ENGL 1301")."""
        for candidate in (normalize_course_id(raw_id), (raw_id or "").strip().upper()):
            try:
                return self._sql.get_course(candidate)
            except RecordNotFoundError:
                continue
        return None

    def sections(self, course_id: str) -> List[CourseSection]:
        return self._sql.list_sections(course_id)

    def student_profile(self, student_id: str) -> Optional[Student]:
        return self._sql.get_student_record(student_id)

    def student_classes(self, student_id: str) -> List[EnrollmentRecord]:
        return self._sql.list_student_classes(student_id)

    def selected_degree(self, student_id: str) -> Optional[DegreeRequirement]:
        """The degree the student is tracking (FC17), or None."""
        student = self.student_profile(student_id)
        if student is None or not student.selected_degree_id:
            return None
        return self._degree_or_none(student.selected_degree_id)

    def hours_by_ids(self, course_ids: Sequence[str]) -> Dict[str, int]:
        """course_id → credit hours, for the ids that have hours on record."""
        ids = sorted({c for c in course_ids if c})
        if not ids:
            return {}
        placeholders = ", ".join("?" for _ in ids)
        rows = self._sql.execute_query(
            f"SELECT course_id, credit_hours FROM courses WHERE course_id IN ({placeholders})",
            tuple(ids),
        )
        return {r["course_id"]: r["credit_hours"] for r in rows if r["credit_hours"] is not None}

    def degree_progress(self, student_id: str) -> Optional[dict]:
        """FC19 progress toward the selected degree (counted by core), or None."""
        degree = self.selected_degree(student_id)
        if degree is None:
            return None
        classes = self.student_classes(student_id)
        return compute_degree_progress(degree, classes, self.hours_by_ids([c.course_id for c in classes]))

    def active_plan(self, student_id: str) -> Optional[dict]:
        """FC6: the student's active plan, or None. Inactive drafts are ignored."""
        return self._sql.get_active_plan(student_id)

    def plan_context(self, student_id: str) -> Optional[dict]:
        """The active plan as a compact payload for the assistant (FC22/FC24/FC27):
        semesters, course titles, credit total, and degree progress."""
        plan = self.active_plan(student_id)
        if plan is None:
            return None
        semesters = [
            {"term": s.get("term"), "year": s.get("year"),
             "courses": list(s.get("courses") or []), "credits": s.get("credits")}
            for s in plan.get("semesters") or []
        ]
        titles: Dict[str, str] = {}
        for course_id in sorted({cid for s in semesters for cid in s["courses"]}):
            course = self._course_or_none(course_id)
            if course is not None:
                titles[course_id] = course.title  # unknown ids are shown by id only
        return {
            "plan_id": plan["plan_id"],
            "degree_id": plan.get("degree_id"),
            "target_major": plan.get("target_major"),
            "concentration": plan.get("concentration"),
            "includes_summer": bool(plan.get("includes_summer")),
            "version_number": plan.get("version_number"),
            "semesters": semesters,
            "course_titles": titles,
            "total_planned_credits": sum((s["credits"] or 0) for s in semesters),
            "progress": self.degree_progress(student_id),
        }

    # ------------------------------------------------------------ Chroma

    def semantic_courses(self, query: str, k: int = 6) -> List[dict]:
        """FC9: courses whose descriptions match the question's meaning."""
        if self._vector is None or not (query or "").strip():
            return []
        results = []
        for hit in self._vector.similarity_search("courses", query, k=k):
            metadata = hit.get("metadata") or {}
            results.append({
                "course_id": metadata.get("course_id") or hit["id"].split(":", 1)[-1],
                "title": metadata.get("title") or hit["text"].split(".")[0],
                "description": metadata.get("description") or "",
                "credit_hours": metadata.get("credit_hours"),
            })
        return results

    def catalog_search(self, query: str, k: int = 4) -> List[dict]:
        """Degree-requirement / certificate / general-core text (FC22)."""
        if self._vector is None or not (query or "").strip():
            return []
        return [
            {"source": (hit.get("metadata") or {}).get("source"),
             "kind": (hit.get("metadata") or {}).get("kind"),
             "text": hit["text"][:1200]}
            for hit in self._vector.similarity_search("catalog", query, k=k)
        ]

    # ------------------------------------------------------------ helpers

    def _course_or_none(self, course_id: str) -> Optional[Course]:
        try:
            return self._sql.get_course(course_id)
        except RecordNotFoundError:
            return None

    def _degree_or_none(self, degree_id: str) -> Optional[DegreeRequirement]:
        try:
            return self._sql.get_degree(degree_id)
        except RecordNotFoundError:
            return None
