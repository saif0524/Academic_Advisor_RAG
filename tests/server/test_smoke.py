"""Thin smoke tests for the advisor HTTP API (optional per fastapi skill).

Scope: app factory boots, resources are mounted, identity works without auth,
and the not-yet-wired surface returns the 501 `not_wired` envelope rather than
fake data. Full data-backed behavior is covered by tests/database and
tests/server/test_data_endpoints.py.
"""
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_DATA = Path(__file__).resolve().parents[2] / "data"
_ENV_KEYS = ("ADVISOR_SQLITE_PATH", "ADVISOR_CHROMA_PATH", "ADVISOR_DATA_DIR",
             "ADVISOR_SEED_MODE", "ADVISOR_EMBEDDING_FUNCTION")


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """Hermetic: lifespan wiring runs against tmp-path stores seeded from data/."""
    tmp = tmp_path_factory.mktemp("smoke")
    saved = {k: os.environ.get(k) for k in _ENV_KEYS}
    os.environ.update(
        ADVISOR_SQLITE_PATH=str(tmp / "advisor.db"),
        ADVISOR_CHROMA_PATH=str(tmp / "chroma"),
        ADVISOR_DATA_DIR=str(_DATA),
        ADVISOR_SEED_MODE="reload",
        ADVISOR_EMBEDDING_FUNCTION="hash",
    )
    from server.app import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_openapi_resources_mounted(client):
    paths = client.get("/openapi.json").json()["paths"]
    expected = {
        "/health",
        "/chat/messages",
        "/courses",
        "/courses/search/semantic",
        "/courses/{course_id}",
        "/courses/{course_id}/sections",
        "/classes",
        "/classes/{course_id}",
        "/plans",
        "/plans/generate",
        "/plans/compare",
        "/plans/{plan_id}/versions",
        "/plans/{plan_id}/revert",
        "/plans/{plan_id}",
        "/degrees",
        "/degrees/{degree_id}",
        "/students/me",
        "/students/me/major",
        "/students/me/major-history",
        "/students/me/degree",
        "/students/me/degree/progress",
        "/audits/course-check",
        "/audits/degree-check",
    }
    assert expected <= set(paths)


def test_chat_send_message_not_wired(client):
    """FC22 needs the agent zone (step 4) — stays 501 honest."""
    response = client.post("/chat/messages", json={"message": "What if I switch to AI?"})
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "not_wired"


def test_semantic_search_wired(client):
    """FC9 wired: Chroma-backed semantic search answers (seed corpus)."""
    response = client.get("/courses/search/semantic", params={"q": "computer networks protocols"})
    assert response.status_code == 200
    assert response.json()["source"] == "chroma"


def test_class_crud_wired(client):
    """FC14/FC20/FC21 wired: SQLite-backed class management."""
    added = client.post("/classes", json={"course_id": "3330"})
    assert added.status_code == 201 and added.json()["status"] == "not_taken"
    patched = client.patch("/classes/3330", json={"status": "passed"})
    assert patched.status_code == 200 and patched.json()["status"] == "passed"
    removed = client.delete("/classes/3330")
    assert removed.status_code == 200 and removed.json()["removed"] is True


def test_plan_generation_not_wired(client):
    """FC2 needs DegreePlanGenerator (core) — stays 501 honest."""
    response = client.post(
        "/plans/generate",
        json={"major_name": "BS in Computer Science", "concentration": "AI", "include_summer": False},
    )
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "not_wired"


def test_audits_not_wired(client):
    """FC24 needs the core validator — stays 501 honest."""
    response = client.post("/audits/course-check", json={"course_id": "3330"})
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "not_wired"


def test_identity_from_header(client):
    """FC36: header identity respected; unknown student returns honest Nones."""
    response = client.get("/students/me", headers={"X-Student-ID": "STU-9999-0000"})
    assert response.status_code == 200
    body = response.json()
    assert body["student_id"] == "STU-9999-0000"
    assert body["name"] is None  # no record for this id — never invented


def test_identity_dev_fallback_is_seeded_student(client):
    """FC36: the default identity matches the seeded demo student profile."""
    response = client.get("/students/me")
    assert response.status_code == 200
    body = response.json()
    assert body["student_id"] == "STU-2026-9941"
    assert body["name"] == "Demo Student"  # from data/student-demo.json seed