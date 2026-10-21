"""Degree-progress deterministic counting (FC19, FC24) — pure offline tests.

Mirrors StudentService's math now that it lives in core (agent tools need
the same function without importing the server layer)."""
from core.entities.degree import DegreeBlock, DegreeBlockCourse, DegreeRequirement
from core.engine.progress import compute_degree_progress
from core.entities.student import EnrollmentRecord


def _degree(elective_rule: str = "Technical Electives") -> DegreeRequirement:
    return DegreeRequirement(
        degree_id="BS-CS",
        major_name="Bachelor of Science in Computer Science",
        total_credits_required=120,
        blocks=[
            DegreeBlock(
                name="Science & Mathematics",
                kind="math_science", credits_required=21,
                courses=[DegreeBlockCourse(
                    course_code="MATH 1301", course_id="1310", credit_hours=3)],
            ),
            DegreeBlock(
                name=f"CSE 3000/4000-level {elective_rule}",
                kind="electives", credits_required=6,
            ),
        ],
        elective_rules={f"CSE 3000/4000-level {elective_rule}": 6},
    )


def _rec(course_id: str, status: str, grade: str = "B") -> EnrollmentRecord:
    return EnrollmentRecord(student_id="S", course_id=course_id, status=status, grade=grade)


def test_progress_counts_matched_passed_course_hours():
    records = [_rec("1310", "passed", "A")]
    totals = compute_degree_progress(
        _degree(), records, hours_by_id={"1310": 3})
    assert totals["completed_hours"] == 3
    assert totals["per_block"]["Science & Mathematics"] == 3


def test_progress_in_progress_hours_are_separate():
    records = [_rec("1310", "in_progress")]
    totals = compute_degree_progress(
        _degree(), records, hours_by_id={"1310": 3})
    assert totals["per_block"]["Science & Mathematics"] == 0
    assert totals["per_block_in_progress"]["Science & Mathematics"] == 3


def test_progress_elective_bucket_fills_by_level_cutoff():
    """Unmatched 4xxx CSE hours fill the 3000/4000-level bucket up to its cap."""
    records = [_rec("4380", "passed", "A"), _rec("4309", "passed", "A")]
    totals = compute_degree_progress(
        _degree(), records, hours_by_id={"4380": 3, "4309": 3})
    assert totals["per_block"]["CSE 3000/4000-level Technical Electives"] == 6  # capped


def test_progress_unmatched_1000_level_course_is_ignored():
    records = [_rec("1105", "passed", "A")]
    totals = compute_degree_progress(
        _degree(), records, hours_by_id={"1105": 3})
    # 1105 doesn't meet the 3000-level cutoff and isn't in a block → ignored
    assert totals["completed_hours"] == 0


def test_progress_completion_percent_against_degree_total():
    records = [_rec("1310", "passed", "A")]
    totals = compute_degree_progress(
        _degree(), records, hours_by_id={"1310": 3})
    assert totals["completion_percent"] == round(100.0 * 3 / 120, 1)


def test_progress_no_selected_degree_totals_are_honest_nones():
    totals = compute_degree_progress(None, [], hours_by_id={})
    assert totals["completion_percent"] is None
    assert totals["outstanding_requirements"] == []