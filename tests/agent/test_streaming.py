"""FC39 streaming tests — deterministic check events + answer tokens, stub LLM."""
from agent.llm.advisor_agent import AIAdvisorAgent

from tests.agent.conftest import DEMO_STUDENT


def _stream(graph, sql, message):
    agent = AIAdvisorAgent(graph, sql)
    return list(agent.process_query_stream(DEMO_STUDENT, message))


def test_stream_emits_checks_then_tokens_then_done(graph, stores):
    events = _stream(graph, stores[0], "Can I take CSE 3330?")
    types = [e["type"] for e in events]
    assert types[-1] == "done"
    assert "check" in types and "token" in types
    assert types.index("check") < types.index("token")  # checks run before wording
    checks = [e for e in events if e["type"] == "check"]
    assert all(c["check_id"] and c["course"] == "3330" for c in checks)


def test_streamed_tokens_join_to_reply(graph, stores):
    events = _stream(graph, stores[0], "What time does CSE 3330 meet?")
    tokens = "".join(e["text"] for e in events if e["type"] == "token")
    assert tokens and tokens == events[-1]["reply"]


def test_stream_has_no_checks_when_no_engine_runs(graph, stores):
    events = _stream(graph, stores[0], "What time does CSE 3330 meet?")
    assert not [e for e in events if e["type"] == "check"]
