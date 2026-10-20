"""Thin smoke tests for the advisor HTTP scaffold (optional per fastapi skill).

Scope: app factory boots, resources are mounted, identity works without a DB,
and unwired endpoints produce the 501 `not_wired` envelope rather than fake
data. Business-logic tests belong to services/core per the tester skill.
"""
import pytest
from fastapi.testclient import TestClient

from server.app import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


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
    response = client.post("/chat/messages", json={"message": "What if I switch to AI?"})
    assert response.status_code == 501
    body = response.json()
    assert body["error"]["code"] == "not_wired"


def test_semantic_search_not_wired(client):
    response = client.get("/courses/search/semantic", params={"q": "machine learning course"})
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "not_wired"


def test_class_crud_not_wired(client):
    add = client.post("/classes", json={"course_id": "1105"})
    assert add.status_code == 501
    patched = client.patch("/classes/1105", json={"status": "passed"})
    assert patched.status_code == 501
    removed = client.delete("/classes/1105")
    assert removed.status_code == 501
    for response in (add, patched, removed):
        assert response.json()["error"]["code"] == "not_wired"


def test_plan_generation_not_wired(client):
    response = client.post(
        "/plans/generate",
        json={"major_name": "BS in Computer Science", "concentration": "AI", "include_summer": False},
    )
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "not_wired"


def test_identity_from_header(client):
    response = client.get("/students/me", headers={"X-Student-ID": "STU-1111"})
    assert response.status_code == 200
    assert response.json() == {
        "student_id": "STU-1111",
        "name": None,
        "current_major": None,
        "concentration": None,
        "career_interest": None,
    }


def test_identity_dev_fallback(client):
    response = client.get("/students/me")
    assert response.status_code == 200
    assert response.json()["student_id"] == "STU-2026-9941"