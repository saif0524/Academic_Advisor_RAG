"""CourseRecommendationValidator tests (§2 engine; FC29–FC32 + FC4c).

Pure deterministic checks — entities only, no LLM, no stores (repo rule:
if a core test needs a mock, the architecture is wrong)."""
from typing import List

from core.entities.course import Course, CourseSection
from core.entities.degree import DegreeBlock, DegreeBlockCourse, DegreeRequirement
from core.entities.student import EnrollmentRecord
from core.engine.validator import CourseRecommendationValidator
from core.engine.results import ValidationResult

DAY_COURSE = Course(
    course_id="3330", title="Discrete Structures", credit_hours=3,
    prerequisites=["4380"], offered_terms=["Fall 2026", "Spring 2027"],
)

HARD_COURSE = Course(
    course_id="4381", title="Applied Cryptography", credit_hours=3,
    prerequisites=["4380"],
)

ELECTIVE = Course(course_id="4380", title="Information Security", credit_hours=3, prerequisites=[])


def _record(course_id: str, status: str, grade: str = "B") -> EnrollmentRecord:
    return EnrollmentRecord(student_id="S", course_id=course_id, status=status, grade=grade)


def _section(section_id: str, course_id: str, days, start: str, end: str) -> CourseSection:
    return CourseSection(
        section_id=section_id, course_id=course_id, semester_term="Fall 2026",
        meeting_days=list(days), start_time=start, end_time=end,
    )


# ------------------------------------------------------------------- FC29

def test_check_prerequisites_met_when_all_passed_FC29():
    check = CourseRecommendationValidator.check_prerequisites_met(
        HARD_COURSE, [_record("4380", "passed")]
    )
    assert check.check_id == "FC29"
    assert check.passed is True


def test_check_prerequisites_fail_when_missing_FC29():
    check = CourseRecommendationValidator.check_prerequisites_met(HARD_COURSE, [])
    assert check.check_id == "FC29"
    assert check.passed is False
    assert "4380" in (check.reason or "")


def test_check_prerequisites_in_progress_does_not_satisfy_FC29():
    """In-progress is underway, not satisfied — honest fail with a reason."""
    check = CourseRecommendationValidator.check_prerequisites_met(
        HARD_COURSE, [_record("4380", "in_progress")]
    )
    assert check.passed is False
    assert "in progress" in (check.reason or "")


def test_check_prerequisites_failed_attempt_does_not_satisfy_FC29():
    check = CourseRecommendationValidator.check_prerequisites_met(
        HARD_COURSE, [_record("4380", "failed")]
    )
    assert check.passed is False


def test_check_prerequisites_no_records_passes_trivially_FC29():
    """Grounded honesty: no data is 'no prerequisite records' — never invented."""
    check = CourseRecommendationValidator.check_prerequisites_met(ELECTIVE, [])
    assert check.check_id == "FC29"
    assert check.passed is True


# ------------------------------------------------------------------- FC30

def test_check_not_already_passed_rejects_passed_FC30():
    check = CourseRecommendationValidator.check_not_already_passed(ELECTIVE, [_record("4380", "passed")])
    assert check.check_id == "FC30"
    assert check.passed is False


def test_check_not_already_passed_rejects_taken_FC30():
    """'taken' (same FC21 family) also blocks a repeat recommendation."""
    check = CourseRecommendationValidator.check_not_already_passed(ELECTIVE, [_record("4380", "taken")])
    assert check.passed is False


def test_check_not_already_passed_allows_failed_retake_FC30():
    check = CourseRecommendationValidator.check_not_already_passed(
        Course(course_id="2301", title="Ethics", prerequisites=[]),
        [_record("2301", "failed")],
    )
    assert check.passed is True


def test_check_not_already_passed_allows_new_course_FC30():
    check = CourseRecommendationValidator.check_not_already_passed(HARD_COURSE, [])
    assert check.passed is True


# ------------------------------------------------------------------- FC31

def test_check_no_schedule_conflict_detects_overlap_FC31():
    existing = [_section("1325-501", "1325", ["Tuesday", "Thursday"], "14:00", "15:20")]
    candidate = _section("1320-501", "1320", ["Tuesday", "Thursday"], "14:00", "15:20")
    check = CourseRecommendationValidator.check_no_schedule_conflict(candidate, existing)
    assert check.check_id == "FC31"
    assert check.passed is False
    assert "1325-501" in (check.reason or "")


def test_check_no_schedule_conflict_passes_disjoint_FC31():
    existing = [_section("2315-001", "2315", ["Monday", "Wednesday"], "12:00", "13:20")]
    candidate = _section("3330-001", "3330", ["Tuesday", "Thursday"], "11:00", "12:20")
    check = CourseRecommendationValidator.check_no_schedule_conflict(candidate, existing)
    assert check.passed is True


def test_check_no_schedule_conflict_skipped_without_candidate_FC31():
    check = CourseRecommendationValidator.check_no_schedule_conflict(None, [])
    assert check.passed is None  # honest: nothing to compare


def test_check_no_schedule_conflict_skipped_without_times_FC31():
    """Sections missing time data cannot conflict — honest None, not a guess."""
    blank = CourseSection(section_id="x", course_id="4380", semester_term="Fall 2026")
    check = CourseRecommendationValidator.check_no_schedule_conflict(blank, [])
    assert check.passed is None


# ------------------------------------------------------------------- FC32

def test_check_within_semester_credit_limit_passes_FC32():
    check = CourseRecommendationValidator.check_within_semester_credit_limit(
        candidate_hours=3, current_semester_hours=9, max_limit=18
    )
    assert check.check_id == "FC32"
    assert check.passed is True


def test_check_within_semester_credit_limit_blocks_over_cap_FC32():
    check = CourseRecommendationValidator.check_within_semester_credit_limit(
        candidate_hours=3, current_semester_hours=17, max_limit=18
    )
    assert check.passed is False
    assert "18" in (check.reason or "")


def test_check_within_semester_credit_limit_unknown_data_not_a_guess_FC32():
    check = CourseRecommendationValidator.check_within_semester_credit_limit(
        candidate_hours=None, current_semester_hours=0, max_limit=18
    )
    assert check.passed is None


def test_check_total_degree_credits_passes_FC32():
    degree = DegreeRequirement(degree_id="BS-CS", major_name="CS", total_credits_required=120)
    check = CourseRecommendationValidator.check_within_total_degree_credits(
        degree=degree, candidate_hours=3, completed_hours=60, planned_hours=54
    )
    assert check.passed is True


def test_check_total_degree_credits_blocks_over_ceiling_FC32():
    degree = DegreeRequirement(degree_id="BS-CS", major_name="CS", total_credits_required=120)
    check = CourseRecommendationValidator.check_within_total_degree_credits(
        degree=degree, candidate_hours=3, completed_hours=119, planned_hours=0
    )
    assert check.passed is False


def test_check_total_degree_credits_unknown_without_degree_FC32():
    check = CourseRecommendationValidator.check_within_total_degree_credits(
        degree=None, candidate_hours=3, completed_hours=10
    )
    assert check.passed is None


# ------------------------------------------------------------------- FC4c

def _cs_degree() -> DegreeRequirement:
    block = DegreeBlock(
        name="Major Core", kind="major_core", credits_required=24,
        courses=[DegreeBlockCourse(course_code="CSE 4380", course_id="4380", credit_hours=3)],
    )
    return DegreeRequirement(
        degree_id="BS-CS", major_name="CS", total_credits_required=120, blocks=[block]
    )


def test_check_fulfills_degree_requirement_applicable_FC4c():
    check = CourseRecommendationValidator.check_fulfills_degree_requirement(_cs_degree(), ELECTIVE)
    assert check.passed is True


def test_check_fulfills_degree_requirement_not_applicable_is_advisory_FC4c():
    """Not counting toward the degree is informational — it must never block
    taking a real course (eligibility is FC29–FC32)."""
    check = CourseRecommendationValidator.check_fulfills_degree_requirement(
        _cs_degree(), Course(course_id="2301", title="Ethics", prerequisites=[])
    )
    assert check.passed is False


def test_check_fulfills_degree_requirement_no_degree_is_unknown_FC4c():
    check = CourseRecommendationValidator.check_fulfills_degree_requirement(None, ELECTIVE)
    assert check.passed is None


# --------------------------------------------------- verify_all_constraints

def _all_pass_result(records: List[EnrollmentRecord], course: Course) -> ValidationResult:
    return CourseRecommendationValidator.verify_all_constraints(
        course=course,
        records=records,
        candidate_section=_section("4380-001", course.course_id, ["Monday"], "09:00", "09:50"),
        semester_sections=[],
        max_semester_credits=18,
        current_semester_hours=0,
        degree=_cs_degree(),
        hours_by_id={"4380": 3, "4381": 3},
    )


def test_verify_all_returns_eligible_when_every_check_passes_FC29_FC30_FC31_FC32():
    result = _all_pass_result([], ELECTIVE)
    assert result.eligible is True
    ids = [c.check_id for c in result.checks]
    # FC32 twice: per-semester cap + degree-total ceiling (both halves)
    assert ids == ["FC29", "FC30", "FC31", "FC32", "FC32", "FC4c"]


def test_verify_all_blocks_on_first_hard_failure_FC29_FC30():
    # FC29 satisfies itself from the passed 4380 prereq record, but FC30
    # blocks the repeat of the candidate (4381) itself.
    result = _all_pass_result([_record("4380", "passed"), _record("4381", "passed")], HARD_COURSE)
    assert result.eligible is False
    by_id = {c.check_id: c for c in result.checks}
    assert by_id["FC30"].passed is False
    assert by_id["FC29"].passed is True


def test_verify_all_missing_data_yields_unknown_not_false_FC29_FC32():
    """Unknown hours/degree checks stay None — eligible is never a wild guess."""
    result = CourseRecommendationValidator.verify_all_constraints(
        course=Course(course_id="9999", title="Mystery", prerequisites=[]),
        records=[],
        max_semester_credits=None,
        degree=None,
        hours_by_id={},
    )
    assert result.eligible is None  # unknown, not a fabricated answer


def test_verify_all_includes_section_when_given_FC31():
    candidate = _section("1320-501", "1320", ["Tuesday", "Thursday"], "14:00", "15:20")
    existing = [_section("1325-501", "1325", ["Tuesday", "Thursday"], "14:00", "15:20")]
    result = CourseRecommendationValidator.verify_all_constraints(
        course=Course(course_id="1320", title="Operating Systems", prerequisites=[]),
        records=[_record("1325", "in_progress")],
        candidate_section=candidate,
        semester_sections=existing,
    )
    assert result.eligible is False
    by_id = {c.check_id: c for c in result.checks}
    assert by_id["FC31"].passed is False