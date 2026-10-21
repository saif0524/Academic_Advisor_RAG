"""Seed pipeline tests (FC33, FC35) — full reload semantics into tmp stores.

The seed pipeline is the only writer of seed-owned tables; these tests pin
its grounding (all content traceable to data/), its idempotency, and its
reload behavior (user-owned chat/plan tables survive reloads; FC34).
"""
import json
from pathlib import Path

import pytest

from database.seed import (
    DEFAULT_STUDENT_ID,
    seed_chroma,
    seed_sqlite,
)
from database.sql.sqlite_manager import SQLDatabaseManager
from database.vector.chroma_manager import VectorDatabaseManager
from database.vector.embeddings import HashEmbeddings

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

SEED_SQL_TABLES = [  # (table, expected rowcount source is data-driven below)
    "courses",
    "sections",
    "degrees",
    "degree_requirement_blocks",
    "degree_requirement_courses",
    "students",
    "major_history",
    "student_classes",
]

USER_SQL_TABLES = ["chat_sessions", "chat_messages", "plans", "plan_versions"]


@pytest.fixture()
def tmp_db_paths(tmp_path: Path):
    sql_path = tmp_path / "advisor.db"
    chroma_path = tmp_path / "chroma"
    mgr = SQLDatabaseManager(sql_path)
    mgr.connect()
    seed_sqlite(mgr, data_dir=DATA_DIR)
    mgr.disconnect()

    vec = VectorDatabaseManager(chroma_path, embedding_function=HashEmbeddings())
    vec.connect()
    seed_chroma(vec, data_dir=DATA_DIR)
    vec.disconnect()
    return sql_path, chroma_path


def _counts(sql: SQLDatabaseManager) -> dict:
    return {t: sql.execute_query(f"SELECT COUNT(*) AS n FROM {t}")[0]["n"] for t in SEED_SQL_TABLES}


# ------------------------------------------------------------------ grounding

def test_seed_loads_full_course_corpus(tmp_db_paths):
    """FC33/FC35: SQLite receives the full 75-course CSE corpus."""
    sql_path, _ = tmp_db_paths
    sql = SQLDatabaseManager(sql_path)
    sql.connect()
    try:
        counts = sql.execute_query(
            "SELECT COUNT(*) AS n FROM courses WHERE department = 'CSE'")
        assert counts[0]["n"] == 77  # 75 corpus + CSE 2320/CSE 2381 (requirement-sourced, corpus-missing)
        # non-CSE gen-ed courses derived from requirement tables are present
        assert sql.execute_query(
            "SELECT COUNT(*) AS n FROM courses WHERE department != 'CSE'")[0]["n"] > 0
        # no prereq fabrication: no data exists in the seed files
        assert sql.execute_query(
            "SELECT COUNT(*) AS n FROM course_prerequisites")[0]["n"] == 0
    finally:
        sql.disconnect()


def test_seed_loads_degree_requirements_and_mock_sections(tmp_db_paths):
    sql_path, _ = tmp_db_paths
    sql = SQLDatabaseManager(sql_path)
    sql.connect()
    try:
        counts = _counts(sql)
        assert counts["degrees"] == 2
        assert counts["degree_requirement_blocks"] >= 10
        assert counts["degree_requirement_courses"] >= 50

        sections_expected = len(json.loads((DATA_DIR / "sections-mock.json").read_text())["sections"])
        assert counts["sections"] == sections_expected  # mock schedule, exact reload

        student = sql.get_student_record(DEFAULT_STUDENT_ID)
        assert student is not None and student.name == "Demo Student"
        assert sql.execute_query(
            "SELECT COUNT(*) AS n FROM student_classes WHERE student_id = ?",
            (DEFAULT_STUDENT_ID,))[0]["n"] == len(
            json.loads((DATA_DIR / "student-demo.json").read_text())["classes"])
    finally:
        sql.disconnect()


def test_seed_loads_chroma_collections(tmp_db_paths):
    """FC33: unstructured corpus (descriptions + catalog/degree text) lands in Chroma."""
    _, chroma_path = tmp_db_paths
    vec = VectorDatabaseManager(chroma_path, embedding_function=HashEmbeddings())
    vec.connect()
    try:
        assert vec.count("courses") == 75
        assert vec.count("catalog") == 4  # degree mds x2 + certificate + general core
    finally:
        vec.disconnect()


# ------------------------------------------------------------------- reload

def test_seed_reload_is_idempotent(tmp_db_paths):
    """Reload-on-startup: seed-owned tables converge to seed state again."""
    sql_path, _ = tmp_db_paths
    sql = SQLDatabaseManager(sql_path)
    sql.connect()
    try:
        before = _counts(sql)
        seed_sqlite(sql, data_dir=DATA_DIR)   # full reload, same connection
        after = _counts(sql)
        assert before == after
    finally:
        sql.disconnect()


def test_seed_reload_preserves_user_owned_tables(tmp_db_paths):
    """FC34: chat history and saved plans are user state — a reload seed must
    refresh seed-owned data without wiping them."""
    sql_path, _ = tmp_db_paths
    sql = SQLDatabaseManager(sql_path)
    sql.connect()
    try:
        session_id = sql.ensure_chat_session(DEFAULT_STUDENT_ID)
        sql.append_chat_message(session_id, DEFAULT_STUDENT_ID, "user", "keep me")
        sql.save_degree_plan(_plan())
        sql.remove_student_class(DEFAULT_STUDENT_ID, "1105")  # user mutation

        seed_sqlite(sql, data_dir=DATA_DIR)  # app reload

        history = sql.get_chat_history(DEFAULT_STUDENT_ID, session_id)
        assert history and history[0]["content"] == "keep me"          # FC34 survives
        assert sql.list_plans(DEFAULT_STUDENT_ID)                      # plans survive
        assert sql.execute_query(
            "SELECT COUNT(*) AS n FROM courses WHERE department='CSE'")[0]["n"] == 77  # seed state back
    finally:
        sql.disconnect()


def test_seed_chroma_reload_replaces_collection(tmp_db_paths):
    """Reload semantics on the vector side: stale docs cannot accumulate."""
    _, chroma_path = tmp_db_paths
    vec = VectorDatabaseManager(chroma_path, embedding_function=HashEmbeddings())
    vec.connect()
    try:
        vec.ingest_documents("courses", [{"id": "course:stale", "text": "stale doc", "metadata": {}}])
        assert vec.count("courses") == 76
        seed_chroma(vec, data_dir=DATA_DIR)
        assert vec.count("courses") == 75
    finally:
        vec.disconnect()


def _plan():
    from core.entities.degree import DegreePlan, SemesterPlan

    return DegreePlan(
        plan_id="PLAN-KEEP", student_id=DEFAULT_STUDENT_ID, degree_id="BS-CS",
        semesters=[SemesterPlan(term="Fall", year=2026, course_ids=["1310"])],
        includes_summer=False,
    )