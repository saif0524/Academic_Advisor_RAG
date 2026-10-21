"""Shared agent-test fixtures: seeded SQLite + Chroma (hash embeddings) and
the graph wired with the STUB classifier/summarizer — LLM never called
(tester skill: business logic only, model always stubbed)."""
from pathlib import Path

import pytest

from agent.llm.classify import StubClassifier
from agent.llm.summarize import StubSummarizer
from agent.tools import AdvisorToolkit
from database.seed import seed_chroma, seed_sqlite
from database.sql.sqlite_manager import SQLDatabaseManager
from database.vector.chroma_manager import VectorDatabaseManager
from database.vector.embeddings import HashEmbeddings

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DEMO_STUDENT = "STU-2026-9941"


@pytest.fixture()
def stores(tmp_path):
    """Hermetic store pair seeded exactly the way the server lifespan seeds."""
    sql = SQLDatabaseManager(str(tmp_path / "advisor.db"))
    sql.connect()
    seed_sqlite(sql, data_dir=DATA_DIR)
    chroma = VectorDatabaseManager(
        str(tmp_path / "chroma"), embedding_function=HashEmbeddings()
    )
    chroma.connect()
    seed_chroma(chroma, data_dir=DATA_DIR)
    yield sql, chroma
    sql.disconnect()
    chroma.disconnect()


@pytest.fixture()
def toolkit(stores):
    sql, chroma = stores
    return AdvisorToolkit(sql_db_manager=sql, vector_db_manager=chroma)


@pytest.fixture()
def graph(toolkit):
    """Advisor graph with deterministic stubs (offline by construction)."""
    from agent.llm.graph import build_advisor_graph
    return build_advisor_graph(toolkit=toolkit, classifier=StubClassifier(), summarizer=StubSummarizer())


@pytest.fixture()
def session_setup(stores):
    """Seed one chat session for the demo student; return its id + manager."""
    sql, _ = stores
    session_id = sql.ensure_chat_session(DEMO_STUDENT)
    return {"sql": sql, "session_id": session_id}


def run_turn(graph, message, student_id=DEMO_STUDENT, session_id=None,
             confirmed_action_id=None, cancelled_action_id=None):
    """One full graph turn via the same shape ChatService uses."""
    return graph.invoke({
        "messages": [],
        "user_input": message,
        "student_id": student_id,
        "session_id": session_id,
        "confirmed_action_id": confirmed_action_id,
        "cancelled_action_id": cancelled_action_id,
    })