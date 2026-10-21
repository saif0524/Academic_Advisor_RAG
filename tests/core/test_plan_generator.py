"""DegreePlanGenerator tests — deterministic engine (FC2, FC25, FC26) plus the
FC29–FC32 safeguard semantics the generator must honor. Pure/offline: entities
and a catalog dict are passed in; no db, no LLM (tester skill: core = the
heart, zero mocks)."""
from core.engine.generator import DegreePlanGenerator, PlanGenerationResult
from core.entities.course import Course
from core.entities.degree import DegreeBlock, DegreeBlockCourse, DegreeRequirement
from core.entities.student import EnrollmentRecord, Student


def course(cid: str, hours: int = 3, prereqs=()) -> Course:
    return Course(course_id=cid, title=f"T {cid}", credit_hours=hours,
                  prerequisites=list(prereqs))


CATALOG = {
    "1105": course("1105", 1),
    "1106": course("1106", 1, prereqs=["1105"]),
    "MATH 1426": course("MATH 1426", 4),
    "MATH 2425": course("MATH 2425", 4, prereqs=["MATH 1426"]),
    "ENGL 1301": course("ENGL 1301", 3),
    "2100": course("2100", 3),
    "2200": course("2200", 3, prereqs=["2100"]),
    "4308": course("4308", 3),
    "4309": course("4309", 3),
    "4311": course("4311", 3),
}

ELECTIVE_BUCKET = "CSE 4000-level Technical Electives"
DEGREE = DegreeRequirement(
    degree_id="TEST-CS",
    major_name="Bachelor of Science in Test Computer Science",
    total_credits_required=30,
    max_semester_credits=15,
    blocks=[
        DegreeBlock(
            name="Foundation Core", kind="major_core", credits_required=9,
            courses=[
                DegreeBlockCourse(course_code="CSE 1105", course_id="1105", credit_hours=1),
                DegreeBlockCourse(course_code="CSE 1106", course_id="1106", credit_hours=1),
                DegreeBlockCourse(course_code="CSE 2100", course_id="2100", credit_hours=3),
                DegreeBlockCourse(course_code="CSE 2200", course_id="2200", credit_hours=3),
            ],
        ),
        DegreeBlock(
            name="Mathematics", kind="math_science", credits_required=8,
            courses=[
                DegreeBlockCourse(course_code="MATH 1426", course_id="MATH 1426", credit_hours=4),
                DegreeBlockCourse(course_code="MATH 2425", course_id="MATH 2425", credit_hours=4),
            ],
        ),
        DegreeBlock(
            name="Communication", kind="general_core", credits_required=3,
            courses=[
                DegreeBlockCourse(course_code="ENGL 1301", course_id="ENGL 1301", credit_hours=3),
            ],
        ),
        DegreeBlock(
            name=ELECTIVE_BUCKET, kind="electives", credits_required=9,
            elective_bucket=ELECTIVE_BUCKET,
        ),
    ],
    elective_rules={ELECTIVE_BUCKET: 9},
)


def student(records=(), in_progress=()) -> Student:
    entries = [
        EnrollmentRecord(student_id="S1", course_id=cid, status="passed",
                         semester_taken="Fall 2025")
        for cid in records
    ] + [
        EnrollmentRecord(student_id="S1", course_id=cid, status="in_progress",
                         semester_taken="Fall 2026")
        for cid in in_progress
    ]
    return Student(student_id="S1", completed_courses=entries)


def plan_ids(result: PlanGenerationResult):
    return [s.course_ids for s in result.plan.semesters]


def all_ids(result: PlanGenerationResult):
    return [cid for sem in plan_ids(result) for cid in sem]


def semester_key(term: str, year: int) -> str:
    return f"{term.lower()}-{year}"


# ------------------------------------------------- FC2 / FC25 roadmap shape

def test_generate_places_every_resolvable_requirement_once_FC2():
    result = DegreePlanGenerator.generate_multi_year_plan(
        student(), DEGREE, CATALOG, current_term=("Fall", 2026))
    ids = all_ids(result)
    core = ["1106", "MATH 1426", "MATH 2425", "ENGL 1301", "2100", "2200"]
    for cid in core:
        assert ids.count(cid) == 1, f"{cid} must be planned exactly once"
    for cid in ["4308", "4309", "4311"]:  # 9 elective hours from a 3-course pool
        assert ids.count(cid) == 1


def test_generate_produces_semester_roadmap_starting_after_current_term_FC25():
    result = DegreePlanGenerator.generate_multi_year_plan(
        student(in_progress=["2100"]), DEGREE, CATALOG, current_term=("Fall", 2026))
    terms = [(s.term, s.year) for s in result.plan.semesters]
    # first semester is the current term (holds in-progress work); roadmap
    # continues in Fall/Spring alternation with no gaps
    assert terms[0] == ("Fall", 2026)
    assert result.plan.semesters[0].course_ids == ["2100"]  # in-progress current work
    expected_tail = [("Spring", 2027), ("Fall", 2027), ("Spring", 2028)]
    assert terms[1:] == expected_tail[: len(terms) - 1]
    assert terms == sorted(terms, key=lambda t: (t[1], ["Spring", "Summer", "Fall"].index(t[0])))


def test_generate_skips_completed_courses_FC30():
    result = DegreePlanGenerator.generate_multi_year_plan(
        student(records=["1105", "ENGL 1301"]), DEGREE, CATALOG, current_term=("Fall", 2026))
    ids = all_ids(result)
    assert "1105" not in ids, "previously passed course must never be planned (FC30)"
    assert "ENGL 1301" not in ids
    assert any("already completed" in note for note in result.notes)


def test_generate_orders_prereq_before_dependent_FC29():
    result = DegreePlanGenerator.generate_multi_year_plan(
        student(), DEGREE, CATALOG, current_term=("Fall", 2026))
    semesters = plan_ids(result)
    flat = all_ids(result)
    assert flat.index("2100") < flat.index("2200"), "prereq must land before dependent"
    assert flat.index("MATH 1426") < flat.index("MATH 2425")
    # and the dependent is in a strictly later semester than its prereq
    idx2100 = next(i for i, s in enumerate(semesters) if "2100" in s)
    idx2200 = next(i for i, s in enumerate(semesters) if "2200" in s)
    assert idx2200 > idx2100


def test_generate_respects_semester_credit_cap_FC32():
    result = DegreePlanGenerator.generate_multi_year_plan(
        student(), DEGREE, CATALOG, current_term=("Fall", 2026))
    hours = {cid: c.credit_hours for cid, c in CATALOG.items()}
    for sem in result.plan.semesters:
        total = sum(hours.get(cid, 0) for cid in sem.course_ids)
        assert total <= DEGREE.max_semester_credits, "per-semester cap enforced"
    # request override narrows the cap further
    narrow = DegreePlanGenerator.generate_multi_year_plan(
        student(), DEGREE, CATALOG, include_summer=False, max_credits_per_sem=7,
        current_term=("Fall", 2026))
    for sem in narrow.plan.semesters:
        total = sum(hours.get(cid, 0) for cid in sem.course_ids)
        assert total <= 7


def test_generate_totalling_stays_within_degree_total_FC32():
    result = DegreePlanGenerator.generate_multi_year_plan(
        student(), DEGREE, CATALOG, current_term=("Fall", 2026))
    hours = {cid: c.credit_hours for cid, c in CATALOG.items()}
    total = sum(hours.get(cid, 0) for cid in all_ids(result))
    assert total <= DEGREE.total_credits_required


def test_generate_summer_sessions_only_when_requested_FC25():
    without = DegreePlanGenerator.generate_multi_year_plan(
        student(), DEGREE, CATALOG, include_summer=False, max_credits_per_sem=6,
        current_term=("Fall", 2026))
    assert all(s.term != "Summer" for s in without.plan.semesters)
    with_summer = DegreePlanGenerator.generate_multi_year_plan(
        student(), DEGREE, CATALOG, include_summer=True, max_credits_per_sem=6,
        current_term=("Fall", 2026))
    assert with_summer.plan.includes_summer is True
    assert any(s.term == "Summer" for s in with_summer.plan.semesters)
    assert set(all_ids(with_summer)) == set(all_ids(without))  # same coverage


def test_generate_is_deterministic():
    a = DegreePlanGenerator.generate_multi_year_plan(
        student(), DEGREE, CATALOG, current_term=("Fall", 2026))
    b = DegreePlanGenerator.generate_multi_year_plan(
        student(), DEGREE, CATALOG, current_term=("Fall", 2026))
    assert a.plan.to_payload() == b.plan.to_payload()
    assert a.notes == b.notes


def test_generate_no_empty_semesters_FC25():
    result = DegreePlanGenerator.generate_multi_year_plan(
        student(), DEGREE, CATALOG, include_summer=True, current_term=("Fall", 2026))
    assert result.plan.semesters
    assert all(s.course_ids for s in result.plan.semesters)


# -------------------------------------------------- elective buckets + notes

def test_elective_bucket_filled_from_ground_pool_only():
    result = DegreePlanGenerator.generate_multi_year_plan(
        student(), DEGREE, CATALOG, current_term=("Fall", 2026))
    for cid in ("4308", "4309", "4311"):
        assert cid in all_ids(result)
    assert not any(cid.startswith("5") for cid in all_ids(result)), \
        "never invent elective courses outside the catalog pool"


def test_elective_bucket_runs_dry_is_reported_not_fabricated():
    small_catalog = {k: v for k, v in CATALOG.items() if k not in {"4311"}}
    result = DegreePlanGenerator.generate_multi_year_plan(
        student(), DEGREE, small_catalog, current_term=("Fall", 2026))
    ids = all_ids(result)
    assert "4311" not in ids
    assert any("unfulfilled" in note for note in result.notes)


def test_unresolvable_requirement_rows_are_excluded_with_a_note():
    degree = DegreeRequirement(
        degree_id="BROKEN", major_name="BS Broken", total_credits_required=6,
        max_semester_credits=15,
        blocks=[DegreeBlock(
            name="Mystery", kind="major_core", credits_required=3,
            courses=[DegreeBlockCourse(course_code="ENGR 9999", course_id=None,
                                       credit_hours=3)],
        )],
    )
    result = DegreePlanGenerator.generate_multi_year_plan(
        student(), degree, CATALOG, current_term=("Fall", 2026))
    assert all_ids(result) == []  # nothing resolvable — nothing invented
    assert any("Mystery" in note for note in result.notes)


# --------------------------------------------------------- FC26 comparison

def test_compare_plans_splits_retained_lost_added_FC26():
    existing_sems = [
        ("Spring", 2027, ["1106", "MATH 1426"]),
        ("Fall", 2027, ["2100", "4308"]),
    ]
    new_sems = [
        ("Spring", 2027, ["1106", "ENGL 1301"]),
        ("Fall", 2027, ["2100"]),
        ("Spring", 2028, ["4309"]),
    ]
    comparison = DegreePlanGenerator.compare_plans(existing_sems, new_sems, CATALOG)
    assert set(comparison.retained) == {"1106", "2100"}
    assert set(comparison.lost) == {"MATH 1426", "4308"}
    assert set(comparison.added) == {"ENGL 1301", "4309"}
    assert comparison.graduation_estimate == "Spring 2028"
    assert comparison.advantages or comparison.disadvantages, "trade-offs outlined (FC26)"


# --------------------------------------------------- draft review (FC29/FC32)

def test_review_flags_passed_courses_and_cap_and_prereq_order():
    draft = [
        ("Fall", 2026, ["1105", "MATH 1426", "ENGL 1301", "4308"]),  # 1105 passed; 11h ok
        ("Spring", 2027, ["MATH 2425"]),  # MATH 1426 planned previous — met
        ("Fall", 2028, ["2200", "2100", "4309"]),  # 2100 not yet seen — prereq violation
    ]
    result = DegreePlanGenerator.review_plan_semesters(
        draft, student(records=["1105"], in_progress=[]), CATALOG,
        max_credits_per_sem=15, current_term=("Fall", 2026))
    assert result.status == "issues"
    texts = [issue["text"] for sem_issues in result.semester_issues.values()
             for issue in sem_issues]
    assert any("already completed" in t for t in texts), "FC30 flagged"
    assert result.semester_issues[semester_key("Fall", 2028)], "prereq-order issue present"
    # a drafted semester over the per-semester cap is flagged (FC32)
    drafted = [
        ("Spring", 2029, ["2100", "2200", "4308", "4309", "4311", "MATH 1426"]),
    ]
    result = DegreePlanGenerator.review_plan_semesters(
        drafted, student(), CATALOG, max_credits_per_sem=15, current_term=("Fall", 2026))
    assert any("cap" in issue["text"] for issue in result.semester_issues["spring-2029"]), "FC32 flagged"


def test_review_clean_draft_is_ok():
    draft = [
        ("Fall", 2026, ["2100", "ENGL 1301"]),
        ("Spring", 2027, ["2200"]),
    ]
    result = DegreePlanGenerator.review_plan_semesters(
        draft, student(), CATALOG, max_credits_per_sem=15, current_term=("Fall", 2026))
    assert result.status == "ok"
    assert result.issues == []


def test_simulate_major_switch_generates_for_new_degree():
    other = DegreeRequirement(
        degree_id="OTHER", major_name="Bachelor of Science in Other",
        total_credits_required=24, max_semester_credits=15,
        blocks=[DegreeBlock(
            name="Core", kind="major_core", credits_required=6,
            courses=[DegreeBlockCourse(course_code="CSE 2100", course_id="2100",
                                       credit_hours=3)],
        )],
    )
    result = DegreePlanGenerator.simulate_major_switch(
        student(records=["2100"]), other, CATALOG, current_term=("Fall", 2026))
    assert result.plan.target_major == other.major_name
    assert "2100" not in all_ids(result), "FC30 carried into simulation"