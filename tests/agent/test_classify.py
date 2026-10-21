"""Intent classification + summarization stubs (§3 routing; FC22, FC27, FC33).

The stub classifier encodes the routing contract the LLM classifier must
honour; tests assert on routing outcomes, never model wording (tester skill).
"""
import pytest

from agent.llm.classify import StubClassifier


@pytest.fixture()
def classifier() -> StubClassifier:
    return StubClassifier()


def test_course_code_question_routes_exact_sql(classifier):
    """FC33: exact/structured questions → the SQLite branch."""
    result = classifier.classify("What time does CSE 3330 meet?")
    assert result.intent == "exact"


def test_instructor_lookup_routes_exact_sql(classifier):
    result = classifier.classify("Who teaches CSE 3310?")
    assert result.intent == "exact"
    assert any("3310" in token for token in result.params.get("course_mentions", []))


def test_semantic_what_does_cover_routes_chroma(classifier):
    """FC33: natural-language course content → the Chroma branch."""
    result = classifier.classify("What does CSE 4380 cover?")
    assert result.intent == "semantic"
    assert result.params.get("query")


def test_degree_requirements_question_routes_semantic(classifier):
    result = classifier.classify("What are the requirements for the security concentration?")
    assert result.intent == "semantic"


def test_recommendation_request_routes_recommend(classifier):
    result = classifier.classify("What should I take as a security elective?")
    assert result.intent == "recommend"
    assert result.params.get("query")


def test_ability_question_routes_audit(classifier):
    result = classifier.classify("Can I take CSE 4344 next semester?")
    assert result.intent == "audit"
    assert result.params.get("course_mentions")


def test_degree_progress_question_routes_audit(classifier):
    result = classifier.classify("How close am I to graduation?")
    assert result.intent == "audit"


def test_add_class_parsed_with_course_id(classifier):
    """FC23 intent + param extraction (execution stays behind confirmation)."""
    result = classifier.classify("Add CSE 4380 to my classes")
    assert result.intent == "propose_action"
    assert result.params["action_type"] == "add_class"
    assert result.params["course_id"] == "4380"


def test_change_class_status_parsed(classifier):
    result = classifier.classify("I already completed 1310 with an A, mark it passed")
    assert result.intent == "propose_action"
    assert result.params["action_type"] == "change_class_status"
    assert result.params["course_id"] == "1310"
    assert result.params["status"] == "passed"


def test_change_major_parsed(classifier):
    result = classifier.classify("I want to switch my major to Software Engineering")
    assert result.intent == "propose_action"
    assert result.params["action_type"] == "change_major"
    assert "Software Engineering" in result.params["major_name"]


def test_change_degree_parsed(classifier):
    result = classifier.classify("Set my tracked degree to BS-CS")
    assert result.intent == "propose_action"
    assert result.params["action_type"] == "change_degree"
    assert result.params["degree_id"] == "BS-CS"


def test_major_change_without_target_needs_clarification(classifier):
    """FC28: missing target → clarification, never a guess."""
    result = classifier.classify("I want to switch my major")
    assert result.intent == "propose_action"
    assert result.followup is not None  # carries the clarify question


def test_small_talk_routes_chitchat(classifier):
    assert classifier.classify("Hey, thanks for your help!").intent == "chitchat"


def test_classifier_receives_history(classifier):
    """FC27: context rides in — the classifier sees prior turns."""
    classifier.classify("What about next semester?", history=["user: what is CSE 4380"])
    assert classifier.seen_histories[-1][-1].startswith("user:")


def test_unknown_course_mention_keeps_raw_value_for_grounding(classifier):
    result = classifier.classify("Add CSE 9999 to my classes")
    assert result.intent == "propose_action"
    assert result.params["course_id"] == "9999"  # resolved/verified by SQL later