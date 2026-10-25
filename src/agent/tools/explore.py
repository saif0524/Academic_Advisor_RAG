"""FC42 exploratory advising — the read-only toolset the explore agent may
call freely, and the deterministic guard applied to its final answer.

The wording is non-deterministic by design; the rules are not:
- tools are READ-ONLY (no FC23 actions can fire from here);
- every course id in the answer is resolved against the catalog — unknown ids
  are removed from the answer, real ones run through
  `CourseRecommendationValidator` (FC29–FC32) via `course_audit`.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from langchain_core.tools import StructuredTool

from agent.tools.course_ids import course_mentions

MAX_TOOL_CALLS = 6        # FC42 per-turn tool budget
MAX_VALIDATED_COURSES = 8  # cap on guard audits per answer (stream noise / latency)

READ_ONLY_TOOL_NAMES = (
    "list_programs", "degree_requirements", "search_courses", "search_catalog",
    "course_details", "my_record", "my_active_plan", "degree_progress",
    "check_eligibility",
)


def _dump(value) -> str:
    return json.dumps(value, default=str)[:6000]


def explore_tools(toolkit, student_id: str,
                  on_step: Optional[Callable[[str], None]] = None) -> List[StructuredTool]:
    """Build the FC42 read-only tools bound to one student (the model never
    passes a student id). `on_step` reports each lookup for FC39 progress."""

    def step(text: str) -> None:
        if on_step:
            on_step(text)

    def list_programs() -> str:
        """List every degree (major) on record with its credit total and its
        concentration tracks. Use for "what majors/concentrations exist?"."""
        step("SQLite: listed degrees and concentrations")
        return _dump(toolkit.list_programs())

    def degree_requirements(degree_id: str = "", concentration: str = "") -> str:
        """Requirement record for a degree (blocks) or one concentration track
        (its courses, with the student's status on each). Empty args = the
        student's own degree."""
        step(f"SQLite: read requirements {degree_id or 'your degree'} {concentration}".strip())
        return _dump(toolkit.degree_requirements(
            student_id, concentration, {"degree_id": degree_id, "concentration": concentration}))

    def search_courses(query: str) -> str:
        """Semantic search over course descriptions (topics, interests, skills).
        Returns course ids, titles, hours and descriptions."""
        step(f"Chroma: searched courses for “{query}”")
        return _dump(toolkit.semantic_courses(query, k=6))

    def search_catalog(query: str) -> str:
        """Semantic search over catalog text: degree requirements,
        certificates (e.g. AI certification), general core."""
        step(f"Chroma: searched catalog text for “{query}”")
        return _dump(toolkit.catalog_search(query, k=3))

    def course_details(course_id: str) -> str:
        """One course's catalog record (title, hours, description, prereqs,
        offered terms) plus its scheduled sections. Not an eligibility check."""
        step(f"SQLite: looked up course {course_id}")
        course = toolkit.find_course(course_id)
        if course is None:
            return _dump({"error": f"{course_id} is not in the catalog"})
        return _dump({
            "course_id": course.course_id, "title": course.title,
            "credit_hours": course.credit_hours, "description": course.description,
            "prerequisites": course.prerequisites, "corequisites": course.corequisites,
            "offered_terms": course.offered_terms,
            "sections": [{"section_id": s.section_id, "term": s.semester_term,
                          "instructor": s.instructor, "schedule": s.get_schedule_string(),
                          "open_seats": s.has_open_seats()}
                         for s in toolkit.sections(course.course_id)],
        })

    def my_record() -> str:
        """The student's profile (major, concentration, tracked degree) and
        every class on record with status and grade."""
        step("SQLite: read your profile and enrollment records")
        student = toolkit.student_profile(student_id)
        return _dump({
            "profile": None if student is None else {
                "name": student.name, "current_major": student.current_major,
                "concentration": student.concentration,
                "selected_degree_id": student.selected_degree_id},
            "classes": [{"course_id": r.course_id, "status": r.status, "grade": r.grade,
                         "semester_taken": r.semester_taken}
                        for r in toolkit.student_classes(student_id)],
        })

    def my_active_plan() -> str:
        """The student's ACTIVE degree plan, semester by semester (null if none)."""
        step("SQLite: read your active degree plan")
        return _dump(toolkit.plan_context(student_id))

    def degree_progress() -> str:
        """Completion percent and outstanding requirements for the student's
        degree, counted by the deterministic engine (FC19)."""
        step("Engine: counted degree progress")
        return _dump(toolkit.degree_audit(student_id, None))

    def check_eligibility(course_id: str) -> str:
        """Run the deterministic validator for one course: prerequisites (FC29),
        repeats (FC30), schedule conflicts (FC31), credit caps (FC32). The only
        way to decide whether the student can take a course."""
        step(f"Engine: validated {course_id} (FC29–FC32)")
        audit = toolkit.course_audit(student_id, course_id)
        if audit is None:
            return _dump({"error": f"{course_id} is not in the catalog"})
        return _dump(audit)

    funcs = (list_programs, degree_requirements, search_courses, search_catalog,
             course_details, my_record, my_active_plan, degree_progress, check_eligibility)
    return [StructuredTool.from_function(f, name=f.__name__, description=f.__doc__.strip())
            for f in funcs]


# ------------------------------------------------------------------ guard

_TERM_YEAR = re.compile(r"\b(FALL|SPRING|SUMMER|WINTER)\s+\d{4}\b", re.I)


@dataclass
class GroundedAnswer:
    text: str
    checks: List[dict] = field(default_factory=list)   # validator checks, each tagged with "course"
    removed: List[str] = field(default_factory=list)   # unknown course ids stripped from the text


def _looks_like_year(mention: str) -> bool:
    return mention.isdigit() and 1900 <= int(mention) <= 2099


def ground_answer(toolkit, student_id: str, text: str) -> GroundedAnswer:
    """FC42 deterministic guard: course ids not in the catalog are removed
    (their sentence/bullet is dropped); every real one is validated
    (FC29–FC32). Bare 19xx/20xx numbers that aren't courses are treated as years."""
    mentions = course_mentions(_TERM_YEAR.sub(" ", text or ""))
    real, unknown = [], []
    for mention in mentions:
        course = toolkit.find_course(mention)
        if course is not None:
            if course.course_id not in real:
                real.append(course.course_id)
        elif not _looks_like_year(mention):
            unknown.append(mention)

    cleaned = _strip_mentions(text or "", unknown) if unknown else (text or "")
    checks: List[dict] = []
    for course_id in real[:MAX_VALIDATED_COURSES]:
        audit = toolkit.course_audit(student_id, course_id)
        for check in (audit or {}).get("result", {}).get("checks") or []:
            checks.append({**check, "course": course_id})
    return GroundedAnswer(text=cleaned, checks=checks, removed=unknown)


def _strip_mentions(text: str, ids: List[str]) -> str:
    """Drop every sentence (or bullet line) that mentions one of `ids`."""
    numbers = {re.sub(r"\D", "", i)[-4:] for i in ids}
    pattern = re.compile(r"\b(" + "|".join(sorted(numbers)) + r")\b")
    kept_lines = []
    for line in text.split("\n"):
        if not pattern.search(line):
            kept_lines.append(line)
            continue
        sentences = re.split(r"(?<=[.!?])\s+", line)
        kept = [s for s in sentences if not pattern.search(s)]
        rest = " ".join(kept).strip()
        if rest and not re.fullmatch(r"[\s•\-*\d.)|]*", rest):
            kept_lines.append(rest)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept_lines)).strip()
