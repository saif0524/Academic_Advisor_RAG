"""SQLDatabaseManager tests (FC1/FC7/FC8/FC10–FC14/FC20–FC21/FC16–FC17/FC33–FC34).

Runs against SQLite files in tmp_path; seedable via database/seed functions so
tests exercise the same data path the server lifespan uses.
"""
from pathlib import Path

import pytest

from core.entities.course import CourseSection
from core.entities.degree import DegreePlan, SemesterPlan
from core.entities.student import EnrollmentRecord
from database.errors import RecordNotFoundError
from database.seed import seed_sqlite
from database.sql.sqlite_manager import SQLDatabaseManager

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MAJOR = "Bachelor of Science in Computer Science"
OTHER_MAJOR = "Bachelor of Science in Software Engineering"


@pytest.fixture()
def sql(tmp_path: Path) -> SQLDatabaseManager:
    mgr = SQLDatabaseManager(tmp_path / "advisor.db")
    mgr.connect()
    yield mgr
    mgr.disconnect()


@pytest.fixture()
def seeded_sql(tmp_path: Path) -> SQLDatabaseManager:
    """Manager with all seed-owned tables populated from data/ (reload mode)."""
    path = tmp_path / "advisor.db"
    seed_sqlite(SQLDatabaseManager(path), data_dir=DATA_DIR)
    mgr = SQLDatabaseManager(path)
    mgr.connect()
    yield mgr
    mgr.disconnect()


# ---------------------------------------------------------------- FC1 / FC36

def test_get_student_record_missing_returns_none(sql):
    assert sql.get_student_record("STU-NOPE") is None


def test_ensure_student_creates_minimal_row_lazily(sql):
    """FC36: with no auth, a write to an unknown id lazily creates the row —
    optional fields stay NULL (honest unknowns)."""
    student = sql.ensure_student("STU-1", name="Test")
    assert student.student_id == "STU-1"
    assert student.name == "Test"
    assert student.current_major is None
    assert sql.get_student_record("STU-1") is not None


def test_demo_student_profile_seeds_all_properties(seeded_sql):
    """FC1/FC36: the demo seed file loads name/major/concentration/interests."""
    student = seeded_sql.get_student_record("STU-2026-9941")
    assert student is not None
    assert student.current_major == MAJOR
    assert student.concentration == "Artificial Intelligence"
    assert student.selected_degree_id == "BS-CS"


# ------------------------------------------------------------------- FC1/FC7

def test_update_major_records_history(sql):
    """FC1 (one major + one concentration) + FC7 (previous combos retained)."""
    sql.ensure_student("STU-2", name="A")
    sql.update_student_major("STU-2", OTHER_MAJOR, None)
    sql.update_student_major("STU-2", MAJOR, "Artificial Intelligence")

    student = sql.get_student_record("STU-2")
    assert student.current_major == MAJOR

    history = sql.get_major_history("STU-2")
    assert [(h["major_name"], h["active"]) for h in history] == [
        (OTHER_MAJOR, False),  # superseded
        (MAJOR, True),         # current
    ]


# ------------------------------------------------- degree selection FC16/FC17

def test_select_degree_persists_selection(seeded_sql):
    seeded_sql.set_selected_degree("STU-2026-9941", "BS-CS")
    assert seeded_sql.get_student_record("STU-2026-9941").selected_degree_id == "BS-CS"


# existence (404) and FC16 alignment (422) enforcement is service-level —
# covered by tests/server/test_data_endpoints.py::test_degree_selection_*


# ------------------------------------------------------ courses FC8/FC10/FC11

def test_list_courses_by_title_keyword(seeded_sql):
    """FC8: keyword search over course names (SQLite is the structured side)."""
    results = seeded_sql.list_courses(query="database")
    ids = [c.course_id for c in results]
    assert "3330" in ids
    assert all("DATABASE" in c.title.upper() or c.description and "database" in c.description.lower() for c in results)


def test_list_courses_by_instructor_via_sections(seeded_sql):
    """FC8: instructor keyword search consults section schedules."""
    results = seeded_sql.list_courses(query="Wei Chen")
    assert {c.course_id for c in results} >= {"1320", "1325"}  # mock schedule pairing


def test_list_courses_department_filter(seeded_sql):
    """FC10: department filter."""
    seeded_sql.list_courses(department="CSE")  # all CSE corpus rows
    results = seeded_sql.list_courses(department="MATH")
    assert results and all(c.department == "MATH" for c in results)
    assert any(c.course_id == "MATH 1426" for c in results)


def test_list_courses_term_filter_via_sections(seeded_sql):
    """FC10: semester-offered filter — courses are offered in a term when a
    section of theirs exists in it (derived from mock sections, never invented)."""
    offered = {c.course_id for c in seeded_sql.list_courses(term="Fall 2026")}
    assert "1105" in offered
    assert seeded_sql.list_courses(term="Fall 2099") == []


def test_list_courses_no_match_returns_empty(seeded_sql):
    """Grounded answers: zero matches → empty list, not filler."""
    assert seeded_sql.list_courses(query="zzz-no-such-course") == []


def test_get_course_missing_raises(seeded_sql):
    with pytest.raises(RecordNotFoundError):
        seeded_sql.get_course("9999")


def test_get_course_detail_fields(seeded_sql):
    """FC11: title/description/credits/related fields from SQLite only."""
    course = seeded_sql.get_course("3330")
    assert course.title == "DATABASE SYSTEMS AND FILE STRUCTURES"
    assert course.credit_hours == 3
    assert course.prerequisites == []  # no prereq data exists in seed files — honest empty
    assert course.offered_terms == ["Fall 2026"]  # derived from seeded sections


def test_get_course_schedule_filters_by_term(seeded_sql):
    """§4 contract: get_course_schedule(term, course_id)."""
    sections = seeded_sql.get_course_schedule("Fall 2026", "1105")
    assert sections and all(s.course_id == "1105" and s.semester_term == "Fall 2026" for s in sections)


# ------------------------------------------------------ sections FC12 / §1

def test_list_sections_with_schedule_fields(seeded_sql):
    """FC12: sections carry days, times, instructors; seat counts present."""
    sections = seeded_sql.list_sections("1105")
    assert len(sections) == 2
    first = sections[0]
    assert first.instructor and first.start_time and first.end_time
    assert first.meeting_days and all(d in {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"} for d in first.meeting_days)
    assert first.room_capacity == 40


def test_list_sections_unknown_course_empty(seeded_sql):
    assert seeded_sql.list_sections("9999") == []


def test_course_section_has_time_conflict():
    """§1 entity behavior supporting FC31 (consumed by the core validator later)."""
    a = CourseSection(section_id="s1", course_id="1105", semester_term="Fall 2026",
                      meeting_days=["Monday", "Wednesday"], start_time="09:00", end_time="09:50")
    b = CourseSection(section_id="s2", course_id="1310", semester_term="Fall 2026",
                      meeting_days=["Monday"], start_time="09:30", end_time="10:50")
    c = CourseSection(section_id="s3", course_id="1320", semester_term="Fall 2026",
                      meeting_days=["Tuesday"], start_time="09:00", end_time="09:50")
    assert a.has_time_conflict(b)
    assert not a.has_time_conflict(c)


def test_course_section_has_open_seats():
    full = CourseSection(section_id="s", course_id="1105", semester_term="t",
                         room_capacity=40, enrolled_count=40)
    assert not full.has_open_seats()


# --------------------------------------------- classes on profile FC13/14/20/21

def test_add_class_defaults_to_not_taken(seeded_sql):
    """FC14: added classes default to Not taken and persist on the profile."""
    record = seeded_sql.add_student_class("STU-2026-9941", "4344")
    assert record.status == "not_taken"
    assert record.bookmarked is False
    assert record.course_id == "4344"


def test_add_unknown_course_rejected_not_fabricated(seeded_sql):
    """Grounded-data rule: unknown course ids fail against the catalog."""
    with pytest.raises(RecordNotFoundError):
        seeded_sql.add_student_class("STU-2026-9941", "9999")


def test_duplicate_class_add_is_idempotent(seeded_sql):
    seeded_sql.add_student_class("STU-2026-9941", "4344")
    seeded_sql.add_student_class("STU-2026-9941", "4344")
    entries = [c for c in seeded_sql.list_student_classes("STU-2026-9941") if c.course_id == "4344"]
    assert len(entries) == 1


def test_update_class_status_and_bookmark(seeded_sql):
    """FC21 (status enum) + FC13 (bookmark flag)."""
    seeded_sql.add_student_class("STU-2026-9941", "4344")
    updated = seeded_sql.update_student_class("STU-2026-9941", "4344", status="in_progress", bookmarked=True)
    assert updated.status == "in_progress"
    assert updated.bookmarked is True


def test_update_class_invalid_status_rejected(seeded_sql):
    """FC21: only the five defined statuses are acceptable."""
    seeded_sql.add_student_class("STU-2026-9941", "4344")
    with pytest.raises(ValueError):
        seeded_sql.update_student_class("STU-2026-9941", "4344", status="dropped_out")


def test_remove_class(seeded_sql):
    """FC20: removal drops the profile row (idempotent false when absent)."""
    seeded_sql.add_student_class("STU-2026-9941", "4344")
    assert seeded_sql.remove_student_class("STU-2026-9941", "4344") is True
    assert seeded_sql.remove_student_class("STU-2026-9941", "4344") is False


def test_list_student_classes_includes_seeded_demo_states(seeded_sql):
    rows = {r.course_id: r for r in seeded_sql.list_student_classes("STU-2026-9941")}
    assert rows["1105"].status == "passed"  # graded demo history
    assert rows["1325"].status == "in_progress"
    assert rows["1106"].bookmarked is True


def test_get_enrollment_history_only_real_states(seeded_sql):
    """§4 contract: enrollment history for engine inputs (FC29–FC32 prep)."""
    history = seeded_sql.get_enrollment_history("STU-2026-9941")
    statuses = {h.course_id: h.status for h in history}
    assert "1105" in statuses  # passed record visible for FC30 checks
    assert all(h.status != "not_taken" for h in history)


def test_enrollment_record_is_passing_grade():
    """§1: grade semantics for FC30 (prevent recommending previously passed)."""
    assert EnrollmentRecord("s", "1105", "Fall 2024", "A", "passed").is_passing_grade()
    assert not EnrollmentRecord("s", "1301", "Spring 2025", "F", "failed").is_passing_grade()


# --------------------------------------------------------- plans FC4/FC6 persistence

def test_save_degree_plan_creates_plan_and_first_version(sql):
    """§4 contract + FC4/FC6: plans persist with a first version snapshot."""
    plan = DegreePlan(
        plan_id="PLAN-1", student_id="STU-2", degree_id="BS-CS",
        semesters=[SemesterPlan(term="Fall", year=2026, course_ids=["1310"])],
        includes_summer=False,
    )
    assert sql.save_degree_plan(plan) is True
    stored = sql.get_plan("STU-2", "PLAN-1")
    assert stored["plan_id"] == "PLAN-1"
    assert stored["version_number"] == 1
    assert stored["semesters"] == plan.to_payload()["semesters"]
    assert sql.list_plans("STU-2")


def test_plan_versions_listed_in_order(sql):
    """FC4: version history readable in order for view/revert features."""
    plan = DegreePlan(plan_id="PLAN-2", student_id="STU-2", degree_id="BS-CS",
                      semesters=[SemesterPlan(term="Fall", year=2026, course_ids=[])])
    sql.save_degree_plan(plan)
    sql.create_plan_version("PLAN-2", payload={"semesters": [{"term": "Spring", "year": 2027, "course_ids": ["1320"]}]},
                            note="added 1320")
    versions = sql.list_plan_versions("PLAN-2")
    assert [v["version_number"] for v in versions] == [1, 2]
    assert versions[1]["payload"]["semesters"][0]["course_ids"] == ["1320"]


def test_plan_ownership_enforced(sql):
    """Another student's plan is not accessible (plan_id + student ownership)."""
    plan = DegreePlan(plan_id="PLAN-1", student_id="STU-2", degree_id="BS-CS", semesters=[])
    assert sql.save_degree_plan(plan) is True
    with pytest.raises(RecordNotFoundError):
        sql.get_plan("STU-OTHER", "PLAN-1")


# ----------------------------------------------------------------- FC34 chat

def test_chat_session_and_messages_persist(sql):
    """FC34: chat history lives in SQLite (survives manager instances)."""
    session_id = sql.ensure_chat_session("STU-2")
    reopened = SQLDatabaseManager(sql.path)
    reopened.connect()
    try:
        assert reopened.ensure_chat_session("STU-2") == session_id  # same session reused
        reopened.append_chat_message(session_id, "STU-2", role="user", content="What if I switch to AI?")
        reopened.append_chat_message(session_id, "STU-2", role="assistant", content="Let's look at options.")
        history = reopened.get_chat_history("STU-2", session_id)
        assert [(m["role"], m["content"]) for m in history] == [
            ("user", "What if I switch to AI?"),
            ("assistant", "Let's look at options."),
        ]
    finally:
        reopened.disconnect()


def test_chat_history_unknown_session_rejected(sql):
    with pytest.raises(RecordNotFoundError):
        sql.get_chat_history("STU-2", "session-unknown")


def test_pending_action_store_and_resolve(sql):
    """FC23: proposed actions persist with open/confirmed state —
    attached to a real chat session (FC34 table FKs)."""
    session_id = sql.ensure_chat_session("STU-2")
    action_id = sql.create_pending_action(
        session_id=session_id, student_id="STU-2",
        action_type="add_class", description="Add CSE 4344 to your profile.",
        payload={"course_id": "4344"},
    )
    pending = sql.get_pending_action(action_id)
    assert pending["status"] == "open"
    sql.resolve_pending_action(action_id, "confirmed")
    assert sql.get_pending_action(action_id)["status"] == "confirmed"
    assert sql.resolve_pending_action(action_id, "confirmed") is False  # already resolved


# --------------------------------------------------------- degrees FC15/FC18

def test_list_degrees_returns_both_seeded_degrees(seeded_sql):
    """FC15: degrees across departments — exactly the records in data/."""
    degrees = seeded_sql.list_degrees()
    assert {d.degree_id for d in degrees} == {"BS-CS", "BS-SE"}
    majors = {d.major_name for d in degrees}
    assert MAJOR in majors and OTHER_MAJOR in majors


def test_get_degree_requirements_from_tables(seeded_sql):
    """FC18: core courses + elective rules come from requirement tables."""
    degree = seeded_sql.get_degree("BS-CS")
    assert degree.total_credits_required == 121
    assert "1105" in degree.core_courses
    assert degree.elective_rules["CSE 4000-level Technical Electives"] == 12


def test_get_degree_requirement_rows_support_progress_math(seeded_sql):
    """FC19 fuel: block-level rows (name/credits/codes) for deterministic counting."""
    rows = seeded_sql.get_degree_requirement_rows("BS-CS")
    names = {r["block_name"] for r in rows}
    assert any("Creative Arts" in n for n in names)
    creative = next(r for r in rows if "Creative Arts" in r["block_name"])
    assert creative["credits_required"] == 3
    assert len(creative["courses"]) == 8