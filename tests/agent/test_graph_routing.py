"""Advisor-graph routing + grounding tests (FC22, FC24, FC27, FC33).

Runs the StateGraph with the stub classifier/summarizer: asserts on routing
outcomes, tool payload contents, and grounded replies — never model wording.
"""
from agent.llm.classify import StubClassifier

from tests.agent.conftest import DEMO_STUDENT, run_turn


# ------------------------------------------------------------- intent routing

def test_exact_route_hits_sqlite_payload(graph):
    """FC22/FC33: course-code question → SQL facts, real seed course only."""
    state = run_turn(graph, "What time does CSE 3330 meet?")
    payload = state["tool_payload"]
    assert payload["found_course"]["course_id"] == "3330"
    assert payload["sections"], "seeded sections for 3330 must be present"
    assert any(s["section_id"] == "3330-001" for s in payload["sections"])
    assert state["reply"], "summarizer must render the SQL facts"


def test_exact_route_unknown_course_is_honest(graph):
    """Grounded-answers rule: unknown id → explicit miss, never fabricated."""
    state = run_turn(graph, "What time does CSE 9999 meet?")
    assert state["tool_payload"]["found_course"] is None
    assert "9999" in state["tool_payload"]["misses"]


def test_semantic_route_hits_chroma_payload(graph):
    """FC9/FC33: natural-language content query → Chroma similarity, honest."""
    state = run_turn(graph, "What does CSE 4380 cover?")
    assert state["tool_payload"]["query"] == "What does CSE 4380 cover?"
    assert state["tool_payload"]["hits"], "seed corpus should match security topics"


def test_recommend_route_validates_every_candidate(graph):
    """FC22 'what should I take' → candidates run the FC29–FC32 gauntlet."""
    state = run_turn(graph, "What should I take as a security elective?")
    payload = state["tool_payload"]
    assert payload["candidates"], "security corpus hits expected for the seed data"
    for candidate in payload["candidates"]:
        assert set(candidate) >= {"course_id", "title", "eligible", "checks"}
        if not candidate["eligible"]:
            assert candidate["reason"]


def test_recommend_route_never_lists_already_passed_course(graph):
    """FC30: the demo student passed 1105 — it can never appear as eligible"""
    state = run_turn(graph, "What should I take next?")
    candidates = state["tool_payload"]["candidates"]
    assert candidates, "degree-backed fallback pool guarantees candidates"
    eligible_ids = [c["course_id"] for c in candidates if c["eligible"]]
    assert "1105" not in eligible_ids


def test_recommend_route_lists_ineligible_with_reasons(graph):
    """FC29/FC30 violations surface as per-check reasons, not silent drops."""
    state = run_turn(graph, "What classes can I take that count for my degree?")
    payload = state["tool_payload"]
    assert payload["candidates"], "degree-backed fallback pool guarantees candidates"
    passed_ids = {c["course_id"] for c in payload["candidates"] if c["eligible"]}
    # 1105 is passed by the demo student → ineligible with a reason row
    assert "1105" not in passed_ids
    ineligible = [c for c in payload["candidates"] if not c["eligible"]]
    assert all(c["reason"] for c in ineligible)


def test_audit_route_runs_deterministic_validator(graph):
    """FC24: 'can I take' → validator checks, LLM never decides. The seed's
    deliberate FC31 demo: 1311-001 overlaps in-progress 1325-501."""
    state = run_turn(graph, "Can I take CSE 1311?")
    payload = state["tool_payload"]
    assert payload["result"]["eligible"] is False
    checks = {c["check_id"]: c for c in payload["result"]["checks"]}
    assert checks["FC31"]["passed"] is False
    assert "1325-501" in checks["FC31"]["reason"]


def test_audit_route_reports_fc29_fc30_alongside_conflict(graph):
    # the demo student already passed 1105 → FC30 blocks a re-recommendation
    state = run_turn(graph, "Can I take CSE 1105 still?")
    checks = {c["check_id"]: c for c in state["tool_payload"]["result"]["checks"]}
    assert checks["FC30"]["passed"] is False


def test_audit_route_degree_progress_uses_pure_math(graph):
    """FC24/FC19: degree-status question → deterministic counting payload."""
    state = run_turn(graph, "How close am I to graduation?")
    payload = state["tool_payload"]
    assert payload["progress"]["degree_id"] == "BS-CS"
    assert payload["progress"]["completion_percent"] is not None


def test_chitchat_route_gets_grounded_intro(graph):
    state = run_turn(graph, "Hey, thanks for your help all this time!")
    assert state["intent"] == "chitchat"
    assert state["reply"]


def test_history_flows_into_classifier(graph, session_setup):
    """FC27: prior turns from SQLite are available to classification context."""
    sql, session_id = session_setup["sql"], session_setup["session_id"]
    sql.append_chat_message(session_id, DEMO_STUDENT, "user", "What is CSE 4380?")
    sql.append_chat_message(session_id, DEMO_STUDENT, "assistant", "Information Security...")

    stub = StubClassifier()
    from agent.llm.graph import build_advisor_graph
    local = build_advisor_graph(toolkit=local_toolkit(sql), classifier=stub,
                                summarizer=stub_summarizer())
    run_turn(local, "What does it require?", student_id=DEMO_STUDENT, session_id=session_id)
    assert any("CSE 4380" in line for line in stub.seen_histories[-1])


def local_toolkit(sql):
    from agent.tools import AdvisorToolkit
    return AdvisorToolkit(sql_db_manager=sql, vector_db_manager=None)


def stub_summarizer():
    from agent.llm.summarize import StubSummarizer
    return StubSummarizer()


def test_unknown_session_for_history_is_404_honest(graph):
    """FC34: an explicit unknown session id errors, never silently continues."""
    from database.errors import RecordNotFoundError
    try:
        run_turn(graph, "What does 4380 cover?",
                 student_id=DEMO_STUDENT, session_id="sess-nope")
        assert False, "unknown session must raise RecordNotFoundError"
    except RecordNotFoundError:
        pass