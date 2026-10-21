"""Agent plan-generation routing tests (FC2/FC25 via the advisor graph).

The deterministic engine owns generation; the graph's plan node only assembles
inputs and relays the engine result — tested with stubbed classifier/summarizer
(tester skill: never live model calls).
"""
from tests.agent.conftest import DEMO_STUDENT, run_turn


def test_plan_request_routes_to_plan_generation(graph, stores):
    """"generate a plan" → new plan_generation intent → engine-built plan."""
    state = run_turn(graph, "Generate a degree plan for me", student_id=DEMO_STUDENT)
    assert state["intent"] == "plan_generation"
    payload = state["tool_payload"]
    plan = payload.get("plan")
    assert plan and plan["plan_id"], "engine must produce a persisted plan"
    assert plan["semesters"], "roadmap must carry semesters (FC25)"
    assert isinstance(payload["notes"], list), "grounded caveats ride along"
    sql, _ = stores
    saved = sql.list_plans(DEMO_STUDENT)
    assert any(p["plan_id"] == plan["plan_id"] for p in saved), "plan persisted (FC33)"


def test_plan_generation_follows_the_students_major_and_skips_passed_FC30(graph):
    state = run_turn(graph, "Generate a degree plan for me", student_id=DEMO_STUDENT)
    plan = state["tool_payload"]["plan"]
    assert plan["target_major"] == "Bachelor of Science in Computer Science"
    planned = {cid for sem in plan["semesters"] for cid in sem["courses"]}
    assert "1105" not in planned, "passed course can never be planned (FC30)"


def test_plan_request_for_another_major_resolves_that_degree(graph):
    state = run_turn(graph, "Generate a degree plan for Software Engineering",
                     student_id=DEMO_STUDENT)
    plan = state["tool_payload"]["plan"]
    assert plan["target_major"] == "Bachelor of Science in Software Engineering"


def test_plan_request_for_unknown_major_refuses_honestly(graph):
    state = run_turn(graph, "Generate a degree plan for underwater basket weaving",
                     student_id=DEMO_STUDENT)
    payload = state["tool_payload"]
    assert payload.get("plan") is None
    assert payload.get("refusal"), "no plan data may be invented"
    assert state["reply"], "the summarizer must render the refusal"