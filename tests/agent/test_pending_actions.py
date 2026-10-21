"""FC23 confirm-before-acting tests: proposals precheck deterministically,
execution happens ONLY on an explicit decision, all five action kinds.

Also covers FC28 clarification for under-specified change requests."""
from tests.agent.conftest import DEMO_STUDENT, run_turn


def _open_action(sql, student_id=DEMO_STUDENT):
    rows = sql.execute_query(
        "SELECT action_id, action_type, description, payload, status FROM chat_pending_actions "
        "WHERE student_id = ? AND status = 'open'", (student_id,))
    return rows


# ------------------------------------------------------------------ proposals

def test_propose_add_class_creates_pending_row_no_write(graph, stores):
    sql, _ = stores
    state = run_turn(graph, "Add CSE 4308 to my classes")
    pending = state["pending_action"]
    assert pending and pending["action_type"] == "add_class"
    assert pending["action_id"].startswith("act-")
    # the deterministic write has NOT happened yet (FC23 gate)
    assert sql.execute_query(
        "SELECT * FROM student_classes WHERE student_id=? AND course_id='4308'",
        (DEMO_STUDENT,)) == []
    open_rows = _open_action(sql)
    assert len(open_rows) == 1 and open_rows[0]["action_type"] == "add_class"


def test_propose_add_class_of_already_passed_course_is_refused(graph, stores):
    """FC30: the safeguard refuses the proposal instead of queuing it."""
    sql, _ = stores
    state = run_turn(graph, "Add CSE 1105 to my classes")
    assert state["pending_action"] is None
    assert not _open_action(sql)
    assert state["reply"]  # refusal explained in-band


def test_propose_add_class_unknown_course_never_fabricates(graph, stores):
    sql, _ = stores
    state = run_turn(graph, "Add CSE 9999 to my classes")
    assert state["pending_action"] is None
    assert not _open_action(sql)
    assert "9999" in state["reply"], "refusal names the unknown course honestly"


def test_propose_add_class_prereq_missing_refused(graph, stores):
    """FC29 at proposal time — with a real prerequisite row (no source seed
    data for prereqs, so the test seeds one) the proposal must be refused"""
    sql, _ = stores
    sql.execute_query(
        "INSERT OR REPLACE INTO course_prerequisites (course_id, required_course_id, kind) "
        "VALUES ('4381', '4380', 'prereq')")
    state = run_turn(graph, "Add CSE 4381 to my classes")
    assert state["pending_action"] is None
    assert "4380" in state["reply"], "refusal cites the missing prerequisite"


def test_propose_change_major_resolves_catalog_name(graph, stores):
    sql, _ = stores
    state = run_turn(graph, "I want to switch my major to Software Engineering")
    pending = state["pending_action"]
    assert pending["action_type"] == "change_major"
    payload = __import__("json").loads(pending["payload"])
    assert "Bachelor of Science in Software Engineering" in payload["major_name"]
    # current major untouched until confirmation
    assert sql.get_student_record(DEMO_STUDENT).current_major == "Bachelor of Science in Computer Science"


def test_propose_change_degree_checks_fc16_alignment(graph, stores):
    sql, _ = stores
    state = run_turn(graph, "Set my tracked degree to BS-SE")
    pending = state["pending_action"]
    assert not pending, "the demo student's major is CS — BS-SE must be misaligned (FC16)"


def test_confirm_add_class_executes_deterministically(graph, stores, session_setup):
    sql, session_id = session_setup["sql"], session_setup["session_id"]
    proposed = run_turn(graph, "Add CSE 4308 to my classes", session_id=session_id)["pending_action"]

    state = run_turn(graph, "Yes do that", session_id=session_id,
                     confirmed_action_id=proposed["action_id"])
    assert "added" in state["reply"].lower()
    rows = sql.execute_query(
        "SELECT status FROM student_classes WHERE student_id=? AND course_id='4308'",
        (DEMO_STUDENT,))
    assert rows and rows[0]["status"] == "not_taken"  # FC14 default
    stored = sql.get_pending_action(proposed["action_id"])
    assert stored["status"] == "confirmed"


def test_reconfirming_resolved_action_is_rejected(graph, stores, session_setup):
    sql, session_id = session_setup["sql"], session_setup["session_id"]
    proposed = run_turn(graph, "Add CSE 4308 to my classes", session_id=session_id)["pending_action"]
    run_turn(graph, "Yes do that", session_id=session_id, confirmed_action_id=proposed["action_id"])

    state = run_turn(graph, "Yes do that again", session_id=session_id,
                     confirmed_action_id=proposed["action_id"])
    assert not sql.execute_query(
        "SELECT count(*) c FROM student_classes WHERE student_id=? AND course_id='4308'",
        (DEMO_STUDENT,))[0]["c"] > 1
    # in-band honest refusal (already resolved), not a silent success
    assert "resolved" in state["reply"].lower() or "already" in state["reply"].lower()


def test_cancel_add_class_writes_nothing(graph, stores, session_setup):
    sql, session_id = session_setup["sql"], session_setup["session_id"]
    proposed = run_turn(graph, "Add CSE 4308 to my classes", session_id=session_id)["pending_action"]

    state = run_turn(graph, "No wait, cancel that", session_id=session_id,
                     cancelled_action_id=proposed["action_id"])
    assert state["pending_action"] is None
    assert sql.execute_query(
        "SELECT * FROM student_classes WHERE student_id=? AND course_id='4308'",
        (DEMO_STUDENT,)) == []
    assert sql.get_pending_action(proposed["action_id"])["status"] == "cancelled"


def test_confirm_change_class_status(graph, stores, session_setup):
    sql, session_id = session_setup["sql"], session_setup["session_id"]
    proposed = run_turn(graph, "Mark 1310 as passed", session_id=session_id)["pending_action"]
    assert proposed["action_type"] == "change_class_status"

    run_turn(graph, "Confirmed", session_id=session_id, confirmed_action_id=proposed["action_id"])
    rows = sql.execute_query(
        "SELECT status, grade FROM student_classes WHERE student_id=? AND course_id='1310'",
        (DEMO_STUDENT,))
    assert rows[0]["status"] == "passed"


def test_confirm_change_major(graph, stores, session_setup):
    sql, session_id = session_setup["sql"], session_setup["session_id"]
    proposed = run_turn(graph, "I want to switch my major to Software Engineering",
                        session_id=session_id)["pending_action"]
    run_turn(graph, "Yes", session_id=session_id, confirmed_action_id=proposed["action_id"])
    assert sql.get_student_record(DEMO_STUDENT).current_major == "Bachelor of Science in Software Engineering"


def test_confirm_change_major_records_history_fc7(graph, stores, session_setup):
    sql, session_id = session_setup["sql"], session_setup["session_id"]
    proposed = run_turn(graph, "I want to switch my major to Software Engineering",
                        session_id=session_id)["pending_action"]
    run_turn(graph, "Yes", session_id=session_id, confirmed_action_id=proposed["action_id"])
    history = sql.get_major_history(DEMO_STUDENT)
    assert any(h["major_name"].endswith("Computer Science") and not h["active"] for h in history)
    assert any(h["major_name"].endswith("Software Engineering") and h["active"] for h in history)


def test_confirm_change_concentration(graph, stores, session_setup):
    sql, session_id = session_setup["sql"], session_setup["session_id"]
    proposed = run_turn(graph, "Switch my concentration to Cybersecurity",
                        session_id=session_id)["pending_action"]
    run_turn(graph, "Yes", session_id=session_id, confirmed_action_id=proposed["action_id"])
    assert sql.get_student_record(DEMO_STUDENT).concentration == "Cybersecurity"


def test_confirm_change_degree_with_fc16_alignment(graph, stores, session_setup):
    sql, session_id = session_setup["sql"], session_setup["session_id"]
    # BS-CS is aligned to the demo student's CS major
    proposed = run_turn(graph, "Set my tracked degree to BS-CS",
                        session_id=session_id)["pending_action"]
    assert proposed["action_type"] == "change_degree"
    run_turn(graph, "Yes", session_id=session_id, confirmed_action_id=proposed["action_id"])
    assert sql.get_student_record(DEMO_STUDENT).selected_degree_id == "BS-CS"


def test_decision_ownership_is_enforced(graph, stores, session_setup):
    """Only the proposing student may confirm — another id is rejected in-band."""
    sql, session_id = session_setup["sql"], session_setup["session_id"]
    proposed = run_turn(graph, "Add CSE 4308 to my classes", session_id=session_id)["pending_action"]

    state = run_turn(graph, "Yes", student_id="STU-OTHER-1", session_id=session_id,
                     confirmed_action_id=proposed["action_id"])
    # the action row stays open and nothing was written for the other student
    assert sql.get_pending_action(proposed["action_id"])["status"] == "open"
    assert not sql.execute_query(
        "SELECT * FROM student_classes WHERE student_id='STU-OTHER-1' AND course_id='4308'")
    assert sql.execute_query(
        "SELECT * FROM student_classes WHERE student_id=? AND course_id='4308'",
        (DEMO_STUDENT,)) == []
    assert state["reply"]


def test_decision_on_unknown_action_id_is_honest(graph, stores, session_setup):
    _, session_id = session_setup["sql"], session_setup["session_id"]
    state = run_turn(graph, "Yes", session_id=session_id, confirmed_action_id="act-gone")
    assert state["reply"]
    assert state["pending_action"] is None


def test_major_change_missing_target_asks_clarifying_question(graph, stores, session_setup):
    """FC28: "switch my major" without a target → clarify, nothing proposed."""
    sql, session_id = session_setup["sql"], session_setup["session_id"]
    state = run_turn(graph, "I want to switch my major. Please help.", session_id=session_id)
    assert state["pending_action"] is None
    assert not _open_action(sql)
    assert state["reply"].strip().endswith("?") or "?" in state["reply"], \
        "the clarify turn asks a question"