"""Agent access to the student's active degree plan (FC22/FC24/FC27/FC33/FC6).

The plan is structured data → SQLite (FC33), never Chroma. The assistant must
see the ACTIVE plan (FC6), ignore unactivated drafts, say so honestly when no
plan is active, and never invent plan courses. LLM is always stubbed."""
from agent.llm.classify import StubClassifier
from agent.llm.graph import build_advisor_graph
from agent.llm.summarize import StubSummarizer
from tests.agent.conftest import DEMO_STUDENT, run_turn


def _make_plan(toolkit, activate=True):
    plan = toolkit.generate_plan(DEMO_STUDENT, {})["plan"]
    if activate:
        assert toolkit._sql.activate_plan(DEMO_STUDENT, plan["plan_id"])
    return plan


def _planned_ids(plan):
    return {cid for sem in plan["semesters"] for cid in sem["courses"]}


def test_active_plan_ignores_newer_inactive_draft_FC6(toolkit):
    active = _make_plan(toolkit, activate=True)
    _make_plan(toolkit, activate=False)  # newer draft, NOT active
    assert toolkit.active_plan(DEMO_STUDENT)["plan_id"] == active["plan_id"]


def test_no_active_plan_yields_none_FC6(toolkit):
    _make_plan(toolkit, activate=False)
    assert toolkit.active_plan(DEMO_STUDENT) is None
    assert toolkit.plan_context(DEMO_STUDENT) is None


def test_plan_context_carries_full_plan_and_totals_FC22(toolkit):
    plan = _make_plan(toolkit)
    ctx = toolkit.plan_context(DEMO_STUDENT)
    assert ctx["plan_id"] == plan["plan_id"]
    assert len(ctx["semesters"]) == len(plan["semesters"])  # FULL plan
    assert _planned_ids(ctx) == _planned_ids(plan)
    assert ctx["total_planned_credits"] == sum(
        (s.get("credits") or 0) for s in ctx["semesters"])
    assert "degree_id" in ctx and "includes_summer" in ctx


def test_my_plan_question_routes_exact_with_plan_payload_FC22_FC33(graph, toolkit):
    plan = _make_plan(toolkit)
    state = run_turn(graph, "What's in my degree plan?")
    assert state["intent"] == "exact"
    payload = state["tool_payload"]
    assert payload["plan"]["plan_id"] == plan["plan_id"]
    assert _planned_ids(payload["plan"]) == _planned_ids(plan)
    assert payload.get("hits") is None  # SQLite path, not Chroma (FC33)
    some_course = sorted(_planned_ids(plan))[0]
    assert some_course in state["reply"]


def test_my_plan_question_without_active_plan_is_honest_FC22(graph, toolkit):
    _make_plan(toolkit, activate=False)
    state = run_turn(graph, "What is in my plan?")
    assert state["tool_payload"]["plan"] is None
    assert "no active plan" in state["reply"].lower()


def test_progress_audit_includes_plan_FC24(graph, toolkit):
    plan = _make_plan(toolkit)
    state = run_turn(graph, "How close am I to graduating?")
    assert state["intent"] == "audit"
    assert state["tool_payload"]["plan"]["plan_id"] == plan["plan_id"]


def test_recommendations_skip_already_planned_courses_FC22(graph, toolkit):
    plan = _make_plan(toolkit)
    state = run_turn(graph, "What classes can I take?")
    payload = state["tool_payload"]
    ids = {c["course_id"] for c in payload["candidates"]}
    assert not (ids & _planned_ids(plan))
    assert set(payload["already_planned"]) <= _planned_ids(plan)
    # every surviving candidate still carries validator checks (FC29–FC32)
    assert all(c["checks"] for c in payload["candidates"])


def test_classifier_receives_plan_flag_FC27(toolkit):
    seen = []

    class Spy(StubClassifier):
        def classify(self, user_input, history=None, student_context=None):
            seen.append(student_context)
            return super().classify(user_input, history, student_context)

    g = build_advisor_graph(toolkit, Spy(), StubSummarizer())
    run_turn(g, "hello")
    assert seen[-1]["has_active_plan"] is False
    _make_plan(toolkit)
    run_turn(g, "hello")
    assert seen[-1]["has_active_plan"] is True
    assert seen[-1]["major"]
