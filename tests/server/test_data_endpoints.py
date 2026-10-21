"""FastAPI data-endpoint wiring tests — seeded managers via the real DI.

Boots the app against tmp SQLite/Chroma paths (env-configured), letting the
lifespan seed from data/ exactly like production. Covers every endpoint that
is fully data-backed after the database build; the still-unwired surface
(core engine / LLM) must keep answering 501 `not_wired`.
"""
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_DATA = Path(__file__).resolve().parents[2] / "data"
_SQLITE = "ADVISOR_SQLITE_PATH"
_CHROMA = "ADVISOR_CHROMA_PATH"
_DATA_DIR, _SEED, _EMB = "ADVISOR_DATA_DIR", "ADVISOR_SEED_MODE", "ADVISOR_EMBEDDING_FUNCTION"
_LLM = "ADVISOR_LLM_PROVIDER"

MAJOR = "Bachelor of Science in Computer Science"
OTHER_MAJOR = "Bachelor of Science in Software Engineering"


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory):
    tmp = tmp_path_factory.mktemp("api")
    saved = {k: os.environ.get(k) for k in (_SQLITE, _CHROMA, _DATA_DIR, _SEED, _EMB, _LLM)}
    os.environ[_SQLITE] = str(tmp / "advisor.db")
    os.environ[_CHROMA] = str(tmp / "chroma")
    os.environ[_DATA_DIR] = str(_DATA)
    os.environ[_SEED] = "reload"
    os.environ[_EMB] = "hash"
    os.environ[_LLM] = "stub"  # offline: agent runs on the deterministic stubs
    from server.app import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


# ------------------------------------------------------------------ courses

def test_course_keyword_search_routes_to_sql(client):
    """FC8/FC33: keyword search answered by SQLite, source echoed."""
    response = client.get("/courses", params={"q": "database"})
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "sql"
    assert body["count"] >= 1
    assert any(r["course_id"] == "3330" for r in body["results"])


def test_semantic_search_routes_to_chroma(client):
    """FC9/FC33: natural-language search answered by Chroma, source echoed."""
    response = client.get("/courses/search/semantic", params={"q": "relational database model and algebra"})
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "chroma"
    assert body["count"] >= 1
    assert body["results"][0]["course_id"] == "3330"


def test_course_detail_with_sections(client):
    """FC11/FC12: detail page fields + schedule sections from the mock seed."""
    response = client.get("/courses/1105")
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "INTRODUCTION TO COMPUTER SCIENCE AND ENGINEERING."
    assert body["credit_hours"] == 1
    assert body["prerequisites"] == []  # no prereq data exists in data/ — honest empty
    assert body["offered_terms"] == ["Fall 2026"]
    assert len(body["sections"]) == 2
    assert body["sections"][0]["instructor"]


def test_unknown_course_is_404_not_fabricated(client):
    response = client.get("/courses/9999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_course_sections_endpoint(client):
    response = client.get("/courses/1105/sections")
    assert response.status_code == 200
    assert response.json()["count"] == 2


def test_course_list_term_filter(client):
    """FC10: term filter returns only courses with sections in that term."""
    response = client.get("/courses", params={"term": "Fall 2026"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    empty = client.get("/courses", params={"term": "Spring 2099"}).json()
    assert empty["results"] == [] and empty["count"] == 0


# ------------------------------------------------------------------ classes

def test_add_class_defaults_not_taken_then_update_then_remove(client):
    """FC14 (default not_taken) → FC21 (status change) → FC20 (remove)."""
    assert client.post("/classes", json={"course_id": "9999"}).status_code == 404  # grounded: no invented courses

    added = client.post("/classes", json={"course_id": "4344"})  # router contract: 201
    assert added.status_code == 201
    assert added.json()["status"] == "not_taken"

    listing = client.get("/classes").json()
    assert any(c["course_id"] == "4344" and c["status"] == "not_taken" for c in listing["results"])
    assert any(c["course_id"] == "1106" and c["bookmarked"] for c in listing["results"])  # seeded bookmark FC13

    patched = client.patch("/classes/4344", json={"status": "in_progress", "bookmarked": True})
    assert patched.status_code == 200 and patched.json()["status"] == "in_progress"

    removed = client.delete("/classes/4344")
    assert removed.status_code == 200 and removed.json()["removed"] is True


def test_update_class_rejects_invalid_status(client):
    """FC21: only the defined status enum is accepted."""
    assert client.post("/classes", json={"course_id": "4308"}).status_code == 201
    response = client.patch("/classes/4308", json={"status": "almost_done"})
    assert response.status_code == 422  # Literal rejected at the boundary
    assert client.delete("/classes/4308").json()["removed"] is True


# ----------------------------------------------------------------- students

def test_profile_comes_from_seed_not_invention(client):
    """FC36/FC1: pre-auth identity resolves to the seeded demo profile."""
    response = client.get("/students/me")
    assert response.status_code == 200
    body = response.json()
    assert body["student_id"] == "STU-2026-9941"
    assert body["name"] == "Demo Student"
    assert body["current_major"] == MAJOR
    assert body["concentration"] == "Artificial Intelligence"


def test_degree_selection_enforces_existence_alignment_and_single(client):
    """FC17 (unknown → 404) + FC16 (aligned to major) — enforced server-side."""
    mismatch = client.put("/students/me/degree", json={"degree_id": "BS-SE"})
    assert mismatch.status_code == 422
    assert mismatch.json()["error"]["code"] == "validation_failed"

    ok = client.put("/students/me/degree", json={"degree_id": "BS-CS"})
    assert ok.status_code == 200 and ok.json()["student_id"] == "STU-2026-9941"


def test_degree_progress_counts_matched_credits(client):
    """FC19: deterministic progress — passed/taken hours matched against
    requirement rows (demo seed: 1105+1310+1320 = 7 of 121 ≈ 5.8%)."""
    response = client.get("/students/me/degree/progress")
    assert response.status_code == 200
    body = response.json()
    assert body["degree_id"] == "BS-CS"
    assert body["completion_percent"] == 5.8
    assert any("16" in r for r in body["outstanding_requirements"])  # foundation core: 23-7


def test_major_update_records_history(client):
    """FC1 (one major + one concentration) + FC7 (previous combos retained)."""
    history_before = client.get("/students/me/major-history").json()
    assert history_before["count"] == 0  # demo seed carries no prior switches

    patched = client.patch("/students/me/major", json={"major_name": OTHER_MAJOR, "concentration": "General"})
    assert patched.status_code == 200
    assert patched.json()["current_major"] == OTHER_MAJOR

    history = client.get("/students/me/major-history").json()
    pairs = [(h["major_name"], h["active"]) for h in history["results"]]
    assert pairs == [(MAJOR, False), (OTHER_MAJOR, True)]


# ------------------------------------------------------------------ degrees

def test_degree_catalog_list_and_detail(client):
    """FC15/FC18: degrees browsable; full requirement fields for one degree."""
    listing = client.get("/degrees").json()
    assert listing["count"] == 2
    assert {d["degree_id"] for d in listing["results"]} == {"BS-CS", "BS-SE"}

    detail = client.get("/degrees/BS-CS").json()
    assert detail["major_name"] == MAJOR
    assert detail["total_credits_required"] == 121
    assert detail["max_semester_credits"] == 18
    assert "1105" in detail["core_courses"]
    assert detail["elective_rules"]["CSE 4000-level Technical Electives"] == 12

    assert client.get("/degrees/BS-NOPE").status_code == 404


# --------------------------------------------------------------- chat (FC34)

def test_chat_history_wired_for_new_and_unknown_sessions(client):
    """FC34: history reads persist through SQLite; unknown session → 404."""
    fresh = client.get("/chat/messages")
    assert fresh.status_code == 200
    body = fresh.json()
    assert body["student_id"] == "STU-2026-9941" and body["messages"] == []

    from database.sql.sqlite_manager import SQLDatabaseManager

    session_id = body["session_id"]
    assert client.get("/chat/messages", params={"session_id": session_id}).status_code == 200
    assert client.get("/chat/messages", params={"session_id": "nope"}).status_code == 404


# ----------------------------------------------------- wired agent surface (FC22)

def test_chat_send_message_wired_via_agent(client):
    """FC22 wired: the stub agent answers with a clarifying question for an
    under-specified request (FC28) — honest, non-empty reply."""
    response = client.post("/chat/messages", json={"message": "What if I switch to AI?"})
    assert response.status_code == 200
    body = response.json()
    assert body["reply"]
    assert body["pending_action"] is None  # clarification, nothing proposed


def test_plan_writes_engine_backed_and_reads_wired(client):
    """FC2/FC3/FC5/FC26 now run through the built DegreePlanGenerator: plan
    writes are engine-backed (generate → edit → make active) and FC6 reads
    list what was created; unknown ids stay honest 404s."""
    created = client.post("/plans/generate", json={"major_name": MAJOR, "concentration": "General"})
    assert created.status_code == 200
    listing = client.get("/plans").json()
    assert listing["count"] >= 1
    assert client.get("/plans/unknown-plan").status_code == 404
    assert client.get("/plans/unknown-plan/versions").status_code == 404
    assert client.patch("/plans/unknown-plan", json={"semesters": []}).status_code == 404
    compare = client.post("/plans/compare", json={
        "existing_plan_id": created.json()["plan_id"], "target_major": OTHER_MAJOR,
        "target_concentration": "General"})
    assert compare.status_code == 200  # FC26 wired via the engine


def test_audits_wired_via_core_validator(client):
    """FC24/FC29–FC32 audits run in core — wired and deterministic."""
    course = client.post("/audits/course-check", json={"course_id": "3330"})
    assert course.status_code == 200
    assert course.json()["eligible"] is True
    degree = client.post("/audits/degree-check", json={})
    assert degree.status_code == 200