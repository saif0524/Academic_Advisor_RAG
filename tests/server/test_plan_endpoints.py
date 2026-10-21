"""Plan/preferences endpoint wiring tests — the DegreePlanGenerator build.
Boots the app against tmp stores seeded exactly like production (same fixture
style as test_data_endpoints.py). Covers FC2/FC3/FC4/FC5/FC6/FC25/FC26 plus
the planning-preferences endpoints (FC25/FC32 inputs) and the engine-backed
draft-review endpoint (FC29–FC32 verdicts; the LLM is never in the loop)."""
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_DATA = Path(__file__).resolve().parents[2] / "data"
_SQLITE, _CHROMA = "ADVISOR_SQLITE_PATH", "ADVISOR_CHROMA_PATH"
_DATA_DIR, _SEED, _EMB = "ADVISOR_DATA_DIR", "ADVISOR_SEED_MODE", "ADVISOR_EMBEDDING_FUNCTION"
_LLM = "ADVISOR_LLM_PROVIDER"

MAJOR = "Bachelor of Science in Computer Science"
SE_MAJOR = "Bachelor of Science in Software Engineering"
GENERAL = "General"


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory):
    tmp = tmp_path_factory.mktemp("planapi")
    saved = {k: os.environ.get(k) for k in (_SQLITE, _CHROMA, _DATA_DIR, _SEED, _EMB, _LLM)}
    os.environ[_SQLITE] = str(tmp / "advisor.db")
    os.environ[_CHROMA] = str(tmp / "chroma")
    os.environ[_DATA_DIR] = str(_DATA)
    os.environ[_SEED] = "reload"
    os.environ[_EMB] = "hash"
    os.environ[_LLM] = "stub"
    from server.app import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _generate(client, major=MAJOR, concentration=GENERAL, **overrides):
    payload = {"major_name": major, "concentration": concentration}
    payload.update(overrides)
    return client.post("/plans/generate", json=payload)


def _semester_credits(client, semesters):
    """Sum planned credit hours via the catalog (courses are SQLite truth)."""
    hours = {
        row["course_id"]: row["credit_hours"]
        for row in client.get("/courses").json()["results"]
        if row["credit_hours"] is not None
    }
    return [
        {**sem, "credits": sum(hours.get(cid, 0) for cid in sem["courses"])}
        for sem in semesters
    ]


# ------------------------------------------------------------- FC2 / FC25

def test_generate_plan_builds_roadmap_and_persists(client):
    """FC2/FC25: deterministic roadmap for a major+spec; plan is on record."""
    response = _generate(client)
    assert response.status_code == 200
    body = response.json()
    assert body["target_major"] == MAJOR
    assert body["semesters"], "a generated plan must carry semesters"
    assert body["semesters"][0]["term"] == "Fall"  # starts at the current term
    catalog_ids = {row["course_id"] for row in client.get("/courses").json()["results"]}
    planned = {cid for sem in body["semesters"] for cid in sem["courses"]}
    assert planned, "plan must place at least one grounded course"
    assert planned <= catalog_ids, f"ungrounded ids: {planned - catalog_ids}"
    assert "1105" not in planned, "demo student already passed 1105 (FC30)"
    listed = client.get("/plans").json()
    assert listed["count"] >= 1 and any(p["plan_id"] == body["plan_id"] for p in listed["results"])


def test_generate_plan_is_deterministic(client):
    first = _generate(client).json()["semesters"]
    second = _generate(client).json()["semesters"]
    assert [(s["term"], s["year"], s["courses"]) for s in first] == \
        [(s["term"], s["year"], s["courses"]) for s in second]


def test_generate_unknown_major_is_404_not_fabricated(client):
    response = _generate(client, major="Bachelor of Arts in Fictional Studies")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_generate_honors_summer_and_cap_requests(client):
    """FC25 optional summer + FC32 cap override both pass through the engine."""
    response = _generate(client, include_summer=True, max_credits_per_semester=6)
    assert response.status_code == 200
    body = response.json()
    assert body["includes_summer"] is True
    assert any(s["term"] == "Summer" for s in body["semesters"])
    for sem in _semester_credits(client, body["semesters"]):
        assert sem["credits"] <= 6, "request cap override must be enforced (FC32)"


def test_generate_cap_defaults_come_from_preferences(client):
    """Preferences (FC25/FC32 inputs) feed generation when no override is sent."""
    client.put("/students/me/preferences", json={
        "max_credits_per_semester": 6, "include_summer": False,
        "preferred_class_times": "Any time"})
    response = _generate(client)
    for sem in _semester_credits(client, response.json()["semesters"]):
        assert sem["credits"] <= 6


def test_generate_places_in_progress_courses_in_current_term(client):
    """The demo student has in-progress Fall 2026 classes — they anchor the
    roadmap's first semester instead of being re-planned."""
    body = _generate(client).json()
    first = body["semesters"][0]
    assert (first["term"], first["year"]) == ("Fall", 2026)
    assert {"1325", "2315"} <= set(first["courses"])


# -------------------------------------------------- activation + FC6 flow

def test_new_plan_is_not_active_until_confirmed(client):
    """Agreed flow (build Q2): generate → edit → make active. A fresh plan
    must NOT jump straight to active."""
    plan_id = _generate(client).json()["plan_id"]
    active = client.get("/plans/active")
    if active.status_code == 200:
        assert active.json()["plan_id"] != plan_id

    activated = client.patch(f"/plans/{plan_id}/activate")
    assert activated.status_code == 200
    assert client.get("/plans/active").json()["plan_id"] == plan_id


def test_activate_switches_the_single_active_plan(client):
    """FC6/FC17-style selection: exactly one active plan per student."""
    first = _generate(client).json()["plan_id"]
    second = _generate(client, concentration="General", include_summer=True).json()["plan_id"]
    client.patch(f"/plans/{first}/activate")
    assert client.get("/plans/active").json()["plan_id"] == first
    client.patch(f"/plans/{second}/activate")
    assert client.get("/plans/active").json()["plan_id"] == second


def test_plan_options_list_catalog_majors(client):
    response = client.get("/plans/options")
    assert response.status_code == 200
    majors = {option["name"] for option in response.json()["majors"]}
    assert {MAJOR, SE_MAJOR} <= majors


# ------------------------------------------------------------- FC3 / FC4

def test_update_plan_creates_a_new_version(client):
    plan_id = _generate(client).json()["plan_id"]
    detail = client.get(f"/plans/{plan_id}").json()
    semesters = detail["semesters"]
    moved = [{**semesters[0], "courses": semesters[0]["courses"][:-1]}] + semesters[1:]
    response = client.patch(f"/plans/{plan_id}", json={"semesters": moved})
    assert response.status_code == 200
    versions = client.get(f"/plans/{plan_id}/versions").json()
    assert len(versions["versions"]) >= 2, "edits must version history (FC4)"


def test_update_rejects_passed_course_FC30(client):
    plan_id = _generate(client).json()["plan_id"]
    detail = client.get(f"/plans/{plan_id}").json()
    bad = detail["semesters"][0]
    bad["courses"] = bad["courses"] + ["1105"]  # demo student passed 1105
    response = client.patch(f"/plans/{plan_id}", json={"semesters": [bad]})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_update_rejects_cap_breach_FC32(client):
    plan_id = _generate(client).json()["plan_id"]
    over = {"term": "Spring", "year": 2029, "courses": [
        "2315", "3310", "3311", "3330", "4308", "2441"]}  # 19 known hours > 18 cap
    response = client.patch(f"/plans/{plan_id}", json={
        "semesters": [over], "includes_summer": False})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_update_unknown_plan_is_404(client):
    response = client.patch("/plans/nope-123", json={"semesters": []})
    assert response.status_code == 404


# --------------------------------------------------------------------- FC5

def test_revert_restores_previous_version(client):
    plan_id = _generate(client).json()["plan_id"]
    original = client.get(f"/plans/{plan_id}").json()["semesters"]
    edited = [{**original[0], "courses": original[0]["courses"][:-1]}] + original[1:]
    client.patch(f"/plans/{plan_id}", json={"semesters": edited})
    response = client.post(f"/plans/{plan_id}/revert", json={"version_id": "1"})
    assert response.status_code == 200
    restored = response.json()["semesters"]
    assert [(s["term"], s["year"], s["courses"]) for s in restored] == \
        [(s["term"], s["year"], s["courses"]) for s in original]


# --------------------------------------------------- draft review (FC29–32)

def test_review_endpoint_flags_issues_FC29_FC32(client):
    flagged = {
        "semesters": [
            {"term": "Fall", "year": 2026, "courses": ["1105", "1325", "2315"]},
            {"term": "Fall", "year": 2028, "courses": ["2315", "3310", "3311", "3330",
                                                       "4308", "2441"]},  # 19h > cap 18
            {"term": "Spring", "year": 2029, "courses": ["2312", "2440"]},  # hours not on record
        ]
    }
    response = client.post("/plans/review", json=flagged)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "issues"
    keys = set(body["semester_issues"])
    assert {"fall-2026", "fall-2028"} <= keys
    texts = [i["text"] for issues in body["semester_issues"].values() for i in issues]
    assert any("already completed" in t for t in texts), "FC30 surfacing"
    assert any("cap" in t for t in texts), "FC32 surfacing"


def test_review_clean_draft_is_ok(client):
    response = client.post("/plans/review", json={
        "semesters": [{"term": "Spring", "year": 2027, "courses": ["1325", "3310"]}]})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["issues"] == []


# ------------------------------------------------------------------ FC26

def test_compare_plans_against_confirmed_major_change(client):
    existing = _generate(client, MAJOR).json()["plan_id"]
    response = client.post("/plans/compare", json={
        "existing_plan_id": existing,
        "target_major": SE_MAJOR,
        "target_concentration": GENERAL,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["target_major"] == SE_MAJOR
    assert body["retained_courses"] or body["lost_courses"], \
        "comparison must diff the two roadmaps"
    assert body["graduation_estimate"], "proposed timeline estimate grounded in the draft"
    assert isinstance(body["advantages"], list) and isinstance(body["disadvantages"], list)


def test_compare_unknown_existing_plan_404(client):
    response = client.post("/plans/compare", json={
        "existing_plan_id": "ghost-plan", "target_major": SE_MAJOR,
        "target_concentration": GENERAL})
    assert response.status_code == 404


# ----------------------------------------------------- planning preferences

def test_preferences_reflect_the_last_write(client):
    put = client.put("/students/me/preferences", json={
        "max_credits_per_semester": 16, "include_summer": True,
        "preferred_class_times": "Mornings"})
    assert put.status_code == 200
    got = client.get("/students/me/preferences").json()
    assert got == {
        "max_credits_per_semester": 16, "include_summer": True,
        "preferred_class_times": "Mornings"}