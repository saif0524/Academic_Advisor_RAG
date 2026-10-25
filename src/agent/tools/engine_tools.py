"""Tools backed by the deterministic engine in `core/` — the only way the
agent can answer "can I take X?", "what should I take?", "how far along am
I?", or "build me a plan".

The LLM never decides eligibility or builds plans. Every answer here comes
from `CourseRecommendationValidator` (FC29–FC32), `compute_degree_progress`
(FC19/FC24) or `DegreePlanGenerator` (FC2/FC25).
"""
from __future__ import annotations

import re
import uuid
from typing import List, Optional, Sequence

from core.engine.generator import DegreePlanGenerator, semesters_payload
from core.engine.progress import compute_degree_progress
from core.engine.results import ConstraintCheck
from core.engine.validator import CourseRecommendationValidator
from core.entities.course import Course, CourseSection
from core.entities.degree import DegreeRequirement
from core.entities.student import EnrollmentRecord, Student

from agent.tools.lookups import LookupTools


def _normalize_concentration(name: Optional[str]) -> str:
    """Fold case, whitespace, and punctuation so formatting-only differences in
    a concentration name ("Datascience", "data-science", "Data  Science")
    collapse to one key for tolerant matching (FC1)."""
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


class EngineTools(LookupTools):

    # ----------------------------------------------------------- FC24 audits

    def course_audit(
        self, student_id: str, course_raw: str, section_id: Optional[str] = None
    ) -> Optional[dict]:
        """"Can I take X?" — run every safeguard check. None if the course doesn't exist."""
        course = self.find_course(course_raw)
        if course is None:
            return None
        records = self.student_classes(student_id)
        in_progress = [r for r in records if r.status == "in_progress"]
        section = self._pick_section(course, section_id, against=self._sections_of(in_progress))
        result = self._check_course(
            course, records, self.selected_degree(student_id),
            section=section,
            semester_sections=self._sections_of(in_progress, same_term_as=section),
            semester_hours=sum(self.hours_by_ids([r.course_id for r in in_progress]).values()),
        )
        return {
            "course": {
                "course_id": course.course_id,
                "title": course.title,
                "description": course.description,
                "credit_hours": course.credit_hours,
                "prerequisites": course.prerequisites,
                "corequisites": course.corequisites,
            },
            "result": result,
        }

    def degree_audit(self, student_id: str, degree_id: Optional[str] = None) -> Optional[dict]:
        """What's left for the degree (FC24, FC19). None if no degree is found."""
        degree = self._degree_or_none(degree_id) if degree_id else self.selected_degree(student_id)
        if degree is None:
            return None
        classes = self.student_classes(student_id)
        totals = compute_degree_progress(degree, classes, self.hours_by_ids([c.course_id for c in classes]))
        checks = [
            ConstraintCheck(
                check_id="FC19", description=f"{degree.degree_id} · {line}",
                passed=None, reason=line.split(":", 1)[-1].strip(),
            ).payload()
            for line in totals["outstanding_requirements"]
        ]
        return {
            "degree_id": degree.degree_id,
            "major_name": degree.major_name,
            "completion_percent": totals["completion_percent"],
            "outstanding_requirements": totals["outstanding_requirements"],
            "checks": checks,
        }

    # ------------------------------------------------------ recommendations

    def recommend_candidates(self, student_id: str, query: Optional[str], k: int = 6,
                             exclude_ids: Sequence[str] = ()) -> dict:
        """"What should I take?" (FC22). Candidates come from semantic search
        when there's a query, otherwise from the degree's remaining courses.
        Every candidate is run through the validator (FC29–FC32)."""
        pool = self._recommendation_pool(student_id, query, pool_size=k + len(exclude_ids))
        already_planned = [c.course_id for c in pool if c.course_id in exclude_ids]
        pool = [c for c in pool if c.course_id not in exclude_ids][:k]

        records = self.student_classes(student_id)
        degree = self.selected_degree(student_id)
        in_progress_sections = self._sections_of([r for r in records if r.status == "in_progress"])
        candidates = []
        for course in pool:
            result = self._check_course(
                course, records, degree,
                section=self._pick_section(course, None, against=in_progress_sections),
                semester_sections=in_progress_sections,
            )
            blocking = next((c for c in result["checks"] if c["passed"] is False), None)
            candidates.append({
                "course_id": course.course_id,
                "title": course.title,
                "credit_hours": course.credit_hours,
                "eligible": result["eligible"],
                "checks": result["checks"],
                "reason": blocking["reason"] if blocking else "Eligible on every record check",
            })
        return {"query": query, "candidates": candidates, "already_planned": already_planned}

    # ------------------------------------------------------ plan generation

    def resolve_plan_target(self, student_id: str, params: Optional[dict] = None) -> dict:
        """FC1/FC2: which degree + concentration a plan request means.
        Returns {"degree", "concentration", "refusal"} — never invents a track."""
        params = params or {}
        student = self.student_profile(student_id) or Student(student_id=student_id)
        target_major, concentration = self._split_target(params.get("target_major"), params.get("concentration"))
        # The FULL degree record: `selected_degree` is already narrowed to the
        # student's own track and would hide every other concentration (FC1).
        degree = (self._resolve_major(target_major) if target_major
                  else self._degree_or_none(student.selected_degree_id) if student.selected_degree_id
                  else None)
        if degree is None:
            if target_major:
                refusal = (f"I couldn't match a degree plan to {target_major!r} — offered "
                           f"majors: {self._major_names()}.")
            else:
                refusal = ("You don't have a major or selected degree on record yet — "
                           "set your major first (FC1) and I can generate from there.")
            return {"degree": None, "concentration": None, "refusal": refusal}

        # FC1: a named track wins; otherwise the student's own track when planning
        # for their own major, and "General" when planning for a different one.
        if concentration is None:
            own_major = not target_major or degree.major_name == student.current_major
            concentration = student.concentration if own_major else "General"
        # FC1: match the named track tolerantly — case, whitespace, and
        # punctuation differences ("Datascience" ~ "Data Science") resolve to
        # the catalog spelling instead of a hard refusal. Matching stays
        # deterministic; only exact-but-for-formatting names collapse.
        named = next((n for n in degree.concentrations if n.lower() == (concentration or "").lower()), None)
        if named is None and _normalize_concentration(concentration) not in ("", "general"):
            key = _normalize_concentration(concentration)
            named = next((n for n in degree.concentrations
                          if _normalize_concentration(n) == key), None)
        if (concentration or "").lower() not in ("", "general") and named is None:
            offered = ", ".join([*degree.concentrations, "General"])
            return {"degree": degree, "concentration": None, "refusal": (
                f"{degree.major_name} has no {concentration!r} concentration on record. "
                f"Offered: {offered}.")}
        return {"degree": degree, "concentration": named or "General", "refusal": None}

    def plan_program_change(self, student_id: str, params: Optional[dict] = None) -> Optional[dict]:
        """FC6/FC23: a plan for a DIFFERENT major or concentration would change
        the student's account (the profile follows the active plan), so the
        assistant must propose that change instead of generating directly.
        Returns the FC23 action {action_type, ...params}, or None when the plan
        is for the student's current program (or the request is refused)."""
        target = self.resolve_plan_target(student_id, params)
        degree = target["degree"]
        if degree is None or target["refusal"]:
            return None
        student = self.student_profile(student_id)
        current_major = student.current_major if student else None
        current_track = ((student.concentration if student else None) or "General").lower()
        if degree.major_name != current_major:
            return {"action_type": "change_major", "major_name": degree.major_name,
                    "concentration": target["concentration"]}
        if target["concentration"].lower() != current_track:
            return {"action_type": "change_concentration", "concentration": target["concentration"]}
        return None

    def generate_plan(self, student_id: str, params: Optional[dict] = None) -> dict:
        """"Build me a plan" (FC2/FC25): DegreePlanGenerator builds it; we save
        it as the student's ACTIVE plan (FC6: a changed plan is active by
        default) and the profile follows it (FC1/FC17)."""
        params = params or {}
        student = self.student_profile(student_id) or Student(student_id=student_id)
        student.completed_courses = self.student_classes(student_id)
        target = self.resolve_plan_target(student_id, params)
        if target["refusal"]:
            return {"plan": None, "notes": [], "refusal": target["refusal"]}
        degree, named = target["degree"], target["concentration"]

        catalog = self._sql.get_catalog()
        prefs = self._sql.get_student_preferences(student_id) or {}
        result = DegreePlanGenerator.generate_multi_year_plan(
            student, degree, catalog,
            include_summer=bool(params.get("include_summer") or prefs.get("include_summer")),
            max_credits_per_sem=params.get("max_credits_per_semester") or prefs.get("max_credits_per_semester"),
            concentration=named,
        )
        plan = result.plan
        plan.plan_id = f"plan-{uuid.uuid4().hex[:10]}"
        semesters = semesters_payload(plan.semesters, catalog)
        self._sql.save_degree_plan(plan, payload={
            "semesters": semesters, "includes_summer": plan.includes_summer, "notes": list(result.notes),
        })
        self._sql.activate_plan(student_id, plan.plan_id)
        profile_updated = self._sql.sync_profile_to_plan(student_id, plan.plan_id)  # FC6
        return {
            "plan": {
                "plan_id": plan.plan_id,
                "target_major": plan.target_major,
                "concentration": plan.concentration,
                "includes_summer": plan.includes_summer,
                "semesters": semesters,
                "is_active": True,
            },
            "notes": list(result.notes),
            "profile_updated": profile_updated,
            "refusal": None,
        }

    # -------------------------------------------------------------- helpers

    def _check_course(
        self, course: Course, records: List[EnrollmentRecord], degree: Optional[DegreeRequirement],
        section: Optional[CourseSection] = None,
        semester_sections: Sequence[CourseSection] = (), semester_hours: int = 0,
    ) -> dict:
        """Run the validator (FC29–FC32) for one course; returns its payload dict."""
        return CourseRecommendationValidator.verify_all_constraints(
            course=course,
            records=records,
            candidate_section=section,
            semester_sections=semester_sections,
            current_semester_hours=semester_hours,
            max_semester_credits=degree.max_semester_credits if degree else None,
            degree=degree,
            hours_by_id=self.hours_by_ids([course.course_id] + [r.course_id for r in records]),
        ).payload()

    def _pick_section(self, course: Course, section_id: Optional[str],
                      against: Sequence[CourseSection] = ()) -> Optional[CourseSection]:
        """The requested section, or the only section if there is exactly one."""
        sections = self.sections(course.course_id)
        if section_id:
            return next((s for s in sections if s.section_id == section_id), None)
        if len(sections) <= 1:
            return sections[0] if sections else None
        # several sections: the first with open seats and no clash is the candidate; if
        # every section clashes the first one is reported so FC31 can fail honestly
        busy = list(against)

        def clashes(candidate: CourseSection) -> bool:
            return any(b.semester_term == candidate.semester_term and candidate.has_time_conflict(b)
                       for b in busy)

        open_sections = [s for s in sections if not (s.room_capacity and s.enrolled_count is not None
                                                      and s.enrolled_count >= s.room_capacity)] or sections
        return next((s for s in open_sections if not clashes(s)), open_sections[0])

    def _sections_of(self, records: List[EnrollmentRecord],
                     same_term_as: Optional[CourseSection] = None) -> List[CourseSection]:
        """Sections of the given classes — for FC31 time-conflict checks. When a
        candidate section is given, only its term is kept (and never itself)."""
        result = []
        for record in records:
            for section in self.sections(record.course_id):
                if same_term_as is None or (section.semester_term == same_term_as.semester_term
                                            and section.section_id != same_term_as.section_id):
                    result.append(section)
        return result

    def _recommendation_pool(self, student_id: str, query: Optional[str], pool_size: int) -> List[Course]:
        """Semantic hits first (FC9); the degree's remaining courses if there are none."""
        pool: List[Course] = []
        if query and query.strip():
            # prefer the SQLite record so prerequisites ride along (FC29)
            pool = [
                self._course_or_none(h["course_id"]) or Course(
                    course_id=h["course_id"], title=h["title"],
                    description=h.get("description"), credit_hours=h.get("credit_hours"))
                for h in self.semantic_courses(query, k=pool_size + 4)
            ]
        if not pool:
            pool = self._remaining_degree_courses(student_id)
        unique: List[Course] = []
        for course in pool:
            if all(c.course_id != course.course_id for c in unique):
                unique.append(course)
        return unique[:pool_size]

    def _remaining_degree_courses(self, student_id: str) -> List[Course]:
        """Required (non-elective) courses of the selected degree not yet taken."""
        degree = self.selected_degree(student_id)
        if degree is None:
            return []
        done = {r.course_id for r in self.student_classes(student_id)
                if r.status in {"passed", "taken", "in_progress"}}
        pool: List[Course] = []
        for block in degree.blocks:
            if block.kind == "electives":
                continue
            for row in block.courses:
                if row.course_id and row.course_id not in done and all(c.course_id != row.course_id for c in pool):
                    course = self._course_or_none(row.course_id)
                    if course is not None:
                        pool.append(course)
        return pool

    def _resolve_major(self, raw: str) -> Optional[DegreeRequirement]:
        """First degree whose major name contains the text (min 4 chars)."""
        text = (raw or "").strip().upper()
        if len(text) < 4:
            return None
        degrees = self._sql.list_degrees()
        by_name = next((d for d in degrees if text in d.major_name.upper()), None)
        if by_name is not None:
            return by_name
        by_id = next((d for d in degrees if text.replace(" ", "-") == d.degree_id.upper()), None)
        if by_id is not None:
            return by_id
        # "BS in Computer Science", "B.S. Software Engineering" → the bare field of study
        bare = re.sub(r"^(?:A\s+)?(?:B\.?\s?S\.?|BACHELORS?(?:\s+OF\s+SCIENCE)?)(?:\s+(?:IN|DEGREE IN))?\s+", "", text).strip()
        if len(bare) >= 4:
            return next((d for d in degrees if bare in d.major_name.upper()), None)
        return None

    @staticmethod
    def _split_target(raw: Optional[str], explicit: Optional[str] = None):
        """Split "BS in Computer Science with a concentration in Cybersecurity"
        into (major text, concentration text). An explicit concentration param wins."""
        text = (raw or "").strip()
        found = None
        match = re.search(
            r"[,\s]*(?:\b(?:with|and|plus)\b\s+)?(?:an?\s+)?\b(?:concentration|specialization|specialisation"
            r"|track|emphasis)\b\s*(?:in|on|of|:)?\s*(.+)$", text, re.IGNORECASE)
        prefix = re.search(
            r"[,\s]*\b(?:with|and|plus)\b\s+(?:an?\s+|the\s+)?(.+?)\s+\b(?:concentration|specialization"
            r"|specialisation|track|emphasis)\b[ .!?]*$", text, re.IGNORECASE)
        if match:
            found = match.group(1).strip(" .!?")
            text = text[:match.start()].strip(" ,")
        elif prefix:  # "... with a cybersecurity concentration"
            found = prefix.group(1).strip(" .!?")
            text = text[:prefix.start()].strip(" ,")
        concentration = (explicit or "").strip() or found
        return (text or None), (concentration or None)

    def _major_names(self) -> str:
        return "; ".join(sorted(d.major_name for d in self._sql.list_degrees()))
