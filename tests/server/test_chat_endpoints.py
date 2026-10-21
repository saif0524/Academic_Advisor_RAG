"""Chat HTTP surface tests (FC22, FC23, FC27, FC34, FC37) with a fake agent.

The lifespan boots the real database zone (env-driven hermetic stores); the
advisor-agent dependency is overridden with a scripted fake so no LLM runs.
Covers: send persistence (FC34), confirm/cancel resume validation, and the
session-list endpoint the chat drawer consumes.
"""
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_DATA = Path(__file__).resolve().parents[2] / "data"
_ENV_KEYS = ("ADVISOR_SQLITE_PATH", "ADVISOR_CHROMA_PATH", "ADVISOR_DATA_DIR",
             "ADVISOR_SEED_MODE", "ADVISOR_EMBEDDING_FUNCTION", "ADVISOR_LLM_PROVIDER")


class FakeAgent:
    """Scripted AIAdvisorAgent stand-in — records calls, returns canned turns."""

    def __init__(self):
        self.calls = []

    def process_query(self, student_id, user_input, session_id=None,
                      confirmed_action_id=None, cancelled_action_id=None):
        self.calls.append({
            "student_id": student_id, "user_input": user_input,
            "session_id": session_id, "confirmed_action_id": confirmed_action_id,
            "cancelled_action_id": cancelled_action_id,
        })
        return {
            "reply": f"stub reply to: {user_input}",
            "pending_action": (
                {"action_id": "act-x", "action_type": "add_class",
                 "description": "Add CSE 4308 Information Security to your profile"}
                if user_input == "add it" else None),
            "session_id": session_id,
        }


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("chat")
    saved = {k: os.environ.get(k) for k in _ENV_KEYS}
    os.environ.update(
        ADVISOR_SQLITE_PATH=str(tmp / "advisor.db"),
        ADVISOR_CHROMA_PATH=str(tmp / "chroma"),
        ADVISOR_DATA_DIR=str(_DATA),
        ADVISOR_SEED_MODE="reload",
        ADVISOR_EMBEDDING_FUNCTION="hash",
        ADVISOR_LLM_PROVIDER="ollama",  # overridden below — proves DI, not LLM build
    )
    from server.app import create_app
    from server.dependencies import get_advisor_agent

    app = create_app()
    agent = FakeAgent()
    app.dependency_overrides[get_advisor_agent] = lambda: agent
    with TestClient(app) as test_client:
        test_client._agent = agent
        yield test_client
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


# ------------------------------------------------------------------- FC34

def test_send_persists_user_and_assistant_turns(client):
    """FC22/FC34: one turn = user + assistant rows in SQLite chat history."""
    reply = client.post("/chat/messages", json={"message": "hello"})
    assert reply.status_code == 200
    body = reply.json()
    assert body["pending_action"] is None

    history = client.get("/chat/messages", params={"session_id": body["session_id"]}).json()
    roles = [m["role"] for m in history["messages"]]
    assert roles[-2:] == ["user", "assistant"]
    assert history["messages"][-1]["content"].startswith("stub reply")


def test_send_carries_session_and_decision_to_agent(client):
    response = client.post("/chat/messages", json={
        "message": "add it", "session_id": "sess-carry",
        "confirmed_action_id": "act-carry"})
    # unknown session still 404s BEFORE the agent runs (honest envelope)
    assert response.status_code == 404
    recorded = [c for c in client._agent.calls if c["session_id"] == "sess-carry"]
    assert recorded == []


def test_send_unknown_session_not_created(client):
    """FC34: explicit unknown session id → 404, never silently continued."""
    response = client.post(
        "/chat/messages", json={"message": "hi", "session_id": "sess-missing"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_send_continues_active_session_when_omitted(client):
    """FC27/FC34: omitted session_id continues the student's active session."""
    first = client.post("/chat/messages", json={"message": "turn one"}).json()
    second = client.post("/chat/messages", json={"message": "turn two right after"}).json()
    assert second["session_id"] == first["session_id"]


def test_pending_action_flows_back_to_client(client):
    body = client.post("/chat/messages", json={"message": "add it"}).json()
    assert body["pending_action"]["action_id"] == "act-x"
    assert body["pending_action"]["action_type"] == "add_class"


# ------------------------------------------------------ FC23 decision resume

def test_confirmed_action_id_travels_after_validation(client):
    """FC23/FC37: the confirming request must carry a REAL pending action."""
    from server import dependencies
    sql = dependencies.get_sql_db_manager()  # lifespan-constructed manager
    session_id = sql.ensure_chat_session("STU-2026-9941")
    action_id = sql.create_pending_action(
        session_id, "STU-2026-9941", "add_class", "Add CSE 4308", {"course_id": "4308"})

    body = client.post("/chat/messages", json={
        "message": "Confirmed", "session_id": session_id,
        "confirmed_action_id": action_id}).json()
    call = client._agent.calls[-1]
    assert call["confirmed_action_id"] == action_id
    assert body["pending_action"] is None  # action was resolved, not re-proposed


def test_decision_unknown_action_is_404(client):
    response = client.post("/chat/messages", json={
        "message": "Confirmed", "confirmed_action_id": "act-unknown"})
    assert response.status_code == 404


def test_decision_previously_resolved_is_422(client):
    from server import dependencies
    sql = dependencies.get_sql_db_manager()
    session_id = sql.ensure_chat_session("STU-2026-9941")
    action_id = sql.create_pending_action(
        session_id, "STU-2026-9941", "add_class", "Add CSE 4308", {})
    sql.resolve_pending_action(action_id, "cancelled")
    response = client.post("/chat/messages", json={
        "message": "Confirmed", "session_id": session_id,
        "confirmed_action_id": action_id})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_decision_on_another_students_action_is_422(client):
    """FC23: a proposal may only be decided by the student who asked for it
    (checked against both the owner and the session)."""
    from server import dependencies
    sql = dependencies.get_sql_db_manager()
    owner_session = sql.ensure_chat_session("STU-2026-9941")
    action_id = sql.create_pending_action(
        owner_session, "STU-2026-9941", "add_class", "Add CSE 4308", {})
    other_session = sql.ensure_chat_session("STU-OTHER-9")
    assert other_session != owner_session
    response = client.post("/chat/messages", json={
        "message": "Confirmed", "session_id": other_session,
        "confirmed_action_id": action_id},
        headers={"X-Student-ID": "STU-OTHER-9"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert sql.get_pending_action(action_id)["status"] == "open"


def test_history_returns_open_pending_action(client):
    """FC23/FC34 durability: an open proposal re-surfaces on history reads"""
    from server import dependencies
    sql = dependencies.get_sql_db_manager()
    session_id = sql.ensure_chat_session("STU-2026-9941")
    # isolate from earlier module tests sharing the active session
    for row in sql.execute_query(
            "SELECT action_id FROM chat_pending_actions "
            "WHERE session_id = ? AND status = 'open'", (session_id,)):
        sql.resolve_pending_action(row["action_id"], "cancelled")
    action_id = sql.create_pending_action(
        session_id, "STU-2026-9941", "add_class", "Add CSE 4308", {})
    body = client.get("/chat/messages", params={"session_id": session_id}).json()
    assert body["pending_action"]["action_id"] == action_id
    sql.resolve_pending_action(action_id, "cancelled")
    body = client.get("/chat/messages", params={"session_id": session_id}).json()
    assert body["pending_action"] is None  # resolved proposals do not come back


# ------------------------------------------------------- conversation list

def test_chat_sessions_list_returns_real_sessions(client):
    """FC34/FC35: the drawer's history view is grounded in SQLite."""
    response = client.get("/chat/sessions")
    assert response.status_code == 200
    results = response.json()["results"]
    assert results, "sessions created by the sends above must list"
    assert all("title" in s and "last_active_at" in s for s in results)