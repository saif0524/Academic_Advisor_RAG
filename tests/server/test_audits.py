"""Audit endpoint tests (FC24) — deterministic validator output over seed data.

Boots the real app (hermetic seeded stores, stub LLM provider) and asserts
the FC29–FC32 check payloads; eligibility is decided by code, never the LLM."""
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_DATA = Path(__file__).resolve().parents[2] / "data"
_ENV_KEYS = ("ADVISOR_SQLITE_PATH", "ADVISOR_CHROMA_PATH", "ADVISOR_DATA_DIR",
             "ADVISOR_SEED_MODE", "ADVISOR_EMBEDDING_FUNCTION", "ADVISOR_LLM_PROVIDER")


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("audits")
    saved = {k: os.environ.get(k) for k in _ENV_KEYS}
    os.environ.update(
        ADVISOR_SQLITE_PATH=str(tmp / "advisor.db"),
        ADVISOR_CHROMA_PATH=str(tmp / "chroma"),
        ADVISOR_DATA_DIR=str(_DATA),
        ADVISOR_SEED_MODE="reload",
        ADVISOR_EMBEDDING_FUNCTION="hash",
        ADVISOR_LLM_PROVIDER="stub",
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


def test_course_check_check_ids_and_passes(client):
    """FC24/FC29: eligibility for a seeded course lists every safeguard."""
    response = client.post("/audits/course-check", json={"course_id": "4308"})
    assert response.status_code == 200
    body = response.json()
    check_ids = [c["check_id"] for c in body["checks"]]
    # FC32 covers both halves (semester cap + degree ceiling); FC4c is the
    # informational applicability line.
    assert check_ids == ["FC29", "FC30", "FC31", "FC32", "FC32", "FC4c"]
    by_id = {c["check_id"]: c for c in body["checks"]}
    assert by_id["FC29"]["passed"] is True  # no prerequisite records on file
    assert by_id["FC30"]["passed"] is True
    assert body["eligible"] is True


def test_course_check_conflict_via_in_progress_sections(client):
    """FC24/FC31: 1311-001 collides with the demo student's in-progress
    1325-501 (seeded overlap demo) → ineligible with the section named."""
    response = client.post(
        "/audits/course-check", json={"course_id": "1311", "section_id": "1311-001"})
    body = response.json()
    by_id = {c["check_id"]: c for c in body["checks"]}
    assert by_id["FC31"]["passed"] is False
    assert "1325-501" in by_id["FC31"]["reason"]
    assert body["eligible"] is False


def test_course_check_blocks_already_passed(client):
    """FC24/FC30: the demo student passed 1105 — cannot retake-as-new."""
    response = client.post("/audits/course-check", json={"course_id": "1105"})
    by_id = {c["check_id"]: c for c in response.json()["checks"]}
    assert by_id["FC30"]["passed"] is False
    assert response.json()["eligible"] is False


def test_course_check_unknown_course_is_404(client):
    response = client.post("/audits/course-check", json={"course_id": "CSE 9999"})
    assert response.status_code == 404


def test_course_check_unknown_section_is_404(client):
    response = client.post(
        "/audits/course-check", json={"course_id": "4308", "section_id": "4308-999"})
    assert response.status_code == 404


def test_degree_check_defaults_to_selected_degree(client):
    """FC24/FC19: degree status for the demo student's selected BS-CS."""
    response = client.post("/audits/degree-check", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["degree_id"] == "BS-CS"
    assert body["completion_percent"] is not None
    assert body["checks"], "block-level outstanding lines render as checks"


def test_degree_check_explicit_degree(client):
    response = client.post("/audits/degree-check", json={"degree_id": "BS-CS"})
    assert response.json()["degree_id"] == "BS-CS"


def test_degree_check_unknown_degree_is_404(client):
    response = client.post("/audits/degree-check", json={"degree_id": "BS-NOPE"})
    assert response.status_code == 404