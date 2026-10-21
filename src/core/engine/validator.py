"""§2 CourseRecommendationValidator (FC29–FC32) — the non-negotiable rule.

Constraint math lives here as pure code; the LLM layer can call it (through
agent tools) but can never bypass it. Functions take entities and the data
they need as arguments — no db managers in core (monorepo dependency rule).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from core.entities.course import Course, CourseSection
from core.entities.degree import DegreeRequirement
from core.entities.student import EnrollmentRecord
from core.engine.results import ConstraintCheck, ValidationResult

_COMPLETED_STATUSES = frozenset({"passed", "taken"})


class CourseRecommendationValidator:
    """Master safeguard checks. Every function returns a `ConstraintCheck`;
    `passed is None` = needs data not on record (honest unknown, FC33)."""

    # ------------------------------------------------------------ FC29

    @staticmethod
    def check_prerequisites_met(
        course: Course, records: Sequence[EnrollmentRecord]
    ) -> ConstraintCheck:
        """Prerequisite satisfaction prior to recommending any course (FC29)."""
        check = ConstraintCheck("FC29", "Prerequisites satisfied before recommending")
        prereqs = course.get_prerequisites()
        if not prereqs:
            check.passed = True
            check.reason = f"No prerequisite records on file for {course.course_id}"
            return check
        status_by_id = {r.course_id: r.status for r in records if r.course_id in prereqs}
        unmet = [p for p in prereqs if status_by_id.get(p) not in _COMPLETED_STATUSES]
        if not unmet:
            check.passed = True
            check.reason = f"All {len(prereqs)} prerequisite(s) satisfied"
            return check
        fragments = [
            f"{p} (currently in progress)" if status_by_id.get(p) == "in_progress" else p
            for p in unmet
        ]
        check.passed = False
        check.reason = f"Not satisfied: {', '.join(fragments)}"
        return check

    # ------------------------------------------------------------ FC30

    @staticmethod
    def check_not_already_passed(
        course: Course, records: Sequence[EnrollmentRecord]
    ) -> ConstraintCheck:
        """Never recommend a previously passed course (FC30). Failed attempts
        may be re-taken and are not blocked."""
        check = ConstraintCheck("FC30", "Course not already completed/passed")
        dupes = [
            r for r in records
            if r.course_id == course.course_id and r.status in _COMPLETED_STATUSES
        ]
        if dupes:
            detail = dupes[0].semester_taken or (f"grade {dupes[0].grade}" if dupes[0].grade else "on profile")
            check.passed = False
            check.reason = f"{course.course_id} was already completed ({detail})"
            return check
        check.passed = True
        check.reason = "Not previously completed"
        return check

    # ------------------------------------------------------------ FC31

    @staticmethod
    def check_no_schedule_conflict(
        candidate_section: Optional[CourseSection],
        semester_sections: Sequence[CourseSection],
    ) -> ConstraintCheck:
        """Day/time overlap detection across sections (FC31). `passed=None`
        when no section was specified or data is missing — never a guess."""
        check = ConstraintCheck("FC31", "No schedule conflict with existing sections")
        if candidate_section is None:
            check.reason = "Skipped: no specific section was given"
            return check
        if not (candidate_section.start_time and candidate_section.end_time):
            check.reason = "Skipped: no meeting time on record for this section"
            return check
        for section in semester_sections:
            if candidate_section.has_time_conflict(section):
                check.passed = False
                check.reason = (
                    f"Conflicts with {section.section_id} ({section.get_schedule_string()})"
                )
                return check
        check.passed = True
        check.reason = "No meeting-time overlaps"
        return check

    # ------------------------------------------------------------ FC32

    @staticmethod
    def check_within_semester_credit_limit(
        candidate_hours: Optional[int],
        current_semester_hours: int = 0,
        max_limit: Optional[int] = None,
    ) -> ConstraintCheck:
        """Per-semester credit-hour cap (FC32 part 1)."""
        check = ConstraintCheck("FC32", "Within the per-semester credit-hour cap")
        if candidate_hours is None or max_limit is None:
            check.reason = "Skipped: credit hours or the semester cap are not on record"
            return check
        after = current_semester_hours + candidate_hours
        if after > max_limit:
            check.passed = False
            check.reason = f"{after} hours would exceed the {max_limit}-hour semester cap"
            return check
        check.passed = True
        check.reason = f"{after} of {max_limit} semester hours"
        return check

    @staticmethod
    def check_within_total_degree_credits(
        degree: Optional[DegreeRequirement],
        candidate_hours: Optional[int],
        completed_hours: int = 0,
        planned_hours: int = 0,
    ) -> ConstraintCheck:
        """Degree-total ceiling (FC32 part 2) — completed + planned + candidate."""
        check = ConstraintCheck("FC32", "Total stays under the degree credit ceiling")
        if degree is None or degree.total_credits_required is None:
            check.reason = "Skipped: no degree or ceiling on record"
            return check
        if candidate_hours is None:
            check.reason = "Skipped: credit hours unknown for the candidate course"
            return check
        after = completed_hours + planned_hours + candidate_hours
        if after > degree.total_credits_required:
            check.passed = False
            check.reason = (
                f"{completed_hours} completed + {planned_hours} planned + {candidate_hours} "
                f"would exceed the {degree.total_credits_required}-credit degree total"
            )
            return check
        check.passed = True
        check.reason = f"{after} of {degree.total_credits_required} degree credits"
        return check

    # -------------------------------------------------- §2 Req 4c (advisory)

    @staticmethod
    def check_fulfills_degree_requirement(
        degree: Optional[DegreeRequirement], course: Course
    ) -> ConstraintCheck:
        """Does the course count toward the degree? (§2 Req 4c) — informational:
        a miss does NOT block eligibility, it just says it won't count."""
        check = ConstraintCheck("FC4c", "Course counts toward the selected degree")
        if degree is None:
            check.reason = "Skipped: no degree selected"
            return check
        for block in degree.blocks:
            if any(row.course_id == course.course_id for row in block.courses):
                check.passed = True
                check.reason = f"Listed under “{block.name}” in {degree.degree_id}"
                return check
        check.passed = False
        check.reason = f"Not listed in {degree.degree_id} requirement blocks"
        return check

    # --------------------------------------------------------- FC22 master

    @staticmethod
    def verify_all_constraints(
        course: Course,
        records: Sequence[EnrollmentRecord],
        candidate_section: Optional[CourseSection] = None,
        semester_sections: Sequence[CourseSection] = (),
        current_semester_hours: int = 0,
        max_semester_credits: Optional[int] = None,
        degree: Optional[DegreeRequirement] = None,
        hours_by_id: Optional[Dict[str, int]] = None,
        planned_hours: int = 0,
    ) -> ValidationResult:
        """Master check (§2): FC29 + FC30 + FC31 + FC32a/FC32b, with the §2 4c
        applicability line riding along as informational. Eligibility is the
        aggregate of the hard checks only (unknowns → eligible None)."""
        hours_by_id = hours_by_id or {}
        candidate_hours = hours_by_id.get(course.course_id)
        completed_hours = sum(
            (hours_by_id.get(r.course_id) or 0)
            for r in records if r.status in _COMPLETED_STATUSES
        )
        hard = [
            CourseRecommendationValidator.check_prerequisites_met(course, records),
            CourseRecommendationValidator.check_not_already_passed(course, records),
            CourseRecommendationValidator.check_no_schedule_conflict(candidate_section, semester_sections),
            CourseRecommendationValidator.check_within_semester_credit_limit(
                candidate_hours, current_semester_hours, max_semester_credits),
            CourseRecommendationValidator.check_within_total_degree_credits(
                degree, candidate_hours, completed_hours, planned_hours),
        ]
        informational: List[ConstraintCheck] = []
        if degree is not None:
            informational.append(
                CourseRecommendationValidator.check_fulfills_degree_requirement(degree, course))
        return ValidationResult.aggregate(hard, informational)