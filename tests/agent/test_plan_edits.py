"""Plan edits from chat (FC3 via FC23): propose → explicit confirm → write.

Proposals are prechecked by the deterministic engine
(`DegreePlanGenerator.review_plan_semesters`: blocking FC30/FC32); nothing
is saved until the confirming turn, and every edit is a NEW plan version (FC4).
LLM stubbed."""
from tests.agent.conftest import DEMO_STUDENT, run_turn


def _active_plan(toolkit):
    plan = toolkit.generate_plan(DEMO_STUDENT, {})["plan"]
    toolkit._sql.activate_plan(DEMO_STUDENT, plan["plan_id"])
    return toolkit._sql.get_plan(DEMO_STUDENT, plan["plan_id"])


def _locate(plan, course_id):
    for sem in plan["semesters"]:
        if course_id in sem["courses"]:
            return sem
    return None


def _pick_removable(plan):
    # a CSE (4-digit id) course in a later semester, so "CSE <id>" is natural
    for sem in plan["semesters"][1:]:
        for cid in sem["courses"]:
            if cid.isdigit():
                return cid, sem
    raise AssertionError("plan has no 4-digit CSE course after the first semester")


def _roomy_target(plan, source):
    """The lightest other semester — leaves headroom under the FC32 cap."""
    others = [s for s in plan["semesters"]
              if (s["term"], s["year"]) != (source["term"], source["year"])]
    return min(others, key=lambda s: s.get("credits") or 0)


def _confirm(graph, state):
    action_id = state["pending_action"]["action_id"]
    return run_turn(graph, "yes", session_id=state["session_id"],
                    confirmed_action_id=action_id)


def test_remove_from_plan_proposes_without_writing_FC23(graph, toolkit):
    plan = _active_plan(toolkit)
    course, _ = _pick_removable(plan)
    state = run_turn(graph, f"Remove CSE {course} from my plan")
    assert state["pending_action"]["action_type"] == "plan_remove_course"
    after = toolkit._sql.get_plan(DEMO_STUDENT, plan["plan_id"])
    assert after["version_number"] == plan["version_number"]
    assert _locate(after, course) is not None


def test_confirmed_remove_creates_new_version_FC3_FC4(graph, toolkit):
    plan = _active_plan(toolkit)
    course, _ = _pick_removable(plan)
    state = run_turn(graph, f"Remove CSE {course} from my plan")
    _confirm(graph, state)
    after = toolkit._sql.get_plan(DEMO_STUDENT, plan["plan_id"])
    assert after["version_number"] == plan["version_number"] + 1
    assert _locate(after, course) is None


def test_cancelled_plan_edit_changes_nothing_FC23(graph, toolkit):
    plan = _active_plan(toolkit)
    course, _ = _pick_removable(plan)
    state = run_turn(graph, f"Remove CSE {course} from my plan")
    run_turn(graph, "no", session_id=state["session_id"],
             cancelled_action_id=state["pending_action"]["action_id"])
    after = toolkit._sql.get_plan(DEMO_STUDENT, plan["plan_id"])
    assert after["version_number"] == plan["version_number"]


def test_add_to_plan_semester_after_confirm_FC3(graph, toolkit):
    plan = _active_plan(toolkit)
    course, source = _pick_removable(plan)
    target = _roomy_target(plan, source)
    state = run_turn(graph, f"Remove CSE {course} from my plan")
    _confirm(graph, state)
    state = run_turn(graph, f"Add CSE {course} to my plan for {target['term']} {target['year']}",
                     session_id=state["session_id"])
    assert state["pending_action"]["action_type"] == "plan_add_course"
    _confirm(graph, state)
    after = toolkit._sql.get_plan(DEMO_STUDENT, plan["plan_id"])
    sem = _locate(after, course)
    assert sem and (sem["term"], sem["year"]) == (target["term"], target["year"])


def test_move_course_between_semesters_FC3(graph, toolkit):
    plan = _active_plan(toolkit)
    course, source = _pick_removable(plan)
    target = _roomy_target(plan, source)
    state = run_turn(graph, f"Move CSE {course} to {target['term']} {target['year']}")
    assert state["pending_action"]["action_type"] == "plan_move_course"
    _confirm(graph, state)
    sem = _locate(toolkit._sql.get_plan(DEMO_STUDENT, plan["plan_id"]), course)
    assert (sem["term"], sem["year"]) == (target["term"], target["year"])


def test_adding_completed_course_to_plan_refused_FC30(graph, toolkit):
    plan = _active_plan(toolkit)
    target = plan["semesters"][-1]
    state = run_turn(graph, f"Add CSE 1105 to my plan for {target['term']} {target['year']}")
    assert state["pending_action"] is None
    assert "1105" in state["reply"] and "FC30" in state["reply"]


def test_plan_edit_without_active_plan_refused_FC6(graph, toolkit):
    toolkit.generate_plan(DEMO_STUDENT, {})  # inactive draft only
    state = run_turn(graph, "Remove CSE 4380 from my plan")
    assert state["pending_action"] is None
    assert "no active plan" in state["reply"].lower()


def test_removing_course_not_in_plan_refused_FC22(graph, toolkit):
    _active_plan(toolkit)
    state = run_turn(graph, "Remove CSE 9999 from my plan")
    assert state["pending_action"] is None
    assert "9999" in state["reply"]


def test_activate_plan_via_chat_needs_confirmation_FC6_FC23(graph, toolkit):
    draft = toolkit.generate_plan(DEMO_STUDENT, {})["plan"]
    state = run_turn(graph, "Make my plan active")
    assert state["pending_action"]["action_type"] == "activate_plan"
    assert toolkit.active_plan(DEMO_STUDENT) is None  # nothing yet
    _confirm(graph, state)
    assert toolkit.active_plan(DEMO_STUDENT)["plan_id"] == draft["plan_id"]
